"""Tests de la API del pipeline (token de servicio + endpoints /api/pipeline/).

Cubre:
- Autenticación: sin token, token inválido, token revocado
- GET /api/pipeline/empresas: scope por gestoría, scope por empresa_ids
- POST /api/pipeline/documentos/subir: happy path, duplicado SHA256, empresa fuera de scope, vacío
- GET /api/pipeline/documentos/pendientes: vacío, con docs, empresa fuera de scope
- GET /api/pipeline/sync-status: contadores correctos, scope vacío
- Admin CRUD tokens: crear, listar, revocar
"""
import hashlib
import io
import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.api.app import crear_app
from sfce.api.auth import hashear_password
from sfce.db.base import Base
from sfce.db.modelos import ColaProcesamiento, Documento, Empresa
from sfce.db.modelos_auth import Gestoria, TokenServicio, Usuario

os.environ["SFCE_JWT_SECRET"] = "a" * 32


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup(tmp_path):
    """BD en memoria con:
    - Gestoría G1 (gestoria_id auto)
    - Gestoría G2
    - Empresa emp1 → G1, Empresa emp2 → G1, Empresa emp3 → G2
    - Token ts_g1: scope gestoria_id=G1 (todas las empresas de G1)
    - Token ts_emp1: scope gestoria_id=G1, empresa_ids=[emp1.id]
    - Token ts_g1_revocado: activo=False
    - Token ts_superadmin: gestoria_id=None (scope global)
    - Usuario superadmin (para crear tokens vía API)
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)

    # Token raws
    raw_g1 = "token_g1_" + "x" * 55
    raw_emp1 = "token_emp1_" + "x" * 53
    raw_revocado = "token_rev_" + "x" * 54
    raw_superadmin = "token_super_" + "x" * 52

    with sf() as s:
        g1 = Gestoria(nombre="G1", email_contacto="g1@test.com")
        g2 = Gestoria(nombre="G2", email_contacto="g2@test.com")
        s.add_all([g1, g2])
        s.flush()

        emp1 = Empresa(cif="B11111111", nombre="Empresa E1", forma_juridica="sl", gestoria_id=g1.id)
        emp2 = Empresa(cif="B22222222", nombre="Empresa E2", forma_juridica="sl", gestoria_id=g1.id)
        emp3 = Empresa(cif="B33333333", nombre="Empresa E3", forma_juridica="sl", gestoria_id=g2.id)
        s.add_all([emp1, emp2, emp3])
        s.flush()

        admin = Usuario(
            email="admin@test.com",
            nombre="Admin Test",
            hash_password=hashear_password("pass"),
            rol="superadmin",
            activo=True,
        )
        s.add(admin)

        # Tokens de servicio
        ts_g1 = TokenServicio(
            nombre="pipeline-g1",
            token_hash=hashlib.sha256(raw_g1.encode()).hexdigest(),
            gestoria_id=g1.id,
            empresa_ids="[]",
            activo=True,
            creado_en="2026-01-01T00:00:00+00:00",
        )
        ts_emp1 = TokenServicio(
            nombre="pipeline-emp1",
            token_hash=hashlib.sha256(raw_emp1.encode()).hexdigest(),
            gestoria_id=g1.id,
            empresa_ids=json.dumps([]),  # se rellenará tras flush
            activo=True,
            creado_en="2026-01-01T00:00:00+00:00",
        )
        ts_revocado = TokenServicio(
            nombre="pipeline-revocado",
            token_hash=hashlib.sha256(raw_revocado.encode()).hexdigest(),
            gestoria_id=g1.id,
            empresa_ids="[]",
            activo=False,
            creado_en="2026-01-01T00:00:00+00:00",
        )
        ts_super = TokenServicio(
            nombre="pipeline-superadmin",
            token_hash=hashlib.sha256(raw_superadmin.encode()).hexdigest(),
            gestoria_id=None,
            empresa_ids="[]",
            activo=True,
            creado_en="2026-01-01T00:00:00+00:00",
        )
        s.add_all([ts_g1, ts_emp1, ts_revocado, ts_super])
        s.commit()

        # Actualizar ts_emp1 con empresa_ids real
        ts_emp1.empresa_ids = json.dumps([emp1.id])
        s.commit()

        ids = {
            "g1": g1.id,
            "g2": g2.id,
            "emp1": emp1.id,
            "emp2": emp2.id,
            "emp3": emp3.id,
            "ts_g1_id": ts_g1.id,
        }

    app = crear_app(sesion_factory=sf)
    client = TestClient(app)

    # Token JWT del admin para usar los endpoints admin
    jwt_admin = client.post(
        "/api/auth/login", json={"email": "admin@test.com", "password": "pass"}
    ).json()["access_token"]

    return {
        "client": client,
        "sf": sf,
        "jwt_admin": jwt_admin,
        "raw_g1": raw_g1,
        "raw_emp1": raw_emp1,
        "raw_revocado": raw_revocado,
        "raw_superadmin": raw_superadmin,
        "ids": ids,
        "tmp_path": tmp_path,
    }


def _headers(raw_token: str) -> dict:
    return {"X-Pipeline-Token": raw_token}


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4 test content pipeline"


# ---------------------------------------------------------------------------
# Auth — token de servicio
# ---------------------------------------------------------------------------

def test_sin_token_401(setup):
    """Sin X-Pipeline-Token → 401."""
    r = setup["client"].get("/api/pipeline/empresas")
    assert r.status_code == 401


def test_token_invalido_401(setup):
    """Token raw que no existe en BD → 401."""
    r = setup["client"].get("/api/pipeline/empresas", headers=_headers("token_que_no_existe"))
    assert r.status_code == 401


def test_token_revocado_401(setup):
    """Token con activo=False → 401."""
    r = setup["client"].get("/api/pipeline/empresas", headers=_headers(setup["raw_revocado"]))
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/pipeline/empresas
# ---------------------------------------------------------------------------

def test_empresas_scope_gestoria(setup):
    """Token con gestoria_id=G1 → devuelve solo emp1 y emp2."""
    r = setup["client"].get("/api/pipeline/empresas", headers=_headers(setup["raw_g1"]))
    assert r.status_code == 200
    ids_respuesta = {e["id"] for e in r.json()}
    assert setup["ids"]["emp1"] in ids_respuesta
    assert setup["ids"]["emp2"] in ids_respuesta
    assert setup["ids"]["emp3"] not in ids_respuesta


def test_empresas_scope_empresa_ids(setup):
    """Token con empresa_ids=[emp1] → solo devuelve emp1."""
    r = setup["client"].get("/api/pipeline/empresas", headers=_headers(setup["raw_emp1"]))
    assert r.status_code == 200
    ids_respuesta = [e["id"] for e in r.json()]
    assert ids_respuesta == [setup["ids"]["emp1"]]


def test_empresas_scope_superadmin(setup):
    """Token superadmin (gestoria_id=None) → devuelve las 3 empresas."""
    r = setup["client"].get("/api/pipeline/empresas", headers=_headers(setup["raw_superadmin"]))
    assert r.status_code == 200
    assert len(r.json()) == 3


# ---------------------------------------------------------------------------
# POST /api/pipeline/documentos/subir
# ---------------------------------------------------------------------------

def test_subir_happy_path(setup, tmp_path):
    """Subida correcta → {documento_id, cola_id, sha256, estado: encolado}."""
    contenido = _pdf_bytes()
    r = setup["client"].post(
        "/api/pipeline/documentos/subir",
        headers=_headers(setup["raw_g1"]),
        data={"empresa_id": setup["ids"]["emp1"], "ejercicio": "2025"},
        files={"archivo": ("factura.pdf", io.BytesIO(contenido), "application/pdf")},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["estado"] == "encolado"
    assert "documento_id" in body
    assert "cola_id" in body
    sha256_esperado = hashlib.sha256(contenido).hexdigest()
    assert body["sha256"] == sha256_esperado

    # Verificar que Documento y ColaProcesamiento existen en BD
    with setup["sf"]() as s:
        doc = s.get(Documento, body["documento_id"])
        assert doc is not None
        assert doc.estado == "pendiente"
        cola = s.get(ColaProcesamiento, body["cola_id"])
        assert cola is not None
        assert cola.estado == "PENDIENTE"
        assert cola.sha256 == sha256_esperado


def test_subir_duplicado_devuelve_existente(setup):
    """Subir el mismo PDF dos veces → segundo devuelve {estado: duplicado}."""
    contenido = b"%PDF duplicado test content 12345"
    params = {"empresa_id": setup["ids"]["emp1"], "ejercicio": "2025"}

    r1 = setup["client"].post(
        "/api/pipeline/documentos/subir",
        headers=_headers(setup["raw_g1"]),
        data=params,
        files={"archivo": ("dup.pdf", io.BytesIO(contenido), "application/pdf")},
    )
    assert r1.status_code == 201
    doc_id_original = r1.json()["documento_id"]

    r2 = setup["client"].post(
        "/api/pipeline/documentos/subir",
        headers=_headers(setup["raw_g1"]),
        data=params,
        files={"archivo": ("dup.pdf", io.BytesIO(contenido), "application/pdf")},
    )
    assert r2.status_code == 201
    body2 = r2.json()
    assert body2["estado"] == "duplicado"
    assert body2["documento_id"] == doc_id_original


def test_subir_empresa_fuera_de_scope_403(setup):
    """Token de G1 intenta subir a empresa de G2 → 403."""
    r = setup["client"].post(
        "/api/pipeline/documentos/subir",
        headers=_headers(setup["raw_g1"]),
        data={"empresa_id": setup["ids"]["emp3"], "ejercicio": "2025"},
        files={"archivo": ("factura.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )
    assert r.status_code == 403


def test_subir_empresa_fuera_de_empresa_ids_403(setup):
    """Token limitado a emp1 intenta subir a emp2 (misma gestoría) → 403."""
    r = setup["client"].post(
        "/api/pipeline/documentos/subir",
        headers=_headers(setup["raw_emp1"]),
        data={"empresa_id": setup["ids"]["emp2"], "ejercicio": "2025"},
        files={"archivo": ("factura.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )
    assert r.status_code == 403


def test_subir_archivo_vacio_422(setup):
    """Archivo vacío → 422."""
    r = setup["client"].post(
        "/api/pipeline/documentos/subir",
        headers=_headers(setup["raw_g1"]),
        data={"empresa_id": setup["ids"]["emp1"], "ejercicio": "2025"},
        files={"archivo": ("vacio.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/pipeline/documentos/pendientes
# ---------------------------------------------------------------------------

def test_pendientes_vacio(setup):
    """Sin documentos → {total: 0, items: []}."""
    r = setup["client"].get(
        "/api/pipeline/documentos/pendientes",
        headers=_headers(setup["raw_g1"]),
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["items"] == []


def test_pendientes_con_docs(setup):
    """Tras subir 2 docs a emp1 → aparecen en pendientes."""
    for i in range(2):
        setup["client"].post(
            "/api/pipeline/documentos/subir",
            headers=_headers(setup["raw_g1"]),
            data={"empresa_id": setup["ids"]["emp1"], "ejercicio": "2025"},
            files={"archivo": (f"f{i}.pdf", io.BytesIO(f"%PDF {i}".encode()), "application/pdf")},
        )

    r = setup["client"].get(
        "/api/pipeline/documentos/pendientes",
        headers=_headers(setup["raw_g1"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


def test_pendientes_filtro_empresa(setup):
    """Filtrar por empresa_id específica."""
    # Subir a emp1
    setup["client"].post(
        "/api/pipeline/documentos/subir",
        headers=_headers(setup["raw_g1"]),
        data={"empresa_id": setup["ids"]["emp1"], "ejercicio": "2025"},
        files={"archivo": ("f.pdf", io.BytesIO(b"%PDF filtro"), "application/pdf")},
    )

    r = setup["client"].get(
        f"/api/pipeline/documentos/pendientes?empresa_id={setup['ids']['emp1']}",
        headers=_headers(setup["raw_g1"]),
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["empresa_id"] == setup["ids"]["emp1"]


def test_pendientes_empresa_fuera_scope_403(setup):
    """Consultar empresa fuera del scope del token → 403."""
    r = setup["client"].get(
        f"/api/pipeline/documentos/pendientes?empresa_id={setup['ids']['emp3']}",
        headers=_headers(setup["raw_g1"]),
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/pipeline/sync-status
# ---------------------------------------------------------------------------

def test_sync_status_vacio(setup):
    """Sin documentos → lista de empresas con todos los contadores a 0."""
    r = setup["client"].get("/api/pipeline/sync-status", headers=_headers(setup["raw_g1"]))
    assert r.status_code == 200
    data = r.json()
    # Debe incluir emp1 y emp2 (en scope del token G1)
    ids_en_respuesta = {item["empresa_id"] for item in data}
    assert setup["ids"]["emp1"] in ids_en_respuesta
    assert setup["ids"]["emp2"] in ids_en_respuesta
    for item in data:
        assert item["pendiente"] == 0
        assert item["ok"] == 0


def test_sync_status_cuenta_pendientes(setup):
    """Tras subir docs → pendiente > 0 para esa empresa."""
    setup["client"].post(
        "/api/pipeline/documentos/subir",
        headers=_headers(setup["raw_g1"]),
        data={"empresa_id": setup["ids"]["emp1"], "ejercicio": "2025"},
        files={"archivo": ("f.pdf", io.BytesIO(b"%PDF sync test"), "application/pdf")},
    )

    r = setup["client"].get("/api/pipeline/sync-status", headers=_headers(setup["raw_g1"]))
    assert r.status_code == 200
    emp1_status = next(
        (item for item in r.json() if item["empresa_id"] == setup["ids"]["emp1"]), None
    )
    assert emp1_status is not None
    assert emp1_status["pendiente"] >= 1


# ---------------------------------------------------------------------------
# Admin: CRUD tokens de servicio
# ---------------------------------------------------------------------------

def test_admin_crear_token(setup):
    """Superadmin crea token → devuelve token_raw solo esta vez."""
    r = setup["client"].post(
        "/api/admin/tokens-servicio",
        headers={"Authorization": f"Bearer {setup['jwt_admin']}"},
        json={"nombre": "pipeline-nuevo", "gestoria_id": setup["ids"]["g1"], "empresa_ids": []},
    )
    assert r.status_code == 201
    body = r.json()
    assert "token_raw" in body
    assert len(body["token_raw"]) == 64  # secrets.token_hex(32)
    assert "id" in body


def test_admin_listar_tokens_sin_raw(setup):
    """Listar tokens → no aparece token_raw."""
    r = setup["client"].get(
        "/api/admin/tokens-servicio",
        headers={"Authorization": f"Bearer {setup['jwt_admin']}"},
    )
    assert r.status_code == 200
    for token in r.json():
        assert "token_raw" not in token
        assert "token_hash_prefix" in token


def test_admin_revocar_token(setup):
    """Revocar token → siguiente request con ese token da 401."""
    # Crear token nuevo
    r_crear = setup["client"].post(
        "/api/admin/tokens-servicio",
        headers={"Authorization": f"Bearer {setup['jwt_admin']}"},
        json={"nombre": "para-revocar", "gestoria_id": None, "empresa_ids": []},
    )
    token_id = r_crear.json()["id"]
    token_raw_nuevo = r_crear.json()["token_raw"]

    # Verificar que funciona antes de revocar
    r_ok = setup["client"].get(
        "/api/pipeline/empresas", headers=_headers(token_raw_nuevo)
    )
    assert r_ok.status_code == 200

    # Revocar
    r_rev = setup["client"].delete(
        f"/api/admin/tokens-servicio/{token_id}",
        headers={"Authorization": f"Bearer {setup['jwt_admin']}"},
    )
    assert r_rev.status_code == 200
    assert r_rev.json()["revocado"] is True

    # Ahora debe dar 401
    r_revocado = setup["client"].get(
        "/api/pipeline/empresas", headers=_headers(token_raw_nuevo)
    )
    assert r_revocado.status_code == 401


def test_admin_crear_token_requiere_superadmin(setup):
    """Usuario no superadmin no puede crear tokens → 403."""
    # Crear usuario asesor
    with setup["sf"]() as s:
        from sfce.api.auth import hashear_password as hp
        s.add(Usuario(
            email="asesor_test2@test.com",
            nombre="Asesor",
            hash_password=hp("pass2"),
            rol="asesor",
            activo=True,
        ))
        s.commit()

    jwt_asesor = setup["client"].post(
        "/api/auth/login", json={"email": "asesor_test2@test.com", "password": "pass2"}
    ).json()["access_token"]

    r = setup["client"].post(
        "/api/admin/tokens-servicio",
        headers={"Authorization": f"Bearer {jwt_asesor}"},
        json={"nombre": "test", "gestoria_id": None},
    )
    assert r.status_code == 403
