# Directorio de Empresas — Design Doc

**Fecha**: 2026-02-27
**Estado**: Aprobado

## Problema

Cada cliente tiene su propio `config.yaml` con proveedores/clientes duplicados. 83 entidades totales, 1 compartida (CaixaBank). Sin fuente centralizada, sin verificacion de CIF, sin reuso entre clientes.

## Decisiones

- **Scope**: por empresa (cada empresa tiene overlay con subcuenta, codimpuesto, regimen)
- **Enriquecimiento**: cache interno + AEAT (CIF espanol) + VIES (VAT europeo)
- **Fuente de verdad**: BD local (config.yaml se migra, BD es unica fuente)

## Enfoque: Tabla maestra + overlay (Enfoque C)

### Modelo de datos

**Nueva tabla `directorio_entidades`** (datos maestros globales):

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| id | Integer PK | Auto-increment |
| cif | String(20) UNIQUE | CIF/NIF/VAT normalizado. Nullable para clientes sin CIF |
| nombre | String(200) NOT NULL | Nombre oficial |
| nombre_comercial | String(200) | Nombre comercial (puede diferir) |
| aliases | JSON | Lista nombres alternativos (OCR, abreviaciones) |
| pais | String(3) | ISO 3166-1 alpha-3 (default ESP) |
| tipo_persona | String(10) | "fisica" / "juridica" |
| forma_juridica | String(20) | "sl", "sa", "autonomo", "comunidad"... |
| cnae | String(4) | Codigo actividad (nullable) |
| sector | String(50) | Clasificacion libre |
| validado_aeat | Boolean | CIF verificado via AEAT |
| validado_vies | Boolean | VAT verificado via VIES (UE) |
| fecha_alta | DateTime | Primer registro |
| fecha_actualizacion | DateTime | Ultima modificacion |
| datos_enriquecidos | JSON | Cache datos externos (AEAT, VIES) |

**Indice**: UNIQUE(cif) WHERE cif IS NOT NULL

**Tabla existente `proveedores_clientes`** (overlay empresa-especifico):
- Agregar FK `directorio_id -> directorio_entidades.id`
- Mantiene: empresa_id, tipo (proveedor/cliente), subcuenta_gasto, subcuenta_contrapartida, codimpuesto, regimen, retencion_pct, aliases (locales), activo
- `cif` pasa a ser derivado del directorio (redundante para busquedas rapidas)

**Relacion**: proveedores_clientes.directorio_id -> directorio_entidades.id (N:1)
Un mismo directorio_entidad puede tener multiples overlays (uno por empresa que lo usa).

### Flujo de alta de entidad nueva

```
OCR extrae CIF
  |
  v
Buscar en directorio_entidades (por CIF normalizado)
  |
  +-- ENCONTRADO --> buscar overlay para esta empresa
  |   +-- overlay EXISTE --> usar directamente
  |   +-- overlay NO EXISTE --> crear overlay con defaults del directorio
  |
  +-- NO ENCONTRADO --> crear en directorio
      +-- Cache: otro cliente tiene este CIF? copiar datos maestros
      +-- AEAT: verificar CIF espanol (nombre oficial, estado alta)
      +-- VIES: verificar VAT europeo (valid, nombre, direccion)
      +-- Crear overlay para esta empresa
```

Para clientes sin CIF (ej: "pacientes-fisioterapia"):
- directorio_entidades con cif=NULL, nombre="PACIENTES FISIOTERAPIA"
- Busqueda por nombre/aliases en vez de por CIF

### Adaptacion del pipeline

**ConfigCliente** cambia internamente para leer de BD:
- `buscar_proveedor_por_cif()` -> query BD: directorio JOIN overlay WHERE empresa_id AND tipo='proveedor'
- `buscar_proveedor_por_nombre()` -> query BD: aliases JSON contains
- `buscar_cliente_por_cif/nombre()` -> idem
- Interface publica NO cambia (mismos metodos, mismos returns)

**Migracion**:
- Script `scripts/migrar_config_a_bd.py`: lee todos los config.yaml, crea entradas en directorio + overlays
- config.yaml se mantiene como backup readonly (no se edita mas)
- Nuevas altas van directo a BD

### Servicios de verificacion

**AEAT** (CIF espanol):
- SOAP: `https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/titu/cont/es/wsidentificacion.wsdl`
- Gratis, sin API key, rate limit ~1 req/s
- Devuelve: nombre oficial, si esta de alta

**VIES** (VAT europeo):
- REST: `https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{country}/vat/{number}`
- Gratis, sin API key
- Devuelve: valid (bool), nombre, direccion

**Modulo**: `sfce/core/verificacion_fiscal.py`
- `verificar_cif_aeat(cif) -> {valido, nombre, datos}`
- `verificar_vat_vies(vat) -> {valido, nombre, direccion, pais}`
- Cache en campo `datos_enriquecidos` (JSON) del directorio
- Llamada lazy: solo al dar de alta o manualmente

### Exposicion en API/Dashboard

- Ruta nueva FastAPI: `/api/directorio/` (CRUD + busqueda fuzzy por nombre/CIF)
- Pagina nueva dashboard: "Directorio" (tabla con busqueda, filtros, detalle entidad con historial)
- Auto-complete en cuarentena: al resolver doc sin entidad, sugiere matches del directorio

### Compatibilidad

- `_asegurar_entidades_fs()` sigue creando entidades en FS, pero ahora lee de BD en vez de YAML
- `_descubrimiento_interactivo()` graba en BD en vez de YAML
- Motor de aprendizaje: patrones de resolucion referencian directorio_id

## No incluido (YAGNI)

- Datos de contacto (telefono, email)
- Condiciones de pago
- Cuentas bancarias
- APIs comerciales (Axesor, Infocif)
- Sincronizacion bidireccional BD<->YAML
