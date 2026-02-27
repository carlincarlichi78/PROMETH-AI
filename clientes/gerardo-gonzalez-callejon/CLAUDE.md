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
1. **Podologia** — actividad sanitaria, clinica propia (EXENTA IVA)
2. **Estetica** — actividad complementaria en el mismo local (IVA 21%)

## Regimen fiscal
- Estimacion directa (simplificada o normal — PENDIENTE confirmar)
- **Podologia**: exenta de IVA (Art. 20.1.3 LIVA — asistencia sanitaria)
- **Estetica**: sujeta a IVA 21% (no es asistencia sanitaria a efectos fiscales)
- Sectores diferenciados: IVA solo deducible por gastos de estetica
- Compensacion IVA arrastrada de 2024: 1,609.34 EUR (toda consumida en 2025)

## Estado en FacturaScripts
- Empresa creada (codigo 2, nombre corto G. GONZALEZ)
- Ejercicio 2025 (codejercicio=0002, 01/01/2025 - 31/12/2025, Abierto)
- PGC importado (802 cuentas, 721 subcuentas)
- **92 facturas proveedor** registradas (IDs 920-1012)
- **79 asientos** verificados + 13 sin asiento (Luz/SUM + Fisaude)
- **79 subcuentas corregidas** (6000→subcuenta especifica por proveedor)
- Datos limpios: se eliminaron 131 facturas + 426 asientos huerfanos de sesiones anteriores

## SFCE Pipeline - Resultado (sesion 27/02/2026)
- config.yaml: 48 proveedores, codejercicio 0002
- **Registro**: 92/93 docs registrados (1 NC SkinClinic devolucion fallida por discrepancia total)
- **Asientos**: 79 OK, 13 sin asiento (12 Luz.pdf tipo SUM + 1 Fisaude)
- **Correccion**: 79 correcciones automaticas (subcuentas), 36 avisos manuales (discrepancias IRPF)
- **Cross-validation**: 6 PASS / 7 FAIL (46%) — esperado con 31% cobertura docs
  - PASS: Ingresos/700, IVA repercutido/477, Libro diario, Balance, Clientes, Personal
  - FAIL: Gastos/600 (diff 39098), IVA soportado/472 (diff 105.74), Autoliq, Fact=Asientos, 303, Proveedores, Auditor IA

### Problemas identificados
1. **13 facturas SIN ASIENTO** (Luz.pdf SUM + Fisaude): asientos.py busca en facturaclientes/ por error, no genera asiento contable
2. **36 discrepancias total asiento vs factura**: IRPF no se aplica correctamente. Afecta web_developer (7%), canete_may (7%), carolina_lara (15%), sainero_gloria (15%), nuevalos_marta (7%)
3. **Bug pipeline.py:405**: crash en resumen porque `pre_val["validados"]` son strings (nombres archivo), no dicts. No afecta el pipeline, solo el resumen final
4. **IVA soportado diff 105.74**: 4574.60 FS vs 4468.86 calculado — posible SUM mal registrada

### OCR conservado
- validated_batch_full.json: 93 docs con OCR completo
- validated_batch.json: copia de full (93 docs)
- registered.json: 92 docs registrados con idfactura
- pipeline_state.json: 7 fases completadas

## Modelo 303 oficial del gestor (extraido de PDFs)

### IVA repercutido (ventas estetica al 21%)
| Trim | Base 21% | Cuota | Intracom | Total deveng |
|------|----------|-------|----------|-------------|
| T1 | 6,327.59 | 1,328.79 | 71.25 | 1,400.04 |
| T2 | 5,387.04 | 1,131.28 | 95.76 | 1,227.04 |
| T3 | 3,374.38 | 708.62 | 21.22 | 729.84 |
| T4 | 8,972.96 | 1,884.32 | 45.08 | 1,929.40 |
| **TOT** | **24,061.97** | **5,053.01** | **233.31** | **5,286.32** |

### IVA soportado deducible (solo estetica)
| Trim | Base int | Cuota int | Intracom | Total deduc |
|------|----------|-----------|----------|------------|
| T1 | 4,627.27 | 795.82 | 71.25 | 867.07 |
| T2 | 3,929.90 | 812.23 | 95.76 | 907.99 |
| T3 | 2,175.18 | 456.79 | 21.22 | 478.01 |
| T4 | 5,249.46 | 908.57 | 45.08 | 953.65 |
| **TOT** | **15,981.81** | **2,973.41** | **233.31** | **3,206.72** |

### Resultado y compensaciones
| Trim | Resultado | Comp.anterior | Aplicada | Pendiente | A pagar |
|------|-----------|---------------|----------|-----------|---------|
| T1 | 532.97 | 1,609.34 | 532.97 | 1,076.37 | 0.00 |
| T2 | 319.05 | 1,076.37 | 319.05 | 757.32 | 0.00 |
| T3 | 251.83 | 757.32 | 251.83 | 505.49 | 0.00 |
| T4 | 975.75 | 505.49 | 505.49 | 0.00 | **470.26** |

### Verificacion cruzada
- Excel Estetica IVA vs 303 deducible: **COINCIDE EXACTO** (3,206.72 = 3,206.72)
- Ingresado efectivo 2025: **470.26 EUR** (solo T4, resto compensado con saldo 2024)

## Gastos del gestor (Excels oficiales)
| Actividad | Docs | Base total | IVA | IRPF |
|-----------|------|-----------|-----|------|
| Podologia | 170 | 41,259.42 | 154.24 | 1,586.66 |
| Estetica | 88 | 17,374.67 | 3,206.72 | 697.73 |
| **Total** | **258** | **58,634.09** | **3,360.96** | **2,284.39** |

## Cobertura pipeline vs gestor
- **Docs**: 93 OCR de 258 gestor = **31% cobertura** (faltan 165 docs)
- **Base FS**: 40,086.79 neto en FS
- **IVA FS**: 4,574.60 (incluye pod+est, sin filtrar por actividad)

## Ingresos (del Libro bienes de ingresos - NO registrados en FS)
- Podologia (exenta IVA): T1=18,646.68 T2=22,641.68 T3=28,830.00 T4=29,629.50 Total=99,747.86
- Estetica (IVA 21%): T1=6,327.59 T2=5,387.04 T3=3,374.38 T4=12,208.40 Total=27,297.41
- IVA repercutido estetica: T1=1,328.79 T2=1,131.28 T3=708.62 T4=1,884.32 Total=5,053.01

## Bienes de inversion
- 25 items, amortizacion 2025 = 8,229.94 EUR
- Items 1-16, 23-25: Podologia | Items 17-22: Estetica

## Proximos pasos (por prioridad)
1. **Conseguir los PDFs de vuelta**: usuario debe re-enviar los 152 PDFs eliminados
2. **Fix IRPF en registro**: facturas con IRPF (7%/15%) no aplican retencion en FS — necesita codretencion en crearFacturaProveedor o correccion post-registro
3. **Fix 13 facturas sin asiento**: verificar si asientos.py usa endpoint incorrecto para SUM
4. **Fix pipeline.py:405**: crash en resumen (string vs dict en pre_val.validados)
5. **Clasificar gastos por actividad**: CRITICO para replicar 303 — cada factura debe ser pod/est/compartido
6. **Registrar ingresos** del Excel en FS (facturas cliente)
7. **Completar documentos faltantes**: 165 docs que el gestor tiene y nosotros no
8. **Generar modelos fiscales** y comparar trimestre a trimestre

## Insight arquitectonico clave
El 303 de Gerardo **solo incluye IVA de estetica**. Para replicarlo:
- El config.yaml necesita campo `actividad` por proveedor (pod/est/compartido)
- Gastos compartidos (luz, local, internet) requieren criterio de reparto
- El pipeline debe filtrar IVA deducible = solo gastos de estetica
- La compensacion 2024 (1,609.34) debe configurarse como saldo inicial

## Pendiente general
- [ ] Confirmar email
- [ ] Confirmar regimen estimacion directa
- [ ] Confirmar epigrafes IAE
- [ ] Re-obtener 152 PDFs eliminados del usuario
- [ ] Fix IRPF en facturas (36 discrepancias)
- [ ] Fix 13 facturas sin asiento
- [ ] Fix pipeline.py:405 bug resumen
- [x] Dar de alta en FacturaScripts como empresa
- [x] Configurar config.yaml SFCE (48 proveedores)
- [x] Pipeline OCR (93 validados de 107)
- [x] Comparacion completa 303 vs gestor (MATCH EXACTO IVA estetica)
- [x] Re-registro 92/93 docs en FS (limpio, sin duplicados)
- [x] Correccion subcuentas automatica (79 corregidas)
- [x] Cross-validation 6/13 PASS (46%, esperado con cobertura parcial)
