# Libro de Instrucciones — Onboarding Colaboradores

> **Publico:** Desarrolladores que se incorporan al proyecto SFCE/PROMETH-AI
> **Actualizado:** 2026-03-01

---

## Primer dia — Levantar el entorno

### Requisitos

- Python 3.11+
- Node.js 20+
- Git

### Pasos

1. Clonar el repo:
   ```bash
   git clone https://github.com/carlincarlichi78/SPICE.git
   cd SPICE
   ```

2. Configurar variables de entorno:
   ```bash
   cp .env.example .env  # o crear .env con las variables requeridas
   export $(grep -v '^#' .env | xargs)
   ```

   Variables minimas para desarrollo local:
   ```
   SFCE_JWT_SECRET=una-cadena-de-al-menos-32-caracteres-aqui
   SFCE_DB_TYPE=sqlite
   SFCE_CORS_ORIGINS=http://localhost:5173
   FS_API_TOKEN=iOXmrA1Bbn8RDWXLv91L
   MISTRAL_API_KEY=...
   OPENAI_API_KEY=...
   GEMINI_API_KEY=...
   ```

3. Instalar dependencias Python:
   ```bash
   pip install -r requirements.txt
   ```

4. Arrancar backend:
   ```bash
   cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000
   ```
   Nota en Windows: `--reload` puede fallar con WinError 6. Reiniciar manualmente tras cambios.

5. Instalar y arrancar frontend:
   ```bash
   cd dashboard && npm install && npm run dev
   ```

6. Acceder: http://localhost:5173 — login: `admin@sfce.local` / `admin`

### Correr tests

```bash
pytest tests/ -v                        # todos (1793+)
pytest tests/test_pipeline/             # solo pipeline
pytest tests/test_modelos_fiscales/     # solo modelos fiscales
pytest tests/ -k "bancario"             # por nombre
pytest tests/ --tb=short -q             # resumen rapido
```

---

## Convenciones de codigo

- **Idioma**: comentarios, variables y documentacion en espanol
- **Commits**: `feat/fix/refactor/docs/test/chore: descripcion en espanol`
- **Sin console.log**: usar el logger del proyecto (`sfce/core/logger.py`)
- **Sin secretos hardcodeados**: siempre variables de entorno
- **Inmutabilidad**: nunca mutar objetos/arrays directamente — crear nuevas copias
- **Archivos**: <400 lineas ideal, 800 max absoluto
- **Funciones**: <50 lineas, nesting maximo 4 niveles
- **TDD**: test primero (RED → GREEN → REFACTOR), cobertura minima 80%

## Flujo Git

```
main                  ← rama principal, siempre verde
feat/nombre-feature   ← branches para features nuevas
fix/nombre-fix        ← branches para bugs
```

- Commits atomicos: un commit por cambio logico, no mezclar
- Sin `--no-verify`
- Sin co-authored-by en commits

## Estructura del proyecto

```
sfce/
  api/          ← FastAPI: app.py, auth.py, rutas/
  core/         ← Logica de negocio: motor_reglas, backend, config, etc.
  db/           ← SQLAlchemy: modelos.py, modelos_auth.py, migraciones/
  phases/       ← Las 7 fases del pipeline
  modelos_fiscales/ ← 28 modelos BOE
  conectores/   ← bancario/, correo/
  normativa/    ← YAMLs normativos versionados
reglas/         ← YAMLs de reglas contables editables
dashboard/
  src/
    features/   ← Organizacion por feature (conciliacion/, pipeline/, etc.)
    components/ ← Componentes compartidos (shadcn/ui)
tests/          ← Espejo de sfce/: test_pipeline/, test_modelos_fiscales/, etc.
clientes/       ← config.yaml por cliente (NO en git: datos reales)
docs/
  LIBRO/        ← Este libro de instrucciones
  plans/        ← Documentos de diseno y decisiones arquitectonicas
```

---

## Lectura obligatoria antes de tocar codigo

### 1. Arquitectura del sistema

El sistema tiene una capa de abstraccion "dual backend" que escribe simultaneamente a FacturaScripts
(software contable externo via API REST) y a la BD local SQLite/PostgreSQL. Entender esto es critico
para no romper la sincronizacion.

→ [02 — Arquitectura General SFCE](_temas/02-sfce-arquitectura.md)

### 2. Infraestructura de produccion

Servidor Hetzner con Docker. FacturaScripts corre en contenedor propio — NO modificar ese contenedor.
Nginx como proxy. Firewall ufw + DOCKER-USER chain que bloquea puertos de BD del exterior.

→ [01 — Infraestructura](_temas/01-infraestructura.md)

### 3. El pipeline de 7 fases

Toda la logica de procesamiento de documentos pasa por aqui. Si tocas cualquier fase, debes entender
el flujo completo: como se pasan datos entre fases, que hace cada quality gate y que significa que
un documento vaya a cuarentena.

→ [03 — Pipeline: Las 7 Fases](_temas/03-pipeline-fases.md)

### 4. Motor de reglas contables

La logica de "a que cuenta va este gasto" esta aqui. Antes de modificar cualquier regla YAML o el
motor, leer como funciona la jerarquia de 6 niveles para no introducir regresiones silenciosas.

→ [06 — Motor de Reglas Contables](_temas/06-motor-reglas.md)

### 5. Sistema de reglas YAML

Los archivos en `reglas/` son editables sin tocar codigo Python. Este tema explica la sintaxis,
como funcionan los niveles de herencia y como probar cambios sin riesgo.

→ [07 — Sistema de Reglas YAML](_temas/07-sistema-reglas-yaml.md)

### 6. Base de datos: schema completo

29 tablas, migraciones numeradas. Antes de anadir una tabla nueva o modificar un modelo SQLAlchemy,
revisar las convenciones de nombres, relaciones existentes y el orden de migraciones.

→ [17 — Base de Datos: Las 29 Tablas](_temas/17-base-de-datos.md)

### 7. Seguridad

Auth JWT + 2FA, rate limiting, lockout, RGPD. Si tocas cualquier endpoint de auth o anyades rutas
nuevas, revisar el patron de verificacion `obtener_usuario_actual()` y la inyeccion de dependencias.
Un endpoint sin auth que deberia tenerla es una vulnerabilidad real.

→ [22 — Seguridad: Auth, Rate Limiting, RGPD y Cifrado](_temas/22-seguridad.md)

### 8. Clientes y configuracion

Cada cliente tiene un `config.yaml` que define su CIF, forma juridica, proveedores frecuentes,
subcuentas personalizadas y codejercicio FS. Muchos bugs de produccion han venido de este archivo.
Entender la diferencia entre `ejercicio` (ruta de archivos) y `codejercicio` (codigo FS) es critico.

→ [23 — Clientes y Configuracion](_temas/23-clientes.md)

---

## Gotchas criticos de la API FacturaScripts

Antes de escribir cualquier llamada a la API de FacturaScripts, leer este tema completo.
Los bugs mas costosos del proyecto han venido de no conocer estas restricciones:

- Los endpoints `crear*` requieren form-encoded, NO JSON
- Las lineas de factura van como JSON string dentro del form
- Los filtros de la API NO funcionan — siempre post-filtrar en Python
- `crearFacturaProveedor` genera asientos invertidos — hay que corregirlos despues
- El orden cronologico de facturas cliente es obligatorio o da 422
- Siempre pasar `codejercicio` explicitamente o FS asigna el ejercicio equivocado

→ [24 — FacturaScripts: API REST e Integracion](_temas/24-facturascripts.md)

---

## Temas adicionales de referencia

Una vez dominados los 8 temas obligatorios, estos son los mas consultados en el dia a dia:

- **API completa (66+ endpoints)** → [11 — API: Todos los Endpoints](_temas/11-api-endpoints.md)
- **WebSocket tiempo real** → [12 — WebSockets y Tiempo Real](_temas/12-websockets.md)
- **Dashboard 21 modulos** → [13 — Dashboard: Los 21 Modulos](_temas/13-dashboard-modulos.md)
- **Modelos fiscales BOE** → [15 — Modelos Fiscales](_temas/15-modelos-fiscales.md)
- **Bancario y conciliacion** → [19 — Modulo Bancario](_temas/19-bancario.md)
- **Decisiones de diseno pasadas** → [27 — Planes y Decisiones](_temas/27-planes-y-decisiones.md)
- **Que esta pendiente** → [28 — Roadmap y Estado del Sistema](_temas/28-roadmap.md)
