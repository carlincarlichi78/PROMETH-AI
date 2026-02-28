"""Tests persistencia modelos fiscales en BD — T25."""
import json
import pytest
from pathlib import Path

from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.repositorio import Repositorio
from sfce.db.modelos import ModeloFiscalGenerado, Empresa


@pytest.fixture
def repo():
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
    inicializar_bd(engine)
    Session = crear_sesion(engine)
    with Session() as s:
        emp = Empresa(
            cif="B12345678", nombre="TEST SL",
            forma_juridica="sl", territorio="peninsula",
        )
        s.add(emp)
        s.commit()
    return Repositorio(Session)


def _empresa_id(repo):
    with repo._sesion() as s:
        from sqlalchemy import select
        return s.scalar(select(Empresa.id).where(Empresa.cif == "B12345678"))


class TestModeloFiscalGeneradoTabla:
    def test_tabla_existe(self, repo):
        empresa_id = _empresa_id(repo)
        reg = repo.guardar_modelo_generado(
            empresa_id=empresa_id,
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas={"27": 2100.0, "69": 1050.0},
        )
        assert reg.id is not None
        assert reg.modelo == "303"
        assert reg.ejercicio == "2025"
        assert reg.periodo == "1T"

    def test_casillas_json_guardadas(self, repo):
        empresa_id = _empresa_id(repo)
        casillas = {"01": 10000.0, "27": 2100.0, "69": 1050.0}
        reg = repo.guardar_modelo_generado(
            empresa_id=empresa_id, modelo="303",
            ejercicio="2025", periodo="2T", casillas=casillas,
        )
        assert json.loads(reg.casillas_json) == casillas

    def test_estado_por_defecto(self, repo):
        empresa_id = _empresa_id(repo)
        reg = repo.guardar_modelo_generado(
            empresa_id=empresa_id, modelo="111",
            ejercicio="2025", periodo="1T", casillas={},
        )
        assert reg.estado == "generado"
        assert reg.valido is True

    def test_con_rutas(self, repo):
        empresa_id = _empresa_id(repo)
        reg = repo.guardar_modelo_generado(
            empresa_id=empresa_id, modelo="303",
            ejercicio="2025", periodo="3T", casillas={},
            ruta_boe="/tmp/B12345678_2025_3T.303",
            ruta_pdf="/tmp/B12345678_2025_3T.303.pdf",
        )
        assert reg.ruta_boe is not None
        assert reg.ruta_pdf is not None

    def test_fecha_generacion_asignada(self, repo):
        empresa_id = _empresa_id(repo)
        reg = repo.guardar_modelo_generado(
            empresa_id=empresa_id, modelo="130",
            ejercicio="2025", periodo="1T", casillas={},
        )
        assert reg.fecha_generacion is not None


class TestListarModelosGenerados:
    def test_listar_por_empresa(self, repo):
        empresa_id = _empresa_id(repo)
        repo.guardar_modelo_generado(empresa_id=empresa_id, modelo="303",
                                     ejercicio="2025", periodo="1T", casillas={})
        repo.guardar_modelo_generado(empresa_id=empresa_id, modelo="111",
                                     ejercicio="2025", periodo="1T", casillas={})
        resultado = repo.listar_modelos_generados(empresa_id)
        assert len(resultado) == 2

    def test_filtrar_por_ejercicio(self, repo):
        empresa_id = _empresa_id(repo)
        repo.guardar_modelo_generado(empresa_id=empresa_id, modelo="303",
                                     ejercicio="2024", periodo="1T", casillas={})
        repo.guardar_modelo_generado(empresa_id=empresa_id, modelo="303",
                                     ejercicio="2025", periodo="1T", casillas={})
        resultado = repo.listar_modelos_generados(empresa_id, ejercicio="2025")
        assert len(resultado) == 1
        assert resultado[0].ejercicio == "2025"

    def test_filtrar_por_modelo(self, repo):
        empresa_id = _empresa_id(repo)
        repo.guardar_modelo_generado(empresa_id=empresa_id, modelo="303",
                                     ejercicio="2025", periodo="1T", casillas={})
        repo.guardar_modelo_generado(empresa_id=empresa_id, modelo="111",
                                     ejercicio="2025", periodo="1T", casillas={})
        resultado = repo.listar_modelos_generados(empresa_id, modelo="303")
        assert len(resultado) == 1
        assert resultado[0].modelo == "303"

    def test_empresa_sin_modelos(self, repo):
        resultado = repo.listar_modelos_generados(empresa_id=9999)
        assert resultado == []
