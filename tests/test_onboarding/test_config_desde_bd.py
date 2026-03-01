"""Tests para generar_config_desde_bd() — bridge BD → pipeline."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
from sfce.db.modelos import Empresa, ProveedorCliente
from sfce.db.modelos_auth import Gestoria
from sfce.core.config_desde_bd import generar_config_desde_bd


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine_bd():
    """Motor SQLite en memoria con todas las tablas creadas."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def engine_con_empresa(engine_bd):
    """BD con una empresa SL y un proveedor + un cliente."""
    with Session(engine_bd) as s:
        # Gestoria obligatoria por FK
        gest = Gestoria(nombre="Gestoria Test", cif="G99999999", email_contacto="test@test.com")
        s.add(gest)
        s.flush()

        emp = Empresa(
            cif="B12345678",
            nombre="Limones Garcia S.L.",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
            idempresa_fs=5,
            codejercicio_fs="0005",
            gestoria_id=gest.id,
            config_extra={
                "ejercicio_activo": 2025,
                "perfil": {
                    "importador": True,
                    "divisas_habituales": ["USD"],
                },
            },
        )
        s.add(emp)
        s.flush()

        proveedor = ProveedorCliente(
            empresa_id=emp.id,
            cif="A00000001",
            nombre="Proveedor Electrico S.A.",
            tipo="proveedor",
            subcuenta_gasto="6200000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21",
            regimen="general",
            pais="ESP",
        )
        cliente = ProveedorCliente(
            empresa_id=emp.id,
            cif="B99999999",
            nombre="Cliente Final S.L.",
            tipo="cliente",
            subcuenta_gasto="7000000000",
            subcuenta_contrapartida="4300000001",
            codimpuesto="IVA21",
            regimen="general",
            pais="ESP",
        )
        s.add_all([proveedor, cliente])
        s.commit()

    return engine_bd


# ---------------------------------------------------------------------------
# Tests datos basicos empresa
# ---------------------------------------------------------------------------

def test_idempresa_desde_columna_directa(engine_con_empresa):
    """idempresa_fs en columna directa se usa como config.idempresa."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert config.idempresa == 5


def test_codejercicio_desde_columna_directa(engine_con_empresa):
    """codejercicio_fs en columna directa se usa como config.codejercicio."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert config.codejercicio == "0005"


def test_ejercicio_activo_desde_config_extra(engine_con_empresa):
    """ejercicio_activo se lee de config_extra."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert config.ejercicio == "2025"


def test_nombre_y_cif_empresa(engine_con_empresa):
    """nombre y cif se mapean correctamente."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert config.nombre == "Limones Garcia S.L."
    assert config.cif == "B12345678"


def test_tipo_empresa_normalizado(engine_con_empresa):
    """forma_juridica 'sl' se mapea al tipo correcto."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert config.tipo == "sl"


def test_importador_desde_perfil(engine_con_empresa):
    """importador se lee del perfil en config_extra."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert config.empresa.get("importador") is True


# ---------------------------------------------------------------------------
# Tests proveedores y clientes
# ---------------------------------------------------------------------------

def test_proveedores_cargados(engine_con_empresa):
    """Proveedor de la BD aparece en config.proveedores."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert len(config.proveedores) == 1
    prov = list(config.proveedores.values())[0]
    assert prov["nombre"] == "Proveedor Electrico S.A."
    assert prov["cif"] == "A00000001"


def test_clientes_cargados(engine_con_empresa):
    """Cliente de la BD aparece en config.clientes."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert len(config.clientes) == 1
    cli = list(config.clientes.values())[0]
    assert cli["nombre"] == "Cliente Final S.L."


def test_proveedor_campos_obligatorios(engine_con_empresa):
    """Proveedor tiene todos los campos requeridos por ConfigCliente."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    prov = list(config.proveedores.values())[0]
    # Campos obligatorios segun config.py: cif, nombre_fs, pais, divisa, subcuenta, codimpuesto, regimen
    for campo in ("cif", "nombre_fs", "pais", "divisa", "subcuenta", "codimpuesto", "regimen"):
        assert campo in prov, f"Campo obligatorio ausente: {campo}"


def test_cliente_campos_obligatorios(engine_con_empresa):
    """Cliente tiene todos los campos requeridos por ConfigCliente."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    cli = list(config.clientes.values())[0]
    # Campos obligatorios segun config.py: cif, nombre_fs, pais, divisa, codimpuesto, regimen
    for campo in ("cif", "nombre_fs", "pais", "divisa", "codimpuesto", "regimen"):
        assert campo in cli, f"Campo obligatorio ausente: {campo}"


def test_buscar_proveedor_por_cif(engine_con_empresa):
    """buscar_proveedor_por_cif() funciona sobre config generado desde BD."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    resultado = config.buscar_proveedor_por_cif("A00000001")
    assert resultado is not None
    assert resultado["nombre"] == "Proveedor Electrico S.A."


def test_buscar_cliente_por_cif(engine_con_empresa):
    """buscar_cliente_por_cif() funciona sobre config generado desde BD."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    resultado = config.buscar_cliente_por_cif("B99999999")
    assert resultado is not None
    assert resultado["nombre"] == "Cliente Final S.L."


# ---------------------------------------------------------------------------
# Tests fallbacks
# ---------------------------------------------------------------------------

def test_idempresa_fallback_a_pk_si_no_hay_fs(engine_bd):
    """Si idempresa_fs es None, usa el PK de empresa como fallback."""
    with Session(engine_bd) as s:
        gest = Gestoria(nombre="G2", cif="G00000002", email_contacto="g2@test.com")
        s.add(gest)
        s.flush()
        emp = Empresa(
            cif="A11111111",
            nombre="Sin FS Config S.L.",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
            idempresa_fs=None,
            codejercicio_fs=None,
            gestoria_id=gest.id,
        )
        s.add(emp)
        s.commit()
        emp_id = emp.id
        config = generar_config_desde_bd(emp_id, s)
    assert config.idempresa == emp_id


def test_codejercicio_fallback_zfill(engine_bd):
    """Si codejercicio_fs es None, construye zfill(4) del PK."""
    with Session(engine_bd) as s:
        gest = Gestoria(nombre="G3", cif="G00000003", email_contacto="g3@test.com")
        s.add(gest)
        s.flush()
        emp = Empresa(
            cif="A22222222",
            nombre="Sin Codeje S.L.",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
            idempresa_fs=None,
            codejercicio_fs=None,
            gestoria_id=gest.id,
        )
        s.add(emp)
        s.commit()
        emp_id = emp.id
        config = generar_config_desde_bd(emp_id, s)
    assert config.codejercicio == str(emp_id).zfill(4)


def test_proveedor_sin_pais_usa_esp(engine_bd):
    """Proveedor sin pais en BD recibe 'ESP' por defecto."""
    with Session(engine_bd) as s:
        gest = Gestoria(nombre="G4", cif="G00000004", email_contacto="g4@test.com")
        s.add(gest)
        s.flush()
        emp = Empresa(
            cif="A33333333",
            nombre="Empresa Pais Null",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
            gestoria_id=gest.id,
        )
        s.add(emp)
        s.flush()
        pv = ProveedorCliente(
            empresa_id=emp.id,
            cif="X00000000",
            nombre="Prov Sin Pais",
            tipo="proveedor",
            pais=None,
        )
        s.add(pv)
        s.commit()
        config = generar_config_desde_bd(emp.id, s)
    prov = list(config.proveedores.values())[0]
    assert prov["pais"] == "ESP"


def test_empresa_sin_proveedores(engine_bd):
    """Empresa sin proveedores ni clientes devuelve dicts vacios."""
    with Session(engine_bd) as s:
        gest = Gestoria(nombre="G5", cif="G00000005", email_contacto="g5@test.com")
        s.add(gest)
        s.flush()
        emp = Empresa(
            cif="A44444444",
            nombre="Empresa Vacia S.L.",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
            gestoria_id=gest.id,
        )
        s.add(emp)
        s.commit()
        config = generar_config_desde_bd(emp.id, s)
    assert config.proveedores == {}
    assert config.clientes == {}


# ---------------------------------------------------------------------------
# Test error
# ---------------------------------------------------------------------------

def test_error_si_empresa_no_existe(engine_bd):
    """Lanza ValueError si empresa_id no existe."""
    with Session(engine_bd) as s:
        with pytest.raises(ValueError, match="Empresa 9999 no encontrada en BD"):
            generar_config_desde_bd(9999, s)


# ---------------------------------------------------------------------------
# Test ruta virtual
# ---------------------------------------------------------------------------

def test_ruta_virtual_bd(engine_con_empresa):
    """La ruta del config generado identifica la empresa y no apunta a un archivo real."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    # Path en Windows normaliza // → / y usa backslash; basta comprobar que
    # la ruta contiene "bd:" y el id de la empresa
    ruta_str = str(config.ruta)
    assert "bd:" in ruta_str
    assert str(emp.id) in ruta_str
    assert not config.ruta.exists()  # no es un archivo real en disco


# ---------------------------------------------------------------------------
# Test perfil_fiscal generado
# ---------------------------------------------------------------------------

def test_perfil_fiscal_generado(engine_con_empresa):
    """ConfigCliente genera PerfilFiscal automaticamente desde el tipo."""
    with Session(engine_con_empresa) as s:
        emp = s.query(Empresa).first()
        config = generar_config_desde_bd(emp.id, s)
    assert config.perfil_fiscal is not None
