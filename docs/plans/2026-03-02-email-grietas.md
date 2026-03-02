# Plan: Corrección Grietas Sistema Email

**Fecha**: 2026-03-02
**Sesión**: 35
**Prioridad**: Alta — el sistema de correo no es operable en producción sin estos fixes

---

## Contexto

Auditoría profunda del sistema de email realizada en sesión 35. Se encontraron 13 grietas en la implementación actual. El sistema está construido pero tiene fallos que impiden su uso real en producción.

Arquitectura decidida: **un buzón por gestoría** bajo `@prometh-ai.es` (Google Workspace), identificación de empresa por email remitente (whitelist).

---

## CRÍTICAS (P0) — el sistema falla silenciosamente

### G1 — Slug no determinista
**Archivo**: `sfce/conectores/correo/ingesta_correo.py`, `canal_email_dedicado.py`
**Problema**: El routing de emails a empresa se basa en un slug derivado del nombre en tiempo de ejecución:
```python
nombre_slug = re.sub(r"[^a-z0-9]", "", emp["nombre"].lower())[:20]
```
Si el nombre de la empresa cambia, el routing se rompe silenciosamente.
**Fix**: Añadir campo `slug` obligatorio y único en tabla `empresas` (migración). Generarlo una vez en onboarding y nunca cambiarlo.

---

### G2 — Remitente en 2 empresas de la misma gestoría → ambigüedad
**Archivo**: `sfce/conectores/correo/ingesta_correo.py`
**Problema**: Si `facturas@endesa.es` está en la whitelist de Pastorino Y de Chiringuito (misma gestoría), gana el primero por orden de prioridad. El segundo pierde sus documentos sin aviso.
**Fix**: Cuando mismo remitente aparece en 2+ empresas → analizar asunto/contenido con IA para desambiguar. Si sigue sin resolver → cuarentena con propuesta al gestor ("¿es de Pastorino o de Chiringuito?").

---

### G5 — No existe endpoint ni UI para gestionar la whitelist
**Archivo**: `sfce/api/rutas/correo.py`, `dashboard/src/features/correo/`
**Problema**: El gestor no puede configurar desde qué emails recibe documentos cada cliente. No existen estos endpoints:
```
GET  /api/correo/empresas/{id}/remitentes-autorizados
POST /api/correo/empresas/{id}/remitentes-autorizados
DEL  /api/correo/remitentes/{id}
PATCH /api/correo/remitentes/{id}
```
Sin esto, todos los emails de remitentes nuevos van a cuarentena indefinidamente.
**Fix**: Implementar endpoints + página en dashboard para que gestor gestione whitelist de cada empresa.

---

### G8 — Sin verificación de acceso si la cuenta fue borrada
**Archivo**: `sfce/api/rutas/correo.py`
**Problema**: Si una `CuentaCorreo` se elimina, el `if cuenta:` falla silenciosamente y cualquier usuario puede editar emails sin verificación de acceso.
**Fix**: Si `cuenta is None` → raise 404, no continuar sin verificar acceso.

---

## ALTOS (P1) — el sistema funciona pero mal

### G3 — Primer email de cliente nuevo → cuarentena siempre
**Archivo**: `sfce/conectores/correo/onboarding_email.py`
**Problema**: Al dar de alta una empresa, la whitelist solo tiene el email del empresario. El primer envío de cualquier proveedor siempre va a cuarentena.
**Fix**: Wizard de onboarding de remitentes — al crear empresa, el gestor registra los proveedores habituales del cliente (Endesa, Telefónica, su proveedor de género, etc.).

---

### G4 — Email a slug desconocido → descartado sin rastro
**Archivo**: `sfce/conectores/correo/worker_catchall.py`
**Problema**: Si el cliente escribe mal la dirección, el PDF desaparece. No hay cuarentena, no hay notificación.
```python
if not empresa_id:
    logger.warning("slug '%s' no resuelve", slug)
    return {"encolados": 0, "motivo": "slug_desconocido"}  # ← SE PIERDE
```
**Fix**: En lugar de descartar → enviar a cuarentena global con motivo `SLUG_DESCONOCIDO` para que superadmin pueda asignarlo manualmente.

---

### G7 — Score multi-señal no se aplica en cuentas gestoría
**Archivo**: `sfce/conectores/correo/ingesta_correo.py`
**Problema**: En buzones de gestoría solo se usan reglas deterministas. Sin regla configurada → 100% de emails en cuarentena. No hay fallback IA ni scoring.
**Fix**: Aplicar `calcular_score_email()` también en cuentas gestoría. Si score >= umbral y sin regla → clasificar con nivel IA.

---

## MEDIOS (P2) — UX rota o comportamiento inesperado

### G6 — Whitelist vacía acepta todo, al configurarla el comportamiento cambia radicalmente
**Archivo**: `sfce/conectores/correo/whitelist_remitentes.py`
**Problema**: Empresa nueva sin whitelist → acepta cualquier remitente. En el momento que el gestor añade el primer remitente, todos los demás empiezan a ir a cuarentena sin aviso.
**Fix**: Documentar este comportamiento en UI + avisar al gestor cuando configura el primer remitente: "A partir de ahora solo se aceptarán los remitentes de esta lista".

---

### G9 — El gestor está ciego respecto a emails
**Archivo**: `sfce/api/rutas/gestor.py`, `dashboard/src/features/`
**Problema**: No hay ninguna página ni endpoint donde el gestor vea qué emails llegaron, de quién, y si se procesaron o fueron a cuarentena.
**Fix**:
- Endpoint `GET /api/gestor/empresas/{id}/emails` con filtros estado/fecha
- Página dashboard `/gestor/emails` con tabla: remitente, asunto, fecha, empresa asignada, estado, adjuntos

---

### G10 — Email a catch-all sin slug válido → descartado en silencio
**Archivo**: `sfce/conectores/correo/worker_catchall.py`
**Problema**: Si el campo `To:` no contiene un slug reconocido, el email desaparece sin dejar rastro en BD.
**Fix**: Guardar siempre en `EmailProcesado` con estado `CUARENTENA` y motivo `SLUG_DESCONOCIDO`, aunque no se pueda asignar a empresa.

---

### G11 — Tests incompletos
**Archivo**: `tests/test_ingesta_correo.py`
**Problema**: No hay tests para:
- Remitente en whitelist de empresa A y B → ¿dónde va?
- Whitelist con wildcard `@dominio.com` → resolución correcta
- Email sin slug en To → cuarentena (no descarte)
- Score multi-señal en gestoría
- Cambio de comportamiento whitelist vacía → configurada

---

### G12 — Regla con slug_destino nulo en cuenta gestoría
**Archivo**: `sfce/api/rutas/correo.py`, `sfce/conectores/correo/ingesta_correo.py`
**Problema**: Una regla con `accion=CLASIFICAR` y `slug_destino=NULL` no se valida al crear. Resultado: email "clasificado" pero sin empresa destino.
**Fix**: Validación al crear regla: si `accion == "CLASIFICAR"` entonces `slug_destino` es obligatorio → 422 si nulo.

---

### G13 — Tipo de documento perdido en gestoría
**Archivo**: `sfce/conectores/correo/ingesta_correo.py`
**Problema**: En cuentas gestoría el `tipo_doc` (FC, FV, NOM, BAN...) nunca se extrae ni se propaga al pipeline. El pipeline no sabe qué tipo de documento es.
**Fix**: Extraer `tipo_doc` de hints de asunto también en rama gestoría y guardarlo en `ColaProcesamiento.hints_json`.

---

## Orden de implementación recomendado

### Sesión A (base operativa)
1. G1 — Campo `slug` en tabla `empresas` (migración)
2. G5 — Endpoints whitelist + UI básica gestor
3. G4 + G10 — Nunca descartar emails, siempre cuarentena

### Sesión B (operación real)
4. G9 — Vista emails para gestor en dashboard
5. G3 — Wizard onboarding remitentes
6. G7 — Score en gestoría + fallback IA

### Sesión C (robustez)
7. G2 — Desambiguación IA remitente múltiple
8. G8 — Fix acceso sin cuenta
9. G12 — Validación regla CLASIFICAR sin slug
10. G13 — tipo_doc en gestoría
11. G6 — Aviso UI cambio comportamiento whitelist
12. G11 — Tests faltantes

---

## Prerequisitos antes de implementar

1. **App Password Google Workspace** — `admin@prometh-ai.es` → myaccount.google.com → Seguridad → Contraseñas de aplicaciones → nombre: `SFCE-IMAP`
2. **Alias `documentacion@prometh-ai.es`** — admin.google.com → Usuarios → admin → Añadir alias
3. **Actualizar `.env.example`**: `SFCE_SMTP_HOST=smtp.gmail.com`, `SFCE_SMTP_PORT=587`
4. **Actualizar `onboarding_email.py`**: `_CUENTA_CATCHALL_SERVIDOR = "imap.gmail.com"`
5. **Configurar `CuentaCorreo` en BD producción** con credenciales Google Workspace
