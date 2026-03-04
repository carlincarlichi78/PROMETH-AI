# SFCE — Manual del Gestor / Asesor
> **Versión:** 1.0 | **Actualizado:** 2026-03-04 | **Audiencia:** admin_gestoria · asesor

---

## Acceso al sistema

**URL:** https://sfce.prometh-ai.es (o la URL que te haya dado tu administrador)
**Login:** tu email `@prometh-ai.es` + contraseña `Uralde2026!`

### Roles y permisos

| Rol | Quién | Qué puede hacer |
|-----|-------|-----------------|
| `admin_gestoria` | Sergio, Gestor1, Gestor2, Javier | Todo lo de asesor + crear usuarios, configurar empresas, onboarding |
| `asesor` | Francisco, Maria, Luis | Ver y trabajar con todas las empresas de su gestoría |

> **Nota:** Cada gestor solo ve las empresas de su gestoría. El superadmin ve todo.

---

## Pantalla de inicio

Al entrar verás el **Centro de Operaciones**: tarjetas por empresa con estado de documentos pendientes, alertas fiscales próximas y KPIs rápidos.

- **Selector de empresa** (arriba a la izquierda): cambia el contexto a la empresa que quieras trabajar.
- **OmniSearch** (barra superior o `Ctrl+K`): búsqueda global — documentos, empresas, facturas, asientos.
- **Copiloto IA** (panel derecho): asistente conversacional para consultas rápidas sobre la empresa activa.
- **Notificaciones** (campana): alertas de documentos en cuarentena, modelos próximos, errores de ingesta.

---

## Módulo: Documentos

### Subir documentos manualmente

`Documentos → Inbox` — arrastra PDFs o usa el botón **Subir**.

También puedes subir un lote en ZIP: `Documentos → Subir ZIP`.

### Ver el pipeline (Operations Center)

`Documentos → Pipeline (Live)` — vista en tiempo real con **layout 3 columnas**:

- **Columna izquierda (Fuentes):** actividad por canal de entrada (Correo IMAP, Watcher local, Subida manual) + ranking de empresas con docs procesados hoy. Click en una empresa para filtrar toda la vista.
- **Columna central (Diagrama de flujo):** nodos Inbox → OCR → Validación → FS → Asiento → Completado con partículas animadas mostrando el flujo. Zona de subida manual en la parte inferior.
- **Columna derecha (Breakdown):** distribución por tipo_doc (FC/FV/NC/SUM…) hoy + feed de actividad en tiempo real.

| Estado | Significado |
|--------|-------------|
| `pendiente` | Recién subido, esperando OCR |
| `procesando` | OCR en curso (Mistral / GPT-4o) |
| `revisión` | Extraído pero requiere validación manual |
| `registrado` | Asiento creado en FacturaScripts |
| `cuarentena` | Error o CIF desconocido — requiere acción |
| `error` | Fallo técnico — ver log |

### Cola de revisión

`Colas → Revisión` — documentos que el motor no pudo procesar automáticamente. Para cada uno:
1. Ver la extracción OCR vs el PDF original (vista dividida).
2. Corregir campos si es necesario (importe, fecha, CIF, IVA).
3. Pulsar **Aprobar** para que continúe al registro contable, o **Rechazar** para descartarlo.

### Cuarentena

`Documentos → Cuarentena` — documentos con CIF desconocido o regla no resuelta.
- Si el CIF no existe en el config del cliente: añadirlo en `Configuración → Procesamiento` y pulsar **Reintentar**.
- Si es un documento duplicado: marcarlo como **Descartado**.

### Archivo

`Documentos → Archivo` — histórico completo de documentos procesados. Filtros por empresa, fecha, tipo, estado.

---

## Módulo: Correo IMAP (Ingesta automática)

`Correo → Cuentas` — lista las cuentas IMAP configuradas para ingesta automática.

### Cómo funciona

Cada empresa puede tener una cuenta dedicada (ej. `facturas-gerardo@prometh-ai.es`). Cuando un proveedor envía una factura a esa dirección, el sistema:
1. Descarga el email (polling cada N minutos).
2. Extrae los adjuntos PDF.
3. Los introduce en el pipeline igual que si se hubieran subido manualmente.

### Gestión del correo

`Correo → Emails` — lista de emails procesados. Puedes ver el estado de cada adjunto.

`Correo → Reglas de clasificación` — reglas automáticas para enrutar emails de remitentes conocidos.

`Correo → Whitelist` — remitentes autorizados. Emails de remitentes fuera de whitelist van a revisión manual.

### Solución de problemas comunes

| Problema | Causa habitual | Solución |
|----------|---------------|----------|
| Email no procesado | Remitente no en whitelist | Añadir en `Correo → Whitelist` |
| Adjunto en cuarentena | CIF no reconocido | Añadir proveedor en config empresa |
| Cuenta IMAP en error | App Password caducada | Regenerar en `myaccount.google.com → App passwords` |

---

## Módulo: Conciliación Bancaria

`Contabilidad → Conciliación` (o desde el sidebar: **Conciliación**)

### Subir extracto bancario

`Conciliación → Subir extracto` — sube archivo Norma 43 (`.c43`, `.txt`) o Excel CaixaBank. El sistema detecta el formato automáticamente.

### Flujo de conciliación

El motor analiza los movimientos bancarios y los cruza con documentos registrados en 5 capas:

| Capa | Lógica | Acción recomendada |
|------|--------|--------------------|
| 1 — Exacta unívoca | Importe exacto + fecha ±2d + único candidato | Se concilia automáticamente |
| 2 — NIF en concepto | NIF del proveedor aparece en el concepto bancario | Revisar sugerencia |
| 3 — Nº factura | Número de factura normalizado en el concepto | Revisar sugerencia |
| 4 — Patrón aprendido | Patrón aprendido de conciliaciones anteriores | Revisar sugerencia |
| 5 — Importe aproximado | Diferencia ≤1% | Revisión manual obligatoria |

### Pestaña Sugerencias

Lista de matches propuestos por el motor. Para cada uno:
- **Confirmar**: acepta el match, crea el asiento si no existe, actualiza el patrón aprendido.
- **Rechazar**: descarta esta sugerencia. El movimiento vuelve a "pendiente".
- **Parcial**: un movimiento bancario cubre N facturas (pagaré conjunto, etc.).

### Ver descuadre de saldo

`Conciliación → Saldo` — muestra la diferencia entre saldo bancario importado y saldo contable calculado.

---

## Módulo: Fiscal

### Calendario fiscal

`Fiscal → Calendario` — próximas obligaciones de todas las empresas. Código de colores:
- 🟢 Verde: >15 días
- 🟡 Amarillo: 7-15 días
- 🔴 Rojo: <7 días o vencido

### Generar modelo

`Fiscal → Modelos → [Modelo] → Generar`

Modelos disponibles: 303, 111, 115, 130, 190, 347, Verifactu, y otros.

Flujo:
1. Seleccionar empresa + período.
2. El sistema calcula los importes desde los asientos de FacturaScripts.
3. Revisar el borrador. Corregir si hay discrepancias.
4. **Generar PDF** para presentación manual, o **Presentar** si está integrado con Sede Electrónica.

### Histórico de modelos

`Fiscal → Histórico` — todos los modelos generados por empresa y período. Descargables en PDF.

---

## Módulo: Facturación

### Facturas recibidas

`Facturación → Recibidas` — listado de facturas de proveedores registradas. Filtros por empresa, fecha, proveedor, estado.

### Facturas emitidas

`Facturación → Emitidas` — facturas de clientes.

### Cobros y pagos

`Facturación → Cobros y Pagos` — seguimiento de vencimientos pendientes.

---

## Módulo: Contabilidad

| Página | Descripción |
|--------|-------------|
| `Libro Diario` | Todos los asientos del ejercicio. Exportable |
| `Balance` | Balance de situación. Compara ejercicios |
| `PyG` | Cuenta de pérdidas y ganancias |
| `Plan de cuentas` | Árbol PGC con saldos actuales |
| `Apertura` | Asiento de apertura del ejercicio |
| `Amortizaciones` | Cálculo y registro de amortizaciones |
| `Cierre` | Asiento de cierre del ejercicio |

---

## Módulo: Económico / Analítico

| Página | Qué muestra |
|--------|-------------|
| `KPIs` | Indicadores clave: margen, EBITDA, rotación |
| `Tesorería` | Flujo de caja proyectado |
| `Informes` | Informes personalizados exportables |
| `Ratios` | Ratios financieros comparados con sector |
| `Presupuesto vs Real` | Desviaciones sobre presupuesto |
| `Comparativa` | Comparar períodos o empresas |
| `Scoring` | Puntuación financiera de la empresa |
| `Centros de coste` | Analítica por departamento/proyecto |

---

## Módulo: RRHH

`RRHH → Trabajadores` — ficha de cada empleado.
`RRHH → Nóminas` — nóminas procesadas. Se procesan igual que facturas: PDF → OCR → registro.

---

## Módulo: Directorio

`Directorio` — directorio de proveedores y clientes de todas las empresas de la gestoría. Búsqueda por nombre, CIF, email.

---

## Herramientas transversales

### OmniSearch (`Ctrl+K`)

Búsqueda instantánea en todo el sistema: documentos, empresas, facturas, asientos, contactos.

### Copiloto IA

Panel lateral. Pregunta en lenguaje natural:
- "¿Qué facturas tiene pendientes de pago Gerardo González?"
- "¿Cuánto IVA se ha declarado en el 3T 2025?"
- "¿Cuál es el saldo de la cuenta 4000000001?"

### Semáforo de salud

`Salud` — estado del sistema: tests OK, conexión FacturaScripts, estado IMAP, últimos errores de pipeline.

---

## Administración (solo `admin_gestoria`)

### Gestión de usuarios

`Configuración → Usuarios` — crear, editar, desactivar asesores. Asignar rol y gestoría.

### Onboarding de nueva empresa

`Onboarding → Nueva empresa` — wizard de 5 pasos:
1. Datos básicos (nombre, CIF, régimen)
2. Perfil de negocio (sector, facturación estimada)
3. Proveedores recurrentes (para motor de reglas)
4. Conexión FacturaScripts (seleccionar instancia + idempresa)
5. Fuentes de ingesta (email, IMAP, manual)

### Configuración de procesamiento

`Configuración → Procesamiento` — reglas del motor de reglas para cada empresa:
- Proveedores con IVA0 (suplidos, aduanas)
- Subcuentas de reclasificación
- Umbrales de confianza OCR

### Integrations

`Configuración → Integraciones` — tokens API, webhooks, configuración SMTP.

---

## Atajos de teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+K` | OmniSearch |
| `Ctrl+/` | Abrir Copiloto |
| `Ctrl+U` | Subir documento |
| `Esc` | Cerrar panel/modal |

---

## Contacto soporte técnico

Incidencias técnicas (no de uso): admin@prometh-ai.es
