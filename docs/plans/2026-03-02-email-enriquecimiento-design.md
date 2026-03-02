# Design: Sistema Email Completo — Enriquecimiento + Grietas
**Fecha**: 2026-03-02
**Sesión**: 35
**Prioridad**: Alta — el sistema de correo no es operable en producción sin estos cambios

---

## Contexto

El sistema de correo está construido pero tiene 13 grietas que impiden su uso real en producción (ver `2026-03-02-email-grietas.md`). Además, el flujo de entrada real —gestoría reenvía facturas de clientes con instrucciones contables en el cuerpo del email— no está soportado. Este diseño cubre ambos problemas de forma integrada.

**Arquitectura confirmada**: un buzón por gestoría bajo `@prometh-ai.es` (Google Workspace). Los clientes también pueden enviar directamente con instrucciones en el cuerpo.

---

## Prerequisitos (configuración Google Workspace)

### Acciones manuales (usuario)
1. **App Password**: `myaccount.google.com` → Seguridad → Contraseñas de aplicaciones → "SFCE-IMAP"
2. **Alias `documentacion@prometh-ai.es`**: `admin.google.com` → Usuarios → admin → Añadir alias

### Cambios de código
- `.env.example`: sustituir variables Zoho por `smtp.gmail.com:587` / `imap.gmail.com:993`
- `onboarding_email.py`: `_CUENTA_CATCHALL_SERVIDOR = "imap.gmail.com"`

---

## Flujos de entrada soportados

```
CASO A — Cliente directo (sin instrucciones)
  cliente@empresa.es → gestoriaX@prometh-ai.es
  1 adjunto, sin texto de instrucciones
  → whitelist identifica empresa
  → ColaProcesamiento (sin enriquecimiento)

CASO B — Gestoría reenvía + instrucciones globales
  gestor → gestoriaX@prometh-ai.es
  body: "gasolina Fulano, 100% IVA furgoneta"
  adjuntos: [gasolina.pdf]
  → ExtractorEnriquecimiento → aplica a todos los adjuntos

CASO C — Gestoría reenvía mezcla multi-cliente
  gestor → gestoriaX@prometh-ai.es
  body: "gasolina Fulano 100% IVA / luz Mengano normal"
  adjuntos: [gasolina.pdf, luz.pdf]
  → ExtractorEnriquecimiento → une por filename → ColaProcesamiento × 2

CASO D — Cliente directo con instrucciones
  empresario@fulanosl.es → gestoriaX@prometh-ai.es
  body: "adjunto mi factura de gasolina, el coche es de uso exclusivo del negocio"
  → ExtractorEnriquecimiento lo procesa igual que el gestor

CASO E — Email adjuntado como .eml
  gestor reenvía adjuntando el email del cliente como .eml
  extractor_adjuntos.py extrae el PDF del interior del .eml

CASO F — Catch-all con slug
  docs+fulanosl+fv@prometh-ai.es → docs@prometh-ai.es
  → slug resuelve empresa
  → ExtractorEnriquecimiento procesa instrucciones opcionales del cuerpo
```

---

## Componente nuevo: `ExtractorEnriquecimiento`

**Archivo**: `sfce/conectores/correo/extractor_enriquecimiento.py`

### Pre-filtro (evita coste GPT)
Antes de llamar a GPT, verificar si vale la pena:
```python
KEYWORDS_CONTABLES = [
    "iva", "irpf", "gasto", "furgoneta", "mixto", "deducible",
    "reparto", "%", "cuenta", "retención", "intracomunitario",
    "importación", "ejercicio", "tipo", "subcuenta", "representación"
]

def _merece_extraccion(texto_limpio: str) -> bool:
    texto = texto_limpio.lower()
    return any(kw in texto for kw in KEYWORDS_CONTABLES) and len(texto.split()) >= 5
```
Si no hay keywords → retorna lista vacía sin llamar a GPT.

### Parser de reenvíos
Antes de enviar a GPT, extraer solo el texto nuevo del gestor:
```python
SEPARADORES_REENVIO = [
    "---------- forwarded message",
    "-------- mensaje reenviado",
    "de:", "from:", "-----original message-----",
    "begin forwarded message",
]

def _extraer_texto_nuevo(cuerpo_texto: str) -> str:
    """Retorna solo el texto por encima del bloque reenviado."""
    lower = cuerpo_texto.lower()
    for sep in SEPARADORES_REENVIO:
        idx = lower.find(sep)
        if idx > 0:
            return cuerpo_texto[:idx].strip()
    return cuerpo_texto.strip()
```

### Schema de salida (confianza por campo)
```python
@dataclass
class CampoEnriquecido:
    valor: Any
    confianza: float  # 0.0 – 1.0

@dataclass
class EnriquecimientoDocumento:
    adjunto: str                              # filename o "GLOBAL" (aplica a todos)
    cliente_slug: CampoEnriquecido | None     # empresa destino inferida
    iva_deducible_pct: CampoEnriquecido | None   # 0-100
    motivo_iva: CampoEnriquecido | None
    categoria_gasto: CampoEnriquecido | None  # slug MCF
    subcuenta_contable: CampoEnriquecido | None
    reparto_empresas: CampoEnriquecido | None # [{slug, pct}]
    regimen_especial: CampoEnriquecido | None # "intracomunitario" | "importacion"
    ejercicio_override: CampoEnriquecido | None   # "2024"
    tipo_doc_override: CampoEnriquecido | None    # "FC" | "FV" | "NC" | "NOM"
    notas: CampoEnriquecido | None
    urgente: bool = False
    fuente: str = "email_gestor"  # o "email_cliente"
```

### Llamada a GPT-4o (structured output)
```python
UMBRAL_AUTO = 0.80   # campo se aplica automáticamente
UMBRAL_REVISION = 0.50  # campo va a confirmación, por debajo se descarta

def extraer(
    cuerpo_texto: str,
    nombres_adjuntos: list[str],
    empresas_gestoria: list[dict],  # [{id, slug, nombre}]
    fuente: str = "email_gestor",
) -> list[EnriquecimientoDocumento]:
    texto_nuevo = _extraer_texto_nuevo(cuerpo_texto)
    if not _merece_extraccion(texto_nuevo):
        return []
    # llamada GPT-4o con JSON schema estricto
    # retorna lista de EnriquecimientoDocumento
```

**Prompt al modelo**: incluye texto nuevo + nombres de adjuntos + lista de slugs/nombres de empresas de la gestoría + schema JSON de salida.

### Lógica de aplicación por campo
```
campo.confianza >= 0.80 → aplicar automáticamente en hints_json
campo.confianza 0.50-0.79 → guardar en "pendiente_confirmacion" del email
campo.confianza < 0.50 → descartar (no contaminamos el pipeline)
```

Si al menos un campo queda `pendiente_confirmacion` → crear notificación `INSTRUCCION_AMBIGUA` al gestor.

---

## Schema formal `hints_json`

Estructura unificada para todos los escritores (catchall, ingesta, pipeline):

```python
class HintsJson(TypedDict, total=False):
    # Campos existentes
    tipo_doc: str           # "FC" | "FV" | "NC" | "NOM" | "BAN" | ...
    nota: str
    slug: str               # empresa destino (catchall)
    from_email: str
    origen: str             # "catchall_email" | "email_ingesta" | "portal" | ...
    email_id: int           # FK a EmailProcesado
    # Nuevo: enriquecimiento
    enriquecimiento: EnriquecimientoAplicado

class EnriquecimientoAplicado(TypedDict, total=False):
    iva_deducible_pct: int        # 0-100
    motivo_iva: str
    categoria_gasto: str          # slug MCF
    subcuenta_contable: str
    reparto_empresas: list        # [{slug, pct}]
    regimen_especial: str
    ejercicio_override: str
    tipo_doc_override: str
    notas: str
    urgente: bool
    fuente: str                   # "email_gestor" | "email_cliente"
    campos_pendientes: list[str]  # campos con confianza 0.50-0.79, a confirmar
```

---

## Cambios en `ingesta_correo.py`

En el loop de procesamiento, después de `extraer_adjuntos()` y antes de `_encolar_archivo()`:

```
1. extraer_adjuntos() → [PDFs]
2. ExtractorEnriquecimiento.extraer(body, filenames, empresas_gestoria) → [instrucciones]
3. asociar_por_filename(instrucciones, PDFs):
   - instruccion.adjunto == pdf.nombre → asignar directamente
   - instruccion.adjunto == "GLOBAL" → asignar a todos los PDFs sin instrucción propia
4. Por cada (pdf, instruccion):
   hints = merge(hints_asunto_existentes, instruccion_filtrada_por_umbral)
   _encolar_archivo(pdf, empresa_id, hints_json=hints)
5. Guardar campos_pendientes en EmailProcesado.enriquecimiento_pendiente_json
6. Si hay campos_pendientes → crear_notificacion_usuario(INSTRUCCION_AMBIGUA)
```

### Extracción DKIM de headers
En `imap_servicio.py._parsear_email()`:
```python
auth_results = msg.get("Authentication-Results", "")
dkim_ok = "dkim=pass" in auth_results.lower()
email_data["dkim_verificado"] = dkim_ok
```

### Soporte .eml como adjunto
En `extractor_adjuntos.py`:
```python
if content_type == "message/rfc822":
    eml_bytes = part.get_payload(decode=True)
    inner_msg = email.message_from_bytes(eml_bytes)
    # extraer adjuntos del inner_msg recursivamente
```

---

## Cambios en el pipeline (aplicación del enriquecimiento)

### `sfce/phases/registration.py`
Nueva función `_aplicar_enriquecimiento(datos_extraidos, hints_json)` llamada al inicio de `registrar()`:

```python
enrich = hints_json.get("enriquecimiento", {})

if enrich.get("iva_deducible_pct") is not None:
    # override porcentaje deducible en todas las líneas
    pct = enrich["iva_deducible_pct"]
    for linea in datos_extraidos.lineas:
        linea.iva_deducible_pct = pct

if enrich.get("tipo_doc_override"):
    datos_extraidos.tipo_doc = enrich["tipo_doc_override"]

if enrich.get("ejercicio_override"):
    datos_extraidos.ejercicio = enrich["ejercicio_override"]

if enrich.get("categoria_gasto"):
    datos_extraidos.categoria_gasto = enrich["categoria_gasto"]
```

**Prioridad explícita**: `instruccion_gestor (6) > aprendizaje_yaml (5) > MCF_automatico (4) > OCR (3)`

### `sfce/phases/correction.py`
Si `enrich.subcuenta_contable` presente → usar directamente como subcuenta de gasto, sin pasar por clasificador MCF.

---

## Aprendizaje desde confirmaciones

Cuando el gestor confirma un campo pendiente desde el dashboard:

```python
# En sfce/api/rutas/correo.py — endpoint POST /api/correo/emails/{id}/confirmar
def confirmar_enriquecimiento(email_id, campos_confirmados, sesion):
    # 1. Aplicar campos confirmados al documento en cola
    # 2. Guardar como regla de aprendizaje
    for campo, valor in campos_confirmados.items():
        if campo == "iva_deducible_pct" and "furgoneta" in notas_lower:
            # crear ReglaClasificacionCorreo tipo ENRIQUECIMIENTO
            # condicion: keyword en cuerpo, accion: aplicar iva_deducible_pct=valor
```

---

## Las 13 grietas (revisadas)

### G1 — Slug (simplificada)
El campo `slug` ya existe en `Empresa` (`nullable=True`). La migración 021 solo hace backfill:
```sql
UPDATE empresas SET slug = lower(regexp_replace(nombre, '[^a-z0-9]', '', 'gi'))
WHERE slug IS NULL;
```
+ constraint NOT NULL post-backfill. `ingesta_correo.py` y `canal_email_dedicado.py` usan `empresa.slug` siempre.

### G2 — Ambigüedad remitente
Mismo remitente en 2+ empresas de la gestoría → GPT-4o desambigua por asunto/cuerpo. Si sigue sin resolver → cuarentena con UI "¿es de Fulano o de Mengano?" + la respuesta del gestor se guarda como regla (aprendizaje).

### G3 — Primer email siempre cuarentena
`configurar_email_empresa()` acepta lista de remitentes iniciales. El wizard de onboarding tiene un paso "Proveedores habituales" donde el gestor registra los más comunes.

### G4 + G10 — Email descartado sin rastro
`worker_catchall.py` y `ingesta_correo.py`: slug desconocido → guardar `EmailProcesado(estado=CUARENTENA, motivo=SLUG_DESCONOCIDO)`. Nunca descartar sin dejar rastro en BD.

### G5 — Sin endpoints whitelist
4 endpoints nuevos + página dashboard. G5 y G6 integrados: la UI muestra aviso "Al añadir el primer remitente, solo se aceptarán los de esta lista" antes de confirmar.

### G6 — Aviso cambio comportamiento whitelist
Integrado en UI de G5: modal de confirmación al añadir el primer remitente.

### G7 — Score no se aplica en gestoría
En rama gestoría de `ingesta_correo.py`: aplicar `calcular_score_email()` + fallback IA si no hay regla que haga match.

### G8 — Acceso sin cuenta
`if cuenta is None: raise HTTPException(404)` en todos los endpoints de correo antes de verificar acceso.

### G9 — Gestor ciego respecto a emails
Endpoint `GET /api/gestor/empresas/{id}/emails` con filtros (estado, fecha, desde, hasta) + paginación desde v1. Página dashboard con tabla: remitente, asunto, fecha, empresa asignada, estado, nº adjuntos, instrucciones aplicadas.

### G11 — Tests incompletos
Tests nuevos: remitente en 2 empresas → ambigüedad, wildcard `@dominio.com`, slug desconocido → cuarentena (no descarte), score en gestoría, whitelist vacía → configurada, pre-filtro extractor, reenvío parseado.

### G12 — Regla CLASIFICAR sin slug
Validación en `POST /api/correo/admin/reglas`: si `accion == "CLASIFICAR"` y `slug_destino` es null → 422.

### G13 — tipo_doc perdido en gestoría
Rama gestoría en `ingesta_correo.py`: `extraer_hints_asunto(asunto)` también aquí. `tipo_doc` y `nota` se propagan a `ColaProcesamiento.hints_json`.

---

## Trazabilidad en dashboard

### Vista documento
Añadir sección "Origen email" en la página de detalle del documento:
- Remitente original
- Asunto
- Instrucciones recibidas (lista de campos con sus valores)
- Instrucciones aplicadas (con marca ✓ o ⚠ pendiente)

### Vista emails gestor (`/gestor/emails`)
Columna "Instrucciones" en la tabla: badge verde (aplicadas) / amarillo (pendiente confirmación) / gris (sin instrucciones).
Botón "Confirmar" en filas con campos pendientes → abre modal con cada campo y su valor propuesto.

---

## Guía contextual en dashboard

**Ruta**: `/ayuda/correo`
**Visible para**: gestor, admin_gestoria, cliente

**Secciones**:
1. Cómo enviar documentos — los 4 casos con ejemplos de asunto y cuerpo
2. Instrucciones reconocidas — tabla de frases naturales → efecto en el sistema
3. Ejemplos completos de email — copiables, con y sin instrucciones
4. Qué pasa si hay ambigüedad — proceso de confirmación explicado con capturas
5. Dirección de email de cada empresa — enlace a la sección de configuración

**Tabla de frases naturales reconocidas** (ejemplos para la guía):

| Frase | Efecto |
|-------|--------|
| "100% IVA", "furgoneta de reparto", "uso exclusivo negocio" | iva_deducible_pct = 100 |
| "50% IVA", "uso mixto", "coche particular y negocio" | iva_deducible_pct = 50 |
| "sin IVA", "IVA 0%" | iva_deducible_pct = 0 |
| "es de Fulano", "para Mengano" | cliente_slug = empresa identificada |
| "es del año pasado", "diciembre 2024" | ejercicio_override = año detectado |
| "es intracomunitaria", "de la UE" | regimen_especial = intracomunitario |
| "es una importación", "viene de fuera de la UE" | regimen_especial = importacion |
| "gastos de representación" | categoria_gasto = representacion |
| "es urgente", "urge contabilizar" | urgente = true |

---

## Archivos afectados

| Archivo | Tipo |
|---------|------|
| `sfce/conectores/correo/extractor_enriquecimiento.py` | Nuevo |
| `sfce/conectores/correo/imap_servicio.py` | Modificado (DKIM + .eml) |
| `sfce/conectores/correo/extractor_adjuntos.py` | Modificado (soporte .eml) |
| `sfce/conectores/correo/ingesta_correo.py` | Modificado (enriquecimiento + G7 + G13) |
| `sfce/conectores/correo/worker_catchall.py` | Modificado (G4 + G10) |
| `sfce/conectores/correo/onboarding_email.py` | Modificado (G3 + prereqs Google) |
| `sfce/conectores/correo/whitelist_remitentes.py` | Modificado (G6 metadata) |
| `sfce/api/rutas/correo.py` | Modificado (G5 + G8 + G12 + confirmar_enriquecimiento) |
| `sfce/api/rutas/gestor.py` | Modificado (G9 endpoint emails) |
| `sfce/phases/registration.py` | Modificado (_aplicar_enriquecimiento) |
| `sfce/phases/correction.py` | Modificado (subcuenta override) |
| `sfce/db/modelos.py` | Modificado (G1 backfill + EmailProcesado.enriquecimiento_pendiente_json) |
| `sfce/db/migraciones/021_empresa_slug_backfill.py` | Nuevo (G1 simplificada) |
| `sfce/db/migraciones/022_email_enriquecimiento.py` | Nuevo (campo en EmailProcesado) |
| `sfce/core/hints_json.py` | Nuevo (TypedDict HintsJson + EnriquecimientoAplicado) |
| `sfce/core/notificaciones.py` | Modificado (motivo INSTRUCCION_AMBIGUA) |
| `dashboard/src/features/correo/whitelist-page.tsx` | Nuevo (G5 + G6) |
| `dashboard/src/features/correo/gestor-emails-page.tsx` | Nuevo (G9) |
| `dashboard/src/features/correo/confirmar-enriquecimiento-dialog.tsx` | Nuevo |
| `dashboard/src/features/ayuda/guia-correo-page.tsx` | Nuevo |
| `.env.example` | Modificado (Google Workspace) |
| `tests/test_correo/test_extractor_enriquecimiento.py` | Nuevo |
| `tests/test_correo/test_ingesta_correo.py` | Modificado (+G11 + enriquecimiento) |
| `tests/test_correo/test_worker_catchall.py` | Modificado (G4 + G10) |
| `tests/test_pipeline/test_registration_enriquecimiento.py` | Nuevo |

---

## Tests estimados: ~65 nuevos
- Extractor enriquecimiento: pre-filtro, parser reenvíos, campos por confianza, GLOBAL vs por adjunto (~20)
- Grietas (G1 backfill, G4/G10 cuarentena, G7 score, G8 404, G9 paginación, G12 validación, G13 tipo_doc) (~20)
- Pipeline enriquecimiento: IVA override, categoria override, ejercicio override, prioridad (~15)
- Aprendizaje desde confirmación (~5)
- .eml extracción anidada, DKIM header (~5)
