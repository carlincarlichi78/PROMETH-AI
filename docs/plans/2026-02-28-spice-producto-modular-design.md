# SPICE — Diseno de Producto Modular

> Fecha: 2026-02-28
> Estado: Borrador validado en sesion de brainstorming
> Siguiente paso: Plan de implementacion (writing-plans)

---

## 1. Vision del producto

SPICE (Sistema de Procesamiento Inteligente de Contabilidad Empresarial) es un SaaS de contabilidad automatizada con IA que cubre desde el autonomo individual hasta la asesoria fiscal con cientos de clientes.

### Cuatro roles, un solo producto

| Rol | Usuario | Ve | Hace |
|-----|---------|-----|------|
| **Superadmin** | Carlos (unico) | Todo el sistema | Configuracion global, crear cuentas |
| **Admin Gestoria / Asesor independiente** | Gestoria o autonomo fiscal | Todos sus clientes (y asesores si los tiene) | Gestion contable completa, modelos fiscales, lotes |
| **Asesor** (dentro de gestoria) | Empleado de la gestoria | Solo sus clientes asignados | Igual que admin gestoria en su scope |
| **Cliente final** | Empresa o autonomo cliente | Solo su empresa | Subir docs, ver estado fiscal, dashboard limitado |

**Modulos contratables por cuenta:**
- **Contabilidad** (base): OCR, asientos, modelos fiscales, conciliacion
- **Asesoramiento** (+): ratios avanzados, alertas, copiloto IA, analisis predictivo

**Pricing**: base por modulos + escala por numero de asesores + escala por tramo de clientes (ver seccion 12.3)

Todos los roles comparten el mismo nucleo tecnico. La diferencia es el scope de datos visible y los modulos contratados.

---

## 2. Arquitectura por capas

```
+---------------------------------------------------+
|          CAPA 4: DASHBOARD ADAPTATIVO             |
|  Modulo economico (universal)                      |
|  + Modulos verticales (hosteleria, retail...)      |
|  + Conciliacion + Alertas + Copiloto               |
|  + Vista Client / Gestoria / Asesor                |
+---------------------------------------------------+
|          CAPA 3: API REST (FastAPI)                |
|  Auth + RBAC + Rutas por dominio + WebSockets      |
+---------------------------------------------------+
|          CAPA 2: MOTORES DE NEGOCIO                |
|  Motor asientos    - Motor conciliacion            |
|  Motor fiscal      - Motor reglas contables        |
|  Motor OCR         - Motor aprendizaje             |
|  Motor alertas     - Motor reporting               |
+---------------------------------------------------+
|          CAPA 1: CONECTORES + DATOS                |
|  Conectores bancarios (C43 + enriquecedores)       |
|  Conectores ingreso (TPV, Stripe, manual...)       |
|  Conectores documento (email, upload, FS)          |
|  BD (SQLite->PostgreSQL) + FS sync                 |
+---------------------------------------------------+
```

### Principio fundamental

**Todo es un conector.** La entrada de datos siempre pasa por un conector que normaliza al modelo interno. El sistema nunca habla directamente con un formato externo.

```
Mundo exterior -> Conector -> Modelo interno -> Motores -> Dashboard
```

---

## 3. Sistema de conectores

### 3.1 Conectores bancarios

**Parser C43 base** — estandar AEB, funciona con todos los bancos espanoles.
Un solo parser, ~80 lineas Python, cubre el mercado.

**Enriquecedores por banco** — capa opcional que extrae campos adicionales:

| Banco | Codigo | Enriquecedor | Datos extra |
|-------|--------|-------------|-------------|
| CaixaBank | 2100 | Si | SEPA + conceptos adicionales |
| Santander | 0049 | Si | Formato propio |
| BBVA | 0182 | Si | Formato propio |
| Sabadell | 0081 | Si | Formato propio |
| Bankinter | 0128 | Si | Formato propio |
| Cualquier otro | * | Generico | Solo C43 estandar |

**Deteccion automatica**: el codigo de banco en la cabecera del C43 (posiciones 3-6) selecciona el enriquecedor.

**Formatos C43 soportados** (por orden de riqueza):
1. Con referencias SEPA y conceptos adicionales (recomendado)
2. Modalidad 3 con SEPA
3. Con conceptos adicionales
4. Modalidad 3 estandar

**Otros formatos bancarios** (fallback):
- QIF (Quicken) — parser simple
- PDF extracto — OCR (ya existente en SFCE)

### 3.2 Conectores de ingreso

Cada tipo de negocio tiene una o mas fuentes de ingreso. Todos producen el mismo modelo `VentasDiarias`.

| Conector | Tipo negocio | Input | Prioridad |
|----------|-------------|-------|-----------|
| TicketZOCR | Hosteleria, Retail | PDF/foto cierre caja | Alta |
| LiquidacionTPV | Hosteleria, Retail | Dentro del C43 (MCC) | Alta |
| RevoAPI | Hosteleria (CaixaBank POS) | API REST | Media |
| StripeCSV | E-commerce | CSV liquidacion | Media |
| PayPalCSV | E-commerce | CSV liquidacion | Baja |
| AmazonSettlements | Marketplace | CSV multiples | Baja |
| AlquilerRecurrente | Inmobiliaria | Config + generacion auto | Baja |
| FCManual | Servicios | Ya existe en SFCE | Ya existe |

**Jerarquia de conectores de ingreso** (por riqueza de datos):
```
Revo API > Ticket Z OCR > Liquidacion C43 > Entrada manual
```
El sistema usa automaticamente el conector mas rico disponible.

### 3.3 Conectores de documento

| Conector | Tipo | Input |
|----------|------|-------|
| EmailInbox | Automatico | Facturas + C43 por email |
| UploadManual | Manual | Drag & drop multi-archivo |
| FSSync | Automatico | FacturaScripts API |

### 3.4 Modelo comun de datos (VentasDiarias)

```python
@dataclass
class VentasDiarias:
    fecha: date
    empresa_id: int
    restaurante: str  # o punto de venta

    # Siempre disponible (cualquier fuente)
    total_ventas: Decimal
    total_tarjeta: Optional[Decimal]
    total_efectivo: Optional[Decimal]

    # Desde Revo API o Ticket Z OCR
    num_tickets: Optional[int]
    num_comensales: Optional[int]
    ticket_medio: Optional[Decimal]
    ventas_por_familia: Optional[Dict[str, Decimal]]

    # Metadatos
    fuente: str  # 'revo_api' | 'ocr_ticket_z' | 'liquidacion_c43' | 'manual'
    confianza: float  # 0.0 - 1.0
```

---

## 4. Modelo de datos bancarios

### 4.1 CuentaBancaria

```python
@dataclass
class CuentaBancaria:
    id: int
    empresa_id: int           # FK Empresa
    banco_codigo: str         # "2100" CaixaBank
    banco_nombre: str         # "CaixaBank"
    iban: str                 # ES12 2100 3889 02 0025560823
    alias: str                # "Cuenta operaciones", "Cuenta TPV"
    divisa: str               # "EUR", "USD", "GBP"
    activa: bool
    email_c43: Optional[str]  # email para recepcion automatica
```

### 4.2 MovimientoBancario (extender tabla existente)

```python
@dataclass
class MovimientoBancario:
    id: int
    cuenta_id: int            # FK CuentaBancaria
    fecha_operacion: date
    fecha_valor: date
    importe: Decimal          # en divisa nativa
    divisa: str
    importe_eur: Decimal      # siempre convertido
    tipo_cambio: Optional[Decimal]
    signo: str                # 'D' (cargo) | 'H' (abono)
    concepto_comun: str       # codigo AEB
    concepto_propio: str
    referencia_1: str
    referencia_2: str
    nombre_contraparte: str
    tipo_clasificado: str     # 'TPV' | 'PROVEEDOR' | 'NOMINA' | 'IMPUESTO' | 'COMISION' | 'OTRO'
    estado_conciliacion: str  # 'pendiente' | 'conciliado' | 'revision' | 'manual'
    asiento_id: Optional[int] # FK Asiento (cuando conciliado)
    hash_unico: str           # SHA256 para deduplicacion (UNIQUE)
```

### 4.3 ArchivoIngestado

```python
@dataclass
class ArchivoIngestado:
    id: int
    hash_archivo: str         # SHA256 contenido (UNIQUE)
    nombre_original: str
    fuente: str               # 'email' | 'manual'
    tipo: str                 # 'c43' | 'ticket_z' | 'factura' | 'nomina'
    empresa_id: int
    fecha_proceso: datetime
    movimientos_totales: int
    movimientos_nuevos: int
    movimientos_duplicados: int
```

### 4.4 Deduplicacion

Hash unico por movimiento: `SHA256(iban + fecha_op + importe + referencia + num_orden)`

```sql
INSERT INTO movimientos_bancarios (..., hash_unico)
VALUES (...)
ON CONFLICT (hash_unico) DO NOTHING
```

Idempotente: procesar el mismo archivo N veces = mismo resultado.

### 4.5 Multi-divisa

- Divisa nativa almacenada siempre
- Conversion a EUR para informes usando tipos BCE (API gratuita)
- Cache local de tipos de cambio (una consulta diaria)

---

## 5. Perfiles de negocio

### 5.1 Definicion

```python
@dataclass
class PerfilNegocio:
    tipo: str                    # 'hosteleria' | 'retail' | 'servicios' | ...
    regimen_iva: str             # 'general' | 'simplificado' | 'exento' | 'recargo_equiv'
    forma_juridica: str          # 'autonomo' | 'sl' | 'sa' | 'comunidad'
    fuentes_ingreso: List[str]   # ['tpv_z_ticket', 'fc_manual']
    cuentas_ingreso: List[str]   # ['705']
    conectores_activos: List[str]
    modelos_fiscales: List[str]  # ['303', '111', '390']
    modulo_dashboard: str        # 'hosteleria' | 'retail' | 'servicios'
    reglas_contables: Dict       # cuentas, IVA, retenciones
```

### 5.2 Perfiles predefinidos

| Perfil | Ingresos | Cuenta PGC | IVA | Modelos | Reglas especiales |
|--------|----------|------------|-----|---------|------------------|
| Hosteleria | Z ticket + TPV | 705 | 10%+21% | 303,111,390 | Cuenta puente 432 |
| Retail | Z ticket + TPV | 700 | 21% o RE | 303,390 | Recargo equivalencia opcional |
| Servicios prof. | FC emitida | 705 | 21% | 303,111,130,390 | Retencion IRPF 15%, cuenta 473 |
| Inmobiliaria | FC alquiler | 752 | Exento/21% | 303,390 | Retencion 19% |
| E-commerce | Stripe/PayPal | 700 | 21% | 303,390 | Comisiones marketplace |
| Construccion | Certificaciones | 700 | ISP | 303,390 | Inversion sujeto pasivo |
| Comunidad PP | Cuotas | 752 | Exento | — | Sin modelos fiscales |

### 5.3 Reglas contables por perfil

```python
REGLAS_CONTABLES = {
    'hosteleria': {
        'cuenta_ingreso': '705',
        'iva_tipos': [('10', 'alimentos'), ('21', 'alcohol')],
        'cuenta_pendiente_cobro_tpv': '432',
        'cuenta_caja': '570',
        'cuenta_comisiones_banco': '626',
    },
    'servicios': {
        'cuenta_ingreso': '705',
        'iva_tipos': [('21', 'general')],
        'retencion_irpf': '15',
        'cuenta_retencion': '473',
    },
    'inmobiliaria': {
        'cuenta_ingreso': '752',
        'iva_tipos': [('exento', 'arrendamiento_vivienda'), ('21', 'arrendamiento_local')],
        'retencion_irpf': '19',
    },
}
```

---

## 6. Motor de conciliacion

### 6.1 Flujo general

```
MovimientosBancarios (C43)
        |
        v
Clasificacion automatica por tipo
        |
   +----+---------------------------+
   |              |                  |
Liquidacion TPV  Pago proveedor   Otros
-> busca 432     -> busca 410     -> cola revision
-> genera asiento-> marca pagado  -> sugerencia IA
-> CONCILIADO    -> CONCILIADO    -> PENDIENTE
```

### 6.2 Asientos automaticos por tipo

**Ventas diarias (desde Ticket Z):**
```
DR 432 Cobros pendientes TPV   (tarjeta)
DR 570 Caja                    (efectivo)
  CR 705 Prestaciones servicios (base imponible)
  CR 477 IVA repercutido        (10% alimentos + 21% alcohol)
```

**Liquidacion TPV (desde C43):**
```
DR 572 Banco c/c               (neto despues de comision)
DR 626 Comisiones bancarias     (comision Comercia/banco)
  CR 432 Cobros pendientes TPV  (cierra cuenta puente)
```

**FC cliente pagada al momento en restaurante:**
- Vinculada al ticket Z del dia, sin asiento adicional
- Marcada como "incluida en ticket Z fecha X"

**FC cliente cobro diferido:**
```
Emision:  DR 430 Clientes / CR 705 + CR 477
Cobro:    DR 572 Banco / CR 430 Clientes
```

### 6.3 Estados de conciliacion

```python
class EstadoConciliacion(Enum):
    PENDIENTE   = "pendiente"    # C43 recibido, sin match
    CONCILIADO  = "conciliado"   # vinculado a asiento
    REVISION    = "revision"     # importe no coincide exactamente
    MANUAL      = "manual"       # resuelto por el usuario
```

### 6.4 Matching inteligente

1. **Exacto**: importe C43 = importe asiento pendiente (misma fecha +/- 2 dias)
2. **Aproximado**: diferencia < 1% (comisiones bancarias, redondeos)
3. **Sugerencia IA**: fuzzy matching por nombre contraparte + importe similar
4. **Manual**: cola de revision para el usuario

---

## 7. Dashboard adaptativo

### 7.1 Modulo economico (universal, todos los perfiles)

Ya existe en SFCE. Paginas:
- KPIs genericos (ventas, margen, resultado, coste personal)
- Ratios PGC (liquidez, solvencia, rentabilidad, eficiencia)
- Tesoreria + cashflow + prevision
- Presupuesto vs Real
- Comparativa interanual
- Scoring clientes/proveedores
- Centros de coste

### 7.2 Modulo conciliacion (nuevo, universal)

- Vista de movimientos bancarios por cuenta
- Estado de conciliacion (pendiente/conciliado/revision)
- Matching manual drag & drop (movimiento <-> asiento)
- Resumen: % conciliado por periodo
- Alertas: movimientos sin conciliar > X dias

### 7.3 Modulos verticales (por perfil de negocio)

**MERIDIAN (hosteleria)**
- RevPASH, covers, ticket medio, mix ventas
- Ratio bebida/comida
- Tendencia semanal (lun-dom)
- Escandallo, food cost %, labor cost %, prime cost
- Punto de equilibrio
- Multi-restaurante + consolidado

**RETAIL**
- Rotacion stock, margen por producto
- Ventas por m2
- Ticket medio, conversion
- Estacionalidad

**SERVICIOS**
- Horas facturadas
- Retenciones acumuladas (473)
- Aging clientes (deuda por antiguedad)
- Modelo 111 acumulado

**RENTAL (inmobiliaria)**
- Ocupacion por inmueble
- Yield bruto/neto
- Vencimientos contratos
- IBI, comunidad, suministros por inmueble

**ECOMMERCE**
- Conversiones, CAC, LTV
- Devoluciones %
- Comisiones marketplace
- Margenes por canal

### 7.4 Vistas por tier

**SPICE Client** (empresa/autonomo):
- Dashboard de SU empresa
- Subir documentos (facturas, tickets Z, C43)
- Ver estado fiscal (proximos vencimientos, modelos pendientes)
- Modulo vertical de su perfil

**SPICE Gestoria** (gestoria/despacho):
- Lista de todos sus clientes con semaforo de estado
- Procesamiento por lotes (subir docs de varios clientes)
- Calendario fiscal global (todos los vencimientos de todos los clientes)
- Generacion masiva de modelos fiscales
- Conciliacion por cliente
- Alertas cross-client (cliente sin facturar, modelo vencido)

**SPICE Asesor** (asesor fiscal/consultor):
- Todo lo de Gestoria +
- Comparativa entre clientes (benchmarking sectorial)
- Cumplimiento normativo global (que clientes estan al dia, cuales no)
- Alertas de riesgo fiscal (operaciones inusuales, ratios anomalos)
- Reporting para AEAT si fuera necesario
- Vista consolidada multi-gestoria (si gestiona varias)

---

## 8. Alertas y notificaciones

| Alerta | Trigger | Destinatario |
|--------|---------|-------------|
| Saldo bajo | Tesoreria < umbral configurado | Client + Gestoria |
| Factura sin conciliar | > X dias sin match bancario | Gestoria |
| Vencimiento fiscal | Modelo vence en N dias | Gestoria + Asesor |
| Anomalia ventas | Caida > 20% vs media 4 semanas | Client + Gestoria |
| Comision inesperada | Nuevo cargo bancario no habitual | Client |
| Cliente sin facturar | > 30 dias sin FC emitida | Gestoria |
| Documento en cuarentena | OCR no pudo clasificar | Client + Gestoria |

Canales: in-app (dashboard), email, push (PWA).

---

## 9. Automatizacion avanzada

### 9.1 Clasificacion aprendida
El motor de aprendizaje (ya existe en SFCE) se extiende a movimientos bancarios:
- "MERCADONA" -> cuenta 600 (compras)
- "ENDESA" -> cuenta 628 (suministros)
- "FACTURAC.COMERCIOS" -> tipo TPV
- Aprende de correcciones manuales del usuario

### 9.2 Asientos recurrentes
Deteccion automatica de patrones repetitivos:
- Alquiler mensual (mismo importe, misma fecha +/- 2 dias)
- Seguros (trimestral/anual)
- Nominas (mensual)
- Suministros (mensual/bimestral)

Sistema sugiere: "Detectado patron recurrente: 1.200 EUR el dia 1 de cada mes a INMOBILIARIA LOPEZ. ¿Crear asiento automatico?"

### 9.3 Prevision de tesoreria
Reemplazar prevision naive (+2%/+4%/+6%) por:
- Ingresos previstos: media ultimas 4 semanas (ponderada)
- Gastos previstos: asientos recurrentes + modelos fiscales pendientes
- Resultado: prevision a 30/60/90 dias con intervalos de confianza

### 9.4 Conciliacion predictiva
Antes de que llegue el C43, el sistema ya sabe:
- "Ayer Gaucho vendio 3.970 EUR por tarjeta (ticket Z)"
- "En 1-2 dias deberia llegar abono de ~3.969 EUR (menos comision)"
- Cuando llega el C43, el match es instantaneo

---

## 10. Compliance y normativa

### 10.1 VERIFACTU (obligatorio 2026)
Sistema de facturacion verificable. Impacto en SPICE:
- Cada FC emitida debe generar hash encadenado
- Envio a AEAT en tiempo real (o casi real)
- Afecta al pipeline de FC
- Requiere certificacion del software

### 10.2 SII (Suministro Inmediato de Informacion)
Para empresas > 6M EUR facturacion:
- Envio de libros registro a AEAT en 4 dias
- Integracion con sede electronica AEAT

### 10.3 Actualizaciones normativas
- PGC: cambios anuales en plan contable -> versionado en sfce/normativa/
- IVA: cambios de tipos -> configuracion por ejercicio fiscal
- Modelos fiscales: actualizaciones BOE -> motor BOE ya versionado

### 10.4 Ley antifraude
Requisitos para software de facturacion:
- Integridad de registros (no borrar facturas)
- Trazabilidad completa
- Formatos estandar de exportacion

---

## 11. Infraestructura y escalabilidad

### 11.1 Base de datos
- Fase 1: SQLite (1-10 clientes, desarrollo rapido)
- Fase 2: PostgreSQL (10+ clientes, concurrencia, backups)
- Migracion: SQLAlchemy abstrae, cambio de connection string

### 11.2 Multi-tenant
- Modelo: BD compartida con `empresa_id` / `tenant_id` en todas las tablas
- Aislamiento por row-level security (PostgreSQL)
- Alternativa para datos sensibles: esquema por tenant

### 11.3 Background jobs
- OCR de documentos (pesado, 5-30s por doc)
- Parseo C43 (ligero, <1s)
- Conciliacion (medio, depende del volumen)
- Herramienta: ARQ (async Redis queue) o Celery

### 11.4 Limites APIs OCR
| API | Limite | Estrategia |
|-----|--------|-----------|
| Mistral OCR3 | Rate limit variable | Motor primario, retry con backoff |
| GPT-4o | 30K TPM | Fallback, reducir workers |
| Gemini Flash | 5 req/min, 20/dia (free) | Solo consenso, tier pagado para volumen |

Para 50+ clientes: plan pagado de al menos Mistral + GPT.

### 11.5 Hosting
- Actual: Hetzner VPS (65.108.60.69)
- Escalado: Railway, Fly.io, o Hetzner Cloud con auto-scaling
- CDN para dashboard: Cloudflare Pages o Vercel

### 11.6 Backups
- BD: dump automatico diario + replicacion
- Archivos: S3-compatible (Hetzner Storage Box o Backblaze B2)
- Test de restauracion mensual

### 11.7 Monitorizacion
- Uptime: UptimeRobot o Betterstack
- Errores: Sentry (Python + React)
- Metricas: Prometheus + Grafana (o simple endpoint /health)

---

## 12. Seguridad y acceso

### 12.1 Jerarquia de roles

```
SUPERADMIN (Carlos)
    |
    +-- GESTORIA (organizacion)
    |       |
    |       +-- ADMIN_GESTORIA (gestor principal, ve todos sus asesores y clientes)
    |       |
    |       +-- ASESOR (mismo acceso que admin_gestoria, solo sus clientes asignados)
    |
    +-- ASESOR_INDEPENDIENTE (gestoria de uno, ve todos sus clientes)
    |
    +-- CLIENTE_FINAL (solo su empresa)
```

| Rol | Alcance | Ve | Hace |
|-----|---------|-----|------|
| `superadmin` | Global | Todo el sistema | Configuracion global, crear gestorias |
| `admin_gestoria` | Su gestoria | Todos sus asesores + todos sus clientes | Gestion completa de su gestoria |
| `asesor` | Sus clientes asignados | Solo clientes que le asigna el admin | Igual que admin_gestoria en su scope |
| `asesor_independiente` | Sus clientes | Todos sus clientes | Igual que admin_gestoria |
| `cliente` | Su empresa | Solo su empresa | Ver estado, subir documentos |

**Notas clave:**
- Un asesor dentro de una gestoria tiene el mismo nivel funcional que el admin_gestoria, pero limitado a sus clientes asignados
- El asesor independiente es una "gestoria de uno": sin subordinados pero acceso total a sus clientes
- Los modulos contratados aplican a toda la gestoria: si la gestoria tiene asesoramiento, todos sus asesores tienen asesoramiento

### 12.2 Modulos contratables

| Modulo | Incluye | Sin este modulo |
|--------|---------|----------------|
| `contabilidad` | Pipeline OCR, asientos, modelos fiscales, conciliacion bancaria | — (base obligatorio) |
| `asesoramiento` | Ratios avanzados, alertas, copiloto IA, analisis predictivo, benchmarking | Solo contabilidad operativa |

Los modulos se contratan a nivel de gestoría/asesor_independiente. Todos los usuarios de esa cuenta comparten los mismos modulos.

### 12.3 Modelo de pricing

**Estructura**: Base por modulos + escala por asesores + escala por clientes

| Concepto | Precio orientativo |
|----------|-------------------|
| Modulo contabilidad | 49 EUR/mes base |
| Modulo asesoramiento | +30 EUR/mes adicional |
| Por cada asesor adicional (tras el primero) | +20 EUR/mes |
| Tramo 1-10 clientes | incluido |
| Tramo 11-30 clientes | +25 EUR/mes |
| Tramo 31-60 clientes | +50 EUR/mes |
| Tramo 61+ clientes | +100 EUR/mes |

**Ejemplos:**
- Asesor independiente, solo contabilidad, 8 clientes: 49 EUR/mes
- Asesor independiente, contabilidad + asesoramiento, 15 clientes: 49 + 30 + 25 = 104 EUR/mes
- Gestoria con 3 asesores, contabilidad + asesoramiento, 25 clientes: 49 + 30 + (2x20) + 25 = 144 EUR/mes

### 12.4 RBAC
- Permisos por recurso (empresa, documento, asiento)
- Scope de acceso: `gestoria_id` + `clientes_asignados[]` en el JWT
- API: middleware de autorizacion en cada ruta verifica scope antes de ejecutar query

### 12.3 RGPD
- Datos personales en movimientos bancarios (nombres)
- Derecho al olvido: anonimizacion de datos personales
- Consentimiento explicito para procesamiento
- Cifrado en reposo (BD) y en transito (HTTPS)

### 12.4 Audit trail
- Tabla AuditLog ya existe en SFCE
- Registrar: quien, que, cuando, desde donde
- Inmutable: solo INSERT, nunca UPDATE/DELETE

---

## 13. Onboarding

### 13.1 Flujo web (reemplaza onboarding.py CLI)

```
Paso 1: Datos empresa
  CIF, nombre, forma juridica, regimen IVA

Paso 2: Perfil de negocio
  Tipo (hosteleria/retail/servicios/...)
  -> pre-selecciona cuentas, modelos, conectores

Paso 3: Configurar bancos
  Anadir cuentas bancarias (IBAN, alias)
  Formato C43 recomendado
  Opcion: configurar envio email automatico

Paso 4: Fuentes de ingreso
  Segun perfil: TPV (subir ticket Z), FC manual, Stripe...

Paso 5: Importar datos existentes (opcional)
  Subir C43 historico, facturas previas
  Migracion desde otro software

-> Sistema operativo en ~10 minutos
```

### 13.2 Onboarding por tier

- **Client**: el flujo completo, autoservicio
- **Gestoria**: alta masiva de clientes (CSV/Excel), configuracion por lotes
- **Asesor**: invitar gestorias, asignar clientes, configurar alertas globales

---

## 14. Monetizacion

### 14.1 Modelo de pricing (ver detalle en seccion 12.3)

Pricing dinamico basado en tres ejes:
1. **Modulos contratados**: contabilidad (base) + asesoramiento (opcional)
2. **Numero de asesores**: +20 EUR/mes por cada asesor adicional al primero
3. **Tramo de clientes**: incluido hasta 10, escalado en tramos de 20/50/ilimitado

Este modelo premia la eficiencia: una gestoria grande con muchos clientes por asesor paga proporcionalmente menos que multiples asesores con pocos clientes cada uno.

### 14.2 Opciones adicionales

- **Trial**: 30 dias gratis con datos reales
- **Descuento anual**: 2 meses gratis pagando anual
- **White-label**: precio a negociar para gestorias que quieran marca propia

---

## 15. UX y competitividad

### 15.1 App movil / PWA
- Foto del ticket Z desde el movil -> procesamiento inmediato
- Notificaciones push (alertas, vencimientos)
- Dashboard responsive (ya existe en SFCE dashboard)

### 15.2 Copiloto IA
- Modulo copilot ya existe en SFCE
- Potenciar con: "¿como van mis impuestos este trimestre?", "¿tengo liquidez para pagar la nomina?"
- Lenguaje natural sobre datos contables

### 15.3 Onboarding interactivo
- Tour guiado la primera vez
- Checklist de configuracion visible
- Videos/tooltips contextuales

---

## 16. Operativa especifica hosteleria (MERIDIAN)

### 16.1 KPIs exclusivos restauracion
- **RevPASH** (Revenue Per Available Seat Hour): ingresos / (asientos x horas apertura)
- **Ticket medio**: total ventas / num tickets
- **Covers**: comensales por servicio (almuerzo/cena)
- **Mix ventas**: % por familia (carnes, pescados, bebidas, vinos, postres)
- **Ratio bebida/comida**: indicador clave de rentabilidad
- **Food cost %**: coste materia prima / ventas
- **Labor cost %**: coste personal / ventas
- **Prime cost**: food + labor / ventas (el KPI mas importante)
- **Punto de equilibrio**: costes fijos / (1 - costes variables / ventas)

### 16.2 Escandallo (receta de coste)
- Coste teorico por plato (ingredientes x precio)
- Coste real (facturas proveedores / platos vendidos)
- Desviacion: alerta si real > teorico + 10%

### 16.3 Multi-restaurante
- Dashboard individual por restaurante
- Vista consolidada del grupo
- Comparativa entre restaurantes (ranking)

---

## 17. Roadmap de fases

### Fase 1: Nucleo bancario + conciliacion (4-6 semanas)
- Parser C43 base + enriquecedor CaixaBank
- Tabla CuentaBancaria + extension MovimientoBancario
- ArchivoIngestado + deduplicacion hash
- Motor conciliacion (match exacto + aproximado)
- Ingesta manual multi-file en dashboard
- API + dashboard conciliacion basico

### Fase 2: Conectores de ingreso + asientos automaticos (4-6 semanas)
- Conector Ticket Z OCR (nuevo tipo documento)
- Tabla VentasDiarias
- Asientos automaticos ventas (432/570/705/477)
- Asiento liquidacion TPV (572/626/432)
- Conciliacion TPV <-> C43
- Multi-divisa (API BCE)

### Fase 3: Perfiles de negocio + dashboard vertical (4-6 semanas)
- Sistema de perfiles configurables
- Reglas contables por perfil
- Modulo MERIDIAN (hosteleria) en dashboard
- Modulo SERVICIOS (retenciones, aging)
- Onboarding web (wizard)

### Fase 4: Multi-tenant + tiers (4-6 semanas)
- RBAC completo (admin/asesor/gestor/cliente/empleado)
- Vistas SPICE Client / Gestoria / Asesor
- Calendario fiscal global (Gestoria)
- Alertas y notificaciones
- Migracion SQLite -> PostgreSQL

### Fase 5: Compliance + productizacion (4-6 semanas)
- VERIFACTU 2026
- Ingesta email automatica (C43 + facturas)
- Clasificacion aprendida de movimientos bancarios
- Prevision tesoreria inteligente
- Pricing + facturacion + trial/freemium

### Fase 6: Escalar (continuo)
- Mas enriquecedores bancarios (Santander, BBVA, Sabadell)
- Mas conectores ingreso (Stripe, PayPal, Amazon)
- Mas modulos verticales (retail, inmobiliaria, e-commerce)
- Comparativa sectorial (Asesor)
- Open Banking PSD2 (cuando madure)
- App movil / PWA nativa

---

## 18. Estado actual del sistema (punto de partida)

### Ya existe y funciona
- Pipeline OCR 7 fases (Mistral + GPT + Gemini)
- Motor de aprendizaje (6 estrategias)
- Motor de reglas contables (normativa versionada)
- Motor de modelos fiscales (28 modelos, BOE, PDF)
- Dual backend FS + BD local
- Dashboard 40 paginas (React 18 + shadcn/ui)
- Modulo economico completo (KPIs, ratios, tesoreria, presupuesto)
- Tabla MovimientoBancario (esqueleto)
- Modulo copilot (esqueleto)
- API FastAPI 66 rutas, 25 tablas
- 1554 tests pasando
- Directorio empresas con verificacion CIF

### No existe (por construir)
- Parser C43
- Conectores de ingreso (TPV, Stripe...)
- Motor de conciliacion completo
- Perfiles de negocio
- Modulos verticales dashboard (MERIDIAN, retail...)
- RBAC / multi-tenant
- Tiers (Client / Gestoria / Asesor)
- Onboarding web
- Alertas y notificaciones
- VERIFACTU
- Ingesta email para C43

---

## Apendice: Archivo C43 de referencia

Disponible en: `C:\Users\carli\Downloads\_Trabajo\TT181225.754.txt`
- CaixaBank (codigo 2100), oficina 3889
- Cliente: Gerardo Gonzalez Callejon
- Contiene movimientos TPV (FACTURAC.COMERCIOS, codigo MCC)
- Contiene gastos (Google Ads, Facebook Ads, mantenimiento)
- Formato para primer test del parser C43
