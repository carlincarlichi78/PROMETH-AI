# Dashboard Rewrite — Plan de Implementacion

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reescribir el dashboard SFCE como producto SaaS con 38 paginas, UI shadcn/ui, modulo economico-financiero, y copiloto IA.

**Architecture:** Feature-based con React Query para data fetching, Zustand para estado UI, shadcn/ui para componentes. Backend FastAPI extendido con endpoints economicos y copiloto. Dos streams paralelos: Stream A (foundation + paginas core) y Stream B (backend extensions + paginas avanzadas).

**Tech Stack:** React 18 + TypeScript strict, Vite 6, Tailwind v4, shadcn/ui + Radix, Recharts, TanStack Query, Zustand, React Hook Form + Zod, Lucide React, date-fns. Backend: FastAPI + SQLAlchemy + SQLite.

**Design Doc:** `docs/plans/2026-02-27-dashboard-rewrite-design.md`

---

## Organizacion en 2 Streams Paralelos

### Stream A: Foundation + Core UI
**Responsable de:** Infraestructura frontend, componentes compartidos, layout, y rewrite de paginas core (Home, Contabilidad 8pg, Facturacion 5pg, Fiscal 4pg, Documentos 4pg, RRHH 2pg).

**Archivos que SOLO toca Stream A:**
- `dashboard/package.json`
- `dashboard/src/components/` (ui/, layout/, charts/, data-table/)
- `dashboard/src/hooks/` (excepto hooks de copilot)
- `dashboard/src/lib/` (api-client, query-keys, formatters)
- `dashboard/src/stores/`
- `dashboard/src/App.tsx`, `Layout.tsx`, `main.tsx`
- `dashboard/src/features/contabilidad/`
- `dashboard/src/features/facturacion/`
- `dashboard/src/features/fiscal/`
- `dashboard/src/features/documentos/`
- `dashboard/src/features/rrhh/`
- `dashboard/src/pages/` (borrar antiguas)
- `dashboard/src/types/index.ts` (tipos core)
- `dashboard/tsconfig.json`, `dashboard/components.json`

### Stream B: Backend + Features Avanzadas
**Responsable de:** Nuevas tablas BD, nuevos endpoints API, y paginas avanzadas (Economico 8pg, Configuracion 6pg, Portal 1pg, Directorio 1pg, Copiloto IA).

**Archivos que SOLO toca Stream B:**
- `sfce/api/rutas/economico.py` (NUEVO)
- `sfce/api/rutas/configuracion.py` (NUEVO)
- `sfce/api/rutas/copilot.py` (NUEVO)
- `sfce/api/rutas/portal.py` (NUEVO)
- `sfce/api/rutas/informes.py` (NUEVO)
- `sfce/api/schemas.py` (agregar schemas nuevos al final)
- `sfce/api/app.py` (registrar routers nuevos)
- `sfce/db/modelos.py` (agregar tablas nuevas al final)
- `sfce/db/repositorio.py` (agregar metodos nuevos)
- `dashboard/src/features/economico/`
- `dashboard/src/features/configuracion/`
- `dashboard/src/features/portal/`
- `dashboard/src/features/directorio/`
- `dashboard/src/features/copilot/`
- `dashboard/src/types/economico.ts` (NUEVO, tipos propios)
- `dashboard/src/types/copilot.ts` (NUEVO, tipos propios)
- `dashboard/src/types/config.ts` (NUEVO, tipos propios)

### Punto de sincronizacion
Al final, se mergean los cambios. Stream B necesita los componentes de Stream A (DataTable, ChartCard, KPICard, etc.) pero puede empezar por backend mientras Stream A construye la foundation. Stream B importara desde `@/components/` que Stream A ya habra creado.

**Regla de conflicto:** Si ambos streams necesitan tocar el mismo archivo, Stream A lo crea/modifica primero. Stream B solo agrega al final (append). El merge final resuelve `App.tsx` (rutas) sumando las de ambos.

---

## STREAM A: Foundation + Core UI

### Task A1: Instalar dependencias npm

**Files:**
- Modify: `dashboard/package.json`

**Step 1: Instalar dependencias de produccion**

Run:
```bash
cd dashboard && npm install @tanstack/react-query @tanstack/react-query-devtools zustand recharts react-hook-form @hookform/resolvers zod date-fns lucide-react class-variance-authority clsx tailwind-merge
```

**Step 2: Instalar shadcn/ui CLI y configurar**

Run:
```bash
cd dashboard && npx shadcn@latest init -d
```

Responder a las preguntas:
- Style: New York
- Base color: Slate
- CSS variables: Yes

Esto crea `components.json` y ajusta `tailwind.config`.

**Step 3: Instalar componentes shadcn/ui necesarios**

Run:
```bash
cd dashboard && npx shadcn@latest add button card dialog dropdown-menu input label select separator sheet sidebar table tabs tooltip badge avatar scroll-area command popover calendar checkbox radio-group switch textarea skeleton alert alert-dialog breadcrumb collapsible navigation-menu progress sonner toggle toggle-group
```

**Step 4: Verificar build**

Run: `cd dashboard && npx tsc --noEmit`
Expected: 0 errores (pueden haber warnings de archivos viejos, aceptable)

**Step 5: Commit**

```bash
git add dashboard/package.json dashboard/package-lock.json dashboard/components.json dashboard/src/components/ui/ dashboard/tsconfig.json dashboard/src/lib/utils.ts
git commit -m "feat: instalar dependencias dashboard rewrite — shadcn/ui, recharts, react-query, zustand"
```

---

### Task A2: Path aliases y configuracion Vite

**Files:**
- Modify: `dashboard/vite.config.ts`
- Modify: `dashboard/tsconfig.json`

**Step 1: Configurar path alias @/ en tsconfig.json**

Agregar en `compilerOptions`:
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

**Step 2: Configurar alias en vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

**Step 3: Verificar build**

Run: `cd dashboard && npx tsc --noEmit`

**Step 4: Commit**

```bash
git add dashboard/vite.config.ts dashboard/tsconfig.json
git commit -m "feat: configurar path alias @/ en vite y tsconfig"
```

---

### Task A3: Zustand stores

**Files:**
- Create: `dashboard/src/stores/empresa-store.ts`
- Create: `dashboard/src/stores/ui-store.ts`

**Step 1: Store de empresa activa**

```typescript
// dashboard/src/stores/empresa-store.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Empresa {
  id: number
  cif: string
  nombre: string
  forma_juridica: string
  territorio: string
  regimen_iva: string
  activa: boolean
}

interface EmpresaStore {
  empresaActiva: Empresa | null
  setEmpresaActiva: (empresa: Empresa | null) => void
}

export const useEmpresaStore = create<EmpresaStore>()(
  persist(
    (set) => ({
      empresaActiva: null,
      setEmpresaActiva: (empresa) => set({ empresaActiva: empresa }),
    }),
    { name: 'sfce-empresa-activa' }
  )
)
```

**Step 2: Store de UI**

```typescript
// dashboard/src/stores/ui-store.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Tema = 'light' | 'dark' | 'system'
type Densidad = 'compacta' | 'comoda'

interface UIStore {
  tema: Tema
  densidad: Densidad
  sidebarColapsado: boolean
  copilotAbierto: boolean
  setTema: (tema: Tema) => void
  setDensidad: (densidad: Densidad) => void
  toggleSidebar: () => void
  toggleCopilot: () => void
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      tema: 'system',
      densidad: 'comoda',
      sidebarColapsado: false,
      copilotAbierto: false,
      setTema: (tema) => set({ tema }),
      setDensidad: (densidad) => set({ densidad }),
      toggleSidebar: () => set((s) => ({ sidebarColapsado: !s.sidebarColapsado })),
      toggleCopilot: () => set((s) => ({ copilotAbierto: !s.copilotAbierto })),
    }),
    { name: 'sfce-ui', partialize: (s) => ({ tema: s.tema, densidad: s.densidad, sidebarColapsado: s.sidebarColapsado }) }
  )
)
```

**Step 3: Commit**

```bash
git add dashboard/src/stores/
git commit -m "feat: zustand stores — empresa activa + UI (tema, sidebar, copilot)"
```

---

### Task A4: API client con React Query

**Files:**
- Create: `dashboard/src/lib/api-client.ts`
- Create: `dashboard/src/lib/query-keys.ts`
- Create: `dashboard/src/lib/formatters.ts`
- Modify: `dashboard/src/main.tsx`

**Step 1: API client**

```typescript
// dashboard/src/lib/api-client.ts

const TOKEN_KEY = 'sfce_token'

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY)
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opciones.headers as Record<string, string> ?? {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const respuesta = await fetch(ruta, { ...opciones, headers })

  if (respuesta.status === 401) {
    localStorage.removeItem(TOKEN_KEY)
    window.location.href = '/login'
    throw new ApiError(401, 'Sesion expirada')
  }

  if (!respuesta.ok) {
    const error = await respuesta.json().catch(() => ({ detail: `Error HTTP ${respuesta.status}` }))
    throw new ApiError(respuesta.status, error.detail ?? `Error ${respuesta.status}`)
  }

  return respuesta.json() as Promise<T>
}

export const api = {
  get: <T>(ruta: string) => fetchApi<T>(ruta),
  post: <T>(ruta: string, body: unknown) => fetchApi<T>(ruta, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(ruta: string, body: unknown) => fetchApi<T>(ruta, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(ruta: string) => fetchApi<T>(ruta, { method: 'DELETE' }),
}
```

**Step 2: Query keys**

```typescript
// dashboard/src/lib/query-keys.ts

/** Claves centralizadas para React Query — previene colisiones y facilita invalidacion */
export const queryKeys = {
  empresas: {
    todas: ['empresas'] as const,
    detalle: (id: number) => ['empresas', id] as const,
    proveedores: (id: number) => ['empresas', id, 'proveedores'] as const,
    trabajadores: (id: number) => ['empresas', id, 'trabajadores'] as const,
  },
  contabilidad: {
    pyg: (empresaId: number, params?: Record<string, string>) => ['contabilidad', empresaId, 'pyg', params] as const,
    balance: (empresaId: number, params?: Record<string, string>) => ['contabilidad', empresaId, 'balance', params] as const,
    diario: (empresaId: number, params?: Record<string, string>) => ['contabilidad', empresaId, 'diario', params] as const,
    facturas: (empresaId: number, params?: Record<string, string>) => ['contabilidad', empresaId, 'facturas', params] as const,
    activos: (empresaId: number) => ['contabilidad', empresaId, 'activos'] as const,
    planCuentas: (empresaId: number) => ['contabilidad', empresaId, 'plan-cuentas'] as const,
  },
  documentos: {
    lista: (empresaId: number, params?: Record<string, string>) => ['documentos', empresaId, params] as const,
    cuarentena: (empresaId: number) => ['documentos', empresaId, 'cuarentena'] as const,
    pipeline: (empresaId: number) => ['documentos', empresaId, 'pipeline'] as const,
  },
  modelos: {
    disponibles: ['modelos', 'disponibles'] as const,
    calendario: (empresaId: number) => ['modelos', empresaId, 'calendario'] as const,
    historico: (empresaId: number) => ['modelos', empresaId, 'historico'] as const,
    calcular: (empresaId: number, modelo: string, periodo: string) => ['modelos', empresaId, modelo, periodo] as const,
  },
  directorio: {
    todos: ['directorio'] as const,
    buscar: (q: string) => ['directorio', 'buscar', q] as const,
    detalle: (id: number) => ['directorio', id] as const,
  },
  // Stream B agrega los suyos aqui
  economico: {
    ratios: (empresaId: number) => ['economico', empresaId, 'ratios'] as const,
    kpis: (empresaId: number) => ['economico', empresaId, 'kpis'] as const,
    tesoreria: (empresaId: number) => ['economico', empresaId, 'tesoreria'] as const,
    cashflow: (empresaId: number) => ['economico', empresaId, 'cashflow'] as const,
    scoring: (empresaId: number) => ['economico', empresaId, 'scoring'] as const,
    presupuesto: (empresaId: number) => ['economico', empresaId, 'presupuesto'] as const,
    comparativa: (empresaId: number) => ['economico', empresaId, 'comparativa'] as const,
  },
} as const
```

**Step 3: Formatters**

```typescript
// dashboard/src/lib/formatters.ts
import { format, parseISO } from 'date-fns'
import { es } from 'date-fns/locale'

/** Formatea importe en EUR: 1234.56 → "1.234,56 EUR" */
export function formatearImporte(valor: number | null | undefined, moneda = 'EUR'): string {
  if (valor == null) return '-'
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: moneda }).format(valor)
}

/** Formatea porcentaje: 0.1234 → "12,34%" */
export function formatearPorcentaje(valor: number | null | undefined, decimales = 2): string {
  if (valor == null) return '-'
  return new Intl.NumberFormat('es-ES', { style: 'percent', minimumFractionDigits: decimales, maximumFractionDigits: decimales }).format(valor)
}

/** Formatea fecha: "2025-01-15" → "15 ene 2025" */
export function formatearFecha(fecha: string | null | undefined, patron = 'd MMM yyyy'): string {
  if (!fecha) return '-'
  return format(parseISO(fecha), patron, { locale: es })
}

/** Formatea numero: 1234567.89 → "1.234.567,89" */
export function formatearNumero(valor: number | null | undefined, decimales = 2): string {
  if (valor == null) return '-'
  return new Intl.NumberFormat('es-ES', { minimumFractionDigits: decimales, maximumFractionDigits: decimales }).format(valor)
}

/** Color segun variacion positiva/negativa */
export function colorVariacion(valor: number): string {
  if (valor > 0) return 'text-green-600'
  if (valor < 0) return 'text-red-600'
  return 'text-gray-500'
}
```

**Step 4: Configurar QueryClient en main.tsx**

```typescript
// dashboard/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { AuthProvider } from '@/context/AuthContext'
import { App } from '@/App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutos
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </StrictMode>
)
```

**Step 5: Verificar build**

Run: `cd dashboard && npx tsc --noEmit`

**Step 6: Commit**

```bash
git add dashboard/src/lib/ dashboard/src/main.tsx
git commit -m "feat: api client, query keys, formatters, react query provider"
```

---

### Task A5: Layout system — AppShell, Header, Sidebar nueva

**Files:**
- Create: `dashboard/src/components/layout/app-shell.tsx`
- Create: `dashboard/src/components/layout/header.tsx`
- Create: `dashboard/src/components/layout/app-sidebar.tsx`
- Create: `dashboard/src/components/layout/breadcrumbs.tsx`
- Modify: `dashboard/src/App.tsx` (nuevo layout)
- Delete: `dashboard/src/Layout.tsx` (reemplazado)
- Delete: `dashboard/src/components/Sidebar.tsx` (reemplazado)

**Step 1: App Shell**

El app-shell es el layout raiz: sidebar colapsable + header + area contenido.

```typescript
// dashboard/src/components/layout/app-shell.tsx
import { Outlet } from 'react-router-dom'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { AppSidebar } from './app-sidebar'
import { Header } from './header'
import { useUIStore } from '@/stores/ui-store'
import { Toaster } from '@/components/ui/sonner'

export function AppShell() {
  const sidebarColapsado = useUIStore((s) => s.sidebarColapsado)

  return (
    <SidebarProvider defaultOpen={!sidebarColapsado}>
      <AppSidebar />
      <SidebarInset>
        <Header />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </SidebarInset>
      <Toaster richColors position="bottom-right" />
    </SidebarProvider>
  )
}
```

**Step 2: Header**

Construir header con: logo, selector empresa (dropdown), busqueda global (Cmd+K), notificaciones, avatar usuario, toggle tema.

```typescript
// dashboard/src/components/layout/header.tsx
import { Search, Bell, Moon, Sun, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useAuth } from '@/context/AuthContext'
import { useUIStore } from '@/stores/ui-store'
import { useEmpresaStore } from '@/stores/empresa-store'
import { Breadcrumbs } from './breadcrumbs'

export function Header() {
  const { usuario, logout } = useAuth()
  const { tema, setTema, toggleCopilot } = useUIStore()
  const empresaActiva = useEmpresaStore((s) => s.empresaActiva)
  const iniciales = usuario?.nombre?.split(' ').map(n => n[0]).join('').slice(0, 2) ?? '??'

  return (
    <header className="flex h-14 items-center gap-3 border-b px-4 bg-background">
      <SidebarTrigger />
      <Separator orientation="vertical" className="h-6" />
      <Breadcrumbs />

      {empresaActiva && (
        <span className="text-sm text-muted-foreground hidden md:block">
          {empresaActiva.nombre}
        </span>
      )}

      <div className="ml-auto flex items-center gap-2">
        {/* Busqueda global Cmd+K — placeholder, implementar despues */}
        <Button variant="outline" size="sm" className="hidden md:flex gap-2 text-muted-foreground">
          <Search className="h-4 w-4" />
          <span>Buscar...</span>
          <kbd className="ml-2 rounded bg-muted px-1.5 py-0.5 text-[10px]">Ctrl+K</kbd>
        </Button>

        {/* Notificaciones */}
        <Button variant="ghost" size="icon">
          <Bell className="h-4 w-4" />
        </Button>

        {/* Copiloto IA */}
        <Button variant="ghost" size="icon" onClick={toggleCopilot}>
          <Sparkles className="h-4 w-4" />
        </Button>

        {/* Toggle tema */}
        <Button variant="ghost" size="icon" onClick={() => setTema(tema === 'dark' ? 'light' : 'dark')}>
          {tema === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        {/* Avatar usuario */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs">{iniciales}</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem disabled>
              <span className="font-medium">{usuario?.nombre}</span>
            </DropdownMenuItem>
            <DropdownMenuItem disabled>
              <span className="text-muted-foreground text-xs">{usuario?.email}</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={logout}>Cerrar sesion</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
```

**Step 3: App Sidebar**

Usar el componente Sidebar de shadcn/ui con grupos colapsables e iconos Lucide. La sidebar muestra secciones segun el design doc (Contabilidad, Facturacion, RRHH, Fiscal, Documentos, Economico, Portal, Directorio, Configuracion).

```typescript
// dashboard/src/components/layout/app-sidebar.tsx
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Home, Receipt, BookOpen, Scale, FileText, Calculator, TrendingUp,
  BarChart3, Building2, Settings, Users, Upload, FolderOpen, AlertTriangle,
  Calendar, FileDown, DoorClosed, DoorOpen, Wallet, PiggyBank, Target,
  GitCompare, CreditCard, FileBarChart, ExternalLink, Database, Palette,
  Shield, HardDrive, Key, UserCog, Briefcase
} from 'lucide-react'
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent, SidebarGroupLabel,
  SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarFooter,
} from '@/components/ui/sidebar'
import { useEmpresaStore } from '@/stores/empresa-store'
import { useAuth } from '@/context/AuthContext'

interface ItemMenu {
  titulo: string
  ruta: string
  icono: React.ElementType
}

interface GrupoMenu {
  label: string
  items: ItemMenu[]
}

export function AppSidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { usuario, logout } = useAuth()
  const empresaActiva = useEmpresaStore((s) => s.empresaActiva)
  const eId = empresaActiva?.id

  const gruposGenerales: GrupoMenu[] = [
    {
      label: '',
      items: [
        { titulo: 'Panel Principal', ruta: '/', icono: Home },
        { titulo: 'Directorio', ruta: '/directorio', icono: Database },
      ],
    },
  ]

  const gruposEmpresa: GrupoMenu[] = eId
    ? [
        {
          label: 'Contabilidad',
          items: [
            { titulo: 'Cuenta de Resultados', ruta: `/empresa/${eId}/pyg`, icono: TrendingUp },
            { titulo: 'Balance de Situacion', ruta: `/empresa/${eId}/balance`, icono: Scale },
            { titulo: 'Libro Diario', ruta: `/empresa/${eId}/diario`, icono: BookOpen },
            { titulo: 'Plan de Cuentas', ruta: `/empresa/${eId}/plan-cuentas`, icono: FileText },
            { titulo: 'Conciliacion Bancaria', ruta: `/empresa/${eId}/conciliacion`, icono: GitCompare },
            { titulo: 'Amortizaciones', ruta: `/empresa/${eId}/amortizaciones`, icono: Calculator },
            { titulo: 'Cierre Ejercicio', ruta: `/empresa/${eId}/cierre`, icono: DoorClosed },
            { titulo: 'Apertura Ejercicio', ruta: `/empresa/${eId}/apertura`, icono: DoorOpen },
          ],
        },
        {
          label: 'Facturacion',
          items: [
            { titulo: 'Facturas Emitidas', ruta: `/empresa/${eId}/facturas-emitidas`, icono: FileDown },
            { titulo: 'Facturas Recibidas', ruta: `/empresa/${eId}/facturas-recibidas`, icono: Receipt },
            { titulo: 'Cobros y Pagos', ruta: `/empresa/${eId}/cobros-pagos`, icono: Wallet },
            { titulo: 'Presupuestos', ruta: `/empresa/${eId}/presupuestos`, icono: FileBarChart },
            { titulo: 'Contratos Recurrentes', ruta: `/empresa/${eId}/contratos`, icono: Briefcase },
          ],
        },
        {
          label: 'RRHH',
          items: [
            { titulo: 'Nominas', ruta: `/empresa/${eId}/nominas`, icono: PiggyBank },
            { titulo: 'Trabajadores', ruta: `/empresa/${eId}/trabajadores`, icono: Users },
          ],
        },
        {
          label: 'Fiscal',
          items: [
            { titulo: 'Calendario Fiscal', ruta: `/empresa/${eId}/calendario-fiscal`, icono: Calendar },
            { titulo: 'Modelos Fiscales', ruta: `/empresa/${eId}/modelos-fiscales`, icono: FileText },
            { titulo: 'Generar Modelo', ruta: `/empresa/${eId}/modelos-fiscales/generar`, icono: Calculator },
            { titulo: 'Historico Modelos', ruta: `/empresa/${eId}/modelos-fiscales/historico`, icono: FolderOpen },
          ],
        },
        {
          label: 'Documentos',
          items: [
            { titulo: 'Bandeja Entrada', ruta: `/empresa/${eId}/inbox`, icono: Upload },
            { titulo: 'Pipeline', ruta: `/empresa/${eId}/pipeline`, icono: BarChart3 },
            { titulo: 'Cuarentena', ruta: `/empresa/${eId}/cuarentena`, icono: AlertTriangle },
            { titulo: 'Archivo Digital', ruta: `/empresa/${eId}/archivo`, icono: FolderOpen },
          ],
        },
        {
          label: 'Economico-Financiero',
          items: [
            { titulo: 'Ratios Financieros', ruta: `/empresa/${eId}/ratios`, icono: TrendingUp },
            { titulo: 'KPIs Sectoriales', ruta: `/empresa/${eId}/kpis`, icono: Target },
            { titulo: 'Tesoreria', ruta: `/empresa/${eId}/tesoreria`, icono: PiggyBank },
            { titulo: 'Centros de Coste', ruta: `/empresa/${eId}/centros-coste`, icono: Building2 },
            { titulo: 'Presupuesto vs Real', ruta: `/empresa/${eId}/presupuesto-real`, icono: GitCompare },
            { titulo: 'Comparativa Interanual', ruta: `/empresa/${eId}/comparativa`, icono: BarChart3 },
            { titulo: 'Credit Scoring', ruta: `/empresa/${eId}/scoring`, icono: CreditCard },
            { titulo: 'Informes PDF', ruta: `/empresa/${eId}/informes`, icono: FileBarChart },
          ],
        },
        {
          label: 'Portal Cliente',
          items: [
            { titulo: 'Vista Cliente', ruta: `/empresa/${eId}/portal`, icono: ExternalLink },
          ],
        },
        {
          label: 'Configuracion',
          items: [
            { titulo: 'Empresa', ruta: `/empresa/${eId}/config/empresa`, icono: Building2 },
            { titulo: 'Usuarios y Roles', ruta: `/empresa/${eId}/config/usuarios`, icono: UserCog },
            { titulo: 'Integraciones', ruta: `/empresa/${eId}/config/integraciones`, icono: Settings },
            { titulo: 'Backup / Restore', ruta: `/empresa/${eId}/config/backup`, icono: HardDrive },
            { titulo: 'Licencia', ruta: `/empresa/${eId}/config/licencia`, icono: Key },
            { titulo: 'Apariencia', ruta: `/empresa/${eId}/config/apariencia`, icono: Palette },
          ],
        },
      ]
    : []

  const todosLosGrupos = [...gruposGenerales, ...gruposEmpresa]

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b p-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm">
            S
          </div>
          <div className="flex flex-col group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold">SFCE</span>
            <span className="text-[10px] text-muted-foreground">Sistema Fiscal Contable</span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        {todosLosGrupos.map((grupo, idx) => (
          <SidebarGroup key={grupo.label || `gen-${idx}`}>
            {grupo.label && <SidebarGroupLabel>{grupo.label}</SidebarGroupLabel>}
            <SidebarGroupContent>
              <SidebarMenu>
                {grupo.items.map((item) => (
                  <SidebarMenuItem key={item.ruta}>
                    <SidebarMenuButton
                      isActive={location.pathname === item.ruta}
                      onClick={() => navigate(item.ruta)}
                      tooltip={item.titulo}
                    >
                      <item.icono className="h-4 w-4" />
                      <span>{item.titulo}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter className="border-t p-3">
        <div className="flex items-center gap-2 group-data-[collapsible=icon]:justify-center">
          <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
            {usuario?.nombre?.charAt(0) ?? '?'}
          </div>
          <div className="flex flex-col group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-medium truncate">{usuario?.nombre}</span>
            <button onClick={logout} className="text-xs text-muted-foreground hover:text-foreground text-left">
              Cerrar sesion
            </button>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
```

**Step 4: Breadcrumbs**

```typescript
// dashboard/src/components/layout/breadcrumbs.tsx
import { useLocation, Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { useEmpresaStore } from '@/stores/empresa-store'

const NOMBRES_RUTA: Record<string, string> = {
  pyg: 'Cuenta de Resultados',
  balance: 'Balance de Situacion',
  diario: 'Libro Diario',
  facturas: 'Facturas',
  'facturas-emitidas': 'Facturas Emitidas',
  'facturas-recibidas': 'Facturas Recibidas',
  'cobros-pagos': 'Cobros y Pagos',
  presupuestos: 'Presupuestos',
  contratos: 'Contratos Recurrentes',
  activos: 'Activos Fijos',
  amortizaciones: 'Amortizaciones',
  'plan-cuentas': 'Plan de Cuentas',
  conciliacion: 'Conciliacion Bancaria',
  cierre: 'Cierre Ejercicio',
  apertura: 'Apertura Ejercicio',
  inbox: 'Bandeja Entrada',
  pipeline: 'Pipeline',
  cuarentena: 'Cuarentena',
  archivo: 'Archivo Digital',
  'modelos-fiscales': 'Modelos Fiscales',
  'calendario-fiscal': 'Calendario Fiscal',
  generar: 'Generar Modelo',
  historico: 'Historico',
  nominas: 'Nominas',
  trabajadores: 'Trabajadores',
  ratios: 'Ratios Financieros',
  kpis: 'KPIs Sectoriales',
  tesoreria: 'Tesoreria',
  'centros-coste': 'Centros de Coste',
  'presupuesto-real': 'Presupuesto vs Real',
  comparativa: 'Comparativa Interanual',
  scoring: 'Credit Scoring',
  informes: 'Informes PDF',
  portal: 'Portal Cliente',
  directorio: 'Directorio',
  config: 'Configuracion',
  empresa: 'Empresa',
  usuarios: 'Usuarios y Roles',
  integraciones: 'Integraciones',
  backup: 'Backup / Restore',
  licencia: 'Licencia',
  apariencia: 'Apariencia',
}

export function Breadcrumbs() {
  const location = useLocation()
  const empresaActiva = useEmpresaStore((s) => s.empresaActiva)
  const segmentos = location.pathname.split('/').filter(Boolean)

  // No mostrar breadcrumbs en root
  if (segmentos.length === 0) return null

  const migas: { label: string; ruta: string }[] = []

  for (let i = 0; i < segmentos.length; i++) {
    const seg = segmentos[i]
    const rutaAcumulada = '/' + segmentos.slice(0, i + 1).join('/')

    // Omitir IDs numericos (son parametros de empresa)
    if (/^\d+$/.test(seg)) continue

    // Segmento "empresa" lo renombramos al nombre de la empresa activa
    if (seg === 'empresa' && empresaActiva) {
      migas.push({ label: empresaActiva.nombre, ruta: `/empresa/${empresaActiva.id}` })
      continue
    }

    const nombre = NOMBRES_RUTA[seg] ?? seg
    migas.push({ label: nombre, ruta: rutaAcumulada })
  }

  return (
    <nav className="flex items-center gap-1 text-sm text-muted-foreground">
      {migas.map((miga, idx) => (
        <span key={miga.ruta} className="flex items-center gap-1">
          {idx > 0 && <ChevronRight className="h-3 w-3" />}
          {idx < migas.length - 1 ? (
            <Link to={miga.ruta} className="hover:text-foreground transition-colors">
              {miga.label}
            </Link>
          ) : (
            <span className="text-foreground font-medium">{miga.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
```

**Step 5: Actualizar App.tsx con nuevo layout**

Reescribir App.tsx para usar AppShell y lazy loading. Borrar archivos viejos (Layout.tsx, components/Sidebar.tsx). Estructura de rutas segun design doc.

NOTA: Las rutas de Stream B (economico, config, portal, copilot) se definen aqui pero apuntan a paginas placeholder que Stream B reemplazara. De esta forma ambos streams trabajan sobre un App.tsx funcional desde el inicio.

```typescript
// dashboard/src/App.tsx
import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { AppShell } from '@/components/layout/app-shell'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { Skeleton } from '@/components/ui/skeleton'

// Lazy loading por pagina
const Login = lazy(() => import('@/features/auth/login-page'))
const Home = lazy(() => import('@/features/home/home-page'))
const NotFound = lazy(() => import('@/features/not-found'))

// Contabilidad
const PyG = lazy(() => import('@/features/contabilidad/pyg-page'))
const Balance = lazy(() => import('@/features/contabilidad/balance-page'))
const Diario = lazy(() => import('@/features/contabilidad/diario-page'))
const PlanCuentas = lazy(() => import('@/features/contabilidad/plan-cuentas-page'))
const Conciliacion = lazy(() => import('@/features/contabilidad/conciliacion-page'))
const Amortizaciones = lazy(() => import('@/features/contabilidad/amortizaciones-page'))
const CierreEjercicio = lazy(() => import('@/features/contabilidad/cierre-page'))
const AperturaEjercicio = lazy(() => import('@/features/contabilidad/apertura-page'))

// Facturacion
const FacturasEmitidas = lazy(() => import('@/features/facturacion/emitidas-page'))
const FacturasRecibidas = lazy(() => import('@/features/facturacion/recibidas-page'))
const CobrosPagos = lazy(() => import('@/features/facturacion/cobros-pagos-page'))
const Presupuestos = lazy(() => import('@/features/facturacion/presupuestos-page'))
const Contratos = lazy(() => import('@/features/facturacion/contratos-page'))

// RRHH
const Nominas = lazy(() => import('@/features/rrhh/nominas-page'))
const Trabajadores = lazy(() => import('@/features/rrhh/trabajadores-page'))

// Fiscal
const CalendarioFiscal = lazy(() => import('@/features/fiscal/calendario-page'))
const ModelosFiscales = lazy(() => import('@/features/fiscal/modelos-page'))
const GenerarModelo = lazy(() => import('@/features/fiscal/generar-page'))
const HistoricoModelos = lazy(() => import('@/features/fiscal/historico-page'))

// Documentos
const Inbox = lazy(() => import('@/features/documentos/inbox-page'))
const PipelinePage = lazy(() => import('@/features/documentos/pipeline-page'))
const CuarentenaPage = lazy(() => import('@/features/documentos/cuarentena-page'))
const Archivo = lazy(() => import('@/features/documentos/archivo-page'))

// Economico (Stream B)
const Ratios = lazy(() => import('@/features/economico/ratios-page'))
const KPIs = lazy(() => import('@/features/economico/kpis-page'))
const Tesoreria = lazy(() => import('@/features/economico/tesoreria-page'))
const CentrosCoste = lazy(() => import('@/features/economico/centros-coste-page'))
const PresupuestoReal = lazy(() => import('@/features/economico/presupuesto-real-page'))
const Comparativa = lazy(() => import('@/features/economico/comparativa-page'))
const Scoring = lazy(() => import('@/features/economico/scoring-page'))
const Informes = lazy(() => import('@/features/economico/informes-page'))

// Portal, Directorio, Config (Stream B)
const Portal = lazy(() => import('@/features/portal/portal-page'))
const Directorio = lazy(() => import('@/features/directorio/directorio-page'))
const ConfigEmpresa = lazy(() => import('@/features/configuracion/empresa-page'))
const ConfigUsuarios = lazy(() => import('@/features/configuracion/usuarios-page'))
const ConfigIntegraciones = lazy(() => import('@/features/configuracion/integraciones-page'))
const ConfigBackup = lazy(() => import('@/features/configuracion/backup-page'))
const ConfigLicencia = lazy(() => import('@/features/configuracion/licencia-page'))
const ConfigApariencia = lazy(() => import('@/features/configuracion/apariencia-page'))

function SuspenseFallback() {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-96" />
      <div className="grid grid-cols-3 gap-4 mt-6">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    </div>
  )
}

export function App() {
  return (
    <Suspense fallback={<SuspenseFallback />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
          <Route path="/" element={<Home />} />
          <Route path="/directorio" element={<Directorio />} />

          {/* Contabilidad */}
          <Route path="/empresa/:id/pyg" element={<PyG />} />
          <Route path="/empresa/:id/balance" element={<Balance />} />
          <Route path="/empresa/:id/diario" element={<Diario />} />
          <Route path="/empresa/:id/plan-cuentas" element={<PlanCuentas />} />
          <Route path="/empresa/:id/conciliacion" element={<Conciliacion />} />
          <Route path="/empresa/:id/amortizaciones" element={<Amortizaciones />} />
          <Route path="/empresa/:id/cierre" element={<CierreEjercicio />} />
          <Route path="/empresa/:id/apertura" element={<AperturaEjercicio />} />

          {/* Facturacion */}
          <Route path="/empresa/:id/facturas-emitidas" element={<FacturasEmitidas />} />
          <Route path="/empresa/:id/facturas-recibidas" element={<FacturasRecibidas />} />
          <Route path="/empresa/:id/cobros-pagos" element={<CobrosPagos />} />
          <Route path="/empresa/:id/presupuestos" element={<Presupuestos />} />
          <Route path="/empresa/:id/contratos" element={<Contratos />} />

          {/* RRHH */}
          <Route path="/empresa/:id/nominas" element={<Nominas />} />
          <Route path="/empresa/:id/trabajadores" element={<Trabajadores />} />

          {/* Fiscal */}
          <Route path="/empresa/:id/calendario-fiscal" element={<CalendarioFiscal />} />
          <Route path="/empresa/:id/modelos-fiscales" element={<ModelosFiscales />} />
          <Route path="/empresa/:id/modelos-fiscales/generar" element={<GenerarModelo />} />
          <Route path="/empresa/:id/modelos-fiscales/historico" element={<HistoricoModelos />} />

          {/* Documentos */}
          <Route path="/empresa/:id/inbox" element={<Inbox />} />
          <Route path="/empresa/:id/pipeline" element={<PipelinePage />} />
          <Route path="/empresa/:id/cuarentena" element={<CuarentenaPage />} />
          <Route path="/empresa/:id/archivo" element={<Archivo />} />

          {/* Economico-Financiero (Stream B) */}
          <Route path="/empresa/:id/ratios" element={<Ratios />} />
          <Route path="/empresa/:id/kpis" element={<KPIs />} />
          <Route path="/empresa/:id/tesoreria" element={<Tesoreria />} />
          <Route path="/empresa/:id/centros-coste" element={<CentrosCoste />} />
          <Route path="/empresa/:id/presupuesto-real" element={<PresupuestoReal />} />
          <Route path="/empresa/:id/comparativa" element={<Comparativa />} />
          <Route path="/empresa/:id/scoring" element={<Scoring />} />
          <Route path="/empresa/:id/informes" element={<Informes />} />

          {/* Portal Cliente (Stream B) */}
          <Route path="/empresa/:id/portal" element={<Portal />} />

          {/* Configuracion (Stream B) */}
          <Route path="/empresa/:id/config/empresa" element={<ConfigEmpresa />} />
          <Route path="/empresa/:id/config/usuarios" element={<ConfigUsuarios />} />
          <Route path="/empresa/:id/config/integraciones" element={<ConfigIntegraciones />} />
          <Route path="/empresa/:id/config/backup" element={<ConfigBackup />} />
          <Route path="/empresa/:id/config/licencia" element={<ConfigLicencia />} />
          <Route path="/empresa/:id/config/apariencia" element={<ConfigApariencia />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}
```

**Step 6: Borrar archivos viejos**

```bash
rm dashboard/src/Layout.tsx dashboard/src/components/Sidebar.tsx
```

**Step 7: Verificar build**

Run: `cd dashboard && npx tsc --noEmit`
NOTA: Fallara porque las paginas lazy aun no existen. Siguiente task las crea.

**Step 8: Commit**

```bash
git add dashboard/src/components/layout/ dashboard/src/App.tsx
git add -u dashboard/src/Layout.tsx dashboard/src/components/Sidebar.tsx
git commit -m "feat: layout system — AppShell, Header, Sidebar shadcn/ui, Breadcrumbs, lazy routes"
```

---

### Task A6: Componentes compartidos — KPICard, ChartCard, DataTable, FilterBar

**Files:**
- Create: `dashboard/src/components/charts/kpi-card.tsx`
- Create: `dashboard/src/components/charts/chart-card.tsx`
- Create: `dashboard/src/components/data-table/data-table.tsx`
- Create: `dashboard/src/components/data-table/data-table-pagination.tsx`
- Create: `dashboard/src/components/data-table/data-table-toolbar.tsx`
- Create: `dashboard/src/components/filter-bar.tsx`
- Create: `dashboard/src/components/estado-vacio.tsx`
- Create: `dashboard/src/components/page-header.tsx`

**Step 1: KPICard**

```typescript
// dashboard/src/components/charts/kpi-card.tsx
import { ArrowDown, ArrowUp, Minus } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface KPICardProps {
  titulo: string
  valor: string
  variacion?: number // porcentaje vs periodo anterior
  descripcion?: string
  icono?: React.ElementType
  className?: string
}

export function KPICard({ titulo, valor, variacion, descripcion, icono: Icono, className }: KPICardProps) {
  const IconoVariacion = variacion && variacion > 0 ? ArrowUp : variacion && variacion < 0 ? ArrowDown : Minus
  const colorVariacion = variacion && variacion > 0
    ? 'text-green-600 dark:text-green-400'
    : variacion && variacion < 0
    ? 'text-red-600 dark:text-red-400'
    : 'text-muted-foreground'

  return (
    <Card className={cn('', className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{titulo}</CardTitle>
        {Icono && <Icono className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{valor}</div>
        {(variacion != null || descripcion) && (
          <div className="flex items-center gap-1 mt-1">
            {variacion != null && (
              <span className={cn('flex items-center text-xs font-medium', colorVariacion)}>
                <IconoVariacion className="h-3 w-3 mr-0.5" />
                {Math.abs(variacion).toFixed(1)}%
              </span>
            )}
            {descripcion && <span className="text-xs text-muted-foreground">{descripcion}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

**Step 2: ChartCard**

```typescript
// dashboard/src/components/charts/chart-card.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface ChartCardProps {
  titulo: string
  children: React.ReactNode
  periodos?: string[]
  periodoActual?: string
  onCambioPeriodo?: (periodo: string) => void
  cargando?: boolean
  className?: string
  altura?: number
}

export function ChartCard({ titulo, children, periodos, periodoActual, onCambioPeriodo, cargando, className, altura = 300 }: ChartCardProps) {
  return (
    <Card className={cn('', className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">{titulo}</CardTitle>
        {periodos && periodos.length > 0 && (
          <Select value={periodoActual} onValueChange={onCambioPeriodo}>
            <SelectTrigger className="w-32 h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {periodos.map((p) => (
                <SelectItem key={p} value={p}>{p}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </CardHeader>
      <CardContent>
        {cargando ? (
          <Skeleton className="w-full" style={{ height: altura }} />
        ) : (
          <div style={{ height: altura }}>{children}</div>
        )}
      </CardContent>
    </Card>
  )
}
```

**Step 3: DataTable**

Tabla generica reutilizable con sort, paginacion, busqueda. Basada en `@tanstack/react-table` no es necesario — usaremos componentes shadcn/ui Table directamente con estado local.

```typescript
// dashboard/src/components/data-table/data-table.tsx
import { useState, useMemo } from 'react'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

export interface ColumnaTabla<T> {
  key: string
  header: string
  render: (item: T) => React.ReactNode
  sortable?: boolean
  sortFn?: (a: T, b: T) => number
  className?: string
}

interface DataTableProps<T> {
  datos: T[]
  columnas: ColumnaTabla<T>[]
  cargando?: boolean
  busqueda?: boolean
  filtroBusqueda?: (item: T, termino: string) => boolean
  filasPorPagina?: number
  vacio?: React.ReactNode
  onClickFila?: (item: T) => void
}

export function DataTable<T extends { id?: number | string }>({
  datos,
  columnas,
  cargando,
  busqueda = false,
  filtroBusqueda,
  filasPorPagina = 20,
  vacio,
  onClickFila,
}: DataTableProps<T>) {
  const [terminoBusqueda, setTerminoBusqueda] = useState('')
  const [ordenColumna, setOrdenColumna] = useState<string | null>(null)
  const [ordenDir, setOrdenDir] = useState<'asc' | 'desc'>('asc')
  const [pagina, setPagina] = useState(0)

  const datosFiltrados = useMemo(() => {
    let resultado = datos
    if (terminoBusqueda && filtroBusqueda) {
      resultado = resultado.filter((item) => filtroBusqueda(item, terminoBusqueda))
    }
    if (ordenColumna) {
      const col = columnas.find((c) => c.key === ordenColumna)
      if (col?.sortFn) {
        resultado = [...resultado].sort((a, b) => {
          const r = col.sortFn!(a, b)
          return ordenDir === 'desc' ? -r : r
        })
      }
    }
    return resultado
  }, [datos, terminoBusqueda, filtroBusqueda, ordenColumna, ordenDir, columnas])

  const totalPaginas = Math.ceil(datosFiltrados.length / filasPorPagina)
  const datosPagina = datosFiltrados.slice(pagina * filasPorPagina, (pagina + 1) * filasPorPagina)

  function toggleOrden(key: string) {
    if (ordenColumna === key) {
      setOrdenDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setOrdenColumna(key)
      setOrdenDir('asc')
    }
  }

  if (cargando) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {busqueda && (
        <Input
          placeholder="Buscar..."
          value={terminoBusqueda}
          onChange={(e) => { setTerminoBusqueda(e.target.value); setPagina(0) }}
          className="max-w-sm"
        />
      )}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columnas.map((col) => (
                <TableHead key={col.key} className={col.className}>
                  {col.sortable ? (
                    <Button variant="ghost" size="sm" className="-ml-3 h-8" onClick={() => toggleOrden(col.key)}>
                      {col.header}
                      {ordenColumna === col.key ? (
                        ordenDir === 'asc' ? <ArrowUp className="ml-1 h-3 w-3" /> : <ArrowDown className="ml-1 h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="ml-1 h-3 w-3 opacity-50" />
                      )}
                    </Button>
                  ) : (
                    col.header
                  )}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {datosPagina.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columnas.length} className="h-24 text-center text-muted-foreground">
                  {vacio ?? 'Sin resultados'}
                </TableCell>
              </TableRow>
            ) : (
              datosPagina.map((item, idx) => (
                <TableRow
                  key={item.id ?? idx}
                  className={onClickFila ? 'cursor-pointer hover:bg-muted/50' : ''}
                  onClick={() => onClickFila?.(item)}
                >
                  {columnas.map((col) => (
                    <TableCell key={col.key} className={col.className}>
                      {col.render(item)}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {totalPaginas > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {datosFiltrados.length} registros
          </span>
          <div className="flex gap-1">
            <Button variant="outline" size="sm" disabled={pagina === 0} onClick={() => setPagina(pagina - 1)}>
              Anterior
            </Button>
            <span className="flex items-center px-3 text-sm text-muted-foreground">
              {pagina + 1} / {totalPaginas}
            </span>
            <Button variant="outline" size="sm" disabled={pagina >= totalPaginas - 1} onClick={() => setPagina(pagina + 1)}>
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
```

**Step 4: Page Header y Estado Vacio**

```typescript
// dashboard/src/components/page-header.tsx
interface PageHeaderProps {
  titulo: string
  descripcion?: string
  acciones?: React.ReactNode
}

export function PageHeader({ titulo, descripcion, acciones }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{titulo}</h1>
        {descripcion && <p className="text-muted-foreground mt-1">{descripcion}</p>}
      </div>
      {acciones && <div className="flex gap-2">{acciones}</div>}
    </div>
  )
}
```

```typescript
// dashboard/src/components/estado-vacio.tsx
import { FileText } from 'lucide-react'

interface EstadoVacioProps {
  titulo: string
  descripcion?: string
  icono?: React.ElementType
  accion?: React.ReactNode
}

export function EstadoVacio({ titulo, descripcion, icono: Icono = FileText, accion }: EstadoVacioProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Icono className="h-12 w-12 text-muted-foreground/50 mb-4" />
      <h3 className="text-lg font-medium">{titulo}</h3>
      {descripcion && <p className="text-sm text-muted-foreground mt-1 max-w-md">{descripcion}</p>}
      {accion && <div className="mt-4">{accion}</div>}
    </div>
  )
}
```

**Step 5: Commit**

```bash
git add dashboard/src/components/charts/ dashboard/src/components/data-table/ dashboard/src/components/page-header.tsx dashboard/src/components/estado-vacio.tsx dashboard/src/components/filter-bar.tsx
git commit -m "feat: componentes compartidos — KPICard, ChartCard, DataTable, PageHeader, EstadoVacio"
```

---

### Task A7: Tipos actualizados + estructura features + stubs Stream B

**Files:**
- Modify: `dashboard/src/types/index.ts` (ampliar tipos existentes)
- Create: `dashboard/src/features/auth/login-page.tsx`
- Create: `dashboard/src/features/not-found.tsx`
- Create: stubs para TODOS los features de Stream B (archivos minimos que exportan un componente placeholder para que el build no falle)

**Step 1: Actualizar tipos**

Ampliar `dashboard/src/types/index.ts` con los tipos adicionales que necesitan las paginas core. No tocar los existentes, agregar al final.

Agregar: PlanCuenta (arbol), MovimientoBancario, Pago, NominaResumen, CalendarioFiscalItem, OperacionPeriodica, y redefinir Factura con campos extra (cif_receptor, nombre_receptor, irpf_importe, recargo_importe, fecha_operacion, divisa, tasa_conversion).

**Step 2: Mover Login y NotFound a features/**

```typescript
// dashboard/src/features/auth/login-page.tsx
// Copiar contenido actual de pages/Login.tsx adaptando imports a @/
export default function LoginPage() { /* ... existente ... */ }
```

```typescript
// dashboard/src/features/not-found.tsx
export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
      <p className="text-muted-foreground mt-2">Pagina no encontrada</p>
    </div>
  )
}
```

**Step 3: Crear stubs para TODAS las paginas de Stream B**

Cada stub es un archivo minimo que exporta un componente placeholder:

```typescript
// Patron stub — para cada pagina de Stream B
// dashboard/src/features/economico/ratios-page.tsx (y los demas)
import { PageHeader } from '@/components/page-header'

export default function RatiosPage() {
  return <PageHeader titulo="Ratios Financieros" descripcion="En construccion — Stream B" />
}
```

Crear stubs para:
- `features/economico/` — ratios-page, kpis-page, tesoreria-page, centros-coste-page, presupuesto-real-page, comparativa-page, scoring-page, informes-page
- `features/portal/portal-page.tsx`
- `features/directorio/directorio-page.tsx`
- `features/configuracion/` — empresa-page, usuarios-page, integraciones-page, backup-page, licencia-page, apariencia-page
- `features/copilot/` (si hay ruta)

**Step 4: Verificar build completo**

Run: `cd dashboard && npx tsc --noEmit && npx vite build`
Expected: Build exitoso

**Step 5: Commit**

```bash
git add dashboard/src/types/ dashboard/src/features/
git commit -m "feat: tipos actualizados, features structure, stubs Stream B"
```

---

### Task A8: Home page — dashboard principal con KPIs y graficos

**Files:**
- Create: `dashboard/src/features/home/home-page.tsx`
- Create: `dashboard/src/features/home/selector-empresa.tsx`
- Delete: `dashboard/src/pages/Home.tsx`

**Descripcion:**
Grid de cards de empresas (existente) + KPIs principales cuando hay empresa activa:
- Ingresos mes, Gastos mes, Resultado, IVA pendiente, Facturas pendientes cobro, Facturas pendientes pago
- Grafico evolucion mensual ingresos vs gastos (AreaChart Recharts)
- Distribucion gastos por categoria (PieChart)
- Timeline actividad reciente
- Mini calendario obligaciones fiscales

Patron: useQuery con queryKeys, formatearImporte para valores, KPICard para metricas, ChartCard para graficos.

Usar datos reales de la API existente (`/api/contabilidad/{id}/pyg`, `/api/contabilidad/{id}/facturas`).

**Step 1: Implementar home-page.tsx con React Query + Recharts**

Al hacer click en una empresa card, setear `useEmpresaStore.setEmpresaActiva(empresa)` y navegar a la ruta de la empresa.

**Step 2: Verificar con dev server**

Run: `cd dashboard && npm run dev`
Navegar a localhost:3000, verificar que el home carga empresas y muestra KPIs.

**Step 3: Commit**

```bash
git add dashboard/src/features/home/
git commit -m "feat: home page — selector empresa, KPIs, graficos evolucion, actividad reciente"
```

---

### Task A9: Contabilidad — 8 paginas

**Files:**
- Create: `dashboard/src/features/contabilidad/pyg-page.tsx`
- Create: `dashboard/src/features/contabilidad/balance-page.tsx`
- Create: `dashboard/src/features/contabilidad/diario-page.tsx`
- Create: `dashboard/src/features/contabilidad/plan-cuentas-page.tsx`
- Create: `dashboard/src/features/contabilidad/conciliacion-page.tsx`
- Create: `dashboard/src/features/contabilidad/amortizaciones-page.tsx`
- Create: `dashboard/src/features/contabilidad/cierre-page.tsx`
- Create: `dashboard/src/features/contabilidad/apertura-page.tsx`
- Delete: `dashboard/src/pages/PyG.tsx`, `Balance.tsx`, `Diario.tsx`, `Activos.tsx`, `CierreEjercicio.tsx`, `Empresa.tsx`

**Patron por pagina:**

```typescript
// Ejemplo: pyg-page.tsx
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte, formatearPorcentaje, colorVariacion } from '@/lib/formatters'
import { PageHeader } from '@/components/page-header'
import { KPICard } from '@/components/charts/kpi-card'
import { ChartCard } from '@/components/charts/chart-card'
import { Card, CardContent } from '@/components/ui/card'
import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import type { PyG } from '@/types'

export default function PyGPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data: pyg, isLoading } = useQuery({
    queryKey: queryKeys.contabilidad.pyg(empresaId),
    queryFn: () => api.get<PyG>(`/api/contabilidad/${empresaId}/pyg`),
  })

  if (isLoading) return <PageHeader titulo="Cuenta de Resultados" descripcion="Cargando..." />
  if (!pyg) return <PageHeader titulo="Cuenta de Resultados" descripcion="Sin datos" />

  return (
    <div className="space-y-6">
      <PageHeader titulo="Cuenta de Resultados" descripcion="Perdidas y Ganancias del ejercicio" />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard titulo="Ingresos" valor={formatearImporte(pyg.ingresos)} icono={TrendingUp} />
        <KPICard titulo="Gastos" valor={formatearImporte(pyg.gastos)} icono={TrendingDown} />
        <KPICard titulo="Resultado" valor={formatearImporte(pyg.resultado)} icono={DollarSign} />
      </div>

      {/* Detalles ingresos/gastos en tablas expandibles + graficos */}
      {/* ... implementar segun design doc ... */}
    </div>
  )
}
```

**Implementar las 8 paginas siguiendo el patron anterior.**

Cada pagina:
1. useParams para empresaId
2. useQuery para fetch datos
3. PageHeader + KPICards + ChartCard con Recharts
4. DataTable donde aplique (diario, plan cuentas)
5. Skeleton loading via isLoading

**Paginas que necesitan endpoints API nuevos (backend existente puede no cubrirlos):**
- Plan de Cuentas: usar `/api/contabilidad/{id}/subcuentas` (puede necesitar endpoint nuevo — crear stub que retorne [])
- Conciliacion: necesita datos bancarios vs asientos (crear stub)
- Amortizaciones: reutiliza `/api/contabilidad/{id}/activos`
- Cierre: reutiliza endpoint existente
- Apertura: stub basico

**Step final: Commit por pagina o agrupado**

```bash
git add dashboard/src/features/contabilidad/
git commit -m "feat: contabilidad 8 paginas — PyG, Balance, Diario, Plan Cuentas, Conciliacion, Amortizaciones, Cierre, Apertura"
```

---

### Task A10: Facturacion — 5 paginas

**Files:**
- Create: `dashboard/src/features/facturacion/emitidas-page.tsx`
- Create: `dashboard/src/features/facturacion/recibidas-page.tsx`
- Create: `dashboard/src/features/facturacion/cobros-pagos-page.tsx`
- Create: `dashboard/src/features/facturacion/presupuestos-page.tsx`
- Create: `dashboard/src/features/facturacion/contratos-page.tsx`
- Delete: `dashboard/src/pages/Facturas.tsx`

**Patron:**
- Emitidas/Recibidas: DataTable con columnas (numero, fecha, cliente/proveedor, base, IVA, total, estado badge), filtros por fecha/estado, click abre detalle inline
- Cobros y Pagos: Aging analysis (4 buckets), waterfall chart, prevision
- Presupuestos/Contratos: stubs funcionales con DataTable basica

**Datos:** Reutilizar `/api/contabilidad/{id}/facturas` filtrando por tipo emitida/recibida.

**Step final: Commit**

```bash
git add dashboard/src/features/facturacion/
git commit -m "feat: facturacion 5 paginas — emitidas, recibidas, cobros/pagos, presupuestos, contratos"
```

---

### Task A11: Fiscal — 4 paginas

**Files:**
- Create: `dashboard/src/features/fiscal/calendario-page.tsx`
- Create: `dashboard/src/features/fiscal/modelos-page.tsx`
- Create: `dashboard/src/features/fiscal/generar-page.tsx`
- Create: `dashboard/src/features/fiscal/historico-page.tsx`
- Delete: `dashboard/src/pages/ModelosFiscales.tsx`, `GenerarModelo.tsx`, `HistoricoModelos.tsx`, `Calendario.tsx`

**Patron:**
- Calendario: vista mensual/trimestral con cards coloreadas por estado
- Modelos: catalogo con cards, badge estado
- Generar: formulario (React Hook Form + Zod), preview casillas, boton generar
- Historico: DataTable con descarga PDF/BOE

**Datos:** Reutilizar endpoints existentes `/api/modelos/*`.

**Step final: Commit**

```bash
git add dashboard/src/features/fiscal/
git commit -m "feat: fiscal 4 paginas — calendario, modelos, generar, historico"
```

---

### Task A12: Documentos — 4 paginas

**Files:**
- Create: `dashboard/src/features/documentos/inbox-page.tsx`
- Create: `dashboard/src/features/documentos/pipeline-page.tsx`
- Create: `dashboard/src/features/documentos/cuarentena-page.tsx`
- Create: `dashboard/src/features/documentos/archivo-page.tsx`
- Delete: `dashboard/src/pages/Inbox.tsx`, `Pipeline.tsx`, `Cuarentena.tsx`

**Patron:**
- Inbox: grid de cards + drag-and-drop zone upload
- Pipeline: barras de progreso por fase, WebSocket para tiempo real
- Cuarentena: DataTable con formulario inline de resolucion
- Archivo: DataTable con busqueda + preview PDF

**Datos:** Reutilizar endpoints existentes `/api/documentos/*`.

**Step final: Commit**

```bash
git add dashboard/src/features/documentos/
git commit -m "feat: documentos 4 paginas — inbox, pipeline, cuarentena, archivo"
```

---

### Task A13: RRHH — 2 paginas

**Files:**
- Create: `dashboard/src/features/rrhh/nominas-page.tsx`
- Create: `dashboard/src/features/rrhh/trabajadores-page.tsx`

**Patron:**
- Nominas: tabla mensual con desglose, grafico comparativa
- Trabajadores: DataTable + ficha expandible

**Datos:** `/api/empresas/{id}/trabajadores`

**Step final: Commit**

```bash
git add dashboard/src/features/rrhh/
git commit -m "feat: rrhh 2 paginas — nominas, trabajadores"
```

---

### Task A14: Borrar paginas antiguas + limpiar imports

**Files:**
- Delete: todos los archivos en `dashboard/src/pages/`
- Delete: `dashboard/src/components/EmpresaCard.tsx`
- Delete: `dashboard/src/api/client.ts`
- Delete: `dashboard/src/hooks/useApi.ts`
- Verify: `dashboard/src/hooks/useWebSocket.ts` (mantener si se usa)

**Step 1: Borrar directorio pages/ completo**

```bash
rm -rf dashboard/src/pages/
rm dashboard/src/api/client.ts dashboard/src/hooks/useApi.ts dashboard/src/components/EmpresaCard.tsx
```

**Step 2: Verificar build**

Run: `cd dashboard && npx tsc --noEmit && npx vite build`
Expected: Build exitoso

**Step 3: Commit**

```bash
git add -u
git commit -m "refactor: eliminar paginas y componentes antiguos pre-rewrite"
```

---

### Task A15: Dark mode + tema

**Files:**
- Modify: `dashboard/src/main.tsx` (efecto tema)
- Modify: `dashboard/src/index.css` (variables dark mode)

**Step 1: Implementar efecto tema en main.tsx o en AppShell**

Leer `useUIStore.tema` y aplicar clase `dark` al `<html>`. Si `system`, usar `window.matchMedia`.

**Step 2: Verificar dark mode toggle funciona**

**Step 3: Commit**

```bash
git add dashboard/src/
git commit -m "feat: dark mode completo con toggle en header"
```

---

### Task A16: Verificacion final Stream A

**Step 1: Build completo**

Run: `cd dashboard && npm run build`
Expected: Build exitoso, 0 errores TypeScript

**Step 2: Verificacion visual**

Arrancar dev server + API, navegar todas las rutas, verificar que cargan.

**Step 3: Commit final**

```bash
git add -A
git commit -m "feat: stream A completo — foundation + 23 paginas core dashboard rewrite"
```

---

## STREAM B: Backend Extensions + Features Avanzadas

### Task B1: Nuevas tablas BD

**Files:**
- Modify: `sfce/db/modelos.py` (agregar 8 tablas al final)

**Step 1: Agregar tablas nuevas**

Agregar al final de `sfce/db/modelos.py` (DESPUES de las 16 tablas existentes, sin modificarlas):

```python
# --- Tablas nuevas para dashboard rewrite ---

class Presupuesto(Base):
    """Presupuesto anual por partida contable."""
    __tablename__ = "presupuestos"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    ejercicio = Column(String(4), nullable=False)
    subcuenta = Column(String(20), nullable=False)
    descripcion = Column(String(200))
    importe_mensual = Column(JSON)  # {"01": 1000, "02": 1000, ...}
    importe_total = Column(Float, default=0)
    fecha_creacion = Column(DateTime, server_default=func.now())


class CentroCoste(Base):
    """Centro de coste (departamento, proyecto, sucursal)."""
    __tablename__ = "centros_coste"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    tipo = Column(String(50))  # departamento | proyecto | sucursal | obra
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())


class AsignacionCoste(Base):
    """Asignacion de gasto a centro de coste."""
    __tablename__ = "asignaciones_coste"

    id = Column(Integer, primary_key=True)
    centro_id = Column(Integer, ForeignKey("centros_coste.id"), nullable=False)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    porcentaje = Column(Float, default=100)
    fecha_asignacion = Column(DateTime, server_default=func.now())


class ScoringHistorial(Base):
    """Historial de scoring de clientes/proveedores."""
    __tablename__ = "scoring_historial"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    entidad_tipo = Column(String(20))  # proveedor | cliente
    entidad_id = Column(Integer, nullable=False)
    puntuacion = Column(Integer)  # 0-100
    factores = Column(JSON)
    fecha = Column(DateTime, server_default=func.now())


class CopilotConversacion(Base):
    """Conversacion del copiloto IA."""
    __tablename__ = "copilot_conversaciones"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, nullable=False)
    titulo = Column(String(200))
    mensajes = Column(JSON, default=[])  # [{rol, contenido, timestamp}]
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, server_default=func.now())


class CopilotFeedback(Base):
    """Feedback del usuario sobre respuestas del copiloto."""
    __tablename__ = "copilot_feedback"

    id = Column(Integer, primary_key=True)
    conversacion_id = Column(Integer, ForeignKey("copilot_conversaciones.id"), nullable=False)
    mensaje_idx = Column(Integer, nullable=False)
    valoracion = Column(Integer)  # 1 (dislike) | 5 (like)
    correccion = Column(Text)
    fecha = Column(DateTime, server_default=func.now())


class InformeProgramado(Base):
    """Informe programado para generacion automatica."""
    __tablename__ = "informes_programados"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(200), nullable=False)
    plantilla = Column(String(50))  # mensual | trimestral | anual | adhoc
    secciones = Column(JSON)  # ["pyg", "balance", "ratios", ...]
    periodicidad = Column(String(20))  # mensual | trimestral | anual | manual
    email_destino = Column(String(200))
    activo = Column(Boolean, default=True)
    ultimo_generado = Column(DateTime)
    fecha_creacion = Column(DateTime, server_default=func.now())


class VistaUsuario(Base):
    """Vista personalizada de filtros guardada por usuario."""
    __tablename__ = "vistas_usuario"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, nullable=False)
    pagina = Column(String(100), nullable=False)  # ej: "facturas-emitidas"
    nombre = Column(String(100), nullable=False)
    filtros = Column(JSON, default={})
    columnas = Column(JSON)  # columnas visibles y orden
    es_default = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, server_default=func.now())
```

NOTA: Asegurar los imports necesarios (Column, Integer, String, Float, Boolean, Text, DateTime, JSON, ForeignKey, func) ya esten en el archivo.

**Step 2: Verificar que las tablas se crean correctamente**

Run: `cd /c/Users/carli/PROYECTOS/CONTABILIDAD && python -c "from sfce.db.modelos import *; print('OK')"

**Step 3: Commit**

```bash
git add sfce/db/modelos.py
git commit -m "feat: 8 tablas nuevas BD — presupuestos, centros coste, scoring, copilot, informes, vistas"
```

---

### Task B2: Schemas Pydantic nuevos

**Files:**
- Modify: `sfce/api/schemas.py` (agregar al final)

**Step 1: Agregar schemas para modulo economico**

Agregar al final de `sfce/api/schemas.py`:

```python
# --- Economico-Financiero ---

class RatioOut(BaseModel):
    """Ratio financiero calculado."""
    nombre: str
    categoria: str  # liquidez | solvencia | rentabilidad | eficiencia | estructura
    valor: float
    unidad: str  # "ratio" | "porcentaje" | "dias" | "euros" | "veces"
    semaforo: str  # verde | amarillo | rojo
    benchmark: Optional[float] = None
    evolucion: list[dict] = []  # [{mes, valor}]
    explicacion: str = ""

class RatiosEmpresaOut(BaseModel):
    """Todos los ratios de una empresa."""
    empresa_id: int
    fecha_calculo: str
    ratios: list[RatioOut]

class KPIOut(BaseModel):
    """KPI sectorial."""
    nombre: str
    valor: float
    objetivo: Optional[float] = None
    unidad: str
    semaforo: str
    evolucion: list[dict] = []

class TesoreriaOut(BaseModel):
    """Estado de tesoreria."""
    saldo_actual: float
    flujo_operativo: float
    flujo_inversion: float
    flujo_financiacion: float
    prevision_30d: float
    prevision_60d: float
    prevision_90d: float
    movimientos_recientes: list[dict] = []

class ScoringOut(BaseModel):
    """Credit scoring de entidad."""
    entidad_id: int
    nombre: str
    tipo: str
    puntuacion: int
    factores: dict = {}
    limite_sugerido: Optional[float] = None

class PresupuestoLineaOut(BaseModel):
    """Linea de presupuesto vs real."""
    subcuenta: str
    descripcion: str
    presupuestado: float
    real: float
    desviacion: float
    desviacion_pct: float
    semaforo: str

class ComparativaOut(BaseModel):
    """Comparativa interanual."""
    concepto: str
    valores: dict  # {"2023": 1000, "2024": 1200, ...}
    variacion: Optional[float] = None
    cagr: Optional[float] = None

# --- Copilot ---

class CopilotMensajeIn(BaseModel):
    """Mensaje del usuario al copiloto."""
    mensaje: str
    conversacion_id: Optional[int] = None

class CopilotRespuestaOut(BaseModel):
    """Respuesta del copiloto."""
    conversacion_id: int
    respuesta: str
    datos_enriquecidos: Optional[dict] = None  # tablas, charts, links
    funciones_invocadas: list[str] = []

class CopilotFeedbackIn(BaseModel):
    """Feedback sobre respuesta del copiloto."""
    conversacion_id: int
    mensaje_idx: int
    valoracion: int  # 1 o 5
    correccion: Optional[str] = None

# --- Configuracion ---

class ConfigAparienciaIn(BaseModel):
    """Configuracion de apariencia."""
    tema: str = "system"  # light | dark | system
    densidad: str = "comoda"
    idioma: str = "es"
    formato_fecha: str = "dd/MM/yyyy"
    formato_numero: str = "es-ES"

class BackupOut(BaseModel):
    """Informacion de backup."""
    id: str
    fecha: str
    tamano: str
    tipo: str  # manual | automatico
```

**Step 2: Commit**

```bash
git add sfce/api/schemas.py
git commit -m "feat: schemas pydantic — economico, copilot, configuracion"
```

---

### Task B3: Endpoints API nuevos — economico

**Files:**
- Create: `sfce/api/rutas/economico.py`
- Modify: `sfce/api/app.py` (registrar router)

**Step 1: Router economico**

```python
# sfce/api/rutas/economico.py
"""Endpoints del modulo economico-financiero."""

from fastapi import APIRouter, Depends, Request
from sfce.api.auth import obtener_usuario_actual
from sfce.api.schemas import RatiosEmpresaOut, TesoreriaOut, ScoringOut
from sfce.api.app import get_sesion_factory

router = APIRouter(prefix="/api/economico", tags=["economico"])


@router.get("/{empresa_id}/ratios", response_model=RatiosEmpresaOut)
def obtener_ratios(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    """Calcula ratios financieros desde datos contables."""
    sesion_factory = request.app.state.sesion_factory
    # Calcular ratios desde partidas/asientos/facturas
    # Categorias: liquidez, solvencia, rentabilidad, eficiencia, estructura
    # Retornar con semaforo basado en benchmarks
    ...


@router.get("/{empresa_id}/kpis")
def obtener_kpis(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    """KPIs sectoriales basados en CNAE/IAE de la empresa."""
    ...


@router.get("/{empresa_id}/tesoreria", response_model=TesoreriaOut)
def obtener_tesoreria(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    """Estado de tesoreria con cash flow triple metodo."""
    ...


@router.get("/{empresa_id}/cashflow")
def obtener_cashflow(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    """Cash flow historico y proyeccion."""
    ...


@router.get("/{empresa_id}/scoring")
def obtener_scoring(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    """Credit scoring de clientes y proveedores."""
    ...


@router.get("/{empresa_id}/presupuesto")
def obtener_presupuesto(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    """Presupuesto vs real por partida."""
    ...


@router.get("/{empresa_id}/comparativa")
def obtener_comparativa(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    """Comparativa interanual de metricas clave."""
    ...
```

**Step 2: Registrar router en app.py**

Agregar en `crear_app()`:
```python
from sfce.api.rutas.economico import router as economico_router
app.include_router(economico_router)
```

**Step 3: Implementar logica de calculo de ratios**

La logica core: leer partidas/asientos de la empresa, calcular cada ratio segun formulas contables PGC:

- Liquidez corriente = Activo Corriente / Pasivo Corriente
- Acid test = (AC - Existencias) / PC
- ROE = Resultado Neto / Patrimonio Neto
- ROA = Resultado Neto / Activo Total
- Endeudamiento = Pasivo / (Pasivo + PN)
- PMC = (Clientes / Ventas) * 365
- PMP = (Proveedores / Compras) * 365

Agrupar subcuentas por rango PGC:
- Activo corriente: 3xx + 4300-4399 + 57xx
- Pasivo corriente: 4000-4099 + 5200-5299
- PN: 1xx
- Ventas: 70xx
- Compras: 60xx

**Step 4: Commit**

```bash
git add sfce/api/rutas/economico.py sfce/api/app.py
git commit -m "feat: API economico — ratios, kpis, tesoreria, cashflow, scoring, presupuesto, comparativa"
```

---

### Task B4: Endpoints API — copilot, configuracion, portal, informes

**Files:**
- Create: `sfce/api/rutas/copilot.py`
- Create: `sfce/api/rutas/configuracion.py`
- Create: `sfce/api/rutas/portal.py`
- Create: `sfce/api/rutas/informes.py`
- Modify: `sfce/api/app.py` (registrar routers)

**Step 1: Router copilot**

Endpoint principal: POST `/api/copilot/chat` que recibe mensaje + conversacion_id, consulta datos relevantes via function calling interno, genera respuesta con Claude API (usando ANTHROPIC_API_KEY del .env).

```python
# sfce/api/rutas/copilot.py
router = APIRouter(prefix="/api/copilot", tags=["copilot"])

@router.post("/chat", response_model=CopilotRespuestaOut)
def chat(body: CopilotMensajeIn, request: Request, user=Depends(obtener_usuario_actual)):
    """Enviar mensaje al copiloto IA."""
    ...

@router.post("/feedback")
def feedback(body: CopilotFeedbackIn, request: Request, _user=Depends(obtener_usuario_actual)):
    """Registrar feedback sobre respuesta."""
    ...

@router.get("/conversaciones/{empresa_id}")
def listar_conversaciones(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    """Historial de conversaciones."""
    ...
```

**Step 2: Router configuracion**

```python
# sfce/api/rutas/configuracion.py
router = APIRouter(prefix="/api/config", tags=["configuracion"])

@router.get("/apariencia")
def obtener_apariencia(request: Request, _user=Depends(obtener_usuario_actual)):
    ...

@router.put("/apariencia")
def actualizar_apariencia(body: ConfigAparienciaIn, request: Request, _user=Depends(obtener_usuario_actual)):
    ...

@router.get("/backup/listar")
def listar_backups(request: Request, _user=Depends(obtener_usuario_actual)):
    ...

@router.post("/backup/crear")
def crear_backup(request: Request, _user=Depends(obtener_usuario_actual)):
    ...

@router.post("/backup/restaurar/{backup_id}")
def restaurar_backup(backup_id: str, request: Request, _user=Depends(obtener_usuario_actual)):
    ...
```

**Step 3: Router portal**

```python
# sfce/api/rutas/portal.py
router = APIRouter(prefix="/api/portal", tags=["portal"])

@router.get("/{empresa_id}/resumen")
def resumen_portal(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    """Resumen simplificado para vista portal cliente."""
    ...

@router.get("/{empresa_id}/documentos")
def documentos_portal(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    ...
```

**Step 4: Router informes**

```python
# sfce/api/rutas/informes.py
router = APIRouter(prefix="/api/informes", tags=["informes"])

@router.post("/generar")
def generar_informe(request: Request, _user=Depends(obtener_usuario_actual)):
    ...

@router.get("/plantillas")
def listar_plantillas(request: Request, _user=Depends(obtener_usuario_actual)):
    ...

@router.get("/programados/{empresa_id}")
def listar_programados(empresa_id: int, request: Request, _user=Depends(obtener_usuario_actual)):
    ...
```

**Step 5: Registrar todos en app.py**

**Step 6: Commit**

```bash
git add sfce/api/rutas/copilot.py sfce/api/rutas/configuracion.py sfce/api/rutas/portal.py sfce/api/rutas/informes.py sfce/api/app.py
git commit -m "feat: API endpoints — copilot, configuracion, portal, informes"
```

---

### Task B5: Tipos TypeScript para Stream B

**Files:**
- Create: `dashboard/src/types/economico.ts`
- Create: `dashboard/src/types/copilot.ts`
- Create: `dashboard/src/types/config.ts`

**Step 1: Tipos economico**

```typescript
// dashboard/src/types/economico.ts
export interface Ratio {
  nombre: string
  categoria: 'liquidez' | 'solvencia' | 'rentabilidad' | 'eficiencia' | 'estructura'
  valor: number
  unidad: 'ratio' | 'porcentaje' | 'dias' | 'euros' | 'veces'
  semaforo: 'verde' | 'amarillo' | 'rojo'
  benchmark: number | null
  evolucion: { mes: string; valor: number }[]
  explicacion: string
}

export interface RatiosEmpresa {
  empresa_id: number
  fecha_calculo: string
  ratios: Ratio[]
}

export interface KPI {
  nombre: string
  valor: number
  objetivo: number | null
  unidad: string
  semaforo: 'verde' | 'amarillo' | 'rojo'
  evolucion: { mes: string; valor: number }[]
}

export interface Tesoreria {
  saldo_actual: number
  flujo_operativo: number
  flujo_inversion: number
  flujo_financiacion: number
  prevision_30d: number
  prevision_60d: number
  prevision_90d: number
  movimientos_recientes: { fecha: string; concepto: string; importe: number; saldo: number }[]
}

export interface ScoringEntidad {
  entidad_id: number
  nombre: string
  tipo: 'proveedor' | 'cliente'
  puntuacion: number
  factores: Record<string, number>
  limite_sugerido: number | null
}

export interface PresupuestoLinea {
  subcuenta: string
  descripcion: string
  presupuestado: number
  real: number
  desviacion: number
  desviacion_pct: number
  semaforo: 'verde' | 'amarillo' | 'rojo'
}

export interface ComparativaItem {
  concepto: string
  valores: Record<string, number>
  variacion: number | null
  cagr: number | null
}
```

**Step 2: Tipos copilot**

```typescript
// dashboard/src/types/copilot.ts
export interface MensajeCopilot {
  rol: 'usuario' | 'asistente'
  contenido: string
  timestamp: string
  datos_enriquecidos?: {
    tablas?: { titulo: string; filas: Record<string, unknown>[] }[]
    charts?: { tipo: string; datos: unknown }[]
    links?: { texto: string; ruta: string }[]
    acciones?: { texto: string; accion: string }[]
  }
}

export interface ConversacionCopilot {
  id: number
  empresa_id: number
  titulo: string
  mensajes: MensajeCopilot[]
  fecha_creacion: string
}
```

**Step 3: Tipos config**

```typescript
// dashboard/src/types/config.ts
export interface ConfigApariencia {
  tema: 'light' | 'dark' | 'system'
  densidad: 'compacta' | 'comoda'
  idioma: string
  formato_fecha: string
  formato_numero: string
}

export interface Backup {
  id: string
  fecha: string
  tamano: string
  tipo: 'manual' | 'automatico'
}
```

**Step 4: Commit**

```bash
git add dashboard/src/types/economico.ts dashboard/src/types/copilot.ts dashboard/src/types/config.ts
git commit -m "feat: tipos TypeScript — economico, copilot, config"
```

---

### Task B6: Paginas Economico-Financiero — 8 paginas

**Files:**
- Rewrite stubs: `dashboard/src/features/economico/ratios-page.tsx`
- Y los demas 7 archivos del modulo economico

**Patron por pagina:**

Cada pagina importa componentes compartidos de Stream A (`@/components/charts/kpi-card`, `@/components/charts/chart-card`, `@/components/data-table/data-table`, `@/components/page-header`) y usa React Query + api client.

**Ratios Financieros (pagina mas compleja):**
- 5 secciones (Liquidez, Solvencia, Rentabilidad, Eficiencia, Estructura)
- Cada ratio: KPICard con semaforo + sparkline
- Comparativa con benchmark sectorial (BarChart horizontal)
- Detalle por ratio con explicacion textual

**KPIs Sectoriales:**
- Deteccion sector desde empresa.cnae
- Cards con KPIs sectoriales + objetivo configurable
- Graficos de evolucion mensual

**Tesoreria:**
- Cash flow triple metodo (3 KPICards)
- AreaChart prevision con zona incertidumbre
- Tabla movimientos recientes

**Centros de Coste:**
- CRUD centros (formulario modal)
- PyG por centro
- BarChart comparativa entre centros

**Presupuesto vs Real:**
- DataTable: subcuenta, presupuestado, real, desviacion, semaforo
- LineChart acumulado presupuesto vs real

**Comparativa Interanual:**
- Selector de ejercicios (2-5)
- Tabla concepto + valor por ejercicio + variacion
- BarChart agrupado por partida
- CAGR automatico

**Credit Scoring:**
- DataTable entidades con puntuacion, semaforo, limite sugerido
- Chart radar con factores por entidad seleccionada

**Informes PDF:**
- Selector plantilla + secciones
- Preview del informe
- Boton generar + descargar

**Step final: Commit por pagina o agrupado**

```bash
git add dashboard/src/features/economico/
git commit -m "feat: economico-financiero 8 paginas — ratios, kpis, tesoreria, centros coste, presupuesto, comparativa, scoring, informes"
```

---

### Task B7: Configuracion — 6 paginas

**Files:**
- Rewrite stubs: `dashboard/src/features/configuracion/*.tsx` (6 archivos)

**Empresa:** Formulario datos fiscales con React Hook Form + Zod
**Usuarios y Roles:** DataTable usuarios + modal crear/editar + selector rol
**Integraciones:** Cards con estado conexion (FS, OCR APIs, email IMAP)
**Backup:** Lista backups + crear manual + restaurar
**Licencia:** Estado licencia, modulos, max empresas (read-only card)
**Apariencia:** Formulario tema/densidad/idioma/formatos con preview

**Step final: Commit**

```bash
git add dashboard/src/features/configuracion/
git commit -m "feat: configuracion 6 paginas — empresa, usuarios, integraciones, backup, licencia, apariencia"
```

---

### Task B8: Directorio — rewrite

**Files:**
- Rewrite stub: `dashboard/src/features/directorio/directorio-page.tsx`

**Funcionalidad:**
- DataTable con CIF, nombre, tipo persona, pais, validaciones
- Buscador con autocompletado
- Formulario crear/editar (modal, React Hook Form + Zod)
- Badge validacion AEAT/VIES
- Ficha detalle expandible (historico facturas, scoring, notas)

**Datos:** Reutilizar endpoints existentes `/api/directorio/*`

**Step final: Commit**

```bash
git add dashboard/src/features/directorio/
git commit -m "feat: directorio rewrite — busqueda, CRUD, validaciones, ficha detalle"
```

---

### Task B9: Portal Cliente

**Files:**
- Rewrite stub: `dashboard/src/features/portal/portal-page.tsx`

**Funcionalidad:**
- Vista reducida: PyG simplificado, facturas propias, calendario fiscal, documentos
- Subir documentos (drag & drop)
- Descargar informes y modelos

**Datos:** Endpoints `/api/portal/{empresa_id}/*`

**Step final: Commit**

```bash
git add dashboard/src/features/portal/
git commit -m "feat: portal cliente — vista reducida, upload docs, descargas"
```

---

### Task B10: Copiloto IA — chat integrado

**Files:**
- Create: `dashboard/src/features/copilot/copilot-panel.tsx`
- Create: `dashboard/src/features/copilot/copilot-message.tsx`
- Create: `dashboard/src/features/copilot/copilot-input.tsx`
- Create: `dashboard/src/hooks/use-copilot.ts`

**Funcionalidad:**
- Panel lateral deslizante (Sheet de shadcn/ui, 400px)
- Input con placeholder contextual
- Mensajes con soporte de tablas/charts/links/acciones inline
- Historial persistente (React Query + API)
- Botones like/dislike en cada respuesta
- Streaming de respuesta (SSE o polling)

**Patron:**

```typescript
// dashboard/src/hooks/use-copilot.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { ConversacionCopilot, MensajeCopilot } from '@/types/copilot'

export function useCopilot(empresaId: number) {
  const queryClient = useQueryClient()

  const enviarMensaje = useMutation({
    mutationFn: (mensaje: string) => api.post<{ respuesta: string; conversacion_id: number }>(
      '/api/copilot/chat',
      { mensaje, empresa_id: empresaId }
    ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['copilot', empresaId] })
    },
  })

  return { enviarMensaje }
}
```

**Step final: Commit**

```bash
git add dashboard/src/features/copilot/ dashboard/src/hooks/use-copilot.ts
git commit -m "feat: copiloto IA — panel chat, mensajes enriquecidos, feedback, historial"
```

---

### Task B11: Integrar copilot panel en AppShell

**NOTA: Esta task requiere coordinacion con Stream A.**

Stream B modifica `dashboard/src/components/layout/app-shell.tsx` para agregar el CopilotPanel condicional.

**Opcion sin conflicto:** Stream B crea un wrapper component que AppShell importa:

```typescript
// dashboard/src/features/copilot/copilot-wrapper.tsx
import { useUIStore } from '@/stores/ui-store'
import { useEmpresaStore } from '@/stores/empresa-store'
import { lazy, Suspense } from 'react'
import { Sheet, SheetContent } from '@/components/ui/sheet'

const CopilotPanel = lazy(() => import('./copilot-panel'))

export function CopilotWrapper() {
  const copilotAbierto = useUIStore((s) => s.copilotAbierto)
  const toggleCopilot = useUIStore((s) => s.toggleCopilot)
  const empresaActiva = useEmpresaStore((s) => s.empresaActiva)

  if (!empresaActiva) return null

  return (
    <Sheet open={copilotAbierto} onOpenChange={toggleCopilot}>
      <SheetContent side="right" className="w-[400px] p-0">
        <Suspense fallback={<div className="p-4">Cargando copiloto...</div>}>
          <CopilotPanel empresaId={empresaActiva.id} />
        </Suspense>
      </SheetContent>
    </Sheet>
  )
}
```

Y despues del merge, agregar `<CopilotWrapper />` al final de AppShell.

**Step final: Commit**

```bash
git add dashboard/src/features/copilot/copilot-wrapper.tsx
git commit -m "feat: copilot wrapper para integracion en AppShell"
```

---

### Task B12: Verificacion final Stream B

**Step 1: Backend — tests basicos**

Run: `cd /c/Users/carli/PROYECTOS/CONTABILIDAD && python -c "from sfce.api.app import crear_app; app = crear_app(); print('OK')"
Expected: Sin errores de import

**Step 2: Frontend build**

Run: `cd dashboard && npx tsc --noEmit && npx vite build`
Expected: Build exitoso

**Step 3: Commit final**

```bash
git add -A
git commit -m "feat: stream B completo — backend economico/copilot/config + 16 paginas avanzadas"
```

---

## MERGE FINAL

### Task M1: Merge ambos streams

**Step 1: Merge branches**

Si cada stream trabaja en branch diferente:
```bash
git checkout feat/dashboard-stream-a
git merge feat/dashboard-stream-b
```

Si trabajan en la misma branch con worktrees, hacer merge de worktrees.

**Step 2: Resolver conflictos**

Archivos potencialmente conflictivos:
- `dashboard/src/components/layout/app-shell.tsx` — agregar CopilotWrapper
- `sfce/api/app.py` — ya tiene todos los routers de ambos streams (Stream B los agrego)

**Step 3: Build final + test manual**

Run:
```bash
cd dashboard && npm run build
cd .. && python -c "from sfce.api.app import crear_app; print('OK')"
```

**Step 4: Commit de merge**

```bash
git commit -m "feat: merge streams A+B — dashboard rewrite 38 paginas completo"
```

---

## Resumen de paginas por stream

| Stream | Feature | Paginas | Total |
|--------|---------|---------|-------|
| A | Home | 1 | 1 |
| A | Contabilidad | PyG, Balance, Diario, Plan Cuentas, Conciliacion, Amortizaciones, Cierre, Apertura | 8 |
| A | Facturacion | Emitidas, Recibidas, Cobros/Pagos, Presupuestos, Contratos | 5 |
| A | Fiscal | Calendario, Modelos, Generar, Historico | 4 |
| A | Documentos | Inbox, Pipeline, Cuarentena, Archivo | 4 |
| A | RRHH | Nominas, Trabajadores | 2 |
| **A Total** | | | **24** |
| B | Economico | Ratios, KPIs, Tesoreria, Centros Coste, Presupuesto vs Real, Comparativa, Scoring, Informes | 8 |
| B | Configuracion | Empresa, Usuarios, Integraciones, Backup, Licencia, Apariencia | 6 |
| B | Portal | Vista Cliente | 1 |
| B | Directorio | Directorio Global | 1 |
| B | Copiloto IA | Chat Panel | (integrado, no ruta propia) |
| **B Total** | | | **16** |
| **TOTAL** | | | **40** |

## Dependencias entre streams

```
Stream A (A1-A6) ──────> Stream A (A7-A15) ─────> Task M1 (merge)
    ↓                                                  ↑
    ↓ (shadcn/ui, DataTable,                          │
    ↓  ChartCard, PageHeader                          │
    ↓  disponibles en @/components/)                  │
    ↓                                                  │
Stream B (B1-B5) backend ──> Stream B (B6-B12) ──────┘
     no necesita nada           necesita @/components/ de A
     de Stream A                (ya estaran creados)
```

**Regla:** Stream B empieza por backend (B1-B5) que NO necesita nada de Stream A. Para cuando Stream B llega a B6 (paginas frontend), Stream A ya habra completado A1-A6 (foundation + componentes compartidos).
