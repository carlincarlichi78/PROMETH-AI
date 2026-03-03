# Auditoría Tests + CI/CD SFCE — 2026-03-02

**Veredicto: SÓLIDO CON GAPS IMPORTANTES**
**Críticos: 3 | Importantes: 6 | CI/CD: 5 | Docker: 3 | Dependencias: 4**

---

## CRÍTICOS (CI puede pasar pero no detecta bugs reales)

### [TEST-1] Analytics API acepta 200 O 404 como resultado válido
- **Archivo**: `tests/test_analytics_api.py:58-84`
- **Problema**: `assert r.status_code in (200, 404)` — el test pasa aunque el endpoint devuelva 404 siempre (empresa no existe en el fixture). No se verifica el body ni que los cálculos sean correctos.
- **Fix**: Crear empresa en el fixture, llamar con datos válidos, verificar estructura del body.

### [TEST-2] `time.sleep()` en test de token expirado — enmasca flakiness
- **Archivo**: `tests/test_auth.py:147,316`
- **Problema**: `time.sleep(0.1)` innecesario — un token con `expires_delta=timedelta(seconds=-1)` ya expiró al crearse.
- **Fix**: Eliminar el sleep.

### [TEST-3] `test_watcher.py` usa múltiples `time.sleep(0.5)` para filesystem events
- **Archivo**: `tests/test_watcher.py:173,186,192,198,221,304,329`
- **Problema**: Depende del timing del OS para detección de filesystem events. Candidato a fallo esporádico en CI bajo carga.
- **Fix**: Polling con timeout explícito o mock del observer.

---

## IMPORTANTES

| ID | Descripción | Archivo |
|----|-------------|---------|
| TEST-5 | Sin `conftest.py` — fixture `sesion_factory` duplicada en 30+ archivos de test | `tests/` (directorio raíz) |
| TEST-6 | `asyncio_mode` no configurado en `pyproject.toml` — tests async pueden fallar silenciosamente sin `@pytest.mark.asyncio` | `pyproject.toml:32-33` |
| TEST-7 | Tests analytics no crean datos → prueban solo que el endpoint no devuelve 500 | `test_analytics_api.py` |
| TEST-8 | CI no mide cobertura — `pytest --tb=short -q` sin `--cov` | `deploy.yml:71` |
| TEST-9 | `datetime.utcnow()` deprecado en Python 3.12 — 12 usos en tests, 25 en producción | múltiples archivos |
| TEST-10 | Sin rollback definido si el deploy falla a mitad (frontend swapeado pero API no arranca) | `deploy.yml:180-201` |

---

## CI/CD — Issues

| ID | Descripción | Archivo |
|----|-------------|---------|
| CI-1 | Imagen Docker se llama `spice` en lugar de `sfce` (nombre de la landing anterior) | `deploy.yml:17` |
| CI-2 | `build-frontend` corre en paralelo con `test` — desperdicia minutos si tests fallan | `deploy.yml:74-77` |
| CI-3 | `POSTGRES_PASSWORD: test_password_ci` en plaintext en el workflow (en historial git) | `deploy.yml:32,46` |
| CI-4 | Smoke test sin `timeout-minutes` — puede colgar el workflow (default GitHub: 6h) | `deploy.yml:240-260` |
| CI-5 | Sin ESLint ni TypeScript check en CI para frontend — errores TS que no bloquean build van a producción | `deploy.yml:88-94` |

---

## DOCKER — Issues

| ID | Descripción | Fix |
|----|-------------|-----|
| DOCKER-1 | Imagen corre como **root** — sin directiva `USER` | Añadir `RUN useradd --system --uid 1001 sfce && USER sfce` |
| DOCKER-2 | `HEALTHCHECK` usa `python -c urllib.request` — frágil (no distingue 200 `status:error`) | Instalar `curl` y usar `curl --fail http://localhost:8000/api/health` |
| DOCKER-3 | `build-docker` no depende de `build-frontend` — imagen sin assets (intencional pero no documentado) | Documentar explícitamente |

---

## DEPENDENCIAS — Issues (el más crítico: CVE en python-jose)

### [DEP-2] ⚠️ `python-jose==3.5.0` tiene CVE-2024-33664 — key confusion attack JWT
- **Archivo**: `requirements.txt`
- **Problema**: `python-jose` tiene vulnerabilidad de confusión de algoritmos en tokens JWT con clave EC. Hay dos librerías JWT instaladas simultáneamente: `python-jose==3.5.0` Y `PyJWT==2.10.1`. Si el código usa `PyJWT` (verificar con grep), `python-jose` es una dependencia muerta CON CVE conocido.
- **Fix inmediato**:
```bash
grep -rn "from jose\|import jose" sfce/
```
Si no hay resultados → eliminar `python-jose` de `requirements.txt`.

### [DEP-1] Nueve librerías PDF en producción — `PyPDF2` es dependencia muerta
- **Archivo**: `requirements.txt:49-56`
- `PyPDF2==3.0.1` y `pypdf` son el mismo paquete (renombrado). Solo `pypdf` se importa en el código.
- **Fix**: Eliminar `PyPDF2==3.0.1` de requirements.txt.

### [DEP-3] `passlib==1.7.4` — sin releases desde 2020, warnings en Python 3.12+
- Sin impacto inmediato, pero `bcrypt` está instalado directamente y podría usarse sin `passlib`.

### [DEP-4] `redis==6.4.0` instalado pero Redis no está en docker-compose de producción
- Si `fastapi-limiter` intenta conectar a Redis en startup → error. Verificar que no se inicializa automáticamente.

---

## HUECOS DE COBERTURA

### Módulos core sin tests directos (confirmado)
| Módulo | Riesgo |
|--------|--------|
| `sfce/core/ocr_mistral.py` | **Alto** — cliente HTTP externo, 0 tests de manejo de errores (429, timeout, JSON malformado) |
| `sfce/core/ocr_gemini.py` | **Alto** — tier 2 OCR, ídem |
| `sfce/core/fs_api.py` | **Alto** — interfaz con FacturaScripts, 0 tests de errores HTTP |
| `sfce/api/rutas/copilot.py` | **Medio** — sin tests |
| `sfce/api/rutas/informes.py` | **Medio** — sin tests directos |
| `sfce/api/rutas/configuracion.py` | **Medio** — sin tests |
| `sfce/api/rutas/gestor_mensajes.py` | **Medio** — sin tests |
| `sfce/core/prompts.py` | **Bajo** — string constants, bajo riesgo |

### Módulos con buena cobertura (en subdirectorios)
Tienen tests en `tests/test_gate0/`, `tests/test_bancario/`, `tests/test_correo/`, `tests/test_modelos_fiscales/`, `tests/test_seguridad/`, `tests/test_supplier_rules/`, `tests/test_onboarding/`, `tests/test_certificados_aapp/`.

---

## MÉTRICAS

| Métrica | Valor |
|---------|-------|
| Archivos de test | 236 (145 raíz + 91 en subdirectorios) |
| Tests reportados | 2565 (incluyendo parametrizados) |
| `StaticPool` correcto | Mayoría de tests de BD |
| `pytest.mark.parametrize` | 30 usos |
| `time.sleep` real en tests | 2 archivos |
| `assert status_code in (200, 404)` | 7 instancias |
| `datetime.utcnow()` en tests | 12 usos |
| `datetime.utcnow()` en producción | 25 usos |

---

## BIEN IMPLEMENTADO ✓

1. `StaticPool` usado correctamente en tests SQLite in-memory
2. Cobertura de dominios críticos: auth, pipeline, recovery, coherencia fiscal, gate0, modelos fiscales, conciliación bancaria
3. Tests parametrizados donde tiene sentido (30 usos)
4. CI/CD con orden correcto: test → build → deploy → smoke
5. Multi-stage Docker build
6. Smoke test post-deploy con loop de retries
7. Secrets correctamente referenciados en `${{ secrets.X }}`

---

## PRIORIDAD

### Fix inmediato
1. **DEP-2**: Verificar si `python-jose` se usa (`grep -rn "from jose" sfce/`) y eliminarlo si no
2. **TEST-8**: Añadir `--cov=sfce --cov-fail-under=75` al pytest de CI

### Próxima sesión
- **TEST-5**: Crear `tests/conftest.py` con `sesion_factory` y `client` compartidos
- **CI-4**: Añadir `timeout-minutes: 10` al job smoke-test
- **CI-5**: Añadir `npm run lint && npm run typecheck` en `build-frontend`
- **DOCKER-1**: Añadir usuario no-root en Dockerfile
- **DEP-1**: Eliminar `PyPDF2==3.0.1` de requirements.txt

### Backlog
- **TEST-1/7**: Tests analytics con datos reales
- **TEST-6**: `asyncio_mode = "auto"` en pyproject.toml
- **TEST-9**: Reemplazar `datetime.utcnow()` por `datetime.now(timezone.utc)` sistemáticamente
- **CI-1**: Renombrar imagen `spice` → `sfce`
- **CI-3**: Mover password de BD de CI a secret
