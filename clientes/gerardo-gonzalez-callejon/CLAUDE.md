# IMPORTANTE: Leer siempre primero ../../CLAUDE.md (infraestructura y contexto general)

# GERARDO GONZALEZ CALLEJON

## Datos personales
- **Nombre**: Gerardo Gonzalez Callejon
- **NIF**: 76638663H
- **Tipo**: Autonomo (persona fisica)
- **Direccion**: Travesia Andalucia Local 3, Marbella (Malaga)
- **Telefono**: 691110966
- **Email**: PENDIENTE

## Actividades economicas
1. **Podologia** — actividad sanitaria, clinica propia
2. **Estetica** — actividad complementaria en el mismo local

## Regimen fiscal
- Estimacion directa (simplificada o normal — PENDIENTE confirmar)
- **Podologia**: exenta de IVA (Art. 20.1.3 LIVA — asistencia sanitaria)
- **Estetica**: sujeta a IVA 21% (no es asistencia sanitaria a efectos fiscales)
- Prorrata o sectores diferenciados por tener actividad exenta + no exenta

## Obligaciones fiscales

### Trimestrales
- **Modelo 303**: IVA (solo por actividad de estetica; podologia exenta)
- **Modelo 130**: Pago fraccionado IRPF (autonomo en estimacion directa)
- **Modelo 111**: Retenciones IRPF (tiene empleados en ambas actividades)

### Anuales
- **Modelo 390**: Resumen anual IVA
- **Modelo 100**: IRPF (declaracion anual — se presenta con la renta)
- **Modelo 347**: Operaciones con terceros >3.005,06 EUR (febrero)

## Empleados
- **Podologia**: varios empleados (plantilla estable)
- **Estetica**: 1-2 empleados (variable segun temporada)

## Particularidades
- Dos actividades con tratamiento de IVA diferente (exenta + sujeta)
- Debe llevar contabilidad separada o prorrata de sectores diferenciados
- Gastos comunes (local, suministros) se reparten entre ambas actividades
- Retenciones del 15% en facturas a empresas/profesionales (7% si es nuevo autonomo)
- Modelo 111 confirmado: tiene nominas con retenciones IRPF

## Criterio de clasificacion de facturas
- La clasificacion es **por factura**, no por proveedor
- Un mismo proveedor puede facturar a podologia, estetica o ambas
- Categorias de imputacion: podologia / estetica / compartido
- Gastos compartidos (alquiler, luz, agua, internet): reparto segun criterio de 2024
- El catalogo de proveedores se construira a partir de la contabilidad de 2024 del gestor
- Para proveedores ambiguos, el usuario indica a que actividad va cada factura

## Plan de trabajo
1. Recibir documentacion 2024 del gestor anterior
2. Extraer catalogo de proveedores/clientes con patron habitual de cada uno
3. Dar de alta proveedores y clientes en FacturaScripts
4. Registrar contabilidad 2025 replicando criterios del gestor
5. Comparar trimestralmente con la contabilidad del gestor para validar

## Estructura de carpetas
```
inbox/                          ← el usuario tira todo aqui
2024/                           ← documentacion del gestor (referencia)
2025/
├── libros_contables_2025.xlsx  ← Excel con 7 pestanas (libros obligatorios)
└── procesado/T1-T4/            ← podologia/estetica/compartido/nominas/banco
```

## Workflow de procesamiento
1. Usuario mete documentos en inbox/
2. Claude lee inbox/, identifica y clasifica cada documento
3. Registra en FacturaScripts (facturas via API, asientos directos para gastos sin factura)
4. Actualiza libros_contables_2025.xlsx
5. Mueve documentos procesados a 2025/procesado/TX/actividad/tipo/
6. Si algo es ambiguo, pregunta al usuario

## Libros contables (pestanas del Excel)
1. Ingresos — facturas emitidas
2. Gastos — facturas recibidas + gastos sin factura
3. Bienes Inversion — activos amortizables
4. Registro Fact. Emitidas — libro IVA (desglose por tipos)
5. Registro Fact. Recibidas — libro IVA soportado
6. Resumen Trimestral — totales por trimestre/actividad (para modelos 303/130/111)
7. Conciliacion Bancaria — extracto vs facturas

## Estado en FacturaScripts
- Empresa creada (codigo 2, nombre corto G. GONZALEZ)
- Tipo: Persona fisica, NIF 76638663H
- Ejercicio 2025 creado (codejercicio=0002, 01/01/2025 - 31/12/2025, estado Abierto)
- Plan contable PGC espanol importado (802 cuentas, 721 subcuentas)
- Regimen general de IVA

## SFCE Pipeline - Estado
- config.yaml completo: 17 proveedores, codejercicio 0002, empleados true
- intake.py adaptado: rglob recursivo para subcarpetas, filtro CARPETA REFERENCIA
- **Dry-run**: 126/127 validados (BAN:71, FC:28, SUM:17, RLC:10, IMP:1)
- **Ultimo pipeline (sesion 27/02)**: 119/126 OK (94%), 7 fallidos — PERO FS VACIO (sesion perdio contexto)
- **Estado actual FS**: VACIO (0 facturas, 0 asientos para empresa 2)
- **Archivos conservados**: intake_results.json (127 docs OCR), validated_batch.json (126 validados)
- **pipeline_state**: fases=[intake, pre_validacion] — listo para --resume desde REGISTRO
- **NO repetir OCR**: intake y pre_validacion ya hechos, conservados en disco

### Comando para retomar (COPIAR Y EJECUTAR)
```bash
cd /c/Users/carli/PROYECTOS/CONTABILIDAD
export FS_API_TOKEN='iOXmrA1Bbn8RDWXLv91L'
export MISTRAL_API_KEY='yATzL24fWGoXtzfFutkvMQm3ZONwYZuk'
export GEMINI_API_KEY='AIzaSyCsKoDsjZ9kYVONe21Kx1Y47UbZb8sEGWY'
export OPENAI_API_KEY=$(grep OPENAI_API_KEY /c/Users/carli/PROYECTOS/AUTOMATIZACION_FACTURAS/.env | cut -d'"' -f2)
python scripts/pipeline.py --cliente gerardo-gonzalez-callejon --ejercicio 2025 --resume --force --no-interactivo
```

### 7 docs fallidos (ultimo pipeline 119/126)
1. **Google/Meta FC rollback** (4): IVA intracomunitario — OCR extrae total sin IVA, FS aplica 21% extra
2. **Internet SUM** (1): Total OCR=46.10 vs FS=55.78 (discrepancia base)
3. **SkinClinic FC** (1): CIF vacio en config, entidad no encontrada
4. **Asesoria Laboral Dec** (1): Total OCR=72.60, FS=0.00

### Bugs corregidos (commits 51d46fe + 03e91d5)
- SUM incluido en `es_proveedor` en TODAS las funciones de registration.py (8 ocurrencias total)
- Busqueda entidad: fallback a entidad_cif + buscar_proveedor_por_nombre
- Asiento directo fallido no cae al path facturas
- Nuevos subtipos BAN: transferencia, impuesto_tasa, tasa, cuota

## Ingresos (del Libro bienes de ingresos - NO registrados en FS)
- Podologia (exenta IVA): T1=18,646.68 T2=22,641.68 T3=28,830.00 T4=29,629.50 Total=99,747.86
- Estetica (IVA 21%): T1=6,327.59 T2=5,387.04 T3=3,374.38 T4=12,208.40 Total=27,297.41
- IVA repercutido estetica: T1=1,328.79 T2=1,131.28 T3=708.62 T4=1,884.32 Total=5,053.01

## Bienes de inversion
- 25 items, amortizacion 2025 = 8,229.94 EUR
- Items 1-16, 23-25: Podologia | Items 17-22: Estetica

## Proximos pasos (por prioridad)
1. **Ejecutar pipeline --resume** (comando arriba): salta OCR, va directo a REGISTRO (~3-5 min)
2. **Resolver 7 fallidos**: Google (IVA intracom), Internet, SkinClinic (CIF), Asesoria (total)
3. **Corregir subcuentas** 6000→config en facturas via PUT partidas
4. **Registrar ingresos** del Excel en FS (facturas cliente o asientos directos)
5. **Clasificar gastos** por actividad (pod/est/compartido) via carpeta_origen
6. **Comparar con modelos oficiales** de CARPETA REFERENCIA (303, 130, 111, 390, 190)

## Pendiente general
- [ ] Confirmar email
- [ ] Confirmar regimen estimacion directa
- [ ] Confirmar epigrafes IAE
- [x] Dar de alta en FacturaScripts como empresa
- [x] Configurar config.yaml SFCE
- [x] Dry-run pipeline exitoso
- [x] Pipeline ejecutado 119/126 OK (pendiente re-ejecutar con FS limpio)
