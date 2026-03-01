# Libro de Instrucciones — Edicion Personal

> **Publico:** Carlos — acceso completo a todos los temas
> **Actualizado:** 2026-03-01
> **Como navegar:** Cada seccion tiene contexto de 2-3 lineas + enlace al tema completo

---

## Comandos de referencia rapida

| Accion | Comando |
|--------|---------|
| Arrancar backend | `cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000` |
| Arrancar frontend | `cd dashboard && npm run dev` |
| Cargar .env | `export $(grep -v '^#' .env \| xargs)` |
| Correr todos los tests | `pytest tests/ -v` |
| Pipeline un cliente | `python scripts/pipeline.py --cliente elena-navarro --ejercicio 2025 --inbox inbox_muestra --no-interactivo` |
| Ver logs API | `tail -f sfce/logs/api.log` |
| Backup manual | `/opt/apps/sfce/backup_total.sh` |
| SSH servidor | `ssh carli@65.108.60.69` |
| Reload Nginx | `docker exec nginx nginx -s reload` |
| Limpiar empresa FS | `python scripts/limpiar_empresa_fs.py --empresa N --dry-run` |
| Regenerar golden files | `UPDATE_GOLDEN=1 pytest tests/test_modelos_fiscales/test_golden.py` |

## Variables de entorno requeridas

| Variable | Servicio | Notas |
|----------|----------|-------|
| `FS_API_TOKEN` | FacturaScripts REST | iOXmrA1Bbn8RDWXLv91L |
| `MISTRAL_API_KEY` | OCR primario | — |
| `OPENAI_API_KEY` | OCR fallback | Cuota limitada en free tier |
| `GEMINI_API_KEY` | Triple consenso | 20 req/dia en free tier |
| `SFCE_JWT_SECRET` | Auth JWT | >=32 chars, OBLIGATORIO |
| `SFCE_CORS_ORIGINS` | CORS | Nunca "*" |
| `SFCE_DB_TYPE` | BD | "sqlite" dev / "postgresql" prod |
| `SFCE_FERNET_KEY` | Cifrado credenciales | Para correo/OAuth |

## Bugs conocidos activos

- `sfce.db`, `tmp/`, `.coverage` no estan en `.gitignore` (se colaron en commit)
- `uvicorn --reload` falla en Windows (WinError 6) — reiniciar manualmente tras cambios Python
- Tests E2E dashboard (Playwright) — 0 implementados
- VAPID push: endpoint `/api/notificaciones/suscribir` pendiente

## Deuda tecnica

- `scripts/core/` tiene divergencia funcional con `sfce/core/` — revisar en proxima sesion
- `migrar_sqlite_a_postgres.py` existe pero no ejecutado en prod
- Golden files modelos fiscales: regenerar con `UPDATE_GOLDEN=1 pytest` si cambia logica BOE
- Backups automaticos BD FacturaScripts — pendiente de configurar
- Merge PR `feat/frontend-pwa` pendiente

---

## Infraestructura

Servidor Hetzner 65.108.60.69. Docker para FacturaScripts (PHP/Apache + MariaDB 10.11) y SFCE (PostgreSQL 16). Nginx como proxy inverso. Firewall ufw + DOCKER-USER chain. NUNCA tocar el contenedor de FacturaScripts directamente.

→ [01 — Infraestructura](_temas/01-infraestructura.md)
→ [26 — Docker y Backups](_temas/26-infra-docker-backups.md)

## Arquitectura SFCE

Diagrama C4 completo del sistema: FastAPI + SQLAlchemy 2.0 + React 18. Capa de abstraccion dual-backend que escribe simultaneamente a FacturaScripts y BD local. 66+ rutas, 25 tablas, WebSocket tiempo real.

→ [02 — Arquitectura General SFCE](_temas/02-sfce-arquitectura.md)

## Pipeline 7 Fases

El pipeline orquesta el procesamiento completo de documentos desde `inbox/` hasta registro verificado. 7 fases secuenciales con quality gates: Intake → Pre-validacion → Clasificacion → Registro → Correccion → Verificacion → Sincronizacion.

→ [03 — Pipeline: Las 7 Fases](_temas/03-pipeline-fases.md)

## Gate 0: Preflight, Cola y Scoring

Punto de entrada pre-pipeline. Calcula SHA256, verifica duplicados, evalua trust level del remitente y decide si el documento pasa directo, va a cola o se rechaza. Critico para evitar procesar duplicados.

→ [04 — Gate 0: Preflight, Cola y Scoring](_temas/04-gate0-cola.md)

## OCR e IA: Sistema de Tiers

Tres tiers de OCR con escalada automatica: T0 Mistral (fast, barato) → T1 + GPT-4o (fallback) → T2 + Gemini Flash (triple consenso). Cache SHA256 por PDF — primera ejecucion paga, el resto gratis.

→ [05 — OCR e IA: Sistema de Tiers](_temas/05-ocr-ia-tiers.md)

## Motor de Reglas Contables

Jerarquia de 6 niveles: normativa > PGC > perfil_fiscal > negocio > cliente > aprendizaje. Cubre todas las formas juridicas, regimenes IVA y territorios (peninsula/Canarias/Ceuta). Este motor decide la cuenta contable de cada documento.

→ [06 — Motor de Reglas Contables](_temas/06-motor-reglas.md)

## Sistema de Reglas YAML

Las reglas contables se definen en archivos YAML versionados en `reglas/`. Patron de sobrescritura por nivel: el nivel cliente sobreescribe el nivel negocio, que sobreescribe el PGC. Editar estos YAMLs es la forma habitual de ajustar comportamiento sin tocar codigo.

→ [07 — Sistema de Reglas YAML](_temas/07-sistema-reglas-yaml.md)

## Motor de Aprendizaje, Scoring y Verificacion Fiscal

El motor aprende de cada resolucion exitosa y actualiza `reglas/aprendizaje.yaml` automaticamente. 6 estrategias de resolucion, scoring por confianza, verificacion fiscal post-registro. Integrado en registration.py con retry loop de 3 intentos.

→ [08 — Motor de Aprendizaje, Scoring y Verificacion Fiscal](_temas/08-aprendizaje-scoring.md)

## Motor de Testeo Autonomo

Sistema de auto-testeo que genera batches de documentos sinteticos, ejecuta el pipeline y evalua resultados contra golden files. Util para verificar que cambios en reglas no rompen casos existentes.

→ [09 — Motor de Testeo Autonomo](_temas/09-motor-testeo.md)

## Sistema de Cuarentena

Documentos con CIF desconocido o confianza baja se mueven fisicamente a `cuarentena/`. Flujo de revision manual, resolucion y re-ingesta. Recordar: restaurar con `mv cuarentena/*.pdf inbox_prueba/`.

→ [10 — Sistema de Cuarentena](_temas/10-cuarentena.md)

## API: Todos los Endpoints

66+ rutas organizadas por dominio: auth, empresas, directorio, pipeline, bancario, modelos fiscales, portal, RGPD, gate0, WebSocket. Incluye tabla completa de metodos, paths, auth requerida y descripcion.

→ [11 — API: Todos los Endpoints](_temas/11-api-endpoints.md)

## WebSockets y Tiempo Real

Canal `/ws/pipeline/{empresa_id}` para progreso en tiempo real. Reconexion automatica en frontend, mensajes JSON tipados, broadcast por empresa. Critico para el dashboard de pipeline en vivo.

→ [12 — WebSockets y Tiempo Real](_temas/12-websockets.md)

## Dashboard: Los 21 Modulos

PWA React 18 + Tailwind v4 + shadcn/ui. 21 modulos: PyG, balance, tesoreria, conciliacion bancaria, facturas, modelos fiscales, pipeline, portal cliente, RRHH, copiloto IA, etc. Feature-based, lazy loading, offline support.

→ [13 — Dashboard: Los 21 Modulos](_temas/13-dashboard-modulos.md)

## Copiloto IA

Chat contextual con acceso a datos de la empresa activa. Consulta saldos, facturas pendientes, estado fiscal. Usa GPT-4o con system prompt que incluye contexto de la empresa y ejercicio activo.

→ [14 — Copiloto IA](_temas/14-copiloto-ia.md)

## Modelos Fiscales

28 modelos BOE-compliant (303, 111, 130, 347, 390, 200, etc.). MotorBOE genera ficheros en formato texto para presentacion telematica. GeneradorPDF usa plantillas HTML como fallback cuando no hay formulario AEAT rellendable.

→ [15 — Modelos Fiscales](_temas/15-modelos-fiscales.md)

## Calendario Fiscal

Generacion automatica de vencimientos por forma juridica y regimen. Exportacion iCal (`.ics`) suscribible desde cualquier calendario. Endpoint publico en el portal cliente. Cubre autonomos y S.L.

→ [16 — Calendario Fiscal](_temas/16-calendario-fiscal.md)

## Base de Datos: Las 29 Tablas

Schema completo SQLAlchemy 2.0. Tablas por dominio: empresas, documentos, asientos/partidas, modelos fiscales, auth/users, audit log, cuarentena, conciliacion, cola procesamiento, tracking. Migraciones numeradas en `sfce/db/migraciones/`.

→ [17 — Base de Datos: Las 29 Tablas](_temas/17-base-de-datos.md)

## Activos Fijos, Operaciones Periodicas y Cierre de Ejercicio

Amortizaciones automaticas por tabla oficial, operaciones recurrentes (nominas, seguros, arrendamientos), proceso de cierre de ejercicio con apertura automatica del siguiente. Tablas: ActivoFijo, AsientoRecurrente.

→ [18 — Activos Fijos, Operaciones Periodicas y Cierre de Ejercicio](_temas/18-activos-periodicas-cierre.md)

## Modulo Bancario: Ingesta y Conciliacion

Parsers para Norma 43 TXT y CaixaBank XLS (auto-detect). Motor de conciliacion: match exacto + aproximado (1% tolerancia, 2 dias ventana). 44 tests contra archivo real TT191225.208.txt.

→ [19 — Modulo Bancario: Ingesta y Conciliacion](_temas/19-bancario.md)

## Modulo de Correo: Ingesta y Clasificacion

Conexion IMAP, ingesta de adjuntos PDF/XML, clasificacion automatica del remitente y tipo de documento. Integrado con el pipeline como canal de entrada alternativo al `inbox/` local.

→ [20 — Modulo de Correo: Ingesta y Clasificacion](_temas/20-correo.md)

## Certificados Digitales y Notificaciones AAPP

Integracion con CertiGestor para notificaciones de AEAT/TGSS. Webhook HMAC para recepcion de alertas. Gestion de certificados digitales por empresa. Tabla NotificacionAAPP en BD.

→ [21 — Certificados Digitales y Notificaciones AAPP](_temas/21-certificados-aapp.md)

## Seguridad: Auth, Rate Limiting, RGPD y Cifrado

JWT + 2FA TOTP + lockout (5 intentos, 30min). Rate limiting por IP/usuario (ventana fija, sin Redis). Export RGPD ZIP con token uso unico 24h. Fernet para cifrado de credenciales OAuth. Audit log completo.

→ [22 — Seguridad: Auth, Rate Limiting, RGPD y Cifrado](_temas/22-seguridad.md)

## Clientes y Configuracion

Estructura `config.yaml` por cliente: CIF, forma juridica, regimen IVA, proveedores frecuentes, subcuentas personalizadas, ejercicio activo, codejercicio FS. `sfce/core/config.py` carga y valida el YAML. Multiempresa via `config_desde_bd.py`.

→ [23 — Clientes y Configuracion](_temas/23-clientes.md)

## FacturaScripts: API REST e Integracion

Referencia completa de la API FS: endpoints create*/GET/PUT, gotchas criticos (form-encoded, no JSON; lineas como JSON string; filtros no funcionan; asientos invertidos; orden cronologico FC). Imprescindible antes de tocar cualquier script de integracion.

→ [24 — FacturaScripts: API REST e Integracion](_temas/24-facturascripts.md)

## Generador de Datos de Prueba

Motor sintetico: 43 familias de documentos, 2343 documentos generables, parametrizable por empresa/ejercicio/tipo/volumen. Usado para E2E del pipeline y para tests de regresion de modelos fiscales.

→ [25 — Generador de Datos de Prueba](_temas/25-generador-datos.md)

## Planes y Decisiones Arquitectonicas

Historial de decisiones de diseno: SFCE v2, dashboard rewrite, evolucion arquitectura, PROMETH-AI fases 0-6. Imprescindible para entender por que el codigo esta como esta y que paths se descartaron.

→ [27 — Planes y Decisiones Arquitectonicas](_temas/27-planes-y-decisiones.md)

## Roadmap y Estado del Sistema

Estado actual de cada componente, proximos pasos priorizados, tareas pendientes de baja prioridad. Referencia para saber que esta completado vs en vuelo vs pendiente.

→ [28 — Roadmap y Estado del Sistema](_temas/28-roadmap.md)
