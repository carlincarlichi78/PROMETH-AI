# 02 — Arquitectura General SFCE

> **Estado:** ✅ COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes:** `sfce/api/app.py`, `sfce/core/backend.py`, `sfce/db/modelos.py`

---

## Qué es SFCE

SFCE (Sistema de Fiabilidad Contable España) es una plataforma SaaS diseñada para gestorías que automatiza el ciclo completo de contabilidad usando OCR e inteligencia artificial. El sistema recibe documentos contables (facturas de clientes, facturas de proveedores, nóminas, extractos bancarios, notas de crédito) y los procesa hasta dejarlos registrados en el software contable con los asientos correctos, sin intervención manual en casos estándar.

El público objetivo son gestorías que gestionan múltiples empresas cliente. SFCE actúa como capa de automatización sobre FacturaScripts (software contable PHP/MariaDB), añadiendo inteligencia de clasificación, validación normativa y aprendizaje continuo. Cada gestoría tiene su propio espacio aislado (multi-tenant), y dentro de ella gestiona las empresas de sus clientes.

Lo que diferencia a SFCE de otros sistemas contables es la combinación de triple consenso OCR (Mistral + GPT-4o + Gemini) con un motor de reglas contables de 6 niveles jerárquicos (normativa > PGC > perfil fiscal > negocio > cliente > aprendizaje). Este motor no solo clasifica documentos sino que aprende de correcciones pasadas, se actualiza automáticamente y aplica las reglas del BOE para cada modelo fiscal. El resultado es un sistema que mejora con el uso y reduce el tiempo de procesamiento en cada ciclo.

---

## Diagrama de componentes

```mermaid
graph TB
    subgraph CLIENTES["Acceso externo"]
        DASH["Dashboard\nReact 18 + TS + Vite 6\n20 módulos"]
        PORTAL["Portal Cliente\n(solo lectura)\n/portal/:id"]
    end

    subgraph API["API FastAPI — 66+ endpoints"]
        GW["Gate 0\nTrust + Scoring\nPreflight + Cola"]
        AUTH["Auth\nJWT + 2FA TOTP\nRate Limiting + Lockout"]
        WS["WebSocket\nTiempo real"]
        RUTAS["Rutas\ndirectorio / bancario / modelos\nfiscales / correo / certificados\npipeline / copiloto / portal"]
    end

    subgraph CORE["Núcleo de procesamiento"]
        PIP["Pipeline 7 Fases\nintake → preflight → OCR\n→ validación → clasificación\n→ registro → corrección"]
        OCR["Motor OCR por Tiers\nT0: Mistral\nT1: +GPT-4o\nT2: +Gemini (triple consenso)"]
        REGLAS["Motor de Reglas\n6 niveles jerárquicos\nnormativa → PGC → perfil fiscal\n→ negocio → cliente → aprendizaje"]
        APREND["Motor de Aprendizaje\n6 estrategias\nauto-update YAML"]
        BACK["Dual Backend\nmodo: dual / fs / local"]
    end

    subgraph DATOS["Capa de datos"]
        YAML["Reglas YAML\n9 archivos\nnormativa + perfil fiscal\n+ aprendizaje"]
        BD["BD SQLite (dev)\nPostgreSQL 16 (prod)\n29 tablas"]
        FS["FacturaScripts\nPHP + MariaDB\ncontabilidad.lemonfresh-tuc.com"]
    end

    subgraph OCR_EXT["Servicios OCR externos"]
        MISTRAL["Mistral OCR3\nprimario"]
        GPT["GPT-4o\nfallback + extracción"]
        GEMINI["Gemini Flash\nauditora triple consenso"]
    end

    DASH -->|"HTTPS + JWT"| API
    PORTAL -->|"HTTPS + JWT"| API
    API --> GW
    API --> AUTH
    API --> WS
    API --> RUTAS
    RUTAS --> PIP
    RUTAS --> REGLAS
    GW --> PIP
    PIP --> OCR
    PIP --> REGLAS
    PIP --> BACK
    REGLAS --> YAML
    REGLAS --> APREND
    APREND --> YAML
    OCR --> MISTRAL
    OCR --> GPT
    OCR --> GEMINI
    BACK -->|"fs_api REST"| FS
    BACK -->|"SQLAlchemy"| BD
    RUTAS -->|"SQLAlchemy"| BD
```

---

## Multi-tenant

La arquitectura multi-tenant sigue una jerarquía de tres niveles: **Gestoría → Empresas → Documentos**. Cada gestoría es un tenant independiente; sus datos nunca se mezclan con los de otras gestorías.

```
Gestoría (tenant raíz)
├── Empresa A (cliente de la gestoría)
│   ├── Documentos (facturas, nóminas, extractos...)
│   ├── Asientos contables
│   └── Modelos fiscales
├── Empresa B
│   └── ...
└── Empresa C
    └── ...
```

El aislamiento se implementa en dos capas:

| Capa | Mecanismo |
|------|-----------|
| JWT | El token incluye `gestoria_id`. Toda petición autenticada lleva el tenant implícito. |
| BD | Todas las tablas con datos de empresa tienen columna `empresa_id`. El helper `verificar_acceso_empresa()` comprueba que la empresa pertenece a la gestoría del token antes de servir datos. |
| FacturaScripts | Cada empresa tiene su propio `idempresa` en FS. Todas las llamadas a la API incluyen `idempresa` explícitamente. |

El endpoint de listado `listar_empresas()` filtra automáticamente por `gestoria_id` del JWT, garantizando que un usuario de una gestoría nunca vea empresas de otra.

---

## Dual Backend

El Dual Backend (`sfce/core/backend.py`) es la capa de abstracción que permite a SFCE escribir simultáneamente en dos destinos: **FacturaScripts** (el software contable real) y la **BD local** (SQLite/PostgreSQL del SFCE).

**Por qué existe:** FacturaScripts no expone todos los datos que necesita el dashboard en tiempo real. Las consultas complejas (P&G, KPIs, conciliación bancaria) son inviables sobre la API REST de FS. La BD local permite consultas analíticas rápidas mientras FS sigue siendo la fuente de verdad contable para modelos fiscales y documentación legal.

**Modos de operación:**

| Modo | Uso | Comportamiento |
|------|-----|----------------|
| `"dual"` | Producción | Escribe en FS + BD local simultáneamente |
| `"fs"` | Legacy / migración | Solo escribe en FacturaScripts |
| `"local"` | Testing / offline | Solo escribe en BD local |

**Parámetro `solo_local=True`:** Se usa al sincronizar asientos que FS ya generó automáticamente (por ejemplo, los asientos que `crearFacturaCliente` produce internamente). Con `solo_local=True`, el backend solo persiste en BD local sin reenviar a FS, evitando duplicados.

**Flujo de sincronización post-corrección:**

```
crearFactura* → FS genera asiento automático
      ↓
Pipeline aplica correcciones (asientos invertidos, divisas, suplidos)
      ↓
_sincronizar_asientos_factura_a_bd() con solo_local=True
      ↓
BD local refleja el estado FINAL corregido (no el estado bruto de FS)
```

Si FS falla durante una operación dual, el backend marca el registro como `pendiente_sync` para reintento posterior.

---

## Módulos implementados

| Módulo | Estado | Tests | Ubicación principal |
|--------|--------|-------|---------------------|
| Pipeline 7 Fases | ✅ Completo | 18 tasks / E2E OK | `sfce/phases/` |
| Motor OCR por Tiers | ✅ Completo | 21 tests | `sfce/core/ocr_*.py` |
| Motor de Reglas (6 niveles) | ✅ Completo | — | `sfce/core/`, `reglas/*.yaml` |
| Motor de Aprendizaje | ✅ Completo | 21 tests | `sfce/core/aprendizaje.py` |
| Modelos Fiscales (28 modelos) | ✅ Completo | 544 tests | `sfce/modelos_fiscales/` |
| Dashboard (20 módulos) | ✅ Completo | Build OK | `dashboard/src/features/` |
| Bancario (Norma 43 + XLS) | ✅ Completo | 112 tests | `sfce/conectores/bancario/` |
| Directorio Empresas | ✅ Completo | 65 tests | `sfce/db/modelos.py`, `sfce/api/rutas/directorio.py` |
| Seguridad (JWT + 2FA + Lockout) | ✅ Completo | 39 tests | `sfce/api/auth.py`, `sfce/api/rate_limiter.py` |
| Multi-tenant | ✅ Completo | 4 E2E PASS | `sfce/api/rutas/`, migracion 004 |
| PWA (Service Worker + offline) | ✅ Completo | Build OK | `dashboard/vite.config.ts`, `public/sw.js` |
| Portal Cliente | ✅ Completo | — | `sfce/api/rutas/portal.py`, `dashboard/src/features/portal/` |
| Gate 0 (Trust + Scoring) | ✅ Completo | — | `sfce/api/rutas/gate0.py` |
| Generador de Datos de Prueba | ✅ Completo | 189 tests | `tests/datos_prueba/generador/` |
| Dual Backend FS+BD | ✅ Completo | Integrado | `sfce/core/backend.py` |
| Correo (CAP-Web) | Planificado | — | `docs/plans/2026-03-01-prometh-ai-fases-4-6.md` |
| Certificados AAPP (CertiGestor) | Planificado | — | `docs/plans/2026-03-01-prometh-ai-fases-4-6.md` |
| Copiloto IA | Planificado | — | — |

**Total tests actuales: 1793 PASS**

---

## Stack tecnológico

### Backend Python

| Tecnología | Rol |
|-----------|-----|
| FastAPI (Python 3.12+) | Framework API REST + WebSocket |
| SQLAlchemy 2.x | ORM, compatible SQLite y PostgreSQL |
| SQLite / PostgreSQL 16 | BD desarrollo / producción |
| JWT (python-jose) | Autenticación stateless |
| pyotp + qrcode | 2FA TOTP |
| Uvicorn | Servidor ASGI |
| Mistral API | OCR primario (Tier 0) |
| OpenAI GPT-4o | OCR fallback + extracción (Tier 1) |
| Google Gemini Flash | Triple consenso OCR (Tier 2) |
| WeasyPrint | Generación PDF modelos fiscales |
| pytest (1793 tests) | Suite de tests |

### Frontend

| Tecnología | Rol |
|-----------|-----|
| React 18 + TypeScript strict | UI principal |
| Vite 6 | Bundler + dev server |
| Tailwind CSS v4 | Estilos utility-first |
| shadcn/ui | Componentes accesibles |
| Recharts | Gráficos KPIs y P&G |
| TanStack Query v5 | Cache y sincronización servidor |
| Zustand | Estado global (empresa activa, auth) |
| @tanstack/react-virtual | Listas virtualizadas |
| vite-plugin-pwa + Workbox | PWA, cache-first assets, offline |
| DOMPurify | Sanitización HTML (XSS) |

### Infraestructura

| Tecnología | Rol |
|-----------|-----|
| Docker + Nginx | Contenedores y proxy inverso |
| Hetzner (65.108.60.69) | Servidor VPS |
| FacturaScripts (PHP + MariaDB 10.11) | Software contable base |
| Let's Encrypt | Certificados TLS |
| ufw + DOCKER-USER chain | Firewall servidor |
| Hetzner Object Storage (Helsinki) | Backups (7d/4w/12m) |
| Uptime Kuma | Monitorización servicios |

---

## Principios de diseño

**1. Motor de reglas en lugar de código ad-hoc**
Las reglas contables (tipos de IVA, cuentas PGC, regímenes fiscales) se expresan en YAML versionado (`reglas/*.yaml`), no en código Python. Esto permite actualizar la normativa de un año sin tocar el motor, y facilita auditorías: cualquier decisión contable tiene su regla explícita en texto legible.

**2. Dual backend para separar fuente de verdad de analítica**
FacturaScripts es la fuente de verdad legal (genera los PDFs de modelos fiscales, firma asientos). La BD local es la fuente de verdad analítica (queries rápidas para dashboard, KPIs, conciliación). Separar ambos roles evita sobrecargar FS con consultas analíticas que no está diseñado para responder.

**3. Triple consenso OCR para máxima fiabilidad**
Un solo motor OCR tiene tasas de error inaceptables para datos contables. El sistema usa tres motores en cascada: si el primero (Mistral) obtiene consenso en campos clave, no se activan los siguientes (coste cero adicional). Solo cuando hay ambigüedad se invoca el segundo y tercer motor, que actúa como auditor. El resultado es alta fiabilidad con coste mínimo en el caso común.

**4. Aprendizaje continuo sin intervención manual**
Cada corrección manual que hace un usuario (cambiar la cuenta contable de un proveedor, ajustar el tipo de IVA) se registra como regla en `reglas/aprendizaje.yaml`. En el siguiente ciclo, el mismo patrón se resuelve automáticamente. El sistema mejora con el uso real de cada gestoría.

**5. Multi-tenant por diseño, no por retrofit**
El aislamiento de gestorías se implementa en la capa de datos (columna `gestoria_id`) y en la capa de autenticación (JWT con `gestoria_id`). No existe una ruta de acceso que eluda esta verificación: `verificar_acceso_empresa()` se llama antes de cualquier operación con datos de empresa, y el ORM filtra por `gestoria_id` en todas las consultas de listado.
