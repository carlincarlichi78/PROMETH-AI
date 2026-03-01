# PROMETH-AI — Brainstorming completo: Ingesta 360 + Onboarding + Importacion historica

**Fecha:** 2026-03-01
**Estado:** Brainstorming capturado, pendiente writing-plans en sesion limpia
**Referencia:** Design doc aprobado `2026-03-01-spice-ingesta-360-design.md`

---

## 1. ESTADO ACTUAL DEL SISTEMA (verificado contra git + filesystem)

### Lo que ya funciona (1793 tests passing)

| Componente | Ubicacion |
|---|---|
| Pipeline OCR 7 fases | `sfce/phases/`, `sfce/core/` |
| Triple OCR (Mistral/GPT/Gemini) | `sfce/core/ocr_*.py` |
| Motor aprendizaje (YAML) | `sfce/core/aprendizaje.py` |
| Integracion FacturaScripts API | `sfce/core/fs_api.py`, `sfce/core/backend.py` |
| Modulo bancario (C43 + XLS + conciliacion) | `sfce/conectores/bancario/` |
| Modelos fiscales (28 modelos, PDF/TXT) | `sfce/modelos_fiscales/` |
| Dashboard React + FastAPI (16 modulos) | `dashboard/`, `sfce/api/` |
| Multi-tenant (gestoria → gestor → empresa) | migracion 004, JWT gestoria_id |
| Seguridad (2FA, lockout, RGPD, rate limiting) | `sfce/api/auth.py`, `sfce/api/rate_limiter.py` |
| Directorio empresas (AEAT/VIES) | `sfce/api/rutas/directorio.py` |
| Modulo correo backend (IMAP, clasificacion, API) | `sfce/conectores/correo/`, `sfce/api/rutas/correo.py` |
| Email catch-all `*@prometh-ai.es` → Gmail | ImprovMX configurado |

### Plan 28/02 — 14 tasks, estado real

| Task | Descripcion | Estado |
|---|---|---|
| 1 | Migracion BD 5 tablas correo | ✅ commit d614132 |
| 2 | Cifrado Fernet credenciales IMAP | ✅ commit cff4ded |
| 3 | Conector IMAP incremental por UID | ✅ commit b17fd99 |
| 4 | Extractor de enlaces HTML | ✅ commit 4d155df |
| 5 | Motor clasificacion 3 niveles | ✅ commit ef53635 |
| 6 | Renombrado post-OCR adjuntos | ✅ commit aa5fd26 |
| 7 | Orquestador ingesta + polling | ✅ commit ee9cbe3 |
| 8 | API REST modulo correo | ✅ commit 2844a52 |
| 9 | Frontend modulo correo Dashboard | ❌ pendiente |
| 10 | Cliente HTTP CertiGestor | ❌ pendiente |
| 11 | Webhook receiver AAPP | ❌ pendiente |
| 12 | Bridge scrapers → inbox | ❌ pendiente |
| 13 | API portal unificado | ❌ pendiente (portal.py basico existe) |
| 14 | Export deadlines iCal | ❌ pendiente |

---

## 2. DECISIONES CONFIRMADAS

- **Task 9** (frontend correo): incluir en el plan
- **CertiGestor** (Tasks 10-12): incluir
- **Base de datos**: SQLite (sin migrar a PG hasta fase servidor dedicado)
- **Arranque**: Fase 0 (seguridad P0) primero, luego plan completo
- **Email dedicado**: `*@prometh-ai.es` ya funciona (ImprovMX catch-all → Gmail)
- **Onboarding**: incluir como bloque completo
- **Importacion historica**: incluir, faseado progresivamente
- **Arquitectura config**: hibrido (datos estructurados en BD, perfil en `config_extra` JSON)

---

## 3. FLUJOS DE ONBOARDING

### 3.1 Alta Gestoria (tenant)

**Quien lo hace**: Superadmin
**Tabla destino**: `gestorias`

```
Datos requeridos:
  - nombre
  - email_contacto
  - cif
  - modulos (JSON: ["contabilidad"])
  - plan_asesores (ej: 3)
  - plan_clientes_tramo (ej: "1-10")

Post-alta:
  - Crear 1 usuario admin_gestoria (el jefe de la gestoria)
```

**Estado actual**: tabla existe, endpoint NO existe, UI NO existe.

### 3.2 Alta Gestor / Asesor (usuario)

**Quien lo hace**: Admin gestoria
**Tabla destino**: `usuarios`

```
Datos requeridos:
  - email
  - nombre
  - rol: "asesor" | "admin_gestoria"
  - gestoria_id (automatico desde JWT del admin)
  - empresas_asignadas (JSON: [1, 4, 7])
  - password temporal → forzar cambio en primer login
  - 2FA opcional

Asesor independiente:
  - rol = "asesor_independiente"
  - gestoria auto-creada (unipersonal)
```

**Estado actual**: tabla existe con todos los campos, endpoints de invitacion NO existen.

### 3.3 Alta Cliente / Empresa — LO MAS IMPORTANTE

**Quien lo hace**: Gestor o Admin gestoria
**Tablas destino**: `empresas` + `proveedores_clientes`

#### Paso 1: Datos basicos (obligatorio)

```
Tabla: empresas
  - cif                  ← validar contra AEAT/VIES (Directorio ya existe)
  - nombre
  - forma_juridica       ← autonomo / sl / sa / cb / sc / coop
  - territorio           ← peninsula / canarias / ceuta
  - regimen_iva          ← general / simplificado / recargo_equivalencia
  - gestoria_id          ← automatico desde JWT
```

#### Paso 2: Perfil de negocio (recomendado)

```
Campo: empresas.config_extra (JSON)
  perfil:
    descripcion:         "Importacion de limones argentinos"
    modelo_negocio:      "Consignacion con anticipo..."
    actividades:         [{codigo: "4631", descripcion: "Comercio al por mayor",
                           iva_venta: 4, exenta: false}]
    particularidades:    ["IVA PT no deducible", "Facturas USD"]
    empleados:           true/false
    importador:          true/false
    exportador:          true/false
    divisas_habituales:  [USD]
    prorrata:            {tipo: "sectores_diferenciados"} (si aplica)
  tolerancias:
    cuadre_asiento:      0.01
    confianza_minima:    85
  banco:
    - "ES13 2100 3889 1802 0018 6156"
```

#### Paso 3: Proveedores / clientes habituales (opcional)

```
Tabla: proveedores_clientes (N registros)
  - cif, nombre, tipo (proveedor/cliente)
  - subcuenta_gasto (6000000000)
  - codimpuesto (IVA0, IVA4, IVA10, IVA21)
  - regimen (general, intracomunitario, extracomunitario)
  - pais, aliases

  Datos extra en JSON o campos adicionales:
  - divisa (EUR, USD)
  - notas
  - reglas_especiales (patron_linea, codimpuesto override)
  - autoliquidacion (iva_pct, subcuenta_soportado, subcuenta_repercutido)
```

#### Paso 4: Configurar FacturaScripts (automatico)

```
Si el gestor quiere → crear empresa en FS via API:
  1. POST /api/3/empresas
  2. POST /api/3/ejercicios (codejercicio auto)
  3. Importar PGC (navegar EditEjercicio)
  4. Guardar idempresa_fs + codejercicio_fs en tabla empresas
```

#### Paso 5: Configurar fuentes de documentos (opcional)

```
  - Cuenta correo IMAP (tabla cuentas_correo, ya existe)
  - Email dedicado: slug@prometh-ai.es
  - Reglas de clasificacion (tabla reglas_clasificacion_correo, ya existe)
```

#### Gap critico: config.yaml vs BD

```
HOY:   Pipeline lee config.yaml (archivo YAML por cliente)
       → sfce/core/config.py carga YAML

FUTURO: Pipeline debe leer de BD
       → Funcion generar_config_desde_bd(empresa_id)
       → Devuelve mismo dict que config.yaml pero desde tablas
       → Pipeline NO se modifica, solo cambia la fuente de datos
```

---

## 4. IMPORTACION HISTORICA — FASEADO

### Que puede traer cada tipo de cliente

**AUTONOMO (caso comun):**
- Libro de gastos (Excel/PDF)
- Libro de ingresos (Excel/PDF)
- Facturas recibidas y emitidas (PDFs sueltos o ZIP)
- Modelos trimestrales (303, 130, 111)
- Declaracion renta (modelo 100)
- Extractos bancarios

**EMPRESA (SL/SA):**
- Todo lo del autonomo MAS:
- Balance de situacion
- Cuenta de PyG
- Libro mayor
- Libro diario (asientos)
- Libro de bienes de inversion
- Cuentas anuales depositadas
- Modelo 200 (Impuesto Sociedades)
- Modelo 347 (operaciones con terceros)
- Backup de software anterior (A3, Sage, ContaPlus, NCS...)

### Capacidad actual del sistema

| Tipo documento | ¿Lo procesa hoy? |
|---|---|
| Facturas PDF sueltas | ✅ Pipeline OCR |
| Extractos bancarios C43/XLS | ✅ Parser bancario |
| ZIP de facturas | ❌ Fase 8 (pendiente) |
| Libro gastos/ingresos Excel | ❌ |
| Balances / PyG (PDF/Excel) | ❌ |
| Libro mayor / diario | ❌ |
| Modelos fiscales PDF AEAT | ❌ |
| Backup A3/Sage/ContaPlus | ❌ |
| Libro bienes inversion | ❌ |

### Fases de implementacion del importador historico

```
FASE I — Lo inmediato (mayor impacto, menor esfuerzo)
─────────────────────────────────────────────────────
  a) ZIP de facturas → descomprimir + pipeline OCR individual
     (ya planificado como Fase 8 del design doc)

  b) Generacion automatica de perfil POST-pipeline:
     Despues de procesar N facturas, analizar resultados:
     → "23 proveedores detectados, 80% IVA21"
     → "Opera con USD y EUR"
     → "Importador (facturas extracomunitarias detectadas)"
     → Auto-generar config_extra y proveedores_clientes
     → Presentar al gestor: "He detectado esto, ¿confirmas?"

  c) Extractos bancarios historicos (C43/XLS ya funciona):
     Subir 12 meses de extractos → patron de gastos recurrentes
     → Detectar domiciliaciones (luz, agua, telefono, seguro)
     → Pre-crear proveedores de suministros


FASE II — Excel/CSV (el formato mas comun de autonomos)
─────────────────────────────────────────────────────
  a) Parser de libro de gastos/ingresos Excel:
     Columnas tipicas: fecha, concepto, base, IVA, total, proveedor
     → Mapear a proveedores_clientes
     → Detectar subcuentas habituales
     → Importar como asientos historicos en BD local

  b) Parser de libro de gastos/ingresos PDF:
     OCR + IA para extraer tabla de un PDF escaneado
     → Mismo flujo que Excel

  c) CSV generico con auto-deteccion de columnas:
     La IA analiza las cabeceras y mapea automaticamente


FASE III — Documentos fiscales AEAT
─────────────────────────────────────────────────────
  a) Modelo 303 (IVA trimestral):
     Extraer: bases imponibles, cuotas, resultado
     → Verificar coherencia con facturas importadas
     → Detectar actividades y tipos de IVA

  b) Modelo 390 (resumen anual IVA):
     → Perfil completo de actividad del ano

  c) Modelo 130/131 (pago fraccionado IRPF autonomos):
     → Confirmar regimen estimacion directa/objetiva

  d) Modelo 200 (Impuesto Sociedades):
     → Balance, PyG, datos fiscales completos

  e) Modelo 347 (operaciones con terceros):
     → Lista de proveedores/clientes con volumen >3005.06 EUR
     → Auto-crear proveedores_clientes con CIF verificado


FASE IV — Contabilidad estructurada
─────────────────────────────────────────────────────
  a) Libro diario (asientos):
     Excel/CSV/PDF con: fecha, cuenta, debe, haber, concepto
     → Importar como asientos historicos
     → Detectar plan contable usado (subcuentas)

  b) Libro mayor:
     → Verificar saldos contra asientos importados
     → Detectar subcuentas personalizadas

  c) Balance de situacion + PyG:
     → Snapshot de la empresa a fecha X
     → Asiento de apertura automatico

  d) Libro de bienes de inversion:
     → Crear activos fijos en tabla activos_fijos
     → Calcular amortizacion pendiente


FASE V — Migracion desde software contable
─────────────────────────────────────────────────────
  a) Adaptador A3 (formato exportacion A3)
  b) Adaptador Sage/ContaPlus (formato .SAI / .MDB)
  c) Adaptador NCS (formato propietario)
  d) Formato XBRL (cuentas anuales electronicas)
  e) Cada adaptador: detectar formato → extraer datos → normalizar
     → alimentar las mismas tablas que las fases anteriores
```

---

## 5. MAPA COMPLETO DE FASES DE EJECUCION

```
FASE 0:  Seguridad P0 (4 fixes)                          ~2-3h
         ─────────────────────────────────────────────

FASE 1:  Onboarding completo                              ~2 sesiones
         - API + UI alta gestoria
         - API + UI invitacion gestor/asesor
         - API + UI wizard alta empresa (5 pasos)
         - generar_config_desde_bd() para pipeline
         ─────────────────────────────────────────────

FASE 2:  Plan 28/02 pendiente (Tasks 9-14)                ~3 sesiones
         - Frontend modulo correo
         - CertiGestor (cliente HTTP, webhooks, bridge)
         - Portal unificado + iCal
         ─────────────────────────────────────────────

FASE 3:  Gate 0 + Scoring + Trust (design doc Fase 4)     ~2 sesiones
         - Preflight (identificar empresa, trust, validar)
         - Deduplicar SHA256
         - Motor de scoring
         - Decision automatica (auto-pub / cola / cuarentena)
         ─────────────────────────────────────────────

FASE 4:  Colas revision + Tracking (design doc Fase 5)    ~2 sesiones
         - Cola gestor, cola admin, cuarentena
         - Tabla documento_tracking
         - UI colas en dashboard
         ─────────────────────────────────────────────

FASE 5:  Enriquecimiento + Supplier Rules BD (Fase 6)     ~2 sesiones
         - Hints (email asunto, portal formulario, gestor)
         - Supplier Rules en BD (evolucion de aprendizaje.yaml)
         - Jerarquia de reglas (6 niveles)
         ─────────────────────────────────────────────

FASE 6:  Canales entrada nuevos (Fases 7-8)               ~1-2 sesiones
         - Email dedicado (slug@prometh-ai.es)
         - Upload masivo ZIP
         ─────────────────────────────────────────────

FASE 7:  Importacion historica I — inmediata               ~2 sesiones
         - ZIP facturas → pipeline OCR
         - Generacion auto de perfil post-pipeline
         - Extractos bancarios historicos → patron gastos
         ─────────────────────────────────────────────

FASE 8:  Importacion historica II — Excel/CSV              ~2 sesiones
         - Parser libro gastos/ingresos Excel
         - Parser libro gastos/ingresos PDF (OCR tabla)
         - CSV generico con auto-deteccion columnas
         ─────────────────────────────────────────────

FASE 9:  Importacion historica III — AEAT                  ~2 sesiones
         - Modelos 303, 390, 130/131, 200, 347
         - Extraer datos fiscales → verificar + perfil
         ─────────────────────────────────────────────

FASE 10: Importacion historica IV — contabilidad           ~3 sesiones
         - Libro diario, libro mayor
         - Balance + PyG → asiento apertura
         - Libro bienes inversion → activos fijos
         ─────────────────────────────────────────────

FASE 11: Importacion historica V — software contable       ~3 sesiones
         - Adaptadores A3, Sage/ContaPlus, NCS
         - XBRL (cuentas anuales electronicas)
         ─────────────────────────────────────────────

FASE 12: Migracion servidor dedicado                       cuando todo funcione
         - Nuevo VPS Hetzner
         - SQLite → PostgreSQL
         - Deploy PROMETH-AI completo
         ─────────────────────────────────────────────

FASE 13: WhatsApp                                          ultimo
         - Bot WhatsApp Business API
         - Phone → empresa_id mapping
         ─────────────────────────────────────────────
```

---

## 6. FLUJO COMPLETO DE UN DOCUMENTO (vision final)

```
  Email / Portal / ZIP / CertiGestor / WhatsApp / Importacion historica
                         |
                         v
              GATE 0 — preflight
        (empresa? trust? valido? duplicado? hints?)
                         |
                         v
        SUPPLIER RULES pre-rellenan campos
                         |
                         v
          PIPELINE OCR — 7 fases existentes
                         |
                         v
              SCORING automatico
                         |
              +----------+----------+
              |          |          |
         >=95 + trust   70-94     <50
              |          |          |
        AUTO-PUBLICA  COLA REV  CUARENTENA
         en FS        gestor     + alerta
              |          |
              |    gestor corrige
              |          |
              |    SUPPLIER RULE generada
              |    (proxima vez: score sube)
              |          |
              +-----+----+
                    |
             TRACKING visible
          (portal cliente + dashboard)
```

---

## 7. PREGUNTAS RESUELTAS

1. **Frontend correo (Task 9)** → incluir en plan
2. **CertiGestor (Tasks 10-12)** → incluir
3. **BD** → SQLite hasta fase servidor dedicado
4. **Arranque** → Fase 0 seguridad primero
5. **Email** → `*@prometh-ai.es` ya configurado
6. **Onboarding** → incluir como Fase 1 (antes del flujo documental)
7. **config.yaml vs BD** → hibrido con `generar_config_desde_bd()`
8. **Importacion historica** → incluir en 5 sub-fases (I-V)

---

## 8. PROXIMOS PASOS

1. **Abrir sesion limpia**
2. **Ejecutar `writing-plans`** con este brainstorming como input
3. **Scope del primer plan**: Fases 0-6 (seguridad + onboarding + correo + gate0 + scoring + colas + canales)
4. **Segundo plan separado**: Fases 7-11 (importacion historica completa)
5. **Tercer plan**: Fases 12-13 (servidor + WhatsApp)
