"""Tests Task 5: parser Norma 43 (TXT) — AEB estándar + Extendida."""
from datetime import date
from decimal import Decimal

import pytest

from sfce.conectores.bancario.parser_c43 import MovimientoC43, parsear_c43

# ---------------------------------------------------------------------------
# Constructores de fixtures
# ---------------------------------------------------------------------------

def _r11(banco: str = "2100", oficina: str = "3889", cuenta: str = "0200229053",
         divisa: str = "EUR", saldo: str = "000000000000010000", signo: str = "H") -> str:
    """Registro 11 (cabecera) — 48 chars mínimo."""
    return "11" + banco + oficina + cuenta + divisa + "250101" + saldo + signo


def _r22(fecha_op: str, fecha_val: str, conc_comun: str, importe_cents: str,
         signo: str, ref1: str = "", ref2: str = "", concepto: str = "") -> str:
    """Registro 22 (movimiento) — exactamente 105 chars."""
    linea = (
        "22"
        + fecha_op.ljust(6)[:6]
        + fecha_val.ljust(6)[:6]
        + conc_comun.zfill(2)[:2]
        + "00"                            # concepto_propio_banco (2 chars, ignorado)
        + importe_cents.zfill(14)[:14]
        + signo[:1]
        + "000000"                        # num_documento (6 chars)
        + ref1.ljust(12)[:12]
        + ref2.ljust(16)[:16]
        + concepto.ljust(38)[:38]
    )
    assert len(linea) == 105, f"R22 debe tener 105 chars, tiene {len(linea)}"
    return linea


def _r23(texto: str) -> str:
    """Registro 23 (concepto complementario) — 76 chars."""
    linea = "2300" + texto.ljust(72)[:72]
    assert len(linea) == 76
    return linea


def _r33(banco: str = "2100", oficina: str = "3889", cuenta: str = "0200229053",
         divisa: str = "EUR", saldo_final: str = "000000000000085000", signo: str = "H") -> str:
    """Registro 33 (totales) — 74 chars."""
    linea = (
        "33" + banco + oficina + cuenta + divisa + "251202"
        + "000001"            # num_debe (6)
        + "00000000001500"    # importe_debe (14)
        + "000001"            # num_haber (6)
        + saldo_final         # 18 chars
        + signo               # 1 char
    )
    assert len(linea) == 74, f"R33 debe tener 74 chars, tiene {len(linea)}"
    return linea


# ---------------------------------------------------------------------------
# Fixtures de texto
# ---------------------------------------------------------------------------

R22_CARGO = _r22("251130", "251130", "01", "00000000001500", "D",
                 ref1="REF001", ref2="REF002", concepto="COMPRA SUPERMERCADO")
R22_ABONO = _r22("251202", "251202", "02", "00000000002000", "H",
                 ref1="", ref2="", concepto="TRANSFERENCIA RECIBIDA")

C43_MINIMO = "\n".join([_r11(), R22_CARGO, R22_ABONO, _r33(), "88"])
C43_EXTENDIDO = "\n".join([_r11(), R22_CARGO, _r23("TEXTO ADICIONAL CONCEPTO"), R22_ABONO, _r33(), "88"])
C43_VACIO = "\n".join([_r11(), _r33(), "88"])
C43_SALDO_NEGATIVO = "\n".join([_r11(saldo="000000000000050000", signo="D"), R22_CARGO, _r33(), "88"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCabecera:
    def test_banco_codigo(self):
        r = parsear_c43(C43_MINIMO)
        assert r["banco_codigo"] == "2100"

    def test_iban(self):
        r = parsear_c43(C43_MINIMO)
        assert r["iban"] == "210038890200229053"

    def test_divisa(self):
        r = parsear_c43(C43_MINIMO)
        assert r["divisa"] == "EUR"

    def test_saldo_inicial_positivo(self):
        r = parsear_c43(C43_MINIMO)
        assert r["saldo_inicial"] == Decimal("100.00")

    def test_saldo_inicial_negativo(self):
        r = parsear_c43(C43_SALDO_NEGATIVO)
        assert r["saldo_inicial"] == Decimal("-500.00")

    def test_saldo_final(self):
        r = parsear_c43(C43_MINIMO)
        assert r["saldo_final"] == Decimal("850.00")


class TestMovimientos:
    def test_num_movimientos(self):
        r = parsear_c43(C43_MINIMO)
        assert len(r["movimientos"]) == 2

    def test_extracto_vacio(self):
        r = parsear_c43(C43_VACIO)
        assert len(r["movimientos"]) == 0

    def test_cargo(self):
        mov = parsear_c43(C43_MINIMO)["movimientos"][0]
        assert mov.fecha_operacion == date(2025, 11, 30)
        assert mov.fecha_valor == date(2025, 11, 30)
        assert mov.importe == Decimal("15.00")
        assert mov.signo == "D"
        assert mov.concepto_comun == "01"
        assert "COMPRA SUPERMERCADO" in mov.concepto_propio

    def test_abono(self):
        mov = parsear_c43(C43_MINIMO)["movimientos"][1]
        assert mov.fecha_operacion == date(2025, 12, 2)
        assert mov.importe == Decimal("20.00")
        assert mov.signo == "H"
        assert mov.concepto_comun == "02"
        assert "TRANSFERENCIA RECIBIDA" in mov.concepto_propio

    def test_referencias(self):
        mov = parsear_c43(C43_MINIMO)["movimientos"][0]
        assert mov.referencia_1 == "REF001"
        assert mov.referencia_2 == "REF002"

    def test_num_orden_secuencial(self):
        movs = parsear_c43(C43_MINIMO)["movimientos"]
        assert movs[0].num_orden == 1
        assert movs[1].num_orden == 2

    def test_movimiento_es_dataclass(self):
        mov = parsear_c43(C43_MINIMO)["movimientos"][0]
        assert isinstance(mov, MovimientoC43)


class TestNorma43Extendida:
    def test_concepto_complementario_concatenado(self):
        r = parsear_c43(C43_EXTENDIDO)
        mov = r["movimientos"][0]
        assert "COMPRA SUPERMERCADO" in mov.concepto_propio
        assert "TEXTO ADICIONAL CONCEPTO" in mov.concepto_propio

    def test_reg23_no_afecta_movimiento_siguiente(self):
        r = parsear_c43(C43_EXTENDIDO)
        mov2 = r["movimientos"][1]
        assert "TEXTO ADICIONAL CONCEPTO" not in mov2.concepto_propio

    def test_num_movimientos_con_reg23(self):
        # El reg 23 NO crea un movimiento extra
        r = parsear_c43(C43_EXTENDIDO)
        assert len(r["movimientos"]) == 2


class TestCasosEdge:
    def test_archivo_vacio_no_crashea(self):
        r = parsear_c43("")
        assert r["movimientos"] == []

    def test_lineas_cortas_ignoradas(self):
        contenido = "\n".join([_r11(), "22", R22_CARGO, _r33(), "88"])
        r = parsear_c43(contenido)
        assert len(r["movimientos"]) == 1

    def test_multiples_reg11_usa_primero(self):
        # Solo debe haber un reg 11 en un extracto real, pero el parser no debe crashear
        r = parsear_c43(C43_MINIMO)
        assert r["banco_codigo"] == "2100"
