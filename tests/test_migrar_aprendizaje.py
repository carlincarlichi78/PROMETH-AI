"""Tests para el script de migración aprendizaje.yaml → supplier_rules."""
import os
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest
import yaml

# Asegurar que el módulo es importable desde raíz
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.db.modelos import Base, SupplierRule
import sfce.db.modelos_auth  # noqa


YAML_PRUEBA = textwrap.dedent("""
version: 1
patrones:
- id: base_001
  regex: no_encontrado
  estrategia: crear_entidad_desde_ocr
  tipo_doc: [FC]
  descripcion: base generico — NO migrar
- id: evol_001
  regex: intracomunitario
  estrategia: adaptar_campos_ocr
  tipo_doc: [FC]
  descripcion: Factura intracomunitaria
- id: evol_005
  regex: subcuenta_generica
  estrategia: adaptar_campos_ocr
  tipo_doc: [FC, SUM]
  descripcion: Subcuenta generica 6000000000
""").strip()


@pytest.fixture
def yaml_tmp(tmp_path) -> Path:
    """Escribe un YAML de prueba y retorna la ruta."""
    ruta = tmp_path / "aprendizaje.yaml"
    ruta.write_text(YAML_PRUEBA, encoding="utf-8")
    return ruta


@pytest.fixture
def engine_vacio():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def _ejecutar_migracion(yaml_path: Path, engine, dry_run: bool = False) -> dict:
    """Helper que ejecuta la lógica de migración con engine inyectado."""
    import yaml as pyyaml
    from scripts.migrar_aprendizaje_yaml_a_supplier_rules import _mapear_evol_a_supplier_rule
    from sqlalchemy.orm import Session

    with open(yaml_path, encoding="utf-8") as f:
        datos = pyyaml.safe_load(f)

    patrones = datos.get("patrones", [])
    evol_patrones = [p for p in patrones if p.get("id", "").startswith("evol_")]

    insertados = 0
    omitidos = 0

    with Session(engine) as sesion:
        for patron in evol_patrones:
            campos = _mapear_evol_a_supplier_rule(patron)
            if not campos:
                omitidos += 1
                continue

            patron_nombre = campos.get("emisor_nombre_patron")
            existente = sesion.query(SupplierRule).filter(
                SupplierRule.empresa_id.is_(None),
                SupplierRule.emisor_cif.is_(None),
                SupplierRule.emisor_nombre_patron == patron_nombre,
            ).first()

            if existente:
                omitidos += 1
                continue

            if not dry_run:
                regla = SupplierRule(empresa_id=None, emisor_cif=None, **campos)
                sesion.add(regla)
            insertados += 1

        if not dry_run:
            sesion.commit()

    return {"insertados": insertados, "omitidos": omitidos}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_migra_evol_no_base(yaml_tmp, engine_vacio):
    """Los patrones base_* no se migran, solo evol_*."""
    resultado = _ejecutar_migracion(yaml_tmp, engine_vacio)
    assert resultado["insertados"] == 2  # evol_001 y evol_005


def test_idempotente_no_duplica(yaml_tmp, engine_vacio):
    """Ejecutar dos veces no duplica reglas."""
    r1 = _ejecutar_migracion(yaml_tmp, engine_vacio)
    r2 = _ejecutar_migracion(yaml_tmp, engine_vacio)
    assert r1["insertados"] == 2
    assert r2["omitidos"] == 2
    assert r2["insertados"] == 0


def test_reglas_insertadas_tienen_nivel_global_nombre(yaml_tmp, engine_vacio):
    """Las reglas migradas tienen nivel=global_nombre y sin empresa_id/cif."""
    from sqlalchemy.orm import Session
    _ejecutar_migracion(yaml_tmp, engine_vacio)

    with Session(engine_vacio) as s:
        reglas = s.query(SupplierRule).all()
    assert len(reglas) == 2
    for regla in reglas:
        assert regla.empresa_id is None
        assert regla.emisor_cif is None
        assert regla.nivel == "global_nombre"
        assert regla.emisor_nombre_patron is not None


def test_dry_run_no_modifica_bd(yaml_tmp, engine_vacio):
    """Con dry_run=True no se insertan filas."""
    from sqlalchemy.orm import Session
    resultado = _ejecutar_migracion(yaml_tmp, engine_vacio, dry_run=True)
    assert resultado["insertados"] == 2  # "contadas" pero no insertadas
    with Session(engine_vacio) as s:
        count = s.query(SupplierRule).count()
    assert count == 0
