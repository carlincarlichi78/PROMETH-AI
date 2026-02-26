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
- Ejercicio 2025 creado (01/01/2025 - 31/12/2025, estado Abierto)
- Plan contable PGC espanol importado (802 cuentas, 721 subcuentas)
- Regimen general de IVA

## Pendiente
- [ ] Confirmar email
- [ ] Confirmar regimen de estimacion directa (simplificada o normal)
- [ ] Confirmar epigrafes IAE de ambas actividades
- [x] Dar de alta en FacturaScripts como empresa
- [ ] Recibir documentacion 2024 del gestor
- [ ] Configurar subcuentas contables para ambas actividades
- [ ] Configurar subcuentas contables para ambas actividades
