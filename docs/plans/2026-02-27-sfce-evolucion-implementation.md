# SFCE Evolucion Arquitectonica — Plan de Implementacion

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactorizar SFCE desde un sistema acoplado a SL+autonomo hacia un motor de reglas contables universal que soporte todos los casos fiscales espanoles, con BD local, dashboard en tiempo real y capacidad de despliegue como producto.

**Architecture:** Motor de reglas centralizado con jerarquia de 6 niveles (normativa > PGC > perfil > negocio > cliente > aprendizaje). Capa de abstraccion sobre FS con doble destino (BD local + FS). Dashboard React+FastAPI con WebSocket para tiempo real.

**Tech Stack:** Python 3.11+, SQLAlchemy + SQLite (migrable PostgreSQL), FastAPI + uvicorn, React 18 + TypeScript + Tailwind + Vite, WebSocket (fastapi-websockets), watchdog (file watcher), PyYAML, openpyxl

**Design doc:** `docs/plans/2026-02-27-sfce-evolucion-arquitectura-design.md`

**Estado actual del codigo:**
- Motor SFCE en `scripts/core/` (14 modulos) + `scripts/phases/` (9 modulos)
- 88 tests pasando en `tests/`
- Config via YAML en `clientes/*/config.yaml`
- Reglas en `reglas/` (9 YAMLs)
- Pipeline via `scripts/pipeline.py`
- Sin pyproject.toml ni estructura de paquete

---

## Organizacion en 4 fases

| Fase | Nombre | Tasks | Descripcion |
|------|--------|-------|-------------|
| **A** | Fundamentos | 1-8 | Reorganizar, perfil fiscal, normativa, capa abstraccion |
| **B** | Motor central | 9-16 | Motor reglas, clasificador, refactorizar pipeline |
| **C** | Datos y persistencia | 17-23 | BD local, importador, exportador, sincronizacion FS |
| **D** | Interfaz y producto | 24-32 | API FastAPI, dashboard React, watcher, licencia |

**Cada fase es independiente y desplegable.** Fase A deja el sistema funcionando igual que ahora pero con estructura nueva. Fase B anade inteligencia. Fase C anade persistencia. Fase D anade interfaz.

**IMPORTANTE**: el pipeline existente DEBE seguir funcionando despues de cada task. Si algo se rompe, arreglarlo antes de continuar.

---

## FASE A: FUNDAMENTOS (Tasks 1-8)

### Task 1: Crear estructura de paquete Python + reorganizar directorios

**Files:**
- Create: `sfce/__init__.py`
- Create: `sfce/core/__init__.py`
- Create: `sfce/phases/__init__.py`
- Create: `sfce/normativa/__init__.py`
- Create: `sfce/reglas/__init__.py`
- Create: `pyproject.toml`
- Modify: `scripts/pipeline.py` (actualizar imports)
- Modify: `scripts/onboarding.py` (actualizar imports)
- Modify: Todos los archivos en `scripts/core/` y `scripts/phases/` (mover)

**Step 1: Crear pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "sfce"
version = "2.0.0"
description = "Sistema de Facturacion y Contabilidad Evolutivo"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31",
    "pyyaml>=6.0",
    "openpyxl>=3.1",
    "python-dotenv>=1.0",
    "mistralai>=1.0",
    "openai>=1.0",
    "google-genai>=1.0",
]

[project.optional-dependencies]
db = ["sqlalchemy>=2.0", "alembic>=1.13"]
api = ["fastapi>=0.110", "uvicorn>=0.27", "websockets>=12.0"]
dev = ["pytest>=8.0", "pytest-cov>=4.1"]

[tool.setuptools.packages.find]
include = ["sfce*"]
```

**Step 2: Crear estructura de directorios sfce/**

```bash
mkdir -p sfce/core sfce/phases sfce/normativa sfce/reglas/pgc sfce/reglas/negocio sfce/reglas/aprendizaje sfce/db sfce/api
```

**Step 3: Copiar modulos core**

Copiar cada archivo de `scripts/core/` a `sfce/core/`, manteniendo los originales como wrappers temporales:

```bash
# Copiar modulos
cp scripts/core/config.py sfce/core/config.py
cp scripts/core/fs_api.py sfce/core/fs_api.py
cp scripts/core/logger.py sfce/core/logger.py
cp scripts/core/errors.py sfce/core/errors.py
cp scripts/core/confidence.py sfce/core/confidence.py
cp scripts/core/aritmetica.py sfce/core/aritmetica.py
cp scripts/core/historico.py sfce/core/historico.py
cp scripts/core/reglas_pgc.py sfce/core/reglas_pgc.py
cp scripts/core/prompts.py sfce/core/prompts.py
cp scripts/core/ocr_gemini.py sfce/core/ocr_gemini.py
cp scripts/core/ocr_mistral.py sfce/core/ocr_mistral.py
cp scripts/core/aprendizaje.py sfce/core/aprendizaje.py
cp scripts/core/asientos_directos.py sfce/core/asientos_directos.py
```

**Step 4: Crear wrappers de compatibilidad en scripts/core/**

Para que el pipeline existente siga funcionando sin cambiar todos los imports de golpe:

```python
# scripts/core/config.py (wrapper)
from sfce.core.config import *
from sfce.core.config import ConfigCliente, cargar_config, validar_config
```

Repetir para cada modulo en `scripts/core/`.

**Step 5: Copiar phases**

```bash
cp scripts/phases/intake.py sfce/phases/intake.py
cp scripts/phases/pre_validation.py sfce/phases/pre_validation.py
cp scripts/phases/registration.py sfce/phases/registration.py
cp scripts/phases/asientos.py sfce/phases/asientos.py
cp scripts/phases/correction.py sfce/phases/correction.py
cp scripts/phases/cross_validation.py sfce/phases/cross_validation.py
cp scripts/phases/ocr_consensus.py sfce/phases/ocr_consensus.py
cp scripts/phases/output.py sfce/phases/output.py
```

Crear wrappers en `scripts/phases/` igual que core.

**Step 6: Actualizar imports internos en sfce/**

En cada archivo copiado a `sfce/`, cambiar:
- `from scripts.core.X import Y` → `from sfce.core.X import Y`
- `from scripts.phases.X import Y` → `from sfce.phases.X import Y`

**Step 7: Copiar reglas YAML**

```bash
cp reglas/subcuentas_pgc.yaml sfce/reglas/pgc/subcuentas_pgc.yaml
cp reglas/subcuentas_tipos.yaml sfce/reglas/pgc/subcuentas_tipos.yaml
cp reglas/tipos_entidad.yaml sfce/reglas/pgc/tipos_entidad.yaml
cp reglas/tipos_retencion.yaml sfce/reglas/pgc/tipos_retencion.yaml
cp reglas/coherencia_fiscal.yaml sfce/reglas/pgc/coherencia_fiscal.yaml
cp reglas/patrones_suplidos.yaml sfce/reglas/pgc/patrones_suplidos.yaml
cp reglas/validaciones.yaml sfce/reglas/negocio/validaciones.yaml
cp reglas/errores_conocidos.yaml sfce/reglas/negocio/errores_conocidos.yaml
cp reglas/aprendizaje.yaml sfce/reglas/aprendizaje/aprendizaje.yaml
```

Crear symlinks o wrappers en `reglas/` para compatibilidad.

**Step 8: Instalar paquete en modo desarrollo**

```bash
pip install -e .
```

**Step 9: Ejecutar tests para verificar que nada se rompio**

```bash
pytest tests/ -v
```

Expected: 88/88 PASS

**Step 10: Commit**

```bash
git add sfce/ pyproject.toml
git commit -m "refactor: reorganizar codigo en paquete sfce/"
```

---

### Task 2: Crear modulo normativa/ con YAML 2025

**Files:**
- Create: `sfce/normativa/__init__.py`
- Create: `sfce/normativa/2025.yaml`
- Create: `sfce/normativa/vigente.py`
- Test: `tests/test_normativa.py`

**Step 1: Escribir test**

```python
# tests/test_normativa.py
from datetime import date
from sfce.normativa.vigente import Normativa

class TestNormativa:
    def setup_method(self):
        self.n = Normativa()

    def test_iva_general_2025(self):
        assert self.n.iva_general(date(2025, 6, 15)) == 21.0

    def test_iva_reducido_2025(self):
        assert self.n.iva_reducido(date(2025, 6, 15)) == 10.0

    def test_iva_superreducido_2025(self):
        assert self.n.iva_superreducido(date(2025, 6, 15)) == 4.0

    def test_recargo_equivalencia_general(self):
        assert self.n.recargo_equivalencia("general", date(2025, 6, 15)) == 5.2

    def test_tipo_is_general(self):
        assert self.n.tipo_is("general", date(2025, 6, 15)) == 25

    def test_tipo_is_pymes(self):
        assert self.n.tipo_is("pymes", date(2025, 6, 15)) == 23

    def test_tipo_is_nueva_creacion(self):
        assert self.n.tipo_is("nueva_creacion", date(2025, 6, 15)) == 15

    def test_retencion_profesional(self):
        assert self.n.retencion_profesional(False, date(2025, 6, 15)) == 15

    def test_retencion_profesional_nuevo(self):
        assert self.n.retencion_profesional(True, date(2025, 6, 15)) == 7

    def test_umbral_modelo_347(self):
        assert self.n.umbral("modelo_347", date(2025, 6, 15)) == 3005.06

    def test_umbral_gran_empresa(self):
        assert self.n.umbral("gran_empresa", date(2025, 6, 15)) == 6014630.00

    def test_smi_mensual(self):
        assert self.n.smi_mensual(date(2025, 6, 15)) == 1134.00

    def test_plazo_303_t1(self):
        plazo = self.n.plazo_presentacion("303", "T1", 2025)
        assert plazo["desde"] == "04-01"
        assert plazo["hasta"] == "04-20"

    def test_pago_fraccionado_130(self):
        assert self.n.pago_fraccionado_130(date(2025, 6, 15)) == 20

    def test_tabla_amortizacion_vehiculos(self):
        tabla = self.n.tabla_amortizacion("vehiculos", date(2025, 6, 15))
        assert tabla["pct_maximo_lineal"] == 16
        assert tabla["periodo_maximo_anos"] == 14

    def test_ano_no_existente_usa_mas_reciente(self):
        """Si pedimos 2030 y no existe, usa el YAML mas reciente disponible"""
        resultado = self.n.iva_general(date(2030, 1, 1))
        assert isinstance(resultado, float)
```

**Step 2: Ejecutar test para verificar que falla**

```bash
pytest tests/test_normativa.py -v
```

Expected: FAIL — modulo no existe

**Step 3: Crear YAML 2025 completo**

Crear `sfce/normativa/2025.yaml` con todos los parametros fiscales vigentes en 2025 (IVA, IS, IRPF, SS, umbrales, plazos, amortizacion). Contenido completo en design doc seccion 6.

**Step 4: Implementar vigente.py**

```python
# sfce/normativa/vigente.py
import yaml
from datetime import date
from pathlib import Path

class Normativa:
    """Fuente unica de verdad fiscal. Consulta parametros por fecha."""

    def __init__(self, directorio: Path | None = None):
        self._directorio = directorio or Path(__file__).parent
        self._cache = {}

    def _cargar_ano(self, ano: int) -> dict:
        if ano in self._cache:
            return self._cache[ano]
        ruta = self._directorio / f"{ano}.yaml"
        if not ruta.exists():
            # Buscar YAML mas reciente disponible
            yamls = sorted(self._directorio.glob("20*.yaml"), reverse=True)
            if not yamls:
                raise FileNotFoundError(f"No hay normativa disponible")
            ruta = yamls[0]
        with open(ruta, "r", encoding="utf-8") as f:
            datos = yaml.safe_load(f)
        self._cache[ano] = datos
        return datos

    def _datos(self, fecha: date) -> dict:
        return self._cargar_ano(fecha.year)

    def iva_general(self, fecha: date) -> float:
        return float(self._datos(fecha)["iva"]["general"])

    def iva_reducido(self, fecha: date) -> float:
        return float(self._datos(fecha)["iva"]["reducido"])

    def iva_superreducido(self, fecha: date) -> float:
        return float(self._datos(fecha)["iva"]["superreducido"])

    def recargo_equivalencia(self, tipo: str, fecha: date) -> float:
        return float(self._datos(fecha)["iva"]["recargo_equivalencia"][tipo])

    def tipo_is(self, categoria: str, fecha: date) -> float:
        return float(self._datos(fecha)["impuesto_sociedades"][categoria])

    def retencion_profesional(self, nuevo_autonomo: bool, fecha: date) -> float:
        datos = self._datos(fecha)["irpf"]
        clave = "retencion_profesional_nuevo" if nuevo_autonomo else "retencion_profesional"
        return float(datos[clave])

    def pago_fraccionado_130(self, fecha: date) -> float:
        return float(self._datos(fecha)["irpf"]["pago_fraccionado_130"])

    def smi_mensual(self, fecha: date) -> float:
        return float(self._datos(fecha)["seguridad_social"]["smi_mensual"])

    def umbral(self, nombre: str, fecha: date) -> float:
        return float(self._datos(fecha)["umbrales"][nombre])

    def plazo_presentacion(self, modelo: str, trimestre: str, ano: int) -> dict:
        datos = self._cargar_ano(ano)
        return datos["plazos_presentacion"]["trimestral"].get(
            trimestre,
            datos["plazos_presentacion"]["anual"].get(f"modelo_{modelo}", {})
        )

    def tabla_amortizacion(self, tipo_bien: str, fecha: date) -> dict:
        tablas = self._datos(fecha)["amortizacion"]["tablas"]
        for tabla in tablas:
            if tabla["tipo_bien"] == tipo_bien:
                return tabla
        raise ValueError(f"Tipo de bien no encontrado: {tipo_bien}")

    def tablas_retencion_irpf(self, fecha: date) -> list:
        return self._datos(fecha)["irpf"]["tablas_retencion"]

    def seguridad_social(self, fecha: date) -> dict:
        return self._datos(fecha)["seguridad_social"]
```

**Step 5: Ejecutar test**

```bash
pytest tests/test_normativa.py -v
```

Expected: ALL PASS

**Step 6: Commit**

```bash
git add sfce/normativa/ tests/test_normativa.py
git commit -m "feat: modulo normativa/ con parametros fiscales 2025 versionados"
```

---

### Task 3: Crear modelo PerfilFiscal

**Files:**
- Create: `sfce/core/perfil_fiscal.py`
- Test: `tests/test_perfil_fiscal.py`

**Step 1: Escribir tests**

```python
# tests/test_perfil_fiscal.py
from sfce.core.perfil_fiscal import PerfilFiscal

class TestPerfilFiscal:
    def test_crear_sl_basica(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl")
        assert pf.tipo_persona == "juridica"
        assert pf.forma_juridica == "sl"
        assert pf.regimen_iva == "general"  # default
        assert pf.territorio == "peninsula"  # default

    def test_modelos_sl(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl",
                          retiene_profesionales=True)
        modelos = pf.modelos_obligatorios()
        assert "303" in modelos["trimestrales"]
        assert "111" in modelos["trimestrales"]
        assert "200" in modelos["anuales"]
        assert "390" in modelos["anuales"]
        assert "130" not in modelos["trimestrales"]

    def test_modelos_autonomo_directa(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          regimen_irpf="directa_simplificada")
        modelos = pf.modelos_obligatorios()
        assert "130" in modelos["trimestrales"]
        assert "100" in modelos["anuales"]
        assert "200" not in modelos["anuales"]

    def test_modelos_autonomo_modulos(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          regimen_irpf="objetiva", regimen_iva="simplificado")
        modelos = pf.modelos_obligatorios()
        assert "131" in modelos["trimestrales"]
        assert "130" not in modelos["trimestrales"]

    def test_modelos_profesional_retencion(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="profesional",
                          retencion_emitidas=True, pct_retencion_emitidas=15,
                          regimen_irpf="directa_simplificada")
        assert pf.retencion_emitidas is True
        assert pf.pct_retencion_emitidas == 15
        modelos = pf.modelos_obligatorios()
        assert "130" in modelos["trimestrales"]

    def test_modelos_con_alquileres(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl",
                          retiene_alquileres=True)
        modelos = pf.modelos_obligatorios()
        assert "115" in modelos["trimestrales"]
        assert "180" in modelos["anuales"]

    def test_operador_intracomunitario(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl",
                          operador_intracomunitario=True)
        modelos = pf.modelos_obligatorios()
        assert "349" in modelos["trimestrales"]

    def test_canarias_igic(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          territorio="canarias")
        assert pf.impuesto_indirecto == "igic"
        modelos = pf.modelos_obligatorios()
        assert "420" in modelos["trimestrales"]
        assert "303" not in modelos["trimestrales"]

    def test_gran_empresa_mensual(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sa",
                          gran_empresa=True, sii_obligatorio=True)
        assert pf.periodicidad == "mensual"

    def test_comunidad_propietarios(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="comunidad_propietarios")
        modelos = pf.modelos_obligatorios()
        assert "303" not in modelos["trimestrales"]
        assert "200" not in modelos["anuales"]

    def test_libros_obligatorios_directa_normal(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          regimen_irpf="directa_normal")
        libros = pf.libros_obligatorios()
        assert "diario" in libros
        assert "inventario" in libros

    def test_libros_modulos_sin_diario(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          regimen_irpf="objetiva")
        libros = pf.libros_obligatorios()
        assert "diario" not in libros
        assert "facturas_recibidas" in libros

    def test_desde_dict(self):
        datos = {
            "tipo_persona": "juridica",
            "forma_juridica": "sl",
            "regimen_iva": "general",
            "retiene_profesionales": True
        }
        pf = PerfilFiscal.desde_dict(datos)
        assert pf.forma_juridica == "sl"
        assert pf.retiene_profesionales is True

    def test_validacion_juridica_sin_irpf(self):
        """Personas juridicas no pueden tener regimen_irpf"""
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl")
        assert pf.regimen_irpf is None

    def test_validacion_fisica_sin_is(self):
        """Personas fisicas no pueden tener tipo_is"""
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo")
        assert pf.tipo_is is None

    def test_pagos_fraccionados_is(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl",
                          pagos_fraccionados_is=True)
        modelos = pf.modelos_obligatorios()
        assert "202" in modelos["trimestrales"]

    def test_recargo_equivalencia(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          regimen_iva="recargo_equivalencia",
                          regimen_irpf="directa_simplificada")
        assert pf.regimen_iva == "recargo_equivalencia"
```

**Step 2: Ejecutar test para verificar que falla**

```bash
pytest tests/test_perfil_fiscal.py -v
```

Expected: FAIL

**Step 3: Implementar PerfilFiscal**

```python
# sfce/core/perfil_fiscal.py
from dataclasses import dataclass, field
from typing import Optional

TERRITORIOS_IGIC = {"canarias"}
TERRITORIOS_IPSI = {"ceuta_melilla"}

@dataclass
class PerfilFiscal:
    """ADN contable de una entidad. Determina todo su comportamiento fiscal."""

    # Identidad
    tipo_persona: str = "juridica"
    forma_juridica: str = "sl"

    # Territorio
    territorio: str = "peninsula"

    # Regimen IVA
    regimen_iva: str = "general"
    prorrata: bool = False
    pct_prorrata: float = 100.0
    sectores_diferenciados: bool = False
    actividades: list = field(default_factory=list)

    # IRPF (solo fisicas)
    regimen_irpf: Optional[str] = None
    retencion_emitidas: bool = False
    pct_retencion_emitidas: Optional[float] = None

    # Modulos
    modulos: Optional[dict] = None

    # IS (solo juridicas)
    tipo_is: Optional[float] = None
    pagos_fraccionados_is: bool = False
    bases_negativas_pendientes: float = 0.0

    # Retenciones
    retiene_profesionales: bool = False
    retiene_alquileres: bool = False
    retiene_capital: bool = False
    paga_no_residentes: bool = False

    # Operaciones especiales
    operador_intracomunitario: bool = False
    importador: bool = False
    exportador: bool = False
    isp_construccion: bool = False
    isp_otros: bool = False
    operaciones_vinculadas: bool = False

    # Bienes de inversion
    tiene_bienes_inversion: bool = False
    amortizacion_metodo: str = "lineal"
    regularizacion_iva_bi: bool = False

    # Tamano
    sii_obligatorio: bool = False
    gran_empresa: bool = False
    deposita_cuentas: bool = False
    tipo_cuentas: Optional[str] = None

    # Plan contable
    plan_contable: str = "pgc_pymes"

    def __post_init__(self):
        """Aplicar restricciones logicas"""
        if self.tipo_persona == "juridica":
            self.regimen_irpf = None
            if self.tipo_is is None and self.forma_juridica not in (
                "comunidad_propietarios", "asociacion", "comunidad_bienes"
            ):
                self.tipo_is = 25  # Default IS
        elif self.tipo_persona == "fisica":
            self.tipo_is = None
            if self.regimen_irpf is None:
                self.regimen_irpf = "directa_simplificada"

    @property
    def impuesto_indirecto(self) -> str:
        if self.territorio in TERRITORIOS_IGIC:
            return "igic"
        if self.territorio in TERRITORIOS_IPSI:
            return "ipsi"
        return "iva"

    @property
    def periodicidad(self) -> str:
        return "mensual" if self.gran_empresa else "trimestral"

    def modelos_obligatorios(self) -> dict:
        """Deriva automaticamente los modelos fiscales obligatorios"""
        trimestrales = []
        anuales = []

        # IVA / IGIC
        sujeto_iva = self.forma_juridica not in ("comunidad_propietarios",)
        if sujeto_iva and self.regimen_iva != "exento":
            if self.impuesto_indirecto == "igic":
                trimestrales.append("420")
            else:
                trimestrales.append("303")
            anuales.append("390")

        # IRPF (fisicas)
        if self.regimen_irpf == "objetiva":
            trimestrales.append("131")
            anuales.append("100")
        elif self.regimen_irpf in ("directa_simplificada", "directa_normal"):
            trimestrales.append("130")
            anuales.append("100")

        # IS (juridicas)
        if self.tipo_is is not None:
            anuales.append("200")
        if self.pagos_fraccionados_is:
            trimestrales.append("202")

        # Retenciones
        if self.retiene_profesionales:
            trimestrales.append("111")
            anuales.append("190")
        if self.retiene_alquileres:
            trimestrales.append("115")
            anuales.append("180")
        if self.retiene_capital:
            trimestrales.append("123")
            anuales.append("193")

        # Operaciones especiales
        if self.operador_intracomunitario:
            trimestrales.append("349")
        if self.operaciones_vinculadas:
            anuales.append("232")
        if self.deposita_cuentas:
            anuales.append("cuentas_anuales")

        # 347 es condicional por importe, siempre potencial
        anuales.append("347")

        return {"trimestrales": trimestrales, "anuales": anuales}

    def libros_obligatorios(self) -> list:
        """Deriva los libros contables obligatorios"""
        libros = ["facturas_recibidas", "bienes_inversion"]

        if self.regimen_irpf == "objetiva":
            return libros  # Modulos: solo recibidas + BI

        libros.append("facturas_emitidas")

        if self.regimen_irpf == "directa_normal" or self.tipo_persona == "juridica":
            libros.extend(["diario", "inventario", "cuentas_anuales"])
        elif self.regimen_irpf == "directa_simplificada":
            libros.extend(["registro_ventas", "registro_compras"])

        if self.tipo_persona == "juridica":
            libros.extend(["actas", "socios"])

        return libros

    @classmethod
    def desde_dict(cls, datos: dict) -> "PerfilFiscal":
        """Crea PerfilFiscal desde un diccionario (ej: YAML config)"""
        campos_validos = {f.name for f in cls.__dataclass_fields__.values()}
        datos_filtrados = {k: v for k, v in datos.items() if k in campos_validos}
        return cls(**datos_filtrados)
```

**Step 4: Ejecutar tests**

```bash
pytest tests/test_perfil_fiscal.py -v
```

Expected: ALL PASS

**Step 5: Commit**

```bash
git add sfce/core/perfil_fiscal.py tests/test_perfil_fiscal.py
git commit -m "feat: modelo PerfilFiscal con derivacion automatica modelos/libros"
```

---

### Task 4: Crear YAML regimenes_iva.yaml y perfiles_fiscales.yaml

**Files:**
- Create: `sfce/reglas/pgc/regimenes_iva.yaml`
- Create: `sfce/reglas/pgc/perfiles_fiscales.yaml`

**Step 1: Crear regimenes_iva.yaml**

Catalogo de todos los regimenes IVA con sus subcuentas, comportamiento y particularidades. Incluye: general, simplificado, recargo_equivalencia, criterio_caja, exento, reagyp, agencias_viaje, bienes_usados. Para cada regimen: subcuentas IVA, como se contabiliza, como afecta al 303.

**Step 2: Crear perfiles_fiscales.yaml**

Plantillas de perfil fiscal por forma juridica. Cuando se da de alta un cliente nuevo y se indica "sl", se carga la plantilla base con los defaults correctos. El usuario solo modifica lo que difiere.

**Step 3: Commit**

```bash
git add sfce/reglas/pgc/
git commit -m "feat: catalogos YAML regimenes IVA y plantillas perfiles fiscales"
```

---

### Task 5: Integrar PerfilFiscal en ConfigCliente

**Files:**
- Modify: `sfce/core/config.py`
- Modify: `clientes/pastorino-costa-del-sol/config.yaml`
- Test: `tests/test_config_perfil.py`

**Step 1: Escribir test**

```python
# tests/test_config_perfil.py
from sfce.core.config import ConfigCliente, cargar_config

class TestConfigConPerfil:
    def test_config_con_perfil_fiscal(self):
        """Config con seccion perfil_fiscal carga PerfilFiscal"""
        config = cargar_config("pastorino-costa-del-sol")
        assert config.perfil_fiscal is not None
        assert config.perfil_fiscal.forma_juridica == "sl"

    def test_config_sin_perfil_usa_tipo_legacy(self):
        """Config sin perfil_fiscal genera uno desde campo 'tipo'"""
        # Config legacy solo tiene empresa.tipo = "sl"
        config_data = {
            "empresa": {"nombre": "Test SL", "cif": "B12345678",
                       "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"}
        }
        config = ConfigCliente(config_data, "test")
        assert config.perfil_fiscal.forma_juridica == "sl"
        assert config.perfil_fiscal.tipo_persona == "juridica"

    def test_modelos_desde_perfil(self):
        """modelos_trimestrales/anuales se derivan del perfil fiscal"""
        config = cargar_config("pastorino-costa-del-sol")
        modelos = config.perfil_fiscal.modelos_obligatorios()
        assert "303" in modelos["trimestrales"]
```

**Step 2: Ejecutar test para que falle**

```bash
pytest tests/test_config_perfil.py -v
```

**Step 3: Modificar ConfigCliente para soportar perfil_fiscal**

Anadir a `ConfigCliente.__init__()`:
- Si `data` tiene seccion `perfil_fiscal` → crear `PerfilFiscal.desde_dict(data["perfil_fiscal"])`
- Si no → generar perfil desde `empresa.tipo` (compatibilidad legacy)

**Step 4: Anadir seccion perfil_fiscal al config.yaml de Pastorino**

```yaml
perfil_fiscal:
  tipo_persona: juridica
  forma_juridica: sl
  territorio: peninsula
  regimen_iva: general
  retiene_profesionales: true
  operador_intracomunitario: true
  importador: true
  deposita_cuentas: true
  tipo_cuentas: pymes
```

**Step 5: Ejecutar tests**

```bash
pytest tests/test_config_perfil.py tests/test_normativa.py tests/test_perfil_fiscal.py -v
```

Expected: ALL PASS

**Step 6: Verificar pipeline no se rompio**

```bash
pytest tests/ -v
```

Expected: 88 + nuevos PASS

**Step 7: Commit**

```bash
git add sfce/core/config.py clientes/pastorino-costa-del-sol/config.yaml tests/test_config_perfil.py
git commit -m "feat: integrar PerfilFiscal en ConfigCliente con compatibilidad legacy"
```

---

### Task 6: Crear capa de abstraccion backend.py

**Files:**
- Create: `sfce/core/backend.py`
- Test: `tests/test_backend.py`

**Step 1: Escribir test**

```python
# tests/test_backend.py
from unittest.mock import MagicMock, patch
from sfce.core.backend import Backend

class TestBackend:
    def test_crear_backend_con_fs(self):
        backend = Backend(modo="fs")
        assert backend.modo == "fs"

    def test_crear_factura_delega_a_fs(self):
        backend = Backend(modo="fs")
        with patch("sfce.core.fs_api.api_post") as mock_post:
            mock_post.return_value = {"doc": {"idfactura": 123}}
            resultado = backend.crear_factura({"datos": "test"}, "proveedor")
            assert mock_post.called

    def test_crear_asiento_delega_a_fs(self):
        backend = Backend(modo="fs")
        with patch("sfce.core.fs_api.api_post") as mock_post:
            mock_post.return_value = {"ok": "ok", "data": {"idasiento": "456"}}
            resultado = backend.crear_asiento({"partidas": []})
            assert mock_post.called

    def test_interfaz_completa(self):
        """Backend tiene todos los metodos requeridos"""
        backend = Backend(modo="fs")
        metodos = ["crear_factura", "crear_asiento", "obtener_subcuentas",
                   "crear_proveedor", "crear_cliente", "obtener_saldo"]
        for metodo in metodos:
            assert hasattr(backend, metodo), f"Falta metodo: {metodo}"
```

**Step 2: Ejecutar test para que falle**

```bash
pytest tests/test_backend.py -v
```

**Step 3: Implementar Backend**

```python
# sfce/core/backend.py
"""Capa de abstraccion sobre FacturaScripts.
Todo el pipeline habla con Backend, nunca directamente con fs_api.
Si manana se cambia FS por Odoo/Holded/BD propia, solo se toca este modulo."""

from sfce.core import fs_api

class Backend:
    def __init__(self, modo: str = "fs", token: str | None = None):
        self.modo = modo
        self._token = token or fs_api.obtener_token()

    def crear_factura(self, datos: dict, tipo: str = "proveedor") -> dict:
        endpoint = "crearFacturaProveedor" if tipo == "proveedor" else "crearFacturaCliente"
        return fs_api.api_post(endpoint, datos, self._token)

    def crear_asiento(self, datos: dict) -> dict:
        return fs_api.api_post("asientos", datos, self._token)

    def crear_partida(self, datos: dict) -> dict:
        return fs_api.api_post("partidas", datos, self._token)

    def obtener_subcuentas(self, empresa_id: int) -> list:
        todas = fs_api.api_get("subcuentas", {}, self._token)
        return [s for s in todas if s.get("idempresa") == empresa_id]

    def crear_proveedor(self, datos: dict) -> dict:
        return fs_api.api_post("proveedores", datos, self._token)

    def crear_cliente(self, datos: dict) -> dict:
        return fs_api.api_post("clientes", datos, self._token)

    def obtener_saldo(self, subcuenta: str, empresa_id: int) -> float:
        partidas = fs_api.api_get("partidas", {}, self._token)
        # Post-filtrar por empresa via asientos
        total_debe = sum(float(p.get("debe", 0)) for p in partidas
                        if p.get("codsubcuenta") == subcuenta)
        total_haber = sum(float(p.get("haber", 0)) for p in partidas
                         if p.get("codsubcuenta") == subcuenta)
        return total_debe - total_haber

    def actualizar_factura(self, idfactura: int, datos: dict, tipo: str = "proveedor") -> dict:
        endpoint = f"facturaproveedores/{idfactura}" if tipo == "proveedor" else f"facturaclientes/{idfactura}"
        return fs_api.api_put(endpoint, datos, self._token)

    def actualizar_partida(self, idpartida: int, datos: dict) -> dict:
        return fs_api.api_put(f"partidas/{idpartida}", datos, self._token)

    def obtener_asientos(self, empresa_id: int) -> list:
        todos = fs_api.api_get("asientos", {}, self._token)
        return [a for a in todos if a.get("idempresa") == empresa_id]
```

**Step 4: Ejecutar tests**

```bash
pytest tests/test_backend.py -v
```

Expected: ALL PASS

**Step 5: Commit**

```bash
git add sfce/core/backend.py tests/test_backend.py
git commit -m "feat: capa abstraccion Backend sobre FacturaScripts"
```

---

### Task 7: Crear DecisionContable y estructura base del motor

**Files:**
- Create: `sfce/core/decision.py`
- Test: `tests/test_decision.py`

**Step 1: Escribir test**

```python
# tests/test_decision.py
from sfce.core.decision import DecisionContable, Partida

class TestDecisionContable:
    def test_crear_decision_basica(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21",
            tipo_iva=21.0,
            confianza=95,
            origen_decision="regla_cliente"
        )
        assert decision.confianza == 95
        assert decision.cuarentena is False

    def test_cuarentena_baja_confianza(self):
        decision = DecisionContable(
            subcuenta_gasto="6220000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21",
            tipo_iva=21.0,
            confianza=50,
            origen_decision="ocr_keywords"
        )
        assert decision.cuarentena is True

    def test_generar_partidas_factura_general(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21",
            tipo_iva=21.0,
            confianza=95,
            origen_decision="regla_cliente"
        )
        partidas = decision.generar_partidas(base=1000.0)
        assert len(partidas) == 3  # gasto + IVA + proveedor
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01

    def test_generar_partidas_con_retencion(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4300000001",
            codimpuesto="IVA21",
            tipo_iva=21.0,
            retencion_pct=15.0,
            confianza=95,
            origen_decision="regla_cliente"
        )
        partidas = decision.generar_partidas(base=1000.0)
        # gasto + IVA + retencion + cliente
        assert len(partidas) == 4

    def test_generar_partidas_recargo_equivalencia(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21",
            tipo_iva=21.0,
            recargo_equiv=5.2,
            confianza=95,
            origen_decision="regla_cliente"
        )
        partidas = decision.generar_partidas(base=1000.0)
        # gasto + IVA + recargo + proveedor
        assert len(partidas) == 4

    def test_generar_partidas_isp(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA0",
            tipo_iva=0.0,
            isp=True,
            isp_tipo_iva=21.0,
            confianza=95,
            origen_decision="regla_cliente"
        )
        partidas = decision.generar_partidas(base=1000.0)
        # gasto + IVA soportado + IVA repercutido + proveedor
        assert len(partidas) == 4
```

**Step 2: Ejecutar test para que falle**

```bash
pytest tests/test_decision.py -v
```

**Step 3: Implementar DecisionContable con generacion de partidas**

Crear `sfce/core/decision.py` con dataclasses `Partida` y `DecisionContable`.
- `DecisionContable.generar_partidas(base)` genera las partidas del asiento segun el regimen.
- Soporta: general, con retencion, recargo equivalencia, ISP (intracomunitario/domestico), criterio de caja.
- Cuarentena automatica si confianza < 70.

**Step 4: Ejecutar tests**

```bash
pytest tests/test_decision.py -v
```

Expected: ALL PASS

**Step 5: Commit**

```bash
git add sfce/core/decision.py tests/test_decision.py
git commit -m "feat: DecisionContable con generacion partidas multi-regimen"
```

---

### Task 8: Tests integracion Fase A + verificar pipeline existente

**Files:**
- Create: `tests/test_integracion_fase_a.py`

**Step 1: Escribir test de integracion**

```python
# tests/test_integracion_fase_a.py
"""Verifica que todos los componentes de Fase A funcionan juntos
y que el pipeline existente no se rompio."""
from datetime import date
from sfce.normativa.vigente import Normativa
from sfce.core.perfil_fiscal import PerfilFiscal
from sfce.core.decision import DecisionContable
from sfce.core.config import cargar_config

class TestIntegracionFaseA:
    def test_normativa_alimenta_decision(self):
        """Normativa → DecisionContable usa tipo IVA correcto"""
        n = Normativa()
        iva = n.iva_general(date(2025, 6, 15))
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21",
            tipo_iva=iva,
            confianza=95,
            origen_decision="test"
        )
        partidas = decision.generar_partidas(base=1000.0)
        iva_partida = [p for p in partidas if "472" in p.subcuenta][0]
        assert iva_partida.debe == 210.0  # 21% de 1000

    def test_perfil_pastorino_coherente(self):
        """Config Pastorino con perfil fiscal genera modelos correctos"""
        config = cargar_config("pastorino-costa-del-sol")
        modelos = config.perfil_fiscal.modelos_obligatorios()
        assert "303" in modelos["trimestrales"]
        assert "200" in modelos["anuales"]

    def test_pipeline_imports_no_rotos(self):
        """Verificar que el pipeline puede importar todas las fases"""
        from sfce.phases import intake
        from sfce.phases import pre_validation
        from sfce.phases import registration
        from sfce.phases import asientos
        from sfce.phases import correction
        from sfce.phases import cross_validation
        from sfce.phases import output
```

**Step 2: Ejecutar TODOS los tests**

```bash
pytest tests/ -v
```

Expected: 88 existentes + ~40 nuevos = ALL PASS

**Step 3: Commit final Fase A**

```bash
git add tests/test_integracion_fase_a.py
git commit -m "test: integracion Fase A — normativa + perfil + decision + pipeline"
```

---

## FASE B: MOTOR CENTRAL (Tasks 9-16)

### Task 9: Crear clasificador contable

**Files:**
- Create: `sfce/core/clasificador.py`
- Create: `sfce/reglas/pgc/palabras_clave_subcuentas.yaml`
- Test: `tests/test_clasificador.py`

Implementar la cascada de 6 niveles de clasificacion:
1. Regla cliente explicita (CIF→subcuenta en config) — confianza 95%
2. Aprendizaje previo (CIF visto antes en aprendizaje.yaml) — confianza 85%
3. Tipo documento (NOM→640, SUM→628, SEG→625) — confianza 80%
4. Palabras clave OCR ("alquiler"→621) — confianza 60%
5. Libro diario importado — confianza 75%
6. Cuarentena

Tests: un test por cada nivel de la cascada + test de fallback a cuarentena + test de confianza <70% va a cuarentena.

---

### Task 10: Crear MotorReglas (nucleo del sistema)

**Files:**
- Create: `sfce/core/motor_reglas.py`
- Test: `tests/test_motor_reglas.py`

Implementar:
- `__init__`: carga los 6 niveles (normativa, pgc, perfil, negocio, cliente, aprendizaje)
- `decidir_asiento(documento)`: consulta clasificador + normativa → DecisionContable
- `validar_asiento(asiento)`: verifica contra reglas
- `aprender(documento, decision_humana)`: registra en nivel 5

Tests: ~15 tests cubriendo cada regimen IVA:
- Factura proveedor regimen general
- Factura con retencion profesional
- Factura intracomunitaria (ISP)
- Factura ISP domestica (construccion)
- Factura recargo equivalencia
- Factura criterio de caja (devengada vs cobrada)
- Nomina → subcuenta 640
- Suministro → subcuenta 628
- Documento desconocido → cuarentena
- Conflicto nivel 5 vs nivel 0 → gana nivel 0

---

### Task 11: Integrar MotorReglas en registration.py

**Files:**
- Modify: `sfce/phases/registration.py`
- Test: `tests/test_registration_motor.py`

Refactorizar `_construir_form_data()` para que use `motor.decidir_asiento()` en vez de la logica actual con `if regimen == "intracomunitario"`.

Mantener compatibilidad: si el motor no esta disponible (ej: tests antiguos), usar logica legacy.

Tests: verificar que el resultado es identico al actual para Pastorino (regression test).

---

### Task 12: Integrar MotorReglas en correction.py

**Files:**
- Modify: `sfce/phases/correction.py`
- Test: `tests/test_correction_motor.py`

Refactorizar handlers para que usen `motor.validar_asiento()`.

Los 7 checks actuales se convierten en reglas del motor.

---

### Task 13: Integrar MotorReglas en asientos_directos.py

**Files:**
- Modify: `sfce/core/asientos_directos.py`
- Test: `tests/test_asientos_directos_motor.py`

Las plantillas fijas de `subcuentas_tipos.yaml` se generan dinamicamente via `motor.decidir_asiento()`. El motor consulta el perfil fiscal para adaptar subcuentas segun tipo de entidad.

---

### Task 14: Derivacion de modelos fiscales via motor

**Files:**
- Modify: `sfce/phases/output.py`
- Create: `sfce/core/calculador_modelos.py`
- Test: `tests/test_calculador_modelos.py`

Implementar `motor.calcular_modelo("303", "T1")` que calcula el modelo fiscal completo desde los datos registrados. Reemplaza la logica de `generar_modelos_fiscales.py`.

Tests: verificar que modelo 303 T3 calculado coincide con el de Pastorino.

---

### Task 15: Pipeline usa MotorReglas como orquestador de decisiones

**Files:**
- Modify: `scripts/pipeline.py`
- Modify: `sfce/phases/*.py` (ajustes menores)

El pipeline crea el MotorReglas al inicio y lo pasa a cada fase.
Cada fase recibe `motor` como parametro en vez de construir su propia logica.

---

### Task 16: Tests integracion Fase B + regression completa

**Files:**
- Create: `tests/test_integracion_fase_b.py`

Test end-to-end: simular pipeline completo de una factura desde intake hasta output usando MotorReglas. Verificar que el resultado es identico al sistema actual para los mismos inputs.

Ejecutar 88 tests existentes + todos los nuevos.

---

## FASE C: DATOS Y PERSISTENCIA (Tasks 17-23)

### Task 17: Crear modelos SQLAlchemy para BD local

**Files:**
- Create: `sfce/db/modelos.py`
- Create: `sfce/db/base.py`
- Test: `tests/test_db_modelos.py`

Tablas: empresas, proveedores_clientes, documentos, asientos, partidas, facturas, saldos_subcuenta, cuarentena, aprendizaje_log.

Tests: crear tablas en SQLite in-memory, insertar datos, verificar constraints.

---

### Task 18: Crear repositorio (queries)

**Files:**
- Create: `sfce/db/repositorio.py`
- Test: `tests/test_repositorio.py`

CRUD para cada tabla + queries especializadas:
- `saldo_subcuenta(empresa, subcuenta)` — suma debe/haber de partidas
- `pyg(empresa, desde, hasta)` — ingresos (7x) - gastos (6x)
- `balance(empresa, fecha)` — activo/pasivo/patrimonio
- `facturas_pendientes_pago(empresa)` — pagada=False
- `documentos_cuarentena(empresa)` — pendientes decision

---

### Task 19: Integrar BD local en Backend (doble destino)

**Files:**
- Modify: `sfce/core/backend.py`
- Test: `tests/test_backend_db.py`

Backend ahora guarda en BD local Y envia a FS.
Si FS falla → marca pendiente_sync.
Funcion `sincronizar()` para reintentar pendientes.

---

### Task 20: Crear importador de libro diario

**Files:**
- Create: `sfce/core/importador.py`
- Test: `tests/test_importador.py`

Parser flexible para CSV/Excel:
- Deteccion automatica de columnas (fecha, cuenta, debe, haber, concepto)
- Extraccion mapa CIF → subcuenta (con frecuencia)
- Generacion config.yaml propuesto
- Soporte separadores `,` `;` `\t`, encodings UTF-8/ISO-8859-1

Tests: crear CSV de prueba con 20 asientos, verificar que extrae mapeo correcto.

---

### Task 21: Crear exportador universal

**Files:**
- Create: `sfce/core/exportador.py`
- Test: `tests/test_exportador.py`

Formatos:
- CSV libro diario (separador/encoding configurables)
- Excel multi-hoja (diario + balance + PyG + libros IVA)
- CSV facturas emitidas/recibidas

Tests: generar CSV con 10 asientos, verificar formato y totales.

---

### Task 22: Migrar datos existentes de FS a BD local

**Files:**
- Create: `scripts/migrar_fs_a_bd.py`

Script one-time que lee todos los datos de FS via API y los carga en BD local.
Para cada empresa: facturas, asientos, partidas, proveedores, clientes.

---

### Task 23: Tests integracion Fase C

**Files:**
- Create: `tests/test_integracion_fase_c.py`

Test end-to-end: procesar factura → verificar en BD local + FS.
Test importador → verificar config generado.
Test exportador → verificar CSV/Excel valido.

---

## FASE D: INTERFAZ Y PRODUCTO (Tasks 24-32)

### Task 24: Crear API FastAPI (estructura base)

**Files:**
- Create: `sfce/api/app.py`
- Create: `sfce/api/rutas/__init__.py`
- Create: `sfce/api/rutas/empresas.py`
- Create: `sfce/api/rutas/documentos.py`
- Create: `sfce/api/rutas/contabilidad.py`

Endpoints REST:
- `GET /api/empresas` — listar empresas
- `GET /api/empresas/{id}/pyg` — PyG tiempo real
- `GET /api/empresas/{id}/balance` — Balance tiempo real
- `GET /api/empresas/{id}/diario` — Libro diario paginado
- `GET /api/empresas/{id}/modelos/{modelo}` — Modelo fiscal calculado
- `GET /api/empresas/{id}/cuarentena` — Docs en cuarentena
- `POST /api/empresas/{id}/cuarentena/{doc_id}/resolver` — Resolver cuarentena
- `POST /api/empresas/{id}/procesar` — Lanzar pipeline
- `GET /api/empresas/{id}/exportar` — Exportar CSV/Excel

---

### Task 25: WebSocket para eventos tiempo real

**Files:**
- Create: `sfce/api/websocket.py`

Eventos:
- `pipeline_progress` — progreso del pipeline
- `documento_procesado` — nuevo doc registrado
- `cuarentena_nuevo` — doc en cuarentena
- `saldo_actualizado` — cambio en saldo subcuenta

---

### Task 26: Scaffolding dashboard React

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/vite.config.ts`
- Create: `dashboard/tailwind.config.ts`
- Create: `dashboard/src/App.tsx`
- Create: `dashboard/src/main.tsx`

Setup basico: React 18 + TypeScript + Tailwind + Vite.
Router con rutas para cada pantalla del design doc.

---

### Task 27: Dashboard — Vista general + empresas

**Files:**
- Create: `dashboard/src/pages/Home.tsx`
- Create: `dashboard/src/pages/Empresa.tsx`
- Create: `dashboard/src/components/EmpresaCard.tsx`

Home con lista de empresas, estado de cada una, alertas.
Pagina de empresa con tabs para cada seccion.

---

### Task 28: Dashboard — Contabilidad (PyG, Balance, Diario)

**Files:**
- Create: `dashboard/src/pages/PyG.tsx`
- Create: `dashboard/src/pages/Balance.tsx`
- Create: `dashboard/src/pages/Diario.tsx`

Graficos y tablas en tiempo real. WebSocket para actualizaciones.

---

### Task 29: Dashboard — Procesamiento (Inbox, Pipeline, Cuarentena)

**Files:**
- Create: `dashboard/src/pages/Inbox.tsx`
- Create: `dashboard/src/pages/Pipeline.tsx`
- Create: `dashboard/src/pages/Cuarentena.tsx`

Inbox con lista de PDFs pendientes y boton procesar.
Pipeline con barra de progreso en tiempo real.
Cuarentena con opciones del motor y boton resolver.

---

### Task 30: Dashboard — Herramientas (Importar, Exportar, Calendario)

**Files:**
- Create: `dashboard/src/pages/Importar.tsx`
- Create: `dashboard/src/pages/Exportar.tsx`
- Create: `dashboard/src/pages/Calendario.tsx`

Wizard de importacion libro diario.
Exportacion con seleccion de formato.
Calendario fiscal con plazos por empresa.

---

### Task 31: File watcher

**Files:**
- Create: `scripts/watcher.py`
- Test: `tests/test_watcher.py`

Demonio con `watchdog` que vigila `clientes/*/inbox/`.
3 modos: manual, semi-auto, automatico.
Configurable por cliente en config.yaml.

---

### Task 32: Sistema de licencias

**Files:**
- Create: `sfce/core/licencia.py`
- Test: `tests/test_licencia.py`

Generacion de licencias firmadas con fecha expiracion.
Verificacion al arrancar SFCE.
Token por cliente para OCR proxy.

---

## FASE E: INGESTA INTELIGENTE Y NOTIFICACIONES (Tasks 33-38)

### Task 33: Convencion de nombres carpetas y documentos

**Files:**
- Create: `sfce/core/nombres.py`
- Modify: `sfce/core/config.py` (rutas con nuevo formato)
- Modify: `scripts/onboarding.py` (crear carpetas con CIF)
- Test: `tests/test_nombres.py`

Implementar:
- `generar_slug_cliente(cif, nombre) -> str` → `"B13995519-pastorino-costa-del-sol"`
- `renombrar_documento(datos_ocr) -> str` → `"FC_2025-06-15_B99999999_acme-sl_1210.00.pdf"`
- Crear carpeta `clientes/_sin_clasificar/` con `pendientes.json`
- Estructura estandar: inbox/, procesado/, cuarentena/, exportaciones/

Tests: verificar slugs, renombrado, caracteres especiales, duplicados de nombre.

---

### Task 34: Cache OCR reutilizable

**Files:**
- Create: `sfce/core/cache_ocr.py`
- Modify: `sfce/phases/intake.py` (verificar cache antes de OCR)
- Test: `tests/test_cache_ocr.py`

Implementar:
- `guardar_cache(ruta_pdf, datos_ocr)` → crea `.ocr.json` junto al PDF
- `cargar_cache(ruta_pdf) -> dict | None` → lee cache si existe y hash coincide
- Hash SHA256 del PDF para invalidar cache si cambia
- Intake verifica cache antes de llamar a Mistral/GPT

Tests: guardar/cargar cache, invalidacion por hash, reutilizacion en pipeline.

---

### Task 35: Deteccion de duplicados

**Files:**
- Create: `sfce/core/duplicados.py`
- Modify: `sfce/phases/pre_validation.py` (check duplicados)
- Test: `tests/test_duplicados.py`

Implementar:
- Duplicado seguro: mismo CIF + numero factura + fecha → rechazar
- Posible duplicado: mismo CIF + importe + fecha cercana (±5 dias) → cuarentena
- Consulta BD local para historico

Tests: duplicado exacto, duplicado parcial, falso positivo (mismo proveedor distinta factura).

---

### Task 36: Ingesta por email (IMAP)

**Files:**
- Create: `sfce/core/ingesta_email.py`
- Create: `scripts/leer_correo.py` (CLI/demonio)
- Test: `tests/test_ingesta_email.py`

Implementar:
- Conexion IMAP a buzon configurable
- Descargar adjuntos PDF de emails no leidos
- OCR rapido (Mistral tier 0) para clasificar
- Enrutar a carpeta cliente (por CIF en BD o por email remitente en config)
- Si no se identifica → `_sin_clasificar/`
- Marcar email como leido
- Guardar `.ocr.json` (cache reutilizable)

Config en `sfce/config_global.yaml`:
```yaml
ingesta_email:
  servidor: imap.gmail.com
  puerto: 993
  usuario: facturas@tudominio.com
  password_env: SFCE_EMAIL_PASSWORD
  carpeta: INBOX
  intervalo_minutos: 5
```

Tests: mock IMAP, verificar enrutamiento por CIF, por email, a sin_clasificar.

---

### Task 37: Sistema de notificaciones

**Files:**
- Create: `sfce/core/notificaciones.py`
- Modify: `sfce/api/websocket.py` (emitir eventos)
- Test: `tests/test_notificaciones.py`

Implementar:
- Canal email: `enviar_email(destinatario, asunto, cuerpo, adjuntos)`
- Canal dashboard: evento WebSocket
- Plantillas email: documento_ilegible, proveedor_nuevo, plazo_fiscal, informe_mensual
- Configuracion por cliente: `emails_autorizados` en config.yaml
- Registro de notificaciones enviadas en BD (no repetir)

Tests: mock SMTP, verificar plantillas, verificar no-repeticion.

---

### Task 38: Deteccion facturas recurrentes faltantes

**Files:**
- Create: `sfce/core/recurrentes.py`
- Test: `tests/test_recurrentes.py`

Implementar:
- Analizar historico BD: proveedores con patron mensual/trimestral
- Detectar patron: "Telefonica ~80€ cada mes"
- Si falta factura esperada → generar alerta
- Requiere minimo 3 ocurrencias para detectar patron

Tests: patron mensual detectado, patron trimestral, falso positivo descartado.

---

## Resumen de esfuerzo estimado

| Fase | Tasks | Tests nuevos | Sesiones estimadas |
|------|-------|-------------|-------------------|
| A — Fundamentos | 1-8 | ~50 | 3-4 |
| B — Motor central | 9-16 | ~40 | 4-5 |
| C — Datos | 17-23 | ~30 | 3-4 |
| D — Interfaz | 24-32 | ~20 | 5-6 |
| E — Ingesta inteligente | 33-38 | ~25 | 3-4 |
| **Total** | **38 tasks** | **~165 tests** | **18-23 sesiones** |

## Orden de ejecucion recomendado

```
Fase A (fundamentos) → OBLIGATORIO primero
    ↓
Fase B (motor) → OBLIGATORIO segundo
    ↓
Fase C (datos) ←→ Fase D (interfaz) ←→ Fase E (ingesta) → PUEDEN ir en paralelo
```

Despues de Fase B, el pipeline ya soporta todos los regimenes fiscales. Fases C, D y E anaden persistencia, interfaz e ingesta inteligente, que son independientes entre si.

## Backlog post-implementacion (futuro)

| Feature | Prioridad | Dependencia |
|---------|-----------|-------------|
| WhatsApp/Telegram bot | Alta | Fase E (ingesta) |
| Open Banking PSD2 (extractos auto) | Muy alta | Fase C (BD) |
| Verifactu (antifraude) | Obligatorio (2026) | Fase B (motor) |
| QR pre-OCR en facturas | Media | Fase B (intake) |
| Portal web cliente (upload+consulta) | Alta | Fase D (dashboard) |
| Informe mensual automatico | Alta | Fase E (notificaciones) |
| Validacion CIF contra AEAT | Media | Fase B |
| Prevision tesoreria 3-6 meses | Alta | Fase C (BD) |
| Comparativa interanual | Media | Fase C (BD) |
| Facturacion automatica al cliente | Media | Fase D |
| KPIs de la gestoria | Media | Fase D |
| Acceso lectura dashboard clientes | Alta | Fase D |
| Tracking certificados/seguros | Media | Fase C (BD) |
