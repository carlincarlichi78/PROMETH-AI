# 19 - Módulo Bancario: Ingesta y Conciliación

> **Estado:** ✅ COMPLETADO
> **Actualizado:** 2026-03-01
> **Fuentes principales:** `sfce/conectores/bancario/parser_c43.py`, `sfce/conectores/bancario/ingesta.py`, `sfce/core/motor_conciliacion.py`, `sfce/api/rutas/bancario.py`

---

## Visión general

El módulo bancario permite ingestar extractos bancarios en formato estándar español (Norma 43 AEB) y formato propietario CaixaBank, deduplicarlos, clasificarlos automáticamente por tipo de movimiento y conciliarlos contra los asientos contables registrados en el SFCE.

---

## 1. Formatos soportados

| Formato | Extensión | Parser | Descripción |
|---------|-----------|--------|-------------|
| Norma 43 AEB estándar | `.txt`, `.c43` | `parser_c43.py` | Extracto texto plano, encoding latin-1, registros de longitud fija |
| Norma 43 CaixaBank extendido | `.txt`, `.c43` | `parser_c43.py` | Variante propietaria CaixaBank: R22 de 80 chars con prefijo 8 chars antes de fechas |
| CaixaBank XLS | `.xls`, `.xlsx` | `parser_xls.py` | Exportación Excel "Excel simple" de CaixaBank |

La detección de formato es **automática** en ambos parsers.

---

## 2. Estructura del formato Norma 43

El extracto AEB Norma 43 usa registros de longitud fija identificados por los dos primeros caracteres:

| Registro | Longitud | Descripción |
|----------|----------|-------------|
| `11` | variable | Cabecera de cuenta: banco(4)+oficina(4)+cuenta(10)+divisa(3 ISO)+saldo_inicial(18)+signo(1) |
| `22` | 105 (std) / 80 (CaixaBank) | Movimiento: fecha_op(6)+fecha_val(6)+concepto_común(2)+concepto_propio(2)+importe(14)+signo(1)+num_doc(6)+ref1(12)+ref2(16)+concepto(38) |
| `23` | 76 | Concepto adicional (Norma 43 Extendida): subtipo(2)+texto(72). Se concatena al concepto_propio del R22 anterior |
| `33` | 74+ | Totales de cuenta: banco+oficina+cuenta+divisa+fecha+num_debe(6)+imp_debe(14)+num_haber(6)+saldo_final(18)+signo(1) |
| `88` | 2 | Fin de fichero |

### Formato CaixaBank (R22 de 80 chars)

```
tipo(2) + espacios(4) + cod_producto(4) + fecha_op(6) + fecha_val(6)
+ conc_comun(2) + conc_propio_banco(4) + importe(14) + signo_0(1)
+ num_doc(6) + ref1(12) + ref2(16) + libre(3)
```

La diferencia crítica es el prefijo de 8 caracteres (`4 espacios + 4 dígitos cod_producto`) que desplaza todos los campos 8 posiciones respecto al estándar AEB.

---

## 3. Auto-detección de formato CaixaBank

```python
def _es_formato_caixabank(lineas: list) -> bool:
    for linea in lineas:
        if len(linea) >= 6 and linea[:2] == "22":
            return linea[2:6] == "    "  # 4 espacios en posiciones [2:6]
    return False
```

El criterio es verificar si el primer registro R22 tiene 4 espacios en las posiciones [2:6]. En el formato estándar AEB esas posiciones contienen la fecha de operación (dígitos), nunca espacios.

---

## 4. Parser C43 (`parser_c43.py`)

### Dataclass de resultado

```python
@dataclass
class MovimientoC43:
    fecha_operacion: date
    fecha_valor: date
    importe: Decimal           # siempre positivo
    signo: str                 # 'D' cargo | 'H' abono
    concepto_comun: str        # código AEB (2 dígitos): 02=abono, 03=adeudo, 06=nómina...
    concepto_propio: str       # texto libre (R22 concepto + R23 concatenados)
    referencia_1: str
    referencia_2: str
    num_orden: int             # posición en el archivo, para hash de deduplicación
```

### Bug CaixaBank resuelto: inferencia del signo

En el formato CaixaBank extendido, el campo `signo` del R22 siempre contiene `'0'` (cero) y no aporta información de dirección. El sentido del movimiento se deriva del campo `concepto_comun` mediante una tabla de códigos AEB:

```python
_CC_ABONO = frozenset({
    '01', '02', '05', '06', '08', '13', '14', '15', '19', '21',
})

def _signo_desde_concepto(concepto_comun: str) -> str:
    return 'H' if concepto_comun.strip().zfill(2) in _CC_ABONO else 'D'
```

Esto fue validado contra el archivo real `TT191225.208.txt` con 44 tests unitarios, incluyendo 7 casos específicos del formato CaixaBank.

### Función principal

```python
def parsear_c43(contenido: str) -> dict:
    # Devuelve:
    # {
    #     'banco_codigo': str,
    #     'iban': str,
    #     'saldo_inicial': Decimal,
    #     'saldo_final': Decimal,
    #     'divisa': str,  # "EUR"
    #     'movimientos': List[MovimientoC43],
    # }
```

La función detecta automáticamente si el contenido es formato estándar o CaixaBank y aplica el parser correspondiente.

---

## 5. Ingesta (`ingesta.py`)

### Función `ingestar_movimientos()` (para TXT)

```python
def ingestar_movimientos(
    contenido_c43: str,      # texto del extracto, encoding latin-1
    nombre_archivo: str,
    cuenta: CuentaBancaria,
    empresa_id: int,
    gestoria_id: int,
    session: Session,
) -> dict:
    # Devuelve:
    # {movimientos_totales, movimientos_nuevos, movimientos_duplicados, ya_procesado}
```

Calcula el SHA256 del contenido completo del archivo. Si el hash ya existe en la tabla `archivos_ingestados`, devuelve `ya_procesado=True` sin procesar nada.

### Función `ingestar_archivo_bytes()` (auto-detect)

```python
def ingestar_archivo_bytes(
    contenido_bytes: bytes,
    nombre_archivo: str,
    cuenta: CuentaBancaria,
    empresa_id: int,
    gestoria_id: int,
    session: Session,
) -> dict:
```

Detecta el formato por extensión:

| Extensión | Parser |
|-----------|--------|
| `.xls`, `.xlsx` | `parser_xls.parsear_xls()` |
| `.txt`, `.c43` (cualquier otra) | `parsear_c43()` con decode latin-1 |

### Idempotencia por SHA256

La deduplicación opera en dos niveles:

1. **Nivel archivo**: SHA256 del contenido completo se registra en la tabla `archivos_ingestados`. Si el archivo ya fue procesado, retorna sin insertar ningún movimiento.

2. **Nivel movimiento**: Para cada movimiento se calcula un hash determinista:

```python
def calcular_hash(iban, fecha, importe, referencia, num_orden) -> str:
    clave = f"{iban}|{fecha.isoformat()}|{importe}|{referencia}|{num_orden}"
    return hashlib.sha256(clave.encode()).hexdigest()
```

El campo `num_orden` (posición en el archivo) permite distinguir movimientos con importe, fecha y referencia idénticos en el mismo extracto.

---

## 6. Motor de Conciliación (`motor_conciliacion.py`)

### Clase de resultado

```python
@dataclass
class ResultadoMatch:
    movimiento_id: int
    asiento_id: int
    tipo: str       # 'exacto' | 'aproximado' | 'manual'
    diferencia: Decimal
    confianza: float    # 0.0 – 1.0
```

### Parámetros de matching

```python
class MotorConciliacion:
    VENTANA_DIAS: int = 2          # tolerancia de fecha (días)
    TOLERANCIA_PCT: float = 0.01   # 1% de diferencia para match aproximado
```

### Algoritmo en dos pasadas

La función `conciliar()` ejecuta el algoritmo en dos fases secuenciales para evitar que matches aproximados "consuman" asientos que podrían tener match exacto:

**Pasada 1 — Match exacto** (confianza = 1.0):
- Mismo importe en `Decimal` (comparación exacta)
- Fecha del movimiento dentro de ventana `±2 días` respecto al asiento
- Estado del movimiento: `pendiente`

**Pasada 2 — Match aproximado** (confianza = 1 - diferencia_porcentual):
- Solo para movimientos que no obtuvieron match exacto
- Diferencia de importe `<= 1%`
- Misma ventana de `±2 días`
- Se selecciona el asiento con mayor confianza si hay varios candidatos

Los asientos ya usados en la pasada 1 no están disponibles para la pasada 2 (`asientos_usados: set`).

### Resultado en BD

| Tipo match | Estado en `movimientos_bancarios.estado_conciliacion` |
|------------|-------------------------------------------------------|
| Exacto | `"conciliado"` |
| Aproximado | `"revision"` |
| Sin match | `"pendiente"` (sin cambios) |

El campo `asiento_id` en el movimiento se actualiza con el ID del asiento emparejado.

---

## 7. API bancaria (`sfce/api/rutas/bancario.py`)

Router con prefijo `/api/bancario`. Todos los endpoints verifican acceso a empresa mediante `verificar_acceso_empresa()`.

### Endpoints de cuentas

| Método | URL | Descripción |
|--------|-----|-------------|
| `POST` | `/api/bancario/{empresa_id}/cuentas` | Crea una cuenta bancaria. Valida IBAN único por empresa. |
| `GET` | `/api/bancario/{empresa_id}/cuentas` | Lista cuentas activas de la empresa. |

### Endpoints de ingesta

| Método | URL | Parámetros | Descripción |
|--------|-----|-----------|-------------|
| `POST` | `/api/bancario/{empresa_id}/ingestar` | `cuenta_iban` (query), `archivo` (multipart) | Ingesta extracto bancario. Auto-detecta formato por extensión. |

### Endpoints de movimientos

| Método | URL | Parámetros | Descripción |
|--------|-----|-----------|-------------|
| `GET` | `/api/bancario/{empresa_id}/movimientos` | `estado?`, `limit=100`, `offset=0` | Lista movimientos con paginación y filtro opcional por estado. |

### Endpoints de conciliación

| Método | URL | Descripción |
|--------|-----|-------------|
| `POST` | `/api/bancario/{empresa_id}/conciliar` | Ejecuta el motor de conciliación. Devuelve `{matches_exactos, matches_aproximados, total}`. |
| `GET` | `/api/bancario/{empresa_id}/estado_conciliacion` | KPIs: `{total, conciliados, pendientes, revision, pct_conciliado}`. |

### Schema de movimiento (respuesta)

```python
class MovimientoOut(BaseModel):
    id: int
    fecha: str
    importe: float
    signo: str                   # 'D' o 'H'
    concepto_propio: str
    nombre_contraparte: str
    tipo_clasificado: Optional[str]   # TPV | PROVEEDOR | NOMINA | IMPUESTO | COMISION | OTRO
    estado_conciliacion: str          # pendiente | conciliado | revision
    asiento_id: Optional[int]
```

---

## 8. Diagrama de flujo

```mermaid
flowchart TD
    A[Archivo bancario .txt/.c43/.xls] --> B{Auto-detect formato}
    B -->|.xls/.xlsx| C[parser_xls.parsear_xls]
    B -->|.txt/.c43| D{¿Es CaixaBank?}
    D -->|linea[2:6]==' '| E[Parser CaixaBank extendido\nSigno desde concepto_comun]
    D -->|Estándar AEB| F[Parser Norma 43 estándar]
    E --> G[Lista MovimientoC43]
    F --> G
    C --> G
    G --> H{Hash archivo\nen archivos_ingestados?}
    H -->|Sí| I[ya_procesado=True\nSin cambios]
    H -->|No| J[Calcular hash por movimiento]
    J --> K{Hash movimiento\nexiste?}
    K -->|Sí| L[movimientos_duplicados++]
    K -->|No| M[INSERT MovimientoBancario\nestado=pendiente]
    M --> N[Clasificar tipo:\nTPV/PROVEEDOR/NOMINA/...]
    N --> O[Guardar en BD]
    O --> P[MotorConciliacion.conciliar]
    P --> Q[Pasada 1: Match exacto\nimporte exacto + ±2 días]
    Q --> R[Pasada 2: Match aproximado\n≤1% diferencia + ±2 días]
    R --> S{Tipo match}
    S -->|exacto| T[estado=conciliado\nconfianza=1.0]
    S -->|aproximado| U[estado=revision\nconfianza=1-diff_pct]
    S -->|sin match| V[estado=pendiente\nsin cambios]
```

---

## 9. Tablas de BD

| Tabla | Descripción |
|-------|-------------|
| `cuentas_bancarias` | Cuentas registradas por empresa: banco_codigo, banco_nombre, iban, alias, divisa, email_c43, activa |
| `movimientos_bancarios` | Movimientos ingestados: fecha, importe, signo, concepto_propio, nombre_contraparte, tipo_clasificado, estado_conciliacion, asiento_id |
| `archivos_ingestados` | Registro de archivos ya procesados (hash SHA256 del contenido completo) |

---

## 10. Notas de operación

- El mismo archivo puede subirse múltiples veces sin crear duplicados (idempotencia total).
- La conciliación es incremental: solo procesa movimientos en estado `pendiente`.
- Los matches aproximados quedan en estado `revision` para revisión manual desde el dashboard.
- El campo `email_c43` en `CuentaBancaria` es opcional: permite configurar futura ingesta automática por correo (módulo correo, ver tema 20).
