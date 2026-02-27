"""SFCE DB — Repositorio de queries."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, and_, select, extract
from sqlalchemy.orm import Session, joinedload

from sfce.db.modelos import (
    DirectorioEntidad, Empresa, ProveedorCliente, Trabajador, Documento,
    Asiento, Partida, Factura, Pago, MovimientoBancario, ActivoFijo,
    OperacionPeriodica, Cuarentena, AuditLog, AprendizajeLog,
    ModeloFiscalGenerado,
)


class Repositorio:
    """Capa de acceso a datos con queries especializadas."""

    def __init__(self, sesion_factory):
        self._sesion_factory = sesion_factory

    def _sesion(self) -> Session:
        return self._sesion_factory()

    # --- CRUD generico ---

    def crear(self, entidad):
        """Inserta una entidad y retorna con id asignado."""
        with self._sesion() as s:
            s.add(entidad)
            s.commit()
            s.refresh(entidad)
            return entidad

    def obtener(self, modelo, id_: int):
        """Obtiene entidad por id."""
        with self._sesion() as s:
            return s.get(modelo, id_)

    def actualizar(self, entidad):
        """Actualiza entidad existente."""
        with self._sesion() as s:
            merged = s.merge(entidad)
            s.commit()
            return merged

    def eliminar(self, modelo, id_: int):
        """Elimina entidad por id."""
        with self._sesion() as s:
            obj = s.get(modelo, id_)
            if obj:
                s.delete(obj)
                s.commit()
                return True
            return False

    # --- Empresas ---

    def listar_empresas(self, solo_activas: bool = True) -> list[Empresa]:
        with self._sesion() as s:
            q = select(Empresa)
            if solo_activas:
                q = q.where(Empresa.activa == True)
            return list(s.scalars(q).all())

    def buscar_empresa_por_cif(self, cif: str) -> Empresa | None:
        with self._sesion() as s:
            return s.scalar(select(Empresa).where(Empresa.cif == cif))

    # --- Proveedores/Clientes ---

    def buscar_proveedor_por_cif(self, empresa_id: int, cif: str) -> ProveedorCliente | None:
        with self._sesion() as s:
            return s.scalar(
                select(ProveedorCliente).where(
                    ProveedorCliente.empresa_id == empresa_id,
                    ProveedorCliente.cif == cif,
                    ProveedorCliente.tipo == "proveedor",
                )
            )

    def listar_proveedores(self, empresa_id: int) -> list[ProveedorCliente]:
        with self._sesion() as s:
            return list(s.scalars(
                select(ProveedorCliente).where(
                    ProveedorCliente.empresa_id == empresa_id,
                    ProveedorCliente.tipo == "proveedor",
                    ProveedorCliente.activo == True,
                )
            ).all())

    # --- Documentos ---

    def buscar_documento_por_hash(self, empresa_id: int, hash_pdf: str) -> Documento | None:
        with self._sesion() as s:
            return s.scalar(
                select(Documento).where(
                    Documento.empresa_id == empresa_id,
                    Documento.hash_pdf == hash_pdf,
                )
            )

    def listar_documentos(self, empresa_id: int, estado: str | None = None,
                           tipo_doc: str | None = None) -> list[Documento]:
        with self._sesion() as s:
            q = select(Documento).where(Documento.empresa_id == empresa_id)
            if estado:
                q = q.where(Documento.estado == estado)
            if tipo_doc:
                q = q.where(Documento.tipo_doc == tipo_doc)
            return list(s.scalars(q.order_by(Documento.fecha_proceso.desc())).all())

    def documentos_cuarentena(self, empresa_id: int) -> list[Cuarentena]:
        """Documentos pendientes en cuarentena."""
        with self._sesion() as s:
            return list(s.scalars(
                select(Cuarentena).where(
                    Cuarentena.empresa_id == empresa_id,
                    Cuarentena.resuelta == False,
                ).order_by(Cuarentena.fecha_creacion)
            ).all())

    # --- Contabilidad ---

    def saldo_subcuenta(self, empresa_id: int, subcuenta: str,
                         hasta_fecha: date | None = None) -> Decimal:
        """Calcula saldo de una subcuenta (debe - haber)."""
        with self._sesion() as s:
            q = (
                select(
                    func.coalesce(func.sum(Partida.debe), 0) -
                    func.coalesce(func.sum(Partida.haber), 0)
                )
                .join(Asiento, Partida.asiento_id == Asiento.id)
                .where(
                    Asiento.empresa_id == empresa_id,
                    Partida.subcuenta == subcuenta,
                )
            )
            if hasta_fecha:
                q = q.where(Asiento.fecha <= hasta_fecha)
            resultado = s.scalar(q)
            return Decimal(str(resultado)) if resultado else Decimal("0")

    def pyg(self, empresa_id: int, ejercicio: str | None = None,
            hasta_fecha: date | None = None) -> dict:
        """Cuenta de Perdidas y Ganancias: ingresos (7xx) - gastos (6xx)."""
        with self._sesion() as s:
            gastos = Decimal("0")
            ingresos = Decimal("0")

            q_base = (
                select(Partida.subcuenta,
                       func.sum(Partida.debe).label("total_debe"),
                       func.sum(Partida.haber).label("total_haber"))
                .join(Asiento, Partida.asiento_id == Asiento.id)
                .where(Asiento.empresa_id == empresa_id)
            )
            if ejercicio:
                q_base = q_base.where(Asiento.ejercicio == ejercicio)
            if hasta_fecha:
                q_base = q_base.where(Asiento.fecha <= hasta_fecha)

            q_base = q_base.group_by(Partida.subcuenta)
            rows = s.execute(q_base).all()

            detalle_gastos = {}
            detalle_ingresos = {}

            for subcuenta, total_debe, total_haber in rows:
                total_debe = Decimal(str(total_debe or 0))
                total_haber = Decimal(str(total_haber or 0))
                saldo = total_debe - total_haber

                if subcuenta.startswith("6"):
                    gastos += saldo
                    detalle_gastos[subcuenta] = float(saldo)
                elif subcuenta.startswith("7"):
                    ingresos += abs(saldo)  # 7xx normalmente en haber
                    detalle_ingresos[subcuenta] = float(abs(saldo))

            resultado = ingresos - gastos

            return {
                "ingresos": float(ingresos),
                "gastos": float(gastos),
                "resultado": float(resultado),
                "detalle_ingresos": detalle_ingresos,
                "detalle_gastos": detalle_gastos,
            }

    def balance(self, empresa_id: int, hasta_fecha: date | None = None) -> dict:
        """Balance de situacion simplificado."""
        with self._sesion() as s:
            q = (
                select(Partida.subcuenta,
                       func.sum(Partida.debe).label("total_debe"),
                       func.sum(Partida.haber).label("total_haber"))
                .join(Asiento, Partida.asiento_id == Asiento.id)
                .where(Asiento.empresa_id == empresa_id)
            )
            if hasta_fecha:
                q = q.where(Asiento.fecha <= hasta_fecha)

            q = q.group_by(Partida.subcuenta)
            rows = s.execute(q).all()

            activo = Decimal("0")
            pasivo = Decimal("0")
            patrimonio = Decimal("0")

            for subcuenta, total_debe, total_haber in rows:
                saldo = Decimal(str(total_debe or 0)) - Decimal(str(total_haber or 0))
                grupo = int(subcuenta[0]) if subcuenta and subcuenta[0].isdigit() else 0

                if grupo in (1, 2):  # inmovilizado / inversiones
                    activo += saldo
                elif grupo == 3:  # existencias
                    activo += saldo
                elif grupo == 4:  # deudores/acreedores
                    if saldo > 0:
                        activo += saldo
                    else:
                        pasivo += abs(saldo)
                elif grupo == 5:  # cuentas financieras
                    if saldo > 0:
                        activo += saldo
                    else:
                        pasivo += abs(saldo)

            patrimonio = activo - pasivo

            return {
                "activo": float(activo),
                "pasivo": float(pasivo),
                "patrimonio_neto": float(patrimonio),
            }

    def facturas_pendientes_pago(self, empresa_id: int) -> list[Factura]:
        """Facturas no pagadas."""
        with self._sesion() as s:
            return list(s.scalars(
                select(Factura).where(
                    Factura.empresa_id == empresa_id,
                    Factura.pagada == False,
                ).order_by(Factura.fecha_factura)
            ).all())

    # --- Activos fijos ---

    def activos_pendientes_amortizacion(self, empresa_id: int) -> list[ActivoFijo]:
        """Activos activos con amortizacion pendiente."""
        with self._sesion() as s:
            return list(s.scalars(
                select(ActivoFijo).where(
                    ActivoFijo.empresa_id == empresa_id,
                    ActivoFijo.activo == True,
                    ActivoFijo.amortizacion_acumulada < (
                        ActivoFijo.valor_adquisicion - ActivoFijo.valor_residual
                    ),
                )
            ).all())

    # --- Operaciones periodicas ---

    def operaciones_pendientes(self, empresa_id: int,
                                fecha_referencia: date | None = None) -> list[OperacionPeriodica]:
        """Operaciones periodicas que deben ejecutarse."""
        fecha_ref = fecha_referencia or date.today()
        with self._sesion() as s:
            return list(s.scalars(
                select(OperacionPeriodica).where(
                    OperacionPeriodica.empresa_id == empresa_id,
                    OperacionPeriodica.activa == True,
                )
            ).all())

    # --- Audit log ---

    def registrar_auditoria(self, empresa_id: int | None, accion: str,
                             entidad_tipo: str | None = None,
                             entidad_id: int | None = None,
                             datos_antes: dict | None = None,
                             datos_despues: dict | None = None,
                             detalle: str | None = None):
        """Registra entrada en audit log."""
        log = AuditLog(
            empresa_id=empresa_id,
            accion=accion,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            datos_antes=datos_antes,
            datos_despues=datos_despues,
            detalle=detalle,
        )
        with self._sesion() as s:
            s.add(log)
            s.commit()

    # --- Aprendizaje ---

    def buscar_patron(self, patron_tipo: str, clave: str) -> AprendizajeLog | None:
        with self._sesion() as s:
            return s.scalar(
                select(AprendizajeLog).where(
                    AprendizajeLog.patron_tipo == patron_tipo,
                    AprendizajeLog.clave == clave,
                )
            )

    def registrar_aprendizaje(self, empresa_id: int | None, patron_tipo: str,
                                clave: str, valor: str, confianza: int = 85):
        """Registra o actualiza patron aprendido."""
        with self._sesion() as s:
            existente = s.scalar(
                select(AprendizajeLog).where(
                    AprendizajeLog.patron_tipo == patron_tipo,
                    AprendizajeLog.clave == clave,
                )
            )
            if existente:
                existente.valor = valor
                existente.confianza = confianza
                existente.usos += 1
                existente.fecha_ultimo_uso = datetime.now()
            else:
                s.add(AprendizajeLog(
                    empresa_id=empresa_id,
                    patron_tipo=patron_tipo,
                    clave=clave,
                    valor=valor,
                    confianza=confianza,
                ))
            s.commit()

    # --- Queries fiscales ---

    @staticmethod
    def _rango_fechas_periodo(ejercicio: str, periodo: str) -> tuple[date, date]:
        """Convierte ejercicio+periodo en fechas inicio/fin.

        Periodos: "1T"=ene-mar, "2T"=abr-jun, "3T"=jul-sep, "4T"=oct-dic, "0A"=anual.
        """
        ano = int(ejercicio)
        rangos = {
            "1T": (date(ano, 1, 1), date(ano, 3, 31)),
            "2T": (date(ano, 4, 1), date(ano, 6, 30)),
            "3T": (date(ano, 7, 1), date(ano, 9, 30)),
            "4T": (date(ano, 10, 1), date(ano, 12, 31)),
            "0A": (date(ano, 1, 1), date(ano, 12, 31)),
        }
        return rangos.get(periodo, (date(ano, 1, 1), date(ano, 12, 31)))

    def iva_por_periodo(self, empresa_id: int, ejercicio: str, periodo: str) -> dict:
        """IVA repercutido/soportado agrupado por tipo para un periodo.

        Consulta partidas de subcuentas 477 (IVA repercutido) y 472 (IVA soportado)
        filtradas por empresa y periodo (trimestre o anual).

        Returns:
            {
                "repercutido": {"general": {"base": 0.0, "cuota": 0.0},
                               "reducido": {...}, "superreducido": {...}},
                "soportado": {"general": {"base": 0.0, "cuota": 0.0}, ...},
                "total_repercutido": 0.0,
                "total_soportado": 0.0,
                "periodo": periodo,
                "ejercicio": ejercicio
            }
        """
        estructura_tipos = {
            "general": {"base": 0.0, "cuota": 0.0},
            "reducido": {"base": 0.0, "cuota": 0.0},
            "superreducido": {"base": 0.0, "cuota": 0.0},
        }
        resultado = {
            "repercutido": {k: dict(v) for k, v in estructura_tipos.items()},
            "soportado": {k: dict(v) for k, v in estructura_tipos.items()},
            "total_repercutido": 0.0,
            "total_soportado": 0.0,
            "periodo": periodo,
            "ejercicio": ejercicio,
        }
        try:
            fecha_ini, fecha_fin = self._rango_fechas_periodo(ejercicio, periodo)
            with self._sesion() as s:
                # Partidas de IVA (477=repercutido haber, 472=soportado debe)
                rows = s.execute(
                    select(
                        Partida.subcuenta,
                        Partida.codimpuesto,
                        func.sum(Partida.debe).label("total_debe"),
                        func.sum(Partida.haber).label("total_haber"),
                    )
                    .join(Asiento, Partida.asiento_id == Asiento.id)
                    .where(
                        Asiento.empresa_id == empresa_id,
                        Asiento.ejercicio == ejercicio,
                        Asiento.fecha >= fecha_ini,
                        Asiento.fecha <= fecha_fin,
                        Partida.subcuenta.in_(["477", "472"]),
                    )
                    .group_by(Partida.subcuenta, Partida.codimpuesto)
                ).all()

                # Mapa codimpuesto -> tipo IVA
                _tipo_iva = {
                    "IVA21": "general", "IVA21RE": "general",
                    "IVA10": "reducido", "IVA10RE": "reducido",
                    "IVA4": "superreducido", "IVA4RE": "superreducido",
                    None: "general",
                }

                for subcuenta, codimpuesto, total_debe, total_haber in rows:
                    tipo = _tipo_iva.get(codimpuesto, "general")
                    cuota = float(Decimal(str(total_haber or 0)) - Decimal(str(total_debe or 0)))
                    cuota = abs(cuota)
                    if subcuenta == "477":
                        resultado["repercutido"][tipo]["cuota"] += cuota
                        resultado["total_repercutido"] += cuota
                    elif subcuenta == "472":
                        resultado["soportado"][tipo]["cuota"] += cuota
                        resultado["total_soportado"] += cuota

                # Bases: buscar en partidas de cuentas 6xx/7xx del mismo asiento
                # Simplificado: consultar facturas registradas en el periodo
                facturas = s.execute(
                    select(
                        Factura.tipo,
                        Factura.base_imponible,
                        Factura.iva_importe,
                    )
                    .join(Documento, Factura.documento_id == Documento.id)
                    .where(
                        Factura.empresa_id == empresa_id,
                        Documento.ejercicio == ejercicio,
                        Factura.fecha_factura >= fecha_ini,
                        Factura.fecha_factura <= fecha_fin,
                    )
                ).all()

                for tipo_fac, base, iva in facturas:
                    base_f = float(base or 0)
                    iva_f = float(iva or 0)
                    # Determinar tipo IVA por porcentaje aproximado
                    tipo_iva = "general"
                    if base_f > 0 and iva_f > 0:
                        pct = (iva_f / base_f) * 100
                        if pct <= 4.5:
                            tipo_iva = "superreducido"
                        elif pct <= 11:
                            tipo_iva = "reducido"
                    if tipo_fac == "emitida":
                        resultado["repercutido"][tipo_iva]["base"] += base_f
                    else:
                        resultado["soportado"][tipo_iva]["base"] += base_f

        except Exception:
            pass  # devolver estructura vacia por defecto

        return resultado

    def retenciones_por_periodo(self, empresa_id: int, ejercicio: str, periodo: str) -> dict:
        """Retenciones IRPF practicadas por tipo en el periodo.

        Consulta partidas de subcuentas 4751 (HP acreedora retenciones).

        Returns:
            {
                "trabajo": 0.0,
                "profesionales": 0.0,
                "alquileres": 0.0,
                "capital": 0.0,
                "total": 0.0,
                "periodo": periodo,
                "ejercicio": ejercicio
            }
        """
        resultado = {
            "trabajo": 0.0,
            "profesionales": 0.0,
            "alquileres": 0.0,
            "capital": 0.0,
            "total": 0.0,
            "periodo": periodo,
            "ejercicio": ejercicio,
        }
        try:
            fecha_ini, fecha_fin = self._rango_fechas_periodo(ejercicio, periodo)
            with self._sesion() as s:
                # Partidas de 4751 (retenciones IRPF acreedoras — saldo en haber)
                rows_4751 = s.execute(
                    select(
                        func.sum(Partida.debe).label("total_debe"),
                        func.sum(Partida.haber).label("total_haber"),
                    )
                    .join(Asiento, Partida.asiento_id == Asiento.id)
                    .where(
                        Asiento.empresa_id == empresa_id,
                        Asiento.ejercicio == ejercicio,
                        Asiento.fecha >= fecha_ini,
                        Asiento.fecha <= fecha_fin,
                        Partida.subcuenta.like("4751%"),
                    )
                ).first()

                total_4751 = 0.0
                if rows_4751:
                    haber = float(rows_4751.total_haber or 0)
                    debe = float(rows_4751.total_debe or 0)
                    total_4751 = abs(haber - debe)

                # Retenciones de facturas registradas
                facturas = s.execute(
                    select(
                        Factura.tipo,
                        Factura.irpf_importe,
                        Documento.tipo_doc,
                    )
                    .join(Documento, Factura.documento_id == Documento.id)
                    .where(
                        Factura.empresa_id == empresa_id,
                        Documento.ejercicio == ejercicio,
                        Factura.fecha_factura >= fecha_ini,
                        Factura.fecha_factura <= fecha_fin,
                        Factura.irpf_importe.isnot(None),
                        Factura.irpf_importe != 0,
                    )
                ).all()

                for tipo_fac, irpf, tipo_doc in facturas:
                    irpf_f = float(irpf or 0)
                    if tipo_doc == "NOM":
                        resultado["trabajo"] += irpf_f
                    elif tipo_doc in ("FV", "FC"):
                        resultado["profesionales"] += irpf_f
                    else:
                        resultado["profesionales"] += irpf_f

                # Si no hay facturas con IRPF desglosado, usar total de 4751
                total_facturas = sum(
                    resultado[k] for k in ("trabajo", "profesionales", "alquileres", "capital")
                )
                if total_facturas == 0 and total_4751 > 0:
                    resultado["profesionales"] = total_4751

                resultado["total"] = sum(
                    resultado[k] for k in ("trabajo", "profesionales", "alquileres", "capital")
                )

        except Exception:
            pass

        return resultado

    def operaciones_terceros(self, empresa_id: int, ejercicio: str) -> list[dict]:
        """Operaciones con terceros >3.005,06 EUR para modelo 347.

        Agrupa facturas por CIF de proveedor/cliente, suma importes anuales.

        Returns:
            [{"cif": str, "nombre": str, "importe_total": float,
              "importe_1T": float, "importe_2T": float,
              "importe_3T": float, "importe_4T": float,
              "tipo": "B"|"A"}]  # B=entregas, A=adquisiciones
        """
        UMBRAL_347 = 3005.06
        try:
            ano = int(ejercicio)
            with self._sesion() as s:
                rows = s.execute(
                    select(
                        Factura.cif_emisor,
                        Factura.nombre_emisor,
                        Factura.cif_receptor,
                        Factura.nombre_receptor,
                        Factura.tipo,
                        Factura.total,
                        Factura.fecha_factura,
                    )
                    .join(Documento, Factura.documento_id == Documento.id)
                    .where(
                        Factura.empresa_id == empresa_id,
                        Documento.ejercicio == ejercicio,
                        Factura.fecha_factura >= date(ano, 1, 1),
                        Factura.fecha_factura <= date(ano, 12, 31),
                        Factura.total.isnot(None),
                    )
                ).all()

            # Agregar por CIF y trimestre
            acumulado: dict[str, dict] = {}
            for cif_emisor, nombre_emisor, cif_receptor, nombre_receptor, tipo_fac, total, fecha in rows:
                if tipo_fac == "recibida":
                    cif = cif_emisor or ""
                    nombre = nombre_emisor or ""
                    tipo_347 = "A"  # adquisicion
                else:
                    cif = cif_receptor or ""
                    nombre = nombre_receptor or ""
                    tipo_347 = "B"  # entrega

                if not cif:
                    continue

                if cif not in acumulado:
                    acumulado[cif] = {
                        "cif": cif, "nombre": nombre,
                        "importe_total": 0.0, "importe_1T": 0.0,
                        "importe_2T": 0.0, "importe_3T": 0.0,
                        "importe_4T": 0.0, "tipo": tipo_347,
                    }

                importe = float(total or 0)
                acumulado[cif]["importe_total"] += importe

                if fecha:
                    mes = fecha.month
                    if mes <= 3:
                        acumulado[cif]["importe_1T"] += importe
                    elif mes <= 6:
                        acumulado[cif]["importe_2T"] += importe
                    elif mes <= 9:
                        acumulado[cif]["importe_3T"] += importe
                    else:
                        acumulado[cif]["importe_4T"] += importe

            return [v for v in acumulado.values() if v["importe_total"] >= UMBRAL_347]

        except Exception:
            return []

    def operaciones_intracomunitarias(self, empresa_id: int, ejercicio: str, periodo: str) -> list[dict]:
        """Operaciones intracomunitarias para modelo 349.

        Facturas con proveedores/clientes de paises UE (codpais en ISO EU).

        Returns:
            [{"cif": str, "nombre": str, "pais": str,
              "importe": float, "tipo_operacion": "E"|"A"|"S"|"I"}]
        """
        # Paises UE (ISO 3166-1 alpha-3)
        PAISES_UE = {
            "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN",
            "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA", "LTU", "LUX",
            "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "SWE",
        }
        # Tambien admitir ISO alpha-2
        PAISES_UE_2 = {
            "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI",
            "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU",
            "MT", "NL", "PL", "PT", "RO", "SK", "SI", "SE",
        }
        try:
            fecha_ini, fecha_fin = self._rango_fechas_periodo(ejercicio, periodo)
            with self._sesion() as s:
                rows = s.execute(
                    select(
                        Factura.cif_emisor,
                        Factura.nombre_emisor,
                        Factura.cif_receptor,
                        Factura.nombre_receptor,
                        Factura.tipo,
                        Factura.base_imponible,
                        ProveedorCliente.pais,
                    )
                    .join(Documento, Factura.documento_id == Documento.id)
                    .outerjoin(
                        ProveedorCliente,
                        and_(
                            ProveedorCliente.empresa_id == empresa_id,
                            ProveedorCliente.cif == Factura.cif_emisor,
                        ),
                    )
                    .where(
                        Factura.empresa_id == empresa_id,
                        Documento.ejercicio == ejercicio,
                        Factura.fecha_factura >= fecha_ini,
                        Factura.fecha_factura <= fecha_fin,
                    )
                ).all()

            resultado = []
            for cif_emisor, nombre_emisor, cif_receptor, nombre_receptor, tipo_fac, base, pais in rows:
                if not pais:
                    continue
                pais_upper = (pais or "").upper()
                if pais_upper not in PAISES_UE and pais_upper not in PAISES_UE_2:
                    continue

                if tipo_fac == "recibida":
                    cif = cif_emisor or ""
                    nombre = nombre_emisor or ""
                    tipo_op = "A"  # adquisicion intracomunitaria
                else:
                    cif = cif_receptor or ""
                    nombre = nombre_receptor or ""
                    tipo_op = "E"  # entrega intracomunitaria

                resultado.append({
                    "cif": cif,
                    "nombre": nombre,
                    "pais": pais,
                    "importe": float(base or 0),
                    "tipo_operacion": tipo_op,
                })

            return resultado

        except Exception:
            return []

    def nominas_por_periodo(self, empresa_id: int, ejercicio: str, periodo: str) -> dict:
        """Datos de nominas para modelos 111/190.

        Consulta documentos tipo NOM y partidas de subcuentas 640/641/476.

        Returns:
            {
                "bruto_total": 0.0,
                "ss_empresa": 0.0,
                "irpf_retenido": 0.0,
                "num_perceptores": 0,
                "periodo": periodo
            }
        """
        resultado = {
            "bruto_total": 0.0,
            "ss_empresa": 0.0,
            "irpf_retenido": 0.0,
            "num_perceptores": 0,
            "periodo": periodo,
        }
        try:
            fecha_ini, fecha_fin = self._rango_fechas_periodo(ejercicio, periodo)
            with self._sesion() as s:
                # Documentos de nomina en el periodo
                docs_nom = s.execute(
                    select(Documento.id, Documento.datos_ocr)
                    .where(
                        Documento.empresa_id == empresa_id,
                        Documento.ejercicio == ejercicio,
                        Documento.tipo_doc == "NOM",
                        Documento.estado == "registrado",
                    )
                ).all()

                # Extraer datos OCR de cada nomina
                trabajadores_vistos: set = set()
                for doc_id, datos_ocr in docs_nom:
                    if not datos_ocr:
                        continue
                    fecha_str = datos_ocr.get("fecha", "") or ""
                    if fecha_str:
                        try:
                            parts = fecha_str.split("-")
                            if len(parts) >= 2:
                                mes = int(parts[1])
                                fecha_doc = date(int(parts[0]), mes, 1)
                                if not (fecha_ini <= fecha_doc <= fecha_fin):
                                    continue
                        except (ValueError, IndexError):
                            pass

                    bruto = float(datos_ocr.get("bruto", 0) or 0)
                    ss_emp = float(datos_ocr.get("ss_empresa", 0) or 0)
                    irpf = float(datos_ocr.get("irpf_importe", 0) or datos_ocr.get("retencion", 0) or 0)
                    trabajador = datos_ocr.get("trabajador", "") or datos_ocr.get("nombre_receptor", "")

                    resultado["bruto_total"] += bruto
                    resultado["ss_empresa"] += ss_emp
                    resultado["irpf_retenido"] += irpf
                    if trabajador and trabajador not in trabajadores_vistos:
                        trabajadores_vistos.add(trabajador)

                # Complementar con partidas contables si no hay datos OCR
                if resultado["bruto_total"] == 0:
                    rows_partidas = s.execute(
                        select(
                            Partida.subcuenta,
                            func.sum(Partida.debe).label("total_debe"),
                            func.sum(Partida.haber).label("total_haber"),
                        )
                        .join(Asiento, Partida.asiento_id == Asiento.id)
                        .where(
                            Asiento.empresa_id == empresa_id,
                            Asiento.ejercicio == ejercicio,
                            Asiento.fecha >= fecha_ini,
                            Asiento.fecha <= fecha_fin,
                            Partida.subcuenta.in_(["640", "641", "6400", "6410", "476", "4751"]),
                        )
                        .group_by(Partida.subcuenta)
                    ).all()

                    for subcuenta, total_debe, total_haber in rows_partidas:
                        saldo = float(Decimal(str(total_debe or 0)) - Decimal(str(total_haber or 0)))
                        if subcuenta.startswith("640") or subcuenta.startswith("641"):
                            resultado["bruto_total"] += abs(saldo)
                        elif subcuenta.startswith("476"):
                            resultado["ss_empresa"] += abs(saldo)
                        elif subcuenta.startswith("4751"):
                            resultado["irpf_retenido"] += abs(saldo)

                resultado["num_perceptores"] = max(len(trabajadores_vistos), 0)

        except Exception:
            pass

        return resultado

    def alquileres_por_periodo(self, empresa_id: int, ejercicio: str, periodo: str) -> dict:
        """Datos de alquileres para modelos 115/180.

        Consulta facturas/asientos con subcuenta 621 (arrendamientos).

        Returns:
            {
                "base_alquileres": 0.0,
                "retenciones_alquileres": 0.0,
                "num_arrendadores": 0,
                "periodo": periodo
            }
        """
        resultado = {
            "base_alquileres": 0.0,
            "retenciones_alquileres": 0.0,
            "num_arrendadores": 0,
            "periodo": periodo,
        }
        try:
            fecha_ini, fecha_fin = self._rango_fechas_periodo(ejercicio, periodo)
            with self._sesion() as s:
                # Facturas recibidas con IRPF (candidatas a alquiler)
                facturas_alquiler = s.execute(
                    select(
                        Factura.cif_emisor,
                        Factura.base_imponible,
                        Factura.irpf_importe,
                    )
                    .join(Documento, Factura.documento_id == Documento.id)
                    .where(
                        Factura.empresa_id == empresa_id,
                        Documento.ejercicio == ejercicio,
                        Factura.tipo == "recibida",
                        Factura.fecha_factura >= fecha_ini,
                        Factura.fecha_factura <= fecha_fin,
                        Factura.irpf_importe.isnot(None),
                        Factura.irpf_importe != 0,
                    )
                ).all()

                arrendadores_vistos: set = set()
                for cif, base, irpf in facturas_alquiler:
                    base_f = float(base or 0)
                    irpf_f = float(irpf or 0)
                    resultado["base_alquileres"] += base_f
                    resultado["retenciones_alquileres"] += irpf_f
                    if cif:
                        arrendadores_vistos.add(cif)

                # Complementar con partidas 621 si no hay facturas
                if resultado["base_alquileres"] == 0:
                    rows_621 = s.execute(
                        select(func.sum(Partida.debe).label("total_debe"))
                        .join(Asiento, Partida.asiento_id == Asiento.id)
                        .where(
                            Asiento.empresa_id == empresa_id,
                            Asiento.ejercicio == ejercicio,
                            Asiento.fecha >= fecha_ini,
                            Asiento.fecha <= fecha_fin,
                            Partida.subcuenta.like("621%"),
                        )
                    ).first()
                    if rows_621 and rows_621.total_debe:
                        resultado["base_alquileres"] = float(rows_621.total_debe)

                resultado["num_arrendadores"] = len(arrendadores_vistos)

        except Exception:
            pass

        return resultado

    def rendimientos_capital(self, empresa_id: int, ejercicio: str, periodo: str) -> dict:
        """Datos capital mobiliario para modelos 123/193.

        Consulta asientos subcuentas 760-769 (ingresos financieros) y 473.

        Returns:
            {
                "rendimientos_brutos": 0.0,
                "retenciones_practicadas": 0.0,
                "num_perceptores": 0,
                "periodo": periodo
            }
        """
        resultado = {
            "rendimientos_brutos": 0.0,
            "retenciones_practicadas": 0.0,
            "num_perceptores": 0,
            "periodo": periodo,
        }
        try:
            fecha_ini, fecha_fin = self._rango_fechas_periodo(ejercicio, periodo)
            with self._sesion() as s:
                rows = s.execute(
                    select(
                        Partida.subcuenta,
                        func.sum(Partida.debe).label("total_debe"),
                        func.sum(Partida.haber).label("total_haber"),
                    )
                    .join(Asiento, Partida.asiento_id == Asiento.id)
                    .where(
                        Asiento.empresa_id == empresa_id,
                        Asiento.ejercicio == ejercicio,
                        Asiento.fecha >= fecha_ini,
                        Asiento.fecha <= fecha_fin,
                        Partida.subcuenta.regexp_match(r"^(76[0-9]|473)"),
                    )
                    .group_by(Partida.subcuenta)
                ).all()

                for subcuenta, total_debe, total_haber in rows:
                    debe = float(total_debe or 0)
                    haber = float(total_haber or 0)
                    if subcuenta.startswith("76"):
                        # Ingresos financieros: saldo en haber
                        resultado["rendimientos_brutos"] += abs(haber - debe)
                    elif subcuenta.startswith("473"):
                        # Retenciones soportadas: saldo en debe
                        resultado["retenciones_practicadas"] += abs(debe - haber)

        except Exception:
            pass

        return resultado

    # --- Directorio de entidades ---

    def buscar_directorio_por_cif(self, cif: str) -> DirectorioEntidad | None:
        """Busca entidad en directorio maestro por CIF."""
        with self._sesion() as s:
            return s.scalar(
                select(DirectorioEntidad).where(DirectorioEntidad.cif == cif)
            )

    def buscar_directorio_por_nombre(self, nombre: str) -> DirectorioEntidad | None:
        """Busca entidad por nombre exacto o alias."""
        nombre_upper = nombre.upper()
        with self._sesion() as s:
            # Busqueda exacta por nombre
            resultado = s.scalar(
                select(DirectorioEntidad).where(
                    func.upper(DirectorioEntidad.nombre) == nombre_upper
                )
            )
            if resultado:
                return resultado
            # Busqueda en aliases (JSON array)
            todas = s.scalars(select(DirectorioEntidad)).all()
            for ent in todas:
                if ent.aliases:
                    for alias in ent.aliases:
                        if alias.upper() == nombre_upper or alias.upper() in nombre_upper:
                            return ent
            return None

    def obtener_o_crear_directorio(self, cif: str | None, nombre: str,
                                    pais: str = "ESP", **kwargs) -> tuple:
        """Busca por CIF; si no existe, crea. Returns (entidad, creado: bool)."""
        if cif:
            existente = self.buscar_directorio_por_cif(cif)
            if existente:
                return existente, False
        ent = DirectorioEntidad(cif=cif, nombre=nombre, pais=pais, **kwargs)
        return self.crear(ent), True

    def crear_overlay(self, empresa_id: int, directorio_id: int, tipo: str,
                       subcuenta_gasto: str = "", codimpuesto: str = "IVA21",
                       regimen: str = "general", **kwargs) -> ProveedorCliente:
        """Crea overlay empresa-especifico vinculado a directorio."""
        dir_ent = self.obtener(DirectorioEntidad, directorio_id)
        overlay = ProveedorCliente(
            empresa_id=empresa_id, directorio_id=directorio_id,
            cif=dir_ent.cif or "", nombre=dir_ent.nombre,
            tipo=tipo, subcuenta_gasto=subcuenta_gasto,
            codimpuesto=codimpuesto, regimen=regimen, **kwargs
        )
        return self.crear(overlay)

    def buscar_overlay_por_cif(self, empresa_id: int, cif: str,
                                tipo: str) -> ProveedorCliente | None:
        """Busca overlay por empresa+CIF+tipo con directorio cargado."""
        with self._sesion() as s:
            return s.scalar(
                select(ProveedorCliente).where(
                    ProveedorCliente.empresa_id == empresa_id,
                    ProveedorCliente.cif == cif,
                    ProveedorCliente.tipo == tipo,
                ).options(joinedload(ProveedorCliente.directorio))
            )

    def listar_directorio(self, pais: str | None = None) -> list[DirectorioEntidad]:
        """Lista entidades del directorio maestro, opcionalmente filtradas por pais."""
        with self._sesion() as s:
            q = select(DirectorioEntidad)
            if pais:
                q = q.where(DirectorioEntidad.pais == pais)
            return list(s.scalars(q.order_by(DirectorioEntidad.nombre)).all())

    # --- Modelos Fiscales Generados ---

    def guardar_modelo_generado(
        self,
        empresa_id: int,
        modelo: str,
        ejercicio: str,
        periodo: str,
        casillas: dict,
        ruta_boe: str | None = None,
        ruta_pdf: str | None = None,
        valido: bool = True,
        notas: str | None = None,
    ) -> ModeloFiscalGenerado:
        """Persiste un modelo fiscal generado en BD."""
        import json
        registro = ModeloFiscalGenerado(
            empresa_id=empresa_id,
            modelo=modelo,
            ejercicio=ejercicio,
            periodo=periodo,
            casillas_json=json.dumps(casillas),
            ruta_boe=ruta_boe,
            ruta_pdf=ruta_pdf,
            valido=valido,
            notas=notas,
        )
        return self.crear(registro)

    def listar_modelos_generados(
        self,
        empresa_id: int,
        ejercicio: str | None = None,
        modelo: str | None = None,
    ) -> list[ModeloFiscalGenerado]:
        """Lista modelos fiscales generados para una empresa."""
        with self._sesion() as s:
            q = select(ModeloFiscalGenerado).where(
                ModeloFiscalGenerado.empresa_id == empresa_id
            )
            if ejercicio:
                q = q.where(ModeloFiscalGenerado.ejercicio == ejercicio)
            if modelo:
                q = q.where(ModeloFiscalGenerado.modelo == modelo)
            return list(s.scalars(
                q.order_by(ModeloFiscalGenerado.fecha_generacion.desc())
            ).all())
