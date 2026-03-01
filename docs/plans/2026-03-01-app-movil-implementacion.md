# App Móvil React Native — Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Crear la app móvil SFCE en `mobile/` con Expo Router, modo dual empresario/gestor, upload de documentos con intake rápido de proveedor, y notificaciones.

**Architecture:** Expo SDK 52 + Expo Router v3 (file-based routing). App dual: detecta el rol del usuario en el JWT tras login y muestra tabs de empresario o de gestor. Upload de documentos con 4-5 pasos incluyendo selector de proveedor con historial (SupplierRule). Auth con JWT en expo-secure-store.

**Tech Stack:** Expo SDK 52, Expo Router v3, NativeWind v4, Zustand v5, TanStack Query v5, expo-camera, expo-image-picker, expo-secure-store, expo-notifications. Node 24 + npm 11.

**Design doc:** `docs/plans/2026-03-01-app-movil-react-native-design.md`

**Prerrequisito backend:** Los endpoints `/api/gestor/resumen`, `/api/gestor/alertas`, `/api/portal/{id}/documentos/subir`, `/api/portal/{id}/notificaciones` deben estar implementados (plan `2026-03-01-canal-acceso-onboarding.md`). El endpoint `/api/portal/{id}/proveedores-frecuentes` se implementa en el Task 1 de este plan.

---

### Task 1: Endpoint backend — proveedores frecuentes

**Files:**
- Modify: `sfce/api/rutas/portal.py`
- Modify: `tests/test_onboarding.py`

El selector de proveedor en la app necesita una lista de proveedores ya usados por la empresa (de la tabla `supplier_rules`).

**Step 1: Escribir el test**

Añadir al final de `tests/test_onboarding.py`:

```python
from sfce.db.modelos import SupplierRule

def test_proveedores_frecuentes_vacio(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)
    r = client.get(
        f"/api/portal/{empresa_id}/proveedores-frecuentes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["proveedores"] == []


def test_proveedores_frecuentes_devuelve_reglas(client_onboarding):
    client, empresa_id = client_onboarding
    token = _token(client)

    # Crear una SupplierRule directamente en BD
    sesion_factory = client.app.state.sesion_factory
    with sesion_factory() as s:
        rule = SupplierRule(
            empresa_id=empresa_id,
            emisor_cif="B12312312",
            emisor_nombre_patron="Repsol",
            tipo_doc_sugerido="FV",
            aplicaciones=5,
        )
        s.add(rule)
        s.commit()

    r = client.get(
        f"/api/portal/{empresa_id}/proveedores-frecuentes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    proveedores = r.json()["proveedores"]
    assert len(proveedores) == 1
    assert proveedores[0]["nombre"] == "Repsol"
    assert proveedores[0]["cif"] == "B12312312"
```

**Step 2: Verificar que fallan**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_onboarding.py::test_proveedores_frecuentes_vacio -v 2>&1 | tail -10
```
Expected: FAIL — endpoint no existe

**Step 3: Implementar endpoint**

En `sfce/api/rutas/portal.py`, añadir al final:

```python
from sfce.db.modelos import SupplierRule
from sqlalchemy import select


@router.get("/{empresa_id}/proveedores-frecuentes")
def proveedores_frecuentes(
    empresa_id: int,
    request: Request,
    usuario=Depends(obtener_usuario_actual),
):
    """Lista de proveedores ya usados por la empresa — para el selector en la app."""
    sf = request.app.state.sesion_factory
    with sf() as sesion:
        reglas = (
            sesion.execute(
                select(SupplierRule)
                .where(SupplierRule.empresa_id == empresa_id)
                .where(SupplierRule.emisor_nombre_patron.is_not(None))
                .order_by(SupplierRule.aplicaciones.desc())
                .limit(50)
            )
            .scalars()
            .all()
        )
        return {
            "proveedores": [
                {
                    "cif": r.emisor_cif,
                    "nombre": r.emisor_nombre_patron,
                    "tipo_doc_sugerido": r.tipo_doc_sugerido,
                    "aplicaciones": r.aplicaciones,
                }
                for r in reglas
            ]
        }
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_onboarding.py -v 2>&1 | tail -15
```
Expected: PASS

**Step 5: Commit**

```bash
git add sfce/api/rutas/portal.py tests/test_onboarding.py
git commit -m "feat: GET /api/portal/{id}/proveedores-frecuentes — selector proveedor en app"
```

---

### Task 2: Scaffold del proyecto Expo

**Files:**
- Create: `mobile/` (directorio completo)

**Step 1: Crear el proyecto**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
npx create-expo-app@latest mobile --template default
```

Cuando pregunte por el nombre, usar: `sfce-mobile`

Expected output: `✅ Your project is ready!`

**Step 2: Verificar que arranca**

```bash
cd mobile
npm run web
```
Expected: abre en http://localhost:8081 con la app de demostración

Parar con Ctrl+C.

**Step 3: Instalar dependencias**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/mobile
npx expo install expo-secure-store expo-camera expo-image-picker expo-notifications
npm install zustand @tanstack/react-query nativewind
npm install -D tailwindcss@^3
```

**Step 4: Configurar NativeWind**

Crear `mobile/tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,jsx,ts,tsx}', './components/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: { extend: {} },
  plugins: [],
}
```

En `mobile/babel.config.js`, añadir el preset de NativeWind:

```javascript
module.exports = function (api) {
  api.cache(true)
  return {
    presets: [
      ['babel-preset-expo', { jsxImportSource: 'nativewind' }],
      'nativewind/babel',
    ],
  }
}
```

**Step 5: Crear .env files**

```bash
# mobile/.env.local
echo "EXPO_PUBLIC_API_URL=http://192.168.1.100:8000" > .env.local

# mobile/.env.production
echo "EXPO_PUBLIC_API_URL=https://contabilidad.lemonfresh-tuc.com" > .env.production
```

Añadir a `.gitignore` del repo raíz:
```
mobile/.env.local
mobile/.env.production
mobile/node_modules/
```

**Step 6: Limpiar plantilla de demostración**

Borrar los archivos de demo generados por la plantilla que no necesitamos:
```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/mobile
rm -rf app/\(tabs\)/* app/\+not-found.tsx
```

**Step 7: Commit**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
git add mobile/
git commit -m "feat: scaffold app móvil Expo SDK 52 + Expo Router + NativeWind"
```

---

### Task 3: Auth store + hook useApi

**Files:**
- Create: `mobile/store/auth.ts`
- Create: `mobile/hooks/useApi.ts`
- Create: `mobile/constants/api.ts`

**Step 1: Crear constants/api.ts**

```typescript
// mobile/constants/api.ts
export const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000'
```

**Step 2: Crear store/auth.ts**

```typescript
// mobile/store/auth.ts
import { create } from 'zustand'
import * as SecureStore from 'expo-secure-store'

interface Usuario {
  id: number
  email: string
  nombre: string
  rol: string
  plan_tier: string
  gestoria_id: number | null
  empresas_asignadas: number[]
}

interface AuthStore {
  token: string | null
  usuario: Usuario | null
  setToken: (token: string) => Promise<void>
  setUsuario: (usuario: Usuario) => void
  cerrarSesion: () => Promise<void>
  cargarTokenGuardado: () => Promise<string | null>
}

const CLAVE_TOKEN = 'sfce_token'

export const useAuthStore = create<AuthStore>((set) => ({
  token: null,
  usuario: null,

  setToken: async (token) => {
    await SecureStore.setItemAsync(CLAVE_TOKEN, token)
    set({ token })
  },

  setUsuario: (usuario) => set({ usuario }),

  cerrarSesion: async () => {
    await SecureStore.deleteItemAsync(CLAVE_TOKEN)
    set({ token: null, usuario: null })
  },

  cargarTokenGuardado: async () => {
    const token = await SecureStore.getItemAsync(CLAVE_TOKEN)
    if (token) set({ token })
    return token
  },
}))
```

**Step 3: Crear hooks/useApi.ts**

```typescript
// mobile/hooks/useApi.ts
import { router } from 'expo-router'
import * as SecureStore from 'expo-secure-store'
import { BASE_URL } from '@/constants/api'

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await SecureStore.getItemAsync('sfce_token')

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (res.status === 401) {
    await SecureStore.deleteItemAsync('sfce_token')
    router.replace('/(auth)/login')
    throw new Error('Sesión expirada')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Error ${res.status}`)
  }

  return res.json()
}

export async function apiUpload<T>(
  path: string,
  formData: FormData
): Promise<T> {
  const token = await SecureStore.getItemAsync('sfce_token')
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })
  if (res.status === 401) {
    await SecureStore.deleteItemAsync('sfce_token')
    router.replace('/(auth)/login')
    throw new Error('Sesión expirada')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `Error ${res.status}`)
  }
  return res.json()
}
```

**Step 4: Crear hooks/useTiene.ts**

```typescript
// mobile/hooks/useTiene.ts
import { useAuthStore } from '@/store/auth'

const TIER_RANK: Record<string, number> = { basico: 1, pro: 2, premium: 3 }

// Mismo mapa que sfce/core/tiers.py — mantener sincronizados
const FEATURES_EMPRESARIO: Record<string, string> = {
  consultar:   'basico',
  subir_docs:  'pro',
  app_movil:   'pro',
  firmar:      'premium',
  chat_gestor: 'premium',
}

export function useTiene(feature: string): boolean {
  const usuario = useAuthStore((s) => s.usuario)
  const requerido = FEATURES_EMPRESARIO[feature] ?? 'premium'
  const actual = usuario?.plan_tier ?? 'basico'
  return (TIER_RANK[actual] ?? 1) >= (TIER_RANK[requerido] ?? 3)
}
```

**Step 5: Verificar TypeScript**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/mobile
npx tsc --noEmit 2>&1 | tail -15
```
Expected: 0 errores

**Step 6: Commit**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
git add mobile/store/ mobile/hooks/ mobile/constants/
git commit -m "feat: auth store Zustand + useApi + useTiene — base de la app móvil"
```

---

### Task 4: Root layout + auth guard + pantalla login

**Files:**
- Create/Modify: `mobile/app/_layout.tsx`
- Create: `mobile/app/(auth)/_layout.tsx`
- Create: `mobile/app/(auth)/login.tsx`

**Step 1: Root layout con QueryClient + auth guard**

```tsx
// mobile/app/_layout.tsx
import { useEffect } from 'react'
import { Stack, router } from 'expo-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'

const queryClient = new QueryClient()

function AuthGate({ children }: { children: React.ReactNode }) {
  const { cargarTokenGuardado, setUsuario, cerrarSesion } = useAuthStore()

  useEffect(() => {
    const init = async () => {
      const token = await cargarTokenGuardado()
      if (!token) {
        router.replace('/(auth)/login')
        return
      }
      try {
        const usuario = await apiFetch<{
          id: number; email: string; nombre: string; rol: string
          plan_tier: string; gestoria_id: number | null; empresas_asignadas: number[]
        }>('/api/auth/me')
        setUsuario(usuario)

        const rol = usuario.rol
        // Routing según rol
        if (rol === 'cliente') {
          // Verificar onboarding
          const empresaId = usuario.empresas_asignadas?.[0]
          if (empresaId) {
            try {
              const onb = await apiFetch<{ estado: string }>(
                `/api/onboarding/cliente/${empresaId}`
              )
              if (onb.estado === 'pendiente_cliente') {
                router.replace(`/onboarding/${empresaId}`)
                return
              }
            } catch { /* ignorar */ }
          }
          router.replace('/(empresario)/')
        } else {
          router.replace('/(gestor)/')
        }
      } catch {
        await cerrarSesion()
        router.replace('/(auth)/login')
      }
    }
    init()
  }, [])

  return <>{children}</>
}

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthGate>
        <Stack screenOptions={{ headerShown: false }} />
      </AuthGate>
    </QueryClientProvider>
  )
}
```

**Step 2: Layout público (auth)**

```tsx
// mobile/app/(auth)/_layout.tsx
import { Stack } from 'expo-router'

export default function AuthLayout() {
  return <Stack screenOptions={{ headerShown: false }} />
}
```

**Step 3: Pantalla login**

```tsx
// mobile/app/(auth)/login.tsx
import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ActivityIndicator, Alert } from 'react-native'
import { router } from 'expo-router'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'

export default function LoginScreen() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [cargando, setCargando] = useState(false)
  const { setToken, setUsuario } = useAuthStore()

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('Error', 'Introduce tu email y contraseña')
      return
    }
    setCargando(true)
    try {
      const datos = await apiFetch<{ access_token: string }>(
        '/api/auth/login',
        { method: 'POST', body: JSON.stringify({ email, password }) }
      )
      await setToken(datos.access_token)

      const usuario = await apiFetch<{
        id: number; email: string; nombre: string; rol: string
        plan_tier: string; gestoria_id: number | null; empresas_asignadas: number[]
      }>('/api/auth/me')
      setUsuario(usuario)

      if (usuario.rol === 'cliente') {
        const empresaId = usuario.empresas_asignadas?.[0]
        if (empresaId) {
          try {
            const onb = await apiFetch<{ estado: string }>(
              `/api/onboarding/cliente/${empresaId}`
            )
            if (onb.estado === 'pendiente_cliente') {
              router.replace(`/onboarding/${empresaId}`)
              return
            }
          } catch { /* ignorar */ }
        }
        router.replace('/(empresario)/')
      } else {
        router.replace('/(gestor)/')
      }
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'No se pudo iniciar sesión')
    } finally {
      setCargando(false)
    }
  }

  return (
    <View className="flex-1 bg-slate-950 items-center justify-center px-6">
      <View className="w-16 h-16 bg-amber-400 rounded-2xl items-center justify-center mb-6">
        <Text className="text-2xl font-bold text-slate-900">S</Text>
      </View>
      <Text className="text-3xl font-semibold text-white mb-1">SFCE</Text>
      <Text className="text-slate-400 text-sm mb-8">Gestión contable inteligente</Text>

      <View className="w-full bg-slate-900 rounded-2xl p-6 gap-4">
        <View className="gap-1.5">
          <Text className="text-sm text-slate-300">Email</Text>
          <TextInput
            className="bg-slate-800 text-white rounded-xl px-4 py-3"
            placeholder="tu@email.com"
            placeholderTextColor="#64748b"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>
        <View className="gap-1.5">
          <Text className="text-sm text-slate-300">Contraseña</Text>
          <TextInput
            className="bg-slate-800 text-white rounded-xl px-4 py-3"
            placeholder="Mínimo 8 caracteres"
            placeholderTextColor="#64748b"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />
        </View>
        <TouchableOpacity
          className="bg-amber-400 rounded-xl py-3 items-center mt-2"
          onPress={handleLogin}
          disabled={cargando}
        >
          {cargando
            ? <ActivityIndicator color="#1e293b" />
            : <Text className="text-slate-900 font-semibold">Entrar</Text>
          }
        </TouchableOpacity>
      </View>
    </View>
  )
}
```

**Step 4: Verificar que compila**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/mobile
npx tsc --noEmit 2>&1 | tail -15
```
Expected: 0 errores TypeScript

**Step 5: Commit**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
git add mobile/app/
git commit -m "feat: root layout auth guard + pantalla login — Expo Router"
```

---

### Task 5: Tabs empresario — Home + Perfil

**Files:**
- Create: `mobile/app/(empresario)/_layout.tsx`
- Create: `mobile/app/(empresario)/index.tsx`
- Create: `mobile/app/(empresario)/perfil.tsx`

**Step 1: Layout con bottom tabs**

```tsx
// mobile/app/(empresario)/_layout.tsx
import { Tabs } from 'expo-router'
import { Home, Upload, Bell, User } from 'lucide-react-native'

export default function EmpresarioLayout() {
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarStyle: { backgroundColor: '#0f172a', borderTopColor: '#1e293b' },
      tabBarActiveTintColor: '#fbbf24',
      tabBarInactiveTintColor: '#64748b',
    }}>
      <Tabs.Screen name="index" options={{ title: 'Inicio', tabBarIcon: ({ color }) => <Home size={22} color={color} /> }} />
      <Tabs.Screen name="subir" options={{ title: 'Subir', tabBarIcon: ({ color }) => <Upload size={22} color={color} /> }} />
      <Tabs.Screen name="notificaciones" options={{ title: 'Alertas', tabBarIcon: ({ color }) => <Bell size={22} color={color} /> }} />
      <Tabs.Screen name="perfil" options={{ title: 'Perfil', tabBarIcon: ({ color }) => <User size={22} color={color} /> }} />
    </Tabs>
  )
}
```

Instalar lucide-react-native:
```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/mobile && npm install lucide-react-native react-native-svg
```

**Step 2: Home empresario**

```tsx
// mobile/app/(empresario)/index.tsx
import { View, Text, ScrollView, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'

interface Resumen {
  nombre: string; ejercicio: string
  resultado_acumulado: number
  importe_pendiente_cobro: number; facturas_pendientes_cobro: number
  importe_pendiente_pago: number; facturas_pendientes_pago: number
}

interface Documento {
  id: number; nombre: string; tipo: string; estado: string; fecha: string | null
}

function fmt(n: number) {
  return n.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

export default function HomeEmpresario() {
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0]

  const { data: resumen, isLoading } = useQuery({
    queryKey: ['resumen', empresaId],
    queryFn: () => apiFetch<Resumen>(`/api/portal/${empresaId}/resumen`),
    enabled: !!empresaId,
  })

  const { data: docsData } = useQuery({
    queryKey: ['documentos', empresaId],
    queryFn: () => apiFetch<{ documentos: Documento[] }>(`/api/portal/${empresaId}/documentos`),
    enabled: !!empresaId,
  })

  if (isLoading) return (
    <View className="flex-1 bg-slate-950 items-center justify-center">
      <ActivityIndicator color="#fbbf24" />
    </View>
  )

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-4">
      <View className="mt-8">
        <Text className="text-2xl font-bold text-white">{resumen?.nombre ?? 'Mi empresa'}</Text>
        <Text className="text-slate-400 text-sm">Ejercicio {resumen?.ejercicio}</Text>
      </View>

      {/* KPIs */}
      <View className="flex-row gap-3">
        <View className="flex-1 bg-slate-900 rounded-xl p-4">
          <Text className="text-xs text-slate-400">Resultado</Text>
          <Text className={`text-lg font-bold mt-1 ${(resumen?.resultado_acumulado ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {fmt(resumen?.resultado_acumulado ?? 0)}
          </Text>
        </View>
        <View className="flex-1 bg-slate-900 rounded-xl p-4">
          <Text className="text-xs text-slate-400">Cobros pend.</Text>
          <Text className="text-lg font-bold mt-1 text-blue-400">{fmt(resumen?.importe_pendiente_cobro ?? 0)}</Text>
          <Text className="text-xs text-slate-500">{resumen?.facturas_pendientes_cobro} fact.</Text>
        </View>
      </View>

      {/* Documentos recientes */}
      <Text className="text-sm font-semibold text-slate-300">Documentos recientes</Text>
      {(docsData?.documentos ?? []).slice(0, 15).map((d) => (
        <View key={d.id} className="bg-slate-900 rounded-xl px-4 py-3 flex-row items-center gap-3">
          <View className="bg-slate-700 rounded-lg px-2 py-0.5">
            <Text className="text-[10px] text-slate-300 uppercase">{d.tipo}</Text>
          </View>
          <Text className="flex-1 text-slate-200 text-sm" numberOfLines={1}>{d.nombre}</Text>
          <View className={`rounded-full px-2 py-0.5 ${d.estado === 'procesado' ? 'bg-emerald-900' : 'bg-amber-900'}`}>
            <Text className={`text-[10px] ${d.estado === 'procesado' ? 'text-emerald-300' : 'text-amber-300'}`}>{d.estado}</Text>
          </View>
        </View>
      ))}
    </ScrollView>
  )
}
```

**Step 3: Perfil**

```tsx
// mobile/app/(empresario)/perfil.tsx
import { View, Text, TouchableOpacity } from 'react-native'
import { router } from 'expo-router'
import { useAuthStore } from '@/store/auth'

const TIER_LABEL: Record<string, string> = { basico: 'Básico', pro: 'Pro', premium: 'Premium' }
const TIER_COLOR: Record<string, string> = { basico: '#94a3b8', pro: '#60a5fa', premium: '#fbbf24' }

export default function PerfilEmpresario() {
  const { usuario, cerrarSesion } = useAuthStore()

  const handleLogout = async () => {
    await cerrarSesion()
    router.replace('/(auth)/login')
  }

  return (
    <View className="flex-1 bg-slate-950 p-5 mt-12 gap-4">
      <Text className="text-2xl font-bold text-white">Mi perfil</Text>

      <View className="bg-slate-900 rounded-2xl p-5 gap-3">
        <View>
          <Text className="text-xs text-slate-400">Nombre</Text>
          <Text className="text-white font-medium mt-0.5">{usuario?.nombre}</Text>
        </View>
        <View>
          <Text className="text-xs text-slate-400">Email</Text>
          <Text className="text-white mt-0.5">{usuario?.email}</Text>
        </View>
        <View>
          <Text className="text-xs text-slate-400">Plan</Text>
          <Text style={{ color: TIER_COLOR[usuario?.plan_tier ?? 'basico'] }} className="font-semibold mt-0.5">
            {TIER_LABEL[usuario?.plan_tier ?? 'basico'] ?? 'Básico'}
          </Text>
        </View>
      </View>

      <TouchableOpacity
        className="bg-red-900/50 border border-red-700 rounded-xl py-4 items-center"
        onPress={handleLogout}
      >
        <Text className="text-red-300 font-medium">Cerrar sesión</Text>
      </TouchableOpacity>
    </View>
  )
}
```

**Step 4: Verificar TypeScript**

```bash
cd mobile && npx tsc --noEmit 2>&1 | tail -10
```

**Step 5: Commit**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
git add mobile/app/\(empresario\)/
git commit -m "feat: tabs empresario — Home KPIs + Perfil"
```

---

### Task 6: Upload empresario — wizard 4 pasos

**Files:**
- Create: `mobile/components/upload/ProveedorSelector.tsx`
- Create: `mobile/components/upload/CamaraCaptura.tsx`
- Create: `mobile/app/(empresario)/subir.tsx`

**Step 1: ProveedorSelector**

```tsx
// mobile/components/upload/ProveedorSelector.tsx
import { useState } from 'react'
import { View, Text, TouchableOpacity, TextInput, FlatList, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'
import { Plus, Check } from 'lucide-react-native'

interface Proveedor { cif: string; nombre: string; tipo_doc_sugerido?: string }
interface Props {
  empresaId: number
  onSeleccionar: (p: Proveedor) => void
  seleccionado: Proveedor | null
}

export function ProveedorSelector({ empresaId, onSeleccionar, seleccionado }: Props) {
  const [modoNuevo, setModoNuevo] = useState(false)
  const [cifNuevo, setCifNuevo] = useState('')
  const [nombreNuevo, setNombreNuevo] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['proveedores', empresaId],
    queryFn: () => apiFetch<{ proveedores: Proveedor[] }>(`/api/portal/${empresaId}/proveedores-frecuentes`),
  })

  if (isLoading) return <ActivityIndicator color="#fbbf24" className="py-4" />

  const proveedores = data?.proveedores ?? []

  if (modoNuevo) {
    return (
      <View className="gap-3">
        <Text className="text-slate-300 text-sm font-medium">Nuevo proveedor</Text>
        <TextInput
          className="bg-slate-800 text-white rounded-xl px-4 py-3"
          placeholder="CIF / NIF (ej: B12345678)"
          placeholderTextColor="#64748b"
          value={cifNuevo}
          onChangeText={setCifNuevo}
          autoCapitalize="characters"
        />
        <TextInput
          className="bg-slate-800 text-white rounded-xl px-4 py-3"
          placeholder="Nombre o razón social"
          placeholderTextColor="#64748b"
          value={nombreNuevo}
          onChangeText={setNombreNuevo}
        />
        <TouchableOpacity
          className="bg-amber-400 rounded-xl py-3 items-center"
          onPress={() => {
            if (nombreNuevo.trim()) {
              onSeleccionar({ cif: cifNuevo.trim(), nombre: nombreNuevo.trim() })
              setModoNuevo(false)
            }
          }}
        >
          <Text className="text-slate-900 font-semibold">Usar este proveedor</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => setModoNuevo(false)}>
          <Text className="text-slate-400 text-center text-sm">← Volver a la lista</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <View className="gap-3">
      {proveedores.map((p) => (
        <TouchableOpacity
          key={p.cif ?? p.nombre}
          className={`flex-row items-center gap-3 bg-slate-900 rounded-xl px-4 py-3 ${seleccionado?.nombre === p.nombre ? 'border border-amber-400' : ''}`}
          onPress={() => onSeleccionar(p)}
        >
          {seleccionado?.nombre === p.nombre && <Check size={16} color="#fbbf24" />}
          <View className="flex-1">
            <Text className="text-white font-medium">{p.nombre}</Text>
            {p.cif && <Text className="text-slate-400 text-xs">{p.cif}</Text>}
          </View>
        </TouchableOpacity>
      ))}
      <TouchableOpacity
        className="flex-row items-center gap-2 border border-dashed border-slate-600 rounded-xl px-4 py-3"
        onPress={() => setModoNuevo(true)}
      >
        <Plus size={16} color="#94a3b8" />
        <Text className="text-slate-400">Añadir nuevo proveedor</Text>
      </TouchableOpacity>
    </View>
  )
}
```

**Step 2: Pantalla subir (wizard 4 pasos)**

```tsx
// mobile/app/(empresario)/subir.tsx
import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, Alert, ActivityIndicator } from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import { router } from 'expo-router'
import { useAuthStore } from '@/store/auth'
import { ProveedorSelector } from '@/components/upload/ProveedorSelector'
import { apiUpload } from '@/hooks/useApi'
import { useTiene } from '@/hooks/useTiene'
import { Camera, Image, CheckCircle } from 'lucide-react-native'

const TIPOS_DOC = ['Factura', 'Ticket', 'Nómina', 'Extracto', 'Otro']

interface Proveedor { cif: string; nombre: string }

export default function SubirDocumento() {
  const puedeSubir = useTiene('subir_docs')
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0]

  const [paso, setPaso] = useState(0)
  const [tipo, setTipo] = useState<string | null>(null)
  const [archivo, setArchivo] = useState<ImagePicker.ImagePickerAsset | null>(null)
  const [proveedor, setProveedor] = useState<Proveedor | null>(null)
  const [enviando, setEnviando] = useState(false)

  if (!puedeSubir) {
    return (
      <View className="flex-1 bg-slate-950 items-center justify-center p-6">
        <Text className="text-4xl mb-4">🔒</Text>
        <Text className="text-white text-lg font-semibold text-center">Disponible en Plan Pro</Text>
        <Text className="text-slate-400 text-sm text-center mt-2">
          Actualiza tu plan para subir documentos desde la app.
        </Text>
      </View>
    )
  }

  const seleccionarImagen = async (fuente: 'camara' | 'galeria') => {
    let resultado: ImagePicker.ImagePickerResult
    if (fuente === 'camara') {
      const { status } = await ImagePicker.requestCameraPermissionsAsync()
      if (status !== 'granted') { Alert.alert('Permiso denegado', 'Necesitamos acceso a la cámara'); return }
      resultado = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.8 })
    } else {
      resultado = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.8 })
    }
    if (!resultado.canceled && resultado.assets[0]) {
      setArchivo(resultado.assets[0])
      setPaso(2)
    }
  }

  const enviar = async () => {
    if (!empresaId || !archivo || !tipo) return
    setEnviando(true)
    try {
      const form = new FormData()
      // @ts-ignore — React Native FormData acepta este formato
      form.append('archivo', { uri: archivo.uri, name: archivo.fileName ?? 'doc.jpg', type: archivo.mimeType ?? 'image/jpeg' })
      form.append('tipo', tipo)
      if (proveedor?.cif) form.append('proveedor_cif', proveedor.cif)
      if (proveedor?.nombre) form.append('proveedor_nombre', proveedor.nombre)

      await apiUpload(`/api/portal/${empresaId}/documentos/subir`, form)
      setPaso(4)  // éxito
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'No se pudo enviar el documento')
    } finally {
      setEnviando(false)
    }
  }

  // Paso 4: éxito
  if (paso === 4) {
    return (
      <View className="flex-1 bg-slate-950 items-center justify-center p-6 gap-4">
        <CheckCircle size={64} color="#34d399" />
        <Text className="text-white text-xl font-bold">Documento enviado</Text>
        <Text className="text-slate-400 text-center">Tu gestoría lo procesará en breve.</Text>
        <TouchableOpacity className="bg-amber-400 rounded-xl px-8 py-3" onPress={() => { setPaso(0); setTipo(null); setArchivo(null); setProveedor(null); router.replace('/(empresario)/') }}>
          <Text className="text-slate-900 font-semibold">Volver al inicio</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-5">
      <Text className="text-2xl font-bold text-white mt-8">Subir documento</Text>

      {/* Stepper */}
      <View className="flex-row gap-1">
        {['Tipo', 'Archivo', 'Proveedor', 'Confirmar'].map((nombre, i) => (
          <View key={i} className={`flex-1 py-1.5 rounded items-center ${i === paso ? 'bg-amber-400' : i < paso ? 'bg-emerald-700' : 'bg-slate-800'}`}>
            <Text className={`text-xs font-medium ${i === paso ? 'text-slate-900' : i < paso ? 'text-white' : 'text-slate-500'}`}>{nombre}</Text>
          </View>
        ))}
      </View>

      {/* Paso 0: tipo */}
      {paso === 0 && (
        <View className="gap-3">
          <Text className="text-slate-300">¿Qué tipo de documento es?</Text>
          {TIPOS_DOC.map((t) => (
            <TouchableOpacity
              key={t}
              className={`bg-slate-900 rounded-xl px-4 py-4 ${tipo === t ? 'border border-amber-400' : ''}`}
              onPress={() => { setTipo(t); setPaso(1) }}
            >
              <Text className="text-white font-medium">{t}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Paso 1: archivo */}
      {paso === 1 && (
        <View className="gap-3">
          <Text className="text-slate-300">Selecciona o captura el documento</Text>
          <TouchableOpacity className="bg-slate-900 rounded-xl p-6 items-center gap-3" onPress={() => seleccionarImagen('camara')}>
            <Camera size={32} color="#fbbf24" />
            <Text className="text-white font-medium">Usar cámara</Text>
          </TouchableOpacity>
          <TouchableOpacity className="bg-slate-900 rounded-xl p-6 items-center gap-3" onPress={() => seleccionarImagen('galeria')}>
            <Image size={32} color="#94a3b8" />
            <Text className="text-slate-300">Elegir de galería</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Paso 2: proveedor */}
      {paso === 2 && empresaId && (
        <View className="gap-3">
          <Text className="text-slate-300">¿De qué proveedor es?</Text>
          <ProveedorSelector
            empresaId={empresaId}
            seleccionado={proveedor}
            onSeleccionar={(p) => { setProveedor(p); setPaso(3) }}
          />
          <TouchableOpacity onPress={() => setPaso(3)}>
            <Text className="text-slate-500 text-center text-sm">Saltar (asignar después)</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Paso 3: confirmar */}
      {paso === 3 && (
        <View className="gap-4">
          <Text className="text-slate-300">Resumen</Text>
          <View className="bg-slate-900 rounded-xl p-4 gap-2">
            <Text className="text-slate-400 text-sm">Tipo: <Text className="text-white">{tipo}</Text></Text>
            <Text className="text-slate-400 text-sm">Archivo: <Text className="text-white">{archivo?.fileName ?? 'imagen.jpg'}</Text></Text>
            {proveedor && <Text className="text-slate-400 text-sm">Proveedor: <Text className="text-white">{proveedor.nombre}</Text></Text>}
          </View>
          <TouchableOpacity
            className="bg-amber-400 rounded-xl py-4 items-center"
            onPress={enviar}
            disabled={enviando}
          >
            {enviando ? <ActivityIndicator color="#1e293b" /> : <Text className="text-slate-900 font-semibold">Enviar documento</Text>}
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  )
}
```

**Step 3: Commit**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
git add mobile/components/ mobile/app/\(empresario\)/subir.tsx
git commit -m "feat: upload wizard empresario 4 pasos — tipo, archivo, proveedor, confirmar"
```

---

### Task 7: Notificaciones + Tabs gestor

**Files:**
- Create: `mobile/app/(empresario)/notificaciones.tsx`
- Create: `mobile/app/(gestor)/_layout.tsx`
- Create: `mobile/app/(gestor)/index.tsx`
- Create: `mobile/app/(gestor)/alertas.tsx`
- Create: `mobile/app/(gestor)/subir.tsx`

**Step 1: Notificaciones empresario**

```tsx
// mobile/app/(empresario)/notificaciones.tsx
import { View, Text, ScrollView, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'
import { AlertCircle, Info, CheckCircle } from 'lucide-react-native'

interface Notificacion {
  tipo: string; prioridad: string; titulo: string; descripcion?: string
}

const PRIORIDAD_COLOR: Record<string, string> = { alta: '#f87171', media: '#fbbf24', baja: '#94a3b8' }
const PRIORIDAD_ICON = {
  alta: AlertCircle,
  media: Info,
  baja: CheckCircle,
}

export default function NotificacionesEmpresario() {
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0]

  const { data, isLoading } = useQuery({
    queryKey: ['notificaciones', empresaId],
    queryFn: () => apiFetch<{ notificaciones: Notificacion[] }>(`/api/portal/${empresaId}/notificaciones`),
    enabled: !!empresaId,
  })

  if (isLoading) return <View className="flex-1 bg-slate-950 items-center justify-center"><ActivityIndicator color="#fbbf24" /></View>

  const notificaciones = data?.notificaciones ?? []

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-4">
      <Text className="text-2xl font-bold text-white mt-8">Notificaciones</Text>
      {notificaciones.length === 0
        ? <Text className="text-slate-400 text-center py-8">Sin notificaciones pendientes</Text>
        : notificaciones.map((n, i) => {
            const Icon = PRIORIDAD_ICON[n.prioridad] ?? Info
            return (
              <View key={i} className="bg-slate-900 rounded-xl p-4 flex-row gap-3">
                <Icon size={20} color={PRIORIDAD_COLOR[n.prioridad] ?? '#94a3b8'} />
                <View className="flex-1">
                  <Text className="text-white font-medium">{n.titulo}</Text>
                  {n.descripcion && <Text className="text-slate-400 text-sm mt-0.5">{n.descripcion}</Text>}
                </View>
              </View>
            )
          })
      }
    </ScrollView>
  )
}
```

**Step 2: Layout tabs gestor**

```tsx
// mobile/app/(gestor)/_layout.tsx
import { Tabs } from 'expo-router'
import { Building2, Upload, Bell } from 'lucide-react-native'

export default function GestorLayout() {
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarStyle: { backgroundColor: '#0f172a', borderTopColor: '#1e293b' },
      tabBarActiveTintColor: '#fbbf24',
      tabBarInactiveTintColor: '#64748b',
    }}>
      <Tabs.Screen name="index" options={{ title: 'Empresas', tabBarIcon: ({ color }) => <Building2 size={22} color={color} /> }} />
      <Tabs.Screen name="subir" options={{ title: 'Subir', tabBarIcon: ({ color }) => <Upload size={22} color={color} /> }} />
      <Tabs.Screen name="alertas" options={{ title: 'Alertas', tabBarIcon: ({ color }) => <Bell size={22} color={color} /> }} />
    </Tabs>
  )
}
```

**Step 3: Lista empresas gestor**

```tsx
// mobile/app/(gestor)/index.tsx
import { View, Text, ScrollView, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

interface Empresa { id: number; nombre: string; cif: string; estado_onboarding: string }

const ESTADO_COLOR: Record<string, string> = {
  configurada: '#34d399',
  pendiente_cliente: '#fbbf24',
  cliente_completado: '#60a5fa',
  esqueleto: '#94a3b8',
}

export default function EmpresasGestor() {
  const { data, isLoading } = useQuery({
    queryKey: ['gestor-resumen'],
    queryFn: () => apiFetch<{ empresas: Empresa[] }>('/api/gestor/resumen'),
  })

  if (isLoading) return <View className="flex-1 bg-slate-950 items-center justify-center"><ActivityIndicator color="#fbbf24" /></View>

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-3">
      <Text className="text-2xl font-bold text-white mt-8">Mis empresas</Text>
      <Text className="text-slate-400 text-sm">{data?.empresas.length ?? 0} empresas gestionadas</Text>
      {(data?.empresas ?? []).map((e) => (
        <View key={e.id} className="bg-slate-900 rounded-xl px-4 py-3 flex-row items-center gap-3">
          <View className="w-2 h-2 rounded-full" style={{ backgroundColor: ESTADO_COLOR[e.estado_onboarding] ?? '#94a3b8' }} />
          <View className="flex-1">
            <Text className="text-white font-medium">{e.nombre}</Text>
            <Text className="text-slate-400 text-xs">{e.cif}</Text>
          </View>
          {e.estado_onboarding !== 'configurada' && (
            <Text className="text-xs text-amber-400">{e.estado_onboarding.replace('_', ' ')}</Text>
          )}
        </View>
      ))}
    </ScrollView>
  )
}
```

**Step 4: Alertas gestor**

```tsx
// mobile/app/(gestor)/alertas.tsx
import { View, Text, ScrollView, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'
import { AlertTriangle, CheckCircle2 } from 'lucide-react-native'

interface Alerta { tipo: string; prioridad: string; titulo: string; descripcion?: string }

export default function AlertasGestor() {
  const { data, isLoading } = useQuery({
    queryKey: ['gestor-alertas'],
    queryFn: () => apiFetch<{ alertas: Alerta[] }>('/api/gestor/alertas'),
  })

  if (isLoading) return <View className="flex-1 bg-slate-950 items-center justify-center"><ActivityIndicator color="#fbbf24" /></View>

  const alertas = data?.alertas ?? []

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-4">
      <Text className="text-2xl font-bold text-white mt-8">Alertas</Text>
      {alertas.length === 0
        ? (
          <View className="items-center py-12 gap-3">
            <CheckCircle2 size={48} color="#34d399" />
            <Text className="text-slate-400">Todo en orden</Text>
          </View>
        )
        : alertas.map((a, i) => (
          <View key={i} className="bg-slate-900 rounded-xl p-4 gap-2">
            <View className="flex-row items-center gap-2">
              <AlertTriangle size={16} color={a.prioridad === 'alta' ? '#f87171' : '#fbbf24'} />
              <Text className="text-white font-semibold">{a.titulo}</Text>
            </View>
            {a.descripcion && <Text className="text-slate-400 text-sm">{a.descripcion}</Text>}
          </View>
        ))
      }
    </ScrollView>
  )
}
```

**Step 5: Upload gestor (simplificado — mismo wizard con paso extra de empresa)**

Para v1, el gestor usa el mismo endpoint pero con selección de empresa primero. Crear `mobile/app/(gestor)/subir.tsx` con el mismo patrón que el empresario pero con un paso 0 adicional: picker de empresa de la lista del gestor.

> Nota: implementar con el mismo patrón del wizard empresario pero añadiendo `<Paso 0: seleccionar empresa>` al inicio. El empresaId viene del picker en lugar del store.

El código es análogo a `app/(empresario)/subir.tsx` — añadir estado `empresaSeleccionada` y un primer paso con `FlatList` de empresas del gestor.

**Step 6: Commit**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
git add mobile/app/\(empresario\)/notificaciones.tsx mobile/app/\(gestor\)/
git commit -m "feat: notificaciones empresario + tabs gestor (empresas, upload, alertas)"
```

---

### Task 8: Wizard onboarding móvil

**Files:**
- Create: `mobile/app/onboarding/[id].tsx`

El wizard móvil replica los 3 pasos del web. Mismo endpoint: `PUT /api/onboarding/cliente/{id}`.

```tsx
// mobile/app/onboarding/[id].tsx
import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, Alert, ActivityIndicator } from 'react-native'
import { useLocalSearchParams, router } from 'expo-router'
import { apiFetch } from '@/hooks/useApi'

const PASOS = ['Datos empresa', 'Cuenta bancaria', 'Documentación']

export default function OnboardingMovil() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const empresaId = Number(id)
  const [paso, setPaso] = useState(0)
  const [datos, setDatos] = useState({
    domicilio: '', telefono: '', persona_contacto: '',
    iban: '', banco_nombre: '',
    email_facturas: '', proveedores: [] as string[],
    nuevo_proveedor: '',
  })
  const [enviando, setEnviando] = useState(false)

  const actualizar = (campo: string, valor: string) =>
    setDatos((d) => ({ ...d, [campo]: valor }))

  const agregarProveedor = () => {
    const nombre = datos.nuevo_proveedor.trim()
    if (nombre && !datos.proveedores.includes(nombre)) {
      setDatos((d) => ({ ...d, proveedores: [...d.proveedores, nombre], nuevo_proveedor: '' }))
    }
  }

  const enviar = async () => {
    setEnviando(true)
    try {
      await apiFetch(`/api/onboarding/cliente/${empresaId}`, {
        method: 'PUT',
        body: JSON.stringify({
          iban: datos.iban, banco_nombre: datos.banco_nombre,
          email_facturas: datos.email_facturas, proveedores: datos.proveedores,
        }),
      })
      router.replace('/(empresario)/')
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'No se pudo guardar')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-5">
      <View className="mt-8">
        <Text className="text-2xl font-bold text-white">Completa tu alta</Text>
        <Text className="text-slate-400 text-sm mt-1">Tu gestoría ha iniciado el proceso.</Text>
      </View>

      {/* Stepper */}
      <View className="flex-row gap-1">
        {PASOS.map((nombre, i) => (
          <View key={i} className={`flex-1 py-1.5 rounded items-center ${i === paso ? 'bg-amber-400' : i < paso ? 'bg-emerald-700' : 'bg-slate-800'}`}>
            <Text className={`text-xs ${i === paso ? 'text-slate-900 font-semibold' : i < paso ? 'text-white' : 'text-slate-500'}`}>{nombre}</Text>
          </View>
        ))}
      </View>

      {/* Paso 0 */}
      {paso === 0 && (
        <View className="gap-3">
          <Text className="text-slate-300">Datos de tu empresa</Text>
          {[
            { campo: 'domicilio', label: 'Domicilio fiscal', placeholder: 'Calle Mayor 1, 28001 Madrid' },
            { campo: 'telefono', label: 'Teléfono (opcional)', placeholder: '600 000 000' },
            { campo: 'persona_contacto', label: 'Persona de contacto', placeholder: 'Juan García' },
          ].map(({ campo, label, placeholder }) => (
            <View key={campo} className="gap-1">
              <Text className="text-sm text-slate-400">{label}</Text>
              <TextInput
                className="bg-slate-800 text-white rounded-xl px-4 py-3"
                placeholder={placeholder}
                placeholderTextColor="#64748b"
                value={(datos as Record<string, string>)[campo]}
                onChangeText={(v) => actualizar(campo, v)}
              />
            </View>
          ))}
          <TouchableOpacity className="bg-amber-400 rounded-xl py-4 items-center mt-2" onPress={() => setPaso(1)}>
            <Text className="text-slate-900 font-semibold">Siguiente →</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Paso 1 */}
      {paso === 1 && (
        <View className="gap-3">
          <Text className="text-slate-300">Cuenta bancaria</Text>
          {[
            { campo: 'iban', label: 'IBAN', placeholder: 'ES91 2100 0418 4502 0005 1332' },
            { campo: 'banco_nombre', label: 'Banco', placeholder: 'CaixaBank' },
          ].map(({ campo, label, placeholder }) => (
            <View key={campo} className="gap-1">
              <Text className="text-sm text-slate-400">{label}</Text>
              <TextInput
                className="bg-slate-800 text-white rounded-xl px-4 py-3"
                placeholder={placeholder}
                placeholderTextColor="#64748b"
                value={(datos as Record<string, string>)[campo]}
                onChangeText={(v) => actualizar(campo, v)}
                autoCapitalize="characters"
              />
            </View>
          ))}
          <TouchableOpacity className="bg-amber-400 rounded-xl py-4 items-center mt-2" onPress={() => setPaso(2)}>
            <Text className="text-slate-900 font-semibold">Siguiente →</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Paso 2 */}
      {paso === 2 && (
        <View className="gap-3">
          <Text className="text-slate-300">Documentación</Text>
          <View className="gap-1">
            <Text className="text-sm text-slate-400">Email de facturas</Text>
            <TextInput
              className="bg-slate-800 text-white rounded-xl px-4 py-3"
              placeholder="facturas@miempresa.com"
              placeholderTextColor="#64748b"
              value={datos.email_facturas}
              onChangeText={(v) => actualizar('email_facturas', v)}
              keyboardType="email-address"
              autoCapitalize="none"
            />
          </View>
          <View className="gap-1">
            <Text className="text-sm text-slate-400">Proveedores habituales</Text>
            <View className="flex-row gap-2">
              <TextInput
                className="flex-1 bg-slate-800 text-white rounded-xl px-4 py-3"
                placeholder="Repsol, Endesa..."
                placeholderTextColor="#64748b"
                value={datos.nuevo_proveedor}
                onChangeText={(v) => actualizar('nuevo_proveedor', v)}
                onSubmitEditing={agregarProveedor}
              />
              <TouchableOpacity className="bg-slate-700 rounded-xl px-4 items-center justify-center" onPress={agregarProveedor}>
                <Text className="text-white">+</Text>
              </TouchableOpacity>
            </View>
            <View className="flex-row flex-wrap gap-2 pt-1">
              {datos.proveedores.map((p) => (
                <TouchableOpacity
                  key={p}
                  className="bg-slate-700 rounded-full px-3 py-1"
                  onPress={() => setDatos((d) => ({ ...d, proveedores: d.proveedores.filter((x) => x !== p) }))}
                >
                  <Text className="text-slate-300 text-xs">{p} ✕</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
          <TouchableOpacity
            className="bg-amber-400 rounded-xl py-4 items-center mt-2"
            onPress={enviar}
            disabled={enviando}
          >
            {enviando ? <ActivityIndicator color="#1e293b" /> : <Text className="text-slate-900 font-semibold">Completar alta</Text>}
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  )
}
```

**Step 2: Commit**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
git add mobile/app/onboarding/
git commit -m "feat: wizard onboarding móvil 3 pasos — replica flujo web en React Native"
```

---

### Task 9: Verificación final

**Step 1: TypeScript sin errores**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/mobile
npx tsc --noEmit 2>&1 | tail -20
```
Expected: 0 errores

**Step 2: Arrancar servidor backend**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
export $(grep -v '^#' .env | xargs)
uvicorn sfce.api.app:crear_app --factory --port 8000 --host 0.0.0.0
```

**Step 3: Arrancar app en modo web (prueba rápida)**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD/mobile
EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start --web
```

Verificar en http://localhost:8081:
- [ ] Login screen visible
- [ ] Login con admin@sfce.local / admin → redirige a tabs gestor
- [ ] Tab "Empresas" muestra lista

**Step 4: Test backend nuevos endpoints**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_onboarding.py::test_proveedores_frecuentes_vacio tests/test_onboarding.py::test_proveedores_frecuentes_devuelve_reglas -v 2>&1 | tail -10
```
Expected: PASS

**Step 5: Commit final**

```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
git add mobile/
git commit -m "feat: app móvil SFCE v1 — Expo Router, dual mode, upload con intake rápido"
```

---

## Resumen de entregables

| Entregable | Ruta | Task |
|-----------|------|------|
| Endpoint proveedores-frecuentes | `sfce/api/rutas/portal.py` | 1 |
| Scaffold Expo + NativeWind | `mobile/` | 2 |
| Auth store + useApi + useTiene | `mobile/store/`, `mobile/hooks/` | 3 |
| Root layout + auth guard | `mobile/app/_layout.tsx` | 4 |
| Login screen | `mobile/app/(auth)/login.tsx` | 4 |
| Home empresario + Perfil | `mobile/app/(empresario)/` | 5 |
| Upload wizard 4 pasos | `mobile/app/(empresario)/subir.tsx` | 6 |
| ProveedorSelector | `mobile/components/upload/` | 6 |
| Notificaciones empresario | `mobile/app/(empresario)/notificaciones.tsx` | 7 |
| Tabs gestor (empresas, alertas, upload) | `mobile/app/(gestor)/` | 7 |
| Wizard onboarding móvil | `mobile/app/onboarding/[id].tsx` | 8 |
