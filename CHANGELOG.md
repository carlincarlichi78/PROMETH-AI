# CHANGELOG — Proyecto CONTABILIDAD

## Sesión 54 — 03/03/2026: FacturaScripts instancias operativas

### Resumen
Resolución definitiva del problema de empresa activa en las 3 instancias FS + todos los usuarios con acceso correcto.

### Problema FS empresa activa — 4 causas encadenadas
| Causa | Síntoma | Fix |
|-------|---------|-----|
| `users.homepage='Wizard'` | Wizard bloqueaba el login | `UPDATE users SET homepage=NULL` |
| `Dinamic/` vacía | Menú no aparecía | AdminPlugins → Reconstruir |
| `settings.default.idempresa=1` | Mostraba E-9881 | UPDATE MariaDB + borrar caché + confirmar en EditSettings |
| `nombrecorto=NULL` | Mostraba `%company%` | `UPDATE empresas SET nombrecorto='NOMBRE'` |

### Estado final instancias FS
| Instancia | Empresa activa | Usuarios |
|-----------|---------------|---------|
| fs-uralde.prometh-ai.es | PASTORINO (idempresa=2) ✅ | carloscanete/sergio/francisco/mgarcia/llupianez |
| fs-gestoriaa.prometh-ai.es | MARCOS (idempresa=2) ✅ | carloscanete/gestor1/gestor2 |
| fs-javier.prometh-ai.es | COMUNIDAD (idempresa=2) ✅ | carloscanete/javier |

Todos con `password=Uralde2026!`, `level=99`, `admin=1`.

### Cómo cambiar empresa activa en FS (referencia futura)
`Administrador → Panel de control` (`/EditSettings`) → dropdown "Empresa" → Guardar

### Otros cambios sesión 53+54
- Balance/PyG operativos (`func.strftime` → `func.to_char`)
- 66 archivos git limpiados (datos cliente borrados + scripts añadidos)
- `docs/problemas/fs-cambio-empresa.md` — documentación completa del problema

---

## Sesión 53 — 03/03/2026: Puesta en marcha producción completa

### Resumen
Sesión de puesta en producción: login SFCE funcional, usuarios reales creados, 13 empresas sembradas, PGC importado en las 3 instancias FS (13/13 OK), balance de situación y PyG operativos.

### Cambios técnicos

| Archivo | Cambio |
|---------|--------|
| `dashboard/src/index.css` | Login más claro: fondo oklch(0.17), texto inputs visible, placeholder legible |
| `requirements.txt` | Eliminados easyocr/paddlepaddle/paddleocr (CUDA ~8GB en CI) |
| `.github/workflows/deploy.yml` | Paso limpieza disco antes de Docker build |
| `sfce/api/rutas/contabilidad.py` | `func.strftime` → `func.to_char` (3 líneas) para compatibilidad PostgreSQL |
| `scripts/importar_pgc_prod.py` | Script importación PGC en los 3 FS via sesión web curl |

### Producción — estado tras sesión

**Usuarios SFCE creados en PostgreSQL prod:**
- admin@sfce.local (superadmin) — contraseña reseteada, funcional
- sergio@prometh-ai.es (admin_gestoria, gestoria_id=1, empresas [1,2,3,4])
- francisco@, maria@, luis@ @prometh-ai.es (asesor, gestoria_id=1)
  - francisco: empresas [1,2], maria: [3,4], luis: [1,2,3,4]
- gestor1@prometh-ai.es (admin_gestoria, gestoria_id=2, empresas [5,6,7])
- gestor2@prometh-ai.es (admin_gestoria, gestoria_id=2, empresas [8,9])
- javier@prometh-ai.es (admin_gestoria, gestoria_id=3, empresas [10,11,12,13])

**13 empresas sembradas** en PostgreSQL prod con idempresa_fs e instancia FS correcta.

**PGC importado** en las 3 instancias FS (721 subcuentas cada ejercicio, 13/13 OK).
- Nick FS usado: `carloscanete` (max 10 chars, no `carloscanetegomez`)
- URL correcta: `/EditEjercicio?code=X` (no `/index.php?page=...`)

**Balance/PyG**: operativos tras fix `func.strftime` → `func.to_char`. Deploy completado.

### Pendiente conocido
- Smoke test en CI falla por `SFCE_CI_TOKEN` no configurado en GitHub Secrets. El deploy en sí funciona correctamente.

## Sesión 44 — 03/03/2026: Quipu Gerardo 2025 — OCR pipeline completo

### Resumen
Generación de `gastos_gerardo_2025.xlsx` (219 PDFs → Quipu import) para Gerardo González Callejo. Pipeline tres capas: pdfplumber → Mistral OCR → GPT-4o parsing. 219/219 filas, 0 rojas, suma 59.417,01 EUR.

### Scripts creados / modificados
| Archivo | Cambio |
|---------|--------|
| `scripts/generar_quipu_facturas2025.py` | Mistral OCR fallback + GPT-4o parsing + cache en disco |
| `scripts/comparar_ocr_engines.py` | Comparador independiente Mistral / GPT-4o-mini / Gemini |
| `scripts/ocr_cache_gerardo.json` | Cache SHA256 PDF → texto OCR + respuesta GPT (evita re-llamadas) |

### Pipeline OCR implementado
1. **pdfplumber** — gratis, cubre ~80% PDFs con texto nativo
2. **Mistral OCR** (`mistral-ocr-latest`) — para scans/PDFs espejados: $0.002/pág
3. **GPT-4o** — segundo paso cuando regex no extrae número o total del texto OCR
4. **Cache en disco** (`ocr_cache_gerardo.json`) — SHA256 del PDF como clave. Re-ejecuciones: $0

### Comparativa motores (3 facturas Asesoría Laboral escaneadas)
| Motor | numero_factura | total | modo |
|-------|---------------|-------|------|
| Mistral OCR + mistral-small | ✓ | ✓ | OCR nativo → texto |
| GPT-4o-mini | ✓ | ✓ | Vision (imagen PNG via PyMuPDF) |
| Gemini 2.5 Flash | ✓ | ✓ | Vision (imagen PNG via PyMuPDF) |

Los tres sacan los mismos resultados. La diferencia es el modo y el coste.

### Costes reales (corregidos)
| Motor | Precio real |
|-------|------------|
| Mistral OCR | $2.00/1000 págs = $0.002/pág |
| GPT-4o-mini | ~$0.001/llamada (texto o visión) |
| Gemini 2.5 Flash | ~$0.0002/imagen (casi gratis) |
| GPT-4o | $2.50/1M tokens input + $10/1M output (caro) |

### Lecciones de extracción número de factura
- 11 patrones regex con NIF/CIF exclusion (`/` en cadena → nunca es NIF/CIF)
- Patrones DOTALL para valores en línea distinta del label (SkinClinic, WakeUp, Vectem)
- GPT-4o como safety net para casos que el regex no cubre

### Infraestructura
- **PyMuPDF** (`fitz`) para PDF→PNG en Windows (pdf2image requiere Poppler, no instalado)
- **google-generativeai**: usar `from google import genai` + `client.models.generate_content()`
- Gemini: modelo `gemini-2.5-flash` (los modelos `2.0-flash-*` no disponibles para nuevos usuarios en este API key)

---

## Sesión 43 — 02/03/2026: Motor Testeo SFCE — ciclo completo

### Resumen
Primera ejecución completa del Motor de Testeo SFCE (skill `test-engine`). Ciclo 5 fases: reconocimiento → triage → corrección → cobertura → cierre. Suite: 2543→2565 passed, 3→0 fallos.

### Fallos detectados y corregidos

| Fallo | Causa raíz | Fix |
|-------|-----------|-----|
| `test_procesar_cuenta_gestoria_cuarentena_si_remitente_desconocido` | IA clasificaba emails de gestoría como SPAM→IGNORADO | `ingesta_correo.py`: si IA dice IGNORAR en cuenta gestoría, convertir a CUARENTENA |
| `test_migracion_021 × 2` | Módulo `migracion_021_empresa_slug_backfill` eliminado en sesión 37, tests obsoletos | Recrear wrapper importable via `importlib` que apunta a `021_empresa_slug_backfill.py` |

### Tests nuevos generados (cobertura < 80%)

| Archivo | Tests | Qué cubre |
|---------|-------|-----------|
| `tests/test_worker_testing_extra.py` | 8 | Heartbeat Kuma (ok/bugs/error de red), modos vigilancia/regression en `_ids_por_modo`, resultados timeout/bug en `ejecutar_sesion_sincrona` |
| `tests/test_procesador_lote_extra.py` | 5 | `agrupar_por_cliente` con ruta externa (ValueError), `_procesar_grupo` con directorio/excepción, `aptos_automatico`, idempotencia migración 022 |

### Commit
`00ae851` — test: tests adicionales worker_testing y procesador_lote (motor testeo sesion 43)

---

## Sesión 39 — 02/03/2026: Onboarding Histórico + Mejoras Onboarding Masivo

### Resumen
Ejecución del plan `docs/plans/2026-03-02-onboarding-historico.md`. Se generaron datos fiscales ficticios para dos clientes de prueba, se integró FsSetup en `onboarding.py`, y se corrigieron dos bloqueantes del onboarding masivo (soporte modelos 115/180 + fallback NIF desde cabecera PDF).

### Clientes ficticios creados
- **Marcos Ruiz Delgado** (`clientes/marcos-ruiz/`) — autónomo fontanero, ejercicio 2024
  - `datos_fiscales_2024.yaml`: modelos 303×4T, 390, 130×4T, 111×4T, 190, balance, cuenta_pyg
  - `config.yaml`: 5 proveedores, 3 clientes, 1 trabajador
- **Restaurante La Marea S.L.** (`clientes/restaurante-la-marea/`) — SL hostelería, ejercicio 2024
  - `datos_fiscales_2024.yaml`: modelos 303×4T, 390, 111×4T, 190, 115×4T, 180, balance, cuenta_pyg
  - `config.yaml`: 8 proveedores, 3 clientes, 6 trabajadores

### Generador PDFs histórico
- `scripts/generar_onboarding_historico.py` — genera PDFs por cliente/ejercicio desde YAML
- `tests/test_generar_onboarding_historico.py` — 6 tests (existencia, modelos requeridos, balance cuadra)
- Fix: `abs()` eliminado en suma patrimonio_neto para balances con remanente negativo

### FsSetup integrado en onboarding.py
- `scripts/onboarding.py` — nuevo flujo automático FS: pregunta si crear empresa → `FsSetup.setup_completo()` → guarda `idempresa` + `codejercicio`
- Fallback manual conservado para casos sin acceso a FS

### Corrección onboarding masivo (modelos 115/180 + NIF fallback)
Dos clientes pasaron de `BLOQUEADO` a `REVISION` con scores 65/100 y 55/100:
- `sfce/core/onboarding/clasificador.py` — enum `RETENCIONES_115` + `ARRENDAMIENTO_180` + patterns
- `sfce/core/onboarding/parsers_modelos.py` — `parsear_modelo_115()` + `parsear_modelo_180()`
- `sfce/core/onboarding/perfil_empresa.py` — campo `tiene_arrendamientos` + handlers `_incorporar_115/180()`
- `sfce/core/onboarding/procesador_lote.py` — `_PARSERS` actualizado + `_extraer_identidad_de_pdf()` como fallback NIF cuando no hay 036/037

### Tests
39 tests onboarding PASS. Cambios son aditivos (sin tocar lógica de validación que cubre plan de mejoras).

### Próxima sesión
Ejecutar `docs/plans/2026-03-02-onboarding-masivo-mejoras.md` (8 tasks):
- Task 1: Migración 023 — columna `modo` en `onboarding_lotes`
- Task 2: `Acumulador.desde_perfil_existente()`
- Tasks 3-4: Endpoints wizard backend
- Tasks 5-7: UI acordeón + uploader inline + wizard 4 pasos
- Task 8: Suite regresión

---

## Sesión 38 — 02/03/2026: Diseño + Plan Onboarding Masivo Mejoras UX + Wizard

### Resumen
Sesión de diseño y planificación. No se escribió código de implementación.

### Problema detectado
El formulario de Onboarding Masivo decía "ZIP, PDFs, CSVs, Excel — todo vale" pero internamente el 036/037 es obligatorio. Sin él el perfil queda bloqueado sin forma de recuperarlo.

### Solución diseñada (3 capas + 2 modos)
- **Capa A**: acordeón informativo + texto claro sobre requisitos
- **Capa B**: uploader inline en perfiles bloqueados para añadir documentos sin repetir lote
- **Capa C**: fusión automática con notificación cuando llega un 036 que desbloquea un perfil
- **Modo guiado**: wizard 4 pasos como alternativa al flujo ZIP

### Artefactos creados
- `docs/plans/2026-03-02-onboarding-masivo-mejoras-design.md` — documento de diseño aprobado
- `docs/plans/2026-03-02-onboarding-masivo-mejoras.md` — plan de implementación (8 tasks, ~20 tests)

### Plan de implementación (para próxima sesión)
8 tasks TDD listas para ejecutar con `superpowers:executing-plans`:
1. Migración 023 — columna `modo` en `onboarding_lotes`
2. `Acumulador.desde_perfil_existente()` — 5 tests
3. Endpoint `POST /perfiles/{id}/completar` — 5 tests
4. Endpoints wizard backend — 6 tests
5. UI acordeón + botón modo guiado + bloqueados visibles
6. UI uploader inline perfiles bloqueados
7. UI wizard 4 pasos + ruta App.tsx
8. Suite de regresión final

---

## Sesión 37 — 02/03/2026: Auditoría Total + Fixes Producción

### Resumen
Auditoría completa del proyecto con 5 agentes paralelos. Todos los hallazgos corregibles resueltos en código y producción.

### Auditoría
- 5 agentes Explore en paralelo → `docs/auditoria/` (00-resumen + 01-BD + 02-API + 03-seguridad + 04-correo + 05-git)
- Semáforo final: BD 🟡, API 🟢, Seguridad 🟢, Correo 🟢, Git/Tests/Frontend 🟡

### Fixes código (commit `96b5e25`)
- `sfce/api/auth.py`: `_validar_config_seguridad()` falla hard si PostgreSQL y `SFCE_FERNET_KEY` vacía
- `sfce/db/modelos.py`: import automático de `modelos_testing` al final — tablas testing se crean con `create_all()`
- Eliminado `sfce/db/migraciones/migracion_021_empresa_slug_backfill.py` (duplicado)

### Fix migración 019 PostgreSQL (commit `083bd23`)
- `migracion_019_cuentas_correo_gestoria.py` reescrita con soporte dual SQLite/PostgreSQL
- `PRAGMA table_info()` → `information_schema.columns` para PostgreSQL
- `ALTER COLUMN empresa_id DROP NOT NULL` directo en PG (sin recrear tabla)

### Producción (SSH `carli@65.108.60.69`)
- Migraciones 019, 020, 021 ejecutadas vía `docker exec sfce_api`
- `SFCE_FERNET_KEY=tR9_p7xHy6n-DGwY_Coy42rrA1zdye7NY32VEkKojAU=` añadida a `/opt/apps/sfce/.env`
- `docker compose up -d sfce_api` (NO restart — reload env_file requiere recrear container)
- `CuentaCorreo` actualizada: Gmail `admin@prometh-ai.es`, App Password `rfgq bxxt iprx abry`
- IMAP verificado: `admin@prometh-ai.es authenticated (Success)`

### GitHub
- Secret `SFCE_CI_TOKEN` creado (JWT de ci@sfce.local, generado con server's `SFCE_JWT_SECRET`)

### Lecciones aprendidas
- `docker compose restart` NO recarga `env_file`. Usar `docker compose up -d` para recargar `.env`
- Migraciones con `PRAGMA` son SQLite-only. Usar `information_schema.columns` para compatibilidad PG
- Módulos Python que empiezan con dígito (`021_*.py`): importar con `importlib.util.spec_from_file_location()`
- `crear_motor()` sin args → SQLite. En producción siempre `crear_motor(_leer_config_bd())`

---

## Sesión 38 — 02/03/2026: Alta gestoría López de Uralde + limpieza BD

### Resumen
Primera sesión de onboarding con cliente real. BD SFCE local limpiada y reconfigurada.

### Cambios BD SFCE local (sfce.db)
- Todos los datos de prueba borrados (asientos, facturas, documentos, empresas, gestorias, usuarios)
- Conservado: `admin@sfce.local` (superadmin)
- Columnas `reset_token` + `reset_token_expira` añadidas a `usuarios` (faltaban tras limpieza manual sin migraciones)

### Gestoría creada
- **ASESORIA LOPEZ DE URALDE SL** (gestoria_id=1, CIF pendiente confirmar: B92010768)
- 4 usuarios: Sergio (admin_gestoria), Francisco/María/Luis (asesor) — todos con `@prometh-ai.es`
- 4 clientes vinculados con `idempresa_fs` correcto (chiringuito=8, elena=11)
- Asignación: Francisco→Pastorino+Elena, María→Gerardo, Luis→Chiringuito

### FS
- Limpieza empresa 2: 106 FV + 24 asientos eliminados
- Empresas de prueba restantes (1,6,7,8,11) siguen en FS — requieren borrado manual desde panel web

### Carpetas
- Creadas `inbox/` en `clientes/pastorino-costa-del-sol/` y `clientes/elena-navarro/`
- Borrada carpeta `clientes/EMPRESA PRUEBA/` (datos de prueba)

### Credenciales
- `PROYECTOS/ACCESOS.md` sección 27 — gestoría + 4 usuarios + clientes asignados

### Lección aprendida
- Contraseñas con `!` deben crearse con script en fichero (`python archivo.py`), NO con `python -c "..."` en bash — el `!` corrompe el hash bcrypt

---

## Sesión 36 (parte 1) — 02/03/2026: Modelo 190 COMPLETADO

### Implementación completa Modelo 190 — resumen anual retenciones IRPF

**Archivos nuevos:**
- `sfce/core/extractor_190.py` — `ExtractorPerceptores190`: lee NOM+FV de BD, multi-candidate OCR lookup, agrupa por NIF. 5 tests.
- `tests/test_extractor_190.py` — 5 tests extractor
- `tests/test_api_modelos_190.py` — 4 tests API endpoints (perceptores, corregir, generar)
- `dashboard/src/features/fiscal/modelo-190-page.tsx` — página revisión perceptores + inline editing + generación BOE

**Archivos modificados:**
- `sfce/core/calculador_modelos.py` — `calcular_190()`: casillas 16-19 (percepciones+retenciones dinerarias+especie), retorna `declarados`. 5 tests.
- `sfce/api/rutas/modelos.py` — 3 endpoints: `GET /190/{id}/{ej}/perceptores`, `PUT /190/{id}/{ej}/perceptores/{nif}`, `POST /190/{id}/{ej}/generar`
- `dashboard/src/App.tsx` + `app-sidebar.tsx` — ruta `/empresa/:id/modelo-190` + enlace Fiscal sidebar
- `tests/test_calculador_modelos.py` — clase `TestModelo190` (5 tests)
- `docs/LIBRO/_temas/15-modelos-fiscales.md` — secciones CalculadorModelos, calcular_190(), ExtractorPerceptores190, API endpoints, dashboard

**Patrones clave:**
- Descarga BOE: `fetch()` nativo (no `api.post()` que hace `.json()`)
- `declarados` en lugar de `perceptores` (consistencia con calcular_180, calcular_193)
- Perceptor incompleto si NIF=None o percepcion_dineraria<=0; FV excluida si retencion=0

**Tests**: +14 (2413→2527). Commit checkpoint: `9ede1ca`

## Sesión 35 — 02/03/2026: Design + Plan Email Enriquecimiento

### Solo diseño y planificación (sin código implementado)

- **Brainstorming completo**: flujos reales gestoría→prometh-ai, cliente directo, multi-cliente
- **Cambio arquitectónico clave**: migración de Zoho a Google Workspace
- **Nuevo componente diseñado**: `ExtractorEnriquecimiento` — GPT-4o extrae instrucciones contables del cuerpo del email con confianza por campo
- **Flujos documentados**: A (cliente directo), B (gestoría con instrucciones globales), C (multi-cliente un email), D (cliente con instrucciones), E (.eml como adjunto), F (catch-all con slug)
- **Schema `EnriquecimientoDocumento`**: 10 campos (iva_deducible_pct, categoria_gasto, subcuenta_contable, reparto_empresas, regimen_especial, ejercicio_override, tipo_doc_override, notas, urgente) + confianza por campo
- **Integración pipeline**: `registration.py` aplica enriquecimiento con prioridad nivel 6 (>aprendizaje yaml nivel 5 >OCR nivel 3)
- **10 mejoras identificadas** sobre diseño inicial: slug ya existe, DKIM nunca se extrae, parser reenvíos, confianza por campo, pipeline debe leer enriquecimiento, schema formal hints_json, aprendizaje desde confirmaciones, .eml support, notificación inmediata, trazabilidad dashboard
- **13 grietas revisadas**: G1 simplificada (slug ya en BD, solo backfill), G6 integrada en UI de G5
- **Design doc**: `docs/plans/2026-03-02-email-enriquecimiento-design.md`
- **Plan**: `docs/plans/2026-03-02-email-enriquecimiento-plan.md` — 18 tasks, 5 lotes paralelos, ~65 tests
- **Commit**: `ae5b6b3`

## Sesión 28 — 02/03/2026: Email Ingesta Tasks 7-10 + Zoho Mail Tasks 1-5

### Email Ingesta Mejorada — Tasks 7-10
- `ack_automatico.py` — 7 templates, sin ACK a no-autorizados. `enviar_raw()` en EmailService. 9 tests.
- `ingesta_correo.py` — integra filtro_ack + score + extractor_adjuntos + _encolar_archivo. 3 tests.
- `daemon_correo.py` — loop async polling. Registrado en lifespan app.py con cancelación limpia. 2 tests.
- `onboarding_email.py` — generar_slug_unico + configurar_email_empresa + whitelist. `empresas.py`: campo email_empresario. 6 tests.
- 118 tests totales en `tests/test_correo/`

### Zoho Mail por Gestoría — Tasks 1-5 (via hooks automáticos)
- Migración 019: gestoria_id + tipo_cuenta + empresa_id nullable en cuentas_correo
- CuentaCorreo ORM: nuevos campos gestoria_id, tipo_cuenta
- ingesta_correo.py: rama gestoria — routing por reglas, omite cuentas 'sistema' en polling
- API correo admin: CRUD cuentas superadmin + GET/PUT por gestoría
- docs/zoho-setup.md + .env.example: variables SMTP/DNS Zoho. 19 tests.

### Estado cierre sesión 28
- 8 commits locales pendientes push (origin en `7ed754e`)
- Tests: ~2417 collected, ~2405 PASS
- Pendiente: Zoho Mail Tasks 6-9 (Dashboard UI, deploy prod, libro)

## Sesión 26 — 02/03/2026: Diseño Zoho Mail por Gestoría

### Solo diseño y planificación (sin código implementado)

- Brainstorming completo: 3 enfoques evaluados, aprobado Enfoque A (catch-all + buzón por gestoría)
- Diseño guardado: `docs/plans/2026-03-02-zoho-email-gestoria-design.md`
- Plan de implementación (9 tasks, ~35 tests): `docs/plans/2026-03-02-zoho-email-gestoria.md`
- Añadido método `enviar_raw()` a `email_service.py` (cabeceras opcionales)

**Arquitectura decidida:**
- `noreply@prometh-ai.es` → SMTP saliente
- `docs@prometh-ai.es` → catch-all para `slug+tipo@prometh-ai.es`
- `gestoriaX@prometh-ai.es` → un buzón por gestoría, routing por remitente

**Próxima sesión:** ejecutar plan `2026-03-02-zoho-email-gestoria.md` con `superpowers:executing-plans`

---

## Sesión 23 — 02/03/2026: Diseño Email Ingesta Mejorada

### Diseñado: sistema de ingesta documental por email

**Contexto:** Se identificó que el módulo de correo existente (`sfce/conectores/correo/`) tenía 3 gaps críticos:
- `IngestaCorreo` no encolaba PDFs en `ColaProcesamiento`
- No había daemon de polling registrado en el lifespan del API
- El onboarding no generaba dirección email dedicada por empresa

**Mejoras diseñadas y planificadas:**
- Extractor de adjuntos multi-formato: ZIP recursivo (depth=2), zip-bomb detection, ZIPs con contraseña, XLS/TXT/XML/IMG
- Parser FacturaE XML: extracción sin OCR, confianza 1.0
- Filtro anti-loop ACK: detecta respuestas automáticas por asunto y cabecera `X-SFCE-ACK`
- Whitelist de remitentes por empresa (dominio wildcard + email exacto)
- Score multi-señal (whitelist + DKIM + filename + historial), umbrales 0.85/0.60
- ACK automático categorizado por motivo, nunca ACK a `REMITENTE_NO_AUTORIZADO`
- Conexión `IngestaCorreo → ColaProcesamiento` (gap crítico cerrado)
- Daemon de polling registrado en lifespan FastAPI
- Onboarding genera slug + CuentaCorreo + whitelist inicial + dirección dedicada

**Plan:** `docs/plans/2026-03-02-email-ingesta-mejorada.md` — 10 tasks, 84 tests
**Commit:** `195e570`

---

## Sesión 22 — 02/03/2026: Onboarding Masivo Parte 1 (Tasks 1-6)

### Implementado: pipeline de ingesta documental masiva

**Task 1 — Prerequisites** (`sfce/db/modelos.py`, `sfce/core/tiers.py`, `sfce/core/fs_setup.py`, `sfce/core/config_desde_bd.py`)
- `EstadoOnboarding.CREADA_MASIVO = "creada_masivo"` añadido al enum
- `FEATURES_GESTORIA["onboarding_masivo"] = Tier.PRO`
- `importar_pgc(tipo_pgc="general")` — soporte PGC general/pymes/esfl/cooperativas
- `_FORMA_A_TIPO` movida a nivel de módulo + `"arrendador"` añadido
- `datos["empresa"]` expone: `recc`, `prorrata_historico`, `bins_por_anyo`, `tipo_is`, `es_erd`, `retencion_facturas_pct`, `obligaciones_adicionales`

**Task 2 — Migración 017** (`sfce/db/migraciones/migracion_017_onboarding_masivo.py`)
- 4 tablas nuevas: `onboarding_lotes`, `onboarding_perfiles`, `onboarding_documentos`, `bienes_inversion_iva`
- Ejecutada en BD real (sfce.db)

**Task 3 — Clasificador** (`sfce/core/onboarding/clasificador.py`)
- 19 tipos detectados: modelos fiscales (036/037, 200, 202, 303, 390, 130, 131, 100, 111, 190, 347, 184), escrituras, libros CSV/Excel
- PDF: patrones regex por cabecera AEAT. CSV/Excel: columnas clave
- Fix: threshold texto vacío 50→20 chars

**Task 4 — Parsers libros AEAT** (`sfce/core/onboarding/parsers_libros.py`)
- `parsear_libro_facturas_emitidas` — agrega clientes + importe habitual
- `parsear_libro_facturas_recibidas` — agrega proveedores + importe habitual
- `parsear_sumas_y_saldos` — saldos por subcuenta + check cuadre (tolerancia 1€)
- `parsear_libro_bienes_inversion` — bienes con años regularización IVA

**Task 5 — Parsers modelos fiscales** (`sfce/core/onboarding/parsers_modelos.py`)
- `parsear_modelo_200`: tipo_is, es_erd, bins_total
- `parsear_modelo_303`: recc, trimestre, prorrata_pct
- `parsear_modelo_390`: prorrata_definitiva
- `parsear_modelo_130`: trimestre, pago_fraccionado
- `parsear_modelo_100`: retencion_pct, pagos_fraccionados_total
- `parsear_modelo_111`: trimestre, tiene_trabajadores

**Task 6 — PerfilEmpresa** (`sfce/core/onboarding/perfil_empresa.py`)
- `PerfilEmpresa`: dataclass con 25+ campos fiscales/contables
- `Acumulador`: incorpora datos de 10+ tipos de documento
- `Validador`: checks duros (NIF, 036, P.Vasco/Navarra) + blandos + score 0-100
- Score ≥85 → apto creación automática. <85 → revisión manual
- Detección territorio por CP (prefijo 01/20/48→PV, 31→NAV, 35/38→CAN, 51→CEU, 52→MEL)

**Tests**: 27 nuevos (6 archivos) + 1 regresión arreglada en test_fs_setup. Suite total: 2296/2296 PASS → 2323/2323 PASS

**Commits**: fcedd67 → d872f52 (7 commits en main)

---

## Sesión 21 — 02/03/2026: App móvil operativa + recuperar contraseña

### Problema resuelto: app móvil no funcionaba en dispositivo real
- `mobile/constants/api.ts`: fallback `localhost:8000` → `https://api.prometh-ai.es`
- La app ya funciona desde cualquier dispositivo sin configuración extra

### Recuperar contraseña
- **Backend**: `POST /api/auth/recuperar-password` + `POST /api/auth/reset-password`
  - Genera token 32-byte seguro, válido 2h, almacenado en `usuarios.reset_token`
  - Con SMTP: envía email con código. Sin SMTP: loguea token (WARNING en logs)
- **Mobile**: `mobile/app/(auth)/recuperar-password.tsx` — 2 pasos (email → token+nueva contraseña)
- **Login**: enlace "¿Olvidaste tu contraseña?" bajo botón Entrar
- **Migración 017**: columnas `reset_token` + `reset_token_expira` en `usuarios`
- **Modelo**: `sfce/db/modelos_auth.py` — 2 campos nuevos en `Usuario`
- **Email service**: método `enviar_reset_password()` añadido

### Migraciones desplegadas en producción
- 015 `mensajes_empresa` ✓
- 016 `push_tokens` ✓
- 017 `reset_token` (ALTER TABLE directamente en PG) ✓

### Otros
- `.gitignore`: añadir `sfce/docs/` (carpeta PDFs, no va a git)
- `scripts/uk_crear_monitores.py`: script Playwright para Uptime Kuma

### Commits
- `7ba3f36` chore: ignorar sfce/docs/ + script Uptime Kuma
- `92e3ea6` feat: recuperar contraseña en app móvil + fix URL API → producción

---

## Sesión 20 — 02/03/2026: Onboarding Masivo — diseño y plan

### Solo diseño/planificación (sin código)

**Feature**: alta automatizada masiva de todos los clientes de una gestoría a partir de documentos fiscales (PDFs, CSVs, Excel).

### Documentos creados
- `docs/plans/2026-03-02-onboarding-masivo-design.md` — diseño completo: 9 tipos entidad, 6 regímenes transversales, PerfilEmpresa, flujo 7 fases, 6 conflictos con código existente
- `docs/plans/2026-03-02-onboarding-masivo-plan-parte1.md` — Tasks 1-6: Prerequisites, Migración 017, Clasificador, Parsers libros IVA/IRPF/bienes, Parsers modelos fiscales, PerfilEmpresa+Acumulador+Validador
- `docs/plans/2026-03-02-onboarding-masivo-plan-parte2.md` — Tasks 7-12: Motor creación, Procesador lotes, API endpoints, Dashboard, E2E tests, Suite final (~42 tests total)

### Conflictos críticos identificados (ya documentados en el plan)
1. `pipeline_runner.py` requiere slug no-null → generar automáticamente
2. `ActivoFijo` no tiene campos IVA → nueva tabla `bienes_inversion_iva`
3. `EstadoOnboarding` falta `CREADA_MASIVO`
4. `forma_juridica` falta `arrendador`
5. `FEATURES_GESTORIA` vacío → añadir `onboarding_masivo: Tier.PRO`
6. `fs_setup.py` sin parámetro `tipo_pgc` → no soporta ESFL/Cooperativas

### Próximos pasos
1. Sesión A: ejecutar Parte 1 con `superpowers:executing-plans`
2. Sesión B: ejecutar Parte 2 (depende de Parte 1)

---

## Sesión 16 — 02/03/2026: Evaluación canales de acceso + Brainstorming app móvil

### Evaluado (sin código)
- Canales de acceso al sistema: dashboard web (localhost), app móvil (prototipo), app escritorio (no existe), producción (no expuesta)
- App de escritorio descartada por ahora. Cuando se haga: Electron envolviendo el mismo React, capa nativa solo para certificados digitales FNMT/AEAT
- App móvil = versión de bolsillo del dashboard. Una app, experiencia adaptada por rol al login

### Diseño aprobado — App Móvil Rediseño Home-First
- `docs/plans/2026-03-02-mobile-app-redesign-design.md` — diseño completo, 5 pilares
- `docs/plans/2026-03-02-mobile-app-redesign.md` — plan 10 tareas listo para ejecutar

**5 pilares definidos:**
1. Semáforo fiscal por empresa (verde/amarillo/rojo)
2. "Ahorra X€ al mes" — previsión IVA+IRPF traducida a consejo mensual
3. Gestor supervisor — home ordenada por urgencia, aprobación con un toque
4. Comunicación contextual — mensajes ligados a documentos o períodos fiscales
5. Foto enriquecida — nota libre para el gestor al subir documento

**Arquitectura:**
- Backend: 2 endpoints nuevos portal (semáforo + ahorra-mes) + tabla mensajes_empresa + tabla push_tokens + servicio Expo Push API
- Mobile: home cliente rediseñada, home gestor con semáforo, pantalla mensajes, push notifications

### Tests
Sin cambios en tests (sesión de diseño/planificación)

---

## Sesión 15 — 02/03/2026: Deploy prometh-ai.es implementado (Tasks 1-11/12)

### Implementado
- `requirements.txt`: 88 dependencias pinned para imagen Docker Python 3.12
- `GET /api/health`: endpoint sin auth para monitorización (TDD, 4 tests)
- `Dockerfile` multi-stage python:3.12-slim con HEALTHCHECK integrado
- `docker-compose.yml`: servicio sfce_api con healthcheck + log rotation
- nginx `app-prometh-ai.conf`: React SPA + proxy /api/ + WebSocket + cache assets
- nginx `api-prometh-ai.conf`: API directa + CORS restringido a app.prometh-ai.es
- `.github/workflows/deploy.yml`: CI/CD 4 jobs (test ‖ build-frontend → build-docker → deploy SSH)
- `scripts/migrar_sqlite_a_postgres.py`: one-time migration SQLite→PG, dry-run OK (547 filas)
- `scripts/infra/setup-prometh-ai.sh`: guía setup + creación dirs en servidor
- `.env.example`: variables dev/prod documentadas

### Tests
2239 passed (era 2234 + 4 health nuevos)

### Pendiente (Task 12 — pasos manuales servidor)
DNS (en proceso), SSL certbot, nginx configs, .env producción, migración BD, GitHub Secrets (8), deploy trigger, Uptime Kuma monitores

---

## 2026-03-02 (sesión 14) — Diseño y plan deploy SFCE → prometh-ai.es

**Objetivo**: Planificar el despliegue del dashboard SFCE en producción bajo prometh-ai.es.

**Resultado**: Design doc + plan de implementación completo (12 tasks). Sin código implementado aún.

**Archivos creados**:
- `docs/plans/2026-03-02-deploy-prometh-ai-design.md` — Arquitectura completa
- `docs/plans/2026-03-02-deploy-prometh-ai.md` — Plan 12 tasks con código exacto

**Decisiones arquitectónicas**:
- `app.prometh-ai.es` + `api.prometh-ai.es` (subdominios separados)
- nginx en `app.` proxea `/api/` → sfce_api (sin cambios en código frontend)
- Docker Compose + imagen GHCR (`ghcr.io/carlincarlichi78/spice:latest`)
- GitHub Actions 4 jobs: test ‖ build-frontend → build-docker → deploy SSH
- Migración SQLite → PostgreSQL 16 con script one-time idempotente
- Workers como asyncio tasks en el mismo contenedor uvicorn (no contenedores separados)

**Próxima sesión**: ejecutar plan con `superpowers:executing-plans`

---

## 2026-03-02 (sesión 13) — Auditoría profunda 8 sistemas + fix P0 seguridad IDOR

**Objetivo**: Auditoría sistemática de los planes 10-17 implementados ayer: Tablero Usuarios, Canal Onboarding, Tiers, App Móvil, Notificaciones, Advisor Platform, Flujo docs→pipeline, Fix roles.

### Auditoría (4 agentes en paralelo)
- **19 bugs críticos** identificados, **16 problemas de seguridad**, **20 de calidad**, **22 ideas**
- Hallazgo principal: 6 vulnerabilidades IDOR/escalada de privilegios en `verificar_acceso_empresa()` y endpoints asociados

### Fix P0 — IDOR + Escalada (commit `e6361a8`)
**Causa raíz**: `verificar_acceso_empresa()` usaba `gestoria_id is None` como proxy de superadmin, lo que:
- Trataba a clientes directos (`gestoria_id=None`) como superadmin → acceso total a todas las empresas
- No verificaba `empresas_asignadas` para clientes con gestoría → IDOR entre clientes de la misma gestoría
- 5 endpoints de portal y gestor no llamaban a `verificar_acceso_empresa()` en absoluto

**Fixes aplicados**:
- `sfce/api/auth.py` — `verificar_acceso_empresa()` reescrita: lógica por rol explícito (superadmin/cliente/gestor)
- `sfce/api/rutas/portal.py` — añadida verificación en `subir_documento`, `aprobar_documento`, `rechazar_documento`, `notificaciones_portal`, `proveedores_frecuentes`
- `sfce/api/rutas/gestor.py` — añadida verificación en `notificar_cliente`; import de `verificar_acceso_empresa`
- `sfce/api/rutas/admin.py` — `actualizar_plan_usuario`: `admin_gestoria` solo modifica usuarios de su gestoria (escalada lateral bloqueada)
- `tests/test_portal_revision.py` + `tests/test_seguridad/test_rgpd.py` — roles legacy corregidos (`gestor`→`asesor`, `readonly`→`cliente`)

**Resultado**: 2234/2234 PASS

### LIBRO actualizado
- `docs/LIBRO/_temas/22-seguridad.md` — sección `verificar_acceso_empresa()` completamente reescrita con nueva lógica, lista de endpoints que la usan, e IDOR histórico documentado

### Pendientes P1 (próxima sesión)
1. Unificar `datetime.now(timezone.utc)` en auth_rutas.py (mezcla utcnow/now)
2. Race condition worker_pipeline: marcar PROCESANDO atómicamente antes de retornar docs
3. Percentiles P25/P50/P75 con interpolación lineal (benchmark_engine.py)
4. Empresas nuevas en Autopilot: `dias_sin_datos=999` → falsa alarma crítica
5. Consolidar GestorNotificaciones (en-memory) → NotificacionUsuario (BD)

### Commits sesión 13
- `e6361a8` fix: P0 security — IDOR en verificar_acceso_empresa + escalada plan_tier

---

## 2026-03-02 (sesión 12) — Auditoría estado proyecto + fix roles auth

**Objetivo**: Inventariar el estado real de todos los planes, verificar suite completa y corregir inconsistencias de roles surgidas al implementar Tablero Usuarios.

### Hallazgos
- Advisor Intelligence Platform: 37 tests PASS, todos los archivos presentes — faltaba solo el registro en CLAUDE.md
- Flujo documentos portal→pipeline: 32 tests PASS — estado correcto, marcado en CLAUDE.md
- Suite completa: 9 FAILED + 7 ERRORS en `test_auth.py` — bug de roles no detectado

### Fix: roles auth (sesión 12)
**Causa**: Al implementar Tablero Usuarios (sesión 4) se cambió `crear_admin_por_defecto` de `rol='admin'` a `rol='superadmin'`, pero los endpoints CRUD legacy de `auth_rutas.py` seguían usando `requiere_rol("admin")`.
- `sfce/api/rutas/auth_rutas.py` — `requiere_rol("admin")` → `requiere_rol("superadmin")` en POST/GET `/api/auth/usuarios`; `roles_validos` → `{"admin_gestoria", "asesor", "asesor_independiente", "cliente"}`
- `sfce/api/rutas/rgpd.py` — `_ROLES_EXPORTACION` actualizada (admin/gestor → asesor/asesor_independiente)
- `tests/test_auth.py` — roles corregidos en 16 sitios (admin→superadmin, gestor→asesor, readonly→cliente)
- **Resultado**: 2234/2234 PASS

### Commits
- `baf4ce4` fix: roles auth — admin→superadmin, gestor→asesor, readonly→cliente
- `9b828b9` docs: CHANGELOG + LIBRO — módulos dashboard y BD actualizados

---

## 2026-03-02 (sesión 10) — SFCE Advisor Intelligence Platform (17 tasks)

**Objetivo**: Implementar la capa analítica premium del SFCE: star schema OLAP-lite, SectorEngine YAML, BenchmarkEngine anónimo, Autopilot de asesor y 6 dashboards especializados en el frontend.

**Ejecución**: Subagent-Driven Development — 17 tasks con ciclo implementer → spec review → quality review por task.

### Backend analytics (`sfce/analytics/`)
- `sfce/analytics/sector_engine.py` — SectorEngine: carga reglas YAML por CNAE (`hosteleria.yaml`), calcula KPIs (ticket_medio, RevPASH, coste_por_comensal), genera alertas por umbral
- `sfce/analytics/benchmark_engine.py` — BenchmarkEngine: percentiles P25/P50/P75 anónimos por CNAE. `MIN_EMPRESAS=5`, `KPI_SOPORTADOS={"ticket_medio"}`. Función pública `calcular_kpi_empresa` + privada `_calcular_kpi_empresa`. `posicion_en_sector()` retorna rojo/amarillo/verde
- `sfce/analytics/autopilot.py` — Briefing semanal del asesor: `ItemBriefing` dataclass, `generar_briefing()` que prioriza rojo→amarillo→verde, títulos y borradores de mensaje automáticos
- `sfce/analytics/reglas_sectoriales/hosteleria.yaml` — KPIs (7) y alertas (4) para sector hostelería CNAE 561x

### Base de datos
- `sfce/db/migraciones/012_star_schema.py` — 6 tablas: `eventos_analiticos`, `fact_caja`, `fact_venta`, `fact_compra`, `fact_personal`, `alertas_analiticas`. Migración ejecutada en BD real
- `sfce/db/migraciones/014_cnae_empresa.py` — campo `cnae VARCHAR(4)` en tabla `empresas`. Idempotente

### API analytics (`sfce/api/rutas/analytics.py`)
- `GET /api/analytics/{empresa_id}/kpis` — KPIs calculados por SectorEngine
- `GET /api/analytics/{empresa_id}/resumen-hoy` — Snapshot diario (demo/fact_caja)
- `GET /api/analytics/{empresa_id}/ventas-detalle` — Evolución ventas 6 meses
- `GET /api/analytics/{empresa_id}/compras-proveedores` — Top proveedores por gasto
- `GET /api/analytics/{empresa_id}/sector-brain` — Benchmarks anónimos por KPI (requiere cnae + ≥5 empresas)
- `GET /api/analytics/autopilot/briefing` — Briefing semanal del asesor (declarado antes de `/{empresa_id}` para evitar conflicto de rutas)

### Frontend Advisor (`dashboard/src/features/advisor/`)
- `api.ts` — `advisorApi`: portfolio, kpis, resumenHoy, ventasDetalle, comprasProveedores, sectorBrain, autopilotBriefing
- `types.ts` — tipos TypeScript del módulo Advisor
- `advisor-gate.tsx` — Guard tier-premium: overlay Lock + CTA → /configuracion/plan
- `command-center-page.tsx` — Grid por empresa con salud/alertas/KPIs. `refetchInterval: 60_000`. Sub-components: HealthBar, VariacionBadge, EmpresaCard
- `restaurant-360-page.tsx` — Dashboard hostelería: PulsoHoy (Canvas + `useAnimatedCounter(val, dur, decimals)`), HeatmapSemanal (Canvas DPR), TopVentas, WaterfallP&L (ComposedChart stacked), ComparativaHistorica (LineChart + selector periodo). `HORAS_APERTURA=8` constante nombrada
- `product-intelligence-page.tsx` — MatrizBCG (Canvas DPR), FoodCostEvolucion (Recharts + ReferenceLine 30%), HistorialCompras (tabla + `MiniSparkline` SVG 60×20px), CostesFamilia (PieChart donut)
- `sector-brain.tsx` — Gauge con marcadores P25/P50/P75 y punto empresa. Estado `disponible/no-disponible`
- `autopilot-page.tsx` — `BriefingCard` por empresa, urgencia coloreada, textarea `borrador_mensaje` expandible
- `sala-estrategia-page.tsx` — Simulador what-if EBITDA: `simular()` función pura, 8 sliders, `useMemo`, guard división por cero, Recharts BarChart

### Routing y navegación
- `dashboard/src/App.tsx` — 5 rutas `/advisor/*` lazy con alias `@/`, todas en `<AdvisorGate>`
- `dashboard/src/components/layout/app-sidebar.tsx` — grupo "Advisor" con `useTiene('advisor_premium')` guard, Zap icon para Autopilot
- `dashboard/src/hooks/useTiene.ts` — +6 feature flags: `advisor_premium/sector_brain/temporal_machine/autopilot/simulador` → premium; `advisor_informes` → pro

### Tests
- `tests/test_benchmark_engine.py` — 4 tests (sector sin datos, empresa sin CNAE, empresa en sector, cálculo percentiles)
- `tests/test_autopilot.py` — 4 tests (usuario no encontrado, empresa rojo, empresa verde, ordenación rojo-primero)
- **Total**: 2213 PASS (+8 vs sesión 9)

### Build
- `npm run build` — 4.50s, 131 entries (antes 119, +12 chunks advisor), 0 errores TypeScript

**Commits**: sesión 10 (48 commits pusheados a origin/main)

---

## 2026-03-01 (sesión 8) — Notificaciones cliente + historial docs + campos adaptativos

**Objetivo**: Completar la experiencia del empresario en la app móvil: recibe notificaciones del gestor, ve su historial de documentos, el formulario de subida se adapta al tipo de documento.

**Sistema de Notificaciones BD** (para app móvil):
- `sfce/db/migraciones/011_notificaciones_usuario.py` — nueva tabla `notificaciones_usuario` (empresa_id, documento_id, titulo, descripcion, tipo, origen, leida, fecha_creacion/lectura)
- `sfce/core/notificaciones.py` — módulo completo satisfaciendo 59 tests preexistentes + nuevo bloque BD: `crear_notificacion_bd()`, `evaluar_motivo_auto()`, `MOTIVOS_AUTO_NOTIFICAR` (duplicado/ilegible/foto borrosa)
- `scripts/pipeline.py` — hook post-intake: `_sincronizar_cuarentena_bd()` + `evaluar_motivo_auto` → notifica auto al empresario para motivos configurados
- `sfce/api/rutas/gestor.py` — `POST /api/gestor/empresas/{id}/notificar-cliente` — gestor crea notificación manual desde dashboard
- `sfce/api/rutas/portal.py` — `GET /{id}/notificaciones` (incluye notifs BD + onboarding + docs pendientes) + `POST /{id}/notificaciones/{id}/leer`
- `dashboard/src/features/documentos/cuarentena-page.tsx` — botón "Notificar" por fila + `NotificarDialog` (título+mensaje editables)

**ProveedorSelector adaptativo** (`mobile/components/upload/ProveedorSelector.tsx`):
- Nueva prop `tipoDoc` — formula campos específicos por tipo documento
- `CAMPOS_POR_TIPO`: Factura (nombre*, CIF*, base, total*), Ticket (nombre*, CIF, total*), Nómina (trabajador*, NIF*, salario*, retención, cuota SS), Extracto (entidad*, IBAN, período*, saldo), Otro (descripción*, importe)
- Para Factura/Ticket muestra proveedores frecuentes; para el resto va directo al formulario
- Fotos obligan a rellenar campos requeridos (`obligatorio=true`)

**App Móvil — empresario** (`mobile/app/(empresario)/subir.tsx`):
- Reescritura completa: NativeWind → StyleSheet.create()
- `tipoDoc` + `obligatorio` siempre activo (empresario solo usa fotos)
- Envía todos los campos extra en FormData; resumen paso 3 muestra entidad/descripción además de nombre

**Nueva pantalla historial** (`mobile/app/(empresario)/documentos.tsx`):
- Tab "Docs" en el layout del empresario
- Lista de documentos con chip de estado coloreado (pendiente/procesado/cuarentena/error)
- Consulta `GET /api/portal/{id}/documentos` — corregido `nombre_archivo` → `ruta_pdf`

**Portal API extendido** (`sfce/api/rutas/portal.py`):
- `POST /{id}/documentos/subir` — 9 campos extra opcionales (nómina/extracto/otro), guardados en `datos_ocr`
- `GET /{id}/documentos` — fix campo `nombre` (usaba `d.nombre_archivo` inexistente → `d.ruta_pdf`)

**Commits**: `24dd4c6` (sistema notificaciones), `f94ddb4` (historial docs + campos adaptativos)

---

## 2026-03-01 (sesión 5) — Actualización Libro Instrucciones

**Objetivo**: Actualizar los archivos del libro (`docs/LIBRO/_temas/`) con todos los cambios de la sesión 4 que habían quedado sin documentar.

**Archivos actualizados**:
- `11-api-endpoints.md`: rol `gestor` en jerarquía, `/me` documenta `gestoria_id`+`empresas_asignadas`, `aceptar-invitacion` con rate limit, `invitar-cliente` roles actualizados, `mis-empresas` acceso gestor
- `13-dashboard-modulos.md`: página `aceptar-invitacion-page`, PortalLayout con guard, ProtectedRoute bloquea clientes, InvitarClienteDialog, loginConToken, patrón redirect-por-rol
- `22-seguridad.md`: nueva sección §11 "Guards de autenticación en el frontend" (ProtectedRoute, PortalLayout, redirect por rol)
- `28-roadmap.md`: Tests E2E tablero completados (4 PASS), nueva sección "Canal de acceso y onboarding" como próxima sesión

---

## 2026-03-01 (sesión 4) — Tablero de Usuarios E2E + Fixes de Seguridad

**Objetivo**: Verificar end-to-end los 4 niveles del tablero de usuarios con Playwright. Corregir bugs encontrados durante el testing.

**Tests Playwright E2E (4 scripts, todos PASS)**:
- `scripts/test_crear_gestoria.py` — nivel 0: superadmin crea gestoría + invita admin
- `scripts/test_nivel1_invitar_gestor.py` — nivel 1: admin acepta invitación + invita gestor
- `scripts/test_nivel2_invitar_cliente.py` — nivel 2: gestor acepta invitación + invita cliente al portal (idempotente)
- `scripts/test_nivel3_cliente_directo.py` — nivel 3: superadmin crea cliente directo sin gestoría

**Bugs corregidos**:
- `InvitarClienteDialog` no importada en ningún componente → añadida a `usuarios-page.tsx`
- Inputs del dialog sin `id` → añadidos `id="nombre"` e `id="email"`
- Rol `gestor` ausente en `roles_permitidos` de `invitar-cliente` → añadido
- Redirect post-aceptación a `/` en lugar de `/portal` para clientes → decode JWT para detectar rol
- `PortalLayout` sin guard de autenticación → añadido `if (!token) return <Navigate to="/login">`
- `ProtectedRoute` no bloqueaba clientes del dashboard → añadido check `if (usuario?.rol === 'cliente')`
- `/me` devolvía `empresas_ids` pero portal usaba `empresas_asignadas` → campos unificados
- `aceptar-invitacion` sin rate limit → añadido `Depends(_rate_limit_login)`
- `usuarios-page.tsx` mostraba lista global de usuarios (leak) → eliminado, solo `InvitarClienteDialog`
- `rgpd.py` devolvía `url` pero portal esperaba `url_descarga` → añadido alias
- `button.tsx` + `dialog.tsx` sin `forwardRef` → convertidos (Radix Slot compat)
- Seed `auth.py`: `rol='admin'` en lugar de `'superadmin'` → corregido

**Commits**: `a618356`, `a95a713`, `3aa24af`, `e3fc088`

---

## 2026-03-01 (sesión 3) — Tablero de Usuarios SFCE — 12 tasks implementados

**Objetivo**: Diseñar e implementar el sistema completo de jerarquía de usuarios en 4 niveles (tablero de juego).

**Diseño**: Design doc `docs/plans/2026-03-01-tablero-usuarios-design.md` — 4 niveles:
- Nivel 0: Super-admin operativo (todo el poder)
- Nivel 1: La gestoría puede jugar (invitación, panel propio)
- Nivel 2: Alta de cliente con historia (OCR 036 + escrituras + FS setup + migración histórica)
- Nivel 3: Cliente en su portal (portal multi-empresa, invitación cliente)

**Backend nuevos**: `email_service.py`, `ocr_036.py`, `ocr_escritura.py`, `fs_setup.py`, `migracion_historica.py`, `sfce/api/rutas/migracion.py`

**Backend modificados**: `auth_rutas.py` (aceptar-invitacion), `admin.py` (clientes directos, panel gestorías completo), `portal.py` (mis-empresas), `empresas.py` (invitar-cliente)

**Frontend nuevos**: `features/admin/api.ts`, `gestorias-page.tsx`, `features/mi-gestoria/api.ts`, `mi-gestoria-page.tsx`, `features/portal/mis-empresas-page.tsx`, `features/empresa/invitar-cliente-dialog.tsx`

**Frontend modificados**: `App.tsx` (rutas /admin/gestorias, /mi-gestoria, /portal), `app-sidebar.tsx` (links por rol), `types/index.ts` (admin_gestoria, gestoria_id)

**Tests nuevos**: test_auth (4), test_admin (11), test_email_service (2), test_ocr_036 (6), test_ocr_escritura (5), test_fs_setup (3), test_migracion_historica (5), test_portal_mis_empresas (2) = 38 tests nuevos

**Tests totales**: 2133 PASS | **Build**: 4.53s, 113 entries

---

## 2026-03-01 (noche 2) — MCF Motor Clasificación Fiscal — Completado y mergeado a main

**Objetivo**: completar las tareas pendientes de la rama `feat/motor-clasificacion-fiscal`.

**Completado**:
- **53 tests ClasificadorFiscal** (`tests/test_clasificador_fiscal.py`): 9 bloques — detección país/régimen, 12 categorías de gasto, suplidos aduaneros, wizard tipo_vehiculo, wizard inicio_actividad, wizard pct_afectacion, divisa extranjera, confianza/trazabilidad, a_entrada_config
- **Handler `iva_turismo_50`** en `correction.py`: Art.95.Tres.2 LIVA — detecta partida 472, genera corrección split 50% deducible + 50% gasto 6280, con guard anti-duplicados. También añade `regla_especial_iva_turismo_50` a `_aplicar_correccion`
- **Wizard MCF** en `intake._descubrimiento_interactivo`: reemplaza 8 preguntas manuales por clasificación automática MCF. Muestra resumen (categoría, IVA, IRPF, confianza, razonamiento), luego solo pregunta lo ambiguo (0-3 preguntas según categoría). Usa `a_entrada_config` para construir la entrada
- **`sfce/core/informe_cuarentena.py`**: informe estructurado de cuarentena combinando tabla BD + PDFs en carpeta. Enriquece items tipo "entidad" con sugerencias MCF. Genera JSON en `auditoria/` + texto legible para terminal. 17 tests en `test_informe_cuarentena.py`
- **Fix coherencia_fiscal.yaml**: Portugal corregido a `intracomunitario` (era extracomunitario incorrectamente). Fix test `test_reglas_pgc.py::test_cif_portugues` para reflejar corrección

**Tests**: 2095 PASS (70 nuevos). Merge a main. Commit: `812bda2`

---

## 2026-03-01 (noche) — Dashboard Rediseño Total: Implementación COMPLETADA

**Objetivo**: Ejecutar el plan de implementación del dashboard redesign (FASES 5, 7, 8 pendientes).

**Completado**:
- **Task 5.1**: CHART_COLORS en 6 archivos (pyg, balance, amortizaciones, cobros-pagos, salud, home) — elimina colores hardcodeados
- **Task 5.2**: EmptyState con CTAs en scoring-page y pipeline-page
- **Task 7.1**: Configuración page — sidebar 18 secciones/6 grupos, SeccionTarjetas con toggles localStorage
- **Task 8.1**: Page transitions — `@keyframes page-enter` 150ms ease-out + `key={location.pathname}` en AppShell
- **Task 8.2**: `use-keyboard-shortcuts.ts` — G+C/F/D/E/R/H navega módulos empresa, ignora INPUT/TEXTAREA
- **Build**: ✓ 4.65s, TypeScript clean, 109 entries precacheadas

**Commits**: `3835a2e`, `718d680`, `297f50e`, `8386606`, `4d355c2`

---

## 2026-03-01 (tarde) — Dashboard Rediseño Total: Diseño y Planificación

**Objetivo**: Analizar el dashboard actual, diseñar el rediseño total y planificar la implementación en 8 fases.

**Actividad**:
- Análisis visual completo con Playwright (22 screenshots de todas las páginas)
- Bugs críticos detectados: cards fondo BLANCO en dark mode (KPIs/Tesorería/Scoring/Pipeline), charts con colores random, Libro Diario microscópico
- Diseño completo aprobado: design system con tokens semánticos, sidebar colapsable con empresa pill, OmniSearch ⌘K, Home como Centro de Operaciones con tarjetas enriquecidas, página /configuracion con 18 secciones
- Enfoque C aprobado: reescritura total con design system primero

**Archivos creados**:
- `docs/plans/2026-03-01-dashboard-redesign-total-design.md`
- `docs/plans/2026-03-01-dashboard-redesign-total-implementation.md`

**Commits**: `ab57077`, `9a16e28`

**SIGUIENTE**: Nueva sesión → `superpowers:executing-plans` con plan de implementación, empezar por F0

---

## 2026-03-01 — Sesion: Planes PROMETH-AI revisados + integraciones CAP-Web/CertiGestor/Desktop

**Objetivo**: Revisar y pulir planes de implementación PROMETH-AI con integraciones reales.

**Realizado**:
- **Planes escritos** (sesión anterior): `fases-0-3.md` (21 tasks) + `fases-4-6.md` (12 tasks)
- **Crítica de planes**: 20+ problemas identificados (Gate0↔OCR desconectados, webhook sin auth, tests teatro, endpoint `/api/alertas` inexistente, etc.)
- **CAP-Web analizado** (`C:/Users/carli/PROYECTOS/CAP-WEB/`): email module 1146 líneas vs SFCE 467. Graph/O365 solo en CAP-Web. Identificado como referencia de código, no integración de servicio.
- **CertiGestor analizado** (`C:/Users/carli/PROYECTOS/proyecto findiur/`): SaaS + Electron full. Scrapers AEAT/DEHú/DGT/eNotum/SS en desktop Electron. API de datos portable.
- **fases-0-3.md actualizado**:
  - Task 12: nota CAP-Web email module como referencia + Graph O365 a portar
  - Task 13: reescrito completamente → módulo nativo `CertificadoAAP`+`NotificacionAAP` (SQLAlchemy, portado de findiur TypeScript)
  - Task 14: webhook con auth HMAC-SHA256 (`X-CertiGestor-Signature`), guarda en `NotificacionAAP`
- **fases-4-6.md actualizado**:
  - Task 7: referencia a `extractor-nif.ts` + `clasificador-emails.ts` de findiur
  - Task 8: referencia a `imap_service.py` CAP-Web para catch-all polling
  - **Fase 11 añadida**: PROMETH-AI Desktop — fork de `proyecto findiur/apps/desktop/`, ~1-2 días trabajo (90% reutilizado), 4 tasks (fork, adaptar sync→HMAC, UI config, electron-builder Win/Mac/Linux)
- **Plataformas definidas**: Web (en construcción) + PWA móvil (ya hecha) + Desktop Electron (Fase 11)
- **tmpclaude-* limpiados** del directorio, añadidos a .gitignore

**Decisiones arquitectónicas**:
- CertiGestor Electron no se puede portar a servidor (requiere P12 en máquina gestor)
- CAP-Web es fuente de código, no servicio a integrar
- PROMETH-AI Desktop = fork findiur/apps/desktop/ con endpoint → PROMETH-AI API

## 2026-03-01 — Sesion: Dominio prometh-ai.es + preparacion web nueva

**Objetivo**: Conectar dominio prometh-ai.es al servidor Hetzner y preparar para web nueva PROMETH-AI.

**Realizado**:
- DNS A records configurados en DonDominio: apex + www → 65.108.60.69
- Eliminados registros parking DonDominio (ANAME apex, wildcard CNAME `*.prometh-ai.es`, www CNAME)
- Nginx config HTTP creada: `/opt/infra/nginx/conf.d/prometh-ai.conf` (redirect HTTP→HTTPS + ACME challenge)
- Nginx recargado y verificado funcionando localmente
- Diagnóstico: dominio registrado hoy (01/03/2026) → nic.es tarda 2-24h en propagar delegación NS (normal para .es nuevo)
- SSL pendiente: ejecutar certbot cuando dig @8.8.8.8 resuelva

**Pendiente para proxima sesion**:
1. Verificar propagacion DNS (`dig +short prometh-ai.es @8.8.8.8` = 65.108.60.69)
2. Ejecutar certbot para SSL
3. Actualizar nginx con bloque HTTPS
4. Disenar y construir web nueva PROMETH-AI (objetivo principal)

---

## 2026-03-01 — Sesion: Brainstorming plan completo PROMETH-AI

**Objetivo**: Revisar design doc Ingesta 360, mapear estado real del proyecto, disenar onboarding + importacion historica.

**Realizado**:
- Verificado estado real del plan 28/02: Tasks 1-8 completadas, Tasks 9-14 pendientes (CLAUDE.md estaba desactualizado)
- Decisiones confirmadas: incluir Task 9 + CertiGestor + onboarding + importacion historica
- Mapeados 4 flujos de onboarding: gestoria, gestor/asesor, asesor independiente, empresa/cliente
- Identificado gap critico: pipeline lee config.yaml pero SaaS necesita leer de BD → solucion hibrida generar_config_desde_bd()
- Disenada importacion historica en 5 sub-fases (ZIP/perfil auto → Excel/CSV → AEAT → contabilidad → software contable)
- Plan completo: 14 fases (0-13), desde seguridad P0 hasta WhatsApp
- Guardado en `docs/plans/2026-03-01-brainstorming-prometh-ai-completo.md`

**Proxima sesion**: writing-plans sobre Fases 0-6 (primer plan), luego Fases 7-11 (segundo plan)

---

## 2026-03-01 — Sesion: Rebrand PROMETH-AI + configuracion email

**Objetivo**: Rebrand de SPICE a PROMETH-AI, compra dominio, configuracion email profesional.

**Realizado**:
- Confirmados 2 planes pendientes de implementar: Ingesta 360 Fases 4-10 + Dashboard Rewrite
- Rebrand decidido: SPICE → PROMETH-AI
- Dominio `prometh-ai.es` comprado en DonDominio (expira 2028)
- Email forwarding configurado con ImprovMX (free plan, sin SMS):
  - Catch-all `*@prometh-ai.es → carlincarlichi@gmail.com`
  - MX1: mx1.improvmx.com (prio 10), MX2: mx2.improvmx.com (prio 20)
  - SPF TXT: `v=spf1 include:spf.dondominio.com include:spf.improvmx.com ~all`
- Decision: NO segundo VPS — PROMETH-AI corre en servidor existente 65.108.60.69
- ACCESOS.md actualizado: secciones 23 (ImprovMX) y 24 (dominio)

**Zoho Mail descartado**: verificacion SMS bloqueada (+34 627333631 no recibe SMS en datacenter EU).

---

## 2026-03-01 — Sesion: Brainstorming SPICE Ingesta 360

**Objetivo**: Disenar el sistema de ingesta automatizada 360 grados de SPICE.

**Brainstorming**:
- Mapeados 6 tipos de actores (superadmin, admin gestoria, gestor, asesor, cliente directo, empleado)
- Escenario de referencia: 3 gestorias + 1 asesor + 5 clientes directos = 58 empresas
- 6 canales de entrada: IMAP polling, email dedicado catch-all, portal web, ZIP masivo, CertiGestor bridge, WhatsApp
- Sistema de trust levels: sistema > gestor > cliente
- Scoring automatico: decide auto-publicar vs cola revision vs cuarentena
- Colas de revision por nivel: gestor → admin gestoria → superadmin
- Sistema de enriquecimiento (hints pre-OCR del emisor)
- Supplier Rules en BD (evolucion de aprendizaje.yaml)
- Tracking de documentos visible para todos los actores
- FS obligatorio como corazon contable (SPICE automatiza, FS registra)

**Decision clave**: NO sobredimensionar. PostgreSQL para colas (no Redis), disco local (no S3), IMAP (no Postfix).

**Investigacion**: patrones de Dext, AutoEntry, Hubdoc, DATEV, Nanonets. Email routing por slug, supplier rules aprendidas, WhatsApp Business API.

**Seguridad P0 identificados**: path traversal en nombres archivo email, IDOR email huerfano, limite uploads, validacion contenido PDF.

**Design doc**: `docs/plans/2026-03-01-spice-ingesta-360-design.md`
**Prerequisito**: plan `2026-02-28-plataforma-unificada-integracion.md` se ejecuta primero (Fases 1-3).

---

## 2026-03-01 — Sesion: Seguridad multi-tenant + limpieza + merge main

**Objetivo**: Cerrar bugs de seguridad de auditoría y hacer merge a main.

**Seguridad multi-tenant**:
- `sfce/api/rutas/modelos.py`: añadida `verificar_acceso_empresa()` en `POST /calcular`
- `sfce/api/rutas/economico.py`: 7 endpoints migrados de `request.app.state.sesion_factory` a DI inyectada
- `sfce/api/rutas/rgpd.py`: revertido auth extra en descarga (token JWT de un solo uso es el mecanismo correcto)
- `sfce/api/rutas/documentos.py`: ya tenía verificación correcta (false positive del audit)

**Limpieza código muerto**:
- `scripts/phases/` borrado completo (9 archivos, ~5000 líneas)
- `dashboard/src/api/client.ts`, `Sidebar.tsx`, `Layout.tsx` borrados
- `.gitignore`: añadidos `sfce.db`, `tmp/`, `.coverage`, `*.tmp.*`
- Desrastreados archivos ignorados que se habían colado en la rama

**Tests**: 1793 passed, 0 failed. Test `test_calcular_303_empresa_sin_datos` y `test_calcular_con_override` actualizados con `token_superadmin`.

**Git**: merge `feat/frontend-pwa` → `main`, push a GitHub.

---

## 2026-03-01 — Sesion: Auditoria profunda + unificacion arquitectura scripts/sfce

**Objetivo**: Auditoria general del proyecto + correccion de bugs criticos + eliminacion de duplicidades arquitectonicas.

**Auditoria (4 agentes paralelos)**:
- 93 hallazgos totales: 14 criticos, 29 altos, 30 medios, 20 bajos
- Dominios: `sfce/api/` (28), `sfce/core/db/phases/` (18), `dashboard/src/` (20), `scripts/ vs sfce/` (27)

**Bugs criticos corregidos**:
- `sfce/api/rutas/portal.py`: AttributeError en produccion — `Asiento.codejercicio`→`.ejercicio`, `Partida.codsubcuenta`→`.subcuenta`, `Documento.tipo`→`.tipo_doc`
- `sfce/core/backend.py`, `exportador.py`, `importador.py`: cross-imports circulares `scripts.core.logger` → `sfce.core.logger`
- `sfce/phases/correction.py:548`: token FacturaScripts hardcodeado (credencial expuesta en codigo) → `obtener_token()` + `API_BASE`
- `sfce/api/websocket.py`: `except Exception: pass` silencioso → logging correcto

**Refactor arquitectura (commit 94448e1)**:
- 11 archivos duplicados eliminados de `scripts/core/`: logger, fs_api, errors, aritmetica, confidence, aprendizaje, prompts, reglas_pgc, ocr_mistral, ocr_gemini, historico
- `scripts/core/config.py` y `asientos_directos.py` conservados (divergencia funcional real; sus imports internos corregidos a `sfce.core.*`)
- `scripts/pipeline.py` migrado de `scripts/phases/` → `sfce/phases/` (pipeline unificado)
- Feature "FV sin CIF buscar por nombre" (RD 1619/2012) portada de `scripts/` a `sfce/`:
  - `sfce/core/config.py`: nuevos metodos `buscar_cliente_por_nombre()` + `buscar_cliente_fallback_sin_cif()`
  - `sfce/phases/intake.py`: fallback por nombre cuando CIF no encontrado en FV
  - `sfce/phases/pre_validation.py`: validacion FV con fallback completo
- Tests redirigidos: 12 archivos de test actualizados (`scripts.core.*` → `sfce.core.*`, `scripts.phases.*` → `sfce.phases.*`)
- Resultado final: **1793 tests PASS, 0 failed** (vs 1793 pre-refactor: sin regresiones)
- Estadisticas commit: 40 archivos, 2001 lineas eliminadas, 97 insertadas

**Pendiente para proxima sesion**:
- Bugs auditoria alta prioridad: `modelos.py:70` (multi-tenant), `rgpd.py:136` (acceso empresa), `economico.py:196` (DI sesion), `documentos.py:99` (verificar_acceso_empresa)
- Borrar `scripts/phases/` (codigo muerto post-unificacion)
- Limpiar `.gitignore`: `sfce.db`, `tmp/`, `.coverage`

---

## 2026-02-28 — Sesion: Fix arranque dashboard + bugs contabilidad

**Objetivo**: Arrancar el dashboard local y corregir errores en módulo de contabilidad.

**Completado**:
- `.claude/launch.json` actualizado con env vars (`SFCE_JWT_SECRET`, `SFCE_CORS_ORIGINS`, etc.) para que `preview_start` arranque la API correctamente
- `iniciar_dashboard.bat` creado para arranque rápido manual
- **Fix `contabilidad.py`**: `int(ejercicio)` reventaba con codejercicio tipo `"C422"` → sustituido por `func.strftime("%Y", Asiento.fecha)` en `pyg2` y `balance2`
- **Fix `contabilidad.py`**: `func.case()` no existe en SQLAlchemy 2.x → sustituido por `case()` importado directamente
- Commit: `4b34691`

---

## 2026-02-28 — Sesion: Dashboard Rewrite Stream A (ejecutar plan)

**Objetivo**: Ejecutar Stream A del plan de implementacion del dashboard rewrite.

**Trabajo realizado**:
- A1-A7: Dependencias, path alias, Zustand stores, API client, React Query, formatters, layout system (AppShell, Header, Sidebar, Breadcrumbs), componentes compartidos (KPICard, ChartCard, DataTable, PageHeader, EstadoVacio), stubs de todas las paginas
- A8: Home page — selector empresa (tarjetas con CIF/forma juridica/regimen IVA), KPIs (ingresos/gastos/resultado/IVA/cobros/pagos), AreaChart evolucion mensual, PieChart gastos por categoria, timeline actividad reciente
- A9: Contabilidad 8 paginas — PyG, Balance, Diario (tabla expandible partidas), Plan Cuentas, Conciliacion (stub), Amortizaciones, Cierre (stepper), Apertura
- A10: Facturacion 5 paginas — Emitidas, Recibidas, Cobros/Pagos aging (4 buckets), Presupuestos (stub), Contratos (stub)
- A11: Fiscal 4 paginas — Calendario, Modelos, Generar, Historico
- A12: Documentos 4 paginas — Inbox, Pipeline (Progress bars), Cuarentena, Archivo
- A13: RRHH 2 paginas — Nominas (masa salarial), Trabajadores (DataTable)
- A14: Borrar 20 archivos src/pages/ (paginas antiguas)
- A15: Dark mode — hook useThemeEffect, toggle Header, variables CSS .dark ya existian
- A16: TypeScript 0 errores, vite build OK (4.07s)
- Fix: stubs Stream B (economico/) usaban prop `empresaId` en lugar de `useParams` → corregido
- Fix: errores TS en configuracion/ (integraciones, usuarios) → corregido
- Fix: errores TS en copilot/ → corregido

**Estado final**: 40 paginas en 13 modulos, TypeScript limpio, build OK, push a GitHub.
**Commits**: 10 commits en feat/sfce-v2-fase-e (A1-A16 + fix + docs)

---

## 2026-02-27 — Sesion: Dashboard Rewrite Design + FS Admin Setup

**Objetivo**: Auditar dashboard actual, disenar rewrite completo como producto SaaS, configurar admin en FacturaScripts.

**Trabajo realizado**:
- Auditoria completa dashboard (frontend 19 paginas ~5700 LOC + backend 35 endpoints)
- Brainstorming interactivo: stack, arquitectura, 38 paginas en 10 secciones
- Modulo economico-financiero: 30+ ratios, KPIs sectoriales, tesoreria, centros coste, scoring
- Copiloto IA: 6 capas (prompt, RAG, function calling, knowledge base, feedback, respuestas enriquecidas)
- Design doc completo: `docs/plans/2026-02-27-dashboard-rewrite-design.md` (590 lineas)
- FacturaScripts: creado usuario `carloscanetegomez` (admin nivel 99) + empresa 6 "GESTORIA CARLOS CANETE"
- CLAUDE.md reducido de 468 a 132 lineas

**Stack aprobado**: shadcn/ui + Recharts + React Query + Zustand + React Hook Form + Zod + Tailwind v4

**Pendiente**: plan de implementacion (writing-plans skill), luego ejecucion rewrite

**Commit**: 35ed2fe en `feat/sfce-v2-fase-e`

---

## 2026-02-27 — Sesion: Dual Backend FS+BD local + Dashboard operativo

**Objetivo**: Pipeline actualice automaticamente la BD local (dashboard) al registrar en FS, sin migracion manual.

**Trabajo realizado**:
- Implementado dual backend (`sfce/core/backend.py`) con 3 modos: fs, local, dual
- Pipeline instancia `Backend(modo="dual")` y lo pasa a registration/correction/asientos_directos
- `_sincronizar_asientos_factura_a_bd()` captura asientos post-correcciones en BD local
- Param `solo_local=True` para sync sin reenviar a FS
- Migradas 5 empresas a SQLite (205 asientos empresa 5)
- Dashboard operativo: API FastAPI (8000) + Vite dev (3000) con proxy
- `resumen_fiscal.py` ampliado con empresas 3, 4, 5
- Fix `launch.json`: Vite dev server en vez de static serve (proxy necesario)

**Verificacion**:
- Pipeline 1 SUM (EMASAGRA) → asiento sincronizado a BD (id=391, idasiento_fs=2131, 3 partidas)
- Antes: 205 asientos, despues: 207 asientos en empresa 5

**Archivos modificados**: backend.py, registration.py, correction.py, asientos_directos.py, pipeline.py, resumen_fiscal.py, launch.json

**Commit**: f0c8909 en `feat/sfce-v2-fase-e`

---

## 2026-02-27 — Sesion: E2E dry-run elena-navarro + pipeline fix

**Objetivo**: Ejecutar pipeline SFCE contra elena-navarro (generador v2) para validar ingesta multi-tipo.

**Trabajo realizado**:
- Creado config.yaml elena-navarro desde empresas.yaml (10 proveedores, 3 clientes, 1 trabajador)
- Creado .env con API keys (FS, Mistral, OpenAI, Gemini) — anadido a .gitignore
- Muestra estratificada 30% (60/199 PDFs) en inbox_muestra/ para controlar costes OCR
- Dry-run exitoso: 41 procesados, 19 cuarentena, score 100%

**Bug fix**:
- `PatronRecurrente` (dataclass) no serializable a JSON en pipeline.py → `dataclasses.asdict()`

**Hallazgos**:
- FC/BAN/NOM/RLC/IMP: 100% deteccion
- FV: 27% — clientes sin CIF van a cuarentena (problema sistemico)
- SUM: 0% → proveedores faltaban en config (Endesa, Emasagra, Movistar, Mapfre anadidos post-test)
- GPT-4o rate limited (30K TPM) → Tier 1 degradado frecuentemente
- OCR Tiers: T0=10 (24%), T1=30 (73%), T2=1 (2%)

**Propuesta proxima sesion**: Directorio empresas — BD compartida proveedores/clientes con auto-resolve CIF

**Commit**: d6bca4e en `feat/sfce-v2-fase-e`

---

## 2026-02-27 — Sesion: SFCE v2 Fase E (Ingesta Inteligente)

**Objetivo**: Implementar Fase E del plan SFCE Evolucion v2 (Tasks 38-46).

**Fase E completada (Tasks 38-46)**:
- T38: nombres.py — convencion naming carpetas/documentos (30 tests)
- T39: cache_ocr.py — cache .ocr.json junto al PDF con SHA256 (31 tests)
- T40: duplicados.py — deteccion duplicados seguro/posible/ninguno (32 tests)
- T41: detectar_trabajador + agregar_trabajador con persistencia YAML (11 tests)
- T42: ingesta_email.py — IMAP, adjuntos PDF, enrutamiento por remitente (34 tests)
- T43: notificaciones.py — 7 tipos, gestor multicanal log/email/websocket (59 tests)
- T44: recurrentes.py — patrones facturas recurrentes + alertas faltantes (32 tests)
- T45: generar_periodicas.py — asientos automaticos amortizaciones/provisiones (49 tests)
- T46: tests integracion Fase E — 8 escenarios cross-modulo (31 tests)

**Infra**: PR #1 mergeada, branch feat/sfce-v2-fase-e creada desde main
**Tests totales**: 954 PASS (+309 nuevos)
**Progreso plan v2**: 46/46 tasks (100%) — PLAN COMPLETADO

---

## 2026-02-27 — Sesion: SFCE v2 Fase D (API + Dashboard + Infra GitHub)

**Objetivo**: Implementar Fase D del plan SFCE Evolucion v2.

**Fase D completada (Tasks 28-37)**:
- T28: FastAPI base con Pydantic schemas, CORS, lifespan BD, 5 routers (35 tests)
- T29: JWT auth con bcrypt directo (no passlib), 3 roles admin/gestor/readonly (33 tests)
- T30: WebSocket con canales por empresa, asyncio.Lock, 6 tipos evento (21 tests)
- T31: Scaffolding React dashboard — routing, AuthContext, API client, useWebSocket
- T32-T33: Dashboard empresas+contabilidad — PyG, Balance, Diario paginado, Facturas, Activos
- T34-T35: Dashboard procesamiento — Inbox, Pipeline real-time, Cuarentena, Importar/Exportar, Calendario, Cierre
- T36: File watcher con watchdog, 3 modos (manual/semi/auto), debounce (35 tests)
- T37: Sistema licencias JWT, modulos, max_empresas, verificacion arranque (42 tests)

**Infra GitHub**:
- Repo creado: `carlincarlichi78/SPICE` (privado)
- PR #1 abierta: feat/sfce-v2-fase-d → main (+11,109 -171 lineas, 70 archivos)
- Limpieza git: 234 binarios (PDFs/Excel/JSON clientes) eliminados del tracking
- `.gitignore` actualizado: excluye binarios clientes, build artifacts, node_modules

**Fix notable**: passlib incompatible con bcrypt 5.x → se usa bcrypt directamente

**Tests totales**: 645 PASS (+166 nuevos)
**Branch**: `feat/sfce-v2-fase-d`
**Progreso plan v2**: 37/46 tasks (80%)

---

## 2026-02-27 — Sesion: SFCE v2 Fases B+C (motor central + BD)

**Objetivo**: Implementar Fases B y C del plan SFCE Evolucion v2.

**Fase B completada (Tasks 11-19)**:
- Clasificador contable cascada 6 niveles (`sfce/core/clasificador.py`)
- MotorReglas — cerebro del sistema, orquesta clasificador+normativa+perfil fiscal (`sfce/core/motor_reglas.py`)
- Integrado en registration.py, correction.py, asientos_directos.py y pipeline.py
- MotorReglas hecho OBLIGATORIO (sin fallback legacy)
- Calculador modelos fiscales 3 categorias: automaticos, semi-auto, asistidos (`sfce/core/calculador_modelos.py`)
- Procesador notas credito con busqueda factura original (`sfce/core/notas_credito.py`)
- 12 tests integracion end-to-end. 392 tests totales

**Fase C completada (Tasks 20-27)**:
- BD dual SQLite(WAL)/PostgreSQL via SQLAlchemy (`sfce/db/`)
- 14 tablas: empresas, proveedores_clientes, trabajadores, documentos, asientos, partidas, facturas, pagos, movimientos_bancarios, activos_fijos, operaciones_periodicas, cuarentena, audit_log, aprendizaje_log
- Repositorio con queries especializadas: saldo_subcuenta, PyG, balance, facturas_pendientes
- Backend doble destino FS+BD local con fallback si FS falla
- Importador CSV/Excel con auto-deteccion separador y formato europeo
- Exportador universal: libro diario CSV/Excel, facturas CSV, Excel multi-hoja
- Migrador FS→BD local (`scripts/migrar_fs_a_bd.py`)
- 12 tests integracion. 479 tests totales

**Tests totales**: 479 PASS
**Branch**: `feat/sfce-v2-fase-d` (D preparada, directorios creados)
**Progreso plan v2**: 27/46 tasks (59%)

---

## 2026-02-27 — Sesion: SPICE Landing Page (implementacion + deploy)

**Objetivo**: Implementar y desplegar landing page profesional de SPICE para presentar a gestoria.

**Trabajo realizado**:
- Scaffold React 19 + Vite 7 + Tailwind v4 + TypeScript en `spice-landing/`
- 17 componentes: Navbar, Hero, Problema, Vision, DiagramaPipeline, DiagramaOCR, TiposDocumento, DiagramaJerarquia, DiagramaClasificador, Trazabilidad, MapaTerritorios, DiagramaCiclo, ModelosFiscales, DiagramaAprendizaje, FormasJuridicas, Resultados, Footer
- 2 hooks (useInView, useCountUp), 6 archivos de datos
- Build: 280KB JS + 44KB CSS, 0 errores TS
- Deploy completo:
  - DNS: A record `spice.carloscanetegomez.dev` → 65.108.60.69 (Porkbun)
  - SSL: certbot Let's Encrypt
  - Nginx: `/opt/infra/nginx/conf.d/spice-landing.conf`
  - Archivos: `/opt/apps/spice-landing/`

**URL**: https://spice.carloscanetegomez.dev
**Commit**: 7f109e0 en `feat/sfce-v2-fase-b`
**Design**: `docs/plans/2026-02-27-spice-landing-design.md`
**Plan**: `docs/plans/2026-02-27-spice-landing-implementation.md`

---

## 2026-02-27 — Sesion: Implementacion Fase A SFCE v2

**Objetivo**: Implementar Tasks 1-10 de la evolucion SFCE v2 (Fase A: Fundamentos).

**Trabajo realizado**:
- T1: Paquete sfce/ con pyproject.toml, 14 core + 8 phases copiados, imports relativos corregidos
- T2: sfce/normativa/vigente.py + 2025.yaml — 5 territorios fiscales (peninsula, canarias IGIC, ceuta/melilla IPSI, navarra, pais vasco), SS, umbrales, plazos, amortizacion
- T3: sfce/core/perfil_fiscal.py — 11 formas juridicas, 5 territorios, 8 regimenes IVA, derivacion automatica modelos/libros
- T4: 3 YAMLs catalogos — regimenes_iva (8), regimenes_igic (5), perfiles_fiscales (11 plantillas)
- T5: ConfigCliente ampliado con PerfilFiscal + seccion trabajadores + busqueda por DNI
- T6: sfce/core/backend.py — abstraccion sobre fs_api con mocks limpios
- T7: sfce/core/decision.py — DecisionContable con trazabilidad, genera partidas multi-regimen (IVA parcial, recargo, ISP, retencion)
- T8: sfce/core/operaciones_periodicas.py — amortizacion lineal, provision pagas extras, regularizacion IVA con prorrata, periodificacion
- T9: sfce/core/cierre_ejercicio.py — regularizacion 6xx/7xx contra 129, gasto IS, cierre todas cuentas, apertura ejercicio nuevo
- T10: Tests integracion Fase A — 11 tests verificando conexion entre todos los modulos

**Tests**: 189 existentes + 114 nuevos = 303 total PASS
**Branch**: `feat/sfce-v2-fase-a` (10 commits)

---

## 2026-02-27 — Sesion: Revision y ampliacion plan SFCE Evolucion

**Objetivo**: Revisar plan v1 de evolucion SFCE antes de implementar. Identificar huecos y ampliar.

**Trabajo realizado**:
- Revision critica del design doc v1 y plan v1 (38 tasks)
- Identificados huecos: operaciones contables incompletas, territorios solo peninsula, BD sin audit trail, modelos fiscales todos como automaticos
- Discusion y aprobacion de 8 areas de mejora con el usuario
- Escrito design doc v2 (`sfce-evolucion-v2-design.md`, 1265 lineas, 28 secciones)
- Escrito plan implementacion v2 (`sfce-evolucion-v2-implementation.md`, 1453 lineas, 46 tasks)
- Actualizado CLAUDE.md con estado v2

**Decisiones tomadas**:
- Ciclo contable completo desde el principio (cierre, amortizaciones, provisiones, regularizacion IVA)
- 5 territorios fiscales (peninsula, canarias, ceuta_melilla, navarra, pais_vasco)
- 13 tablas BD con audit_log, pagos, movimientos_bancarios, activos_fijos
- Doble motor SQLite/PostgreSQL via SQLAlchemy
- Modelos fiscales en 3 categorias (automaticos/semi-auto/asistidos)
- Modelo 200 IS semi-automatico (borrador contable + gestor completa ajustes extracontables)
- Modelo 100 IRPF solo asistido (SFCE aporta rendimientos actividad, gestor hace en Renta Web)
- Provision pagas extras: configuracion por trabajador, no inferida. Deteccion automatica de trabajador nuevo via DNI en nomina
- Trazabilidad completa: log razonamiento JSON por cada asiento
- Cuarentena estructurada con 7 tipos y preguntas tipadas
- Sin Nuitka. Proteccion via OCR proxy + token + SaaS
- Claude Code siempre en la ecuacion (dashboard complementa)
- Nominas: OCR extrae importes ya calculados, no recalculamos SS/IRPF. Normativa sirve para validar coherencia

**Proxima sesion**: implementar Fase A (Tasks 1-10)

## Sesión 2026-03-01 (sesión 4) — Actualización Libro de Instrucciones

### Objetivo
Puesta al día del Libro de Instrucciones (`docs/LIBRO/_temas/`) tras innumerables mejoras acumuladas desde su creación. 12 archivos actualizados en paralelo con agentes.

### Archivos del libro actualizados
| Archivo | Cambios principales |
|---|---|
| `06-motor-reglas.md` | MCF completo (50 categorías, campos YAML, base legal LIVA/LIRPF/LIS), normativa multi-territorio (península, Canarias IGIC, Navarra, País Vasco, Ceuta) |
| `22-seguridad.md` | Rate limiting VentanaFijaLimiter, account lockout, 2FA TOTP flow, RGPD nonces, migraciones 001+003 |
| `11-api-endpoints.md` | 125 endpoints documentados (antes 106), tablero usuarios, portal multi-empresa, estadísticas globales |
| `17-base-de-datos.md` | 39 tablas, multi-tenant completo, migraciones 001-006, nombres reales SQLAlchemy |
| `13-dashboard-modulos.md` | Rediseño total, stack real con versiones, 25 módulos, tema OKLCh, keyboard shortcuts, PWA |
| `05-ocr-ia-tiers.md` | Worker OCR async, recovery bloqueados, OCR 036/037, OCR escrituras, caché SHA256 |
| `04-gate0-cola.md` | Scoring 5 factores con pesos reales, bloqueo duro coherencia, campos cola nuevos |
| `02-sfce-arquitectura.md` | 12 componentes nuevos en diagrama, jerarquía usuarios, MCF, normativa |
| `23-clientes.md` | Flujos invitación token, 4 roles, portal multi-empresa, idempresa=6 |
| `28-roadmap.md` | Estado limpio y real, sin contenido obsoleto de proyectos anteriores |
| `08-aprendizaje-scoring.md` | Supplier Rules BD, migración YAML→BD, convivencia entre sistemas |
| `07-sistema-reglas-yaml.md` | Inventario con líneas/entradas reales, normativa/2025.yaml, detalle MCF |

### Nueva obligación añadida a CLAUDE.md
Actualizar el libro en cada cierre de sesión, con el mismo nivel de detalle con que fue elaborado.

---

## Sesión 4 — 01/03/2026: Tablero Usuarios E2E + Auditoría Seguridad

### Tests E2E Playwright implementados y verificados (PASS)
- `test_crear_gestoria.py` (nivel 0), `test_nivel1_invitar_gestor.py`, `test_nivel2_invitar_cliente.py`, `test_nivel3_cliente_directo.py`
- Descubierto: nivel 2 era falso positivo (email en input, no en URL de invitación) → fijo

### Bugs corregidos
| Bug | Archivo | Fix |
|-----|---------|-----|
| seed rol="admin" en lugar de "superadmin" | `sfce/api/auth.py` | Correcto a "superadmin" |
| /me sin gestoria_id | `auth_rutas.py` | Añadido + empresas_asignadas unificado |
| Radix Slot requiere forwardRef | `button.tsx`, `dialog.tsx` | Convertidos con React.forwardRef |
| Redirect post-invitación igual para todos | `aceptar-invitacion-page.tsx`, `login-page.tsx` | Decode JWT → cliente va a /portal |
| Cliente accedía al AppShell | `ProtectedRoute.tsx` | Bloqueo → /portal si rol=cliente |
| PortalLayout sin auth | `portal-layout.tsx` | Guard → /login si sin token |
| gestor no podía invitar cliente | `empresas.py` | Añadido "gestor" a roles_permitidos |
| url_descarga mismatch | `rgpd.py` | Añadido campo alias |
| usuarios-page filtraba todos usuarios | `usuarios-page.tsx` | Eliminado leak global |
| aceptar-invitacion sin rate limit | `auth_rutas.py` | Añadido Depends(_rate_limit_login) |

### Commits
- `a618356` feat: tablero usuarios — flujo invitaciones E2E completo (niveles 0-3)
- `a95a713` fix: redirect cliente a /portal, unificar empresas en /me
- `3aa24af` fix: seguridad roles — cliente bloqueado AppShell, rate limit invitacion
- `e3fc088` fix: 4 bugs reales — url_descarga, portal auth guard, gestor invita cliente, usuarios-page

---

## Sesiones 55-65 — 03/03/2026 – 04/03/2026 (archivado desde CLAUDE.md)

> Historial detallado de estas sesiones estaba en CLAUDE.md. Movido aquí para reducir contexto.

### Sesion 55 — Pipeline Gerardo 8 bugs + crearFacturaProveedor 2 pasos
- 8 bugs corregidos: gemini deprecado→2.5-flash, SmartParser fields (emisor_cif no proveedor_cif), CIF intracomunitario endswith, fecha inglesa, campos _*, fecha DD-MM-YYYY, FS url override
- Bloqueado en crearFacturaProveedor multi-empresa → migrado a POST 2 pasos (sesion 58)

### Sesion 57 — WebSocket tarjetas empresa tiempo real
- Auth JWT en WebSocket: `verificar_token_ws()` codigo 4401/4403
- Eventos desde worker_pipeline: `pipeline_progreso`, `documento_procesado`, `cuarentena_nuevo`
- `use-empresa-websocket.ts` + EmpresaCard spinner + ultima actividad + alerta cuarentena

### Sesion 58 — Pipeline 2 pasos + Auditoria completa
- `registration.py` usa `_crear_factura_2pasos()` (ya existia, no conectada)
- FE-1: localStorage → sessionStorage. API-3: crear_motor(_leer_config_bd()). VULN-1: log token → sha256[:12]
- BUG-4: subprocess → asyncio.to_thread. VULN-4/5/6: verificar_acceso_empresa. FE-3: roles reales

### Sesion 59 — Portal cliente operativo
- Login Gerardo gerardo.gonzalez@gmail.com / Uralde2026! → /portal/2
- Fix ejercicio_activo: str(date.today().year). Nginx no-cache SW.

### Sesion 60 — Mejoras ingesta email + Inbox Watcher diseno
- Forwarding entre asesores (reenvio.py). Atomicidad por email. Timeout IMAP 30s. N+1 → bulk query
- Plan: docs/plans/2026-03-03-inbox-watcher.md

### Sesion 61 — Inbox Watcher Tasks 1-5
- sfce.empresa_id en 6 config.yaml. Variables .env watcher. TDD FileStabilizer, _cargar_empresa_id, _subir_pdf
- 17 tests en test_watcher.py

### Sesion 62 — Inbox Watcher completo (Tasks 6-9)
- _procesar_archivo + startup_scan. InboxEventHandler + main() watchdog Observer
- iniciar_dashboard.bat: 3a ventana "SFCE Watcher". 2661 tests PASS (+23)

### Sesion 63 — Cuentas IMAP por asesor
- Migracion 028: usuario_id INTEGER en cuentas_correo
- _extraer_cif_pdf() + _resolver_empresa_por_cif() en ingesta_correo.py
- Rama tipo='asesor': routing CIF → empresa asignada, fallback cuarentena
- API: CrearCuentaAdminRequest.usuario_id + POST /admin/cuentas/{id}/test
- Dashboard: seccion "Cuentas IMAP Asesores" con badge activa + boton Probar
- Script seed: scripts/crear_cuentas_imap_asesores.py (App Passwords pendientes)
- 2665 PASS (+4), 4 skipped

### Sesion 64 — Fix pipeline email asesor E2E
- Fix _construir_email_asesor: no asignaba _decision_encola → PDF nunca se encolaba
- Fix extractor_adjuntos: adj.get("contenido") or adj.get("datos_bytes", b"")
- E2E verificado: email → EmailProcesado CLASIFICADO → cola_procesamiento PENDIENTE

### Sesion 65 — Panel documentos + asiento FS on-demand
- GET /api/documentos/{empresa_id}/{doc_id}/asiento-fs: consulta FS lazy sin guardar en BD
- Boton lazy DocumentoPanel: useQuery(enabled: buscarFs), TablaPartidas reutilizable
- Design doc conciliacion bancaria: motor 5 capas + aprendizaje + UI panel sugerencias
- Commit: c190f04 (asiento-fs) + 0cc971d (design doc conciliacion)
