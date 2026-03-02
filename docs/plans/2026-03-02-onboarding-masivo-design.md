# Onboarding Masivo — Design Document
**Fecha**: 2026-03-02
**Estado**: Aprobado

---

## Resumen

Sistema de alta automatizada masiva de clientes de una gestoría. Una gestoría sube
sus documentos fiscales (PDFs, CSVs, Excel) en cualquier formato y el sistema crea
automáticamente todas las empresas en BD + FacturaScripts, genera config.yaml,
estructura de carpetas en disco y envía invitaciones a los empresarios.

---

## Enfoque elegido

**Pipeline de Ingesta Documental** — acepta cualquier formato de entrada, clasifica
cada documento, extrae datos con parsers específicos por tipo, acumula un
`PerfilEmpresa` por cliente y crea las empresas cuando hay confianza suficiente.
Reutiliza `ocr_036.py`, `ocr_escritura.py`, `fs_setup.py` y `email_service.py`
ya implementados.

---

## Tipos de entidad cubiertos

| Tipo | NIF | Modelos que presenta |
|------|-----|----------------------|
| Autónomo ED normal/simplificada | DNI | 037, 130, 303, 390, 100, 111/190 |
| Autónomo módulos | DNI | 037, 131 (sin libros contables) |
| Autónomo REAG | DNI | 037, 100 (sin IVA — compensación) |
| S.L. / S.A. | B/A- | 036, 200, 202, 303, 390, 111/190, 347 |
| Comunidad de Bienes / S.C. | E- | 036, 184, 303, 390 |
| Comunidad de Propietarios | H- | 036, 347, 111/190 si empleados (sin IVA, sin IS) |
| Asociación / Fundación | G/F- | 036, estatutos, 200 si no exenta |
| Cooperativa | F- | 036, escritura, 200 (IS régimen especial) |
| Arrendador persona física | DNI | 100, 115/180 (sin actividad empresarial) |
| Autónomo recargo equivalencia | DNI | 037, 100 (sin 303 por ventas) |

### Regímenes especiales transversales

| Régimen | Afecta a | Impacto |
|---------|---------|---------|
| RECC (criterio de caja) | Autónomos, S.L. pequeñas | IVA declarado al cobro/pago |
| Prorrata general/especial | Cualquier actividad mixta | % deducción IVA varía por año |
| Sectores diferenciados | Médicos, promotores... | Cada sector tiene % propio |
| ISP (inversión sujeto pasivo) | Construcción, metales | IVA lo declara el receptor |
| OSS/IOSS | E-commerce | IVA intracomunitario centralizado |
| REBU | Coches usados, antigüedades | IVA sobre margen |

---

## Documentos por tipo de entidad

### Autónomo ED
| Doc | Obligatorio | Qué aporta |
|-----|------------|-----------|
| 037 | ✅ | Identidad, régimen IVA, epígrafe IAE |
| Libro facturas emitidas CSV | ✅ | Clientes habituales, series |
| Libro facturas recibidas CSV | ✅ | Proveedores habituales, cuentas gasto |
| 303 × 4 trimestres | ⚡ | Prorrata real, RECC, cuotas pendientes |
| 130 último año | ⚡ | Rendimiento actividad, pagos fraccionados |
| 100 último año | ⚡ | Deducciones IRPF, retención % en facturas |
| Libro bienes inversión CSV | ⚡ si aplica | Regularización quinquenal futura |

### Autónomo módulos
| Doc | Obligatorio | Qué aporta |
|-----|------------|-----------|
| 037 | ✅ | Epígrafe módulo, actividad |
| 131 último año | ✅ | Módulos aplicados, rendimiento |

### S.L. / S.A.
| Doc | Obligatorio | Qué aporta |
|-----|------------|-----------|
| 036 | ✅ | Identidad, régimen IVA |
| Escritura constitución | ✅ | Capital social, socios, administradores |
| Libro facturas emitidas CSV | ✅ | Clientes habituales |
| Libro facturas recibidas CSV | ✅ | Proveedores habituales |
| Sumas y saldos Excel | ✅ | Saldos apertura |
| 200 último año | ⚡ | BINs por año, tipo IS, ERD, deducciones |
| 202 último año | ⚡ | Pagos fraccionados pendientes |
| 111/190 | ⚡ si trabajadores | Retenciones, nómina media |

### Comunidad de Propietarios
| Doc | Obligatorio | Qué aporta |
|-----|------------|-----------|
| 036 | ✅ | NIF H-, domicilio |
| Presupuesto anual | ⚡ | Cuotas ordinarias, fondo reserva |
| 347 | ⚡ | Proveedores habituales |
| 111/190 | ⚡ si empleados | Portero, jardinero |

### Asociación / Fundación
| Doc | Obligatorio | Qué aporta |
|-----|------------|-----------|
| 036 | ✅ | NIF G/F-, actividad |
| Estatutos | ✅ | Exención Ley 49/2002, objeto social |
| 200 | ⚡ si no exenta | Actividades exentas vs no exentas |
| Libro facturas recibidas CSV | ⚡ | Proveedores |

### Comunidad de Bienes / S.C.
| Doc | Obligatorio | Qué aporta |
|-----|------------|-----------|
| 036 | ✅ | NIF E-, comuneros |
| 184 último año | ✅ | Reparto rentas entre comuneros |
| Libros facturas CSV | ✅ | Proveedores/clientes |

### Arrendador persona física
| Doc | Obligatorio | Qué aporta |
|-----|------------|-----------|
| DNI / 037 | ✅ | Identidad |
| 100 último año | ✅ | Rendimiento capital inmobiliario |
| 115/180 | ⚡ si retiene | Arrendatarios persona jurídica |
| Contratos de arrendamiento | ⚡ | Inmuebles, rentas, tipo (residencial/comercial) |

---

## Modelo de datos — PerfilEmpresa (acumulador)

```python
PerfilEmpresa:
  # Bloque 1 — Identificación
  nif: str
  nombre_razon_social: str
  nombre_comercial: str | None
  domicilio_fiscal: dict
  domicilio_notificaciones: dict | None
  domicilio_actividad: dict | None
  fecha_alta_censal: date
  fecha_inicio_actividad: date | None
  fecha_baja: date | None
  territorio: str          # peninsula | canarias | pais_vasco | navarra | ceuta | melilla
  forma_juridica: str      # autonomo | sl | sa | cb | sc | coop | asociacion |
                           # comunidad | fundacion | arrendador | rec_equivalencia | reag
  cnae: str | None
  epigrafe_iae: list[str]
  nif_iva_intracomunitario: str | None

  # Bloque 2 — Régimen IVA
  regimen_iva: str
  recc: bool
  recc_fecha_acogida: date | None
  prorrata_tipo: str | None             # general | especial | ninguna
  prorrata_historico: dict[int, float]  # año → % — CRÍTICO para bienes inversión
  prorrata_provisional_actual: float | None
  sectores_diferenciados: list[dict]
  isp_aplicable: bool
  isp_actividades: list[str]
  oss_pais_registro: str | None
  operaciones_intracomunitarias: bool

  # Bloque 3 — IRPF / IS
  tipo_is: float | None          # 25 | 23 | 15 | 20 | 10...
  es_erd: bool
  bins_por_anyo: dict[int, float]
  reserva_capitalizacion_pendiente: float | None
  reserva_nivelacion_pendiente: float | None
  deducciones_is_pendientes: dict[str, float]
  ejercicio_fiscal_inicio: str   # "01-01" o fecha no estándar
  retencion_facturas_pct: float | None   # 15% general, 7% nueva actividad
  es_nueva_actividad: bool
  pagos_fraccionados_por_trimestre: dict[str, float]

  # Bloque 4 — Bienes de inversión IVA (art. 99-110 LIVA)
  bienes_inversion_iva: list[dict]
  # Cada item: descripcion, fecha_adquisicion, fecha_puesta_servicio,
  #            precio_adquisicion, iva_soportado_deducido,
  #            pct_deduccion_anyo_adquisicion, tipo_bien (inmueble|resto),
  #            anyos_regularizacion_restantes, transmitido, fecha_transmision

  # Bloque 5 — Socios y administradores (S.L./S.A.)
  socios: list[dict]
  # Cada item: nif, nombre, pct_participacion, es_administrador,
  #            tipo_administracion, retribucion_administrador
  operaciones_vinculadas: bool
  supera_umbral_232: bool

  # Bloque 6 — Trabajadores
  tiene_trabajadores: bool
  numero_trabajadores: int | None
  ccc: str | None
  retencion_media_irpf_nominas: float | None
  nomina_mensual_media: float | None

  # Bloque 7 — Inmuebles (arrendador)
  inmuebles: list[dict]
  # Cada item: referencia_catastral, direccion, tipo (residencial|comercial|...),
  #            nif_arrendatario, renta_mensual, con_retencion, con_iva,
  #            anyo_adquisicion, valor_adquisicion, gastos_deducibles

  # Bloque 8 — Obligaciones informativas adicionales
  obligaciones_adicionales: list[str]
  # "720" | "232" | "179" | "238" | "184" | "180" | "190"

  # Bloque 9 — Entidades habituales
  proveedores_habituales: list[dict]
  clientes_habituales: list[dict]

  # Bloque 10 — Saldos apertura
  sumas_saldos: dict[str, dict] | None  # subcuenta → {deudor, acreedor}

  # Bloque 11 — Metadatos del proceso
  documentos_procesados: list[str]
  documentos_pendientes: list[str]
  confianza: float           # 0.0 – 1.0
  advertencias: list[str]
  bloqueos: list[str]
```

---

## Tablas BD nuevas (migración 017)

```sql
-- Un lote por gestoría
CREATE TABLE onboarding_lotes (
  id                  INTEGER PRIMARY KEY,
  gestoria_id         INTEGER NOT NULL REFERENCES gestorias(id),
  nombre              TEXT NOT NULL,
  fecha_subida        DATETIME NOT NULL,
  estado              TEXT NOT NULL DEFAULT 'procesando',
      -- procesando | pendiente_revision | creando_fs | completado | error
  total_clientes      INTEGER DEFAULT 0,
  completados         INTEGER DEFAULT 0,
  en_revision         INTEGER DEFAULT 0,
  bloqueados          INTEGER DEFAULT 0,
  con_error           INTEGER DEFAULT 0,
  usuario_id          INTEGER REFERENCES usuarios(id),
  notas               TEXT
);

-- Un perfil por cliente del lote
CREATE TABLE onboarding_perfiles (
  id                  INTEGER PRIMARY KEY,
  lote_id             INTEGER NOT NULL REFERENCES onboarding_lotes(id),
  empresa_id          INTEGER REFERENCES empresas(id),  -- NULL hasta crear
  nif                 TEXT NOT NULL,
  nombre_detectado    TEXT,
  forma_juridica      TEXT,
  territorio          TEXT,
  confianza           REAL DEFAULT 0,
  estado              TEXT NOT NULL DEFAULT 'borrador',
      -- borrador | pendiente_revision | bloqueado | aprobado | creado | error
  datos_json          TEXT NOT NULL DEFAULT '{}',
  advertencias_json   TEXT NOT NULL DEFAULT '[]',
  bloqueos_json       TEXT NOT NULL DEFAULT '[]',
  revisado_por        INTEGER REFERENCES usuarios(id),
  fecha_revision      DATETIME
);

-- Un registro por archivo subido
CREATE TABLE onboarding_documentos (
  id                  INTEGER PRIMARY KEY,
  perfil_id           INTEGER NOT NULL REFERENCES onboarding_perfiles(id),
  nombre_archivo      TEXT NOT NULL,
  tipo_detectado      TEXT,
  confianza_deteccion REAL DEFAULT 0,
  datos_extraidos_json TEXT DEFAULT '{}',
  ruta_archivo        TEXT,
  fecha_procesado     DATETIME,
  error               TEXT
);

-- Tabla nueva para Libro Bienes de Inversión IVA (art. 99-110 LIVA)
-- Independiente de activos_fijos (que es amortización IS, no regularización IVA)
CREATE TABLE bienes_inversion_iva (
  id                              INTEGER PRIMARY KEY,
  empresa_id                      INTEGER NOT NULL REFERENCES empresas(id),
  descripcion                     TEXT NOT NULL,
  fecha_adquisicion               DATE NOT NULL,
  fecha_puesta_servicio           DATE,
  precio_adquisicion              NUMERIC(12,2) NOT NULL,
  iva_soportado_deducido          NUMERIC(12,2) NOT NULL,
  pct_deduccion_anyo_adquisicion  NUMERIC(5,2) NOT NULL,
  tipo_bien                       TEXT NOT NULL,  -- inmueble | resto
  anyos_regularizacion_total      INTEGER NOT NULL,  -- 10 inmuebles | 5 resto
  anyos_regularizacion_restantes  INTEGER NOT NULL,
  transmitido                     BOOLEAN DEFAULT FALSE,
  fecha_transmision               DATE,
  activo                          BOOLEAN DEFAULT TRUE
);
```

---

## Flujo de procesamiento (7 fases)

### Fase 1 — Ingesta
- Acepta ZIP, PDFs sueltos, CSVs, Excel
- Descomprime y agrupa por cliente:
  a. Por carpeta (si la gestoría las organizó)
  b. Por NIF en nombre de archivo
  c. Por NIF extraído del contenido (fallback)
  d. Sin agrupar → cola revisión manual

### Fase 2 — Clasificación de documentos
- CSV/Excel: detectar columnas → tipo de libro
- PDF con texto: regex sobre cabeceras AEAT → tipo de modelo
- PDF sin texto (scan): OCR Tier 0 (Mistral) → reintenta clasificación
- Desconocido → cola revisión manual

**Tipos detectados**: censo_036_037, escritura_constitucion, estatutos,
is_anual_200, is_fraccionado_202, iva_trimestral_303, iva_anual_390,
irpf_fraccionado_130, irpf_modulos_131, irpf_anual_100,
retenciones_trimestral_111, retenciones_anual_190, operaciones_347,
atribucion_rentas_184, libro_facturas_emitidas, libro_facturas_recibidas,
libro_bienes_inversion, sumas_y_saldos, presupuesto_ccpp

### Fase 3 — Extracción por tipo
| Parser | Implementación |
|--------|---------------|
| censo_036_037 | `ocr_036.py` ✅ ya implementado |
| escritura_constitucion | `ocr_escritura.py` ✅ ya implementado |
| estatutos | pdfplumber + NLP básico → exención 49/2002 |
| is_anual_200 | parser nuevo — BINs, tipo IS, ERD, ejercicio fiscal |
| iva_trimestral_303 | parser nuevo — régimen, prorrata, RECC |
| iva_anual_390 | parser nuevo — prorrata definitiva, resumen |
| irpf_fraccionado_130 | parser nuevo — pagos YTD, rendimiento |
| irpf_anual_100 | parser nuevo — retención %, deducciones |
| retenciones_111 | parser nuevo — trabajadores, importe |
| operaciones_347 | parser nuevo — terceros > 3.005€ |
| libro_facturas_* | pandas CSV — columnas AEAT estándar |
| sumas_y_saldos | pandas Excel — formato libre |
| libro_bienes_inversion | pandas CSV — columnas reglamentarias AEAT |
| presupuesto_ccpp | pandas Excel configurable |

**Todos los PDFs** generados por software o descargados de AEAT tienen texto
extraíble con pdfplumber → coste OCR ≈ 0. Solo se activa OCR para documentos
físicos escaneados.

### Fase 4 — Acumulación del perfil
- Reglas de prioridad si hay conflicto entre documentos
- Detección `forma_juridica` desde prefijo NIF + tipo documento
- Detección `territorio` desde CP en domicilio 036:
  - CP 01xxx/20xxx/48xxx → `pais_vasco` → **BLOQUEAR**
  - CP 31xxx → `navarra` → **BLOQUEAR**
  - CP 35xxx/38xxx → `canarias` → advertir (IGIC)
- Enriquecimiento cruzado: sumas_saldos detecta cuentas 550/551 → operación vinculada
- Upsert en `directorio_entidades` por cada CIF de libros facturas

### Fase 5 — Validación y score de confianza

**Checks duros (bloquean creación)**:
- NIF inválido (checksum)
- Territorio País Vasco / Navarra
- NIF contradictorio entre documentos
- Sin 036/037 (base obligatoria)
- Sumas y saldos no cuadran (diferencia > 1€)

**Checks blandos (advierten)**:
- Bienes inversión sin historial prorrata completo
- Ejercicio fiscal no estándar
- Cuenta 550/551/552 con saldo → préstamo socio
- BINs sin detalle por año
- Cuenta 4750 con saldo → deuda AEAT preexistente
- Canarias/Ceuta/Melilla → revisar régimen especial

**Score ponderado**:
```
+40  036/037 válido y NIF verificable
+20  libros facturas (emitidas + recibidas)
+15  sumas y saldos o balance
+10  tipo entidad detectado con seguridad
+10  régimen IVA confirmado
+05  sin inconsistencias

-30  NIF inválido
-20  inconsistencia NIF entre documentos
-15  territorio pais_vasco | navarra (bloqueo)
-10  bienes inversión sin historial prorrata
-10  sumas y saldos no cuadran
-05  ejercicio fiscal no estándar
```

Umbrales: ≥85 automático | 60-84 con revisión | <60 borrador | negativo bloqueado

### Fase 6 — Creación automática (si confianza ≥ 60 y sin bloqueos duros)

**Pre-condición**: verificar `gestoria.limite_empresas >= empresas_actuales + total_lote`
antes de iniciar el lote. Si no hay cuota → bloquear todo el lote con mensaje claro.

Por cada empresa aprobada:
1. Crear `Empresa` en BD con `estado_onboarding = CREADA_MASIVO`
2. Añadir `forma_juridica = "arrendador"` si aplica (nuevo valor)
3. Guardar campos fiscales extras en `config_extra` JSON:
   `recc`, `prorrata_historico`, `bins_por_anyo`, `tipo_is`, `es_erd`,
   `retencion_facturas_pct`, `operaciones_vinculadas`, `obligaciones_adicionales`
4. Crear registro `onboarding_cliente` vacío (para portal wizard)
5. Generar `slug` desde NIF + nombre normalizado (centralizado en `Empresa.generar_slug()`)
6. Crear carpeta `clientes/{slug}/` en disco con subdirectorios
7. Generar `clientes/{slug}/config.yaml` desde `PerfilEmpresa`
   (**CRÍTICO**: pipeline_runner requiere slug + config.yaml en disco)
8. Crear empresa en FacturaScripts via `fs_setup.py` — extendido con `tipo_pgc`:
   - autonomo/sl/sa/cb/sc → PGC General o PGC PYMES
   - asociacion/fundacion → PGC Entidades Sin Fines Lucrativos
   - cooperativa → PGC Cooperativas
9. Cargar sumas y saldos → asiento apertura (cuenta 129 + subcuentas)
10. Crear proveedores/clientes en `proveedores_clientes` + en FS
11. Cargar `bienes_inversion_iva` si hay libro de bienes inversión
12. Insertar `OperacionPeriodica` con `tipo="regularizacion_iva"` por cada bien
13. Enviar invitación al empresario via `email_service.py`
14. Marcar `onboarding_perfiles.estado = "creado"`

### Fase 7 — Dashboard de revisión
- Vista por lote: progreso en tiempo real, estado por cliente
- Por cada PENDIENTE REVISIÓN: qué se extrajo, qué falta, formulario completar
- Por cada BLOQUEADO: motivo exacto + instrucciones resolución
- Botón "Aprobar y crear" por cliente individual
- Al finalizar: descarga informe PDF del lote

---

## Estructura de carpetas generada

```
clientes/
  {slug}/                        ← generado: "{nif}-{nombre-normalizado}"
    config.yaml                  ← generado automáticamente desde PerfilEmpresa
    inbox/
    procesados/
    cuarentena/
    modelos_fiscales/
    onboarding/                  ← documentos originales del alta (histórico)
      036.pdf
      libros_facturas/
        emitidas_2024.csv
        recibidas_2024.csv
      200_2024.pdf
      sumas_saldos_2024.xlsx
      escritura.pdf
```

---

## Ajustes al sistema existente (prerequisitos)

| # | Tipo | Cambio | Archivo |
|---|------|--------|---------|
| C1 | CRÍTICO | Generación slug centralizada + obligatoria | `modelos.py` |
| C2 | CRÍTICO | Nueva tabla `bienes_inversion_iva` | migración 017 |
| C3 | CRÍTICO | `fs_setup.py` — param `tipo_pgc` | `fs_setup.py` |
| C4 | CRÍTICO | Pre-verificar cuota plan antes del lote | nuevo endpoint |
| I1 | Importante | Añadir `arrendador` a `forma_juridica` | `modelos.py` |
| I2 | Importante | `FEATURES_GESTORIA["onboarding_masivo"] = Tier.PRO` | `tiers.py` |
| I3 | Importante | Extender `config_desde_bd.py` con campos de `config_extra` | `config_desde_bd.py` |
| I4 | Importante | Crear `onboarding_cliente` vacío por empresa del lote | lote processor |
| I5 | Importante | `EstadoOnboarding.CREADA_MASIVO` | `modelos.py` |
| I6 | Mejora | Upsert `directorio_entidades` durante ingesta libros | parser libros |

---

## Tests requeridos

| Test | Qué verifica |
|------|-------------|
| `test_clasificador_documentos` | Detecta tipo correcto de cada PDF/CSV |
| `test_parser_036_037` | Ya existe ✅ |
| `test_parser_modelos_fiscales` | 200, 303, 390, 130, 100 extraen campos clave |
| `test_parser_libros_aeat` | CSV → proveedores/clientes correctos |
| `test_acumulador_perfil` | Fusión correcta de múltiples documentos |
| `test_score_confianza` | Ponderación correcta, bloqueos duros funcionan |
| `test_deteccion_territorio` | País Vasco/Navarra → bloqueado |
| `test_generacion_slug` | Sin colisiones, caracteres seguros, persistido en BD |
| `test_generacion_config_yaml` | Config generado válido para pipeline |
| `test_creacion_carpetas_disco` | Estructura completa creada correctamente |
| `test_batch_fs_reanudable` | Si falla en cliente N, retoma desde N |
| `test_verificacion_cuota_previa` | Bloquea lote si supera límite plan |
| `test_bienes_inversion_iva` | Libro bienes inversión → tabla correcta |
| `test_onboarding_e2e_autonomo` | ZIP completo autónomo → empresa activa |
| `test_onboarding_e2e_sl` | ZIP S.L. → empresa + apertura + socios |
| `test_onboarding_e2e_ccpp` | ZIP comunidad propietarios → sin IVA/IS |
| `test_onboarding_e2e_asociacion` | ZIP asociación → PGC ESFL correcto |
| `test_onboarding_e2e_parcial` | ZIP incompleto → queda en revisión |
| `test_onboarding_bloqueado_pais_vasco` | CIF domicilio Bilbao → bloqueado |

---

## Decisiones de diseño

- **`config_extra` JSON** almacena campos fiscales extras sin nuevas columnas en `empresas`
- **`bienes_inversion_iva`** es tabla separada de `activos_fijos` — son conceptos distintos
  (regularización IVA vs amortización IS)
- **Slug generación centralizada** en `Empresa` — prerequisito del pipeline_runner
- **`CREADA_MASIVO`** distingue empresas creadas en batch de las creadas con wizard individual
- **PGC correcto por tipo** — Asociaciones con PGC General serían error contable grave
- **Coste OCR ≈ 0** — documentos de onboarding son PDFs con texto extraíble (software/AEAT)
- **Proceso reanudable** — estado por empresa permite reiniciar desde el punto de fallo
- **Onboarding masivo = feature Pro** de gestoría (definido en `FEATURES_GESTORIA`)
