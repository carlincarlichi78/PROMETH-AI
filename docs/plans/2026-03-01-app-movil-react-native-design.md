# Design: App Móvil React Native — SFCE

**Fecha**: 2026-03-01
**Estado**: Aprobado
**Sesión**: 5

---

## Contexto

SFCE necesita una app móvil nativa para dos tipos de usuario:
- **Empresario** (rol `cliente`): consultar KPIs, subir facturas desde cámara, ver notificaciones
- **Gestor** (roles `gestor`/`asesor`/`admin_gestoria`): vista ligera — subir docs de sus clientes, ver alertas

Una sola app detecta el rol del usuario tras login y muestra los tabs correspondientes.

**Canales ya definidos:**
- Web dashboard (superadmin + gestor, producción)
- App móvil (empresario + gestor ligero) — este documento
- Electron (gestor premium, fase posterior)

---

## Stack Tecnológico

| Tecnología | Versión | Rol |
|-----------|---------|-----|
| Expo SDK | 52 | Base de la app |
| Expo Router | v3 | Navegación file-based |
| NativeWind | v4 | Tailwind para React Native |
| Zustand | ^5 | Auth store (token + usuario) |
| TanStack Query | v5 | Data fetching + cache |
| expo-camera | latest | Captura de documentos |
| expo-image-picker | latest | Selección desde galería |
| expo-secure-store | latest | JWT cifrado en dispositivo |
| expo-notifications | latest | Push notifications |
| EAS Build | latest | Builds en la nube (iOS + Android) |

**Sin offline**: la app requiere conexión. Sin expo-sqlite ni AsyncStorage para datos.

---

## Estructura de Carpetas

```
CONTABILIDAD/
  mobile/                          ← nuevo directorio en monorepo
    app/
      _layout.tsx                  ← Root layout: auth guard + QueryClient + Zustand
      (auth)/
        _layout.tsx                ← Layout público (sin tabs)
        login.tsx                  ← Login con email + password
      (empresario)/
        _layout.tsx                ← Bottom tabs para rol cliente
        index.tsx                  ← Home: KPIs + documentos recientes
        subir.tsx                  ← Upload wizard (4 pasos)
        notificaciones.tsx         ← Lista de alertas
        perfil.tsx                 ← Datos cuenta + plan_tier + logout
      (gestor)/
        _layout.tsx                ← Bottom tabs para rol gestor/asesor
        index.tsx                  ← Lista empresas con estado
        subir.tsx                  ← Upload wizard con selector cliente (5 pasos)
        alertas.tsx                ← Onboardings pendientes + docs en cola
      onboarding/
        [id].tsx                   ← Wizard 3 pasos si empresa pendiente_cliente
    components/
      ui/
        Button.tsx
        Card.tsx
        Badge.tsx
        Input.tsx
        Spinner.tsx
      upload/
        IntakeForm.tsx             ← Tipo de documento + proveedor
        ProveedorSelector.tsx      ← Selector con historial + "añadir nuevo"
        CamaraCaptura.tsx          ← Captura foto o galería
    hooks/
      useApi.ts                    ← fetch wrapper con JWT automático + 401 handler
      useTiene.ts                  ← mismo mapa de features que sfce/core/tiers.py
    store/
      auth.ts                      ← Zustand: token, usuario (id, email, rol, plan_tier)
    constants/
      api.ts                       ← BASE_URL desde EXPO_PUBLIC_API_URL
    package.json
    app.json                       ← Expo config (nombre, bundle ID, etc.)
    .env.local                     ← EXPO_PUBLIC_API_URL=http://192.168.x.x:8000
    .env.production                ← EXPO_PUBLIC_API_URL=https://contabilidad.lemonfresh-tuc.com
```

---

## Flujos de Navegación

### Arranque de la app

```
AppStart
  ↓
¿Hay token en SecureStore?
  NO → /login
  SÍ → GET /api/auth/me
        401 → borrar token → /login
        OK  → ¿rol === 'cliente'?
                SÍ → ¿empresa.estado_onboarding === 'pendiente_cliente'?
                       SÍ → /onboarding/[id]
                       NO → /(empresario)/
                NO → /(gestor)/
```

### Flujo upload — Empresario

```
Tab "Subir"
  Paso 1: elegir tipo (Factura | Ticket | Nómina | Extracto | Otro)
  Paso 2: cámara (expo-camera) o galería (expo-image-picker)
  Paso 3: asignar proveedor
    - Lista proveedores guardados (GET /api/portal/{id}/proveedores-frecuentes)
    - "Añadir nuevo" → form CIF + nombre → guarda SupplierRule
  Paso 4: confirmar → POST /api/portal/{empresa_id}/documentos/subir
           (multipart/form-data: archivo + tipo + proveedor_cif + proveedor_nombre)
  → Éxito: volver a Home con notificación toast
```

### Flujo upload — Gestor

```
Tab "Subir"
  Paso 1: elegir empresa cliente (GET /api/gestor/resumen → lista empresas)
  Paso 2: elegir tipo (Factura | Ticket | Nómina | Extracto | Otro)
  Paso 3: cámara o galería
  Paso 4: proveedor de esa empresa
    - Historial de proveedores del cliente
    - "Añadir nuevo" → form CIF + nombre
  Paso 5: confirmar → POST /api/portal/{empresa_id}/documentos/subir
  → Éxito: volver a lista empresas
```

**Regla de SupplierRule:** La primera vez que se sube un documento de un proveedor, se pide CIF + nombre. El sistema guarda la regla. En uploads siguientes, ese proveedor aparece en el selector — solo hay que elegirlo.

---

## Auth + Seguridad

**Almacenamiento JWT:**
```typescript
// SecureStore: cifrado por el SO, inaccesible desde otras apps
await SecureStore.setItemAsync('sfce_token', access_token)
await SecureStore.getItemAsync('sfce_token')
await SecureStore.deleteItemAsync('sfce_token')
```

**API wrapper:**
```typescript
// mobile/hooks/useApi.ts
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await SecureStore.getItemAsync('sfce_token')
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })
  if (res.status === 401) {
    await SecureStore.deleteItemAsync('sfce_token')
    router.replace('/(auth)/login')
    throw new Error('Sesión expirada')
  }
  if (!res.ok) throw new Error(`Error ${res.status}`)
  return res.json()
}
```

**Renovación de token:**
- Al abrir la app (si hay token): `POST /api/auth/refresh` silencioso → actualiza token en SecureStore
- Si falla el refresh → forzar re-login

**Variables de entorno:**
```bash
# .env.local (desarrollo)
EXPO_PUBLIC_API_URL=http://192.168.x.x:8000  # IP local del servidor dev

# .env.production
EXPO_PUBLIC_API_URL=https://contabilidad.lemonfresh-tuc.com
```

---

## API Endpoints Consumidos

Todos ya implementados o planificados en el plan `2026-03-01-canal-acceso-onboarding.md`:

| Método | Endpoint | Pantalla |
|--------|----------|---------|
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Arranque + Perfil |
| POST | `/api/auth/refresh` | Arranque silencioso |
| GET | `/api/portal/{id}/resumen` | Home empresario |
| GET | `/api/portal/{id}/documentos` | Home empresario |
| POST | `/api/portal/{id}/documentos/subir` | Upload |
| GET | `/api/portal/{id}/notificaciones` | Notificaciones |
| GET | `/api/onboarding/cliente/{id}` | Guard onboarding |
| PUT | `/api/onboarding/cliente/{id}` | Wizard onboarding |
| GET | `/api/gestor/resumen` | Tab empresas gestor |
| GET | `/api/gestor/alertas` | Tab alertas gestor |

**Endpoint nuevo a añadir al backend:**
```
GET /api/portal/{empresa_id}/proveedores-frecuentes
→ Lista de proveedores usados por esa empresa (de SupplierRule)
→ Sirve para el selector de proveedores en upload
```

---

## Tiers en la App

```typescript
// mobile/hooks/useTiene.ts — mismo mapa que sfce/core/tiers.py
const FEATURES_EMPRESARIO = {
  consultar:   'basico',
  subir_docs:  'pro',
  app_movil:   'pro',
  firmar:      'premium',
  chat_gestor: 'premium',
}
```

- El acceso a la app ya implica `plan_tier >= 'pro'` (feature `app_movil`)
- El tab "Subir" solo aparece si `useTiene('subir_docs')` — plan pro o superior
- Si el empresario tiene plan básico y descarga la app, ve un mensaje "Actualiza tu plan"

---

## Push Notifications

- **Servicio**: Expo Push Service (sin Firebase para v1)
- **Registro**: al hacer login → `POST /api/portal/{id}/notificaciones/suscribir` con `expo_push_token`
- **Tipos de notificación**:
  - Documento procesado → "Tu factura de [Proveedor] ha sido procesada"
  - Modelo fiscal próximo → "El Modelo 303 vence en 5 días"
  - Onboarding pendiente → "Completa el alta de tu empresa"

El endpoint de suscripción ya está planificado (`vite-plugin-pwa` + VAPID en el web, Expo Push en móvil).

---

## Decisiones diferidas

- **Bundle ID / App ID**: definir al publicar en App Store / Play Store
- **Icono y splash screen**: diseño visual de la app
- **Firma digital** (feature `firmar`): requiere integración con proveedor de firma legal (Signaturit, DocuSign) — fase premium
- **Chat gestor-empresario** (feature `chat_gestor`): WebSocket o polling — fase premium
- **Biometría** (Face ID / huella): acceso rápido sin re-login — fase 2

---

## Lo que NO está en v1

- Offline / cache local
- Firma digital
- Chat interno
- Facturación dentro de la app
- Panel de administración completo para el gestor (solo vista ligera)
