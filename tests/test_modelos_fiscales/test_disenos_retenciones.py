"""
Tests de disenos de registro para modelos fiscales de retenciones e IRPF.
Verifica estructura YAML: carga, campos, posiciones sin solapamiento, registros repetibles.
"""

import pytest
from sfce.modelos_fiscales.cargador import CargadorDisenos


class TestDisenosRetenciones:
    @pytest.fixture
    def cargador(self):
        return CargadorDisenos()

    @pytest.mark.parametrize("modelo", ["111", "190", "115", "180", "123", "193", "130", "131"])
    def test_carga_sin_error(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert diseno.modelo == modelo

    @pytest.mark.parametrize("modelo", ["111", "190", "115", "180", "123", "193", "130", "131"])
    def test_tiene_registros(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert len(diseno.registros) >= 1

    @pytest.mark.parametrize("modelo", ["111", "190", "115", "180", "123", "193", "130", "131"])
    def test_campos_no_se_solapan(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            posiciones = sorted(campo.posicion for campo in registro.campos)
            for i in range(1, len(posiciones)):
                assert posiciones[i][0] > posiciones[i-1][1], \
                    f"Solapamiento en {modelo} registro '{registro.tipo}': {posiciones[i-1]} y {posiciones[i]}"

    @pytest.mark.parametrize("modelo", ["190", "180", "193"])
    def test_modelos_anuales_tienen_repetibles(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        repetibles = [r for r in diseno.registros if r.repetible]
        assert len(repetibles) >= 1, f"{modelo} debe tener al menos un registro repetible"

    @pytest.mark.parametrize("modelo", ["111", "115", "123", "130", "131"])
    def test_modelos_trimestrales_no_tienen_repetibles(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        repetibles = [r for r in diseno.registros if r.repetible]
        assert len(repetibles) == 0, f"{modelo} es trimestral y no deberia tener registros repetibles"

    def test_111_tiene_casilla_28(self, cargador):
        diseno = cargador.cargar("111")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_28" in nombres

    def test_111_tiene_casilla_30(self, cargador):
        diseno = cargador.cargar("111")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_30" in nombres

    def test_130_tiene_rendimiento_neto(self, cargador):
        diseno = cargador.cargar("130")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_03" in nombres

    def test_130_tiene_casilla_19(self, cargador):
        """Casilla 19 es el resultado final de liquidacion del modelo 130."""
        diseno = cargador.cargar("130")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_19" in nombres

    def test_131_tiene_casilla_12_total(self, cargador):
        """Casilla 12 es el total de cuotas de actividades en modulos."""
        diseno = cargador.cargar("131")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_12" in nombres

    def test_190_tiene_tipo_declarante(self, cargador):
        diseno = cargador.cargar("190")
        tipos = [r.tipo for r in diseno.registros]
        assert "declarante" in tipos

    def test_190_tiene_tipo_perceptor(self, cargador):
        diseno = cargador.cargar("190")
        tipos = [r.tipo for r in diseno.registros]
        assert "perceptor" in tipos

    def test_180_tiene_tipo_arrendador(self, cargador):
        diseno = cargador.cargar("180")
        tipos = [r.tipo for r in diseno.registros]
        assert "arrendador" in tipos

    def test_193_tiene_tipo_perceptor(self, cargador):
        diseno = cargador.cargar("193")
        tipos = [r.tipo for r in diseno.registros]
        assert "perceptor" in tipos

    @pytest.mark.parametrize("modelo", ["111", "190", "115", "180", "123", "193", "130", "131"])
    def test_longitud_registro_definida(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert diseno.longitud_registro > 0

    @pytest.mark.parametrize("modelo", ["111", "190", "115", "180", "123", "193", "130", "131"])
    def test_version_definida(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert diseno.version is not None

    @pytest.mark.parametrize("modelo", ["111", "190", "115", "180", "123", "193", "130", "131"])
    def test_tiene_validaciones(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert len(diseno.validaciones) >= 1, f"{modelo} debe tener al menos una validacion"

    @pytest.mark.parametrize("modelo", ["111", "190", "115", "180", "123", "193", "130", "131"])
    def test_posiciones_dentro_longitud_registro(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        longitud = diseno.longitud_registro
        for registro in diseno.registros:
            for campo in registro.campos:
                inicio, fin = campo.posicion
                assert fin <= longitud, \
                    f"Campo '{campo.nombre}' en {modelo}: posicion fin {fin} supera longitud {longitud}"

    @pytest.mark.parametrize("modelo", ["111", "190", "115", "180", "123", "193", "130", "131"])
    def test_posiciones_empiezan_en_1(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            primero = min(campo.posicion[0] for campo in registro.campos)
            assert primero == 1, \
                f"Registro '{registro.tipo}' en {modelo}: primer campo empieza en {primero}, debe ser 1"

    @pytest.mark.parametrize("modelo", ["111", "190", "115", "180", "123", "193", "130", "131"])
    def test_campos_tienen_tipo_valido(self, cargador, modelo):
        # El cargador convierte el tipo a TipoCampo (enum), comparar via .value
        tipos_validos = {"alfanumerico", "numerico", "numerico_signo", "fecha", "telefono"}
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            for campo in registro.campos:
                valor_tipo = campo.tipo.value if hasattr(campo.tipo, "value") else campo.tipo
                assert valor_tipo in tipos_validos, \
                    f"Campo '{campo.nombre}' en {modelo}: tipo '{valor_tipo}' no es valido"

    def test_115_tiene_casilla_04_resultado(self, cargador):
        """Modelo 115 tiene casilla 04 como resultado de liquidacion."""
        diseno = cargador.cargar("115")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_04" in nombres

    def test_123_tiene_casilla_04_resultado(self, cargador):
        """Modelo 123 tiene casilla 04 como resultado de liquidacion."""
        diseno = cargador.cargar("123")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_04" in nombres

    def test_180_tiene_referencia_catastral(self, cargador):
        """El registro de arrendador del 180 debe incluir referencia catastral."""
        diseno = cargador.cargar("180")
        arrendador = next(r for r in diseno.registros if r.tipo == "arrendador")
        nombres = {c.nombre for c in arrendador.campos}
        assert "referencia_catastral" in nombres

    def test_190_perceptor_tiene_clave_percepcion(self, cargador):
        """El registro de perceptor del 190 debe incluir clave de percepcion."""
        diseno = cargador.cargar("190")
        perceptor = next(r for r in diseno.registros if r.tipo == "perceptor")
        nombres = {c.nombre for c in perceptor.campos}
        assert "clave_percepcion" in nombres

    def test_193_perceptor_tiene_clave_tipo(self, cargador):
        """El registro de perceptor del 193 debe incluir clave de tipo de rendimiento."""
        diseno = cargador.cargar("193")
        perceptor = next(r for r in diseno.registros if r.tipo == "perceptor")
        nombres = {c.nombre for c in perceptor.campos}
        assert "clave_tipo" in nombres
