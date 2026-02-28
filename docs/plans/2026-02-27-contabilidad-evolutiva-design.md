# Plan 1: Contabilidad Evolutiva — MVP Design

**Fecha**: 2026-02-27
**Lema**: Contabilidad Evolutiva, Autonoma y en Tiempo Real
**Objetivo**: Dashboard web para gestores/asesores donde la contabilidad de sus clientes se procesa automaticamente, de principio a fin, sin intervencion humana.

## Vision del producto

Un gestor accede a un portal web, sube documentacion de sus clientes, y el sistema de forma autonoma:
- Procesa cada factura/nomina/documento de principio a fin
- Mantiene los modelos fiscales actualizados en tiempo real (303, 130, 111, 390...)
- Muestra cuarentena inteligente para documentos problematicos (con opciones de resolucion en clicks)
- Auto-corrige bugs de codigo via Claude headless (sin intervencion humana)

**Alcance MVP**: Solo para el gestor principal (1 usuario) con sus 12-13 clientes. Multi-gestor en version futura.

**Publico objetivo final**: Asesores y gestores que quieran ofrecer contabilidad automatizada a sus clientes.

## Problema que resuelve

El pipeline SFCE actual funciona ~70-90% autonomo, pero:
1. El onboarding de clientes consume contexto de Claude
2. El intake OCR de 100+ documentos agota la sesion de Claude
3. El 10-30% de fallos requiere intervencion manual
4. No hay interfaz visual — todo es CLI + JSON

El producto elimina la dependencia de Claude en el loop de procesamiento.

## 4 Niveles de autonomia

| Nivel | Que resuelve | % estimado |
|-------|-------------|------------|
| 1. Pipeline automatico | Documentos limpios, proveedores conocidos | 70-90% |
| 2. Motor aprendizaje | Patrones conocidos de errores previos | +5-15% |
| 3. Dashboard cuarentena (gestor) | Problemas de datos que requieren decision humana | +5-10% |
| 4. Claude auto-fix (headless) | Bugs de codigo, sin humano presente | Resto |

## Arquitectura

```
+--------------------------------------------------------------+
|                    DASHBOARD (React+Vite+Tailwind)            |
|  Login - Clientes - Subida docs - Modelos fiscales            |
|  Cuarentena - Timeline actividad - Estado pipeline            |
+---------------------------+----------------------------------+
                            | REST API + WebSocket
+---------------------------+----------------------------------+
|                    BACKEND (Node.js + Express)                |
|  Auth (JWT) - API clientes/docs - WebSocket server            |
|  Cola de trabajos (BullMQ + Redis)                            |
+-------+------------------+------------------+----------------+
        |                  |                  |
+-------+-------+  +-------+-------+  +-------+-------+
|  Worker       |  |  FacturaScripts|  |  Claude       |
|  pipeline.py  |  |  (Docker)     |  |  Auto-fix     |
|  OCR+Registro |  |  Contabilidad |  |  (headless)   |
+-------+-------+  +-------+-------+  +-------+-------+
        |                  |                  |
+-------+------------------+------------------+----------------+
|                    PostgreSQL                                 |
|  Gestores - Clientes - Documentos - Pipeline state            |
|  Asientos - Modelos fiscales - Aprendizaje - Alertas          |
+--------------------------------------------------------------+
```

### Componentes

1. **Dashboard web** (React + Vite + Tailwind) — interfaz visual del gestor
2. **API backend** (Node.js + Express + TypeScript) — gestiona clientes, documentos, estado
3. **Worker** (Python) — pipeline.py actual, ejecutado como proceso background via BullMQ
4. **FacturaScripts** (Docker) — motor contable, ya desplegado en Hetzner
5. **PostgreSQL** — estado centralizado (reemplaza los JSON actuales: pipeline_state, intake_results, etc.)
6. **Redis + BullMQ** — cola de trabajos para procesar documentos async
7. **WebSocket (Socket.io)** — actualizacion en tiempo real del dashboard
8. **Claude Auto-fix** — Claude Code SDK headless para bugs de codigo

## Flujo completo de un documento

```
Gestor sube PDF
    |
    v
API recibe -> guarda en storage -> crea job en cola (BullMQ)
    |
    v
Worker toma el job
    |-- OCR (Mistral/GPT) -> extrae datos
    |-- Validacion (aritmetica + PGC)
    |-- Proveedor conocido?
    |      SI -> Registro en FS -> asiento + modelos
    |      NO -> Motor aprendizaje resuelve?
    |              SI -> Registro en FS
    |              NO -> CUARENTENA (con diagnostico)
    |
    |-- Error de codigo?
    |      SI -> Claude auto-fix (headless)
    |           |-- Fix OK + tests pasan -> aplica + reprocesa
    |           +-- Fix falla -> cuarentena + notificacion
    |
    v
WebSocket -> dashboard se actualiza en tiempo real
Modelos fiscales recalculados
```

## Pantallas del dashboard

### Vista principal — Mis Clientes

Grid/lista de todos los clientes del gestor con:
- Nombre y tipo (SL/autonomo)
- Numero de documentos procesados
- Estado (OK / errores / nuevo)
- Score de fiabilidad (%)
- Boton [+ Nuevo cliente]

### Vista cliente — Detalle

Panel lateral con secciones:
- **Resumen fiscal**: ingresos, gastos, IVA, resultado
- **Modelos fiscales**: 303, 130, 111, 390... con datos actualizados
- **Documentos**: listado de todos los docs procesados
- **Cuarentena**: docs pendientes de resolucion
- **Configuracion**: datos empresa, proveedores, ejercicio
- **Timeline**: actividad reciente (facturas procesadas, errores, etc.)

### Cuarentena — Resolucion inteligente

Cada documento en cuarentena muestra:
- El problema especifico (diagnostico claro, no tecnico)
- Opciones de resolucion en clicks (asignar proveedor, crear nuevo, editar datos, descartar)
- Vista previa del PDF y datos OCR extraidos
- Posibilidad de editar campos manualmente
- Al resolver: el sistema aprende y reprocesa automaticamente

### Subida de documentos

- Drag & drop de PDFs (uno o varios)
- Barra de progreso por documento
- Estado en tiempo real: procesando -> OK / cuarentena
- Opcion de "procesar automaticamente" o "esperar mi revision"

## Stack tecnico

| Componente | Tecnologia | Donde |
|------------|-----------|-------|
| Frontend | React 18 + Vite + Tailwind CSS | Hetzner VPS (65.108.60.69) |
| Backend API | Node.js + Express + TypeScript | Hetzner VPS |
| Cola trabajos | BullMQ + Redis | Hetzner VPS |
| Worker | Python (pipeline.py existente) | Hetzner VPS |
| Motor contable | FacturaScripts (Docker) | Hetzner VPS (ya desplegado) |
| BD | PostgreSQL | Hetzner VPS |
| WebSocket | Socket.io | Integrado en Express |
| Claude auto-fix | Claude Code SDK (headless) | Hetzner VPS |
| OCR | Mistral API + GPT-4o fallback | APIs externas |
| Storage docs | Filesystem local (con backup) | Hetzner VPS |

## Claude Auto-fix (Nivel 4)

### Flujo

```
Worker detecta error de codigo (traceback)
    |
    v
Genera reporte: {error, traceback, documento, fase, contexto}
    |
    v
Lanza Claude Code headless:
    "Analiza este error del pipeline SFCE. Archivo: X, linea: Y.
     Error: Z. Propone un fix y ejecuta los tests."
    |
    |-- Tests pasan -> aplica fix, commit, reprocesa documento
    +-- Tests fallan -> cuarentena + alerta al desarrollador
```

### Limites de seguridad

- Claude solo puede modificar archivos en `scripts/` y `reglas/`
- Cada fix requiere que los 88+ tests pasen
- Maximo 3 intentos de auto-fix por error unico
- Log completo de cada fix para auditoria
- No puede modificar configuracion de clientes ni datos contables

## Flujo inteligente de procesamiento

El gestor puede configurar por cliente:
- **Auto-procesar**: cada documento que llega se procesa inmediatamente sin esperar
- **Batch con revision**: documentos se acumulan, el gestor revisa antes de procesar
- **Umbral de cuarentena**: si mas del X% va a cuarentena, pausar y notificar

## Coste estimado por factura

| Concepto | Coste |
|----------|-------|
| OCR Mistral (primario) | ~$0.001/pagina |
| GPT-4o (fallback, ~25% docs) | ~$0.01/pagina |
| Gemini Flash (tier 2, ~5% docs) | Gratis (free tier) |
| FacturaScripts | Gratis (self-hosted) |
| Claude auto-fix | ~$0.05-0.10 por bug (infrecuente) |
| **Total estimado** | **~$0.005/factura** (~$0.50 por 100 facturas) |

## Proximos pasos

1. Escribir plan de implementacion detallado (tareas, orden, dependencias)
2. Implementar MVP iterativamente
3. Probar con clientes existentes (Pastorino, Gerardo, Chiringuito)
4. Iterar basado en uso real
5. Futuro: multi-gestor, portal cliente, integraciones bancarias
