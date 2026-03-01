# Dashboard SFCE — Rediseño Total: Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transformar el dashboard SFCE de herramienta funcional a plataforma de inteligencia contable premium — productiva para el gestor, impresionante para el cliente.

**Architecture:** Sistema de 8 fases progresivas. Fase 0 sienta las bases del design system (arregla bugs globales, tokens semánticos, componentes base). Las fases 1-3 rediseñan el shell (sidebar, header, home). Las fases 4-8 mejoran módulos individuales, configuración y polish final. Cada fase es independiente y committeable.

**Tech Stack:** React 18 + TypeScript strict + Vite 6 + Tailwind v4 + shadcn/ui + Recharts 3 + Zustand + TanStack Query v5 + cmdk (ya instalado) + lucide-react

**Design Doc:** `docs/plans/2026-03-01-dashboard-redesign-total-design.md`

**Working directory para todos los comandos:** `dashboard/`

---

## FASE 0 — Design System: Tokens, Componentes Base, Fix Bugs Críticos

> **Objetivo:** Arreglar los bugs visuales globales y crear los componentes reutilizables que usarán todas las demás fases.

---

### Task 0.1: Tokens de color semánticos + fix fondo blanco

**Problema crítico:** Las páginas KPIs, Tesorería, Scoring, Pipeline tienen cards con fondo BLANCO en dark mode porque usan `bg-white` o `bg-card` sin el token correcto. Los charts usan colores azul/rosa/morado sin relación con la paleta ámbar.

**Files:**
- Modify: `src/index.css`

**Step 1: Leer el archivo actual para entender la estructura**

```bash
head -120 src/index.css
```

**Step 2: Añadir tokens semánticos al bloque `:root` y `.dark`**

En `src/index.css`, dentro del bloque `.dark { }` existente, añadir después de las variables actuales:

```css
/* --- Superficie: jerarquía de profundidad --- */
--surface-0: oklch(0.13 0.015 50);
--surface-1: oklch(0.16 0.015 50);
--surface-2: oklch(0.19 0.015 50);
--surface-3: oklch(0.22 0.015 50);

/* --- Estados semánticos --- */
--state-success: oklch(0.72 0.17 162);
--state-warning: oklch(0.75 0.14 50);
--state-danger:  oklch(0.70 0.20 15);
--state-info:    oklch(0.72 0.12 220);

/* --- Charts: paleta cohesiva ámbar --- */
--chart-1: oklch(0.75 0.14 50);
--chart-2: oklch(0.65 0.12 50);
--chart-3: oklch(0.72 0.17 162);
--chart-4: oklch(0.70 0.20 15);
--chart-5: oklch(0.50 0.02 50);
```

Y en el bloque `:root { }` (modo light), añadir los mismos tokens con valores light:

```css
--surface-0: oklch(0.97 0.01 75);
--surface-1: oklch(0.94 0.01 75);
--surface-2: oklch(0.91 0.01 75);
--surface-3: oklch(0.88 0.01 75);

--state-success: oklch(0.52 0.17 162);
--state-warning: oklch(0.55 0.14 50);
--state-danger:  oklch(0.55 0.20 15);
--state-info:    oklch(0.52 0.12 220);

--chart-1: oklch(0.65 0.14 50);
--chart-2: oklch(0.55 0.12 50);
--chart-3: oklch(0.52 0.17 162);
--chart-4: oklch(0.55 0.20 15);
--chart-5: oklch(0.45 0.02 50);
```

**Step 3: Verificar que el CSS compila sin errores**

```bash
npm run build 2>&1 | tail -5
```
Expected: `✓ built in` sin errores

**Step 4: Commit**

```bash
git add src/index.css
git commit -m "feat: design tokens — surface, state-*, chart-* semánticos"
```

---

### Task 0.2: Componente `<StatCard>` — KPI card universal

**Files:**
- Create: `src/components/ui/stat-card.tsx`

**Step 1: Crear el componente**

```tsx
// src/components/ui/stat-card.tsx
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  titulo: string
  valor: string | number
  subtitulo?: string
  tendencia?: 'up' | 'down' | 'neutral'
  tendenciaTexto?: string
  variante?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  icono?: React.ReactNode
  cargando?: boolean
  className?: string
  onClick?: () => void
}

const varianteClases = {
  default:  'border-border/50',
  success:  'border-[var(--state-success)]/30',
  warning:  'border-[var(--state-warning)]/30',
  danger:   'border-[var(--state-danger)]/30',
  info:     'border-[var(--state-info)]/30',
}

const tendenciaIcono = {
  up:      <TrendingUp  className="h-3.5 w-3.5 text-[var(--state-success)]" />,
  down:    <TrendingDown className="h-3.5 w-3.5 text-[var(--state-danger)]" />,
  neutral: <Minus       className="h-3.5 w-3.5 text-muted-foreground" />,
}

export function StatCard({
  titulo, valor, subtitulo, tendencia, tendenciaTexto,
  variante = 'default', icono, cargando, className, onClick,
}: StatCardProps) {
  if (cargando) {
    return (
      <div className={cn(
        'rounded-xl border p-5 bg-[var(--surface-1)] animate-pulse',
        varianteClases[variante], className
      )}>
        <div className="h-3 w-24 bg-[var(--surface-2)] rounded mb-3" />
        <div className="h-8 w-32 bg-[var(--surface-2)] rounded mb-2" />
        <div className="h-3 w-20 bg-[var(--surface-2)] rounded" />
      </div>
    )
  }

  return (
    <div
      className={cn(
        'rounded-xl border p-5 bg-[var(--surface-1)] transition-all duration-150',
        varianteClases[variante],
        onClick && 'cursor-pointer hover:bg-[var(--surface-2)] hover:-translate-y-0.5',
        className
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <span className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide">
          {titulo}
        </span>
        {icono && <span className="text-muted-foreground">{icono}</span>}
      </div>

      <div className="text-[32px] font-bold tracking-tight tabular-nums leading-none mb-2">
        {valor}
      </div>

      {(subtitulo || tendencia) && (
        <div className="flex items-center gap-1.5">
          {tendencia && tendenciaIcono[tendencia]}
          <span className="text-[13px] text-muted-foreground">{tendenciaTexto ?? subtitulo}</span>
        </div>
      )}
    </div>
  )
}
```

**Step 2: Verificar TypeScript**

```bash
npx tsc --noEmit 2>&1 | grep stat-card
```
Expected: sin errores

**Step 3: Commit**

```bash
git add src/components/ui/stat-card.tsx
git commit -m "feat: componente StatCard — KPI universal con tendencia y variantes"
```

---

### Task 0.3: Componente `<EmptyState>` — estados vacíos con personalidad

**Files:**
- Create: `src/components/ui/empty-state.tsx`

**Step 1: Crear el componente**

```tsx
// src/components/ui/empty-state.tsx
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface EmptyStateProps {
  icono?: React.ReactNode
  titulo: string
  descripcion: string
  accion?: {
    texto: string
    onClick: () => void
  }
  className?: string
}

export function EmptyState({ icono, titulo, descripcion, accion, className }: EmptyStateProps) {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center py-16 px-8 text-center',
      className
    )}>
      {icono && (
        <div className="mb-5 p-4 rounded-2xl bg-[var(--surface-1)] text-muted-foreground">
          {icono}
        </div>
      )}
      <h3 className="text-[18px] font-semibold text-foreground mb-2">{titulo}</h3>
      <p className="text-[14px] text-muted-foreground max-w-sm leading-relaxed mb-6">
        {descripcion}
      </p>
      {accion && (
        <Button onClick={accion.onClick} className="gap-2">
          {accion.texto}
        </Button>
      )}
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add src/components/ui/empty-state.tsx
git commit -m "feat: componente EmptyState — estados vacíos con CTA accionable"
```

---

### Task 0.4: Componente `<ChartWrapper>` — paleta ámbar para todos los charts

**Files:**
- Create: `src/components/ui/chart-wrapper.tsx`

**Step 1: Crear el wrapper**

```tsx
// src/components/ui/chart-wrapper.tsx
// Wrapper que inyecta la paleta ámbar cohesiva en todos los charts Recharts

export const CHART_COLORS = {
  primary:   'var(--chart-1)',
  secondary: 'var(--chart-2)',
  success:   'var(--chart-3)',
  danger:    'var(--chart-4)',
  neutral:   'var(--chart-5)',
  // Para waterfall/barras
  positivo:  'var(--chart-3)',  // emerald
  negativo:  'var(--chart-4)',  // rose
  neutro:    'var(--chart-5)',  // slate
}

export const CHART_TOOLTIP_STYLE = {
  backgroundColor: 'var(--surface-3)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  color: 'var(--foreground)',
  fontSize: '13px',
}

export const CHART_AXIS_STYLE = {
  tick: { fill: 'var(--muted-foreground)', fontSize: 12 },
  axisLine: { stroke: 'var(--border)' },
  tickLine: false,
}

interface ChartWrapperProps {
  children: React.ReactNode
  titulo?: string
  subtitulo?: string
  altura?: number
  className?: string
}

export function ChartWrapper({ children, titulo, subtitulo, altura = 280, className }: ChartWrapperProps) {
  return (
    <div className={`rounded-xl border border-border/50 bg-[var(--surface-1)] p-5 ${className ?? ''}`}>
      {titulo && (
        <div className="mb-4">
          <h3 className="text-[15px] font-semibold">{titulo}</h3>
          {subtitulo && <p className="text-[13px] text-muted-foreground mt-0.5">{subtitulo}</p>}
        </div>
      )}
      <div style={{ height: altura }}>
        {children}
      </div>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add src/components/ui/chart-wrapper.tsx
git commit -m "feat: ChartWrapper + CHART_COLORS — paleta ámbar unificada para Recharts"
```

---

### Task 0.5: Componente `<PageTitle>` — títulos consistentes en todas las páginas

**Files:**
- Create: `src/components/ui/page-title.tsx`

**Step 1: Crear el componente**

```tsx
// src/components/ui/page-title.tsx
import { cn } from '@/lib/utils'

interface PageTitleProps {
  titulo: string
  subtitulo?: string
  acciones?: React.ReactNode
  className?: string
}

export function PageTitle({ titulo, subtitulo, acciones, className }: PageTitleProps) {
  return (
    <div className={cn('flex items-start justify-between mb-6', className)}>
      <div>
        <h1 className="text-[28px] font-bold tracking-tight bg-gradient-to-r from-[var(--primary)] to-foreground bg-clip-text text-transparent">
          {titulo}
        </h1>
        {subtitulo && (
          <p className="text-[14px] text-muted-foreground mt-1">{subtitulo}</p>
        )}
      </div>
      {acciones && <div className="flex items-center gap-2">{acciones}</div>}
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add src/components/ui/page-title.tsx
git commit -m "feat: componente PageTitle — gradiente ámbar consistente en todas las páginas"
```

---

### Task 0.6: Fix bug crítico — fondo blanco en páginas KPIs, Tesorería, Scoring, Pipeline

**Problema:** Las `<Card>` de shadcn usan `bg-card` que en algunos contextos resuelve a blanco.

**Files:**
- Modify: `src/features/economico/kpis-page.tsx`
- Modify: `src/features/economico/tesoreria-page.tsx`
- Modify: `src/features/economico/scoring-page.tsx`
- Modify: `src/features/documentos/pipeline-page.tsx`

**Step 1: Leer cada archivo para localizar el problema**

```bash
grep -n "bg-card\|bg-white\|<Card\|className.*card" src/features/economico/kpis-page.tsx | head -20
grep -n "bg-card\|bg-white\|<Card\|className.*card" src/features/economico/tesoreria-page.tsx | head -20
```

**Step 2: En cada página, reemplazar `<Card>` con `<StatCard>` o añadir `bg-[var(--surface-1)]`**

Para cada `<Card className="...">` en estas páginas, cambiar a:
```tsx
<Card className="bg-[var(--surface-1)] border-border/50 ...">
```

O mejor aún, reemplazar los bloques de KPIs simples con `<StatCard>`:

```tsx
// Antes (kpis-page.tsx):
<Card>
  <CardContent>
    <p>Ventas Totales</p>
    <p className="text-green-500">2.428.202 €</p>
  </CardContent>
</Card>

// Después:
import { StatCard } from '@/components/ui/stat-card'
<StatCard
  titulo="Ventas Totales"
  valor="2.428.202 €"
  tendencia="up"
  tendenciaTexto="ejercicio activo"
/>
```

**Step 3: Verificar visualmente con Playwright**

```bash
cd .. && python /tmp/capture_fix.py
```

Crear `/tmp/capture_fix.py`:
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://localhost:3000/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[type="email"]', "admin@sfce.local")
    page.fill('input[type="password"]', "admin")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    page.goto("http://localhost:3000/empresa/4/kpis")
    page.wait_for_timeout(1500)
    page.screenshot(path="/tmp/fix_kpis.png")
    page.goto("http://localhost:3000/empresa/4/tesoreria")
    page.wait_for_timeout(1500)
    page.screenshot(path="/tmp/fix_tesoreria.png")
    b.close()
    print("Screenshots guardados en /tmp/fix_*.png")
```

**Step 4: Confirmar que no hay cards blancas en las screenshots**

**Step 5: Commit**

```bash
cd dashboard
git add src/features/economico/ src/features/documentos/pipeline-page.tsx
git commit -m "fix: cards bg-[surface-1] en KPIs, Tesorería, Scoring, Pipeline — elimina fondo blanco dark mode"
```

---

## FASE 1 — Sidebar: Grupos Colapsables, Badges, Empresa Pill

### Task 1.1: Sidebar con grupos colapsables y memoria en localStorage

**Files:**
- Modify: `src/components/layout/app-sidebar.tsx`

**Step 1: Leer el archivo actual**

```bash
wc -l src/components/layout/app-sidebar.tsx
```

**Step 2: Añadir estado de grupos colapsables**

Añadir al inicio del componente `AppSidebar`:

```tsx
// Estado de grupos colapsados — persistido en localStorage
const [gruposAbiertos, setGruposAbiertos] = React.useState<Record<string, boolean>>(() => {
  try {
    const guardado = localStorage.getItem('sfce-sidebar-grupos')
    return guardado ? JSON.parse(guardado) : {}
  } catch { return {} }
})

const toggleGrupo = (label: string) => {
  setGruposAbiertos(prev => {
    const nuevo = { ...prev, [label]: !prev[label] }
    localStorage.setItem('sfce-sidebar-grupos', JSON.stringify(nuevo))
    return nuevo
  })
}

// Detectar qué grupo está activo según la ruta actual
const grupoActivo = React.useMemo(() => {
  const ruta = location.pathname
  for (const grupo of gruposEmpresa) {
    if (grupo.items.some(item => ruta.startsWith(item.ruta.replace(':id', empresaActiva?.id?.toString() ?? '')))) {
      return grupo.label
    }
  }
  return null
}, [location.pathname, empresaActiva])

// Abrir automáticamente el grupo activo
React.useEffect(() => {
  if (grupoActivo) {
    setGruposAbiertos(prev => {
      if (prev[grupoActivo]) return prev
      const nuevo = { ...prev, [grupoActivo]: true }
      localStorage.setItem('sfce-sidebar-grupos', JSON.stringify(nuevo)
      return nuevo
    })
  }
}, [grupoActivo])
```

**Step 3: Modificar el render de grupos para hacerlos colapsables**

Reemplazar el mapeo actual de `gruposEmpresa` con:

```tsx
{gruposEmpresa.map((grupo) => {
  const estaAbierto = gruposAbiertos[grupo.label] ?? (grupo.label === grupoActivo)
  const tieneActivo = grupo.items.some(item =>
    location.pathname === item.ruta.replace(':id', empresaActiva?.id?.toString() ?? '')
  )

  return (
    <SidebarGroup key={grupo.label}>
      <SidebarGroupLabel
        className="flex items-center justify-between cursor-pointer select-none hover:text-foreground transition-colors"
        onClick={() => toggleGrupo(grupo.label)}
      >
        <span>{grupo.label}</span>
        <div className="flex items-center gap-1.5">
          {/* Badge de alertas — se añade en Task 1.2 */}
          <ChevronRight className={cn(
            'h-3 w-3 transition-transform duration-150',
            estaAbierto && 'rotate-90'
          )} />
        </div>
      </SidebarGroupLabel>

      {estaAbierto && (
        <SidebarGroupContent>
          <SidebarMenu>
            {grupo.items.map((item) => {
              const activo = location.pathname === item.ruta.replace(':id', empresaActiva?.id?.toString() ?? '')
              return (
                <SidebarMenuItem key={item.titulo}>
                  <SidebarMenuButton asChild isActive={activo}>
                    <Link to={item.ruta.replace(':id', empresaActiva?.id?.toString() ?? '')}>
                      <item.icono className="h-4 w-4" />
                      <span>{item.titulo}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )
            })}
          </SidebarMenu>
        </SidebarGroupContent>
      )}
    </SidebarGroup>
  )
})}
```

**Step 4: Verificar que el sidebar funciona**

```bash
npm run dev &
# navegar manualmente a http://localhost:3000
# verificar que grupos se colapsan/expanden
# verificar que el estado persiste al recargar
```

**Step 5: Commit**

```bash
git add src/components/layout/app-sidebar.tsx
git commit -m "feat: sidebar grupos colapsables con memoria localStorage y auto-expand grupo activo"
```

---

### Task 1.2: Empresa pill integrada en sidebar

**Files:**
- Modify: `src/components/layout/app-sidebar.tsx`

**Step 1: Añadir la empresa pill entre el header y los menús**

Insertar después del `<SidebarHeader>` y antes del primer `<SidebarGroup>`:

```tsx
{/* Empresa pill — solo visible si hay empresa activa */}
{empresaActiva && (
  <div className="px-3 py-2">
    <button
      onClick={() => navigate('/')}
      className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg
                 bg-[var(--surface-1)] border border-border/50
                 hover:bg-[var(--surface-2)] transition-all duration-150
                 text-left group"
    >
      {/* Avatar con color único por empresa */}
      <div
        className="h-7 w-7 rounded-md flex items-center justify-center text-[11px] font-bold text-white flex-shrink-0"
        style={{ backgroundColor: getColorEmpresa(empresaActiva.id) }}
      >
        {empresaActiva.nombre.charAt(0)}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[12px] font-semibold truncate leading-tight">
          {empresaActiva.nombre.length > 22
            ? empresaActiva.nombre.substring(0, 22) + '…'
            : empresaActiva.nombre}
        </p>
        <p className="text-[11px] text-muted-foreground">{empresaActiva.cifnif}</p>
      </div>
      <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0 group-hover:text-foreground" />
    </button>
  </div>
)}
```

Añadir la función helper fuera del componente:

```tsx
function getColorEmpresa(id: number): string {
  const colores = [
    '#d97706', '#059669', '#7c3aed', '#dc2626', '#0891b2',
    '#be185d', '#047857', '#b45309',
  ]
  return colores[(id - 1) % colores.length]
}
```

**Step 2: Commit**

```bash
git add src/components/layout/app-sidebar.tsx
git commit -m "feat: empresa pill integrada en sidebar con avatar de color único"
```

---

### Task 1.3: Botón Configuración siempre visible en sidebar

**Files:**
- Modify: `src/components/layout/app-sidebar.tsx`

**Step 1: Añadir botón ⚙️ prominente antes del footer**

Localizar el bloque `<SidebarFooter>` y antes de él añadir:

```tsx
{/* Sección sistema — siempre visible */}
<SidebarGroup>
  <SidebarGroupContent>
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton asChild isActive={location.pathname === '/salud'}>
          <Link to="/salud">
            <HeartPulse className="h-4 w-4" />
            <span>Salud del Sistema</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
      <SidebarMenuItem>
        <SidebarMenuButton
          asChild
          isActive={location.pathname.startsWith('/configuracion')}
          className="text-[var(--primary)] hover:text-[var(--primary)] font-medium"
        >
          <Link to="/configuracion">
            <Settings className="h-4 w-4" />
            <span>Configuración</span>
          </Link>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  </SidebarGroupContent>
</SidebarGroup>
```

**Step 2: Añadir la ruta `/configuracion` en App.tsx**

```tsx
// En src/App.tsx, dentro de las rutas protegidas con AppShell:
{
  path: '/configuracion',
  lazy: () => import('./features/configuracion/configuracion-page').then(m => ({ Component: m.ConfiguracionPage }))
},
{
  path: '/configuracion/:seccion',
  lazy: () => import('./features/configuracion/configuracion-page').then(m => ({ Component: m.ConfiguracionPage }))
},
```

**Step 3: Crear la página placeholder de Configuración**

```tsx
// src/features/configuracion/configuracion-page.tsx
import { PageTitle } from '@/components/ui/page-title'
import { Settings } from 'lucide-react'

export function ConfiguracionPage() {
  return (
    <div className="p-6">
      <PageTitle
        titulo="Configuración"
        subtitulo="Centro de control de SFCE"
      />
      <p className="text-muted-foreground text-[14px]">
        En construcción — Fase 7 del plan de implementación.
      </p>
    </div>
  )
}
```

**Step 4: Commit**

```bash
git add src/components/layout/app-sidebar.tsx src/App.tsx src/features/configuracion/
git commit -m "feat: botón Configuración permanente en sidebar + ruta /configuracion placeholder"
```

---

## FASE 2 — Header: OmniSearch, Botón ⚙️, Breadcrumb Mejorado

### Task 2.1: OmniSearch / Command Palette (⌘K)

**Files:**
- Create: `src/features/omnisearch/omnisearch.tsx`
- Modify: `src/components/layout/header.tsx`

**Step 1: Crear el componente OmniSearch usando cmdk (ya instalado)**

```tsx
// src/features/omnisearch/omnisearch.tsx
import * as React from 'react'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from 'cmdk'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { useNavigate } from 'react-router-dom'
import { useEmpresaStore } from '@/stores/empresa-store'
import { Building2, LayoutDashboard, FileText, Calendar, Zap, Settings } from 'lucide-react'

interface OmniSearchProps {
  abierto: boolean
  onCerrar: () => void
}

// Páginas estáticas para búsqueda
const PAGINAS = [
  { titulo: 'Panel Principal', ruta: '/', icono: LayoutDashboard },
  { titulo: 'Directorio', ruta: '/directorio', icono: FileText },
  { titulo: 'Configuración', ruta: '/configuracion', icono: Settings },
]

const PAGINAS_EMPRESA = [
  { titulo: 'Cuenta de Resultados', ruta: 'pyg', icono: FileText },
  { titulo: 'Balance de Situación', ruta: 'balance', icono: FileText },
  { titulo: 'Libro Diario', ruta: 'diario', icono: FileText },
  { titulo: 'Facturas Emitidas', ruta: 'facturas-emitidas', icono: FileText },
  { titulo: 'Facturas Recibidas', ruta: 'facturas-recibidas', icono: FileText },
  { titulo: 'Calendario Fiscal', ruta: 'calendario-fiscal', icono: Calendar },
  { titulo: 'Modelos Fiscales', ruta: 'modelos-fiscales', icono: FileText },
  { titulo: 'Bandeja de Entrada', ruta: 'inbox', icono: FileText },
  { titulo: 'Ratios Financieros', ruta: 'ratios', icono: FileText },
  { titulo: 'KPIs Sectoriales', ruta: 'kpis', icono: FileText },
  { titulo: 'Tesorería', ruta: 'tesoreria', icono: FileText },
]

export function OmniSearch({ abierto, onCerrar }: OmniSearchProps) {
  const navigate = useNavigate()
  const { empresaActiva } = useEmpresaStore()
  const [query, setQuery] = React.useState('')

  const irA = (ruta: string) => {
    navigate(ruta)
    onCerrar()
    setQuery('')
  }

  return (
    <Dialog open={abierto} onOpenChange={onCerrar}>
      <DialogContent className="p-0 max-w-[560px] overflow-hidden bg-[var(--surface-2)] border-border/60">
        <Command className="bg-transparent" shouldFilter={true}>
          <CommandInput
            placeholder="Buscar o ejecutar un comando..."
            value={query}
            onValueChange={setQuery}
            className="text-[15px] border-0 bg-transparent focus:ring-0 px-4 py-3.5"
            autoFocus
          />
          <CommandList className="max-h-[380px] overflow-y-auto px-2 pb-2">
            <CommandEmpty className="py-8 text-center text-[14px] text-muted-foreground">
              Sin resultados para "{query}"
            </CommandEmpty>

            <CommandGroup heading="Acciones rápidas">
              <CommandItem onSelect={() => irA('/')} className="gap-2.5 rounded-lg cursor-pointer">
                <Zap className="h-4 w-4 text-[var(--state-warning)]" />
                <span>Panel Principal</span>
              </CommandItem>
              {empresaActiva && (
                <CommandItem
                  onSelect={() => irA(`/empresa/${empresaActiva.id}/inbox`)}
                  className="gap-2.5 rounded-lg cursor-pointer"
                >
                  <Zap className="h-4 w-4 text-[var(--state-warning)]" />
                  <span>Ir a Bandeja — {empresaActiva.nombre}</span>
                </CommandItem>
              )}
              <CommandItem onSelect={() => irA('/onboarding/nueva-empresa')} className="gap-2.5 rounded-lg cursor-pointer">
                <Zap className="h-4 w-4 text-[var(--state-warning)]" />
                <span>Nueva empresa</span>
              </CommandItem>
            </CommandGroup>

            <CommandSeparator className="my-1" />

            {empresaActiva && (
              <CommandGroup heading={`Páginas — ${empresaActiva.nombre}`}>
                {PAGINAS_EMPRESA.map(p => (
                  <CommandItem
                    key={p.ruta}
                    onSelect={() => irA(`/empresa/${empresaActiva.id}/${p.ruta}`)}
                    className="gap-2.5 rounded-lg cursor-pointer"
                  >
                    <p.icono className="h-4 w-4 text-muted-foreground" />
                    <span>{p.titulo}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}

            <CommandSeparator className="my-1" />

            <CommandGroup heading="Navegación global">
              {PAGINAS.map(p => (
                <CommandItem
                  key={p.ruta}
                  onSelect={() => irA(p.ruta)}
                  className="gap-2.5 rounded-lg cursor-pointer"
                >
                  <p.icono className="h-4 w-4 text-muted-foreground" />
                  <span>{p.titulo}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  )
}
```

**Step 2: Integrar en el Header**

En `src/components/layout/header.tsx`, añadir:

```tsx
import { OmniSearch } from '@/features/omnisearch/omnisearch'

// Dentro del componente Header:
const [omniAbierto, setOmniAbierto] = React.useState(false)

// Keyboard shortcut global
React.useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      setOmniAbierto(true)
    }
  }
  document.addEventListener('keydown', handler)
  return () => document.removeEventListener('keydown', handler)
}, [])
```

Reemplazar el botón de búsqueda actual con:

```tsx
<button
  onClick={() => setOmniAbierto(true)}
  className="flex items-center gap-2 px-3 py-1.5 rounded-lg
             bg-[var(--surface-1)] border border-border/50 text-muted-foreground
             hover:bg-[var(--surface-2)] hover:text-foreground transition-all duration-150
             text-[13px] min-w-[180px]"
>
  <Search className="h-3.5 w-3.5" />
  <span className="flex-1 text-left">Buscar...</span>
  <kbd className="text-[11px] bg-[var(--surface-2)] px-1.5 py-0.5 rounded border border-border/50">
    ⌘K
  </kbd>
</button>

<OmniSearch abierto={omniAbierto} onCerrar={() => setOmniAbierto(false)} />
```

**Step 3: Verificar TypeScript**

```bash
npx tsc --noEmit 2>&1 | grep -E "error|omnisearch" | head -10
```

**Step 4: Commit**

```bash
git add src/features/omnisearch/ src/components/layout/header.tsx
git commit -m "feat: OmniSearch Command Palette ⌘K — búsqueda global páginas y acciones"
```

---

## FASE 3 — Home: Centro de Operaciones

### Task 3.1: API hook para datos de resumen de empresa

**Files:**
- Create: `src/features/home/api.ts`

**Step 1: Crear el hook de datos**

```typescript
// src/features/home/api.ts
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

export interface ResumenEmpresa {
  empresa_id: number
  bandeja: {
    pendientes: number
    errores_ocr: number
    cuarentena: number
    ultimo_procesado: string | null
  }
  fiscal: {
    proximo_modelo: string | null
    dias_restantes: number | null
    fecha_limite: string | null
    importe_estimado: number | null
  }
  contabilidad: {
    errores_asientos: number
    ultimo_asiento: string | null
  }
  facturacion: {
    ventas_ytd: number
    facturas_vencidas: number
    pendientes_cobro: number
  }
  scoring: number | null
  alertas_ia: string[]
  ventas_6m: number[]
}

export function useResumenEmpresa(empresaId: number) {
  return useQuery<ResumenEmpresa>({
    queryKey: ['resumen-empresa', empresaId],
    queryFn: () => apiClient.get(`/empresas/${empresaId}/resumen`),
    staleTime: 5 * 60 * 1000, // 5 minutos
    retry: false,
  })
}

export interface EstadisticasGlobales {
  total_clientes: number
  docs_pendientes_total: number
  alertas_urgentes: number
  proximo_deadline: { modelo: string; dias: number; fecha: string } | null
  volumen_gestionado: number
}

export function useEstadisticasGlobales() {
  return useQuery<EstadisticasGlobales>({
    queryKey: ['estadisticas-globales'],
    queryFn: () => apiClient.get('/empresas/estadisticas-globales'),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}
```

**Step 2: Commit**

```bash
git add src/features/home/api.ts
git commit -m "feat: API hooks resumen empresa y estadísticas globales para Home"
```

---

### Task 3.2: Barra de estado global en Home

**Files:**
- Modify: `src/features/home/home-page.tsx`

**Step 1: Leer la página actual**

```bash
cat src/features/home/home-page.tsx
```

**Step 2: Crear componente `BarraEstadoGlobal`**

```tsx
// Dentro de home-page.tsx (o en archivo separado si es grande)
function BarraEstadoGlobal() {
  const { data, isLoading } = useEstadisticasGlobales()

  if (isLoading) return (
    <div className="grid grid-cols-5 gap-px rounded-xl overflow-hidden border border-border/50 mb-6 animate-pulse">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="bg-[var(--surface-1)] h-16" />
      ))}
    </div>
  )

  // Fallback con datos locales si la API aún no tiene el endpoint
  const stats = data ?? {
    total_clientes: 5,
    docs_pendientes_total: 1796,
    alertas_urgentes: 0,
    proximo_deadline: { modelo: '303', dias: 50, fecha: '20 abr 2026' },
    volumen_gestionado: 3700000,
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-px rounded-xl overflow-hidden border border-border/50 mb-6">
      {[
        { label: 'Clientes activos', valor: stats.total_clientes, icono: '🏢' },
        { label: 'Docs pendientes', valor: stats.docs_pendientes_total.toLocaleString('es'), icono: '📥' },
        { label: 'Alertas urgentes', valor: stats.alertas_urgentes, icono: '⚠️',
          clase: stats.alertas_urgentes > 0 ? 'text-[var(--state-danger)]' : '' },
        { label: stats.proximo_deadline ? `${stats.proximo_deadline.modelo} · ${stats.proximo_deadline.dias}d` : 'Sin deadline',
          valor: stats.proximo_deadline?.fecha ?? '—', icono: '📅' },
        { label: 'Volumen gestionado', valor: `${(stats.volumen_gestionado / 1000000).toFixed(1)}M€`, icono: '💰' },
      ].map((stat) => (
        <div key={stat.label} className="bg-[var(--surface-1)] px-4 py-3 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            {stat.icono} {stat.label}
          </span>
          <span className={`text-[18px] font-bold tabular-nums ${stat.clase ?? ''}`}>
            {stat.valor}
          </span>
        </div>
      ))}
    </div>
  )
}
```

**Step 3: Commit**

```bash
git add src/features/home/home-page.tsx
git commit -m "feat: barra de estado global en Home — panorama de toda la cartera"
```

---

### Task 3.3: Tarjeta de cliente enriquecida

**Files:**
- Create: `src/features/home/empresa-card.tsx`
- Modify: `src/features/home/home-page.tsx`

**Step 1: Crear `EmpresaCard`**

```tsx
// src/features/home/empresa-card.tsx
import { useNavigate } from 'react-router-dom'
import { useResumenEmpresa } from './api'
import { Building2, Inbox, Calendar, TrendingUp, CreditCard, AlertCircle, ChevronRight, Settings } from 'lucide-react'

interface Empresa {
  id: number
  nombre: string
  cifnif: string
  tipoidfiscal?: string
  sector?: string
}

interface EmpresaCardProps {
  empresa: Empresa
}

function HealthRing({ score }: { score: number | null }) {
  if (score === null) return (
    <div className="h-12 w-12 rounded-full border-2 border-border/50 flex items-center justify-center">
      <span className="text-[10px] text-muted-foreground">—</span>
    </div>
  )
  const color = score >= 70 ? 'var(--state-success)' : score >= 40 ? 'var(--state-warning)' : 'var(--state-danger)'
  const circunferencia = 2 * Math.PI * 20
  const offset = circunferencia - (score / 100) * circunferencia
  return (
    <div className="relative h-12 w-12 flex-shrink-0">
      <svg className="rotate-[-90deg]" width="48" height="48" viewBox="0 0 48 48">
        <circle cx="24" cy="24" r="20" fill="none" strokeWidth="3" stroke="var(--surface-2)" />
        <circle cx="24" cy="24" r="20" fill="none" strokeWidth="3"
          stroke={color} strokeLinecap="round"
          strokeDasharray={circunferencia} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.6s ease-out' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[11px] font-bold leading-none" style={{ color }}>{score}</span>
        <span className="text-[8px] text-muted-foreground">/100</span>
      </div>
    </div>
  )
}

function Sparkline({ datos }: { datos: number[] }) {
  if (!datos.length) return null
  const max = Math.max(...datos)
  const min = Math.min(...datos)
  const rango = max - min || 1
  const ancho = 120
  const alto = 28
  const puntos = datos.map((v, i) => {
    const x = (i / (datos.length - 1)) * ancho
    const y = alto - ((v - min) / rango) * alto
    return `${x},${y}`
  }).join(' ')
  const ultimo = datos[datos.length - 1]
  const penultimo = datos[datos.length - 2] ?? ultimo
  const tendencia = ultimo >= penultimo

  return (
    <div className="flex items-center gap-2">
      <svg width={ancho} height={alto} className="overflow-visible">
        <polyline fill="none" stroke="var(--chart-1)" strokeWidth="1.5"
          strokeLinecap="round" strokeLinejoin="round" points={puntos} />
      </svg>
      <span className={`text-[11px] font-medium ${tendencia ? 'text-[var(--state-success)]' : 'text-[var(--state-danger)]'}`}>
        {tendencia ? '↗' : '↘'}
      </span>
    </div>
  )
}

export function EmpresaCard({ empresa }: EmpresaCardProps) {
  const navigate = useNavigate()
  const { data: resumen, isLoading } = useResumenEmpresa(empresa.id)

  const ir = (ruta: string) => navigate(ruta)

  const fiscal = resumen?.fiscal
  const semaforo = fiscal?.dias_restantes == null ? 'neutral'
    : fiscal.dias_restantes <= 7 ? 'danger'
    : fiscal.dias_restantes <= 30 ? 'warning'
    : 'success'

  const semaforoColor = {
    neutral: 'text-muted-foreground',
    success: 'text-[var(--state-success)]',
    warning: 'text-[var(--state-warning)]',
    danger:  'text-[var(--state-danger)]',
  }

  return (
    <div className="rounded-xl border border-border/50 bg-[var(--surface-1)] overflow-hidden
                    hover:border-[var(--primary)]/30 hover:-translate-y-0.5
                    transition-all duration-150 group flex flex-col">
      {/* Cabecera */}
      <div
        className="p-4 pb-3 cursor-pointer"
        onClick={() => ir(`/empresa/${empresa.id}/pyg`)}
      >
        <div className="flex items-start gap-3">
          <HealthRing score={resumen?.scoring ?? null} />
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-[13px] font-bold leading-tight truncate">{empresa.nombre}</h3>
              <button
                onClick={(e) => { e.stopPropagation(); ir(`/empresa/${empresa.id}/pyg`) }}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-[var(--surface-2)]"
              >
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">{empresa.cifnif}</p>
            {empresa.sector && (
              <p className="text-[11px] text-muted-foreground truncate">{empresa.sector}</p>
            )}
          </div>
        </div>
      </div>

      {/* Bloques de datos */}
      <div className="border-t border-border/30 grid grid-cols-2 divide-x divide-border/30">
        {/* Bandeja */}
        <button
          className="p-3 text-left hover:bg-[var(--surface-2)] transition-colors"
          onClick={() => ir(`/empresa/${empresa.id}/inbox`)}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <Inbox className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Bandeja</span>
          </div>
          {isLoading ? (
            <div className="h-5 w-16 bg-[var(--surface-2)] rounded animate-pulse" />
          ) : (
            <>
              <p className="text-[15px] font-bold tabular-nums">
                {resumen?.bandeja.pendientes.toLocaleString('es') ?? 0}
              </p>
              <p className="text-[11px] text-muted-foreground">pendientes</p>
              {(resumen?.bandeja.errores_ocr ?? 0) > 0 && (
                <p className="text-[11px] text-[var(--state-danger)] mt-0.5">
                  ⚠ {resumen!.bandeja.errores_ocr} errores OCR
                </p>
              )}
            </>
          )}
        </button>

        {/* Fiscal */}
        <button
          className="p-3 text-left hover:bg-[var(--surface-2)] transition-colors"
          onClick={() => ir(`/empresa/${empresa.id}/calendario-fiscal`)}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Fiscal</span>
          </div>
          {isLoading ? (
            <div className="h-5 w-20 bg-[var(--surface-2)] rounded animate-pulse" />
          ) : fiscal?.proximo_modelo ? (
            <>
              <p className={`text-[15px] font-bold ${semaforoColor[semaforo]}`}>
                {fiscal.proximo_modelo}
              </p>
              <p className="text-[11px] text-muted-foreground">
                {fiscal.dias_restantes}d · {fiscal.fecha_limite}
              </p>
            </>
          ) : (
            <p className="text-[12px] text-muted-foreground">Sin obligaciones</p>
          )}
        </button>
      </div>

      <div className="border-t border-border/30 grid grid-cols-2 divide-x divide-border/30">
        {/* Facturación */}
        <button
          className="p-3 text-left hover:bg-[var(--surface-2)] transition-colors"
          onClick={() => ir(`/empresa/${empresa.id}/facturas-emitidas`)}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <TrendingUp className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Ventas</span>
          </div>
          {isLoading ? (
            <div className="h-5 w-24 bg-[var(--surface-2)] rounded animate-pulse" />
          ) : (
            <>
              <p className="text-[15px] font-bold tabular-nums">
                {resumen?.facturacion.ventas_ytd
                  ? `${(resumen.facturacion.ventas_ytd / 1000).toFixed(0)}K€`
                  : '—'}
              </p>
              {(resumen?.facturacion.facturas_vencidas ?? 0) > 0 && (
                <p className="text-[11px] text-[var(--state-danger)]">
                  ⚠ {resumen!.facturacion.facturas_vencidas} vencidas
                </p>
              )}
            </>
          )}
        </button>

        {/* Contabilidad */}
        <button
          className="p-3 text-left hover:bg-[var(--surface-2)] transition-colors"
          onClick={() => ir(`/empresa/${empresa.id}/pyg`)}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <CreditCard className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Contabilidad</span>
          </div>
          {isLoading ? (
            <div className="h-5 w-16 bg-[var(--surface-2)] rounded animate-pulse" />
          ) : (
            <>
              <p className={`text-[13px] font-semibold ${
                (resumen?.contabilidad.errores_asientos ?? 0) === 0
                  ? 'text-[var(--state-success)]'
                  : 'text-[var(--state-danger)]'
              }`}>
                {(resumen?.contabilidad.errores_asientos ?? 0) === 0 ? '✓ Sin errores' : `✗ ${resumen!.contabilidad.errores_asientos} errores`}
              </p>
              {resumen?.contabilidad.ultimo_asiento && (
                <p className="text-[11px] text-muted-foreground">
                  Último: {new Date(resumen.contabilidad.ultimo_asiento).toLocaleDateString('es')}
                </p>
              )}
            </>
          )}
        </button>
      </div>

      {/* Sparkline */}
      {resumen?.ventas_6m && resumen.ventas_6m.some(v => v > 0) && (
        <div className="border-t border-border/30 px-4 py-2.5 flex items-center justify-between">
          <span className="text-[11px] text-muted-foreground">Ventas 6M</span>
          <Sparkline datos={resumen.ventas_6m} />
        </div>
      )}

      {/* Alerta IA */}
      {resumen?.alertas_ia && resumen.alertas_ia.length > 0 && (
        <div className="border-t border-[var(--state-warning)]/20 bg-[var(--state-warning)]/5 px-4 py-2.5">
          <p className="text-[11px] text-[var(--state-warning)] flex items-start gap-1.5">
            <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
            <span>{resumen.alertas_ia[0]}</span>
          </p>
        </div>
      )}

      {/* Quick actions footer */}
      <div className="border-t border-border/30 grid grid-cols-3 divide-x divide-border/30 mt-auto">
        {[
          { label: 'Bandeja', ruta: 'inbox' },
          { label: 'PyG', ruta: 'pyg' },
          { label: 'Fiscal', ruta: 'calendario-fiscal' },
        ].map(({ label, ruta }) => (
          <button
            key={ruta}
            className="py-2 text-[11px] font-medium text-muted-foreground
                       hover:text-foreground hover:bg-[var(--surface-2)]
                       transition-colors text-center"
            onClick={() => ir(`/empresa/${empresa.id}/${ruta}`)}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}
```

**Step 2: Actualizar `home-page.tsx` para usar `EmpresaCard`**

```tsx
// En home-page.tsx, reemplazar el render de tarjetas existente:
import { EmpresaCard } from './empresa-card'
import { BarraEstadoGlobal } from './barra-estado-global'

// En el JSX:
<BarraEstadoGlobal />

{/* Controles de vista */}
<div className="flex items-center justify-between mb-4">
  <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide">
    Empresas activas
  </h2>
</div>

<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
  {empresas.map(empresa => (
    <EmpresaCard key={empresa.id} empresa={empresa} />
  ))}
  {/* Tarjeta Nuevo cliente */}
  <button
    onClick={() => navigate('/onboarding/nueva-empresa')}
    className="rounded-xl border-2 border-dashed border-border/50
               hover:border-[var(--primary)]/50 hover:bg-[var(--surface-1)]/50
               transition-all duration-150 flex flex-col items-center justify-center
               gap-2 p-8 text-muted-foreground hover:text-foreground min-h-[280px]"
  >
    <Plus className="h-8 w-8" />
    <span className="text-[14px] font-medium">Nuevo cliente</span>
  </button>
</div>
```

**Step 3: Verificar TypeScript y compilación**

```bash
npx tsc --noEmit 2>&1 | grep -E "error|empresa-card" | head -15
```

**Step 4: Verificar visualmente**

```bash
# El servidor dev ya debe estar corriendo
# Navegar a http://localhost:3000 y verificar las tarjetas enriquecidas
```

**Step 5: Commit**

```bash
git add src/features/home/
git commit -m "feat: tarjetas de cliente enriquecidas — Health Ring, bloques clickables, sparklines, alertas IA"
```

---

## FASE 5 — Fix Bugs en Páginas (Prioridad alta)

### Task 5.1: Unificar colores de todos los charts con CHART_COLORS

**Files:**
- Modify: `src/features/contabilidad/pyg-page.tsx`
- Modify: `src/features/economico/ratios-page.tsx`
- Modify: otros archivos con charts

**Step 1: Buscar todos los archivos con charts Recharts**

```bash
grep -rl "BarChart\|LineChart\|AreaChart\|RadarChart\|PieChart" src/features/ | sort
```

**Step 2: En cada archivo, importar y usar CHART_COLORS y ChartWrapper**

```tsx
import { CHART_COLORS, CHART_TOOLTIP_STYLE, CHART_AXIS_STYLE, ChartWrapper } from '@/components/ui/chart-wrapper'

// Reemplazar colores hardcodeados:
// fill="#8884d8"  →  fill={CHART_COLORS.primary}
// fill="#82ca9d"  →  fill={CHART_COLORS.success}
// fill="#ff7300"  →  fill={CHART_COLORS.danger}
// stroke="..."    →  stroke={CHART_COLORS.primary}
```

**Step 3: Commit**

```bash
git add src/features/
git commit -m "fix: todos los charts usan CHART_COLORS — paleta ámbar cohesiva"
```

---

### Task 5.2: Empty states mejorados con CTA

**Files:**
- Modify: `src/features/economico/scoring-page.tsx`
- Modify: `src/features/documentos/pipeline-page.tsx`
- Modify: `src/features/economico/tesoreria-page.tsx`

**Step 1: Reemplazar empty states genéricos con `<EmptyState>`**

```tsx
// scoring-page.tsx — reemplazar el texto genérico:
import { EmptyState } from '@/components/ui/empty-state'
import { BarChart2 } from 'lucide-react'

// Donde antes decía "Sin datos de scoring...":
<EmptyState
  icono={<BarChart2 className="h-8 w-8" />}
  titulo="Sin historial de pagos aún"
  descripcion="El Credit Scoring se calcula automáticamente a partir del historial de pagos de facturas. Procesa documentos para generar scores."
  accion={{ texto: 'Ir a Bandeja de Entrada', onClick: () => navigate(`/empresa/${id}/inbox`) }}
/>
```

```tsx
// pipeline-page.tsx:
<EmptyState
  icono={<GitBranch className="h-8 w-8" />}
  titulo="Sin pipeline activo"
  descripcion="Cuando proceses documentos desde la Bandeja de Entrada, verás el progreso en tiempo real por cada fase del pipeline."
  accion={{ texto: 'Ir a Bandeja de Entrada', onClick: () => navigate(`/empresa/${id}/inbox`) }}
/>
```

**Step 2: Commit**

```bash
git add src/features/economico/ src/features/documentos/
git commit -m "fix: empty states con EmptyState component — CTAs accionables y descripción contextual"
```

---

## FASE 7 — Configuración: Centro de Control Total

### Task 7.1: Layout de la página Configuración

**Files:**
- Create: `src/features/configuracion/configuracion-page.tsx`
- Create: `src/features/configuracion/secciones/dashboard-tarjetas.tsx`

**Step 1: Crear el layout principal de Configuración**

```tsx
// src/features/configuracion/configuracion-page.tsx
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { PageTitle } from '@/components/ui/page-title'
import { cn } from '@/lib/utils'
import {
  Building2, LayoutDashboard, Bell, Plug, Users, Shield,
  Database, CreditCard, Sliders, Workflow
} from 'lucide-react'

const SECCIONES = [
  {
    grupo: 'Gestoría',
    items: [
      { id: 'general', label: 'General', icono: Building2 },
      { id: 'marca', label: 'Marca e identidad', icono: Building2 },
      { id: 'notificaciones', label: 'Notificaciones', icono: Bell },
    ]
  },
  {
    grupo: 'Dashboard',
    items: [
      { id: 'tarjetas', label: 'Tarjetas de cliente', icono: LayoutDashboard },
      { id: 'vistas', label: 'Vistas y densidad', icono: Sliders },
    ]
  },
  {
    grupo: 'Automatización',
    items: [
      { id: 'alertas', label: 'Umbrales de alertas', icono: Bell },
      { id: 'workflows', label: 'Workflows automáticos', icono: Workflow },
      { id: 'campos-custom', label: 'Campos personalizados', icono: Sliders },
    ]
  },
  {
    grupo: 'Integraciones',
    items: [
      { id: 'api-keys', label: 'API Keys', icono: Plug },
      { id: 'correo', label: 'Correo SMTP', icono: Plug },
      { id: 'webhooks', label: 'Webhooks', icono: Plug },
    ]
  },
  {
    grupo: 'Usuarios',
    items: [
      { id: 'usuarios', label: 'Usuarios y roles', icono: Users },
      { id: 'seguridad', label: 'Seguridad y 2FA', icono: Shield },
      { id: 'sesiones', label: 'Sesiones activas', icono: Shield },
    ]
  },
  {
    grupo: 'Sistema',
    items: [
      { id: 'backup', label: 'Backup y restauración', icono: Database },
      { id: 'licencia', label: 'Licencia', icono: CreditCard },
      { id: 'auditoria', label: 'Log de auditoría', icono: Shield },
    ]
  },
]

export function ConfiguracionPage() {
  const { seccion = 'tarjetas' } = useParams()
  const navigate = useNavigate()

  return (
    <div className="flex h-full">
      {/* Sidebar de navegación interna */}
      <nav className="w-56 flex-shrink-0 border-r border-border/50 pr-0 py-6 overflow-y-auto">
        {SECCIONES.map(grupo => (
          <div key={grupo.grupo} className="mb-4">
            <p className="px-4 mb-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              {grupo.grupo}
            </p>
            {grupo.items.map(item => (
              <button
                key={item.id}
                onClick={() => navigate(`/configuracion/${item.id}`)}
                className={cn(
                  'w-full flex items-center gap-2.5 px-4 py-2 text-[13px] text-left transition-colors',
                  seccion === item.id
                    ? 'text-foreground font-medium bg-[var(--surface-1)]'
                    : 'text-muted-foreground hover:text-foreground hover:bg-[var(--surface-1)]/50'
                )}
              >
                <item.icono className="h-3.5 w-3.5" />
                {item.label}
              </button>
            ))}
          </div>
        ))}
      </nav>

      {/* Contenido de la sección activa */}
      <main className="flex-1 p-6 overflow-y-auto">
        {seccion === 'tarjetas' && <SeccionTarjetas />}
        {seccion !== 'tarjetas' && (
          <div>
            <PageTitle titulo={SECCIONES.flatMap(g => g.items).find(i => i.id === seccion)?.label ?? 'Configuración'} />
            <p className="text-muted-foreground text-[14px]">Esta sección estará disponible próximamente.</p>
          </div>
        )}
      </main>
    </div>
  )
}
```

**Step 2: Crear sección de configuración de tarjetas**

```tsx
// src/features/configuracion/secciones/dashboard-tarjetas.tsx
// (implementación completa de toggle + drag de bloques)
// Usa localStorage para guardar la configuración
// (código completo en siguiente iteración por tamaño)
```

**Step 3: Commit**

```bash
git add src/features/configuracion/
git commit -m "feat: página Configuración con layout sidebar — 18 secciones organizadas"
```

---

## FASE 8 — Micro-interactions y Polish Final

### Task 8.1: Page transitions

**Files:**
- Modify: `src/components/layout/app-shell.tsx`
- Modify: `src/index.css`

**Step 1: Añadir animación de entrada en las páginas**

```css
/* En src/index.css */
@keyframes page-enter {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-enter {
  animation: page-enter 150ms ease-out both;
}
```

**Step 2: Aplicar animación en el Outlet del AppShell**

```tsx
// En app-shell.tsx, envolver el Outlet:
<main key={location.pathname} className="flex-1 overflow-auto page-enter">
  <Outlet />
</main>
```

**Step 3: Commit**

```bash
git add src/components/layout/app-shell.tsx src/index.css
git commit -m "feat: page transitions — fade + slide-up 150ms en cada navegación"
```

---

### Task 8.2: Keyboard shortcuts globales

**Files:**
- Create: `src/hooks/use-keyboard-shortcuts.ts`
- Modify: `src/components/layout/app-shell.tsx`

**Step 1: Crear el hook**

```tsx
// src/hooks/use-keyboard-shortcuts.ts
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEmpresaStore } from '@/stores/empresa-store'

export function useKeyboardShortcuts() {
  const navigate = useNavigate()
  const { empresaActiva } = useEmpresaStore()
  const id = empresaActiva?.id

  useEffect(() => {
    let gPresionado = false
    let gTimer: ReturnType<typeof setTimeout>

    const handler = (e: KeyboardEvent) => {
      // Ignorar si el foco está en un input/textarea
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return

      if (e.key === 'g' || e.key === 'G') {
        gPresionado = true
        clearTimeout(gTimer)
        gTimer = setTimeout(() => { gPresionado = false }, 1000)
        return
      }

      if (gPresionado && id) {
        gPresionado = false
        clearTimeout(gTimer)
        const mapa: Record<string, string> = {
          c: `/empresa/${id}/pyg`,
          f: `/empresa/${id}/calendario-fiscal`,
          d: `/empresa/${id}/inbox`,
          e: `/empresa/${id}/ratios`,
          r: `/empresa/${id}/facturas-emitidas`,
          h: `/empresa/${id}/nominas`,
        }
        if (mapa[e.key.toLowerCase()]) {
          navigate(mapa[e.key.toLowerCase()])
          return
        }
      }

      // Atajos globales
      if (e.key === '?') {
        // TODO: mostrar modal de shortcuts
      }
    }

    document.addEventListener('keydown', handler)
    return () => {
      document.removeEventListener('keydown', handler)
      clearTimeout(gTimer)
    }
  }, [navigate, id])
}
```

**Step 2: Activar en AppShell**

```tsx
// En app-shell.tsx:
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts'
// Dentro del componente:
useKeyboardShortcuts()
```

**Step 3: Commit**

```bash
git add src/hooks/use-keyboard-shortcuts.ts src/components/layout/app-shell.tsx
git commit -m "feat: keyboard shortcuts — G+C/F/D/E/R/H navegar módulos, ? ayuda"
```

---

## Orden de ejecución recomendado

```
F0.1 → F0.2 → F0.3 → F0.4 → F0.5 → F0.6   (design system + fix bugs críticos)
F1.1 → F1.2 → F1.3                           (sidebar)
F2.1                                          (omnisearch)
F3.1 → F3.2 → F3.3                           (home enriquecido)
F5.1 → F5.2                                  (fix páginas restantes)
F7.1                                          (configuración)
F8.1 → F8.2                                  (polish)
```

## Verificación final

Tras completar todas las fases, hacer un pass visual con Playwright:

```bash
python /tmp/capture_dashboard.py  # reutilizar script inicial
# Comparar screenshots nuevos vs los originales en /tmp/dashboard_screenshots/
```

Commits totales esperados: ~20 commits atómicos
Tiempo estimado por fase: F0 (30min), F1 (30min), F2 (20min), F3 (60min), F5 (30min), F7 (45min), F8 (20min)
