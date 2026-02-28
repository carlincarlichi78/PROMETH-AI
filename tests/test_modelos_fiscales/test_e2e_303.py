"""Tests E2E modelo 303 — datos → casillas → BOE → PDF."""
import pytest

from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.repositorio import Repositorio
from sfce.db.modelos import Empresa
from sfce.core.servicio_fiscal import ServicioFiscal
from sfce.modelos_fiscales.generador import GeneradorModelos
from sfce.modelos_fiscales.generador_pdf import GeneradorPDF
from sfce.normativa.vigente import Normativa


# ─────────────────────────── fixtures ───────────────────────────

@pytest.fixture
def motor_bd():
    """Motor SQLite en memoria para cada test."""
    motor = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
    inicializar_bd(motor)
    return motor


@pytest.fixture
def repo(motor_bd):
    """Repositorio con BD en memoria limpia."""
    sesion_factory = crear_sesion(motor_bd)
    return Repositorio(sesion_factory)


@pytest.fixture
def empresa_prueba(repo):
    """Inserta empresa de prueba y retorna su id."""
    empresa = Empresa(
        nombre="EMPRESA TEST S.L.",
        cif="B12345678",
        forma_juridica="sl",
        activa=True,
    )
    repo.crear(empresa)
    return empresa


@pytest.fixture
def servicio(repo):
    """ServicioFiscal con normativa real y repositorio en memoria."""
    normativa = Normativa()
    return ServicioFiscal(repo, normativa)


@pytest.fixture
def casillas_303():
    """Casillas de prueba realistas para el modelo 303."""
    return {
        "01": 10000.0,   # base imponible tipo general
        "03": 0.0,       # cuota devengada tipo general (se calcula)
        "27": 2100.0,    # total cuotas devengadas
        "28": 5000.0,    # base IVA deducible
        "29": 1050.0,    # cuota IVA deducible
        "31": 0.0,
        "33": 0.0,
        "35": 0.0,
        "36": 0.0,
        "37": 1050.0,    # total a deducir
        "45": 1050.0,    # diferencia (27 - 37)
        "64": 0.0,
        "69": 1050.0,    # resultado a ingresar
    }


@pytest.fixture
def empresa_datos():
    """Datos de empresa para generacion BOE/PDF."""
    return {"nif": "B12345678", "nombre": "EMPRESA TEST S.L."}


# ─────────────────────────── tests ───────────────────────────────

class TestE2E303CasillasDesdeServicio:
    """Calculo de casillas via ServicioFiscal con BD vacia (devuelve 0s)."""

    def test_servicio_devuelve_dict_casillas(self, servicio, empresa_prueba):
        resultado = servicio.calcular_casillas(
            empresa_id=empresa_prueba.id,
            modelo="303",
            ejercicio="2025",
            periodo="1T",
        )
        assert isinstance(resultado["casillas"], dict)
        assert resultado["modelo"] == "303"
        assert resultado["ejercicio"] == "2025"
        assert resultado["periodo"] == "1T"

    def test_casillas_bd_vacia_son_numericas(self, servicio, empresa_prueba):
        resultado = servicio.calcular_casillas(
            empresa_id=empresa_prueba.id,
            modelo="303",
            ejercicio="2025",
            periodo="1T",
        )
        casillas = resultado["casillas"]
        for clave, valor in casillas.items():
            assert isinstance(valor, (int, float)), (
                f"Casilla {clave} debe ser numerica, es {type(valor)}"
            )


class TestE2E303ValidacionCasillas:
    """Validacion de casillas contra reglas AEAT del modelo 303."""

    def test_validar_casillas_devuelve_resultado(self, casillas_303):
        gen = GeneradorModelos()
        resultado = gen.validar("303", casillas_303)
        assert hasattr(resultado, "valido")
        assert hasattr(resultado, "errores")
        assert hasattr(resultado, "advertencias")

    def test_casillas_coherentes_devuelven_resultado_validacion(self, casillas_303):
        """La validacion siempre devuelve un ResultadoValidacion con la estructura correcta."""
        gen = GeneradorModelos()
        resultado = gen.validar("303", casillas_303)
        assert hasattr(resultado, "valido")
        assert hasattr(resultado, "errores")
        assert hasattr(resultado, "advertencias")
        assert isinstance(resultado.errores, list)
        assert isinstance(resultado.advertencias, list)

    def test_casillas_303_completas_son_validas(self):
        """Casillas aritmeticamente coherentes con todas las reglas del 303."""
        gen = GeneradorModelos()
        # Casillas que satisfacen todas las reglas del YAML:
        # casilla_27 == casilla_03 + casilla_06 + casilla_09 + casilla_12 + casilla_15 + casilla_77 + casilla_26
        # casilla_64 == casilla_45 - casilla_46
        # casilla_69 == casilla_64
        casillas_completas = {
            "01": 10000.0,
            "03": 2100.0,   # 10000 × 21%
            "06": 0.0,
            "09": 0.0,
            "12": 0.0,
            "15": 0.0,
            "26": 0.0,
            "77": 0.0,
            "27": 2100.0,   # suma de cuotas = 2100
            "28": 5000.0,
            "29": 1050.0,
            "35": 0.0,
            "36": 0.0,
            "37": 1050.0,   # total deducible
            "45": 1050.0,   # 27 - 37
            "46": 0.0,
            "64": 1050.0,   # 45 - 46
            "69": 1050.0,   # == 64
        }
        resultado = gen.validar("303", casillas_completas)
        assert resultado.valido is True, (
            f"Casillas completas deben ser validas. Errores: {resultado.errores}"
        )

    def test_casilla_69_incorrecta_produce_advertencia_o_error(self):
        """Si casilla 69 no coincide con 64, debe producir advertencia o error."""
        gen = GeneradorModelos()
        casillas_incorrectas = {
            "27": 2100.0,
            "37": 1050.0,
            "45": 1050.0,
            "64": 1050.0,
            "69": 9999.0,  # deberia ser 1050
        }
        resultado = gen.validar("303", casillas_incorrectas)
        tiene_problema = (
            not resultado.valido
            or len(resultado.advertencias) > 0
            or len(resultado.errores) > 0
        )
        assert tiene_problema, "Casilla 69 incorrecta debe producir error o advertencia"


class TestE2E303GeneracionBOE:
    """Generacion de fichero BOE posicional para el modelo 303."""

    def test_generar_boe_devuelve_resultado(self, casillas_303, empresa_datos):
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas=casillas_303,
            empresa=empresa_datos,
        )
        assert resultado is not None
        assert resultado.contenido
        assert resultado.nombre_fichero

    def test_boe_longitud_correcta(self, casillas_303, empresa_datos):
        """El fichero BOE debe tener la longitud definida en el YAML (500 chars)."""
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas=casillas_303,
            empresa=empresa_datos,
        )
        # El registro tiene 500 caracteres segun 303.yaml
        assert len(resultado.contenido) == 500

    def test_boe_primer_char_es_1(self, casillas_303, empresa_datos):
        """Posicion 1 del registro es tipo_registro = '1' (siempre)."""
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas=casillas_303,
            empresa=empresa_datos,
        )
        assert resultado.contenido[0] == "1", (
            f"Primer caracter debe ser '1', es '{resultado.contenido[0]}'"
        )

    def test_boe_modelo_en_posicion_2_4(self, casillas_303, empresa_datos):
        """Posiciones 2-4 contienen el identificador del modelo '303'."""
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas=casillas_303,
            empresa=empresa_datos,
        )
        # Posiciones 1-indexed [2,4] → 0-indexed [1:4]
        assert resultado.contenido[1:4] == "303"

    def test_boe_nif_en_posicion_9_17(self, casillas_303, empresa_datos):
        """Posiciones 9-17 contienen el NIF del declarante."""
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas=casillas_303,
            empresa=empresa_datos,
        )
        # Posiciones 1-indexed [9,17] → 0-indexed [8:17]
        nif_en_fichero = resultado.contenido[8:17].strip()
        assert nif_en_fichero == "B12345678"

    def test_boe_nombre_fichero_formato_correcto(self, casillas_303, empresa_datos):
        """El nombre de fichero sigue el formato {NIF}_{ejercicio}_{periodo}.{modelo}."""
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas=casillas_303,
            empresa=empresa_datos,
        )
        # Formato: B12345678_2025_1T.303
        assert resultado.nombre_fichero == "B12345678_2025_1T.303"

    def test_boe_ejercicio_en_posicion_5_8(self, casillas_303, empresa_datos):
        """Posiciones 5-8 contienen el ejercicio fiscal."""
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas=casillas_303,
            empresa=empresa_datos,
        )
        # Posiciones 1-indexed [5,8] → 0-indexed [4:8]
        ejercicio_fichero = resultado.contenido[4:8]
        assert ejercicio_fichero == "2025"


class TestE2E303FlujoCompleto:
    """Test del flujo completo via ServicioFiscal con casillas_override."""

    def test_generar_modelo_con_override(self, servicio, empresa_prueba, casillas_303, empresa_datos):
        """Flujo completo: calcular (BD vacia) + override + generar BOE."""
        resultado = servicio.generar_modelo(
            empresa_id=empresa_prueba.id,
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas_override=casillas_303,
            empresa_datos=empresa_datos,
        )
        assert "casillas" in resultado
        assert "contenido_boe" in resultado
        assert "nombre_fichero" in resultado
        assert "validacion" in resultado

    def test_contenido_boe_longitud_500(self, servicio, empresa_prueba, casillas_303, empresa_datos):
        resultado = servicio.generar_modelo(
            empresa_id=empresa_prueba.id,
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas_override=casillas_303,
            empresa_datos=empresa_datos,
        )
        assert len(resultado["contenido_boe"]) == 500

    def test_casillas_override_aplicadas(self, servicio, empresa_prueba, empresa_datos):
        """Las casillas del override se reflejan en el resultado final."""
        override = {"27": 5555.0, "69": 5555.0, "37": 0.0, "45": 5555.0}
        resultado = servicio.generar_modelo(
            empresa_id=empresa_prueba.id,
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas_override=override,
            empresa_datos=empresa_datos,
        )
        assert resultado["casillas"]["27"] == 5555.0
        assert resultado["casillas"]["69"] == 5555.0

    def test_validacion_incluida_en_resultado(self, servicio, empresa_prueba, casillas_303, empresa_datos):
        resultado = servicio.generar_modelo(
            empresa_id=empresa_prueba.id,
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas_override=casillas_303,
            empresa_datos=empresa_datos,
        )
        validacion = resultado["validacion"]
        assert "valido" in validacion
        assert "errores" in validacion
        assert "advertencias" in validacion


class TestE2E303GeneracionPDF:
    """Generacion de PDF visual del modelo 303."""

    def test_generar_pdf_devuelve_bytes(self, casillas_303, empresa_datos):
        gen_pdf = GeneradorPDF()
        pdf_bytes = gen_pdf.generar(
            modelo="303",
            casillas=casillas_303,
            empresa=empresa_datos,
            ejercicio="2025",
            periodo="1T",
        )
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_pdf_empieza_con_header_pdf(self, casillas_303, empresa_datos):
        """Un PDF valido siempre empieza con %PDF."""
        gen_pdf = GeneradorPDF()
        pdf_bytes = gen_pdf.generar(
            modelo="303",
            casillas=casillas_303,
            empresa=empresa_datos,
            ejercicio="2025",
            periodo="1T",
        )
        assert pdf_bytes[:4] == b"%PDF", (
            f"El PDF debe empezar con %PDF, empieza con {pdf_bytes[:4]!r}"
        )

    def test_pdf_guardar_en_disco(self, casillas_303, empresa_datos, tmp_path):
        """El PDF se puede guardar en disco correctamente."""
        gen_pdf = GeneradorPDF()
        pdf_bytes = gen_pdf.generar(
            modelo="303",
            casillas=casillas_303,
            empresa=empresa_datos,
            ejercicio="2025",
            periodo="1T",
        )
        ruta = gen_pdf.guardar(pdf_bytes, tmp_path, "modelo_303_prueba")
        assert ruta.exists()
        assert ruta.stat().st_size > 0
        assert ruta.suffix == ".pdf"
