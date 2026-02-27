# Dashboard Rewrite — Plan de Implementacion

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reescribir completamente el dashboard SFCE como producto SaaS con 38 paginas, shadcn/ui, modulo economico-financiero y copiloto IA.

**Architecture:** Feature-based folder structure. React Query para data fetching, Zustand para estado UI (empresa activa, theme, sidebar). shadcn/ui como sistema de componentes. Backend FastAPI existente extendido con endpoints economico-financieros y copilot.

**Tech Stack:** React 18, TypeScript strict, shadcn/ui, Radix UI, Recharts, TanStack Query, Zustand, React Hook Form, Zod, date-fns, Tailwind CSS v4, Lucide React, Vite 6.

**Design doc:** `docs/plans/2026-02-27-dashboard-rewrite-design.md`

---

## Fase 1: Fundacion

### Task 1: Instalar dependencias

**Files:**
- Modify: `dashboard/package.json`

**Step 1: Instalar dependencias de produccion**

Run:
```bash
cd dashboard && npm install @tanstack/react-query @tanstack/react-table zustand react-hook-form @hookform/resolvers zod recharts date-fns lucide-react class-variance-authority clsx tailwind-merge tailwind-animate sonner
```

**Step 2: Instalar shadcn/ui CLI y configurar**

Run:
```bash
cd dashboard && npx shadcn@latest init
```

Responder:
- Style: Default
- Base color: Slate
- CSS variables: Yes
- tailwind.config: usar CSS (Tailwind v4)
- Components path: `src/components/ui`
- Utils path: `src/lib/utils`

**Step 3: Instalar componentes shadcn/ui base**

Run:
```bash
cd dashboard && npx shadcn@latest add button card dialog dropdown-menu input label select separator sheet sidebar breadcrumb badge tabs table tooltip avatar command popover calendar scroll-area skeleton switch textarea alert alert-dialog checkbox radio-group progress toast sonner collapsible navigation-menu toggle-group accordion
```

**Step 4: Verificar build**

Run: `cd dashboard && npx tsc --noEmit && npm run build`
Expected: BUILD OK sin errores

**Step 5: Commit**

```bash
git add dashboard/
git commit -m "feat: instalar shadcn/ui, React Query, Zustand, Recharts y dependencias dashboard"
```

---

### Task 2: Estructura de carpetas y utilidades base

**Files:**
- Create: `dashboard/src/lib/utils.ts` (si shadcn no lo creo)
- Create: `dashboard/src/lib/api-client.ts`
- Create: `dashboard/src/lib/query-keys.ts`
- Create: `dashboard/src/lib/formatters.ts`
- Create: `dashboard/src/stores/ui-store.ts`
- Create: `dashboard/src/stores/auth-store.ts`
- Create: `dashboard/src/types/api.ts`

**Step 1: Crear lib/utils.ts**

```typescript
// dashboard/src/lib/utils.ts
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

**Step 2: Crear lib/formatters.ts**

```typescript
// dashboard/src/lib/formatters.ts
import { format, formatDistanceToNow } from "date-fns"
import { es } from "date-fns/locale"

export function formatMoneda(valor: number): string {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
  }).format(valor)
}

export function formatNumero(valor: number, decimales = 2): string {
  return new Intl.NumberFormat("es-ES", {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(valor)
}

export function formatPorcentaje(valor: number, decimales = 1): string {
  return `${formatNumero(valor, decimales)}%`
}

export function formatFecha(fecha: string | Date, formato = "dd/MM/yyyy"): string {
  return format(new Date(fecha), formato, { locale: es })
}

export function formatFechaRelativa(fecha: string | Date): string {
  return formatDistanceToNow(new Date(fecha), { addSuffix: true, locale: es })
}
```

**Step 3: Crear lib/query-keys.ts**

```typescript
// dashboard/src/lib/query-keys.ts
export const queryKeys = {
  empresas: {
    all: ["empresas"] as const,
    detail: (id: number) => ["empresas", id] as const,
    proveedores: (id: number) => ["empresas", id, "proveedores"] as const,
    trabajadores: (id: number) => ["empresas", id, "trabajadores"] as const,
  },
  contabilidad: {
    pyg: (empresaId: number, params?: Record<string, string>) =>
      ["contabilidad", empresaId, "pyg", params] as const,
    balance: (empresaId: number, params?: Record<string, string>) =>
      ["contabilidad", empresaId, "balance", params] as const,
    diario: (empresaId: number, params?: Record<string, string>) =>
      ["contabilidad", empresaId, "diario", params] as const,
    facturas: (empresaId: number, params?: Record<string, string>) =>
      ["contabilidad", empresaId, "facturas", params] as const,
    activos: (empresaId: number) =>
      ["contabilidad", empresaId, "activos"] as const,
  },
  documentos: {
    all: (empresaId: number) => ["documentos", empresaId] as const,
    cuarentena: (empresaId: number) => ["documentos", empresaId, "cuarentena"] as const,
  },
  directorio: {
    all: ["directorio"] as const,
    detail: (id: number) => ["directorio", id] as const,
  },
  fiscal: {
    modelos: (empresaId: number) => ["fiscal", empresaId, "modelos"] as const,
    calendario: (empresaId: number) => ["fiscal", empresaId, "calendario"] as const,
    historico: (empresaId: number) => ["fiscal", empresaId, "historico"] as const,
  },
  economico: {
    ratios: (empresaId: number, periodo?: string) =>
      ["economico", empresaId, "ratios", periodo] as const,
    kpis: (empresaId: number) => ["economico", empresaId, "kpis"] as const,
    tesoreria: (empresaId: number) => ["economico", empresaId, "tesoreria"] as const,
    cashflow: (empresaId: number) => ["economico", empresaId, "cashflow"] as const,
    presupuesto: (empresaId: number) => ["economico", empresaId, "presupuesto"] as const,
    comparativa: (empresaId: number) => ["economico", empresaId, "comparativa"] as const,
    scoring: (empresaId: number) => ["economico", empresaId, "scoring"] as const,
  },
} as const
```

**Step 4: Crear stores/ui-store.ts (Zustand)**

```typescript
// dashboard/src/stores/ui-store.ts
import { create } from "zustand"
import { persist } from "zustand/middleware"

interface UiState {
  empresaActivaId: number | null
  sidebarColapsado: boolean
  tema: "light" | "dark" | "system"
  densidad: "compacta" | "comoda"
  copilotAbierto: boolean
  setEmpresaActiva: (id: number | null) => void
  toggleSidebar: () => void
  setTema: (tema: "light" | "dark" | "system") => void
  setDensidad: (densidad: "compacta" | "comoda") => void
  toggleCopilot: () => void
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      empresaActivaId: null,
      sidebarColapsado: false,
      tema: "light",
      densidad: "comoda",
      copilotAbierto: false,
      setEmpresaActiva: (id) => set({ empresaActivaId: id }),
      toggleSidebar: () => set((s) => ({ sidebarColapsado: !s.sidebarColapsado })),
      setTema: (tema) => set({ tema }),
      setDensidad: (densidad) => set({ densidad }),
      toggleCopilot: () => set((s) => ({ copilotAbierto: !s.copilotAbierto })),
    }),
    { name: "sfce-ui" }
  )
)
```

**Step 5: Crear stores/auth-store.ts (Zustand reemplaza AuthContext)**

```typescript
// dashboard/src/stores/auth-store.ts
import { create } from "zustand"
import { persist } from "zustand/middleware"

interface Usuario {
  id: number
  email: string
  nombre: string
  rol: "admin" | "gestor" | "readonly" | "cliente"
  empresas_ids: number[]
}

interface AuthState {
  token: string | null
  usuario: Usuario | null
  cargando: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  setUsuario: (usuario: Usuario | null) => void
  setCargando: (cargando: boolean) => void
}

const API_BASE = "/api"

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      usuario: null,
      cargando: true,
      login: async (email, password) => {
        const res = await fetch(`${API_BASE}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        })
        if (!res.ok) throw new Error("Credenciales incorrectas")
        const data = await res.json()
        set({ token: data.access_token })
        // Obtener usuario
        const meRes = await fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${data.access_token}` },
        })
        if (meRes.ok) {
          const usuario = await meRes.json()
          set({ usuario, cargando: false })
        }
      },
      logout: () => set({ token: null, usuario: null }),
      setUsuario: (usuario) => set({ usuario }),
      setCargando: (cargando) => set({ cargando }),
    }),
    {
      name: "sfce-auth",
      partialize: (state) => ({ token: state.token }),
    }
  )
)
```

**Step 6: Crear lib/api-client.ts (reescribir con React Query)**

```typescript
// dashboard/src/lib/api-client.ts
import { useAuthStore } from "@/stores/auth-store"

const API_BASE = "/api"

async function fetchApi<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().token
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...opciones?.headers,
  }

  const res = await fetch(`${API_BASE}${ruta}`, { ...opciones, headers })

  if (res.status === 401) {
    useAuthStore.getState().logout()
    throw new Error("Sesion expirada")
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || "Error del servidor")
  }

  return res.json()
}

export const api = {
  get: <T>(ruta: string, params?: Record<string, string>) => {
    const url = params
      ? `${ruta}?${new URLSearchParams(params)}`
      : ruta
    return fetchApi<T>(url)
  },
  post: <T>(ruta: string, body?: unknown) =>
    fetchApi<T>(ruta, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(ruta: string, body?: unknown) =>
    fetchApi<T>(ruta, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(ruta: string) =>
    fetchApi<T>(ruta, { method: "DELETE" }),
}
```

**Step 7: Crear types/api.ts (tipos compartidos)**

Mover y extender los tipos de `dashboard/src/types/index.ts` a `dashboard/src/types/api.ts`. Mantener los existentes (Usuario, Empresa, PyG, Balance, Partida, Asiento, Factura, ActivoFijo, ProveedorCliente, Trabajador, Documento, Cuarentena, EventoWS) y anadir:

```typescript
// dashboard/src/types/api.ts
// ... tipos existentes migrados + nuevos:

export interface Ratio {
  nombre: string
  valor: number
  categoria: "liquidez" | "solvencia" | "rentabilidad" | "eficiencia" | "estructura"
  tendencia: number[] // ultimos 12 meses
  benchmark_sector?: number
  semaforo: "verde" | "amarillo" | "rojo"
  explicacion: string
}

export interface KPI {
  nombre: string
  valor: number
  unidad: string
  objetivo?: number
  variacion_anterior?: number
  semaforo: "verde" | "amarillo" | "rojo"
}

export interface CashFlow {
  operativo: number
  inversion: number
  financiacion: number
  neto: number
  detalle_operativo: { concepto: string; importe: number }[]
  detalle_inversion: { concepto: string; importe: number }[]
  detalle_financiacion: { concepto: string; importe: number }[]
}

export interface PrediccionTesoreria {
  fecha: string
  saldo_real?: number
  saldo_previsto: number
  cobros_previstos: number
  pagos_previstos: number
}

export interface CentroCoste {
  id: number
  nombre: string
  tipo: "departamento" | "proyecto" | "sucursal"
  total_gastos: number
  presupuesto?: number
}

export interface PresupuestoPartida {
  cuenta: string
  descripcion: string
  presupuestado: number
  real: number
  desviacion: number
  desviacion_pct: number
}

export interface CreditScore {
  entidad_id: number
  nombre: string
  cif: string
  puntuacion: number
  factores: { nombre: string; puntos: number; max: number }[]
  limite_sugerido: number
  historial_pagos: { fecha: string; dias_retraso: number }[]
}

export interface MensajeCopilot {
  id: string
  rol: "usuario" | "asistente"
  contenido: string
  timestamp: string
  charts?: unknown[]
  tablas?: unknown[]
  acciones?: { label: string; ruta: string }[]
  feedback?: "positivo" | "negativo"
}
```

**Step 8: Configurar path aliases en tsconfig**

Modificar `dashboard/tsconfig.json` (o `tsconfig.app.json`):

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

Y en `dashboard/vite.config.ts` anadir:

```typescript
import path from "path"

export default defineConfig({
  // ... plugins existentes
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // ... server existente
})
```

**Step 9: Verificar build**

Run: `cd dashboard && npx tsc --noEmit && npm run build`
Expected: BUILD OK

**Step 10: Commit**

```bash
git add dashboard/
git commit -m "feat: estructura base — stores Zustand, api client, query keys, tipos, formatters"
```

---

### Task 3: Configurar React Query provider y tema

**Files:**
- Modify: `dashboard/src/main.tsx`
- Create: `dashboard/src/lib/theme.ts`
- Modify: `dashboard/src/index.css`

**Step 1: Crear lib/theme.ts (dark mode helper)**

```typescript
// dashboard/src/lib/theme.ts
import { useUiStore } from "@/stores/ui-store"
import { useEffect } from "react"

export function useTheme() {
  const tema = useUiStore((s) => s.tema)

  useEffect(() => {
    const root = document.documentElement
    if (tema === "system") {
      const dark = window.matchMedia("(prefers-color-scheme: dark)").matches
      root.classList.toggle("dark", dark)
    } else {
      root.classList.toggle("dark", tema === "dark")
    }
  }, [tema])
}
```

**Step 2: Reescribir main.tsx con QueryClientProvider**

```typescript
// dashboard/src/main.tsx
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "@/components/ui/sonner"
import App from "./App"
import "./index.css"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 min
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  </StrictMode>
)
```

**Step 3: Actualizar index.css con variables tema shadcn/ui**

Reemplazar el CSS actual con el generado por shadcn + variables dark mode. Mantener Tailwind v4 import.

**Step 4: Verificar build**

Run: `cd dashboard && npm run build`
Expected: BUILD OK

**Step 5: Commit**

```bash
git add dashboard/
git commit -m "feat: React Query provider, sistema temas dark/light, Toaster"
```

---

## Fase 2: Layout Shell

### Task 4: AppShell — Header, Sidebar, Breadcrumbs

**Files:**
- Create: `dashboard/src/components/layout/app-shell.tsx`
- Create: `dashboard/src/components/layout/header.tsx`
- Create: `dashboard/src/components/layout/app-sidebar.tsx`
- Create: `dashboard/src/components/layout/breadcrumbs.tsx`
- Create: `dashboard/src/components/layout/empresa-selector.tsx`
- Create: `dashboard/src/components/layout/user-menu.tsx`
- Delete: `dashboard/src/Layout.tsx` (reemplazado)
- Delete: `dashboard/src/components/Sidebar.tsx` (reemplazado)
- Delete: `dashboard/src/components/EmpresaCard.tsx` (reemplazado)
- Modify: `dashboard/src/App.tsx`

**Step 1: Crear header.tsx**

Header con: logo SFCE, empresa-selector, busqueda global (Cmd+K), notificaciones, user menu.
Usar componentes shadcn: `Button`, `Avatar`, `DropdownMenu`, `Command` (para busqueda).
Iconos: `Search`, `Bell`, `Sparkles` (copilot), `Moon`/`Sun` de Lucide.

**Step 2: Crear app-sidebar.tsx**

Sidebar usando shadcn `Sidebar` component con:
- 10 secciones con separadores (segun design doc seccion 3)
- Iconos Lucide por seccion
- Colapsable (solo iconos en modo mini)
- Highlight de ruta activa via `useLocation()`
- Responsive: oculto en mobile, iconos en tablet, completo en desktop

Secciones y rutas:
```
Panel Principal → /empresa/:id
CONTABILIDAD
  Cuenta Resultados → /empresa/:id/pyg
  Balance Situacion → /empresa/:id/balance
  Libro Diario → /empresa/:id/diario
  Plan de Cuentas → /empresa/:id/plan-cuentas
  Conciliacion Bancaria → /empresa/:id/conciliacion
  Amortizaciones → /empresa/:id/amortizaciones
  Cierre Ejercicio → /empresa/:id/cierre
  Apertura Ejercicio → /empresa/:id/apertura
FACTURACION
  Facturas Emitidas → /empresa/:id/facturas-emitidas
  Facturas Recibidas → /empresa/:id/facturas-recibidas
  Cobros y Pagos → /empresa/:id/cobros-pagos
  Presupuestos → /empresa/:id/presupuestos
  Contratos → /empresa/:id/contratos
RRHH
  Nominas → /empresa/:id/nominas
  Trabajadores → /empresa/:id/trabajadores
FISCAL
  Calendario → /empresa/:id/calendario
  Modelos Fiscales → /empresa/:id/modelos-fiscales
  Generar Modelo → /empresa/:id/modelos-fiscales/generar
  Historico → /empresa/:id/modelos-fiscales/historico
DOCUMENTOS
  Bandeja Entrada → /empresa/:id/inbox
  Pipeline → /empresa/:id/pipeline
  Cuarentena → /empresa/:id/cuarentena
  Archivo Digital → /empresa/:id/archivo
ECONOMICO-FINANCIERO
  Ratios Financieros → /empresa/:id/ratios
  KPIs Sectoriales → /empresa/:id/kpis
  Tesoreria → /empresa/:id/tesoreria
  Centros de Coste → /empresa/:id/centros-coste
  Presupuesto vs Real → /empresa/:id/presupuesto
  Comparativa Interanual → /empresa/:id/comparativa
  Credit Scoring → /empresa/:id/scoring
  Informes PDF → /empresa/:id/informes
PORTAL CLIENTE → /portal
DIRECTORIO → /directorio
CONFIGURACION
  Empresa → /empresa/:id/config
  Usuarios y Roles → /config/usuarios
  Integraciones → /config/integraciones
  Backup → /config/backup
  Licencia → /config/licencia
  Apariencia → /config/apariencia
```

**Step 3: Crear empresa-selector.tsx**

Dropdown con buscador usando shadcn `Popover` + `Command`:
- Lista empresas del usuario (de React Query)
- Busqueda por nombre/CIF
- Al seleccionar: `useUiStore.setEmpresaActiva(id)` + navegar a `/empresa/:id`
- Mostrar empresa actual en el header

**Step 4: Crear user-menu.tsx**

Dropdown con avatar, nombre, rol, separador, opciones:
- Perfil, Tema (light/dark/system), Cerrar sesion

**Step 5: Crear breadcrumbs.tsx**

Breadcrumbs automaticos basados en ruta actual. Parsear `useLocation().pathname` y generar migas.

**Step 6: Crear app-shell.tsx**

Composicion: `SidebarProvider` + `Sidebar` + `main` con Header + Breadcrumbs + `{children}`.

**Step 7: Reescribir App.tsx con nuevo routing**

```typescript
// dashboard/src/App.tsx
import { Routes, Route, Navigate } from "react-router-dom"
import { Suspense, lazy } from "react"
import { AppShell } from "@/components/layout/app-shell"
import { ProtectedRoute } from "@/components/protected-route"
import { useTheme } from "@/lib/theme"

// Lazy load todas las paginas
const Login = lazy(() => import("@/features/auth/pages/login"))
const Home = lazy(() => import("@/features/home/pages/home"))
// ... todas las demas paginas lazy

function App() {
  useTheme()
  return (
    <Suspense fallback={<div>Cargando...</div>}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/" element={<Home />} />
            <Route path="/empresa/:id" element={<EmpresaDashboard />} />
            <Route path="/empresa/:id/pyg" element={<PyG />} />
            {/* ... 36 rutas mas */}
          </Route>
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}
```

**Step 8: Verificar build + verificar visualmente**

Run: `cd dashboard && npm run build`
Verificar con preview_screenshot que el layout se renderiza.

**Step 9: Commit**

```bash
git add dashboard/
git commit -m "feat: layout shell — header, sidebar colapsable, breadcrumbs, empresa selector, dark mode"
```

---

## Fase 3: Componentes Compartidos

### Task 5: DataTable generico

**Files:**
- Create: `dashboard/src/components/data-table/data-table.tsx`
- Create: `dashboard/src/components/data-table/column-header.tsx`
- Create: `dashboard/src/components/data-table/pagination.tsx`
- Create: `dashboard/src/components/data-table/toolbar.tsx`
- Create: `dashboard/src/components/data-table/export-button.tsx`

**Implementacion:**

DataTable generico con TanStack Table:
- Props: `columns: ColumnDef<T>[]`, `data: T[]`, `busqueda?: boolean`, `exportar?: boolean`, `paginacion?: boolean`
- Sorting por columna (click header)
- Filtro global (search input)
- Paginacion (10/25/50/100 por pagina)
- Seleccion de filas con checkbox (opcional)
- Export CSV (descargar como archivo)
- Column visibility toggle
- Loading skeleton cuando `data` es undefined
- Empty state con icono + mensaje

Usar shadcn `Table`, `Input`, `Button`, `Select`, `DropdownMenu`.

**Step 1: Escribir data-table.tsx con TanStack Table**

**Step 2: Escribir column-header.tsx (sort + hide)**

**Step 3: Escribir pagination.tsx**

**Step 4: Escribir toolbar.tsx (busqueda + filtros + export)**

**Step 5: Verificar build**

**Step 6: Commit**

```bash
git commit -m "feat: componente DataTable generico — sort, filter, paginate, export CSV"
```

---

### Task 6: ChartCard, KPICard, FilterBar

**Files:**
- Create: `dashboard/src/components/charts/chart-card.tsx`
- Create: `dashboard/src/components/charts/kpi-card.tsx`
- Create: `dashboard/src/components/charts/sparkline.tsx`
- Create: `dashboard/src/components/filter-bar.tsx`
- Create: `dashboard/src/components/page-header.tsx`
- Create: `dashboard/src/components/loading-skeleton.tsx`
- Create: `dashboard/src/components/empty-state.tsx`
- Create: `dashboard/src/components/periodo-selector.tsx`

**ChartCard:**
- Wrapper con shadcn `Card`: titulo, subtitulo, selector periodo, boton fullscreen
- Slot para chart (children)
- Loading skeleton
- Empty state

**KPICard:**
- shadcn `Card` con: valor grande (formateado), label, variacion vs anterior (flecha + color + %), sparkline opcional, semaforo opcional (dot verde/amarillo/rojo)
- Props: `label`, `valor`, `formato: "moneda"|"porcentaje"|"numero"`, `variacion?`, `tendencia?: number[]`, `semaforo?`

**Sparkline:**
- Mini Recharts `LineChart` sin ejes, solo linea, 60x20px

**FilterBar:**
- Chips de filtros activos (removibles con X)
- Boton "Filtrar" → dropdown con campos
- Boton "Reset"

**PageHeader:**
- Titulo pagina (h1), subtitulo opcional, acciones (botones derecha)

**PeriodoSelector:**
- Toggle: Mes / Trimestre / Ano
- Selector fecha dentro del periodo
- Navegacion anterior/siguiente

**Step 1-6: Implementar cada componente**

**Step 7: Commit**

```bash
git commit -m "feat: componentes compartidos — ChartCard, KPICard, Sparkline, FilterBar, PageHeader"
```

---

## Fase 4: Paginas — Modulo por modulo

> **Patron para cada pagina:**
> 1. Crear archivo en `dashboard/src/features/{modulo}/pages/{pagina}.tsx`
> 2. Crear hooks React Query en `dashboard/src/features/{modulo}/hooks/use-{recurso}.ts`
> 3. Usar componentes compartidos (DataTable, ChartCard, KPICard)
> 4. Conectar a API existente via `api.get()` + `useQuery()`
> 5. Si endpoint no existe → crear en `sfce/api/rutas/`
> 6. Lazy load en App.tsx

### Task 7: Home — Panel Principal

**Files:**
- Create: `dashboard/src/features/home/pages/home.tsx`
- Create: `dashboard/src/features/home/hooks/use-resumen.ts`
- Create: `dashboard/src/features/home/components/actividad-reciente.tsx`
- Create: `dashboard/src/features/home/components/calendario-mini.tsx`

**Implementacion:**

Grid 2x2 de KPICards: ingresos mes, gastos mes, resultado, IVA pendiente.
Area chart: evolucion mensual ingresos vs gastos (Recharts `AreaChart`).
Donut chart: distribucion gastos por categoria (Recharts `PieChart`).
Timeline actividad reciente (ultimos 10 documentos/asientos).
Calendario mini con proximas obligaciones fiscales.
Accesos rapidos (cards con iconos).

Si no hay empresa seleccionada: mostrar grid de empresas (como Home actual).

**API necesaria:** GET `/contabilidad/{id}/resumen` (nuevo endpoint — devolver KPIs basicos).
Si no quieres crear endpoint nuevo, calcular desde PyG + Balance existentes.

**Step 1: Crear hook use-resumen.ts**

```typescript
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api-client"
import { queryKeys } from "@/lib/query-keys"

export function useResumenEmpresa(empresaId: number) {
  return useQuery({
    queryKey: queryKeys.contabilidad.pyg(empresaId),
    queryFn: () => api.get(`/contabilidad/${empresaId}/pyg`),
    enabled: !!empresaId,
  })
}
```

**Step 2: Crear home.tsx con grid KPIs + charts**

**Step 3: Crear actividad-reciente.tsx**

**Step 4: Verificar con preview_screenshot**

**Step 5: Commit**

```bash
git commit -m "feat: pagina Home — KPIs, evolucion ingresos/gastos, actividad reciente"
```

---

### Task 8: Contabilidad — 8 paginas

**Files:**
- Create: `dashboard/src/features/contabilidad/pages/pyg.tsx`
- Create: `dashboard/src/features/contabilidad/pages/balance.tsx`
- Create: `dashboard/src/features/contabilidad/pages/diario.tsx`
- Create: `dashboard/src/features/contabilidad/pages/plan-cuentas.tsx`
- Create: `dashboard/src/features/contabilidad/pages/conciliacion.tsx`
- Create: `dashboard/src/features/contabilidad/pages/amortizaciones.tsx`
- Create: `dashboard/src/features/contabilidad/pages/cierre.tsx`
- Create: `dashboard/src/features/contabilidad/pages/apertura.tsx`
- Create: `dashboard/src/features/contabilidad/hooks/use-contabilidad.ts`
- Create: `dashboard/src/features/contabilidad/components/partida-tree.tsx`

**PyG** — Tabla jerarquica expandible (grupo 6xx gastos, 7xx ingresos), sparklines, comparativa periodo anterior. Usa datos de API `/contabilidad/{id}/pyg`.

**Balance** — Activo vs Pasivo+PN, drill-down subcuenta, stacked bar chart composicion. Usa `/contabilidad/{id}/balance`.

**Diario** — DataTable con asientos, detalle expandible con partidas, filtros fecha/cuenta/concepto. Usa `/contabilidad/{id}/diario`.

**Plan Cuentas** — Arbol jerarquico interactivo (componente tree con shadcn `Collapsible`). API nueva: GET `/contabilidad/{id}/plan-cuentas` (agrupar subcuentas por cuenta padre).

**Conciliacion** — Vista dual (split view): movimientos banco izquierda, asientos derecha. Matching visual. API nueva: GET `/contabilidad/{id}/conciliacion`.

**Amortizaciones** — DataTable activos con `Progress` bar % amortizado. Cuadro amortizacion expandible. API: reusar `/contabilidad/{id}/activos`.

**Cierre** — Wizard 5 pasos con shadcn `Tabs` o stepper custom. Checklist con iconos estado. Preview asientos. API existente parcial.

**Apertura** — Card estado + boton generar. Simple.

**Step 1-8: Implementar cada pagina siguiendo el patron**

Priorizar PyG, Balance, Diario (ya tienen API). Plan Cuentas, Conciliacion necesitan endpoints nuevos.

**Step 9: Commit por pagina o grupo**

```bash
git commit -m "feat: contabilidad — PyG, Balance, Diario con charts y comparativa"
git commit -m "feat: contabilidad — Plan Cuentas, Conciliacion, Amortizaciones, Cierre, Apertura"
```

---

### Task 9: Facturacion — 5 paginas

**Files:**
- Create: `dashboard/src/features/facturacion/pages/emitidas.tsx`
- Create: `dashboard/src/features/facturacion/pages/recibidas.tsx`
- Create: `dashboard/src/features/facturacion/pages/cobros-pagos.tsx`
- Create: `dashboard/src/features/facturacion/pages/presupuestos.tsx`
- Create: `dashboard/src/features/facturacion/pages/contratos.tsx`
- Create: `dashboard/src/features/facturacion/hooks/use-facturas.ts`

**Emitidas/Recibidas** — DataTable con badge estado (cobrada verde, pendiente amarillo, vencida rojo). Detalle inline expandible. Acciones (marcar pagada, PDF). Usa `/contabilidad/{id}/facturas` filtrado por tipo.

**Cobros y Pagos** — Aging analysis (4 buckets: 0-30, 30-60, 60-90, 90+). Waterfall chart. Prevision. API nueva: GET `/contabilidad/{id}/cobros-pagos`.

**Presupuestos** — CRUD presupuestos. Convertir a factura. Tablas nuevas BD necesarias.

**Contratos** — CRUD contratos recurrentes. Tabla nueva BD necesaria.

> Nota: Presupuestos y Contratos requieren tablas BD nuevas. Implementar primero las paginas con datos existentes (Emitidas, Recibidas, Cobros/Pagos) y dejar Presupuestos/Contratos como placeholder con "Proximamente".

**Commits:**
```bash
git commit -m "feat: facturacion — emitidas, recibidas con aging analysis y cobros/pagos"
```

---

### Task 10: Fiscal — 4 paginas

**Files:**
- Create: `dashboard/src/features/fiscal/pages/calendario.tsx`
- Create: `dashboard/src/features/fiscal/pages/modelos.tsx`
- Create: `dashboard/src/features/fiscal/pages/generar-modelo.tsx`
- Create: `dashboard/src/features/fiscal/pages/historico.tsx`
- Create: `dashboard/src/features/fiscal/hooks/use-fiscal.ts`

Reescribir las 4 paginas existentes (Calendario, ModelosFiscales, GenerarModelo, HistoricoModelos) con shadcn/ui. APIs ya existen en `sfce/api/rutas/modelos.py`.

**Calendario** — Vista calendario con cards por mes. Color semaforo por estado.

**Modelos** — Grid de cards por modelo (303, 111, 130, 390, etc).

**Generar** — Selector modelo + periodo, preview casillas, boton generar.

**Historico** — DataTable con todos los modelos generados, descargar PDF/BOE.

```bash
git commit -m "feat: fiscal — calendario, modelos, generacion, historico con shadcn/ui"
```

---

### Task 11: RRHH — 2 paginas

**Files:**
- Create: `dashboard/src/features/rrhh/pages/nominas.tsx`
- Create: `dashboard/src/features/rrhh/pages/trabajadores.tsx`
- Create: `dashboard/src/features/rrhh/hooks/use-rrhh.ts`

**Nominas** — DataTable mensual. Desglose bruto/SS/IRPF/neto. Chart comparativa mensual.

**Trabajadores** — DataTable + detalle expandible. Costes acumulados.

API existente: GET `/empresas/{id}/trabajadores`.

```bash
git commit -m "feat: rrhh — nominas y trabajadores con desglose costes"
```

---

### Task 12: Documentos — 4 paginas

**Files:**
- Create: `dashboard/src/features/documentos/pages/inbox.tsx`
- Create: `dashboard/src/features/documentos/pages/pipeline.tsx`
- Create: `dashboard/src/features/documentos/pages/cuarentena.tsx`
- Create: `dashboard/src/features/documentos/pages/archivo.tsx`
- Create: `dashboard/src/features/documentos/hooks/use-documentos.ts`
- Create: `dashboard/src/features/documentos/components/pdf-viewer.tsx`

**Inbox** — Grid de cards con preview PDF (iframe o embed). Drag & drop upload. Badge tipo detectado. APIs existentes.

**Pipeline** — Fases con progress bars. WebSocket para tiempo real. Log por documento.

**Cuarentena** — Cards con pregunta + formulario inline (React Hook Form). Resolver → POST existente.

**Archivo** — DataTable con busqueda full-text. Preview PDF. Filtros avanzados. API nueva: GET `/documentos/{id}/archivo`.

```bash
git commit -m "feat: documentos — inbox, pipeline tiempo real, cuarentena, archivo digital"
```

---

### Task 13: Economico-Financiero — 8 paginas + API Backend

> Este es el modulo mas complejo. Requiere endpoints nuevos en el backend.

**Files Backend:**
- Create: `sfce/api/rutas/economico.py`
- Create: `sfce/core/ratios.py`
- Create: `sfce/core/kpis.py`
- Create: `sfce/core/tesoreria.py`
- Create: `sfce/core/scoring.py`
- Modify: `sfce/api/app.py` (registrar router economico)
- Modify: `sfce/api/schemas.py` (anadir schemas economicos)

**Files Frontend:**
- Create: `dashboard/src/features/economico/pages/ratios.tsx`
- Create: `dashboard/src/features/economico/pages/kpis.tsx`
- Create: `dashboard/src/features/economico/pages/tesoreria.tsx`
- Create: `dashboard/src/features/economico/pages/centros-coste.tsx`
- Create: `dashboard/src/features/economico/pages/presupuesto.tsx`
- Create: `dashboard/src/features/economico/pages/comparativa.tsx`
- Create: `dashboard/src/features/economico/pages/scoring.tsx`
- Create: `dashboard/src/features/economico/pages/informes.tsx`
- Create: `dashboard/src/features/economico/hooks/use-economico.ts`

#### Sub-Task 13a: Backend — Motor de ratios financieros

**sfce/core/ratios.py:**

```python
def calcular_ratios(sesion, empresa_id: int, ejercicio: str) -> list[dict]:
    """Calcula 30+ ratios desde Asiento/Partida."""
    # Obtener saldos por subcuenta
    # Calcular cada ratio por categoria:
    # - Liquidez: activo_corriente/pasivo_corriente, acid_test, etc
    # - Solvencia: deuda_total/activo_total, etc
    # - Rentabilidad: resultado/fondos_propios (ROE), resultado/activo (ROA), etc
    # - Eficiencia: ventas/activo, PMC, PMP, etc
    # - Estructura: inmovilizado/activo, etc
```

Los ratios se calculan en tiempo real desde las tablas existentes:
- **Activo corriente**: sum(debe-haber) subcuentas 3xx+4xx+5xx
- **Activo no corriente**: sum(debe-haber) subcuentas 2xx
- **Pasivo corriente**: sum(haber-debe) subcuentas 4xx (acreedores) + 5xx (deudas cp)
- **Pasivo no corriente**: sum(haber-debe) subcuentas 1xx
- **Patrimonio neto**: sum(haber-debe) subcuentas 1xx (capital+reservas)
- **Ventas**: sum(haber) subcuentas 7xx
- **Resultado**: ventas - gastos (sum subcuentas 6xx)

**sfce/api/rutas/economico.py:**

```python
router = APIRouter(prefix="/economico", tags=["economico"])

@router.get("/{empresa_id}/ratios")
def obtener_ratios(empresa_id: int, ejercicio: str = None):
    ...

@router.get("/{empresa_id}/kpis")
def obtener_kpis(empresa_id: int):
    ...

@router.get("/{empresa_id}/tesoreria")
def obtener_tesoreria(empresa_id: int, horizonte: int = 90):
    ...

@router.get("/{empresa_id}/cashflow")
def obtener_cashflow(empresa_id: int, ejercicio: str = None):
    ...

@router.get("/{empresa_id}/scoring")
def obtener_scoring(empresa_id: int):
    ...

@router.get("/{empresa_id}/comparativa")
def obtener_comparativa(empresa_id: int, ejercicios: str = None):
    ...

@router.get("/{empresa_id}/presupuesto")
def obtener_presupuesto(empresa_id: int, ejercicio: str = None):
    ...
```

#### Sub-Task 13b: Frontend — Paginas economico-financieras

**Ratios** — 5 tabs (liquidez/solvencia/rentabilidad/eficiencia/estructura). Cada ratio como card con valor, sparkline 12 meses, semaforo, explicacion. Barra horizontal comparativa vs sector.

**KPIs** — Auto-deteccion sector. Grid de KPICards especificas. Para hosteleria: food cost, ticket medio, RevPASH, comensales.

**Tesoreria** — Area chart saldo historico + zona prevision. Tabla movimientos diarios. Alertas saldo minimo.

**Centros Coste** — CRUD centros + asignacion gastos. PyG por centro. Bar chart comparativa.

**Presupuesto vs Real** — Tabla partidas con semaforo desviacion. Line chart acumulado. Requiere tabla BD `presupuestos`.

**Comparativa** — Selector ejercicios (multi). Tabla concepto x ejercicio. Bar chart agrupado. CAGR.

**Scoring** — DataTable proveedores/clientes con puntuacion 0-100. Desglose factores. Limite credito.

**Informes** — Selector plantilla + secciones a incluir. Boton generar PDF. Historial descargas.

```bash
git commit -m "feat: backend motor ratios financieros + endpoints economicos"
git commit -m "feat: economico-financiero — ratios, KPIs, tesoreria, scoring, comparativa, informes"
```

---

### Task 14: Directorio + Portal + Configuracion

**Files:**
- Create: `dashboard/src/features/directorio/pages/directorio.tsx`
- Create: `dashboard/src/features/portal/pages/portal.tsx`
- Create: `dashboard/src/features/configuracion/pages/empresa-config.tsx`
- Create: `dashboard/src/features/configuracion/pages/usuarios.tsx`
- Create: `dashboard/src/features/configuracion/pages/integraciones.tsx`
- Create: `dashboard/src/features/configuracion/pages/backup.tsx`
- Create: `dashboard/src/features/configuracion/pages/licencia.tsx`
- Create: `dashboard/src/features/configuracion/pages/apariencia.tsx`

**Directorio** — Reescribir pagina existente con DataTable + detalle dialog. CRUD. APIs existentes.

**Portal** — Vista reducida para rol "cliente". Solo sus facturas, PyG simplificado, calendario, upload docs.

**Config paginas** — Formularios con React Hook Form + Zod. Empresa: datos fiscales, logo upload. Usuarios: DataTable + dialog CRUD. Apariencia: toggles tema/densidad/idioma.

```bash
git commit -m "feat: directorio, portal cliente, configuracion — 8 paginas"
```

---

### Task 15: Login + Auth rewrite

**Files:**
- Create: `dashboard/src/features/auth/pages/login.tsx`
- Create: `dashboard/src/components/protected-route.tsx`
- Delete: `dashboard/src/pages/Login.tsx`
- Delete: `dashboard/src/context/AuthContext.tsx` (reemplazado por Zustand)
- Delete: `dashboard/src/hooks/useApi.ts` (reemplazado por api-client)
- Delete: `dashboard/src/components/ProtectedRoute.tsx`

**Login** — Pagina centrada con card, logo SFCE, campos email/password, boton entrar. Fondo con gradient sutil. Usa `useAuthStore.login()`.

**ProtectedRoute** — Verifica `useAuthStore.token`. Si no hay token → `/login`. Si cargando → skeleton.

```bash
git commit -m "feat: login page + auth con Zustand, eliminar AuthContext legacy"
```

---

## Fase 5: Copiloto IA

### Task 16: Copiloto IA — Frontend

**Files:**
- Create: `dashboard/src/features/copilot/components/copilot-panel.tsx`
- Create: `dashboard/src/features/copilot/components/copilot-button.tsx`
- Create: `dashboard/src/features/copilot/components/message-bubble.tsx`
- Create: `dashboard/src/features/copilot/components/rich-response.tsx`
- Create: `dashboard/src/features/copilot/hooks/use-copilot.ts`

**CopilotButton** — Boton flotante inferior derecho (shadcn `Button` con icono `Sparkles`). Click → toggleCopilot store.

**CopilotPanel** — Sheet lateral (400px). Input abajo, mensajes arriba. Scroll automatico. Historial persistente. Respuestas con markdown renderizado + tablas + mini-charts + links + acciones.

**useCopilot** — Hook que hace POST `/copilot/chat` con mensaje + empresa_id. Streaming response (SSE).

```bash
git commit -m "feat: copiloto IA — panel lateral, chat, respuestas enriquecidas"
```

---

### Task 17: Copiloto IA — Backend

**Files:**
- Create: `sfce/api/rutas/copilot.py`
- Create: `sfce/core/copilot.py`
- Create: `sfce/core/copilot_funciones.py`
- Modify: `sfce/api/app.py` (registrar router copilot)
- Modify: `sfce/api/schemas.py`

**sfce/core/copilot.py:**
- System prompt con contexto empresa
- RAG: inyectar resumen financiero actual
- Function calling: definir ~15 funciones (consultar_pyg, calcular_ratio, etc)
- Feedback: guardar like/dislike en BD

**sfce/api/rutas/copilot.py:**
- POST `/copilot/chat` — recibe mensaje, devuelve respuesta (SSE streaming)
- POST `/copilot/feedback` — guardar feedback
- GET `/copilot/historial` — conversaciones anteriores

Requiere API key de LLM (Mistral o GPT). Usar variable de entorno existente.

```bash
git commit -m "feat: backend copiloto IA — function calling, RAG, feedback loop"
```

---

## Fase 6: Limpieza y Polish

### Task 18: Eliminar archivos legacy + limpieza

**Files a eliminar:**
- `dashboard/src/pages/` (directorio completo — todo migrado a features/)
- `dashboard/src/components/Sidebar.tsx`
- `dashboard/src/components/EmpresaCard.tsx`
- `dashboard/src/Layout.tsx`
- `dashboard/src/context/AuthContext.tsx`
- `dashboard/src/hooks/useApi.ts`
- `dashboard/src/api/client.ts`
- `dashboard/src/types/index.ts` (migrado a types/api.ts)

**Step 1: Eliminar archivos legacy**
**Step 2: Verificar que no hay imports rotos: `npx tsc --noEmit`**
**Step 3: Verificar build: `npm run build`**
**Step 4: Commit**

```bash
git commit -m "refactor: eliminar archivos legacy — pages/, AuthContext, Layout, Sidebar old"
```

---

### Task 19: Polish — Animaciones, responsive, error boundaries

**Files:**
- Create: `dashboard/src/components/error-boundary.tsx`
- Modify: `dashboard/src/App.tsx` (envolver features en ErrorBoundary)

**ErrorBoundary** — Por feature. Fallback con card de error + boton reintentar.

**Responsive** — Verificar todas las paginas en mobile/tablet/desktop.

**Animaciones** — Transiciones fade entre paginas (CSS). Hover effects en cards. Skeleton loading en queries.

**Verificacion final:**
- `npm run build` sin errores
- Preview en mobile, tablet, desktop
- Dark mode funcional
- Todas las paginas cargan sin errores

```bash
git commit -m "feat: error boundaries, responsive, animaciones, polish final"
```

---

### Task 20: Push final y actualizacion docs

**Step 1: Push branch**

```bash
git push origin feat/sfce-v2-fase-e
```

**Step 2: Actualizar CLAUDE.md**

Actualizar dashboard info con nueva estructura, nuevas paginas, stack actualizado.

**Step 3: Commit docs**

```bash
git commit -m "docs: actualizar CLAUDE.md con nuevo dashboard"
git push
```

---

## Resumen de fases y dependencias

```
Fase 1: Fundacion (Tasks 1-3)          → Secuencial, ~30 min
Fase 2: Layout Shell (Task 4)          → Secuencial, ~45 min
Fase 3: Componentes (Tasks 5-6)        → Secuencial, ~30 min
Fase 4: Paginas (Tasks 7-15)           → PARALELO entre modulos, ~4h total
  ├── Task 7: Home
  ├── Task 8: Contabilidad (8 pags)
  ├── Task 9: Facturacion (5 pags)
  ├── Task 10: Fiscal (4 pags)
  ├── Task 11: RRHH (2 pags)
  ├── Task 12: Documentos (4 pags)
  ├── Task 13: Economico (8 pags + backend)
  ├── Task 14: Directorio+Portal+Config (8 pags)
  └── Task 15: Login+Auth
Fase 5: Copiloto IA (Tasks 16-17)      → Secuencial, ~2h
Fase 6: Limpieza (Tasks 18-20)         → Secuencial, ~30 min
```

**Total estimado: 20 tasks, ~8-10 horas de trabajo agente.**
**38 paginas + motor economico + copiloto IA + layout completo.**
