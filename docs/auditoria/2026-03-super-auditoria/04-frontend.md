# Auditoría Frontend + Dashboard SFCE — 2026-03-02

**Veredicto: ISSUES IMPORTANTES**
**Críticos: 4 | Importantes: 6 | Menores: 8**

---

## CRÍTICOS

### [FE-1] ⚠️ BUG EN PRODUCCIÓN: Onboarding y Revisión leen token de `localStorage` (incorrecto) — requests sin autenticación
- **Archivos afectados**:
  - `dashboard/src/features/onboarding/onboarding-masivo-page.tsx:12`
  - `dashboard/src/features/onboarding/perfil-revision-card.tsx:6`
  - `dashboard/src/features/onboarding/wizard-onboarding-page.tsx:9`
  - `dashboard/src/features/documentos/revision-page.tsx:14`
- **Problema**: Definen helpers `auth()` propios que leen de `localStorage.getItem('token')`. El token real está en `sessionStorage` con clave `'sfce_token'` (definido en `AuthContext`). `localStorage.getItem('token')` siempre devuelve `null`.
- **Impacto**: Las 4 páginas envían `Bearer null` → backend responde 401 → funcionalidad completamente rota en producción.
- **Fix**: Reemplazar en los 4 archivos:
```typescript
// INCORRECTO
const auth = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` })
// CORRECTO
const auth = () => ({ Authorization: `Bearer ${sessionStorage.getItem('sfce_token')}` })
```
O mejor: usar `ApiClient` central que ya gestiona esto correctamente.

### [FE-2] Ruta `/testing` accesible para cualquier usuario autenticado (sin guard de rol)
- **Archivo**: `dashboard/src/App.tsx:232`
- **Problema**: `ProtectedRoute` solo bloquea usuarios sin token. Cualquier `asesor` puede navegar a `/testing` y disparar sesiones de regression del motor de testing.
- **Fix**: Añadir `RoleGuard` para `superadmin` en la ruta.

### [FE-3] Condición de rol `'admin'` en sidebar — nunca verdadera, bloquea acceso a `/admin/gestorias`
- **Archivo**: `dashboard/src/components/layout/app-sidebar.tsx:294`
- **Problema**: `usuario?.rol === 'admin'` → el rol `'admin'` no existe en el sistema real (fue reemplazado por `'superadmin'`). El link a `/admin/gestorias` es invisible para todos. El `types/index.ts` incluye `'admin'` como tipo válido — desincronización con el backend.
- **Fix**: Cambiar a `usuario?.rol === 'superadmin'`. Limpiar `'admin'` y `'gestor'` del union type en `types/index.ts`.

### [FE-4] `window.open(url_descarga)` sin validación de URL — open redirect potencial
- **Archivo**: `dashboard/src/features/portal/portal-page.tsx:94`
- **Problema**: `url_descarga` del servidor se pasa directamente a `window.open()` sin validar que sea del mismo origen.
- **Fix**:
```typescript
const url = new URL(url_descarga, window.location.origin)
if (url.origin !== window.location.origin) throw new Error('URL inválida')
window.open(url.toString(), '_blank', 'noopener,noreferrer')
```

---

## IMPORTANTES

| ID | Descripción | Archivo |
|----|-------------|---------|
| FE-5 | `dompurify` instalado pero nunca importado ni usado — falsa sensación de seguridad | `package.json:24` |
| FE-6 | RBAC client-side solo controla visibilidad del sidebar, no bloquea rutas (la protección real depende 100% del backend — aceptable si el backend es estricto, pero debe documentarse) | `App.tsx`, `ProtectedRoute.tsx` |
| FE-7 | `useSemaforo` hace fetch a `/api/testing/semaforo` sin cabecera Authorization | `testing-page.tsx:23-28` |
| FE-8 | Mutaciones en wizard de onboarding sin manejo de errores — `handleEliminar` es fire-and-forget, deja estado desincronizado | `wizard-onboarding-page.tsx:398` |
| FE-9 | `PortalLayout` no verifica rol — un gestor que navegue a `/portal` ve la vista de cliente | `portal-layout.tsx` |
| FE-10 | PWA cachea respuestas API autenticadas con `NetworkFirst` — datos de sesión anterior pueden servirse en sesión nueva | `vite.config.ts:39-48` |

---

## MENORES

| ID | Descripción | Archivo |
|----|-------------|---------|
| FE-11 | `key={i}` (índice array) en listas de datos dinámicos | `copilot-message.tsx:41`, `wizard-onboarding-page.tsx:100,154,270` |
| FE-12 | `ReactQueryDevtools` incluido en bundle de producción (debería ser solo en dev) | `main.tsx:8` |
| FE-13 | `localStorage` para preferencias de sidebar vs `sessionStorage` para token — correcto, pero documentarlo |  |
| FE-14 | `as any` para pasar `Semaforo` a `SemaforoCard` — solucionable alineando tipos | `testing-page.tsx:93-95` |
| FE-15 | PWA manifest tiene `name: 'SPICE'` en lugar de `'SFCE'` | `vite.config.ts:15-17` |
| FE-16 | Sin `ErrorBoundary` global — pantalla en blanco si un chunk lazy falla | `main.tsx` |
| FE-17 | `noUncheckedIndexedAccess` activado pero bypasseado con `!` en `login-page.tsx:31` | `login-page.tsx:31` |
| FE-18 | `ChevronDown` reimplementado como SVG inline (import directo de lucide sería suficiente) | `wizard-onboarding-page.tsx:358-364` |

---

## COMPONENTES MÁS GRANDES (candidatos a split)

| Componente | Líneas | Propuesta |
|-----------|--------|-----------|
| `product-intelligence-page.tsx` | ~600 | Extraer `TablaProveedores`, `GraficoVentasMensuales`, `RankingProductos` |
| `sala-estrategia-page.tsx` | ~595 | Extraer sección chat/simulador y sección objetivos |
| `restaurant-360-page.tsx` | ~524 | Extraer gráficos individuales (al menos 3 componentes) |
| `wizard-onboarding-page.tsx` | ~505 | Mover Paso1/2/3/4 a archivos separados en `pasos/` |
| `app-sidebar.tsx` | ~441 | Extraer `EmpresaSidebarGroups.tsx` y `GlobalSidebarGroups.tsx` |

---

## TYPESCRIPT ISSUES

- `types/index.ts:6`: `Usuario.rol` incluye `'admin'` y `'gestor'` que no existen en el backend. Debería ser: `'superadmin' | 'admin_gestoria' | 'asesor' | 'asesor_independiente' | 'cliente'`
- `testing-page.tsx:93-95`: 3 usos de `as any` — solucionable alineando tipos `Semaforo` con `SemaforoData`
- `revision-page.tsx:75`: Double cast `as Record<string, string>` sin validación real
- `wizard-onboarding-page.tsx`: Funciones async sin tipo de retorno explícito

---

## ACCESIBILIDAD — Issues principales

- Drop area de PDFs en wizard: `<div>` sin `role`, `tabIndex` ni manejo de teclado — inaccesible con teclado
- `app-sidebar.tsx`: Empresa activa sin `aria-label` en tooltip de navegación
- `revision-page.tsx`: Labels de formulario sin `htmlFor` asociado a `id` del input
- Sin `aria-live` en áreas de resultados de mutaciones asíncronas (sin feedback para screen readers)

---

## BIEN IMPLEMENTADO ✓

1. `sessionStorage` para token JWT en `AuthContext` (no `localStorage`) — correcto
2. Validación del token contra `/api/auth/me` en cada recarga
3. Idle timer de 30 minutos con logout automático
4. Lazy loading de todas las rutas con Suspense
5. `useTiene.ts` para feature flags por tier — bien implementado
6. `AdvisorGate` con overlay de upgrade — UX correcta para tiers
7. TypeScript strict + `noUncheckedIndexedAccess` activado
8. CORS origin sin wildcard en la API (protección adicional)
9. Zustand solo para estado global real (no sobrecargado)

---

## PRIORIDAD

### Fix inmediato (está roto en producción)
1. **FE-1**: Cambiar `localStorage.getItem('token')` → `sessionStorage.getItem('sfce_token')` en los 4 archivos

### Próxima sesión
- **FE-3**: `'admin'` → `'superadmin'` en sidebar + limpiar union type en `types/index.ts`
- **FE-2**: Guard de rol para ruta `/testing`
- **FE-4**: Validar URL antes de `window.open()`

### Backlog
- FE-5: Usar dompurify o eliminarlo
- FE-7: Añadir token a `useSemaforo`
- FE-8: Error handling en wizard mutations
- FE-10: `Vary: Authorization` en backend o excluir rutas sensibles del cache PWA
- FE-12: ReactQueryDevtools solo en dev
- FE-15: Actualizar nombre en manifest PWA
- FE-16: Añadir ErrorBoundary global
