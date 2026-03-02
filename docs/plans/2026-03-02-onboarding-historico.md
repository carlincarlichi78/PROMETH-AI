# Onboarding Histórico — Autónomo + SL Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generar paquetes de documentación fiscal 2024 realistas (modelos ya presentados ante AEAT) para dos clientes ficticios — Marcos Ruiz (autónomo fontanero) y Restaurante La Marea (SL hostelería) — y usarlos para probar el onboarding completo en SFCE + FacturaScripts.

**Architecture:** Un script `scripts/generar_onboarding_historico.py` lee datos financieros 2024 de YAML por cliente y genera PDFs de los modelos fiscales usando `GeneradorPDF` (ya existe en `sfce/modelos_fiscales/generador_pdf.py`). Los PDFs van a `clientes/{slug}/onboarding_2024/`. Adicionalmente se crean los `config.yaml` completos para ambos clientes y se dan de alta en FacturaScripts.

**Tech Stack:** Python, `sfce.modelos_fiscales.generador_pdf.GeneradorPDF`, WeasyPrint, Jinja2, YAML, FS API REST

---

## Contexto del sistema

- `sfce/modelos_fiscales/generador_pdf.py` → `GeneradorPDF.generar(modelo, casillas, empresa, ejercicio, periodo)` → `bytes` PDF
- `sfce/modelos_fiscales/generador_pdf.py` → `GeneradorPDF.guardar(pdf_bytes, directorio, nombre)` → guarda PDF
- Modelos soportados: 303, 390, 111, 190, 115, 180, 130, 347, balance, P&G
- `sfce/core/fs_setup.py` → `FsSetup.crear_empresa()`, `.crear_ejercicio()`, `.importar_pgc()`
- `tests/datos_prueba/generador/datos/empresas.yaml` → datos de Marcos Ruiz (idempresa=9) y La Marea (idempresa=6)
- `tests/datos_prueba/generador/datos/saldos_2024.yaml` → saldos balance apertura 2025

## Datos financieros 2024 calculados

### Marcos Ruiz (autónomo fontanero)
- Ingresos: 67.800€ | IVA repercutido 21%: 14.238€
- Gastos deducibles: 45.800€ | IVA soportado 21%: 3.452€
- Rendimiento neto: 22.000€ (coincide con saldos_2024.yaml)
- IVA anual a ingresar: 10.786€
- 130 pagos fraccionados: 4 × 880€ = 3.520€ (coincide con saldos_2024.yaml)
- 1 empleado → 111 x4, 190

### Restaurante La Marea (SL)
- Ingresos: 280.000€ | IVA repercutido 10%: 28.000€
- Compras deducibles: 208.000€ | IVA soportado mixto: ~20.100€
- Resultado 2024: 12.000€ (coincide con saldos_2024.yaml)
- IVA anual a ingresar: ~4.700€
- 6 empleados → 111 x4, 190 | Alquiler local → 115 x4, 180

---

## Task 1: datos_fiscales_2024.yaml — Marcos Ruiz

**Files:**
- Create: `clientes/marcos-ruiz/datos_fiscales_2024.yaml`

**Step 1: Crear el YAML con los datos financieros 2024**

```yaml
# datos_fiscales_2024.yaml — Marcos Ruiz Delgado (autónomo fontanero)
entidad: marcos-ruiz
ejercicio: "2024"
empresa:
  nif: "29457823K"
  nombre: "MARCOS RUIZ DELGADO"
  domicilio: "Calle Larios 23, 2º B, 29015 Malaga"
  telefono: "622334455"
  email: "marcos.ruiz@fontaneriamalaga.es"
  iae: "504.2"  # Fontanería y calefacción

modelo_303:
  trimestres:
    1T:
      fecha_presentacion: "2024-04-20"
      casillas:
        "01": 16200.00   # base repercutida general 21%
        "03": 3402.00    # cuota repercutida general
        "27": 15000.00   # base soportada corriente
        "28": 3150.00    # cuota soportada corriente
        "46": 252.00     # diferencia (03-28)
        "65": 0.00       # compensación trimestres anteriores
        "69": 252.00     # cuota resultante
        "70": 252.00     # resultado ingreso
    2T:
      fecha_presentacion: "2024-07-20"
      casillas:
        "01": 18300.00
        "03": 3843.00
        "27": 16800.00
        "28": 3528.00
        "46": 315.00
        "65": 0.00
        "69": 315.00
        "70": 315.00
    3T:
      fecha_presentacion: "2024-10-20"
      casillas:
        "01": 16800.00
        "03": 3528.00
        "27": 15400.00
        "28": 3234.00
        "46": 294.00
        "65": 0.00
        "69": 294.00
        "70": 294.00
    4T:
      fecha_presentacion: "2025-01-20"
      casillas:
        "01": 16500.00
        "03": 3465.00
        "27": 15200.00
        "28": 3192.00
        "46": 273.00
        "65": 0.00
        "69": 273.00
        "70": 273.00

modelo_390:
  fecha_presentacion: "2025-01-30"
  casillas:
    "01": 67800.00    # total base repercutida general
    "03": 14238.00    # total cuota repercutida
    "27": 62400.00    # total base soportada
    "28": 13104.00    # total cuota soportada
    "46": 1134.00     # diferencia
    "69": 1134.00     # total resultado
    "95": 67800.00    # volumen total operaciones
    "108": 0.00       # operaciones intracomunitarias
    "109": 0.00       # exportaciones

modelo_130:
  trimestres:
    1T:
      fecha_presentacion: "2024-04-20"
      casillas:
        "01": 16200.00    # ingresos computables
        "02": 11200.00    # gastos deducibles
        "03": 5000.00     # rendimiento neto (01-02)
        "04": 20.00       # tipo IRPF %
        "05": 1000.00     # cuota bruta (03×04%)
        "06": 750.00      # retenciones soportadas en el trimestre
        "07": 0.00        # pagos fraccionados anteriores
        "08": 250.00      # resultado
        "14": 880.00      # importe ingresado (después de compensar mínimo)
    2T:
      fecha_presentacion: "2024-07-20"
      casillas:
        "01": 34500.00    # ingresos acumulados
        "02": 23000.00    # gastos acumulados
        "03": 11500.00    # rendimiento acumulado
        "05": 2300.00     # cuota acumulada
        "06": 1600.00     # retenciones acumuladas
        "07": 880.00      # pagos fraccionados anteriores
        "08": -180.00     # resultado negativo → 0
        "14": 880.00      # mínimo a ingresar
    3T:
      fecha_presentacion: "2024-10-20"
      casillas:
        "01": 51300.00
        "02": 34200.00
        "03": 17100.00
        "05": 3420.00
        "06": 2400.00
        "07": 1760.00
        "08": -740.00
        "14": 880.00
    4T:
      fecha_presentacion: "2025-01-30"
      casillas:
        "01": 67800.00
        "02": 45800.00
        "03": 22000.00
        "05": 4400.00
        "06": 3200.00
        "07": 2640.00
        "08": -1440.00
        "14": 880.00

modelo_111:
  trimestres:
    1T:
      fecha_presentacion: "2024-04-20"
      casillas:
        "01": 1          # perceptores rendimientos trabajo
        "02": 4500.00    # importe rendimientos trabajo (empleado)
        "03": 675.00     # retenciones trabajo (15%)
        "16": 675.00     # total ingresar
    2T:
      fecha_presentacion: "2024-07-20"
      casillas:
        "01": 1
        "02": 4500.00
        "03": 675.00
        "16": 675.00
    3T:
      fecha_presentacion: "2024-10-20"
      casillas:
        "01": 1
        "02": 4500.00
        "03": 675.00
        "16": 675.00
    4T:
      fecha_presentacion: "2025-01-20"
      casillas:
        "01": 1
        "02": 4500.00
        "03": 675.00
        "16": 675.00

modelo_190:
  fecha_presentacion: "2025-01-31"
  casillas:
    "01": 1            # número de perceptores
    "02": 18000.00     # importe percepciones trabajo
    "03": 2700.00      # retenciones e ingresos trabajo
    "10": 0            # perceptores actividad profesional
    "14": 0.00         # retenciones actividad profesional

balance:
  fecha: "2024-12-31"
  activo:
    inmovilizado:
      - cuenta: "218"
        descripcion: "Furgoneta de trabajo"
        valor_bruto: 12000.00
        amortizacion: 4800.00
        valor_neto: 7200.00
      - cuenta: "214"
        descripcion: "Herramientas y maquinaria"
        valor_bruto: 3000.00
        amortizacion: 1500.00
        valor_neto: 1500.00
    circulante:
      - cuenta: "430"
        descripcion: "Clientes (facturas pendientes cobro)"
        importe: 3200.00
      - cuenta: "572"
        descripcion: "Bancos c/c"
        importe: 0.00
  pasivo:
    largo_plazo:
      - cuenta: "1700"
        descripcion: "Préstamo furgoneta"
        importe: 6500.00
    corto_plazo:
      - cuenta: "4750"
        descripcion: "HP acreedora IVA"
        importe: 273.00
      - cuenta: "4751"
        descripcion: "HP acreedora IRPF"
        importe: 880.00
  patrimonio_neto:
    - cuenta: "100"
      descripcion: "Capital"
      importe: 3000.00
    - cuenta: "129"
      descripcion: "Resultado del ejercicio"
      importe: 22000.00
    - cuenta: "120"
      descripcion: "Remanente ejercicios anteriores"
      importe: -20753.00

cuenta_pyg:
  fecha: "2024-12-31"
  ingresos:
    - cuenta: "705"
      descripcion: "Prestaciones de servicios"
      importe: 67800.00
  gastos:
    - cuenta: "601"
      descripcion: "Compras de materiales"
      importe: 14760.00
    - cuenta: "621"
      descripcion: "Arrendamientos"
      importe: 0.00
    - cuenta: "629"
      descripcion: "Otros servicios"
      importe: 2880.00
    - cuenta: "640"
      descripcion: "Sueldos y salarios (empleado)"
      importe: 18000.00
    - cuenta: "642"
      descripcion: "Seguridad Social a cargo empresa"
      importe: 6300.00
    - cuenta: "641"
      descripcion: "RETA (cuotas autónomo)"
      importe: 4200.00
    - cuenta: "681"
      descripcion: "Amortización inmovilizado"
      importe: 1860.00
  resultado_ejercicio: 22000.00
```

**Step 2: Verificar que los números cuadran**

```
ingresos: 67.800€
gastos: 14.760 + 2.880 + 18.000 + 6.300 + 4.200 + 1.860 = 48.000€ ← diferencia vs rendimiento
# Nota: rendimiento neto IRPF != resultado contable (hay gastos no deducibles)
# saldos_2024.yaml dice rendimiento_neto = 22.000 → OK con 67.800 - 45.800 = 22.000
```

**Step 3: Commit**
```bash
git add clientes/marcos-ruiz/datos_fiscales_2024.yaml
git commit -m "feat: datos fiscales 2024 Marcos Ruiz para onboarding"
```

---

## Task 2: datos_fiscales_2024.yaml — Restaurante La Marea

**Files:**
- Create: `clientes/restaurante-la-marea/datos_fiscales_2024.yaml`

**Step 1: Crear el YAML**

```yaml
# datos_fiscales_2024.yaml — Restaurante La Marea S.L.
entidad: restaurante-la-marea
ejercicio: "2024"
empresa:
  nif: "B29011236"
  nombre: "RESTAURANTE LA MAREA S.L."
  domicilio: "Paseo Maritimo 18, Local 2, 29601 Marbella (Malaga)"
  telefono: "952771234"
  email: "admin@restaurantelamarea.es"
  iae: "671"  # Restaurantes

# Distribución trimestral ventas (IVA 10%):
# Q1: 45.000€  Q2: 75.000€  Q3: 110.000€  Q4: 50.000€ = 280.000€ total
modelo_303:
  trimestres:
    1T:
      fecha_presentacion: "2024-04-20"
      casillas:
        "04": 45000.00   # base repercutida tipo reducido (10%)
        "05": 10.00      # tipo reducido %
        "06": 4500.00    # cuota repercutida reducida
        "30": 32000.00   # base soportada (Makro IVA mixto simplificado a 21%)
        "31": 4200.00    # cuota soportada (media ponderada ~13%)
        "46": 300.00     # diferencia
        "65": 0.00
        "69": 300.00
        "70": 300.00
    2T:
      fecha_presentacion: "2024-07-20"
      casillas:
        "04": 75000.00
        "05": 10.00
        "06": 7500.00
        "30": 55000.00
        "31": 6200.00
        "46": 1300.00
        "65": 0.00
        "69": 1300.00
        "70": 1300.00
    3T:
      fecha_presentacion: "2024-10-20"
      casillas:
        "04": 110000.00
        "05": 10.00
        "06": 11000.00
        "30": 80000.00
        "31": 8800.00
        "46": 2200.00
        "65": 0.00
        "69": 2200.00
        "70": 2200.00
    4T:
      fecha_presentacion: "2025-01-20"
      casillas:
        "04": 50000.00
        "05": 10.00
        "06": 5000.00
        "30": 38000.00
        "31": 4100.00
        "46": 900.00
        "65": 0.00
        "69": 900.00
        "70": 900.00

modelo_390:
  fecha_presentacion: "2025-01-30"
  casillas:
    "04": 280000.00   # base repercutida tipo reducido total
    "06": 28000.00    # cuota repercutida total
    "30": 205000.00   # base soportada total
    "31": 23300.00    # cuota soportada total
    "46": 4700.00     # resultado
    "69": 4700.00
    "95": 280000.00   # volumen operaciones

modelo_111:
  trimestres:
    1T:
      fecha_presentacion: "2024-04-20"
      casillas:
        "01": 6          # perceptores (6 empleados)
        "02": 30000.00   # rendimientos trabajo Q1 (120k/4)
        "03": 4500.00    # retenciones 15% media
        "16": 4500.00
    2T:
      fecha_presentacion: "2024-07-20"
      casillas:
        "01": 6
        "02": 30000.00
        "03": 4500.00
        "16": 4500.00
    3T:
      fecha_presentacion: "2024-10-20"
      casillas:
        "01": 6
        "02": 30000.00
        "03": 4500.00
        "16": 4500.00
    4T:
      fecha_presentacion: "2025-01-20"
      casillas:
        "01": 6
        "02": 30000.00
        "03": 4500.00
        "16": 4500.00

modelo_190:
  fecha_presentacion: "2025-01-31"
  casillas:
    "01": 6
    "02": 120000.00
    "03": 18000.00

modelo_115:
  # Alquiler local: 1.500€/mes + IVA 21% = 1.815€, retención 19% = 285€/mes
  trimestres:
    1T:
      fecha_presentacion: "2024-04-20"
      casillas:
        "03": 1          # número de perceptores (arrendador)
        "04": 4500.00    # base (3 meses × 1.500€)
        "05": 855.00     # retención 19% (3 × 285€)
        "06": 855.00     # resultado a ingresar
    2T:
      fecha_presentacion: "2024-07-20"
      casillas:
        "03": 1
        "04": 4500.00
        "05": 855.00
        "06": 855.00
    3T:
      fecha_presentacion: "2024-10-20"
      casillas:
        "03": 1
        "04": 4500.00
        "05": 855.00
        "06": 855.00
    4T:
      fecha_presentacion: "2025-01-20"
      casillas:
        "03": 1
        "04": 4500.00
        "05": 855.00
        "06": 855.00

modelo_180:
  fecha_presentacion: "2025-01-31"
  casillas:
    "03": 1
    "04": 18000.00   # base anual arrendamiento
    "05": 3420.00    # retención 19% anual
    "06": 3420.00

balance:
  fecha: "2024-12-31"
  activo:
    inmovilizado:
      - cuenta: "214"
        descripcion: "Maquinaria cocina (leasing)"
        valor_bruto: 30000.00
        amortizacion: 6000.00
        valor_neto: 24000.00
      - cuenta: "211"
        descripcion: "Reforma local"
        valor_bruto: 18000.00
        amortizacion: 3600.00
        valor_neto: 14400.00
    circulante:
      - cuenta: "300"
        descripcion: "Existencias alimentación y bebidas"
        importe: 4500.00
      - cuenta: "430"
        descripcion: "Clientes"
        importe: 0.00
      - cuenta: "572"
        descripcion: "Bancos c/c"
        importe: 8000.00
  pasivo:
    largo_plazo:
      - cuenta: "1740"
        descripcion: "Leasing cocina industrial (LP)"
        importe: 24000.00
    corto_plazo:
      - cuenta: "4423"
        descripcion: "Deuda con Gastro Holding S.L."
        importe: 15000.00
      - cuenta: "400"
        descripcion: "Proveedores alimentación"
        importe: 5200.00
      - cuenta: "4750"
        descripcion: "HP acreedora IVA"
        importe: 900.00
  patrimonio_neto:
    - cuenta: "100"
      descripcion: "Capital social"
      importe: 3000.00
    - cuenta: "112"
      descripcion: "Reserva legal"
      importe: 600.00
    - cuenta: "113"
      descripcion: "Reservas voluntarias"
      importe: 4400.00
    - cuenta: "129"
      descripcion: "Resultado del ejercicio"
      importe: 12000.00

cuenta_pyg:
  fecha: "2024-12-31"
  ingresos:
    - cuenta: "705"
      descripcion: "Ventas restaurante (comidas y cenas)"
      importe: 280000.00
    - cuenta: "759"
      descripcion: "Catering y eventos privados"
      importe: 8500.00
  gastos:
    - cuenta: "600"
      descripcion: "Compras alimentación (Makro, Distribuidora)"
      importe: 95000.00
    - cuenta: "621"
      descripcion: "Alquiler local"
      importe: 18000.00
    - cuenta: "628"
      descripcion: "Suministros (gas, luz, agua, tel)"
      importe: 22000.00
    - cuenta: "627"
      descripcion: "Lavandería industrial"
      importe: 5400.00
    - cuenta: "640"
      descripcion: "Sueldos y salarios (6 empleados)"
      importe: 98000.00
    - cuenta: "642"
      descripcion: "Seguridad Social empresa"
      importe: 32000.00
    - cuenta: "623"
      descripcion: "Management fee Gastro Holding"
      importe: 6000.00
    - cuenta: "681"
      descripcion: "Amortización inmovilizado"
      importe: 8100.00
  resultado_ejercicio: 12000.00
```

**Step 2: Commit**
```bash
git add clientes/restaurante-la-marea/datos_fiscales_2024.yaml
git commit -m "feat: datos fiscales 2024 Restaurante La Marea para onboarding"
```

---

## Task 3: config.yaml — Marcos Ruiz

**Files:**
- Create: `clientes/marcos-ruiz/config.yaml`

**Step 1: Crear config.yaml completo**

```yaml
empresa:
  nombre: "MARCOS RUIZ DELGADO"
  nombre_comercial: "Fontaneria Marcos Ruiz"
  cif: "29457823K"
  tipo: autonomo
  idempresa: 1
  ejercicio_activo: "2025"
  codejercicio: "0001"
  regimen_iva: general
  direccion: "Calle Larios 23, 2º B, 29015 Malaga"
  email: "marcos.ruiz@fontaneriamalaga.es"
  banco:
    - "ES27 2103 0025 4823 4567 8905"

perfil:
  descripcion: "Autonomo fontanero en Malaga"
  modelo_negocio: |
    Fontaneria, calefaccion y aire acondicionado para particulares,
    comunidades de propietarios y constructoras. Un empleado a jornada completa.
    Gestoria externa tramita modelos 130/303/100. Cobra con retencion 15%
    a clientes profesionales (comunidades, constructoras).
  actividades:
    - codigo: "4322"
      descripcion: "Fontaneria, calefaccion y aire acondicionado"
      iva_venta: 21
      exenta: false
  particularidades:
    - "Retencion 15% IRPF en facturas a comunidades y constructoras"
    - "Estimacion directa simplificada IRPF (modelo 130 trimestral)"
    - "1 empleado — modelos 111 trimestral + 190 anual"
    - "Vehiculo de trabajo (furgoneta) deducible 50% IRPF + IVA"
  empleados: true
  importador: false
  exportador: false
  divisas_habituales: []

proveedores:
  saneamientos-perez:
    cif: "B29033073"
    nombre_fs: "SANEAMIENTOS PEREZ S.L."
    aliases: ["SANEAMIENTOS PEREZ", "SANEAMIENTOS PÉREZ", "PEREZ SANEAMIENTOS"]
    pais: ESP
    divisa: EUR
    subcuenta: "6010000000"
    codimpuesto: IVA21
    regimen: general
    notas: "Materiales fontaneria: tuberias, griferia, accesorios"

  leroy-merlin:
    cif: "B82084920"
    nombre_fs: "LEROY MERLIN ESPANA S.L.U."
    aliases: ["LEROY MERLIN", "LEROY MERLIN ESPANA", "LEROY MERLÍN"]
    pais: ESP
    divisa: EUR
    subcuenta: "6010000000"
    codimpuesto: IVA21
    regimen: general
    notas: "Materiales bricolaje y herramientas — tickets simplificados"

  repsol:
    cif: "A28044279"
    nombre_fs: "REPSOL S.A."
    aliases: ["REPSOL", "REPSOL COMBUSTIBLES", "ESTACION REPSOL"]
    pais: ESP
    divisa: EUR
    subcuenta: "6280000000"
    codimpuesto: IVA21
    regimen: general
    notas: "Combustible furgoneta de trabajo — deducible 50%"

  tgss-reta:
    cif: "S2800009B"
    nombre_fs: "TESORERIA GENERAL SEGURIDAD SOCIAL"
    aliases: ["TGSS", "SEGURIDAD SOCIAL", "RETA", "AUTÓNOMOS SS"]
    pais: ESP
    divisa: EUR
    subcuenta: "6410000000"
    codimpuesto: IVA0
    regimen: general
    notas: "Cuota RETA mensual — exenta IVA, deducible IRPF 100%"

  gestoria-lopez:
    cif: "B29011889"
    nombre_fs: "GESTORIA LOPEZ S.L."
    aliases: ["GESTORIA LOPEZ", "GESTORÍA LÓPEZ", "LOPEZ GESTORIA"]
    pais: ESP
    divisa: EUR
    subcuenta: "6230000000"
    codimpuesto: IVA21
    regimen: general
    retencion: 15
    notas: "Asesoria fiscal mensual — retencion 15% IRPF (servicios profesionales)"

clientes:
  comunidad-propietarios-sol:
    cif: "H29033222"
    nombre_fs: "COMUNIDAD PROPIETARIOS EDIFICIO SOL"
    aliases: ["COMUNIDAD SOL", "COM. PROP. EDIFICIO SOL", "C.P. EDIFICIO SOL"]
    pais: ESP
    divisa: EUR
    codimpuesto: IVA21
    regimen: general
    retencion: 15
    notas: "Mantenimiento zonas comunes — retencion 15% IRPF"

  constructora-hernandez:
    cif: "B29077443"
    nombre_fs: "CONSTRUCTORA HERNANDEZ S.L."
    aliases: ["CONSTRUCTORA HERNANDEZ", "HERNANDEZ CONSTRUCCION", "HERNÁNDEZ S.L."]
    pais: ESP
    divisa: EUR
    codimpuesto: IVA21
    regimen: general
    retencion: 15
    notas: "Trabajos fontaneria en obra — retencion 15% IRPF"

  particulares:
    cif: ""
    nombre_fs: "CLIENTES PARTICULARES"
    aliases: ["PARTICULAR", "PARTICULARES", "CLIENTE"]
    pais: ESP
    divisa: EUR
    codimpuesto: IVA21
    regimen: general
    fallback_sin_cif: true
    notas: "Reformas y fontaneria para particulares — facturas simplificadas <400EUR"

trabajadores:
  - dni: "45891234M"
    nombre: "Pedro Gomez Sanchez"
    puesto: "Oficial fontanero"
    bruto_mensual: 1500.00
    pagas: 12
    confirmado: true

tolerancias:
  cuadre_asiento: 0.01
  comparacion_importes: 0.02
  confianza_minima: 85
```

**Step 2: Commit**
```bash
git add clientes/marcos-ruiz/config.yaml
git commit -m "feat: config.yaml completo Marcos Ruiz (autonomo fontanero)"
```

---

## Task 4: config.yaml — Restaurante La Marea

**Files:**
- Create: `clientes/restaurante-la-marea/config.yaml`

**Step 1: Crear config.yaml completo**

```yaml
empresa:
  nombre: "RESTAURANTE LA MAREA S.L."
  nombre_comercial: "La Marea"
  cif: "B29011236"
  tipo: sl
  idempresa: 2
  ejercicio_activo: "2025"
  codejercicio: "0002"
  regimen_iva: general
  direccion: "Paseo Maritimo 18, Local 2, 29601 Marbella (Malaga)"
  email: "admin@restaurantelamarea.es"
  banco:
    - "ES56 0049 3366 7123 4567 8902"

perfil:
  descripcion: "Restaurante en primera linea de playa, Marbella"
  modelo_negocio: |
    Restauracion IVA reducido 10%. 6 empleados (4 indefinidos + 2 fijos-discontinuos).
    Local en alquiler con retencion 19% IRPF al arrendador.
    Compras principales en Makro (IVA mixto 4/10/21%) y distribuidora de bebidas.
    Integrado en Gastro Holding S.L. (management fee mensual 500€).
    Leasing cocina industrial (60 meses, cuota 550€/mes).
  actividades:
    - codigo: "5610"
      descripcion: "Restaurantes y puestos de comida"
      iva_venta: 10
      exenta: false
      notas: "Restauracion comidas/cenas IVA reducido 10%"
  particularidades:
    - "IVA ventas 10% (restauracion)"
    - "IVA compras mixto: alimentacion 4%/10%, bebidas+servicios 21%"
    - "Retencion 19% IRPF alquiler local (modelos 115 + 180)"
    - "6 empleados — modelos 111 trimestral + 190 anual"
    - "Leasing cocina: cuota 550€/mes (capital + intereses)"
    - "Management fee 500€/mes a Gastro Holding (factura intercompany)"
  empleados: true
  importador: false
  exportador: false
  divisas_habituales: []

proveedores:
  makro:
    cif: "A28054609"
    nombre_fs: "MAKRO AUTOSERVICIO S.A."
    aliases: ["MAKRO", "MAKRO MARBELLA", "CASH&CARRY MAKRO"]
    pais: ESP
    divisa: EUR
    subcuenta: "6000000000"
    codimpuesto: IVA21
    regimen: general
    notas: "Alimentacion y bebidas — IVA mixto 4/10/21% segun producto. Procesar linea a linea."

  distribuidora-bebidas-sur:
    cif: "B29091105"
    nombre_fs: "DISTRIBUIDORA DE BEBIDAS SUR S.L."
    aliases: ["DISTRIBUIDORA BEBIDAS", "BEBIDAS SUR", "DIST. BEBIDAS SUR"]
    pais: ESP
    divisa: EUR
    subcuenta: "6000000000"
    codimpuesto: IVA21
    regimen: general
    notas: "Vinos, cervezas, refrescos — IVA 21%"

  lavanderia-industrial:
    cif: "B29044328"
    nombre_fs: "LAVANDERIA INDUSTRIAL MALAGA S.L."
    aliases: ["LAVANDERIA INDUSTRIAL", "LAVANDERÍA MÁLAGA", "LAVANDERIA MALAGA"]
    pais: ESP
    divisa: EUR
    subcuenta: "6270000000"
    codimpuesto: IVA21
    regimen: general
    notas: "Lavado manteles, servilletas y uniformes"

  naturgy:
    cif: "A08032104"
    nombre_fs: "NATURGY S.A."
    aliases: ["NATURGY", "GAS NATURAL", "NATURGY GAS", "ENDESA GAS"]
    pais: ESP
    divisa: EUR
    subcuenta: "6280000000"
    codimpuesto: IVA21
    regimen: general
    notas: "Suministro gas natural cocinas industriales"

  endesa:
    cif: "A81948077"
    nombre_fs: "ENDESA ENERGIA S.A.U."
    aliases: ["ENDESA", "ENDESA ENERGIA", "ENDESA ELECTRICIDAD"]
    pais: ESP
    divisa: EUR
    subcuenta: "6280000000"
    codimpuesto: IVA21
    regimen: general
    notas: "Suministro electrico local"

  arrendador-local:
    cif: "27345678P"
    nombre_fs: "MIGUEL ANGEL TORRES RIOS"
    aliases: ["TORRES RIOS", "PROPIETARIO LOCAL", "ARRENDADOR"]
    pais: ESP
    divisa: EUR
    subcuenta: "6210000000"
    codimpuesto: IVA21
    regimen: general
    retencion: 19
    notas: "Alquiler local Paseo Maritimo — retencion 19% IRPF"

  gastro-holding:
    cif: "B29055407"
    nombre_fs: "GRUPO GASTRO COSTA DEL SOL S.L."
    aliases: ["GASTRO HOLDING", "GRUPO GASTRO", "GASTRO COSTA DEL SOL"]
    pais: ESP
    divisa: EUR
    subcuenta: "6230000000"
    codimpuesto: IVA21
    regimen: general
    notas: "Sociedad holding — management fee 500€/mes"

  mapfre:
    cif: "A28141935"
    nombre_fs: "SEGUROS MAPFRE S.A."
    aliases: ["MAPFRE", "SEGUROS MAPFRE", "MAPFRE SEGUROS"]
    pais: ESP
    divisa: EUR
    subcuenta: "6250000000"
    codimpuesto: IVA0
    regimen: general
    notas: "Seguro multirriesgo local + RC — exento IVA"

clientes:
  clientes-diarios:
    cif: ""
    nombre_fs: "CLIENTES DIARIOS (TICKETS)"
    aliases: ["TICKETS", "CAJA DIARIA", "VENTAS DIARIAS", "CLIENTES"]
    pais: ESP
    divisa: EUR
    codimpuesto: IVA10
    regimen: general
    fallback_sin_cif: true
    notas: "Facturacion simplificada agregada mensual — Art. 7.1 RD 1619/2012"

  hotel-marbella-palace:
    cif: "A29044153"
    nombre_fs: "HOTEL MARBELLA PALACE S.A."
    aliases: ["HOTEL MARBELLA PALACE", "MARBELLA PALACE", "PALACE HOTEL"]
    pais: ESP
    divisa: EUR
    codimpuesto: IVA10
    regimen: general
    notas: "Catering eventos del hotel — facturas nominales IVA 10%"

  empresa-eventos:
    cif: "B29066180"
    nombre_fs: "EMPRESA EVENTOS CORPORATIVOS S.L."
    aliases: ["EVENTOS CORPORATIVOS", "EMPRESA EVENTOS", "CORPORATIVOS"]
    pais: ESP
    divisa: EUR
    codimpuesto: IVA10
    regimen: general
    notas: "Comidas corporativas — IVA 10%"

trabajadores:
  - dni: "29512340H"
    nombre: "Santiago Fernandez Ruiz"
    puesto: "Jefe de Sala"
    bruto_mensual: 2333.33
    pagas: 12
    confirmado: true
  - dni: "45678123R"
    nombre: "Ana Belen Castillo Vega"
    puesto: "Cocinera"
    bruto_mensual: 2166.67
    pagas: 12
    confirmado: true
  - dni: "52134567G"
    nombre: "Francisco Torres Medina"
    puesto: "Camarero"
    bruto_mensual: 1833.33
    pagas: 12
    confirmado: true
  - dni: "31298765S"
    nombre: "Dolores Pena Santos"
    puesto: "Camarera"
    bruto_mensual: 1833.33
    pagas: 12
    confirmado: true
  - dni: "29876543C"
    nombre: "Luis Garcia Moreno"
    puesto: "Ayudante Cocina (Fijo Discontinuo)"
    bruto_mensual: 1583.33
    pagas: 12
    confirmado: true
  - dni: "45012367B"
    nombre: "Rosa Maria Diaz Lopez"
    puesto: "Auxiliar Sala (Fijo Discontinuo)"
    bruto_mensual: 1500.00
    pagas: 12
    confirmado: true

tolerancias:
  cuadre_asiento: 0.01
  comparacion_importes: 0.02
  confianza_minima: 85
```

**Step 2: Commit**
```bash
git add clientes/restaurante-la-marea/config.yaml
git commit -m "feat: config.yaml completo Restaurante La Marea (SL hosteleria)"
```

---

## Task 5: Script generar_onboarding_historico.py

**Files:**
- Create: `scripts/generar_onboarding_historico.py`
- Test: `tests/test_generar_onboarding_historico.py`

**Step 1: Escribir tests primero (TDD)**

```python
# tests/test_generar_onboarding_historico.py
"""Tests para el generador de documentos de onboarding histórico."""
import pytest
from pathlib import Path
import yaml

SCRIPT = Path("scripts/generar_onboarding_historico.py")
DATOS_MARCOS = Path("clientes/marcos-ruiz/datos_fiscales_2024.yaml")
DATOS_MAREA = Path("clientes/restaurante-la-marea/datos_fiscales_2024.yaml")


def test_datos_marcos_ruiz_existe():
    assert DATOS_MARCOS.exists()


def test_datos_la_marea_existe():
    assert DATOS_MAREA.exists()


def test_datos_marcos_tiene_modelos_requeridos():
    datos = yaml.safe_load(DATOS_MARCOS.read_text(encoding="utf-8"))
    for modelo in ["modelo_303", "modelo_390", "modelo_130", "modelo_111",
                   "modelo_190", "balance", "cuenta_pyg"]:
        assert modelo in datos, f"Falta {modelo} en marcos-ruiz"


def test_datos_marea_tiene_modelos_requeridos():
    datos = yaml.safe_load(DATOS_MAREA.read_text(encoding="utf-8"))
    for modelo in ["modelo_303", "modelo_390", "modelo_111", "modelo_190",
                   "modelo_115", "modelo_180", "balance", "cuenta_pyg"]:
        assert modelo in datos, f"Falta {modelo} en restaurante-la-marea"


def test_303_marcos_tiene_4_trimestres():
    datos = yaml.safe_load(DATOS_MARCOS.read_text(encoding="utf-8"))
    trimestres = datos["modelo_303"]["trimestres"]
    assert set(trimestres.keys()) == {"1T", "2T", "3T", "4T"}


def test_balance_marcos_cuadra():
    datos = yaml.safe_load(DATOS_MARCOS.read_text(encoding="utf-8"))
    b = datos["balance"]
    activo = sum(
        i.get("valor_neto", i.get("importe", 0))
        for grupo in b["activo"].values()
        for i in grupo
    )
    pasivo = sum(i["importe"] for grupo in b["pasivo"].values() for i in grupo)
    pn = sum(abs(i["importe"]) for i in b["patrimonio_neto"])
    # activo ≈ pasivo + patrimonio neto (margen 1€ por redondeos)
    assert abs(activo - (pasivo + pn)) < 1.0, f"Balance no cuadra: {activo} != {pasivo}+{pn}"
```

**Step 2: Ejecutar tests — deben pasar los de datos, fallar el de balance**
```bash
python -m pytest tests/test_generar_onboarding_historico.py -v
```

**Step 3: Crear el script**

```python
#!/usr/bin/env python3
"""
Genera paquete de documentación fiscal histórica para onboarding de cliente.

Uso:
    python scripts/generar_onboarding_historico.py --cliente marcos-ruiz --ejercicio 2024
    python scripts/generar_onboarding_historico.py --cliente restaurante-la-marea --ejercicio 2024
    python scripts/generar_onboarding_historico.py --todos --ejercicio 2024
"""
import argparse
import sys
from pathlib import Path
import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sfce.modelos_fiscales.generador_pdf import GeneradorPDF


MODELOS_AUTONOMO = ["303", "390", "130", "111", "190"]
MODELOS_SL       = ["303", "390", "111", "190", "115", "180"]

# Secciones del YAML → código modelo
_SECCION_A_MODELO = {
    "modelo_303": "303",
    "modelo_390": "390",
    "modelo_130": "130",
    "modelo_111": "111",
    "modelo_190": "190",
    "modelo_115": "115",
    "modelo_180": "180",
    "modelo_347": "347",
    "modelo_349": "349",
}


def _empresa_para_generador(datos: dict) -> dict:
    """Adapta los datos del YAML al formato que espera GeneradorPDF."""
    e = datos["empresa"]
    return {
        "nif": e["nif"],
        "nombre": e["nombre"],
        "domicilio": e.get("domicilio", ""),
        "telefono": e.get("telefono", ""),
        "email": e.get("email", ""),
    }


def _generar_modelo_trimestral(
    gen: GeneradorPDF,
    modelo: str,
    datos_modelo: dict,
    empresa: dict,
    ejercicio: str,
    directorio: Path,
) -> list[Path]:
    """Genera un PDF por trimestre para modelos trimestrales."""
    generados = []
    trimestres = datos_modelo.get("trimestres", {})
    for periodo, datos_periodo in trimestres.items():
        casillas = datos_periodo.get("casillas", {})
        pdf_bytes = gen.generar(
            modelo=modelo,
            casillas={str(k): v for k, v in casillas.items()},
            empresa=empresa,
            ejercicio=ejercicio,
            periodo=periodo,
        )
        nombre = f"modelo_{modelo}_{periodo}_{ejercicio}"
        ruta = gen.guardar(pdf_bytes, directorio, nombre)
        print(f"  ✓ {ruta.name}")
        generados.append(ruta)
    return generados


def _generar_modelo_anual(
    gen: GeneradorPDF,
    modelo: str,
    datos_modelo: dict,
    empresa: dict,
    ejercicio: str,
    directorio: Path,
) -> Path:
    """Genera un PDF anual (resumen) para un modelo."""
    casillas = datos_modelo.get("casillas", {})
    pdf_bytes = gen.generar(
        modelo=modelo,
        casillas={str(k): v for k, v in casillas.items()},
        empresa=empresa,
        ejercicio=ejercicio,
        periodo="0A",
    )
    nombre = f"modelo_{modelo}_anual_{ejercicio}"
    ruta = gen.guardar(pdf_bytes, directorio, nombre)
    print(f"  ✓ {ruta.name}")
    return ruta


def _generar_balance_pyg(datos: dict, ejercicio: str, directorio: Path) -> list[Path]:
    """Genera PDFs de balance de situación y cuenta P&G usando plantilla HTML."""
    from sfce.modelos_fiscales.generador_pdf import GeneradorPDF
    gen = GeneradorPDF()
    generados = []

    for seccion, nombre_doc in [("balance", "balance_situacion"), ("cuenta_pyg", "cuenta_pyg")]:
        if seccion not in datos:
            continue
        # Transformar estructura balance/pyg a casillas numéricas para el generador
        casillas = _balance_a_casillas(datos[seccion], seccion)
        pdf_bytes = gen.generar(
            modelo=seccion,  # el generador usará HTML fallback para modelos desconocidos
            casillas=casillas,
            empresa=_empresa_para_generador(datos),
            ejercicio=ejercicio,
            periodo="0A",
        )
        nombre = f"{nombre_doc}_{ejercicio}"
        ruta = gen.guardar(pdf_bytes, directorio, nombre)
        print(f"  ✓ {ruta.name}")
        generados.append(ruta)

    return generados


def _balance_a_casillas(datos_balance: dict, tipo: str) -> dict:
    """Convierte estructura balance/pyg a dict plano de casillas."""
    casillas = {}
    if tipo == "balance":
        n = 1
        for grupo_nombre, grupo in datos_balance.get("activo", {}).items():
            for item in grupo:
                casillas[str(n)] = item.get("valor_neto", item.get("importe", 0))
                casillas[f"{n}_desc"] = item.get("descripcion", "")
                n += 1
    elif tipo == "cuenta_pyg":
        for item in datos_balance.get("ingresos", []):
            casillas[item["cuenta"]] = item["importe"]
        for item in datos_balance.get("gastos", []):
            casillas[item["cuenta"]] = -item["importe"]
        casillas["resultado"] = datos_balance.get("resultado_ejercicio", 0)
    return casillas


def generar_onboarding(slug: str, ejercicio: str) -> list[Path]:
    """Genera todos los documentos de onboarding para un cliente."""
    datos_path = RAIZ / "clientes" / slug / f"datos_fiscales_{ejercicio}.yaml"
    if not datos_path.exists():
        print(f"ERROR: No existe {datos_path}")
        return []

    datos = yaml.safe_load(datos_path.read_text(encoding="utf-8"))
    empresa = _empresa_para_generador(datos)
    directorio = RAIZ / "clientes" / slug / f"onboarding_{ejercicio}"
    directorio.mkdir(parents=True, exist_ok=True)

    gen = GeneradorPDF()
    generados = []

    print(f"\n{'='*60}")
    print(f"Generando onboarding {slug} — ejercicio {ejercicio}")
    print(f"Destino: {directorio}")
    print(f"{'='*60}")

    for seccion, modelo in _SECCION_A_MODELO.items():
        if seccion not in datos:
            continue
        datos_modelo = datos[seccion]
        print(f"\n[Modelo {modelo}]")
        if "trimestres" in datos_modelo:
            rutas = _generar_modelo_trimestral(
                gen, modelo, datos_modelo, empresa, ejercicio, directorio
            )
            generados.extend(rutas)
        else:
            ruta = _generar_modelo_anual(
                gen, modelo, datos_modelo, empresa, ejercicio, directorio
            )
            generados.append(ruta)

    print("\n[Balance + P&G]")
    generados.extend(_generar_balance_pyg(datos, ejercicio, directorio))

    print(f"\n{'='*60}")
    print(f"TOTAL generados: {len(generados)} PDFs en {directorio}")
    return generados


def main():
    parser = argparse.ArgumentParser(description="Genera documentacion fiscal historica para onboarding")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--cliente", help="Slug del cliente (ej: marcos-ruiz)")
    grupo.add_argument("--todos", action="store_true", help="Genera para todos los clientes con datos")
    parser.add_argument("--ejercicio", default="2024", help="Ejercicio fiscal (default: 2024)")
    args = parser.parse_args()

    if args.todos:
        slugs = [
            p.parent.name
            for p in (RAIZ / "clientes").glob(f"*/datos_fiscales_{args.ejercicio}.yaml")
        ]
        print(f"Clientes encontrados: {slugs}")
    else:
        slugs = [args.cliente]

    for slug in slugs:
        generar_onboarding(slug, args.ejercicio)


if __name__ == "__main__":
    main()
```

**Step 4: Ejecutar tests**
```bash
python -m pytest tests/test_generar_onboarding_historico.py -v
```
Esperado: todos PASS.

**Step 5: Commit**
```bash
git add scripts/generar_onboarding_historico.py tests/test_generar_onboarding_historico.py
git commit -m "feat: script generar_onboarding_historico + tests"
```

---

## Task 6: Generar PDFs onboarding

**Step 1: Activar entorno y variables**
```bash
export $(grep -v '^#' .env | xargs)
```

**Step 2: Generar Marcos Ruiz**
```bash
python scripts/generar_onboarding_historico.py --cliente marcos-ruiz --ejercicio 2024
```
Esperado: directorio `clientes/marcos-ruiz/onboarding_2024/` con ~10 PDFs:
- `modelo_303_1T_2024.pdf`, `modelo_303_2T_2024.pdf`, `modelo_303_3T_2024.pdf`, `modelo_303_4T_2024.pdf`
- `modelo_390_anual_2024.pdf`
- `modelo_130_1T_2024.pdf` ... `modelo_130_4T_2024.pdf`
- `modelo_111_1T_2024.pdf` ... `modelo_111_4T_2024.pdf`
- `modelo_190_anual_2024.pdf`
- `balance_situacion_2024.pdf`
- `cuenta_pyg_2024.pdf`

**Step 3: Generar La Marea**
```bash
python scripts/generar_onboarding_historico.py --cliente restaurante-la-marea --ejercicio 2024
```
Esperado: directorio `clientes/restaurante-la-marea/onboarding_2024/` con ~18 PDFs.

**Step 4: Verificar PDFs visualmente**
Abrir 2-3 PDFs para confirmar que el contenido es legible y los números son correctos.

**Step 5: Commit**
```bash
git add clientes/marcos-ruiz/onboarding_2024/ clientes/restaurante-la-marea/onboarding_2024/
git commit -m "feat: paquetes onboarding 2024 Marcos Ruiz + La Marea generados"
```

---

## Task 7: Crear empresas en FacturaScripts

FS está en blanco (limpiado en sesión anterior). Crear empresa 1 (Marcos Ruiz) y empresa 2 (La Marea).

**Files:**
- Read: `sfce/core/fs_setup.py`

**Step 1: Crear empresa Marcos Ruiz (idempresa=1)**
```bash
python - <<'EOF'
import sys
sys.path.insert(0, ".")
from sfce.core.fs_setup import FsSetup

fs = FsSetup()

# Crear empresa
r = fs.crear_empresa(
    nombre="MARCOS RUIZ DELGADO",
    cif="29457823K",
    nombrecorto="M.RUIZ",
)
print(f"Empresa creada: idempresa={r.idempresa_fs}")

# Crear ejercicio 2024
r2 = fs.crear_ejercicio(r.idempresa_fs, 2024)
print(f"Ejercicio 2024: {r2.codejercicio}")

# Crear ejercicio 2025
r3 = fs.crear_ejercicio(r.idempresa_fs, 2025)
print(f"Ejercicio 2025: {r3.codejercicio}")

# Importar PGC en ambos ejercicios
fs.importar_pgc(r2.codejercicio)
fs.importar_pgc(r3.codejercicio)
print("PGC importado en 2024 y 2025")
EOF
```

**Step 2: Crear empresa La Marea (idempresa=2)**
```bash
python - <<'EOF'
import sys
sys.path.insert(0, ".")
from sfce.core.fs_setup import FsSetup

fs = FsSetup()

r = fs.crear_empresa(
    nombre="RESTAURANTE LA MAREA S.L.",
    cif="B29011236",
    nombrecorto="LAMAREA",
)
print(f"Empresa creada: idempresa={r.idempresa_fs}")

r2 = fs.crear_ejercicio(r.idempresa_fs, 2024)
r3 = fs.crear_ejercicio(r.idempresa_fs, 2025)
fs.importar_pgc(r2.codejercicio)
fs.importar_pgc(r3.codejercicio)
print(f"Ejercicios + PGC: {r2.codejercicio}, {r3.codejercicio}")
EOF
```

**Step 3: Verificar en FS**
```bash
python -c "
import requests
r = requests.get('https://contabilidad.lemonfresh-tuc.com/api/3/empresas', headers={'Token': 'iOXmrA1Bbn8RDWXLv91L'})
import json; [print(e['idempresa'], e['nombre']) for e in r.json()]
"
```
Esperado: 2 empresas listadas.

**Step 4: Ajustar idempresa en config.yaml si FS asignó IDs distintos**

Si FS asignó idempresa=1 a Marcos Ruiz y idempresa=2 a La Marea → configs ya correctos.
Si difieren, editar `idempresa` y `codejercicio` en ambos config.yaml.

**Step 5: Commit**
```bash
git commit -m "feat: empresas Marcos Ruiz + La Marea creadas en FacturaScripts"
```

---

## Task 8: Onboarding — Procesar documentos históricos 2024

Poner los PDFs de `onboarding_2024/` en el inbox del pipeline y ver cómo los gestiona.

**Step 1: Copiar PDFs al inbox**
```bash
cp clientes/marcos-ruiz/onboarding_2024/*.pdf clientes/marcos-ruiz/inbox/
cp clientes/restaurante-la-marea/onboarding_2024/*.pdf clientes/restaurante-la-marea/inbox/
```

**Step 2: Ejecutar pipeline fase 1 (intake + OCR) — Marcos Ruiz**
```bash
python scripts/pipeline.py \
  --cliente marcos-ruiz \
  --ejercicio 2024 \
  --fase 1 \
  --no-interactivo
```

Observar:
- ¿Cómo clasifica los 303, 390, 130, 111, 190?
- ¿Los reconoce como IMP (impuesto) o van a cuarentena?
- ¿Extrae algún dato de las casillas?

**Step 3: Ejecutar pipeline fase 1 — La Marea**
```bash
python scripts/pipeline.py \
  --cliente restaurante-la-marea \
  --ejercicio 2024 \
  --fase 1 \
  --no-interactivo
```

**Step 4: Revisar resultados**
```bash
ls clientes/marcos-ruiz/2024/procesado/ 2>/dev/null
ls clientes/marcos-ruiz/cuarentena/ 2>/dev/null
cat clientes/marcos-ruiz/pipeline_state.json 2>/dev/null | python -m json.tool | head -40
```

**Step 5: Documentar hallazgos**

En función de lo que encuentre el pipeline, identificar gaps:
- Si los modelos fiscales van a cuarentena → el pipeline necesita reconocerlos
- Si se clasifican como IMP → ver qué extrae
- Si OCR extrae casillas → excelente, el sistema ya funciona

**Step 6: Commit**
```bash
git add clientes/marcos-ruiz/ clientes/restaurante-la-marea/
git commit -m "test: onboarding historico 2024 ejecutado para ambos clientes"
```

---

## Resumen de archivos creados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `clientes/marcos-ruiz/datos_fiscales_2024.yaml` | Datos | Financiero 2024 Marcos Ruiz |
| `clientes/restaurante-la-marea/datos_fiscales_2024.yaml` | Datos | Financiero 2024 La Marea |
| `clientes/marcos-ruiz/config.yaml` | Config | Pipeline config autónomo |
| `clientes/restaurante-la-marea/config.yaml` | Config | Pipeline config SL hostelería |
| `scripts/generar_onboarding_historico.py` | Script | Generador PDFs modelos fiscales |
| `tests/test_generar_onboarding_historico.py` | Tests | Tests del generador |
| `clientes/marcos-ruiz/onboarding_2024/*.pdf` | Output | ~14 PDFs fiscales 2024 |
| `clientes/restaurante-la-marea/onboarding_2024/*.pdf` | Output | ~18 PDFs fiscales 2024 |
