"""Capa de abstraccion sobre FacturaScripts + BD local.

Todos los modulos del SFCE acceden a datos via Backend, nunca directamente
a fs_api. Doble destino: guarda en BD local Y envia a FS.
Si FS falla, marca como pendiente_sync para reintento.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sfce.core.logger import crear_logger

logger = crear_logger("backend")


class Backend:
    """Interfaz unificada para operaciones contables.

    Modos:
    - "dual": BD local + FS (produccion)
    - "fs": solo FS (legacy)
    - "local": solo BD local (offline/testing)
    """

    def __init__(self, modo: str = "fs", repo=None, empresa_id: int | None = None):
        self.modo = modo
        self.repo = repo
        self.empresa_id = empresa_id

        # Importar fs_api solo si se necesita
        if modo in ("fs", "dual"):
            from .fs_api import api_get, api_post, api_put, api_delete, api_get_one
            self._api_get = api_get
            self._api_post = api_post
            self._api_put = api_put
            self._api_delete = api_delete
            self._api_get_one = api_get_one

    # --- Facturas ---
    def crear_factura(self, endpoint: str, data: dict) -> dict:
        """Crea factura via endpoint crearFactura*."""
        resultado = {}

        if self.modo in ("fs", "dual"):
            resultado = self._api_post(endpoint, data)

        if self.modo in ("local", "dual") and self.repo:
            self._guardar_factura_local(data, resultado)

        return resultado

    def actualizar_factura(self, endpoint: str, data: dict) -> dict:
        """Actualiza factura (ej: marcar pagada)."""
        resultado = data
        if self.modo in ("fs", "dual"):
            resultado = self._api_put(endpoint, data)

        if self.modo in ("local", "dual") and self.repo:
            self._actualizar_factura_local(endpoint, data)

        return resultado

    def obtener_facturas(self, tipo: str = "proveedores", params: dict = None) -> list:
        """Obtiene facturas. tipo: 'proveedores' o 'clientes'."""
        if self.modo in ("fs", "dual"):
            ep = "facturaproveedores" if tipo == "proveedores" else "facturaclientes"
            return self._api_get(ep, params or {})
        if self.repo and self.empresa_id:
            from sfce.db.modelos import Factura
            tipo_db = "recibida" if tipo == "proveedores" else "emitida"
            return self.repo.listar_documentos(self.empresa_id, tipo_doc="FC")
        return []

    # --- Asientos ---
    def crear_asiento(self, data: dict, solo_local: bool = False) -> dict:
        """Crea asiento contable. Retorna dict con datos FS + _asiento_local_id.

        Args:
            data: datos del asiento
            solo_local: si True, solo guarda en BD local (para sync de asientos
                        que ya existen en FS, ej: generados por crearFactura*)
        """
        resultado = {}

        if not solo_local and self.modo in ("fs", "dual"):
            try:
                resultado = self._api_post("asientos", data)
            except Exception as e:
                if self.modo == "dual":
                    logger.warning(f"FS fallo al crear asiento, guardando solo local: {e}")
                    resultado = {"_pendiente_sync": True, "_error_fs": str(e)}
                else:
                    raise

        if self.repo and self.empresa_id:
            asiento_local_id = self._guardar_asiento_local(data, resultado)
            resultado["_asiento_local_id"] = asiento_local_id

        return resultado

    def obtener_asientos(self, params: dict = None) -> list:
        """Obtiene asientos con filtros."""
        if self.modo in ("fs", "dual"):
            return self._api_get("asientos", params or {})
        return []

    # --- Partidas ---
    def crear_partida(self, data: dict, asiento_local_id: int | None = None,
                      solo_local: bool = False) -> dict:
        """Crea partida (linea de asiento).

        Args:
            data: datos de la partida
            asiento_local_id: FK al asiento en BD local
            solo_local: si True, solo guarda en BD local (para sync)
        """
        resultado = data
        if not solo_local and self.modo in ("fs", "dual"):
            resultado = self._api_post("partidas", data)

        if self.repo and asiento_local_id:
            self._guardar_partida_local(data, resultado, asiento_local_id)

        return resultado

    def actualizar_partida(self, idpartida: int, data: dict) -> dict:
        """Actualiza partida existente."""
        resultado = data
        if self.modo in ("fs", "dual"):
            resultado = self._api_put(f"partidas/{idpartida}", data)

        if self.modo in ("local", "dual") and self.repo:
            self._actualizar_partida_local(idpartida, data)

        return resultado

    def obtener_partidas(self, params: dict = None) -> list:
        """Obtiene partidas con filtros."""
        if self.modo in ("fs", "dual"):
            return self._api_get("partidas", params or {})
        return []

    # --- Subcuentas ---
    def obtener_subcuentas(self, params: dict = None) -> list:
        """Obtiene subcuentas contables."""
        if self.modo in ("fs", "dual"):
            return self._api_get("subcuentas", params or {})
        return []

    # --- Entidades ---
    def crear_proveedor(self, data: dict) -> dict:
        """Crea proveedor."""
        resultado = {}
        if self.modo in ("fs", "dual"):
            resultado = self._api_post("proveedores", data)
        if self.modo in ("local", "dual") and self.repo and self.empresa_id:
            self._guardar_proveedor_local(data)
        return resultado

    def crear_cliente(self, data: dict) -> dict:
        """Crea cliente."""
        resultado = {}
        if self.modo in ("fs", "dual"):
            resultado = self._api_post("clientes", data)
        if self.modo in ("local", "dual") and self.repo and self.empresa_id:
            self._guardar_cliente_local(data)
        return resultado

    # --- Saldos ---
    def obtener_saldo(self, codsubcuenta: str, params: dict = None) -> dict | None:
        """Obtiene saldo de una subcuenta."""
        if self.modo in ("fs", "dual"):
            return self._api_get_one(f"subcuentas/{codsubcuenta}")
        if self.repo and self.empresa_id:
            saldo = self.repo.saldo_subcuenta(self.empresa_id, codsubcuenta)
            return {"codsubcuenta": codsubcuenta, "saldo": float(saldo)}
        return None

    # --- Contabilidad local ---
    def pyg(self, ejercicio: str | None = None) -> dict | None:
        """PyG desde BD local."""
        if self.repo and self.empresa_id:
            return self.repo.pyg(self.empresa_id, ejercicio=ejercicio)
        return None

    def balance(self) -> dict | None:
        """Balance desde BD local."""
        if self.repo and self.empresa_id:
            return self.repo.balance(self.empresa_id)
        return None

    # --- Auditoria ---
    def registrar_auditoria(self, accion: str, **kwargs):
        """Registra accion en audit log."""
        if self.repo:
            self.repo.registrar_auditoria(self.empresa_id, accion, **kwargs)

    # --- Sincronizacion ---
    def sincronizar_pendientes(self) -> dict:
        """Reintenta operaciones pendientes con FS."""
        if self.modo != "dual" or not self.repo:
            return {"sincronizados": 0, "errores": 0}

        # Por ahora placeholder — se implementara con cola de sync
        return {"sincronizados": 0, "errores": 0}

    # --- Helpers privados ---
    def _guardar_asiento_local(self, data: dict, resultado_fs: dict) -> int | None:
        """Guarda asiento en BD local. Retorna ID local del asiento."""
        from sfce.db.modelos import Asiento

        idasiento_fs = data.get("_idasiento_fs")  # explícito para sync
        if not idasiento_fs and resultado_fs and not resultado_fs.get("_pendiente_sync"):
            if "data" in resultado_fs:
                idasiento_fs = resultado_fs["data"].get("idasiento")

        fecha_str = data.get("fecha")
        if fecha_str and isinstance(fecha_str, str):
            try:
                from datetime import datetime as dt
                # Formato FS: DD-MM-YYYY o YYYY-MM-DD
                if "-" in fecha_str and len(fecha_str.split("-")[0]) == 4:
                    fecha = dt.strptime(fecha_str, "%Y-%m-%d").date()
                else:
                    fecha = dt.strptime(fecha_str, "%d-%m-%Y").date()
            except ValueError:
                fecha = date.today()
        else:
            fecha = date.today()

        asiento = Asiento(
            empresa_id=self.empresa_id,
            fecha=fecha,
            concepto=data.get("concepto", ""),
            ejercicio=data.get("codejercicio", ""),
            idasiento_fs=idasiento_fs,
            origen="pipeline",
            sincronizado_fs=idasiento_fs is not None,
        )
        self.repo.crear(asiento)
        return asiento.id

    def _guardar_factura_local(self, data: dict, resultado_fs: dict):
        """Guarda factura en BD local."""
        from sfce.db.modelos import Documento
        doc = Documento(
            empresa_id=self.empresa_id,
            tipo_doc="FC",
            estado="registrado",
            ejercicio=data.get("codejercicio", ""),
        )
        if resultado_fs and "doc" in resultado_fs:
            doc.factura_id_fs = resultado_fs["doc"].get("idfactura")
        self.repo.crear(doc)

    def _guardar_proveedor_local(self, data: dict):
        """Guarda proveedor en BD local."""
        from sfce.db.modelos import ProveedorCliente
        prov = ProveedorCliente(
            empresa_id=self.empresa_id,
            cif=data.get("cifnif", ""),
            nombre=data.get("nombre", ""),
            tipo="proveedor",
        )
        try:
            self.repo.crear(prov)
        except Exception:
            pass  # Duplicado, ignorar

    def _guardar_cliente_local(self, data: dict):
        """Guarda cliente en BD local."""
        from sfce.db.modelos import ProveedorCliente
        cli = ProveedorCliente(
            empresa_id=self.empresa_id,
            cif=data.get("cifnif", ""),
            nombre=data.get("nombre", ""),
            tipo="cliente",
        )
        try:
            self.repo.crear(cli)
        except Exception:
            pass  # Duplicado, ignorar

    def _guardar_partida_local(self, data: dict, resultado_fs: dict,
                                asiento_local_id: int):
        """Guarda partida en BD local."""
        from sfce.db.modelos import Partida
        from decimal import Decimal

        idpartida_fs = None
        if isinstance(resultado_fs, dict):
            idpartida_fs = resultado_fs.get("idpartida") or resultado_fs.get("id")

        partida = Partida(
            asiento_id=asiento_local_id,
            subcuenta=data.get("codsubcuenta", ""),
            debe=Decimal(str(data.get("debe", 0))),
            haber=Decimal(str(data.get("haber", 0))),
            concepto=data.get("concepto", ""),
            codimpuesto=data.get("codimpuesto", ""),
            idpartida_fs=idpartida_fs,
        )
        try:
            self.repo.crear(partida)
        except Exception as e:
            logger.warning(f"No se pudo guardar partida local: {e}")

    def _actualizar_partida_local(self, idpartida_fs: int, data: dict):
        """Actualiza partida en BD local por idpartida_fs."""
        from sfce.db.modelos import Partida
        try:
            sesion = self.repo.sesion_factory()
            with sesion:
                partida = sesion.query(Partida).filter(
                    Partida.idpartida_fs == idpartida_fs
                ).first()
                if partida:
                    if "codsubcuenta" in data:
                        partida.subcuenta = data["codsubcuenta"]
                    if "debe" in data:
                        partida.debe = Decimal(str(data["debe"]))
                    if "haber" in data:
                        partida.haber = Decimal(str(data["haber"]))
                    sesion.commit()
        except Exception as e:
            logger.warning(f"No se pudo actualizar partida local (fs={idpartida_fs}): {e}")

    def _actualizar_factura_local(self, endpoint: str, data: dict):
        """Actualiza factura en BD local (ej: pagada)."""
        from sfce.db.modelos import Factura
        # Extraer idfactura del endpoint: "facturaproveedores/123" o "facturaclientes/123"
        partes = endpoint.rstrip("/").split("/")
        if len(partes) < 2:
            return
        try:
            idfactura_fs = int(partes[-1])
        except (ValueError, IndexError):
            return

        try:
            sesion = self.repo.sesion_factory()
            with sesion:
                factura = sesion.query(Factura).filter(
                    Factura.idfactura_fs == idfactura_fs
                ).first()
                if factura and "pagada" in data:
                    factura.pagada = bool(int(data["pagada"]))
                    sesion.commit()
        except Exception as e:
            logger.warning(f"No se pudo actualizar factura local (fs={idfactura_fs}): {e}")
