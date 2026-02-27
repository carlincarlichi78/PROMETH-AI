"""Tests para MotorBOE — generador posicional generico."""
import pytest
from sfce.modelos_fiscales.motor_boe import MotorBOE
from sfce.modelos_fiscales.tipos import (
    CampoSpec, RegistroSpec, DisenoModelo, TipoCampo, ResultadoGeneracion
)


def _diseno_simple() -> DisenoModelo:
    """Diseno de test: 50 chars, 4 campos."""
    return DisenoModelo(
        modelo="TEST",
        version="2025",
        tipo_formato="posicional",
        longitud_registro=50,
        registros=[
            RegistroSpec(tipo="unico", campos=[
                CampoSpec(nombre="tipo", posicion=(1, 1), tipo=TipoCampo.ALFANUMERICO, valor_fijo="1"),
                CampoSpec(nombre="modelo", posicion=(2, 5), tipo=TipoCampo.NUMERICO, valor_fijo="0303"),
                CampoSpec(nombre="nif", posicion=(6, 14), tipo=TipoCampo.ALFANUMERICO, fuente="nif_declarante"),
                CampoSpec(nombre="importe", posicion=(15, 30), tipo=TipoCampo.NUMERICO_SIGNO, decimales=2, fuente="casillas.01"),
            ])
        ],
        validaciones=[]
    )


class TestMotorBOE:
    def test_generar_linea_basica(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno,
            ejercicio="2025",
            periodo="1T",
            casillas={"01": 15234.50},
            empresa={"nif": "B12345678", "nombre": "TEST SL"}
        )
        assert isinstance(resultado, ResultadoGeneracion)
        assert len(resultado.contenido) == 50
        # tipo_registro
        assert resultado.contenido[0] == "1"
        # modelo
        assert resultado.contenido[1:5] == "0303"
        # nif (9 chars, relleno espacios derecha)
        assert resultado.contenido[5:14] == "B12345678"

    def test_numerico_signo_positivo(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={"01": 15234.50},
            empresa={"nif": "B12345678"}
        )
        # posicion 15-30 = 16 chars, numerico_signo: " 00000001523450"
        campo_importe = resultado.contenido[14:30]
        assert campo_importe[0] == " "  # positivo
        assert "1523450" in campo_importe

    def test_numerico_signo_negativo(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={"01": -500.25},
            empresa={"nif": "B12345678"}
        )
        campo_importe = resultado.contenido[14:30]
        assert campo_importe[0] == "N"  # negativo

    def test_nombre_fichero(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={"01": 0},
            empresa={"nif": "B12345678"}
        )
        assert resultado.nombre_fichero == "B12345678_2025_1T.TEST"

    def test_casilla_faltante_usa_cero(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={},  # sin casilla 01
            empresa={"nif": "B12345678"}
        )
        assert len(resultado.contenido) == 50

    def test_alfanumerico_trunca_si_largo(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={"01": 0},
            empresa={"nif": "B12345678901234"}  # mas largo que 9 chars
        )
        assert len(resultado.contenido) == 50

    def test_multiples_registros(self):
        diseno = DisenoModelo(
            modelo="MULTI", version="2025", tipo_formato="posicional",
            longitud_registro=20,
            registros=[
                RegistroSpec(tipo="cabecera", campos=[
                    CampoSpec(nombre="tipo", posicion=(1, 1), tipo=TipoCampo.ALFANUMERICO, valor_fijo="1"),
                ]),
                RegistroSpec(tipo="detalle", campos=[
                    CampoSpec(nombre="tipo", posicion=(1, 1), tipo=TipoCampo.ALFANUMERICO, valor_fijo="2"),
                ]),
            ],
            validaciones=[]
        )
        motor = MotorBOE()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={}, empresa={"nif": "X"}
        )
        lineas = resultado.contenido.split("\r\n")
        assert len(lineas) == 2
        assert lineas[0][0] == "1"
        assert lineas[1][0] == "2"

    def test_registros_repetibles_con_declarados(self):
        diseno = DisenoModelo(
            modelo="347", version="2025", tipo_formato="posicional",
            longitud_registro=30,
            registros=[
                RegistroSpec(tipo="cabecera", campos=[
                    CampoSpec(nombre="tipo", posicion=(1, 1), tipo=TipoCampo.ALFANUMERICO, valor_fijo="1"),
                ]),
                RegistroSpec(tipo="declarado", repetible=True, campos=[
                    CampoSpec(nombre="tipo", posicion=(1, 1), tipo=TipoCampo.ALFANUMERICO, valor_fijo="2"),
                    CampoSpec(nombre="nif_decl", posicion=(2, 10), tipo=TipoCampo.ALFANUMERICO, fuente="declarado.nif"),
                    CampoSpec(nombre="importe", posicion=(11, 25), tipo=TipoCampo.NUMERICO_SIGNO, decimales=2, fuente="casillas.importe_anual"),
                ]),
            ],
            validaciones=[]
        )
        motor = MotorBOE()
        declarados = [
            {"nif": "A11111111", "importe_anual": 5000.00},
            {"nif": "B22222222", "importe_anual": 8000.00},
        ]
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="0A",
            casillas={}, empresa={"nif": "X"},
            declarados=declarados
        )
        lineas = resultado.contenido.split("\r\n")
        assert len(lineas) == 3  # 1 cabecera + 2 declarados
        assert lineas[1][1:10] == "A11111111"
        assert lineas[2][1:10] == "B22222222"
