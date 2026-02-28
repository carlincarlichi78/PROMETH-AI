# Modelos Fiscales Completos — Design Doc

**Fecha**: 2026-02-27
**Estado**: Aprobado
**Objetivo**: Sistema completo de generacion de ~28 modelos fiscales oficiales AEAT con fichero BOE, PDF visual y presentacion desde dashboard SFCE.

## Contexto

### Estado actual
- FS tiene plugins para 303, 390, 111, 190, 130, 347 (generacion manual via web)
- `calculador_modelos.py` calcula 9 modelos programaticamente (output: dict casillas)
- `generar_modelos_fiscales.py` genera .txt plano (no formato BOE oficial)
- No hay generacion de ficheros importables en Sede Electronica AEAT
- No hay PDF visual de los modelos

### Problema
El gestor necesita generar TODOS los modelos fiscales oficiales en formato importable por la AEAT, con PDF para revision y archivo. FS cubre solo 6 modelos y requiere interaccion manual.

### Decision
Dashboard SFCE como interfaz principal del gestor. FS queda como motor contable (registro facturas/asientos). Los modelos se generan desde SFCE usando datos de la BD local.

## Arquitectura

```
                    Dashboard SFCE (React)
                    /modelos-fiscales/*
                         |
                    +---------+
                    | FastAPI  |
                    | /api/modelos/
                    +---------+
                         |
              +----------+-----------+
              |          |           |
    CalculadorModelos  MotorBOE  GeneradorPDF
    (casillas)         (fichero)  (visual)
              |          |           |
              +----------+-----------+
                         |
                  +------+------+
                  |  BD Local   | <-- datos contables
                  |  (SQLite)   |
                  +-------------+
```

### 3 capas independientes

1. **CalculadorModelos** (expandir existente): datos contables -> dict de casillas `{casilla_01: 15234.50, ...}`
2. **MotorBOE** (nuevo): casillas + especificacion YAML -> fichero posicional .txt/.dat formato AEAT
3. **GeneradorPDF** (nuevo): casillas + PDF oficial rellenable -> PDF visual del modelo

Cada capa es independiente y testeable por separado.

## Catalogo de modelos (~28)

### IVA (6 modelos)
| Modelo | Nombre | Periodo | Obligados |
|--------|--------|---------|-----------|
| 303 | Autoliquidacion IVA | Trimestral | Todos |
| 390 | Resumen anual IVA | Anual | Todos |
| 349 | Operaciones intracomunitarias | Trimestral/Anual | Con ops. intra-UE |
| 347 | Ops. con terceros >3.005,06 EUR | Anual | Todos |
| 340 | Libros registro (SII) | Mensual | Gran empresa |
| 420 | IGIC Canarias | Trimestral | Canarias |

### IRPF / Retenciones (8 modelos)
| Modelo | Nombre | Periodo | Obligados |
|--------|--------|---------|-----------|
| 111 | Retenciones trabajo/profesional | Trimestral | Con empleados/prof. |
| 190 | Resumen anual retenciones | Anual | Con empleados/prof. |
| 115 | Retenciones alquileres | Trimestral | Con alquileres |
| 180 | Resumen anual alquileres | Anual | Con alquileres |
| 123 | Retenciones capital mobiliario | Trimestral | Con dividendos/intereses |
| 193 | Resumen anual capital mobiliario | Anual | Con dividendos/intereses |
| 130 | Pago fraccionado IRPF (directa) | Trimestral | Autonomos directa |
| 131 | Pago fraccionado IRPF (modulos) | Trimestral | Autonomos modulos |

### Sociedades (3 modelos)
| Modelo | Nombre | Periodo | Obligados |
|--------|--------|---------|-----------|
| 200 | Impuesto Sociedades | Anual | S.L./S.A. |
| 202 | Pagos fraccionados IS | Trimestral | S.L. (>gran empresa) |
| 220 | IS consolidado | Anual | Grupos |

### IRPF persona fisica (1 modelo)
| Modelo | Nombre | Periodo | Obligados |
|--------|--------|---------|-----------|
| 100 | Renta (datos negocio) | Anual | Autonomos |

### Censal (2 modelos)
| Modelo | Nombre | Periodo | Obligados |
|--------|--------|---------|-----------|
| 036 | Censo empresarios (completo) | Al alta/cambios | S.L./S.A. |
| 037 | Censo simplificado | Al alta/cambios | Autonomos |

### No residentes (4 modelos)
| Modelo | Nombre | Periodo | Obligados |
|--------|--------|---------|-----------|
| 210 | IRNR sin EP | Trimestral | No residentes |
| 211 | Retencion inmuebles no resid. | Cada operacion | Compradores |
| 216 | Retenciones no residentes | Trimestral | Con pagos a no resid. |
| 296 | Resumen anual no residentes | Anual | Con pagos a no resid. |

### Otros (4 modelos)
| Modelo | Nombre | Periodo | Obligados |
|--------|--------|---------|-----------|
| 184 | Entidades regimen atribucion | Anual | CB, SC, comunidades |
| 345 | Planes de pensiones | Anual | Con planes |
| 720 | Bienes en extranjero | Anual | >50K EUR extranjero |
| 360 | Devolucion IVA extranjero | Anual | Casos especiales |

### Prioridad implementacion
1. **Core IVA+IRPF** (14 modelos): 303, 390, 349, 347, 111, 190, 115, 180, 123, 193, 130, 131, 420, 340
2. **Sociedades+Censal** (5 modelos): 200, 202, 220, 036, 037
3. **Resto** (9 modelos): 100, 210, 211, 216, 296, 184, 345, 720, 360

## MotorBOE — Especificacion YAML por modelo

Cada modelo tiene un YAML con su diseno de registro posicional (fuente: Excel oficial AEAT).

### Estructura del YAML

```yaml
# sfce/modelos_fiscales/disenos/303.yaml
modelo: "303"
version: "2025"
tipo_formato: "posicional"  # o "xml" para modelo 200
longitud_registro: 500

registros:
  - tipo: "cabecera"
    campos:
      - nombre: "tipo_registro"
        posicion: [1, 1]
        tipo: "alfanumerico"
        valor_fijo: "1"
      - nombre: "modelo"
        posicion: [2, 4]
        tipo: "numerico"
        valor_fijo: "303"
      - nombre: "ejercicio"
        posicion: [5, 8]
        tipo: "numerico"
        fuente: "ejercicio"
      - nombre: "nif"
        posicion: [9, 17]
        tipo: "alfanumerico"
        fuente: "nif_declarante"

  - tipo: "detalle"
    campos:
      - nombre: "casilla_01"
        posicion: [68, 85]
        tipo: "numerico_signo"
        decimales: 2
        fuente: "casillas.01"
        descripcion: "Base imponible tipo general"
      - nombre: "casilla_03"
        posicion: [86, 103]
        tipo: "numerico_signo"
        decimales: 2
        fuente: "casillas.03"
        descripcion: "Cuota tipo general"

validaciones:
  - regla: "casilla_27 == casilla_01 + casilla_03 + casilla_05"
    nivel: "error"
    mensaje: "IVA devengado no cuadra con bases"
  - regla: "casilla_45 == casilla_27 - casilla_37"
    nivel: "error"
    mensaje: "Resultado no cuadra con devengado - soportado"
```

### Tipos de campo soportados
- `alfanumerico`: relleno con espacios a la derecha
- `numerico`: relleno con ceros a la izquierda
- `numerico_signo`: primer caracter N (negativo) o espacio (positivo), resto numerico
- `fecha`: formato YYYYMMDD o DDMMYYYY segun modelo
- `telefono`: 9 digitos
- `valor_fijo`: valor constante en el fichero

### Fuentes de datos
- `"ejercicio"`, `"nif_declarante"`, `"periodo"`: metadatos de la declaracion
- `"casillas.XX"`: casilla calculada por CalculadorModelos
- `"empresa.nombre"`, `"empresa.direccion"`: datos de la BD

### Motor generico (pseudo-codigo)

```python
class MotorBOE:
    def generar(self, modelo: str, ejercicio: str, periodo: str,
                casillas: dict, empresa: dict) -> str:
        diseno = cargar_yaml(f"disenos/{modelo}.yaml")
        validar_casillas(casillas, diseno.validaciones)
        lineas = []
        for registro in diseno.registros:
            linea = " " * diseno.longitud_registro
            for campo in registro.campos:
                valor = resolver_fuente(campo, casillas, empresa)
                linea = insertar_campo(linea, campo, valor)
            lineas.append(linea)
        return "\n".join(lineas)
```

### Modelos con formato XML
Modelo 200 (IS) usa formato XML con esquema XSD. Para estos:
- El YAML define la estructura XML en vez de posiciones
- El motor genera XML validado contra XSD oficial
- Misma interfaz: `generar(modelo, ejercicio, periodo, casillas, empresa) -> str`

## GeneradorPDF

### Estrategia dual

1. **PDF rellenable** (primario): los modelos AEAT tienen PDFs con campos de formulario. Usar `pdfrw` o `PyPDF2` para rellenar campos automaticamente.
   - Descarga unica del PDF template desde AEAT
   - Almacenar en `sfce/modelos_fiscales/plantillas_pdf/303.pdf`
   - Mapeo campo_pdf -> casilla en YAML

2. **HTML -> PDF** (fallback): para modelos sin PDF rellenable, generar HTML con WeasyPrint.
   - Plantilla Jinja2 por modelo
   - Ya existe infraestructura WeasyPrint en el proyecto

### Output
- PDF nombrado: `{NIF}_{ejercicio}_{periodo}.{modelo}.pdf` (ej: `B12345678_2025_1T.303.pdf`)
- Almacenar en: `clientes/{cliente}/{ejercicio}/modelos_fiscales/`

## Integracion Dashboard

### Nuevas paginas React

```
/modelos-fiscales/
  +-- CalendarioFiscal     (vista trimestral con plazos y estados)
  +-- GenerarModelo        (selector modelo + periodo + preview casillas)
  +-- DetalleModelo        (casillas editables + validacion + descarga)
  +-- HistoricoModelos     (modelos generados anteriormente)
```

### Flujo del gestor
1. Entra al calendario fiscal -> ve modelos pendientes este trimestre
2. Click "Generar 303 T1 2026"
3. Sistema calcula casillas automaticamente desde datos contables
4. Gestor revisa casillas, puede editar manualmente si necesita ajustar
5. Click "Validar" -> sistema ejecuta validaciones AEAT
6. Click "Descargar BOE" -> fichero .txt importable en Sede Electronica
7. Click "Descargar PDF" -> PDF visual para archivo
8. Estado cambia a "Generado" en el calendario

### API endpoints nuevos

```
POST   /api/modelos/{modelo}/calcular     -> calcula casillas
POST   /api/modelos/{modelo}/validar      -> valida casillas
POST   /api/modelos/{modelo}/generar-boe  -> genera fichero BOE
POST   /api/modelos/{modelo}/generar-pdf  -> genera PDF visual
GET    /api/modelos/calendario/{ejercicio} -> calendario fiscal
GET    /api/modelos/historico/{empresa_id} -> modelos generados
```

## Actualizacion anual

Cada ejercicio la AEAT puede modificar disenos de registro.

### Proceso
1. AEAT publica nuevos Excel en [Disenos de registro](https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro.html)
2. Script conversor: `python scripts/actualizar_disenos.py --ejercicio 2027`
3. Parsea Excel AEAT -> genera YAMLs actualizados con version nueva
4. Tests automaticos comparan con version anterior y reportan cambios
5. Commit + deploy

### Versionado
- `sfce/modelos_fiscales/disenos/303.yaml` tiene campo `version: "2025"`
- Si AEAT cambia formato para 2026, se actualiza el YAML
- Historico: modelos generados con version anterior siguen siendo validos

## Estructura de archivos

```
sfce/modelos_fiscales/
  +-- __init__.py
  +-- motor_boe.py          # Motor generico BOE (posicional + XML)
  +-- generador_pdf.py       # Rellenado PDF + fallback HTML
  +-- validador.py            # Validaciones AEAT por modelo
  +-- calculadores/
  |     +-- __init__.py
  |     +-- iva.py            # 303, 390, 349, 347, 340, 420
  |     +-- retenciones.py    # 111, 190, 115, 180, 123, 193
  |     +-- irpf.py           # 130, 131, 100
  |     +-- sociedades.py     # 200, 202, 220
  |     +-- censal.py         # 036, 037
  |     +-- no_residentes.py  # 210, 211, 216, 296
  |     +-- otros.py          # 184, 345, 720, 360
  +-- disenos/                # YAMLs con disenos de registro
  |     +-- 303.yaml
  |     +-- 390.yaml
  |     +-- ... (28 YAMLs)
  +-- plantillas_pdf/         # PDFs oficiales AEAT rellenables
  |     +-- 303.pdf
  |     +-- ...
  +-- plantillas_html/        # Fallback Jinja2 para modelos sin PDF
        +-- base_modelo.html
        +-- ...
```

## Dependencias nuevas
- `pdfrw` o `PyPDF2`: rellenar PDFs formulario
- `openpyxl`: parsear Excel disenos de registro AEAT (ya en proyecto)
- `lxml`: generar XML para modelo 200 (opcional, ya disponible)
- WeasyPrint: ya instalado (fallback HTML->PDF)

## Testing
- Unit tests por calculador (casillas correctas)
- Unit tests MotorBOE (formato posicional correcto, longitudes, tipos)
- Unit tests validador (reglas AEAT)
- Integration tests: datos BD -> casillas -> fichero BOE -> reimportar y verificar
- Test golden files: ficheros BOE de referencia comparados byte a byte

## Fase futura: Presentacion telematica
- API SOAP AEAT para envio directo con certificado digital
- Requiere firma electronica (.pfx/.p12)
- Investigar en fase posterior, no bloquea el diseño actual
- El MotorBOE genera el mismo contenido que se enviaria por API
