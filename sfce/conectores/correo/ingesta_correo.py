"""Orquestador de ingesta de emails: descarga → clasifica → guarda → encola OCR."""
import json
import logging
import re as _re
from datetime import datetime
from pathlib import Path
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sfce.db.modelos import (
    CuentaCorreo, EmailProcesado, AdjuntoEmail,
    EnlaceEmail, ReglaClasificacionCorreo, ContrasenaZip, Empresa,
    RemitenteAutorizado,
)
from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_email
from sfce.conectores.correo.extractor_enlaces import extraer_enlaces
from sfce.conectores.correo.parser_hints import extraer_hints_asunto
from sfce.conectores.correo.filtro_ack import es_respuesta_automatica, tiene_cabecera_ack
from sfce.conectores.correo.score_email import calcular_score_email, decision_por_score
from sfce.conectores.correo.extractor_adjuntos import extraer_adjuntos, ErrorZipBomb, ErrorZipDemasiado
from sfce.conectores.correo.worker_catchall import _encolar_archivo
from sfce.conectores.correo.reenvio import (
    extraer_remitente_reenviado,
    es_asesor_gestoria,
    resolver_empresa_reenvio,
)

logger = logging.getLogger(__name__)

# Fix #6: dict único a nivel de módulo, sin redefinición interna
_ESTADO_POR_ACCION = {
    "CLASIFICAR": "CLASIFICADO",
    "APROBAR_MANUAL": "CUARENTENA",
    "IGNORAR": "IGNORADO",
    "CUARENTENA": "CUARENTENA",
}


def _cargar_contrasenas_zip(sesion: Session, empresa_id: int, remitente: str) -> list[str]:
    """Carga contraseñas ZIP configuradas para la empresa/remitente."""
    rows = sesion.execute(
        select(ContrasenaZip).where(
            ContrasenaZip.empresa_id == empresa_id,
            ContrasenaZip.activo == True,  # noqa: E712
        )
    ).scalars().all()
    passwords: list[str] = []
    for row in rows:
        patron = row.remitente_patron
        if patron is None or remitente.endswith(patron.lstrip("*")):
            passwords.extend(json.loads(row.contrasenas_json or "[]"))
    return passwords


class IngestaCorreo:
    """Orquesta el procesamiento de una cuenta de correo."""

    def __init__(self, engine: Engine, directorio_adjuntos: str = "clientes") -> None:
        self._engine = engine
        self._dir_adjuntos = Path(directorio_adjuntos)

    def procesar_cuenta(self, cuenta_id: int) -> int:
        """Procesa una cuenta de correo. Retorna número de emails nuevos procesados."""
        # Fix #2 (race condition): leer cuenta + reglas en sesión inicial
        with Session(self._engine) as sesion:
            cuenta = sesion.get(CuentaCorreo, cuenta_id)
            if not cuenta or not cuenta.activa:
                return 0
            ultimo_uid = cuenta.ultimo_uid
            empresa_id = cuenta.empresa_id
            gestoria_id = cuenta.gestoria_id
            tipo = cuenta.tipo_cuenta or "empresa"

            # Para cuentas dedicadas sin gestoria_id explícito, obtenerlo de la empresa
            if tipo == "dedicada" and not gestoria_id and empresa_id:
                empresa_obj = sesion.get(Empresa, empresa_id)
                if empresa_obj:
                    gestoria_id = empresa_obj.gestoria_id

            if tipo == "gestoria":
                reglas, empresas_gestoria = self._cargar_reglas_gestoria(
                    sesion, gestoria_id
                )
                empresas_asesor: list[dict] = []
            elif tipo == "asesor":
                reglas = []
                empresas_gestoria = []
                # Cargar empresas asignadas al asesor para routing por CIF
                usuario_id = cuenta.usuario_id
                empresas_asesor = []
                if usuario_id:
                    from sfce.db.modelos_auth import Usuario as _Usuario
                    u = sesion.get(_Usuario, usuario_id)
                    if u and u.empresas_asignadas:
                        ids_asignadas = u.empresas_asignadas
                        empresas_objs = sesion.query(Empresa).filter(
                            Empresa.id.in_(ids_asignadas)
                        ).all()
                        empresas_asesor = [
                            {"id": e.id, "cif": e.cif, "nombre": e.nombre}
                            for e in empresas_objs
                        ]
            else:
                reglas = self._cargar_reglas(sesion, empresa_id)
                empresas_gestoria = []
                empresas_asesor = []
                # Para forwarding en cuentas dedicadas: cargar empresas de la gestoría
                if tipo == "dedicada" and gestoria_id:
                    _reglas_extra, empresas_gestoria = self._cargar_reglas_gestoria(
                        sesion, gestoria_id
                    )

        emails = self._descargar_emails_cuenta(cuenta_id, ultimo_uid)
        if not emails:
            return 0

        procesados = 0
        max_uid_procesado = ultimo_uid or 0

        for email_data in emails:
            # Fix #3 (atomicidad): commit por email, fallo no afecta anteriores
            try:
                procesado = self._procesar_email(
                    email_data=email_data,
                    cuenta_id=cuenta_id,
                    empresa_id=empresa_id,
                    gestoria_id=gestoria_id,
                    tipo=tipo,
                    reglas=reglas,
                    empresas_gestoria=empresas_gestoria,
                    empresas_asesor=empresas_asesor,
                )
                if procesado:
                    procesados += 1
                    uid_str = str(email_data.get("uid", ""))
                    if uid_str.isdigit():
                        max_uid_procesado = max(max_uid_procesado, int(uid_str))
            except Exception as exc:
                logger.error(
                    "Cuenta %d — error procesando email uid=%s: %s",
                    cuenta_id, email_data.get("uid"), exc,
                    exc_info=True,
                )

        # Actualizar ultimo_uid solo si procesamos algo nuevo
        if max_uid_procesado > (ultimo_uid or 0):
            with Session(self._engine) as sesion:
                cuenta_obj = sesion.get(CuentaCorreo, cuenta_id)
                if cuenta_obj:
                    cuenta_obj.ultimo_uid = max_uid_procesado
                    sesion.commit()

        logger.info("Cuenta %d: %d emails nuevos procesados", cuenta_id, procesados)
        return procesados

    def _procesar_email(
        self,
        email_data: dict,
        cuenta_id: int,
        empresa_id: int | None,
        gestoria_id: int | None,
        tipo: str,
        reglas: list[dict],
        empresas_gestoria: list[dict],
        empresas_asesor: list[dict] | None = None,
    ) -> bool:
        """Procesa un único email. Retorna True si fue procesado (no duplicado).

        Cada email tiene su propia sesión y commit para garantizar atomicidad.
        """
        with Session(self._engine) as sesion:
            # Evitar duplicados
            ya_existe = sesion.execute(
                select(EmailProcesado).where(
                    EmailProcesado.cuenta_id == cuenta_id,
                    EmailProcesado.uid_servidor == email_data["uid"],
                )
            ).scalar_one_or_none()
            if ya_existe:
                return False

            asunto = email_data.get("asunto", "")
            headers = email_data.get("headers", {})
            remitente = email_data["remitente"]

            if tipo == "gestoria":
                email_bd = self._construir_email_gestoria(
                    email_data=email_data,
                    cuenta_id=cuenta_id,
                    asunto=asunto,
                    remitente=remitente,
                    reglas=reglas,
                    empresas_gestoria=empresas_gestoria,
                    sesion=sesion,
                )
            elif tipo == "asesor":
                email_bd = self._construir_email_asesor(
                    email_data=email_data,
                    cuenta_id=cuenta_id,
                    asunto=asunto,
                    remitente=remitente,
                    empresas_asesor=empresas_asesor or [],
                )
            else:
                email_bd = self._construir_email_dedicada(
                    email_data=email_data,
                    cuenta_id=cuenta_id,
                    empresa_id=empresa_id,
                    gestoria_id=gestoria_id,
                    asunto=asunto,
                    headers=headers,
                    remitente=remitente,
                    reglas=reglas,
                    empresas_gestoria=empresas_gestoria,
                    sesion=sesion,
                )

            sesion.add(email_bd)
            sesion.flush()

            # Registrar adjuntos en BD
            for adj in email_data.get("adjuntos", []):
                sesion.add(AdjuntoEmail(
                    email_id=email_bd.id,
                    nombre_original=adj["nombre"],
                    tamano_bytes=len(adj.get("datos_bytes", b"")),
                    mime_type=adj.get("mime_type", "application/pdf"),
                ))

            # Registrar enlaces del cuerpo HTML
            if email_data.get("cuerpo_html"):
                for enlace in extraer_enlaces(email_data["cuerpo_html"]):
                    sesion.add(EnlaceEmail(
                        email_id=email_bd.id,
                        url=enlace["url"],
                        dominio=enlace["dominio"],
                        patron_detectado=enlace["patron"],
                    ))

            # Encolar adjuntos en pipeline (solo cuentas no-gestoria con decisión positiva)
            decision = getattr(email_bd, "_decision_encola", None)
            empresa_destino = email_bd.empresa_destino_id or empresa_id
            if tipo != "gestoria" and decision in ("AUTO", "REVISION") and empresa_destino:
                try:
                    contrasenas = _cargar_contrasenas_zip(
                        sesion, empresa_destino,
                        remitente,
                    )
                    archivos = extraer_adjuntos(
                        email_data.get("adjuntos", []),
                        contrasenas_zip=contrasenas,
                    )

                    # G7: enriquecimiento del cuerpo del email
                    instrucciones_map = self._ejecutar_enriquecimiento(
                        email_data, archivos
                    )

                    for archivo in archivos:
                        instruccion = instrucciones_map.get(archivo.nombre)
                        enr_aplicado = self._aplicar_instruccion_enriquecimiento(instruccion)
                        _encolar_archivo(
                            archivo, empresa_destino, email_bd.id,
                            email_data, directorio=self._dir_adjuntos,
                            sesion=sesion,
                            hints_extra=enr_aplicado or None,
                        )
                except (ErrorZipBomb, ErrorZipDemasiado) as exc:
                    email_bd.motivo_cuarentena = type(exc).__name__
                    email_bd.estado = "CUARENTENA"

            sesion.commit()
            return True

    def _construir_email_gestoria(
        self, email_data, cuenta_id, asunto, remitente, reglas, empresas_gestoria, sesion
    ) -> "EmailProcesado":
        clasificacion = clasificar_email(
            remitente=remitente,
            asunto=asunto,
            cuerpo_texto=email_data.get("cuerpo_texto", ""),
            reglas=reglas,
        )
        accion = clasificacion.get("accion", "CUARENTENA")
        if accion == "IGNORAR" and clasificacion.get("nivel") == "IA":
            accion = "CUARENTENA"
        estado_inicial = _ESTADO_POR_ACCION.get(accion, "CUARENTENA")
        empresa_destino_id = None
        if accion == "CLASIFICAR":
            slug = clasificacion.get("slug_destino")
            if slug and empresas_gestoria:
                empresa_destino_id = self._resolver_empresa_por_slug(slug, empresas_gestoria)

        # G2: detectar ambigüedad — Fix #17 (N+1): carga todos en una sola query
        motivo_cuarentena = "SIN_REGLA" if estado_inicial == "CUARENTENA" else None
        if empresas_gestoria:
            empresas_ids = [
                e.id if hasattr(e, "id") else e.get("id")
                for e in empresas_gestoria
            ]
            candidatos_g2 = _detectar_ambiguedad_remitente_bulk(
                remitente, empresas_ids, sesion
            )
            if len(candidatos_g2) > 1:
                logger.warning(
                    "G2: remitente '%s' en %d empresas — cuarentena por ambiguedad",
                    remitente, len(candidatos_g2),
                )
                accion = "CUARENTENA"
                estado_inicial = "CUARENTENA"
                empresa_destino_id = None
                motivo_cuarentena = "AMBIGUEDAD_REMITENTE"
            elif len(candidatos_g2) == 1 and empresa_destino_id is None:
                empresa_destino_id = candidatos_g2[0]

        # G13: hints del asunto
        hints_gestoria = extraer_hints_asunto(asunto)
        if hints_gestoria.tipo_doc and clasificacion.get("tipo_doc") is None:
            clasificacion["tipo_doc"] = hints_gestoria.tipo_doc

        return EmailProcesado(
            cuenta_id=cuenta_id,
            uid_servidor=email_data["uid"],
            message_id=email_data.get("message_id"),
            remitente=remitente,
            asunto=asunto,
            fecha_email=email_data.get("fecha"),
            estado=estado_inicial,
            nivel_clasificacion=clasificacion["nivel"],
            empresa_destino_id=empresa_destino_id,
            confianza_ia=clasificacion.get("confianza"),
            es_respuesta_ack=False,
            score_confianza=None,
            motivo_cuarentena=motivo_cuarentena,
        )

    def _construir_email_asesor(
        self, email_data, cuenta_id, asunto, remitente, empresas_asesor
    ) -> "EmailProcesado":
        """Routing por CIF: extrae CIF del primer adjunto PDF y lo cruza con
        las empresas asignadas al asesor. Fallback: cuarentena SIN_CIF_IDENTIFICABLE."""
        empresa_destino_id = None
        motivo_cuarentena = None
        estado = "CLASIFICADO"

        for adj in email_data.get("adjuntos", []):
            b = adj.get("bytes") or adj.get("datos_bytes", b"")
            if b:
                cif = _extraer_cif_pdf(b)
                if cif:
                    empresa_destino_id = _resolver_empresa_por_cif(cif, empresas_asesor)
                    break

        if empresa_destino_id is None:
            estado = "CUARENTENA"
            motivo_cuarentena = "SIN_CIF_IDENTIFICABLE"

        return EmailProcesado(
            cuenta_id=cuenta_id,
            uid_servidor=email_data["uid"],
            message_id=email_data.get("message_id"),
            remitente=remitente,
            asunto=asunto,
            fecha_email=email_data.get("fecha"),
            estado=estado,
            nivel_clasificacion="REGLA",
            empresa_destino_id=empresa_destino_id,
            confianza_ia=None,
            es_respuesta_ack=False,
            score_confianza=None,
            motivo_cuarentena=motivo_cuarentena,
        )

    def _construir_email_dedicada(
        self, email_data, cuenta_id, empresa_id, gestoria_id,
        asunto, headers, remitente, reglas, empresas_gestoria, sesion
    ) -> "EmailProcesado":
        # Fix #4: empresa_destino_id = empresa_id de la cuenta (no None)
        empresa_destino_id = empresa_id
        motivo_cuarentena = None

        # 1. Filtro anti-loop ACK
        es_ack = es_respuesta_automatica(asunto) or tiene_cabecera_ack(headers)

        # 2. Detección de reenvío entre asesores
        es_reenvio = False
        score_guardado: float | None = None

        if not es_ack and gestoria_id and empresas_gestoria:
            es_reenvio = es_asesor_gestoria(remitente, gestoria_id, sesion)

        if es_reenvio:
            decision, empresa_destino_id, motivo_cuarentena = self._resolver_reenvio(
                email_data=email_data,
                gestoria_id=gestoria_id,
                empresas_gestoria=empresas_gestoria,
                empresa_id_cuenta=empresa_id,
                sesion=sesion,
            )
        elif es_ack:
            decision = "IGNORAR"
        else:
            # Email normal: calcular score UNA SOLA VEZ
            score_guardado, _factores = calcular_score_email(email_data, empresa_id, sesion)
            decision = decision_por_score(score_guardado)
            if decision == "CUARENTENA":
                motivo_cuarentena = "SCORE_BAJO"

        # 3. Clasificación por reglas (para hints y nivel)
        hints = extraer_hints_asunto(asunto)
        clasificacion = clasificar_email(
            remitente=remitente,
            asunto=asunto,
            cuerpo_texto=email_data.get("cuerpo_texto", ""),
            reglas=reglas,
        )
        if hints.tipo_doc and clasificacion.get("tipo_doc") is None:
            clasificacion["tipo_doc"] = hints.tipo_doc

        estado_inicial = {
            "AUTO": "CLASIFICADO",
            "REVISION": "CLASIFICADO",
            "CUARENTENA": "CUARENTENA",
            "IGNORAR": "IGNORADO",
        }.get(decision, "PENDIENTE")

        email_obj = EmailProcesado(
            cuenta_id=cuenta_id,
            uid_servidor=email_data["uid"],
            message_id=email_data.get("message_id"),
            remitente=remitente,
            asunto=asunto,
            fecha_email=email_data.get("fecha"),
            estado=estado_inicial,
            nivel_clasificacion=clasificacion["nivel"],
            empresa_destino_id=empresa_destino_id,  # Fix #4: ya no es None
            confianza_ia=clasificacion.get("confianza"),
            es_respuesta_ack=es_ack,
            score_confianza=score_guardado if not es_ack and not es_reenvio else None,
            motivo_cuarentena=motivo_cuarentena,
        )
        # Guardar decision en atributo temporal para encolar en _procesar_email
        email_obj._decision_encola = decision  # type: ignore[attr-defined]
        return email_obj

    def _resolver_reenvio(
        self,
        email_data: dict,
        gestoria_id: int,
        empresas_gestoria: list[dict],
        empresa_id_cuenta: int | None,
        sesion: Session,
    ) -> tuple[str, int | None, str | None]:
        """Determina decision+empresa para un email reenviado por un asesor.

        Returns:
            (decision, empresa_destino_id, motivo_cuarentena)
        """
        cuerpo = email_data.get("cuerpo_texto", "") or ""
        remitente_original = extraer_remitente_reenviado(cuerpo)

        if not remitente_original:
            logger.warning(
                "Reenvío de asesor detectado pero no se pudo extraer remitente original "
                "(uid=%s) — marcando REVISION",
                email_data.get("uid"),
            )
            return "CUARENTENA", empresa_id_cuenta, "REENVIO_SIN_REMITENTE"

        empresas_ids = [
            e.id if hasattr(e, "id") else e.get("id")
            for e in empresas_gestoria
            if (e.id if hasattr(e, "id") else e.get("id")) is not None
        ]
        empresa_destino = resolver_empresa_reenvio(remitente_original, empresas_ids, sesion)

        if empresa_destino:
            logger.info(
                "Reenvío detectado: remitente original '%s' → empresa_id=%d",
                remitente_original, empresa_destino,
            )
            return "AUTO", empresa_destino, None
        else:
            logger.warning(
                "Reenvío de asesor: remitente original '%s' no encontrado o ambiguo — REVISION",
                remitente_original,
            )
            return "REVISION", empresa_id_cuenta, None

    def _ejecutar_enriquecimiento(self, email_data: dict, archivos: list) -> dict:
        """G7: ejecuta ExtractorEnriquecimiento sobre el cuerpo del email."""
        try:
            from sfce.conectores.correo.extractor_enriquecimiento import (
                ExtractorEnriquecimiento,
                _CAMPOS_MAPEABLES,
                UMBRAL_AUTO,
                UMBRAL_REVISION,
            )
            extractor_enr = ExtractorEnriquecimiento()
            instrucciones_enr = extractor_enr.extraer(
                cuerpo_texto=email_data.get("cuerpo_texto", "") or "",
                nombres_adjuntos=[a.nombre for a in archivos],
                empresas_gestoria=[],
                fuente="email_ingesta",
            )
            return {i.adjunto: i for i in instrucciones_enr}
        except Exception as e_enr:
            logger.warning("Enriquecimiento no disponible: %s", e_enr)
            return {}

    @staticmethod
    def _aplicar_instruccion_enriquecimiento(instruccion) -> dict:
        """Construye hints_extra desde una instrucción de enriquecimiento."""
        if not instruccion:
            return {}
        try:
            from sfce.conectores.correo.extractor_enriquecimiento import (
                _CAMPOS_MAPEABLES, UMBRAL_AUTO, UMBRAL_REVISION,
            )
        except ImportError:
            return {}
        enr_aplicado: dict = {}
        campos_pendientes: list = []
        for campo in _CAMPOS_MAPEABLES:
            c = getattr(instruccion, campo, None)
            if c is None:
                continue
            if c.confianza >= UMBRAL_AUTO:
                enr_aplicado[campo] = c.valor
            elif c.confianza >= UMBRAL_REVISION:
                campos_pendientes.append(campo)
        if instruccion.urgente:
            enr_aplicado["urgente"] = True
        if instruccion.fuente:
            enr_aplicado["fuente"] = instruccion.fuente
        if campos_pendientes:
            enr_aplicado["campos_pendientes"] = campos_pendientes
        return enr_aplicado

    def _descargar_emails_cuenta(self, cuenta_id: int, ultimo_uid: int) -> list[dict]:
        """Descarga emails nuevos usando el protocolo configurado en la cuenta."""
        with Session(self._engine) as sesion:
            cuenta = sesion.get(CuentaCorreo, cuenta_id)
            if not cuenta:
                return []
            if cuenta.protocolo == "imap":
                from sfce.conectores.correo.imap_servicio import ImapServicio
                from sfce.core.cifrado import descifrar
                contrasena = descifrar(cuenta.contrasena_enc) if cuenta.contrasena_enc else ""
                svc = ImapServicio(
                    servidor=cuenta.servidor,
                    puerto=cuenta.puerto,
                    ssl=bool(cuenta.ssl),
                    usuario=cuenta.usuario,
                    contrasena=contrasena,
                    carpeta=cuenta.carpeta_entrada,
                )
                return svc.descargar_nuevos(ultimo_uid)
        return []

    def _cargar_reglas_gestoria(
        self, sesion: Session, gestoria_id: int
    ) -> tuple[list[dict], list[dict]]:
        """Carga reglas de todas las empresas de la gestoría + globales."""
        empresas_ids = sesion.execute(
            select(Empresa.id).where(Empresa.gestoria_id == gestoria_id)
        ).scalars().all()

        reglas_orm = sesion.execute(
            select(ReglaClasificacionCorreo).where(
                ReglaClasificacionCorreo.activa == True,  # noqa: E712
                ReglaClasificacionCorreo.empresa_id.in_(empresas_ids)
                | ReglaClasificacionCorreo.empresa_id.is_(None),
            ).order_by(ReglaClasificacionCorreo.prioridad)
        ).scalars().all()

        empresas_orm = sesion.execute(
            select(Empresa).where(Empresa.id.in_(empresas_ids))
        ).scalars().all()

        empresas = [{"id": e.id, "nombre": e.nombre} for e in empresas_orm]
        return [self._regla_a_dict(r) for r in reglas_orm], empresas

    def _resolver_empresa_por_slug(
        self, slug: str, empresas: list[dict]
    ) -> int | None:
        """Busca empresa_id por slug (slug = nombre normalizado, primeros 20 chars)."""
        import re
        for emp in empresas:
            nombre_slug = re.sub(r"[^a-z0-9]", "", emp["nombre"].lower())[:20]
            if nombre_slug == slug:
                return emp["id"]
        return None

    @staticmethod
    def _regla_a_dict(r: ReglaClasificacionCorreo) -> dict:
        return {
            "tipo": r.tipo,
            "condicion_json": r.condicion_json,
            "accion": r.accion,
            "slug_destino": r.slug_destino,
            "prioridad": r.prioridad,
            "activa": r.activa,
        }

    def _cargar_reglas(self, sesion: Session, empresa_id: int) -> list[dict]:
        """Carga reglas activas de la empresa + reglas globales (empresa_id=None)."""
        reglas = sesion.execute(
            select(ReglaClasificacionCorreo).where(
                ReglaClasificacionCorreo.activa == True,  # noqa: E712
                (ReglaClasificacionCorreo.empresa_id == empresa_id)
                | ReglaClasificacionCorreo.empresa_id.is_(None),
            ).order_by(ReglaClasificacionCorreo.prioridad)
        ).scalars().all()
        return [
            {
                "tipo": r.tipo,
                "condicion_json": r.condicion_json,
                "accion": r.accion,
                "slug_destino": r.slug_destino,
                "prioridad": r.prioridad,
                "activa": r.activa,
            }
            for r in reglas
        ]


def _detectar_ambiguedad_remitente(
    remitente: str, empresas_gestoria: list, sesion: Session
) -> list:
    """Retorna lista de empresa_ids donde el remitente está en whitelist.

    Deprecated internamente: usar _detectar_ambiguedad_remitente_bulk para evitar N+1.
    Mantenida para compatibilidad con código externo.
    """
    try:
        from sfce.conectores.correo.whitelist_remitentes import verificar_whitelist
        coincidencias = []
        for empresa in empresas_gestoria:
            eid = empresa.id if hasattr(empresa, "id") else empresa.get("id")
            if eid and verificar_whitelist(remitente, eid, sesion):
                coincidencias.append(eid)
        return coincidencias
    except Exception:
        return []


def _detectar_ambiguedad_remitente_bulk(
    remitente: str, empresas_ids: list[int], sesion: Session
) -> list[int]:
    """Fix #17 (N+1): detecta ambigüedad en una sola query.

    Retorna lista de empresa_ids donde el remitente está autorizado.
    """
    if not empresas_ids:
        return []
    remitente_lower = remitente.lower().strip()
    dominio = "@" + remitente_lower.split("@")[-1] if "@" in remitente_lower else None

    entradas = sesion.execute(
        select(RemitenteAutorizado).where(
            RemitenteAutorizado.empresa_id.in_(empresas_ids),
            RemitenteAutorizado.activo == True,  # noqa: E712
        )
    ).scalars().all()

    coincidencias: list[int] = []
    for entrada in entradas:
        patron = entrada.email.lower().strip()
        if patron == remitente_lower:
            coincidencias.append(entrada.empresa_id)
        elif patron.startswith("@") and dominio and patron == dominio:
            coincidencias.append(entrada.empresa_id)
    return list(dict.fromkeys(coincidencias))


# ---------------------------------------------------------------------------
# Utilidades routing tipo='asesor'
# ---------------------------------------------------------------------------

_CIF_PATRON = _re.compile(
    r"\b([A-Z]\d{7}[A-Z0-9]|\d{8}[A-Z])\b"
)


def _extraer_cif_pdf(bytes_pdf: bytes) -> str | None:
    """Extrae el primer CIF/NIF encontrado en el texto del PDF (pdfplumber)."""
    try:
        import io
        import pdfplumber
        with pdfplumber.open(io.BytesIO(bytes_pdf)) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text() or ""
                m = _CIF_PATRON.search(texto)
                if m:
                    return m.group(1)
    except Exception:
        logger.debug("_extraer_cif_pdf: no se pudo leer el PDF", exc_info=True)
    return None


def _resolver_empresa_por_cif(
    cif: str, empresas: list[dict]
) -> int | None:
    """Devuelve el id de la empresa cuyo CIF coincide (soporta prefijo ES)."""
    cif_norm = cif.upper().strip()
    # Eliminar prefijo de país si viene como intracomunitario (ej: ES76638663H)
    if len(cif_norm) > 9 and cif_norm[:2].isalpha():
        cif_sin_prefijo = cif_norm[2:]
    else:
        cif_sin_prefijo = cif_norm
    for e in empresas:
        cif_empresa = (e.get("cif") or "").upper().strip()
        if cif_empresa and (cif_empresa == cif_norm or cif_empresa == cif_sin_prefijo):
            return e["id"]
    return None


def ejecutar_polling_todas_las_cuentas(engine: Engine) -> None:
    """Entry point para scheduler: procesa todas las cuentas activas excepto 'sistema'."""

    with Session(engine) as sesion:
        cuentas = sesion.execute(
            select(CuentaCorreo.id).where(
                CuentaCorreo.activa == True,  # noqa: E712
                CuentaCorreo.tipo_cuenta != "sistema",
            )
        ).scalars().all()

    ingesta = IngestaCorreo(engine=engine)
    for cuenta_id in cuentas:
        try:
            ingesta.procesar_cuenta(cuenta_id)
        except Exception as exc:
            logger.error("Error procesando cuenta %d: %s", cuenta_id, exc)
