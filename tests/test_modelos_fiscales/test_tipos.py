"""Tests para tipos base de modelos fiscales."""
from sfce.modelos_fiscales.tipos import (
    CampoSpec, RegistroSpec, ValidacionSpec, DisenoModelo,
    TipoCampo, ResultadoGeneracion, ResultadoValidacion
)


class TestTipos:
    def test_campo_spec_alfanumerico(self):
        campo = CampoSpec(
            nombre="nif",
            posicion=(9, 17),
            tipo=TipoCampo.ALFANUMERICO,
            fuente="nif_declarante"
        )
        assert campo.longitud == 9
        assert campo.tipo == TipoCampo.ALFANUMERICO

    def test_campo_spec_numerico_con_decimales(self):
        campo = CampoSpec(
            nombre="casilla_01",
            posicion=(68, 85),
            tipo=TipoCampo.NUMERICO_SIGNO,
            decimales=2,
            fuente="casillas.01"
        )
        assert campo.longitud == 18
        assert campo.decimales == 2

    def test_campo_spec_valor_fijo(self):
        campo = CampoSpec(
            nombre="tipo_registro",
            posicion=(1, 1),
            tipo=TipoCampo.ALFANUMERICO,
            valor_fijo="1"
        )
        assert campo.valor_fijo == "1"
        assert campo.fuente is None

    def test_registro_spec(self):
        campos = [
            CampoSpec(nombre="tipo", posicion=(1, 1), tipo=TipoCampo.ALFANUMERICO, valor_fijo="1"),
            CampoSpec(nombre="modelo", posicion=(2, 4), tipo=TipoCampo.NUMERICO, valor_fijo="303"),
        ]
        registro = RegistroSpec(tipo="cabecera", campos=campos)
        assert registro.tipo == "cabecera"
        assert len(registro.campos) == 2

    def test_registro_spec_repetible(self):
        registro = RegistroSpec(tipo="declarado", campos=[], repetible=True)
        assert registro.repetible is True

    def test_validacion_spec(self):
        val = ValidacionSpec(
            regla="casilla_27 == casilla_01 + casilla_03",
            nivel="error",
            mensaje="IVA devengado no cuadra"
        )
        assert val.nivel == "error"

    def test_diseno_modelo(self):
        diseno = DisenoModelo(
            modelo="303",
            version="2025",
            tipo_formato="posicional",
            longitud_registro=500,
            registros=[],
            validaciones=[]
        )
        assert diseno.modelo == "303"
        assert diseno.tipo_formato == "posicional"

    def test_resultado_generacion(self):
        res = ResultadoGeneracion(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            contenido="1303202500000...",
            formato="posicional",
            nombre_fichero="B12345678_2025_1T.303"
        )
        assert res.nombre_fichero == "B12345678_2025_1T.303"

    def test_resultado_validacion_ok(self):
        res = ResultadoValidacion(valido=True, errores=[], advertencias=[])
        assert res.valido is True

    def test_resultado_validacion_con_errores(self):
        res = ResultadoValidacion(
            valido=False,
            errores=["Casilla 27 no cuadra"],
            advertencias=["Casilla 78 vacia"]
        )
        assert not res.valido
        assert len(res.errores) == 1
