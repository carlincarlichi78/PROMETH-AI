# SFCE — Libro Técnico Personal
> **Versión:** Consolidada (5 + 3 manuales) | **Actualizado:** 2026-03-07 (sesión 117)

---

## Archivos del libro

### Libro Técnico (programador)

| Archivo | Contenido |
|---------|-----------|
| `00-indice-infra-stack.md` | Comandos rápidos, variables de entorno, infraestructura Hetzner, Docker/nginx, 4 instancias FacturaScripts, credenciales, API FS lecciones críticas, CI/CD, stack tecnológico |
| `01-arquitectura-pipeline-ocr.md` | Arquitectura general, módulos implementados, multi-tenant, dual backend, pipeline 7 fases, Gate 0, OCR por tiers, motor de reglas (6 niveles), aprendizaje, cuarentena |
| `02-bd-y-api.md` | 45+ tablas (con detalle campos críticos incluyendo migración 029), ORM, migraciones, todos los endpoints API (~140 endpoints organizados por dominio) |
| `03-bancario-fiscal-seguridad.md` | Módulo bancario completo (parser C43/XLS + motor conciliación 5 capas), modelos fiscales (28 modelos + MotorBOE), correo IMAP, seguridad JWT/2FA/RGPD/multi-tenant, ADRs |
| `04-estado-pendientes-roadmap.md` | Estado actual, tasks pendientes, roadmap, deuda técnica, notas para retomar |

### Manuales de usuario

| Archivo | Audiencia | Contenido |
|---------|-----------|-----------|
| `LIBRO-GESTOR.md` | admin_gestoria · asesor | Dashboard completo: documentos, pipeline, conciliación, fiscal, facturación, contabilidad, RRHH, administración |
| `LIBRO-CLIENTE.md` | Clientes / empresarios | Cómo enviar documentos, estado del procesamiento, FAQ, calendario de envío |

### Accesos (local únicamente — gitignoreado)

| Archivo | Contenido |
|---------|-----------|
| `LIBRO-ACCESOS.md` | **Solo local, nunca en git.** SSH, PostgreSQL, 4 instancias FS + tokens, usuarios SFCE, API keys IA, Google Workspace, GitHub secrets, Restic backups, tabla clientes |
| `c:\Users\carli\PROYECTOS\ACCESOS.md` | Fuente maestra global (todos los proyectos, 27 secciones) |

---

## Comandos de inicio de sesión

```bash
# Verificar estado tests completo
python -m pytest --tb=no -q
# Esperado: ~2923 passed

# Commits recientes
git log -5 --oneline

# Abrir dashboard
cd dashboard && npm run dev
```

---

## Estado rápido (sesión 122 — CERRADA)

- **Completado:** Deploy manual producción (imagen reconstruida en VPS, sfce_api healthy). GitHub Actions operativo: repo público = minutos ilimitados, CI/CD ya corre en cada push. Fix `ruamel.yaml` en requirements.txt (faltaba → tests test_motor_plantillas fallaban en CI). 2923 PASS.
- **Pendiente sesión 123:** FAC0007A4 FS Uralde (BLOQUEADOR). Poppler en PATH proceso. Adeudos Feb/Mar cuarentena. 4 PDFs imagen sin datos. 3 Ingresos 3T. Plenergy id=358.
- **ARRANCAR API CORRECTAMENTE:** `python arrancar_api.py` (NO `export $(xargs)` — trunca SFCE_FERNET_KEY)

---

## Notas operacionales producción

- **Seed IMAP ejecutado** (sesión 75). `scripts/crear_cuentas_imap_asesores.py` en git tiene passwords vacíos — no ejecutar directamente. Usar temp script vía `docker cp + docker exec`.
- **`es_respuesta_ack` corregido** a `boolean` en prod. Fix: drop default → type change → restore default.
- **IBAN interno C43**: formato `banco(4)+oficina(4)+cuenta(10)` sin prefijo ES (ver 03-bancario).
- **`_leer_config_bd`**: está en `sfce.api.app`, NO en `sfce.db.base`.

## Regla de uso

1. Para cualquier duda técnica, leer el archivo correspondiente del libro antes de explorar código.
2. Al cerrar sesión: actualizar `04-estado-pendientes-roadmap.md` con el estado actual.
3. Libro Técnico: 5 archivos (00-04). Manuales: LIBRO-GESTOR, LIBRO-CLIENTE, LIBRO-ACCESOS (local). No crear más sin consolidar.
