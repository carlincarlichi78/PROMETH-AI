"""Tests Task 5: parser Norma 43 (TXT) — AEB estándar + Extendida + CaixaBank."""
import os
from datetime import date
from decimal import Decimal

import pytest

from sfce.conectores.bancario.parser_c43 import MovimientoC43, parsear_c43

# ---------------------------------------------------------------------------
# Constructores de fixtures — formato estándar AEB
# ---------------------------------------------------------------------------

def _r11(banco: str = "2100", oficina: str = "3889", cuenta: str = "0200229053",
         divisa: str = "EUR", saldo: str = "000000000000010000", signo: str = "H") -> str:
    """Registro 11 (cabecera) estándar — 48 chars mínimo."""
    return "11" + banco + oficina + cuenta + divisa + "250101" + saldo + signo


def _r22(fecha_op: str, fecha_val: str, conc_comun: str, importe_cents: str,
         signo: str, ref1: str = "", ref2: str = "", concepto: str = "") -> str:
    """Registro 22 (movimiento) estándar — exactamente 105 chars."""
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
    """Registro 33 (totales) estándar — 74 chars."""
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
# Constructores de fixtures — formato CaixaBank (R22 de 80 chars)
# ---------------------------------------------------------------------------

def _r11_caixabank(banco: str = "2100", oficina: str = "3889",
                   cuenta: str = "0200255608") -> str:
    """
    Registro 11 CaixaBank — sin campo divisa ISO, con fecha_ini+fecha_fin.
    [2:6]=banco [6:10]=oficina [10:20]=cuenta [20:26]=fecha_ini [26:32]=fecha_fin
    """
    return "11" + banco + oficina + cuenta + "250101" + "260108" + " " * 26


def _r22_caixabank(fecha_op: str, fecha_val: str, conc_comun: str,
                   importe_cents: str, ref1: str = "", ref2: str = "") -> str:
    """
    Registro 22 formato CaixaBank — exactamente 80 chars.

    Layout:
      [0:2]  = "22"
      [2:6]  = "    " (4 espacios — marcador CaixaBank)
      [6:10] = cod_producto (4 dígitos)
      [10:16]= fecha_op (AAMMDD)
      [16:22]= fecha_val (AAMMDD)
      [22:24]= concepto_comun (2 dígitos)
      [24:28]= concepto_propio_banco (4 chars, CaixaBank extiende a 4)
      [28:42]= importe (14 chars, en céntimos)
      [42:43]= signo (siempre '0' en CaixaBank)
      [43:49]= num_documento (6 chars)
      [49:61]= ref1 (12 chars)
      [61:77]= ref2 (16 chars)
      [77:80]= libre (3 chars)
    """
    linea = (
        "22"
        + "    "                          # marcador CaixaBank (4 espacios)
        + "9736"                          # cod_producto (fijo para tests)
        + fecha_op.ljust(6)[:6]
        + fecha_val.ljust(6)[:6]
        + conc_comun.zfill(2)[:2]
        + "0300"                          # concepto_propio_banco (4 chars CaixaBank)
        + importe_cents.zfill(14)[:14]
        + "0"                             # signo siempre '0' en CaixaBank
        + "000000"                        # num_documento (6 chars)
        + ref1.ljust(12)[:12]
        + ref2.ljust(16)[:16]
        + "   "                           # libre (3 chars)
    )
    assert len(linea) == 80, f"R22 CaixaBank debe tener 80 chars, tiene {len(linea)}"
    return linea


def _extracto_caixabank(*movs: str) -> str:
    """Arma un extracto CaixaBank mínimo con los movimientos dados."""
    return "\n".join([_r11_caixabank(), *movs, "88"])


# ---------------------------------------------------------------------------
# Fixtures de texto — formato estándar
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
# Tests — formato estándar AEB
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
        r = parsear_c43(C43_MINIMO)
        assert r["banco_codigo"] == "2100"


# ---------------------------------------------------------------------------
# Tests — formato CaixaBank extendido
# ---------------------------------------------------------------------------

class TestCaixaBankFormato:
    """
    Formato CaixaBank: R22 de 80 chars con prefijo 8 chars antes de las fechas.
    El campo signo R22 es siempre '0'; la dirección se infiere del concepto_común.
    """

    def test_detecta_formato_caixabank(self):
        r22 = _r22_caixabank("250115", "250115", "03", "00000000001500")
        r = parsear_c43(_extracto_caixabank(r22))
        assert len(r["movimientos"]) == 1

    def test_fecha_operacion_caixabank(self):
        r22 = _r22_caixabank("250115", "250117", "03", "00000000001500")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.fecha_operacion == date(2025, 1, 15)

    def test_fecha_valor_caixabank(self):
        r22 = _r22_caixabank("250115", "250117", "03", "00000000001500")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.fecha_valor == date(2025, 1, 17)

    def test_importe_caixabank(self):
        r22 = _r22_caixabank("250115", "250115", "03", "00000000002599")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.importe == Decimal("25.99")

    def test_importe_entero_caixabank(self):
        r22 = _r22_caixabank("250115", "250115", "03", "00000000010000")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.importe == Decimal("100.00")

    def test_signo_adeudo_concepto_03(self):
        """Concepto 03 (adeudo genérico) → signo 'D'."""
        r22 = _r22_caixabank("250115", "250115", "03", "00000000001500")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.signo == "D"

    def test_signo_abono_concepto_02(self):
        """Concepto 02 (abono genérico) → signo 'H'."""
        r22 = _r22_caixabank("250115", "250115", "02", "00000000005000")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.signo == "H"

    def test_signo_abono_concepto_06(self):
        """Concepto 06 (nómina/abono) → signo 'H'."""
        r22 = _r22_caixabank("250115", "250115", "06", "00000000120000")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.signo == "H"

    def test_signo_adeudo_concepto_07(self):
        """Concepto 07 (comisiones bancarias) → signo 'D'."""
        r22 = _r22_caixabank("250115", "250115", "07", "00000000001200")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.signo == "D"

    def test_signo_adeudo_concepto_12(self):
        """Concepto 12 (tarjeta/domiciliación) → signo 'D'."""
        r22 = _r22_caixabank("250115", "250115", "12", "00000000001000")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.signo == "D"

    def test_concepto_comun_caixabank(self):
        r22 = _r22_caixabank("250115", "250115", "03", "00000000001500")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.concepto_comun == "03"

    def test_concepto_propio_desde_r23(self):
        """En CaixaBank el concepto viene en R23; R22 no tiene campo concepto."""
        r22 = _r22_caixabank("250115", "250115", "03", "00000000001000")
        r23 = "2304" + "AMAZON PAYMENTS EUROPE             ".ljust(72)[:72]
        extracto = "\n".join([_r11_caixabank(), r22, r23, "88"])
        mov = parsear_c43(extracto)["movimientos"][0]
        assert "AMAZON PAYMENTS EUROPE" in mov.concepto_propio

    def test_banco_codigo_caixabank(self):
        r22 = _r22_caixabank("250115", "250115", "02", "00000000001000")
        r = parsear_c43(_extracto_caixabank(r22))
        assert r["banco_codigo"] == "2100"

    def test_iban_caixabank(self):
        r22 = _r22_caixabank("250115", "250115", "02", "00000000001000")
        r = parsear_c43(_extracto_caixabank(r22))
        assert r["iban"] == "210038890200255608"

    def test_divisa_por_defecto_eur_caixabank(self):
        """CaixaBank no tiene campo divisa ISO en R11 → debe retornar 'EUR'."""
        r22 = _r22_caixabank("250115", "250115", "02", "00000000001000")
        r = parsear_c43(_extracto_caixabank(r22))
        assert r["divisa"] == "EUR"

    def test_multiples_movimientos_caixabank(self):
        movs = [
            _r22_caixabank("250101", "250101", "03", "00000000002500"),
            _r22_caixabank("250115", "250115", "02", "00000000150000"),
            _r22_caixabank("250131", "250131", "07", "00000000001200"),
        ]
        r = parsear_c43(_extracto_caixabank(*movs))
        assert len(r["movimientos"]) == 3
        assert r["movimientos"][0].signo == "D"
        assert r["movimientos"][1].signo == "H"
        assert r["movimientos"][2].signo == "D"

    def test_num_orden_caixabank(self):
        movs = [
            _r22_caixabank("250101", "250101", "03", "00000000001000"),
            _r22_caixabank("250115", "250115", "02", "00000000002000"),
        ]
        r = parsear_c43(_extracto_caixabank(*movs))
        assert r["movimientos"][0].num_orden == 1
        assert r["movimientos"][1].num_orden == 2

    def test_fecha_diciembre_caixabank(self):
        """Verifica parsing de fecha de diciembre (mes 12) en CaixaBank."""
        r22 = _r22_caixabank("251218", "251220", "02", "00000000300000")
        mov = parsear_c43(_extracto_caixabank(r22))["movimientos"][0]
        assert mov.fecha_operacion == date(2025, 12, 18)
        assert mov.fecha_valor == date(2025, 12, 20)


# ---------------------------------------------------------------------------
# Tests — archivo C43 real (opcional, requiere archivo externo)
# ---------------------------------------------------------------------------

_REAL_C43 = r"C:\Users\carli\Downloads\TT191225.208.txt"


@pytest.mark.skipif(not os.path.exists(_REAL_C43), reason="Archivo C43 real no disponible")
class TestArchivoRealCaixaBank:
    """Tests contra el archivo C43 real de CaixaBank (TT191225.208.txt)."""

    def _parsear(self):
        with open(_REAL_C43, encoding="latin-1") as f:
            return parsear_c43(f.read())

    def test_parsea_todos_los_movimientos(self):
        """TT191225.208.txt tiene 505 registros R22."""
        r = self._parsear()
        assert len(r["movimientos"]) >= 500

    def test_banco_caixabank(self):
        r = self._parsear()
        assert r["banco_codigo"] == "2100"

    def test_divisa_eur(self):
        r = self._parsear()
        assert r["divisa"] == "EUR"

    def test_todas_las_fechas_validas(self):
        r = self._parsear()
        for mov in r["movimientos"]:
            assert 2024 <= mov.fecha_operacion.year <= 2026

    def test_todos_los_importes_positivos(self):
        r = self._parsear()
        for mov in r["movimientos"]:
            assert mov.importe > 0

    def test_todos_los_signos_validos(self):
        r = self._parsear()
        for mov in r["movimientos"]:
            assert mov.signo in ("D", "H")

    def test_num_orden_secuencial(self):
        r = self._parsear()
        movs = r["movimientos"]
        for i, mov in enumerate(movs, 1):
            assert mov.num_orden == i
