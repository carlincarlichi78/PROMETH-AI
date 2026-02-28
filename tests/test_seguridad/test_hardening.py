"""Tests de seguridad: JWT fail-hard y CORS restrictivo."""
import importlib.util
import sys
import pytest


def _cargar_auth_module():
    """Carga sfce.api.auth directamente sin pasar por sfce/api/__init__.py."""
    import pathlib
    ruta = pathlib.Path(__file__).parent.parent.parent / "sfce" / "api" / "auth.py"
    spec = importlib.util.spec_from_file_location("sfce.api.auth", ruta)
    mod = importlib.util.module_from_spec(spec)
    # Asegurar que los imports del módulo funcionan
    for nombre in ("sfce", "sfce.api", "sfce.db", "sfce.db.modelos_auth"):
        if nombre not in sys.modules:
            sys.modules[nombre] = type(sys)("sfce")
    spec.loader.exec_module(mod)
    return mod


def test_jwt_secret_falla_sin_variable(monkeypatch):
    """El módulo debe fallar si SFCE_JWT_SECRET no está en el entorno."""
    monkeypatch.delenv("SFCE_JWT_SECRET", raising=False)
    import sfce.api.auth as auth_module
    # Resetear el estado interno del módulo
    auth_module._JWT_SECRET = None
    with pytest.raises(RuntimeError, match="SFCE_JWT_SECRET"):
        auth_module._validar_config_seguridad()


def test_jwt_secret_ok_con_variable(monkeypatch):
    """No debe lanzar error si SFCE_JWT_SECRET está configurado."""
    monkeypatch.setenv("SFCE_JWT_SECRET", "a" * 32)
    import sfce.api.auth as auth_module
    auth_module._JWT_SECRET = None  # reset para test limpio
    auth_module._validar_config_seguridad()  # no debe lanzar


def test_cors_origins_desde_env(monkeypatch):
    """CORS debe usar los orígenes del env, no '*'."""
    monkeypatch.setenv("SFCE_CORS_ORIGINS", "https://app.spice.es,https://staging.spice.es")
    from sfce.api.app import _leer_cors_origins
    origins = _leer_cors_origins()
    assert "https://app.spice.es" in origins
    assert "https://staging.spice.es" in origins
    assert "*" not in origins


def test_cors_origins_default_dev(monkeypatch):
    """En ausencia de env, CORS solo permite localhost (desarrollo)."""
    monkeypatch.delenv("SFCE_CORS_ORIGINS", raising=False)
    from sfce.api.app import _leer_cors_origins
    origins = _leer_cors_origins()
    assert any("localhost" in o for o in origins)
    assert "*" not in origins
