# SFCE — Libro Técnico Personal
> **Versión:** Consolidada (5 + 3 manuales) | **Actualizado:** 2026-03-08 (sesión 129)

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
# Esperado: ~2943 passed

# Commits recientes
git log -5 --oneline

# Abrir dashboard
cd dashboard && npm run dev
```

---

## Estado rápido (sesión 131 — CERRADA)

- **Completado:** Carga FVs sintéticas (FV04-15, 18, 21) en FS → 29 FVs totales. Cuadre M303: T1/T2/T4 MATCH PERFECTO al céntimo. T3 gap -1.014,30€ = FV19+FV20 no aportadas. IVA soportado: diferencia explicada por criterio conservador del asesor fiscal.
- **Pendiente sesión 132:** FV19+FV20 cuando las aporte la clienta. Commitear gastos_julio_2025.md. Dropbox como intracomunitaria. Poppler en PATH. CIF Romur Spanish Properties.
- **ARRANCAR API CORRECTAMENTE:** `python arrancar_api.py` (NO `export $(xargs)` — trunca SFCE_FERNET_KEY)

---

## Notas operacionales producción

- **Seed IMAP ejecutado** (sesión 75). `scripts/crear_cuentas_imap_asesores.py` en git tiene passwords vacíos — no ejecutar directamente.
- **`es_respuesta_ack` corregido** a `boolean` en prod.
- **IBAN interno C43**: formato `banco(4)+oficina(4)+cuenta(10)` sin prefijo ES (ver 03-bancario).
- **`_leer_config_bd`**: está en `sfce.api.app`, NO en `sfce.db.base`.
- **Motor Plantillas vs Motor Identificación**: cuando `_fuente == "plantilla"`, el LLM no se llama y las señales (iban/telefono) no se extraen del documento. Las señales vienen del config.yaml del proveedor.
- **IBAN María Isabel (cobro)**: `ES4114650100951735096975` — aparece en FV a particulares como cuenta de pago.
- **Scoring FV corregido** (sesión 127): floor 85 receptor en config, 72 NIF persona física, 65 CIF entidad nueva, 60 sin CIF. FC sin cambio (55).

## Regla de uso

1. Para cualquier duda técnica, leer el archivo correspondiente del libro antes de explorar código.
2. Al cerrar sesión: actualizar `04-estado-pendientes-roadmap.md` con el estado actual.
3. Libro Técnico: 5 archivos (00-04). Manuales: LIBRO-GESTOR, LIBRO-CLIENTE, LIBRO-ACCESOS (local). No crear más sin consolidar.
