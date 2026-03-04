# SFCE — Libro Técnico Personal
> **Versión:** Consolidada (5 archivos) | **Actualizado:** 2026-03-04 (sesión 66)

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

---

## Comandos de inicio de sesión

```bash
# Verificar estado tests bancario
python -m pytest tests/test_bancario/ --tb=no -q
# Esperado: 161 passed

# Commits recientes
git log -5 --oneline

# Ver tasks pendientes
grep "^### Task" docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md
```

---

## Estado rápido (sesión 66)

- **Plan activo:** `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md`
- **Completado:** Tasks 1-6 (motor 5 capas + feedback loop) + Tasks 9-10 (api.ts + componentes dashboard)
- **Pendiente:** Tasks 7-8 (API endpoints confirmar/rechazar/bulk/parcial) + Task 11 (conciliacion-page.tsx 5 pestañas) + Task 13 (regresión + producción)
- **Próximo paso:** Task 7 — endpoints API en `sfce/api/rutas/bancario.py`

---

## Regla de uso

1. Para cualquier duda técnica, leer el archivo correspondiente del libro antes de explorar código.
2. Al cerrar sesión: actualizar `04-estado-pendientes-roadmap.md` con el estado actual.
3. Mantener exactamente 5 archivos más este índice. No crear más sin consolidar.
