# Dashboard SFCE — Rediseño Total: Design Doc

**Fecha**: 2026-03-01
**Estado**: Aprobado
**Objetivo**: Transformar el dashboard de una herramienta funcional a una plataforma de inteligencia contable premium — productiva para el gestor, impresionante para el cliente.

---

## Diagnóstico del estado actual

### Bugs críticos
- Cards en KPIs, Tesorería, Scoring, Pipeline tienen **fondo BLANCO en dark mode** (falta `surface-1`)
- Charts usan colores azul/rosa/morado aleatorios **desconectados** de la paleta ámbar
- Libro Diario con texto microscópico, prácticamente ilegible

### Problemas de UX
- Home: tarjetas de empresa con icono genérico e idéntico, cero información de negocio
- Sidebar: todos los grupos expandidos siempre, sin jerarquía ni badges de alertas
- 6+ páginas con áreas vacías enormes y empty states sin guía ni CTAs
- Sin botón de Configuración visible y accesible desde cualquier punto
- Sin vista global del portfolio de clientes (solo vista tarjetas sin datos)
- Sin OmniSearch / Command Palette real (placeholder sin funcionalidad)

---

## Principios guía

1. **Zero empty states** — Si no hay datos, explicar por qué y sugerir el siguiente paso
2. **Every pixel earns its place** — No hay espacio vacío sin propósito
3. **Proactive intelligence** — El sistema dice qué hacer, no solo qué pasó
4. **Keyboard-first** — Todo accesible sin ratón para el gestor power user
5. **Progressive disclosure** — Simple a primera vista, infinitamente profundo si se necesita
6. **Semántica de color consistente** — El color tiene significado, siempre el mismo

---

## 1. Sistema de Diseño Global

### Tokens de color semánticos

```css
/* Sobre la base ámbar existente */
--state-success: oklch(0.72 0.17 162)  /* emerald — OK, pagado, presentado */
--state-warning: oklch(0.75 0.14 50)   /* amber   — pendiente, próximo */
--state-danger:  oklch(0.70 0.20 15)   /* rose    — vencido, error, crítico */
--state-info:    oklch(0.72 0.12 220)  /* sky     — procesando, informativo */

/* Superficie — jerarquía de profundidad */
--surface-0: oklch(0.13 0.015 50)   /* fondo base */
--surface-1: oklch(0.16 0.015 50)   /* cards principales — FIX del bug blanco */
--surface-2: oklch(0.19 0.015 50)   /* cards anidadas, hover filas */
--surface-3: oklch(0.22 0.015 50)   /* tooltips, popovers */

/* Charts — paleta cohesiva ámbar */
--chart-primary:   oklch(0.75 0.14 50)    /* amber-400 */
--chart-secondary: oklch(0.65 0.12 50)    /* amber-600/60 */
--chart-success:   oklch(0.72 0.17 162)   /* emerald-400 */
--chart-danger:    oklch(0.70 0.20 15)    /* rose-400 */
--chart-neutral:   oklch(0.50 0.02 50)    /* slate-400 */
```

### Escala tipográfica

```
display:  48px / 700 / tracking-tight   → números KPI grandes
headline: 32px / 700 / tracking-tight   → títulos de página
title:    24px / 600                    → headers de sección
subtitle: 18px / 500                    → subtítulos
body:     15px / 400                    → contenido
caption:  13px / 400 / muted            → labels, metadatos
micro:    11px / 500 / tracking-wide    → badges, tags
```

### Sistema de motion

```
80ms  ease-out       → micro feedback (hover, click, focus)
150ms ease-out       → transiciones de UI (panel open/close)
300ms ease-in-out    → contadores animados de KPI
600ms ease-out       → charts al montar (draw animation)
150ms ease-out       → page transitions (fade + 4px slide-up)
```

### Componentes base nuevos/mejorados

| Componente | Descripción |
|------------|-------------|
| `<StatCard>` | KPI card con valor, tendencia, sparkline opcional, color semántico |
| `<DataTable>` | Tabla unificada con paginación, filtros pill, hover con glow |
| `<PageTitle>` | Título con gradiente ámbar + subtítulo + acciones — aplicar en TODAS las páginas |
| `<StatusBadge>` | Badge con color semántico consistente (eliminar inline styles) |
| `<ChartWrapper>` | Wrapper que aplica paleta ámbar a todos los Recharts |
| `<EmptyState>` | Ilustración SVG + título + causa + CTA accionable |
| `<SkeletonPage>` | Skeleton que imita el layout exacto de cada página |

---

## 2. Sidebar — Rediseño

### Layout

```
┌────────────────────────────┐
│  S  SFCE                   │
│     Sistema Fiscal         │
├────────────────────────────┤
│ ╔═ CHIRINGUITO SOL ▾ ════╗ │  ← empresa pill: click = cambiar empresa
│ ╚═══════════════════════╝ │     color de avatar único por empresa
├────────────────────────────┤
│  🏠  Panel Principal       │
│  🗂   Directorio           │
├────────────────────────────┤
│  ▾ CONTABILIDAD        ²   │  ← expandido si activo, badge = alertas
│    → Cuenta Resultados     │  ← item activo: glow ámbar + línea izquierda
│      Balance               │
│      Libro Diario          │
│      ...                   │
├────────────────────────────┤
│  ▸ FACTURACIÓN         ¹   │  ← colapsado, badge = 1 alerta
│  ▸ RRHH                    │
│  ▸ FISCAL              ³   │  ← 3 modelos pendientes
│  ▸ DOCUMENTOS          ↻   │  ← spinner = procesando
│  ▸ ECONÓMICO               │
│  ▸ PORTAL CLIENTE          │
├────────────────────────────┤
│  ⚙️  Configuración         │  ← SIEMPRE visible y prominente
│  🩺  Salud del Sistema     │
├────────────────────────────┤
│  [A] Admin · ···           │
└────────────────────────────┘
```

### Comportamiento
- Solo el grupo activo expandido por defecto; estado guardado en `localStorage`
- Badges numéricos visibles incluso con grupos colapsados
- Spinner animado en grupo con operación en curso
- Colapso total a iconos: badges visibles sobre el icono
- Recientes: últimas 3 páginas visitadas (`Alt+1/2/3`)
- Favoritos: pin de páginas frecuentes al inicio del sidebar

---

## 3. Header — Rediseño

```
[≡] Empresa · Sección    [🔍 Buscar o ejecutar... ⌘K]    [🔔²] [⚡IA] [🌙] [⚙️] [AS▾]
```

### OmniSearch / Command Palette (⌘K)

Búsqueda global que encuentra: clientes, facturas, documentos, modelos fiscales, subcuentas, páginas. También ejecuta acciones directas sin navegar.

```
┌──────────────────────────────────────────────────┐
│ 🔍 Buscar o ejecutar...                          │
├──────────────────────────────────────────────────┤
│ ACCIONES RÁPIDAS                                 │
│ ⚡ Procesar bandeja Chiringuito                  │
│ ⚡ Generar modelo 303 T1 2026                    │
│ ⚡ Nueva empresa                                 │
├──────────────────────────────────────────────────┤
│ CLIENTES                                         │
│ 🏢 Chiringuito Sol y Arena S.L.                  │
│ 🏢 Pastorino Costa del Sol S.L.                  │
├──────────────────────────────────────────────────┤
│ PÁGINAS                                          │
│ 📊 Cuenta de Resultados                          │
│ ⚖  Balance de Situación                          │
└──────────────────────────────────────────────────┘
```

---

## 4. Home — Centro de Operaciones

### Barra de estado global (nueva)

```
╔══════════╦═══════════════════╦═══════════════╦════════════════╦═══════════════════╗
║ 5 clientes║ 1.796 pendientes  ║ ⚠️ 3 alertas  ║ 📅 303 · 50d  ║ 💰 3.7M€ gestion.║
╚══════════╩═══════════════════╩═══════════════╩════════════════╩═══════════════════╝
```

Panorama completo de toda la cartera sin entrar en ningún cliente.

### Controles del grid

```
[▦ Tarjetas]  [☰ Lista]  [📅 Timeline]  [▦▦ Matriz]   [Ordenar: Urgencia ▾]   [⊞ Tamaño ▾]
```

### Tarjeta de cliente — estructura completa

```
┌──────────────────────────────────────────────────────────┐
│                                              [···]  [↗]  │
│  ╭──────╮  CHIRINGUITO SOL Y ARENA S.L.  ● ACTIVA        │
│  │  78  │  B29066776 · Hostelería · CNAE 5610             │
│  │ /100 │  S.L. · IVA Régimen General · Trimestral        │
│  ╰──────╯  Ejercicio C424 · Gestor: Carlos C.             │
├──────────────────────────────────────────────────────────┤
│  📥 BANDEJA                📅 PRÓXIMO FISCAL              │
│  1.796 pendientes          🟡 303 T1 — 50 días            │
│  0 errores OCR             20 abr 2026                    │
│  0 cuarentena              ~45.000€ estimado              │
├──────────────────────────────────────────────────────────┤
│  💰 FACTURACIÓN             🏦 TESORERÍA                   │
│  640.747€ ventas YTD        Sin datos bancarios           │
│  0 vencidas · 12 cobro      → Conectar extracto           │
├──────────────────────────────────────────────────────────┤
│  ✅ CONTABILIDAD            👥 RRHH                        │
│  0 errores asientos         3 trabajadores                │
│  Último: 28 feb 2026        Nóminas: al día               │
├──────────────────────────────────────────────────────────┤
│  Ventas 6M  ▅▆▇▅▆████  ↗ +12% vs año anterior            │
├──────────────────────────────────────────────────────────┤
│  ⚡ IA: Liquidez 13x benchmark — posible exceso           │
│         de tesorería no rentabilizado                    │
├──────────────────────────────────────────────────────────┤
│  [📥 Bandeja]  [📅 Fiscal]  [📊 PyG]  [⚙️ Cliente]       │
└──────────────────────────────────────────────────────────┘
```

### Bloques activables/desactivables por cliente (configurables)

| Bloque | Contenido |
|--------|-----------|
| Perfil | Nombre, CIF, forma jurídica, sector, régimen IVA/IRPF, gestor |
| Bandeja | Docs pendientes, errores OCR, cuarentena, último procesado |
| Fiscal | Próxima obligación, días restantes, importe estimado, modelos que presenta |
| Contabilidad | Errores asientos, último asiento, estado cierre |
| Facturación | Ventas YTD, facturas vencidas, pendientes cobro |
| Tesorería | Saldo, próximos vencimientos de pago |
| RRHH | Nº trabajadores, estado nóminas, próxima liquidación SS |
| Scoring | Puntuación salud financiera 0-100 con color semántico |
| Alertas IA | Anomalías detectadas por el motor |
| Sparkline | Mini-gráfico ventas últimos 6 meses |
| Notas gestor | Campo libre editable |
| Campos custom | Campos personalizados definidos en Configuración |

### Ordenación de tarjetas
1. Primero las que tienen alertas rojas (urgentes)
2. Luego alertas ámbar (atención)
3. Luego las verdes (todo OK)
4. Dentro de cada grupo: por volumen de negocio descendente

### 4 vistas del Home

**Tarjetas** — tarjeta rica con todos los bloques activos (default)

**Lista densa** — filas comprimidas con los mismos datos, más clientes visibles simultáneamente

**Timeline** — eje temporal horizontal con deadlines fiscales, documentos esperados y pagos de todos los clientes simultáneamente (tipo Gantt visual)

**Matriz** — tabla clientes × módulos × estado como color de celda. Portfolio overview instantáneo sin navegar.

---

## 5. Mejoras por módulo

| Módulo | Bug/Problema | Solución |
|--------|-------------|----------|
| KPIs Sectoriales | Fondo BLANCO cards | `surface-1` + sparklines + comparativa ejercicio anterior |
| Tesorería | Fondo BLANCO + todo 0 | `surface-1` + gráfico flujo 90d + CTA "Conectar extracto bancario" |
| Ratios Financieros | 2 cards, espacio vacío | 2 columnas + gauge mini charts + interpretación IA bajo cada ratio |
| Credit Scoring | Empty state sin guía | Explicación del modelo + ejemplo visual + tabla con barras de score |
| Pipeline | Todo en 0, tabla plana | Vista **Kanban** por fase: Recibido→OCR→Validación→Registro→Completado |
| Bandeja | Tabla plana sin info | Confianza OCR con barra color + quick actions por fila + batch actions |
| Calendario Fiscal | Tabla plana | Vista **calendario visual** mes/trimestre + semáforo días + click→generar |
| Libro Diario | Texto microscópico | Tamaño legible + filtros rápidos + panel lateral con detalle de asiento |
| Salud Sistema | Header azul-gris, vacío | Amber theme + status cards servicios vivos + uptime chart 30d |
| Todos los charts | Colores azul/rosa/morado random | Paleta `chart-*` unificada: amber/emerald/rose/slate |
| PyG waterfall | Tooltip overlap | Colores semánticos + tooltip corregido |

---

## 6. Configuración — Centro de Control Total

**Ruta**: `/configuracion` — layout propio tipo GitHub/Vercel Settings

### Estructura de navegación interna

```
GESTORÍA
  • General (nombre, CIF, dirección, teléfono)
  • Marca (logo, color primario, firma email)
  • Correo SMTP (configurar envío desde dominio propio)
  • Notificaciones globales

DASHBOARD
  • Tarjetas de cliente (template global + por cliente)
  • Vistas disponibles (habilitar/deshabilitar Timeline/Matriz)
  • Densidad UI (compacto/normal/grande)
  • Ordenación por defecto

ALERTAS Y AUTOMATIZACIÓN
  • Umbrales configurables (días vencimiento, días alerta fiscal)
  • Canales (in-app / email / push web)
  • Frecuencia (tiempo real / diario / semanal)
  • Workflows automáticos

CAMPOS PERSONALIZADOS
  • Definir campos extra para perfiles de empresa
  • Activar en tarjetas de Home

POR EMPRESA
  • Configuración específica de bloques por cliente
  • Campos personalizados propios
  • Obligaciones fiscales no estándar
  • Alertas especiales

INTEGRACIONES
  • FacturaScripts API token
  • API Keys IA (Mistral, OpenAI, Gemini)
  • Correo (IMAP/SMTP)
  • Webhooks salientes

USUARIOS
  • Roles y permisos
  • Invitaciones
  • 2FA obligatorio
  • Sesiones activas
  • Log de auditoría

SISTEMA
  • Backup (programación, destino, retención)
  • Licencia (plan, uso, facturación)
  • Diagnóstico / Salud
```

### Configuración de tarjetas (detalle)

```
┌────────────────────────────────────────────────────────────┐
│ TEMPLATE GLOBAL — Bloques visibles en tarjetas de cliente  │
│                                                            │
│ Arrastra para reordenar. Toggle para activar/desactivar.   │
│                                                            │
│ ☑ Perfil           ☑ Bandeja         ☑ Fiscal             │
│ ☑ Contabilidad     ☑ Facturación     ☐ Tesorería          │
│ ☐ RRHH             ☑ Scoring         ☑ Alertas IA         │
│ ☑ Sparkline        ☐ Notas gestor    ☐ Campos custom      │
│                                                            │
│ POR CLIENTE: [Chiringuito Sol y Arena ▾]                   │
│ ● Heredar template global                                  │
│ ○ Personalizar para este cliente                           │
└────────────────────────────────────────────────────────────┘
```

### Workflows automáticos (ejemplos)

```
SI documento es ilegible (confianza OCR < 40%)
→ Enviar email al cliente solicitando mejor copia

SI vencimiento fiscal en < 15 días
→ Crear recordatorio en calendario + notificación push

SI factura lleva > 60 días sin cobrar
→ Notificar al gestor con resumen de importe y cliente

SI asiento tiene error de validación
→ Badge rojo en sidebar grupo Contabilidad
```

---

## 7. Micro-interactions y Polish

- **Skeleton loaders** que imitan el layout exacto de cada página (no barras genéricas)
- **Page transitions**: fade + 4px slide-up en 150ms al navegar entre páginas
- **Chart animations**: barras/líneas se dibujan al entrar en la vista (600ms ease-out)
- **KPI counters**: números cuentan hacia el valor final al montar (300ms)
- **Empty states con personalidad**: ilustración SVG minimalista + causa + CTA accionable
- **Tooltips `?`**: cada métrica financiera explica qué es y cómo se calcula
- **Batch actions**: selección múltiple en tablas con toolbar flotante de acciones

### Keyboard shortcuts

| Atajo | Acción |
|-------|--------|
| `⌘K` / `Ctrl+K` | OmniSearch / Command Palette |
| `G` + `C` | Ir a Contabilidad |
| `G` + `F` | Ir a Fiscal |
| `G` + `D` | Ir a Documentos |
| `G` + `E` | Ir a Económico |
| `J` / `K` | Navegar entre tarjetas en Home |
| `Enter` | Entrar en empresa seleccionada |
| `Esc` | Cerrar panel/modal activo |
| `?` | Mostrar todos los shortcuts |
| `Alt+1/2/3` | Páginas recientes |

---

## Plan de fases de implementación (alto nivel)

| Fase | Contenido | Impacto |
|------|-----------|---------|
| **F0** | Design system: tokens, `surface-1`, `ChartWrapper`, `StatCard`, `EmptyState` | Arregla bugs visuales globales |
| **F1** | Sidebar rediseño: grupos colapsables, badges, empresa pill, botón config | Navegación profesional |
| **F2** | Header: OmniSearch/⌘K, botón ⚙️ fijo, breadcrumb mejorado | Power user experience |
| **F3** | Home: barra global, tarjetas enriquecidas, bloques modulares, quick actions | WOW factor inmediato |
| **F4** | Vistas alternativas Home: Lista, Timeline, Matriz | Portfolio management real |
| **F5** | Fix bugs páginas: KPIs/Tesorería/Scoring/Salud/Charts | Calidad premium consistente |
| **F6** | Mejoras módulos: Ratios gauges, Pipeline kanban, Calendario visual, Bandeja batch | UX por módulo |
| **F7** | Configuración `/configuracion`: template tarjetas, workflows, alertas | Control total |
| **F8** | Micro-interactions: transitions, skeleton loaders, counter animations, keyboard shortcuts | Polish final |
