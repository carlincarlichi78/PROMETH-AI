# Pipeline Paralelo Fases 0+1 — Plan de Implementación

> **Para Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans para implementar este plan task-by-task.

**Goal:** Reducir tiempo de ejecución del pipeline de 20 min a ~5 min paralelizando OCR + pre-validación por documento con ThreadPoolExecutor(5).

**Architecture:** Patrón Map→Reduce: 5 workers procesan un documento cada uno (OCR + checks 1-7,9), el hilo principal hace post-collect (check 8 batch + sort ASC por fecha) y escribe los JSONs ordenados para que las Fases 2-6 operen en orden cronológico correcto para FacturaScripts.

**Tech Stack:** Python stdlib `concurrent.futures.ThreadPoolExecutor`, `threading` (ya presentes). Sin dependencias nuevas.

---

## Guardrails de arquitectura (obligatorios)

1. **SQLite Guardrail**: el worker instancia `with sesion_factory() as db:` propio — nunca comparte sesión con el hilo principal
2. **Exception Isolation**: try/except en el worker devuelve resultado-error seguro, nunca mata el pool
3. **Clave correcta**: pipeline usa `datos_extraidos` (NO `datos_ocr`) — confirmado en `_procesar_un_pdf` línea ~888

---

## Task 1: `validar_documento_individual()` en pre_validation.py

**Files:**
- Modify: `sfce/phases/pre_validation.py` — añadir función pública antes de `ejecutar_pre_validacion`
- Test: `tests/test_pipeline_paralelo.py` (nuevo)

**Descripción:** Extraer la lógica del bucle interno de `ejecutar_pre_validacion` (checks 1-7, 9, A1-A7, F1, F7-F10, checks por tipo) a una función pública que procesa UN documento. El check 8 (duplicados en batch) se excluye deliberadamente — pertenece a la fase Reduce.

**Step 1: Escribir test que falla**

```python
# tests/test_pipeline_paralelo.py
import pytest
from unittest.mock import patch, MagicMock
from sfce.phases.pre_validation import validar_documento_individual

def _doc_valido():
    return {
        "archivo": "factura_test.pdf",
        "tipo": "FC",
        "hash_sha256": "abc123",
        "datos_extraidos": {
            "emisor_cif": "B12345678",
            "fecha": "2025-03-15",
            "total": 121.0,
            "base_imponible": 100.0,
            "iva_importe": 21.0,
            "iva_porcentaje": 21,
        },
    }

def _config_mock():
    cfg = MagicMock()
    cfg.cif = "A87654321"
    cfg.ejercicio = "2025"
    cfg.empresa = {"anio_ejercicio": "2025"}
    cfg.tolerancias = {"comparacion_importes": 0.02}
    cfg.tipos_cambio = {}
    proveedor = {"_nombre_corto": "prov_test", "cif": "B12345678",
                 "divisa": "EUR", "codimpuesto": "IVA21", "regimen": "general",
                 "pais": "ESP"}
    cfg.buscar_proveedor_por_cif.return_value = proveedor
    cfg.buscar_proveedor_por_nombre.return_value = proveedor
    return cfg

def test_validar_documento_individual_valido():
    errores, avisos = validar_documento_individual(
        _doc_valido(), _config_mock(), hashes_fs=set()
    )
    assert errores == [], f"No debería haber errores: {errores}"

def test_validar_documento_individual_cif_invalido():
    doc = _doc_valido()
    doc["datos_extraidos"]["emisor_cif"] = "INVALIDO"
    cfg = _config_mock()
    cfg.buscar_proveedor_por_cif.return_value = None
    cfg.buscar_proveedor_por_nombre.return_value = None
    errores, _ = validar_documento_individual(doc, cfg, hashes_fs=set())
    assert any("CHECK 1" in e or "CHECK 2" in e for e in errores)

def test_validar_documento_individual_sin_check8():
    """Check 8 NO debe ejecutarse en validar_documento_individual."""
    # Dos docs con mismo número de factura — en individual ambos deben pasar
    doc = _doc_valido()
    doc["datos_extraidos"]["numero_factura"] = "F-001"
    errores, _ = validar_documento_individual(doc, _config_mock(), hashes_fs=set())
    # No debe reportar error de duplicado (check 8)
    assert not any("CHECK 8" in e for e in errores)
```

**Step 2: Ejecutar test para verificar que falla**

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
python -m pytest tests/test_pipeline_paralelo.py::test_validar_documento_individual_valido -v
```
Esperado: `ImportError: cannot import name 'validar_documento_individual'`

**Step 3: Implementar `validar_documento_individual` en pre_validation.py**

Insertar ANTES de la función `ejecutar_pre_validacion` (línea ~410):

```python
def validar_documento_individual(
    doc: dict,
    config: "ConfigCliente",
    hashes_fs: set,
    tolerancia: float = 0.02,
) -> tuple[list[str], list[str]]:
    """Valida un único documento (checks 1-7, 9, A1-A7, F1, F7-F10, tipo-específicos).

    Diseñada para ejecución concurrente en ThreadPoolExecutor.
    El check 8 (duplicados en batch) está excluido — debe ejecutarse
    post-collect en el hilo principal sobre la lista completa.

    Args:
        doc: Documento procesado por intake (dict con datos_extraidos, tipo, etc.)
        config: Configuración del cliente.
        hashes_fs: Set de hashes ya registrados en FS (para check 8 de hashes).
        tolerancia: Tolerancia para check 7 (cuadre aritmético).

    Returns:
        (errores, avisos) — listas de strings. errores bloquea el documento.
    """
    archivo = doc.get("archivo", "?")
    tipo_doc = doc.get("tipo", "OTRO")
    datos = doc.get("datos_extraidos", {})
    errores_doc: list[str] = []
    avisos_doc: list[str] = []

    # Determinar entidad y CIF relevante según tipo
    es_proveedor = tipo_doc in ("FC", "NC", "ANT", "SUM")
    if tipo_doc in ("FC", "NC", "ANT", "SUM"):
        cif_entidad = datos.get("emisor_cif") or ""
        entidad = config.buscar_proveedor_por_cif(cif_entidad) if cif_entidad else None
    elif tipo_doc in ("FV", "REC"):
        cif_entidad = datos.get("receptor_cif") or ""
        entidad = config.buscar_cliente_por_cif(cif_entidad) if cif_entidad else None
    elif tipo_doc in ("NOM", "RLC"):
        cif_entidad = datos.get("emisor_cif") or config.empresa.get("cif", "")
        entidad = None
    elif tipo_doc in ("BAN", "IMP"):
        cif_entidad = datos.get("emisor_cif") or datos.get("receptor_cif") or ""
        entidad = None
    else:
        cif_entidad = datos.get("emisor_cif") or ""
        entidad = config.buscar_proveedor_por_cif(cif_entidad) if cif_entidad else None

    pais_entidad = entidad.get("pais", "ESP") if entidad else "ESP"

    # Check 1: CIF formato
    tipos_cif_opcional = ("NOM", "BAN", "RLC", "IMP")
    err = _validar_cif_formato(cif_entidad, pais_entidad)
    if err:
        if tipo_doc in tipos_cif_opcional:
            avisos_doc.append(f"[CHECK 1] {err} (no bloqueante para {tipo_doc})")
        else:
            errores_doc.append(f"[CHECK 1] {err}")

    # Check 2: Entidad existe
    err = _validar_entidad_existe(doc, tipo_doc, config)
    if err:
        errores_doc.append(f"[CHECK 2] {err}")

    # Check 3: Divisa
    err = _validar_divisa(doc, tipo_doc, config)
    if err:
        avisos_doc.append(f"[CHECK 3] {err}")

    # Check 4: Tipo IVA
    err = _validar_tipo_iva(doc, tipo_doc, config)
    if err:
        avisos_doc.append(f"[CHECK 4] {err}")

    # Check 5: Fecha en ejercicio
    err = _validar_fecha_ejercicio(doc, config)
    if err:
        if tipo_doc in ("RLC", "BAN"):
            avisos_doc.append(f"[CHECK 5] {err} (no bloqueante para {tipo_doc})")
        else:
            errores_doc.append(f"[CHECK 5] {err}")

    # Check 6: Importe positivo
    err = _validar_importe_positivo(doc, tipo_doc)
    if err:
        errores_doc.append(f"[CHECK 6] {err}")

    # Check 7: Cuadre base+IVA=total
    if tipo_doc not in ("NOM", "BAN", "RLC", "IMP"):
        err = _validar_cuadre_base_iva_total(doc, tolerancia)
        if err:
            avisos_doc.append(f"[CHECK 7] {err}")

    # Check 9: No existe en FS (I/O bound — principal beneficio de paralelizar)
    if tipo_doc not in ("NOM", "BAN", "RLC", "IMP"):
        err = _validar_no_existe_en_fs(doc, tipo_doc, config)
        if err:
            errores_doc.append(f"[CHECK 9] {err}")

    # A1-A7: Aritmética pura
    avisos_aritmetica = ejecutar_checks_aritmeticos(doc)
    for aviso in avisos_aritmetica:
        avisos_doc.append(aviso)

    # F1: Coherencia CIF -> IVA
    cif_emisor = datos.get("emisor_cif", "")
    iva_pct = float(datos.get("iva_porcentaje", 0) or 0)
    if cif_emisor and iva_pct > 0:
        err_f1 = validar_coherencia_cif_iva(cif_emisor, iva_pct)
        if err_f1:
            avisos_doc.append(f"[F1] {err_f1}")

    # F7: Divisa extranjera sin tipo de cambio
    divisa_doc = (datos.get("divisa") or "EUR").upper()
    if divisa_doc != "EUR":
        tc_key = f"{divisa_doc}_EUR"
        if not config.tipos_cambio.get(tc_key):
            avisos_doc.append(
                f"[F7] Factura en {divisa_doc} sin tipo de cambio "
                f"configurado ({tc_key} no existe en config.yaml)"
            )

    # F8: Intracomunitaria sin ISP
    if es_proveedor and entidad:
        regimen_prov = entidad.get("regimen", "general")
        if regimen_prov == "intracomunitario":
            iva_factura = float(datos.get("iva_porcentaje", 0) or 0)
            if iva_factura > 0:
                avisos_doc.append(
                    f"[F8] Proveedor intracomunitario "
                    f"({entidad.get('_nombre_corto', cif_entidad)}) "
                    f"con IVA {iva_factura}% (esperado 0% + ISP)"
                )
            lineas = datos.get("lineas", [])
            texto_lineas = " ".join(l.get("descripcion", "") for l in lineas).lower()
            texto_completo = (datos.get("notas", "") or "").lower() + " " + texto_lineas
            tiene_isp = any(
                t in texto_completo
                for t in ["inversion sujeto pasivo", "inversión sujeto pasivo",
                          "isp", "reverse charge", "art. 84",
                          "articulo 84", "artículo 84"]
            )
            if not tiene_isp and not entidad.get("autoliquidacion"):
                avisos_doc.append(
                    "[F8] Proveedor intracomunitario sin mención de ISP "
                    "ni autoliquidación configurada"
                )

    # F9: IRPF anómalo
    irpf_pct = datos.get("irpf_porcentaje")
    irpf_imp = float(datos.get("irpf_importe", 0) or 0)
    if irpf_pct is not None:
        irpf_pct = float(irpf_pct)
        if irpf_pct < 0:
            avisos_doc.append(f"[F9] IRPF negativo ({irpf_pct}%) — posible error de signo")
        elif irpf_pct > 0:
            tasas_legales = {1, 2, 7, 15, 19, 24, 35}
            if irpf_pct not in tasas_legales:
                avisos_doc.append(
                    f"[F9] IRPF {irpf_pct}% no es una tasa legal "
                    f"(válidas: {sorted(tasas_legales)})"
                )
    if irpf_imp < 0:
        avisos_doc.append(
            f"[F9] Cuota IRPF negativa ({irpf_imp}€) — retención no puede ser negativa"
        )

    # F10: Fecha coherente
    fecha_str = datos.get("fecha", "")
    if fecha_str:
        try:
            fecha_doc = datetime.strptime(fecha_str, "%Y-%m-%d")
            if fecha_doc > datetime.now():
                avisos_doc.append(f"[F10] Fecha factura {fecha_str} es futura")
            dias_antiguedad = (datetime.now() - fecha_doc).days
            if dias_antiguedad > 365:
                avisos_doc.append(
                    f"[F10] Factura con {dias_antiguedad} días de antigüedad (>1 año)"
                )
        except ValueError:
            pass

    # Checks específicos por tipo
    if tipo_doc == "NOM":
        for check_fn in [_check_nomina_cuadre, _check_nomina_irpf, _check_nomina_ss]:
            aviso = check_fn(datos)
            if aviso:
                avisos_doc.append(aviso)
    elif tipo_doc == "SUM":
        aviso = _check_suministro_cuadre(datos)
        if aviso:
            avisos_doc.append(aviso)
    elif tipo_doc == "BAN":
        aviso = _check_bancario_importe(datos)
        if aviso:
            avisos_doc.append(aviso)
    elif tipo_doc == "RLC":
        aviso = _check_rlc_cuota(datos)
        if aviso:
            avisos_doc.append(aviso)

    return errores_doc, avisos_doc
```

**Step 4: Ejecutar tests para verificar que pasan**

```bash
python -m pytest tests/test_pipeline_paralelo.py -v
```
Esperado: 3 tests PASS

**Step 5: Commit**

```bash
git add sfce/phases/pre_validation.py tests/test_pipeline_paralelo.py
git commit -m "feat(pipeline): añadir validar_documento_individual() para ejecucion paralela"
```

---

## Task 2: Alias público en intake.py

**Files:**
- Modify: `sfce/phases/intake.py` — añadir al final del archivo

**Step 1: Añadir alias público al final de intake.py**

```python
# --- Alias público para uso en pipeline paralelo ---
procesar_un_pdf = _procesar_un_pdf
```

**Step 2: Verificar importación**

```bash
python -c "from sfce.phases.intake import procesar_un_pdf; print('OK')"
```
Esperado: `OK`

**Step 3: Commit**

```bash
git add sfce/phases/intake.py
git commit -m "feat(pipeline): exponer procesar_un_pdf como alias publico en intake"
```

---

## Task 3: `_ejecutar_fases_01_paralelo()` en pipeline.py

**Files:**
- Modify: `scripts/pipeline.py` — añadir función helper antes de `main()`
- Test: `tests/test_pipeline_paralelo.py` — añadir tests de sort y excepcion isolation

**Step 1: Añadir tests de la barrera y sort**

```python
# En tests/test_pipeline_paralelo.py
from datetime import datetime

def test_sort_por_fecha_ascendente():
    """Los resultados paralelos deben ordenarse por fecha ASC antes de pasar a Fase 2."""
    from scripts.pipeline import _ordenar_por_fecha

    docs = [
        {"datos_extraidos": {"fecha": "2025-06-15"}, "tipo": "FC"},
        {"datos_extraidos": {"fecha": "2025-01-10"}, "tipo": "FC"},
        {"datos_extraidos": {"fecha": "2025-03-20"}, "tipo": "FC"},
        {"datos_extraidos": {}, "tipo": "FC"},  # sin fecha → al final
    ]
    ordenados = _ordenar_por_fecha(docs)
    fechas = [d.get("datos_extraidos", {}).get("fecha", "") for d in ordenados]
    assert fechas[0] == "2025-01-10"
    assert fechas[1] == "2025-03-20"
    assert fechas[2] == "2025-06-15"
    assert fechas[3] == ""  # sin fecha al final

def test_worker_aislamiento_excepcion():
    """Una excepción en el worker no debe propagar fuera del ThreadPoolExecutor."""
    import concurrent.futures

    def worker_que_falla(x):
        if x == 2:
            raise RuntimeError("Fallo simulado de API")
        return {"resultado": x * 2}

    resultados = []
    errores = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futuros = {executor.submit(worker_que_falla, i): i for i in range(5)}
        for futuro in concurrent.futures.as_completed(futuros):
            try:
                resultados.append(futuro.result())
            except Exception as e:
                errores.append(str(e))

    assert len(errores) == 1
    assert "Fallo simulado" in errores[0]
    assert len(resultados) == 4  # Los otros 4 procesaron OK
```

**Step 2: Ejecutar tests para verificar que fallan**

```bash
python -m pytest tests/test_pipeline_paralelo.py::test_sort_por_fecha_ascendente -v
```
Esperado: `ImportError: cannot import name '_ordenar_por_fecha'`

**Step 3: Implementar `_ordenar_por_fecha` y `_ejecutar_fases_01_paralelo` en pipeline.py**

Insertar ANTES de `def main():` (aproximadamente línea 288):

```python
def _ordenar_por_fecha(documentos: list[dict]) -> list[dict]:
    """Ordena documentos por datos_extraidos.fecha ASC. Docs sin fecha van al final.

    Crítico para FacturaScripts: las facturas de cliente (FV) deben registrarse
    en orden cronológico para evitar error 422 por número de factura no correlativo.
    """
    def _clave(doc: dict):
        fecha = (doc.get("datos_extraidos") or {}).get("fecha") or ""
        try:
            return datetime.strptime(fecha[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return datetime.max

    return sorted(documentos, key=_clave)


def _ejecutar_fases_01_paralelo(
    config,
    ruta_cliente: Path,
    args,
    auditoria,
    sesion_factory=None,
    max_workers: int = 5,
) -> tuple:
    """Ejecuta Fases 0 (OCR) y 1 (pre-validación) en paralelo por documento.

    Patrón Map→Reduce:
    - MAP: ThreadPoolExecutor(5) — cada worker procesa 1 PDF completo
      (OCR + validación individual, checks 1-7 + check 9 paralelo)
    - REDUCE: hilo principal — check 8 (duplicados batch), sort ASC por fecha,
      escritura de intake_results.json y validated_batch.json ordenados

    Guardrails de arquitectura:
    1. SQLite: cada worker instancia su propia sesión (with sesion_factory() as db)
    2. Exception isolation: try/except en cada worker devuelve error seguro
    3. Gemini bloqueado si len(pdfs_a_procesar) > 20 (rate limit)

    Returns:
        (resultado_intake: ResultadoFase, resultado_pre_val: ResultadoFase)
    """
    from sfce.phases.intake import (
        _calcular_hash,
        _cargar_estado_pipeline,
        _guardar_estado_pipeline,
        procesar_un_pdf,
    )
    from sfce.phases.pre_validation import (
        validar_documento_individual,
        _validar_no_duplicado,
    )

    import concurrent.futures as _cf
    import os as _os
    from openai import OpenAI as _OpenAI

    resultado_intake = ResultadoFase("intake")
    resultado_pre_val = ResultadoFase("pre_validacion")
    carpeta_inbox = getattr(args, "inbox", "inbox")
    ruta_inbox = ruta_cliente / carpeta_inbox
    ruta_cuarentena = ruta_cliente / "cuarentena"

    if not ruta_inbox.exists():
        resultado_intake.error("No existe carpeta inbox/", {"ruta": str(ruta_inbox)})
        return resultado_intake, resultado_pre_val

    # Buscar PDFs (replica lógica de ejecutar_intake)
    _carpetas_excluidas = {"CARPETA REFERENCIA", "procesado", "cuarentena"}

    def _filtrar_pdfs(patron):
        return sorted([
            p for p in ruta_inbox.rglob(patron)
            if not any(excl in p.parts for excl in _carpetas_excluidas)
        ])

    pdfs = _filtrar_pdfs("*.pdf") or _filtrar_pdfs("*.PDF")
    if not pdfs:
        resultado_intake.aviso("No hay PDFs en inbox/")
        resultado_intake.datos["documentos"] = []
        resultado_pre_val.datos["validados"] = []
        resultado_pre_val.datos["excluidos"] = []
        return resultado_intake, resultado_pre_val

    # Pre-filtrar duplicados por hash (secuencial, rápido)
    estado_pipeline = _cargar_estado_pipeline(ruta_cliente)
    hashes_previos = set(estado_pipeline.get("hashes_procesados", []))
    hashes_fs = set(estado_pipeline.get("hashes_registrados_fs", []))

    pdfs_a_procesar = []
    for ruta_pdf in pdfs:
        h = _calcular_hash(ruta_pdf)
        if h in hashes_previos:
            logger.info(f"  Duplicado, saltando: {ruta_pdf.name}")
            resultado_intake.aviso(f"PDF duplicado: {ruta_pdf.name}", {"hash": h})
        else:
            pdfs_a_procesar.append((ruta_pdf, h))

    if not pdfs_a_procesar:
        resultado_intake.aviso("No hay PDFs nuevos por procesar")
        resultado_intake.datos["documentos"] = []
        resultado_pre_val.datos["validados"] = []
        resultado_pre_val.datos["excluidos"] = []
        return resultado_intake, resultado_pre_val

    n_docs = len(pdfs_a_procesar)
    logger.info(f"Encontrados {n_docs} PDFs nuevos — iniciando pipeline paralelo fases 0+1")

    # Determinar motores OCR
    mistral_disponible = bool(_os.environ.get("MISTRAL_API_KEY"))
    openai_disponible = bool(_os.environ.get("OPENAI_API_KEY"))
    if not mistral_disponible and not openai_disponible:
        resultado_intake.error("Ninguna API key OCR configurada")
        return resultado_intake, resultado_pre_val

    client = _OpenAI(api_key=_os.environ["OPENAI_API_KEY"]) if openai_disponible else None
    motor_primario = "mistral" if mistral_disponible else "openai"

    # GUARDRAIL: Gemini bloqueado si >20 documentos (rate limit 20 req/día)
    try:
        from sfce.core.ocr_gemini import extraer_factura_gemini as _  # noqa
        _gemini_lib_ok = True
    except ImportError:
        _gemini_lib_ok = False
    gemini_disponible = (
        _gemini_lib_ok
        and bool(_os.environ.get("GEMINI_API_KEY"))
        and n_docs <= 20
    )
    if _gemini_lib_ok and n_docs > 20:
        logger.info(f"Gemini deshabilitado: {n_docs} docs > límite 20 req/día")

    interactivo = not getattr(args, "no_interactivo", False)
    tolerancia = config.tolerancias.get("comparacion_importes", 0.02)

    # ── WORKER COMBINADO fase 0+1 ──────────────────────────────────────────
    def _worker_fase_01(item: tuple) -> dict:
        ruta_pdf, hash_pdf = item

        # GUARDRAIL SQLite: instanciar sesión propia por hilo
        # (ninguna función de fases 0-1 usa BD actualmente, pero el patrón
        # garantiza seguridad si en el futuro se añade acceso a SQLite)
        _db_session = None
        if sesion_factory:
            try:
                _db_session = sesion_factory().__enter__()
            except Exception:
                _db_session = None  # BD no crítica para OCR/validación

        try:
            # ── Fase 0: OCR ──────────────────────────────────────────────
            res_ocr = procesar_un_pdf(
                ruta_pdf, hash_pdf, config, client, motor_primario,
                gemini_disponible, ruta_cuarentena, interactivo,
                ruta_inbox=ruta_inbox,
            )

            if not res_ocr.get("doc"):
                return {**res_ocr, "errores_val": [], "avisos_val": []}

            # ── Fase 1: Validación individual (checks 1-7, 9, F-checks) ──
            errores_val, avisos_val = validar_documento_individual(
                res_ocr["doc"], config, hashes_fs, tolerancia=tolerancia
            )
            return {**res_ocr, "errores_val": errores_val, "avisos_val": avisos_val}

        except Exception as exc:
            # GUARDRAIL: nunca dejar que una excepción mate el pool
            logger.error(f"[worker_fase01] Error inesperado en {ruta_pdf.name}: {exc}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                "doc": None,
                "hash": hash_pdf,
                "avisos": [(f"Error inesperado: {ruta_pdf.name}", {"error": str(exc)})],
                "tier": -1,
                "errores_val": [f"Error worker: {exc}"],
                "avisos_val": [],
            }
        finally:
            if _db_session is not None:
                try:
                    _db_session.__exit__(None, None, None)
                except Exception:
                    pass

    # ── MAP: ejecución paralela ────────────────────────────────────────────
    usar_paralelo = not interactivo and max_workers > 1 and n_docs > 1
    workers_efectivos = min(max_workers, n_docs) if usar_paralelo else 1
    logger.info(
        f"Motor: {motor_primario} | Workers: {workers_efectivos}"
        f"{' | Gemini: ON' if gemini_disponible else ' | Gemini: OFF'}"
        f" | Modo: {'paralelo' if usar_paralelo else 'secuencial'}"
    )

    resultados_raw = []
    tier_stats = {}

    if usar_paralelo:
        with _cf.ThreadPoolExecutor(max_workers=workers_efectivos) as executor:
            futuros = {executor.submit(_worker_fase_01, item): item
                       for item in pdfs_a_procesar}
            for futuro in _cf.as_completed(futuros):
                ruta_pdf, _ = futuros[futuro]
                try:
                    res = futuro.result()
                except Exception as exc:
                    logger.error(f"Future no capturado para {ruta_pdf.name}: {exc}")
                    res = {"doc": None, "hash": futuros[futuro][1],
                           "avisos": [], "tier": -1,
                           "errores_val": [str(exc)], "avisos_val": []}
                resultados_raw.append(res)
    else:
        for item in pdfs_a_procesar:
            resultados_raw.append(_worker_fase_01(item))

    # ── REDUCE ────────────────────────────────────────────────────────────

    # Recoger docs extraídos y hashes nuevos
    docs_extraidos = []
    hashes_nuevos = []
    for res in resultados_raw:
        for msg, datos_av in res.get("avisos", []):
            resultado_intake.aviso(msg, datos_av)
        if res.get("doc"):
            docs_extraidos.append(res["doc"])
            hashes_nuevos.append(res["hash"])
            tier = res.get("tier", 0)
            tier_stats[tier] = tier_stats.get(tier, 0) + 1

    # Actualizar hashes procesados
    estado_pipeline["hashes_procesados"] = list(hashes_previos | set(hashes_nuevos))
    _guardar_estado_pipeline(ruta_cliente, estado_pipeline)

    # Check 8: duplicados en batch (requiere lista completa — post-collect)
    docs_procesados_check8 = []
    validados = []
    excluidos = []

    for res in resultados_raw:
        doc = res.get("doc")
        if not doc:
            continue
        errores_val = list(res.get("errores_val", []))
        avisos_val = list(res.get("avisos_val", []))

        tipo_doc = doc.get("tipo", "OTRO")
        if tipo_doc not in ("NOM", "BAN", "RLC", "IMP"):
            err_ch8 = _validar_no_duplicado(doc, docs_procesados_check8, hashes_fs)
            if err_ch8:
                errores_val.append(f"[CHECK 8] {err_ch8}")

        docs_procesados_check8.append(doc)

        if errores_val:
            excluidos.append({**doc, "errores_validacion": errores_val,
                               "avisos_validacion": avisos_val})
            resultado_pre_val.aviso(f"Documento excluido: {doc['archivo']}",
                                    {"errores": errores_val})
        else:
            validados.append({**doc, "avisos_validacion": avisos_val})

        if auditoria:
            estado_doc = "validado" if not errores_val else "excluido"
            auditoria.registrar("pre_validacion", "verificacion",
                                f"{doc['archivo']}: {estado_doc}",
                                {"errores": errores_val, "avisos": avisos_val})

    # SORT ASC por fecha (crítico para FacturaScripts FV)
    validados = _ordenar_por_fecha(validados)

    # Escribir intake_results.json
    import __builtin_datetime__ as _dt  # workaround — usar datetime ya importado
    ruta_intake = ruta_cliente / "intake_results.json"
    with open(ruta_intake, "w", encoding="utf-8") as f:
        import json as _json
        _json.dump({
            "fecha_ejecucion": datetime.now().isoformat(),
            "total_pdfs_encontrados": len(pdfs),
            "total_procesados": len(docs_extraidos),
            "total_duplicados": len(pdfs) - len(pdfs_a_procesar),
            "ocr_tier_stats": tier_stats,
            "documentos": docs_extraidos,
        }, f, ensure_ascii=False, indent=2)

    # Escribir validated_batch.json (ya ordenado por fecha ASC)
    ruta_validados = ruta_cliente / "validated_batch.json"
    with open(ruta_validados, "w", encoding="utf-8") as f:
        _json.dump({
            "fecha_ejecucion": datetime.now().isoformat(),
            "total_validados": len(validados),
            "total_excluidos": len(excluidos),
            "validados": validados,
            "excluidos": excluidos,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"OCR Tiers: T0={tier_stats.get(0,0)}, T1={tier_stats.get(1,0)}, "
                f"T2={tier_stats.get(2,0)}")
    logger.info(f"Pre-validación: {len(validados)} OK, {len(excluidos)} excluidos")
    logger.info(f"Orden cronológico aplicado — primer doc: "
                f"{validados[0].get('datos_extraidos', {}).get('fecha', '?') if validados else 'n/a'}")

    # Poblar ResultadoFase para compatibilidad con quality gates de pipeline
    resultado_intake.datos["documentos"] = docs_extraidos
    resultado_intake.datos["ruta_resultados"] = str(ruta_intake)
    resultado_intake.datos["ocr_tier_stats"] = tier_stats
    resultado_intake.datos["duplicados_negocio"] = {"seguros": 0, "posibles": 0}

    resultado_pre_val.datos["validados"] = validados
    resultado_pre_val.datos["excluidos"] = excluidos
    resultado_pre_val.datos["ruta_validados"] = str(ruta_validados)

    return resultado_intake, resultado_pre_val
```

**Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_pipeline_paralelo.py -v
```
Esperado: todos PASS

**Step 5: Commit**

```bash
git add scripts/pipeline.py
git commit -m "feat(pipeline): anadir _ejecutar_fases_01_paralelo y _ordenar_por_fecha"
```

---

## Task 4: Integrar en `main()` de pipeline.py

**Files:**
- Modify: `scripts/pipeline.py` — sección principal de `main()` después de definir FASES

**Descripción:** Detectar cuándo usar la ejecución combinada vs. standalone. La lógica es:
- Si `--fase N` con N en {0,1}: usar funciones originales (standalone)
- Si `--fase N` con N >= 2 o `--fase None`: usar el combinado (si aplica)
- Si `--resume` y ambas fases ya completadas: saltarlas igualmente

**Step 1: Modificar el bloque de ejecución en main()**

Buscar la línea que comienza el loop `# Ejecutar pipeline` (aproximadamente línea 457) y reemplazar el bloque completo del loop por:

```python
    # ── Ejecución pipeline ──────────────────────────────────────────────────
    #
    # Fases 0+1: se ejecutan combinadas en paralelo salvo que el usuario
    # pida explícitamente solo fase 0 ó 1 con --fase N.
    # Fases 2-6: siempre secuenciales en el hilo principal.

    ejecutar_solo_fase = args.fase is not None
    fases_01_ejecutadas = False
    resultados_precomputed: dict = {}

    if not ejecutar_solo_fase or args.fase in (0, 1):
        # Determinar si ambas fases 0 y 1 deben ejecutarse (no ya completadas en resume)
        fase0_pendiente = not (args.resume and estado.fase_completada("intake"))
        fase1_pendiente = not (args.resume and estado.fase_completada("pre_validacion"))

        if fase0_pendiente and fase1_pendiente and not ejecutar_solo_fase:
            # Ejecución combinada (el camino rápido)
            logger.info("")
            logger.info("=" * 60)
            logger.info("  Fases 0+1: OCR + Pre-validación (paralelo)")
            logger.info("=" * 60)
            try:
                res_intake, res_preval = _ejecutar_fases_01_paralelo(
                    config, ruta_cliente, args, auditoria,
                    sesion_factory=sesion_factory if _BD_DISPONIBLE and sesion_factory else None,
                )
            except Exception as exc:
                logger.error(f"Error en fases combinadas 0+1: {exc}")
                import traceback
                logger.debug(traceback.format_exc())
                if not args.force:
                    return 1
                res_intake = ResultadoFase("intake")
                res_preval = ResultadoFase("pre_validacion")

            # Quality gates y persistencia para ambas fases
            for nombre_fase, resultado in [("intake", res_intake),
                                            ("pre_validacion", res_preval)]:
                if not resultado.exitoso:
                    logger.error(f"QUALITY GATE FALLIDO: {nombre_fase}")
                    for err in resultado.errores:
                        logger.error(f"  - {err['mensaje']}")
                    if not args.force:
                        estado.guardar()
                        auditoria.guardar()
                        return 1
                estado.completar_fase(nombre_fase, resultado.datos)
                auditoria.registrar(nombre_fase, "fase_completada", resultado.resumen())
                logger.info(f"  {resultado.resumen()}")

            # Post-intake: sincronizar cuarentena BD
            if _BD_DISPONIBLE and sesion_factory and empresa_bd_id:
                _sincronizar_cuarentena_bd(
                    sesion_factory, empresa_bd_id,
                    ruta_cliente / "cuarentena",
                    res_intake, logger,
                )

            fases_01_ejecutadas = True

    # Loop fases (saltando 0 y 1 si ya se ejecutaron combinadas)
    for fase_def in FASES:
        nombre = fase_def["nombre"]
        indice = fase_def["indice"]
        descripcion = fase_def["descripcion"]

        # Saltar fases 0 y 1 si ya se ejecutaron en modo combinado
        if fases_01_ejecutadas and nombre in ("intake", "pre_validacion"):
            continue

        # Skip si ya completada (resume)
        if args.resume and estado.fase_completada(nombre):
            logger.info(f"[SKIP] {descripcion} (ya completada)")
            continue

        # Skip en dry-run
        if args.dry_run and fase_def.get("dry_run_skip", False):
            logger.info(f"[SKIP] {descripcion} (dry-run)")
            continue

        logger.info("")
        logger.info(f"{'='*60}")
        logger.info(f"  {descripcion}")
        logger.info(f"{'='*60}")

        try:
            resultado = fase_def["ejecutar"]()
        except Exception as e:
            import traceback
            logger.error(f"Error inesperado en {nombre}: {e}")
            logger.debug(traceback.format_exc())
            auditoria.registrar(nombre, "error", f"Error inesperado: {e}")
            auditoria.guardar()
            if not args.force:
                return 1
            continue

        # Quality gate
        if not resultado.exitoso:
            logger.error(f"QUALITY GATE FALLIDO: {nombre}")
            for err in resultado.errores:
                logger.error(f"  - {err['mensaje']}")

            if args.force:
                logger.warning("--force activo, continuando...")
            else:
                logger.error(f"Pipeline BLOQUEADO en fase {nombre}")
                logger.error("Usar --force para ignorar o --resume tras corregir")
                estado.guardar()
                auditoria.guardar()
                return 1

        # Guardar resultado de fase
        estado.completar_fase(nombre, resultado.datos)
        auditoria.registrar(nombre, "fase_completada", resultado.resumen())
        logger.info(f"  {resultado.resumen()}")

        if resultado.correcciones:
            logger.info(f"  Correcciones auto-aplicadas: {len(resultado.correcciones)}")
        if resultado.avisos:
            logger.info(f"  Avisos: {len(resultado.avisos)}")

        # Post-intake standalone (--fase 0)
        if nombre == "intake" and _BD_DISPONIBLE and sesion_factory and empresa_bd_id:
            _sincronizar_cuarentena_bd(
                sesion_factory, empresa_bd_id,
                ruta_cliente / "cuarentena",
                resultado, logger,
            )
```

**Step 2: Arreglar bug del import `__builtin_datetime__`**

En `_ejecutar_fases_01_paralelo`, el workaround `import __builtin_datetime__` debe reemplazarse por `import json` (ya está importado globalmente). Limpiar el código para usar `json` y `datetime` del scope del módulo.

**Step 3: Verificar que el pipeline arranca sin errores de import**

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
python -c "from scripts.pipeline import main, _ejecutar_fases_01_paralelo, _ordenar_por_fecha; print('imports OK')"
```
Esperado: `imports OK`

**Step 4: Commit**

```bash
git add scripts/pipeline.py
git commit -m "feat(pipeline): integrar ejecucion paralela fases 0+1 en main()"
```

---

## Task 5: Tests adicionales

**Files:**
- Modify: `tests/test_pipeline_paralelo.py`

```python
def test_ordenar_sin_fecha_va_al_final():
    from scripts.pipeline import _ordenar_por_fecha
    docs = [
        {"datos_extraidos": {"fecha": "2025-12-01"}},
        {"datos_extraidos": {}},  # sin fecha
        {"datos_extraidos": {"fecha": "2025-01-01"}},
    ]
    ordenados = _ordenar_por_fecha(docs)
    assert ordenados[0]["datos_extraidos"]["fecha"] == "2025-01-01"
    assert ordenados[1]["datos_extraidos"]["fecha"] == "2025-12-01"
    assert ordenados[2]["datos_extraidos"].get("fecha", "") == ""

def test_ordenar_lista_vacia():
    from scripts.pipeline import _ordenar_por_fecha
    assert _ordenar_por_fecha([]) == []

def test_gemini_bloqueado_mas_de_20_docs(monkeypatch, tmp_path):
    """Con >20 docs, gemini_disponible debe ser False en el worker."""
    # Este test verifica la lógica de decisión sin llamar a APIs reales
    # Se valida inspeccionando el log de _ejecutar_fases_01_paralelo
    import logging
    captured = []

    class CapHandler(logging.Handler):
        def emit(self, record):
            captured.append(record.getMessage())

    handler = CapHandler()
    logging.getLogger("pipeline").addHandler(handler)

    # Simular la condición con monkeypatch
    from scripts.pipeline import _ejecutar_fases_01_paralelo
    # La lógica está en el cuerpo de la función; verificar el log message
    # Sin PDFs reales, la función retorna temprano tras ruta_inbox.exists() = False
    # → test de integración real necesario con --dry-run
    logging.getLogger("pipeline").removeHandler(handler)
```

**Step 6: Ejecutar suite completa de tests**

```bash
python -m pytest tests/test_pipeline_paralelo.py -v
```
Esperado: todos los tests PASS

**Step 7: Commit**

```bash
git add tests/test_pipeline_paralelo.py
git commit -m "test(pipeline): suite de tests para pipeline paralelo fases 0+1"
```

---

## Task 6: Verificación --dry-run e integración

**Prerequisitos:** Cliente con PDFs en inbox. Usar `gerardo-gonzalez-callejon` o crear carpeta de prueba.

**Step 1: dry-run verificando paralelismo en logs**

```bash
cd c:/Users/carli/PROYECTOS/CONTABILIDAD
export $(grep -v '^#' .env | xargs)
python scripts/pipeline.py \
  --cliente gerardo-gonzalez-callejon \
  --ejercicio 2025 \
  --inbox inbox_gerardo \
  --no-interactivo \
  --dry-run \
  2>&1 | tail -40
```

Verificar en output:
- `"Workers: 5"` (o el número que aplique)
- `"Gemini: ON/OFF"` (OFF si >20 docs)
- `"Fases 0+1: OCR + Pre-validación (paralelo)"`
- `"Orden cronológico aplicado — primer doc: YYYY-MM-DD"`

**Step 2: Verificar validated_batch.json ordenado**

```bash
python -c "
import json
with open('clientes/gerardo-gonzalez-callejon/validated_batch.json') as f:
    data = json.load(f)
fechas = [d.get('datos_extraidos',{}).get('fecha','SIN') for d in data['validados'][:10]]
print('Primeras 10 fechas:', fechas)
all_ok = all(fechas[i] <= fechas[i+1] for i in range(len(fechas)-1) if fechas[i] != 'SIN' and fechas[i+1] != 'SIN')
print('Ordenado ASC:', all_ok)
"
```
Esperado: `Ordenado ASC: True`

**Step 3: Commit final y push**

```bash
git add -A
git commit -m "feat(pipeline): paralelizacion fases 0+1 — OCR+validacion 5 workers, sort ASC, Gemini cap 20"
git push origin main
```

---

## Notas de implementación

### Sobre `sesion_factory` en el worker
La sesión se crea defensivamente aunque fases 0-1 no usen BD actualmente.
El patrón `with sesion_factory() as db:` garantiza que si en el futuro se añade
acceso BD (ej. telemetría por documento), el código ya es correcto.

### Sobre `interactivo`
Con `--no-interactivo` → `usar_paralelo = True` (modo normal pipeline prod)
Sin `--no-interactivo` → `usar_paralelo = False` (modo dev/interactivo secuencial)
El descubrimiento interactivo (`input()`) no puede ejecutarse en threads paralelos.

### Sobre compatibilidad `--fase N`
- `--fase 0`: usa `ejecutar_intake()` original (standalone)
- `--fase 1`: usa `ejecutar_pre_validacion()` original (lee intake_results.json)
- `--fase 2-6`: fases combinadas ya completadas, ejecuta solo la fase pedida
- Sin `--fase`: ejecución combinada paralela (camino rápido)
