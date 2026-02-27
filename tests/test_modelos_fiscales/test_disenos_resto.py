import pytest
from sfce.modelos_fiscales.cargador import CargadorDisenos


MODELOS_RESTO = ["200", "202", "220", "036", "037", "210", "211", "216", "296", "184", "345", "720", "360", "340", "420", "100"]


class TestDisenosResto:
    @pytest.fixture
    def cargador(self):
        return CargadorDisenos()

    @pytest.mark.parametrize("modelo", MODELOS_RESTO)
    def test_carga_sin_error(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert diseno.modelo == modelo

    @pytest.mark.parametrize("modelo", MODELOS_RESTO)
    def test_tiene_registros(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert len(diseno.registros) >= 1

    @pytest.mark.parametrize("modelo", [m for m in MODELOS_RESTO if m not in ("200", "220")])
    def test_campos_no_se_solapan(self, cargador, modelo):
        """Solo para posicionales (200 y 220 son XML)."""
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            posiciones = sorted(campo.posicion for campo in registro.campos)
            for i in range(1, len(posiciones)):
                if posiciones[i-1][0] == 0:
                    continue  # skip XML fields
                assert posiciones[i][0] > posiciones[i-1][1], \
                    f"Solapamiento en {modelo}: {posiciones[i-1]} y {posiciones[i]}"

    def test_200_es_xml(self, cargador):
        diseno = cargador.cargar("200")
        assert diseno.tipo_formato == "xml"

    def test_220_es_xml(self, cargador):
        diseno = cargador.cargar("220")
        assert diseno.tipo_formato == "xml"

    @pytest.mark.parametrize("modelo", ["296", "184", "345", "720", "360", "340"])
    def test_tiene_registros_repetibles(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        repetibles = [r for r in diseno.registros if r.repetible]
        assert len(repetibles) >= 1, f"{modelo} debe tener registros repetibles"

    def test_420_similar_a_303(self, cargador):
        diseno = cargador.cargar("420")
        assert diseno.tipo_formato == "posicional"
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_01" in nombres

    def test_202_es_posicional(self, cargador):
        diseno = cargador.cargar("202")
        assert diseno.tipo_formato == "posicional"
        assert diseno.longitud_registro == 500

    def test_036_longitud_2000(self, cargador):
        diseno = cargador.cargar("036")
        assert diseno.longitud_registro == 2000

    def test_037_longitud_1000(self, cargador):
        diseno = cargador.cargar("037")
        assert diseno.longitud_registro == 1000

    def test_100_longitud_2000(self, cargador):
        diseno = cargador.cargar("100")
        assert diseno.longitud_registro == 2000

    def test_200_longitud_registro_cero(self, cargador):
        """XML: longitud_registro no aplica, debe ser 0."""
        diseno = cargador.cargar("200")
        assert diseno.longitud_registro == 0

    def test_200_tiene_registro_liquidacion(self, cargador):
        diseno = cargador.cargar("200")
        tipos = {r.tipo for r in diseno.registros}
        assert "liquidacion" in tipos

    def test_200_tiene_casilla_599(self, cargador):
        diseno = cargador.cargar("200")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_599" in nombres

    def test_296_tiene_cabecera_y_declarado(self, cargador):
        diseno = cargador.cargar("296")
        tipos = {r.tipo for r in diseno.registros}
        assert "cabecera" in tipos
        assert "declarado" in tipos

    def test_184_tiene_cabecera_y_miembro(self, cargador):
        diseno = cargador.cargar("184")
        tipos = {r.tipo for r in diseno.registros}
        assert "cabecera" in tipos
        assert "miembro" in tipos

    def test_345_tiene_participe(self, cargador):
        diseno = cargador.cargar("345")
        tipos = {r.tipo for r in diseno.registros}
        assert "participe" in tipos

    def test_720_tiene_bien(self, cargador):
        diseno = cargador.cargar("720")
        tipos = {r.tipo for r in diseno.registros}
        assert "bien" in tipos

    def test_340_tiene_registro_factura(self, cargador):
        diseno = cargador.cargar("340")
        tipos = {r.tipo for r in diseno.registros}
        assert "registro_factura" in tipos

    def test_100_tiene_actividades_economicas(self, cargador):
        diseno = cargador.cargar("100")
        tipos = {r.tipo for r in diseno.registros}
        assert "actividades_economicas" in tipos

    def test_210_tiene_datos_no_residente(self, cargador):
        diseno = cargador.cargar("210")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "nif_no_residente" in nombres
        assert "casilla_04" in nombres

    def test_211_tiene_referencia_catastral(self, cargador):
        diseno = cargador.cargar("211")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "referencia_catastral" in nombres

    def test_216_tiene_num_perceptores(self, cargador):
        diseno = cargador.cargar("216")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_01" in nombres

    def test_360_tiene_registro_factura(self, cargador):
        diseno = cargador.cargar("360")
        tipos = {r.tipo for r in diseno.registros}
        assert "factura" in tipos

    def test_220_tiene_entidad_grupo_repetible(self, cargador):
        diseno = cargador.cargar("220")
        repetibles = [r for r in diseno.registros if r.repetible]
        assert len(repetibles) >= 1

    @pytest.mark.parametrize("modelo", MODELOS_RESTO)
    def test_version_presente(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert diseno.version is not None
        assert len(diseno.version) > 0

    @pytest.mark.parametrize("modelo", MODELOS_RESTO)
    def test_todos_campos_tienen_nombre(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            for campo in registro.campos:
                assert campo.nombre, f"Campo sin nombre en modelo {modelo} registro {registro.tipo}"

    @pytest.mark.parametrize("modelo", MODELOS_RESTO)
    def test_todos_campos_tienen_tipo_valido(self, cargador, modelo):
        from sfce.modelos_fiscales.tipos import TipoCampo
        tipos_validos = {t.value for t in TipoCampo}
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            for campo in registro.campos:
                assert campo.tipo.value in tipos_validos, \
                    f"Tipo invalido '{campo.tipo}' en {modelo}.{campo.nombre}"
