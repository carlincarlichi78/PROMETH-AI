# Datos de Prueba SFCE - Documento de Diseño

> Generación de un dataset completo y realista para testear el SFCE end-to-end.

## Decisiones de diseño

| Decision | Eleccion | Razon |
|----------|----------|-------|
| Enfoque generacion | Plantillas HTML → PDF (weasyprint) | Maximo realismo visual, escala ilimitada, control total |
| Punto entrada | PDFs en inbox/ | Testear flujo completo desde Fase 0 (OCR) |
| Alta en FS | No — solo PDFs | El SFCE crea proveedores/clientes/asientos automaticamente |
| Errores | ~20% con errores deliberados tipificados | Verificar deteccion SFCE |
| Edge cases | ~15% con casos limite correctos pero complejos | Verificar robustez SFCE |
| Periodo | 2025 completo, con saldos apertura de cierre 2024 | Simulacro contable realista anual |

---

## 1. Universo de entidades (11)

### Sociedades Limitadas

| # | Entidad | Actividad | idempresa | Casuisticas clave |
|---|---------|-----------|-----------|-------------------|
| 1 | **AURORA DIGITAL SOLUTIONS S.L.** | Consultoria IT + desarrollo web | 3 | Retenciones IRPF ventas, intracomunitarias (AWS/Microsoft Ireland), gastos mixtos deducible parcial, leasing vehiculo, poliza credito |
| 2 | **DISTRIBUCIONES LEVANTE MEDITERRANEO S.L.** | Compra-venta alimentacion mayorista | 4 | Alto volumen, rappels, devoluciones, IVA 4%/10%/21%, importacion India (USD), confirming, nave hipotecada, flota vehiculos |

### Grupo empresarial (Gastro Costa del Sol)

| # | Entidad | Actividad | idempresa | Casuisticas clave |
|---|---------|-----------|-----------|-------------------|
| 3 | **GRUPO GASTRO COSTA DEL SOL S.L.** | Holding | 5 | Prestamos intercompany, dividendos con retencion 19%, management fees, poliza grupo, consolidacion |
| 4 | → **RESTAURANTE LA MAREA S.L.** | Restauracion | 6 | IVA 10% (comida) + 21% (bebidas), propinas, leasing cocina, 6 empleados convenio hosteleria |
| 5 | → **CHIRINGUITO SOL Y ARENA S.L.** | Restauracion estacional | 7 | Actividad abr-oct, licencia playa, fijos-discontinuos, altas/bajas SS estacionales, resultado negativo acumulado |
| 6 | → **CATERING COSTA EVENTS S.L.** | Catering eventos | 8 | Anticipos clientes, facturas a medida, depositos, eventos nocturnidad/festivos, prestamo cruzado con Chiringuito |

### Autonomos

| # | Entidad | Actividad | idempresa | Casuisticas clave |
|---|---------|-----------|-----------|-------------------|
| 7 | **MARCOS RUIZ DELGADO** | Fontaneria y reformas | 9 | Estimacion directa, modelo 130, retenciones ventas a empresas, facturas simplificadas a particulares, aprendiz contrato formacion |
| 8 | **ELENA NAVARRO PRECIADOS** | Fisioterapia (exenta) + pilates (21%) | 10 | Prorrata, gastos compartidos, exencion sanitaria, hipoteca local, colegio profesional |
| 9 | **JOSE ANTONIO BERMUDEZ FLORES** | Olivar + produccion aceite | 11 | REAGP, compensacion 12%, jornaleros eventuales agrarios, seguro cosechas, existencias aceite, hipoteca finca rustica |
| 10 | **FRANCISCO MORA CASTILLO** | Bar/cafeteria | 12 | Estimacion objetiva (MODULOS), IVA regimen simplificado, modelo 131, no lleva contabilidad convencional, maquina tragaperras |

### Otras entidades

| # | Entidad | Actividad | idempresa | Casuisticas clave |
|---|---------|-----------|-----------|-------------------|
| 11 | **COMUNIDAD DE PROPIETARIOS MIRADOR DEL MAR** | Gestion edificio residencial | 13 | Cuotas comunidad, derramas, portero (convenio fincas urbanas), IVA parcial, fondo reserva, prestamo ascensor, FEDER rehabilitacion |

---

## 2. Proveedores y clientes por entidad

### 2.1 AURORA DIGITAL SOLUTIONS S.L.

**Proveedores (6)**:
- Amazon Web Services (IRL) — hosting, intracomunitaria, EUR
- Microsoft Ireland (IRL) — licencias 365, intracomunitaria, EUR
- Vodafone España — telefonia/internet, IVA 21%
- Northgate Renting (ESP) — renting vehiculo, IVA 21%
- Mutua Madrileña — seguro RC + salud colectivo, exento IVA
- Ofiprix Material Oficina — consumibles, IVA 21%

**Clientes (4)**:
- Ayuntamiento de Valencia — desarrollo web, retencion 15%
- Clinica Dental Sonrisa S.L. — mantenimiento IT, nacional
- TechBerlin GmbH (DEU) — consultoria, intracomunitaria
- Particulares varios — webs pequeñas, sin retencion

**Servicios profesionales**:
- Gestoria Martinez y Asociados — asesoria fiscal, retencion 15%
- Bufete Juridico Ramirez — abogado, retencion 15%
- Prevencion Global S.L. — PRL

### 2.2 DISTRIBUCIONES LEVANTE MEDITERRANEO S.L.

**Proveedores (6)**:
- Cooperativa Agricola La Huerta — frutas/verduras, IVA 4% y 10%
- Frigorificos del Sur S.L. — transporte refrigerado, IVA 21%
- Envases Plasticos Alicante — packaging, IVA 21%
- Importadora Especias Bombay (IND) — especias, extracomunitaria, USD, DUA
- Repsol Gasolinera — combustible flota, IVA 21%
- Fertiberia — productos limpieza almacen, IVA 21%

**Clientes (4)**:
- Supermercados Consum S. Coop. — rappels trimestrales, devoluciones
- Hosteleria Costa Blanca S.L. — devoluciones frecuentes
- Restaurante El Faro — cliente regular
- Exportaciones Maghreb S.L. — exportacion Marruecos, IVA 0%

### 2.3 GRUPO GASTRO COSTA DEL SOL S.L. (holding)

**Proveedores**:
- Gestoria Costa del Sol — asesoria grupo, retencion 15%
- Seguros Mapfre — poliza grupo (RC + multirriesgo)
- Google Ads — publicidad grupo, intracomunitaria (Google Ireland)

**Clientes (internos)**:
- La Marea S.L. — management fee mensual
- Chiringuito Sol y Arena S.L. — management fee mensual
- Catering Costa Events S.L. — management fee mensual

### 2.4 RESTAURANTE LA MAREA S.L.

**Proveedores (5)**:
- Makro España — alimentacion, IVA 4%/10%/21%
- Distribuidora de Bebidas Sur — bebidas, IVA 21%
- Lavanderia Industrial Malaga — manteles/uniformes, IVA 21%
- Gas Natural Fenosa — gas cocina, IVA 21%
- Grupo Gastro Holding — management fee, intereses prestamo

**Clientes (3)**:
- Clientes diarios (tickets simplificados agregados mensual)
- Hotel Marbella Palace — servicio catering puntual
- Empresa eventos corporativos

### 2.5 CHIRINGUITO SOL Y ARENA S.L.

**Proveedores (4)**:
- Makro España — alimentacion estacional
- Ayuntamiento Marbella — canon licencia playa
- Alquiler mobiliario terraza (renting estacional)
- Grupo Gastro Holding — management fee, prestamo intercompany

**Clientes (2)**:
- Ventas diarias (tickets simplificados)
- Eventos privados playa (factura)

### 2.6 CATERING COSTA EVENTS S.L.

**Proveedores (4)**:
- Makro España — alimentacion
- Alquiler menaje eventos S.L. — vajilla/cristaleria
- Grupo Gastro Holding — management fee, prestamo
- Chiringuito Sol y Arena — prestamo cruzado estacional

**Clientes (3)**:
- Bodas y eventos particulares (anticipos + factura final)
- Empresas eventos corporativos (factura estandar)
- Ayuntamiento Marbella — catering fiestas municipales, retencion

### 2.7 MARCOS RUIZ DELGADO

**Proveedores (5)**:
- Saneamientos Perez — materiales fontaneria, IVA 21%
- Leroy Merlin — tickets simplificados, IVA 21%
- Repsol — gasolina furgoneta, IVA 21%
- Mutualidad Autonomos (RETA) — cuota mensual
- Gestoria Lopez — asesoria, retencion 15%

**Clientes (3)**:
- Comunidad Propietarios Edificio Sol — retención 15%
- Particulares varios — facturas simplificadas
- Constructora Hernandez S.L. — retencion 15%

### 2.8 ELENA NAVARRO PRECIADOS

**Proveedores (5)**:
- Quirumed — equipamiento sanitario, IVA 21%
- Farmacia Central — material sanitario, IVA 4%
- Propietario local (persona fisica) — alquiler con retencion 19%
- Spotify Business — musica ambiente, intracomunitaria (Spotify Sweden)
- Colegio Fisioterapeutas Andalucia — cuota anual, exenta

**Clientes (3)**:
- Pacientes fisioterapia — facturas exentas IVA
- Alumnos pilates — facturas con 21% IVA
- Club Deportivo Municipal — servicio mixto (fisio exenta + pilates 21%)

### 2.9 JOSE ANTONIO BERMUDEZ FLORES

**Proveedores (5)**:
- Fertiberia — fertilizantes/fitosanitarios, IVA 21%
- Talleres Agricolas Jaen — reparacion maquinaria, IVA 21%
- Comunidad Regantes Sierra Magina — cuota riego
- Gasoil Agricola Distribuidor — gasoil bonificado, IVA 21%
- Mutualidad Autonomos (RETA) — cuota mensual agraria

**Clientes (3)**:
- Cooperativa Oleicola Sierra Magina — compensacion REAGP 12%
- Aceites Jaen Premium S.L. — venta directa aceite
- Venta mercadillo local — tickets simplificados

### 2.10 FRANCISCO MORA CASTILLO

**Proveedores (5)**:
- Distribuidora Bebidas Andalucia — cervezas/refrescos, IVA 21%
- Makro España — alimentacion bar, IVA 4%/10%/21%
- Propietario local (persona fisica) — alquiler con retencion 19%
- Suministros varios (luz, agua, gas)
- Gestoria Lopez — asesoria, retencion 15%

**Clientes**:
- Ventas diarias no desglosadas (regimen simplificado, no emite facturas individuales)
- Maquina tragaperras — ingreso fijo mensual operador

### 2.11 COMUNIDAD PROPIETARIOS MIRADOR DEL MAR

**Proveedores (5)**:
- Empresa limpieza Limpisa S.L. — limpieza zonas comunes, IVA 21%
- Electricidad Endesa — suministro zonas comunes, IVA 21%
- Ascensores Otis — mantenimiento, IVA 21%
- Jardineria Verde S.L. — mantenimiento jardin, IVA 21%
- Administrador fincas — honorarios, retencion 15%

**Ingresos**:
- 24 propietarios — cuotas mensuales ordinarias
- Derramas extraordinarias (ascensor, fachada)
- Alquiler local comercial planta baja — con IVA 21% + retencion 19%

---

## 3. Productos financieros

### Por entidad

| Entidad | Producto | Importe | Plazo | Cuota mensual aprox | Cuenta contable |
|---------|----------|---------|-------|---------------------|-----------------|
| Aurora Digital | Prestamo ICO digitalizacion | 30.000€ | 5 años | 550€ | 1700/5200 |
| Aurora Digital | Poliza credito | 30.000€ limite | Renovable anual | Intereses variable | 5201 |
| Aurora Digital | Leasing vehiculo | 28.000€ | 4 años | 620€ | 1740/5240 |
| Aurora Digital | Renting equipos informaticos | 800€/mes | 3 años | 800€ | 621 (gasto) |
| Distrib. Levante | Prestamo circulante | 150.000€ | 3 años | 4.500€ | 1700/5200 |
| Distrib. Levante | Hipoteca nave | 320.000€ (pte 180.000€) | 15 años | 1.400€ | 1705/5205 |
| Distrib. Levante | Leasing camara frigorifica | 45.000€ | 5 años | 830€ | 1740/5240 |
| Distrib. Levante | Renting 3 furgonetas | 1.200€/mes total | 4 años | 1.200€ | 621 |
| Distrib. Levante | Linea descuento comercial | 80.000€ limite | Renovable | Comision + intereses | 5208 |
| Distrib. Levante | Confirming | Variable | Rotativo | Comision 0.5% | 400/5201 |
| Marcos Ruiz | Prestamo personal furgoneta | 15.000€ (pte 6.500€) | 5 años | 280€ | 1700/5200 |
| Marcos Ruiz | Renting herramientas Hilti | 150€/mes | 2 años | 150€ | 621 |
| Elena Navarro | Hipoteca local comercial | 120.000€ (pte 95.000€) | 20 años | 580€ | 1705/5205 |
| Elena Navarro | Microcredito ICO | 12.000€ (pte 8.000€) | 4 años | 280€ | 1700/5200 |
| Elena Navarro | Leasing equipamiento clinica | 22.000€ | 5 años | 400€ | 1740/5240 |
| Jose Antonio | Prestamo agrario subvencionado | 25.000€ | 7 años | 320€ | 1700/5200 |
| Jose Antonio | Hipoteca finca rustica | 80.000€ (pte 55.000€) | 20 años | 380€ | 1705/5205 |
| Jose Antonio | Leasing tractor | 35.000€ | 6 años | 520€ | 1740/5240 |
| Comunidad Mirador | Prestamo ascensor | 30.000€ (pte 22.000€) | 8 años | 340€ | 1700/5200 |
| Gastro Holding | Poliza credito grupo | 200.000€ limite | Renovable | Variable | 5201 |
| La Marea | Leasing cocina industrial | 30.000€ (pte 24.000€) | 5 años | 550€ | 1740/5240 |
| Chiringuito | Renting mobiliario terraza | 600€/mes (abr-oct) | Estacional | 600€ | 621 |
| Catering Costa | Renting furgoneta | 450€/mes | 4 años | 450€ | 621 |
| Francisco Mora | Prestamo reforma bar | 18.000€ | 5 años | 340€ | 1700/5200 |

### Operaciones intercompany (Grupo Gastro)

| De | A | Tipo | Importe | Interes | Plazo |
|----|---|------|---------|---------|-------|
| Holding | La Marea | Prestamo | 15.000€ | Euribor+2% | 3 años |
| Holding | Chiringuito | Prestamo | 8.000€ | Euribor+2% | 2 años |
| Holding | Catering | Prestamo | 10.000€ | Euribor+2% | 3 años |
| Catering | Chiringuito | Prestamo estacional | 5.000€ | 3% fijo | 6 meses (abr-oct) |

### Dividendos (Grupo Gastro)

| De | A | Importe bruto | Retencion 19% | Neto |
|----|---|---------------|---------------|------|
| La Marea → Holding | (100%) | 12.000€ | 2.280€ | 9.720€ |
| Catering → Holding | (100%) | 6.000€ | 1.140€ | 4.860€ |
| Chiringuito → Holding | — | 0€ (perdidas) | — | — |
| Holding → Socio A (60%) | Persona fisica | 10.800€ | 2.052€ | 8.748€ |
| Holding → Socio B (40%) | Persona fisica | 7.200€ | 1.368€ | 5.832€ |

### Comisiones bancarias (todas las entidades)

| Tipo comision | Frecuencia | Importe tipico | Entidades |
|---------------|------------|----------------|-----------|
| Mantenimiento cuenta | Trimestral | 15-30€ | Todas |
| Transferencias | Por operacion | 0.50-3€ | Todas |
| Transferencia internacional | Por operacion | 15-25€ | Aurora, Distrib. |
| Comision TPV/datafono | Mensual (% ventas) | 0.5-1.5% | Restaurantes, Elena (pilates), Francisco |
| Comision apertura poliza | Anual | 0.5% limite | Aurora, Holding, Distrib. |
| Comision no disposicion | Trimestral | 0.15% no dispuesto | Aurora, Holding |
| Comision descuento comercial | Por remesa | 0.5% + intereses | Distrib. |
| Comision confirming | Por operacion | 0.3-0.5% | Distrib. |
| Cambio divisa | Por operacion | 0.5-1% | Distrib. (USD), Aurora (USD puntual) |

---

## 4. Personal y obligaciones laborales

### Plantilla por entidad

| Entidad | Empleados | Contratos | Convenio | Particularidades |
|---------|-----------|-----------|----------|------------------|
| Aurora Digital | 4 | 3 indefinidos + 1 practicas | Consultoria TIC | Teletrabajo (compensacion 55€/mes), formacion FUNDAE |
| Distrib. Levante | 8 | 6 indefinidos + 2 temporales campaña | Comercio alimentacion | Horas extra, plus transporte, dietas repartidores |
| Marcos Ruiz | 1 | Formacion en alternancia | Construccion | Bonificacion SS contrato formacion |
| Elena Navarro | 1 | Parcial indefinido (20h/semana) | Oficinas y despachos | Reduccion jornada |
| Jose Antonio | 3-5 estacionales | Eventuales agrarios (oct-ene) | Agrario | Regimen especial agrario SS, jornadas reales |
| Francisco Mora | 1 | Indefinido | Hosteleria | Turnicidad, festivos |
| Comunidad Mirador | 1 | Indefinido | Empleados fincas urbanas | Vivienda porteria como salario especie |
| Gastro Holding | 2 | Indefinidos (1 alta direccion) | Oficinas | Bonus anual directora, regimen especial alta direccion |
| La Marea | 6 | 4 indefinidos + 2 fijos-discontinuos | Hosteleria | Propinas, turnicidad, nocturnidad fin semana |
| Chiringuito | 4 | Fijos-discontinuos (abr-oct) | Hosteleria | Altas/bajas estacionales, desempleo parcial oct-mar |
| Catering Costa | 3 | Indefinidos | Hosteleria | Horas extra eventos, nocturnidad, festivos |

**Total empleados**: ~34 personas → ~34 nominas/mes → ~408 nominas/año

### Documentos laborales mensuales por entidad

- Nominas individuales (1 por empleado)
- RLC (cuota patronal SS)
- RNT (detalle por trabajador)

### Documentos laborales periodicos

- Modelo 111 trimestral (retenciones IRPF nominas + profesionales)
- Modelo 190 anual
- Pagas extra: junio y diciembre (salvo prorrateadas)
- Finiquitos cuando aplique (temporales Distrib., fin temporada Chiringuito)
- Certificados retenciones anuales

---

## 5. Gastos recurrentes (todas las entidades)

### Suministros (mensuales)

| Tipo | Entidades | IVA | Importe tipico |
|------|-----------|-----|----------------|
| Electricidad | Todas | 21% (10% hasta jun 2025 si aplica) | 80-800€ segun entidad |
| Agua | Todas con local | 10% | 30-150€ |
| Gas natural | Restaurantes, Elena, Francisco | 21% | 50-400€ |
| Telefono/Internet | Todas | 21% | 30-120€ |
| Gasolina/gasoil | Con vehiculos | 21% | 100-600€ |

### Seguros (anuales/trimestrales)

| Tipo | Entidades | IVA | Importe anual |
|------|-----------|-----|---------------|
| RC profesional | Aurora, Elena, Marcos | Exento | 300-1.200€ |
| Multirriesgo local/nave | Todas con local | Exento (IPS) | 400-2.000€ |
| Vehiculos (flota) | Distrib., La Marea, Marcos | Exento (IPS) | 500-3.000€ |
| Salud colectivo | Aurora (beneficio social) | Exento | 2.400€ |
| D&O directivos | Holding | Exento | 800€ |
| Accidentes convenio | Restaurantes, Distrib. | Exento | 600-1.500€ |
| Seguro cosechas | Jose Antonio | Exento (Agroseguro) | 1.200€ |
| Seguro edificio | Comunidad | Exento | 2.800€ |

### Impuestos y tasas (anuales)

| Tipo | Entidades | Importe tipico |
|------|-----------|----------------|
| IAE | S.L. facturacion >1M (Distrib.) | 800-2.000€ |
| IBI | Con inmuebles propios/alquilados | 200-3.000€ |
| Tasa basuras | Con local | 100-400€ |
| Tasa vado | Con acceso vehicular | 80-200€ |
| IVTM (vehiculos) | Con vehiculos propios | 60-200€/vehiculo |
| Licencia actividad/playa | Chiringuito | 8.000€/temporada |

### Servicios profesionales (mensuales/puntuales)

| Tipo | Entidades | Retencion | Importe |
|------|-----------|-----------|---------|
| Gestoria/asesoria fiscal | Todas | 15% | 100-400€/mes |
| Abogado | Puntual (Aurora, Distrib.) | 15% | 500-2.000€ |
| Notaria | Puntual (hipotecas, constituciones) | — | 300-800€ |
| Registro mercantil | S.L. anuales | — | 50-100€ |
| PRL | Con empleados | — | 200-800€/año |
| Administrador fincas | Comunidad | 15% | 250€/mes |

---

## 6. Subvenciones y ayudas

| Entidad | Subvencion | Importe | Tipo | Tratamiento contable |
|---------|------------|---------|------|---------------------|
| Aurora Digital | Kit Digital | 12.000€ (2 pagos) | No reintegrable capital | 130/131 (subvencion oficial capital) → traspaso 746 segun amortizacion |
| Distrib. Levante | Subvencion contratacion autonomica | 4.000€ por 2 empleados | No reintegrable explotacion | 740 (subvencion explotacion) |
| Jose Antonio | PAC (Politica Agraria Comun) | 3.500€/año | No reintegrable explotacion | 740 |
| Jose Antonio | Ayuda Agroseguro | 50% prima seguro cosechas | No reintegrable explotacion | 740 |
| Marcos Ruiz | Tarifa plana autonomos (residual) | Reduccion cuota SS | Bonificacion | Menor gasto SS |
| Comunidad Mirador | FEDER rehabilitacion fachada | 15.000€ | No reintegrable capital | 130/131 → traspaso 746 |
| Francisco Mora | Ayuda autonomos hosteleroa COVID (residual) | 2.000€ | No reintegrable explotacion | 740 |

---

## 7. Historial 2024 (saldos iniciales)

Cada entidad arranca 2025 con cierre contable realista de 2024.

### Sociedades Limitadas → Modelo 200 + Balance + PyG + Cuentas Anuales

**Aurora Digital S.L.**
- Activo: servidores (15.000€ - amort. acum. 6.000€), vehiculo leasing (22.000€ - amort. 5.500€), clientes pendientes cobro (8.500€), tesoreria (12.000€)
- Pasivo: prestamo ICO (24.000€ pte, 6.000€ c/p + 18.000€ l/p), leasing (22.400€ pte), proveedores (3.200€), HP acreedora IVA T4 (1.800€)
- PN: capital 3.000€, reservas 15.000€, resultado 2024: +18.500€

**Distribuciones Levante S.L.**
- Activo: nave (320.000€ - amort. 64.000€), flota (45.000€ - amort. 18.000€), camara frigorifica leasing (45.000€ - amort. 9.000€), existencias (85.000€), clientes (42.000€), provision insolvencia (-3.500€), tesoreria (25.000€)
- Pasivo: hipoteca (180.000€), prestamo circulante (120.000€), leasing (36.000€), poliza credito dispuesta (45.000€), proveedores (38.000€), HP acreedora (12.000€)
- PN: capital 10.000€, reservas 80.000€, resultado 2024: +42.000€

**Grupo Gastro Holding S.L.**
- Activo: participaciones filiales (3 × 3.000€ nominal), prestamos a filiales (33.000€), tesoreria (18.000€)
- Pasivo: poliza credito dispuesta (60.000€), HP acreedora (2.400€)
- PN: capital 12.000€, reservas 8.000€, resultado 2024: +15.000€

**La Marea S.L.**
- Activo: cocina industrial leasing (30.000€ - amort. 6.000€), reforma (18.000€ - amort. 3.600€), existencias bar (4.500€), tesoreria (8.000€)
- Pasivo: leasing (24.000€), deuda holding (15.000€), proveedores (5.200€)
- PN: capital 3.000€, reservas 5.000€, resultado 2024: +12.000€

**Chiringuito Sol y Arena S.L.**
- Activo: deposito licencia playa (2.000€), tesoreria (3.500€)
- Pasivo: deuda holding (8.000€), proveedores (1.800€)
- PN: capital 3.000€, resultado negativo acumulado (-4.200€), resultado 2024: -1.500€

**Catering Costa Events S.L.**
- Activo: utensilios cocina (6.000€ - amort. 1.200€), clientes anticipos pendientes ejecutar (3.500€), tesoreria (5.000€)
- Pasivo: deuda holding (10.000€), proveedores (2.800€)
- PN: capital 3.000€, reservas 2.000€, resultado 2024: +6.000€

### Autonomos → Modelo 100 + Libro bienes inversion

**Marcos Ruiz**
- Bienes inversion: furgoneta (12.000€, amort. acum. 4.800€, pte prestamo 6.500€), herramientas varias (3.000€, amort. 1.500€)
- Rendimiento neto 2024: +22.000€
- Pagos fraccionados 130 realizados: 4 × 880€

**Elena Navarro**
- Bienes inversion: equipamiento clinica (18.000€, amort. acum. 3.600€), leasing equipos (22.000€, amort. 4.400€)
- Hipoteca local: pendiente 95.000€
- Microcredito ICO: pendiente 8.000€
- Rendimiento neto 2024: fisioterapia +28.000€, pilates +12.000€
- Prorrata 2024 definitiva: 35% (pilates sobre total)

**Jose Antonio Bermudez**
- Bienes inversion: tractor (35.000€, amort. acum. 28.000€ → 80%), aperos (8.000€, amort. 4.000€)
- Existencias: 12.000 litros aceite campaña anterior (valoracion: 36.000€)
- Finca rustica: hipoteca pendiente 55.000€
- Prestamo agrario: pendiente 20.000€
- Rendimiento neto 2024: +18.000€ (REAGP)

**Francisco Mora**
- Bienes inversion: cafetera industrial (4.500€, amort. 900€), mobiliario bar (6.000€, amort. 1.200€), reforma bar (18.000€, amort. 3.600€)
- Prestamo reforma: pendiente 14.500€
- Rendimiento neto por modulos 2024: +16.000€ (calculado por modulos, no contabilidad)
- Cuota IVA simplificado 2024: 4 × 680€

### Comunidad Propietarios → Acta + Estado cuentas

**Comunidad Mirador del Mar**
- Fondo reserva: 35.000€
- Prestamo ascensor: pendiente 22.000€
- Cuotas pendientes cobro (3 vecinos morosos): 2.700€
- Saldo cuenta mantenimiento: 8.500€
- Subvencion FEDER pendiente cobro: 7.500€ (segundo plazo)

---

## 8. Catalogo de errores a inyectar

### Errores (el SFCE debe DETECTAR y BLOQUEAR)

| ID | Error | Descripcion | Ejemplo concreto | % inyeccion |
|----|-------|-------------|------------------|-------------|
| E01 | CIF invalido | Letra/digito control incorrecto | B1399551**8** en vez de B1399551**9** | 2% |
| E02 | IVA mal calculado | Resultado IVA no coincide con base × tipo | 1.000 × 21% = 215€ | 3% |
| E03 | Total no cuadra | Base + IVA + recargos ≠ total factura | 54.45€ pero total dice 55.00€ | 2% |
| E04 | Factura duplicada | Mismo nº factura + proveedor + fecha | Dos veces factura VF-8834 | 2% |
| E05 | Fecha fuera ejercicio | Factura 2024 en inbox 2025 | Fecha 28/12/2024 en carpeta 2025 | 1% |
| E06 | Retencion incorrecta | Porcentaje IRPF erroneo | 7% en vez de 15%, o retencion en no obligado | 2% |
| E07 | Tipo IVA incorrecto | IVA equivocado para el producto/servicio | 21% en pan (deberia 4%) | 2% |
| E08 | Divisa sin tipo cambio | Factura USD sin indicar conversion | Factura India sin tasaconv | 1% |
| E09 | Numero factura ausente | PDF sin numero visible | Proveedor descuidado | 1% |
| E10 | Datos emisor incompletos | Falta CIF, direccion o nombre fiscal | Solo nombre comercial, sin CIF | 1% |
| E11 | IVA en operacion exenta | IVA donde no deberia haber | Fisioterapia con 21% IVA | 1% |
| E12 | Intracomunitaria mal | Falta inversion sujeto pasivo o mencion | AWS sin "operacion intracomunitaria" | 1% |
| E13 | Cuota SS incorrecta | Base cotizacion mal calculada en RLC | Base reguladora no coincide con nomina | 1% |
| E14 | Nomina sin retencion | IRPF 0% sin causa justificada | Empleado normal sin comunicacion modelo 145 | 0.5% |
| E15 | Factura a nombre erroneo | Persona fisica vs S.L. | Factura a "Juan Garcia" pero es de "La Marea S.L." | 0.5% |

### Edge cases (correctos pero complejos — el SFCE debe PROCESAR bien)

| ID | Caso | Descripcion | Entidad principal |
|----|------|-------------|-------------------|
| EC01 | Factura multimoneda | USD con tipo cambio BCE del dia | Distrib. Levante |
| EC02 | Factura 3 tipos IVA | Lineas al 4%, 10% y 21% en misma factura | Distrib. Levante |
| EC03 | Nota credito parcial | Devolucion de 3 de 20 unidades | Distrib. → Consum |
| EC04 | Rappel trimestral | Factura negativa por volumen acumulado | Distrib. → Consum |
| EC05 | Prorrata | Gasto compartido fisio/pilates 60/40 | Elena Navarro |
| EC06 | Compensacion REAGP | Factura con 12% compensacion (no IVA) | Jose Antonio |
| EC07 | Leasing valor residual | Ultima cuota con opcion compra | Aurora (vehiculo) |
| EC08 | Subvencion capital | Kit Digital 12.000€ en 2 pagos | Aurora Digital |
| EC09 | Intracomunitaria completa | Inversion sujeto pasivo + autoliquidacion 472/477 | Aurora (AWS/Microsoft) |
| EC10 | Retencion arrendamiento | Alquiler con 19% IRPF arrendador | Elena, Marcos, Francisco |
| EC11 | Factura simplificada | Ticket sin datos receptor, <400€ | Marcos (Leroy Merlin), Francisco |
| EC12 | Anticipo + factura final | 30% anticipo → factura descontando anticipo | Catering (evento) |
| EC13 | Prestamo intercompany | Holding→filial con interes mercado | Grupo Gastro |
| EC14 | Dividendo con retencion | Doble nivel: filial→holding, holding→socio | Grupo Gastro |
| EC15 | Derrama extraordinaria | Cuota extra sin IVA, aprobada en junta | Comunidad |
| EC16 | Jornalero eventual | Alta/baja SS mismo mes, regimen agrario | Jose Antonio |
| EC17 | Factura proforma | No contabilizable (se confunde con factura) | Aurora |
| EC18 | DUA importacion | IVA diferido en importacion extracomunitaria | Distrib. Levante |
| EC19 | Confirming/factoring | Cesion credito con descuento financiero | Distrib. Levante |
| EC20 | Multa no deducible | Sancion trafico, gasto fiscal no deducible | La Marea |
| EC21 | Modulos IVA simplificado | Cuota fija trimestral, regularizacion T4 | Francisco Mora |
| EC22 | Venta inmovilizado | Tractor viejo con plusvalia/minusvalia | Jose Antonio |
| EC23 | Prestamo cruzado estacional | Catering→Chiringuito abr-oct | Grupo Gastro |
| EC24 | Salario en especie | Vivienda porteria como retribucion | Comunidad Mirador |
| EC25 | Factura con recargo equivalencia | Si algun cliente de Distrib. es comerciante minorista | Distrib. Levante |

---

## 9. Distribucion temporal 2025

### Calendario de intensidad por mes

| Mes | Actividad general | Eventos especiales |
|-----|-------------------|--------------------|
| Ene | Media | Apertura ejercicio, suministros dic, SS dic, IBI 1er plazo |
| Feb | Media-baja | Operaciones regulares |
| Mar | Alta | Cierre T1, modelos 303/111/130/131, mas facturacion |
| Abr | Media | Inicio temporada Chiringuito, altas SS estacionales, PAC Jose Antonio |
| May | Media | Operaciones regulares, Kit Digital 1er pago Aurora |
| Jun | Alta | Pagas extra, cierre T2, pico restaurantes, modelos trimestrales |
| Jul | Variable | Pico restaurantes/chiringuito, minimo Aurora (vacaciones) |
| Ago | Baja-variable | Vacaciones general, pico chiringuito, minimo actividad oficina |
| Sep | Media-alta | Vuelta actividad, fin temporada chiringuito inicia, modelos T3 |
| Oct | Alta | Cosecha aceituna Jose Antonio, altas jornaleros, cierre T3, bajas SS chiringuito |
| Nov | Alta | Campaña navidad Distrib. Levante, mas facturacion |
| Dic | Muy alta | Pagas extra, cierre ejercicio, amortizaciones, provisiones, inventario existencias, dividendos grupo, regularizacion IVA modulos Francisco |

### Distribucion documentos por trimestre (~100 docs/entidad)

| Trimestre | % docs | Tipos predominantes |
|-----------|--------|---------------------|
| T1 (ene-mar) | 25% | Facturas regulares + cierre trimestral |
| T2 (abr-jun) | 25% | + pagas extra + estacionalidad |
| T3 (jul-sep) | 20% | Menor actividad oficina, pico hosteleria |
| T4 (oct-dic) | 30% | Cierre ejercicio, amortizaciones, provisiones, campañas |

---

## 10. Arquitectura del generador

### Estructura de archivos

```
tests/
└── datos_prueba/
    ├── generador/
    │   ├── motor.py                  # Orquestador principal CLI
    │   ├── datos/
    │   │   ├── empresas.yaml         # 11 entidades + proveedores + clientes + empleados
    │   │   ├── saldos_2024.yaml      # Balances apertura por entidad
    │   │   ├── catalogo_errores.yaml # E01-E15 con probabilidades y parametros
    │   │   └── edge_cases.yaml       # EC01-EC25 con distribucion y parametros
    │   ├── plantillas/
    │   │   ├── factura_estandar.html
    │   │   ├── factura_simplificada.html
    │   │   ├── factura_extranjera.html
    │   │   ├── factura_servicios.html
    │   │   ├── factura_restauracion.html
    │   │   ├── nota_credito.html
    │   │   ├── nomina.html
    │   │   ├── rlc_ss.html
    │   │   ├── recibo_bancario.html
    │   │   ├── impuesto_tasa.html
    │   │   ├── subvencion.html
    │   │   ├── recibo_suministro.html
    │   │   └── dua_importacion.html
    │   ├── generadores/
    │   │   ├── gen_facturas.py       # Facturas compra + venta
    │   │   ├── gen_nominas.py        # Nominas + SS (RLC/RNT)
    │   │   ├── gen_bancarios.py      # Prestamos, leasing, comisiones, confirming
    │   │   ├── gen_impuestos.py      # IBI, IAE, tasas, multas
    │   │   ├── gen_suministros.py    # Luz, agua, gas, telefono
    │   │   ├── gen_seguros.py        # Polizas y recibos
    │   │   ├── gen_subvenciones.py   # Resoluciones y pagos
    │   │   ├── gen_intercompany.py   # Prestamos grupo, dividendos, management fees
    │   │   └── gen_errores.py        # Inyector de errores post-generacion
    │   ├── utils/
    │   │   ├── cif.py                # Genera/valida CIF/NIF realistas
    │   │   ├── fechas.py             # Distribucion temporal por trimestre y mes
    │   │   ├── importes.py           # Calculo IVA/IRPF/SS/REAGP coherente
    │   │   ├── pdf_renderer.py       # HTML→PDF con weasyprint
    │   │   └── ruido.py              # Variacion visual (sellos, firmas, rotacion, manchas)
    │   └── css/
    │       ├── base.css
    │       └── variantes/
    │           ├── corporativo.css   # Estilo empresa grande
    │           ├── autonomo.css      # Estilo factura autonomo
    │           ├── administracion.css # Estilo documentos oficiales
    │           └── extranjero.css    # Estilo factura internacional
    │
    └── salida/                       # OUTPUT — generado por motor.py
        ├── aurora-digital/
        │   ├── config.yaml           # Config SFCE para esta entidad
        │   ├── saldos_apertura.json  # Saldos iniciales 2025
        │   ├── inbox/               # PDFs para el SFCE
        │   └── manifiesto.json      # Metadatos: que es cada PDF, errores, edge cases
        ├── distribuciones-levante/
        │   └── ...
        ├── marcos-ruiz/
        │   └── ...
        ├── elena-navarro/
        │   └── ...
        ├── jose-antonio-bermudez/
        │   └── ...
        ├── francisco-mora/
        │   └── ...
        ├── comunidad-mirador/
        │   └── ...
        ├── gastro-holding/
        │   └── ...
        ├── restaurante-la-marea/
        │   └── ...
        ├── chiringuito-sol-arena/
        │   └── ...
        └── catering-costa/
            └── ...
```

### Flujo del motor

```
python tests/datos_prueba/generador/motor.py --todas --año 2025

1. Carga empresas.yaml → perfil completo de cada entidad
2. Carga saldos_2024.yaml → estado inicial contable
3. Para cada entidad:
   a. Genera calendario anual (distribucion realista por mes segun perfil)
   b. Ejecuta generadores en orden:
      - gen_facturas (compras + ventas) → ~50-60 docs
      - gen_nominas (nominas + SS) → ~15-25 docs
      - gen_bancarios (prestamos + comisiones) → ~12-15 docs
      - gen_suministros (luz/agua/gas/tel) → ~10-12 docs
      - gen_seguros → ~4-6 docs
      - gen_impuestos (IBI/IAE/tasas) → ~3-5 docs
      - gen_subvenciones → ~1-3 docs
      - gen_intercompany (solo grupo) → ~5-8 docs
   c. gen_errores: inyecta errores en ~20% de documentos ya generados
   d. pdf_renderer: convierte HTML→PDF cada documento
   e. ruido.py: aplica variacion visual aleatoria
   f. Genera manifiesto.json
   g. Genera config.yaml SFCE
4. Resumen final: total docs generados, errores inyectados, edge cases
```

### CLI completo

```bash
# Todo
python motor.py --todas

# Una entidad
python motor.py --entidad aurora-digital

# Un trimestre
python motor.py --entidad aurora-digital --trimestre T1

# Sin errores (solo happy path)
python motor.py --todas --sin-errores

# Solo regenerar errores sobre PDFs existentes
python motor.py --todas --solo-errores

# Copiar salida a clientes/ del proyecto CONTABILIDAD
python motor.py --todas --deploy

# Seed fijo para reproducibilidad
python motor.py --todas --seed 42
```

### manifiesto.json (verificacion automatica SFCE)

```json
{
  "entidad": "aurora-digital",
  "generado": "2026-02-26T14:30:00",
  "seed": 42,
  "total_documentos": 108,
  "resumen": {
    "facturas_compra": 38,
    "facturas_venta": 18,
    "nominas": 22,
    "ss_rlc": 12,
    "recibos_bancarios": 8,
    "suministros": 5,
    "seguros": 3,
    "impuestos": 2
  },
  "errores_inyectados": {
    "total": 22,
    "detalle": {"E01": 2, "E02": 3, "E03": 2, "E06": 3, "E09": 1, "E12": 2}
  },
  "edge_cases": {
    "total": 15,
    "detalle": {"EC07": 1, "EC08": 2, "EC09": 4, "EC12": 1, "EC17": 1}
  },
  "documentos": [
    {
      "archivo": "2025-01-15_AWS-Ireland_F2025-0001.pdf",
      "tipo": "factura_compra",
      "subtipo": "intracomunitaria",
      "emisor": {"nombre": "Amazon Web Services EMEA SARL", "cif": "IE9692928F", "pais": "IRL"},
      "fecha": "2025-01-15",
      "base": 450.00,
      "iva_tipo": 0,
      "iva_cuota": 0,
      "retencion": 0,
      "total": 450.00,
      "divisa": "EUR",
      "error_inyectado": null,
      "edge_case": "EC09",
      "notas": "Requiere autoliquidacion 472/477"
    }
  ]
}
```

---

Este es el diseño completo. Voy a hacer commit del documento y luego transicionar al plan de implementación. Pero dado el volumen de contexto consumido, creo que deberíamos **cerrar sesión aquí** y arrancar la implementación en la siguiente sesión con el plan ya escrito. ¿Te parece?