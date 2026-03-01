# 13 — Dashboard: Módulos y Arquitectura

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes:** `dashboard/src/features/`, `dashboard/package.json`, `dashboard/src/index.css`

---

## Comandos rápidos

```bash
# Backend API
cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000

# Frontend (proxy automático a localhost:8000)
cd dashboard && npm run dev
# Sirve en http://localhost:3000

# Build producción
cd dashboard && npm run build
# → dist/ con 109 entradas precacheadas, build ~4.65s
```

Login por defecto: `admin@sfce.local` / `admin`

---

## Stack tecnológico

| Librería | Versión | Uso |
|----------|---------|-----|
| React | 18.3 | UI framework |
| TypeScript | 5.7 strict | Tipado |
| Vite | 6 | Bundler + dev server |
| Tailwind CSS | v4 | Estilos utilitarios |
| shadcn/ui | 3.8 | Componentes UI accesibles (Radix primitives) |
| Recharts | 3.7 | Gráficas (AreaChart, PieChart, BarChart) |
| TanStack Query | v5 | Server state, caché, invalidación |
| Zustand | 5 | Client state (empresa activa, auth) |
| @tanstack/react-virtual | 3 | Virtualización de listas largas |
| React Router DOM | v7 | Enrutamiento SPA |
| React Hook Form + Zod | 7 + 4 | Formularios con validación |
| cmdk | 1.1 | Command palette (OmniSearch) |
| date-fns | 4 | Fechas |
| react-day-picker | 9 | Calendario UI |
| sonner | 2 | Toast notifications |
| DOMPurify | 3.3 | Sanitización HTML antes de renderizar |
| next-themes | 0.4 | Dark mode |
| vite-plugin-pwa | 1.2 | PWA + Service Worker Workbox |
| Inter | — | Fuente principal (Google Fonts) |
| lucide-react | 0.575 | Iconos |

---

## Arquitectura general

**Feature-based:** cada módulo vive en su propio directorio bajo `dashboard/src/features/`. Estructura tipo:

```
features/
  facturacion/
    index.tsx          # export default lazy
    facturas-page.tsx  # componente de página
    api.ts             # llamadas API del módulo
    components/        # componentes internos
    hooks/             # hooks del módulo
    types.ts           # tipos locales
```

**Lazy loading:** todos los módulos de página usan `React.lazy` + `Suspense`. Bundle inicial mínimo; cada módulo se descarga al navegar.

**Path alias `@/`:** configurado en `vite.config.ts`:

```ts
resolve: {
  alias: { '@': path.resolve(__dirname, './src') }
}
```

**Proxy Vite:**

```ts
server: {
  port: 3000,
  proxy: {
    '/api/ws': { target: 'ws://localhost:8000', ws: true },
    '/api':    { target: 'http://localhost:8000', changeOrigin: true },
  },
}
```

El proxy WS debe declararse antes del HTTP porque Vite aplica el primero que coincide.

**Stores Zustand:**

- `useEmpresaStore` — empresa activa (`empresaActiva`, `setEmpresaActiva`)
- `useAuthStore` — usuario autenticado, token JWT en sessionStorage

---

## Tema visual

**Paleta ámbar OKLCh** — inspirada en Claude.ai, dark-first. Tokens en `dashboard/src/index.css`.

Variables clave:

| Token | Valor (light) | Uso |
|-------|---------------|-----|
| `--primary` | `oklch(0.65 0.13 45)` | Acento principal ámbar |
| `--background` | `oklch(0.97 0.01 75)` | Fondo crema signature |
| `--sidebar` | `oklch(0.22 0.015 245)` dark | Sidebar dark slate/navy (h=245°) |
| `--chart-1..5` | Paleta ámbar cohesiva | Gráficas |

**Dark mode:** via `next-themes` + clase `.dark`. Sidebar siempre dark slate/navy (oklch h=245°) en ambos modos.

**Glassmorphism:** aplicado en cards y paneles flotantes.

**CHART_COLORS:** definidos en `dashboard/src/components/charts/chart-wrapper.tsx`.

---

## Tabla de módulos

Directorios en `dashboard/src/features/` (25 entradas incluye `not-found.tsx`):

| Módulo | Ruta URL | Feature dir | Estado | Descripción |
|--------|----------|-------------|--------|-------------|
| Home | `/` o `/empresa/:id` | `home/` | Completado | Sin empresa → `<SelectorEmpresa />`. Con id → KPI strip con tarjetas individuales + resumen empresa |
| Auth | `/login` | `auth/` | Completado | Login + 2FA TOTP (flujo 202 + temp_token) |
| Onboarding | `/onboarding` | `onboarding/` | Completado | Alta interactiva empresa nueva |
| Empresa | `/empresa/:id` | `empresa/` | Completado | AppShell por empresa, hidratación store desde URL |
| Económico / PyG | `/empresa/:id/pyg` | `economico/` | Completado | PyG, balance, ratios financieros |
| Contabilidad | `/empresa/:id/diario` | `contabilidad/` | Completado | Libro diario, asientos, partidas |
| Fiscal | `/empresa/:id/fiscal` | `fiscal/` | Completado | Modelos fiscales (303, 111, 130…), calendario vencimientos |
| Facturación | `/empresa/:id/facturas` | `facturacion/` | Completado | FC y FV con filtros tipo/estado/fecha |
| Bancario | `/empresa/:id/bancario` | `conciliacion/` | Completado | Extractos, movimientos, motor conciliación |
| Documentos / Bandeja | `/empresa/:id/documentos` | `documentos/` | Completado | Pipeline docs, estados (ok/cuarentena/pendiente) |
| Colas | `/empresa/:id/colas` | `colas/` | Completado | Cola Gate 0, revisión pendientes con scoring |
| Correo | `/empresa/:id/correo` | `correo/` | Completado | Cuentas IMAP, emails clasificados |
| RRHH | `/empresa/:id/rrhh` | `rrhh/` | Completado | Trabajadores, nóminas |
| Activos | — | incluido en `economico/` | Completado | Activos fijos |
| Directorio | `/directorio` | `directorio/` | Completado | Entidades globales, búsqueda paginada, validación AEAT/VIES |
| Copiloto IA | `/empresa/:id/copilot` | `copilot/` | Completado | Chat IA con historial y feedback |
| Configuración | `/empresa/:id/config` | `configuracion/` | Completado | 18 secciones: empresa, proveedores, reglas, usuarios… |
| Mi Gestoría | `/mi-gestoria` | `mi-gestoria/` | Completado | Panel admin gestoría (nivel gestor/admin) |
| Admin Gestorías | `/admin/gestorias` | `admin/` | Completado | Gestión gestorías (nivel superadmin) |
| Portal cliente | `/portal` | `portal/` | Completado | Índice multi-empresa + redirección automática si hay 1 |
| OmniSearch | barra superior | `omnisearch/` | Completado | Búsqueda global (cmdk) entre empresas, facturas, docs |
| Notificaciones | topbar deslizante | `notificaciones/` | Completado | Panel Web Push, suscripción VAPID, listado alertas |
| Salud | `/salud` | `salud/` | Completado | Health check API, BD, workers |
| Offline | SW navigateFallback | `offline/` | Completado | Página sin conexión |
| 404 | `*` | `not-found.tsx` | Completado | Página no encontrada |

---

## Componentes clave compartidos

| Componente | Ubicación | Descripción |
|------------|-----------|-------------|
| `AppShell` | `src/components/app-shell.tsx` | Layout raíz; hidrata store empresa desde URL |
| `AppSidebar` | `src/components/app-sidebar.tsx` | Sidebar rediseñado, dark slate/navy |
| `KPICard` | `src/components/kpi-card.tsx` | Tarjeta métrica con variación y tendencia |
| `EmptyState` | `src/components/empty-state.tsx` | Placeholder estado vacío |
| `PageTitle` | `src/components/page-title.tsx` | Cabecera de página estandarizada |
| `ChartWrapper` | `src/components/charts/chart-wrapper.tsx` | Wrapper Recharts con CHART_COLORS y tema |

---

## Keyboard shortcuts

Navegación rápida con dos teclas seguidas:

| Atajo | Destino |
|-------|---------|
| `G + C` | Contabilidad (diario) |
| `G + F` | Fiscal |
| `G + D` | Documentos |
| `G + E` | Económico (PyG) |
| `G + R` | RRHH |
| `G + H` | Home |

---

## Endpoints del dashboard implementados

| Endpoint | Datos que devuelve |
|----------|--------------------|
| `GET /api/empresas/estadisticas-globales` | Resumen global: total empresas, docs en bandeja, docs procesados, alertas activas (datos reales desde BD) |
| `GET /api/empresas/{id}/resumen` | Bandeja pendiente, asientos descuadrados, ventas YTD, ventas 6 meses. `fiscal.proximo_modelo` en null (requiere ServicioFiscal) |

---

## Home — KPI strip

El Home con empresa activa muestra un strip de KPIs con tarjetas individuales:

```ts
// home/home-page.tsx
export default function HomePage() {
  const { id } = useParams<{ id: string }>()
  if (!id) return <SelectorEmpresa />
  return <DashboardEmpresa empresaId={Number(id)} />
}
```

**Navegación al seleccionar empresa:**

```ts
navigate(`/empresa/${id}/pyg`)  // siempre a PyG, no a /empresa/:id raíz
```

**AppShell — hidratación desde URL:** al acceder directamente a `/empresa/:id/*`, el AppShell extrae el `id` de los params y lo inyecta en el store antes de renderizar. Sidebar, topbar y breadcrumbs muestran la empresa correcta sin pasar por el selector.

---

## Seguridad frontend

**JWT en sessionStorage:** no persiste entre pestañas, se borra al cerrar la pestaña, no accesible desde iframes de otros orígenes.

**Idle timer:** 30 minutos de inactividad disparan logout automático. Eventos monitorizados: `mousedown`, `keydown`, `touchstart`, `scroll`.

**DOMPurify:** cualquier HTML recibido de la API se sanitiza antes de `dangerouslySetInnerHTML`:

```ts
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />
```

**Eliminación console.log en producción:** `vite.config.ts` usa `esbuild.drop: ['console', 'debugger']`.

---

## PWA

Configurado con `vite-plugin-pwa` + Workbox.

**Manifest:**

- Nombre: `SPICE — Sistema Fiscal Contable` / short: `SPICE`
- Display: `standalone`
- Theme color: `#1e293b`
- Iconos: `/icons/icon-192.svg`, `/icons/icon-512.svg` (`any maskable`)

**Estrategias de caché Workbox:**

| Patrón URL | Estrategia | Cache | TTL |
|------------|-----------|-------|-----|
| `/api/**` | NetworkFirst | `api-cache` | 5 min, 100 entradas |
| `*.png/jpg/svg/gif/webp/ico` | CacheFirst | `images-cache` | 30 días, 60 entradas |
| `*.woff2/ttf/otf/eot` | CacheFirst | `fonts-cache` | 365 días, 20 entradas |
| Navegación HTML | navigateFallback | precache | `index.html` |

- `navigateFallbackDenylist: [/^\/api\//]` — rutas API nunca usan fallback HTML
- `registerType: 'autoUpdate'` — SW se actualiza automáticamente
- 109 entradas precacheadas en el build actual

**Pendiente:** activar `VITE_VAPID_PUBLIC_KEY` + endpoint `/api/notificaciones/suscribir` para push notifications.

---

## Build de producción

```bash
cd dashboard && npm run build
# Genera dist/ con:
# - Assets con hash de contenido (cache busting)
# - dist/sw.js — Service Worker (109 entradas precacheadas)
# - dist/manifest.webmanifest — manifiesto PWA
# - console.* y debugger eliminados por esbuild
# Tiempo: ~4.65s
```

**uvicorn + Windows — WinError 6:** `uvicorn --reload` falla con `WinError 6` si hay conexiones WebSocket activas al modificar un archivo Python. Reiniciar el servidor manualmente tras cambios Python. La opción `--reload` se puede omitir en desarrollo estable.

---

## Tests E2E

```bash
cd dashboard && npm run test:e2e
cd dashboard && npm run test:e2e:ui    # modo UI interactivo
cd dashboard && npm run test:e2e:debug # modo debug
```

Runner: Playwright (`@playwright/test` 1.58). Tests E2E del dashboard pendientes de implementar.
