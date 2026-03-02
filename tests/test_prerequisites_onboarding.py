"""Tests de prerequisites para onboarding masivo."""
import pytest
from sfce.db.modelos import EstadoOnboarding, Empresa
from sfce.core.tiers import FEATURES_GESTORIA, Tier
from sfce.core.fs_setup import FsSetup


def test_estado_onboarding_tiene_creada_masivo():
    assert EstadoOnboarding.CREADA_MASIVO.value == "creada_masivo"


def test_forma_juridica_acepta_arrendador():
    # forma_juridica es String libre — verificar que config_desde_bd lo mapea
    from sfce.core.config_desde_bd import _FORMA_A_TIPO
    assert "arrendador" in _FORMA_A_TIPO


def test_features_gestoria_tiene_onboarding_masivo():
    assert "onboarding_masivo" in FEATURES_GESTORIA
    assert FEATURES_GESTORIA["onboarding_masivo"] == Tier.PRO


def test_fs_setup_acepta_tipo_pgc():
    setup = FsSetup(base_url="http://fake", token="tok")
    import inspect
    sig = inspect.signature(setup.importar_pgc)
    assert "tipo_pgc" in sig.parameters


def test_config_desde_bd_expone_recc(tmp_path):
    from unittest.mock import MagicMock
    from sfce.core.config_desde_bd import generar_config_desde_bd
    empresa = MagicMock()
    empresa.id = 1
    empresa.cif = "B12345678"
    empresa.nombre = "Test SL"
    empresa.forma_juridica = "sl"
    empresa.territorio = "peninsula"
    empresa.regimen_iva = "general"
    empresa.idempresa_fs = 1
    empresa.codejercicio_fs = "0001"
    empresa.config_extra = {"recc": True, "ejercicio_activo": "2025"}
    empresa.activos = []
    sesion = MagicMock()
    sesion.get.return_value = empresa
    sesion.query.return_value.filter_by.return_value.all.return_value = []
    config = generar_config_desde_bd(1, sesion)
    assert config.data["empresa"].get("recc") is True
