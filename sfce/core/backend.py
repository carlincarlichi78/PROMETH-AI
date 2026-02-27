"""Capa de abstraccion sobre FacturaScripts (y futuros backends).

Todos los modulos del SFCE acceden a datos via Backend, nunca directamente
a fs_api. Esto permite:
- Cambiar backend sin tocar logica de negocio
- Doble destino (FS + BD local) en el futuro
- Testing con mocks limpios
"""
from typing import Any
from .fs_api import api_get, api_post, api_put, api_delete, api_get_one


class Backend:
    """Interfaz unificada para operaciones contables."""

    def __init__(self, modo: str = "fs"):
        self.modo = modo

    # --- Facturas ---
    def crear_factura(self, endpoint: str, data: dict) -> dict:
        """Crea factura via endpoint crearFactura*."""
        return api_post(endpoint, data)

    def actualizar_factura(self, endpoint: str, data: dict) -> dict:
        """Actualiza factura (ej: marcar pagada)."""
        return api_put(endpoint, data)

    def obtener_facturas(self, tipo: str = "proveedores", params: dict = None) -> list:
        """Obtiene facturas. tipo: 'proveedores' o 'clientes'."""
        ep = "facturaproveedores" if tipo == "proveedores" else "facturaclientes"
        return api_get(ep, params or {})

    # --- Asientos ---
    def crear_asiento(self, data: dict) -> dict:
        """Crea asiento contable."""
        return api_post("asientos", data)

    def obtener_asientos(self, params: dict = None) -> list:
        """Obtiene asientos con filtros."""
        return api_get("asientos", params or {})

    # --- Partidas ---
    def crear_partida(self, data: dict) -> dict:
        """Crea partida (linea de asiento)."""
        return api_post("partidas", data)

    def actualizar_partida(self, idpartida: int, data: dict) -> dict:
        """Actualiza partida existente."""
        return api_put(f"partidas/{idpartida}", data)

    def obtener_partidas(self, params: dict = None) -> list:
        """Obtiene partidas con filtros."""
        return api_get("partidas", params or {})

    # --- Subcuentas ---
    def obtener_subcuentas(self, params: dict = None) -> list:
        """Obtiene subcuentas contables."""
        return api_get("subcuentas", params or {})

    # --- Entidades ---
    def crear_proveedor(self, data: dict) -> dict:
        """Crea proveedor en FS."""
        return api_post("proveedores", data)

    def crear_cliente(self, data: dict) -> dict:
        """Crea cliente en FS."""
        return api_post("clientes", data)

    # --- Saldos ---
    def obtener_saldo(self, codsubcuenta: str, params: dict = None) -> dict | None:
        """Obtiene saldo de una subcuenta."""
        return api_get_one(f"subcuentas/{codsubcuenta}")
