"""Tests para sfce.core.backend — capa abstraccion sobre FacturaScripts."""
import pytest
from unittest.mock import patch, MagicMock
from sfce.core.backend import Backend


class TestBackendInterfaz:
    def test_crear_backend_fs(self):
        b = Backend(modo="fs")
        assert b.modo == "fs"

    def test_interfaz_completa(self):
        """Todos los metodos de la interfaz existen."""
        b = Backend(modo="fs")
        metodos = [
            "crear_factura", "crear_asiento", "crear_partida",
            "obtener_subcuentas", "crear_proveedor", "crear_cliente",
            "obtener_saldo", "actualizar_factura", "actualizar_partida",
            "obtener_asientos", "obtener_partidas", "obtener_facturas",
        ]
        for m in metodos:
            assert hasattr(b, m), f"Falta metodo {m}"
            assert callable(getattr(b, m)), f"{m} no es callable"


class TestBackendDelegaFS:
    @patch("sfce.core.backend.api_post")
    def test_crear_factura_delega(self, mock_post):
        mock_post.return_value = {"doc": {"idfactura": 42}, "lines": []}
        b = Backend(modo="fs")
        resultado = b.crear_factura("crearFacturaProveedor", {"observaciones": "test"})
        mock_post.assert_called_once_with("crearFacturaProveedor", {"observaciones": "test"})
        assert resultado["doc"]["idfactura"] == 42

    @patch("sfce.core.backend.api_post")
    def test_crear_asiento_delega(self, mock_post):
        mock_post.return_value = {"ok": "OK", "data": {"idasiento": "99"}}
        b = Backend(modo="fs")
        resultado = b.crear_asiento({"concepto": "nomina enero"})
        mock_post.assert_called_once_with("asientos", {"concepto": "nomina enero"})
        assert resultado["data"]["idasiento"] == "99"

    @patch("sfce.core.backend.api_post")
    def test_crear_partida_delega(self, mock_post):
        mock_post.return_value = {"idpartida": 1}
        b = Backend(modo="fs")
        resultado = b.crear_partida({"codsubcuenta": "6000000000", "debe": 100})
        mock_post.assert_called_once()
        assert resultado["idpartida"] == 1

    @patch("sfce.core.backend.api_get")
    def test_obtener_subcuentas_delega(self, mock_get):
        mock_get.return_value = [{"codsubcuenta": "6000000000"}]
        b = Backend(modo="fs")
        resultado = b.obtener_subcuentas()
        mock_get.assert_called_once_with("subcuentas", {})
        assert len(resultado) == 1

    @patch("sfce.core.backend.api_put")
    def test_actualizar_factura_delega(self, mock_put):
        mock_put.return_value = {"idfactura": 1, "pagada": True}
        b = Backend(modo="fs")
        resultado = b.actualizar_factura("facturaproveedores/1", {"pagada": 1})
        mock_put.assert_called_once()

    @patch("sfce.core.backend.api_put")
    def test_actualizar_partida_delega(self, mock_put):
        mock_put.return_value = {"idpartida": 5}
        b = Backend(modo="fs")
        resultado = b.actualizar_partida(5, {"debe": 200})
        mock_put.assert_called_once_with("partidas/5", {"debe": 200})

    @patch("sfce.core.backend.api_get")
    def test_obtener_asientos_delega(self, mock_get):
        mock_get.return_value = [{"idasiento": 1}]
        b = Backend(modo="fs")
        resultado = b.obtener_asientos({"codejercicio": "2025"})
        mock_get.assert_called_once_with("asientos", {"codejercicio": "2025"})

    @patch("sfce.core.backend.api_get")
    def test_obtener_partidas_delega(self, mock_get):
        mock_get.return_value = [{"idpartida": 1}]
        b = Backend(modo="fs")
        resultado = b.obtener_partidas()
        mock_get.assert_called_once_with("partidas", {})

    @patch("sfce.core.backend.api_get")
    def test_obtener_facturas_delega(self, mock_get):
        mock_get.return_value = [{"idfactura": 1}]
        b = Backend(modo="fs")
        resultado = b.obtener_facturas("proveedores")
        mock_get.assert_called_once_with("facturaproveedores", {})

    @patch("sfce.core.backend.api_post")
    def test_crear_proveedor_delega(self, mock_post):
        mock_post.return_value = {"codproveedor": "001"}
        b = Backend(modo="fs")
        resultado = b.crear_proveedor({"nombre": "Test"})
        mock_post.assert_called_once_with("proveedores", {"nombre": "Test"})

    @patch("sfce.core.backend.api_post")
    def test_crear_cliente_delega(self, mock_post):
        mock_post.return_value = {"codcliente": "001"}
        b = Backend(modo="fs")
        resultado = b.crear_cliente({"nombre": "Test"})
        mock_post.assert_called_once_with("clientes", {"nombre": "Test"})
