# SFCE Evolucion v2 — Plan de Implementacion

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactorizar SFCE hacia un motor de reglas contables universal que soporte todos los casos fiscales espanoles (todos los territorios, todos los regimenes), con ciclo contable completo (cierre, amortizaciones, provisiones), BD local dual (SQLite/PostgreSQL), dashboard en tiempo real, trazabilidad de decisiones y capacidad de despliegue como producto SaaS.

**Architecture:** Motor de reglas centralizado con jerarquia de 6 niveles (normativa > PGC > perfil > negocio > cliente > aprendizaje). Normativa versionada por ano y territorio (peninsula, canarias, ceuta_melilla, navarra, pais_vasco). Capa de abstraccion sobre FS con doble destino (BD local + FS). Dashboard React+FastAPI con WebSocket. Trazabilidad completa: cada asiento incluye log de razonamiento. Cuarentena estructurada con preguntas tipadas.

**Tech Stack:** Python 3.11+, SQLAlchemy + SQLite/PostgreSQL (dual), FastAPI + uvicorn, React 18 + TypeScript + Tailwind + Vite, WebSocket, watchdog, PyYAML, openpyxl, PyJWT

**Design doc:** `docs/plans/2026-02-27-sfce-evolucion-v2-design.md`

**Estado actual del codigo:**
- Motor SFCE en `scripts/core/` (14 modulos) + `scripts/phases/` (9 modulos)
- 88+ tests pasando en `tests/`
- Config via YAML en `clientes/*/config.yaml`
- Reglas en `reglas/` (9 YAMLs)
- Pipeline via `scripts/pipeline.py`
- Sin pyproject.toml ni estructura de paquete

---

## Organizacion en 5 fases (46 tasks)

| Fase | Nombre | Tasks | Descripcion |
|------|--------|-------|-------------|
| **A** | Fundamentos | 1-10 | Reorganizar, normativa multi-territorio, perfil fiscal, backend, decision con trazabilidad, operaciones periodicas, cierre ejercicio |
| **B** | Motor central | 11-19 | Clasificador, motor reglas, refactorizar pipeline, modelos fiscales 3 categorias, notas credito |
| **C** | Datos y persistencia | 20-27 | BD dual SQLite/PostgreSQL, 13 tablas, repositorio, importador, exportador |
| **D** | Interfaz y producto | 28-37 | API FastAPI, JWT auth, WebSocket, dashboard React, watcher, licencia |
| **E** | Ingesta inteligente | 38-46 | Naming, cache OCR, duplicados, trabajadores nuevos, IMAP, notificaciones, recurrentes, periodicas auto |

**Cada fase es independiente y desplegable.** El pipeline existente DEBE seguir funcionando despues de cada task.

**IMPORTANTE:** Despues de Fase B, el pipeline soporta todos los regimenes fiscales. Fases C, D y E son independientes entre si.

---

## FASE A: FUNDAMENTOS (Tasks 1-10)

### Task 1: Crear estructura de paquete Python + reorganizar directorios

**Files:**
- Create: `sfce/__init__.py`, `sfce/core/__init__.py`, `sfce/phases/__init__.py`, `sfce/normativa/__init__.py`, `sfce/reglas/__init__.py`
- Create: `pyproject.toml`
- Modify: todos los archivos en `scripts/core/` y `scripts/phases/` (mover + wrapper)

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
api = ["fastapi>=0.110", "uvicorn>=0.27", "websockets>=12.0", "pyjwt>=2.8"]
dev = ["pytest>=8.0", "pytest-cov>=4.1"]

[tool.setuptools.packages.find]
include = ["sfce*"]
```

**Step 2: Crear estructura de directorios sfce/**

```bash
mkdir -p sfce/core sfce/phases sfce/normativa sfce/reglas/pgc sfce/reglas/negocio sfce/reglas/aprendizaje sfce/db sfce/api/rutas
```

**Step 3: Copiar modulos core de scripts/core/ a sfce/core/**

Copiar cada archivo. Actualizar imports internos: `from scripts.core.X` -> `from sfce.core.X`.

**Step 4: Crear wrappers de compatibilidad en scripts/core/**

Para que el pipeline existente siga funcionando:

```python
# scripts/core/config.py (wrapper)
from sfce.core.config import *
from sfce.core.config import ConfigCliente, cargar_config, validar_config
```

Repetir para cada modulo.

**Step 5: Copiar phases de scripts/phases/ a sfce/phases/**

Actualizar imports internos. Crear wrappers en scripts/phases/.

**Step 6: Copiar reglas YAML a sfce/reglas/**

```
reglas/subcuentas_pgc.yaml -> sfce/reglas/pgc/
reglas/subcuentas_tipos.yaml -> sfce/reglas/pgc/
reglas/tipos_entidad.yaml -> sfce/reglas/pgc/
reglas/tipos_retencion.yaml -> sfce/reglas/pgc/
reglas/coherencia_fiscal.yaml -> sfce/reglas/pgc/
reglas/patrones_suplidos.yaml -> sfce/reglas/pgc/
reglas/validaciones.yaml -> sfce/reglas/negocio/
reglas/errores_conocidos.yaml -> sfce/reglas/negocio/
reglas/aprendizaje.yaml -> sfce/reglas/aprendizaje/
```

**Step 7: Instalar paquete en modo desarrollo**

```bash
pip install -e .
```

**Step 8: Ejecutar tests para verificar que nada se rompio**

```bash
pytest tests/ -v
```

Expected: 88+ PASS

**Step 9: Commit**

```bash
git commit -m "refactor: reorganizar codigo en paquete sfce/"
```

---

### Task 2: Crear modulo normativa/ con YAML 2025 multi-territorio

**Files:**
- Create: `sfce/normativa/2025.yaml`
- Create: `sfce/normativa/vigente.py`
- Test: `tests/test_normativa.py`

**Step 1: Escribir tests**

```python
# tests/test_normativa.py
from datetime import date
from sfce.normativa.vigente import Normativa

class TestNormativa:
    def setup_method(self):
        self.n = Normativa()

    # --- Peninsula ---
    def test_iva_general_peninsula(self):
        assert self.n.iva_general(date(2025, 6, 15)) == 21.0

    def test_iva_reducido_peninsula(self):
        assert self.n.iva_reducido(date(2025, 6, 15)) == 10.0

    def test_iva_superreducido_peninsula(self):
        assert self.n.iva_superreducido(date(2025, 6, 15)) == 4.0

    def test_recargo_equivalencia_general(self):
        assert self.n.recargo_equivalencia("general", date(2025, 6, 15)) == 5.2

    def test_tipo_is_general_peninsula(self):
        assert self.n.tipo_is("general", date(2025, 6, 15)) == 25

    def test_tipo_is_pymes_peninsula(self):
        assert self.n.tipo_is("pymes", date(2025, 6, 15)) == 23

    def test_retencion_profesional(self):
        assert self.n.retencion_profesional(False, date(2025, 6, 15)) == 15

    def test_retencion_profesional_nuevo(self):
        assert self.n.retencion_profesional(True, date(2025, 6, 15)) == 7

    def test_umbral_modelo_347(self):
        assert self.n.umbral("modelo_347", date(2025, 6, 15)) == 3005.06

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

    def test_ss_cc_empresa(self):
        ss = self.n.seguridad_social(date(2025, 6, 15))
        assert ss["tipo_contingencias_comunes_empresa"] == 23.60

    # --- Canarias (IGIC) ---
    def test_igic_general(self):
        imp = self.n.impuesto_indirecto(date(2025, 6, 15), "canarias")
        assert imp["general"] == 7

    def test_igic_reducido(self):
        imp = self.n.impuesto_indirecto(date(2025, 6, 15), "canarias")
        assert imp["reducido"] == 3

    def test_igic_tipo_cero(self):
        imp = self.n.impuesto_indirecto(date(2025, 6, 15), "canarias")
        assert imp["tipo_cero"] == 0

    # --- Navarra ---
    def test_is_navarra(self):
        assert self.n.tipo_is("general", date(2025, 6, 15), "navarra") == 28

    def test_is_navarra_micro(self):
        assert self.n.tipo_is("micro", date(2025, 6, 15), "navarra") == 20

    def test_irpf_navarra_primer_tramo(self):
        tabla = self.n.tabla_irpf(date(2025, 6, 15), "navarra")
        assert tabla[0]["tipo"] == 13

    # --- Pais Vasco ---
    def test_is_pais_vasco(self):
        assert self.n.tipo_is("general", date(2025, 6, 15), "pais_vasco") == 24

    def test_irpf_pais_vasco_primer_tramo(self):
        tabla = self.n.tabla_irpf(date(2025, 6, 15), "pais_vasco")
        assert tabla[0]["tipo"] == 23

    # --- Ceuta y Melilla (IPSI) ---
    def test_ipsi_general(self):
        imp = self.n.impuesto_indirecto(date(2025, 6, 15), "ceuta_melilla")
        assert imp["tipo_6"] == 10.0

    # --- Fallback ---
    def test_ano_no_existente_usa_mas_reciente(self):
        resultado = self.n.iva_general(date(2030, 1, 1))
        assert isinstance(resultado, float)

    def test_territorio_default_es_peninsula(self):
        assert self.n.tipo_is("general", date(2025, 6, 15)) == 25
```

**Step 2: Ejecutar test para que falle**

```bash
pytest tests/test_normativa.py -v
```

Expected: FAIL

**Step 3: Crear YAML 2025 completo multi-territorio**

Crear `sfce/normativa/2025.yaml` con estructura completa segun design doc v2 seccion 6: peninsula, canarias (IGIC), ceuta_melilla (IPSI), navarra, pais_vasco, seguridad_social (comun), umbrales, plazos_presentacion, amortizacion.

**Step 4: Implementar vigente.py con parametro territorio**

```python
# sfce/normativa/vigente.py
import yaml
from datetime import date
from pathlib import Path

class Normativa:
    """Fuente unica de verdad fiscal. Consulta parametros por fecha y territorio."""

    def __init__(self, directorio: Path | None = None):
        self._directorio = directorio or Path(__file__).parent
        self._cache = {}

    def _cargar_ano(self, ano: int) -> dict:
        if ano in self._cache:
            return self._cache[ano]
        ruta = self._directorio / f"{ano}.yaml"
        if not ruta.exists():
            yamls = sorted(self._directorio.glob("20*.yaml"), reverse=True)
            if not yamls:
                raise FileNotFoundError("No hay normativa disponible")
            ruta = yamls[0]
        with open(ruta, "r", encoding="utf-8") as f:
            datos = yaml.safe_load(f)
        self._cache[ano] = datos
        return datos

    def _datos(self, fecha: date) -> dict:
        return self._cargar_ano(fecha.year)

    def _territorio(self, fecha: date, territorio: str = "peninsula") -> dict:
        return self._datos(fecha).get(territorio, self._datos(fecha).get("peninsula", {}))

    # --- IVA/IGIC/IPSI ---
    def iva_general(self, fecha: date, territorio: str = "peninsula") -> float:
        t = self._territorio(fecha, territorio)
        return float(t.get("iva", t.get("igic", t.get("ipsi", {})))["general"])

    def iva_reducido(self, fecha: date, territorio: str = "peninsula") -> float:
        t = self._territorio(fecha, territorio)
        return float(t.get("iva", t.get("igic", {}))["reducido"])

    def iva_superreducido(self, fecha: date, territorio: str = "peninsula") -> float:
        t = self._territorio(fecha, territorio)
        return float(t.get("iva", {}).get("superreducido", 0))

    def recargo_equivalencia(self, tipo: str, fecha: date, territorio: str = "peninsula") -> float:
        return float(self._territorio(fecha, territorio)["iva"]["recargo_equivalencia"][tipo])

    def impuesto_indirecto(self, fecha: date, territorio: str = "peninsula") -> dict:
        t = self._territorio(fecha, territorio)
        for clave in ("iva", "igic", "ipsi"):
            if clave in t:
                return t[clave]
        return t.get("iva", {})

    # --- IS ---
    def tipo_is(self, categoria: str, fecha: date, territorio: str = "peninsula") -> float:
        return float(self._territorio(fecha, territorio)["impuesto_sociedades"][categoria])

    # --- IRPF ---
    def tabla_irpf(self, fecha: date, territorio: str = "peninsula") -> list:
        return self._territorio(fecha, territorio)["irpf"]["tablas_retencion"]

    def retencion_profesional(self, nuevo: bool, fecha: date, territorio: str = "peninsula") -> float:
        datos = self._territorio(fecha, territorio)["irpf"]
        clave = "retencion_profesional_nuevo" if nuevo else "retencion_profesional"
        return float(datos[clave])

    def pago_fraccionado_130(self, fecha: date, territorio: str = "peninsula") -> float:
        return float(self._territorio(fecha, territorio)["irpf"]["pago_fraccionado_130"])

    # --- SS (comun a todos) ---
    def smi_mensual(self, fecha: date) -> float:
        return float(self._datos(fecha)["seguridad_social"]["smi_mensual"])

    def seguridad_social(self, fecha: date) -> dict:
        return self._datos(fecha)["seguridad_social"]

    # --- Umbrales (comunes) ---
    def umbral(self, nombre: str, fecha: date) -> float:
        return float(self._datos(fecha)["umbrales"][nombre])

    # --- Plazos (comunes) ---
    def plazo_presentacion(self, modelo: str, trimestre: str, ano: int) -> dict:
        datos = self._cargar_ano(ano)
        plazos = datos["plazos_presentacion"]
        return plazos["trimestral"].get(trimestre, plazos["anual"].get(f"modelo_{modelo}", {}))

    # --- Amortizacion (comun) ---
    def tabla_amortizacion(self, tipo_bien: str, fecha: date) -> dict:
        for tabla in self._datos(fecha)["amortizacion"]["tablas"]:
            if tabla["tipo_bien"] == tipo_bien:
                return tabla
        raise ValueError(f"Tipo de bien no encontrado: {tipo_bien}")
```

**Step 5: Ejecutar tests**

```bash
pytest tests/test_normativa.py -v
```

Expected: ALL PASS

**Step 6: Commit**

```bash
git commit -m "feat: modulo normativa/ con parametros fiscales 2025 multi-territorio"
```

---

### Task 3: Crear modelo PerfilFiscal

**Files:**
- Create: `sfce/core/perfil_fiscal.py`
- Test: `tests/test_perfil_fiscal.py`

**Step 1: Escribir tests**

Tests completos para: SL basica, autonomo directa, autonomo modulos, profesional con retencion, canarias IGIC, comunidad propietarios, gran empresa mensual, recargo equivalencia, pagos fraccionados IS, libros obligatorios por regimen, desde_dict, validaciones cruzadas (juridica sin IRPF, fisica sin IS).

Total: ~18 tests cubriendo cada forma juridica, territorio y regimen.

Ver design doc v2 seccion 4 para el modelo de datos completo.

**Step 2: Implementar PerfilFiscal**

Dataclass con `__post_init__` para restricciones logicas, properties `impuesto_indirecto` y `periodicidad`, metodos `modelos_obligatorios()`, `libros_obligatorios()`, `desde_dict()`.

Implementacion completa en plan v1 Task 3 — anadir soporte para IGIC (modelo 420), IPSI, periodicidad mensual para gran_empresa.

**Step 3: Ejecutar tests, commit**

```bash
pytest tests/test_perfil_fiscal.py -v
git commit -m "feat: modelo PerfilFiscal con derivacion automatica modelos/libros"
```

---

### Task 4: Crear YAMLs regimenes IVA, IGIC y perfiles fiscales

**Files:**
- Create: `sfce/reglas/pgc/regimenes_iva.yaml`
- Create: `sfce/reglas/pgc/regimenes_igic.yaml`
- Create: `sfce/reglas/pgc/perfiles_fiscales.yaml`

**Step 1: Crear regimenes_iva.yaml**

Catalogo de regimenes IVA con subcuentas y comportamiento: general, simplificado, recargo_equivalencia, criterio_caja, exento, reagyp, agencias_viaje, bienes_usados. Para cada regimen: subcuentas IVA (472, 477, cuentas transitorias), como se contabiliza, como afecta al 303, IVA deducible.

**Step 2: Crear regimenes_igic.yaml**

Equivalente para IGIC canario: general (7%), reducido (3%), tipo_cero (0%), incrementado_1 (9.5%), incrementado_2 (15%), especial (20%). Subcuentas IGIC, modelo 420.

**Step 3: Crear perfiles_fiscales.yaml**

Plantillas por forma juridica. Al dar de alta "sl" se cargan defaults correctos (IS 25%, deposita cuentas, 303+111+200+390, etc.). El gestor solo modifica lo que difiere.

**Step 4: Commit**

```bash
git commit -m "feat: catalogos YAML regimenes IVA/IGIC y plantillas perfiles fiscales"
```

---

### Task 5: Integrar PerfilFiscal en ConfigCliente + seccion trabajadores

**Files:**
- Modify: `sfce/core/config.py`
- Modify: `clientes/pastorino-costa-del-sol/config.yaml`
- Test: `tests/test_config_perfil.py`

**Step 1: Escribir tests**

```python
class TestConfigConPerfil:
    def test_config_con_perfil_fiscal(self):
        config = cargar_config("pastorino-costa-del-sol")
        assert config.perfil_fiscal is not None
        assert config.perfil_fiscal.forma_juridica == "sl"

    def test_config_sin_perfil_usa_tipo_legacy(self):
        """Config sin perfil_fiscal genera uno desde campo 'tipo'"""
        config_data = {"empresa": {"nombre": "Test", "cif": "B12345678",
                       "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"}}
        config = ConfigCliente(config_data, "test")
        assert config.perfil_fiscal.forma_juridica == "sl"

    def test_trabajadores_desde_config(self):
        """Config con seccion trabajadores los carga"""
        config_data = {
            "empresa": {"nombre": "Test", "cif": "B12345678",
                       "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
            "trabajadores": [
                {"nombre": "Ana Garcia", "dni": "12345678A",
                 "bruto_mensual": 2142.86, "pagas": 14, "confirmado": True}
            ]
        }
        config = ConfigCliente(config_data, "test")
        assert len(config.trabajadores) == 1
        assert config.trabajadores[0]["pagas"] == 14
```

**Step 2: Modificar ConfigCliente**

Anadir a `__init__()`:
- Si `data` tiene `perfil_fiscal` -> `PerfilFiscal.desde_dict(data["perfil_fiscal"])`
- Si no -> generar desde `empresa.tipo`
- Si `data` tiene `trabajadores` -> cargar lista

**Step 3: Anadir perfil_fiscal y trabajadores al config.yaml de Pastorino**

**Step 4: Ejecutar todos los tests, commit**

```bash
pytest tests/ -v
git commit -m "feat: integrar PerfilFiscal y trabajadores en ConfigCliente"
```

---

### Task 6: Crear capa de abstraccion backend.py

**Files:**
- Create: `sfce/core/backend.py`
- Test: `tests/test_backend.py`

**Step 1: Escribir tests con mocks**

Tests para: crear_factura delega a fs, crear_asiento delega a fs, interfaz completa (todos los metodos existen), actualizar_factura, actualizar_partida.

**Step 2: Implementar Backend**

Clase `Backend` con `modo="fs"`. Todos los metodos delegan a `sfce.core.fs_api`. Ver design doc v2 seccion 15.

Metodos: crear_factura, crear_asiento, crear_partida, obtener_subcuentas, crear_proveedor, crear_cliente, obtener_saldo, actualizar_factura, actualizar_partida, obtener_asientos.

**Step 3: Ejecutar tests, commit**

```bash
pytest tests/test_backend.py -v
git commit -m "feat: capa abstraccion Backend sobre FacturaScripts"
```

---

### Task 7: Crear DecisionContable con trazabilidad

**Files:**
- Create: `sfce/core/decision.py`
- Test: `tests/test_decision.py`

**Step 1: Escribir tests**

```python
class TestDecisionContable:
    def test_crear_decision_basica(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=95, origen_decision="regla_cliente")
        assert decision.cuarentena is False
        assert len(decision.log_razonamiento) >= 0

    def test_cuarentena_baja_confianza(self):
        decision = DecisionContable(
            subcuenta_gasto="6220000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=50, origen_decision="ocr_keywords")
        assert decision.cuarentena is True

    def test_generar_partidas_general(self):
        decision = DecisionContable(...)
        partidas = decision.generar_partidas(base=1000.0)
        assert len(partidas) == 3  # gasto + IVA + proveedor
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01

    def test_generar_partidas_con_retencion(self):
        # 4 partidas: gasto + IVA + retencion + contrapartida
        ...

    def test_generar_partidas_recargo_equivalencia(self):
        # 4 partidas: gasto + IVA + recargo + proveedor
        ...

    def test_generar_partidas_isp(self):
        # 4 partidas: gasto + IVA soportado + IVA repercutido + proveedor
        ...

    def test_generar_partidas_iva_parcial(self):
        # IVA 50% deducible (vehiculo)
        decision = DecisionContable(
            subcuenta_gasto="6290000000", subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            pct_iva_deducible=50.0,
            confianza=95, origen_decision="regla_cliente")
        partidas = decision.generar_partidas(base=100.0)
        gasto = [p for p in partidas if "629" in p.subcuenta][0]
        assert gasto.debe == 110.50  # 100 + 10.50 IVA no deducible
        iva = [p for p in partidas if "472" in p.subcuenta][0]
        assert iva.debe == 10.50  # solo 50%

    def test_generar_partidas_criterio_caja(self):
        # Cuenta transitoria 477* en vez de 477
        ...

    def test_log_razonamiento(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000", subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=95, origen_decision="regla_cliente",
            log_razonamiento=["1. Regla cliente: CIF B99 -> 600", "2. IVA general 21%"])
        assert len(decision.log_razonamiento) == 2
        assert "Regla cliente" in decision.log_razonamiento[0]

    def test_to_dict_completo(self):
        """Serializable a JSON para guardar en BD"""
        decision = DecisionContable(...)
        d = decision.to_dict()
        assert "log_razonamiento" in d
        assert "partidas" in d
```

**Step 2: Implementar DecisionContable**

```python
# sfce/core/decision.py
from dataclasses import dataclass, field

@dataclass
class Partida:
    subcuenta: str
    debe: float = 0.0
    haber: float = 0.0
    concepto: str = ""

@dataclass
class DecisionContable:
    subcuenta_gasto: str
    subcuenta_contrapartida: str
    codimpuesto: str
    tipo_iva: float
    confianza: int
    origen_decision: str
    recargo_equiv: float | None = None
    retencion_pct: float | None = None
    pct_iva_deducible: float = 100.0
    isp: bool = False
    isp_tipo_iva: float | None = None
    regimen: str = "general"
    cuarentena: bool = False
    motivo_cuarentena: str | None = None
    opciones_alternativas: list = field(default_factory=list)
    log_razonamiento: list = field(default_factory=list)
    partidas: list = field(default_factory=list)

    def __post_init__(self):
        if self.confianza < 70 and not self.cuarentena:
            self.cuarentena = True
            self.motivo_cuarentena = f"Confianza {self.confianza}% < 70%"

    def generar_partidas(self, base: float) -> list[Partida]:
        partidas = []
        iva_importe = round(base * self.tipo_iva / 100, 2)
        iva_deducible = round(iva_importe * self.pct_iva_deducible / 100, 2)
        iva_no_deducible = round(iva_importe - iva_deducible, 2)
        total = round(base + iva_importe, 2)

        # Gasto (base + IVA no deducible)
        importe_gasto = round(base + iva_no_deducible, 2)
        partidas.append(Partida(self.subcuenta_gasto, debe=importe_gasto,
                                concepto="Base imponible" + (f" + IVA no deducible {iva_no_deducible}" if iva_no_deducible > 0 else "")))

        # IVA soportado (solo parte deducible)
        if iva_deducible > 0:
            partidas.append(Partida("4720000000", debe=iva_deducible,
                                    concepto=f"IVA soportado {self.tipo_iva}%"
                                    + (f" ({self.pct_iva_deducible}% deducible)" if self.pct_iva_deducible < 100 else "")))

        # Recargo equivalencia
        if self.recargo_equiv:
            recargo = round(base * self.recargo_equiv / 100, 2)
            partidas.append(Partida("4720000000", debe=recargo,
                                    concepto=f"Recargo equivalencia {self.recargo_equiv}%"))
            total = round(total + recargo, 2)

        # ISP (autorepercusion)
        if self.isp and self.isp_tipo_iva:
            iva_isp = round(base * self.isp_tipo_iva / 100, 2)
            partidas.append(Partida("4770000000", haber=iva_isp,
                                    concepto=f"IVA repercutido ISP {self.isp_tipo_iva}%"))
            # En ISP, proveedor solo paga base (sin IVA en factura)
            total = base

        # Retencion
        if self.retencion_pct:
            retencion = round(base * self.retencion_pct / 100, 2)
            partidas.append(Partida("4751000000", haber=retencion,
                                    concepto=f"Retencion {self.retencion_pct}%"))
            total = round(total - retencion, 2)

        # Contrapartida (proveedor/acreedor)
        partidas.append(Partida(self.subcuenta_contrapartida, haber=total,
                                concepto="Contrapartida"))

        self.partidas = partidas
        return partidas

    def to_dict(self) -> dict:
        return {
            "subcuenta_gasto": self.subcuenta_gasto,
            "subcuenta_contrapartida": self.subcuenta_contrapartida,
            "codimpuesto": self.codimpuesto,
            "tipo_iva": self.tipo_iva,
            "pct_iva_deducible": self.pct_iva_deducible,
            "recargo_equiv": self.recargo_equiv,
            "retencion_pct": self.retencion_pct,
            "isp": self.isp,
            "regimen": self.regimen,
            "confianza": self.confianza,
            "origen_decision": self.origen_decision,
            "cuarentena": self.cuarentena,
            "motivo_cuarentena": self.motivo_cuarentena,
            "log_razonamiento": self.log_razonamiento,
            "partidas": [{"subcuenta": p.subcuenta, "debe": p.debe,
                         "haber": p.haber, "concepto": p.concepto}
                        for p in self.partidas],
        }
```

**Step 3: Ejecutar tests, commit**

```bash
pytest tests/test_decision.py -v
git commit -m "feat: DecisionContable con trazabilidad y partidas multi-regimen"
```

---

### Task 8: Crear operaciones_periodicas.py

**Files:**
- Create: `sfce/core/operaciones_periodicas.py`
- Test: `tests/test_operaciones_periodicas.py`

**Step 1: Escribir tests**

```python
from sfce.core.operaciones_periodicas import OperacionesPeriodicas
from sfce.core.perfil_fiscal import PerfilFiscal
from sfce.normativa.vigente import Normativa

class TestAmortizacion:
    def test_calcular_cuota_mensual_lineal(self):
        op = OperacionesPeriodicas(Normativa())
        cuota = op.cuota_amortizacion_mensual(
            valor_adquisicion=30000, valor_residual=0,
            pct_amortizacion=16)
        assert cuota == 400.0  # 30000 * 16% / 12

    def test_asiento_amortizacion(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_asiento_amortizacion(
            tipo_bien="vehiculos", valor=30000, residual=0,
            pct=16, subcuenta_activo="2180000000")
        assert len(partidas) == 2
        assert partidas[0].subcuenta == "6810000000"  # gasto amort
        assert partidas[0].debe == 400.0
        assert partidas[1].subcuenta == "2810000000"  # amort acum
        assert partidas[1].haber == 400.0

class TestProvisionPagasExtras:
    def test_calcular_provision_14_pagas(self):
        op = OperacionesPeriodicas(Normativa())
        provision = op.provision_paga_extra_mensual(
            bruto_mensual=2500, pagas=14)
        # 2 pagas extra. Provision mensual = 2500 * 2 / 12 = 416.67
        assert abs(provision - 416.67) < 0.01

    def test_asiento_provision_paga(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_asiento_provision_paga(
            bruto_mensual=2500, pagas=14)
        assert len(partidas) == 2
        assert partidas[0].subcuenta == "6400000000"  # sueldos
        assert partidas[0].debe == 416.67
        assert partidas[1].subcuenta == "4650000000"  # remun ptes
        assert partidas[1].haber == 416.67

    def test_12_pagas_sin_provision(self):
        op = OperacionesPeriodicas(Normativa())
        provision = op.provision_paga_extra_mensual(
            bruto_mensual=2500, pagas=12)
        assert provision == 0.0

class TestRegularizacionIVA:
    def test_iva_a_pagar(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_regularizacion_iva(
            iva_repercutido=5000, iva_soportado=3000)
        assert len(partidas) == 3
        # 477 DEBE 5000, 472 HABER 3000, 4750 HABER 2000
        assert any(p.subcuenta == "4750000000" and p.haber == 2000 for p in partidas)

    def test_iva_a_compensar(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_regularizacion_iva(
            iva_repercutido=3000, iva_soportado=5000)
        assert any(p.subcuenta == "4700000000" and p.debe == 2000 for p in partidas)

    def test_iva_con_prorrata(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_regularizacion_iva(
            iva_repercutido=5000, iva_soportado=3000, prorrata=80)
        # IVA no deducible = 3000 * 20% = 600
        assert any(p.subcuenta == "6340000000" and p.debe == 600 for p in partidas)
```

**Step 2: Implementar OperacionesPeriodicas**

Clase con metodos para cada tipo de operacion periodica. Usa `Normativa` para tablas amortizacion. Genera listas de `Partida`.

**Step 3: Ejecutar tests, commit**

```bash
pytest tests/test_operaciones_periodicas.py -v
git commit -m "feat: operaciones periodicas (amortizacion, provision pagas, regularizacion IVA)"
```

---

### Task 9: Crear cierre_ejercicio.py

**Files:**
- Create: `sfce/core/cierre_ejercicio.py`
- Test: `tests/test_cierre_ejercicio.py`

**Step 1: Escribir tests**

```python
from sfce.core.cierre_ejercicio import CierreEjercicio

class TestRegularizacion:
    def test_regularizacion_basica(self):
        """Cierra cuentas 6xx y 7xx contra 129"""
        cierre = CierreEjercicio()
        saldos = {
            "6000000000": {"debe": 50000, "haber": 0},     # compras
            "6420000000": {"debe": 10000, "haber": 0},     # SS empresa
            "7000000000": {"debe": 0, "haber": 80000},     # ventas
        }
        partidas = cierre.generar_regularizacion(saldos)
        # Debe cerrar 600 (HABER 50000), 642 (HABER 10000), 700 (DEBE 80000)
        # 129 = 80000 - 60000 = 20000 beneficio (HABER)
        cuenta_129 = [p for p in partidas if "129" in p.subcuenta]
        assert len(cuenta_129) == 1
        assert cuenta_129[0].haber == 20000

    def test_regularizacion_con_perdida(self):
        saldos = {
            "6000000000": {"debe": 80000, "haber": 0},
            "7000000000": {"debe": 0, "haber": 50000},
        }
        partidas = cierre.generar_regularizacion(saldos)
        cuenta_129 = [p for p in partidas if "129" in p.subcuenta]
        assert cuenta_129[0].debe == 30000  # perdida

class TestCierre:
    def test_asiento_cierre(self):
        """Cierra TODAS las cuentas a 0"""
        saldos = {
            "1000000000": {"debe": 0, "haber": 50000},     # capital
            "1290000000": {"debe": 0, "haber": 20000},     # resultado
            "5720000000": {"debe": 30000, "haber": 0},     # bancos
            "4000000001": {"debe": 0, "haber": 10000},     # proveedor
            "4300000001": {"debe": 10000, "haber": 0},     # cliente
        }
        partidas = cierre.generar_cierre(saldos)
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01

class TestApertura:
    def test_asiento_apertura(self):
        """Inverso del cierre: reabre cuentas patrimoniales"""
        saldos_cierre = {
            "1000000000": {"debe": 0, "haber": 50000},
            "5720000000": {"debe": 30000, "haber": 0},
        }
        partidas = cierre.generar_apertura(saldos_cierre)
        # Inverso: lo que era HABER ahora es DEBE y viceversa
        assert any(p.subcuenta == "1000000000" and p.haber == 50000 for p in partidas)
        assert any(p.subcuenta == "5720000000" and p.debe == 30000 for p in partidas)

class TestGastoIS:
    def test_asiento_impuesto_sociedades(self):
        cierre = CierreEjercicio()
        partidas = cierre.generar_gasto_is(base_imponible=120000, tipo_is=25)
        assert len(partidas) == 2
        assert partidas[0].subcuenta == "6300000000"  # gasto IS
        assert partidas[0].debe == 30000
        assert partidas[1].subcuenta == "4752000000"  # HP acreedora IS
        assert partidas[1].haber == 30000
```

**Step 2: Implementar CierreEjercicio**

Clase con metodos:
- `generar_regularizacion(saldos)` — cierra 6xx/7xx contra 129
- `generar_gasto_is(base_imponible, tipo_is)` — 6300 @ 4752
- `generar_cierre(saldos)` — todas las cuentas a 0
- `generar_apertura(saldos_cierre)` — inverso, solo patrimoniales
- `secuencia_completa(saldos, perfil_fiscal, normativa)` — ejecuta los 10 pasos en orden

**Step 3: Ejecutar tests, commit**

```bash
pytest tests/test_cierre_ejercicio.py -v
git commit -m "feat: cierre ejercicio (regularizacion, IS, cierre, apertura)"
```

---

### Task 10: Tests integracion Fase A + verificar pipeline existente

**Files:**
- Create: `tests/test_integracion_fase_a.py`

**Step 1: Escribir test de integracion**

```python
from datetime import date
from sfce.normativa.vigente import Normativa
from sfce.core.perfil_fiscal import PerfilFiscal
from sfce.core.decision import DecisionContable
from sfce.core.operaciones_periodicas import OperacionesPeriodicas
from sfce.core.cierre_ejercicio import CierreEjercicio

class TestIntegracionFaseA:
    def test_normativa_alimenta_decision(self):
        n = Normativa()
        iva = n.iva_general(date(2025, 6, 15))
        decision = DecisionContable(
            subcuenta_gasto="6000000000", subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=iva, confianza=95, origen_decision="test")
        partidas = decision.generar_partidas(base=1000.0)
        iva_p = [p for p in partidas if "472" in p.subcuenta][0]
        assert iva_p.debe == 210.0

    def test_normativa_navarra_is(self):
        n = Normativa()
        assert n.tipo_is("general", date(2025, 1, 1), "navarra") == 28

    def test_perfil_canarias_igic(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          territorio="canarias")
        assert pf.impuesto_indirecto == "igic"
        modelos = pf.modelos_obligatorios()
        assert "420" in modelos["trimestrales"]
        assert "303" not in modelos["trimestrales"]

    def test_cierre_completo_con_is(self):
        cierre = CierreEjercicio()
        n = Normativa()
        saldos = {"6000000000": {"debe": 80000, "haber": 0},
                  "7000000000": {"debe": 0, "haber": 120000}}
        tipo_is = n.tipo_is("general", date(2025, 12, 31))
        partidas_is = cierre.generar_gasto_is(40000, tipo_is)
        assert partidas_is[0].debe == 10000  # 40000 * 25%

    def test_pipeline_imports_no_rotos(self):
        from sfce.phases import intake, pre_validation, registration
        from sfce.phases import asientos, correction, cross_validation, output
```

**Step 2: Ejecutar TODOS los tests**

```bash
pytest tests/ -v
```

Expected: 88 existentes + ~60 nuevos = ALL PASS

**Step 3: Commit**

```bash
git commit -m "test: integracion Fase A — normativa multi-territorio + perfil + decision + cierre"
```

---

## FASE B: MOTOR CENTRAL (Tasks 11-19)

### Task 11: Crear clasificador contable

**Files:**
- Create: `sfce/core/clasificador.py`
- Create: `sfce/reglas/pgc/palabras_clave_subcuentas.yaml`
- Test: `tests/test_clasificador.py`

Cascada 6 niveles: regla_cliente (95%) -> aprendizaje (85%) -> tipo_doc (80%) -> palabras_clave_ocr (60%) -> libro_diario_importado (75%) -> cuarentena.

Tests: un test por nivel + fallback cuarentena + confianza <70% a cuarentena.

---

### Task 12: Crear MotorReglas (nucleo del sistema)

**Files:**
- Create: `sfce/core/motor_reglas.py`
- Test: `tests/test_motor_reglas.py`

`__init__`: carga 6 niveles. `decidir_asiento(doc)`: consulta clasificador + normativa -> DecisionContable con log_razonamiento. `validar_asiento(asiento)`: checks. `aprender(doc, decision_humana)`: nivel 5.

Tests: ~15 tests por regimen (general, retencion, ISP, RE, criterio caja, nomina, suministro, desconocido->cuarentena, conflicto nivel 5 vs 0).

---

### Task 13: Integrar MotorReglas en registration.py

**Files:**
- Modify: `sfce/phases/registration.py`
- Test: `tests/test_registration_motor.py`

Refactorizar `_construir_form_data()` para usar `motor.decidir_asiento()`. Mantener compatibilidad legacy. Regression test vs Pastorino.

---

### Task 14: Integrar MotorReglas en correction.py

**Files:**
- Modify: `sfce/phases/correction.py`
- Test: `tests/test_correction_motor.py`

Los 7 checks actuales se convierten en reglas del motor via `motor.validar_asiento()`.

---

### Task 15: Integrar MotorReglas en asientos_directos.py

**Files:**
- Modify: `sfce/core/asientos_directos.py`
- Test: `tests/test_asientos_directos_motor.py`

Plantillas fijas de `subcuentas_tipos.yaml` se generan via `motor.decidir_asiento()`. Motor consulta perfil fiscal para adaptar.

---

### Task 16: Calculador modelos fiscales (3 categorias)

**Files:**
- Create: `sfce/core/calculador_modelos.py`
- Test: `tests/test_calculador_modelos.py`

**Automaticos**: calcular_303, calcular_390, calcular_111, calcular_190, calcular_115, calcular_180, calcular_130, calcular_131, calcular_347, calcular_349.

**Semi-automaticos**: borrador_200 (pre-rellena resultado contable, pagos a cuenta, bases negativas; devuelve dict con campos editables marcados).

**Asistidos**: informe_rendimientos_actividad (para modelo 100, solo datos del negocio).

Tests: verificar 303 T3 coincide con Pastorino. Verificar borrador 200 tiene campos correctos.

---

### Task 17: Flujo completo notas de credito

**Files:**
- Modify: `sfce/phases/registration.py`
- Modify: `sfce/phases/intake.py`
- Test: `tests/test_notas_credito.py`

**Flujo**:
1. Intake clasifica NC
2. Motor busca factura original (por referencia, CIF+importe+fecha)
3. Si no encuentra -> cuarentena tipo "nota_credito_sin_origen"
4. Genera asiento inverso (parcial o total)
5. Actualiza acumulados (303, 347)

Tests: NC total, NC parcial, NC sin factura original -> cuarentena.

---

### Task 18: Pipeline usa MotorReglas como orquestador

**Files:**
- Modify: `scripts/pipeline.py`
- Modify: `sfce/phases/*.py` (ajustes menores)

Pipeline crea MotorReglas al inicio, lo pasa a cada fase como parametro.

---

### Task 19: Tests integracion Fase B + regression completa

**Files:**
- Create: `tests/test_integracion_fase_b.py`

Test end-to-end: simular pipeline completo de una factura usando MotorReglas. Verificar resultado identico al sistema actual. Ejecutar 88 tests antiguos + todos los nuevos.

---

## FASE C: DATOS Y PERSISTENCIA (Tasks 20-27)

### Task 20: Crear base.py doble motor SQLite/PostgreSQL

**Files:**
- Create: `sfce/db/__init__.py`
- Create: `sfce/db/base.py`
- Test: `tests/test_db_base.py`

```python
# sfce/db/base.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

class Base(DeclarativeBase):
    pass

def crear_motor(config: dict | None = None):
    config = config or {"tipo_bd": "sqlite", "ruta_bd": ":memory:"}
    tipo = config.get("tipo_bd", "sqlite")

    if tipo == "sqlite":
        ruta = config.get("ruta_bd", "sfce.db")
        url = f"sqlite:///{ruta}" if ruta != ":memory:" else "sqlite:///:memory:"
        engine = create_engine(url, connect_args={"check_same_thread": False})
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA busy_timeout=5000"))
            conn.commit()
    elif tipo == "postgresql":
        url = f"postgresql://{config['db_user']}:{config['db_password']}@{config['db_host']}:{config.get('db_port', 5432)}/{config['db_name']}"
        engine = create_engine(url, pool_size=10, max_overflow=20)
    else:
        raise ValueError(f"Tipo BD no soportado: {tipo}")

    return engine

def crear_sesion(engine):
    return sessionmaker(bind=engine)
```

Tests: crear motor SQLite in-memory, crear tablas, insertar/leer datos.

---

### Task 21: Crear modelos SQLAlchemy (13 tablas)

**Files:**
- Create: `sfce/db/modelos.py`
- Test: `tests/test_db_modelos.py`

13 tablas: empresas, proveedores_clientes, trabajadores, documentos, asientos, partidas, facturas, pagos, movimientos_bancarios, activos_fijos, operaciones_periodicas, cuarentena, audit_log, saldos_subcuenta, aprendizaje_log.

Tests: crear tablas en SQLite in-memory, insertar datos, verificar FK constraints, verificar JSON fields.

---

### Task 22: Crear repositorio (queries)

**Files:**
- Create: `sfce/db/repositorio.py`
- Test: `tests/test_repositorio.py`

CRUD + queries especializadas: saldo_subcuenta, pyg (7xx - 6xx), balance, facturas_pendientes_pago, documentos_cuarentena, activos_pendientes_amortizacion, operaciones_periodicas_pendientes.

---

### Task 23: Integrar BD local en Backend (doble destino)

**Files:**
- Modify: `sfce/core/backend.py`
- Test: `tests/test_backend_db.py`

Backend guarda en BD local Y envia a FS. Si FS falla -> pendiente_sync. Funcion sincronizar() para reintentos. Audit log automatico en cada operacion.

---

### Task 24: Crear importador libro diario

**Files:**
- Create: `sfce/core/importador.py`
- Test: `tests/test_importador.py`

Parser CSV/Excel: deteccion columnas, extraccion mapa CIF->subcuenta, generacion config.yaml propuesto. Soporte separadores y encodings.

---

### Task 25: Crear exportador universal

**Files:**
- Create: `sfce/core/exportador.py`
- Test: `tests/test_exportador.py`

CSV libro diario, Excel multi-hoja, CSV facturas emitidas/recibidas.

---

### Task 26: Migrar datos existentes FS -> BD local

**Files:**
- Create: `scripts/migrar_fs_a_bd.py`

Script one-time: lee FS via API, carga en BD local. Para cada empresa: facturas, asientos, partidas, proveedores, clientes.

---

### Task 27: Tests integracion Fase C

**Files:**
- Create: `tests/test_integracion_fase_c.py`

Test: procesar factura -> verificar en BD local. Test importador -> config generado. Test exportador -> CSV/Excel valido.

---

## FASE D: INTERFAZ Y PRODUCTO (Tasks 28-37)

### Task 28: Crear API FastAPI estructura base

**Files:**
- Create: `sfce/api/app.py`
- Create: `sfce/api/rutas/__init__.py`
- Create: `sfce/api/rutas/empresas.py`
- Create: `sfce/api/rutas/documentos.py`
- Create: `sfce/api/rutas/contabilidad.py`

Endpoints REST: empresas, PyG, balance, diario, modelos, cuarentena, procesar, exportar.

---

### Task 29: Autenticacion JWT

**Files:**
- Create: `sfce/api/auth.py`
- Test: `tests/test_auth.py`

JWT con 3 roles: admin, gestor, readonly. Middleware FastAPI. Hash passwords con bcrypt. Refresh tokens.

---

### Task 30: WebSocket eventos tiempo real

**Files:**
- Create: `sfce/api/websocket.py`

Eventos: pipeline_progress, documento_procesado, cuarentena_nuevo, saldo_actualizado.

---

### Task 31: Scaffolding dashboard React

**Files:**
- Create: `dashboard/package.json`, `vite.config.ts`, `tailwind.config.ts`
- Create: `dashboard/src/App.tsx`, `dashboard/src/main.tsx`

React 18 + TypeScript + Tailwind + Vite. Router con rutas.

---

### Task 32: Dashboard — Vista general + empresas

**Files:**
- Create: `dashboard/src/pages/Home.tsx`
- Create: `dashboard/src/pages/Empresa.tsx`
- Create: `dashboard/src/components/EmpresaCard.tsx`

---

### Task 33: Dashboard — Contabilidad (PyG, Balance, Diario, Activos)

**Files:**
- Create: `dashboard/src/pages/PyG.tsx`
- Create: `dashboard/src/pages/Balance.tsx`
- Create: `dashboard/src/pages/Diario.tsx`
- Create: `dashboard/src/pages/Activos.tsx`

Tablas y graficos en tiempo real. Vista de activos fijos con amortizacion acumulada.

---

### Task 34: Dashboard — Procesamiento (Inbox, Pipeline, Cuarentena)

**Files:**
- Create: `dashboard/src/pages/Inbox.tsx`
- Create: `dashboard/src/pages/Pipeline.tsx`
- Create: `dashboard/src/pages/Cuarentena.tsx`

Cuarentena estructurada: muestra tipo pregunta, opciones, datos relevantes. Click resuelve.

---

### Task 35: Dashboard — Herramientas (Importar, Exportar, Calendario, Cierre, Modelo 200)

**Files:**
- Create: `dashboard/src/pages/Importar.tsx`
- Create: `dashboard/src/pages/Exportar.tsx`
- Create: `dashboard/src/pages/Calendario.tsx`
- Create: `dashboard/src/pages/CierreEjercicio.tsx`
- Create: `dashboard/src/pages/Modelo200.tsx`

Wizard importacion. Exportacion con seleccion formato. Calendario fiscal con alertas. Wizard cierre de ejercicio (10 pasos). Formulario semi-automatico modelo 200.

---

### Task 36: File watcher

**Files:**
- Create: `scripts/watcher.py`
- Test: `tests/test_watcher.py`

Demonio watchdog que vigila `clientes/*/inbox/`. 3 modos: manual, semi-auto, automatico.

---

### Task 37: Sistema licencias

**Files:**
- Create: `sfce/core/licencia.py`
- Test: `tests/test_licencia.py`

Tokens firmados con fecha expiracion. Verificacion al arrancar. OCR proxy token.

---

## FASE E: INGESTA INTELIGENTE (Tasks 38-46)

### Task 38: Convencion nombres carpetas y documentos

**Files:**
- Create: `sfce/core/nombres.py`
- Test: `tests/test_nombres.py`

`generar_slug_cliente(cif, nombre)`, `renombrar_documento(datos_ocr)`. Carpeta `_sin_clasificar/`.

---

### Task 39: Cache OCR reutilizable

**Files:**
- Create: `sfce/core/cache_ocr.py`
- Test: `tests/test_cache_ocr.py`

`.ocr.json` junto al PDF. Hash SHA256. Intake verifica cache antes de OCR.

---

### Task 40: Deteccion duplicados

**Files:**
- Create: `sfce/core/duplicados.py`
- Test: `tests/test_duplicados.py`

Duplicado seguro (CIF+numero+fecha) -> rechazo. Posible (CIF+importe+fecha+-5d) -> cuarentena.

---

### Task 41: Deteccion trabajadores nuevos

**Files:**
- Modify: `sfce/phases/intake.py`
- Modify: `sfce/core/config.py`
- Test: `tests/test_trabajadores_nuevos.py`

**Step 1: Escribir tests**

```python
class TestDeteccionTrabajadores:
    def test_nomina_trabajador_conocido(self):
        """DNI en config -> procesar normal"""
        config = mock_config_con_trabajadores([
            {"dni": "12345678A", "nombre": "Ana Garcia", "pagas": 14}
        ])
        resultado = detectar_trabajador(datos_ocr={"dni": "12345678A"}, config=config)
        assert resultado["conocido"] is True
        assert resultado["pagas"] == 14

    def test_nomina_trabajador_nuevo(self):
        """DNI no en config -> cuarentena"""
        config = mock_config_con_trabajadores([])
        resultado = detectar_trabajador(
            datos_ocr={"dni": "12345678A", "nombre": "Ana Garcia", "bruto": 2142.86},
            config=config)
        assert resultado["conocido"] is False
        assert resultado["cuarentena"]["tipo"] == "trabajador_nuevo"
        assert resultado["cuarentena"]["default"] == 14

    def test_resolver_trabajador_nuevo(self):
        """Gestor confirma pagas -> se anade a config"""
        config = mock_config_con_trabajadores([])
        resolver_trabajador_nuevo(config, "12345678A", "Ana Garcia", 2142.86, pagas=14)
        assert len(config.trabajadores) == 1
        assert config.trabajadores[0]["confirmado"] is True
```

**Step 2: Implementar**

En intake.py: cuando tipo_doc=NOM, extraer DNI. Buscar en config.trabajadores. Si no existe -> crear cuarentena tipo "trabajador_nuevo" con default 14 pagas.

En config.py: `agregar_trabajador()` que anade a config.yaml y marca confirmado=True.

**Step 3: Ejecutar tests, commit**

---

### Task 42: Ingesta email IMAP

**Files:**
- Create: `sfce/core/ingesta_email.py`
- Create: `scripts/leer_correo.py`
- Test: `tests/test_ingesta_email.py`

IMAP, descargar adjuntos PDF, OCR rapido, enrutar por CIF o email remitente.

---

### Task 43: Sistema notificaciones

**Files:**
- Create: `sfce/core/notificaciones.py`
- Test: `tests/test_notificaciones.py`

Canal email + dashboard WebSocket. Plantillas: documento_ilegible, proveedor_nuevo, trabajador_nuevo, plazo_fiscal, factura_recurrente_faltante.

---

### Task 44: Deteccion facturas recurrentes faltantes

**Files:**
- Create: `sfce/core/recurrentes.py`
- Test: `tests/test_recurrentes.py`

Patron historico por proveedor (minimo 3 ocurrencias). Alerta si falta.

---

### Task 45: Operaciones periodicas automaticas (generador)

**Files:**
- Create: `scripts/generar_periodicas.py`
- Test: `tests/test_generar_periodicas.py`

Script/funcion que consulta tabla `operaciones_periodicas`, genera asientos pendientes (amortizaciones del mes, provisiones pagas extras), los registra via Backend.

Configurable: `--empresa X --mes 2025-06` o automatico via cron/watcher.

---

### Task 46: Tests integracion Fase E

**Files:**
- Create: `tests/test_integracion_fase_e.py`

Test: cache OCR guardar/cargar/reutilizar. Test: duplicado detectado. Test: trabajador nuevo -> cuarentena -> resolucion. Test: operacion periodica generada.

---

## Resumen de esfuerzo estimado

| Fase | Tasks | Tests nuevos estimados | Sesiones estimadas |
|------|-------|----------------------|-------------------|
| A — Fundamentos | 1-10 | ~70 | 4-5 |
| B — Motor central | 11-19 | ~50 | 5-6 |
| C — Datos | 20-27 | ~35 | 3-4 |
| D — Interfaz | 28-37 | ~25 | 6-7 |
| E — Ingesta | 38-46 | ~30 | 3-4 |
| **Total** | **46 tasks** | **~210 tests** | **21-26 sesiones** |

## Orden de ejecucion

```
Fase A (fundamentos) -> OBLIGATORIO primero
    |
Fase B (motor) -> OBLIGATORIO segundo
    |
Fase C (datos) <-> Fase D (interfaz) <-> Fase E (ingesta)
    PUEDEN ir en paralelo tras Fase B
```

Despues de Fase B, el pipeline soporta todos los regimenes y territorios fiscales. Fases C, D y E anaden persistencia, interfaz e ingesta, independientes entre si.
