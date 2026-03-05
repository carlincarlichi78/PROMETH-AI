"""Tests unitarios de FSAdapter — sin tocar FS real (todo mockeado)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call

import pytest
import requests

from sfce.core.fs_adapter import FSAdapter, FSError, FSResult, _normalizar_cif


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _adapter() -> FSAdapter:
    return FSAdapter(
        base_url="https://fs.test/api/3",
        token="token-test",
        idempresa=7,
        codejercicio="0007",
    )


def _mock_response(status: int = 200, body=None) -> MagicMock:
    """Crea un requests.Response falso."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.json.return_value = body if body is not None else {}
    resp.text = str(body)
    return resp


# ---------------------------------------------------------------------------
# A1 — _post: defensas básicas
# ---------------------------------------------------------------------------

class TestPostDefensas:

    def test_filtra_campos_internos(self):
        """Campos que empiezan por _ no llegan a FS."""
        adapter = _adapter()
        capturado = {}

        def fake_post(url, data, timeout):
            capturado.update(data)
            return _mock_response(200, {"idfactura": "1"})

        adapter._session.post = fake_post
        adapter._post("facturaclientes", {"nombre": "Test", "_interno": "secreto"})

        assert "_interno" not in capturado
        assert "nombre" in capturado

    def test_inyecta_idempresa_y_codejercicio(self):
        """idempresa y codejercicio se añaden si no están."""
        adapter = _adapter()
        capturado = {}

        def fake_post(url, data, timeout):
            capturado.update(data)
            return _mock_response(200, {})

        adapter._session.post = fake_post
        adapter._post("asientos", {"concepto": "Test", "fecha": "2025-01-01"})

        assert capturado["idempresa"] == 7
        assert capturado["codejercicio"] == "0007"

    def test_serializa_lineas_a_json(self):
        """Lista de líneas se convierte a json.dumps."""
        adapter = _adapter()
        capturado = {}

        def fake_post(url, data, timeout):
            capturado.update(data)
            return _mock_response(200, {})

        adapter._session.post = fake_post
        lineas = [{"codsubcuenta": "4300000001", "debe": 100, "haber": 0}]
        adapter._post("asientos", {"lineas": lineas})

        assert isinstance(capturado["lineas"], str)
        parsed = json.loads(capturado["lineas"])
        assert parsed[0]["codsubcuenta"] == "4300000001"

    def test_fuerza_recargo_cero_en_lineas(self):
        """recargo=0 se añade a cada línea si no existe."""
        adapter = _adapter()
        capturado = {}

        def fake_post(url, data, timeout):
            capturado.update(data)
            return _mock_response(200, {})

        adapter._session.post = fake_post
        lineas = [{"codsubcuenta": "6000000000", "debe": 50}]
        adapter._post("asientos", {"lineas": lineas})

        parsed = json.loads(capturado["lineas"])
        assert parsed[0]["recargo"] == 0

    def test_trunca_nick_a_10_chars(self):
        """codproveedor y codcliente se truncan a 10 caracteres."""
        adapter = _adapter()
        capturado = {}

        def fake_post(url, data, timeout):
            capturado.update(data)
            return _mock_response(200, {})

        adapter._session.post = fake_post
        adapter._post("facturaclientes", {"codcliente": "CLIENTEMUYLARGO"})

        assert len(capturado["codcliente"]) <= 10
        assert capturado["codcliente"] == "CLIENTEMUY"

    def test_convierte_personafisica_bool_a_int(self):
        """personafisica bool → int (0/1)."""
        adapter = _adapter()
        capturado = {}

        def fake_post(url, data, timeout):
            capturado.update(data)
            return _mock_response(200, {})

        adapter._session.post = fake_post

        adapter._post("proveedores", {"personafisica": True})
        assert capturado["personafisica"] == 1

        adapter._post("proveedores", {"personafisica": False})
        assert capturado["personafisica"] == 0

    def test_convierte_personafisica_str_a_int(self):
        """personafisica 'true'/'false' string → int."""
        adapter = _adapter()
        capturado = {}

        def fake_post(url, data, timeout):
            capturado.update(data)
            return _mock_response(200, {})

        adapter._session.post = fake_post
        adapter._post("proveedores", {"personafisica": "true"})
        assert capturado["personafisica"] == 1

    def test_retry_en_timeout(self):
        """Reintenta 3 veces ante Timeout y devuelve FSResult(ok=False)."""
        adapter = _adapter()
        conteo = {"llamadas": 0}

        def fake_post_timeout(url, data, timeout):
            conteo["llamadas"] += 1
            raise requests.exceptions.Timeout("timeout")

        adapter._session.post = fake_post_timeout

        with patch("sfce.core.fs_adapter.time.sleep"):
            result = adapter._post("asientos", {"concepto": "test"})

        assert result.ok is False
        assert conteo["llamadas"] == 3
        assert "Timeout" in result.error


# ---------------------------------------------------------------------------
# A4 — _normalizar_response: formatos de respuesta FS
# ---------------------------------------------------------------------------

class TestNormalizarResponse:

    def test_formato_ok_data(self):
        """Formato {"ok": "...", "data": {"idfactura": "5"}}."""
        adapter = _adapter()
        resp = _mock_response(200, {"ok": "Registro creado", "data": {"idfactura": "5"}})
        result = adapter._normalizar_response(resp)

        assert result.ok is True
        assert result.id_creado == 5

    def test_formato_plano(self):
        """Formato {"idfactura": "8"}."""
        adapter = _adapter()
        resp = _mock_response(200, {"idfactura": "8"})
        result = adapter._normalizar_response(resp)

        assert result.ok is True
        assert result.id_creado == 8

    def test_formato_lista(self):
        """Formato [{"idfactura": "3"}]."""
        adapter = _adapter()
        resp = _mock_response(200, [{"idfactura": "3"}])
        result = adapter._normalizar_response(resp)

        assert result.ok is True
        assert result.id_creado == 3

    def test_error_http_400(self):
        """HTTP 400 → FSResult(ok=False)."""
        adapter = _adapter()
        resp = _mock_response(400, {"error": "Datos inválidos"})
        result = adapter._normalizar_response(resp)

        assert result.ok is False
        assert "inválidos" in result.error
        assert result.http_status == 400


# ---------------------------------------------------------------------------
# Buscar proveedor por CIF
# ---------------------------------------------------------------------------

class TestBuscarProveedor:

    def test_busca_por_cif_normalizado(self):
        """Encuentra proveedor aunque el CIF tenga prefijo ES."""
        adapter = _adapter()
        adapter._get = MagicMock(return_value=[
            {"cifnif": "ES76638663H", "nombre": "Proveedor Test", "codproveedor": "PRO001"},
        ])

        resultado = adapter.buscar_proveedor("76638663H")
        assert resultado is not None
        assert resultado["codproveedor"] == "PRO001"

    def test_devuelve_none_si_no_existe(self):
        """Devuelve None si no hay coincidencia."""
        adapter = _adapter()
        adapter._get = MagicMock(return_value=[
            {"cifnif": "B12345678", "nombre": "Otro", "codproveedor": "PRO002"},
        ])

        resultado = adapter.buscar_proveedor("A99999999")
        assert resultado is None


# ---------------------------------------------------------------------------
# Crear factura 2 pasos
# ---------------------------------------------------------------------------

class TestCrearFactura2Pasos:

    def test_rollback_si_falla_linea(self):
        """Si falla una línea, elimina la cabecera creada."""
        adapter = _adapter()

        # POST cabecera → éxito (idfactura=42)
        # POST línea → error
        respuestas = [
            _mock_response(200, {"idfactura": "42"}),
            _mock_response(422, {"error": "Línea inválida"}),
        ]
        adapter._session.post = MagicMock(side_effect=respuestas)
        delete_llamado = {"url": None}

        def fake_delete(url, timeout):
            resp = MagicMock()
            resp.status_code = 200
            delete_llamado["url"] = url
            return resp

        adapter._session.delete = fake_delete

        result = adapter.crear_factura_proveedor(
            cabecera={"codproveedor": "PRO001", "fecha": "2025-01-15"},
            lineas=[{"pvpunitario": 100, "cantidad": 1, "codimpuesto": "IVA21"}],
        )

        assert result.ok is False
        assert "facturaproveedores/42" in delete_llamado["url"]

    def test_lote_clientes_ordena_por_fecha(self):
        """crear_lote_facturas_cliente ordena las facturas ASC antes de crearlas."""
        adapter = _adapter()
        fechas_enviadas = []

        def fake_crear(cabecera, lineas):
            fechas_enviadas.append(cabecera["fecha"])
            return FSResult(ok=True, id_creado=1, data={"idfactura": 1})

        adapter.crear_factura_cliente = fake_crear

        facturas = [
            {"cabecera": {"fecha": "2025-03-01"}, "lineas": []},
            {"cabecera": {"fecha": "2025-01-15"}, "lineas": []},
            {"cabecera": {"fecha": "2025-02-10"}, "lineas": []},
        ]
        adapter.crear_lote_facturas_cliente(facturas)

        assert fechas_enviadas == ["2025-01-15", "2025-02-10", "2025-03-01"]


# ---------------------------------------------------------------------------
# Obtener partidas — post-filtrado
# ---------------------------------------------------------------------------

class TestObtenerPartidas:

    def test_post_filtra_partidas_por_idasiento(self):
        """Solo devuelve partidas del idasiento correcto (filtros FS no funcionan)."""
        adapter = _adapter()
        adapter._get = MagicMock(return_value=[
            {"idpartida": 1, "idasiento": 10, "codsubcuenta": "4300000001"},
            {"idpartida": 2, "idasiento": 99, "codsubcuenta": "7000000000"},  # distinto
            {"idpartida": 3, "idasiento": 10, "codsubcuenta": "4770000000"},
        ])

        partidas = adapter.obtener_partidas(10)

        assert len(partidas) == 2
        assert all(p["idasiento"] == 10 for p in partidas)


# ---------------------------------------------------------------------------
# FSResult.raise_if_error
# ---------------------------------------------------------------------------

class TestFSResultRaiseIfError:

    def test_raise_si_error(self):
        result = FSResult(ok=False, error="Algo falló", http_status=500)
        with pytest.raises(FSError) as exc_info:
            result.raise_if_error()
        assert "Algo falló" in str(exc_info.value)
        assert exc_info.value.http_status == 500

    def test_no_raise_si_ok(self):
        result = FSResult(ok=True, id_creado=42)
        result.raise_if_error()  # No debe lanzar


# ---------------------------------------------------------------------------
# Normalizar CIF
# ---------------------------------------------------------------------------

class TestNormalizarCif:

    def test_mayusculas_y_sin_espacios(self):
        assert _normalizar_cif("  b-12345678  ") == "B12345678"

    def test_cadena_vacia(self):
        assert _normalizar_cif("") == ""

    def test_none(self):
        assert _normalizar_cif(None) == ""
