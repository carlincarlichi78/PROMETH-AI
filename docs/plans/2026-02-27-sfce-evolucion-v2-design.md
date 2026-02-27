# SFCE Evolucion v2 — Design Doc

**Fecha**: 2026-02-27
**Estado**: Aprobado
**Sustituye a**: `2026-02-27-sfce-evolucion-arquitectura-design.md` (v1)
**Cambios respecto v1**: operaciones contables completas, todos los territorios fiscales, BD ampliada con doble motor, trazabilidad de decisiones, cuarentena estructurada, modelos fiscales por categoria, deteccion trabajadores, rol Claude Code

---

## 1. Contexto y motivacion

### Que es SFCE
Sistema de Facturacion y Contabilidad Evolutivo. Automatiza la contabilidad para clientes de gestoria: recibe PDFs, extrae datos via OCR, clasifica, registra en FacturaScripts, corrige, valida y genera modelos fiscales.

### Problema actual
El sistema esta acoplado a dos tipos de entidad (SL + autonomo estimacion directa) con:
- Subcuentas hardcodeadas en config.yaml por proveedor
- Logica de regimen IVA dispersa entre registration.py y correction.py
- Asientos directos con plantillas fijas en YAML
- Valores fiscales hardcodeados en codigo
- Sin soporte para: modulos, recargo equivalencia, criterio de caja, profesionales con retencion, comunidades, IGIC, bienes de inversion, amortizaciones
- Sin operaciones de cierre de ejercicio
- Sin trazabilidad de decisiones contables
- Sin soporte para territorios forales

### Objetivo
SFCE debe cubrir **todos los casos fiscales** que una gestoria pueda enviar: cualquier tipo de persona fisica o juridica, cualquier regimen de IVA, cualquier territorio fiscal espanol. Ademas debe:
- Ejecutar el ciclo contable completo (dia a dia, trimestral, anual, cierre)
- Mostrar contabilidad en tiempo real via dashboard
- Explicar cada decision contable con trazabilidad completa
- Importar historico contable de clientes existentes
- Exportar en formatos universales
- Ser desplegable como producto a clientes
- Mantener normativa fiscal actualizada por ejercicio y territorio
- Funcionar siempre con Claude Code como cerebro operativo

---

## 2. Decisiones estrategicas

| Decision | Eleccion | Razon |
|----------|---------|-------|
| FacturaScripts | Mantener con capa abstraccion | Funciona, es gratis. Abstraccion permite cambiar en futuro |
| Onboarding | Semi-automatico | SFCE propone config.yaml desde libro diario, usuario valida |
| Output gestorias | CSV universal libro diario | Compatible con todos los programas contables |
| Estructura codigo | Reorganizar internamente | sfce/ (motor) + clientes/ (datos) en mismo repo |
| BD propia | Si, SQLite + PostgreSQL via SQLAlchemy | SQLite para desktop, PostgreSQL para SaaS |
| Dashboard | React + TypeScript + Tailwind + FastAPI | Stack del usuario, local, tiempo real via WebSocket |
| Proteccion producto | OCR proxy + token + SaaS | Sin Nuitka. SaaS como modelo principal |
| Modelos fiscales | 3 categorias: automaticos, semi-auto, asistidos | Honestidad sobre lo que se puede automatizar |
| Claude Code | Siempre en la ecuacion | Dashboard complementa, nunca reemplaza |

---

## 3. Estructura del proyecto reorganizada

```
CONTABILIDAD/
├── sfce/                              <- Motor (todo el codigo)
│   ├── core/                          <- Modulos base
│   │   ├── motor_reglas.py            <- Motor central de reglas
│   │   ├── perfil_fiscal.py           <- Modelo de perfil fiscal
│   │   ├── clasificador.py            <- Clasificador contable (cascada 6 niveles)
│   │   ├── decision.py                <- DecisionContable + log razonamiento
│   │   ├── backend.py                 <- Abstraccion sobre FS
│   │   ├── operaciones_periodicas.py  <- Amortizaciones, provisiones, regularizacion
│   │   ├── cierre_ejercicio.py        <- Regularizacion + cierre + apertura
│   │   ├── calculador_modelos.py      <- Modelos fiscales (auto/semi/asistido)
│   │   ├── importador.py              <- Importa libro diario previo
│   │   ├── exportador.py              <- Genera CSV/Excel universal
│   │   ├── duplicados.py              <- Deteccion duplicados
│   │   ├── cache_ocr.py              <- Cache OCR reutilizable
│   │   ├── nombres.py                 <- Naming conventions
│   │   ├── notificaciones.py          <- Email + WebSocket
│   │   ├── recurrentes.py             <- Facturas recurrentes faltantes
│   │   ├── ingesta_email.py           <- IMAP ingestion
│   │   ├── licencia.py                <- Verificacion licencia
│   │   ├── config.py                  <- Existente: cargador config cliente
│   │   ├── fs_api.py                  <- Existente: cliente API FS
│   │   ├── aprendizaje.py             <- Existente
│   │   ├── asientos_directos.py       <- Existente (refactorizar)
│   │   ├── aritmetica.py              <- Existente
│   │   ├── logger.py                  <- Existente
│   │   ├── confidence.py              <- Existente
│   │   ├── prompts.py                 <- Existente
│   │   ├── ocr_gemini.py              <- Existente
│   │   └── ocr_mistral.py             <- Existente
│   ├── phases/                        <- Pipeline (7 fases)
│   │   └── (intake, pre_validation, registration, asientos,
│   │       correction, cross_validation, output)
│   ├── normativa/                     <- Fuente unica verdad fiscal
│   │   ├── base.yaml                  <- Parametros estables
│   │   ├── 2024.yaml
│   │   ├── 2025.yaml
│   │   ├── 2026.yaml
│   │   └── vigente.py                 <- API con parametro territorio
│   ├── reglas/                        <- Reglas organizadas por nivel
│   │   ├── pgc/                       <- Nivel 1: plan contable
│   │   ├── negocio/                   <- Nivel 3: experiencia gestor
│   │   └── aprendizaje/               <- Nivel 5: auto-generado
│   ├── db/                            <- Base de datos local
│   │   ├── base.py                    <- Doble motor SQLite/PostgreSQL
│   │   ├── modelos.py                 <- Tablas SQLAlchemy (13 tablas)
│   │   ├── repositorio.py             <- Queries
│   │   └── migraciones/
│   └── api/                           <- Backend API para dashboard
│       ├── app.py                     <- FastAPI
│       ├── auth.py                    <- JWT autenticacion
│       ├── rutas/
│       └── websocket.py               <- Eventos tiempo real
├── dashboard/                         <- React + Tailwind
├── clientes/                          <- Workspace (datos de clientes)
├── scripts/                           <- CLIs (pipeline, onboarding, watcher, etc.)
├── tests/
└── docs/
```

---

## 4. Perfil fiscal (modelo de datos)

El perfil fiscal es el ADN contable de cada entidad. Determina todo: subcuentas, IVA, modelos, asientos.

```yaml
perfil_fiscal:
  # --- IDENTIDAD ---
  tipo_persona: juridica              # fisica | juridica
  forma_juridica: sl                  # autonomo | profesional | sl | slu | sa | sll | cb | scp | cooperativa | asociacion | comunidad_propietarios

  # --- TERRITORIO ---
  territorio: peninsula               # peninsula | canarias | ceuta_melilla | navarra | pais_vasco
  impuesto_indirecto: iva             # iva | igic | ipsi (auto-derivado de territorio)

  # --- REGIMEN IVA/IGIC ---
  regimen_iva: general                # general | simplificado | recargo_equivalencia | criterio_caja | exento | reagyp | agencias_viaje | bienes_usados
  prorrata: false
  pct_prorrata: 100
  sectores_diferenciados: false
  actividades:
    - nombre: "Actividad principal"
      epigrafe_iae: "XXX.X"
      regimen_iva: general

  # --- IRPF (solo personas fisicas) ---
  regimen_irpf: null                  # directa_simplificada | directa_normal | objetiva | null
  retencion_emitidas: false
  pct_retencion_emitidas: null        # 15 | 7

  # --- MODULOS (solo si regimen_irpf=objetiva) ---
  modulos:
    personal_asalariado: 0
    personal_no_asalariado: 1
    potencia_electrica_kw: 0
    superficie_local_m2: 0
    indices_actividad: {}

  # --- IMPUESTO SOCIEDADES (solo juridicas) ---
  tipo_is: null                       # 25 | 23 | 15 | 20 | 10 | null
  pagos_fraccionados_is: false
  bases_negativas_pendientes: 0.0

  # --- RETENCIONES QUE PRACTICA ---
  retiene_profesionales: false
  retiene_alquileres: false
  retiene_capital: false
  paga_no_residentes: false

  # --- OPERACIONES ESPECIALES ---
  operador_intracomunitario: false
  importador: false
  exportador: false
  isp_construccion: false
  isp_otros: false
  operaciones_vinculadas: false

  # --- BIENES DE INVERSION ---
  tiene_bienes_inversion: false
  amortizacion_metodo: lineal
  regularizacion_iva_bi: false

  # --- TAMANO / OBLIGACIONES ESPECIALES ---
  sii_obligatorio: false
  gran_empresa: false
  deposita_cuentas: false
  tipo_cuentas: null                  # normales | abreviadas | pymes

  # --- PLAN CONTABLE ---
  plan_contable: pgc_pymes
```

### Trabajadores (seccion nueva en config.yaml)

```yaml
trabajadores:
  - nombre: "Garcia Lopez, Ana"
    dni: "12345678A"
    bruto_mensual: 2142.86
    pagas: 14
    fecha_alta: "2024-03-15"
    tipo_contrato: general    # general | temporal | fijo_discontinuo
    categoria: "grupo_5"
    confirmado: true           # false si fue detectado automaticamente
```

Deteccion automatica: cuando llega una nomina con DNI no conocido, el sistema crea entrada con `confirmado: false` y genera cuarentena para que el gestor confirme numero de pagas.

### Derivacion automatica de modelos

| Condicion | Trimestral | Anual |
|-----------|-----------|-------|
| `regimen_iva != exento` (peninsula) | **303** | **390** |
| `territorio: canarias` | **420** (IGIC) | — |
| `regimen_irpf: objetiva` | **131** | **100** |
| `regimen_irpf: directa_*` | **130** | **100** |
| `tipo_is != null` | — | **200** |
| `pagos_fraccionados_is` | **202** | — |
| `retiene_profesionales` | **111** | **190** |
| `retiene_alquileres` | **115** | **180** |
| `retiene_capital` | **123** | **193** |
| `operador_intracomunitario` | **349** | — |
| Operaciones > 3.005,06 con tercero | — | **347** |
| `deposita_cuentas` | — | Cuentas anuales RM |
| `gran_empresa` | Todo **mensual** | — |

---

## 5. Motor de reglas contables

### Principio
Ninguna fase del pipeline decide nada contable por su cuenta. Todas preguntan al motor.

### Jerarquia de reglas (6 niveles)

```
Nivel 0: NORMATIVA (ley vigente, versionada por ano y territorio)
Nivel 1: PGC (plan contable, estructura de cuentas)
Nivel 2: PERFIL FISCAL (por entidad)
Nivel 3: REGLAS DE NEGOCIO (experiencia del gestor)
Nivel 4: REGLAS POR CLIENTE (especificas)
Nivel 5: APRENDIZAJE (auto-generado, nunca contradice 0-4)
```

### Interfaz del motor

```python
class MotorReglas:
    def decidir_asiento(self, documento: dict) -> DecisionContable
    def validar_asiento(self, asiento: dict) -> list[Anomalia]
    def calcular_modelo(self, modelo: str, trimestre: str) -> dict
    def aprender(self, documento: dict, decision_humana: dict)
```

### Clasificador contable (cascada de decision)

```
1. Regla cliente explicita? (CIF->subcuenta) -> confianza 95%
2. Aprendizaje previo? (CIF visto antes) -> confianza 85%
3. Tipo documento? (NOM->640, SUM->628) -> confianza 80%
4. Palabras clave OCR? ("alquiler"->621) -> confianza 60%
5. Libro diario importado? -> confianza 75%
6. Ninguna -> CUARENTENA
```

Si confianza < 70%, va a cuarentena aunque tenga respuesta.

### DecisionContable (output del motor)

```python
@dataclass
class DecisionContable:
    subcuenta_gasto: str
    subcuenta_contrapartida: str
    codimpuesto: str
    tipo_iva: float
    recargo_equiv: float | None
    retencion_pct: float | None
    pct_iva_deducible: float          # NUEVO: 100, 50 (vehiculos), 0
    partidas: list[Partida]
    regimen: str
    isp: bool
    isp_tipo_iva: float | None        # Para autorepercusion
    confianza: int
    origen_decision: str
    cuarentena: bool
    motivo_cuarentena: str | None
    opciones_alternativas: list
    log_razonamiento: list[str]       # NUEVO: trazabilidad completa
```

---

## 6. Modulo normativa/ (parametros fiscales versionados por territorio)

### Estructura

```
sfce/normativa/
├── base.yaml        <- Parametros estables (estructura PGC, tipos persona)
├── 2024.yaml
├── 2025.yaml
├── 2026.yaml
└── vigente.py       <- API con parametro territorio
```

### Contenido YAML anual — estructura por territorio

```yaml
version: "2025-01-01"
vigente_desde: "2025-01-01"
vigente_hasta: "2025-12-31"

# --- PENINSULA + BALEARES ---
peninsula:
  iva:
    general: 21
    reducido: 10
    superreducido: 4
    recargo_equivalencia:
      general: 5.2
      reducido: 1.4
      superreducido: 0.5
  impuesto_sociedades:
    general: 25
    pymes: 23
    nueva_creacion: 15
    cooperativas: 20
    entidades_sin_lucro: 10
  irpf:
    tablas_retencion:
      - hasta: 12450
        tipo: 19
      - hasta: 20200
        tipo: 24
      - hasta: 35200
        tipo: 30
      - hasta: 60000
        tipo: 37
      - hasta: 300000
        tipo: 45
      - desde: 300000
        tipo: 47
    retencion_profesional: 15
    retencion_profesional_nuevo: 7
    retencion_alquiler: 19
    pago_fraccionado_130: 20

# --- CANARIAS ---
canarias:
  igic:
    general: 7
    reducido: 3
    tipo_cero: 0
    incrementado_1: 9.5
    incrementado_2: 15
    especial: 20
  impuesto_sociedades:  # mismo que peninsula
    general: 25
    pymes: 23
    nueva_creacion: 15
  irpf:  # mismo que peninsula
    tablas_retencion: [...]  # idem peninsula

# --- CEUTA Y MELILLA ---
ceuta_melilla:
  ipsi:
    tipo_1: 0.5
    tipo_2: 1.0
    tipo_3: 2.0
    tipo_4: 4.0
    tipo_5: 8.0
    tipo_6: 10.0
  impuesto_sociedades:
    general: 25
    bonificacion_ceuta_melilla: 50  # 50% bonificacion

# --- NAVARRA ---
navarra:
  iva:  # mismo que peninsula
    general: 21
    reducido: 10
    superreducido: 4
  impuesto_sociedades:
    general: 28
    pequena: 23
    micro: 20
    nueva_creacion: 17
    cooperativas: 20
  irpf:
    tablas_retencion:
      - hasta: 4171
        tipo: 13
      - hasta: 8800
        tipo: 22.5
      - hasta: 16550
        tipo: 28
      - hasta: 29600
        tipo: 35.5
      - hasta: 45000
        tipo: 39.5
      - hasta: 65000
        tipo: 45
      - hasta: 154000
        tipo: 49
      - desde: 154000
        tipo: 52
  umbrales:
    concierto_economico: 10000000
    pct_operaciones_fuera: 25

# --- PAIS VASCO ---
pais_vasco:
  iva:  # mismo que peninsula
    general: 21
    reducido: 10
    superreducido: 4
  impuesto_sociedades:
    general: 24
    pequena: 22
    micro: 20
    nueva_creacion: 14
  irpf:
    tablas_retencion:
      - hasta: 17360
        tipo: 23
      - hasta: 32990
        tipo: 28
      - hasta: 46060
        tipo: 35
      - hasta: 63820
        tipo: 40
      - hasta: 87980
        tipo: 45
      - hasta: 123590
        tipo: 49
      - desde: 123590
        tipo: 49
  umbrales:
    concierto_economico: 10000000
    pct_operaciones_fuera: 25

# --- COMUNES (todos los territorios) ---
seguridad_social:
  smi_mensual: 1134.00
  smi_diario: 37.80
  base_minima_general: 1260.00
  base_maxima_general: 4720.50
  tipo_contingencias_comunes_empresa: 23.60
  tipo_contingencias_comunes_trabajador: 4.70
  tipo_desempleo_general_empresa: 5.50
  tipo_desempleo_general_trabajador: 1.55
  tipo_fogasa: 0.20
  tipo_fp_empresa: 0.60
  tipo_fp_trabajador: 0.10
  tipo_mec: 0.50

umbrales:
  gran_empresa: 6014630.00
  modelo_347: 3005.06
  limite_efectivo: 1000.00
  sii_obligatorio: 6014630.00

plazos_presentacion:
  trimestral:
    T1: { desde: "04-01", hasta: "04-20" }
    T2: { desde: "07-01", hasta: "07-20" }
    T3: { desde: "10-01", hasta: "10-20" }
    T4: { desde: "01-01", hasta: "01-30" }
  anual:
    modelo_390: { desde: "01-01", hasta: "01-30" }
    modelo_200: { desde: "07-01", hasta: "07-25" }
    modelo_100: { desde: "04-01", hasta: "06-30" }
    modelo_347: { desde: "02-01", hasta: "02-28" }

amortizacion:
  tablas:
    - tipo_bien: "edificios_comerciales"
      pct_maximo_lineal: 2
      periodo_maximo_anos: 68
    - tipo_bien: "mobiliario"
      pct_maximo_lineal: 10
      periodo_maximo_anos: 20
    - tipo_bien: "equipos_informaticos"
      pct_maximo_lineal: 25
      periodo_maximo_anos: 8
    - tipo_bien: "vehiculos"
      pct_maximo_lineal: 16
      periodo_maximo_anos: 14
    - tipo_bien: "maquinaria"
      pct_maximo_lineal: 12
      periodo_maximo_anos: 18
    - tipo_bien: "utillaje"
      pct_maximo_lineal: 30
      periodo_maximo_anos: 8
    - tipo_bien: "instalaciones"
      pct_maximo_lineal: 10
      periodo_maximo_anos: 20
    - tipo_bien: "aplicaciones_informaticas"
      pct_maximo_lineal: 33
      periodo_maximo_anos: 6
```

### API vigente.py (con territorio)

```python
class Normativa:
    def iva_general(self, fecha, territorio="peninsula") -> float
    def iva_reducido(self, fecha, territorio="peninsula") -> float
    def impuesto_indirecto(self, fecha, territorio="peninsula") -> dict
    def tipo_is(self, categoria, fecha, territorio="peninsula") -> float
    def tabla_irpf(self, fecha, territorio="peninsula") -> list
    def retencion_profesional(self, nuevo, fecha, territorio="peninsula") -> float
    def seguridad_social(self, fecha) -> dict  # comun a todos
    def umbral(self, nombre, fecha) -> float
    def plazo_presentacion(self, modelo, trimestre, ano) -> dict
    def tabla_amortizacion(self, tipo_bien, fecha) -> dict
```

---

## 7. Ciclo contable completo

### 7.1. Operaciones del dia a dia

| Operacion | Asiento tipo | Origen |
|-----------|-------------|--------|
| Factura recibida (compra/gasto) | 6xx + 472 @ 400 | PDF OCR |
| Factura emitida (venta/ingreso) | 430 @ 7xx + 477 | PDF OCR (cliente la manda) |
| Nota de credito recibida | 400 @ 6xx + 472 (inverso) | PDF OCR |
| Nota de credito emitida | 7xx + 477 @ 430 (inverso) | PDF OCR |
| Nomina | 640 + 642 @ 476 + 4751 + 572 | PDF OCR |
| Suministro | 628 + 472 @ 410 | PDF OCR |
| Extracto bancario | 626/662 @ 572 | PDF OCR |
| Pago a proveedor | 400 @ 572 | Conciliacion bancaria (futuro) |
| Cobro de cliente | 572 @ 430 | Conciliacion bancaria (futuro) |

### 7.2. Nomina completa (asiento real)

El OCR extrae los importes de la nomina. El motor los mapea:

```
DEBE:
  640.xxx  Sueldos y salarios .......... {bruto}
  642.xxx  SS a cargo empresa .......... {ss_empresa}

HABER:
  476.xxx  SS acreedora ................ {ss_empresa + ss_trabajador}
  4751.xxx IRPF retenciones ............ {irpf}
  465.xxx  Remuneraciones ptes pago .... {neto}
     o 572.xxx  Bancos ................. {neto}
```

Provision pagas extras (operacion periodica, sin PDF):
```
Mensual:  640 @ 465 -> {bruto_mensual * pagas_extra / (pagas_total - pagas_extra) / 12}
Devengo:  465 @ 476 + 4751 + 572  (cuando llega nomina paga extra)
```

Validacion: los porcentajes de SS del YAML normativa se usan para verificar coherencia del OCR, no para calcular.

### 7.3. Nota de credito — flujo completo

```
1. OCR identifica NC (tipo_doc: "NC")
2. Motor busca factura original:
   - Por numero referencia en NC
   - Por CIF + importe similar + fecha cercana
   - Si no encuentra -> cuarentena ("vincular NC a factura original")
3. Generar asiento inverso (parcial o total):
   DEBE:  400 Proveedor ............. {total_nc}
   HABER: 6xx Gasto ................. {base_nc}
   HABER: 472 IVA soportado ......... {iva_nc}
4. Si factura original pagada -> generar cobro pendiente
5. Actualizar acumulados modelo 303, 347
```

### 7.4. Operaciones trimestrales

| Operacion | Asiento | Automatizable |
|-----------|---------|--------------|
| Regularizacion IVA | 477 @ 472 + 4750/4700 | SI, totalmente |
| Pago liquidacion IVA | 4750 @ 572 | NO (depende de pago real) |
| Pago fraccionado IRPF (130) | 473 @ 572 | NO |
| Ingreso retenciones (111) | 4751 @ 572 | NO |
| Liquidacion TC SS | 476 @ 572 | NO |

**Regularizacion IVA en detalle**:
```
Caso 1: IVA a pagar (477 > 472)
  DEBE:  477  IVA repercutido ......... {total_477}
  HABER: 472  IVA soportado ........... {total_472}
  HABER: 4750 HP acreedora IVA ........ {diferencia}

Caso 2: IVA a compensar (472 > 477)
  DEBE:  477  IVA repercutido ......... {total_477}
  DEBE:  4700 HP deudora IVA .......... {diferencia}
  HABER: 472  IVA soportado ........... {total_472}

Con prorrata: IVA no deducible -> 634 @ 472
```

### 7.5. Operaciones anuales / cierre de ejercicio

**Secuencia de cierre** (orden obligatorio):

```
1. Amortizaciones pendientes (si no se hicieron mensualmente)
   681 @ 281 por cada activo

2. Regularizacion existencias (si aplica)
   610 @ 300 (variacion)

3. Provision clientes dudoso cobro (si hay impagados > 6 meses)
   694 @ 490

4. Regularizacion prorrata definitiva (si prorrata)
   634/639 @ 472

5. Regularizacion IVA bienes inversion (casilla 78 modelo 303 T4)
   Ajuste 472 segun % afectacion real vs estimada

6. Periodificaciones
   Gastos anticipados: 480 @ 6xx
   Ingresos anticipados: 7xx @ 485

7. Gasto por Impuesto de Sociedades (solo juridicas)
   6300 @ 4752  (base_imponible * tipo_is)

8. Asiento de REGULARIZACION (cierra cuentas 6xx y 7xx)
   DEBE: 7xx (todos los ingresos) -> saldo a 0
   HABER: 6xx (todos los gastos) -> saldo a 0
   Diferencia -> 129 (resultado del ejercicio)

9. Asiento de CIERRE (cierra TODAS las cuentas)
   Todas las cuentas con saldo -> contrapartida inversa -> saldo 0

10. Asiento de APERTURA (1 de enero nuevo ejercicio)
    Inverso del cierre: reabre todas las cuentas patrimoniales
    (NO reabre 6xx ni 7xx)
```

**Distribucion del resultado** (tras Junta General, meses despues):
```
Beneficio: 129 @ 112 (reserva legal) + 526 (dividendos) + 113 (reservas voluntarias)
Perdida:   121 (resultado negativo) @ 129
```

### 7.6. Amortizaciones

**Tabla de activos fijos** (BD):
```
activos_fijos:
  id, empresa_id, descripcion, tipo_bien, fecha_adquisicion,
  valor_adquisicion, valor_residual, vida_util_anos,
  metodo_amortizacion, pct_amortizacion,
  amortizacion_acumulada, valor_neto_contable,
  fecha_baja, motivo_baja, iva_deducido, pct_iva_deducible
```

**Asiento mensual** (automatico via operaciones_periodicas):
```
DEBE:  681.xxx  Amortizacion inmov. material ... {cuota_mensual}
HABER: 281.xxx  Amort. acum. inmov. material ... {cuota_mensual}

cuota_mensual = (valor_adquisicion - valor_residual) * pct / 12
```

**Baja de activo** (manual, via dashboard o Claude Code):
```
DEBE:  572  Bancos .................. {precio_venta}
DEBE:  281  Amort. acumulada ........ {amort_acumulada}
HABER: 21x  Inmov. material ......... {valor_adquisicion}
HABER: 477  IVA repercutido ......... {iva_venta}
Si beneficio: HABER 771
Si perdida:   DEBE  671
```

### 7.7. IVA no deducible

El motor aplica `pct_iva_deducible` segun tipo de gasto:

| Gasto | % deducible | Fundamento |
|-------|------------|------------|
| Vehiculo turismo | 50% (presuncion AEAT) | Art 95.3.2 LIVA |
| Gasolina vehiculo mixto | 50% | Idem |
| Atenciones a clientes | 0% | Art 96.1.5 LIVA |
| Joyas, alimentos, espectaculos | 0% | Art 96.1 LIVA |
| Viajes empleados | 100% | Gasto empresa |
| Resto | 100% | General |

Asiento con IVA parcialmente deducible:
```
Factura gasolina 100 + 21 IVA, vehiculo 50%:

DEBE:  629  Combustible ......... 110,50  (100 + 10,50 no deducible)
DEBE:  472  IVA soportado .......  10,50  (solo 50%)
HABER: 400  Proveedor ........... 121,00
```

### 7.8. Operaciones periodicas programadas

| Tipo | Frecuencia | Asiento | Automatico |
|------|-----------|---------|------------|
| Amortizacion activos | Mensual | 681 @ 281 | SI |
| Provision pagas extras | Mensual | 640 @ 465 | SI |
| Regularizacion IVA | Trimestral | 477 @ 472 + 4750/4700 | SI |
| Provision vacaciones | Mensual (opcional) | 640 @ 4750 | Configurable |

Tabla BD `operaciones_periodicas`:
```
id, empresa_id, tipo, frecuencia (mensual/trimestral/anual),
ultima_ejecucion, proxima_ejecucion,
plantilla_asiento (JSON), activa, descripcion
```

---

## 8. Trazabilidad de decisiones

### Log de razonamiento por asiento

Cada asiento registrado incluye un log completo:

```json
{
  "documento": "FC_2025-06-15_B99999999_acme_1210.00.pdf",
  "tipo_doc": "FC",
  "razonamiento": [
    "1. Regla cliente: CIF B99999999 mapeado a 6000000001 (confianza 95%)",
    "2. Regimen IVA: general (perfil fiscal cliente, peninsula)",
    "3. Tipo IVA: 21% (normativa 2025)",
    "4. Retencion: no aplica",
    "5. IVA deducible: 100%",
    "6. ISP: no"
  ],
  "partidas": [
    {"subcuenta": "6000000001", "debe": 1000.00, "concepto": "base imponible"},
    {"subcuenta": "4720000000", "debe": 210.00, "concepto": "IVA soportado 21%"},
    {"subcuenta": "4000000001", "haber": 1210.00, "concepto": "proveedor Acme SL"}
  ],
  "verificaciones": {
    "aritmetica": "OK (base * 1.21 = total)",
    "subcuenta_valida": "OK",
    "no_duplicado": "OK",
    "coherencia_fiscal": "OK"
  },
  "ocr": {
    "motor": "mistral",
    "tier": 0,
    "confianza": 94
  },
  "confianza_final": 95,
  "origen_decision": "regla_cliente"
}
```

Se guarda en tabla `documentos.log_decision` (JSON).

### Retroalimentacion

Cuando el gestor corrige un asiento:
1. Sistema compara decision original vs correccion
2. Identifica en que paso de la cadena se equivoco
3. Genera regla de aprendizaje especifica
4. Log: "Correccion: subcuenta 6000000001 -> 6220000000. Motivo: gestor indica que Acme es reparaciones, no mercaderia. Aprendido."

---

## 9. Modelos fiscales — por categoria

### TOTALMENTE AUTOMATICOS

| Modelo | Logica | Datos necesarios |
|--------|--------|-----------------|
| **303** | Suma bases imponibles por tipo IVA, calcula cuotas | Facturas del trimestre |
| **390** | Resumen anual del 303 | Todos los 303 del ano |
| **111** | Suma retenciones practicadas a profesionales | Facturas con retencion |
| **190** | Resumen anual del 111 | Todos los 111 |
| **115** | Suma retenciones por alquileres | Facturas alquiler |
| **180** | Resumen anual del 115 | Todos los 115 |
| **130** | 20% del rendimiento neto (ingresos - gastos) | PyG del periodo |
| **131** | Cuotas segun indices de actividad | Perfil fiscal (modulos) |
| **347** | Operaciones > 3.005,06 por tercero | Facturas por CIF anuales |
| **349** | Operaciones intracomunitarias | Facturas intra-UE |
| **420** | Equivalente al 303 para IGIC | Facturas (Canarias) |

### SEMI-AUTOMATICOS (borrador contable + revision gestor)

| Modelo | Que pre-rellena SFCE | Que completa el gestor |
|--------|---------------------|----------------------|
| **200 (IS)** | Resultado contable, pagos a cuenta (202), bases negativas | Ajustes extracontables: gastos no deducibles (multas, liberalidades), amortizacion fiscal libre, diferencias temporarias |
| **202** | 18% del ultimo IS o base ultimo trimestre | Gestor valida |
| **Cuentas anuales** | Balance, PyG, memoria basica | Informe de gestion, auditoria si procede |

**Borrador modelo 200 en dashboard**:
```
RESULTADO CONTABLE (automatico)
  Ingresos: 500.000
  Gastos:  -380.000
  Resultado contable: 120.000

AJUSTES EXTRACONTABLES (gestor completa en dashboard)
  [ ] Gastos no deducibles: _______
  [ ] Amortizacion fiscal libre: _______
  [ ] Provisiones no deducibles: _______
  [ ] Otros: _______

BASE IMPONIBLE (recalculado automaticamente)
  Resultado + ajustes - bases negativas = _______

CUOTA (calculado)
  Tipo IS: 25% -> Cuota: _______
  - Pagos fraccionados (mod 202): -_______
  - Retenciones soportadas: -_______
  = A PAGAR/DEVOLVER: _______
```

### SOLO ASISTIDOS (SFCE aporta datos parciales)

| Modelo | Que aporta SFCE | Por que no se puede automatizar |
|--------|----------------|---------------------------------|
| **100 (IRPF)** | Rendimientos actividad economica (ingresos - gastos del negocio) | Requiere datos personales: rendimientos trabajo, capital, situacion familiar, deducciones vivienda, planes pensiones, deducciones CCAA |

Para el 100, SFCE genera un **informe de rendimientos de actividad economica** que el gestor copia en Renta Web de la AEAT.

---

## 10. BD local y sincronizacion

### Doble motor: SQLite + PostgreSQL

```python
# sfce/db/base.py
def crear_motor(config: dict):
    tipo = config.get("tipo_bd", "sqlite")
    if tipo == "sqlite":
        url = f"sqlite:///{config.get('ruta_bd', 'sfce.db')}"
        engine = create_engine(url, connect_args={"check_same_thread": False})
        # WAL mode + busy timeout para concurrencia basica
    elif tipo == "postgresql":
        url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        engine = create_engine(url, pool_size=10, max_overflow=20)
    return engine
```

Config:
```yaml
# Desktop (defecto)
base_datos:
  tipo_bd: sqlite
  ruta_bd: ./datos/sfce.db

# Servidor SaaS
base_datos:
  tipo_bd: postgresql
  db_host: localhost
  db_port: 5432
  db_user: sfce
  db_password_env: SFCE_DB_PASSWORD
  db_name: sfce_produccion
```

Reglas de compatibilidad:
- Sin SQL crudo: todo via SQLAlchemy ORM/Core
- Sin tipos especificos de motor
- Migraciones con Alembic (funciona en ambos)
- Tests en SQLite in-memory

Multi-tenancy SaaS: **schema por gestor** en PostgreSQL (aislamiento total de datos fiscales).

### Tablas (13 tablas)

```
empresas: id, nombre, cif, perfil_fiscal (JSON), config_path

proveedores_clientes: id, empresa_id, cif, nombre, subcuenta, regimen, codpais

trabajadores: id, empresa_id, nombre, dni, bruto_mensual, pagas,
              fecha_alta, tipo_contrato, confirmado

documentos: id, empresa_id, tipo_doc, ruta_pdf, estado, fecha_proceso,
            datos_ocr (JSON), confianza, tier_ocr, log_decision (JSON)

asientos: id, empresa_id, numero, fecha, concepto, documento_id,
          idasiento_fs (ref FS), origen (pipeline/periodico/cierre/manual)

partidas: id, asiento_id, subcuenta, debe, haber, concepto

facturas: id, empresa_id, tipo, numero, fecha, cif_tercero,
          base_imponible, iva, total, pagada, idfactura_fs

pagos: id, empresa_id, factura_id, fecha_pago, importe,
       medio_pago, referencia_bancaria, observaciones

movimientos_bancarios: id, empresa_id, cuenta_bancaria, fecha,
                       fecha_valor, concepto, importe, saldo,
                       referencia, factura_id (nullable), estado

activos_fijos: id, empresa_id, descripcion, tipo_bien,
               fecha_adquisicion, valor_adquisicion, valor_residual,
               vida_util_anos, metodo, pct_amortizacion,
               amortizacion_acumulada, fecha_baja, pct_iva_deducible

operaciones_periodicas: id, empresa_id, tipo, frecuencia,
                        ultima_ejecucion, proxima_ejecucion,
                        plantilla_asiento (JSON), activa

cuarentena: id, documento_id, tipo_pregunta, pregunta,
            opciones (JSON), datos_relevantes (JSON),
            prioridad, resuelto, decision, fecha_resolucion

audit_log: id, fecha, usuario, tabla, registro_id,
           accion (INSERT/UPDATE/DELETE),
           datos_anteriores (JSON), datos_nuevos (JSON), motivo

saldos_subcuenta: empresa_id, subcuenta, ejercicio,
                  saldo_debe, saldo_haber (recalculado en tiempo real)

aprendizaje_log: id, fecha, documento_id, error, estrategia, resultado
```

### Sincronizacion con FS

```
SFCE procesa documento
  -> Guarda en BD local (instantaneo)
  -> Envia a FS via backend.py (puede fallar/tardar)
  -> Si FS OK -> guarda idasiento_fs como referencia
  -> Si FS falla -> marca "pendiente_sync", reintenta luego
```

BD local = fuente de verdad para dashboard.
FS = copia sincronizada para respaldo.

---

## 11. Cuarentena estructurada

### Tipos de cuarentena

| Tipo | Pregunta | Opciones | Prioridad |
|------|----------|----------|-----------|
| subcuenta_desconocida | A que subcuenta va este gasto? | Lista subcuentas + "otra" | Alta |
| proveedor_nuevo | Confirmar datos proveedor | Datos OCR pre-rellenados | Media |
| trabajador_nuevo | Confirmar pagas del trabajador | 12, 14, 15 | Media |
| nota_credito_sin_origen | Vincular NC a factura original | Lista facturas candidatas | Alta |
| duplicado_posible | Es duplicado de factura X? | Si/No + ver ambas | Alta |
| baja_confianza | Verificar datos OCR (confianza <70%) | Datos extraidos | Media |
| conflicto_reglas | Regla cliente vs normativa | Explicacion del conflicto | Alta |

### Estructura de un item de cuarentena

```json
{
  "tipo": "trabajador_nuevo",
  "documento": "NOM_2025-01_garcia-lopez.pdf",
  "datos_relevantes": {
    "nombre": "Garcia Lopez, Ana",
    "dni": "12345678A",
    "bruto_mensual": 2142.86
  },
  "pregunta": "Numero de pagas anuales para este trabajador?",
  "opciones": [12, 14, 15],
  "default": 14,
  "prioridad": "media"
}
```

### Modos de resolucion

- **Batch** (produccion): pipeline procesa todo, cuarentena se resuelve despues. Claude Code o dashboard.
- **Interactivo** (Claude Code): pipeline genera resumen con pendientes. Claude Code pregunta al gestor y alimenta respuestas.

---

## 12. Importador de libro diario

(Sin cambios respecto v1)

Documentos que importa: libro diario CSV/Excel, censo proveedores, balance sumas y saldos, modelo 390.

Parser flexible con deteccion automatica de columnas. Genera config.yaml propuesto + reglas_cliente.yaml.

---

## 13. Exportador universal

(Sin cambios respecto v1)

Formatos: CSV libro diario, Excel multi-hoja, CSV facturas emitidas/recibidas, TXT modelos fiscales.

---

## 14. Dashboard

### Stack
React + TypeScript + Tailwind + Vite (frontend)
FastAPI + JWT auth (backend Python, lee BD local)
WebSocket (eventos tiempo real)

### Pantallas

```
DASHBOARD HOME
├── Vista general: empresas, estado, alertas
│
├── POR EMPRESA:
│   ├── Cuenta de resultados (PyG) — tiempo real
│   ├── Balance de situacion — tiempo real
│   ├── Libro diario — navegable, filtrable
│   ├── Libro mayor por subcuenta
│   ├── Modelos fiscales — automaticos + borrador 200
│   ├── Facturas emitidas/recibidas + PDF
│   ├── Activos fijos — amortizacion acumulada, baja
│   ├── Trabajadores — lista, provision pagas
│   ├── Documentos procesados — estado, confianza, log decision
│   ├── Cuarentena — decision humana pendiente
│   └── Configuracion — perfil fiscal, proveedores, reglas
│
├── PROCESAMIENTO:
│   ├── Inbox — PDFs pendientes, boton "Procesar"
│   ├── Pipeline en curso — progreso tiempo real
│   └── Historial — lotes, errores, metricas
│
├── HERRAMIENTAS:
│   ├── Importar libro diario — wizard
│   ├── Exportar — CSV/Excel/formatos
│   ├── Cierre de ejercicio — wizard guiado
│   ├── Operaciones periodicas — ver/ejecutar
│   └── Calendario fiscal — plazos por empresa con alertas
│
└── ADMIN:
    ├── Normativa vigente — ver/actualizar
    ├── Reglas de negocio — editar
    ├── Aprendizaje — ver patrones, promover/eliminar
    ├── Usuarios — gestion (JWT)
    └── Licencias — gestion clientes producto
```

### Autenticacion

JWT con 3 roles:
- **admin**: todo
- **gestor**: sus empresas, procesar, resolver cuarentena
- **readonly**: ver datos, exportar (para clientes del gestor)

---

## 15. Capa de abstraccion backend.py

(Sin cambios respecto v1)

SFCE nunca habla directamente con FS. Backend traduce. Doble destino: BD local (siempre) + FS (intento, retry si falla).

---

## 16. File watcher y modos de operacion

(Sin cambios respecto v1)

3 modos: manual, semi-auto, automatico. Demonio con watchdog.

---

## 17. Ingesta por email

(Sin cambios respecto v1)

IMAP, descarga adjuntos, OCR rapido, enruta por CIF o email remitente.

---

## 18. Notificaciones

(Sin cambios respecto v1)

Canales: dashboard (WebSocket), email. Eventos: documento procesado, proveedor/trabajador nuevo, documento ilegible, plazo fiscal, cuarentena, duplicado, factura recurrente faltante.

---

## 19. Cache OCR reutilizable

(Sin cambios respecto v1)

`.ocr.json` junto al PDF, hash SHA256 para invalidacion.

---

## 20. Deteccion de duplicados

(Sin cambios respecto v1)

Duplicado seguro (CIF + numero + fecha) -> rechazo. Posible duplicado (CIF + importe + fecha cercana) -> cuarentena.

---

## 21. Deteccion facturas recurrentes faltantes

(Sin cambios respecto v1)

Patron historico por proveedor, alerta si falta factura esperada. Minimo 3 ocurrencias.

---

## 22. Convencion de nombres

(Sin cambios respecto v1)

Carpetas: `{CIF}-{nombre-slug}/`. Documentos: `{TIPO}_{FECHA}_{CIF}_{nombre}_{importe}.pdf`.

---

## 23. Asientos por regimen especial

### Profesional con IRPF en emitidas
```
430 Cliente           1.065,00 DEBE
477 IVA repercutido     210,00 HABER
4751 HP acreedora ret.  150,00 HABER
705 Prestacion serv.  1.000,00 HABER
```

### Recargo de equivalencia
```
600 Compras          1.000,00 DEBE
472 IVA soportado      210,00 DEBE
472 Recargo equiv.      52,00 DEBE
400 Proveedor        1.262,00 HABER
```

### Criterio de caja — al facturar (IVA NO se devenga)
```
430 Cliente          1.210,00 DEBE
477* IVA pte cobro     210,00 HABER
700 Ventas           1.000,00 HABER
```

### Criterio de caja — al cobrar
```
477* IVA pte cobro     210,00 DEBE
477 IVA repercutido    210,00 HABER
```

### Estimacion objetiva (modulos)
```
600 Compras          1.000,00 DEBE
472 IVA soportado      210,00 DEBE
400 Proveedor        1.210,00 HABER
# Solo registra recibidas para 303 simplificado + 131
```

### Comunidad de propietarios
```
440 Propietarios       500,00 DEBE
751 Cuotas ordinarias  500,00 HABER
# Sin IVA, sin IS
```

### ISP domestica (construccion)
```
600 Subcontrata      1.000,00 DEBE
472 IVA soportado      210,00 DEBE
477 IVA repercutido    210,00 HABER
410 Acreedor         1.000,00 HABER
```

### IVA parcialmente deducible (vehiculo 50%)
```
629 Combustible        110,50 DEBE   (base + IVA no deducible)
472 IVA soportado       10,50 DEBE   (solo 50%)
400 Proveedor          121,00 HABER
```

---

## 24. Proteccion del producto

| Capa | Mecanismo |
|------|-----------|
| OCR via proxy | Llamadas OCR pasan por servidor del gestor. Sin proxy = sin OCR. Cola de reintentos si proxy cae temporalmente |
| Token por cliente | Cada instalacion tiene token unico, desactivable remotamente |
| Dashboard login | JWT con roles, gestionado por el gestor |
| Modelo SaaS | Acceso via navegador, sin distribuir codigo |

Modelo de despliegue principal: **SaaS en servidor del gestor**. Multi-tenant via schemas PostgreSQL. Docker compose (SFCE + FS + PostgreSQL + Dashboard).

Fallback OCR proxy: cola local de documentos pendientes. Si proxy cae, acumula y procesa cuando vuelve. Alerta al gestor.

---

## 25. Rol de Claude Code

Claude Code **siempre** esta en la ecuacion. El dashboard complementa, nunca reemplaza.

### Sin dashboard (fase actual)
```
Gestor -> Claude Code -> ejecuta pipeline -> lee resultados ->
pregunta al gestor (cuarentena) -> aplica correcciones ->
modifica codigo/config cuando algo no funciona
```

### Con dashboard
```
Dashboard: visualizacion, resolucion rapida de cuarentena, formularios
Claude Code: ejecuta pipeline, diagnostica errores, modifica motor,
             interpreta lenguaje natural, decisiones complejas,
             cierre de ejercicio, ajustes contables no estandar
```

Ejemplo: "Los asientos de nomina de Gerardo salen mal" -> Dashboard no puede hacer nada. Claude Code entiende, diagnostica, corrige.

Ejemplo: "Prepara el cierre 2025 de Pastorino" -> Claude Code ejecuta la secuencia completa de 10 pasos de cierre.

---

## 26. Conciliacion bancaria (futuro)

Cliente sube extracto bancario (CSV/OFX/Norma 43). SFCE cruza movimientos con facturas.

Tabla `movimientos_bancarios` ya incluida en el esquema BD (seccion 10).

No se implementa en primera fase. Interfaces preparadas.

---

## 27. Backlog post-implementacion

> El dashboard cubre informes, KPIs e impuestos en tiempo real de forma nativa.
> No se necesitan modulos separados.

| Feature | Prioridad | Dependencia |
|---------|-----------|-------------|
| Open Banking PSD2 (extractos auto) | Futura | BD + conciliacion |
| SII (Suministro Inmediato Informacion) | Futura | Solo para gran_empresa |
| Conciliacion bancaria | Futura | BD + movimientos_bancarios |

---

## 28. Resumen de componentes

| Componente | Prioridad | Estado |
|-----------|-----------|--------|
| Reorganizar sfce/ | P0 | Nuevo |
| perfil_fiscal.py + trabajadores | P0 | Nuevo |
| normativa/ (todos los territorios) | P0 | Nuevo |
| operaciones_periodicas.py | P0 | Nuevo |
| cierre_ejercicio.py | P0 | Nuevo |
| decision.py (con trazabilidad) | P0 | Nuevo |
| motor_reglas.py | P1 | Nuevo |
| clasificador.py | P1 | Nuevo |
| calculador_modelos.py (3 categorias) | P1 | Nuevo |
| backend.py (abstraccion) | P1 | Nuevo |
| db/ (13 tablas, doble motor) | P2 | Nuevo |
| Refactorizar registration/correction | P2 | Modificacion |
| importador.py | P2 | Nuevo |
| exportador.py | P2 | Nuevo |
| api/ (FastAPI + JWT auth) | P3 | Nuevo |
| dashboard/ (React, todas las vistas) | P3 | Nuevo |
| watcher.py | P3 | Nuevo |
| ingesta_email.py | P4 | Nuevo |
| notificaciones.py | P4 | Nuevo |
| cache_ocr.py | P4 | Nuevo |
| duplicados.py | P4 | Nuevo |
| recurrentes.py | P4 | Nuevo |
| nombres.py | P4 | Nuevo |
| licencia.py | P4 | Nuevo |
