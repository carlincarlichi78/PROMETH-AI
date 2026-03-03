# Diseño: Cuentas IMAP por Asesor

**Fecha:** 2026-03-03
**Estado:** Aprobado

## Problema

Los documentos que los clientes envían por correo al asesor asignado no entran automáticamente al pipeline. Se necesita monitorizar el buzón IMAP de cada asesor y enrutar los adjuntos PDF a la empresa correcta.

## Decisión

Nuevo `tipo_cuenta='asesor'` en `cuentas_correo` con `usuario_id` FK. Routing por CIF extraído del PDF (pdfplumber, sin API), con fallback a whitelist remitente y cuarentena.

---

## 1. Modelo de datos

### Migración `028_cuenta_correo_asesor.py`

```sql
ALTER TABLE cuentas_correo ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id);
```

### Invariantes por tipo_cuenta

| tipo_cuenta | empresa_id | gestoria_id | usuario_id |
|-------------|-----------|-------------|------------|
| empresa     | requerido  | null        | null       |
| gestoria    | null       | requerido   | null       |
| asesor      | null       | null        | requerido  |
| dedicada    | null       | null        | null       |
| sistema     | null       | null        | null       |

### 6 cuentas a crear

| usuario      | email IMAP                  | empresas en scope                   |
|--------------|-----------------------------|-------------------------------------|
| francisco    | francisco@prometh-ai.es     | PASTORINO (id=1)                    |
| mgarcia      | mgarcia@prometh-ai.es       | GERARDO (id=2), CHIRINGUITO (id=3)  |
| llupianez    | llupianez@prometh-ai.es     | ELENA (id=4)                        |
| gestor1      | gestor1@prometh-ai.es       | MARCOS (id=5), AURORA (id=7), DISTRIB (id=9) |
| gestor2      | gestor2@prometh-ai.es       | LAMAREA (id=6), CATERING (id=8)     |
| javier       | javier@prometh-ai.es        | COMUNIDAD (id=10), FRANMORA (id=11), GASTRO (id=12), BERMUDEZ (id=13) |

Servidor IMAP: `imap.gmail.com`, puerto `993`, SSL `true`.

---

## 2. Routing logic

Nueva rama en `IngestaCorreo.procesar_cuenta()` para `tipo_cuenta='asesor'`:

```
para cada email nuevo:
  1. descargar bytes de adjuntos PDF
  2. pdfplumber → extraer texto (sin API, gratuito)
  3. buscar CIF/NIF en texto con regex:
       - Sociedad: [A-Z]\d{7}[A-Z0-9]
       - Autónomo: \d{8}[A-Z]
  4. cruzar CIF encontrado contra empresas del usuario (campo cif en BD)
  5. si match único → ColaProcesamiento para esa empresa
  6. si no match → whitelist_remitentes (lógica existente)
  7. si no match → cuarentena (empresa_destino_id=None)
```

Función nueva: `_resolver_empresa_por_cif(cif_extraido, empresas_usuario) -> Empresa | None`

Función nueva: `_extraer_cif_pdf(bytes_pdf) -> str | None` (pdfplumber, regex)

---

## 3. API endpoints nuevos

```
POST /api/correo/admin/cuentas/{id}/test   → verifica login IMAP (timeout 10s)
GET  /api/correo/admin/cuentas?tipo=asesor → lista cuentas asesor (ya existe el GET general)
```

El endpoint de creación ya existe: `POST /api/correo/admin/cuentas`.
Solo necesita aceptar `usuario_id` como campo adicional.

---

## 4. Dashboard UI

Extender `cuentas-correo-page.tsx`:

- Nueva sección "Cuentas IMAP asesores" debajo de las existentes
- Tabla: usuario, email, activa, último poll, emails procesados (contador)
- Botón "Nueva cuenta" → dialog (usuario select, servidor, puerto, SSL, usuario IMAP, contraseña)
- Botón "Probar conexión" por fila → badge verde/rojo
- Botón "Activar/Desactivar" por fila

---

## 5. Setup Google Workspace (manual, previo a crear registros)

Para cada asesor en Google Admin (`admin.google.com`):
1. `Usuarios → [usuario] → Apps → Gmail → Configuración` → habilitar IMAP
2. El usuario crea App Password: `myaccount.google.com → Seguridad → Contraseñas de aplicaciones → SFCE-IMAP`

La App Password (16 chars) se introduce en el dashboard al crear la CuentaCorreo. Se cifra con Fernet antes de guardar.

---

## 6. Tests

- `test_cuenta_correo_asesor.py`: migración, routing CIF, fallback whitelist, fallback cuarentena
- `test_extraer_cif_pdf.py`: extracción CIF de texto con casos edge (múltiples CIFs, sin CIF, CIF intracomunitario)
- Endpoint test: `POST /api/correo/admin/cuentas/{id}/test` con mock IMAP
- UI: smoke test dashboard (no E2E completo)

---

## 7. Orden de implementación

1. Migración 028 (schema)
2. `_extraer_cif_pdf()` + `_resolver_empresa_por_cif()` + tests
3. Rama `tipo='asesor'` en `procesar_cuenta()`
4. Endpoint `POST .../test` + aceptar `usuario_id` en POST crear cuenta
5. Dashboard UI (sección asesores en cuentas-correo-page)
6. Crear los 6 registros en BD (tras setup Google Workspace)
