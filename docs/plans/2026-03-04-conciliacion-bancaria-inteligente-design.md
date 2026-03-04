# Conciliación Bancaria Inteligente — Design Doc

> **Fecha:** 2026-03-04
> **Estado:** Aprobado
> **Archivos clave:** `sfce/core/motor_conciliacion.py`, `sfce/conectores/bancario/`, `sfce/api/rutas/bancario.py`, `dashboard/src/features/contabilidad/conciliacion-page.tsx`

---

## 1. Contexto y Motivación

El sistema SFCE ya dispone de un motor de conciliación bancaria funcional (Norma 43 + CaixaBank XLS, 2 pasadas: exacto + aproximado) y una API REST básica. El gap actual es:

- El motor solo cruza movimientos vs asientos por **importe + fecha** (no usa contexto documental)
- No existe UI para revisar matches en estado `revision`
- Los documentos del pipeline (con NIF proveedor, número de factura) no se usan en el matching
- No hay aprendizaje de patrones históricos
- La conciliación N:1 (una transferencia cubre N facturas) no está soportada

Este diseño evoluciona el sistema a **Conciliación Híbrida con Aprendizaje**: motor de 5 capas priorizadas, tabla de sugerencias multi-candidato, feedback loop bidireccional, y UI de revisión con vista dividida + PDF modal.

---

## 2. Modelo de Datos

### 2.1 Modificaciones a tablas existentes

#### `cuentas_bancarias`
```sql
ALTER TABLE cuentas_bancarias
    ADD COLUMN saldo_bancario_ultimo NUMERIC(12,2),
    ADD COLUMN fecha_saldo_ultimo    DATE;
```
El campo `saldo_bancario_ultimo` se actualiza en cada ingesta con el campo `saldo_final` del archivo C43/XLS. Permite detectar descuadres respecto al saldo contable calculado.

#### `movimientos_bancarios`
```sql
ALTER TABLE movimientos_bancarios
    ADD COLUMN documento_id    INTEGER REFERENCES documentos(id),  -- documento confirmado (1:1)
    ADD COLUMN score_confianza FLOAT,
    ADD COLUMN metadata_match  TEXT,   -- JSON: detalle del match
    ADD COLUMN capa_match      INTEGER; -- capa que resolvió (1-5)
```

Estados de `estado_conciliacion` (campo existente, se añade valor):
- `pendiente` — sin match
- `sugerido` — motor encontró candidatos, pendiente revisión humana
- `revision` — match aproximado (capa 5), requiere confirmación
- `conciliado` — confirmado (automático unívoco o manual)
- `parcial` — N:1 en curso (importe asignado < importe total)

### 2.2 Tablas nuevas

#### `sugerencias_match`
Permite múltiples candidatos por movimiento, ordenados por score.
```sql
CREATE TABLE sugerencias_match (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    movimiento_id  INTEGER NOT NULL REFERENCES movimientos_bancarios(id) ON DELETE CASCADE,
    documento_id   INTEGER NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    score          FLOAT NOT NULL,
    capa_origen    INTEGER NOT NULL,   -- 1-5
    activa         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(movimiento_id, documento_id)
);
CREATE INDEX idx_sugerencias_movimiento ON sugerencias_match(movimiento_id, activa, score DESC);
```

#### `patrones_conciliacion`
Aprende de confirmaciones manuales: relaciona texto bancario + rango de importe con un proveedor/cuenta.
```sql
CREATE TABLE patrones_conciliacion (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id           INTEGER NOT NULL REFERENCES empresas(id),
    patron_texto         VARCHAR(500) NOT NULL,   -- texto normalizado (mayúsc., sin tildes)
    patron_limpio        VARCHAR(500),            -- sin fechas, códigos TPV, ruido genérico
    nif_proveedor        VARCHAR(20),
    cuenta_contable      VARCHAR(10),             -- cuenta sugerida (ej: "6290000000")
    rango_importe_aprox  VARCHAR(20) NOT NULL,    -- "0-10"|"10-100"|"100-1000"|"1000-10000"|"10000+"
    frecuencia_exito     INTEGER NOT NULL DEFAULT 1,
    ultima_confirmacion  DATE,
    UNIQUE(empresa_id, patron_texto, rango_importe_aprox)
);
CREATE INDEX idx_patrones_empresa ON patrones_conciliacion(empresa_id, patron_limpio, rango_importe_aprox);
```

#### `conciliaciones_parciales`
Soporta N:1: una transferencia bancaria cubre múltiples facturas.
```sql
CREATE TABLE conciliaciones_parciales (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    movimiento_id    INTEGER NOT NULL REFERENCES movimientos_bancarios(id),
    documento_id     INTEGER NOT NULL REFERENCES documentos(id),
    importe_asignado NUMERIC(12,2) NOT NULL,
    confirmado_en    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(movimiento_id, documento_id)
);
```

**Lógica de estado N:1:**
- `movimiento.estado = "parcial"` mientras `SUM(importe_asignado) < movimiento.importe - 0.05`
- `movimiento.estado = "conciliado"` cuando `SUM(importe_asignado) >= movimiento.importe - 0.05`

---

## 3. Funciones de Utilidad

### 3.1 `normalizar_concepto(texto: str) -> tuple[str, str]`

```python
def normalizar_concepto(texto: str) -> tuple[str, str]:
    """
    Devuelve (patron_texto, patron_limpio).

    patron_texto: mayúsculas + sin tildes (para búsqueda general)
    patron_limpio: además elimina fechas, códigos TPV, referencias numéricas largas,
                   frases genéricas ("PAGO CON TARJETA EN", "RECIBO", "TRANSF ORD")
    """
    import unicodedata, re
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = texto.upper().strip()
    patron_texto = texto

    # Eliminar para patron_limpio:
    limpio = re.sub(r'\d{2}/\d{2}/\d{4}', '', texto)          # fechas DD/MM/YYYY
    limpio = re.sub(r'\d{8}', '', limpio)                       # fechas DDMMYYYY
    limpio = re.sub(r'ES\d{20,}', '', limpio)                   # IBANs
    limpio = re.sub(r'\b\d{6,}\b', '', limpio)                  # secuencias largas de dígitos
    limpio = re.sub(r'\bPAGO CON TARJETA EN\b', '', limpio)
    limpio = re.sub(r'\bRECIBO\b', '', limpio)
    limpio = re.sub(r'\bTRANSF(?:ERENCIA)? (?:ORD(?:INARIA)?)?\b', '', limpio)
    limpio = re.sub(r'\bCOMISION\b', '', limpio)
    limpio = ' '.join(limpio.split())  # normalizar espacios
    return patron_texto, limpio
```

### 3.2 `limpiar_nif(nif: str) -> str`

```python
def limpiar_nif(nif: str) -> str:
    """Elimina espacios, guiones y puntos. Devuelve NIF en mayúsculas."""
    import re
    return re.sub(r'[\s\-\.]', '', nif).upper()
```

### 3.3 `rango_importe(importe: Decimal) -> str`

```python
def rango_importe(importe: Decimal) -> str:
    v = abs(float(importe))
    if v < 10:      return "0-10"
    if v < 100:     return "10-100"
    if v < 1000:    return "100-1000"
    if v < 10000:   return "1000-10000"
    return "10000+"
```

---

## 4. Motor de Conciliación — 5 Capas

### Clase refactorizada

```python
class MotorConciliacion:
    VENTANA_EXACTA    = 2    # días
    VENTANA_NIF       = 5    # días (capas 2-3)
    VENTANA_PATRON    = 7    # días (capa 4)
    VENTANA_APROX     = 2    # días (capa 5)
    TOLERANCIA_PCT    = 0.01  # 1%
    UMBRAL_REDONDEO   = Decimal("0.05")

    def conciliar_inteligente(self) -> dict:
        """
        Ejecuta las 5 capas en orden.
        Retorna: {conciliados_auto, sugeridos, revision, pendientes}
        """
        pendientes = self._movimientos_pendientes()
        asientos_usados: set[int] = set()

        for capa in [1, 2, 3, 4, 5]:
            self._ejecutar_capa(capa, pendientes, asientos_usados)

        return self._estadisticas()
```

### Capa 1 — Exacta y Unívoca

**Consulta SQL (optimizada):**
```sql
SELECT d.id, d.importe_total, d.asiento_id, d.nif_proveedor, d.numero_factura
FROM documentos d
JOIN asientos a ON a.id = d.asiento_id
WHERE d.empresa_id = :empresa_id
  AND d.importe_total BETWEEN :importe * 0.999 AND :importe * 1.001
  AND a.fecha BETWEEN :fecha - 2 AND :fecha + 2
  AND d.id NOT IN :asientos_usados
```

**Regla de univocidad:** Si la consulta devuelve **exactamente 1 documento** → conciliar automáticamente (estado=`conciliado`, score=1.0, capa=1). Si devuelve 2+ → degrada: insertar en `sugerencias_match` con score decreciente basado en proximidad de NIF y crear estado `sugerido`.

### Capa 2 — Identidad Documental (NIF)

**Consulta SQL:**
```sql
SELECT d.id, d.importe_total, d.nif_proveedor, d.asiento_id
FROM documentos d
WHERE d.empresa_id = :empresa_id
  AND d.nif_proveedor IS NOT NULL
  AND d.importe_total BETWEEN :importe * 0.99 AND :importe * 1.01
  AND d.asiento_id NOT IN :asientos_usados
```

Luego en Python:
```python
nif_limpio = limpiar_nif(doc.nif_proveedor)
concepto_norm = normalizar_concepto(mov.concepto_propio)[0]
if nif_limpio in concepto_norm and fecha_en_ventana(mov, doc, dias=5):
    insertar_sugerencia(mov, doc, capa=2, score=0.90)
```

### Capa 3 — Referencia de Factura

```python
# No regex sobre el banco: buscar si el número de factura del documento está en el concepto
for doc in candidatos:
    if doc.numero_factura:
        ref_norm = re.sub(r'[\s\-/]', '', doc.numero_factura).upper()
        if ref_norm in mov.concepto_propio.upper().replace(' ', '').replace('-', '').replace('/', ''):
            insertar_sugerencia(mov, doc, capa=3, score=0.90)
```

### Capa 4 — Patrones Aprendidos

```python
patron_texto, patron_limpio = normalizar_concepto(mov.concepto_propio)
rango = rango_importe(mov.importe)

patron = session.query(PatronConciliacion).filter(
    PatronConciliacion.empresa_id == self.empresa_id,
    PatronConciliacion.patron_limpio == patron_limpio,
    PatronConciliacion.rango_importe_aprox == rango,
    PatronConciliacion.frecuencia_exito > 0
).first()

if patron and patron.nif_proveedor:
    doc = self._buscar_doc_por_nif_y_fecha(patron.nif_proveedor, mov.fecha, ventana=7)
    if doc:
        score = min(0.50 + patron.frecuencia_exito * 0.05, 0.95)
        insertar_sugerencia(mov, doc, capa=4, score=score)
```

### Capa 5 — Aproximada (último recurso)

```python
# Solo para movimientos sin sugerencias aún
for mov in sin_sugerencias:
    candidatos = query_por_importe(mov.importe, pct=0.01, ventana=2)
    for doc in candidatos:
        diff_pct = abs(mov.importe - doc.importe_total) / mov.importe
        insertar_sugerencia(mov, doc, capa=5, score=1.0 - diff_pct, estado_mov="revision")
```

### Gestión de Diferencias en Confirmación

```python
def gestionar_diferencia(mov_importe: Decimal, doc_importe: Decimal) -> dict:
    diferencia = abs(mov_importe - doc_importe)
    if diferencia <= Decimal("0.05"):
        return {
            "accion": "auto_redondeo",
            "cuenta_contable": "6590000000",  # 659 Otros gastos gestión corriente
            "importe_ajuste": float(diferencia)
        }
    else:
        return {
            "accion": "crear_asiento_comision",
            "cuenta_contable": "6260000000",  # 626 Servicios bancarios y similares
            "importe_ajuste": float(diferencia),
            "requiere_confirmacion": True
        }
```

**Cuentas FacturaScripts utilizadas:**

| Situación | Cuenta PGC | Subcuenta FS |
|-----------|-----------|--------------|
| Auto-redondeo ≤ 0.05€ | 659 - Otros gastos gestión corriente | `6590000000` |
| Comisión bancaria > 0.05€ | 626 - Servicios bancarios y similares | `6260000000` |
| Cuenta transitoria bancaria | 572 - Bancos e instituciones de crédito | depende empresa |

---

## 5. Feedback Loop (Aprendizaje)

### Confirmación positiva

```python
def _feedback_positivo(mov, doc, session):
    patron_texto, patron_limpio = normalizar_concepto(mov.concepto_propio)
    rango = rango_importe(mov.importe)

    patron = session.query(PatronConciliacion).filter_by(
        empresa_id=mov.empresa_id,
        patron_texto=patron_texto,
        rango_importe_aprox=rango
    ).first()

    if patron:
        patron.frecuencia_exito += 1
        patron.ultima_confirmacion = date.today()
        patron.nif_proveedor = limpiar_nif(doc.nif_proveedor) if doc.nif_proveedor else patron.nif_proveedor
    else:
        session.add(PatronConciliacion(
            empresa_id=mov.empresa_id,
            patron_texto=patron_texto,
            patron_limpio=patron_limpio,
            nif_proveedor=limpiar_nif(doc.nif_proveedor) if doc.nif_proveedor else None,
            rango_importe_aprox=rango,
            frecuencia_exito=1,
            ultima_confirmacion=date.today()
        ))
```

### Rechazo (feedback negativo)

```python
def _feedback_negativo(mov, doc, session):
    # Desactivar sugerencia
    sugerencia = session.query(SugerenciaMatch).filter_by(
        movimiento_id=mov.id, documento_id=doc.id
    ).first()
    if sugerencia:
        sugerencia.activa = False

    # Penalizar patrón si la sugerencia venía de capa 4
    if sugerencia and sugerencia.capa_origen == 4:
        patron_texto, _ = normalizar_concepto(mov.concepto_propio)
        rango = rango_importe(mov.importe)
        patron = session.query(PatronConciliacion).filter_by(
            empresa_id=mov.empresa_id,
            patron_texto=patron_texto,
            rango_importe_aprox=rango
        ).first()
        if patron:
            patron.frecuencia_exito -= 1
            if patron.frecuencia_exito <= 0:
                session.delete(patron)
```

---

## 6. Atomicidad en Confirmación

El flujo de confirmación es una **transacción atómica**: si la comunicación con FacturaScripts falla, no se actualiza la BD local.

```python
async def confirmar_match(movimiento_id: int, documento_id: int, session: Session) -> dict:
    try:
        # 1. Obtener datos
        mov = session.get(MovimientoBancario, movimiento_id)
        doc = session.get(Documento, documento_id)
        diff = gestionar_diferencia(mov.importe, doc.importe_total)

        # 2. Llamar a FS primero (puede fallar)
        if diff["accion"] == "crear_asiento_comision":
            resultado_fs = await crear_asiento_comision_fs(doc.empresa_id, diff)
            # Si lanza excepción → no continuamos

        # 3. Solo si FS OK → actualizar BD local (todo en una transacción)
        with session.begin_nested():
            mov.documento_id    = documento_id
            mov.estado_conciliacion = "conciliado"
            mov.score_confianza = 1.0
            mov.capa_match      = 0  # 0 = manual

            # Desactivar sugerencias del movimiento
            session.query(SugerenciaMatch).filter_by(
                movimiento_id=movimiento_id
            ).update({"activa": False})

            # Feedback positivo
            _feedback_positivo(mov, doc, session)

        session.commit()
        return {"ok": True, "diferencia": diff}

    except Exception as e:
        session.rollback()
        raise
```

---

## 7. Endpoints API

| Método | URL | Descripción |
|--------|-----|-------------|
| `POST` | `/api/bancario/{id}/ingestar` | MEJORADO: +actualiza saldo, +lanza motor automático |
| `GET`  | `/api/bancario/{id}/sugerencias` | Lista SugerenciasMatch activas (score DESC, con doc embedded) |
| `GET`  | `/api/bancario/{id}/saldo-descuadre` | `{saldo_bancario, saldo_contable, diferencia, alerta, movimientos_sin_equivalente[]}` |
| `POST` | `/api/bancario/{id}/confirmar-match` | `{movimiento_id, documento_id}` → conciliar + FS + aprendizaje |
| `POST` | `/api/bancario/{id}/rechazar-match` | `{movimiento_id, documento_id}` → feedback negativo |
| `POST` | `/api/bancario/{id}/confirmar-bulk` | `{score_minimo: 0.95}` → confirma todos los sugeridos automáticamente |
| `POST` | `/api/bancario/{id}/conciliacion-parcial` | `{movimiento_id, items: [{documento_id, importe}]}` → N:1 |
| `GET`  | `/api/bancario/{id}/patrones` | CRUD patrones aprendidos |
| `DELETE` | `/api/bancario/{id}/patrones/{pid}` | Eliminar patrón manualmente |

---

## 8. Dashboard — Estructura y Componentes

### Ruta y archivo principal

`/empresa/:id/conciliacion` → `dashboard/src/features/contabilidad/conciliacion-page.tsx`

### 5 Pestañas

```
┌─────────────────────────────────────────────────────────────────────┐
│  Conciliación Bancaria — EMPRESA X                                  │
├──────────┬────────────────┬──────────────┬──────────┬──────────────┤
│ Resumen  │ Sugerencias(N) │ Movimientos  │ Patrones │ Cuentas      │
└──────────┴────────────────┴──────────────┴──────────┴──────────────┘
```

#### Tab: Resumen

- **Upload zona** (SubirExtracto existente, mejorado para auto-trigger)
- **Alerta de saldo** (si `diferencia > 0.01€`):
  ```
  ⚠️ Descuadre detectado: banco 10.250€ / sistema 9.750€ (Δ500€)
  [Ver movimientos sin equivalente →]
  ```
  El botón navega a Tab Movimientos con filtro `sin_equivalente=true`.
- **KPI strip**: Auto-conciliados | Sugeridos | En revisión | Pendientes | % Cobertura

#### Tab: Sugerencias

Vista dividida (40/60):

```
┌────────────────────────────┬─────────────────────────────────────────────┐
│ MOVIMIENTOS CON SUGERENCIA │ DETALLE CANDIDATOS                          │
│                            │                                             │
│  [✓ Confirmar todos 0.95+] │  ┌── Movimiento ──────────────────────────┐ │
│                            │  │ 02/03/2025  -187.34€                   │ │
│  ● ENDESA  0.90  02/03     │  │ ENDESA ENERGIA SA RECIBO 20250301      │ │
│    -187.34€                │  └────────────────────────────────────────┘ │
│                            │                                             │
│  ● AMAZON  0.85  05/03     │  ┌── Candidatos ──────────────────────────┐ │
│    -9.99€                  │  │ ████████░░ 0.90  FV-2025-0234          │ │
│                            │  │ Endesa S.A.  187.34€  ●Capa 2 NIF     │ │
│  ● GONZALEZ 0.65  28/02    │  │                                        │ │
│    -1200€                  │  │ ██████░░░░ 0.65  FV-2025-0231          │ │
│                            │  │ Endesa S.A.  186.00€  ●Capa 5 aprox   │ │
│                            │  └────────────────────────────────────────┘ │
│                            │                                             │
│                            │  [📄 Ver PDF completo]                      │
│                            │                                             │
│                            │  [✓ CONFIRMAR]  [✗ RECHAZAR]  [⟳ OMITIR]  │
└────────────────────────────┴─────────────────────────────────────────────┘
```

**Modal PDF:** Al hacer clic en "Ver PDF completo" → `<Dialog>` fullscreen con `<iframe src="/api/documentos/{empresa_id}/{doc_id}/descargar" />`.

**N:1 (Conciliación Parcial):** Botón "Asignar múltiples facturas" abre panel expandido con selector multi-documento y campo de importe por factura.

**Bulk action:** "Confirmar todos con Score > 0.95" → llama `POST /confirmar-bulk` con `score_minimo=0.95`.

#### Tab: Movimientos

Tabla existente mejorada con:
- Filtro extra: `sin_equivalente` (movimientos en banco sin ningún candidato)
- Columna `Documento` con link al doc si conciliado

#### Tab: Patrones

Tabla CRUD de `patrones_conciliacion`:
- Columnas: Concepto bancario | NIF proveedor | Cuenta | Rango importe | Usos | Última confirmación
- Botón eliminar por fila
- Sin creación manual (solo se generan automáticamente por confirmaciones)

#### Tab: Cuentas

CRUD existente de `CuentaBancaria` + columna comparativa saldo bancario vs saldo contable.

---

## 9. Testing

### Suites TDD requeridas

| Suite | Tests estimados |
|-------|----------------|
| `test_normalizar_concepto.py` | 12 (tildes, fechas, IBANs, frases genéricas) |
| `test_motor_conciliacion.py` | 25 (las 5 capas, univocidad capa 1, feedback +/-) |
| `test_api_bancario.py` | 20 (todos los endpoints nuevos) |
| `test_conciliacion_parcial.py` | 8 (N:1, estado parcial, estado conciliado) |
| `test_saldo_descuadre.py` | 6 (saldo bancario vs contable, alerta) |

**Total estimado: 71 tests nuevos**

### Migración BD

Migración `029_conciliacion_inteligente.py`:
1. ALTER TABLE cuentas_bancarias (+saldo_bancario_ultimo, +fecha_saldo_ultimo)
2. ALTER TABLE movimientos_bancarios (+documento_id, +score_confianza, +metadata_match, +capa_match)
3. CREATE TABLE sugerencias_match
4. CREATE TABLE patrones_conciliacion
5. CREATE TABLE conciliaciones_parciales

---

## 10. Componentes Nuevos / Modificados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `sfce/db/migraciones/029_conciliacion_inteligente.py` | NUEVO | Migración completa |
| `sfce/core/motor_conciliacion.py` | REFACTOR | Motor 5 capas + feedback |
| `sfce/core/normalizar_bancario.py` | NUEVO | normalizar_concepto, limpiar_nif, rango_importe |
| `sfce/api/rutas/bancario.py` | EXTENDER | 6 endpoints nuevos/mejorados |
| `dashboard/src/features/contabilidad/conciliacion-page.tsx` | REFACTOR | 5 pestañas completas |
| `dashboard/src/features/contabilidad/components/panel-sugerencias.tsx` | NUEVO | Vista dividida |
| `dashboard/src/features/contabilidad/components/match-card.tsx` | NUEVO | Tarjeta candidato con score |
| `dashboard/src/features/contabilidad/components/pdf-modal.tsx` | NUEVO | Modal fullscreen PDF |
| `dashboard/src/features/contabilidad/components/patrones-tabla.tsx` | NUEVO | CRUD patrones |
| `dashboard/src/features/contabilidad/components/conciliacion-parcial.tsx` | NUEVO | Selector N:1 |
| `dashboard/src/features/contabilidad/api.ts` | EXTENDER | Hooks para endpoints nuevos |
