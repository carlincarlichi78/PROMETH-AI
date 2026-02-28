"""Tests Task 5: parser CaixaBank XLS."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from sfce.conectores.bancario.parser_xls import parsear_xls

# Archivo real CaixaBank — se usa solo si existe (tests de integración)
ARCHIVO_XLS = Path(r"C:\Users\carli\Downloads\TT280226.269.XLS")

pytestmark_real = pytest.mark.skipif(
    not ARCHIVO_XLS.exists(),
    reason=f"Archivo XLS no disponible: {ARCHIVO_XLS}",
)


# ---------------------------------------------------------------------------
# Tests con archivo real
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not ARCHIVO_XLS.exists(), reason="Archivo XLS no disponible")
class TestArchivoRealCaixaBank:
    """Valida el parser contra un extracto XLS real de CaixaBank."""

    @pytest.fixture(scope="class")
    def resultado(self):
        return parsear_xls(ARCHIVO_XLS.read_bytes())

    def test_banco_codigo(self, resultado):
        assert resultado["banco_codigo"] == "2100"

    def test_iban_sin_espacios(self, resultado):
        iban = resultado["iban"]
        assert " " not in iban
        assert iban.startswith("2100")

    def test_divisa_eur(self, resultado):
        assert resultado["divisa"] == "EUR"

    def test_tiene_movimientos(self, resultado):
        assert len(resultado["movimientos"]) > 0

    def test_signos_validos(self, resultado):
        for mov in resultado["movimientos"]:
            assert mov.signo in ("D", "H"), f"Signo inválido: {mov.signo!r}"

    def test_importes_positivos(self, resultado):
        for mov in resultado["movimientos"]:
            assert mov.importe > Decimal("0"), f"Importe no positivo: {mov.importe}"

    def test_fechas_tipo_date(self, resultado):
        for mov in resultado["movimientos"]:
            assert isinstance(mov.fecha_operacion, date)
            assert isinstance(mov.fecha_valor, date)

    def test_fechas_razonables(self, resultado):
        for mov in resultado["movimientos"]:
            assert 2020 <= mov.fecha_operacion.year <= 2030

    def test_saldo_final_positivo(self, resultado):
        assert resultado["saldo_final"] > Decimal("0")

    def test_num_orden_secuencial(self, resultado):
        movs = resultado["movimientos"]
        for i, mov in enumerate(movs, 1):
            assert mov.num_orden == i

    def test_concepto_propio_no_vacio(self, resultado):
        """Al menos algunos movimientos deben tener concepto."""
        con_concepto = [m for m in resultado["movimientos"] if m.concepto_propio.strip()]
        assert len(con_concepto) > 0

    def test_concepto_comun_formato(self, resultado):
        """concepto_comun debe ser string de 2 dígitos (o vacío)."""
        for mov in resultado["movimientos"]:
            if mov.concepto_comun:
                assert mov.concepto_comun.isdigit(), f"concepto_comun no es dígito: {mov.concepto_comun!r}"
                assert len(mov.concepto_comun) <= 2


# ---------------------------------------------------------------------------
# Tests con datos sintéticos (no dependen del archivo real)
# ---------------------------------------------------------------------------

def _crear_xls_sintetico(movimientos: list) -> bytes:
    """
    Crea un XLS mínimo con la estructura CaixaBank.
    Fila 0: vacía, Fila 1: título, Fila 2: vacía, Fila 3: cabecera, Fila 4+: datos
    Columnas: 0=vacía, 1=cuenta, 3=divisa, 4=f.op, 5=f.val, 6=ingreso, 7=gasto,
              8=saldo+, 9=saldo-, 10=conc_comun, 11=conc_prop, 12=ref1, 13=ref2
    """
    try:
        import xlwt
    except ImportError:
        pytest.skip("xlwt no disponible para crear XLS sintético")

    wb = xlwt.Workbook()
    ws = wb.add_sheet("Excel simple")

    ws.write(1, 0, "MOVIMIENTOS DESDE : 01/01/2025")
    ws.write(3, 1, "Número de cuenta")

    cuenta = "2100 3889 16 0200229053"
    for fila_idx, mov in enumerate(movimientos, start=4):
        ws.write(fila_idx, 1, cuenta)
        ws.write(fila_idx, 3, "EUR")
        ws.write(fila_idx, 4, mov["fecha_op"])
        ws.write(fila_idx, 5, mov["fecha_val"])
        if mov["signo"] == "H":
            ws.write(fila_idx, 6, mov["importe"])
            ws.write(fila_idx, 8, mov["saldo"])
        else:
            ws.write(fila_idx, 7, mov["importe"])
            ws.write(fila_idx, 8, mov["saldo"])
        ws.write(fila_idx, 10, mov.get("conc_comun", 17.0))
        ws.write(fila_idx, 11, mov.get("conc_prop", ""))

    import io
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestParserXlsUnitario:
    """Tests unitarios que no dependen del archivo real."""

    def test_importar_modulo(self):
        from sfce.conectores.bancario.parser_xls import parsear_xls
        assert callable(parsear_xls)

    def test_bytes_invalidos_lanza_excepcion(self):
        with pytest.raises(Exception):
            parsear_xls(b"esto no es un xls valido")

    def test_xls_sintetico_basico(self):
        movimientos = [
            {"fecha_op": "15/11/2025", "fecha_val": "15/11/2025",
             "signo": "D", "importe": 50.25, "saldo": 1000.00,
             "conc_comun": 17.0, "conc_prop": "COMISION"},
            {"fecha_op": "20/11/2025", "fecha_val": "20/11/2025",
             "signo": "H", "importe": 200.00, "saldo": 1200.00,
             "conc_comun": 2.0, "conc_prop": "TRANSFERENCIA"},
        ]
        datos = _crear_xls_sintetico(movimientos)
        r = parsear_xls(datos)

        assert r["banco_codigo"] == "2100"
        assert r["divisa"] == "EUR"
        assert len(r["movimientos"]) == 2

        cargo = r["movimientos"][0]
        assert cargo.signo == "D"
        assert cargo.importe == Decimal("50.25")
        assert cargo.fecha_operacion == date(2025, 11, 15)
        assert "COMISION" in cargo.concepto_propio

        abono = r["movimientos"][1]
        assert abono.signo == "H"
        assert abono.importe == Decimal("200.00")
        assert abono.num_orden == 2

    def test_xls_sintetico_saldo_final(self):
        movimientos = [
            {"fecha_op": "01/12/2025", "fecha_val": "01/12/2025",
             "signo": "H", "importe": 1500.00, "saldo": 1500.00},
        ]
        datos = _crear_xls_sintetico(movimientos)
        r = parsear_xls(datos)
        assert r["saldo_final"] == Decimal("1500.00")
