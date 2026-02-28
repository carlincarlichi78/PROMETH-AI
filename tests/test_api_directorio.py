"""Tests para API REST directorio de entidades."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base, crear_sesion
from sfce.db.modelos import DirectorioEntidad, Empresa  # noqa: F401 — registra modelos
from sfce.db.repositorio import Repositorio
from sfce.api.app import crear_app


def _crear_engine_test():
    """Engine SQLite in-memory con StaticPool (misma conexion en todos los hilos)."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def client():
    engine = _crear_engine_test()
    Base.metadata.create_all(engine)
    Session = crear_sesion(engine)
    app = crear_app(sesion_factory=Session)
    return TestClient(app)


@pytest.fixture
def client_con_datos():
    engine = _crear_engine_test()
    Base.metadata.create_all(engine)
    Session = crear_sesion(engine)
    repo = Repositorio(Session)
    repo.crear(DirectorioEntidad(cif="B12345678", nombre="EMPRESA TEST SL", pais="ESP"))
    repo.crear(DirectorioEntidad(cif="A08663619", nombre="CAIXABANK SA", pais="ESP"))
    repo.crear(DirectorioEntidad(cif="SE556703748501", nombre="SPOTIFY AB", pais="SWE"))
    app = crear_app(sesion_factory=Session)
    return TestClient(app)


class TestAPIDirectorio:
    def test_listar_directorio_vacio(self, client):
        resp = client.get("/api/directorio/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_listar_directorio_con_datos(self, client_con_datos):
        resp = client_con_datos.get("/api/directorio/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_listar_directorio_filtro_pais(self, client_con_datos):
        resp = client_con_datos.get("/api/directorio/?pais=ESP")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_buscar_por_cif(self, client_con_datos):
        resp = client_con_datos.get("/api/directorio/buscar?cif=B12345678")
        assert resp.status_code == 200
        data = resp.json()
        assert data["nombre"] == "EMPRESA TEST SL"

    def test_buscar_por_cif_no_existe(self, client_con_datos):
        resp = client_con_datos.get("/api/directorio/buscar?cif=Z99999999")
        assert resp.status_code == 200
        assert resp.json() is None

    def test_buscar_sin_params(self, client):
        # Sin params devuelve 200 con lista vacía (búsqueda paginada con q opcional)
        resp = client.get("/api/directorio/buscar")
        assert resp.status_code == 200

    def test_crear_entidad(self, client):
        resp = client.post("/api/directorio/", json={
            "cif": "H99999999", "nombre": "NUEVA ENTIDAD", "pais": "ESP"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["cif"] == "H99999999"
        assert data["id"] is not None

    def test_crear_entidad_duplicada(self, client_con_datos):
        resp = client_con_datos.post("/api/directorio/", json={
            "cif": "B12345678", "nombre": "OTRA", "pais": "ESP"
        })
        assert resp.status_code == 409

    def test_obtener_por_id(self, client_con_datos):
        lista = client_con_datos.get("/api/directorio/").json()
        entidad_id = lista[0]["id"]
        resp = client_con_datos.get(f"/api/directorio/{entidad_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == entidad_id

    def test_obtener_por_id_no_existe(self, client):
        resp = client.get("/api/directorio/999")
        assert resp.status_code == 404

    def test_actualizar_entidad(self, client_con_datos):
        lista = client_con_datos.get("/api/directorio/").json()
        entidad_id = lista[0]["id"]
        resp = client_con_datos.put(f"/api/directorio/{entidad_id}", json={
            "nombre": "NOMBRE ACTUALIZADO", "pais": "ESP",
        })
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "NOMBRE ACTUALIZADO"

    def test_crear_entidad_sin_cif(self, client):
        resp = client.post("/api/directorio/", json={
            "nombre": "PACIENTES VARIOS", "pais": "ESP"
        })
        assert resp.status_code == 201
        assert resp.json()["cif"] is None
