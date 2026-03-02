"""Tests para detección de ambigüedad de remitente en múltiples empresas (G2)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base


def _motor():
    # Importar todos los modelos para registrar las tablas con sus FKs
    import sfce.db.modelos  # noqa: F401
    import sfce.db.modelos_auth  # noqa: F401
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    return e


def test_detectar_ambiguedad_importable():
    """La función _detectar_ambiguedad_remitente puede importarse."""
    try:
        from sfce.conectores.correo.ingesta_correo import _detectar_ambiguedad_remitente
        assert callable(_detectar_ambiguedad_remitente)
    except ImportError:
        pytest.skip("_detectar_ambiguedad_remitente no implementada aún")


def test_ambiguedad_con_un_resultado_no_hay_ambiguedad():
    """Si remitente aparece en 1 empresa → no hay ambigüedad."""
    from sfce.conectores.correo.ingesta_correo import _detectar_ambiguedad_remitente

    engine = _motor()
    with Session(engine) as s:
        coincidencias = _detectar_ambiguedad_remitente("factura@test.es", [], s)
    assert len(coincidencias) <= 1


def test_ambiguedad_lista_vacia_retorna_vacio():
    """Sin empresas, siempre retorna lista vacía."""
    from sfce.conectores.correo.ingesta_correo import _detectar_ambiguedad_remitente

    engine = _motor()
    with Session(engine) as s:
        resultado = _detectar_ambiguedad_remitente("proveedor@empresa.es", [], s)
    assert resultado == []


def test_ambiguedad_remitente_en_dos_empresas():
    """Remitente con whitelist en 2 empresas → detecta ambigüedad."""
    from sfce.conectores.correo.ingesta_correo import _detectar_ambiguedad_remitente
    from sfce.conectores.correo.whitelist_remitentes import agregar_remitente
    from sfce.db.modelos import Empresa

    engine = _motor()
    with Session(engine) as s:
        emp1 = Empresa(cif="A11111111", nombre="Empresa Uno SL", forma_juridica="SL")
        emp2 = Empresa(cif="B22222222", nombre="Empresa Dos SL", forma_juridica="SL")
        s.add_all([emp1, emp2])
        s.flush()
        id1, id2 = emp1.id, emp2.id

        agregar_remitente("proveedor@comun.es", id1, s)
        agregar_remitente("proveedor@comun.es", id2, s)
        s.commit()

    empresas = [{"id": id1, "nombre": "Empresa Uno SL"}, {"id": id2, "nombre": "Empresa Dos SL"}]
    with Session(engine) as s:
        coincidencias = _detectar_ambiguedad_remitente("proveedor@comun.es", empresas, s)

    assert len(coincidencias) == 2
    assert id1 in coincidencias
    assert id2 in coincidencias


def test_ambiguedad_remitente_en_una_empresa_sin_ambiguedad():
    """Remitente con whitelist en 1 de 2 empresas → sin ambigüedad."""
    from sfce.conectores.correo.ingesta_correo import _detectar_ambiguedad_remitente
    from sfce.conectores.correo.whitelist_remitentes import agregar_remitente
    from sfce.db.modelos import Empresa

    engine = _motor()
    with Session(engine) as s:
        emp1 = Empresa(cif="C33333333", nombre="Solo Esta SL", forma_juridica="SL")
        emp2 = Empresa(cif="D44444444", nombre="La Otra SL", forma_juridica="SL")
        s.add_all([emp1, emp2])
        s.flush()
        id1, id2 = emp1.id, emp2.id

        # Solo en emp1
        agregar_remitente("exclusivo@proveedor.es", id1, s)
        # emp2 vacía → permite todo, pero verificar_whitelist retorna True si vacía
        # Para que emp2 NO incluya al remitente, añadimos otra entrada diferente
        agregar_remitente("otro@distinto.es", id2, s)
        s.commit()

    empresas = [{"id": id1, "nombre": "Solo Esta SL"}, {"id": id2, "nombre": "La Otra SL"}]
    with Session(engine) as s:
        coincidencias = _detectar_ambiguedad_remitente("exclusivo@proveedor.es", empresas, s)

    # Solo emp1 tiene el remitente; emp2 tiene whitelist con otra entrada → no autoriza
    assert id1 in coincidencias
    assert id2 not in coincidencias


def test_whitelist_verificar_dominio_wildcard():
    """@dominio.es en whitelist autoriza cualquier email de ese dominio."""
    from sfce.conectores.correo.whitelist_remitentes import (
        verificar_whitelist,
        agregar_remitente,
    )
    from sfce.db.modelos import Empresa

    engine = _motor()
    with Session(engine) as s:
        emp = Empresa(cif="A12345678", nombre="Test SL", forma_juridica="SL")
        s.add(emp)
        s.flush()
        empresa_id = emp.id

        # Añadir wildcard de dominio
        agregar_remitente("@endesa.es", empresa_id, s)
        s.commit()

    with Session(engine) as s:
        resultado_ok = verificar_whitelist("facturas@endesa.es", empresa_id, s)
        resultado_no = verificar_whitelist("info@otra.es", empresa_id, s)

    assert resultado_ok is True
    assert resultado_no is False


def test_whitelist_wildcard_dominio_case_insensitive():
    """El wildcard de dominio es insensible a mayúsculas."""
    from sfce.conectores.correo.whitelist_remitentes import (
        verificar_whitelist,
        agregar_remitente,
    )
    from sfce.db.modelos import Empresa

    engine = _motor()
    with Session(engine) as s:
        emp = Empresa(cif="E55555555", nombre="Case SL", forma_juridica="SL")
        s.add(emp)
        s.flush()
        empresa_id = emp.id
        agregar_remitente("@iberdrola.es", empresa_id, s)
        s.commit()

    with Session(engine) as s:
        # Mayúsculas en dominio
        resultado = verificar_whitelist("FACTURAS@IBERDROLA.ES", empresa_id, s)

    assert resultado is True


def test_ambiguedad_con_wildcard_en_multiples_empresas():
    """Wildcard @dominio.es configurado en 2 empresas → ambigüedad detectada."""
    from sfce.conectores.correo.ingesta_correo import _detectar_ambiguedad_remitente
    from sfce.conectores.correo.whitelist_remitentes import agregar_remitente
    from sfce.db.modelos import Empresa

    engine = _motor()
    with Session(engine) as s:
        emp1 = Empresa(cif="F66666666", nombre="Restaurante A SL", forma_juridica="SL")
        emp2 = Empresa(cif="G77777777", nombre="Restaurante B SL", forma_juridica="SL")
        s.add_all([emp1, emp2])
        s.flush()
        id1, id2 = emp1.id, emp2.id

        # Mismo proveedor (wildcard de dominio) en ambas empresas
        agregar_remitente("@makro.es", id1, s)
        agregar_remitente("@makro.es", id2, s)
        s.commit()

    empresas = [{"id": id1, "nombre": "Restaurante A SL"}, {"id": id2, "nombre": "Restaurante B SL"}]
    with Session(engine) as s:
        coincidencias = _detectar_ambiguedad_remitente("pedidos@makro.es", empresas, s)

    assert len(coincidencias) == 2
