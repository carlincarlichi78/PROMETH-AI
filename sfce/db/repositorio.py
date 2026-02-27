"""SFCE DB — Repositorio de queries."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, and_, select
from sqlalchemy.orm import Session

from sfce.db.modelos import (
    Empresa, ProveedorCliente, Trabajador, Documento, Asiento, Partida,
    Factura, Pago, MovimientoBancario, ActivoFijo, OperacionPeriodica,
    Cuarentena, AuditLog, AprendizajeLog,
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
