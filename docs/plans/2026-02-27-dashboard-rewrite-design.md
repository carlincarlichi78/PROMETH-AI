# Design Doc: SFCE Dashboard — Rewrite Completo

**Fecha**: 2026-02-27
**Objetivo**: Reescritura completa del dashboard SFCE como producto SaaS vendible, con UI de ultima generacion, modulo economico-financiero potente y copiloto IA integrado.
**Audiencia**: Producto comercial para vender a gestorias y empresas.

---

## 1. Stack Tecnologico

| Capa | Tecnologia | Justificacion |
|------|------------|---------------|
| UI Components | shadcn/ui + Radix UI | Componentes accesibles, personalizables, no vendor lock-in |
| Charts | Recharts | Declarativo, composable, SSR compatible |
| Data Fetching | TanStack Query (React Query) | Cache inteligente, invalidacion, estados loading/error |
| State UI | Zustand | Ligero, sin boilerplate, empresa activa + theme + sidebar |
| Forms | React Hook Form + Zod | Validacion tipada, rendimiento, schemas reutilizables |
| Dates | date-fns | Tree-shakeable, locale es-ES |
| Styles | Tailwind CSS v4 + tailwind-animate + CVA | Utility-first, animaciones fluidas, variants tipadas |
| Icons | Lucide React | Consistentes, tree-shakeable, 1000+ iconos |
| Framework | React 18 + TypeScript strict | Base actual, tipado estricto |
| Build | Vite | Ya configurado, HMR rapido |

### Dependencias eliminadas
- CSS custom actual → Tailwind v4
- Fetch manual → React Query
- useState global → Zustand

---

## 2. Arquitectura

### Estructura de carpetas (feature-based)

```
dashboard/src/
  features/
    contabilidad/       # PyG, Balance, Diario, Plan Contable, Conciliacion, Amortizaciones, Cierre, Apertura
    facturacion/        # Emitidas, Recibidas, Cobros/Pagos, Presupuestos, Contratos
    fiscal/             # Calendario, Modelos, Generacion, Historico
    rrhh/               # Nominas, Trabajadores
    documentos/         # Inbox, Pipeline, Cuarentena, Archivo
    economico/          # Ratios, KPIs, Tesoreria, Costes, Presupuestos, Comparativa, Scoring, Informes
    portal/             # Vista cliente externa
    directorio/         # Proveedores/Clientes globales
    configuracion/      # Empresa, Usuarios, Roles, Integraciones, Backup, Licencia
    copilot/            # Chat IA, historial, funciones
  components/
    ui/                 # shadcn/ui components (Button, Card, Dialog, etc.)
    layout/             # AppShell, Header, Sidebar, Breadcrumbs
    charts/             # Wrappers Recharts reutilizables
    data-table/         # Tabla generica con sort/filter/paginate/export
  hooks/                # useEmpresa, useAuth, useWebSocket, useCopilot
  lib/                  # api-client, query-keys, formatters, validators
  stores/               # Zustand stores
  types/                # Tipos compartidos
```

### Patrones clave

- **React Query** para toda comunicacion con API: cache 5min, staleTime, invalidacion por mutacion
- **Zustand** solo para estado UI: empresa activa, theme (light/dark), sidebar collapsed, copilot open
- **Error Boundaries** por feature con fallback UI
- **Lazy loading** por ruta (React.lazy + Suspense)
- **WebSocket** para pipeline en tiempo real y notificaciones

---

## 3. Layout y Navegacion

### Header
- Logo SPICE + nombre producto
- Selector empresa activo (dropdown con buscador)
- Barra busqueda global (Cmd+K) — busca en facturas, asientos, proveedores, documentos
- Notificaciones (campana con badge)
- Copiloto IA (boton flotante)
- Avatar usuario + menu (perfil, tema, cerrar sesion)

### Sidebar (colapsable)
Iconos + texto, colapsable a solo iconos. Secciones con separadores:

```
Panel Principal          (Home)
─────────────────────
CONTABILIDAD
  Cuenta de Resultados   (PyG)
  Balance de Situacion
  Libro Diario
  Plan de Cuentas
  Conciliacion Bancaria
  Amortizaciones
  Cierre Ejercicio
  Apertura Ejercicio
─────────────────────
FACTURACION
  Facturas Emitidas
  Facturas Recibidas
  Cobros y Pagos
  Presupuestos
  Contratos Recurrentes
─────────────────────
RRHH
  Nominas
  Trabajadores
─────────────────────
FISCAL
  Calendario Fiscal
  Modelos Fiscales
  Generar Modelo
  Historico Modelos
─────────────────────
DOCUMENTOS
  Bandeja Entrada
  Pipeline
  Cuarentena
  Archivo Digital
─────────────────────
ECONOMICO-FINANCIERO
  Ratios Financieros
  KPIs Sectoriales
  Tesoreria
  Centros de Coste
  Presupuesto vs Real
  Comparativa Interanual
  Credit Scoring
  Informes PDF
─────────────────────
PORTAL CLIENTE
─────────────────────
DIRECTORIO
─────────────────────
CONFIGURACION
  Empresa
  Usuarios y Roles
  Integraciones
  Backup / Restore
  Licencia
  Apariencia
```

### Breadcrumbs
`Contabilidad > Libro Diario > Enero 2025`

### Responsive
- Desktop: sidebar expandido
- Tablet: sidebar colapsado (solo iconos)
- Mobile: sidebar oculto (hamburger menu)

---

## 4. Catalogo de Paginas (38 paginas)

### 4.1 Panel Principal (Home)
- KPIs principales: ingresos/gastos mes, resultado, IVA pendiente, facturas pendientes cobro/pago
- Graficos: evolucion mensual ingresos vs gastos (area chart), distribucion gastos por categoria (donut)
- Timeline actividad reciente (ultimos documentos procesados, asientos, alertas)
- Calendario mini con proximas obligaciones fiscales
- Accesos rapidos personalizables (drag & drop)

### 4.2 Contabilidad (8 paginas)

**Cuenta de Resultados (PyG)**
- Estructura jerarquica expandible: ventas, coste ventas, margen bruto, gastos operativos, EBITDA, amortizaciones, resultado explotacion, financieros, resultado antes impuestos, IS, resultado neto
- Periodo seleccionable (mes/trimestre/ano)
- Comparativa con periodo anterior (absoluto + %)
- Sparklines por partida
- Export PDF/Excel

**Balance de Situacion**
- Activo (corriente/no corriente) vs Pasivo + Patrimonio Neto
- Drill-down hasta subcuenta
- Grafico composicion (stacked bar)
- Comparativa interanual
- Export PDF/Excel

**Libro Diario**
- Tabla paginada con filtros: fecha, cuenta, concepto, importe
- Detalle asiento expandible inline (todas las partidas)
- Filtro por tipo documento origen
- Totales debe/haber
- Export CSV/Excel

**Plan de Cuentas**
- Arbol jerarquico interactivo (expandir/colapsar)
- Buscador por codigo o descripcion
- Saldo actual por cuenta
- Click → detalle movimientos

**Conciliacion Bancaria**
- Vista dual: movimientos banco vs asientos contables
- Matching automatico (sugerencias IA)
- Drag & drop para conciliar manualmente
- Estado: conciliado/pendiente/descuadre
- Resumen: total conciliado, pendiente, diferencia

**Amortizaciones**
- Tabla activos con % amortizado (progress bar)
- Cuadro amortizacion por activo (expandible)
- Grafico amortizacion acumulada
- Generar asientos amortizacion (boton)
- Proyeccion futura

**Cierre Ejercicio**
- Wizard 5 pasos: verificar saldos → regularizar IVA → amortizaciones pendientes → asiento cierre (6xx/7xx→129) → resultado
- Checklist con estado (ok/warning/error)
- Preview asientos antes de generar
- Boton ejecutar con confirmacion

**Apertura Ejercicio**
- Generar asiento apertura desde cierre anterior
- Verificar continuidad saldos
- Estado: pendiente/generada/verificada

### 4.3 Facturacion (5 paginas)

**Facturas Emitidas**
- Tabla con filtros: cliente, fecha, estado (cobrada/pendiente/vencida), importe
- Badge colores por estado
- Detalle inline con lineas
- Acciones: marcar cobrada, enviar recordatorio, duplicar, PDF
- Totales y graficos de cobro

**Facturas Recibidas**
- Igual estructura que emitidas pero para proveedores
- Estado: pagada/pendiente/vencida
- Link a asiento contable generado
- Acciones: marcar pagada, PDF original

**Cobros y Pagos**
- Vista unificada de tesoreria operativa
- Aging analysis (0-30, 30-60, 60-90, 90+ dias)
- Grafico waterfall: saldo inicial → cobros → pagos → saldo final
- Prevision cobros/pagos proximos 30/60/90 dias

**Presupuestos**
- Crear presupuesto para cliente
- Convertir a factura con un click
- Estados: borrador/enviado/aceptado/rechazado
- Historico y tasa conversion

**Contratos Recurrentes**
- Facturas periodicas automaticas (alquileres, cuotas, servicios)
- Configurar: importe, periodicidad, inicio/fin
- Proxima generacion programada
- Historial facturas generadas

### 4.4 RRHH (2 paginas)

**Nominas**
- Tabla mensual por trabajador
- Desglose: bruto, SS empresa, SS trabajador, IRPF, neto
- Comparativa mensual (chart)
- Coste total empresa por trabajador
- Export para modelo 111

**Trabajadores**
- Ficha trabajador: datos personales, contrato, categoria, antigueedad
- Historico nominas
- Provision pagas extras (progress bar)
- Costes acumulados ano

### 4.5 Fiscal (4 paginas)

**Calendario Fiscal**
- Vista calendario con obligaciones por mes
- Color por estado: al dia (verde), proximo (amarillo), vencido (rojo)
- Click → detalle modelo + acciones
- Filtro por tipo (trimestral/anual)

**Modelos Fiscales**
- Catalogo 13 modelos con estado por periodo
- Card por modelo: numero, nombre, periodicidad, estado ultimo
- Quick actions: generar, ver historico

**Generar Modelo**
- Selector modelo + periodo
- Preview datos calculados (bases, cuotas, resultados)
- Desglose partidas que componen cada casilla
- Boton generar → PDF + BOE

**Historico Modelos**
- Timeline de todos los modelos generados
- Filtro por modelo, periodo, estado
- Descargar PDF/BOE de cualquier version
- Comparativa entre periodos

### 4.6 Documentos (4 paginas)

**Bandeja de Entrada (Inbox)**
- Grid/lista de PDFs pendientes
- Preview PDF inline (viewer)
- Clasificacion automatica (tipo detectado + confianza)
- Acciones: procesar, mover a cuarentena, eliminar
- Drag & drop para subir nuevos
- Contador por tipo

**Pipeline**
- Vista en tiempo real del procesamiento
- Fases con progress: OCR → Clasificacion → Extraccion → Validacion → Registro → Correccion → Sync
- WebSocket para actualizacion en vivo
- Log detallado por documento
- Metricas: velocidad, precision, costes OCR

**Cuarentena**
- Documentos que requieren intervencion humana
- 7 tipos de problema con iconos/colores
- Formulario resolucion inline (responder preguntas)
- Resolver → reintenta pipeline automaticamente
- Stats: media resolucion, tipos mas frecuentes

**Archivo Digital**
- Todos los documentos procesados, organizados por tipo/fecha/proveedor
- Buscador full-text (en contenido OCR)
- Preview PDF
- Metadata: fecha, proveedor/cliente, importe, asiento vinculado
- Filtros avanzados

### 4.7 Economico-Financiero (8 paginas)

**Ratios Financieros**
- 30+ ratios organizados en 5 categorias:
  - **Liquidez**: ratio corriente, acid test, tesoreria inmediata, fondo maniobra
  - **Solvencia**: endeudamiento, autonomia financiera, cobertura intereses, calidad deuda
  - **Rentabilidad**: ROE, ROA, ROI, margen neto, margen operativo, margen bruto, ROCE
  - **Eficiencia**: rotacion activos, rotacion inventario, PMC (periodo medio cobro), PMP (periodo medio pago), ciclo operativo, ciclo caja
  - **Estructura**: composicion activo, composicion pasivo, inmovilizacion, capitalizacion
- Cada ratio: valor actual, evolucion 12 meses (sparkline), semaforo (verde/amarillo/rojo vs benchmark sectorial), explicacion textual
- Comparativa con sector (barras horizontales)
- Export informe completo PDF

**KPIs Sectoriales**
- Deteccion automatica de sector por actividad empresa (CNAE/IAE)
- **Hosteleria**: food cost %, ticket medio, coste primo (materia prima + personal), ratio personal/ventas, ventas por metro cuadrado, indice ocupacion (tickets TPV → comensales estimados), coste por comensal, RevPASH (revenue per available seat hour)
- **Comercio**: ventas/m2, rotacion stock, margen por linea producto, shrinkage, GMV, conversion rate
- **Servicios profesionales**: facturacion/hora, utilizacion %, ratio facturacion/costes personal, revenue per employee
- **Construccion**: desviacion presupuesto obra, % ejecucion, coste hora maquinaria
- **General**: punto muerto, GAO (grado apalancamiento operativo), productividad por empleado
- Cada KPI con objetivo configurable y semaforo
- Graficos de evolucion mensual

**Tesoreria**
- **Cash flow triple metodo**: operativo (resultado + ajustes), inversion (activos fijos), financiacion (deuda + capital)
- **Prevision tesoreria**: proyeccion 30/60/90/180 dias basada en cobros/pagos programados + patrones historicos
- Grafico: saldo historico + proyeccion (area chart con zona incertidumbre)
- **Alertas**: saldo minimo configurable, alerta si proyeccion cruza umbral
- Movimientos diarios con categorias
- Conciliacion rapida

**Centros de Coste**
- Definir centros: departamento, proyecto, sucursal, obra
- Asignacion de gastos a centros (manual o por regla)
- PyG por centro de coste
- Comparativa entre centros (bar chart agrupado)
- Evolucion mensual por centro
- Drill-down hasta asiento/factura

**Presupuesto vs Real**
- Presupuesto anual por partida contable
- Vista mensual: presupuestado vs real vs desviacion (absoluta y %)
- Semaforo por partida (dentro rango / alerta / excedido)
- Grafico acumulado (linea presupuesto vs linea real)
- Re-forecast: ajustar presupuesto restante con datos reales
- Alertas automaticas si desviacion >10%

**Comparativa Interanual**
- Seleccionar 2-5 ejercicios
- Tabla: concepto | Ej.2023 | Ej.2024 | Ej.2025 | Variacion
- Graficos evolucion: barras agrupadas por partida
- CAGR (tasa crecimiento anual compuesto) automatico
- Indices (base 100 primer ano)
- Estacionalidad: patron mensual superpuesto por anos

**Credit Scoring**
- Puntuacion automatica clientes/proveedores (0-100)
- Factores: historico pagos, antigueedad relacion, volumen, sector, morosidad
- Semaforo: verde (>70) / amarillo (40-70) / rojo (<40)
- Limite credito sugerido
- Alertas cambio de comportamiento
- Ranking mejores/peores pagadores

**Informes PDF**
- Generacion automatica informes profesionales
- Plantillas: informe mensual, trimestral, anual, ad-hoc
- Contenido configurable: que secciones incluir
- Logo empresa, datos fiscales en cabecera
- Graficos incrustados en PDF
- Programar envio automatico (email cliente)

### 4.8 Portal Cliente (1 pagina)
- Vista reducida para el cliente final (rol "cliente")
- Solo ve SU empresa: PyG simplificado, facturas, calendario fiscal, documentos
- Subir documentos (drag & drop → inbox)
- Chat con gestor (copilot mode)
- Descargar informes y modelos

### 4.9 Directorio (1 pagina)
- BD global proveedores/clientes compartida entre empresas
- CIF unico con verificacion AEAT/VIES
- Buscador con autocompletado
- Ficha: datos fiscales, historico facturas, scoring, notas
- Merge duplicados

### 4.10 Configuracion (6 paginas)

**Empresa**: datos fiscales, logo, sector, territorio, regimen IVA, ejercicio activo
**Usuarios y Roles**: CRUD usuarios, 4 roles (admin/gestor/readonly/cliente), permisos granulares
**Integraciones**: conexion FS, APIs OCR, email IMAP, webhooks
**Backup/Restore**: backup BD manual, restaurar, programar automaticos
**Licencia**: estado licencia, modulos activos, max empresas, renovacion
**Apariencia**: tema claro/oscuro, densidad UI (compacta/comoda), idioma, formato fechas/numeros

---

## 5. Copiloto IA

### Vision
Chat IA integrado en el dashboard que responde preguntas contables, financieras y operativas usando los datos reales de la empresa. No es un chatbot generico — es un analista financiero con acceso completo a la contabilidad.

### Interfaz
- Boton flotante esquina inferior derecha (icono sparkle)
- Panel lateral deslizante (400px ancho)
- Input con placeholder contextual: "Pregunta sobre [Empresa X]..."
- Historial de conversaciones persistente
- Respuestas enriquecidas: texto + tablas + mini-charts + links a paginas relevantes + acciones rapidas

### Arquitectura 6 capas

**Capa 1 — System Prompt**
Instrucciones base: rol (analista financiero), contexto empresa (sector, regimen, tamano), formato respuestas (espanol, moneda EUR, formatos europeos), restricciones (no inventar datos).

**Capa 2 — RAG (Retrieval-Augmented Generation)**
Antes de cada pregunta, inyectar contexto relevante:
- Resumen financiero actual (ingresos, gastos, resultado, liquidez)
- Ultimos movimientos relevantes
- Alertas activas
- Sector y benchmarks
El retriever selecciona que datos inyectar segun la pregunta.

**Capa 3 — Function Calling**
El LLM puede invocar funciones para consultar datos especificos:
- `consultar_pyg(periodo, comparar_con)` → datos PyG
- `consultar_balance(fecha)` → balance
- `consultar_ratio(nombre, periodo)` → ratio con historico
- `buscar_facturas(filtros)` → facturas que coinciden
- `consultar_tesoreria(horizonte)` → cash flow + prevision
- `calcular_kpi(nombre, parametros)` → KPI sectorial
- `consultar_modelo_fiscal(modelo, periodo)` → datos modelo
- `buscar_asientos(filtros)` → asientos contables
- `comparar_periodos(p1, p2, metricas)` → comparativa
~15-20 funciones en total, cada una con schema Zod tipado.

**Capa 4 — Knowledge Base**
Conocimiento estatico inyectado por contexto:
- Benchmarks sectoriales (food cost normal hosteleria: 28-35%, etc.)
- Normativa fiscal vigente (plazos, tipos, umbrales)
- Reglas contables PGC
- Mejores practicas por sector
Almacenado en YAML/JSON, versionado, actualizable.

**Capa 5 — Feedback Loop**
- Botones like/dislike en cada respuesta
- Dislike → opcion de corregir ("la respuesta correcta seria...")
- Feedback almacenado en BD
- Usado para mejorar prompts y knowledge base
- Metricas: satisfaction rate, tipos de preguntas mas frecuentes

**Capa 6 — Respuestas Enriquecidas**
El copiloto no solo devuelve texto. Puede incluir:
- **Tablas** formateadas con datos relevantes
- **Mini-charts** (sparklines, barras, donuts) renderizados inline
- **Links** a paginas del dashboard ("Ver detalle en Ratios Financieros")
- **Acciones** sugeridas ("Generar modelo 303 del T1" → boton que ejecuta)
- **Alertas** contextuales ("Atencion: tu ratio de liquidez esta por debajo del umbral")

### Ejemplo de interaccion

**Usuario**: "Me puedes decir cual es la rentabilidad media acumulada de los ultimos 6 meses con respecto al ano anterior?"

**Copiloto** (internamente):
1. System prompt → contexto empresa
2. RAG → inyecta PyG ultimos 18 meses
3. Function calling → `consultar_pyg(ultimos_6_meses)` + `consultar_pyg(mismos_meses_ano_anterior)`
4. Calcula rentabilidad media
5. Compara con ano anterior

**Respuesta**:
> La rentabilidad media de los ultimos 6 meses (jul-dic 2025) es del **8.3%** sobre ventas.
> Comparado con el mismo periodo de 2024 (**6.1%**), has mejorado **+2.2 puntos porcentuales** (+36% relativo).
>
> [Mini bar chart: rentabilidad mensual jul-dic 2024 vs 2025]
>
> Los meses con mejor rendimiento fueron octubre (11.2%) y noviembre (9.8%), impulsados por el incremento de ventas sin aumento proporcional de costes fijos.
>
> [Ver detalle completo → Comparativa Interanual]

---

## 6. Componentes Compartidos

### DataTable generico
- Columnas configurables (sort, filter, resize, hide)
- Paginacion server-side
- Busqueda global + filtros por columna
- Seleccion multiple + acciones bulk
- Export CSV/Excel/PDF
- Estados vacios con ilustracion + CTA
- Loading skeleton

### ChartCard
- Wrapper para Recharts con header (titulo + periodo selector + fullscreen)
- Responsive
- Loading state
- Empty state
- Tooltip consistente

### KPICard
- Valor principal grande
- Subtitulo descriptivo
- Variacion vs periodo anterior (flecha + color + %)
- Sparkline opcional
- Semaforo opcional

### FilterBar
- Filtros activos como chips removibles
- Filtros disponibles en dropdown
- Guardar combinaciones como "vistas" personalizadas
- Reset a default

---

## 7. UX y Animaciones

- **Transiciones** entre paginas con fade (150ms)
- **Skeleton loading** en todas las cargas (no spinners)
- **Toast notifications** para acciones (exito/error)
- **Modals** con backdrop blur para acciones destructivas
- **Hover effects** en cards y filas de tabla
- **Dark mode** completo con toggle en header
- **Densidad** configurable: compacta (mas datos) / comoda (mas espacio)
- **Empty states** con ilustraciones y CTAs claros

---

## 8. Seguridad y Roles

| Rol | Acceso |
|-----|--------|
| admin | Todo. CRUD usuarios, configuracion, backup |
| gestor | Contabilidad, facturacion, fiscal, documentos, economico. Sin config usuarios/licencia |
| readonly | Solo lectura en todo. Sin acciones (generar, procesar, modificar) |
| cliente | Solo portal cliente de SU empresa |

- JWT con refresh token
- CORS restrictivo (origenes permitidos)
- Rate limiting en API
- Audit log de acciones criticas
- Sanitizacion inputs (Zod en frontend + Pydantic en backend)

---

## 9. API Backend (extensiones necesarias)

Endpoints nuevos requeridos (FastAPI):

| Grupo | Endpoints nuevos |
|-------|-----------------|
| Economico | `/ratios/{empresa}`, `/kpis/{empresa}`, `/tesoreria/{empresa}`, `/cashflow/{empresa}`, `/scoring/{empresa}`, `/presupuesto/{empresa}`, `/comparativa/{empresa}` |
| Copilot | `/copilot/chat`, `/copilot/functions/{fn}`, `/copilot/feedback` |
| Portal | `/portal/{empresa}/resumen`, `/portal/{empresa}/documentos` |
| Configuracion | `/config/apariencia`, `/config/backup`, `/config/restore` |
| Informes | `/informes/generar`, `/informes/plantillas`, `/informes/programados` |

Todos los endpoints economico-financieros calculan en tiempo real desde tablas existentes (Asiento, Partida, Factura, Pago).

---

## 10. Datos y Persistencia

- **Fuente principal**: BD SQLite local (tablas actuales: 16 tablas SQLAlchemy)
- **Tablas nuevas**: presupuestos, centros_coste, asignaciones_coste, scoring_historial, copilot_conversaciones, copilot_feedback, informes_programados, vistas_usuario
- **Cache**: React Query en frontend (5min staleTime)
- **Datos reales** desde el inicio: sin datos mock, todo conectado a BD
- **WebSocket**: pipeline en tiempo real, notificaciones, alertas

---

## Aprobacion

Diseno aprobado por el usuario en sesion interactiva 2026-02-27.
Siguiente paso: plan de implementacion detallado.
