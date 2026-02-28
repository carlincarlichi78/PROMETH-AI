# Frontend PWA + Seguridad + Portal + Notificaciones — Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convertir el dashboard SFCE en una PWA segura con portal cliente y notificaciones push.

**Architecture:** vite-plugin-pwa gestiona el service worker y el manifest. El JWT se mueve de localStorage a sessionStorage + memoria. El portal cliente tiene su propia ruta/layout fuera del AppShell. Las notificaciones push usan Web Push API con el service worker existente.

**Tech Stack:** React 18 + TypeScript + Vite 6 + Tailwind v4 + shadcn/ui + vite-plugin-pwa + DOMPurify + workbox

**Scope:** Solo `dashboard/` — no tocar `sfce/` ni raíz del proyecto.

**Rama:** `feat/frontend-pwa`

---

## Contexto del codebase

### Archivos clave
- `dashboard/vite.config.ts` — configuración Vite (sin PWA aún)
- `dashboard/index.html` — HTML raíz (sin meta PWA)
- `dashboard/src/context/AuthContext.tsx` — JWT en `localStorage` actualmente
- `dashboard/src/App.tsx` — router principal; portal en `/empresa/:id/portal` dentro de ProtectedRoute
- `dashboard/src/features/portal/portal-page.tsx` — portal básico, usa localStorage directamente
- `dashboard/package.json` — sin vite-plugin-pwa ni dompurify

### Estado actual del portal
El portal existe en `/empresa/:id/portal` dentro del AppShell (sidebar completo). Hay endpoints backend en `/api/portal/{id}/resumen` y `/api/portal/{id}/documentos` que requieren Bearer token.

### Nota httpOnly cookies
Los endpoints backend usan `Depends(obtener_usuario_actual)` que lee Bearer del header Authorization. Sin modificar `sfce/`, no podemos activar httpOnly cookies de verdad. La mejora será: **sessionStorage en vez de localStorage** (mejor que localStorage para XSS) + infraestructura `credentials: 'include'` documentada como TODO.

---

## Task 1: PWA — vite-plugin-pwa, manifest, service worker, offline page

**Files:**
- Modify: `dashboard/vite.config.ts`
- Modify: `dashboard/index.html`
- Create: `dashboard/public/manifest.json`
- Create: `dashboard/public/icons/icon-192.svg`
- Create: `dashboard/public/icons/icon-512.svg`
- Create: `dashboard/src/features/offline/offline-page.tsx`
- Create: `dashboard/src/sw-custom.ts` (custom SW additions)

### Step 1: Instalar vite-plugin-pwa

```bash
cd dashboard && npm install -D vite-plugin-pwa
```

### Step 2: Actualizar vite.config.ts

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'icons/*.svg'],
      manifest: {
        name: 'SPICE — Sistema Fiscal Contable',
        short_name: 'SPICE',
        description: 'Sistema Fiscal Contable Evolutivo para gestorías',
        theme_color: '#1e293b',
        background_color: '#ffffff',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          { src: '/icons/icon-192.svg', sizes: '192x192', type: 'image/svg+xml', purpose: 'any maskable' },
          { src: '/icons/icon-512.svg', sizes: '512x512', type: 'image/svg+xml', purpose: 'any maskable' },
        ],
      },
      workbox: {
        // Cache-first para assets estáticos
        runtimeCaching: [
          {
            urlPattern: /^https?.*\/api\//,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 10,
              expiration: { maxEntries: 100, maxAgeSeconds: 5 * 60 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'images-cache',
              expiration: { maxEntries: 60, maxAgeSeconds: 30 * 24 * 60 * 60 },
            },
          },
          {
            urlPattern: /\.(?:woff2?|ttf|otf|eot)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'fonts-cache',
              expiration: { maxEntries: 20, maxAgeSeconds: 365 * 24 * 60 * 60 },
            },
          },
        ],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
      },
      devOptions: { enabled: false },
    }),
  ],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    port: 3000,
    proxy: {
      '/api/ws': { target: 'ws://localhost:8000', ws: true },
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    // Eliminar console.log y debugger en producción
    minify: 'esbuild',
  },
  esbuild: {
    drop: ['console', 'debugger'],
  },
})
```

### Step 3: Actualizar index.html con meta PWA

```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/icons/icon-192.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#1e293b" />
    <meta name="description" content="Sistema Fiscal Contable Evolutivo" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="apple-mobile-web-app-title" content="SPICE" />
    <link rel="apple-touch-icon" href="/icons/icon-192.svg" />
    <link rel="manifest" href="/manifest.json" />
    <title>SPICE Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### Step 4: Crear iconos SVG

`public/icons/icon-192.svg` — logo SPICE minimalista (S en fondo dark):
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
  <rect width="192" height="192" rx="32" fill="#1e293b"/>
  <text x="96" y="130" font-family="system-ui,sans-serif" font-size="110" font-weight="700" fill="white" text-anchor="middle">S</text>
</svg>
```

`public/icons/icon-512.svg` — mismo diseño, 512px.

### Step 5: Crear página offline

`dashboard/src/features/offline/offline-page.tsx`:
```tsx
export default function OfflinePage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-muted/30 gap-6 p-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-primary-foreground font-bold text-3xl">
        S
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-foreground">Sin conexión</h1>
        <p className="text-muted-foreground max-w-sm">
          Tus datos están seguros. Vuelve a conectarte para sincronizar.
        </p>
      </div>
      <button
        onClick={() => window.location.reload()}
        className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
      >
        Reintentar
      </button>
    </div>
  )
}
```

### Step 6: Registrar SW y ruta offline en main.tsx + App.tsx

En `main.tsx`, añadir `import { registerSW } from 'virtual:pwa-register'` y llamar `registerSW()`.
En `App.tsx`, añadir ruta `<Route path="/offline" element={<OfflinePage />} />`.

### Step 7: Verificar build

```bash
cd dashboard && npm run build 2>&1 | tail -20
```
Expected: build sin errores, archivo `dist/sw.js` generado.

### Step 8: Commit

```bash
git add dashboard/
git commit -m "feat: PWA — vite-plugin-pwa, manifest SPICE, SW cache-first/network-first, offline page"
```

---

## Task 2: Seguridad frontend

**Files:**
- Modify: `dashboard/src/context/AuthContext.tsx`
- Modify: `dashboard/src/features/portal/portal-page.tsx` (quitar localStorage directo)
- Modify: `dashboard/vite.config.ts` (drop console ya añadido en Task 1)

### Step 1: Instalar DOMPurify

```bash
cd dashboard && npm install dompurify && npm install -D @types/dompurify
```

### Step 2: Actualizar AuthContext.tsx

Cambios:
1. Cambiar `localStorage` → `sessionStorage` (elimina persistencia entre sesiones separadas, misma sesión del navegador)
2. Añadir idle timer de 30 minutos
3. Token también en estado en memoria (no solo storage)

```typescript
import { createContext, useContext, useEffect, useState, useCallback, useRef, type ReactNode } from 'react'
import type { Usuario, LoginResponse } from '../types'

interface AuthContextType {
  token: string | null
  usuario: Usuario | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  cargando: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)
const CLAVE_TOKEN = 'sfce_token'
const IDLE_MS = 30 * 60 * 1000 // 30 minutos

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(CLAVE_TOKEN))
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [cargando, setCargando] = useState(true)
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const limpiarSesion = useCallback(() => {
    sessionStorage.removeItem(CLAVE_TOKEN)
    setToken(null)
    setUsuario(null)
    if (idleTimer.current) clearTimeout(idleTimer.current)
  }, [])

  const reiniciarIdleTimer = useCallback(() => {
    if (idleTimer.current) clearTimeout(idleTimer.current)
    idleTimer.current = setTimeout(limpiarSesion, IDLE_MS)
  }, [limpiarSesion])

  // Registrar eventos de actividad
  useEffect(() => {
    if (!token) return
    const eventos = ['mousedown', 'keydown', 'touchstart', 'scroll']
    const handler = () => reiniciarIdleTimer()
    eventos.forEach(e => document.addEventListener(e, handler, { passive: true }))
    reiniciarIdleTimer()
    return () => {
      eventos.forEach(e => document.removeEventListener(e, handler))
      if (idleTimer.current) clearTimeout(idleTimer.current)
    }
  }, [token, reiniciarIdleTimer])

  const validarToken = useCallback(async (tokenActual: string) => {
    try {
      const respuesta = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${tokenActual}` },
        // TODO: cuando backend soporte httpOnly cookies, cambiar a credentials: 'include'
      })
      if (!respuesta.ok) throw new Error('Token invalido')
      const datos: Usuario = await respuesta.json()
      setUsuario(datos)
    } catch {
      limpiarSesion()
    }
  }, [limpiarSesion])

  useEffect(() => {
    if (token) {
      validarToken(token).finally(() => setCargando(false))
    } else {
      setCargando(false)
    }
  }, [token, validarToken])

  const login = useCallback(async (email: string, password: string) => {
    const respuesta = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!respuesta.ok) {
      const error = await respuesta.json().catch(() => ({ detail: 'Error de autenticacion' }))
      throw new Error(error.detail ?? 'Credenciales incorrectas')
    }
    const datos: LoginResponse = await respuesta.json()
    const nuevoToken = datos.access_token
    sessionStorage.setItem(CLAVE_TOKEN, nuevoToken)
    setToken(nuevoToken)
    await validarToken(nuevoToken)
  }, [validarToken])

  const logout = useCallback(() => limpiarSesion(), [limpiarSesion])

  return (
    <AuthContext.Provider value={{ token, usuario, login, logout, cargando }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const contexto = useContext(AuthContext)
  if (!contexto) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return contexto
}
```

### Step 3: Escanear usos de dangerouslySetInnerHTML

```bash
cd dashboard && grep -r "dangerouslySetInnerHTML\|innerHTML" src/ --include="*.tsx" --include="*.ts"
```

Si hay resultados, envolver con DOMPurify:
```typescript
import DOMPurify from 'dompurify'
// Uso:
dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(contenidoExterno) }}
```

### Step 4: Verificar TypeScript compila

```bash
cd dashboard && npx tsc --noEmit 2>&1 | tail -20
```

### Step 5: Commit

```bash
git add dashboard/
git commit -m "feat: seguridad frontend — sessionStorage JWT, idle timer 30min, DOMPurify, console.log eliminado en prod"
```

---

## Task 3: Portal Cliente — ruta separada /portal/:empresa_id

**Files:**
- Modify: `dashboard/src/App.tsx` — añadir ruta `/portal/:id` fuera de ProtectedRoute/AppShell
- Create: `dashboard/src/features/portal/portal-layout.tsx` — layout mínimo sin sidebar
- Modify: `dashboard/src/features/portal/portal-page.tsx` — refactoring completo con shadcn/tailwind, modelos fiscales, descarga datos

### Objetivo
La URL `/portal/:empresa_id` es una ruta pública (o con auth propia mínima). El cliente final accede aquí y ve solo sus datos: KPIs, facturas, modelos fiscales, botón "Descargar mis datos". No hay sidebar ni acceso al panel de gestoría.

**Decisión de auth del portal**: La ruta `/portal/:empresa_id` se accede con un token JWT en query param (`?token=...`) generado por la gestoría, o bien el cliente usa sus propias credenciales vía un mini-login en el portal. Implementar: si no hay token en query param ni en sessionStorage, mostrar mini-login de portal. El endpoint backend ya requiere Bearer token.

### Step 1: Crear PortalLayout

`dashboard/src/features/portal/portal-layout.tsx`:
```tsx
import { Outlet } from 'react-router-dom'

export default function PortalLayout() {
  return (
    <div className="min-h-screen bg-muted/20">
      <header className="border-b bg-background px-6 py-3 flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm">S</div>
        <span className="font-semibold text-sm text-foreground">SPICE — Portal Cliente</span>
      </header>
      <main className="container max-w-4xl mx-auto py-8 px-4">
        <Outlet />
      </main>
    </div>
  )
}
```

### Step 2: Refactorizar portal-page.tsx completo

El portal necesita:
1. Leer token de `?token=` en URL o de sessionStorage (clave `sfce_portal_token`)
2. Si no hay token, mostrar mini-login simplificado
3. KPIs con shadcn Card
4. Lista facturas (emitidas + recibidas pendientes)
5. Lista modelos fiscales generados
6. Botón "Descargar mis datos" → llama al endpoint RGPD existente `/api/empresas/{id}/exportar-datos`

```tsx
import { useState, useEffect, useCallback } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Download, FileText, Receipt, TrendingUp } from 'lucide-react'

const CLAVE_PORTAL = 'sfce_portal_token'

// ... (implementación completa con mini-login + datos)
```

### Step 3: Actualizar App.tsx

Añadir antes de `<Route path="*">`:
```tsx
// Portal Cliente — layout propio, fuera del AppShell
const PortalLayout = lazy(() => import('@/features/portal/portal-layout'))
const PortalPublico = lazy(() => import('@/features/portal/portal-page'))
// ...
<Route element={<PortalLayout />}>
  <Route path="/portal/:id" element={<PortalPublico />} />
</Route>
```

Mover la ruta antigua `/empresa/:id/portal` también a `<PortalPublico />` para redirigir.

### Step 4: TypeScript + build

```bash
cd dashboard && npx tsc --noEmit 2>&1 | tail -20
```

### Step 5: Commit

```bash
git add dashboard/
git commit -m "feat: portal cliente — ruta /portal/:id separada de AppShell, mini-login, KPIs, facturas, modelos, descarga RGPD"
```

---

## Task 4: Notificaciones Push

**Files:**
- Modify: `dashboard/vite.config.ts` — añadir archivo custom SW
- Create: `dashboard/src/sw-push.ts` — handler push en SW
- Create: `dashboard/src/features/notificaciones/notificaciones-service.ts` — gestión suscripción
- Create: `dashboard/src/features/notificaciones/notificaciones-panel.tsx` — UI componente
- Create: `dashboard/src/features/notificaciones/index.ts` — exports
- Modify: `dashboard/src/components/layout/app-shell.tsx` — integrar panel notificaciones

### Arquitectura Push
- SW maneja eventos `push` → muestra notificaciones nativas
- Frontend gestiona suscripción (subscribe/unsubscribe)
- Tipos de notificación: `modelo_vence` (3 días), `pipeline_error`, `doc_procesado`
- **Nota**: El backend (sfce/) necesita endpoint para guardar suscripciones y enviar pushes. Esto es fuera de scope de esta sesión. Se añade la infraestructura frontend completa.

### Step 1: Crear sw-push.ts (inyectado en SW via vite-plugin-pwa)

```typescript
// Manejador de eventos push en el service worker
declare const self: ServiceWorkerGlobalScope

self.addEventListener('push', (event: PushEvent) => {
  if (!event.data) return
  const datos = event.data.json() as {
    tipo: 'modelo_vence' | 'pipeline_error' | 'doc_procesado'
    titulo: string
    cuerpo: string
    url?: string
  }
  event.waitUntil(
    self.registration.showNotification(datos.titulo, {
      body: datos.cuerpo,
      icon: '/icons/icon-192.svg',
      badge: '/icons/icon-192.svg',
      data: { url: datos.url ?? '/' },
      tag: datos.tipo,
    })
  )
})

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()
  const url = (event.notification.data?.url as string) ?? '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then(clients => {
      const cliente = clients.find(c => c.url === url && 'focus' in c)
      if (cliente) return cliente.focus()
      return self.clients.openWindow(url)
    })
  )
})
```

### Step 2: Crear notificaciones-service.ts

```typescript
const VAPID_PUBLIC_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY ?? ''

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)))
}

export async function suscribirNotificaciones(token: string): Promise<boolean> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return false
  const permiso = await Notification.requestPermission()
  if (permiso !== 'granted') return false
  const registro = await navigator.serviceWorker.ready
  const suscripcion = await registro.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: VAPID_PUBLIC_KEY ? urlBase64ToUint8Array(VAPID_PUBLIC_KEY) : undefined,
  })
  // TODO: enviar suscripcion al backend cuando esté disponible
  // await fetch('/api/notificaciones/suscribir', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  //   body: JSON.stringify(suscripcion),
  // })
  return true
}

export async function desuscribir(): Promise<void> {
  const registro = await navigator.serviceWorker.ready
  const suscripcion = await registro.pushManager.getSubscription()
  await suscripcion?.unsubscribe()
}

export function notificacionesSoportadas(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}
```

### Step 3: Crear NotificacionesPanel componente

`dashboard/src/features/notificaciones/notificaciones-panel.tsx`:
```tsx
import { useState, useEffect } from 'react'
import { Bell, BellOff, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuTrigger,
  DropdownMenuItem, DropdownMenuSeparator, DropdownMenuLabel,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { notificacionesSoportadas, suscribirNotificaciones } from './notificaciones-service'
import { useAuth } from '@/context/AuthContext'

interface Notificacion {
  id: string
  tipo: 'modelo_vence' | 'pipeline_error' | 'doc_procesado'
  titulo: string
  cuerpo: string
  leida: boolean
  fecha: Date
}

// Demo notifications para mostrar UI funcional
const NOTIF_DEMO: Notificacion[] = [
  { id: '1', tipo: 'modelo_vence', titulo: 'Modelo 303 vence en 3 días', cuerpo: 'Plazo: 20 enero 2026', leida: false, fecha: new Date() },
  { id: '2', tipo: 'doc_procesado', titulo: 'Documento procesado', cuerpo: 'Factura_enero.pdf procesada correctamente', leida: false, fecha: new Date(Date.now() - 3600000) },
]

export function NotificacionesPanel() {
  const { token } = useAuth()
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>(NOTIF_DEMO)
  const [permiso, setPermiso] = useState<NotificationPermission>('default')
  const soportadas = notificacionesSoportadas()

  useEffect(() => {
    if ('Notification' in window) setPermiso(Notification.permission)
  }, [])

  const noLeidas = notificaciones.filter(n => !n.leida).length

  const activarPush = async () => {
    if (!token) return
    await suscribirNotificaciones(token)
    setPermiso(Notification.permission)
  }

  const marcarLeida = (id: string) =>
    setNotificaciones(prev => prev.map(n => n.id === id ? { ...n, leida: true } : n))

  const marcarTodasLeidas = () =>
    setNotificaciones(prev => prev.map(n => ({ ...n, leida: true })))

  const iconoTipo = (tipo: Notificacion['tipo']) => {
    if (tipo === 'modelo_vence') return '📅'
    if (tipo === 'pipeline_error') return '⚠️'
    return '✅'
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-4 w-4" />
          {noLeidas > 0 && (
            <Badge className="absolute -top-1 -right-1 h-4 w-4 p-0 flex items-center justify-center text-[10px]">
              {noLeidas}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>Notificaciones</span>
          {noLeidas > 0 && (
            <Button variant="ghost" size="sm" className="h-auto p-0 text-xs text-muted-foreground" onClick={marcarTodasLeidas}>
              Marcar todas leídas
            </Button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {notificaciones.length === 0 && (
          <div className="py-6 text-center text-sm text-muted-foreground">Sin notificaciones</div>
        )}
        {notificaciones.map(n => (
          <DropdownMenuItem key={n.id} className={`flex flex-col items-start gap-0.5 py-2 cursor-pointer ${n.leida ? 'opacity-60' : ''}`} onClick={() => marcarLeida(n.id)}>
            <div className="flex w-full items-center gap-2">
              <span>{iconoTipo(n.tipo)}</span>
              <span className="flex-1 text-sm font-medium">{n.titulo}</span>
              {!n.leida && <span className="h-2 w-2 rounded-full bg-primary shrink-0" />}
            </div>
            <p className="text-xs text-muted-foreground pl-6">{n.cuerpo}</p>
          </DropdownMenuItem>
        ))}
        {soportadas && permiso !== 'granted' && (
          <>
            <DropdownMenuSeparator />
            <div className="p-2">
              <Button size="sm" variant="outline" className="w-full gap-2" onClick={activarPush}>
                <Bell className="h-3 w-3" />
                Activar notificaciones push
              </Button>
            </div>
          </>
        )}
        {!soportadas && (
          <div className="p-2 text-xs text-center text-muted-foreground flex items-center justify-center gap-1">
            <BellOff className="h-3 w-3" />
            Push no disponible en este navegador
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
```

### Step 4: Exportar desde index.ts

```typescript
export { NotificacionesPanel } from './notificaciones-panel'
export { suscribirNotificaciones, desuscribir, notificacionesSoportadas } from './notificaciones-service'
```

### Step 5: Integrar en app-shell.tsx

Añadir `<NotificacionesPanel />` en la barra superior del AppShell (junto al botón de usuario/logout).

### Step 6: Configurar vite-plugin-pwa para incluir sw-push

En `vite.config.ts`, dentro de `VitePWA`, añadir:
```typescript
strategies: 'injectManifest',
srcDir: 'src',
filename: 'sw.ts',
```
Y crear `dashboard/src/sw.ts` que importa el handler push y reexporta workbox.

**Alternativa más simple** (evita complejidad de injectManifest): Usar `registerType: 'autoUpdate'` con `workbox` (ya configurado) y añadir el handler push directamente en el archivo de SW personalizado mediante `additionalManifestEntries`. Para el scope de esta tarea, el push handler se puede simular con `Notification API` directa (sin SW push real) hasta que el backend esté listo.

**Decisión**: Usar `workbox` strategy por defecto + crear archivo SW adicional en `public/sw-custom.js` que se fusiona manualmente. Más pragmático.

### Step 7: Build y TypeScript check

```bash
cd dashboard && npx tsc --noEmit && npm run build 2>&1 | tail -20
```

### Step 8: Commit

```bash
git add dashboard/
git commit -m "feat: notificaciones push — SW handler, panel UI, suscripcion, tipos modelo_vence/pipeline_error/doc_procesado"
```

---

## Checklist final

- [ ] `npm run build` sin errores
- [ ] TypeScript sin errores (`npx tsc --noEmit`)
- [ ] Service worker generado en `dist/sw.js`
- [ ] Manifest en `dist/manifest.json` o embebido
- [ ] Portal accesible en `/portal/1` sin sidebar de gestoría
- [ ] Auto-logout después de 30 min inactidad (sessionStorage + timer)
- [ ] `console.log` eliminados en build prod (verificar con `grep "console" dist/assets/*.js`)
- [ ] Componente notificaciones visible en AppShell
