# Design: Sistema de Tiers Básico/Pro/Premium — SFCE

**Fecha**: 2026-03-01
**Estado**: Aprobado
**Sesión**: 5 (paralela a implementación onboarding)

---

## Contexto

SFCE es un SaaS B2B2C. Hay dos clientes:
- **Gestoría**: el despacho contable (B2B). Paga por capacidad.
- **Empresario**: el negocio gestionado (B2B2C). Paga por funcionalidades.

Los tiers definen qué puede hacer cada uno. El contenido exacto de cada tier (números y features concretas) se decide comercialmente y se configura en un dict — sin tocar lógica de negocio.

---

## Modelo de negocio — Dos ejes independientes

### Eje 1: Plan de la Gestoría (capacidad)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `plan_tier` | `'basico'|'pro'|'premium'` | Tier del plan contratado |
| `limite_empresas` | `Integer|None` | Máx. empresas gestionadas. `None` = ilimitado |

Los números exactos por tier (`limite_empresas`) se asignan manualmente por el superadmin hasta que se decida la tabla comercial.

### Eje 2: Plan del Empresario (funcionalidades)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `plan_tier` | `'basico'|'pro'|'premium'` | Tier del empresario |

El tier del empresario lo asigna el gestor/superadmin al invitarle o desde el panel de usuarios.

---

## Implementación — Enfoque A (plan_tier simple, sin overrides)

Un solo campo `plan_tier` por entidad. Sin tablas de permisos ni JSON de módulos adicionales. YAGNI.

---

## Helper de tiers: `sfce/core/tiers.py`

```python
from enum import IntEnum

class Tier(IntEnum):
    BASICO   = 1
    PRO      = 2
    PREMIUM  = 3

TIER_MAP = {"basico": Tier.BASICO, "pro": Tier.PRO, "premium": Tier.PREMIUM}

# Contenido de tiers — EDITAR AQUÍ cuando se decida comercialmente.
# Clave: nombre de feature. Valor: tier mínimo requerido.

FEATURES_GESTORIA: dict[str, Tier] = {
    # Pendiente decisión comercial
    # Ejemplo: "soporte_prioritario": Tier.PREMIUM,
}

FEATURES_EMPRESARIO: dict[str, Tier] = {
    "consultar":     Tier.BASICO,    # KPIs, documentos procesados
    "subir_docs":    Tier.PRO,       # upload desde cámara/web
    "app_movil":     Tier.PRO,       # acceso a la app React Native
    "firmar":        Tier.PREMIUM,   # firma digital legal
    "chat_gestor":   Tier.PREMIUM,   # mensajería interna con el gestor
}


def tiene_feature_empresario(usuario, feature: str) -> bool:
    tier_usuario = TIER_MAP.get(getattr(usuario, "plan_tier", "basico"), Tier.BASICO)
    tier_requerido = FEATURES_EMPRESARIO.get(feature, Tier.PREMIUM)
    return tier_usuario >= tier_requerido


def tiene_feature_gestoria(gestoria, feature: str) -> bool:
    tier_gestoria = TIER_MAP.get(getattr(gestoria, "plan_tier", "basico"), Tier.BASICO)
    tier_requerido = FEATURES_GESTORIA.get(feature, Tier.PREMIUM)
    return tier_gestoria >= tier_requerido


def verificar_limite_empresas(gestoria, cuenta_actual: int) -> bool:
    """False si la gestoría ha alcanzado su límite de empresas."""
    limite = getattr(gestoria, "limite_empresas", None)
    if limite is None:
        return True
    return cuenta_actual < limite
```

### Uso en endpoints

```python
from sfce.core.tiers import tiene_feature_empresario

@router.post("/{empresa_id}/documentos/subir")
def subir_documento(empresa_id: int, usuario=Depends(obtener_usuario_actual)):
    if not tiene_feature_empresario(usuario, "subir_docs"):
        raise HTTPException(
            status_code=403,
            detail={"error": "plan_insuficiente", "feature": "subir_docs", "requiere": "pro"}
        )
    # ...
```

---

## Cambios en Base de Datos

### Tabla `gestorias` (modelos_auth.py)

```python
plan_tier         = Column(String(10), nullable=False, default="basico")
limite_empresas   = Column(Integer, nullable=True)  # None = ilimitado
```

### Tabla `usuarios` (modelos_auth.py)

```python
plan_tier = Column(String(10), nullable=False, default="basico")
```

### Migración: `sfce/db/migraciones/010_plan_tiers.py`

```python
ALTER TABLE gestorias ADD COLUMN plan_tier TEXT NOT NULL DEFAULT 'basico';
ALTER TABLE gestorias ADD COLUMN limite_empresas INTEGER;
ALTER TABLE usuarios  ADD COLUMN plan_tier TEXT NOT NULL DEFAULT 'basico';
```

---

## API — Nuevos endpoints

| Método | Endpoint | Quién | Descripción |
|--------|----------|-------|-------------|
| `PUT` | `/api/admin/gestorias/{id}/plan` | Superadmin | Actualiza tier + límite de una gestoría |
| `PUT` | `/api/admin/usuarios/{id}/plan` | Superadmin / Admin gestoría | Actualiza tier de un empresario |
| `GET` | `/api/auth/me` | Cualquiera | Ya existe — añadir `plan_tier` en respuesta |

---

## Frontend

### Panel superadmin (`/admin/gestorias`)
- Badge del tier actual junto al nombre de cada gestoría
- Dropdown para cambiar tier directamente en la lista

### Portal empresario
- Secciones bloqueadas muestran `<TierGate feature="subir_docs">` en lugar de error 403
- El componente `TierGate` renderiza un candado con "Disponible en Plan Pro"
- Datos del tier vienen de `/api/auth/me` (sin llamada extra)

### Hook frontend

```tsx
// dashboard/src/hooks/useTier.ts
import { useAuthContext } from '@/context/AuthContext'

const TIER_RANK = { basico: 1, pro: 2, premium: 3 } as const

export function useTiene(feature: string): boolean {
  const { usuario } = useAuthContext()
  // Mapa igual que el backend — fuente única en tiers.py + sincronizar aquí
  const FEATURES: Record<string, keyof typeof TIER_RANK> = {
    consultar:   'basico',
    subir_docs:  'pro',
    app_movil:   'pro',
    firmar:      'premium',
    chat_gestor: 'premium',
  }
  const requerido = FEATURES[feature] ?? 'premium'
  const actual = usuario?.plan_tier ?? 'basico'
  return (TIER_RANK[actual] ?? 1) >= (TIER_RANK[requerido] ?? 3)
}
```

```tsx
// Uso en cualquier componente:
function SubirDocumentoButton() {
  const puedeSubir = useTiene('subir_docs')
  if (!puedeSubir) return <TierGate feature="subir_docs" requiere="Pro" />
  return <Button>Subir factura</Button>
}
```

---

## Decisiones diferidas

- **Números exactos** de `limite_empresas` por tier (decisión comercial)
- **Precio** de cada tier (integración Stripe, fase posterior)
- **Features de gestoría** concretas (pendiente definir diferenciación entre tiers de gestoría)
- **Descuento** si empresario tiene el mismo plan que la gestoría que lo gestiona

---

## Lo que NO se implementa ahora

- Sistema de cobro / pasarela de pagos
- Notificación automática al acercarse al límite de empresas
- Downgrade automático al caducar el plan
- Trial period

Estos son decisiones comerciales que se añaden cuando el modelo de negocio esté validado.
