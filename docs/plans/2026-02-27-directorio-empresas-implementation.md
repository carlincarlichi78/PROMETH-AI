# Directorio de Empresas — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** BD compartida de proveedores/clientes con tabla maestra global + overlay por empresa, verificacion AEAT/VIES, y migracion desde config.yaml.

**Architecture:** Nueva tabla `directorio_entidades` (datos maestros globales, CIF unico) referenciada por `proveedores_clientes` via FK. ConfigCliente pasa a leer de BD. Servicios AEAT/VIES para verificar CIF. Pipeline y API adaptados.

**Tech Stack:** SQLAlchemy (existente), requests (AEAT SOAP via zeep o raw), FastAPI (existente), pytest

---

### Task 1: Modelo DirectorioEntidad + migracion Alembic

**Files:**
- Modify: `sfce/db/modelos.py`
- Modify: `sfce/db/base.py` (solo si hace falta, probablemente no)
- Test: `tests/test_directorio.py`

**Step 1: Write failing test**

```python
# tests/test_directorio.py
"""Tests para DirectorioEntidad y relacion con ProveedorCliente."""
import pytest
from sfce.db.base import Base, crear_motor, crear_sesion, inicializar_bd
from sfce.db.modelos import DirectorioEntidad, ProveedorCliente, Empresa


@pytest.fixture
def sesion():
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
    inicializar_bd(engine)
    Session = crear_sesion(engine)
    with Session() as s:
        yield s


class TestDirectorioEntidad:
    def test_crear_entidad_con_cif(self, sesion):
        ent = DirectorioEntidad(cif="B12345678", nombre="EMPRESA TEST SL", pais="ESP")
        sesion.add(ent)
        sesion.commit()
        assert ent.id is not None
        assert ent.cif == "B12345678"

    def test_crear_entidad_sin_cif(self, sesion):
        ent = DirectorioEntidad(nombre="PACIENTES FISIOTERAPIA", pais="ESP")
        sesion.add(ent)
        sesion.commit()
        assert ent.id is not None
        assert ent.cif is None

    def test_cif_unico(self, sesion):
        ent1 = DirectorioEntidad(cif="A99999999", nombre="UNO", pais="ESP")
        sesion.add(ent1)
        sesion.commit()
        ent2 = DirectorioEntidad(cif="A99999999", nombre="DOS", pais="ESP")
        sesion.add(ent2)
        with pytest.raises(Exception):
            sesion.commit()

    def test_relacion_overlay(self, sesion):
        dir_ent = DirectorioEntidad(cif="B11111111", nombre="PROV TEST", pais="ESP")
        sesion.add(dir_ent)
        sesion.flush()
        empresa = Empresa(cif="X99999999", nombre="MI EMPRESA", forma_juridica="sl",
                         territorio="peninsula")
        sesion.add(empresa)
        sesion.flush()
        overlay = ProveedorCliente(
            empresa_id=empresa.id, cif="B11111111", nombre="PROV TEST",
            tipo="proveedor", directorio_id=dir_ent.id
        )
        sesion.add(overlay)
        sesion.commit()
        assert overlay.directorio_id == dir_ent.id
        assert overlay.directorio.nombre == "PROV TEST"

    def test_aliases_json(self, sesion):
        ent = DirectorioEntidad(
            cif="C22222222", nombre="ENDESA ENERGIA SAU", pais="ESP",
            aliases=["ENDESA", "ENDESA ENERGIA"]
        )
        sesion.add(ent)
        sesion.commit()
        sesion.refresh(ent)
        assert "ENDESA" in ent.aliases
```

**Step 2: Run test, expect FAIL** (DirectorioEntidad not defined)

```bash
pytest tests/test_directorio.py -v
```

**Step 3: Implement modelo**

En `sfce/db/modelos.py`, agregar ANTES de `ProveedorCliente`:

```python
class DirectorioEntidad(Base):
    """Directorio maestro global de entidades (proveedores/clientes)."""
    __tablename__ = "directorio_entidades"

    id = Column(Integer, primary_key=True)
    cif = Column(String(20), unique=True, nullable=True)  # nullable para clientes sin CIF
    nombre = Column(String(200), nullable=False)
    nombre_comercial = Column(String(200))
    aliases = Column(JSON, default=list)
    pais = Column(String(3), default="ESP")
    tipo_persona = Column(String(10))  # fisica | juridica
    forma_juridica = Column(String(20))
    cnae = Column(String(4))
    sector = Column(String(50))
    validado_aeat = Column(Boolean, default=False)
    validado_vies = Column(Boolean, default=False)
    fecha_alta = Column(DateTime, default=datetime.now)
    fecha_actualizacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    datos_enriquecidos = Column(JSON, default=dict)

    overlays = relationship("ProveedorCliente", back_populates="directorio")

    __table_args__ = (
        Index("ix_directorio_nombre", "nombre"),
    )
```

En `ProveedorCliente`, agregar campo + relacion:

```python
directorio_id = Column(Integer, ForeignKey("directorio_entidades.id"), nullable=True)
directorio = relationship("DirectorioEntidad", back_populates="overlays")
```

**Step 4: Run tests, expect PASS**

```bash
pytest tests/test_directorio.py -v
```

**Step 5: Commit**

```bash
git add sfce/db/modelos.py tests/test_directorio.py
git commit -m "feat: modelo DirectorioEntidad + FK en ProveedorCliente"
```

---

### Task 2: Repositorio — queries directorio

**Files:**
- Modify: `sfce/db/repositorio.py`
- Test: `tests/test_directorio.py` (ampliar)

**Step 1: Write failing tests**

```python
# Agregar a tests/test_directorio.py
from sfce.db.repositorio import Repositorio

@pytest.fixture
def repo(sesion):
    # Crear factory que devuelve sesion reutilizable
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
    inicializar_bd(engine)
    Session = crear_sesion(engine)
    return Repositorio(Session)


class TestRepositorioDirectorio:
    def test_buscar_directorio_por_cif(self, repo):
        from sfce.db.modelos import DirectorioEntidad
        repo.crear(DirectorioEntidad(cif="B12345678", nombre="TEST SL", pais="ESP"))
        resultado = repo.buscar_directorio_por_cif("B12345678")
        assert resultado is not None
        assert resultado.nombre == "TEST SL"

    def test_buscar_directorio_por_cif_no_existe(self, repo):
        resultado = repo.buscar_directorio_por_cif("Z99999999")
        assert resultado is None

    def test_buscar_directorio_por_nombre(self, repo):
        from sfce.db.modelos import DirectorioEntidad
        repo.crear(DirectorioEntidad(
            cif="A11111111", nombre="ENDESA ENERGIA SAU", pais="ESP",
            aliases=["ENDESA", "ENDESA ENERGIA"]
        ))
        resultado = repo.buscar_directorio_por_nombre("ENDESA")
        assert resultado is not None
        assert resultado.cif == "A11111111"

    def test_buscar_directorio_por_nombre_parcial(self, repo):
        from sfce.db.modelos import DirectorioEntidad
        repo.crear(DirectorioEntidad(
            cif="B22222222", nombre="QUIRUMED SL", pais="ESP",
            aliases=["QUIRUMED"]
        ))
        resultado = repo.buscar_directorio_por_nombre("QUIRUMED SL")
        assert resultado is not None

    def test_obtener_o_crear_directorio(self, repo):
        ent, creado = repo.obtener_o_crear_directorio(
            cif="C33333333", nombre="NUEVA EMPRESA", pais="ESP"
        )
        assert creado is True
        assert ent.id is not None
        ent2, creado2 = repo.obtener_o_crear_directorio(
            cif="C33333333", nombre="OTRA COSA"
        )
        assert creado2 is False
        assert ent2.id == ent.id

    def test_obtener_overlay_con_directorio(self, repo):
        from sfce.db.modelos import DirectorioEntidad, Empresa
        dir_ent = repo.crear(DirectorioEntidad(
            cif="D44444444", nombre="FARMACIA CENTRAL", pais="ESP"
        ))
        empresa = repo.crear(Empresa(
            cif="E55555555", nombre="MI EMPRESA", forma_juridica="autonomo",
            territorio="peninsula"
        ))
        overlay = repo.crear_overlay(
            empresa_id=empresa.id, directorio_id=dir_ent.id,
            tipo="proveedor", subcuenta_gasto="6020000000",
            codimpuesto="IVA4", regimen="general"
        )
        assert overlay.directorio_id == dir_ent.id

    def test_buscar_overlay_por_cif(self, repo):
        from sfce.db.modelos import DirectorioEntidad, Empresa
        dir_ent = repo.crear(DirectorioEntidad(cif="F66666666", nombre="PROV", pais="ESP"))
        empresa = repo.crear(Empresa(
            cif="G77777777", nombre="EMPRESA", forma_juridica="sl",
            territorio="peninsula"
        ))
        repo.crear_overlay(
            empresa_id=empresa.id, directorio_id=dir_ent.id,
            tipo="proveedor", subcuenta_gasto="6000000000",
            codimpuesto="IVA21", regimen="general"
        )
        resultado = repo.buscar_overlay_por_cif(empresa.id, "F66666666", "proveedor")
        assert resultado is not None
        assert resultado.directorio.nombre == "PROV"
```

**Step 2: Run tests, expect FAIL**

**Step 3: Implement queries**

En `sfce/db/repositorio.py`, agregar metodos:

```python
from sfce.db.modelos import DirectorioEntidad

def buscar_directorio_por_cif(self, cif: str) -> DirectorioEntidad | None:
    with self._sesion() as s:
        return s.scalar(
            select(DirectorioEntidad).where(DirectorioEntidad.cif == cif)
        )

def buscar_directorio_por_nombre(self, nombre: str) -> DirectorioEntidad | None:
    nombre_upper = nombre.upper()
    with self._sesion() as s:
        # Busqueda exacta por nombre
        resultado = s.scalar(
            select(DirectorioEntidad).where(
                func.upper(DirectorioEntidad.nombre) == nombre_upper
            )
        )
        if resultado:
            return resultado
        # Busqueda en aliases (JSON array contains)
        todas = s.scalars(select(DirectorioEntidad)).all()
        for ent in todas:
            if ent.aliases:
                for alias in ent.aliases:
                    if alias.upper() == nombre_upper or alias.upper() in nombre_upper:
                        return ent
        return None

def obtener_o_crear_directorio(self, cif: str | None, nombre: str,
                                pais: str = "ESP", **kwargs) -> tuple:
    """Busca por CIF; si no existe, crea. Returns (entidad, creado: bool)."""
    if cif:
        existente = self.buscar_directorio_por_cif(cif)
        if existente:
            return existente, False
    ent = DirectorioEntidad(cif=cif, nombre=nombre, pais=pais, **kwargs)
    return self.crear(ent), True

def crear_overlay(self, empresa_id: int, directorio_id: int, tipo: str,
                   subcuenta_gasto: str = "", codimpuesto: str = "IVA21",
                   regimen: str = "general", **kwargs) -> ProveedorCliente:
    dir_ent = self.obtener(DirectorioEntidad, directorio_id)
    overlay = ProveedorCliente(
        empresa_id=empresa_id, directorio_id=directorio_id,
        cif=dir_ent.cif or "", nombre=dir_ent.nombre,
        tipo=tipo, subcuenta_gasto=subcuenta_gasto,
        codimpuesto=codimpuesto, regimen=regimen, **kwargs
    )
    return self.crear(overlay)

def buscar_overlay_por_cif(self, empresa_id: int, cif: str,
                            tipo: str) -> ProveedorCliente | None:
    with self._sesion() as s:
        return s.scalar(
            select(ProveedorCliente).where(
                ProveedorCliente.empresa_id == empresa_id,
                ProveedorCliente.cif == cif,
                ProveedorCliente.tipo == tipo,
            ).options(joinedload(ProveedorCliente.directorio))
        )
```

**Step 4: Run tests, expect PASS**

**Step 5: Commit**

```bash
git add sfce/db/repositorio.py tests/test_directorio.py
git commit -m "feat: repositorio queries directorio + obtener_o_crear + overlay"
```

---

### Task 3: Script migracion config.yaml → BD

**Files:**
- Create: `scripts/migrar_config_a_directorio.py`
- Test: `tests/test_directorio.py` (ampliar)

**Step 1: Write failing test**

```python
class TestMigracionConfig:
    def test_migrar_elena_navarro(self, tmp_path):
        from scripts.migrar_config_a_directorio import migrar_cliente
        # Copiar config.yaml real a tmp
        import shutil
        src = Path("clientes/elena-navarro/config.yaml")
        dst = tmp_path / "config.yaml"
        shutil.copy(src, dst)
        engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
        inicializar_bd(engine)
        Session = crear_sesion(engine)
        repo = Repositorio(Session)
        stats = migrar_cliente(tmp_path, repo)
        assert stats["proveedores_directorio"] >= 9  # elena tiene 9 proveedores
        assert stats["clientes_directorio"] >= 3
        assert stats["overlays_creados"] >= 12

    def test_migrar_dos_clientes_comparten_directorio(self, tmp_path):
        """Si dos clientes tienen el mismo proveedor (CIF), solo 1 entrada directorio."""
        from scripts.migrar_config_a_directorio import migrar_cliente
        # Crear 2 configs con CaixaBank en comun
        config1 = {
            "empresa": {"nombre": "Empresa 1", "cif": "A11111111", "tipo": "sl",
                        "idempresa": 1, "ejercicio_activo": "2025"},
            "proveedores": {
                "caixabank": {"cif": "A08663619", "nombre_fs": "CAIXABANK SA",
                              "pais": "ESP", "divisa": "EUR", "subcuenta": "6620",
                              "codimpuesto": "IVA0", "regimen": "general"}
            }
        }
        config2 = {
            "empresa": {"nombre": "Empresa 2", "cif": "B22222222", "tipo": "autonomo",
                        "idempresa": 2, "ejercicio_activo": "2025"},
            "proveedores": {
                "caixabank": {"cif": "A08663619", "nombre_fs": "CAIXABANK SA",
                              "pais": "ESP", "divisa": "EUR", "subcuenta": "6620",
                              "codimpuesto": "IVA0", "regimen": "general"}
            }
        }
        import yaml
        dir1 = tmp_path / "emp1"; dir1.mkdir()
        dir2 = tmp_path / "emp2"; dir2.mkdir()
        (dir1 / "config.yaml").write_text(yaml.dump(config1), encoding="utf-8")
        (dir2 / "config.yaml").write_text(yaml.dump(config2), encoding="utf-8")
        engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
        inicializar_bd(engine)
        Session = crear_sesion(engine)
        repo = Repositorio(Session)
        migrar_cliente(dir1, repo)
        migrar_cliente(dir2, repo)
        # Solo 1 entrada CaixaBank en directorio
        caixa = repo.buscar_directorio_por_cif("A08663619")
        assert caixa is not None
        # Pero 2 overlays (uno por empresa)
        with Session() as s:
            overlays = s.scalars(
                select(ProveedorCliente).where(ProveedorCliente.cif == "A08663619")
            ).all()
            assert len(overlays) == 2
```

**Step 2: Run test, expect FAIL**

**Step 3: Implement script**

```python
# scripts/migrar_config_a_directorio.py
"""Migra config.yaml de todos los clientes a BD directorio."""
import sys
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))

import yaml
from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.repositorio import Repositorio
from sfce.db.modelos import Empresa


def migrar_cliente(ruta_cliente: Path, repo: Repositorio) -> dict:
    """Migra un config.yaml a BD directorio + overlays."""
    config_path = ruta_cliente / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    emp_data = data.get("empresa", {})
    stats = {"proveedores_directorio": 0, "clientes_directorio": 0,
             "overlays_creados": 0, "ya_existentes": 0}

    # Obtener o crear empresa
    empresa = repo.buscar_empresa_por_cif(emp_data["cif"])
    if not empresa:
        empresa = repo.crear(Empresa(
            cif=emp_data["cif"], nombre=emp_data["nombre"],
            forma_juridica=emp_data.get("tipo", "sl"),
            territorio="peninsula",
            idempresa_fs=emp_data.get("idempresa"),
            codejercicio_fs=emp_data.get("codejercicio"),
        ))

    # Migrar proveedores
    for nombre_corto, prov in data.get("proveedores", {}).items():
        cif = prov.get("cif", "").strip() or None
        dir_ent, creado = repo.obtener_o_crear_directorio(
            cif=cif, nombre=prov.get("nombre_fs", nombre_corto),
            pais=prov.get("pais", "ESP"),
            aliases=prov.get("aliases", []),
        )
        if creado:
            stats["proveedores_directorio"] += 1
        else:
            stats["ya_existentes"] += 1
        # Crear overlay
        existente = repo.buscar_overlay_por_cif(
            empresa.id, dir_ent.cif or "", "proveedor"
        ) if dir_ent.cif else None
        if not existente:
            repo.crear_overlay(
                empresa_id=empresa.id, directorio_id=dir_ent.id,
                tipo="proveedor",
                subcuenta_gasto=prov.get("subcuenta", "6000000000"),
                codimpuesto=prov.get("codimpuesto", "IVA21"),
                regimen=prov.get("regimen", "general"),
                retencion_pct=prov.get("retencion"),
                pais=prov.get("pais", "ESP"),
                aliases=[nombre_corto],
            )
            stats["overlays_creados"] += 1

    # Migrar clientes
    for nombre_corto, cli in data.get("clientes", {}).items():
        cif = cli.get("cif", "").strip() or None
        dir_ent, creado = repo.obtener_o_crear_directorio(
            cif=cif, nombre=cli.get("nombre_fs", nombre_corto),
            pais=cli.get("pais", "ESP"),
            aliases=cli.get("aliases", []),
        )
        if creado:
            stats["clientes_directorio"] += 1
        else:
            stats["ya_existentes"] += 1
        existente = repo.buscar_overlay_por_cif(
            empresa.id, dir_ent.cif or "", "cliente"
        ) if dir_ent.cif else None
        if not existente:
            repo.crear_overlay(
                empresa_id=empresa.id, directorio_id=dir_ent.id,
                tipo="cliente",
                codimpuesto=cli.get("codimpuesto", "IVA21"),
                regimen=cli.get("regimen", "general"),
                pais=cli.get("pais", "ESP"),
                aliases=[nombre_corto],
            )
            stats["overlays_creados"] += 1

    return stats


def migrar_todos():
    """Migra todos los clientes con config.yaml."""
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": str(RAIZ / "sfce.db")})
    inicializar_bd(engine)
    Session = crear_sesion(engine)
    repo = Repositorio(Session)

    clientes_dir = RAIZ / "clientes"
    total = {"proveedores_directorio": 0, "clientes_directorio": 0,
             "overlays_creados": 0, "ya_existentes": 0}

    for config_path in sorted(clientes_dir.glob("*/config.yaml")):
        ruta_cliente = config_path.parent
        print(f"Migrando: {ruta_cliente.name}")
        stats = migrar_cliente(ruta_cliente, repo)
        for k, v in stats.items():
            total[k] += v
        print(f"  {stats}")

    print(f"\nTotal: {total}")


if __name__ == "__main__":
    migrar_todos()
```

**Step 4: Run tests, expect PASS**

**Step 5: Commit**

```bash
git add scripts/migrar_config_a_directorio.py tests/test_directorio.py
git commit -m "feat: script migracion config.yaml a directorio BD"
```

---

### Task 4: Servicio verificacion AEAT + VIES

**Files:**
- Create: `sfce/core/verificacion_fiscal.py`
- Test: `tests/test_verificacion_fiscal.py`

**Step 1: Write failing tests**

```python
# tests/test_verificacion_fiscal.py
"""Tests para verificacion CIF via AEAT y VAT via VIES."""
import pytest
from unittest.mock import patch, MagicMock
from sfce.core.verificacion_fiscal import verificar_cif_aeat, verificar_vat_vies, inferir_tipo_persona


class TestInferirTipoPersona:
    def test_cif_empresa(self):
        assert inferir_tipo_persona("B12345678") == "juridica"

    def test_nif_persona(self):
        assert inferir_tipo_persona("12345678A") == "fisica"

    def test_nie(self):
        assert inferir_tipo_persona("X1234567L") == "fisica"

    def test_vat_europeo(self):
        assert inferir_tipo_persona("SE556703748501") == "juridica"


class TestVerificarVIES:
    @patch("sfce.core.verificacion_fiscal.requests.get")
    def test_vat_valido(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"isValid": True, "name": "SPOTIFY AB", "address": "Stockholm"}
        )
        resultado = verificar_vat_vies("SE556703748501")
        assert resultado["valido"] is True
        assert resultado["nombre"] == "SPOTIFY AB"

    @patch("sfce.core.verificacion_fiscal.requests.get")
    def test_vat_invalido(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"isValid": False}
        )
        resultado = verificar_vat_vies("SE000000000000")
        assert resultado["valido"] is False

    @patch("sfce.core.verificacion_fiscal.requests.get")
    def test_vies_error_red(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        resultado = verificar_vat_vies("SE556703748501")
        assert resultado["valido"] is None
        assert "error" in resultado


class TestVerificarAEAT:
    @patch("sfce.core.verificacion_fiscal.requests.post")
    def test_cif_valido_aeat(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            text='<Contribuyente><Resultado>IDENTIFICADO</Resultado><Nombre>ENDESA ENERGIA SAU</Nombre></Contribuyente>'
        )
        resultado = verificar_cif_aeat("A81948077")
        assert resultado["valido"] is True
        assert "ENDESA" in resultado["nombre"]

    @patch("sfce.core.verificacion_fiscal.requests.post")
    def test_cif_no_identificado(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            text='<Contribuyente><Resultado>NO IDENTIFICADO</Resultado></Contribuyente>'
        )
        resultado = verificar_cif_aeat("Z99999999")
        assert resultado["valido"] is False
```

**Step 2: Run test, expect FAIL**

**Step 3: Implement modulo**

```python
# sfce/core/verificacion_fiscal.py
"""Verificacion de CIF (AEAT) y VAT (VIES)."""
import re
import xml.etree.ElementTree as ET
from typing import Optional

import requests

from sfce.core.logger import crear_logger

logger = crear_logger("verificacion_fiscal")

# VIES REST API (gratuita, sin key)
VIES_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{country}/vat/{number}"

# AEAT SOAP (verificacion CIF espanol)
AEAT_URL = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/titu/cont/es/wsidentificacion.wsdl"
AEAT_ENDPOINT = "https://www1.agenciatributaria.gob.es/wlpl/BURT-JDIT/ws/VNifV2SOAP"


def inferir_tipo_persona(cif: str) -> str:
    """Infiere tipo persona desde CIF/NIF."""
    cif = cif.strip().upper()
    # NIF persona fisica: 8 digitos + letra
    if re.match(r'^\d{8}[A-Z]$', cif):
        return "fisica"
    # NIE: X/Y/Z + 7 digitos + letra
    if re.match(r'^[XYZ]\d{7}[A-Z]$', cif):
        return "fisica"
    # CIF persona juridica: letra + 7 digitos + digito/letra control
    if re.match(r'^[A-HJ-NP-SUVW]\d{7}[0-9A-J]$', cif):
        return "juridica"
    # VAT europeo (2 letras + numeros): asumimos juridica
    if re.match(r'^[A-Z]{2}\d+', cif):
        return "juridica"
    return "desconocida"


def verificar_vat_vies(vat: str) -> dict:
    """Verifica numero VAT europeo via VIES REST API.

    Args:
        vat: numero VAT completo (ej: "SE556703748501")

    Returns:
        {"valido": bool|None, "nombre": str, "direccion": str, "pais": str, "error": str}
    """
    vat = vat.strip().upper()
    pais = vat[:2]
    numero = vat[2:]
    try:
        url = VIES_URL.format(country=pais, number=numero)
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "valido": data.get("isValid", False),
                "nombre": data.get("name", ""),
                "direccion": data.get("address", ""),
                "pais": pais,
            }
        return {"valido": None, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.warning(f"Error consultando VIES para {vat}: {e}")
        return {"valido": None, "error": str(e)}


def verificar_cif_aeat(cif: str) -> dict:
    """Verifica CIF/NIF espanol via AEAT SOAP.

    Args:
        cif: CIF/NIF espanol (ej: "A81948077")

    Returns:
        {"valido": bool|None, "nombre": str, "error": str}
    """
    cif = cif.strip().upper()
    soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                      xmlns:vnif="http://www2.agenciatributaria.gob.es/static_files/common/internet/dep/titu/cont/es/VNifV2Ent.xsd">
        <soapenv:Body>
            <vnif:VNifV2Ent>
                <vnif:Contribuyente>
                    <vnif:Nif>{cif}</vnif:Nif>
                </vnif:Contribuyente>
            </vnif:VNifV2Ent>
        </soapenv:Body>
    </soapenv:Envelope>"""
    try:
        resp = requests.post(
            AEAT_ENDPOINT,
            data=soap_body.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=UTF-8", "SOAPAction": ""},
            timeout=10
        )
        if resp.status_code == 200:
            # Parsear XML respuesta
            root = ET.fromstring(resp.text)
            # Buscar Resultado y Nombre en cualquier namespace
            resultado_el = root.find(".//{*}Resultado")
            nombre_el = root.find(".//{*}Nombre")
            resultado_texto = resultado_el.text if resultado_el is not None else ""
            nombre_texto = nombre_el.text if nombre_el is not None else ""
            return {
                "valido": "IDENTIFICADO" in resultado_texto.upper() and "NO" not in resultado_texto.upper(),
                "nombre": nombre_texto,
            }
        return {"valido": None, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.warning(f"Error consultando AEAT para {cif}: {e}")
        return {"valido": None, "error": str(e)}
```

**Step 4: Run tests, expect PASS**

**Step 5: Commit**

```bash
git add sfce/core/verificacion_fiscal.py tests/test_verificacion_fiscal.py
git commit -m "feat: verificacion CIF via AEAT + VAT via VIES"
```

---

### Task 5: ConfigCliente lee de BD (adaptador)

**Files:**
- Modify: `scripts/core/config.py`
- Test: `tests/test_directorio.py` (ampliar)

**Step 1: Write failing tests**

```python
class TestConfigClienteDesdeBD:
    def test_buscar_proveedor_por_cif_desde_bd(self, repo):
        """ConfigCliente.buscar_proveedor_por_cif usa BD cuando hay repo."""
        from sfce.db.modelos import DirectorioEntidad, Empresa
        from scripts.core.config import ConfigCliente
        dir_ent = repo.crear(DirectorioEntidad(
            cif="B46011995", nombre="QUIRUMED SL", pais="ESP",
            aliases=["QUIRUMED"]
        ))
        empresa = repo.crear(Empresa(
            cif="24813607B", nombre="ELENA NAVARRO", forma_juridica="autonomo",
            territorio="peninsula"
        ))
        repo.crear_overlay(
            empresa_id=empresa.id, directorio_id=dir_ent.id,
            tipo="proveedor", subcuenta_gasto="6290000000",
            codimpuesto="IVA21", regimen="general"
        )
        config_data = {
            "empresa": {"nombre": "ELENA NAVARRO", "cif": "24813607B",
                        "tipo": "autonomo", "idempresa": 99, "ejercicio_activo": "2025"},
            "proveedores": {},
            "clientes": {},
        }
        config = ConfigCliente(config_data, "test", repo=repo, empresa_bd_id=empresa.id)
        resultado = config.buscar_proveedor_por_cif("B46011995")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "quirumed-sl"  # slugificado

    def test_fallback_yaml_si_no_repo(self, repo):
        """Sin repo, ConfigCliente usa YAML como antes."""
        from scripts.core.config import ConfigCliente
        config_data = {
            "empresa": {"nombre": "TEST", "cif": "X99999999",
                        "tipo": "sl", "idempresa": 1, "ejercicio_activo": "2025"},
            "proveedores": {
                "test-prov": {"cif": "A11111111", "nombre_fs": "TEST PROV",
                              "pais": "ESP", "divisa": "EUR", "subcuenta": "600",
                              "codimpuesto": "IVA21", "regimen": "general"}
            },
        }
        config = ConfigCliente(config_data, "test")
        resultado = config.buscar_proveedor_por_cif("A11111111")
        assert resultado is not None
```

**Step 2: Run tests, expect FAIL**

**Step 3: Modify ConfigCliente**

En `scripts/core/config.py`, modificar `__init__` y metodos de busqueda:

```python
def __init__(self, data: dict, ruta: Path, repo=None, empresa_bd_id: int = None):
    # ... campos existentes ...
    self._repo = repo
    self._empresa_bd_id = empresa_bd_id

def buscar_proveedor_por_cif(self, cif: str) -> Optional[dict]:
    # Primero BD si disponible
    if self._repo and self._empresa_bd_id:
        overlay = self._repo.buscar_overlay_por_cif(
            self._empresa_bd_id, cif, "proveedor"
        )
        if overlay:
            return self._overlay_a_dict(overlay)
    # Fallback YAML
    cif_norm = _normalizar_cif(cif)
    if not cif_norm:
        return None
    for nombre, datos in self.proveedores.items():
        if _normalizar_cif(datos.get("cif", "")) == cif_norm:
            return {**datos, "_nombre_corto": nombre}
    return None

# Metodo helper para convertir overlay SQLAlchemy a dict compatible
def _overlay_a_dict(self, overlay) -> dict:
    nombre_corto = _slugificar(overlay.nombre)
    return {
        "cif": overlay.cif,
        "nombre_fs": overlay.nombre,
        "pais": overlay.pais or "ESP",
        "divisa": "EUR",
        "subcuenta": overlay.subcuenta_gasto or "",
        "codimpuesto": overlay.codimpuesto or "IVA21",
        "regimen": overlay.regimen or "general",
        "aliases": overlay.aliases or [],
        "_nombre_corto": nombre_corto,
    }
```

Aplicar misma logica a `buscar_proveedor_por_nombre`, `buscar_cliente_por_cif`, `buscar_cliente_por_nombre`.

**Step 4: Run ALL tests (973+nuevos), expect PASS**

```bash
pytest tests/ -x -q
```

**Step 5: Commit**

```bash
git add scripts/core/config.py tests/test_directorio.py
git commit -m "feat: ConfigCliente lee de BD con fallback YAML"
```

---

### Task 6: Ruta API directorio

**Files:**
- Create: `sfce/api/rutas/directorio.py`
- Modify: `sfce/api/app.py` (registrar router)
- Modify: `sfce/api/schemas.py` (agregar schemas)
- Test: `tests/test_directorio.py` (ampliar)

**Step 1: Write failing test**

```python
class TestAPIDirectorio:
    def test_listar_directorio(self, client):
        resp = client.get("/api/directorio/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_buscar_por_cif(self, client):
        # Crear entidad primero
        resp = client.get("/api/directorio/buscar?cif=B12345678")
        assert resp.status_code in (200, 404)

    def test_crear_entidad(self, client):
        resp = client.post("/api/directorio/", json={
            "cif": "H99999999", "nombre": "NUEVA ENTIDAD", "pais": "ESP"
        })
        assert resp.status_code == 201
        assert resp.json()["cif"] == "H99999999"
```

**Step 2-4: Implement + test**

Router FastAPI con endpoints: GET /, GET /buscar, POST /, GET /{id}, PUT /{id}

**Step 5: Commit**

```bash
git add sfce/api/rutas/directorio.py sfce/api/app.py sfce/api/schemas.py tests/test_directorio.py
git commit -m "feat: API REST directorio entidades (CRUD + busqueda)"
```

---

### Task 7: Pagina dashboard Directorio

**Files:**
- Create: `dashboard/src/pages/Directorio.tsx`
- Modify: `dashboard/src/App.tsx` (agregar ruta)
- Modify: `dashboard/src/components/Sidebar.tsx` (agregar link)

Pagina con tabla de entidades, busqueda por CIF/nombre, filtros pais/tipo, detalle con overlays por empresa, boton "Verificar AEAT/VIES".

**Step 1-5: Implementar componente React + commit**

```bash
git add dashboard/src/pages/Directorio.tsx dashboard/src/App.tsx dashboard/src/components/Sidebar.tsx
git commit -m "feat: pagina dashboard Directorio (tabla + busqueda + verificacion)"
```

---

### Task 8: Integrar directorio en pipeline

**Files:**
- Modify: `scripts/pipeline.py` (inicializar repo BD)
- Modify: `scripts/phases/registration.py` (`_asegurar_entidades_fs` usa directorio)
- Modify: `scripts/phases/intake.py` (`_descubrimiento_interactivo` graba en BD)
- Test: `tests/test_directorio.py` (test integracion pipeline)

**Step 1: Write test de integracion**

```python
class TestIntegracionPipeline:
    def test_asegurar_entidades_usa_directorio(self, repo):
        """_asegurar_entidades_fs crea overlays en BD al registrar."""
        # Mock FS API, verificar que BD se actualiza
        pass

    def test_descubrimiento_interactivo_graba_bd(self, repo):
        """Al descubrir entidad nueva, se graba en directorio + overlay."""
        pass
```

**Step 2-4: Implementar integracion**

En `pipeline.py`:
- Al arrancar, crear `engine` + `Repositorio`
- Pasar `repo` y `empresa_bd_id` a `ConfigCliente`
- En `_asegurar_entidades_fs`: ademas de crear en FS, crear en directorio BD
- En `_descubrimiento_interactivo`: grabar en directorio BD en vez de YAML

**Step 5: Commit**

```bash
git add scripts/pipeline.py scripts/phases/registration.py scripts/phases/intake.py tests/test_directorio.py
git commit -m "feat: pipeline integrado con directorio BD"
```

---

### Task 9: Ejecutar migracion real + test E2E

**Files:**
- Run: `python scripts/migrar_config_a_directorio.py`

**Step 1: Ejecutar migracion**

```bash
python scripts/migrar_config_a_directorio.py
```

Esperado: 5 clientes migrados, ~83 entidades en directorio, ~83 overlays.

**Step 2: Verificar BD**

```bash
python -c "
from sfce.db.base import crear_motor, crear_sesion
from sfce.db.modelos import DirectorioEntidad, ProveedorCliente
from sqlalchemy import select, func
engine = crear_motor({'tipo_bd': 'sqlite', 'ruta_bd': 'sfce.db'})
Session = crear_sesion(engine)
with Session() as s:
    total_dir = s.scalar(select(func.count(DirectorioEntidad.id)))
    total_ov = s.scalar(select(func.count(ProveedorCliente.id)))
    print(f'Directorio: {total_dir} entidades')
    print(f'Overlays: {total_ov} registros')
"
```

**Step 3: Dry-run elena-navarro con BD**

```bash
export $(cat .env | grep -v '^#' | xargs)
python scripts/pipeline.py --cliente elena-navarro --ejercicio 2025 --dry-run --no-interactivo --inbox inbox_muestra
```

Esperado: 60/60 validados (igual que sin BD).

**Step 4: Commit BD + docs**

```bash
git add sfce.db
git commit -m "feat: migracion directorio completada — 5 clientes, ~83 entidades"
```

---

### Task 10: Tests finales + documentacion

**Files:**
- Run: `pytest tests/ -v` (TODOS deben pasar)
- Modify: `CLAUDE.md` (actualizar seccion directorio)

**Step 1: Verificar suite completa**

```bash
pytest tests/ -v --tb=short
```

Esperado: 973+ tests PASS (existentes + ~30 nuevos directorio).

**Step 2: Actualizar CLAUDE.md**

Agregar seccion:

```markdown
## Directorio de Empresas — IMPLEMENTADO

**Tabla maestra**: `directorio_entidades` (CIF unico global, aliases, pais, verificacion AEAT/VIES)
**Overlay**: `proveedores_clientes` con FK a directorio (subcuenta, codimpuesto, regimen por empresa)
**Fuente de verdad**: BD local SQLite. config.yaml migrado, readonly.
**Migracion**: `python scripts/migrar_config_a_directorio.py`
**API**: `/api/directorio/` (CRUD + busqueda)
**Dashboard**: pagina Directorio con tabla, busqueda, verificacion fiscal
```

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: directorio empresas implementado"
```
