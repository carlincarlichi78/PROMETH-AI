"""Capa de abstraccion sobre FacturaScripts + BD local.

Todos los modulos del SFCE acceden a datos via Backend, nunca directamente
a fs_api. Doble destino: guarda en BD local Y envia a FS.
Si FS falla, marca como pendiente_sync para reintento.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from scripts.core.logger import crear_logger

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
        if self.modo in ("fs", "dual"):
            return self._api_put(endpoint, data)
        return data

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
    def crear_asiento(self, data: dict) -> dict:
        """Crea asiento contable."""
        resultado = {}

        if self.modo in ("fs", "dual"):
            try:
                resultado = self._api_post("asientos", data)
            except Exception as e:
                if self.modo == "dual":
                    logger.warning(f"FS fallo al crear asiento, guardando solo local: {e}")
                    resultado = {"_pendiente_sync": True, "_error_fs": str(e)}
                else:
                    raise

        if self.modo in ("local", "dual") and self.repo and self.empresa_id:
            self._guardar_asiento_local(data, resultado)

        return resultado

    def obtener_asientos(self, params: dict = None) -> list:
        """Obtiene asientos con filtros."""
        if self.modo in ("fs", "dual"):
            return self._api_get("asientos", params or {})
        return []

    # --- Partidas ---
    def crear_partida(self, data: dict) -> dict:
        """Crea partida (linea de asiento)."""
        if self.modo in ("fs", "dual"):
            return self._api_post("partidas", data)
        return data

    def actualizar_partida(self, idpartida: int, data: dict) -> dict:
        """Actualiza partida existente."""
        if self.modo in ("fs", "dual"):
            return self._api_put(f"partidas/{idpartida}", data)
        return data

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
    def _guardar_asiento_local(self, data: dict, resultado_fs: dict):
        """Guarda asiento en BD local."""
        from sfce.db.modelos import Asiento, Partida

        idasiento_fs = None
        if resultado_fs and not resultado_fs.get("_pendiente_sync"):
            # Parsear respuesta FS
            if "data" in resultado_fs:
                idasiento_fs = resultado_fs["data"].get("idasiento")

        asiento = Asiento(
            empresa_id=self.empresa_id,
            fecha=date.today(),
            concepto=data.get("concepto", ""),
            ejercicio=data.get("codejercicio", ""),
            idasiento_fs=idasiento_fs,
            origen="pipeline",
            sincronizado_fs=idasiento_fs is not None,
        )
        self.repo.crear(asiento)

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
