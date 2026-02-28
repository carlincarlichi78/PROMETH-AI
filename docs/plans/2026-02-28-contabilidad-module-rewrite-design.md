# Design Doc — Módulo Contabilidad: Reescritura Top de Mercado

**Fecha**: 2026-02-28
**Branch**: `feat/sfce-v2-fase-e`
**Opción elegida**: B — Mejora focalizada alta visibilidad
**Datos reales**: Chiringuito Sol y Arena S.L. (empresa 4), ejercicio C422 (2022-2025), 1461 asientos, 4507 partidas, 1796 facturas

---

## Contexto y motivación

El módulo contabilidad actual es funcional pero genérico. El objetivo es llevarlo a nivel de producto SaaS premium comparable a Fathom Analytics, Spotlight Reporting o Syft — herramientas de FP&A que ningún ERP español ofrece con esta calidad de UX.

Bugs conocidos que se resuelven como prerequisito:
- `_parsear_fecha` no maneja DD-MM-YYYY de FS API → todas las fechas son `2026-02-28`
- `nombre_emisor` null en facturas emitidas (FC)
- Diario limitado a 50 asientos sin paginación en frontend
- Subcuentas mostradas como códigos numéricos sin nombre de cuenta

---

## Sección 1 — Fundamentos: diccionario PGC + rectificación de datos

### 1.1 Módulo `sfce/core/pgc_nombres.py`

Diccionario estático con la estructura completa del PGC 2007 (Real Decreto 1514/2007):

- Los 9 **grupos** con nombre y naturaleza contable
- ~250 **subgrupos y cuentas** más usados
- Función `obtener_nombre(subcuenta: str) -> str` — mapeo por prefijo, de más específico a más genérico
- Función `clasificar(subcuenta: str) -> dict` — devuelve `{nombre, grupo, subgrupo, naturaleza, clasificacion_balance}`

El campo `clasificacion_balance` es crítico para Balance y PyG:
```
"naturaleza": "activo_corriente" | "activo_no_corriente" | "pasivo_corriente" |
              "pasivo_no_corriente" | "patrimonio" | "ingreso" | "gasto"
```

Cuentas bilaterales (ej: 472 HP IVA soportado): la clasificación final la determina el signo del saldo en tiempo real, no solo el prefijo.

Líneas PGC formales para PyG (estructura Real Decreto 1514/2007):
```
L1  · Importe neto cifra negocios     (700-705)
L4  · Aprovisionamientos              (600-607)
     → MARGEN BRUTO
L6  · Gastos de personal              (640-649)
L7  · Otros gastos de explotación     (621-631, 65x)
     → EBITDA
L8  · Amortización del inmovilizado   (681-682)
     → EBIT (Resultado de explotación)
L12 · Ingresos financieros            (760-762)
L13 · Gastos financieros              (660-665)
     → Resultado financiero
     → EBT (Resultado antes impuestos)
L17 · Impuestos sobre beneficios      (630-633)
     → RESULTADO DEL EJERCICIO
```

### 1.2 Fix `_parsear_fecha` en `migrar_fs_a_bd.py`

FS API devuelve fechas en formato `DD-MM-YYYY`. El método actual falla silenciosamente:

```python
# ANTES (falla con "10-01-2022")
return date.fromisoformat(str(fecha_str)[:10])  # → ValueError → date.today()

# DESPUÉS
try:
    return date.fromisoformat(s[:10])
except ValueError:
    return datetime.strptime(s[:10], '%d-%m-%Y').date()
```

### 1.3 Script `scripts/rectificar_fechas_fs.py`

Script one-shot para actualizar los 3.257 registros con fechas incorrectas.

**Estrategia**: 4 páginas × 500 asientos = 1461 en ~4 llamadas API. Construir dict `{idasiento_fs: fecha_real}` y ejecutar `executemany` en SQLite — batch único <1s.

```
Asientos:  4 páginas FS → 1461 registros → UPDATE asientos SET fecha=?
FC:        3 páginas FS → 1200 registros → UPDATE facturas SET fecha_factura=?, nombre_receptor=?
FV:        2 páginas FS → 596  registros → UPDATE facturas SET fecha_factura=?
Total API: ~9 llamadas. Tiempo estimado: <15 segundos.
```

Flags: `--dry-run` (muestra cambios sin aplicar), `--empresa N` (por empresa), verificación final de que no queda ninguna fecha `2026-02-28`.

### 1.4 Fix `nombre_emisor` en endpoint `/facturas`

```python
# contabilidad.py — endpoint /facturas
nombre_emisor = f.nombre_emisor if f.tipo == 'recibida' else f.nombre_receptor
```

---

## Sección 2 — PyG: rediseño completo

### 2.1 Selector de período con comparativa

El selector no trabaja solo con "ejercicio completo". Opciones:
- Ejercicio completo
- Trimestre (T1/T2/T3/T4)
- Mes concreto
- Rango personalizado (date range picker)

Para cualquier período seleccionado, la API calcula automáticamente el período anterior del mismo tamaño y devuelve **dos juegos de datos** (`actual` y `anterior`). Todos los componentes de la página consumen ambos.

### 2.2 Nuevo contrato de datos `/pyg`

```json
{
  "periodo": {"desde": "2022-01-01", "hasta": "2022-12-31"},
  "resumen": {
    "ventas_netas": 2428202.0,
    "margen_bruto": 2259627.0, "margen_bruto_pct": 93.1,
    "ebitda": 1514300.0,       "ebitda_pct": 62.4,
    "ebit": 1474200.0,         "ebit_pct": 60.7,
    "resultado": 1474200.0,    "resultado_pct": 60.7
  },
  "lineas": [
    {
      "id": "L1", "descripcion": "Importe neto de la cifra de negocios",
      "importe": 2428202.0, "pct_ventas": 100.0,
      "tipo": "ingreso",
      "detalle": [{"subcuenta": "7000000000", "nombre": "Ventas de mercaderías", "importe": 2428202.0}]
    },
    {"id": "MB", "descripcion": "MARGEN BRUTO", "importe": 2259627.0, "tipo": "subtotal_positivo"},
    {"id": "EBITDA", "descripcion": "EBITDA", "importe": 1514300.0, "tipo": "subtotal_destacado"},
    {"id": "EBIT", "descripcion": "Resultado de explotación (EBIT)", "importe": 1474200.0, "tipo": "subtotal_destacado"},
    {"id": "RES", "descripcion": "RESULTADO DEL EJERCICIO", "importe": 1474200.0, "tipo": "resultado_final"}
  ],
  "waterfall": [
    {"nombre": "Ventas netas", "valor": 2428202, "offset": 0, "tipo": "inicio"},
    {"nombre": "Aprovisionamientos", "valor": 168575, "offset": 2259627, "tipo": "negativo"},
    {"nombre": "Margen Bruto", "valor": 2259627, "offset": 0, "tipo": "subtotal"},
    {"nombre": "Personal", "valor": 745327, "offset": 1514300, "tipo": "negativo"},
    {"nombre": "EBITDA", "valor": 1514300, "offset": 0, "tipo": "subtotal"},
    {"nombre": "Amortizaciones", "valor": 40100, "offset": 1474200, "tipo": "negativo"},
    {"nombre": "RESULTADO", "valor": 1474200, "offset": 0, "tipo": "final"}
  ],
  "evolucion_mensual": [
    {"mes": "2022-01", "ingresos": 0, "gastos": 0, "resultado": 0}
  ],
  "actual": {...},
  "anterior": {...}
}
```

Los offsets del waterfall se calculan en backend — el frontend solo renderiza, sin lógica de cascada.

### 2.3 KPI cards con sparkline y tendencia

4 cards: Ventas netas | Margen Bruto (%) | EBITDA (%) | Resultado neto (%).

Cada card incluye:
- Valor principal con formato `€`
- Badge de variación vs período anterior: `↑ +12.3%` (verde) o `↓ -8.1%` (rojo)
- Mini `LineChart` sparkline de los últimos 6 meses (Recharts miniaturizado)

### 2.4 4 tabs

**Tab 1 — "Cascada de valor" (Waterfall)**

`ComposedChart` de Recharts con barras apiladas (transparent base + colored bar). Sistema de colores:
- Azul índigo: barras de origen
- Rose-500: descensos (gastos)
- Emerald-500: ascensos
- Slate-600: subtotales intermedios (MB, EBITDA)
- Violet-600: resultado final

Conectores horizontales punteados entre barras. Animación de entrada `ease-out` 400ms, escalonada 80ms entre barras. Click en barra → resalta la fila correspondiente en Tab 2.

**Tab 2 — "Cuenta formal" (Tabla PGC)**

Columnas: Descripción | Actual | Anterior | Δ€ | Δ%

Filas expandibles con chevron. Al expandir, subcuentas con nombre PGC + importe + % sobre la línea padre. Click en subcuenta → panel slide-over con listado de asientos que componen ese importe (fecha, número, concepto, importe). Click en asiento → navega al Diario filtrando por ese número.

Filas de subtotal (MB, EBITDA, EBIT, Resultado) con fondo diferenciado y tipografía semibold.

Lógica de color en Δ%: para líneas de gasto, variación positiva = rojo (gastaste más). Para líneas de ingreso/margen, variación positiva = verde.

Líneas PGC con importe 0 se agrupan al final en sección colapsada "Sin actividad".

**Tab 3 — "Evolución mensual"**

`ComposedChart`: barras agrupadas (verde ingresos, rojo gastos) + línea azul resultado superpuesta.

Dos elementos adicionales:
- **Punto de equilibrio**: línea horizontal punteada en `(personal + amortizaciones) / meses_con_actividad`. Los meses donde ingresos superan esta línea se marcan visualmente en el eje X.
- **Brush selector**: componente `Brush` de Recharts en parte inferior — seleccionar rango de meses hace zoom y sincroniza el selector de período de la cabecera.

Banner de aviso si fechas no rectificadas: "Evolución no disponible — fechas pendientes de rectificación. [Ejecutar rectificación →]".

**Tab 4 — "Composición de costes" (Treemap)**

`Treemap` de Recharts: rectángulos de área proporcional al importe, agrupados por línea PGC. Colores por grupo, intensidad por subcuenta dentro del grupo. Hover: nombre + importe + % total. Click en rectángulo: filtra la tabla inferior a esa categoría.

### 2.5 Card "Top 10 gastos"

Lista horizontal fija. Cada fila: nombre cuenta PGC (no código) + barra de progreso proporcional + importe + % sobre total gastos. Sin interacción requerida — visibilidad inmediata.

### 2.6 Tooltip enriquecido global

Componente `TooltipPyG` personalizado (no el default de Recharts). Muestra: nombre completo PGC, importe actual, importe período anterior, variación €, variación %, % sobre ventas. Fondo con `backdrop-blur-sm`.

---

## Sección 3 — Balance: rediseño completo

### 3.1 Correcciones críticas del backend

**Clasificación correcta de cuentas bilaterales**: la cuenta 472 (HP IVA soportado) es activo si saldo deudor, pasivo si acreedor. El backend clasifica en base al signo del saldo calculado, no solo por prefijo.

**Ejercicio abierto sin cuenta 129**: el resultado (1.474.199€) está en cuentas 6xx/7xx. El backend lo calcula como `sum(7xx haber-debe) - sum(6xx debe-haber)` y lo inyecta en PN como línea "Resultado del ejercicio (estimado)" con flag `ejercicio_abierto: true`.

### 3.2 Nuevo contrato de datos `/balance`

```json
{
  "fecha_corte": "2022-12-31",
  "ejercicio_abierto": true,
  "activo": {
    "total": 2689763.67,
    "no_corriente": {
      "total": -32100.16,
      "lineas": [
        {"id": "ANC_II", "descripcion": "II. Inmovilizado material",
         "importe": -32100.16, "detalle": [...]}
      ]
    },
    "corriente": {
      "total": 2721863.83,
      "lineas": [
        {"id": "AC_III_clientes", "descripcion": "III. Clientes por ventas y prestaciones",
         "importe": 2671022.83, "detalle": [...]},
        {"id": "AC_III_aapp", "descripcion": "III. Administraciones Públicas deudoras",
         "importe": 50841.00, "detalle": [...]}
      ]
    }
  },
  "patrimonio_neto": {
    "total": 939871.93,
    "lineas": [
      {"id": "PN_resultado", "descripcion": "VII. Resultado del ejercicio (estimado)",
       "importe": 1474199.59, "badge": "estimado"}
    ]
  },
  "pasivo": {
    "total": 1749891.74,
    "no_corriente": {"total": 0.0, "lineas": []},
    "corriente": {
      "total": 1749891.74,
      "lineas": [
        {"id": "PC_V_proveedores", "descripcion": "V. Proveedores", "importe": 203975.84},
        {"id": "PC_V_personal", "descripcion": "V. Personal (remuneraciones y SS)", "importe": 1201439.35},
        {"id": "PC_V_fiscal", "descripcion": "V. Administraciones Públicas acreedoras", "importe": 344476.55}
      ]
    }
  },
  "ratios": {
    "fondo_maniobra": 971972.09,
    "liquidez_corriente": 1.56,
    "acid_test": 1.56,
    "endeudamiento": 65.1,
    "autonomia_financiera": 34.9,
    "pmc_dias": 401,
    "pmp_dias": 441,
    "nof": 2467047.0,
    "roe": null,
    "roa": null
  },
  "alertas": [
    {"codigo": "PMC_ALTO", "nivel": "critical",
     "mensaje": "PMC 401 días — anómalo para hostelería (benchmark: <30 días). Revisar contabilización de ventas diarias en caja.",
     "valor_actual": 401, "benchmark": 30},
    {"codigo": "ENDEUDAMIENTO_ALTO", "nivel": "warning",
     "mensaje": "Endeudamiento 65,1% en zona de precaución (límite recomendado: 50%).",
     "valor_actual": 65.1, "benchmark": 50},
    {"codigo": "EJERCICIO_ABIERTO", "nivel": "info",
     "mensaje": "Ejercicio sin asiento de cierre — resultado estimado pendiente de regularización."}
  ],
  "cuadre": {"ok": true, "diferencia": 0.0},
  "actual": {...},
  "anterior": {...}
}
```

### 3.3 Sistema de alertas automáticas

El backend calcula ratios y los contrasta contra benchmarks por sector CNAE (hostelería: 5610). Alertas implementadas:

| Código | Condición | Nivel |
|--------|-----------|-------|
| `PMC_ALTO` | PMC > 60 días | critical |
| `PN_NEGATIVO` | PN < 0 | critical |
| `FM_NEGATIVO` | FM < 0 | critical |
| `ENDEUDAMIENTO_ALTO` | Endeudamiento > 65% | warning |
| `NOF_SUPERA_FM` | NOF > FM | warning |
| `LIQUIDEZ_BAJA` | Liquidez < 1.0 | critical |
| `EJERCICIO_ABIERTO` | sin cuenta 129 | info |

### 3.4 Frontend: layout y componentes

**Banners de alerta** — renderizados antes que cualquier dato, con color por nivel (rojo/amarillo/azul).

**Row de 6 ratios con semáforo** (verde/amarillo/rojo contra benchmarks sectoriales):
```
Fondo Maniobra +971.972€ 🟢  |  Liquidez 1,56 🟢   |  Endeudamiento 65,1% 🟡
PMC 401 días 🔴              |  PMP 441 días 🟡    |  Autonomía 34,9% 🟡
```

**Formato T — dos columnas** en desktop. Columnas dentro de cada tabla: Descripción | Actual | Anterior | Δ€ | Δ%.

Estructura Activo:
```
A) ACTIVO NO CORRIENTE           -32.100€
   ▶ II. Inmovilizado material   -32.100€  [solo amortización — aviso]
B) ACTIVO CORRIENTE           2.721.863€
   ▶ III. Clientes            2.671.022€  [chip rojo PMC alto]
   ▶ III. AAPP deudoras          50.841€
TOTAL ACTIVO                  2.689.763€
```

Estructura PN+Pasivo:
```
A) PATRIMONIO NETO              939.872€
   ▶ Resultado ejercicio (est) 1.474.199€  [badge "estimado"]
C) PASIVO CORRIENTE           1.749.891€
   ▶ V. Proveedores             203.975€
   ▶ V. Personal              1.201.439€  [chip — 68,6% del pasivo]
   ▶ V. AAPP acreedoras         344.476€
TOTAL PN + PASIVO             2.689.763€  ✓ Cuadrado
```

Badge "Cuadrado ✓" en verde si activo = PN+pasivo. Badge rojo con diferencia si no.

Drill-down: click en cualquier línea → slide-over con asientos (mismo patrón que PyG).

### 3.5 Gráfico de estructura y matching de plazos

Dos barras apiladas al 100% lado a lado:
```
ACTIVO                     FINANCIACIÓN
[ANC  1%]                  [PN   35%]
[AC  99%]                  [PNC   0%]
                           [PC   65%]
```
Línea de "regla de oro" conectando ANC con PN+PNC. Badge "Estructura financiera correcta ✓" si ANC ≤ PN+PNC.

### 3.6 Análisis capital circulante (Working Capital)

Tres métricas visuales:
- **Fondo de Maniobra**: barra AC vs PC con resultado FM y semáforo
- **Ciclo de Conversión de Efectivo**: timeline visual PMC vs PMP
- **NOF vs FM**: si NOF > FM → banner amarillo "Necesita financiación adicional de X€"

### 3.7 Radar chart vs benchmark sectorial

`RadarChart` de Recharts con 6 ejes: Liquidez, Endeudamiento, Autonomía, PMC normalizado, PMP normalizado, Solvencia. Dos series: empresa (polígono relleno semitransparente) y benchmark hostelería (línea punteada). El PMC de Chiringuito (401 días) saldrá completamente fuera de escala — alarmante e inmediato.

### 3.8 Diagnóstico financiero automático (rule-based)

Componente que genera 3-5 bullets en lenguaje natural con los valores reales:

```
🟢 FM positivo (+971.972€): la empresa puede cubrir deudas a corto plazo con activo corriente.
🔴 PMC 401 días: anómalo para hostelería (benchmark <30 días). Verificar si ventas diarias
   están contabilizadas en tesorería en lugar de clientes.
🟡 Endeudamiento 65,1%: zona de precaución. El 68,6% del pasivo son obligaciones laborales.
🟡 NOF (2,47M€) supera FM (972k€): necesidad de financiación adicional de ~1,5M€.
ℹ️  Ejercicio abierto: resultado 1.474.199€ estimado, pendiente de asiento de regularización.
```

### 3.9 Estado de Flujos de Efectivo estimado (método indirecto)

Tercer estado financiero principal, derivado de movimientos del balance:

```
ACTIVIDADES DE EXPLOTACIÓN
  + Resultado del ejercicio                    +1.474.199€
  + Amortizaciones (no cash, 68x)                +40.100€
  ± Variación clientes (430)                  -2.671.022€
  ± Variación proveedores (400)                 +203.975€
  ± Variación deuda fiscal (47x)               +344.476€
  ± Variación deuda personal (465+476)        +1.201.439€
  = CASH FLOW OPERATIVO ESTIMADO               +593.167€

ACTIVIDADES DE INVERSIÓN
  ± Variación inmovilizado neto (21x+28x)        -32.100€
  = CASH FLOW INVERSIÓN                          -32.100€

ACTIVIDADES DE FINANCIACIÓN
  ± Deuda financiera (50x/15x)                        0€
  = CASH FLOW FINANCIACIÓN                            0€

VARIACIÓN DE TESORERÍA ESTIMADA                +561.067€
```

Banner "EFE estimado — sin datos bancarios reales. [Ir a Conciliación →]". El componente se renderiza siempre pero con el aviso de limitación si no hay cuenta 570.

---

## Sección 4 — Diario: virtual scroll + Libro Mayor

### 4.1 Cambios en API `/diario`

Nuevos parámetros:
```python
limit: int = 200          # aumentado de 50
offset: int = 0
busqueda: Optional[str]   # full-text en concepto (server-side)
desde: Optional[date]
hasta: Optional[date]
origen: Optional[str]     # FC, FV, NOM, BAN, migrado_fs
subcuenta: Optional[str]  # prefijo para filtrar partidas
```

Nuevo endpoint `GET /diario/total` — devuelve solo `{"total": 1461}` sin cargar partidas. Rápido, para mostrar el conteo en cabecera antes de cargar datos.

Respuesta paginada con envelope:
```json
{"total": 1461, "offset": 0, "limite": 200, "asientos": [...]}
```

### 4.2 Virtual scroll con carga incremental

`@tanstack/virtual` para render de filas. El cliente carga 200 asientos por bloque. Al acercarse al final del bloque cargado (<50 filas del final), dispara fetch del siguiente bloque. El usuario percibe scroll continuo sin cortes.

Total para Chiringuito: 1461 asientos en 8 bloques de 200. Primera carga: 200 asientos = ~150ms. Resto carga en background.

### 4.3 Filtros avanzados

Panel collapsible (oculto por defecto). Filtros:
- **Rango de fechas**: date range picker con accesos rápidos (Este mes, T1, T2, T3, T4, Año)
- **Origen**: chips multiselect (FC, FV, NOM, BAN, IMP, migrado_fs)
- **Subcuenta**: autocompletar — escribe "640" → sugiere "640 · Sueldos y salarios"
- **Rango importe**: mínimo/máximo
- **Búsqueda texto**: full-text en concepto (server-side, API param `busqueda`)

**Barra de resultados activa** cuando hay filtros:
`"Mostrando 149 de 1.461 asientos — Debe: 203.975€ = Haber: 203.975€ ✓"`
Cuadre del subconjunto filtrado en tiempo real.

### 4.4 Tabla enriquecida

Columnas: [expand] | Núm. | Fecha | Concepto | Origen (badge) | Debe | Haber | Cuadre

**Badge de origen**: chip de color por tipo (FC verde, FV naranja, NOM azul, BAN cyan, IMP gris).
**Badge de cuadre**: ✓ verde si debe=haber exacto, ✗ rojo con diferencia si no cuadra.

Al expandir, cada partida muestra:
- `4000000016 · PRIMAFRIO S.L. (Proveedores)` — código + nombre PGC
- Debe / Haber monoespaciado
- Icono link si existe factura relacionada → navega a Facturación
- Saldo acumulado de esa subcuenta hasta este asiento (calculado bajo demanda)

**Agrupación por mes** (toggle): cabeceras `Enero 2022 — 85 asientos — Debe: 180.000€ = Haber: 180.000€`, colapsables. El contador puede colapsar meses ya revisados.

### 4.5 Exportación

Botón "Exportar" en cabecera — exporta la vista filtrada actual:

**CSV contable**: columnas `Asiento|Fecha|Subcuenta|Nombre Cuenta|Concepto|Debe|Haber`. UTF-8 BOM para Excel en Windows.

**Excel profesional**: dos hojas — "Diario" (todas las filas) y "Resumen" (totales por mes y subcuenta). Formato tabla Excel, columnas numéricas como `Number`, fechas como `Date`. Entregable directo a auditor.

### 4.6 Libro Mayor (componente nuevo)

Segundo libro contable obligatorio. Implementado como **slide-over de pantalla completa** que se abre al hacer click en cualquier subcuenta en partidas expandidas, o desde Plan de Cuentas.

**Cabecera**: `4000000016 · PRIMAFRIO S.L. — Saldo actual: -184.427,59€`

**Tabla de movimientos**: Fecha | Nº Asiento | Concepto | Debe | Haber | **Saldo acumulado**. La columna de saldo es running total — muestra cómo evolucionó el saldo de la cuenta desde 0 hasta el valor actual.

**Gráfico de evolución del saldo**: `AreaChart` con el saldo acumulado a lo largo del tiempo. Para clientes (430): curva de crecimiento de deuda. Para proveedores (400): picos de vencimiento. Visualmente revela patrones inmediatamente.

**Estadísticas**: número de movimientos, total debe, total haber, saldo final, saldo promedio del período.

**Botón exportar**: CSV de todos los movimientos de esa cuenta.

---

## Dependencias entre secciones

```
Sección 1.1 (pgc_nombres.py)
    ↓ requerido por
Sección 2 (PyG: nombres cuentas, estructura PGC)
Sección 3 (Balance: clasificación corriente/no corriente)
Sección 4 (Diario: nombres en partidas, Libro Mayor)

Sección 1.2+1.3 (fix fechas + rectificar_fechas_fs.py)
    ↓ requerido por
Sección 2 Tab 3 (evolución mensual — datos sin sentido sin fechas reales)
Sección 3 (selector fecha de corte)
Sección 4 (filtro por mes en Diario)

Sección 3 backend (estructura balance)
    ↓ requerido por
Sección 3 EFE (variaciones de balance)
```

## Archivos afectados

### Backend (Python)
| Archivo | Cambio |
|---------|--------|
| `sfce/core/pgc_nombres.py` | NUEVO — diccionario PGC con jerarquía |
| `sfce/api/rutas/contabilidad.py` | MODIFICA — endpoints pyg, balance, diario, facturas |
| `sfce/api/schemas.py` | MODIFICA — nuevos schemas PyGOut, BalanceOut, etc. |
| `scripts/migrar_fs_a_bd.py` | MODIFICA — fix _parsear_fecha |
| `scripts/rectificar_fechas_fs.py` | NUEVO — script one-shot rectificación |

### Frontend (React/TypeScript)
| Archivo | Cambio |
|---------|--------|
| `dashboard/src/features/contabilidad/pyg-page.tsx` | REESCRITURA completa |
| `dashboard/src/features/contabilidad/balance-page.tsx` | REESCRITURA completa |
| `dashboard/src/features/contabilidad/diario-page.tsx` | REESCRITURA completa |
| `dashboard/src/components/charts/waterfall-chart.tsx` | NUEVO |
| `dashboard/src/components/charts/libro-mayor.tsx` | NUEVO |
| `dashboard/src/components/diagnostico-financiero.tsx` | NUEVO |
| `dashboard/src/components/estado-flujos-efectivo.tsx` | NUEVO |
| `dashboard/src/types/index.ts` | MODIFICA — nuevos tipos |
| `dashboard/src/lib/query-keys.ts` | MODIFICA — nuevas query keys |
| `dashboard/package.json` | MODIFICA — añadir @tanstack/virtual |

## Estimación de esfuerzo

| Sección | Backend | Frontend | Total |
|---------|---------|----------|-------|
| 1 — PGC + datos | 4h | — | 4h |
| 2 — PyG | 3h | 5h | 8h |
| 3 — Balance | 3h | 5h | 8h |
| 4 — Diario + Mayor | 2h | 4h | 6h |
| **Total** | **12h** | **14h** | **~26h** |
