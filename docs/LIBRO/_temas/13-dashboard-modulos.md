# 13 — Dashboard: Los 21 Módulos

> **Estado:** COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes:** `dashboard/src/features/`, `dashboard/vite.config.ts`, `dashboard/src/`

---

## Stack tecnológico

| Librería | Versión aprox | Uso |
|----------|---------------|-----|
| React | 18 | UI framework |
| TypeScript | strict mode | Tipado |
| Vite | 6 | Bundler + dev server |
| Tailwind CSS | v4 | Estilos utilitarios |
| shadcn/ui | latest | Componentes UI accesibles |
| Recharts | latest | Gráficas (AreaChart, PieChart, BarChart) |
| TanStack Query | v5 | Server state, caché, invalidación |
| Zustand | latest | Client state (empresa activa, auth) |
| @tanstack/react-virtual | latest | Virtualización de listas largas |
| vite-plugin-pwa | latest | PWA + Service Worker Workbox |
| DOMPurify | latest | Sanitización HTML antes de renderizar |
| React Router DOM | v6 | Enrutamiento SPA |
| lucide-react | latest | Iconos |

---

## PWA

Configurado en `vite.config.ts` con `vite-plugin-pwa`.

**Manifest:**

- Nombre completo: `SPICE — Sistema Fiscal Contable`
- Short name: `SPICE`
- Display: `standalone` (sin chrome del navegador)
- Theme color: `#1e293b`
- Iconos: SVG 192x192 y SVG 512x512 en `/icons/icon-192.svg` y `/icons/icon-512.svg`, marcados como `any maskable`

**Service Worker Workbox — estrategias de caché:**

| Patrón de URL | Estrategia | Cache | TTL |
|--------------|-----------|-------|-----|
| `/api/**` | NetworkFirst | `api-cache` | 5 minutos, 100 entradas |
| `*.png/jpg/svg/gif/webp/ico` | CacheFirst | `images-cache` | 30 días, 60 entradas |
| `*.woff2/ttf/otf/eot` | CacheFirst | `fonts-cache` | 365 días, 20 entradas |
| Navegación (HTML) | navigateFallback | precache | `index.html` |

- `navigateFallbackDenylist: [/^\/api\//]` — las rutas de API nunca usan el fallback HTML.
- `cleanupOutdatedCaches: true` — elimina caches de versiones anteriores en cada update.
- `registerType: 'autoUpdate'` — el SW se actualiza automáticamente sin pedir confirmación al usuario.
- 86 entradas precacheadas en el build de producción.

**Página offline:** `dashboard/src/features/offline/` — mostrada por el SW cuando la navegación falla y `index.html` no está en caché.

---

## Seguridad frontend

**JWT en sessionStorage:**

El token JWT se guarda en `sessionStorage` (no `localStorage`). Diferencias clave:

- No persiste entre pestañas del mismo navegador
- Se borra automáticamente al cerrar la pestaña o el navegador
- No accesible desde iframes de otros orígenes

**Idle timer — logout automático:**

30 minutos de inactividad disparan el logout. Eventos monitorizados:

```ts
['mousedown', 'keydown', 'touchstart', 'scroll']
```

El timer se reinicia con cada uno de estos eventos. Al expirar, borra sessionStorage y redirige a `/login`.

**DOMPurify:**

Cualquier HTML recibido de la API (p. ej. contenido de correos, notas de documentos) se sanitiza antes de pasar a `dangerouslySetInnerHTML`:

```ts
import DOMPurify from 'dompurify'
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />
```

**Eliminación de console.log en producción:**

`vite.config.ts` usa `esbuild.drop: ['console', 'debugger']`. En el bundle de producción no existe ningún `console.*` ni `debugger`.

---

## Tabla de los 21 módulos

Directorios reales en `dashboard/src/features/` más `not-found.tsx`:

| Módulo | Ruta URL | Feature dir | Descripción |
|--------|----------|-------------|-------------|
| Home | `/` o `/empresa/:id` | `home/` | Sin empresa activa → `<SelectorEmpresa />`. Con id → KPIs empresa (PyG, facturas recientes) |
| Auth | `/login` | `auth/` | Login + validación 2FA TOTP (flujo 202 + temp_token) |
| Onboarding | `/onboarding` | `onboarding/` | Alta interactiva de empresa nueva |
| Contabilidad | `/empresa/:id/diario` | `contabilidad/` | Libro diario, asientos, partidas |
| Económico | `/empresa/:id/pyg` | `economico/` | PyG, balance, ratios financieros, presupuesto vs. real |
| Fiscal | `/empresa/:id/fiscal` | `fiscal/` | Modelos fiscales (303, 111, 130...), calendario vencimientos |
| Facturación | `/empresa/:id/facturas` | `facturacion/` | FC y FV con filtros por tipo/estado/fecha, exportar |
| Bancario / Conciliación | `/empresa/:id/bancario` | `conciliacion/` | Subir extractos, tabla movimientos, motor conciliación |
| Documentos | `/empresa/:id/documentos` | `documentos/` | Pipeline docs, estados (ok/cuarentena/pendiente) |
| Colas | `/empresa/:id/colas` | `colas/` | Cola Gate 0, revisión de pendientes con scoring |
| Correo | `/empresa/:id/correo` | `correo/` | Cuentas IMAP, emails clasificados automáticamente |
| Directorio | `/directorio` | `directorio/` | Entidades globales, búsqueda paginada, validación AEAT/VIES |
| RRHH | `/empresa/:id/rrhh` | `rrhh/` | Trabajadores, nóminas |
| Copiloto IA | `/empresa/:id/copilot` | `copilot/` | Chat IA con historial y feedback |
| Configuración | `/empresa/:id/config` | `configuracion/` | Config empresa, proveedores, reglas clasificación |
| Portal cliente | `/portal/:id` | `portal/` | Vista del cliente final (sin sidebar gestoría) con KPIs y descarga RGPD |
| Notificaciones | topbar (panel deslizante) | `notificaciones/` | Panel Web Push, suscripción VAPID, listado alertas |
| Salud | `/salud` | `salud/` | Health check del sistema (API, BD, workers) |
| Offline | SW navigateFallback | `offline/` | Página sin conexión mostrada por el Service Worker |
| OmniSearch | barra superior | `omnisearch/` | Búsqueda global en tiempo real entre empresas, facturas, docs |
| 404 | `*` | `not-found.tsx` | Página no encontrada |

---

## Arquitectura del dashboard

**Feature-based:** cada módulo vive en su propio directorio bajo `dashboard/src/features/`. Convención:

```
features/
  facturacion/
    index.tsx          # export default lazy
    facturas-page.tsx  # componente de página
    api.ts             # llamadas a la API para este módulo
    components/        # componentes internos del módulo
    hooks/             # hooks del módulo
    types.ts           # tipos locales
```

**Lazy loading:** todos los módulos de página se cargan con `React.lazy` + `Suspense`. El bundle inicial es mínimo; cada módulo se descarga al navegar.

**Path alias `@/`:** configurado en `vite.config.ts`:

```ts
resolve: {
  alias: { '@': path.resolve(__dirname, './src') }
}
```

Permite `import { api } from '@/lib/api-client'` desde cualquier archivo sin rutas relativas.

**Stores Zustand:**

- `useEmpresaStore` — empresa activa (`empresaActiva`, `setEmpresaActiva`)
- `useAuthStore` — usuario autenticado, token JWT en sessionStorage

---

## Selector de empresa

Lógica en `dashboard/src/features/home/home-page.tsx`:

```ts
export default function HomePage() {
  const { id } = useParams<{ id: string }>()
  // Sin empresa en la URL → mostrar selector
  if (!id) return <SelectorEmpresa />
  return <DashboardEmpresa empresaId={Number(id)} />
}
```

El `<SelectorEmpresa />` está en `dashboard/src/features/home/selector-empresa.tsx`.

**Navegación al seleccionar empresa:**

```ts
navigate(`/empresa/${id}/pyg`)  // siempre a la ruta PyG, NO a /empresa/:id
```

Navegar a `/empresa/:id` sin subruta no tiene componente propio; el router redirige o renderiza Home de nuevo.

**AppShell — hidratación desde URL:**

Al acceder directamente a cualquier URL `/empresa/:id/*`, el AppShell extrae el `id` de los params de React Router y lo inyecta en el store de Zustand antes de renderizar el módulo. Así el sidebar, topbar y breadcrumbs muestran la empresa correcta aunque el usuario haya llegado por enlace directo sin pasar por el selector.

---

## Notas de desarrollo

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

El proxy WS (`/api/ws`) debe declararse antes del proxy HTTP (`/api`) porque Vite aplica el primero que coincide.

**Arrancar en desarrollo:**

```bash
# Backend
cd sfce && uvicorn sfce.api.app:crear_app --factory --port 8000

# Frontend (con proxy a :8000)
cd dashboard && npm run dev
```

El frontend sirve en `http://localhost:3000`. Nunca servir `dist/` directamente en desarrollo porque el SW de producción intercepta las llamadas API antes de que lleguen al proxy.

**Build de producción:**

```bash
cd dashboard && npm run build
```

Genera `dist/` con:

- Assets con hash de contenido (cache busting automático)
- `dist/sw.js` — Service Worker con 86 entradas precacheadas
- `dist/manifest.webmanifest` — manifiesto PWA
- `console.*` y `debugger` eliminados por esbuild

**uvicorn + Windows — WinError 6:**

`uvicorn --reload` falla con `WinError 6` si hay conexiones WebSocket activas cuando se modifica un archivo Python. Reiniciar el servidor manualmente tras cambios en código Python. Ver capítulo 12 para detalles.
