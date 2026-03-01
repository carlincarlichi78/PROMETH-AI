"""Tests para migración 013: config_procesamiento_empresa + slug + ruta_disco + cola_id."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool


def _engine_con_migracion():
    from sfce.db.migraciones.migracion_013 import ejecutar_migracion
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Crear sólo las tablas base sin resolver todas las FK (SQLite no las valida)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gestorias (id INTEGER PRIMARY KEY, nombre TEXT)
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY,
                cif TEXT NOT NULL,
                nombre TEXT NOT NULL,
                forma_juridica TEXT NOT NULL DEFAULT 'sl',
                territorio TEXT NOT NULL DEFAULT 'peninsula',
                regimen_iva TEXT NOT NULL DEFAULT 'general',
                activa INTEGER DEFAULT 1,
                gestoria_id INTEGER,
                fecha_alta TEXT,
                config_extra TEXT,
                estado_onboarding TEXT DEFAULT 'configurada'
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS asientos (id INTEGER PRIMARY KEY)
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS documentos (
                id INTEGER PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                tipo_doc TEXT NOT NULL,
                ruta_pdf TEXT,
                hash_pdf TEXT,
                estado TEXT DEFAULT 'pendiente',
                fecha_proceso TEXT
            )
        """))
    ejecutar_migracion(engine)
    return engine


def test_tabla_config_procesamiento_existe():
    """La migración crea la tabla config_procesamiento_empresa."""
    engine = _engine_con_migracion()
    inspector = inspect(engine)
    assert "config_procesamiento_empresa" in inspector.get_table_names()

    cols = {c["name"] for c in inspector.get_columns("config_procesamiento_empresa")}
    assert "empresa_id" in cols
    assert "modo" in cols
    assert "schedule_minutos" in cols
    assert "ocr_previo" in cols
    assert "ultimo_pipeline" in cols
    assert "notif_calidad_cliente" in cols
    assert "notif_contable_gestor" in cols


def test_empresa_tiene_campo_slug():
    """Empresa tiene campo slug tras la migración."""
    engine = _engine_con_migracion()
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("empresas")}
    assert "slug" in cols


def test_documento_tiene_campos_nuevos():
    """Documento tiene ruta_disco y cola_id tras la migración."""
    engine = _engine_con_migracion()
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("documentos")}
    assert "ruta_disco" in cols
    assert "cola_id" in cols


def test_migracion_idempotente():
    """Ejecutar dos veces no lanza error."""
    engine = _engine_con_migracion()
    from sfce.db.migraciones.migracion_013 import ejecutar_migracion
    ejecutar_migracion(engine)  # segunda vez sin error
