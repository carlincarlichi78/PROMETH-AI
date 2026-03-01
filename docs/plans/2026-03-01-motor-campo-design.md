# Motor de Escenarios de Campo SFCE — Design Doc

**Fecha:** 2026-03-01
**Estado:** Aprobado
**Objetivo:** Motor autónomo que prueba todos los procesos del sistema SFCE con miles de variaciones paramétricas, detecta errores, intenta arreglarlos y registra bugs. Cero consumo de APIs de IA.

---

## Contexto

El SFCE tiene 7 procesos principales que necesitan testing de campo continuo:
1. Pipeline 7 fases (Intake→PreValidación→Registro→Asientos→Corrección→CruceValidación→Salidas)
2. Gate 0 (preflight, trust levels, scoring, colas)
3. 8 tipos de documentos (FC, FV, NC, NOM, SUM, BAN, RLC, IMP)
4. 66+ endpoints API REST
5. Integración dual con FacturaScripts (empresa id=3 sandbox)
6. Módulo bancario (C43/XLS + conciliación)
7. Fidelidad Dashboard (coherencia contabilidad ↔ datos mostrados)

---

## Decisiones de diseño

| Decisión | Elección | Razón |
|----------|----------|-------|
| Entorno | Empresa id=3 (EMPRESA PRUEBA) en FS real | Sandbox ya existente, sin contaminar clientes |
| OCR | Bypass total — inyectar `datos_extraidos` JSON directo | 0 coste APIs IA (Mistral/GPT/Gemini) |
| Auditor IA | Desactivado en cross_validation (parámetro) | 0 coste Gemini |
| On error | Intentar fix → si no → anotar bug → limpiar → continuar | Máxima cobertura sin paradas |
| Persistencia | SQLite `motor_campo.db` | Sin dependencias externas |

---

## Arquitectura

```
motor_campo.py (orquestador)
    │
    ├── catalogo/          # Escenarios definidos como dataclasses Python
    │   ├── fc.py          # Facturas cliente
    │   ├── fv.py          # Facturas proveedor
    │   ├── especiales.py  # NC, NOM, SUM, RLC, IMP
    │   ├── bancario.py    # C43, XLS, conciliación
    │   ├── gate0.py       # Trust, scoring, colas
    │   ├── api.py         # Auth, seguridad, multi-tenant
    │   └── dashboard.py   # Fidelidad datos
    │
    ├── generador.py       # Genera variantes paramétricas de cada escenario
    ├── executor.py        # Ejecuta escenario contra sistema real
    ├── validator.py       # Verifica resultado vs esperado
    ├── autofix.py         # Diagnostica y aplica fixes conocidos
    ├── cleanup.py         # Limpia empresa id=3 después de cada escenario
    ├── bug_registry.py    # SQLite motor_campo.db
    └── reporter.py        # Reporte HTML al final de cada ciclo
```

---

## Componentes

### 1. Catálogo de Escenarios

Cada escenario es una dataclass con:
```python
@dataclass
class Escenario:
    id: str                          # "fc_iva21", "fv_intracomunitario"
    grupo: str                       # "facturas_cliente", "bancario", etc.
    descripcion: str
    datos_extraidos: dict            # JSON bypass OCR
    config_empresa: dict             # codejercicio, idempresa, etc.
    resultado_esperado: ResultadoEsperado
    variaciones: list[VariacionParam] # qué campos variar
```

### 2. Generador de Variaciones

Dado un escenario base, genera N variantes modificando:
- **Importes:** redondos (100, 1000), decimales (123.45), grandes (99999.99), pequeños (0.01), borde (0.00)
- **Fechas:** primer día ejercicio, último día, mitad, un día fuera del ejercicio
- **IVA:** 0%, 4%, 10%, 21%, mixto en líneas
- **Divisa:** EUR, USD (tasaconv 1.05), GBP (tasaconv 1.18), USD con tasaconv extraño (0.9999)
- **Proveedor:** español con CIF, intracomunitario UE, extra-EU sin CIF, sin CIF con fallback

Resultado: cada escenario genera entre 8 y 40 variantes.

### 3. Executor

Inyecta la variante en el sistema real:
- **Pipeline:** llama directamente `ejecutar_pre_validacion()` con `datos_extraidos` preconstruidos (saltar Fase 0/OCR)
- **API endpoints:** HTTP requests a `http://localhost:8000/api/...` con JWT de admin
- **FacturaScripts:** a través del pipeline (empresa id=3, codejercicio="0003")
- **Bancario:** genera archivo C43/XLS sintético en memoria, llama `/api/bancario/3/ingestar`

### 4. Validator

Verifica resultado real vs esperado:
```python
checks_contables:
  - DEBE == HABER (tolerancia 0.01 EUR)
  - IVA calculado == IVA esperado
  - Subcuenta correcta según tipo documento
  - Asiento no invertido (DEBE/HABER en lado correcto)
  - Divisa convertida correctamente a EUR

checks_api:
  - HTTP status code == esperado
  - Schema respuesta (campos requeridos presentes)
  - No expone datos de otra empresa (multi-tenant)

checks_fidelidad:
  - Valor dashboard == valor calculado manualmente
  - Sync FS→BD completado (documento aparece en Asiento/Partida)
```

### 5. Auto-Fix Engine

Patrones de fix conocidos:
| Error detectado | Fix automático |
|----------------|----------------|
| Asiento invertido DEBE/HABER | PUT partidas intercambiando debe↔haber |
| IVA en línea incorrecto | PUT lineas con codimpuesto correcto |
| Subcuenta 600 en proveedor | No arreglar, documentar como bug |
| Sync FS→BD no completado | Llamar `_sincronizar_asientos_factura_a_bd()` manualmente |
| codejercicio incorrecto | PUT factura con codejercicio correcto |

Si el fix tiene éxito: anotar como "bug arreglado automáticamente".
Si falla tras 2 intentos: anotar como "bug pendiente manual".

### 6. Cleanup

Después de cada escenario (éxito o fallo):
```python
# Borrar en orden inverso (FK constraints)
DELETE partidas WHERE asiento_id IN (asientos del escenario)
DELETE asientos creados en el escenario
DELETE lineasfactura* de las facturas del escenario
DELETE factura* del escenario (via API FS)
DELETE documentos BD local del escenario
```

### 7. Bug Registry (`motor_campo.db`)

```sql
CREATE TABLE ejecuciones (
    id INTEGER PRIMARY KEY,
    sesion_id TEXT,
    timestamp DATETIME,
    escenario_id TEXT,
    variante_id TEXT,
    resultado TEXT,  -- "ok" | "bug_arreglado" | "bug_pendiente"
    duracion_ms INTEGER
);

CREATE TABLE bugs (
    id INTEGER PRIMARY KEY,
    sesion_id TEXT,
    escenario_id TEXT,
    variante_id TEXT,
    fase TEXT,           -- "pre_validacion", "registro", "asientos", "api", "dashboard"
    descripcion TEXT,
    stack_trace TEXT,
    fix_intentado TEXT,
    fix_exitoso BOOLEAN,
    timestamp DATETIME
);
```

### 8. Reporter

Genera `reports/motor_campo_{sesion_id}.html` con:
- Resumen: total ejecutados, OK, bugs arreglados, bugs pendientes
- Tabla por grupo de escenarios
- Detalle de cada bug (expandible)
- Gráfico de cobertura por proceso

---

## Escenarios (38 total)

### Grupo 1: Facturas Cliente (5)
| ID | Descripción | Variantes |
|----|-------------|-----------|
| `fc_basica` | FC española IVA 21% | importes × fechas = 16 |
| `fc_iva_reducido` | FC con IVA 10% y 4% | importes × IVA = 8 |
| `fc_intracomunitaria` | FC cliente UE, IVA 0% | importes × países = 12 |
| `fc_usd` | FC en dólares con tasaconv | importes × tasaconv = 10 |
| `fc_multilinea` | FC con 3+ líneas e IVA mixto | combinaciones líneas = 15 |

### Grupo 2: Facturas Proveedor (4)
| ID | Descripción | Variantes |
|----|-------------|-----------|
| `fv_basica` | FV española IVA 21% | importes × fechas = 16 |
| `fv_intracomunitario` | FV proveedor alemán IVA 0% + autoliquidación | importes × países = 12 |
| `fv_suplidos` | FV con suplidos aduaneros (4709) | combinaciones suplidos = 10 |
| `fv_usd` | FV en USD con conversión EUR | importes × tasaconv = 10 |

### Grupo 3: Documentos Especiales (6)
| ID | Descripción | Variantes |
|----|-------------|-----------|
| `nc_cliente` | NC rectificativa de FC | importes (parcial/total) = 8 |
| `nc_proveedor` | NC rectificativa de FV | importes (parcial/total) = 8 |
| `nom_basica` | Nómina con IRPF + SS | importes brutos × retenciones = 12 |
| `sum_suministro` | Suministro (luz/agua/teléfono) | tipos × importes = 9 |
| `rlc_ss` | Recibo liquidación SS | cuotas × períodos = 6 |
| `imp_tasa` | Impuesto/tasa AAPP | tipos × importes = 8 |

### Grupo 4: Bancario (5)
| ID | Descripción | Variantes |
|----|-------------|-----------|
| `ban_c43_estandar` | Extracto Norma 43 AEB | movimientos × saldos = 10 |
| `ban_c43_caixabank` | Extracto C43 formato CaixaBank extendido | movimientos × tipos = 10 |
| `ban_xls_caixabank` | Extracto XLS CaixaBank | filas × columnas = 8 |
| `ban_conciliacion_exacta` | Match exacto movimiento ↔ asiento | N movimientos = 10 |
| `ban_conciliacion_aprox` | Match aproximado (±1%, ±2 días) | tolerancias × días = 12 |

### Grupo 5: Gate 0 (5)
| ID | Descripción | Variantes |
|----|-------------|-----------|
| `gate0_trust_maxima` | Trust MAXIMA → AUTO_PUBLICADO | scores = 8 |
| `gate0_trust_baja` | Trust BAJA + score bajo → CUARENTENA | scores = 8 |
| `gate0_duplicado` | SHA256 duplicado → 409 | estados previos = 6 |
| `gate0_supplier_auto` | Supplier rule auto-aplicable (≥90%, ≥3 muestras) | reglas = 8 |
| `gate0_supplier_nueva` | Supplier rule nueva → crear y aprender | correcciones = 6 |

### Grupo 6: API/Seguridad (5)
| ID | Descripción | Variantes |
|----|-------------|-----------|
| `api_auth_2fa` | Login + 2FA TOTP completo | estados 2FA = 6 |
| `api_rate_limit` | Rate limiting (5 login/min) + lockout (5 intentos) | velocidades = 8 |
| `api_multitenant` | Empresa A no puede ver datos empresa B | combinaciones = 10 |
| `api_rgpd` | Export RGPD token único 24h | estados token = 6 |
| `api_modelo303` | Calcular modelo 303 trimestral | períodos × regímenes = 12 |

### Grupo 7: Fidelidad Dashboard (8)
| ID | Descripción |
|----|-------------|
| `dash_pyg` | PYG ingresos/gastos == suma facturas registradas |
| `dash_balance` | Activo == Pasivo + PN |
| `dash_iva` | 477 HABER == IVA repercutido FC. 472 DEBE == IVA soportado FV |
| `dash_libro_diario` | DEBE global == HABER global en libro diario |
| `dash_sync_fs_bd` | Factura creada en FS → aparece en BD local (Asiento/Partida) |
| `dash_ratios` | Liquidez, solvencia, rentabilidad calculados correctamente |
| `dash_conciliacion` | Movimientos conciliados reflejados en estado dashboard |
| `dash_modelo303` | 303 calculado por motor == suma manual cuotas del período |

---

## Modos de ejecución

```bash
# Todos los escenarios × todas las variantes
python scripts/motor_campo.py --modo completo

# 1 variante por escenario (ciclo rápido ~5 min)
python scripts/motor_campo.py --modo rapido

# Ciclo infinito (pausa configurable entre ciclos)
python scripts/motor_campo.py --modo continuo --pausa 300

# Un escenario específico
python scripts/motor_campo.py --escenario fc_basica

# Un grupo completo
python scripts/motor_campo.py --grupo bancario
```

---

## Consumo de recursos

| Recurso | Consumo |
|---------|---------|
| Mistral / GPT / Gemini | **0 llamadas** |
| FacturaScripts API | ~10-50 llamadas por escenario (crear + limpiar) |
| SFCE API local | ~5-20 llamadas por escenario |
| BD local SQLite | Escrituras + lecturas por escenario |
| CPU | Bajo (sin procesamiento imagen/OCR) |

---

## Archivos nuevos

```
scripts/motor_campo.py              # Orquestador principal
scripts/motor_campo/
    catalogo/
        fc.py, fv.py, especiales.py, bancario.py, gate0.py, api.py, dashboard.py
    generador.py
    executor.py
    validator.py
    autofix.py
    cleanup.py
    bug_registry.py
    reporter.py
    plantilla_reporte.html
data/
    motor_campo.db                  # SQLite bugs + ejecuciones
reports/
    motor_campo_*.html              # Reportes generados
```
