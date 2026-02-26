# IMPORTANTE: Leer siempre primero ../../CLAUDE.md (infraestructura y contexto general)

# PASTORINO COSTA DEL SOL S.L.

## Datos empresa
- **Razon social**: PASTORINO COSTA DEL SOL S.L.
- **CIF**: B13995519
- **Tipo**: Sociedad Limitada
- **Administrador**: Jose Manuel Pastorino (autonomo societario)
- **Actividad**: Importacion y comercializacion de limones argentinos
- **Provincia**: Malaga (Costa del Sol)
- **Direccion**: Av. General Lopez Dominguez 12, 29603 Marbella, Malaga
- **Email**: info@pastorinocostadelsol.com
- **Banco**: CaixaBank - IBAN ES13 2100 3889 1802 0018 6156 / ES82 2100 3889 1872 0130 6481

## Estado en FacturaScripts
- idempresa: 1
- Empresa creada, regimen general IVA, PGC espanol cargado (ejercicios 2025 y 2026)
- **Proveedores dados de alta** (10): Cauquen(1), LOGINET(2), Primafrio(3), Primatransit(4), Maersk(5), Odoo SA(6), Odoo ERP SP(7), Copyrap(8), El Corte Ingles(9), Transitainer(10)
- **Clientes dados de alta** (2): Malaga Natural(1), Tropical Trade SP Z O O(2)
- **50 facturas registradas**: 39 proveedor (35 originales + 4 anticipos Cauquen) + 1 NC + 5 cliente (4 MN + 1 Tropical Trade) + 1 Primatransit NC eliminada. Todas pagadas.
- **Facturas 2025 COMPLETAS** — Jose Manuel solo importa unos meses al año (T3 principal, algo en T2/T4)
- **46 asientos contables generados** (41 prov + 5 cliente). IVA PT corregido (A65-67). Intracomunitarias corregidas (A75-77). USD→EUR corregido en A56,60-64,80-83.
- **Regla de pago**: todas pagadas por banco (TRANS), fecha pago = fecha factura
- **TC USD**: 1.1775 (25/02/2026) aplicado a facturas Cauquen y LOGINET

## Proveedores principales
| Proveedor | CIF/ID | Pais | Tipo | Moneda |
|-----------|--------|------|------|--------|
| CAUQUEN ARGENTINA S.A.U. | AR 30-70793648-3 | Argentina | Exportador limones | USD |
| LNET S.A. (LOGINET) | AR 30-71035801-6 | Argentina | Flete maritimo | USD |
| PRIMAFRIO S.L. | B73047599 | Espana | Transporte frigorifico | EUR |
| PRIMATRANSIT S.L. | B16815003 | Espana | Agente aduanas | EUR |
| TRANSITAINER PORTUGAL LTDA | PT | Portugal | Despacho aduanero | EUR |
| MAERSK A/S / MAERSK SPAIN SLU | DK53139655 | Dinamarca/Espana | Naviera | EUR |
| ODOO S.A. / ODOO ERP SP SL | BE0477472701 / B72659014 | Belgica/Espana | Software ERP | EUR |

## Clientes
- **MALAGA NATURAL 2012 S.L.** (CIF B93159044) - Mercamalaga, Malaga
  - Distribuidor de 3 contenedores Sines (comision 10-12%, 1ra liquidacion 12%)
  - IVA reducido 4% (alimento basico)
  - 4 liquidaciones = 3 contenedores Sines (no 1:1)
- **TROPICAL TRADE SP Z O O** - Varsovia, Polonia
  - Comprador del contenedor Rotterdam (MNBU4144463)
  - Intracomunitaria (POL), IVA 0%, FOT Rotterdam
  - INV/2025/00005: 1,440 cajas x 24 EUR = 34,560 EUR

## Modelo de negocio (consignacion)
Cauquen envia limones "under consignment" con anticipo (8 USD/caja). Jose Manuel gestiona venta:
1. Cauquen exporta FOB Buenos Aires + cobra anticipo (1,440 cajas x 8 USD = 11,520 USD por contenedor)
2. LOGINET flete maritimo Buenos Aires > Europa (USD)
3. Maersk transporta contenedores refrigerados (40RH)
4. Transitainer/Primatransit despachan aduana Portugal/Espana
5. Primafrio transporte terrestre Portugal > Mercamalaga
6. **Venta**: Malaga Natural (Sines, comision 10-12%) o Tropical Trade (Rotterdam, sin comision)
7. **Liquidacion**: del precio de venta se descuenta comision distribuidor → JM se lleva 10% → se restan gastos → Cauquen cobra el resto
8. Pago final a Cauquen = lo que sobra despues de comisiones, margen JM y gastos. SIEMPRE en USD.

## Contenedores 2025
| Contenedor | Buque | ETD | Puerto | Exportador |
|-----------|-------|-----|--------|-----------|
| SUDU8020260 | Maersk Lanco | 31/05/25 | Sines PT | Cauquen |
| MNBU0233449 | San Lorenzo Maersk | 07/06/25 | Sines PT | Cauquen |
| SUDU6177121 | Maersk Londrina | 21/06/25 | Sines PT | Cauquen |
| MNBU4144463 | San Raphael Maersk | 26/07/25 | **Rotterdam** | Cauquen → **Tropical Trade (POL)** |

## Obligaciones fiscales

### Trimestrales
- **Modelo 303**: IVA (IVA repercutido 4% - IVA soportado 21% + IVA importacion)
- **Modelo 111**: Retenciones IRPF (si aplica)
- **Modelo 349**: Operaciones intracomunitarias (Odoo Belgica)

### Anuales
- **Modelo 390**: Resumen anual IVA
- **Modelo 200**: Impuesto de Sociedades
- **Modelo 347**: Operaciones con terceros >3.005,06 EUR
- **Cuentas anuales**: deposito en Registro Mercantil

## Particularidades contables
- IVA diferido importacion (casilla 77 modelo 303)
- DUA/DAU como justificante de importacion (despachos en Portugal)
- Facturas en USD (Cauquen, Loginet) requieren tipo de cambio
- Operaciones intracomunitarias con Odoo (autoliquidacion IVA)
- Limones tributan IVA 4% (alimento basico, no IVA general 21%)
- Liquidaciones Malaga Natural: 10% comision (12% en 1ra liquidacion ref 2207/P102295)
- Cauquen: modelo consignacion con anticipos (8 USD/caja) + liquidacion final

## IVA portugues en importaciones (CRITICO)
Las importaciones via Portugal generan IVA portugues (6% limones) que NO es deducible en Espana.
Proceso obligatorio para cada contenedor que entre por Portugal:

### Contabilizacion
1. Facturas Primatransit tienen lineas "IVA ADUANA" (IVA 0%) = IVA portugues pagado como suplido
2. FS genera asiento automatico metiendo TODO en 6000000000 (Compras)
3. **Hay que corregir manualmente**: sacar importe IVA PT de 600 y crear partida en **4709000000** (HP deudora devolucion impuestos)
4. Verificar cuadre: DEBE = HABER en cada asiento corregido

### Cruce DAU <-> Factura Primatransit
- Cada DAU corresponde a 1 contenedor y 1 factura Primatransit
- Seccion 47 del DAU: A00 = arancel (6.4%), B00 = IVA PT (6%)
- El importe B00 del DAU debe coincidir con la linea "IVA ADUANA" de la factura Primatransit

### Recuperacion
- **Modelo 360** en AEAT (devolucion IVA soportado en otro pais UE)
- Plazo: hasta 30/09 del ano siguiente
- Cuando Portugal devuelve: asiento 572 (Bancos) DEBE / 4709 HABER
- Si deniegan: asiento 631 (Otros tributos) DEBE / 4709 HABER (se convierte en gasto)

### Datos 2025
| Contenedor | DAU | Factura Primatransit | IVA PT |
|---|---|---|---|
| SUDU8020260 | 40672 | FAC2025A131 (2390101398) | 2,444.89 EUR |
| MNBU0233449 | 40674 | FAC2025A132 (2390101399) | 2,846.99 EUR |
| SUDU6177121 | PERDIDO | FAC2025A133 (2390101400) | 2,749.68 EUR |
| **Total 4709** | | | **8,041.56 EUR** |

## Estructura de archivos 2025
```
2025/
  libros_contables_2025.xlsx    # Excel principal con 9 pestanas
  legal/                        # Escritura constitucion, suscripciones
  procesado/
    T2/gastos/flete-maritimo/   # Facturas LOGINET junio
    T3/
      ingresos/                 # Facturas emitidas INV/2025/00001-00004
      gastos/
        compra-mercaderia/      # Factura Cauquen (limones FOB)
        flete-maritimo/         # Facturas LOGINET julio-agosto
        transporte-nacional/    # Facturas Primafrio
        despacho-aduanero/      # Primatransit + Transitainer
        naviera/                # Facturas Maersk
        software/               # Odoo
        publicidad/             # Copyrap
        material-oficina/       # El Corte Ingles
      documentos-importacion/
        dau/                    # DAU/DUA de aduanas
        bl/                     # Bill of Lading
        phyto/                  # Certificados fitosanitarios
        container/              # Documentos contenedores
        packing-list/
      liquidaciones/            # Liquidaciones Malaga Natural
      banco/                    # Justificantes bancarios
      otros/                    # Proformas, seguros, varios
    T4/gastos/                  # Primatransit dic, Odoo oct
```

## Resumen fiscal 2025 (actualizado sesion 4)
| Concepto | Anual | T2 | T3 | T4 |
|----------|-------|----|----|-----|
| Base ventas | 172,778.40 | 0 | 172,778.40 | 0 |
| IVA repercutido | 5,528.74 | 0 | 5,528.74 | 0 |
| Base compras | 127,630.46 | 39,286.62 | 86,448.74 | 1,895.10 |
| IVA soportado | 2,390.60 | 0 | 2,128.71 | 261.89 |
| **303 resultado** | **3,138.14** | **0** | **3,400.03** | **-261.89** |
| Resultado explotacion | 53,189.50 | | | |
| Resultado neto (est.) | 39,892.12 | | | |

Ejecutar: `python scripts/resumen_fiscal.py --empresa 1 --ejercicio 2025 --trimestre T3`

## Inbox - Archivos descartados (no facturas)
| Archivo | Motivo |
|---------|--------|
| 01PRMR523886.pdf | Recibo prima seguro Coface (536.75 EUR) - considerar si registrar como gasto |
| 3575_250905150252_009.pdf | CMR documento transporte |
| 3592_250908143329_001.pdf | CMR documento transporte |
| Factura Proforma 1.pdf | Proforma Cauquen (17,971 EUR) - no es factura definitiva |
| 4x Borrador*.pdf | Liquidaciones Malaga Natural (soporte de las 4 INV) |

## Operaciones intracomunitarias (configuradas)
| Proveedor | codpais | regimeniva | Autoliquidacion IVA |
|-----------|---------|------------|---------------------|
| Odoo S.A. | BEL | Intracomunitario | SI (472+477 corregidos en asientos 75-76) |
| Transitainer Portugal | PRT | Intracomunitario | SI (472+477 corregido en asiento 77) |
| Maersk A/S | DNK | General | NO — posible exencion Art.22 LIVA. Consultar asesor fiscal |
| **Tropical Trade** (cliente) | **POL** | **Intracomunitario** | N/A (venta, no compra). IVA 0% |

## Maersk — decision pendiente asesor fiscal
Transporte maritimo internacional Argentina>Europa por empresa danesa. El coste puede estar incluido en valor aduana (DUA), lo que haria la autoliquidacion redundante (doble imposicion). Se deja como IVA 0% sin autoliquidacion hasta confirmar con asesor. Para el 349 SI se declaran como adquisiciones intracomunitarias.

## Scripts disponibles
| Script | Uso |
|--------|-----|
| `scripts/crear_libros_contables.py` | Genera Excel con 10 pestanas (incluye VALIDACION) desde API de FS. Convierte USD→EUR automaticamente |
| `scripts/resumen_fiscal.py` | Resumen fiscal por consola (303/130/111 + Balance/PyG) |
| `scripts/generar_modelos_fiscales.py` | Genera 13 archivos .txt con modelos fiscales en carpeta cliente |
| `scripts/validar_asientos.py` | Validacion automatica de asientos (5 checks + --fix para corregir DIVISA y NC) |
| `scripts/renombrar_documentos.py` | Renombrado inteligente de PDFs. Usa OCR JSON + FS API + heuristicas. Reversible |

## Archivos .bat (doble clic para ejecutar)
| Archivo | Que hace |
|---------|----------|
| `generar_excel.bat` | Regenera Excel libros contables 2025 |
| `resumen_fiscal.bat` | Muestra resumen fiscal 2025 por consola |
| `validar_asientos.bat` | Valida asientos (solo informe) |
| `validar_asientos_fix.bat` | Valida y corrige errores DIVISA/NC automaticamente |
| `generar_modelos.bat` | Genera archivos .txt de modelos fiscales |
| `renombrar_documentos.bat` | Renombra PDFs en modo DRY-RUN (quitar --dry-run para ejecutar real) |

## Cauquen - facturas en FS
| Factura | Fecha | Importe | Tipo | Contenedor |
|---------|-------|---------|------|------------|
| E 00005-00004401 (id=145) | 09/06/25 | 11,520 USD | Anticipo | MNBU0233449 |
| E 00005-00004446 (id=146) | 16/06/25 | 11,520 USD | Anticipo | SUDU8020260 |
| E 00005-00004509 (id=147) | 29/06/25 | 11,520 USD | Anticipo | SUDU6177121 |
| ANT E 00005-00004696 (id=148) | 28/07/25 | 11,520 USD | Anticipo | MNBU4144463 |
| E 00005-00004696 (id=121) | 28/07/25 | 28,800 USD | Liquidacion final | ? |

## Facturas cliente en FS
| Factura | Cliente | Base | Total | Pagada |
|---------|---------|------|-------|--------|
| INV/2025/00001 (id=16) | Malaga Natural | 33,359.04 | 34,693.40 | Si |
| INV/2025/00002 (id=13) | Malaga Natural | 34,933.68 | 36,331.03 | Si |
| INV/2025/00003 (id=14) | Malaga Natural | 34,992.00 | 36,391.68 | Si |
| INV/2025/00004 (id=15) | Malaga Natural | 34,933.68 | 36,331.03 | Si |
| INV/2025/00005 (id=17) | Tropical Trade | 34,560.00 | 34,560.00 | Si |

## Pendiente

### SFCE (Sistema de Fiabilidad Contable Evolutivo) — EN CURSO
- [ ] **Implementar SFCE**: pipeline automatico 7 fases con triple verificacion contra FS
  - Diseno aprobado: `docs/plans/2026-02-26-sistema-fiabilidad-contable-design.md`
  - Plan implementacion: `docs/plans/2026-02-26-sfce-implementation.md`
  - 17 tareas, empezar por core/ (T1-T5), luego config (T6-T8), luego fases (T9-T15), luego pipeline (T16-T17)
  - Alcance GLOBAL: aplica a todos los clientes en CONTABILIDAD/

### Pastorino — pendiente
- [ ] Regenerar archivos modelos fiscales (.txt)
- [ ] Recibo seguro Coface (01PRMR523886.pdf): registrar como gasto en ejercicio 2026 (536.75 EUR, cuenta 625)
- [ ] Conciliacion bancaria con extractos CaixaBank
- [ ] Jose Manuel debe pedir DAU perdido del contenedor SUDU6177121 a Transitainer
- [ ] Presentar modelo 360 AEAT antes 30/09/2026 (devolucion IVA PT: 8,041.56 EUR)
- [ ] Consultar asesor fiscal sobre tratamiento IVA Maersk (Art. 22 LIVA vs autoliquidacion)
- [ ] Registrar asiento IS cuando se presente modelo 200 (IS est. 13,297.38 EUR)
- [ ] Presentar modelos oficiales en AEAT (303 trimestrales, 349, 347, 390, 200)
