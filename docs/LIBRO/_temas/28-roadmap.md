# Roadmap y Estado del Sistema

> **Estado:** EN PRODUCCION — SFCE completado, tablero operativo
> **Actualizado:** 2026-03-01
> **Tests totales:** 2133 PASS
> **Branch activa:** main
> **Tags:** `fase6-ingesta-360`, `c1-c4-pipeline-completion`

---

## Metricas actuales

| Metrica | Valor |
|---------|-------|
| Tests passing | 2133 |
| Endpoints API activos | 75+ rutas |
| Modulos del dashboard | 15 modulos |
| Modelos fiscales implementados | 28 modelos |
| Familias de documentos (generador) | 43 familias |
| Documentos sinteticos generables | 2.343 docs |
| Clientes reales activos | 5 clientes |
| Plugins FacturaScripts activos | 4 (303, 111, 347, 130) |

---

## Completado (en main, 01/03/2026)

### Nucleo SFCE

| Componente | Tests | Detalle |
|------------|-------|---------|
| Pipeline v1 | — | 7 fases, 18/18 tasks, quality gates |
| SFCE v2 | 954 | 5 fases, normativa, perfil fiscal, clasificador, BD, API |
| Motor Autoevaluacion v2 | 21 | 6 capas, triple OCR consenso |
| Intake Multi-Tipo | 67 | FC/FV/NC/NOM/SUM/BAN/RLC/IMP |
| Motor Aprendizaje | 21 | 6 estrategias, auto-update YAML |
| OCR por Tiers | — | T0 Mistral → T1 +GPT → T2 +Gemini, 5 workers |
| Modelos Fiscales | 544 | 28 modelos, MotorBOE, GeneradorPDF, API+dashboard |
| Directorio Empresas | 65 | CIF unico global, verificacion AEAT/VIES |
| Dual Backend | — | FS+BD local, sync automatico asientos post-correcciones |
| MCF Motor Clasificacion Fiscal | 70 | 50 categorias, base legal LIVA+LIRPF 2025 |
| Gate 0 | — | Trust levels, preflight SHA256, scoring 5 factores, decision automatica |
| Supplier Rules BD | 5 | Jerarquia 3 niveles (CIF+empresa > CIF global > nombre patron) |
| Worker OCR + Recovery | 13 | Daemon async Tiers 0/1/2, recovery >1h, coherencia fiscal |
| Cache OCR | — | SHA256 invalidacion, `.ocr.json` junto a PDF |
| Coherencia Fiscal | 13 | Validador post-OCR, bloqueos duros + alertas |

### Plataforma SaaS

| Componente | Tests | Detalle |
|------------|-------|---------|
| Seguridad SaaS | — | JWT RS256, rate limiting VentanaFija, lockout, 2FA TOTP, RGPD |
| Multi-tenant | — | Gestorias, usuarios, invitaciones, roles, audit log |
| Tablero Usuarios | 2133 total | 4 niveles: superadmin → gestoria → gestor → cliente. 12 tasks |
| Email Service | — | SMTP basico, envio invitaciones automatico |
| OCR 036/037 | — | Parser Modelo 036/037: NIF, domicilio, regimen IVA, epigrafes |
| OCR Escrituras | — | Parser escrituras constitucion: CIF, capital, administradores |
| FS Setup Auto | — | Crea empresa + ejercicio + importa PGC automaticamente |
| Migracion Historica | — | Parsea libros IVA CSV, extrae proveedores habituales |
| iCal Export | — | Deadlines fiscales → .ics |
| Webhook CertiGestor | — | Notificaciones AAPP con auth HMAC-SHA256 |
| Certificados AAPP | — | Modelos + servicio portado de CertiGestor |

### Dashboard Frontend

| Componente | Detalle |
|------------|---------|
| Rediseno Total | React 18 + TS strict + Vite 6 + Tailwind v4 + shadcn/ui + Recharts + TanStack Query v5 + Zustand |
| Build | 4.65s, 109 entries precacheadas, PWA con vite-plugin-pwa |
| Modulos | 15 modulos, feature-based, lazy loading, path alias `@/` |
| Tema | Paleta ambar OKLCh, dark mode, glassmorphism |
| OmniSearch | Command Palette (cmdk), busqueda global |
| Keyboard shortcuts | G+C/F/D/E/R/H, page transitions |
| Configuracion | 18 secciones |
| Endpoints home | `GET /api/empresas/estadisticas-globales`, `GET /api/empresas/{id}/resumen` (datos reales BD) |

### Infraestructura

| Componente | Detalle |
|------------|---------|
| PostgreSQL 16 | Docker `/opt/apps/sfce/`, puerto `127.0.0.1:5433`, BD `sfce_prod` |
| Backups totales | `backup_total.sh` cron 02:00 diario — 6 PG + 2 MariaDB + configs + SSL + Vaultwarden → Hetzner Helsinki. Retencion 7d/4w/12m |
| Firewall | ufw activo + DOCKER-USER chain bloquea 5432/6379/8000/8080 del exterior |
| Seguridad nginx | `server_tokens off` + HSTS/X-Frame/X-Content-Type/Referrer/Permissions en todos los vhosts |
| Uptime Kuma | Docker `127.0.0.1:3001`, acceso via SSH tunnel |

---

## Proxima sesion — PRIORIDAD: Test Nivel 0 end-to-end

**Contexto**: Las 4 levels del tablero estan implementadas pero NO probadas en real.
**Regla del tablero**: no avanzar de nivel sin que el anterior funcione end-to-end.

**Nivel 0 a probar** con Playwright (`superpowers:webapp-testing`):

1. Superadmin crea gestoria desde `/admin/gestorias` en el dashboard
2. Superadmin invita a admin de gestoria (token generado, email enviado o visible en respuesta)
3. Admin gestoria acepta invitacion (`POST /api/auth/aceptar-invitacion?token=xxx`)
4. Admin gestoria entra al dashboard y ve `/mi-gestoria`

Corregir lo que falle → verificar → solo entonces pasar a Nivel 1.

---

## Pendiente (baja prioridad)

| Item | Descripcion |
|------|-------------|
| Tests E2E dashboard | Playwright para flujos criticos: login, pipeline, conciliacion, modelo fiscal, portal cliente |
| Migracion SQLite → PostgreSQL | `scripts/migrar_sqlite_a_postgres.py` — servidor ya tiene PG16, script existe pero no ejecutado |
| VAPID Push Notifications | Activar `VITE_VAPID_PUBLIC_KEY` + endpoint `POST /api/notificaciones/suscribir` |
| `fiscal.proximo_modelo` | En resumen empresa — requiere ServicioFiscal integrado |
| Motor de Escenarios de Campo | `scripts/motor_campo.py --modo rapido` — testeo parametrico masivo sin coste API |
| Pagina cuarentena en dashboard | Visualizar documentos en cuarentena, sugerencias MCF |
| Integrar MCF en pipeline completo | ClasificadorFiscal activo en flujo principal (actualmente standalone) |

---

## Deuda tecnica

| Item | Impacto | Accion |
|------|---------|--------|
| 0 tests E2E dashboard | Alto — flujos criticos sin cobertura automatizada | Sprint siguiente |
| `migrar_sqlite_a_postgres.py` no ejecutado | Medio — produccion sigue en SQLite single-user | P2 |
| VAPID endpoint backend faltante | Medio — push notifications no funcionan | P2 |
| `fiscal.proximo_modelo` = null | Bajo — dashboard home muestra null en campo fiscal | P2 |
