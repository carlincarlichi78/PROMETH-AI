# Sistema de Fiabilidad Contable Evolutivo (SFCE)

**Fecha**: 2026-02-26
**Estado**: Aprobado
**Alcance**: Global (todos los clientes en CONTABILIDAD/)

## Objetivo

Sistema end-to-end que garantiza integridad contable desde que un PDF cae en inbox/ hasta que el asiento queda perfecto en FacturaScripts. Zero tolerancia al error, con verificaciones multicapa que se refuerzan con el tiempo.

## Decisiones de diseno

| Decision | Eleccion |
|----------|----------|
| Automatizacion | Totalmente automatico (solo alerta en errores nuevos) |
| Config por cliente | Archivo YAML en carpeta de cada cliente |
| Errores nuevos | Bloquear + alertar + registrar |
| Trigger | Comando unico por lote (`pipeline.py`) |
| Extraccion datos | Dual: pdfplumber (texto) + GPT-4o (parsing) |
| Informes | Consola + pestana AUDITORIA en Excel + .log |
| Arquitectura | Pipeline secuencial con 7 fases + Quality Gates |

## Arquitectura de archivos

```
CONTABILIDAD/
  scripts/
    pipeline.py                  # Orquestador principal
    onboarding.py                # Alta interactiva de clientes nuevos
    phases/                      # Modulos por fase
      __init__.py
      intake.py                  # Fase 0: Extraccion de datos
      pre_validation.py          # Fase 1: Validacion pre-FS
      registration.py            # Fase 2: Registro en FS
      asientos.py                # Fase 3: Generacion de asientos
      correction.py              # Fase 4: Correccion automatica
      cross_validation.py        # Fase 5: Verificacion cruzada
      output.py                  # Fase 6: Generacion de salidas
    core/                        # Utilidades compartidas
      __init__.py
      fs_api.py                  # Cliente API FacturaScripts
      config.py                  # Carga y valida config.yaml
      confidence.py              # Sistema de puntuacion de confianza
      errors.py                  # Catalogo de errores + registro
      logger.py                  # Logging unificado
    crear_libros_contables.py    # Existente (se refactoriza parcialmente)
    validar_asientos.py          # Existente (logica se integra en fase 4-5)
    resumen_fiscal.py            # Existente (sin cambios)
    generar_modelos_fiscales.py  # Existente (se integra en fase 6)
    renombrar_documentos.py      # Existente (logica se integra en fase 0 y 6)
  reglas/                        # Reglas globales (YAML)
    validaciones.yaml            # Reglas de validacion para todos los clientes
    errores_conocidos.yaml       # Catalogo evolutivo de errores
    tipos_entidad.yaml           # Obligaciones por tipo (SL, autonomo, comunidad, asociacion, etc.)
  clientes/
    {cliente}/
      config.yaml                # Configuracion del cliente
      pipeline_state.json        # Estado de ultima ejecucion
      inbox/                     # Entrada de documentos
      cuarentena/                # Documentos bloqueados
      {ano}/
        auditoria/               # Logs de auditoria
        procesado/               # Documentos procesados
```

## Config por cliente (config.yaml)

```yaml
empresa:
  nombre: "NOMBRE EMPRESA"
  cif: "B12345678"
  tipo: sl                    # sl | autonomo
  idempresa: 1
  ejercicio_activo: "2025"
  regimen_iva: general
  actividades:
    - codigo: "4631"
      iva_venta: 4            # IVA aplicable a ventas

proveedores:
  NOMBRE_CORTO:
    cif: "B12345678"
    nombre_fs: "Nombre en FacturaScripts"
    aliases: ["alias1", "alias2"]     # Para matching OCR
    pais: ESP                         # ISO alpha-3
    divisa: EUR
    subcuenta: "6000000000"
    codimpuesto: IVA21
    regimen: general                  # general | intracomunitario | extracomunitario
    autoliquidacion:                  # Solo si regimen == intracomunitario
      iva: 21
      subcuenta_soportado: "4720000021"
      subcuenta_repercutido: "4770000021"
    pendiente_fiscal: false           # true = bloquea auto-fix
    reglas_especiales:
      - tipo: iva_extranjero
        patron_linea: "IVA ADUANA"
        subcuenta_correcta: "4709000000"
        descripcion: "IVA PT no deducible"

clientes:
  NOMBRE_CORTO:
    cif: "B12345678"
    nombre_fs: "Nombre en FacturaScripts"
    pais: ESP
    divisa: EUR
    codimpuesto: IVA4
    regimen: general

tipos_cambio:
  USD_EUR: 1.1775
  fecha_tc: "2025-02-25"

tolerancias:
  cuadre_asiento: 0.01        # EUR
  comparacion_importes: 0.02  # EUR
  confianza_minima: 85        # % para aceptar extraccion
```

## Triple verificacion contra FacturaScripts

### Verificacion 1: PRE-FS
"Los datos que VAMOS A ENVIAR a FS son correctos?"

- CIF conocido en config.yaml
- Divisa correcta para el proveedor
- IVA correcto segun regimen
- Base + IVA = Total (tolerancia +/-0.02)
- Fecha dentro del ejercicio
- No es duplicado (hash + numero factura)
- No existe ya en FS (consulta API)

GATE: Solo si todo OK se envia a FS.

### Verificacion 2: POST-REGISTRO
"FS ALMACENO lo que le enviamos?"

Despues de crear cada factura:
- GET factura de vuelta
- Comparar campo por campo: neto, totaliva, total, coddivisa, tasaconv, codimpuesto por linea, pagada, codproveedor/codcliente
- Si alguno no coincide: BLOQUEA + alerta

### Verificacion 3: POST-ASIENTO (la mas critica)
"FS GENERO el asiento contable CORRECTO?"

Para cada asiento generado:

A. **Cuadre**: sum(DEBE) == sum(HABER) (tolerancia +/-0.01)
B. **Importes EUR**: Si factura USD, partidas deben estar en EUR. AUTO-FIX si no.
C. **Subcuentas**: Cada partida usa subcuenta esperada segun config.yaml
D. **Notas credito**: Si serie R, DEBE/HABER invertidos. AUTO-FIX si no.
E. **Intracomunitarias**: Si proveedor intracom con autoliquidacion, partidas 472/477 presentes. AUTO-FIX si faltan.
F. **Reglas especiales**: IVA PT a 4709, etc. AUTO-FIX segun config.
G. **Pendiente fiscal**: Si marcado, solo AVISO (no auto-fix).

### Verificacion Final: CRUCE GLOBAL
"TODO cuadra entre si?"

- Num facturas == Num asientos
- Total facturas por subcuenta == saldo subcuenta
- IVA repercutido facturas == subcuenta 477
- IVA soportado facturas == subcuenta 472
- Autoliquidacion 472 == autoliquidacion 477
- Total gastos == 600 neto + 4709
- Total ingresos == 700
- 303 calculado == 303 desde subcuentas

## Las 7 fases

### Fase 0: INTAKE (Extraccion)
Entrada: inbox/ con PDFs
Salida: intake_results.json

1. Escanear inbox/ (listar PDFs no procesados)
2. Hash SHA256 por PDF (deduplicacion)
3. Por cada PDF:
   a. pdfplumber: extraer texto raw
   b. Si hay texto: GPT-4o parsea texto en JSON estructurado
   c. Si no hay texto (escaneado): GPT-4o Vision sobre imagen
   d. Identificar proveedor/cliente por CIF (contra config.yaml)
   e. Clasificar tipo: FC, FV, NC, ANT, etc.
   f. Calcular confianza por campo
4. Guardar intake_results.json

Gate 1: Todos los CIFs identificados, confianza >= 85% en campos criticos. PDF que falla va a cuarentena/.

### Fase 1: VALIDACION PRE-FS
Entrada: intake_results.json
Salida: validated_batch.json

Validaciones:
- CIF/NIF formato valido
- Proveedor/cliente en config.yaml
- Divisa esperada
- IVA esperado segun regimen
- Fecha en ejercicio activo
- Importe > 0 (NC negativo OK)
- Base + IVA = Total
- No duplicado (hash + numero factura + proveedor)
- No existe ya en FS

Gate 2: 100% documentos pasan. Los que fallan se excluyen + registro.

### Fase 2: REGISTRO EN FS
Entrada: validated_batch.json
Salida: registered.json

Por factura:
1. Construir form-data (codimpuesto, coddivisa, tasaconv, lineas como json.dumps)
2. POST a crearFacturaProveedor/crearFacturaCliente
3. GET factura creada -> Verificacion 2
4. PUT pagada=1
5. GET pagada -> verificar

Gate 3: Todas las facturas creadas y verificadas. Si falla: DELETE + alerta.

### Fase 3: GENERACION DE ASIENTOS
Entrada: registered.json
Salida: asientos_generados.json

1. Generar asientos via API (si disponible) o flag para generacion manual
2. Verificar que cada factura tiene su asiento
3. Obtener todas las partidas

Gate 4: Num asientos == Num facturas.

### Fase 4: CORRECCION AUTOMATICA
Entrada: asientos_generados.json + config.yaml
Salida: asientos_corregidos.json

Verificacion 3 completa:
1. Cuadre DEBE == HABER
2. Importes en EUR (auto-fix USD)
3. NC serie R invertir (auto-fix)
4. Intracomunitarias 472/477 (auto-fix)
5. Reglas especiales por proveedor (auto-fix)
6. Subcuenta correcta
7. Importe asiento == importe factura en EUR

Cada correccion: registra en log + verifica con GET + alimenta catalogo errores.

Gate 5: Todos los asientos pasan todas las validaciones.

### Fase 5: VERIFICACION CRUZADA
Entrada: Todo lo anterior + API FS completa
Salida: cross_validation_report.json

Cruces:
1. Total facturas proveedor == subcuenta 600 neto + 4709
2. Total facturas cliente == subcuenta 700
3. IVA repercutido == subcuenta 477
4. IVA soportado == subcuenta 472
5. Autoliquidacion 472 == autoliquidacion 477
6. Num facturas == num asientos
7. Libro diario cuadra globalmente
8. 303 calculado == 303 desde subcuentas
9. Balance: Activo == Pasivo + PN

Gate 6: Todos los cruces OK (tolerancia +/-0.01).

### Fase 6: GENERACION DE SALIDAS
Entrada: Datos validados
Salida: Excel + .txt + .log + PDFs movidos

1. Excel libros contables (10 pestanas + AUDITORIA)
2. Archivos .txt modelos fiscales
3. Mover PDFs de inbox/ a procesado/{trimestre}/{tipo}/
4. Renombrar PDFs con convencion estandar
5. Informe auditoria (.log + pestana Excel)
6. Actualizar pipeline_state.json

Gate 7: Excel generado, PDFs movidos, score >= 95%.

## Sistema de confianza

Cada dato extraido recibe puntuacion (0-100%):
- pdfplumber extrae texto correctamente: +40
- GPT-4o parsea correctamente: +30
- Coincide con FS API (si existe): +20
- Pasa validacion config: +10

Umbrales por campo:
| Campo | Umbral minimo |
|-------|--------------|
| CIF | 90% |
| Importe | 85% |
| Fecha | 85% |
| Numero factura | 80% |
| Tipo IVA | 90% (deterministico desde config) |
| Divisa | 95% (deterministico desde config) |

Niveles resultado:
- FIABLE (95-100%): Verificado por multiples fuentes
- ACEPTABLE (85-94%): Verificado con alguna fuente faltante
- NO FIABLE (<85%): Discrepancias, BLOQUEADO

## Mecanismo de evolucion

### Catalogo de errores (reglas/errores_conocidos.yaml)
Cada error nuevo se registra con:
- Condicion de deteccion
- Accion de correccion (si es auto-fixable)
- Verificacion post-correccion
- Contador de ocurrencias

Flujo: Error nuevo detectado -> BLOQUEA -> se resuelve manualmente -> solucion se codifica como regla -> proxima vez se auto-corrige.

### Historial de confianza por proveedor
Se acumula en pipeline_state.json:
- Ejecuciones totales
- Confianza media
- Errores detectados y auto-corregidos
- Proveedores nuevos reciben escrutinio extra

### Reglas de validacion globales (reglas/validaciones.yaml)
Reglas en YAML que aplican a todos los clientes:
- Validaciones pre-FS (formato CIF, fechas, importes)
- Validaciones post-asiento (cuadre, subcuentas, ejercicio)
- Validaciones cruce (facturas vs subcuentas, 303, balance)

Nuevas reglas se anaden al YAML sin cambiar codigo.

### Score de fiabilidad global
Despues de cada ejecucion:
- Score = weighted_average(extraccion, registro, asientos, cruce)
- Se compara con ejecuciones anteriores
- Tendencia: mejora o empeora
- Si empeora -> alerta para investigar

## Ejecucion

Comando unico:
```
python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025
```

Opciones:
- `--dry-run`: simula sin modificar FS
- `--resume`: continua desde la ultima fase completada
- `--fase N`: ejecuta solo la fase N
- `--verbose`: detalle completo en consola
- `--force`: ignora quality gates (no recomendado)

Archivos .bat por cliente:
```
pipeline.bat   # Ejecucion normal (todas las fases)
```

## Dependencias Python

Nuevas:
- pdfplumber: extraccion de texto de PDFs
- openai: GPT-4o para parsing de texto/imagenes
- pyyaml: lectura de config.yaml y reglas

Existentes (ya usadas):
- requests: API FS
- openpyxl: generacion Excel
- json, hashlib, os, logging: stdlib

## Compatibilidad con scripts existentes

- `crear_libros_contables.py`: su logica de generacion Excel se reutiliza en fase 6
- `validar_asientos.py`: sus 5 validaciones se integran en fase 4
- `resumen_fiscal.py`: sin cambios, se puede ejecutar independientemente
- `generar_modelos_fiscales.py`: se integra en fase 6
- `renombrar_documentos.py`: su logica de renombrado se integra en fase 6

Los scripts existentes siguen funcionando de forma independiente para uso ad-hoc.
