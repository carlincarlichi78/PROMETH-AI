"""Tests para sfce.core.backend — capa abstraccion sobre FacturaScripts."""
import pytest
from unittest.mock import MagicMock
from sfce.core.backend import Backend


def _backend_fs_mock():
    """Crea Backend modo FS con API mockeada."""
    b = Backend.__new__(Backend)
    b.modo = "fs"
    b.repo = None
    b.empresa_id = None
    b._api_get = MagicMock()
    b._api_post = MagicMock()
    b._api_put = MagicMock()
    b._api_delete = MagicMock()
    b._api_get_one = MagicMock()
    return b


class TestBackendInterfaz:
    def test_crear_backend_local(self):
        b = Backend(modo="local")
        assert b.modo == "local"

    def test_interfaz_completa(self):
        """Todos los metodos de la interfaz existen."""
        b = Backend(modo="local")
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
    def test_crear_factura_delega(self):
        b = _backend_fs_mock()
        b._api_post.return_value = {"doc": {"idfactura": 42}, "lines": []}
        resultado = b.crear_factura("crearFacturaProveedor", {"observaciones": "test"})
        b._api_post.assert_called_once_with("crearFacturaProveedor", {"observaciones": "test"})
        assert resultado["doc"]["idfactura"] == 42

    def test_crear_asiento_delega(self):
        b = _backend_fs_mock()
        b._api_post.return_value = {"ok": "OK", "data": {"idasiento": "99"}}
        resultado = b.crear_asiento({"concepto": "nomina enero"})
        b._api_post.assert_called_once_with("asientos", {"concepto": "nomina enero"})
        assert resultado["data"]["idasiento"] == "99"

    def test_crear_partida_delega(self):
        b = _backend_fs_mock()
        b._api_post.return_value = {"idpartida": 1}
        resultado = b.crear_partida({"codsubcuenta": "6000000000", "debe": 100})
        b._api_post.assert_called_once()
        assert resultado["idpartida"] == 1

    def test_obtener_subcuentas_delega(self):
        b = _backend_fs_mock()
        b._api_get.return_value = [{"codsubcuenta": "6000000000"}]
        resultado = b.obtener_subcuentas()
        b._api_get.assert_called_once_with("subcuentas", {})
        assert len(resultado) == 1

    def test_actualizar_factura_delega(self):
        b = _backend_fs_mock()
        b._api_put.return_value = {"idfactura": 1, "pagada": True}
        resultado = b.actualizar_factura("facturaproveedores/1", {"pagada": 1})
        b._api_put.assert_called_once()

    def test_actualizar_partida_delega(self):
        b = _backend_fs_mock()
        b._api_put.return_value = {"idpartida": 5}
        resultado = b.actualizar_partida(5, {"debe": 200})
        b._api_put.assert_called_once_with("partidas/5", {"debe": 200})

    def test_obtener_asientos_delega(self):
        b = _backend_fs_mock()
        b._api_get.return_value = [{"idasiento": 1}]
        resultado = b.obtener_asientos({"codejercicio": "2025"})
        b._api_get.assert_called_once_with("asientos", {"codejercicio": "2025"})

    def test_obtener_partidas_delega(self):
        b = _backend_fs_mock()
        b._api_get.return_value = [{"idpartida": 1}]
        resultado = b.obtener_partidas()
        b._api_get.assert_called_once_with("partidas", {})

    def test_obtener_facturas_delega(self):
        b = _backend_fs_mock()
        b._api_get.return_value = [{"idfactura": 1}]
        resultado = b.obtener_facturas("proveedores")
        b._api_get.assert_called_once_with("facturaproveedores", {})

    def test_crear_proveedor_delega(self):
        b = _backend_fs_mock()
        b._api_post.return_value = {"codproveedor": "001"}
        resultado = b.crear_proveedor({"nombre": "Test"})
        b._api_post.assert_called_once_with("proveedores", {"nombre": "Test"})

    def test_crear_cliente_delega(self):
        b = _backend_fs_mock()
        b._api_post.return_value = {"codcliente": "001"}
        resultado = b.crear_cliente({"nombre": "Test"})
        b._api_post.assert_called_once_with("clientes", {"nombre": "Test"})
