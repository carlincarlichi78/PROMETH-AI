# SFCE — Índice, Infraestructura y Stack
> **Actualizado:** 2026-03-04 (sesión 66) | **Tests:** 161 bancario, ~2500+ total | **Branch:** main

---

## Comandos rápidos

```bash
# Backend API
cd sfce && export $(grep -v '^#' ../.env | xargs)
uvicorn sfce.api.app:crear_app --factory --reload --port 8000

# Frontend dashboard
cd dashboard && npm run dev   # → http://localhost:5173

# Tests bancario (referencia estado conciliación)
python -m pytest tests/test_bancario/ --tb=no -q

# Tests completos
python -m pytest --tb=no -q

# Pipeline completo
export $(grep -v '^#' .env | xargs)
python scripts/pipeline.py --cliente gerardo-gonzalez-callejon --ejercicio 2025 --inbox inbox_gerardo --no-interactivo

# Cargar .env SIEMPRE con export, NUNCA source
export $(grep -v '^#' .env | xargs)
```

---

## Variables de entorno

| Variable | Servicio | Notas |
|----------|----------|-------|
| `FS_API_TOKEN` | FacturaScripts REST API | Token para endpoints `crear*` |
| `MISTRAL_API_KEY` | Mistral OCR3 | Motor OCR primario |
| `OPENAI_API_KEY` | GPT-4o | OCR fallback + extracción |
| `GEMINI_API_KEY` | Gemini Flash | Triple consenso OCR + auditor |
| `SFCE_JWT_SECRET` | Auth | >=32 chars. API falla al arrancar si falta |
| `SFCE_DB_TYPE` | BD | `sqlite` (dev) o `postgresql` (prod) |
| `POSTGRES_DSN` | BD | DSN completo si `SFCE_DB_TYPE=postgresql` |
| `SFCE_CORS_ORIGINS` | API | Origins permitidos. Nunca `"*"` |
| `SFCE_FERNET_KEY` | Cifrado | Para credenciales correo/FS. Caracteres especiales: NO usar `export $(xargs)` — usar `arrancar_api.py` |

---

## Infraestructura

### Servidor Hetzner

| Campo | Valor |
|-------|-------|
| IP | 65.108.60.69 |
| Acceso | `ssh carli@65.108.60.69` (RSA, sin contraseña) |
| OS | Ubuntu LTS |
| PostgreSQL 16 | `127.0.0.1:5433`, BD `sfce_prod`, user `sfce_user` |

**Tunel SSH para PostgreSQL:** `ssh -L 5433:127.0.0.1:5433 carli@65.108.60.69 -N`

### Puertos activos

| Puerto | Servicio |
|--------|----------|
| 8000 | API FastAPI (dev local) |
| 5173 | Vite dev server (proxy → 8000) |
| 5433 | PostgreSQL 16 (solo localhost servidor) |
| 8010/8011/8012 | FS Uralde/GestoriaA/Javier (internos Docker) |
| 443/80 | Nginx HTTPS/HTTP |

### Docker / Nginx

- Configuraciones nginx: `/opt/infra/nginx/conf.d/`
- Reload: `docker exec nginx nginx -s reload`
- **`docker compose restart` NO recarga env_file** → usar `docker compose up -d sfce_api`
- Backups: `/opt/apps/sfce/backup_total.sh` cron 02:00 diario → Hetzner Helsinki (7d/4w/12m)

### URLs activas

| Servicio | URL |
|----------|-----|
| FS superadmin | https://contabilidad.prometh-ai.es |
| FS Uralde | https://fs-uralde.prometh-ai.es |
| FS Gestoría A | https://fs-gestoriaa.prometh-ai.es |
| FS Javier | https://fs-javier.prometh-ai.es |
| SFCE Dashboard | https://app.prometh-ai.es |
| SFCE API | https://api.prometh-ai.es |
| SFCE API health | https://api.prometh-ai.es/api/health |

---

## FacturaScripts — 4 instancias

**Password universal SFCE + FS + Google Workspace:** `Uralde2026!`

| URL | Gestoría | Token API |
|-----|----------|-----------|
| https://contabilidad.prometh-ai.es | superadmin | `iOXmrA1Bbn8RDWXLv91L` |
| https://fs-uralde.prometh-ai.es | Uralde (id=1) | `d0ed76fcc22785424b6c` |
| https://fs-gestoriaa.prometh-ai.es | Gestoría A (id=2) | `deaff29f162b66b7bbd2` |
| https://fs-javier.prometh-ai.es | Javier (id=3) | `6f8307e8330dcb78022c` |

### Empresas (13) — SFCE id → FS idempresa

| id | FS | Empresa | Gestoría |
|----|-----|---------|---------|
| 1 | 2 | PASTORINO COSTA DEL SOL S.L. | Uralde |
| 2 | 3 | GERARDO GONZALEZ CALLEJON | Uralde |
| 3 | 4 | CHIRINGUITO SOL Y ARENA S.L. | Uralde |
| 4 | 5 | ELENA NAVARRO PRECIADOS | Uralde |
| 5 | 2 | MARCOS RUIZ DELGADO | Gestoría A |
| 6 | 3 | RESTAURANTE LA MAREA S.L. | Gestoría A |
| 7 | 4 | AURORA DIGITAL S.L. | Gestoría A |
| 8 | 5 | CATERING COSTA S.L. | Gestoría A |
| 9 | 6 | DISTRIBUCIONES LEVANTE S.L. | Gestoría A |
| 10 | 2 | COMUNIDAD MIRADOR DEL MAR | Javier |
| 11 | 3 | FRANCISCO MORA | Javier |
| 12 | 4 | GASTRO HOLDING S.L. | Javier |
| 13 | 5 | JOSE ANTONIO BERMUDEZ | Javier |

> idempresa 1 de cada instancia = empresa por defecto del wizard (E-XXXX). No usar.

### Lecciones críticas API FacturaScripts

- **`crear*` requieren form-encoded** (NO JSON): `requests.post(url, data=...)`
- **Líneas**: `form_data["lineas"] = json.dumps([...])`. IVA: `codimpuesto` (IVA0/IVA4/IVA21)
- **`crearFacturaProveedor` INCOMPATIBLE con multi-empresa**: usar POST 2 pasos (`facturaproveedores` + `lineasfacturaproveedores`)
- **Filtros NO funcionan**: `idempresa`, `idasiento`, `codejercicio`. SIEMPRE post-filtrar en Python
- **`crear*` sin `codejercicio`**: FS asigna a empresa incorrecta. SIEMPRE pasar explícitamente
- **Al crear proveedores**: NO pasar `codsubcuenta` del config.yaml. FS auto-asigna 400x
- **Campos `_*` en form_data**: filtrar antes de POST: `{k:v for k,v in form.items() if not k.startswith('_')}`
- **POST asientos**: SIEMPRE pasar `idempresa` explícitamente. Response: `{"ok":"...","data":{"idasiento":"X"}}`
- **CIF intracomunitario**: usar `endswith()` — `"ES76638663H".endswith("76638663H")` True
- **Asientos invertidos**: causa = codsubcuenta 600 asignada al proveedor. Corrección post-creación con PUT partidas
- **PUT lineasfacturaproveedores REGENERA asiento**: reclasificaciones SIEMPRE después
- **Nick FS max 10 chars**: codcliente/codproveedor
- **crearFacturaCliente 422 por orden cronológico**: pre-generar fechas del año, ordenar ASC, crear en ese orden
- **Subcuentas PGC no existentes**: 4651→4650; 6811→6810. Testear con POST de prueba antes de uso masivo
- **`codejercicio`** puede diferir del año (empresa 4 → "0004"). Usar `config.codejercicio` para API
- **`personafisica`**: usar 0/1 (integer), NO false/true (string)
- **Gemini free**: 5 req/min y 20 req/día. Para batches >20: solo GPT+Mistral

### Orden correcciones FS (CRÍTICO — no alterar)

1. Corregir `codimpuesto` en líneas factura (IVA21→IVA0 para suplidos)
2. Esperar regeneración asientos por FS
3. Corregir asientos invertidos (debe/haber)
4. Corregir divisas (USD→EUR)
5. Reclasificar suplidos (600→4709)

---

## CI/CD — GitHub Actions

**Repo:** `carlincarlichi78/SPICE` (privado) | **Trigger:** push a `main`

| Job | Qué hace | Depende de |
|-----|----------|------------|
| `test` | pytest contra PostgreSQL efímero | — |
| `build-frontend` | `npm run build` + artefacto | — (paralelo) |
| `build-docker` | Build + push a GHCR | test |
| `deploy` | SCP frontend + SSH: docker pull + up + nginx reload | build-docker + build-frontend |

**Secrets requeridos:** `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `SFCE_JWT_SECRET`, `SFCE_DB_PASSWORD`, `MISTRAL_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `FS_API_TOKEN`

---

## Stack tecnológico

### Backend Python

| Tecnología | Rol |
|-----------|-----|
| FastAPI (Python 3.12+) | Framework API REST + WebSocket |
| SQLAlchemy 2.x | ORM, compatible SQLite y PostgreSQL |
| SQLite (dev) / PostgreSQL 16 (prod) | Base de datos |
| JWT (python-jose, HS256) | Autenticación stateless |
| pyotp + qrcode | 2FA TOTP |
| Uvicorn | Servidor ASGI |
| Mistral API | OCR primario (Tier 0) |
| OpenAI GPT-4o | OCR fallback + extracción + Vision (Tier 1) |
| Google Gemini Flash (`gemini-2.5-flash`) | Triple consenso OCR (Tier 2) |
| WeasyPrint | Generación PDF modelos fiscales |
| smtplib | Email SMTP invitaciones |
| pytest | Suite de tests (~2500+) |
| Fernet (cryptography) | Cifrado simétrico credenciales |
| bcrypt | Hash contraseñas |

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

**Tokens auth:** almacenados en `sessionStorage` (NO localStorage). Desaparecen al cerrar pestaña.

**IMPORTANT Windows:** `uvicorn --reload` falla con `WinError 6`. Reiniciar manualmente tras cambios Python.

**Vite puerto dinámico en Windows:** si 3000-3004 ocupados, arranca en 3005+. Leer log Vite.

**NEVER `page.goto()` mismo URL en Playwright:** Chromium hace hard-reload limpiando sessionStorage → token=null.

### Infraestructura

| Tecnología | Rol |
|-----------|-----|
| Docker + Nginx | Contenedores y proxy inverso |
| Hetzner (65.108.60.69) | Servidor VPS |
| FacturaScripts (PHP + MariaDB 10.11) | Software contable base |
| Let's Encrypt | Certificados TLS (expiran 2026-05-30) |
| ufw + DOCKER-USER chain | Firewall servidor |
| Hetzner Object Storage Helsinki | Backups |
| Uptime Kuma (127.0.0.1:3001) | Monitorización |

### Plugins FacturaScripts activos (todas las instancias)

Modelo303 v2.7, Modelo111 v2.2, Modelo347 v3.51, Modelo130 v3.71, Modelo115 v1.6, Verifactu v0.84

---

## Usuarios SFCE

| Email | Rol | Gestoría |
|-------|-----|---------|
| admin@sfce.local | superadmin | — (dev) |
| admin@prometh-ai.es | superadmin | — (prod) |
| sergio@prometh-ai.es | admin_gestoria | Uralde |
| francisco@, maria@, luis@ @prometh-ai.es | asesor | Uralde |
| gestor1@, gestor2@ @prometh-ai.es | admin_gestoria | Gestoría A |
| javier@prometh-ai.es | admin_gestoria | Javier |

**Login local dev:** admin@sfce.local / admin (crear con `crear_admin_por_defecto`)
