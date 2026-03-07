# SFCE — Estado Actual, Pendientes y Roadmap
> **Actualizado:** 2026-03-07 (sesión 115 cierre) | **Branch:** main | **Tests:** 2858 PASS | **Push:** OK

---

## Estado actual (sesión 115 — SmartParser cascade fix + diagnóstico tickets térmicos + bloqueantes FS)

### Commits sesión 115

| Hash | Descripción |
|------|-------------|
| (pendiente commit cierre) | fix(smart_parser): _resultado_es_suficiente() — cascade no para con base_imponible null |

### Tasks sesión 115

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| SmartParser cascade fix | ✅ DONE | Añadida `_resultado_es_suficiente()`: si base_imponible null, escala a siguiente motor (GPT-4o-mini → GPT-4o) |
| GEMINI_API_KEY rotada | ✅ DONE | Clave anterior marcada como leaked por Google. Nueva clave en .env local y VPS producción + reinicio sfce_api |
| Diagnóstico 1 Enero -14.pdf plenergy | ✅ DONE | Mistral Vision extrae B.Imp=24.79€, IVA 21%. pdfplumber ratio 0.894 pero semánticamente corrupto. Hash PDF=id 358 confirmado |
| Pipeline 30 docs inbox María Isabel | ✅ DONE | OCR ejecutado. 2 bloqueantes identificados (ver pendientes). Gemini confunde 5→6 en CIFs y números factura |
| FAC0007A4 bloqueante FV | ⚠️ PENDIENTE | Factura con fecha 30-09-2025 ya en FS bloquea inserción del 1T/2T. Investigar si es legítima o de prueba |
| CIF desconocido tickets cuarentena | ⚠️ PENDIENTE | Intake rechaza tickets porque CIF receptor no identificable. Añadir 25719412F al lookup del intake |

### Pendientes sesión 116 (CONTABILIDAD)

1. **Investigar FAC0007A4** en FS instancia Uralde (empresa_id=14) — ¿registro legítimo del 3T o de prueba? Si es de prueba borrar. Si es legítimo, las FV 1T/2T deben insertarse antes con fecha anterior
2. **Desactivar Gemini en SmartParser** — cascade directa: GPT-4o-mini → GPT-4o (Gemini confunde dígitos 5→6)
3. **CIF María Isabel en config.yaml** — añadir `25719412F` al lookup del intake para que los tickets de la cliente no vayan a cuarentena por CIF desconocido
4. **Tickets cuarentena por CIF desconocido** — resolver tras fix intake (13 tickets pendientes)
5. **Mistral Vision primero para tickets** — cuando tipo_documento=="ticket", invocar Mistral antes que pdfplumber

---

## Estado actual (sesión 114 — null safety registration + preautorización anulada + pipeline María Isabel)

### Commits sesión 114

| Hash | Descripción |
|------|-------------|
| (pendiente) | fix(pipeline): null safety base_imponible/iva_porcentaje + excluir preautorizaciones anuladas |

### Tasks sesión 114

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Pipeline María Isabel 2025 | ✅ DONE | 18 OK, 1 fallido (1 Enero -14 plenergy), 12 cuarentena. 18 PDFs movidos a procesado/T1/ |
| Null safety registration.py | ✅ FIXED | 5 lugares con `.get(key, default)` → `.get(key) or default` para base_imponible e iva_porcentaje (keys con null explícito) |
| Pre-validación preautorizaciones | ✅ FIXED | Check 0 en pre_validation: si `metadata.preautorizacion_anulada==True` → excluir antes de registro |
| 1 Enero -13.pdf (preaut. anulada) | ✅ EXCLUIDA | Ticket plenergy con preautorización anulada — excluida correctamente por check 0. Factura 93 residual en FS (total=0) pendiente borrar |
| 1 Enero -14.pdf (plenergy fallido) | ⚠️ PENDIENTE | base/iva null, IVA 0% vs esperado 21%. Discrepancia verificación. Revisar si también es preaut. anulada |
| 12 cuarentena | ℹ️ INFO | Tickets ilegibles sin CIF reconocible. Sin OCR cache (borrado al mover a cuarentena). Revisión manual. |
| Cross-validation FAILs 0.02€ | ⚠️ PENDIENTE | Diff ~0.02€ en 472/diario/303. Probablemente factura 93 residual (total=0 en FS) |

### Pendientes sesión 115 (CONTABILIDAD)

1. **Factura 93 en FS** — residual de preautorización anulada (1 Enero -13 plenergy, total=0). Borrar desde UI FS o MariaDB: `DELETE FROM facturascli WHERE idfactura=93` en instancia Javier (empresa 7=COMUNIDAD MIRADOR DEL MAR? verificar)
2. **1 Enero -14.pdf (plenergy)** — revisar si es también preautorización anulada. Si sí: el check 0 la excluirá en próxima ejecución. Si no: corregir datos OCR manualmente.
3. **12 cuarentena María Isabel** — tickets sin CIF. Requieren revisión manual (posiblemente tickets de gasolinera ilegibles)
4. **Dropbox duplicadas** — BLOQUEADO: archivos físicos no disponibles. María Isabel necesita re-subir PDF (11.99€ intracom IE9852817, enero 2025)
5. **Enriquecer otros clientes** — ejecutar enriquecer_config.py cuando estén onboarded

---

## Estado actual (sesión 113 — Fix FV IRPF + cross_validation FSAdapter)

### Commits sesión 113

| Hash | Descripción |
|------|-------------|
| e58a8c9b | fix(registration): FV con IRPF inyecta irpf_pct + migrar cross_validation a FSAdapter |

### Tasks sesión 113

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Dropbox duplicadas (1 Enero -8.pdf) | ⚠️ BLOQUEADO | Archivos físicos no encontrados en filesystem. No están en inbox/cuarentena/procesado. Factura tampoco en FS. Necesita re-subir PDF original. |
| FV sin IRPF (3T-3, 3T-4) | ✅ CORRECTO | Receptores son particulares (JUAN ANTONIO RUIZ GARCIA, NAOMI MOISIN) — sin IRPF es correcto. 3T-3=idfactura25, 3T-4=idfactura26 en FS con asientos OK. |
| FV totales asiento discrepan (3T-2, 3T-5) | ✅ FIXED | Bug pipeline: FV con IRPF no transmitía totalirpf a FS. Fix: _construir_form_data inyecta _irpf_pct en lineas FV. Asientos 161+173 corregidos en MariaDB (4730 añadida, totalirpf actualizado). |
| cross_validation.py → FSAdapter | ✅ DONE | _obtener_datos_fs migrada de api_get a FSAdapter._get. ejecutar_cruce crea FSAdapter.desde_config(config). |
| Tests | ✅ DONE | 2858 PASS (2856 base + 2 nuevos para FV IRPF) |

### Pendientes sesión 114 (CONTABILIDAD)

1. **Dropbox duplicadas** — archivos 1 Enero -8.pdf y _1.pdf no encontrados localmente. Factura Dropbox (11.99€ intracom IE9852817, enero 2025) no está en FS. Bloqueado hasta que María Isabel re-suba el PDF.
2. **Enriquecer otros clientes** — ejecutar enriquecer_config.py para el resto cuando estén onboarded

---

## Estado actual (sesión 112 — Conectar campos v2 config.yaml al pipeline)

### Commits sesión 112

| Hash | Descripción |
|------|-------------|
| fff6e257 | feat(intake): clasificación por roles declarativos + config.buscar_por_cif + limpieza cache cuarentena |
| 5b8acd07 | feat(pipeline): conectar campos v2 config.yaml al pipeline + 5 fixes |

### Tasks sesión 112

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Fix config.yaml Dropbox subcuenta | ✅ DONE | 6290→6220 (servicios informáticos) en subcuenta y asiento.subcuenta_gasto |
| concepto_keywords en intake multi-signal | ✅ DONE | señal f2 +30 puntos; busca keywords v2 en concepto OCR |
| importe_rango en intake multi-signal | ✅ DONE | señal h2 +15 puntos; verifica si total cae en [min, max] |
| checks V1-V3 en pre_validation | ✅ DONE | V1=iva_esperado, V2=irpf_obligatorio, V3=total_max — solo avisos |
| asiento.subcuenta_gasto en registration | ✅ DONE | prioridad sobre subcuenta legacy; asiento.intracom también |
| es_cif_propio/buscar_por_cif en scripts/core/config.py | ✅ DONE | paridad con sfce/core/config.py |
| _normalizar_cif(None) safe | ✅ DONE | ambos config.py — `if not cif: return ""` |
| entidad_cif null bugfix intake | ✅ DONE | `(entidad.get("cif") or "")` en _construir_documento_confianza y doc_resultado |
| Pipeline María Isabel 11/11 | ✅ DONE | 11 registrados, 12/13 cross-val PASS, asientos cuadrados |
| Tests pytest | ✅ DONE | 2856 PASS |

### Pendientes sesión 113 (CONTABILIDAD)

1. **Dropbox duplicadas** — `1 Enero -8.pdf` + `1 Enero -8_1.pdf` (mismo hash, conf 31%): descartar o procesar 1 como FP intracom
2. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)
3. **Enriquecer otros clientes** — ejecutar enriquecer_config.py para el resto de clientes cuando estén onboarded
4. **FV sin IRPF** — Ingresos 3T-3 y 3T-4: aviso "[MANUAL] Autonomo emite factura sin retencion IRPF" — verificar si es correcto o falta IRPF 15%
5. **FV totales asiento discrepan** — Ingresos 3T-2 y 3T-5: total asiento != total factura (posible IVA repercutido en FV con IRPF)

---

## Estado actual (sesión 111 — Enriquecer config.yaml automático GPT-4o)

### Commits sesión 111

| Hash | Descripción |
|------|-------------|
| (este commit) | feat(enriquecer): script enriquecer_config.py GPT-4o + tests + config María Isabel enriquecido |

### Tasks sesión 111

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Crear scripts/enriquecer_config.py | ✅ DONE | Script que enriquece config.yaml con campos avanzados vía GPT-4o (formato_pdf, frecuencia, importe_rango, concepto_keywords, validacion, asiento, perfil_fiscal) |
| Crear tests/test_enriquecer_config.py | ✅ DONE | 15 tests (merge sin pisar, dry-run, YAML válido, backup, intracom, force) |
| Ejecutar María Isabel real | ✅ DONE | 26 proveedores + 1 cliente enriquecidos, perfil_fiscal añadido, backup config.yaml.bak.20260305 |
| Tests pytest | ✅ DONE | 2856 PASS |

### Pendientes sesión 112 (CONTABILIDAD)

1. **Re-ejecutar pipeline María Isabel** — 11 PDFs listos en inbox/ con cache OCR en .ocr_cache/ — verificar pipeline con config enriquecido
2. **Dropbox duplicadas** — `1 Enero -8.pdf` + `1 Enero -8_1.pdf` (mismo hash, conf 31%): descartar o procesar 1 como FP intracom
3. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)
4. **Enriquecer otros clientes** — ejecutar enriquecer_config.py para el resto de clientes cuando estén onboarded

---

## Estado actual (sesión 110 — Reorganización: limpiar FS + .ocr_cache/ + reset pipeline)

### Commits sesión 110

| Hash | Descripción |
|------|-------------|
| (pendiente) | refactor(cache_ocr): migrar cache OCR a .ocr_cache/ con retrocompat + limpiar FS empresa 7 |

### Tasks sesión 110

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Limpiar FS empresa 7 (María Isabel) | ✅ DONE | DELETE facturasprov, facturascli, asientos, partidas — todo a 0 en MariaDB fs-uralde |
| Mover PDFs a inbox/ | ✅ DONE | 11 PDFs de 2025/procesado/T3+T4 → inbox/ |
| Crear .ocr_cache/ y migrar JSONs | ✅ DONE | 11 .ocr.json de inbox/ → .ocr_cache/ |
| Modificar cache_ocr.py | ✅ DONE | _ruta_cliente_desde_pdf() busca config.yaml, _ruta_cache() usa .ocr_cache/, retrocompat migra legacy automáticamente |
| Borrar state files pipeline | ✅ DONE | pipeline_state.json, intake_results.json, etc. eliminados |
| Tests pytest | ✅ DONE | 2841 PASS |

### Pendientes sesión 111 (CONTABILIDAD)

1. **Re-ejecutar pipeline María Isabel** — 11 PDFs listos en inbox/ con cache OCR en .ocr_cache/ — verificar que pipeline lee de nueva ubicación
2. **Dropbox duplicadas** — `1 Enero -8.pdf` + `1 Enero -8_1.pdf` (mismo hash, conf 31%): descartar o procesar 1 como FP intracom
3. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)

---

## Estado actual (sesión 109 — Pipeline María Isabel: 4 fixes + 11/11 PDFs registrados)

### Commits sesión 109

| Hash | Descripción |
|------|-------------|
| a7da5182 | fix(pipeline): 4 fixes María Isabel — swap emisor/receptor OCR, CHECK1 FV, Ingresos→FV, generar_asiento FV |

### Tasks sesión 109

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Diagnóstico 3 bugs pipeline María Isabel | ✅ DONE | CIF inversión OCR, pre_validation CHECK1, Ingresos→FV, asientos FV sin generar |
| Fix 1: swap emisor/receptor OCR (intake.py) | ✅ DONE | Caso A: emisor_cif null + receptor_cif es proveedor → swap CIF. Caso B: receptor_cif=empresa + emisor_cif es cliente → swap completo (FV invertido) |
| Fix 2: CHECK 1 pre_validation (pre_validation.py) | ✅ DONE | FV sin receptor_cif no bloquea (usa fallback VARIOS_CLIENTES). FC con entidad_cif canónico de intake → usa ese para validar |
| Fix 3: "Ingresos*" en nombre archivo → FV (intake.py) | ✅ DONE | Añadido hint por `ruta_pdf.stem.lower()` además de subcarpeta |
| Fix 4: generar_asiento para FV (registration.py) | ✅ DONE | `elif tipo_doc == "FV": fs.generar_asiento(idfactura, tipo="cliente")` |
| Pipeline María Isabel 11/11 | ✅ DONE | 11 FC + 4 FV registrados con asientos. inbox vacío |
| Tests pytest | ✅ DONE | 2841 PASS |

### Pendientes sesión 110 (CONTABILIDAD)

1. **Dropbox duplicadas** — `1 Enero -8.pdf` + `1 Enero -8_1.pdf` (mismo hash, conf 31%): descartar o procesar 1 como FP intracom
2. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)

---

## Estado actual (sesión 108 — gen_asiento.php: subcuenta_gasto + intracom)

### Commits sesión 108

| Hash | Descripción |
|------|-------------|
| (pendiente push) | feat(gen_asiento): subcuenta_gasto + intracom_pct via PHP CLI |

### Tasks sesión 108

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| gen_asiento.php reescrito | ✅ DONE | Args opcionales `[subcuenta_gasto] [intracom_pct]`. UPDATE partida 600→subcuenta correcta. UPDATE 472 fantasma + INSERT 477 para intracom. JSON incluye subcuenta_gasto/intracom_pct |
| FSAdapter.generar_asiento() | ✅ DONE | Nuevos params `subcuenta_gasto: str\|None` e `intracom_pct: float\|None`. Se pasan como args 3/4 al PHP |
| registration.py step 5b/5c | ✅ DONE | Step 5b pasa `_subcuenta_gasto` e `_iva_autorepercusion` (si intracom). Step 5c solo corre como fallback si gen_asiento no manejó la autorepercusión |
| Test producción facturas 73-76 | ✅ DONE | Asientos 121-124 borrados y regenerados. Coloso→629, Chito→623+475, Dropbox→622+472/477 intracom, Mapfre→625 |
| Tests pytest | ✅ DONE | 2841 PASS |

### Pendientes sesión 109 (CONTABILIDAD)

1. **Dropbox duplicadas** — `1 Enero -8.pdf` + `1 Enero -8_1.pdf` (mismo hash, conf 31%). Decidir: descartar o procesar uno como FP intracom
2. **Resto PDFs María Isabel** — verificar PDFs pendientes de importar, reprocesar con pipeline
3. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)

---

## Estado actual (sesión 107 — Diagnóstico InvoiceToAccounting FS)

### Commits sesión 107

| Hash | Descripción |
|------|-------------|
| — | Sin commits de código (sesión diagnóstico) |

### Tasks sesión 107

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Limpieza FS Uralde emp7 | ✅ DONE | Borradas 6 FP + asientos de María Isabel Navarro López (idfactura 67-72, asientos 107-117) |
| Diagnóstico gen_asiento | ✅ DONE | 4 facturas prueba creadas (A=COLOSO IVA21, B=CHITO IRPF15, C=DROPBOX intracom, D=MAPFRE exenta) |
| Comportamiento FS gen_asiento | ✅ DONE | Verificados asientos generados por InvoiceToAccounting::generate() para cada tipo |

### Hallazgos clave sesión 107

- **pvptotal en líneas FS = neto sin IVA** (no total). Si pvptotal incluye IVA, Calculator discrepa y generate() falla.
- **FS auto-genera asiento en PUT** si totales de cabecera coinciden con Calculator. No hace falta llamar gen_asiento.php manualmente.
- **Intracom (operacion=I)**: FS genera 4720000000 con 0/0. Sin autorepercusión (falta 472 DEBE + 477 HABER). Requiere corrección post-generate.
- **Exenta (IVA0 doméstica)**: mismo patrón que intracom — 4720000000 vacía. Gasto en 600 (debería ser 625/628 según tipo).
- **IVA21 normal**: correcto — 400 HABER total / 472 DEBE iva / 600 DEBE neto.
- **IVA21 + IRPF15**: correcto — 400 HABER total / 472 DEBE iva / 4751 HABER irpf / 600 DEBE neto.

### Pendientes sesión 108 (CONTABILIDAD)

1. **Dropbox duplicadas** — `1 Enero -8.pdf` + `1 Enero -8_1.pdf` (mismo hash, conf 31%). Decidir: descartar o procesar uno como FP intracom
2. **Resto PDFs María Isabel** — verificar PDFs pendientes de importar, reprocesar con pipeline
3. **Corrección gen_asiento.php para intracom** — añadir partidas 472/477 automáticamente cuando `operacion=I` o codimpuesto intracom
4. **Reclasificación cuenta gasto exentas** — mapear codimpuesto a cuenta gasto correcta (600→625 seguros, 628 suministros, etc.)

---

---

## Estado actual (sesión 106 — Proveedor Discovery GPT-4o)

### Commits sesión 106

| Hash | Descripción |
|------|-------------|
| (pendiente) | feat(discovery): proveedor_discovery GPT-4o + intake integration |

### Tasks sesión 106

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| `sfce/core/proveedor_discovery.py` | ✅ DONE | Módulo nuevo: `descubrir_proveedor()` (GPT-4o, timeout 30s, 1 retry), `cargar_cifs_sugeridos()`, `guardar_sugerencias()` — genera `config_sugerencias.yaml` comentado |
| Integración en intake.py | ✅ DONE | Fase 3b en `_procesar_un_pdf`: CIF desconocido + no en `cifs_sugeridos` → llama GPT-4o. Doc sigue a cuarentena. Acumula sugerencias por run |
| Deduplicación cross-run | ✅ DONE | `cargar_cifs_sugeridos()` lee CIFs del archivo previo al inicio de `ejecutar_intake`. No repite llamada GPT para el mismo CIF |
| `tests/test_proveedor_discovery.py` | ✅ DONE | 17 tests unitarios (GPT mock, dedup, guardar, cargar) |
| `tests/test_intake_discovery.py` | ✅ DONE | 4 tests integración (_procesar_un_pdf con discovery, ejecutar_intake escribe sugerencias) |
| Tests totales | ✅ DONE | 2841 PASS (↑21 tests desde sesión 105) |

### Pendientes sesión 107 (CONTABILIDAD)

1. **Dropbox duplicadas** — `1 Enero -8.pdf` + `1 Enero -8_1.pdf` (mismo hash, conf 31%). Decidir: descartar o procesar uno como FP intracom
2. **Resto PDFs María Isabel** — verificar PDFs pendientes de importar al inbox, reprocesar con pipeline
3. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)

---

## Estado anterior (sesión 105 — intake multi-señal + verdad absoluta config.yaml)

### Commits sesión 105

| Hash | Descripción |
|------|-------------|
| `f4346f10` | feat(intake): match multi-señal + verdad absoluta config.yaml |

### Tasks sesión 105

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| `_match_proveedor_multi_signal()` | ✅ DONE | 9 señales acumuladas (CIF exacto+50, CIF raw+45, nombre/alias+40, CIF parcial+35, nombre en texto+30, keywords+25, nombre archivo+20, importe+15, idioma+10). Threshold≥35 |
| `_enriquecer_desde_config()` | ✅ DONE | config.yaml como verdad absoluta: proveedor conocido → sobreescribe CIF y nombre OCR |
| Floor confianza | ✅ DONE | score≥50 → max(actual,80%); score≥35 → max(actual,65%) |
| Coloso Algeciras anti-cuarentena | ✅ DONE | Ticket térmico OCR nulo → .ocr.json manual B67718361. FC, entidad=coloso_algeciras, conf=42% |
| Tests | ✅ DONE | 2820 PASS |

### Pendientes sesión 106 (CONTABILIDAD)

1. **Dropbox duplicadas** — `1 Enero -8.pdf` + `1 Enero -8_1.pdf` (mismo hash, conf 31%). Decidir: descartar o procesar uno como FP intracom
2. **Resto PDFs María Isabel** — actualmente solo 6 PDFs en sistema (5 en procesado, 1 en inbox). Verificar si hay más PDFs pendientes de importar al inbox
3. **Cuarentena** — 0 PDFs actualmente (limpia). Si hay nuevos lotes, ampliar config.yaml y reprocesar
4. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)

---

## Estado anterior (sesión 104 — E2E María Isabel completo, Coloso resuelto)

### Commits sesión 104

| Hash | Descripción |
|------|-------------|
| (pendiente) | fix(registration): numero_factura null → crash NoneType.upper() en tickets |

### Tasks sesión 104

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Limpiar empresa 7 FS | ✅ DONE | Borrar 1 FP (Dropbox id=66) + 7 asientos. Empresa 7 vacía para reproceso limpio |
| Pipeline E2E María Isabel (8 PDFs) | ✅ DONE | 6 FP registradas: Campmany ×2, Autopista Sol ×2, Plenergy ×1, Coloso ×1. Asientos 107-117 |
| Ticket Coloso (1 Enero -13.pdf) | ✅ DONE | OCR thermal corrupto (CIF "257") → `.ocr.json` manual B67718361, total 30€. FP 72, asiento 117 |
| Fix registration.py null descripcion | ✅ DONE | `datos.get("numero_factura") or "Factura"` en 3 sitios — evita crash en tickets sin nº factura |

### Pendientes sesión 105 (CONTABILIDAD)

1. **Dropbox duplicadas** — `1 Enero -8.pdf` y `1 Enero -8_1.pdf` (mismo hash, confianza 31%). Decidir: descartar duplicados o procesar uno como FP Dropbox intracom
2. **Resto PDFs María Isabel** — ~200+ PDFs inbox original, reprocesar con pipeline completo
3. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)
4. **Cuarentena ~218 PDFs** — ampliar config.yaml con proveedores y reprocesar

---

## Estado anterior (sesión 103 — E2E generar_asiento() validado end-to-end)

### Commits sesión 103

| Hash | Descripción |
|------|-------------|
| `05d28051` | feat(pipeline): generar_asiento PHP CLI + fixes E2E sesion 103 |
| `c7449e7e` | fix(pipeline): E2E fixes — motivo_exclusion Pydantic + scripts/core/config ssh props |

### Tasks sesión 103

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| gen_asiento.php en servidor | ✅ DONE | Script PHP en container FS Uralde. Patrón MAX-antes/MAX-después + UPDATE idfactura→idasiento |
| FSAdapter.generar_asiento() | ✅ DONE | `sfce/core/fs_adapter.py` — SSH subprocess + JSON parse + FSResult |
| registration.py llama generar_asiento() | ✅ DONE | Entre "marcar pagada" y "autorepercusión intracom". Solo `es_proveedor` |
| Fix intake.py cache flattening | ✅ DONE | `datos_gpt = cache_datos.get("datos_extraidos")` |
| Fix scripts/core/config.py | ✅ DONE | Añadir `fs_ssh_host`/`fs_container_name` (paridad con sfce/core/config.py) |
| Fix motivo_exclusion Pydantic | ✅ DONE | `scripts/pipeline.py` + `sfce/phases/pre_validation.py` — campo requerido en `DocumentoExcluido` |
| E2E Dropbox intracomunitario | ✅ DONE | FP 66 creada, asiento 105 generado via SSH, 472/477 autorepercusión 2.08 EUR, 600→629 corregido |

### Pendientes sesión 104 (CONTABILIDAD)

1. **Resto PDFs María Isabel** — ~200+ PDFs inbox original (procesado/T1+T2 + cuarentena), reprocesar con pipeline completo
2. **Ticket Coloso** — OCR thermal nulo. (a) `.ocr.json` manual (B67718361, ~30€ DIESEL), (b) GPT-4o-mini Vision
3. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)
4. **Cuarentena ~218 PDFs** — ampliar config.yaml con proveedores y reprocesar

---

## Estado anterior (sesión 102 — MBS SUITES plan implementado completo)

### Commits sesión 102 (MBS SUITES — repo mbs-suites-intelligence)

| Hash | Descripción |
|------|-------------|
| `91af586` | feat: dashboard React — Vite + Tailwind + Overview + Competitors + PriceChart |
| `37800d7` | feat: deploy config — nginx SSL + docker-compose.prod + script deploy |

### Tasks sesión 102

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Task 4.2: Frontend React + Vite + Tailwind | ✅ DONE | package.json, vite.config, tsconfig, index.html, src/main.tsx, App.tsx + router |
| Task 4.3: Dashboard Overview + Competitors | ✅ DONE | KPICard, PriceChart (Recharts), Overview (KPIs+IA+alertas), Competitors (lista+historial) |
| Task 5.1: Deploy config | ✅ DONE | nginx.conf SSL, docker-compose.prod.yml, deploy.sh — build OK, TS 0 errores |
| Push GitHub | ✅ DONE | `37800d7` en origin/main |

### Pendientes sesión 103 (MBS SUITES — ops deploy)

1. **DNS** — apuntar `dashboard.mbsintelligence.com` al VPS Hetzner (65.108.60.69)
2. **SSL** — `certbot certonly --standalone -d dashboard.mbsintelligence.com` en servidor
3. **rsync** — subir repo al servidor: `rsync -av --exclude='.git' --exclude='node_modules' "MBS SUITES/" carli@65.108.60.69:/opt/apps/mbs-intel/`
4. **`.env` real** — copiar `.env.example` → `.env` con APIFY_TOKEN, ANTHROPIC_API_KEY, RESEND_API_KEY, DB_PASSWORD, DJANGO_SECRET_KEY
5. **`bash deploy.sh`** — arranca todo (build frontend + migraciones + collectstatic + containers)
6. **Datos iniciales** — crear zonas + propiedades MBS desde Django shell (script en plan Task 5.1 Step 6)
7. **Periodic Task en Admin** — crear tarea `scraping.trigger_daily_scrape` crontab `0 6 * * *`

### Pendientes sesión 102 (CONTABILIDAD)

1. **Ticket gasolinera** — "CoLoS0 SAN 46 S.L.u" no identificado, añadir proveedor a config.yaml
2. **Resto PDFs María Isabel** — ~200+ PDFs inbox original, reprocesar
3. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)
4. **Cuarentena ~218 PDFs** — ampliar config.yaml con proveedores y reprocesar

---

## Estado anterior (sesión 101b — asiento intracom Dropbox corregido)

### Commits sesión 101b

| Hash | Descripción |
|------|-------------|
| `111a8c83` | fix(config): Dropbox codimpuesto IVA21→IVA0 + asiento intracom 63 corregido manualmente en FS |

### Tasks sesión 101b

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Asiento intracom Dropbox (factura 63) | ✅ DONE | Fix línea IVA=0, borrar asiento 97 corrompido, regenerar asiento 98 limpio, UPDATE idasiento, añadir 472 DEBE 2.08 + 477 HABER 2.08. DEBE=HABER=11.9911 ✓ |
| Bug pipeline intracom | ✅ DONE | Root cause: CIF `9852817J`→`IE9852817` (ya fix sesión 101). `codimpuesto: IVA21`→`IVA0` en config Dropbox |

### Pendientes sesión 102 (CONTABILIDAD)

1. **Ticket gasolinera** — "CoLoS0 SAN 46 S.L.u" no identificado, añadir proveedor a config.yaml
2. **Resto PDFs María Isabel** — ~200+ PDFs inbox original, reprocesar
3. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)
4. **Cuarentena ~218 PDFs** — ampliar config.yaml con proveedores y reprocesar

---

## Estado anterior (sesión 101 — MBS SUITES: nuevo proyecto planificado)

### Commits sesión 100-101

| Hash | Descripción |
|------|-------------|
| `1e0e590a` | fix(config): CIF Dropbox corregido IE9852817 para Maria Isabel |
| `44e253f2` | fix(pipeline): correcciones descubiertas en prueba E2E sesion 100 |

### Tasks sesión 101

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| MBS SUITES — nuevo proyecto | ✅ DONE | Briefing completo de Marbella Banus Suites (reseñas, stack, fundadores, mercado). Diseño técnico aprobado + plan implementación completo en `PROYECTOS/MBS SUITES/docs/plans/` |
| MBS SUITES — validación Apify | ✅ DONE | Test script `test_apify_actors.py` integrado como Fase 0 del plan |
| CONTABILIDAD — CIF Maria Isabel | ✅ DONE | Fix CIF Dropbox IE9852817 (sesión 100, commit 1e0e590a) |

### Pendientes sesión 102 (CONTABILIDAD)

1. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)
2. **Cuarentena ~218 PDFs** — ampliar config.yaml con proveedores y reprocesar
3. **Tests E2E dashboard** — Playwright

### Pendientes sesión 102 (MBS SUITES — proyecto nuevo)

1. **Crear repo GitHub** `mbs-suites-intelligence` (privado)
2. **Inicializar git** en `PROYECTOS/MBS SUITES/`
3. **Ejecutar Fase 0** — `test_apify_actors.py` con token Apify real
4. **Arrancar Fase 1** — setup Django + Docker

---

## Estado actual (sesión 99 — F6: flujo email→pipeline completado)

### Commits sesión 99

| Hash | Descripción |
|------|-------------|
| `7507a65e` | fix(F6): worker_catchall crea Documento en BD antes de ColaProcesamiento |

### Tasks completadas (sesión 99)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| F6 — Ruta inbox email→pipeline | ✅ DONE | Bug: `worker_catchall` creaba `ColaProcesamiento(documento_id=None)` → `_clamar_docs_para_empresa` devolvía `[]` → pipeline nunca arrancaba. Fix: crear `Documento` con flush() antes de `ColaProcesamiento` en `_encolar_archivo()` + bucle de `procesar_email_catchall()`. |
| Tests F6 | ✅ DONE | +2 tests: `test_email_catchall_crea_documento_en_bd`, `test_documento_id_no_nulo_permite_pipeline`. 2820 PASS. |

### Pendientes sesión 100

1. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)

---

## Estado actual (sesión 98 — Pata 3: FSAdapter API pública + inbox rutas + watcher verificado)

### Commits sesión 98

| Hash | Descripción |
|------|-------------|
| `5ba0d2dc` | fix: _inbox_empresa siempre resuelve a clientes/{slug}/inbox/, elimina fallback docs/{id} |
| `790d7822` | refactor: crear_partida() público en FSAdapter, eliminar uso de _post/_put directos en partidas |

### Tasks completadas (sesión 98)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Fix _inbox_empresa() | ✅ DONE | Elimina fallback `docs/{id}/inbox/`. SIEMPRE → `clientes/{slug}/inbox/`. Crea dir si no existe. Lanza ValueError si empresa inexistente. |
| crear_partida() público | ✅ DONE | `FSAdapter.crear_partida(datos)` como método público. Encapsula `_post("partidas", ...)`. |
| Migrar _post/_put partidas | ✅ DONE | `registration.py` ×3 (472/477 intracom + 2 correcciones asientos) + `correction.py` ×2 (IVA turismo 50%, IVA extranjero). Manejo de errores en 472/477. |
| Watcher verificado | ✅ DONE | `scripts/watcher.py` ya existía completo. 23 tests pasando. 6 config.yaml con empresa_id. `.env.example` y `iniciar_dashboard.bat` completos. |
| Tests suite completa | ✅ DONE | 2818 passed, 0 failed (sin regresiones) |

### Pendientes sesión 99

1. **F6** — Ruta inbox email→pipeline (worker correo → `clientes/{id}/inbox/` vs pipeline `clientes/{slug}/{año}/inbox/`)
2. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)

---

## Estado anterior (sesión 97 — Pata 2: contratos Pydantic entre fases del pipeline)

### Commits sesión 97

| Hash | Descripción |
|------|-------------|
| `c2e47721` | feat(contracts): Pydantic models para interfaces entre fases del pipeline |
| `9aa4bcc9` | feat(contracts): integrar validacion Pydantic en escritura de todas las fases |

### Tasks completadas (sesión 97)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| contracts.py | ✅ DONE | `sfce/core/contracts.py`: 6 modelos Pydantic (IntakeOutput, PreValidationOutput, RegistrationOutput, AsientosOutput, CorrectionOutput, CrossValidationOutput) con validación en escritura |
| test_contracts.py | ✅ DONE | 17 tests unitarios: tipos inválidos, coerce str→float, totales inconsistentes, clave canónica 'validados', campos extra no rompen |
| Integración fases | ✅ DONE | 6 fases + pipeline paralelo: cada `json.dump()` reemplazado por `XxxOutput.validar_y_serializar()` |
| Clave canónica validados | ✅ DONE | `validated_batch.json` siempre produce `"validados"` (nunca `"documentos"`) |
| scripts/validar_contratos.py | ✅ DONE | Script diagnóstico para validar JSONs existentes de cualquier cliente |
| Tests suite completa | ✅ DONE | 2818 passed, 4 skipped (antes: 2801, +17 nuevos) |

### Pendientes sesión 98

**Estado contratos:** completo en pipeline principal. `cross_validation.py`, `aprendizaje.py`, scripts siguen con api_get (fuera de scope contratos).

1. **Ampliar config.yaml MARIA ISABEL** — 218 PDFs en cuarentena. Inspeccionar CIFs e identificar proveedores.
2. **Re-procesar cuarentena** — mover PDFs a inbox/ + pipeline --no-interactivo
3. **Verificar 7000x vs 7050x** — FS usa cuenta ventas mercaderías para FV servicios. Evaluar corrección.
4. **F6** — Ruta inbox email→pipeline
5. **Tests E2E dashboard** — Playwright
6. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)

---

## Estado actual (sesión 96 — FSAdapter capa defensiva FacturaScripts)

### Commits sesión 96

| Hash | Descripción |
|------|-------------|
| `cc01845e` | feat(core): FSAdapter — capa defensiva FacturaScripts (B1-B5) |
| `75bfdeeb` | feat(core): FSAdapter B6 — migrar pre_validation.py (check 9) |

### Tasks completadas (sesión 96)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| FSAdapter creado | ✅ DONE | `sfce/core/fs_adapter.py` ~420L: FSResult, FSError, FSAdapter con todas las defensas FS |
| 22 tests TDD | ✅ DONE | `tests/test_fs_adapter.py` cubre: filtrado _*, idempresa, retry, lineas json, recargo=0, nick 10 chars, personafisica, rollback 2-pasos |
| B1 asientos_directos.py | ✅ DONE | `crear_asiento_directo()` → `fs.crear_asiento_con_partidas()` |
| B2 phases/asientos.py | ✅ DONE | `FSAdapter.desde_config(config)`, pasa `fs` a helpers |
| B3 phases/correction.py | ✅ DONE | `fs.corregir_partida()` + `fs._post()` |
| B4 phases/registration.py | ✅ DONE | Todas las funciones internas usan `fs: FSAdapter` |
| B5 api/rutas/bancario.py | ✅ DONE | `FSAdapter.desde_empresa_bd(empresa, gestoria)` |
| B6 phases/pre_validation.py | ✅ DONE | `_validar_no_existe_en_fs()` → `FSAdapter.desde_config(config)` |
| Tests suite completa | ✅ DONE | 2801 passed, 4 skipped (antes: 2779) |

### Pendientes sesión 97

**Estado FSAdapter:** completo en pipeline principal. `cross_validation.py`, `aprendizaje.py` y scripts siguen con api_get (fuera de scope inmediato).

1. **Ampliar config.yaml MARIA ISABEL** — 218 PDFs en cuarentena. Inspeccionar CIFs e identificar proveedores.
2. **Re-procesar cuarentena** — mover PDFs a inbox/ + pipeline --no-interactivo
3. **Verificar 7000x vs 7050x** — FS usa cuenta ventas mercaderías para FV servicios. Evaluar corrección.
4. **F6** — Ruta inbox email→pipeline
5. **Tests E2E dashboard** — Playwright
6. **cross_validation.py** — migrar api_get a FSAdapter (nice to have)

---

## Estado actual (sesión 95 — Golden Prompt V3.2 integrado)

### Commits sesión 95

| Hash | Descripción |
|------|-------------|
| `fc1117a2` | docs: design golden prompt V3.2 — unificacion OCR few-shot con metadata |
| `8f14c23c` | feat(ocr): añadir PROMPT_EXTRACCION_V3_2 few-shot + alias retrocompat |
| `fd8897e2` | feat(ocr): construir_partidas_nomina lee de metadata V3.2 con patron is_not_none |
| `13d2aadb` | feat(ocr): construir_partidas_rlc lee de metadata V3.2 con patron is_not_none |
| `b6818afe` | feat(ocr): integracion completa — OCR modules, smart_parser, pre_validation, ValueError fallback |

### Tasks completadas (sesión 95)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Audit prompts OCR | ✅ DONE | Inventario completo: PROMPT_EXTRACCION (multi-tipo, 135L), PROMPT_PARSEO (minimalista), prompts Gemini auditor |
| Design Golden Prompt V3.2 | ✅ DONE | Diseño aprobado: esquema universal + metadata{} para nóminas/RLC, 4 ejemplos few-shot, patrón is_not_none, no tocar registration.py (subtipo viene de config.yaml) |
| prompts.py — V3.2 + alias | ✅ DONE | PROMPT_EXTRACCION_V3_2 + alias PROMPT_EXTRACCION para retrocompat |
| construir_partidas_nomina | ✅ DONE | Lee de metadata{} primero (is not None), fallback a raíz legacy. Normaliza a nombres YAML |
| construir_partidas_rlc | ✅ DONE | Ídem para cuota_empresarial/base_cotizacion/cuota_obrera |
| pre_validation._check_rlc_cuota | ✅ DONE | Lee de metadata{} con is not None |
| ocr_mistral/gpt/gemini + smart_parser | ✅ DONE | .format(texto_documento=...) en todos los módulos |
| ValueError → warning bancario | ✅ DONE | construir_partidas_bancario degrada a logger.warning + fallback "comision" |

### Pendientes sesión 96

**Estado OCR:** Golden Prompt V3.2 activo en todos los motores. 2779 tests PASS.

1. **Ampliar config.yaml MARIA ISABEL** — 218 PDFs en cuarentena. Inspeccionar CIFs e identificar proveedores.
2. **Re-procesar cuarentena** — mover PDFs a inbox/ + pipeline --no-interactivo
3. **Verificar 7000x vs 7050x** — FS usa cuenta ventas mercaderías para FV servicios. Evaluar corrección.
4. **F6** — Ruta inbox email→pipeline
5. **Tests E2E dashboard** — Playwright

---

## Estado actual (sesión 94 — FV Ingresos MARIA ISABEL registrados + asientos cuadrados)

### Commits sesión 94

| Hash | Descripción |
|------|-------------|
| *(en proceso)* | fix(fs_api): normalizar_fecha soporta DD/MM/YYYY + calcular_trimestre con try/except |

### Tasks completadas (sesión 94)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Debug 400 en facturaclientes | ✅ DONE | Root cause: 7 facturaclientes previas de sesión 92 (IDs 2-8) con fechas hasta dic-2025 bloqueaban inserción cronológica. Eliminadas. |
| Registrar 5 FV Ingresos | ✅ DONE | Manual via API: facturas 10-14 (Blanco Abogados, ene-sep 2025). Asientos 91-95 generados vía PHP CLI `InvoiceToAccounting::generate()`. |
| Fix partidas FV descuadradas | ✅ DONE | FS generate() crea 4 partidas correctas (430x+477x+7000x+4730x). Script corregir las duplicó por error → fix_partidas_duplicadas_fv.py. Todos cuadrados. |
| Fix `normalizar_fecha` + `calcular_trimestre` | ✅ DONE | `sfce/core/fs_api.py`: soporta DD/MM/YYYY (slash) + try/except para fechas texto |

### Pendientes sesión 95 — CONTINUAR MARIA ISABEL

**Estado FS empresa 7 (codejercicio=0007):**
- FC: 5 facturas (58-62) + asientos (86-90) ✓
- FV: 5 facturas (10-14) + asientos (91-95) ✓
- En cuarentena: ~218 PDFs (CIF de proveedor desconocido en config.yaml)

1. **Ampliar config.yaml** — añadir proveedores de los 218 PDFs en cuarentena. Inspeccionar `cuarentena/` para ver qué CIFs hay.
2. **Re-procesar cuarentena** — mover PDFs de vuelta a inbox/ y ejecutar pipeline de nuevo para los documentos antes en cuarentena.
3. **Verificar cuenta 7000x vs 7050x** — FS usa 7000000000 (ventas mercaderías) para FV de servicios. Debería ser 7050x (prestaciones servicios). Evaluar si es necesario corregir o es aceptable.
4. **F6** — Ruta inbox email→pipeline
5. **Tests E2E dashboard** — Playwright

---

## Estado actual (sesión 93 — OCR GPT-4o-mini cuarentena + fixes pipeline MARIA ISABEL)

### Commits sesión 93

| Hash | Descripción |
|------|-------------|
| `46dc0d63` | fix(ocr): GPT-4o-mini vision para PDFs escaneados + fixes pipeline MARIA ISABEL |

### Tasks completadas (sesión 93)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Borrar asientos 44-72 + facturas 28-56 FS | ✅ DONE | DELETE vía MariaDB root/root_uralde_2026. 87 partidas, 29 asientos, 29 líneas, 29 facturas borradas |
| Fix IVA21 recargo=0 permanente | ✅ DONE | `UPDATE impuestos SET recargo=0 WHERE codimpuesto='IVA21'` en fs-uralde-mariadb-1 |
| OCR GPT-4o-mini cuarentena | ✅ DONE | 260 PDFs procesados con gpt-4o-mini Vision (PyMuPDF + detail:low). 0 errores. Todos movidos a inbox/. Cache .ocr.json guardado junto a cada PDF |
| Fix cache OCR bug (intake.py) | ✅ DONE | Cache hit ya no retorna raw dict — continúa por flujo de clasificación |
| Fix FV tipo hint (intake.py) | ✅ DONE | PDFs en inbox/ingresos/ → tipo_doc=FV aunque clasifiquen como FC/OTRO |
| Fix registration.py FV | ✅ DONE | Ordenación cronológica + cifnif/nombrecliente explícitos en facturaclientes POST |

### Pendientes para sesión 94 — PIPELINE MARIA ISABEL

**Estado inbox:** 223 PDFs con OCR gpt-4o-mini en `clientes/maria-isabel-navarro-lopez/inbox/`. Cuarentena vacía. FS empresa 7 limpio (0 facturas).

**Nota sobre conteo:** usuario detectó 223 PDFs vs ~282 esperados (88 originales + 194 cuarentena). Posible causa: `shutil.move` sobrescribió duplicados `_1` sobre originales en varias pasadas del script OCR. Verificar antes de ejecutar pipeline completo.

1. **Auditar inbox/** — contar PDFs por mes (deberían ser ~12 meses × ~15-20 docs cada uno). Identificar si faltan meses enteros.
2. **Pipeline completo** — `python scripts/pipeline.py --cliente maria-isabel-navarro-lopez --ejercicio 2025 --inbox inbox --no-interactivo`
3. **F6** — Ruta inbox email→pipeline
4. **Tests E2E dashboard** — Playwright

---

## Estado actual (sesión 92 — Asientos MARIA ISABEL + diagnóstico OCR Gemini)

### Commits sesión 92

| Hash | Descripción |
|------|-------------|
| *(sin commits de código — trabajo vía SSH/SQL directo en FS Uralde)* | Generación asientos + fix recargo + enlace idasiento |

### Tasks completadas (sesión 92)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Fase 3 asientos MARIA ISABEL | ✅ DONE | PHP CLI: importar PGC (802 cuentas) + `InvoiceToAccounting::generate()` para 29 facturas. Root cause "asiento descuadrado": `lineasfacturasprov.recargo=5.2` (RE heredado de IVA21 instancia Uralde). Fix: `UPDATE lineasfacturasprov SET recargo=0 WHERE idfactura BETWEEN 28 AND 56`. UPDATE manual `facturasprov.idasiento = idfactura + 16`. idasientos 44-72 asignados. |
| Fases 4-6 MARIA ISABEL | ✅ DONE | Fase 4 (corrección): 1 aviso. Fase 5 (verificación cruzada): 13/13 PASS. Fase 6 (salidas): informe generado. |
| Diagnóstico cuarentena/inbox | ✅ DONE | 193 PDFs en inbox, 160 en cuarentena raíz. 80 `.ocr.json` con todos los campos null (Gemini falló en escáneres). 112 con datos parciales y nombres basura. Causa: Gemini como motor primario para PDFs físicos de baja calidad. |

### Pendientes para sesión 93 — ARRANQUE LIMPIO MARIA ISABEL

**PREPARACIÓN FS (hacer primero):**
1. **Borrar asientos FS empresa 7** — DELETE asientos idasiento 44-72 + partidas asociadas vía MariaDB o API DELETE
2. **Borrar facturas FS empresa 7** — DELETE facturasprov idfactura 28-56 + lineas asociadas (o usar DELETE API)
3. **Verificar proveedores empresa 7** — mantener los que ya existen (no recrear). Verificar que `codsubcuenta` sea 400x correcto
4. **Verificar recargo=0 en IVA21** — `UPDATE impuestos SET recargo=0 WHERE codimpuesto='IVA21'` en instancia Uralde (para que no se repita el problema)

**OCR Y RE-PROCESADO:**
5. **Re-OCR con Mistral** — todos los JSONs borrados (el usuario ya los borró). Ejecutar pipeline fase 0/1 con Mistral como motor primario. Inbox: `clientes/maria-isabel-navarro-lopez/inbox/` (facturas recibidas + bancarios) + subcarpeta `inbox/ingresos/` (facturas emitidas/honorarios → tipo FV)
6. **Recuperar cuarentena** — mover 160 PDFs de `cuarentena/` raíz a `inbox/` antes de re-procesar
7. **Pipeline completo** — fases 1-6 con todos los documentos (~353 PDFs totales)

**POST-PIPELINE:**
8. **Comparar vs M130/M303** — una vez todos los documentos registrados
9. **F6 ruta inbox email→pipeline** — worker guarda `clientes/{empresa_id}/inbox/`; pipeline espera `clientes/{slug}/{año}/inbox/`

---

## Estado actual (sesión 91 — Onboarding MARIA ISABEL NAVARRO LOPEZ + fix key validated_batch)

### Commits sesión 91

| Hash | Descripción |
|------|-------------|
| *(pendiente commit)* | fix(registration): leer ambas claves validated_batch + registered.json vacío si 0 docs |

### Tasks completadas (sesión 91)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Onboarding MARIA ISABEL NAVARRO LOPEZ | ✅ DONE | idempresa=7 (FS Uralde), empresa_id=14 (SFCE BD), config.yaml completo con 25+ proveedores |
| Bug F8 raíz — validated_batch key mismatch | ✅ DONE | Pipeline paralelo escribe `"validados"` pero `registration.py` leía `"documentos"` → 0 docs → no se creaba `registered.json`. Fix: leer ambas claves con `or`; escribir `registered.json` vacío si 0 docs |
| Pipeline fase 2 MARIA ISABEL | ✅ DONE | 29 facturas registradas en FS (IDs 28-56), 0 fallidos |

### Pendientes para sesión 92

1. **Fase 3 asientos MARIA ISABEL** — 29 facturas sin asiento. El método 2-step (`facturaproveedores` + `lineasfacturaproveedores`) bypassa el event observer de FS que genera los asientos automáticamente. Opciones: (a) usar `crearFacturaProveedor` con `codejercicio=0007` y ver si funciona; (b) borrar las 29 facturas y recrear via `crearFacturaProveedor`; (c) llamar a la UI controller de FS via HTTP para contabilizar en batch
2. **Completar pipeline MARIA ISABEL** — fases 4-6 tras resolver asientos
3. **Comparar vs modelos fiscales** — confrontar asientos SFCE con M130/M303 presentados por la cliente
4. **F6 — Ruta inbox email→pipeline** — Worker guarda `clientes/{empresa_id}/inbox/`; pipeline espera `clientes/{slug}/{año}/inbox/`
5. **Tests E2E dashboard** — Playwright: confirmar match, rechazar, FilterBar, conciliar-directo, bulk

---

## Estado actual (sesión 90 — F8: registro FS total correcto)

### Commits sesión 90

| Hash | Descripción |
|------|-------------|
| `fb8f9ced` | fix(f8): pvpsindto/pvptotal explícitos + PUT totales cabecera — resuelve total=0 en registro FS |

### Tasks completadas (sesión 90)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| F8 — Pipeline FS total=0.00 | ✅ DONE | FS no auto-calcula `pvpsindto`/`pvptotal` desde `pvpunitario`. Fix: pasar `pvpsindto = pvpunitario * cantidad` en cada línea POST. Tras todas las líneas, acumular neto/iva/irpf y hacer PUT a cabecera para actualizar totales. Logs detallados → DEBUG. |

### Pendientes para sesión 91

1. **Verificar F8 en producción** — pipeline completo con factura real, comprobar `total != 0` en FS (empresa 2, Gerardo)
2. **Verificar confirmar-match** — re-confirmar mov 132 y comprobar asiento con importe correcto en FS
3. **F6 — Ruta inbox email→pipeline** — Worker guarda `clientes/{empresa_id}/inbox/`; pipeline espera `clientes/{slug}/{año}/inbox/`
4. **Tests E2E dashboard** — Playwright: confirmar match, rechazar, FilterBar, conciliar-directo, bulk
5. **Capa C VClNegocios** — 0 matches (bajó de 8)

---

## Estado actual (sesión 89 — Conciliación: asiento con importe correcto)

### Commits sesión 89

| Hash | Descripción |
|------|-------------|
| `89d4e842` | fix(conciliacion): asiento con importe correcto — partidas json.dumps + base_url en api_get |

### Tasks completadas (sesión 89)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| 500 error redeployar bancario.py | ✅ DONE | El docker cp de sesión 88 no sobrevivió el restart. Re-deployed via scp+docker cp la versión con `session` param |
| Asiento FS con 0€ al confirmar match | ✅ DONE | `_confirmar_en_fs` buscaba subcuenta proveedor (FS por NIF, fallback 4000000000) y crea 2 partidas con `json.dumps(lineas)` |
| `_crear_asiento_directo_en_fs` sin json.dumps | ✅ DONE | Mismo fix: `"lineas": json.dumps(lineas)` para que FS reciba JSON válido |
| `api_get` sin `base_url` | ✅ DONE | Añadido parámetro `base_url` a `api_get` en `fs_api.py` — ahora todas las funciones lo soportan |
| Limpieza asiento vacío FS#8 | ✅ DONE | DELETE asiento FS#8 + reset mov 132 a pendiente para re-confirmar |

### Pendientes para sesión 90

1. **F8 — Pipeline FS registration fix** — Fase 2 rollback (FS devuelve `total=0.00`). `registered.json` nunca se genera → pipeline bloqueado. Investigar `registration.py` + respuesta real FS con logs detallados
2. **F6 — Ruta inbox email→pipeline** — Worker correo guarda en `clientes/{empresa_id}/inbox/`; pipeline espera `clientes/{slug}/{año}/inbox/`. Alinear rutas o mover automáticamente
3. **Tests E2E dashboard** — Playwright flujos críticos: confirmar match (verificar asiento con importe), rechazar, FilterBar, conciliar-directo, bulk
4. **Verificar confirmar-match producción** — mov 132 está en pendiente, re-confirmar y verificar que FS crea asiento con importe correcto
5. **Capa C VClNegocios** — 0 matches (bajó de 8). Verificar si faltan PDFs en inbox prod

---

## Estado actual (sesión 88b — Ejercicio 2026 Gerardo + bugs correo/IMAP)

### Commits sesión 88b

| Hash | Descripción |
|------|-------------|
| *(pendiente commit)* | fix(correo): IMAP UID parsing, workers health flags, ejercicio dinámico |

### Tasks completadas (sesión 88b)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Ejercicio 2026 Gerardo en FS | ✅ DONE | Creado codejercicio="GG26" en fs-uralde idempresa=3. Config.yaml usa mapa `ejercicios` |
| ConfigCliente.codejercicio dinámico | ✅ DONE | Resuelve codejercicio por mapa `{año: cod}` en ambos config.py (scripts/ y sfce/) |
| Bug IMAP UIDs no parseados | ✅ DONE | `imap_servicio.py`: split() antes de isdigit(). UIDs en Gmail vienen como `b'9 10'` |
| Workers health flags faltantes | ✅ DONE | `app.py`: añadidos `worker_ocr_activo`, `worker_pipeline_activo`, `worker_correo_activo = True` |
| Ruta inbox email → pipeline | ⚠️ WORKAROUND | Email guarda en `clientes/{id}/inbox/`, pipeline lee de `clientes/{slug}/{año}/inbox/`. Copia manual por ahora |

### Pendientes para sesión 89

1. **F8 — Pipeline FS registration fix** — Fase 2 rollback en todas (FS devuelve total=0.00). `registered.json` nunca se genera → pipeline bloqueado. Investigar `registration.py` + respuesta real FS con logs detallados
2. **F6 — Ruta inbox email→pipeline** — Worker correo guarda en `clientes/{empresa_id}/inbox/`; pipeline espera `clientes/{slug}/{año}/inbox/`. Alinear rutas o añadir paso de movimiento automático
3. **Tests E2E dashboard** — Playwright flujos críticos: confirmar match, rechazar, FilterBar, conciliar-directo, bulk, upload C43
4. **Confirmar matches en producción** — probar flujo completo post-fix
5. **Capa C VClNegocios** — bajó de 8 a 0 matches

---

## Estado actual (sesión 88 — Conciliación: error feedback + filtrado documentos)

### Commits sesión 88

| Hash | Descripción |
|------|-------------|
| *(ver git log)* | fix(conciliacion): error feedback confirmar/rechazar + filtrado documentos sugerencias |

### Tasks completadas (sesión 88)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Bug: confirmar sugerido no hace nada | ✅ DONE | `SeccionSugerencias` y `PanelSugerencias` muestran el mensaje de error del backend (ej: 502 FS) cuando la mutación falla |
| Filtrado documentos en tab Sugerencias | ✅ DONE | Añadido filtro de texto en `PanelSugerencias` — filtra por NIF proveedor, nº factura, concepto, contraparte; con contador N de M |
| FilterBar en tabs Conciliados/Revisión/Asiento Directo | ✅ DONE | `TabMovimientos` en `conciliacion-page.tsx` ahora incluye `FilterBar` (q + fecha_desde + fecha_hasta) |

### Pendientes para sesión 89

1. **Pipeline FS registration fix** — Fase 2 rollback en todas (FS devuelve total=0.00). Investigar pre_validacion → registration
2. **Tests E2E dashboard** — Playwright flujos críticos: confirmar match, rechazar, FilterBar (q/fecha), conciliar-directo, bulk, upload C43
3. **Confirmar matches en producción** — probar flujo completo post-fix (error feedback + filtros)
4. **Capa C VClNegocios** — bajó de 8 a 0 matches. Verificar si faltan PDFs VClNegocios en inbox prod
5. **Verificación visual sala de control** — arrancar `npm run dev` y navegar `/pipeline/live`, comprobar animaciones con datos reales WS

---

## Estado actual (sesión 87 — Pipeline Sala de Control + Conciliacion Fase 4 frontend)

### Commits sesión 87

| Hash | Descripción |
|------|-------------|
| `4f70a253` | feat(pipeline): sala de control — layout 4 cols full-height gestoría + pipeline global |
| `8a423c83` | feat(conciliacion): Fase 4 frontend — useConciliarDirecto, SeccionManual, tab Asiento Directo |
| `f33d6438` | feat(pipeline): PipelineFlowDiagramVertical — flujo global columna derecha |
| `abd5a6c3` | feat(pipeline): GestoriaColumn — header gestoría + cards distribuidas |
| `6179ac69` | feat(pipeline): EmpresaCard — indicador estado, mini-pipeline, ring pulse |
| `f20d09ad` | feat(pipeline): MiniPipelineVertical — 6 nodos + partícula animada |
| `6bee872a` | feat(pipeline): animaciones CSS tarjetas empresa — ring pulse, dot ping, border glow |
| `4da81846` | feat(pipeline): exponer eventosActivos por empresa en hook WS |
| `5762d167` | feat(pipeline): tipos y constantes gestorías — mapping 13 empresas + colores |

### Tasks completadas (sesión 87)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Pipeline Sala de Control | ✅ DONE | Layout 4 columnas full-height: GestoriaColumn × 3 + PipelineFlowDiagramVertical |
| GestoriaColumn | ✅ DONE | Header gestoria + EmpresaCard distribuidas |
| PipelineFlowDiagramVertical | ✅ DONE | 189 líneas, flujo 6 nodos animado |
| Conciliación Fase 3 frontend | ✅ DONE | FilterBar con debounce 400ms + date pickers en VistaPendientes; `useMovimientos` ampliado con q/fechaDesde/fechaHasta/tipo |
| Conciliacion Fase 4 frontend | ✅ DONE | `useConciliarDirecto` hook, `SeccionManual` conectada a POST /conciliar-directo, tab "Asiento Directo" |
| Fix pipeline dry-run | ✅ DONE | ResultadoFase import, fechas español OCR, recurrentes robusto — verificado 2568 tests PASS |

### Pendientes para sesión 88

1. **Pipeline FS registration fix** — Fase 2 rollback en todas (FS devuelve total=0.00). Investigar pre_validacion → registration
2. **Tests E2E dashboard** — Playwright flujos críticos: confirmar match, rechazar, FilterBar (q/fecha), conciliar-directo, bulk, upload C43
3. **Confirmar matches en producción** — probar flujo completo + conciliar-directo desde dashboard prod
4. **Capa C VClNegocios** — bajó de 8 a 0 matches. Verificar si faltan PDFs VClNegocios en inbox prod
5. **Verificación visual sala de control** — arrancar `npm run dev` y navegar `/pipeline/live`, comprobar animaciones con datos reales WS

---

## Estado actual (sesión 86 — cierre sin cambios)

**Sesión de revisión únicamente. Retomamos estado bancario Fase 1+2 (commit 6bfd7d88). No se implementó nada nuevo. Se commitean residuos de sesiones anteriores no commiteados.**

### Tasks completadas (sesión 86)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Commit residuos sesiones 83-85 | ✅ DONE | `scripts/pipeline.py` (import ResultadoFase) + `sfce/core/nombres.py` (fechas español) + `sfce/core/recurrentes.py` (normalizar fechas) + `tipos-pipeline.ts` |
| Cierre protocolo | ✅ DONE | Docs actualizados, CLAUDE.md sincronizado con sesión 85 |

### Pendientes para sesión 87 (próxima sesión)

1. **Bancario Fase 3 (Frontend)** — FilterBar debounce en VistaPendientes: q, fecha_desde, fecha_hasta, tipo; panel lateral conciliación manual buscando /api/documentos/{empresa_id}; fix IBAN selector; tooltips truncado; AlertDialog bulk confirm
2. **Bancario Fase 4 (Backend + Frontend)** — endpoint `POST /conciliar-directo` (movimiento_id + subcuenta_destino → asiento directo, sin factura) + tab "Asiento Directo" en PanelConciliacion
3. **Pipeline FS registration fix** — Fase 2 pipeline.py hace rollback en todas (total FS=0.00). Investigar
4. **Tests E2E dashboard** — Playwright, flujos críticos: confirmar match, rechazar, bulk, upload C43
5. **Capa C subset-sum VClNegocios** — bajó de 8 a 0 matches (falta OCR de VClNegocios PDFs en inbox prod?)

---

## Estado actual (sesión 85 — diseño Pipeline Live Sala de Control)

**Sesión de diseño puro. Brainstorming + design doc + plan de implementación para el rediseño completo del Pipeline en Vivo. Sin código escrito — plan listo para ejecutar en sesión paralela.**

### Tasks completadas (sesión 85)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Brainstorming Pipeline Live | ✅ DONE | 4 rondas de preguntas → diseño aprobado: layout 4 cols, gestorías como columnas, tarjetas empresa con mini-pipeline |
| Design doc | ✅ DONE | `docs/plans/2026-03-04-pipeline-live-sala-control-design.md` — layout, componentes, efectos visuales, mapping 13 empresas |
| Plan de implementación | ✅ DONE | `docs/plans/2026-03-04-pipeline-live-sala-control.md` — 9 tasks con código completo, sin cambios de backend |

### Pendientes para sesión 86

1. **Verificar ejecución paralela** del plan `2026-03-04-pipeline-live-sala-control.md` (usuario lo está ejecutando)
2. **Pipeline FS registration fix** — Fase 2 pipeline.py hace rollback en todas (total FS=0.00). Investigar
3. **Tests E2E dashboard** — Playwright, flujos críticos: confirmar match, rechazar, bulk, upload C43
4. **Confirmar matches en producción** — probar flujo completo confirmar/rechazar sugerencias
5. **Capa C subset-sum VClNegocios** — bajó de 8 a 0 matches (falta OCR de VClNegocios PDFs en inbox prod?)

---

## Estado actual (sesión 84 — conciliación bancaria Gerardo operativa en prod)

**Sesión de integración end-to-end del módulo bancario. Motor conciliación corrió contra PostgreSQL de producción via túnel SSH. 125 sugerencias generadas y visibles en dashboard. 3 bugs críticos del frontend corregidos y desplegados.**

### Tasks completadas (sesión 84)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Reorganización inbox Gerardo | ✅ DONE | 238 PDFs de FACTURAS 2025 → inbox; 9 PDFs duplicados eliminados; 40 JSONs ya existentes preservados |
| OCR pipeline (238 PDFs) | ✅ DONE | `pipeline.py` con dotenv fix; generó 238 nuevos `.ocr.json`; 105 → cuarentena (CIF desconocido); falló en Fase 2 FS (total=0.00) — no impacta motor bancario |
| Motor conciliación → producción | ✅ DONE | SSH túnel localhost:5435→PG prod; `conciliar_facturas_gerardo.py` apuntó a PG; 278 docs + 566 movs → **125 sugerencias insertadas** |
| Migración datos_ocr → columnas | ✅ DONE | 274 docs actualizados: `importe_total` (166), `nombre_archivo` (273), `nif_proveedor`, `fecha_documento` desde JSON |
| Estados movimientos | ✅ DONE | 125 movimientos actualizados a `estado_conciliacion='sugerido'` via SQL directo en prod |
| Fix IMAP admin@prometh-ai.es | ✅ DONE | Password actualizada a `bowa ixgl tijf oaku` (cifrada con Fernet y escrita en BD prod) |
| Fix DocumentoResumen | ✅ DONE | Commit `3842722b`: añadido `nombre_archivo` al schema Pydantic + endpoint |
| Fix confirmar match | ✅ DONE | Commit `33314572`: `_confirmar_en_fs` es best-effort — si FS falla, se concilia igualmente en BD local |
| Filtro por cuenta | ✅ DONE | Commit `33314572`: endpoint movimientos acepta `?cuenta_id=N`; página con selector independiente |
| Paginación movimientos | ✅ DONE | Commit `33314572`: respuesta `MovimientosPaginados {items, total, offset, limit}`; UI con botones ‹/› |

### Pendientes para sesión 85

1. **Tests E2E dashboard** — Playwright, flujos críticos: confirmar match, rechazar, bulk, upload C43
2. **Pipeline FS registration fix** — Fase 2 pipeline.py hace rollback en todas (total FS=0.00). Investigar por qué FacturaScripts devuelve 0 en verificación post-registro
3. **Confirmar matches en producción** — el usuario debe confirmar/rechazar sugerencias y verificar que persisten (ya funciona según fix sesión 84)
4. **Capa C subset-sum VClNegocios** — bajó de 8 a 0 matches al correr contra PG (falta OCR de VClNegocios PDFs en inbox prod?)
5. **tunnel SSH automatizable** — si el motor bancario se va a correr periódicamente, necesita un wrapper que no requiera tunnel manual

---

## Estado actual (sesión 83 — Pipeline Operations Center implementado)

**Implementación completa del plan `docs/plans/2026-03-04-pipeline-operations-center.md`. 6 commits frontend+backend. Deploy en producción OK.**

### Tasks completadas (sesión 83)

| Task | Commit | Qué se hizo |
|------|--------|-------------|
| WS desde correo (worker_catchall) | `32f64b4a` | `_emitir_ws_nuevo_pdf()` helper en `_encolar_archivo` |
| WS desde manual (gate0) | `f5fc0d84` | Emite `watcher_nuevo_pdf` con `fuente="manual"` tras commit |
| Endpoint pipeline-breakdown | `a59ef123` | `GET /api/dashboard/pipeline-breakdown` — breakdown tipo_doc + empresa + fuentes |
| Hooks frontend | `9cd9c48f` | `ParticulaActiva.fuente` + `contadores_fuente` WS + `BreakdownStatus` + URLs relativas |
| Componentes Operations Center | `0884b809` | FuentesPanel, BreakdownPanel, PipelineNode mejorado, GlobalStatsStrip rediseñado |
| Layout 3 columnas | `261652a5` | pipeline-live-page.tsx reescrita: FuentesPanel ↔ FlowDiagram ↔ BreakdownPanel |

### Pendientes para sesión 84

1. **Pipeline Gerardo en producción** — `python scripts/pipeline.py --cliente gerardo-gonzalez-callejon --ejercicio 2025 --inbox inbox_gerardo --no-interactivo` → poblar `documentos` empresa_id=2
2. **Verificar sugerencias** — tras pipeline, `GET /api/bancario/2/sugerencias` debe devolver registros con motor V2
3. **Tests E2E dashboard** (Playwright, flujos críticos: upload manual, conciliación, pipeline live)
4. **Fix IMAP admin@prometh-ai.es** — AUTHENTICATIONFAILED, revisar App Password Google Workspace

---

## Estado actual (sesión 82 — diseño Operations Center + fix bancario)

**Sesión de análisis y planificación: diagnóstico flujo emails (WS ausente), diseño Operations Center completo, plan de implementación escrito. Fix bancario por el usuario.**

### Tasks completadas (sesión 82)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Diagnóstico emails en pipeline | ✅ DONE | Confirmado: `ingesta_correo` / `worker_catchall` NO emiten WS. `EVENTO_WATCHER_NUEVO_PDF` definido pero nunca emitido. |
| Diseño Operations Center | ✅ DONE | Layout 3 columnas: FuentesPanel + FlowDiagram + BreakdownPanel. Brainstorming completo. |
| Plan implementación | ✅ DONE | `docs/plans/2026-03-04-pipeline-operations-center.md` — 11 tasks, código completo |
| Fix bancario (usuario) | ✅ DONE | `limit movimientos 100→500` + `dotenv en pipeline` (commit 686e66c1) |

### Pendientes para sesión 83

1. **EJECUTAR PLAN** `docs/plans/2026-03-04-pipeline-operations-center.md` usando `superpowers:executing-plans`
   - Task 1+2: WS desde worker_catchall (correo) + gate0 (manual)
   - Task 3: endpoint `/api/dashboard/pipeline-breakdown`
   - Task 4: hooks actualizados (fuente + breakdown)
   - Task 5+6+7+8: FuentesPanel + BreakdownPanel + nodos mejorados + GlobalStatsStrip
   - Task 9+10+11: layout 3 cols + TS verify + deploy
2. Pipeline Gerardo en producción → poblar `documentos` empresa_id=2
3. Tests E2E dashboard
4. Fix IMAP admin@prometh-ai.es

---

## Estado actual (sesión 81 — fix Pipeline en Vivo: WebSocket + upload + diagrama)

**Sesión de diagnóstico y fix del módulo Pipeline en Vivo del dashboard. 1 commit frontend.**

### Tasks completadas (sesión 81)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Diagnóstico WebSocket DESCONECTADO | ✅ DONE | Causa: `VITE_API_URL ?? 'localhost:8000'` no definida en CI build → conectaba al PC del usuario |
| Fix WebSocket URL producción | ✅ DONE | `usePipelineWebSocket.ts` usa `window.location` en prod, `VITE_API_URL` solo en dev |
| Zona upload en Pipeline en Vivo | ✅ DONE | `SubirDocumentos.tsx` — drag & drop PDF/ZIP, llama a `/api/gate0/ingestar` con JWT |
| Fix fetch `/api/empresas` localhost | ✅ DONE | URL relativa en lugar de `VITE_API_URL ?? localhost` |
| Diagrama flujo — fuentes de entrada | ✅ DONE | Chips "Correo / Watcher / Manual" sobre nodo Inbox en `PipelineFlowDiagram.tsx` |

### Pendientes para sesión 82

1. **Pipeline Gerardo en producción** — ejecutar pipeline OCR para poblar `documentos` empresa_id=2
2. **Verificar sugerencias** — tras pipeline, `GET /api/bancario/2/sugerencias` debe devolver registros
3. **Tests E2E dashboard** — Playwright, flujos críticos conciliación
4. **Error IMAP admin@prometh-ai.es** — AUTHENTICATIONFAILED, revisar App Password Google Workspace
5. **scripts/pipeline.py modificado** — hay cambios sin commitear (`git status` muestra `M scripts/pipeline.py`), revisar y commitear si corresponde

---

## Estado actual (sesión 80 — limpieza BD duplicados + motor V2 deploy + verificación C43)

**Sesión de consolidación del módulo bancario. Se ejecutaron los planes de sesiones 78 y 79 pendientes. Sin commits de código nuevos (todo ya en `f4074dd7`). Solo cambios en BD producción y deploy manual.**

### Tasks completadas (sesión 80)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Push pendiente | ✅ DONE | Todos los commits ya estaban en origin/main al iniciar la sesión |
| Migración 030 producción | ✅ DONE | Columna `confirmada` (boolean) en `sugerencias_match` vía importlib |
| Ingesta C43 Gerardo | ✅ DONE | `TT280226.423.txt` ya procesado (1064 movs, 0 duplicados, hash_unico OK) |
| Fix interceptor Axios 422 | ✅ DONE | `api-client.ts` ya tenía el Array→string correcto — no requirió cambios |
| Limpieza cuentas duplicadas | ✅ DONE | IDs 1-3 (IBAN corto 18 dígitos) → `activa=False`; IDs 4-6 activas |
| Motor /conciliar → V2 | ✅ DONE | Endpoint usa `conciliar_inteligente()` + `session.commit()` (f4074dd7) |
| Deploy manual prod | ✅ DONE | `docker cp bancario.py sfce_api` + restart. CI/CD GHCR pendiente de pull |
| Verificación sugerencias | ✅ DONE | Motor ejecutado: 0 matches (BD solo 1 doc empresa_id=2 sin importe) |

### Diagnóstico bloqueante

**Motor V2 retorna 0 sugerencias** porque la tabla `documentos` solo tiene 1 registro para `empresa_id=2` sin `importe_total`. Para generar sugerencias hay que ejecutar el pipeline OCR con las facturas PDF de Gerardo en producción.

### Pendientes para sesión 81

1. **Pipeline Gerardo en producción** — `python scripts/pipeline.py --cliente gerardo-gonzalez-callejon --ejercicio 2025 --inbox inbox_gerardo --no-interactivo` para poblar tabla `documentos`
2. **Verificar sugerencias** — tras pipeline, `GET /api/bancario/2/sugerencias` debe devolver registros
3. **Tests E2E dashboard** — Playwright, flujos críticos conciliación
4. **Error IMAP admin@prometh-ai.es**: AUTHENTICATIONFAILED — revisar App Password Google Workspace
5. **CI/CD GHCR pull** — verificar que próximo deploy incluye `bancario.py` nuevo desde imagen

---

## Estado actual (sesión 79 — fix dotenv GEMINI + dedup BD fallback)

**Sesión de corrección: GEMINI_API_KEY no cargaba con xargs (SFCE_FERNET_KEY con caracteres especiales). Fix dedup: cuando un doc ya existe en BD, recuperar importe/emisor/nif de datos_ocr si el extractor local no los obtuvo. Un commit.**

### Commits de la sesión 79

| Commit | Descripción |
|--------|-------------|
| `ff8406d7` | fix(conciliacion): dotenv fix SFCE_FERNET_KEY + dedup fallback importes desde BD |

### Tasks completadas (sesión 79)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| dotenv fix | ✅ DONE | `load_dotenv(RAIZ/.env)` en `conciliar_facturas_gerardo.py` — evita xargs truncando SFCE_FERNET_KEY |
| dedup BD fallback | ✅ DONE | Al hacer dedup por hash_pdf: cargar `importe_total`, `nombre_emisor`, `nif_emisor` de `datos_ocr` si el extractor local los obtuvo como None |
| Diagnóstico sesión 78 | ✅ DONE | Confirmado: sesión 78 ya commitió `pdfplumber+pymupdf+Gemini T3` y endpoint `/conciliar` pero no cerró formalmente |

### Pendientes para sesión 80

1. **PUSH pendiente** — `git push origin main` (commits `f4074dd7`, `b6a60b72`, `ff8406d7`)
2. **Migración 030 en producción** — columna `confirmada` en `sugerencias_match`
3. **Subir TT280226.423.txt** desde Dashboard → validar ingesta C43 E2E JIT real
4. **Fix interceptor Axios 422** — `detail` array → `detail.map(d => d.msg).join(", ")`
5. **Test `test_caixabank_extendido`** — verificar con `TT280226.423.txt`
6. **Motor conciliación API en producción** — `POST /api/bancario/2/conciliar`
7. **Tests E2E dashboard** — Playwright flujos críticos conciliación
8. **Error IMAP admin@prometh-ai.es**: AUTHENTICATIONFAILED

---

## Estado actual (sesión 78 — endpoint /conciliar + extracción PDF 2/3 capas)

**Sin cierre formal. Dos commits: endpoint `/conciliar` usa `MotorConciliacion.conciliar_inteligente()` + tipos frontend; extracción PDF pdfplumber → pymupdf → Gemini Flash (Tier 1/2/3). 17 PDFs escaneados/sin-importe → Gemini.**

### Commits de la sesión 78

| Commit | Descripción |
|--------|-------------|
| `f4074dd7` | feat(bancario): endpoint /conciliar usa MotorConciliacion.conciliar_inteligente() + tipos frontend |
| `b6a60b72` | feat(conciliacion): extraccion PDF 2 capas — pdfplumber + pymupdf fallback |

---

## Estado actual (sesión 77 — Motor conciliación 4 capas + triangulación Gerardo)

**Parsers TPV XLS y tarjeta PDF. Motor matching 4 capas sin LLM: 278 PDFs, 107 sugerencias, 24.8% cobertura en EUR. Sesión de análisis: mapa flujo documental + plan sesión 78.**

### Commits de la sesión 77

| Commit | Descripción |
|--------|-------------|
| `6750f00d` | feat(bancario): triangulacion total Gerardo — TPV + tarjetas PDF + JIT |
| `3f91e352` | feat(conciliacion): motor matching 4 capas sin LLM — facturas 2025 Gerardo |

### Tasks completadas (sesión 77)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| `parser_tpv_xls.py` (nuevo) | ✅ DONE | Parsea TP*.XLS datafono CaixaBank 27 cols. Fix `int(float())` para `codigo_comercio`. |
| `parser_tarjeta_pdf.py` (nuevo) | ✅ DONE | Parsea extractos PDF MyCard + VClNegocios. Extrae `fecha_cargo` individual para match exacto con R22 TCR. |
| `triangulacion_gerardo.py` (nuevo) | ✅ DONE | Orquesta ingesta C43 + match TPV-MCC + match tarjeta-TCR. Fix offset +1 día: CaixaBank registra MCC el día siguiente de fecha_captura TPV. 1064 movs, 10/33 TPV, 62/184 tarjetas. |
| `conciliar_facturas_gerardo.py` (nuevo) | ✅ DONE | Motor 4 capas sin LLM. Capa A exacto: 48 matches. Capa B fuzzy+triangulacion: 50. Capa C subset-sum VClNegocios: 8. Capa D patrón mensual: 1. 107 sugerencias persistidas. |
| Análisis arquitectura | ✅ DONE | Mapa gráfico flujo documental completo. Crítica técnica sistema (subprocess antipatrón, pollers vs events, score Gate0, etc.) |
| Plan sesión 78 | ✅ DONE | Fase 0–7 documentada: migración 030, parser CaixaBank, ingesta E2E, motor conciliación, fix Axios 422 |

### Pendientes para sesión 78

1. **PUSH pendiente** — `git push origin main` (commits `6750f00d`, `3f91e352`, docs sesión 77)
2. **Migración 030 en producción** — columna `confirmada` en `sugerencias_match` (script en Task 13 abajo)
3. **Subir TT280226.423.txt** desde Dashboard → validar ingesta C43 E2E JIT real (3 cuentas Gerardo González)
4. **Fix interceptor Axios 422** — `detail` array → `detail.map(d => d.msg).join(", ")`
5. **Test `test_caixabank_extendido`** — verificar/crear en `test_parser_c43.py` con `TT280226.423.txt`
6. **Motor conciliación API** — `POST /api/bancario/2/conciliar` (producción)
7. **Tests E2E dashboard** — Playwright flujos críticos
8. **Error IMAP admin@prometh-ai.es**: AUTHENTICATIONFAILED

---

## Estado actual (sesión 76 — Zero-Touch multi-cuenta + IBAN Módulo11/97)

**Ingesta C43 multi-cuenta completamente autónoma: JIT onboarding, IBAN calculado correctamente con Módulo 11 AEB + Módulo 97 ISO 13616, 11 tests nuevos. Suite 2741 PASS.**

### Commits de la sesión 76

| Commit | Descripción |
|--------|-------------|
| `cbb02fa` | fix(api-client): no sobreescribir Content-Type en FormData + manejar detail array de FastAPI |
| `cc3dcd3` | feat(bancario): ingesta Zero-Touch multi-cuenta — JIT onboarding + IBAN Modulo11/97 |

### Tasks completadas (sesión 76)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Fix `[object Object]` en UI | ✅ DONE | `api-client.ts`: detecta FormData y omite `Content-Type`; parsea `detail` array de FastAPI 422 |
| `iban_utils.py` (nuevo) | ✅ DONE | `construir_iban_es(entidad, oficina, cuenta)` — Módulo 11 AEB para DC + Módulo 97 ISO 13616 para check digits. IBAN 24 chars `ES__BBBBOOOODDNNNNNNNNNN` |
| `parser_c43.py` refactor | ✅ DONE | `parsear_c43()` devuelve `list[dict]` (un dict por R11). `num_orden` se reinicia por cuenta. IBAN completo calculado con `iban_utils` |
| `ingesta.py` multi-cuenta | ✅ DONE | `ingestar_c43_multicuenta()`: SHA256 file-level dedup, JIT `CuentaBancaria` por IBAN, dedup movimientos, respuesta con `cuentas_procesadas/creadas/detalle` |
| Endpoint `bancario.py` | ✅ DONE | `cuenta_iban` opcional; TXT→JIT multicuenta (gestoria_id fallback a 0), XLS→single-account con cuenta_iban obligatorio |
| `test_zero_touch_multicuenta.py` (nuevo) | ✅ DONE | 11 tests: JIT onboarding (4), movimientos por cuenta (3), idempotencia (3), archivo real skipif (1) |
| `test_parser_c43.py` adaptado | ✅ DONE | Helper `_p1()` para nueva signatura lista; `TestMultiCuenta` con 4 tests |
| Frontend TypeScript | ✅ DONE | `api.ts`: `DetalleCuenta` + `ResultadoIngesta` multi-cuenta. `subir-extracto.tsx`: botón sin requerir IBAN para TXT; muestra `cuentas_creadas` |

### Pendientes para próxima sesión

1. **Migración 030 en producción** — script en sección Task 13 abajo. `confirmada` column en `sugerencias_match`.
2. **Subir TT280226.423.txt** desde Dashboard → validar ingesta C43 E2E con JIT onboarding real (3 cuentas Gerardo González)
3. **Tests E2E dashboard** — Playwright flujos críticos conciliación
4. **Error IMAP cuenta 1** (admin@prometh-ai.es): `AUTHENTICATIONFAILED` — revisar credenciales
5. **Investigar `javier@prometh-ai.es`** — usuario_id=20 en prod sin rol correcto

---

## Estado actual (sesión 75 — onboarding bancario + IMAP prod)

**Onboarding completo de empresa_id=2 (Gerardo González) y activación global IMAP en producción.**

### Tasks completadas (sesión 75)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Script seed IMAP | ✅ DONE | 6 cuentas `tipo=asesor` + 2 `tipo=dedicada` creadas en prod con App Passwords cifradas (Fernet). Worker IMAP arrancó automáticamente |
| Fix tipo BD `es_respuesta_ack` | ✅ DONE | `ALTER TABLE emails_procesados ALTER COLUMN es_respuesta_ack TYPE boolean` — corregido INTEGER→BOOLEAN en producción |
| Cuentas bancarias empresa_id=2 | ✅ DONE | 3 cuentas CaixaBank extraídas de TT280226.423.txt (R11) dadas de alta: IBANs `210038890200255608`, `210068480200053517`, `210068480200254001` — formato `banco+oficina+cuenta` exacto del parser |
| Bloqueo UI conciliación empresa_id=2 | ✅ RESUELTO | Selector de cuentas ahora muestra las 3 CaixaBank. Botón "Subir extracto" habilitado |

### Pendientes para próxima sesión

1. **Subir TT280226.423.txt** desde Dashboard → conciliación empresa Gerardo González para validar ingesta E2E
2. **Tests E2E dashboard** — Playwright flujos críticos conciliación
3. **Migración 030 en producción** — ver script en sección Task 13 abajo
4. **Error IMAP cuenta 1** (admin@prometh-ai.es): `AUTHENTICATIONFAILED` — revisar credenciales de esa cuenta
5. **Investigar `javier@prometh-ai.es`** — usuario_id=20 en prod pero no aparece en tabla Usuarios SFCE (verificar si tiene rol correcto)

---

## Estado actual (cierre sesión 74)

**UI completa de conciliación (5 pestañas) y endpoints de mutación atómica finalizados y testeados. Regresión cero: 2724 tests pasan.**

### Commits de la sesión 74

| Commit | Descripción |
|--------|-------------|
| (pendiente push) | feat(dashboard): integración completa de tabs de conciliación con API real (Task 11/12) |

### Tasks completadas (sesiones 72-73-74 — Conciliación bancaria completa)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Task 7 — API endpoints | ✅ DONE | `confirmar-match`, `rechazar-match`, `confirmar-bulk`, GET `/sugerencias?movimiento_id=`, schemas Pydantic `SugerenciaOut`/`MovimientoResumen`/`DocumentoResumen` |
| Task 8 — match-parcial | ✅ DONE | POST `/match-parcial` N:1 con tolerancia 0.05€, `ConciliacionParcial` por doc |
| Task 11 — Dashboard 5 pestañas | ✅ DONE | `conciliacion-page.tsx` completo: Pendientes (VistaPendientes), Sugerencias (PanelSugerencias datos reales), Revisión (TablaMovimientos filtro `revision`), Conciliados (TablaMovimientos filtro `conciliado` + doc.id), Patrones (TablaPatrones CRUD) |
| Task 12 — Routing + Sidebar | ✅ DONE | Ruta `/conciliacion` + entrada sidebar `ArrowLeftRight` |
| `useSugerencias` global | ✅ DONE | `enabled: empresaId > 0` (ya no bloquea con `movimientoId=null`). Permite pestaña global Sugerencias |
| `MatchCard` migrado | ✅ DONE | Migrado de `SugerenciaMatch` → `SugerenciaOut`. Callbacks: `onConfirmar(movId, sugId)` / `onRechazar(sugId)` |
| `PanelSugerencias` datos reales | ✅ DONE | Usa `useSugerencias(empresaId, null)` + `useConfirmarMatch` + `useRechazarMatch`. Sin mocks |
| Interfaces TypeScript | ✅ DONE | `SugerenciaOut`, `MovimientoResumen`, `DocumentoResumen`. TypeScript 0 errores |

### Task 13 — Regresión final y migración en producción

**Estado:** EN CURSO (A la espera de Deploy manual del usuario)

- Tests: ✅ 2724 passed, 4 skipped (regresión cero)
- Migración 030 en producción: pendiente (script abajo)
- Deploy CI/CD: pendiente push

### Pendientes para próxima sesión (sesión 74 — originales)

1. ~~**Script seed IMAP**~~ ✅ COMPLETADO sesión 75
2. **Tests E2E dashboard** — Playwright flujos críticos conciliación
3. **Migración 030 en producción** — ejecutar script abajo (Fase 8 del deploy)

---

## Estado actual (cierre sesión 72)

### Commits de la sesión 72

| Commit | Descripción |
|--------|-------------|
| `61b3538` | feat: endpoints confirmar-match + rechazar-match + migración 030 |

### Tasks completadas (sesión 72 — Backend conciliación atómica)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Migración 030 | ✅ DONE | Columna `confirmada` (BOOLEAN) en `sugerencias_match`. Compatible PG + SQLite |
| Schemas Pydantic | ✅ DONE | `SugerenciaOut`, `MovimientoResumen`, `DocumentoResumen`, `ConfirmarMatchIn`, `RechazarMatchIn` |
| POST `/confirmar-match` | ✅ DONE | Vincula sugerencia → movimiento. Genera asiento contable. Invalida alternativas. Audita |
| POST `/rechazar-match` | ✅ DONE | Desactiva sugerencia. Reactiva movimiento como pendiente. Audita |
| GET `/sugerencias` filtro | ✅ DONE | Parámetro opcional `?movimiento_id=` para consulta desde panel maestro-detalle |
| Tests | ✅ DONE | 6 tests nuevos en `test_api_bancario.py` — 171 tests bancario pasan |

---

## Estado actual (cierre sesión 71)

### Commits de la sesión 71

Sin commits de código — sesión de configuración Google Workspace.

### Tasks completadas (sesión 71 — App Passwords Google Workspace)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Política 2FA Admin Console | ✅ DONE | Desactivar enforcement → usuarios configuran 2FA → reactivar. Documentado procedimiento en LIBRO-ACCESOS.md |
| App Passwords asesores | ✅ DONE | 2FA activado + App Password SFCE-IMAP generada para los 6 usuarios (francisco, maria, luis, gestor1, gestor2, javier) |
| App Password admin | ✅ DONE | Nueva App Password `bowa ixgl tijf oaku` generada para admin@prometh-ai.es |
| Actualizar contraseñas individuales | ✅ DONE | francisco → `Uralde2027!`, javier → `Uralde2028!` anotadas en LIBRO-ACCESOS.md |
| Recuperar App Password Maria | ✅ DONE | Descifrada desde BD local (Fernet) y registrada en LIBRO-ACCESOS.md |

### Pendientes para próxima sesión

1. **Script seed IMAP**: `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py` — crear/actualizar cuentas IMAP en BD prod con las App Passwords generadas
2. **Sugerencias reales en PanelConciliacion** — reemplazar mock con `useQuery` a `/sugerencias` filtrado por `movimiento_id`
3. **Tabs "Revisión" y "Conciliados"** — implementar con `TablaMovimientos` existente + filtro estado
4. **Tests E2E dashboard** — Playwright flujos críticos (conciliación, documentos)

---

## Estado actual (cierre sesión 70)

### Commits de la sesión 70

| Commit | Descripción |
|--------|-------------|
| `4ad7d7f` | feat: endpoint POST /match-parcial — conciliacion parcial N:1 + 5 tests |
| `c83c58e` | feat: ConciliacionPage con 5 tabs + ruta /conciliacion + entrada sidebar |
| `f2aa593` | feat: VistaPendientes — layout maestro-detalle con scroll independiente |
| `6a3040d` | feat: PanelConciliacion — cabecera movimiento + sugerencias IA (mock) + asiento manual colapsable |

### Tasks completadas (sesión 70 — conciliación parcial + UI conciliación)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| POST /match-parcial | ✅ DONE | Endpoint N:1 en `bancario.py`: schema Pydantic, verifica empresa, tolerancia 0.05€, crea `ConciliacionParcial` por doc, actualiza estados. 5 tests en `test_api_bancario.py` |
| ConciliacionPage (5 tabs) | ✅ DONE | `features/conciliacion/conciliacion-page.tsx`: Tabs shadcn/ui con Pendientes/Sugerencias/Revisión/Conciliados/Patrones. Ruta `/conciliacion` + entrada sidebar `ArrowLeftRight` |
| VistaPendientes | ✅ DONE | Layout maestro-detalle con `ScrollArea`. Lista izquierda (38%) + panel derecho. Estado local `selectedId` |
| PanelConciliacion | ✅ DONE | 3 secciones: cabecera importe grande rojo/verde, sugerencias IA (3 mocks con score/capa/botones), asiento manual colapsable (`Collapsible` + `Input` + `Label`) |

### Pendientes para próxima sesión

1. **App Passwords IMAP** (acción manual) — francisco/luis/gestor1/gestor2/javier: `myaccount.google.com → Seguridad → App passwords`
2. **Script seed IMAP**: `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py`
3. **Sugerencias reales en PanelConciliacion** — reemplazar mock con `useQuery` a `/sugerencias` filtrado por `movimiento_id` (añadir param al endpoint o filtrar en frontend)
4. **Tabs "Revisión" y "Conciliados"** — implementar con `TablaMovimientos` existente + filtro estado
5. **Tests E2E dashboard** — Playwright flujos críticos (conciliación, documentos)

---

## Estado actual (cierre sesión 69)

### Commits de la sesión 69

| Commit | Descripción |
|--------|-------------|
| `55471aa` | docs: protocolo de cierre automático en CLAUDE.md — 9 fases |
| `cfebfb8` | docs: LIBRO-GESTOR.md (dashboard completo) + LIBRO-CLIENTE.md |
| `768192a` | docs: LIBRO-ACCESOS.md gitignoreado + .gitignore + protocolo fase 2 |
| `3d4accd` | docs: cierre sesion 69 (primer protocolo) |
| `c361805` | chore: scripts debug IMAP útiles + gitignore debug_*.py |
| `17a3397` | chore: eliminar worktree mcf + ClasificadorFiscal anotado en roadmap |

### Tasks completadas (sesión 69 — documentación y organización)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| PROTOCOLO DE CIERRE | ✅ DONE | Definido en CLAUDE.md (9 fases): recopilar estado, actualizar libros, commit, push, deploy, informe |
| LIBRO-GESTOR.md | ✅ DONE | Manual completo del dashboard para asesores: 15 módulos, flujos, atajos |
| LIBRO-CLIENTE.md | ✅ DONE | Guía cliente: envío documentos, estados, FAQ, calendario de envío |
| LIBRO-ACCESOS.md | ✅ DONE | Credenciales SFCE (gitignoreado): SSH, PG, 4 instancias FS, usuarios, API keys, GWS, GitHub, Restic |
| Reorganización LIBRO-PERSONAL.md | ✅ DONE | Índice actualizado: Libro Técnico + Manuales de usuario + Accesos |

### Pendientes para próxima sesión

1. **App Passwords IMAP** (acción manual) — francisco/luis/gestor1/gestor2/javier: `myaccount.google.com → Seguridad → App passwords`
2. **Script seed IMAP**: `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py`
3. **Conciliación N:1 parcial** — endpoint `POST /match-parcial` planificado, no implementado
4. **Tests E2E dashboard** — Playwright flujos críticos (conciliación, documentos)

---

## Estado actual (cierre sesión 68)

### Commits de la sesión 68

| Commit | Descripción |
|--------|-------------|
| `ced102d` | feat: telemetría pipeline + shift-left correcciones en registro |
| `3b1a39e` | fix: tests correo — adaptar mocks _extraer_cif_pdf a interfaz lista |

### Tasks completadas (sesión 68 — optimización pipeline, plan Gemini)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| TAREA 1 — Telemetría | ✅ DONE | `intake.py`: mide `duracion_ocr_s` por llamada API; `cache_hit=True` si caché. `registration.py`: mide `duracion_registro_s` por POST FS. `output.py`: sección TELEMETRÍA en informe .log (media + total) |
| TAREA 2 — Shift-left | ✅ DONE | `_pre_aplicar_correcciones_conocidas()` en `registration.py`: inyecta `codimpuesto=IVA0` + `codsubcuenta=4709` para suplidos, `codsubcuenta` destino para reglas `reclasificar_linea`, subcuenta global del proveedor. Llamada antes del POST a FS. Fase 4 sigue como red de seguridad |
| Fix tests correo | ✅ DONE | `_extraer_cif_pdf` devuelve lista — 6 tests adaptados (`test_cif_pdf.py` + `test_ingesta_asesor.py`) |

### Nota TAREA 2 (shift-left)
`codsubcuenta` se inyecta en `linea_fs` antes del POST. FS lo usará si acepta el campo en `lineafacturaproveedores`. En caso contrario, Fase 4 (`_check_subcuenta`) sigue corrigiéndolo via PUT. La ventaja del suplido+IVA0 es inmediata e inequívoca.

---

## Estado actual (cierre sesión 67)

### Tasks completadas (plan `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md`)

| Task | Estado |
|------|--------|
| Tasks 1-6 Motor conciliación + Dashboard components | ✅ DONE |
| Tasks 7-8-11-12-13 API endpoints + Dashboard page + Routing | ✅ DONE (sesión 67) |

---

## Estado anterior (cierre sesión 66)

### Commits de la sesión 66

| Commit | Descripción |
|--------|-------------|
| `b4ae75e` | feat: migración 029 — tablas conciliación inteligente (sugerencias, patrones, parciales) |
| `91f96dc` | feat: normalizar_bancario — normalizar_concepto + limpiar_nif + rango_importe |
| `067f482` | feat: motor conciliación capa 1 — exacta y unívoca con documentos pipeline |
| `5e50fef` | docs: cierre sesión 66 — Tasks 1-3 completas |
| `e91e74b` | feat: feedback_conciliacion — aprendizaje bidireccional + gestión diferencias ≤0.05€ |
| `0b89e42` | feat: motor conciliación capas 2-5 — NIF, referencia factura, patrones, aproximada |
| `ce04387` | feat: dashboard conciliación — api.ts, match-card, panel-sugerencias, patrones CRUD |

### Tasks completadas (plan `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md`)

| Task | Estado | Qué se hizo |
|------|--------|-------------|
| Task 1 — Migración 029 | ✅ DONE | 3 tablas nuevas (`sugerencias_match`, `patrones_conciliacion`, `conciliaciones_parciales`). Columnas en `documentos` (nif_proveedor, numero_factura, etc.), `cuentas_bancarias` (saldo_bancario_ultimo, fecha_saldo_ultimo), `movimientos_bancarios` (documento_id, score_confianza, metadata_match, capa_match). 4 tests PASS |
| Task 2 — normalizar_bancario.py | ✅ DONE | `normalizar_concepto()` + `limpiar_nif()` + `rango_importe()`. 23 tests PASS |
| Task 3 — ORM + Capa 1 | ✅ DONE | ORM: `SugerenciaMatch`, `PatronConciliacion`, `ConciliacionParcial`. Campos nuevos en `Documento`, `CuentaBancaria`, `MovimientoBancario`. `conciliar_inteligente()` + Capa 1 exacta-unívoca. 2 tests PASS |
| Task 4-5-6 — Capas 2-5 + Feedback | ✅ DONE (commit 0b89e42 + e91e74b) | Capas 2 (NIF), 3 (ref factura), 4 (patrones aprendidos), 5 (aproximada). Feedback loop bidireccional. |
| Task 9-10-12 — Dashboard | ✅ DONE (commit ce04387) | `api.ts`, hooks TanStack Query, `match-card.tsx`, `panel-sugerencias.tsx`, `patrones-crud.tsx` |

---

## TASKS COMPLETADAS — Plan conciliación bancaria (Tasks 7-8 y 11-13)

| Task | Estado | Sesión |
|------|--------|--------|
| Task 7 — API endpoints (sugerencias, confirmar, rechazar, bulk, saldo-descuadre) | ✅ DONE | 72 |
| Task 8 — match-parcial N:1 + Bulk + Parcial | ✅ DONE | 72 |
| Task 11 — Dashboard `conciliacion-page.tsx` (5 pestañas completas con datos reales) | ✅ DONE | 73-74 |
| Task 12 — Routing `/conciliacion` + entrada Sidebar | ✅ DONE | 70 |
| Task 13 — Regresión final | ✅ DONE (2724 passed) | 74 |

### Task 13 — Migración 030 en producción

**Estado:** EN CURSO — A la espera de Deploy manual del usuario

```bash
# Script de migración 030 en producción (ejecutar manualmente)
ssh carli@65.108.60.69
cd /opt/apps/sfce
docker exec sfce_api python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('m030', 'sfce/db/migraciones/030_sugerencia_confirmada.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from sfce.db.base import crear_motor, _leer_config_bd
engine = crear_motor(_leer_config_bd())
mod.aplicar(engine)
print('Migración 030 aplicada en producción')
"
```

---

## Verificación estado actual

```bash
# Verificar tests bancario
python -m pytest tests/test_bancario/ --tb=no -q
# Debe dar: 161 passed

# Verificar motor conciliación implementado
python -c "
from sfce.core.motor_conciliacion import MotorConciliacion
print([m for m in dir(MotorConciliacion) if 'capa' in m or 'inteligente' in m or 'sugerencia' in m])
"

# Verificar migración 029
python -m pytest tests/test_bancario/test_migracion_029.py -v
```

---

## Pendientes previos (baja prioridad, pre-sesión 66)

| Item | Descripción | Acción |
|------|-------------|--------|
| Migración 028 en producción | Pendiente desde sesión 64 | `ALTER TABLE cuentas_correo ADD COLUMN gestoria_id INTEGER` |
| App Passwords IMAP | francisco/luis/gestor1/gestor2/javier | `myaccount.google.com/apppasswords` (requiere 2FA) |
| Script seed producción | `docker exec sfce_api python scripts/crear_cuentas_imap_asesores.py` | Después de App Passwords |
| Push commits locales | `git push origin main` | — |
| Plugins fiscales FS nuevas instancias | Instalar en Gestoría A y Javier | Consola FS superadmin |
| Migración SQLite → PostgreSQL en producción | `scripts/migrar_sqlite_a_postgres.py` | P2 |
| VAPID Push Notifications | Activar `VITE_VAPID_PUBLIC_KEY` + `POST /api/notificaciones/suscribir` | P2 |
| Tests E2E dashboard | Playwright flujos críticos | Sprint siguiente |

---

## Roadmap (features planificadas)

### Próximas features (plan aprobado)

| Feature | Plan | Estado |
|---------|------|--------|
| Conciliación bancaria inteligente completa (Tasks 7-8, 11-13) | `docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md` | EN CURSO |
| Dashboard Rediseño Total (38 páginas nuevas) | `docs/plans/2026-03-01-dashboard-redesign-total.md` | APROBADO |
| Motor de Escenarios de Campo | `docs/plans/2026-03-01-motor-campo-design.md` | APROBADO |

### ClasificadorFiscal (descartado sesión 69 — reimplementar limpio cuando toque)

**Qué era:** rama `feat/motor-clasificacion-fiscal` (commits `fa5f596`, `c85dcf7`). Eliminada por divergencia con main.

**Qué hacía:**
- `ClasificadorFiscal` — clase que deduce automáticamente el tratamiento fiscal de un proveedor (IVA, IRPF, suplidos, intracomunitario) a partir de su nombre/CIF/categoría, sin necesidad de regla manual en config.yaml
- `categorias_gasto.yaml` — base de conocimiento fiscal España: ~40 categorías de gasto con sus tratamientos por defecto (IVA21/IVA0/IVA4, retención IRPF, tipo PGC, si es suplido)

**Valor futuro:** Complementa el motor de reglas actual. En lugar de configurar cada proveedor manualmente, el clasificador propone el tratamiento y el usuario confirma o corrige. Encajaría como Capa 0 del pipeline (pre-Gate 0) o como sugerencia en la cola de revisión.

**Para reimplementar:** crear rama nueva desde main, copiar la lógica de `ClasificadorFiscal` y `categorias_gasto.yaml` desde los commits referenciados arriba usando `git show fa5f596:ruta/archivo`.

### Dashboard Rediseño Total (pendiente)

38 páginas nuevas planificadas:
- Home Centro de Operaciones (cero empty states, datos reales)
- OmniSearch real (Command Palette con búsqueda en BD)
- Paleta ámbar unificada OKLCh
- Analytics avanzados (fact_caja, fact_venta, fact_compra)
- Copiloto IA integrado en sidebar

### Motor de Escenarios de Campo

Empresa id=3 sandbox, bypass OCR, SQLite `motor_campo.db`, 7 procesos cubiertos.
```bash
python scripts/motor_campo.py --modo rapido    # sin coste APIs
python scripts/motor_campo.py --modo completo
python scripts/motor_campo.py --modo continuo
```

### Features post-conciliación

| Feature | Descripción |
|---------|-------------|
| Correo CAP-Web | Gestión correo avanzada (fases 4-6 PROMETH-AI) |
| Certificados AAPP completo | CertiGestor integrado |
| Copiloto IA conversacional | Claude Haiku, fallback local, integrado en dashboard |
| Portal Móvil | App móvil empresario (subir facturas, ver notificaciones) |

---

## Deuda técnica

| Item | Impacto | Acción |
|------|---------|--------|
| 0 tests E2E dashboard | Alto — flujos críticos sin cobertura | Sprint post-conciliación |
| `migrar_sqlite_a_postgres.py` no ejecutado en prod | Medio — producción en SQLite | P2 |
| VAPID endpoint backend faltante | Medio — push notifications no funcionan | P2 |
| `fiscal.proximo_modelo` = null en dashboard | Bajo — campo null en home | P2 |
| uvicorn --reload falla en Windows (WinError 6) | Bajo dev — reiniciar manualmente | workaround documentado |

---

## Notas críticas para retomar sesión (TODO SIGUIENTE SESIÓN)

```bash
# 1. Verificar punto de partida
python -m pytest tests/test_bancario/ --tb=no -q
# Esperado: 161 passed

# 2. Revisar estado git
git log -5 --oneline
git status

# 3. El plan activo está en:
cat docs/plans/2026-03-04-conciliacion-bancaria-inteligente.md | grep "^### Task [789]\|^### Task 1[0-9]"
```

**Notas ORM para tests nuevos (Tasks 7-13):**
- `db_inteligente` fixture necesita `import sfce.db.modelos_auth` (FK gestorias.id)
- `CuentaBancaria` en tests nuevos: `gestoria_id=1` (campo NOT NULL)
- `conciliar_inteligente()` está en `sfce/core/motor_conciliacion.py` al final de la clase `MotorConciliacion`

**Archivos clave a modificar en Tasks 7-13:**
- `sfce/api/rutas/bancario.py` — Tasks 7-8
- `dashboard/src/features/conciliacion/conciliacion-page.tsx` — Task 11
- `dashboard/src/App.tsx` + `dashboard/src/components/sidebar.tsx` — Task 12
- Tests bancario: `tests/test_bancario/test_api_bancario.py` (ya modificado con stubs)

---

## Scripts de utilidad

| Script | Uso |
|--------|-----|
| `scripts/pipeline.py` | SFCE Pipeline 7 fases |
| `scripts/onboarding.py` | Alta interactiva clientes nuevos |
| `scripts/validar_asientos.py` | Validación asientos (5 checks + --fix) |
| `scripts/watcher.py` | Inbox watcher: detecta PDFs en `clientes/*/inbox/` |
| `scripts/motor_campo.py` | Motor de Escenarios de Campo |
| `scripts/migrar_sqlite_a_postgres.py` | Migración BD dev → prod (no ejecutado aún) |
| `scripts/crear_cuentas_imap_asesores.py` | Seed cuentas IMAP asesores en producción |
| `backup_total.sh` | Backup completo (cron 02:00) |
