"""Tests de disenos YAML de modelos fiscales de IVA: 303, 390, 349, 347."""
import pytest
from sfce.modelos_fiscales.cargador import CargadorDisenos


class TestDisenosIVA:
    @pytest.fixture
    def cargador(self):
        return CargadorDisenos()

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_carga_sin_error(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert diseno.modelo == modelo

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_tiene_registros(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert len(diseno.registros) >= 1

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_campos_no_se_solapan(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            posiciones = sorted(campo.posicion for campo in registro.campos)
            for i in range(1, len(posiciones)):
                assert posiciones[i][0] > posiciones[i - 1][1], (
                    f"Solapamiento en {modelo} registro '{registro.tipo}': "
                    f"{posiciones[i - 1]} y {posiciones[i]}"
                )

    def test_303_tiene_casillas_principales(self, cargador):
        diseno = cargador.cargar("303")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        for casilla in ["casilla_01", "casilla_03", "casilla_27", "casilla_37", "casilla_45"]:
            assert casilla in nombres, f"Falta {casilla} en modelo 303"

    def test_347_tiene_registro_declarados(self, cargador):
        diseno = cargador.cargar("347")
        tipos = [r.tipo for r in diseno.registros]
        assert "cabecera" in tipos or "tipo1" in tipos

    def test_349_tiene_registro_repetible(self, cargador):
        diseno = cargador.cargar("349")
        repetibles = [r for r in diseno.registros if r.repetible]
        assert len(repetibles) >= 1

    def test_303_tiene_validaciones(self, cargador):
        diseno = cargador.cargar("303")
        assert len(diseno.validaciones) >= 2

    def test_390_longitud_grande(self, cargador):
        diseno = cargador.cargar("390")
        assert diseno.longitud_registro >= 2000

    # --- Tests adicionales de integridad ---

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_version_presente(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert diseno.version, f"Falta version en modelo {modelo}"

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_tipo_formato_posicional(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert diseno.tipo_formato == "posicional"

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_longitud_registro_positiva(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert diseno.longitud_registro > 0, f"Longitud de registro invalida en {modelo}"

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_campos_tienen_tipo_valido(self, cargador, modelo):
        from sfce.modelos_fiscales.tipos import TipoCampo
        tipos_validos = {t.value for t in TipoCampo}
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            for campo in registro.campos:
                assert campo.tipo.value in tipos_validos, (
                    f"Tipo de campo invalido '{campo.tipo}' en {modelo}/{campo.nombre}"
                )

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_posicion_inicio_menor_que_fin(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            for campo in registro.campos:
                inicio, fin = campo.posicion
                assert inicio <= fin, (
                    f"Posicion invalida en {modelo}/{campo.nombre}: inicio {inicio} > fin {fin}"
                )

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_posicion_empieza_en_1(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            posiciones = [c.posicion[0] for c in registro.campos]
            assert min(posiciones) >= 1, (
                f"Posicion < 1 en {modelo} registro '{registro.tipo}'"
            )

    def test_347_tiene_registro_tipo2_repetible(self, cargador):
        diseno = cargador.cargar("347")
        repetibles = [r for r in diseno.registros if r.repetible]
        assert len(repetibles) >= 1, "Modelo 347 debe tener al menos un registro repetible (tipo2)"

    def test_349_tipo2_tiene_campo_clave_operacion(self, cargador):
        diseno = cargador.cargar("349")
        for registro in diseno.registros:
            if registro.repetible:
                nombres = {c.nombre for c in registro.campos}
                assert "clave_operacion" in nombres, (
                    "Registro repetible del 349 debe tener campo clave_operacion"
                )

    def test_347_tipo2_tiene_importes_trimestrales(self, cargador):
        diseno = cargador.cargar("347")
        for registro in diseno.registros:
            if registro.repetible:
                nombres = {c.nombre for c in registro.campos}
                for trimestre in ["importe_1t", "importe_2t", "importe_3t", "importe_4t"]:
                    assert trimestre in nombres, (
                        f"Registro tipo2 del 347 debe tener campo {trimestre}"
                    )

    def test_303_tiene_cuotas_devengadas_y_soportadas(self, cargador):
        diseno = cargador.cargar("303")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_27" in nombres, "303 debe tener casilla_27 (total devengado)"
        assert "casilla_37" in nombres, "303 debe tener casilla_37 (total a deducir)"

    def test_390_tiene_casilla_prorrata(self, cargador):
        diseno = cargador.cargar("390")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_84" in nombres, "390 debe tener casilla_84 (prorrata general)"

    def test_390_tiene_casilla_resultado(self, cargador):
        diseno = cargador.cargar("390")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        assert "casilla_65" in nombres, "390 debe tener casilla_65 (resultado del ejercicio)"

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_validaciones_tienen_regla_y_mensaje(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        for val in diseno.validaciones:
            assert val.regla, f"Validacion sin regla en {modelo}"
            assert val.mensaje, f"Validacion sin mensaje en {modelo}"
            assert val.nivel in ("error", "advertencia"), (
                f"Nivel de validacion invalido '{val.nivel}' en {modelo}"
            )

    def test_349_tiene_registro_no_repetible(self, cargador):
        diseno = cargador.cargar("349")
        no_repetibles = [r for r in diseno.registros if not r.repetible]
        assert len(no_repetibles) >= 1, "349 debe tener al menos un registro cabecera (no repetible)"

    def test_347_tipo1_tiene_num_declarados(self, cargador):
        diseno = cargador.cargar("347")
        for registro in diseno.registros:
            if not registro.repetible:
                nombres = {c.nombre for c in registro.campos}
                assert "num_declarados" in nombres, (
                    "Registro cabecera del 347 debe tener campo num_declarados"
                )
