import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from sfce.core.onboarding.perfil_empresa import PerfilEmpresa
from sfce.core.onboarding.motor_creacion import MotorCreacion, ResultadoCreacion


@pytest.fixture
def perfil_sl():
    p = PerfilEmpresa(
        nif="B12345678",
        nombre="Talleres García SL",
        forma_juridica="sl",
        territorio="peninsula",
        regimen_iva="general",
    )
    p.documentos_procesados = ["censo_036_037", "libro_facturas_emitidas",
                                "libro_facturas_recibidas", "sumas_y_saldos"]
    p.proveedores_habituales = [
        {"cif": "B87654321", "nombre": "Proveedor SL",
         "tipo": "proveedor", "importe_habitual": 500}
    ]
    p.sumas_saldos = {
        "1000000000": {"deudor": 0, "acreedor": 10000},
        "4300000000": {"deudor": 5000, "acreedor": 0},
    }
    return p


def test_motor_genera_slug_correcto(perfil_sl, tmp_path):
    motor = MotorCreacion(base_clientes=tmp_path)
    slug = motor._generar_slug(perfil_sl)
    assert "B12345678" in slug or "talleres" in slug.lower()
    assert " " not in slug


def test_motor_crea_carpetas_en_disco(perfil_sl, tmp_path):
    motor = MotorCreacion(base_clientes=tmp_path)
    slug = motor._generar_slug(perfil_sl)
    motor._crear_estructura_disco(slug, perfil_sl)
    base = tmp_path / slug
    assert base.is_dir()
    assert (base / "inbox").is_dir()
    assert (base / "procesados").is_dir()
    assert (base / "cuarentena").is_dir()
    assert (base / "modelos_fiscales").is_dir()
    assert (base / "onboarding").is_dir()


def test_motor_genera_config_yaml(perfil_sl, tmp_path):
    motor = MotorCreacion(base_clientes=tmp_path)
    slug = motor._generar_slug(perfil_sl)
    motor._crear_estructura_disco(slug, perfil_sl)
    motor._generar_config_yaml(slug, perfil_sl, idempresa_fs=7, codejercicio="0007")
    config_path = tmp_path / slug / "config.yaml"
    assert config_path.exists()
    contenido = config_path.read_text(encoding="utf-8")
    assert "B12345678" in contenido
    assert "idempresa" in contenido


def test_motor_selecciona_pgc_correcto():
    motor = MotorCreacion(base_clientes=Path("/tmp"))
    assert motor._tipo_pgc("sl") == "general"
    assert motor._tipo_pgc("asociacion") == "esfl"
    assert motor._tipo_pgc("fundacion") == "esfl"
    assert motor._tipo_pgc("coop") == "cooperativas"
    assert motor._tipo_pgc("comunidad") == "pymes"
    assert motor._tipo_pgc("autonomo") == "pymes"


def test_motor_verifica_cuota_plan():
    motor = MotorCreacion(base_clientes=Path("/tmp"))
    gestoria_mock = MagicMock()
    gestoria_mock.limite_empresas = 10
    # 8 actuales + 5 nuevas = 13 > 10 → False
    assert motor.verificar_cuota(gestoria_mock, empresas_actuales=8,
                                  total_lote=5) is False
    # 4 actuales + 5 nuevas = 9 <= 10 → True
    assert motor.verificar_cuota(gestoria_mock, empresas_actuales=4,
                                  total_lote=5) is True
    # Sin límite → True
    gestoria_sin_limite = MagicMock()
    gestoria_sin_limite.limite_empresas = None
    assert motor.verificar_cuota(gestoria_sin_limite,
                                  empresas_actuales=100, total_lote=50) is True
