# SFCE Evolucion Arquitectonica — Design Doc

**Fecha**: 2026-02-27
**Estado**: Aprobado (pendiente plan de implementacion)
**Enfoque elegido**: B — Motor de reglas contables

---

## 1. Contexto y motivacion

### Que es SFCE
Sistema de Facturacion y Contabilidad Evolutivo. Automatiza la contabilidad para clientes de gestoria: recibe PDFs, extrae datos via OCR, clasifica, registra en FacturaScripts, corrige, valida y genera modelos fiscales.

### Problema actual
El sistema esta **muy acoplado** a dos tipos de entidad (SL + autonomo estimacion directa) con:
- Subcuentas hardcodeadas en config.yaml por proveedor
- Logica de regimen IVA dispersa entre registration.py y correction.py
- Asientos directos con plantillas fijas en YAML
- Valores fiscales (21%, 25%, 3005.06€) hardcodeados en codigo
- Sin soporte para: modulos, recargo equivalencia, criterio de caja, profesionales con retencion, comunidades, IGIC, bienes de inversion, amortizaciones

### Objetivo
SFCE debe cubrir **todos los casos fiscales** que una gestoria pueda enviar: cualquier tipo de persona fisica o juridica, cualquier regimen de IVA, cualquier territorio fiscal espanol. Ademas debe:
- Mostrar contabilidad en tiempo real via dashboard
- Importar historico contable de clientes existentes
- Exportar en formatos universales
- Ser desplegable como producto a clientes
- Mantener normativa fiscal actualizada por ejercicio

---

## 2. Decisiones estrategicas

| Decision | Eleccion | Razon |
|----------|---------|-------|
| FacturaScripts | Mantener con capa abstraccion | Funciona, es gratis. Abstraccion permite cambiar en futuro |
| Onboarding | Semi-automatico | SFCE propone config.yaml desde libro diario, usuario valida |
| Output gestorias | CSV universal libro diario | Compatible con todos los programas contables (A3, Sage, ContaPlus, Holded...) |
| Estructura codigo | Reorganizar internamente | sfce/ (motor) + clientes/ (datos) en mismo repo |
| BD propia | Si, SQLite (migrable a PostgreSQL) | Dashboard necesita datos instantaneos, no depender de API FS |
| Dashboard | React + TypeScript + Tailwind + FastAPI | Stack del usuario, local, tiempo real via WebSocket |
| Proteccion producto | Codigo compilado + OCR proxy | Sin API proxy el producto no funciona. Sin codigo fuente no se puede piratear |

---

## 3. Estructura del proyecto reorganizada

```
CONTABILIDAD/
├── sfce/                              ← Motor (todo el codigo)
│   ├── core/                          ← Modulos base
│   │   ├── motor_reglas.py            ← NUEVO: motor central de reglas
│   │   ├── perfil_fiscal.py           ← NUEVO: modelo de perfil fiscal
│   │   ├── clasificador.py            ← NUEVO: clasificador contable
│   │   ├── backend.py                 ← NUEVO: abstraccion sobre FS
│   │   ├── importador.py              ← NUEVO: importa libro diario previo
│   │   ├── exportador.py              ← NUEVO: genera CSV/Excel universal
│   │   ├── licencia.py                ← NUEVO: verificacion licencia
│   │   ├── config.py                  ← Existente: cargador config cliente
│   │   ├── fs_api.py                  ← Existente: cliente API FS (detras de backend.py)
│   │   ├── aprendizaje.py             ← Existente
│   │   ├── asientos_directos.py       ← Existente (refactorizar para usar motor)
│   │   ├── aritmetica.py              ← Existente
│   │   ├── logger.py                  ← Existente
│   │   ├── confidence.py              ← Existente
│   │   ├── prompts.py                 ← Existente
│   │   ├── ocr_gemini.py              ← Existente
│   │   └── ocr_mistral.py             ← Existente
│   ├── phases/                        ← Pipeline (7 fases)
│   │   ├── intake.py                  ← Existente
│   │   ├── pre_validation.py          ← Existente
│   │   ├── registration.py            ← Existente (refactorizar para usar motor)
│   │   ├── asientos.py                ← Existente
│   │   ├── correction.py              ← Existente (refactorizar para usar motor)
│   │   ├── cross_validation.py        ← Existente
│   │   └── output.py                  ← Existente
│   ├── normativa/                     ← NUEVO: fuente unica verdad fiscal
│   │   ├── base.yaml                  ← Parametros que rara vez cambian
│   │   ├── 2024.yaml
│   │   ├── 2025.yaml
│   │   ├── 2026.yaml
│   │   └── vigente.py                 ← API: dame parametro X en fecha Y
│   ├── reglas/                        ← Reglas globales organizadas por nivel
│   │   ├── pgc/                       ← Nivel 1: plan contable
│   │   │   ├── subcuentas_pgc.yaml
│   │   │   ├── regimenes_iva.yaml     ← NUEVO
│   │   │   └── perfiles_fiscales.yaml ← NUEVO: plantillas de perfil por forma juridica
│   │   ├── negocio/                   ← Nivel 3: experiencia del gestor
│   │   │   ├── validaciones.yaml
│   │   │   ├── errores_conocidos.yaml
│   │   │   ├── patrones_suplidos.yaml
│   │   │   └── coherencia_fiscal.yaml
│   │   └── aprendizaje/               ← Nivel 5: auto-generado
│   │       └── aprendizaje.yaml
│   ├── db/                            ← NUEVO: base de datos local
│   │   ├── modelos.py                 ← Tablas SQLAlchemy
│   │   ├── migraciones/
│   │   └── repositorio.py             ← Queries
│   └── api/                           ← NUEVO: backend API para dashboard
│       ├── app.py                     ← FastAPI
│       ├── rutas/
│       └── websocket.py               ← Eventos tiempo real
├── dashboard/                         ← NUEVO: React + Tailwind
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── clientes/                          ← Workspace (datos de clientes)
│   ├── pastorino-costa-del-sol/
│   │   ├── config.yaml                ← Incluye perfil_fiscal
│   │   ├── reglas_cliente.yaml        ← NUEVO: reglas nivel 4 especificas
│   │   ├── inbox/
│   │   └── procesado/
│   └── .../
├── scripts/                           ← CLIs
│   ├── pipeline.py
│   ├── onboarding.py
│   ├── watcher.py                     ← NUEVO: file watcher
│   └── ...
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
  regimen_irpf: null                  # directa_simplificada | directa_normal | objetiva | null (juridicas)
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
  pagos_fraccionados_is: false        # Modelo 202
  bases_negativas_pendientes: 0.0

  # --- RETENCIONES QUE PRACTICA ---
  retiene_profesionales: false        # 111/190
  retiene_alquileres: false           # 115/180
  retiene_capital: false              # 123/193
  paga_no_residentes: false           # 216

  # --- OPERACIONES ESPECIALES ---
  operador_intracomunitario: false    # ROI, 349
  importador: false                   # DUA, casilla 77
  exportador: false
  isp_construccion: false             # ISP domestica construccion
  isp_otros: false                    # ISP metales, chatarra, inmuebles
  operaciones_vinculadas: false       # 232

  # --- BIENES DE INVERSION ---
  tiene_bienes_inversion: false
  amortizacion_metodo: lineal         # lineal | degresivo | numeros_digitos
  regularizacion_iva_bi: false        # Casilla 78 modelo 303

  # --- TAMANO / OBLIGACIONES ESPECIALES ---
  sii_obligatorio: false
  gran_empresa: false
  deposita_cuentas: false
  tipo_cuentas: null                  # normales | abreviadas | pymes

  # --- PLAN CONTABLE ---
  plan_contable: pgc_pymes            # pgc | pgc_pymes | pgc_ent_no_lucro
```

### Derivacion automatica de modelos

El motor calcula modelos obligatorios a partir del perfil:

| Condicion | Trimestral | Anual |
|-----------|-----------|-------|
| `regimen_iva != exento` | **303** | **390** |
| `territorio: canarias` | **420** (IGIC) | — |
| `regimen_irpf: objetiva` | **131** | **100** |
| `regimen_irpf: directa_*` | **130** | **100** |
| `tipo_is != null` | — | **200** |
| `pagos_fraccionados_is` | **202** | — |
| `retiene_profesionales` | **111** | **190** |
| `retiene_alquileres` | **115** | **180** |
| `retiene_capital` | **123** | **193** |
| `operador_intracomunitario` | **349** | — |
| Operaciones > 3.005,06€ con tercero | — | **347** |
| `operaciones_vinculadas` + umbral | — | **232** |
| `deposita_cuentas` | — | Cuentas anuales RM |
| `gran_empresa` | Todo **mensual** | — |

### Tipos de persona soportados

**Personas fisicas:**
- Autonomo estimacion directa simplificada
- Autonomo estimacion directa normal
- Autonomo estimacion objetiva (modulos)
- Profesional (con retencion en emitidas)
- Autonomo societario
- Autonomo colaborador familiar (no lleva contabilidad propia)

**Personas juridicas:**
- S.L. / S.L.U.
- S.A.
- S.L.L. (Sociedad Laboral)
- Cooperativa
- Comunidad de Bienes (C.B.)
- Sociedad Civil (S.C.P.)
- Asociacion / Fundacion
- Comunidad de propietarios

### Regimenes IVA soportados
- General
- Simplificado (modulos)
- Recargo de equivalencia
- Criterio de caja
- Exento (sanidad, educacion, seguros)
- REAGYP
- Agencias de viaje
- REBU (bienes usados)

### Territorios fiscales
- Peninsula + Baleares (IVA)
- Canarias (IGIC)
- Ceuta y Melilla (IPSI)
- Navarra / Pais Vasco (IVA pero haciendas forales — diferencias en IS)

---

## 5. Motor de reglas contables

### Principio
Ninguna fase del pipeline decide nada contable por su cuenta. Todas preguntan al motor.

### Jerarquia de reglas (6 niveles)

```
Nivel 0: NORMATIVA (ley vigente, versionada por ano)
  → normativa/2025.yaml: tipos IVA, IS, IRPF, SS, umbrales, plazos
  → Inmutable por niveles inferiores

Nivel 1: PGC (plan contable, estructura de cuentas)
  → reglas/pgc/subcuentas_pgc.yaml
  → Define que significa cada cuenta

Nivel 2: PERFIL FISCAL (por entidad)
  → config.yaml: perfil_fiscal
  → Determina regimen, modelos, comportamiento

Nivel 3: REGLAS DE NEGOCIO (experiencia del gestor)
  → reglas/negocio/validaciones.yaml, patrones_suplidos.yaml
  → Definidas por el usuario, respetadas por el sistema

Nivel 4: REGLAS POR CLIENTE (especificas)
  → reglas_cliente.yaml: mapeo CIF→subcuenta, excepciones
  → Generadas por importador o por decision humana

Nivel 5: APRENDIZAJE (auto-generado)
  → reglas/aprendizaje/aprendizaje.yaml
  → Solo se aplica si no contradice niveles 0-4
  → Puede ser promovido a nivel 4 con confirmacion humana
```

### Resolucion de conflictos

Los niveles inferiores NUNCA contradicen a los superiores:
- Aprendizaje dice IVA=10%, normativa dice 21% → **Gana normativa**
- Regla cliente dice subcuenta 600, pero documento es alquiler → **Motor alerta**
- Perfil dice regimen general, factura tiene recargo equivalencia → **Cuarentena**
- Aprendizaje dice "CIF X va a 622", no hay regla cliente → **Gana aprendizaje**

### Interfaz del motor

```python
class MotorReglas:
    def __init__(self, normativa, pgc, perfil_fiscal, reglas_negocio,
                 reglas_cliente, aprendizaje):
        """Carga los 6 niveles en orden de prioridad"""

    def decidir_asiento(self, documento: dict) -> DecisionContable:
        """Dado un documento OCR, devuelve la decision completa:
        subcuenta, IVA, partidas, regimen, confianza, origen"""

    def validar_asiento(self, asiento: dict) -> list[Anomalia]:
        """Verifica un asiento contra todas las reglas"""

    def calcular_modelo(self, modelo: str, trimestre: str) -> dict:
        """Calcula un modelo fiscal desde los datos registrados"""

    def aprender(self, documento: dict, decision_humana: dict):
        """Registra una decision humana como nueva regla nivel 5"""
```

### Clasificador contable (cascada de decision)

```
1. ¿Regla cliente explicita? (CIF→subcuenta en config)
   SI → usar (confianza 95%)

2. ¿Aprendizaje previo? (CIF visto antes)
   SI → usar (confianza 85%)

3. ¿Tipo documento lo indica? (NOM→640, SUM→628, SEG→625)
   SI → usar (confianza 80%)

4. ¿Palabras clave OCR? ("alquiler"→621, "reparacion"→622)
   SI → sugerir (confianza 60%)

5. ¿Libro diario importado? (historial ejercicio anterior)
   SI → usar (confianza 75%)

6. Ninguna coincidencia → CUARENTENA
```

Si confianza < 70%, va a cuarentena aunque tenga respuesta. Usuario valida en dashboard, motor aprende.

### DecisionContable (output del motor)

```python
@dataclass
class DecisionContable:
    subcuenta_gasto: str           # "6220000000"
    subcuenta_contrapartida: str   # "4000000001"
    codimpuesto: str               # "IVA21"
    tipo_iva: float                # 21.0
    recargo_equiv: float | None    # 5.2 o None
    retencion_pct: float | None    # 15.0 o None
    partidas: list[Partida]        # Asiento completo pre-generado
    regimen: str                   # "general"
    isp: bool                      # Inversion sujeto pasivo
    confianza: int                 # 0-100
    origen_decision: str           # "regla_cliente" | "aprendizaje" | "tipo_doc" | "ocr_keywords"
    cuarentena: bool               # True si confianza < 70
    motivo_cuarentena: str | None
    opciones_alternativas: list    # Otras subcuentas posibles con su confianza
```

---

## 6. Modulo normativa/ (parametros fiscales versionados)

### Estructura

```
sfce/normativa/
├── base.yaml        ← Parametros estables (estructura PGC, tipos persona)
├── 2024.yaml        ← Parametros vigentes en 2024
├── 2025.yaml        ← Parametros vigentes en 2025
├── 2026.yaml        ← Parametros vigentes en 2026
└── vigente.py       ← API: consulta parametro por fecha
```

### Contenido de un YAML anual (ejemplo 2025.yaml)

```yaml
version: "2025-01-01"
vigente_desde: "2025-01-01"
vigente_hasta: "2025-12-31"

iva:
  general: 21
  reducido: 10
  superreducido: 4
  recargo_equivalencia:
    general: 5.2
    reducido: 1.4
    superreducido: 0.5
  excepciones:
    - producto: "electricidad"
      tipo: 21
      vigente_desde: "2025-01-01"
    - producto: "alimentos_basicos"
      tipo: 4
      vigente_desde: "2025-01-01"

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
  autonomos_tramos:
    - hasta: 670
      base_minima: 735.29
      base_maxima: 816.98
    - hasta: 900
      base_minima: 816.99
      base_maxima: 900.00

umbrales:
  gran_empresa: 6014630.00
  modelo_347: 3005.06
  limite_efectivo: 1000.00
  modulos_exclusion_irpf: 250000
  modulos_exclusion_iva: 250000
  sii_obligatorio: 6014630.00
  pymes_is_reducido: 1000000

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
    cuentas_anuales: { desde: "07-01", hasta: "07-30" }

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
```

### API vigente.py

```python
# sfce/normativa/vigente.py
def iva_general(fecha) -> float
def tipo_is(forma_juridica, facturacion, fecha) -> float
def retencion_profesional(nuevo_autonomo, fecha) -> float
def base_cotizacion_minima(regimen, fecha) -> float
def umbral(nombre, fecha) -> float
def plazo_presentacion(modelo, trimestre, fecha) -> dict
def tabla_amortizacion(tipo_bien, fecha) -> dict
```

Regla: **ningun valor fiscal se hardcodea en codigo**. Todo sale de normativa.

### Actualizacion

Cada inicio de ejercicio fiscal:
1. Copiar YAML del ano anterior
2. Actualizar solo lo que cambia
3. El motor usa automaticamente el YAML correcto segun la fecha del documento

---

## 7. Importador de libro diario

### Documentos que importa

| Documento | Formato | Que extrae |
|-----------|---------|-----------|
| Libro diario | CSV / Excel | CIF↔subcuenta, patrones clasificacion |
| Censo proveedores/clientes | CSV / Excel | CIF, nombre, subcuenta, codpais |
| Balance sumas y saldos | CSV / Excel / PDF | Saldos para verificacion |
| Modelo 390 | PDF | Regimen IVA, % aplicados |

### Flujo

```
1. Gestoria entrega documentos
2. importador.py lee libro diario
3. Extrae mapa CIF → subcuenta (con frecuencia de uso)
4. Extrae mapa CIF → regimen IVA inferido
5. Genera config.yaml PROPUESTO
6. Usuario revisa en dashboard y aprueba/corrige
7. Se genera config.yaml definitivo + reglas_cliente.yaml
```

### Parser flexible

Los libros diarios tienen estructura estandar:
```
Fecha | Asiento | Cuenta | Debe | Haber | Concepto | Documento
```

Parser con deteccion automatica de columnas para cubrir 90% de casos.
Mapeo manual de columnas en dashboard para el 10% restante.

---

## 8. Exportador universal

### Formato principal: CSV libro diario

```csv
fecha;num_asiento;cuenta;subcuenta;debe;haber;concepto;documento;contrapartida
01/01/2025;1;600;6000000001;1000.00;0.00;Compra mercancia FRA-001;FRA-001;4000000001
```

Separador configurable (`;` o `,`), encoding configurable (UTF-8 o ISO-8859-1).

### Formatos disponibles

| Formato | Contenido | Para quien |
|---------|----------|-----------|
| Excel multi-hoja | Diario + Balance + PyG + Libros IVA | Cliente directo / gestoria |
| CSV libro diario | Solo asientos | Importacion a cualquier programa |
| CSV facturas emitidas | Libro facturas emitidas | AEAT / auditoria |
| CSV facturas recibidas | Libro facturas recibidas | AEAT / auditoria |
| TXT modelos fiscales | 303, 111, 130, etc. | Referencia presentacion |

Formatos especificos (A3, Sage) se anaden bajo demanda como modulos del exportador.

---

## 9. BD local y sincronizacion con FS

### Tecnologia
SQLite (inicio). Migrable a PostgreSQL si escala.

### Tablas principales

```
empresas: id, nombre, cif, perfil_fiscal (JSON), config_path

proveedores_clientes: id, empresa_id, cif, nombre, subcuenta, regimen, codpais

documentos: id, empresa_id, tipo_doc, ruta_pdf, estado, fecha_proceso,
            datos_ocr (JSON), confianza, tier_ocr

asientos: id, empresa_id, numero, fecha, concepto, documento_id,
          idasiento_fs (ref FS)

partidas: id, asiento_id, subcuenta, debe, haber, concepto

facturas: id, empresa_id, tipo, numero, fecha, cif_tercero,
          base_imponible, iva, total, pagada, idfactura_fs (ref FS)

saldos_subcuenta: empresa_id, subcuenta, ejercicio, saldo_debe, saldo_haber
                  (recalculado en tiempo real)

cuarentena: id, documento_id, motivo, opciones (JSON), resuelto, decision

aprendizaje_log: id, fecha, documento_id, error, estrategia, resultado
```

### Sincronizacion con FS

```
SFCE procesa documento
  → Guarda en BD local (instantaneo)
  → Envia a FS via backend.py (puede fallar/tardar)
  → Si FS OK → guarda idasiento_fs como referencia
  → Si FS falla → marca "pendiente_sync", reintenta luego
```

BD local = fuente de verdad para dashboard.
FS = copia sincronizada para visualizacion/respaldo.

---

## 10. Dashboard

### Stack
React + TypeScript + Tailwind + Vite (frontend)
FastAPI (backend Python, lee BD local)
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
│   ├── Modelos fiscales — calculados al vuelo
│   ├── Facturas emitidas/recibidas + PDF
│   ├── Documentos procesados — estado, confianza, tier OCR
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
│   ├── Conciliacion bancaria — (futuro)
│   └── Calendario fiscal — plazos por empresa
│
└── ADMIN:
    ├── Normativa vigente — ver/actualizar
    ├── Reglas de negocio — editar
    ├── Aprendizaje — ver patrones, promover/eliminar
    └── Licencias — gestion clientes producto
```

### Tiempo real
Pipeline emite eventos via WebSocket. Dashboard actualiza PyG, balance, saldos sin recargar.

### Cuarentena en dashboard
Documento con opciones del motor. Click en subcuenta correcta → motor aprende → documento se procesa.

---

## 11. File watcher y modos de operacion

### Modos

```
MANUAL:       python pipeline.py --cliente X --ejercicio 2025
SEMI-AUTO:    Watcher detecta PDF → notifica en dashboard → click "Procesar"
AUTOMATICO:   Watcher detecta PDF → pipeline automatico → cuarentena si confianza <70%
```

### Implementacion
Demonio Python con `watchdog`, vigila `clientes/*/inbox/`.
Configurable por cliente (manual/semi/auto).

---

## 12. Capa de abstraccion backend.py

### Proposito
SFCE nunca habla directamente con FS. Habla con backend.py que traduce.
Si manana se cambia FS por Odoo/Holded/BD propia, solo se toca backend.py.

### Interfaz

```python
class Backend:
    def crear_factura(self, datos) -> dict
    def crear_asiento(self, partidas) -> dict
    def obtener_subcuenta(self, codigo, empresa) -> dict
    def crear_proveedor(self, datos) -> dict
    def crear_cliente(self, datos) -> dict
    def obtener_saldo(self, subcuenta, empresa) -> float
    def sincronizar(self, pendientes) -> list[ResultadoSync]
```

### Doble destino

```python
def crear_factura(self, datos):
    # 1. Guardar en BD local (siempre, instantaneo)
    factura = self.db.insertar_factura(datos)
    # 2. Enviar a FS (intentar, puede fallar)
    try:
        resultado_fs = self.fs_api.crear_factura(datos)
        factura.idfactura_fs = resultado_fs["idfactura"]
    except Exception:
        factura.pendiente_sync = True
    return factura
```

---

## 13. Proteccion del producto (despliegue a clientes)

### Capas de proteccion

| Capa | Mecanismo |
|------|-----------|
| Codigo compilado | Nuitka → binario, sin codigo fuente |
| OCR via proxy | Llamadas OCR pasan por servidor del gestor. Sin proxy = sin OCR |
| Token por cliente | Cada instalacion tiene token unico, desactivable |
| Dashboard login | Credenciales gestionadas por el gestor |

### Modelos de despliegue

```
Opcion A: Local en PC del cliente
  Docker compose (SFCE + FS + BD + Dashboard)
  Cliente paga sus API keys OCR

Opcion B: Servidor del gestor (SaaS)
  Multi-tenant en servidor propio
  Gestor paga APIs, cobra al cliente
```

---

## 14. Conciliacion bancaria (futuro)

### Vision
Cliente sube extracto bancario (CSV/OFX). SFCE cruza movimientos con facturas registradas.

### Formatos prioritarios
- CSV generico (fecha, concepto, importe)
- Norma 43 (formato bancario espanol estandar)
- OFX/QIF (estandar internacional)

### Flujo
```
1. Importar extracto bancario
2. Para cada movimiento, buscar factura coincidente:
   - Por importe exacto
   - Por fecha aproximada (+/- 5 dias)
   - Por concepto (fuzzy match)
3. Coincidencias automaticas (confianza >90%) → conciliar
4. Dudosas → mostrar en dashboard para decision humana
5. Sin coincidencia → crear apunte pendiente de identificar
```

No se implementa en la primera fase. Se disena la BD para soportarlo (tabla `movimientos_bancarios`).

---

## 15. Asientos por regimen especial

### Profesional con IRPF en emitidas (factura 1000€ + IVA 21% - retencion 15%)

```
430 Cliente           1.065,00 DEBE
477 IVA repercutido     210,00 HABER
4751 HP acreedora ret.  150,00 HABER
705 Prestacion serv.  1.000,00 HABER  (o subcuenta segun actividad)
```

### Recargo de equivalencia (compra 1000€ + IVA 21% + RE 5.2%)

```
600 Compras          1.000,00 DEBE
472 IVA soportado      210,00 DEBE
472 Recargo equiv.      52,00 DEBE
400 Proveedor        1.262,00 HABER
```

### Criterio de caja — al facturar (IVA NO se devenga)

```
430 Cliente          1.210,00 DEBE
477* IVA pte cobro     210,00 HABER   (cuenta transitoria)
700 Ventas           1.000,00 HABER
```

### Criterio de caja — al cobrar (IVA se devenga)

```
477* IVA pte cobro     210,00 DEBE
477 IVA repercutido    210,00 HABER
```

### Estimacion objetiva (modulos) — solo registra facturas recibidas

```
# Factura proveedor normal (para IVA soportado deducible)
600 Compras          1.000,00 DEBE
472 IVA soportado      210,00 DEBE
400 Proveedor        1.210,00 HABER
# NO genera libro diario completo. Solo registra para modelo 303 simplificado + 131
```

### Comunidad de propietarios — cuota mensual

```
440 Propietarios       500,00 DEBE
751 Cuotas ordinarias  500,00 HABER
# Sin IVA, sin IS
```

### REBU — bienes usados (venta coche comprado a 8000, vendido a 10000)

```
# IVA solo sobre margen (10000-8000=2000)
430 Cliente         10.000,00 DEBE
477 IVA margen         420,00 HABER   (21% de 2000)
700 Ventas           9.580,00 HABER
```

### ISP domestica (subcontratista construccion)

```
# Similar a intracomunitario: autorepercusion
600 Subcontrata      1.000,00 DEBE
472 IVA soportado      210,00 DEBE
477 IVA repercutido    210,00 HABER
410 Acreedor         1.000,00 HABER   (sin IVA en factura)
```

---

## 16. Resumen de componentes nuevos

| Componente | Prioridad | Dependencias |
|-----------|-----------|-------------|
| Reorganizar estructura sfce/ | P0 | Ninguna |
| perfil_fiscal.py | P0 | Ninguna |
| normativa/ (YAMLs + vigente.py) | P0 | Ninguna |
| motor_reglas.py | P1 | perfil_fiscal + normativa |
| clasificador.py | P1 | motor_reglas |
| backend.py (abstraccion) | P1 | Ninguna |
| db/ (modelos + repositorio) | P2 | backend.py |
| Refactorizar registration.py | P2 | motor_reglas + backend |
| Refactorizar correction.py | P2 | motor_reglas |
| importador.py | P2 | db + clasificador |
| exportador.py | P2 | db |
| api/ (FastAPI) | P3 | db |
| dashboard/ (React) | P3 | api |
| watcher.py | P3 | pipeline |
| licencia.py | P4 | Ninguna |
| Conciliacion bancaria | P4 | db + importador |

**P0** = fundamento, sin esto nada funciona
**P1** = motor central, el cerebro
**P2** = integracion con existente + datos
**P3** = interfaz de usuario
**P4** = features de producto
