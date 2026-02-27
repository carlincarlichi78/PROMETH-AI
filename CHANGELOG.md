# CHANGELOG — Proyecto CONTABILIDAD

## 2026-02-27 — Sesion: SFCE v2 Fases B+C (motor central + BD)

**Objetivo**: Implementar Fases B y C del plan SFCE Evolucion v2.

**Fase B completada (Tasks 11-19)**:
- Clasificador contable cascada 6 niveles (`sfce/core/clasificador.py`)
- MotorReglas — cerebro del sistema, orquesta clasificador+normativa+perfil fiscal (`sfce/core/motor_reglas.py`)
- Integrado en registration.py, correction.py, asientos_directos.py y pipeline.py
- MotorReglas hecho OBLIGATORIO (sin fallback legacy)
- Calculador modelos fiscales 3 categorias: automaticos, semi-auto, asistidos (`sfce/core/calculador_modelos.py`)
- Procesador notas credito con busqueda factura original (`sfce/core/notas_credito.py`)
- 12 tests integracion end-to-end. 392 tests totales

**Fase C completada (Tasks 20-27)**:
- BD dual SQLite(WAL)/PostgreSQL via SQLAlchemy (`sfce/db/`)
- 14 tablas: empresas, proveedores_clientes, trabajadores, documentos, asientos, partidas, facturas, pagos, movimientos_bancarios, activos_fijos, operaciones_periodicas, cuarentena, audit_log, aprendizaje_log
- Repositorio con queries especializadas: saldo_subcuenta, PyG, balance, facturas_pendientes
- Backend doble destino FS+BD local con fallback si FS falla
- Importador CSV/Excel con auto-deteccion separador y formato europeo
- Exportador universal: libro diario CSV/Excel, facturas CSV, Excel multi-hoja
- Migrador FS→BD local (`scripts/migrar_fs_a_bd.py`)
- 12 tests integracion. 479 tests totales

**Tests totales**: 479 PASS
**Branch**: `feat/sfce-v2-fase-d` (D preparada, directorios creados)
**Progreso plan v2**: 27/46 tasks (59%)

---

## 2026-02-27 — Sesion: SPICE Landing Page (implementacion + deploy)

**Objetivo**: Implementar y desplegar landing page profesional de SPICE para presentar a gestoria.

**Trabajo realizado**:
- Scaffold React 19 + Vite 7 + Tailwind v4 + TypeScript en `spice-landing/`
- 17 componentes: Navbar, Hero, Problema, Vision, DiagramaPipeline, DiagramaOCR, TiposDocumento, DiagramaJerarquia, DiagramaClasificador, Trazabilidad, MapaTerritorios, DiagramaCiclo, ModelosFiscales, DiagramaAprendizaje, FormasJuridicas, Resultados, Footer
- 2 hooks (useInView, useCountUp), 6 archivos de datos
- Build: 280KB JS + 44KB CSS, 0 errores TS
- Deploy completo:
  - DNS: A record `spice.carloscanetegomez.dev` → 65.108.60.69 (Porkbun)
  - SSL: certbot Let's Encrypt
  - Nginx: `/opt/infra/nginx/conf.d/spice-landing.conf`
  - Archivos: `/opt/apps/spice-landing/`

**URL**: https://spice.carloscanetegomez.dev
**Commit**: 7f109e0 en `feat/sfce-v2-fase-b`
**Design**: `docs/plans/2026-02-27-spice-landing-design.md`
**Plan**: `docs/plans/2026-02-27-spice-landing-implementation.md`

---

## 2026-02-27 — Sesion: Implementacion Fase A SFCE v2

**Objetivo**: Implementar Tasks 1-10 de la evolucion SFCE v2 (Fase A: Fundamentos).

**Trabajo realizado**:
- T1: Paquete sfce/ con pyproject.toml, 14 core + 8 phases copiados, imports relativos corregidos
- T2: sfce/normativa/vigente.py + 2025.yaml — 5 territorios fiscales (peninsula, canarias IGIC, ceuta/melilla IPSI, navarra, pais vasco), SS, umbrales, plazos, amortizacion
- T3: sfce/core/perfil_fiscal.py — 11 formas juridicas, 5 territorios, 8 regimenes IVA, derivacion automatica modelos/libros
- T4: 3 YAMLs catalogos — regimenes_iva (8), regimenes_igic (5), perfiles_fiscales (11 plantillas)
- T5: ConfigCliente ampliado con PerfilFiscal + seccion trabajadores + busqueda por DNI
- T6: sfce/core/backend.py — abstraccion sobre fs_api con mocks limpios
- T7: sfce/core/decision.py — DecisionContable con trazabilidad, genera partidas multi-regimen (IVA parcial, recargo, ISP, retencion)
- T8: sfce/core/operaciones_periodicas.py — amortizacion lineal, provision pagas extras, regularizacion IVA con prorrata, periodificacion
- T9: sfce/core/cierre_ejercicio.py — regularizacion 6xx/7xx contra 129, gasto IS, cierre todas cuentas, apertura ejercicio nuevo
- T10: Tests integracion Fase A — 11 tests verificando conexion entre todos los modulos

**Tests**: 189 existentes + 114 nuevos = 303 total PASS
**Branch**: `feat/sfce-v2-fase-a` (10 commits)

---

## 2026-02-27 — Sesion: Revision y ampliacion plan SFCE Evolucion

**Objetivo**: Revisar plan v1 de evolucion SFCE antes de implementar. Identificar huecos y ampliar.

**Trabajo realizado**:
- Revision critica del design doc v1 y plan v1 (38 tasks)
- Identificados huecos: operaciones contables incompletas, territorios solo peninsula, BD sin audit trail, modelos fiscales todos como automaticos
- Discusion y aprobacion de 8 areas de mejora con el usuario
- Escrito design doc v2 (`sfce-evolucion-v2-design.md`, 1265 lineas, 28 secciones)
- Escrito plan implementacion v2 (`sfce-evolucion-v2-implementation.md`, 1453 lineas, 46 tasks)
- Actualizado CLAUDE.md con estado v2

**Decisiones tomadas**:
- Ciclo contable completo desde el principio (cierre, amortizaciones, provisiones, regularizacion IVA)
- 5 territorios fiscales (peninsula, canarias, ceuta_melilla, navarra, pais_vasco)
- 13 tablas BD con audit_log, pagos, movimientos_bancarios, activos_fijos
- Doble motor SQLite/PostgreSQL via SQLAlchemy
- Modelos fiscales en 3 categorias (automaticos/semi-auto/asistidos)
- Modelo 200 IS semi-automatico (borrador contable + gestor completa ajustes extracontables)
- Modelo 100 IRPF solo asistido (SFCE aporta rendimientos actividad, gestor hace en Renta Web)
- Provision pagas extras: configuracion por trabajador, no inferida. Deteccion automatica de trabajador nuevo via DNI en nomina
- Trazabilidad completa: log razonamiento JSON por cada asiento
- Cuarentena estructurada con 7 tipos y preguntas tipadas
- Sin Nuitka. Proteccion via OCR proxy + token + SaaS
- Claude Code siempre en la ecuacion (dashboard complementa)
- Nominas: OCR extrae importes ya calculados, no recalculamos SS/IRPF. Normativa sirve para validar coherencia

**Proxima sesion**: implementar Fase A (Tasks 1-10)
