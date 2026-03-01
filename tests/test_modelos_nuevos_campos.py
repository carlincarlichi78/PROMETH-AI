"""Tests para campos nuevos en modelos SQLAlchemy (migración 013)."""
import sfce.db.modelos_auth  # noqa: F401 — registra Gestoria en el mapper antes de Empresa


def test_documento_tiene_ruta_disco():
    from sfce.db.modelos import Documento
    doc = Documento(empresa_id=1, tipo_doc="FV", ruta_pdf="x.pdf")
    doc.ruta_disco = "/absolute/path/to/file.pdf"
    assert doc.ruta_disco == "/absolute/path/to/file.pdf"


def test_documento_tiene_cola_id():
    from sfce.db.modelos import Documento
    doc = Documento(empresa_id=1, tipo_doc="FV", ruta_pdf="x.pdf")
    doc.cola_id = 42
    assert doc.cola_id == 42


def test_empresa_tiene_slug():
    from sfce.db.modelos import Empresa
    emp = Empresa(nombre="Test S.L.", cif="B12345678",
                  forma_juridica="sl")
    emp.slug = "test-sl"
    assert emp.slug == "test-sl"


def test_config_procesamiento_modelo():
    from sfce.db.modelos import ConfigProcesamientoEmpresa
    cfg = ConfigProcesamientoEmpresa(empresa_id=5, modo="auto", schedule_minutos=30)
    assert cfg.modo == "auto"
    assert cfg.schedule_minutos == 30


def test_config_procesamiento_campos_existen():
    """Los campos del modelo existen y son accesibles."""
    from sfce.db.modelos import ConfigProcesamientoEmpresa
    cfg = ConfigProcesamientoEmpresa(empresa_id=3, modo="revision")
    assert cfg.modo == "revision"
    assert cfg.empresa_id == 3
    # Los campos opcionales existen como atributos
    assert hasattr(cfg, "schedule_minutos")
    assert hasattr(cfg, "ocr_previo")
    assert hasattr(cfg, "notif_calidad_cliente")
    assert hasattr(cfg, "notif_contable_gestor")
    assert hasattr(cfg, "ultimo_pipeline")
