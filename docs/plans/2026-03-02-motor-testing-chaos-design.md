# Motor de Testing de Caos Documental SFCE — Design Doc

**Fecha:** 2026-03-02
**Estado:** Aprobado
**Sesión:** 20

---

## 1. Problema

El Motor de Escenarios de Campo actual (`scripts/motor_campo/`) tiene 39 escenarios construidos pero nunca ejecutados, con 4 bugs críticos que lo hacen inservible en producción:

1. **Cleanup no funciona**: `Executor` nunca llama `cleanup.registrar_factura()` → cada ejecución deja basura en FacturaScripts
2. **`bypass_ocr=True` en todos los escenarios**: no se testea Mistral/GPT/Gemini ni las 7 fases reales del pipeline
3. **`AutoFix` sin contexto**: necesita `idasiento + partidas` en el resultado, pero `ejecutar()` no los devuelve
4. **`Validator` no valida IVA**: el campo `iva_correcto=True` existe pero nunca se chequea

Además, el motor actual no cubre los canales reales por los que entran documentos: email IMAP, subida desde app móvil (portal), ni los 15 tipos de error que el generador de datos ya sabe inyectar.

---

## 2. Objetivo

Construir un **Motor de Testing de Caos Documental** que:

- Simule los flujos reales de entrada de documentos (email, móvil, directo)
- Envíe documentos problemáticos conocidos (blank, borroso, duplicado, CIF inválido, total desencuadrado) y verifique que el sistema los clasifica correctamente
- Se integre en el stack SFCE como background worker
- Alimente una página SFCE Health en el dashboard con semáforo en tiempo real
- Se ejecute automáticamente post-deploy (smoke) y semanalmente (regression)

---

## 3. Arquitectura general

```
PIRÁMIDE DE TESTING

Capa 2 — Playwright E2E (flujos UI)
  Flujos: crear gestoría, invitar gestor, portal upload, login, onboarding
  Frecuencia: semanal (regression) o manual
  Runner: headless Chromium

Capa 1 — Motor de Caos Documental (live API + workers)
  Canales: Email IMAP, Portal API (móvil), HTTP directo
  Documentos: biblioteca precompilada (facturas limpias + E01-E15 + edge cases)
  Frecuencia: smoke post-deploy + vigilancia 5min + regression semanal

Capa 0 — pytest (offline)
  2274 tests, sin APIs reales, CI pre-deploy
  Resultados → webhook → testing_sesiones (PostgreSQL)

Todos los resultados → PostgreSQL (sfce_prod, esquema testing_*)
Dashboard /testing → semáforo de las 3 capas
```

---

## 4. Biblioteca de documentos

### 4.1 Estructura

```
scripts/motor_campo/biblioteca/
  manifesto.json                   ← fuente de verdad: metadata + resultado esperado
  generar_biblioteca.py            ← script para (re)generar los PDFs

  facturas_limpias/
    fc_pyme_iva21.pdf              familia pyme_clasica, IVA 21%
    fc_corp_usd.pdf                corporativo, divisa USD, tasaconv 1.08
    fc_intracomunitaria.pdf        cliente UE, IVA 0%, ISP
    fc_multilinea.pdf              3 líneas, IVA mixto 21/10/0
    fv_espanola.pdf                proveedor español, IVA 21%
    fv_intracomunitaria.pdf        proveedor alemán DE*, autorepercusión 472/477
    fv_suplidos.pdf                agencia aduanas, reclasificación 600→4709
    fv_autonomo.pdf                autónomo español, retención 15%
    nom_a3nom.pdf                  nómina A3nom, bruto 2000, IRPF 15%
    nom_hosteleria.pdf             nómina hostelería, sector específico
    rec_seguro.pdf                 recibo seguro, IVA exento
    rec_suministro.pdf             Endesa, IVA 21%, cta 6280

  tickets_fotos/
    ticket_tpv.jpg                 foto JPEG desde móvil, bien enfocada
    ticket_gasolina.jpg            foto JPEG, ángulo ladeado
    ticket_supermercado.pdf        ticket simplificado

  caos_documental/
    E01_cif_invalido.pdf           dígito control CIF corrupto → cuarentena
    E02_iva_mal_calculado.pdf      IVA ≠ base × tipo → cuarentena
    E03_importe_negativo.pdf       base < 0 sin ser NC → cuarentena
    E04a_original.pdf              primera copia → procesado
    E04b_duplicado.pdf             SHA256 idéntico → 409 duplicado
    E05_fecha_fuera_rango.pdf      año anterior al ejercicio → cuarentena
    E07_total_desencuadrado.pdf    total ≠ base + IVA → cuarentena
    E08_proveedor_desconocido.pdf  CIF no en config empresa_id=3 → cuarentena
    blanco.pdf                     PDF sin contenido → cuarentena
    ilegible.jpg                   imagen 20×20 píxeles → cuarentena
    formato_invalido.pdf           texto ASCII renombrado como PDF → cuarentena

  bancario/
    c43_normal.txt                 Norma 43 AEB estándar (2 movimientos)
    c43_caixabank.txt              variante CaixaBank TT191225
    c43_saldo_negativo.txt         saldo < 0 → procesado (válido)
    c43_vacio.txt                  sin movimientos → procesado (0 asientos)
```

### 4.2 manifesto.json

Cada entrada define el resultado que el validator debe verificar:

```json
{
  "fc_pyme_iva21.pdf": {
    "tipo_doc_esperado": "FC",
    "estado_esperado": "procesado",
    "asiento_cuadrado": true,
    "iva_correcto": true,
    "codimpuesto_esperado": "IVA21",
    "tiene_asiento": true,
    "canales": ["email", "portal", "directo"],
    "max_duracion_s": 600
  },
  "E01_cif_invalido.pdf": {
    "tipo_doc_esperado": "FV",
    "estado_esperado": "cuarentena",
    "razon_cuarentena_esperada": "check_1_cif_invalido",
    "tiene_asiento": false,
    "canales": ["email", "portal", "directo"],
    "max_duracion_s": 600
  },
  "E04b_duplicado.pdf": {
    "tipo_doc_esperado": "FV",
    "estado_esperado": "duplicado",
    "http_status_esperado": 409,
    "tiene_asiento": false,
    "canales": ["directo"],
    "prerequisito": "E04a_original.pdf",
    "max_duracion_s": 30
  },
  "blanco.pdf": {
    "tipo_doc_esperado": null,
    "estado_esperado": "cuarentena",
    "razon_cuarentena_esperada": "pdf_sin_contenido",
    "tiene_asiento": false,
    "canales": ["email", "portal", "directo"],
    "max_duracion_s": 120
  }
}
```

### 4.3 Script de generación

`scripts/motor_campo/biblioteca/generar_biblioteca.py`:
- Carga config de empresa_id=3
- Llama `tests/datos_prueba/generador/` para cada categoría
- Inyecta errores E01-E15 con `gen_errores.py`
- Genera `manifesto.json` automáticamente
- Ejecutar manualmente cuando la biblioteca necesite actualizarse
- Los PDFs generados se commitean (el .gitignore solo excluye `clientes/**/*.pdf`)

---

## 5. Executors

Todos implementan la misma interfaz:

```python
class ExecutorBase:
    def ejecutar(self, variante: VarianteEjecucion) -> ResultadoEjecucion:
        ...

@dataclass
class ResultadoEjecucion:
    escenario_id: str
    variante_id: str
    canal: str                    # "email" | "portal" | "bancario" | "http" | "playwright"
    resultado: str                # "ok" | "bug_pendiente" | "timeout" | "error_sistema"
    estado_doc_final: str | None  # "procesado" | "cuarentena" | "duplicado" | None
    tipo_doc_detectado: str | None
    idasiento: int | None
    asiento_cuadrado: bool | None
    duracion_ms: int
    detalles: dict                # contexto adicional para debug
```

### 5.1 ExecutorHTTP (mejora del actual)

Llama directamente a la API SFCE con `bypass_ocr=True`. Sin espera de workers.
Retorna `idasiento` y `partidas` en `detalles` para que AutoFix pueda operar.
Registra `idfactura` en cleanup tras cada creación.

**Úsado en:** SMOKE, VIGILANCIA, escenarios de Gate0/seguridad/dashboard en REGRESSION.

### 5.2 ExecutorEmail (nuevo)

```
Prerequisito: cuenta IMAP de empresa_id=3 configurada en BD (tabla CuentaCorreo)
Prerequisito: credenciales SMTP en env vars MOTOR_SMTP_HOST/PORT/USER/PASSWORD

Flujo:
1. smtplib: enviar email con adjunto desde biblioteca al buzón IMAP empresa_id=3
   - Asunto: "SFCE_TEST_{escenario_id}_{uuid4()[:8]}"  ← uuid para evitar duplicados entre runs
   - From: MOTOR_SMTP_USER → To: cuenta_imap_empresa3@zoho.com
2. Poll /api/gate0/cola?empresa_id=3&nombre_archivo_contains={uuid}
   cada 5s, timeout 90s ← esperar que daemon_correo (60s) descargue
3. Obtener doc_id de la cola
4. Poll /api/documentos/{doc_id}/estado cada 5s, timeout 600s
   hasta estado ∉ {PENDIENTE, PROCESANDO}
5. GET /api/documentos/{doc_id} → estado_final, idasiento, tipo_doc
6. Limpiar: borrar doc de BD + archivo del disco de empresa_id=3
```

### 5.3 ExecutorPortal (nuevo)

Simula la app móvil haciendo upload vía portal API.

```
Prerequisito: JWT de usuario cliente de empresa_id=3 (ci_cliente@sfce.local)

Flujo:
1. POST /api/portal/3/documentos/subir
   multipart/form-data: archivo + tipo_doc (si se conoce) + nombre único con uuid
2. Obtener doc_id de la respuesta
3. Poll /api/documentos/{doc_id}/estado cada 5s, timeout 600s
4. GET /api/documentos/{doc_id} → estado_final, idasiento, tipo_doc
5. Limpiar: borrar doc de BD + archivo del disco
```

### 5.4 ExecutorBancario (mejora del actual)

```
1. POST /api/bancario/3/ingestar (archivo .txt Norma 43)
2. Respuesta síncrona: movimientos_creados, saldo_inicial, saldo_final
3. Verificar contra valores esperados del manifesto
4. Limpiar: borrar movimientos bancarios de empresa_id=3 de BD
```

### 5.5 ExecutorPlaywright (nuevo)

Ejecuta flujos UI con Playwright headless. Refactoring de los scripts existentes en `scripts/test_*.py`:

```python
async def ejecutar_playwright(escenario_id: str, headless: bool = True) -> ResultadoEjecucion:
    # Cada flujo retorna ResultadoEjecucion en vez de imprimir
    # Capturas en /tmp/playwright_{escenario_id}_{timestamp}/
    ...
```

Los scripts existentes se adaptan añadiendo una función `ejecutar()` que retorna el resultado y la función `main()` actual llama a `ejecutar()` para CLI.

---

## 6. Validador mejorado

```python
def validar(resultado: ResultadoEjecucion, esperado_manifesto: dict) -> list[dict]:
    errores = []

    # 1. Estado final del documento
    if resultado.estado_doc_final != esperado_manifesto["estado_esperado"]:
        errores.append({"tipo": "estado_incorrecto", ...})

    # 2. Tipo de documento detectado (si aplica)
    if esperado_manifesto.get("tipo_doc_esperado"):
        if resultado.tipo_doc_detectado != esperado_manifesto["tipo_doc_esperado"]:
            errores.append({"tipo": "tipo_doc_incorrecto", ...})

    # 3. Cuadre contable (si debe tener asiento)
    if esperado_manifesto.get("asiento_cuadrado") and resultado.idasiento:
        partidas = GET /api/asientos/{resultado.idasiento}
        debe = sum(p.debe for p in partidas)
        haber = sum(p.haber for p in partidas)
        if abs(debe - haber) > 0.02:
            errores.append({"tipo": "cuadre", ...})

    # 4. IVA correcto (si aplica)
    if esperado_manifesto.get("iva_correcto") and resultado.idasiento:
        codimpuesto_real = _extraer_codimpuesto_asiento(resultado.idasiento)
        if codimpuesto_real != esperado_manifesto.get("codimpuesto_esperado"):
            errores.append({"tipo": "iva_incorrecto", ...})

    # 5. Razón de cuarentena (para E01-E15)
    if esperado_manifesto.get("razon_cuarentena_esperada"):
        razon_real = GET /api/documentos/{doc_id}/razon_cuarentena
        if razon_real != esperado_manifesto["razon_cuarentena_esperada"]:
            errores.append({"tipo": "cuarentena_razon_incorrecta", ...})

    # 6. Tiempo de procesado
    if resultado.duracion_ms > esperado_manifesto["max_duracion_s"] * 1000:
        errores.append({"tipo": "timeout_excedido", ...})

    return errores
```

---

## 7. Cleanup completo

El cleanup tiene 3 capas que se ejecutan SIEMPRE después de cada escenario (con o sin error):

```python
class CleanupCompleto:
    def limpiar(self, empresa_id: int, contexto: dict):
        self._limpiar_facturascripts(contexto)  # 1. FS API
        self._limpiar_bd(empresa_id)             # 2. PostgreSQL (12 tablas)
        self._limpiar_disco(empresa_id)          # 3. Archivos en disco

    def _limpiar_facturascripts(self, ctx):
        for tipo, idf in ctx.get("facturas_creadas", []):
            endpoint = "facturaclientes" if tipo == "FC" else "facturaproveedores"
            DELETE /api/3/{endpoint}/{idf}
        for ida in ctx.get("asientos_creados", []):
            DELETE /api/3/asientos/{ida}

    def _limpiar_bd(self, empresa_id):
        # Orden correcto para FK constraints
        DELETE cola_procesamiento WHERE empresa_id = {id}
        DELETE documentos WHERE empresa_id = {id}
        DELETE asientos WHERE empresa_id = {id}  # cascade → partidas
        DELETE facturas WHERE empresa_id = {id}
        DELETE pagos WHERE empresa_id = {id}
        DELETE movimientos_bancarios WHERE cuenta_bancaria_id IN
            (SELECT id FROM cuentas_bancarias WHERE empresa_id = {id})
        DELETE notificaciones_usuario WHERE empresa_id = {id}
        DELETE supplier_rules WHERE empresa_id = {id}
        DELETE archivos_ingestados WHERE empresa_id = {id}
        DELETE centros_coste WHERE empresa_id = {id}
        # NO borrar: empresa, config, testing_*, cuentas_correo

    def _limpiar_disco(self, empresa_id):
        rm -rf docs/uploads/{empresa_id}/
        rm -rf clientes/empresa-prueba/inbox/*
        rm -rf clientes/empresa-prueba/procesado/*
```

**CRÍTICO:** Las tablas `testing_sesiones`, `testing_ejecuciones`, `testing_bugs` **nunca se limpian** — son el histórico del motor.

---

## 8. Base de datos — migración 015_testing

3 tablas nuevas en `sfce_prod`:

```sql
testing_sesiones
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid()
  modo         VARCHAR(20) NOT NULL  -- smoke | regression | vigilancia | manual
  trigger      VARCHAR(20) NOT NULL  -- ci | schedule | api | manual
  estado       VARCHAR(20) NOT NULL  -- en_curso | completado | fallido | abortado
  inicio       TIMESTAMP WITH TIME ZONE
  fin          TIMESTAMP WITH TIME ZONE
  total_ok     INTEGER DEFAULT 0
  total_bugs   INTEGER DEFAULT 0
  total_arreglados INTEGER DEFAULT 0
  total_timeout INTEGER DEFAULT 0
  commit_sha   VARCHAR(40)           -- versión testeada
  notas        TEXT

testing_ejecuciones
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid()
  sesion_id    UUID REFERENCES testing_sesiones(id) ON DELETE CASCADE
  escenario_id VARCHAR(100) NOT NULL
  variante_id  VARCHAR(100) NOT NULL
  canal        VARCHAR(20) NOT NULL   -- email | portal | bancario | http | playwright
  resultado    VARCHAR(30) NOT NULL   -- ok | bug_pendiente | bug_arreglado | timeout | error_sistema
  estado_doc_final VARCHAR(30)        -- procesado | cuarentena | duplicado | null
  tipo_doc_detectado VARCHAR(10)
  idasiento    INTEGER
  asiento_cuadrado BOOLEAN
  duracion_ms  INTEGER
  timestamp    TIMESTAMP WITH TIME ZONE DEFAULT NOW()

testing_bugs
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid()
  sesion_id    UUID REFERENCES testing_sesiones(id) ON DELETE CASCADE
  escenario_id VARCHAR(100) NOT NULL
  variante_id  VARCHAR(100)
  tipo         VARCHAR(50) NOT NULL
  descripcion  TEXT NOT NULL
  stack_trace  TEXT
  fix_intentado TEXT
  fix_exitoso  BOOLEAN DEFAULT FALSE
  timestamp    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
```

El `BugRegistry` SQLite (`data/motor_campo.db`) se elimina. El motor escribe directamente en PostgreSQL vía SQLAlchemy.

---

## 9. Worker Testing integrado en SFCE

### 9.1 Modos y escenarios

| Modo | Executor | Timeout | Escenarios | Frecuencia | Objetivo |
|---|---|---|---|---|---|
| **SMOKE** | HTTP (bypass_ocr) | 5s/esc | 12 críticos | post-deploy CI | < 90s total |
| **VIGILANCIA** | HTTP (bypass_ocr) | 5s/esc | 5 canary | cada 5 min | heartbeat Uptime Kuma |
| **REGRESSION** | Email+Portal+HTTP | 600s/esc | todos + variantes + E01-E15 | lunes 03:00 | 15-25 min |
| **MANUAL** | configurable | configurable | libre | desde dashboard | debug |

**12 escenarios SMOKE** (HTTP, bypass_ocr):
```
fc_basica, fv_basica, nc_cliente,
gate0_trust_maxima, gate0_trust_baja, gate0_duplicado,
api_login, api_login_incorrecto, api_sin_token,
dash_pyg, dash_balance, ban_c43_estandar
```

**5 escenarios VIGILANCIA** (canary):
```
fc_basica, api_login, dash_pyg, gate0_trust_maxima, ban_c43_estandar
```

### 9.2 Integración en lifespan

```python
# sfce/api/app.py — lifespan()
from sfce.core.worker_testing import loop_worker_testing

testing_task = asyncio.create_task(loop_worker_testing(sesion_factory=sesion_factory))
app.state.worker_testing_task = testing_task

# En shutdown:
testing_task.cancel()
```

### 9.3 Pre-check antes de cada sesión

Antes de ejecutar cualquier sesión, el worker verifica:

```python
async def _pre_check_sistema() -> bool:
    health = GET /api/health
    if health["status"] != "ok":
        return False
    # Verificar workers activos en app.state
    workers_ok = all([
        app.state.worker_ocr_activo,
        app.state.worker_pipeline_activo,
        app.state.worker_correo_activo,
    ])
    return workers_ok
```

Si pre-check falla → sesión en estado `abortado`, no ejecuta escenarios.

---

## 10. Endpoint health extendido

```python
# GET /api/health — sin autenticación

{
  "status": "ok" | "degraded",
  "version": "2.0.0",
  "db": "ok" | "error",
  "workers": {
    "ocr": "ok" | "inactivo",
    "pipeline": "ok" | "inactivo",
    "correo": "ok" | "inactivo",
    "testing": "ok" | "inactivo"
  },
  "ultima_sesion_testing": {
    "modo": "vigilancia",
    "estado": "completado",
    "bugs": 0,
    "hace_segundos": 287
  },
  "timestamp": "2026-03-02T14:35:42Z"
}
```

---

## 11. API endpoints testing

```
POST /api/testing/ejecutar
  Body: {modo, grupo?, escenario_id?, canal?}
  Auth: requiere_rol("superadmin")
  Returns: {sesion_id, estado: "en_curso"}

GET /api/testing/sesiones
  Query: ?limit=20&offset=0&modo=smoke
  Returns: [{sesion_id, modo, trigger, estado, total_ok, total_bugs, inicio, fin}]

GET /api/testing/sesiones/{sesion_id}
  Returns: {sesion, ejecuciones: [...], bugs: [...]}

GET /api/testing/semaforo
  Returns: estado actual de las 3 capas (para el dashboard)
  {
    "pytest":    {ok: 2274, bugs: 0, hace_h: 2, estado: "verde"},
    "motor":     {ok: 37, bugs: 2, hace_min: 8, estado: "amarillo"},
    "playwright":{ok: 12, bugs: 0, hace_dias: 3, estado: "verde"}
  }
```

---

## 12. Dashboard — página SFCE Health

Nueva ruta `/testing` con componente `TestingPage`:

```
┌──────────────────────────────────────────────────────────────────┐
│  SFCE Health                              [Ejecutar ahora ▼]     │
├──────────────────┬──────────────────┬──────────────────────────┤
│  pytest          │  Motor Campo     │  Playwright E2E          │
│  ● Verde         │  ● Amarillo      │  ● Verde                 │
│  2274 tests ✓    │  37/39 OK        │  12/12 ✓                 │
│  0 fallos        │  2 bugs activos  │  0 fallos                │
│  hace 2h (CI)    │  hace 8min       │  hace 3 días             │
└──────────────────┴──────────────────┴──────────────────────────┘

  Bugs activos (2)                    Tendencia últimas 10 sesiones
  ● fv_intracomunitaria: ISP no gen   [sparkline: ok/bugs por sesión]
  ● E02_iva_mal_calculado: no cuar
  [Ver detalle]  [Ignorar]

  Últimas sesiones
  ┌─────────────────────────────────────────────────────────────┐
  │ regression #47 — 2026-03-02 03:00 — 18m 32s — 37 OK, 2 bugs│
  │ smoke #312    — 2026-03-02 14:00 — 1m 12s  — 12 OK, 0 bugs │
  │ vigilancia #8844 — 2026-03-02 13:55 — 12s  — 5 OK, 0 bugs  │
  └─────────────────────────────────────────────────────────────┘
```

**Implementación**: React + TanStack Query (poll cada 10s durante sesión activa, cada 60s en reposo). Sin WebSocket en MVP — polling es suficiente para esta frecuencia.

---

## 13. CI/CD — 5º job: smoke post-deploy

```yaml
# .github/workflows/deploy.yml
smoke-test:
  needs: deploy
  runs-on: ubuntu-latest
  steps:
    - name: Esperar API ready
      run: |
        for i in {1..12}; do
          STATUS=$(curl -sf https://api.prometh-ai.es/api/health | jq -r '.status' 2>/dev/null)
          [ "$STATUS" = "ok" ] && echo "API ready" && break
          echo "Intento $i/12 — esperando..."
          sleep 5
        done

    - name: Lanzar smoke
      id: smoke
      run: |
        SESSION_ID=$(curl -sf -X POST \
          "https://api.prometh-ai.es/api/testing/ejecutar" \
          -H "Authorization: Bearer ${{ secrets.SFCE_CI_TOKEN }}" \
          -H "Content-Type: application/json" \
          -d '{"modo":"smoke"}' \
          | jq -r '.sesion_id')
        echo "sesion_id=$SESSION_ID" >> $GITHUB_OUTPUT

    - name: Esperar resultado (max 3 min)
      run: |
        for i in {1..36}; do
          RESULT=$(curl -sf \
            "https://api.prometh-ai.es/api/testing/sesiones/${{ steps.smoke.outputs.sesion_id }}" \
            -H "Authorization: Bearer ${{ secrets.SFCE_CI_TOKEN }}")
          ESTADO=$(echo $RESULT | jq -r '.sesion.estado')
          BUGS=$(echo $RESULT | jq -r '.sesion.total_bugs')
          echo "[$i/36] estado=$ESTADO bugs=$BUGS"
          if [ "$ESTADO" = "completado" ]; then
            [ "$BUGS" = "0" ] && echo "SMOKE OK" && exit 0
            echo "SMOKE FAILED: $BUGS bugs detectados"
            exit 1
          fi
          sleep 5
        done
        echo "SMOKE TIMEOUT: sesión no completó en 3 minutos"
        exit 1
```

**Secret nuevo necesario**: `SFCE_CI_TOKEN` — token JWT de usuario `ci@sfce.local` con rol `superadmin`. Se añade a GitHub Secrets y al `.env` del servidor.

---

## 14. Uptime Kuma — 3 heartbeats nuevos

El worker_testing hace `curl` al endpoint heartbeat de Uptime Kuma al completar cada sesión:

```python
# En worker_testing.py, al completar sesión
if modo == "vigilancia" and bugs_pendientes == 0:
    requests.get(f"{UPTIME_KUMA_URL}/api/push/{KUMA_SLUG_VIGILANCIA}")
elif modo == "smoke":
    requests.get(f"{UPTIME_KUMA_URL}/api/push/{KUMA_SLUG_SMOKE}")
elif modo == "regression":
    requests.get(f"{UPTIME_KUMA_URL}/api/push/{KUMA_SLUG_REGRESSION}")
```

Los slugs se configuran como env vars: `KUMA_SLUG_SMOKE`, `KUMA_SLUG_VIGILANCIA`, `KUMA_SLUG_REGRESSION`.

Si el heartbeat no llega en el tiempo esperado → Uptime Kuma marca monitor en rojo → alerta.

---

## 15. Usuarios CI/CD necesarios

| Usuario | Email | Rol | Propósito |
|---|---|---|---|
| CI smoke | `ci@sfce.local` | superadmin | Trigger testing desde GitHub Actions |
| Portal test | `ci_cliente@sfce.local` | cliente empresa_id=3 | ExecutorPortal autenticado |

Ambos se crean via seed en `sfce/db/seeds.py` o vía `crear_admin_por_defecto()` extendido. Sus tokens se almacenan en GitHub Secrets y `.env` del servidor.

---

## 16. Archivos nuevos / modificados

### Nuevos
```
scripts/motor_campo/biblioteca/          ← biblioteca precompilada
scripts/motor_campo/biblioteca/generar_biblioteca.py
scripts/motor_campo/biblioteca/manifesto.json
scripts/motor_campo/executor_email.py
scripts/motor_campo/executor_portal.py
scripts/motor_campo/executor_playwright.py
scripts/motor_campo/cleanup_completo.py  ← reemplaza cleanup.py
sfce/core/worker_testing.py
sfce/db/migraciones/015_testing.py
sfce/db/modelos_testing.py
sfce/api/rutas/testing.py
dashboard/src/features/testing/testing-page.tsx
dashboard/src/features/testing/semaforo-card.tsx
dashboard/src/features/testing/sesion-detail-page.tsx
```

### Modificados
```
scripts/motor_campo/executor.py          ← retorna idfactura/idasiento, registra en cleanup
scripts/motor_campo/validator.py         ← valida IVA, cuarentena_razon, duracion
scripts/motor_campo/autofix.py           ← usa contexto correcto del resultado
scripts/motor_campo/bug_registry.py      ← reemplazado por modelos_testing.py
scripts/motor_campo/orquestador.py       ← usa cleanup_completo, modelos_testing
scripts/motor_campo/catalogo/fc.py       ← documentos desde biblioteca
scripts/test_crear_gestoria.py           ← añade función ejecutar() que retorna resultado
scripts/test_nivel1_invitar_gestor.py    ← idem
sfce/api/app.py                          ← añade worker_testing al lifespan
sfce/api/rutas/health.py                 ← añade estado workers
.github/workflows/deploy.yml             ← añade job smoke-test
```

---

## 17. Dependencias

```
# Nuevas en requirements.txt
# smtplib: stdlib Python (ya disponible)
# playwright: ya existe para scripts E2E
# uuid: stdlib Python

# Nuevas env vars en .env
MOTOR_SMTP_HOST=smtp.zoho.eu
MOTOR_SMTP_PORT=587
MOTOR_SMTP_USER=testing@[dominio-zoho-configurado]
MOTOR_SMTP_PASSWORD=[contraseña-zoho]
MOTOR_EMAIL_DESTINO=[buzón IMAP empresa_id=3]

KUMA_SLUG_SMOKE=[heartbeat-slug-uptime-kuma]
KUMA_SLUG_VIGILANCIA=[heartbeat-slug-uptime-kuma]
KUMA_SLUG_REGRESSION=[heartbeat-slug-uptime-kuma]

SFCE_CI_TOKEN=[jwt-ci@sfce.local]
```

---

## 18. Orden de implementación recomendado

**Fase 1 — Fundamentos** (sin esto nada funciona):
1. Fix cleanup_completo.py (3 capas: FS + BD + disco)
2. Fix executor.py (retorna idfactura/idasiento, llama cleanup)
3. Migración 015_testing.py + modelos_testing.py
4. Fix validator.py (IVA, cuarentena_razon, duracion)

**Fase 2 — Biblioteca y executor mejorado**:
5. generar_biblioteca.py + manifesto.json
6. ExecutorHTTP mejorado con autofix correcto
7. Worker Testing (solo modo SMOKE y VIGILANCIA con HTTP)
8. API /testing + health extendido

**Fase 3 — Canales reales**:
9. ExecutorPortal (usuario ci_cliente + portal API)
10. ExecutorEmail (SMTP + poll IMAP worker)
11. ExecutorBancario mejorado (casos edge C43)

**Fase 4 — Dashboard y CI/CD**:
12. Dashboard /testing (semáforo + sesiones)
13. Job smoke en deploy.yml + SFCE_CI_TOKEN
14. Uptime Kuma heartbeats (3 monitores)

**Fase 5 — Playwright y regression completo**:
15. Refactoring scripts Playwright (añadir ejecutar())
16. ExecutorPlaywright
17. Regression mode completo con E01-E15

---

## 19. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Cleanup falla → basura acumulada en FS | Alto | Cleanup ejecuta siempre (try/finally), alertar si falla pero no abortar |
| Zoho SMTP/IMAP no configurado cuando se ejecuta regression | Medio | ExecutorEmail hace pre-check de conexión SMTP antes de enviar |
| Rate limit OCR (Gemini 20 req/día) durante regression | Medio | Regression usa solo Tier 0 (Mistral) si Gemini está agotado |
| Documento de testing ruteado a empresa real | Alto | Asunto email incluye prefijo "SFCE_TEST_" + uuid, el daemon_correo filtra por cuenta IMAP dedicada empresa_id=3 |
| Sesión regression bloquea workers durante 25min | Bajo | Worker_testing es independiente; solo compite por rate limit OCR, no por BD |
| smoke-test en CI falla por flakiness (no por bug real) | Medio | 2 reintentos antes de marcar fallo; timeout 3 min da margen |
