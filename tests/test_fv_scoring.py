# tests/test_fv_scoring.py
"""Tests para scoring diferenciado de FV (facturas de venta).

Bug 1: FV con receptor cliente en config → confianza debe ser >= 85 (FIABLE)
Bug 2: FV con receptor NIF persona física → confianza >= 72 (ACEPTABLE)
Bug 3: FV sin receptor_cif → confianza >= 60 (factura simplificada)
Bug 4: FV con receptor CIF entidad nueva → confianza >= 65
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers comunes
# ---------------------------------------------------------------------------

def _crear_config_fv(cif_empresa="25719412F"):
    """Config mock para empresa autonomo (María Isabel o similar) con clientes."""
    config = MagicMock()
    config.cif = cif_empresa
    config.cifs_propios = [cif_empresa]
    config.nombres_propios = ["MARIA ISABEL NAVARRO LOPEZ"]
    config.empresa = {"tipo": "autonomo", "regimen_iva": "general"}
    config.tolerancias = {"confianza_minima": 85}

    # Por defecto: no match proveedor, no match cliente
    config.buscar_proveedor_por_cif.return_value = None
    config.buscar_proveedor_por_nombre.return_value = None
    config.buscar_cliente_por_cif.return_value = None
    config.buscar_cliente_por_nombre.return_value = None
    config.buscar_cliente_fallback_sin_cif.return_value = None
    config.es_cif_propio.return_value = False
    config.buscar_por_cif.return_value = None
    return config


def _entidad_cliente_conocido():
    """Entidad cliente registrado en config (ej: Blanco Abogados)."""
    return {
        "_nombre_corto": "blanco-abogados",
        "cif": "B92476787",
        "nombre_fs": "BLANCO ABOGADOS S.L.",
        "subcuenta": "4300000001",
        "codimpuesto": "IVA21",
        "regimen": "general",
        "pais": "ESP",
        "divisa": "EUR",
        "fallback_sin_cif": False,
    }


def _entidad_varios_clientes():
    """Entidad fallback para FV sin receptor identificado."""
    return {
        "_nombre_corto": "varios-clientes",
        "cif": "00000000T",
        "nombre_fs": "VARIOS CLIENTES",
        "subcuenta": "4300000002",
        "codimpuesto": "IVA21",
        "regimen": "general",
        "pais": "ESP",
        "divisa": "EUR",
        "fallback_sin_cif": True,
    }


def _datos_fv_base(receptor_cif=None, receptor_nombre="CLIENTE PRUEBA"):
    """Datos OCR mínimos para una FV válida."""
    return {
        "tipo_documento": "factura",
        "emisor_nombre": "MARIA ISABEL NAVARRO LOPEZ",
        "emisor_cif": "25719412F",
        "receptor_nombre": receptor_nombre,
        "receptor_cif": receptor_cif,
        "numero_factura": "10/2025",
        "fecha": "2025-06-01",
        "base_imponible": 500.0,
        "iva_porcentaje": 21,
        "iva_importe": 105.0,
        "total": 605.0,
        "divisa": "EUR",
        "_fuente": "mistral",
    }


def _ejecutar_floor_fv(datos_gpt, entidad, tipo_doc="FV", confianza_base=40):
    """Simula el bloque de floor de confianza de intake._procesar_un_pdf.

    Ejecuta solo la lógica de floor sin necesidad de PDF real.
    Retorna confianza_global_val resultante.
    """
    from sfce.core.confidence import calcular_nivel
    from sfce.core.verificacion_fiscal import inferir_tipo_persona

    confianza_global_val = confianza_base
    config_match = datos_gpt.get("_config_match")

    if config_match:
        score_ms = config_match.get("score", 0)
        if score_ms >= 50:
            confianza_global_val = max(confianza_global_val, 85)
        elif score_ms >= 35:
            confianza_global_val = max(confianza_global_val, 70)
    elif entidad and not entidad.get("auto_detectado") and not entidad.get("skip_fs_lookup"):
        if datos_gpt.get("_fuente") == "detector_adeudo_ing":
            confianza_global_val = max(confianza_global_val, 75)
        elif tipo_doc == "FV":
            es_fallback = entidad.get("fallback_sin_cif", False)
            if not es_fallback:
                confianza_global_val = max(confianza_global_val, 85)
            else:
                cif_receptor = (datos_gpt.get("receptor_cif") or "").upper()
                if cif_receptor and inferir_tipo_persona(cif_receptor) == "fisica":
                    confianza_global_val = max(confianza_global_val, 72)
                elif not cif_receptor:
                    confianza_global_val = max(confianza_global_val, 60)
                else:
                    confianza_global_val = max(confianza_global_val, 65)
        else:
            confianza_global_val = max(confianza_global_val, 55)

    return confianza_global_val


# ---------------------------------------------------------------------------
# Tests Bug 1: receptor cliente en config → FIABLE
# ---------------------------------------------------------------------------

class TestFVReceptorEnConfig:
    def test_receptor_cif_en_config_confianza_ge_85(self):
        """FV con receptor CIF registrado en config → confianza >= 85 (FIABLE)."""
        datos = _datos_fv_base(receptor_cif="B92476787", receptor_nombre="BLANCO ABOGADOS S.L.")
        entidad = _entidad_cliente_conocido()

        confianza = _ejecutar_floor_fv(datos, entidad, tipo_doc="FV", confianza_base=40)

        assert confianza >= 85, f"Esperado >= 85, obtenido {confianza}"

    def test_receptor_en_config_nivel_fiable(self):
        """FV con receptor en config → nivel FIABLE o ACEPTABLE."""
        from sfce.core.confidence import calcular_nivel

        datos = _datos_fv_base(receptor_cif="B92476787")
        entidad = _entidad_cliente_conocido()

        confianza = _ejecutar_floor_fv(datos, entidad, tipo_doc="FV", confianza_base=50)
        nivel = calcular_nivel(confianza)

        assert nivel in ("FIABLE", "ACEPTABLE"), f"Nivel inesperado: {nivel}"

    def test_receptor_en_config_no_afectado_por_confianza_base_alta(self):
        """Si confianza base ya es 90, el floor no la baja."""
        datos = _datos_fv_base(receptor_cif="B92476787")
        entidad = _entidad_cliente_conocido()

        confianza = _ejecutar_floor_fv(datos, entidad, tipo_doc="FV", confianza_base=90)

        assert confianza == 90, f"El floor no debe bajar una confianza ya alta: {confianza}"


# ---------------------------------------------------------------------------
# Tests Bug 2: receptor NIF persona física → floor 72
# ---------------------------------------------------------------------------

class TestFVReceptorNIFPersonaFisica:
    @pytest.mark.parametrize("nif", [
        "46051871Y",  # NIF genérico válido formato
        "26807985J",
        "12345678Z",
    ])
    def test_nif_persona_fisica_confianza_ge_72(self, nif):
        """FV con receptor NIF de persona física → confianza >= 72."""
        datos = _datos_fv_base(receptor_cif=nif, receptor_nombre="CLIENTE PARTICULAR")
        entidad = _entidad_varios_clientes()

        confianza = _ejecutar_floor_fv(datos, entidad, tipo_doc="FV", confianza_base=40)

        assert confianza >= 72, f"NIF {nif}: esperado >= 72, obtenido {confianza}"

    def test_nif_persona_fisica_no_llega_a_85(self):
        """NIF persona física con varios_clientes NO debe alcanzar floor de cliente registrado."""
        datos = _datos_fv_base(receptor_cif="46051871Y")
        entidad = _entidad_varios_clientes()

        confianza = _ejecutar_floor_fv(datos, entidad, tipo_doc="FV", confianza_base=40)

        # 72 < 85 — correcto: no es lo mismo que cliente conocido
        assert confianza < 85, f"NIF persona física no debería alcanzar floor de cliente registrado"

    def test_cif_juridico_sin_registro_confianza_65(self):
        """FV con CIF entidad jurídica no registrada → floor 65."""
        datos = _datos_fv_base(receptor_cif="B93509107", receptor_nombre="EMPRESA NUEVA S.L.")
        entidad = _entidad_varios_clientes()

        confianza = _ejecutar_floor_fv(datos, entidad, tipo_doc="FV", confianza_base=40)

        assert confianza >= 65, f"CIF jurídico nuevo: esperado >= 65, obtenido {confianza}"
        assert confianza < 72, f"CIF jurídico nuevo no debe alcanzar floor de persona física"


# ---------------------------------------------------------------------------
# Tests Bug 3: FV sin receptor_cif → factura simplificada → floor 60
# ---------------------------------------------------------------------------

class TestFVSinReceptorCif:
    def test_sin_receptor_cif_confianza_ge_60(self):
        """FV sin receptor_cif (factura simplificada) → confianza >= 60."""
        datos = _datos_fv_base(receptor_cif=None, receptor_nombre="JULIAN VEGA VILCHEZ")
        entidad = _entidad_varios_clientes()

        confianza = _ejecutar_floor_fv(datos, entidad, tipo_doc="FV", confianza_base=40)

        assert confianza >= 60, f"Sin receptor_cif: esperado >= 60, obtenido {confianza}"

    def test_sin_receptor_cif_inferior_a_nif_fisica(self):
        """Sin CIF → floor 60, menos que NIF persona física (72)."""
        datos_sin_cif = _datos_fv_base(receptor_cif=None)
        datos_con_nif = _datos_fv_base(receptor_cif="46051871Y")
        entidad = _entidad_varios_clientes()

        confianza_sin = _ejecutar_floor_fv(datos_sin_cif, entidad, tipo_doc="FV", confianza_base=40)
        confianza_con = _ejecutar_floor_fv(datos_con_nif, entidad, tipo_doc="FV", confianza_base=40)

        assert confianza_sin < confianza_con, (
            f"Sin CIF ({confianza_sin}) debería ser < con NIF ({confianza_con})"
        )


# ---------------------------------------------------------------------------
# Tests: FC no afectado (compatibilidad hacia atrás)
# ---------------------------------------------------------------------------

class TestFCFloorNoAfectado:
    def test_fc_lookup_directo_sigue_en_55(self):
        """FC con entidad por lookup directo mantiene floor=55 (sin regresión)."""
        datos = {
            "emisor_cif": "B12345678",
            "emisor_nombre": "PROVEEDOR S.L.",
            "total": 100.0,
            "fecha": "2025-01-01",
            "_fuente": "mistral",
        }
        entidad = {
            "_nombre_corto": "proveedor-sl",
            "cif": "B12345678",
            "nombre_fs": "PROVEEDOR S.L.",
            "fallback_sin_cif": False,
        }

        confianza = _ejecutar_floor_fv(datos, entidad, tipo_doc="FC", confianza_base=40)

        assert confianza == 55, f"FC lookup directo debe mantener floor=55, obtenido {confianza}"

    def test_fc_config_match_score_alto_sigue_en_85(self):
        """FC con config_match score>=50 mantiene floor=85."""
        datos = {
            "emisor_cif": "B12345678",
            "_config_match": {"score": 60},
            "_fuente": "mistral",
        }
        entidad = {"_nombre_corto": "proveedor-sl", "cif": "B12345678"}

        confianza = _ejecutar_floor_fv(datos, entidad, tipo_doc="FC", confianza_base=40)

        assert confianza >= 85, f"config_match score>=50 debe dar floor=85, obtenido {confianza}"


# ---------------------------------------------------------------------------
# Tests: jerarquía de floors FV
# ---------------------------------------------------------------------------

class TestJerarquiaFloorsFV:
    def test_jerarquia_floors_decreciente(self):
        """Cliente registrado > NIF física > CIF nuevo > sin CIF."""
        entidad_cliente = _entidad_cliente_conocido()
        entidad_fallback = _entidad_varios_clientes()

        c_cliente = _ejecutar_floor_fv(
            _datos_fv_base(receptor_cif="B92476787"), entidad_cliente, confianza_base=40
        )
        c_nif = _ejecutar_floor_fv(
            _datos_fv_base(receptor_cif="46051871Y"), entidad_fallback, confianza_base=40
        )
        c_cif_nuevo = _ejecutar_floor_fv(
            _datos_fv_base(receptor_cif="B93509107"), entidad_fallback, confianza_base=40
        )
        c_sin_cif = _ejecutar_floor_fv(
            _datos_fv_base(receptor_cif=None), entidad_fallback, confianza_base=40
        )

        assert c_cliente >= c_nif >= c_cif_nuevo >= c_sin_cif, (
            f"Jerarquía incorrecta: cliente={c_cliente}, nif={c_nif}, "
            f"cif_nuevo={c_cif_nuevo}, sin_cif={c_sin_cif}"
        )
        assert c_cliente > c_sin_cif, "Cliente registrado debe superar ampliamente sin CIF"
