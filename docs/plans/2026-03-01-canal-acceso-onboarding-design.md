# Design: Canal de Acceso y Onboarding — SFCE

**Fecha**: 2026-03-01
**Estado**: Aprobado
**Sesión**: 5

---

## Contexto

Con el tablero de usuarios E2E verificado (superadmin → gestoría → gestor → cliente), el siguiente paso es definir:
1. Por qué canal accede cada tipo de usuario
2. Cómo se da de alta una nueva empresa (onboarding colaborativo)

---

## 1. Arquitectura de Canales

| Canal | Usuarios | Tecnología | Estado |
|-------|----------|------------|--------|
| Web dashboard | Superadmin, Gestor | React + Vite (existente) | P0 — ya implementado |
| App móvil | Empresario (cliente final) + gestor vista ligera | React Native | P1 — pendiente |
| App escritorio | Gestor (plan premium) | Electron | P2 — fase posterior |

**Principio API-first**: la API FastAPI es el centro. No asume que el cliente es siempre un navegador. Cada canal consume la misma API REST con JWT.

**Electron**: cuando llegue, empaqueta el dashboard React — reutiliza ~95% del código web. No es urgente.

---

## 2. Modelo de Producto — Tiers

El sistema soporta 3 planes: Básico, Pro, Premium. El contenido de cada tier se definirá en una sesión separada. La arquitectura debe ser extensible para soportar feature flags por plan.

Las 4 acciones del cliente (consultar, subir documentos, aprobar/firmar, comunicarse) se distribuirán entre tiers.

---

## 3. Flujo de Onboarding de Empresa

### Terminología
- **Gestor**: usuario de la gestoría que gestiona las cuentas
- **Empresario**: el cliente final de la gestoría (dueño de la empresa gestionada)
- **Empresa gestionada**: el negocio (Pastorino, Elena Navarro, etc.)

### Ruta A — Gestor completa todo
Para empresas donde el gestor tiene todos los datos:

```
1. Gestor abre WizardEmpresaGestor (5 pasos existentes):
   - Paso 1: Datos básicos (NIF, nombre, tipo sociedad)
   - Paso 2: Perfil de negocio (IAE, régimen IVA)
   - Paso 3: Proveedores habituales
   - Paso 4: FacturaScripts (idempresa, codejercicio)
   - Paso 5: Fuentes de documentos (correo, drive, manual)
2. empresa.estado_onboarding = 'configurada'
3. Gestor invita al empresario al portal (opcional, en cualquier momento)
```

### Ruta B — Gestor inicia, empresario completa (colaborativo)
Para empresas donde el empresario aporta datos operativos (IBAN, correo de facturas, proveedores):

```
1. Gestor completa pasos 1-2 del wizard (NIF, nombre, régimen IVA)
2. Pulsa "Invitar cliente a completar onboarding"
   → empresa.estado_onboarding = 'pendiente_cliente'
   → Email automático al empresario con link de invitación

3. Empresario acepta invitación → WizardOnboardingCliente (3 pasos, NUEVO):
   - Paso 1: Confirmar datos empresa (domicilio, teléfono)
   - Paso 2: Cuenta bancaria + IBAN (para conciliación)
   - Paso 3: Email de recepción de facturas + proveedores habituales
   → empresa.estado_onboarding = 'cliente_completado'
   → Gestor recibe notificación

4. Gestor completa pasos 3-5 del wizard (configuración técnica)
   → empresa.estado_onboarding = 'configurada'
```

### Autoregistro del empresario (sin gestor)
Si un empresario accede por primera vez sin haber sido invitado por un gestor, puede crear su propia empresa con un wizard simplificado. Requiere aprobación del superadmin para activarse.

---

## 4. Modelo de Datos

### Cambio en tabla `empresas`

```sql
ALTER TABLE empresas ADD COLUMN estado_onboarding TEXT DEFAULT 'configurada';
-- CHECK: 'esqueleto' | 'pendiente_cliente' | 'cliente_completado' | 'configurada'
```

Estados:
- `esqueleto` — gestor creó solo NIF+nombre (paso 1 incompleto)
- `pendiente_cliente` — esperando que el empresario complete sus datos
- `cliente_completado` — empresario completó, gestor debe finalizar config técnica
- `configurada` — todo completo y operativo

### Nueva tabla `onboarding_cliente`

```sql
CREATE TABLE onboarding_cliente (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  empresa_id      INTEGER NOT NULL REFERENCES empresas(id),
  iban            TEXT,
  banco_nombre    TEXT,
  email_facturas  TEXT,
  proveedores_json TEXT DEFAULT '[]',  -- JSON array de nombres
  completado_en   DATETIME,
  completado_por  INTEGER REFERENCES usuarios(id)
);
```

---

## 5. Spec API — Nuevos Endpoints

### Auth (mejoras para móvil)
| Método | Endpoint | Descripción | Estado |
|--------|----------|-------------|--------|
| POST | `/api/auth/refresh` | Renovar JWT (tokens cortos para móvil) | NEW |

### Portal empresario (móvil)
| Método | Endpoint | Descripción | Estado |
|--------|----------|-------------|--------|
| GET | `/api/portal/{id}/resumen` | KPIs empresa | Existe |
| GET | `/api/portal/{id}/documentos` | Documentos procesados | Existe |
| POST | `/api/portal/{id}/documentos/subir` | Upload desde cámara | NEW |
| GET | `/api/portal/{id}/notificaciones` | Alertas fiscales, docs pendientes | NEW |

### Onboarding cliente
| Método | Endpoint | Descripción | Estado |
|--------|----------|-------------|--------|
| GET | `/api/onboarding/cliente/{empresa_id}` | Estado actual del onboarding | NEW |
| PUT | `/api/onboarding/cliente/{empresa_id}` | Completar/actualizar datos | NEW |

### Gestor vista ligera (móvil)
| Método | Endpoint | Descripción | Estado |
|--------|----------|-------------|--------|
| GET | `/api/gestor/resumen` | Lista empresas con estado + alertas | NEW |
| GET | `/api/gestor/alertas` | Onboardings pendientes, docs en cola | NEW |

---

## 6. Frontend — WizardOnboardingCliente (nuevo)

Ubicación: `dashboard/src/features/onboarding/WizardOnboardingCliente.tsx`

Características:
- 3 pasos (no 5): solo datos que el empresario puede y debe proporcionar
- Sin pasos técnicos (FacturaScripts, fuentes — esos son del gestor)
- Accesible desde la URL de aceptación de invitación: `/aceptar-invitacion?token=...`
- También accesible desde el portal del empresario si `estado_onboarding !== 'configurada'`

Pasos:
1. **Datos empresa**: domicilio fiscal, teléfono, persona de contacto
2. **Cuenta bancaria**: IBAN, nombre del banco (para conciliación automática)
3. **Documentación**: email de recepción de facturas, proveedores habituales (nombre + estimación frecuencia)

---

## 7. Prioridades de Implementación

### Fase A (web) — dashboard actual
1. Migración BD: añadir `estado_onboarding` a empresas + tabla `onboarding_cliente`
2. `WizardOnboardingCliente` (3 pasos)
3. Integrar en flujo `aceptar-invitacion-page.tsx`: si empresa en `pendiente_cliente` → mostrar wizard
4. Alertas en dashboard gestor: badge en empresas `pendiente_cliente`/`cliente_completado`
5. Endpoint `PUT /api/onboarding/cliente/{id}`
6. Tests: unit (wizard), integración (endpoints), E2E (flujo completo)

### Fase B (API móvil spec)
1. Documentar todos los endpoints NEW con OpenAPI
2. Implementar `POST /api/portal/{id}/documentos/subir` (multipart + OCR trigger)
3. Implementar `GET /api/portal/{id}/notificaciones`
4. Implementar `GET /api/gestor/resumen` + `alertas`
5. Implementar `POST /api/auth/refresh`
6. Verificar que todos los endpoints funcionan con curl/Postman (sin app móvil)

---

## Decisiones no tomadas (sesión futura)

- Contenido exacto de cada tier (Básico/Pro/Premium)
- Stack definitivo React Native (Expo vs bare, navigation, etc.)
- Push notifications: Firebase vs Expo Push
- Offline support en app móvil (qué datos se cachean localmente)
