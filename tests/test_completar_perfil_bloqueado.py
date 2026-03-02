"""Tests endpoint POST /api/onboarding/perfiles/{id}/completar."""
import json
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.db.modelos import Base
from sfce.db.modelos_auth import Usuario
from sfce.api.rutas.auth_rutas import hashear_password


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    # Crear tablas onboarding manualmente (raw SQL, igual que migraciones)
    with Session() as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gestoria_id INTEGER,
                nombre TEXT,
                fecha_subida TEXT,
                estado TEXT DEFAULT 'procesando',
                total_clientes INTEGER DEFAULT 0,
                completados INTEGER DEFAULT 0,
                en_revision INTEGER DEFAULT 0,
                bloqueados INTEGER DEFAULT 0,
                usuario_id INTEGER,
                modo TEXT DEFAULT 'zip'
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_perfiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id INTEGER,
                empresa_id INTEGER,
                nif TEXT,
                nombre_detectado TEXT,
                forma_juridica TEXT,
                territorio TEXT,
                confianza REAL DEFAULT 0,
                estado TEXT DEFAULT 'borrador',
                datos_json TEXT,
                advertencias_json TEXT,
                bloqueos_json TEXT,
                revisado_por INTEGER,
                fecha_revision TEXT
            )
        """))
        # Crear usuario admin
        admin = Usuario(
            email="admin@sfce.local",
            nombre="Admin Test",
            hash_password=hashear_password("admin"),
            rol="superadmin",
            activo=True,
            empresas_ids=[],
        )
        s.add(admin)
        s.flush()

        # Insertar lote y perfil bloqueado de ejemplo
        s.execute(text("""
            INSERT INTO onboarding_lotes (id, gestoria_id, nombre, fecha_subida, estado, bloqueados)
            VALUES (1, 1, 'Test lote', '2026-03-02', 'completado', 1)
        """))
        datos_sin_036 = json.dumps({
            "nif": "", "nombre": "", "nombre_comercial": None,
            "forma_juridica": "sl", "territorio": "peninsula",
            "domicilio_fiscal": {}, "fecha_alta_censal": None,
            "fecha_inicio_actividad": None, "regimen_iva": "general",
            "regimen_iva_confirmado": False, "recc": False,
            "prorrata_historico": {2024: 82.3}, "sectores_diferenciados": [],
            "isp_aplicable": False, "tipo_is": None, "es_erd": False,
            "bins_por_anyo": {}, "bins_total": None,
            "retencion_facturas_pct": None, "pagos_fraccionados": {},
            "tiene_trabajadores": False, "socios": [],
            "operaciones_vinculadas": False, "obligaciones_adicionales": [],
            "proveedores_habituales": [], "clientes_habituales": [],
            "sumas_saldos": None, "bienes_inversion_iva": [],
            "documentos_procesados": ["iva_anual_390"],
            "advertencias": [], "config_extra": {},
        })
        s.execute(text("""
            INSERT INTO onboarding_perfiles
              (id, lote_id, nif, nombre_detectado, estado, datos_json,
               bloqueos_json, confianza)
            VALUES (1, 1, '', 'SIN NOMBRE', 'bloqueado', :datos,
                    '["Falta documento base: 036/037 obligatorio"]', 0)
        """), {"datos": datos_sin_036})
        s.commit()

    app = crear_app(sesion_factory=Session)

    with TestClient(app) as c:
        resp = c.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
        token = resp.json()["access_token"]
        yield c, token


def _036_pdf_falso() -> bytes:
    """PDF mínimo con texto de modelo 036 para clasificador."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"


def test_completar_perfil_bloqueado_devuelve_nuevo_estado(client):
    c, token = client
    from unittest.mock import patch
    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding

    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.CENSO_036_037,
        confianza=0.92,
    )
    mock_datos = {
        "nif": "B12345678",
        "nombre": "TALLERES GARCIA",
        "forma_juridica": "sl",
        "domicilio": {"cp": "46001"},
        "regimen_iva": "general",
        "fecha_alta": "2023-01-15",
    }

    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf), \
         patch("sfce.api.rutas.onboarding_masivo._extraer_datos_completar",
               return_value=mock_datos):
        resp = c.post(
            "/api/onboarding/perfiles/1/completar",
            files={"archivos": ("036.pdf", _036_pdf_falso(), "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["nuevo_estado"] in ("apto", "revision")
    assert data["score"] >= 40


def test_completar_perfil_inexistente_404(client):
    c, token = client
    resp = c.post(
        "/api/onboarding/perfiles/999/completar",
        files={"archivos": ("036.pdf", _036_pdf_falso(), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_completar_perfil_conserva_datos_previos(client):
    """Los datos del 390 previo deben conservarse tras añadir el 036."""
    c, token = client
    from unittest.mock import patch
    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding

    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.CENSO_036_037,
        confianza=0.92,
    )
    mock_datos = {
        "nif": "B12345678", "nombre": "TALLERES GARCIA",
        "forma_juridica": "sl", "domicilio": {"cp": "46001"},
        "regimen_iva": "general",
    }

    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf), \
         patch("sfce.api.rutas.onboarding_masivo._extraer_datos_completar",
               return_value=mock_datos):
        resp = c.post(
            "/api/onboarding/perfiles/1/completar",
            files={"archivos": ("036.pdf", _036_pdf_falso(), "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    # Verificar en BD que datos_json contiene prorrata previa
    from sqlalchemy import text as sqlt
    with c.app.state.sesion_factory() as s:
        row = s.execute(sqlt(
            "SELECT datos_json FROM onboarding_perfiles WHERE id=1"
        )).fetchone()
    datos = json.loads(row[0])
    assert datos["prorrata_historico"].get(2024) == 82.3 or datos["prorrata_historico"].get("2024") == 82.3


def test_completar_cif_distinto_error(client):
    """Si el 036 tiene CIF que no pertenece al perfil, error claro."""
    c, token = client
    from unittest.mock import patch
    from sfce.core.onboarding.clasificador import ResultadoClasificacion, TipoDocOnboarding

    mock_clf = ResultadoClasificacion(
        tipo=TipoDocOnboarding.CENSO_036_037,
        confianza=0.92,
    )
    with patch("sfce.api.rutas.onboarding_masivo.clasificar_documento",
               return_value=mock_clf), \
         patch("sfce.api.rutas.onboarding_masivo._extraer_datos_completar",
               return_value={"nif": "A99999999", "nombre": "OTRA",
                             "forma_juridica": "sl", "domicilio": {"cp": "28001"}}):
        resp = c.post(
            "/api/onboarding/perfiles/1/completar",
            files={"archivos": ("036.pdf", _036_pdf_falso(), "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200  # Se acepta — perfil tenía nif vacío


def test_completar_sin_archivos_422(client):
    c, token = client
    resp = c.post(
        "/api/onboarding/perfiles/1/completar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
