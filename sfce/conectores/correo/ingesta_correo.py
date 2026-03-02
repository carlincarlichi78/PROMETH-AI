"""Orquestador de ingesta de emails: descarga → clasifica → guarda → encola OCR."""
import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sfce.db.modelos import (
    CuentaCorreo, EmailProcesado, AdjuntoEmail,
    EnlaceEmail, ReglaClasificacionCorreo, ContrasenaZip, Empresa,
)
from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_email
from sfce.conectores.correo.extractor_enlaces import extraer_enlaces
from sfce.conectores.correo.parser_hints import extraer_hints_asunto
from sfce.conectores.correo.filtro_ack import es_respuesta_automatica, tiene_cabecera_ack
from sfce.conectores.correo.score_email import calcular_score_email, decision_por_score
from sfce.conectores.correo.extractor_adjuntos import extraer_adjuntos, ErrorZipBomb, ErrorZipDemasiado
from sfce.conectores.correo.worker_catchall import _encolar_archivo

logger = logging.getLogger(__name__)

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
        with Session(self._engine) as sesion:
            cuenta = sesion.get(CuentaCorreo, cuenta_id)
            if not cuenta or not cuenta.activa:
                return 0
            ultimo_uid = cuenta.ultimo_uid
            empresa_id = cuenta.empresa_id
            tipo = cuenta.tipo_cuenta or "empresa"
            if tipo == "gestoria":
                reglas, empresas_gestoria = self._cargar_reglas_gestoria(
                    sesion, cuenta.gestoria_id
                )
            else:
                reglas = self._cargar_reglas(sesion, empresa_id)
                empresas_gestoria = []

        emails = self._descargar_emails_cuenta(cuenta_id, ultimo_uid)
        if not emails:
            return 0

        procesados = 0
        with Session(self._engine) as sesion:
            for email_data in emails:
                # Evitar duplicados
                ya_existe = sesion.execute(
                    select(EmailProcesado).where(
                        EmailProcesado.cuenta_id == cuenta_id,
                        EmailProcesado.uid_servidor == email_data["uid"],
                    )
                ).scalar_one_or_none()
                if ya_existe:
                    continue

                asunto = email_data.get("asunto", "")
                headers = email_data.get("headers", {})

                # Cuentas gestoría: clasificación por reglas, routing por slug
                if tipo == "gestoria":
                    clasificacion = clasificar_email(
                        remitente=email_data["remitente"],
                        asunto=asunto,
                        cuerpo_texto=email_data.get("cuerpo_texto", ""),
                        reglas=reglas,
                    )
                    accion = clasificacion.get("accion", "CUARENTENA")
                    _ESTADO_POR_ACCION = {
                        "CLASIFICAR": "CLASIFICADO",
                        "APROBAR_MANUAL": "CUARENTENA",
                        "IGNORAR": "IGNORADO",
                        "CUARENTENA": "CUARENTENA",
                    }
                    estado_inicial = _ESTADO_POR_ACCION.get(accion, "CUARENTENA")
                    empresa_destino_id = None
                    if accion == "CLASIFICAR":
                        slug = clasificacion.get("slug_destino")
                        if slug and empresas_gestoria:
                            empresa_destino_id = self._resolver_empresa_por_slug(
                                slug, empresas_gestoria
                            )

                    # G2: detectar ambigüedad — remitente en whitelist de múltiples empresas
                    motivo_cuarentena_gestoria = "SIN_REGLA" if estado_inicial == "CUARENTENA" else None
                    remitente_email = email_data["remitente"]
                    if empresas_gestoria:
                        candidatos_g2 = _detectar_ambiguedad_remitente(
                            remitente_email, empresas_gestoria, sesion
                        )
                        if len(candidatos_g2) > 1:
                            logger.warning(
                                "G2: remitente '%s' en %d empresas — cuarentena por ambiguedad",
                                remitente_email,
                                len(candidatos_g2),
                            )
                            accion = "CUARENTENA"
                            estado_inicial = "CUARENTENA"
                            empresa_destino_id = None
                            motivo_cuarentena_gestoria = "AMBIGUEDAD_REMITENTE"

                    # G13: extraer tipo_doc del asunto también en cuentas gestoría
                    hints_gestoria = extraer_hints_asunto(asunto)
                    if hints_gestoria.tipo_doc and clasificacion.get("tipo_doc") is None:
                        clasificacion["tipo_doc"] = hints_gestoria.tipo_doc

                    email_bd = EmailProcesado(
                        cuenta_id=cuenta_id,
                        uid_servidor=email_data["uid"],
                        message_id=email_data.get("message_id"),
                        remitente=email_data["remitente"],
                        asunto=asunto,
                        fecha_email=email_data.get("fecha"),
                        estado=estado_inicial,
                        nivel_clasificacion=clasificacion["nivel"],
                        empresa_destino_id=empresa_destino_id,
                        confianza_ia=clasificacion.get("confianza"),
                        es_respuesta_ack=False,
                        score_confianza=None,
                        motivo_cuarentena=motivo_cuarentena_gestoria,
                    )
                else:
                    # 1. Filtro anti-loop ACK
                    es_ack = es_respuesta_automatica(asunto) or tiene_cabecera_ack(headers)

                    # 2. Score multi-señal
                    if es_ack:
                        score, _factores = 0.0, {}
                        decision = "IGNORAR"
                    else:
                        score, _factores = calcular_score_email(email_data, empresa_id, sesion)
                        decision = decision_por_score(score)

                    # 3. Clasificación por reglas (para hints y nivel)
                    hints = extraer_hints_asunto(asunto)
                    clasificacion = clasificar_email(
                        remitente=email_data["remitente"],
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

                    email_bd = EmailProcesado(
                        cuenta_id=cuenta_id,
                        uid_servidor=email_data["uid"],
                        message_id=email_data.get("message_id"),
                        remitente=email_data["remitente"],
                        asunto=asunto,
                        fecha_email=email_data.get("fecha"),
                        estado=estado_inicial,
                        nivel_clasificacion=clasificacion["nivel"],
                        empresa_destino_id=None,
                        confianza_ia=clasificacion.get("confianza"),
                        es_respuesta_ack=es_ack,
                        score_confianza=score,
                        motivo_cuarentena=None if decision != "CUARENTENA" else "SCORE_BAJO",
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

                # 4. Encolar adjuntos en pipeline (solo cuentas no-gestoria)
                if tipo == "gestoria":
                    decision = None  # no se usa en el bloque de encola
                if tipo != "gestoria" and decision in ("AUTO", "REVISION"):
                    try:
                        contrasenas = _cargar_contrasenas_zip(
                            sesion, empresa_id,
                            email_data.get("remitente", ""),
                        )
                        archivos = extraer_adjuntos(
                            email_data.get("adjuntos", []),
                            contrasenas_zip=contrasenas,
                        )

                        # G7: ejecutar ExtractorEnriquecimiento sobre el cuerpo del email
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
                            instrucciones_map = {i.adjunto: i for i in instrucciones_enr}
                        except Exception as e_enr:
                            instrucciones_map = {}
                            logger.debug("Enriquecimiento no disponible: %s", e_enr)

                        for archivo in archivos:
                            # Construir hints_extra desde instrucción de enriquecimiento
                            instruccion = instrucciones_map.get(archivo.nombre)
                            enr_aplicado: dict = {}
                            campos_pendientes: list = []
                            if instruccion:
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

                            _encolar_archivo(
                                archivo, empresa_id, email_bd.id,
                                email_data, directorio=self._dir_adjuntos,
                                sesion=sesion,
                                hints_extra=enr_aplicado or None,
                            )
                    except (ErrorZipBomb, ErrorZipDemasiado) as exc:
                        email_bd.motivo_cuarentena = type(exc).__name__
                        email_bd.estado = "CUARENTENA"

                procesados += 1

            # Actualizar ultimo_uid
            cuenta_obj = sesion.get(CuentaCorreo, cuenta_id)
            if emails and cuenta_obj:
                max_uid = max(
                    int(e["uid"]) for e in emails if str(e["uid"]).isdigit()
                )
                if max_uid > (cuenta_obj.ultimo_uid or 0):
                    cuenta_obj.ultimo_uid = max_uid

            sesion.commit()

        logger.info("Cuenta %d: %d emails nuevos procesados", cuenta_id, procesados)
        return procesados

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
        """Carga reglas de todas las empresas de la gestoría + globales.

        Returns:
            (reglas, empresas) donde empresas es [{id, nombre}]
        """
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

    - Lista vacía → sin restricción (ninguna empresa lo tiene configurado).
    - 1 elemento → destino único, sin ambigüedad.
    - >1 elemento → ambigüedad: remitente autorizado en múltiples empresas.
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
