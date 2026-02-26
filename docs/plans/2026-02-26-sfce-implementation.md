# SFCE — Plan de Implementacion

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Construir el Sistema de Fiabilidad Contable Evolutivo (SFCE): pipeline automatico de 7 fases con triple verificacion contra FacturaScripts, sistema de confianza y evolucion.

**Architecture:** Pipeline secuencial con Quality Gates. Cada fase es un modulo independiente orquestado por `pipeline.py`. Config por cliente en YAML. Catalogo de errores evolutivo en YAML. Score de confianza acumulativo.

**Tech Stack:** Python 3.10+, pdfplumber, openai (GPT-4o), pyyaml, requests, openpyxl, hashlib, logging

**Diseno de referencia:** `docs/plans/2026-02-26-sistema-fiabilidad-contable-design.md`

---

## Resumen de tareas

| # | Tarea | Archivos | Dependencia |
|---|-------|----------|-------------|
| 0 | **Onboarding interactivo** | `scripts/onboarding.py` | 3,6b |
| 1 | Core: Logger unificado | `scripts/core/logger.py` | - |
| 2 | Core: Cliente API FS | `scripts/core/fs_api.py` | 1 |
| 3 | Core: Cargador de config | `scripts/core/config.py` | 1 |
| 4 | Core: Sistema de confianza | `scripts/core/confidence.py` | 1 |
| 5 | Core: Catalogo de errores | `scripts/core/errors.py` | 1 |
| 6 | Reglas globales YAML | `reglas/*.yaml` | - |
| 6b | Catalogo tipos de entidad | `reglas/tipos_entidad.yaml` | - |
| 7 | Config Pastorino (con perfil) | `clientes/pastorino.../config.yaml` | 6,6b |
| 8 | Config Gerardo (con perfil) | `clientes/gerardo.../config.yaml` | 6,6b |
| 9 | Fase 0: Intake + descubrimiento | `scripts/phases/intake.py` | 2,3,4 |
| 10 | Fase 1: Validacion pre-FS | `scripts/phases/pre_validation.py` | 2,3,5 |
| 11 | Fase 2: Registro en FS | `scripts/phases/registration.py` | 2,3 |
| 12 | Fase 3: Generacion asientos | `scripts/phases/asientos.py` | 2 |
| 13 | Fase 4: Correccion automatica | `scripts/phases/correction.py` | 2,3,5 |
| 14 | Fase 5: Verificacion cruzada | `scripts/phases/cross_validation.py` | 2,3 |
| 15 | Fase 6: Generacion salidas | `scripts/phases/output.py` | 2,3 |
| 16 | Pipeline orquestador | `scripts/pipeline.py` | 0,9-15 |
| 17 | Integracion y .bat | `clientes/*/pipeline.bat` | 16 |

---

## Tarea 0: Onboarding interactivo de clientes

**Files:**
- Create: `scripts/onboarding.py`

Script interactivo que se ejecuta UNA VEZ al dar de alta un cliente nuevo.
Genera config.yaml completo con perfil de negocio, proveedores, clientes y reglas.

**Step 1: Implementar cuestionario interactivo**

El script hace preguntas por consola (input()) organizadas en secciones:

```
SECCION 1: DATOS BASICOS
  - Razon social
  - CIF/NIF
  - Direccion fiscal (calle, CP, ciudad, provincia)
  - Email, telefono
  - Tipo entidad → seleccionar de tipos_entidad.yaml
  - Banco (IBAN)

SECCION 2: ACTIVIDADES ECONOMICAS
  - ¿Cuantas actividades tiene? (1-N)
  - Por cada actividad:
    - Codigo IAE / CNAE
    - Descripcion
    - IVA aplicable a ventas (21%, 10%, 4%, exenta)
    - Notas especiales
  - Si >1 actividad con IVA diferente:
    - ¿Prorrata general o sectores diferenciados?

SECCION 3: REGIMEN FISCAL
  - Regimen IVA: general, simplificado, recargo equivalencia, exento
  - ¿Tiene retenciones IRPF? (para modelo 111)
  - ¿Tiene empleados? (para nominas/SS)
  - ¿Importa/exporta? ¿Desde/hacia donde?
  - ¿Divisas extranjeras habituales?

SECCION 4: PROVEEDORES CONOCIDOS
  - ¿Cuantos proveedores habituales? (0-N)
  - Por cada proveedor:
    - Nombre, CIF, pais, divisa
    - Regimen IVA (general, intracomunitario, extracomunitario)
    - Subcuenta contable (sugerir 600 por defecto)
    - ¿Alguna regla especial? (texto libre)

SECCION 5: CLIENTES CONOCIDOS
  - Igual que proveedores pero con subcuenta 430 y IVA de venta

SECCION 6: PARTICULARIDADES
  - Texto libre para documentar modelo de negocio
  - Notas especiales que el sistema debe saber
```

**Step 2: Generar config.yaml**

Con las respuestas, generar automaticamente:
- Seccion `empresa:` con datos basicos
- Seccion `perfil:` con actividades, modelo de negocio y particularidades
- Seccion `proveedores:` con todos los proveedores y sus reglas
- Seccion `clientes:` con todos los clientes
- Seccion `tipos_cambio:` si hay divisas extranjeras
- Seccion `tolerancias:` con valores por defecto

**Step 3: Crear estructura de carpetas**

Automaticamente crear:
```
clientes/{nombre-slug}/
  config.yaml          ← generado por onboarding
  inbox/               ← para soltar documentos
  cuarentena/          ← para documentos problematicos
  {ejercicio}/
    procesado/
      T1/ T2/ T3/ T4/  ← subcarpetas por trimestre
    auditoria/          ← logs del pipeline
    modelos_fiscales/   ← archivos .txt
```

**Step 4: Dar de alta empresa en FacturaScripts**

Via API:
1. Crear empresa en FS (POST /empresas)
2. Crear ejercicio contable
3. Importar PGC segun tipo (pymes, completo, sectorial)
4. Dar de alta proveedores conocidos (POST /proveedores + /contactos)
5. Dar de alta clientes conocidos (POST /clientes)

**Step 5: Generar .bat de onboarding**

```bat
@echo off
REM Onboarding nuevo cliente
cd /d "%~dp0"
python scripts/onboarding.py
pause
```

CLI:
```bash
python scripts/onboarding.py
python scripts/onboarding.py --desde-yaml plantilla.yaml  # para importar datos existentes
```

**Step 6: Commit**
```bash
git add scripts/onboarding.py
git commit -m "feat: onboarding interactivo para alta de clientes nuevos"
```

---

## Tarea 9 (ampliacion): Descubrimiento de entidades desconocidas

NOTA: Esta funcionalidad se integra en `scripts/phases/intake.py` (Tarea 9).
No es una tarea separada, sino una ampliacion de la Fase 0.

Cuando intake.py encuentra un CIF que NO esta en config.yaml:

```
FLUJO DE DESCUBRIMIENTO
========================

1. Extraer datos del PDF:
   nombre_emisor, cif_emisor, pais (inferido del CIF), importe, divisa

2. Verificar en config.yaml:
   - ¿CIF conocido como proveedor? → continuar normal
   - ¿CIF conocido como cliente? → continuar normal
   - ¿CIF == CIF de la empresa? → es factura emitida, buscar receptor
   - ¿CIF desconocido? → ACTIVAR DESCUBRIMIENTO

3. Guardar estado del pipeline (para --resume)

4. Presentar al usuario:
   "ENTIDAD DESCONOCIDA detectada en: [archivo.pdf]
    Nombre: [EMPRESA X]
    CIF: [B99999999]
    Pais: [España] (inferido)
    Importe factura: [1,500.00 EUR]

    ¿Que relacion tiene con [NOMBRE CLIENTE]?"

5. Preguntar:
   a) Tipo relacion: proveedor / acreedor / cliente / deudor
   b) Regimen IVA: general / intracomunitario / extracomunitario / exento
   c) Divisa habitual: EUR / USD / otra
   d) Subcuenta contable: sugerir segun tipo (600 prov, 410 acreedor, 430 cli, 440 deudor)
   e) ¿Tipo IVA en sus facturas? (21%, 10%, 4%, 0%, exento)
   f) ¿Alguna regla especial? (texto libre, opcional)

6. Automaticamente:
   - Anadir a config.yaml del cliente
   - Dar de alta en FS (POST /proveedores o /clientes + /contactos)
   - Continuar procesando la factura con la nueva config

7. Log de auditoria: "Nueva entidad registrada: [nombre] [CIF] como [tipo]"
```

Si el pipeline se ejecuta en modo no-interactivo (ej: scheduled task):
- Mover documento a cuarentena/
- Registrar en log: "CIF desconocido, requiere configuracion manual"
- Continuar con el resto de documentos

---

## Perfil de negocio en config.yaml

NOTA: No es una tarea separada. Se integra en Tareas 7 y 8 (config de cada cliente)
y en Tarea 0 (onboarding). La seccion `perfil:` se anade a config.yaml.

Estructura de la seccion perfil:

```yaml
perfil:
  descripcion: "Resumen en 1-2 frases del negocio del cliente"

  modelo_negocio: |
    Texto libre explicando como opera el negocio.
    Esto ayuda al sistema (y a Claude) a entender el contexto
    y tomar decisiones correctas sobre contabilizacion.

  actividades:
    - codigo: "4631"
      descripcion: "Comercio al por mayor de frutas"
      iva_venta: 4
      exenta: false
      notas: "Limones = alimento basico, IVA superreducido 4%"

    - codigo: "9602"          # ejemplo para Gerardo
      descripcion: "Estetica"
      iva_venta: 21
      exenta: false

    - codigo: "8690"          # ejemplo para Gerardo
      descripcion: "Podologia"
      iva_venta: 0
      exenta: true
      base_legal: "Art.20.1.3 LIVA - servicios sanitarios"

  prorrata:                   # solo si multiples actividades con IVA diferente
    tipo: sectores_diferenciados  # o prorrata_general
    criterio_reparto: "metros cuadrados"  # para gastos compartidos

  particularidades:
    - "Importaciones via Portugal generan IVA PT no deducible (modelo 360)"
    - "Facturas USD de Argentina requieren tipo de cambio"
    - "Maersk: IVA pendiente consulta asesor fiscal"

  empleados: false            # true si tiene nominas
  importador: true            # true si importa bienes
  exportador: false
  divisas_habituales: [USD]
```

El pipeline usa esta informacion para:
1. Saber que IVA aplicar a las ventas segun actividad
2. Detectar si una factura de gasto es compartida (necesita prorrata)
3. Alertar sobre particularidades documentadas
4. Generar los modelos fiscales correctos

---

## Tarea 1: Core — Logger unificado

**Files:**
- Create: `scripts/core/__init__.py`
- Create: `scripts/core/logger.py`

**Step 1: Crear modulo core**

```python
# scripts/core/__init__.py
"""Core del Sistema de Fiabilidad Contable Evolutivo (SFCE)."""
```

**Step 2: Implementar logger**

```python
# scripts/core/logger.py
"""Logger unificado para SFCE con salida a consola y archivo."""
import logging
import sys
from pathlib import Path
from datetime import datetime


def crear_logger(nombre: str, ruta_log: Path = None, nivel: int = logging.INFO) -> logging.Logger:
    """Crea logger con formato consistente para consola + archivo.

    Args:
        nombre: nombre del logger (ej: 'pipeline', 'intake')
        ruta_log: ruta al archivo .log (si None, solo consola)
        nivel: nivel de logging (default INFO)

    Returns:
        Logger configurado con handlers consola + archivo
    """
    logger = logging.getLogger(f"sfce.{nombre}")
    logger.setLevel(nivel)

    # Evitar duplicar handlers si se llama multiples veces
    if logger.handlers:
        return logger

    formato = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Consola
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(nivel)
    ch.setFormatter(formato)
    logger.addHandler(ch)

    # Archivo (si se especifica ruta)
    if ruta_log:
        ruta_log.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(ruta_log, encoding="utf-8")
        fh.setLevel(logging.DEBUG)  # Archivo siempre DEBUG
        fh.setFormatter(formato)
        logger.addHandler(fh)

    return logger


class AuditoriaLogger:
    """Registra cada accion del pipeline para auditoria."""

    def __init__(self, ruta_auditoria: Path):
        self.ruta = ruta_auditoria
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.registros = []
        self.inicio = datetime.now()

    def registrar(self, fase: str, tipo: str, detalle: str, datos: dict = None):
        """Registra una accion/verificacion/error."""
        registro = {
            "timestamp": datetime.now().isoformat(),
            "fase": fase,
            "tipo": tipo,  # "verificacion", "correccion", "error", "info"
            "detalle": detalle,
            "datos": datos or {}
        }
        self.registros.append(registro)

    def guardar(self):
        """Guarda la auditoria como JSON."""
        import json
        resultado = {
            "inicio": self.inicio.isoformat(),
            "fin": datetime.now().isoformat(),
            "total_registros": len(self.registros),
            "registros": self.registros
        }
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)

    def resumen(self) -> dict:
        """Devuelve resumen de la auditoria."""
        por_tipo = {}
        for r in self.registros:
            por_tipo[r["tipo"]] = por_tipo.get(r["tipo"], 0) + 1
        return {
            "total": len(self.registros),
            "por_tipo": por_tipo,
            "errores": [r for r in self.registros if r["tipo"] == "error"]
        }
```

**Step 3: Commit**
```bash
git add scripts/core/
git commit -m "feat: core logger unificado con auditoria"
```

---

## Tarea 2: Core — Cliente API FacturaScripts

**Files:**
- Create: `scripts/core/fs_api.py`

Consolidar las 5 copias de `api_get()` que existen en los scripts actuales en un unico cliente robusto.

**Step 1: Implementar cliente API**

```python
# scripts/core/fs_api.py
"""Cliente unificado para la API REST de FacturaScripts."""
import os
import time
import requests
from typing import Any
from .logger import crear_logger

API_BASE = "https://contabilidad.lemonfresh-tuc.com/api/3"
TOKEN_FALLBACK = "iOXmrA1Bbn8RDWXLv91L"

logger = crear_logger("fs_api")


def obtener_token() -> str:
    """Obtiene token de variable de entorno o fallback."""
    return os.environ.get("FS_API_TOKEN", TOKEN_FALLBACK)


def api_get(endpoint: str, params: dict = None, token: str = None,
            limit: int = 200) -> list:
    """GET con paginacion automatica.

    Args:
        endpoint: nombre del endpoint (ej: 'facturaproveedores')
        params: parametros adicionales (idempresa, codejercicio, etc.)
        token: token de autenticacion (si None, usa obtener_token())
        limit: tamano de pagina

    Returns:
        Lista completa de registros (paginados automaticamente)
    """
    token = token or obtener_token()
    headers = {"Token": token}
    todos = []
    p = dict(params or {})
    p["limit"] = limit
    p["offset"] = 0

    while True:
        url = f"{API_BASE}/{endpoint}"
        resp = requests.get(url, headers=headers, params=p, timeout=30)
        resp.raise_for_status()
        lote = resp.json()

        if not lote:
            break

        todos.extend(lote)

        if len(lote) < limit:
            break

        p["offset"] += limit

    return todos


def api_post(endpoint: str, data: dict, token: str = None) -> dict:
    """POST form-encoded a la API.

    Returns:
        Respuesta JSON del servidor
    """
    token = token or obtener_token()
    headers = {"Token": token}
    url = f"{API_BASE}/{endpoint}"
    resp = requests.post(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_put(endpoint: str, data: dict, token: str = None) -> dict:
    """PUT form-encoded a la API.

    Returns:
        Respuesta JSON del servidor
    """
    token = token or obtener_token()
    headers = {"Token": token}
    url = f"{API_BASE}/{endpoint}"
    resp = requests.put(url, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_delete(endpoint: str, token: str = None) -> bool:
    """DELETE a la API.

    Returns:
        True si se elimino correctamente
    """
    token = token or obtener_token()
    headers = {"Token": token}
    url = f"{API_BASE}/{endpoint}"
    resp = requests.delete(url, headers=headers, timeout=30)
    return resp.status_code == 200


def verificar_factura(idfactura: int, tipo: str = "proveedor",
                      token: str = None) -> dict:
    """GET una factura especifica y devuelve sus datos.

    Args:
        idfactura: ID de la factura en FS
        tipo: 'proveedor' o 'cliente'

    Returns:
        dict con datos de la factura
    """
    endpoint_map = {
        "proveedor": "facturaproveedores",
        "cliente": "facturaclientes"
    }
    endpoint = f"{endpoint_map[tipo]}/{idfactura}"
    token = token or obtener_token()
    headers = {"Token": token}
    url = f"{API_BASE}/{endpoint}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


# === Funciones de utilidad de datos ===

def normalizar_fecha(fecha_str: str) -> str:
    """Convierte DD-MM-YYYY a YYYY-MM-DD para comparacion."""
    if not fecha_str:
        return ""
    partes = fecha_str.strip().split("-")
    if len(partes) == 3 and len(partes[0]) == 2:
        return f"{partes[2]}-{partes[1]}-{partes[0]}"
    return fecha_str


def convertir_a_eur(importe: float, tasaconv: float, divisa: str) -> float:
    """Convierte importe de divisa original a EUR.

    Args:
        importe: importe en divisa original
        tasaconv: tipo de cambio (1 EUR = X divisa)
        divisa: codigo divisa (EUR, USD, etc.)

    Returns:
        Importe en EUR (redondeado a 2 decimales)
    """
    if divisa == "EUR" or tasaconv in (0, 1, None):
        return round(importe, 2)
    return round(importe / tasaconv, 2)


def calcular_trimestre(fecha_str: str) -> str:
    """Determina trimestre de una fecha DD-MM-YYYY o YYYY-MM-DD."""
    fecha_norm = normalizar_fecha(fecha_str)
    mes = int(fecha_norm.split("-")[1])
    if mes <= 3:
        return "T1"
    elif mes <= 6:
        return "T2"
    elif mes <= 9:
        return "T3"
    return "T4"
```

**Step 2: Commit**
```bash
git add scripts/core/fs_api.py
git commit -m "feat: cliente API FS unificado con paginacion y utilidades"
```

---

## Tarea 3: Core — Cargador de configuracion

**Files:**
- Create: `scripts/core/config.py`

**Step 1: Implementar cargador y validador de config.yaml**

```python
# scripts/core/config.py
"""Cargador y validador de configuracion por cliente."""
import yaml
from pathlib import Path
from typing import Optional
from .logger import crear_logger

logger = crear_logger("config")

# Campos obligatorios por seccion
CAMPOS_EMPRESA = {"nombre", "cif", "tipo", "idempresa", "ejercicio_activo"}
CAMPOS_PROVEEDOR = {"cif", "nombre_fs", "pais", "divisa", "subcuenta", "codimpuesto", "regimen"}
CAMPOS_CLIENTE = {"cif", "nombre_fs", "pais", "divisa", "codimpuesto", "regimen"}
TIPOS_EMPRESA = {"sl", "autonomo"}
REGIMENES = {"general", "intracomunitario", "extracomunitario"}
DIVISAS = {"EUR", "USD", "GBP"}
PAISES_UE = {
    "AUT", "BEL", "BGR", "CYP", "CZE", "DEU", "DNK", "ESP", "EST",
    "FIN", "FRA", "GRC", "HRV", "HUN", "IRL", "ITA", "LTU", "LUX",
    "LVA", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "SWE"
}


class ConfigCliente:
    """Configuracion cargada y validada de un cliente."""

    def __init__(self, data: dict, ruta: Path):
        self.data = data
        self.ruta = ruta
        self.empresa = data.get("empresa", {})
        self.proveedores = data.get("proveedores", {})
        self.clientes = data.get("clientes", {})
        self.tipos_cambio = data.get("tipos_cambio", {})
        self.tolerancias = data.get("tolerancias", {
            "cuadre_asiento": 0.01,
            "comparacion_importes": 0.02,
            "confianza_minima": 85
        })

    @property
    def nombre(self) -> str:
        return self.empresa.get("nombre", "")

    @property
    def cif(self) -> str:
        return self.empresa.get("cif", "")

    @property
    def tipo(self) -> str:
        return self.empresa.get("tipo", "sl")

    @property
    def idempresa(self) -> int:
        return self.empresa.get("idempresa", 1)

    @property
    def ejercicio(self) -> str:
        return self.empresa.get("ejercicio_activo", "2025")

    def buscar_proveedor_por_cif(self, cif: str) -> Optional[dict]:
        """Busca proveedor en config por CIF."""
        for nombre, datos in self.proveedores.items():
            if datos.get("cif", "").upper() == cif.upper():
                return {**datos, "_nombre_corto": nombre}
        return None

    def buscar_proveedor_por_nombre(self, nombre: str) -> Optional[dict]:
        """Busca proveedor por nombre o aliases."""
        nombre_upper = nombre.upper()
        for clave, datos in self.proveedores.items():
            if clave.upper() == nombre_upper:
                return {**datos, "_nombre_corto": clave}
            if datos.get("nombre_fs", "").upper() == nombre_upper:
                return {**datos, "_nombre_corto": clave}
            for alias in datos.get("aliases", []):
                if alias.upper() == nombre_upper:
                    return {**datos, "_nombre_corto": clave}
        return None

    def buscar_cliente_por_cif(self, cif: str) -> Optional[dict]:
        """Busca cliente en config por CIF."""
        for nombre, datos in self.clientes.items():
            if datos.get("cif", "").upper() == cif.upper():
                return {**datos, "_nombre_corto": nombre}
        return None

    def es_intracomunitario(self, nombre_prov: str) -> bool:
        """Verifica si proveedor es intracomunitario."""
        for clave, datos in self.proveedores.items():
            if clave.upper() == nombre_prov.upper():
                return datos.get("regimen") == "intracomunitario"
        return False

    def tiene_autoliquidacion(self, nombre_prov: str) -> bool:
        """Verifica si proveedor requiere autoliquidacion."""
        for clave, datos in self.proveedores.items():
            if clave.upper() == nombre_prov.upper():
                return "autoliquidacion" in datos
        return False

    def reglas_especiales(self, nombre_prov: str) -> list:
        """Devuelve reglas especiales del proveedor."""
        for clave, datos in self.proveedores.items():
            if clave.upper() == nombre_prov.upper():
                return datos.get("reglas_especiales", [])
        return []

    def tc_defecto(self, divisa: str) -> float:
        """Devuelve tipo de cambio por defecto para una divisa."""
        clave = f"{divisa}_EUR"
        return self.tipos_cambio.get(clave, 1.0)


def cargar_config(ruta_cliente: Path) -> ConfigCliente:
    """Carga y valida config.yaml de un cliente.

    Args:
        ruta_cliente: ruta a la carpeta del cliente

    Returns:
        ConfigCliente validado

    Raises:
        FileNotFoundError: si no existe config.yaml
        ValueError: si la config tiene errores de validacion
    """
    ruta_config = ruta_cliente / "config.yaml"

    if not ruta_config.exists():
        raise FileNotFoundError(f"No existe {ruta_config}")

    with open(ruta_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    errores = validar_config(data)
    if errores:
        for e in errores:
            logger.error(f"Config invalida: {e}")
        raise ValueError(f"Config {ruta_config} tiene {len(errores)} errores")

    logger.info(f"Config cargada: {data['empresa']['nombre']}")
    return ConfigCliente(data, ruta_config)


def validar_config(data: dict) -> list[str]:
    """Valida estructura y contenido del config.yaml.

    Returns:
        Lista de errores (vacia si todo OK)
    """
    errores = []

    # Empresa
    if "empresa" not in data:
        errores.append("Falta seccion 'empresa'")
        return errores

    empresa = data["empresa"]
    faltantes = CAMPOS_EMPRESA - set(empresa.keys())
    if faltantes:
        errores.append(f"Empresa: faltan campos {faltantes}")

    if empresa.get("tipo") not in TIPOS_EMPRESA:
        errores.append(f"Empresa: tipo '{empresa.get('tipo')}' no valido. Usar: {TIPOS_EMPRESA}")

    # Proveedores
    for nombre, prov in data.get("proveedores", {}).items():
        faltantes = CAMPOS_PROVEEDOR - set(prov.keys())
        if faltantes:
            errores.append(f"Proveedor {nombre}: faltan campos {faltantes}")

        if prov.get("regimen") not in REGIMENES:
            errores.append(f"Proveedor {nombre}: regimen '{prov.get('regimen')}' no valido")

        if prov.get("divisa") not in DIVISAS:
            errores.append(f"Proveedor {nombre}: divisa '{prov.get('divisa')}' no valida")

        if prov.get("regimen") == "intracomunitario" and prov.get("pais") not in PAISES_UE:
            errores.append(f"Proveedor {nombre}: pais '{prov.get('pais')}' no es UE pero regimen es intracomunitario")

        # Autoliquidacion solo si intracomunitario
        if "autoliquidacion" in prov and prov.get("regimen") != "intracomunitario":
            errores.append(f"Proveedor {nombre}: autoliquidacion solo aplica a intracomunitarios")

    # Clientes
    for nombre, cli in data.get("clientes", {}).items():
        faltantes = CAMPOS_CLIENTE - set(cli.keys())
        if faltantes:
            errores.append(f"Cliente {nombre}: faltan campos {faltantes}")

    return errores
```

**Step 2: Commit**
```bash
git add scripts/core/config.py
git commit -m "feat: cargador y validador de config.yaml por cliente"
```

---

## Tarea 4: Core — Sistema de confianza

**Files:**
- Create: `scripts/core/confidence.py`

**Step 1: Implementar sistema de puntuacion de confianza**

Clave: cada dato extraido recibe puntos de multiples fuentes. Si las fuentes coinciden, sube la confianza. Si discrepan, baja.

```python
# scripts/core/confidence.py
"""Sistema de puntuacion de confianza para datos extraidos."""
from dataclasses import dataclass, field
from typing import Optional


UMBRALES = {
    "cif": 90,
    "importe": 85,
    "fecha": 85,
    "numero_factura": 80,
    "tipo_iva": 90,
    "divisa": 95,
}

PESOS_FUENTE = {
    "pdfplumber": 40,    # Extraccion deterministica de texto
    "gpt": 30,           # Parsing LLM del texto
    "config": 10,        # Coincide con config.yaml esperado
    "fs_api": 20,        # Coincide con dato en FS (si existe)
}


@dataclass
class DatoConConfianza:
    """Un dato con su puntuacion de confianza."""
    campo: str
    valor: any
    confianza: int = 0
    fuentes: dict = field(default_factory=dict)  # fuente -> valor extraido

    def agregar_fuente(self, fuente: str, valor):
        """Agrega una fuente de extraccion."""
        self.fuentes[fuente] = valor
        self._recalcular()

    def _recalcular(self):
        """Recalcula confianza basada en coincidencia de fuentes."""
        if not self.fuentes:
            self.confianza = 0
            return

        # Valor de referencia = el mas comun o el de mayor peso
        valores_str = {k: str(v) for k, v in self.fuentes.items()}

        # Si solo hay una fuente
        if len(self.fuentes) == 1:
            fuente = list(self.fuentes.keys())[0]
            self.confianza = PESOS_FUENTE.get(fuente, 25)
            self.valor = list(self.fuentes.values())[0]
            return

        # Multiples fuentes: sumar pesos de las que coinciden
        self.confianza = 0
        valor_ref = None
        max_peso = 0

        for fuente, val in self.fuentes.items():
            peso = PESOS_FUENTE.get(fuente, 10)
            if peso > max_peso:
                max_peso = peso
                valor_ref = val

        self.valor = valor_ref

        for fuente, val in self.fuentes.items():
            peso = PESOS_FUENTE.get(fuente, 10)
            if self._valores_coinciden(val, valor_ref):
                self.confianza += peso
            else:
                # Fuente discrepante: resta la mitad de su peso
                self.confianza -= peso // 2

        self.confianza = max(0, min(100, self.confianza))

    @staticmethod
    def _valores_coinciden(v1, v2) -> bool:
        """Compara valores con tolerancia para numeros."""
        if v1 is None or v2 is None:
            return v1 == v2
        try:
            f1, f2 = float(v1), float(v2)
            return abs(f1 - f2) < 0.02
        except (ValueError, TypeError):
            return str(v1).strip().upper() == str(v2).strip().upper()

    def pasa_umbral(self) -> bool:
        """Verifica si supera el umbral minimo para este campo."""
        umbral = UMBRALES.get(self.campo, 85)
        return self.confianza >= umbral


@dataclass
class DocumentoConfianza:
    """Resultado de extraccion de un documento con confianzas."""
    archivo: str
    hash_sha256: str
    tipo: str = ""  # FC, FV, NC, ANT, etc.
    datos: dict = field(default_factory=dict)  # campo -> DatoConConfianza

    def agregar_dato(self, campo: str, fuente: str, valor):
        """Agrega un dato de una fuente."""
        if campo not in self.datos:
            self.datos[campo] = DatoConConfianza(campo=campo, valor=valor)
        self.datos[campo].agregar_fuente(fuente, valor)

    def confianza_global(self) -> int:
        """Calcula confianza promedio ponderada del documento."""
        if not self.datos:
            return 0

        campos_criticos = {"cif", "importe", "fecha", "numero_factura"}
        total_peso = 0
        total_confianza = 0

        for campo, dato in self.datos.items():
            peso = 3 if campo in campos_criticos else 1
            total_peso += peso
            total_confianza += dato.confianza * peso

        return round(total_confianza / total_peso) if total_peso > 0 else 0

    def campos_bajo_umbral(self) -> list[str]:
        """Devuelve campos que no pasan su umbral."""
        return [c for c, d in self.datos.items() if not d.pasa_umbral()]

    def es_fiable(self) -> bool:
        """True si todos los campos criticos pasan umbral."""
        criticos = {"cif", "importe", "fecha"}
        for campo in criticos:
            if campo in self.datos and not self.datos[campo].pasa_umbral():
                return False
        return self.confianza_global() >= 85


def calcular_nivel(score: int) -> str:
    """Devuelve nivel de fiabilidad."""
    if score >= 95:
        return "FIABLE"
    elif score >= 85:
        return "ACEPTABLE"
    return "NO_FIABLE"
```

**Step 2: Commit**
```bash
git add scripts/core/confidence.py
git commit -m "feat: sistema de puntuacion de confianza multicapa"
```

---

## Tarea 5: Core — Catalogo de errores evolutivo

**Files:**
- Create: `scripts/core/errors.py`

**Step 1: Implementar catalogo de errores**

```python
# scripts/core/errors.py
"""Catalogo evolutivo de errores conocidos."""
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional
from .logger import crear_logger

logger = crear_logger("errors")


class CatalogoErrores:
    """Gestiona el catalogo de errores conocidos (YAML)."""

    def __init__(self, ruta_yaml: Path):
        self.ruta = ruta_yaml
        self.errores = []
        self._cargar()

    def _cargar(self):
        """Carga errores desde YAML."""
        if self.ruta.exists():
            with open(self.ruta, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self.errores = data.get("errores", [])
        else:
            self.errores = []

    def guardar(self):
        """Guarda catalogo actualizado."""
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        data = {"errores": self.errores, "actualizado": datetime.now().isoformat()}
        with open(self.ruta, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def buscar(self, tipo: str, condicion_extra: dict = None) -> Optional[dict]:
        """Busca un error conocido por tipo."""
        for error in self.errores:
            if error.get("tipo") == tipo:
                if condicion_extra:
                    deteccion = error.get("deteccion", {})
                    if all(deteccion.get(k) == v for k, v in condicion_extra.items()):
                        return error
                else:
                    return error
        return None

    def registrar_ocurrencia(self, error_id: str):
        """Incrementa contador de ocurrencias de un error."""
        for error in self.errores:
            if error.get("id") == error_id:
                error["ocurrencias"] = error.get("ocurrencias", 0) + 1
                error["ultima_ocurrencia"] = datetime.now().isoformat()
                self.guardar()
                return

    def agregar_error(self, tipo: str, descripcion: str, deteccion: dict,
                      correccion: dict = None, cliente: str = "todos") -> str:
        """Agrega un nuevo error al catalogo.

        Returns:
            ID del error creado
        """
        nuevo_id = f"ERR{len(self.errores) + 1:03d}"
        nuevo = {
            "id": nuevo_id,
            "descubierto": datetime.now().strftime("%Y-%m-%d"),
            "cliente": cliente,
            "tipo": tipo,
            "descripcion": descripcion,
            "deteccion": deteccion,
            "correccion": correccion or {"automatica": False},
            "aplicable_a": cliente,
            "ocurrencias": 1,
            "ultima_ocurrencia": datetime.now().isoformat()
        }
        self.errores.append(nuevo)
        self.guardar()
        logger.info(f"Nuevo error registrado: {nuevo_id} - {descripcion}")
        return nuevo_id

    def es_auto_corregible(self, error_id: str) -> bool:
        """Verifica si un error tiene correccion automatica."""
        for error in self.errores:
            if error.get("id") == error_id:
                return error.get("correccion", {}).get("automatica", False)
        return False


class ResultadoFase:
    """Resultado de ejecutar una fase del pipeline."""

    def __init__(self, fase: str):
        self.fase = fase
        self.exitoso = True
        self.errores = []      # Errores bloqueantes
        self.avisos = []       # Avisos no bloqueantes
        self.correcciones = [] # Correcciones auto-aplicadas
        self.datos = {}        # Datos de salida de la fase

    def error(self, mensaje: str, datos: dict = None):
        """Registra error bloqueante."""
        self.exitoso = False
        self.errores.append({"mensaje": mensaje, "datos": datos or {}})

    def aviso(self, mensaje: str, datos: dict = None):
        """Registra aviso no bloqueante."""
        self.avisos.append({"mensaje": mensaje, "datos": datos or {}})

    def correccion(self, mensaje: str, datos: dict = None):
        """Registra correccion auto-aplicada."""
        self.correcciones.append({"mensaje": mensaje, "datos": datos or {}})

    def resumen(self) -> str:
        """Resumen legible del resultado."""
        estado = "OK" if self.exitoso else "FALLO"
        partes = [f"[{estado}] Fase {self.fase}"]
        if self.errores:
            partes.append(f"  {len(self.errores)} errores")
        if self.correcciones:
            partes.append(f"  {len(self.correcciones)} correcciones auto-aplicadas")
        if self.avisos:
            partes.append(f"  {len(self.avisos)} avisos")
        return " | ".join(partes)
```

**Step 2: Commit**
```bash
git add scripts/core/errors.py
git commit -m "feat: catalogo evolutivo de errores + ResultadoFase"
```

---

## Tarea 6: Reglas globales YAML

**Files:**
- Create: `reglas/validaciones.yaml`
- Create: `reglas/errores_conocidos.yaml`

**Step 1: Crear reglas de validacion globales**

```yaml
# reglas/validaciones.yaml
# Reglas de validacion para TODOS los clientes SFCE

validaciones_pre_fs:
  - nombre: "CIF formato valido"
    campo: cif
    severidad: error
    descripcion: "CIF/NIF debe tener formato valido (letra+8digitos o 8digitos+letra)"

  - nombre: "Fecha en ejercicio"
    campo: fecha
    severidad: error
    descripcion: "Fecha de factura debe estar dentro del ejercicio activo"

  - nombre: "Base + IVA = Total"
    severidad: error
    tolerancia: 0.02
    descripcion: "La suma de base imponible + cuota IVA debe igualar el total"

  - nombre: "Importe positivo"
    campo: importe
    severidad: error
    excepciones: ["NC"]
    descripcion: "El importe total debe ser positivo (excepto notas de credito)"

  - nombre: "No duplicado"
    severidad: error
    descripcion: "No puede existir otra factura con mismo numero+proveedor+fecha"

validaciones_post_asiento:
  - nombre: "Cuadre DEBE=HABER"
    severidad: error
    auto_fix: false
    descripcion: "La suma de DEBE debe igualar la suma de HABER en cada asiento"

  - nombre: "Importes en EUR"
    severidad: error
    auto_fix: true
    descripcion: "Partidas de asientos USD deben convertirse a EUR"

  - nombre: "NC invertida"
    severidad: error
    auto_fix: true
    descripcion: "Notas de credito serie R deben tener DEBE/HABER invertidos"

  - nombre: "Autoliquidacion intracomunitaria"
    severidad: error
    auto_fix: true
    descripcion: "Facturas intracomunitarias necesitan partidas 472/477"

  - nombre: "Reglas especiales proveedor"
    severidad: error
    auto_fix: true
    descripcion: "Aplicar reglas de reclasificacion definidas en config (ej: IVA PT)"

validaciones_cruce:
  - nombre: "Facturas == Asientos"
    severidad: error
    descripcion: "Numero de facturas debe igualar numero de asientos"

  - nombre: "Gastos vs subcuenta 600"
    severidad: error
    tolerancia: 0.01
    descripcion: "Total base facturas proveedor = 600 neto + 4709"

  - nombre: "Ingresos vs subcuenta 700"
    severidad: error
    tolerancia: 0.01
    descripcion: "Total base facturas cliente = subcuenta 700 HABER"

  - nombre: "IVA repercutido vs 477"
    severidad: error
    tolerancia: 0.01
    descripcion: "IVA repercutido facturas + autoliq = subcuenta 477 HABER"

  - nombre: "IVA soportado vs 472"
    severidad: error
    tolerancia: 0.01
    descripcion: "IVA soportado facturas + autoliq = subcuenta 472 DEBE"

  - nombre: "Autoliquidacion equilibrada"
    severidad: error
    tolerancia: 0.01
    descripcion: "Autoliquidacion en 472 debe igualar autoliquidacion en 477"

  - nombre: "Libro diario cuadra"
    severidad: error
    tolerancia: 0.01
    descripcion: "Suma global DEBE == suma global HABER en libro diario"
```

**Step 2: Crear catalogo inicial de errores conocidos (basado en historial)**

```yaml
# reglas/errores_conocidos.yaml
# Catalogo evolutivo de errores - se actualiza automaticamente

errores:
  - id: ERR001
    descubierto: "2026-02-25"
    tipo: divisa_sin_convertir
    descripcion: "FS genera asientos con importes en divisa original (USD) en vez de EUR"
    deteccion:
      fase: post_asiento
      condicion: "factura.divisa != EUR AND partida.importe ~= factura.total_original"
    correccion:
      automatica: true
      accion: "PUT partida con importe = total / tasaconv"
    verificacion: "abs(sum_debe - sum_haber) < 0.01 AND partida.importe ~= total_eur"
    aplicable_a: todos
    ocurrencias: 10

  - id: ERR002
    descubierto: "2026-02-26"
    tipo: nc_sin_invertir
    descripcion: "FS genera asientos de NC serie R sin invertir DEBE/HABER"
    deteccion:
      fase: post_asiento
      condicion: "factura.serie == R AND subcuenta_400.haber > 0"
    correccion:
      automatica: true
      accion: "swap(partida.debe, partida.haber) para todas las partidas del asiento"
    verificacion: "subcuenta_400.debe > 0 AND subcuenta_600.haber > 0"
    aplicable_a: todos
    ocurrencias: 2

  - id: ERR003
    descubierto: "2026-02-25"
    tipo: iva_extranjero_cuenta_incorrecta
    descripcion: "IVA portugues en cuenta 600 (gasto) en vez de 4709 (HP deudora)"
    deteccion:
      fase: post_asiento
      condicion: "linea.descripcion CONTAINS patron_linea AND partida.subcuenta == 600"
    correccion:
      automatica: true
      accion: "reclasificar partida de subcuenta 600 a 4709"
    verificacion: "no existe partida 600 con concepto IVA ADUANA"
    aplicable_a: todos
    ocurrencias: 3

  - id: ERR004
    descubierto: "2026-02-25"
    tipo: autoliq_intracom_faltante
    descripcion: "FS no genera autoliquidacion para facturas intracomunitarias"
    deteccion:
      fase: post_asiento
      condicion: "proveedor.regimen == intracomunitario AND (no existe 472 o no existe 477)"
    correccion:
      automatica: true
      accion: "crear partida 472 DEBE y 477 HABER con base * iva%"
    verificacion: "existe 472.debe == base*iva% AND existe 477.haber == base*iva%"
    aplicable_a: todos
    ocurrencias: 3

  - id: ERR005
    descubierto: "2026-02-25"
    tipo: api_form_encoded
    descripcion: "Endpoints crear* requieren form-encoded, no JSON"
    deteccion:
      fase: registro
      condicion: "API devuelve 400 con content-type application/json"
    correccion:
      automatica: true
      accion: "usar data= en vez de json= en requests.post"
    aplicable_a: todos
    ocurrencias: 0

  - id: ERR006
    descubierto: "2026-02-25"
    tipo: lineas_json_string
    descripcion: "Campo lineas debe ser JSON string, no array Python"
    deteccion:
      fase: registro
      condicion: "API ignora lineas pasadas como array"
    correccion:
      automatica: true
      accion: "envolver lineas con json.dumps()"
    aplicable_a: todos
    ocurrencias: 0
```

**Step 3: Commit**
```bash
git add reglas/
git commit -m "feat: reglas globales de validacion + catalogo errores iniciales"
```

---

## Tarea 6b: Catalogo de tipos de entidad

**Files:**
- Create: `reglas/tipos_entidad.yaml`

Cada tipo de entidad (SL, autonomo, comunidad de propietarios, asociacion, etc.)
tiene obligaciones contables y fiscales diferentes. Este catalogo define TODO lo que
el sistema necesita saber para cada tipo.

**Step 1: Crear catalogo de tipos**

```yaml
# reglas/tipos_entidad.yaml
# Catalogo de tipos de entidad — define obligaciones contables y fiscales por tipo

tipos:
  autonomo:
    nombre: "Trabajador autonomo (persona fisica)"
    pgc: pymes
    sujeto_iva: true
    sujeto_is: false
    sujeto_irpf: true
    tipo_impositivo_is: 0
    modelos_trimestrales: [303, 130, 111]
    modelos_anuales: [390, 100, 347]
    libros_obligatorios:
      - ingresos
      - gastos
      - bienes_inversion
      - facturas_emitidas
      - facturas_recibidas
    estados_financieros: []
    cuentas_anuales: false
    notas: "IRPF via modelo 100 anual. Pago fraccionado trimestral via 130."

  sl:
    nombre: "Sociedad Limitada (S.L.)"
    pgc: pymes           # 'completo' si cifra negocio > 8M EUR
    sujeto_iva: true
    sujeto_is: true
    sujeto_irpf: false
    tipo_impositivo_is: 25
    modelos_trimestrales: [303, 111]
    modelos_anuales: [390, 200, 347]
    libros_obligatorios:
      - diario
      - mayor
      - inventarios
      - facturas_emitidas
      - facturas_recibidas
    estados_financieros: [balance, pyg, memoria]
    cuentas_anuales: true
    deposito_registro_mercantil: true

  sa:
    nombre: "Sociedad Anonima (S.A.)"
    pgc: completo
    sujeto_iva: true
    sujeto_is: true
    sujeto_irpf: false
    tipo_impositivo_is: 25
    modelos_trimestrales: [303, 111]
    modelos_anuales: [390, 200, 347]
    libros_obligatorios:
      - diario
      - mayor
      - inventarios
      - actas
      - acciones_nominativas
      - facturas_emitidas
      - facturas_recibidas
    estados_financieros: [balance, pyg, memoria, ecpn, efe]
    cuentas_anuales: true
    deposito_registro_mercantil: true

  comunidad_propietarios:
    nombre: "Comunidad de propietarios"
    pgc: sectorial_fincas
    sujeto_iva: false
    sujeto_iva_excepciones: "Solo si tiene locales comerciales alquilados"
    sujeto_is: false
    sujeto_irpf: false
    tipo_impositivo_is: 0
    modelos_trimestrales: []
    modelos_anuales: [184, 347]
    libros_obligatorios:
      - ingresos_gastos
      - actas
    estados_financieros: [cuenta_explotacion]
    cuentas_anuales: false
    notas: "Modelo 184 atribucion de rentas. IVA solo si alquila locales."

  asociacion:
    nombre: "Asociacion sin animo de lucro"
    pgc: sectorial_enl
    sujeto_iva: parcial
    sujeto_iva_excepciones: "Exenta en actividad propia, sujeta en actividad economica"
    sujeto_is: true
    sujeto_irpf: false
    tipo_impositivo_is: 10
    modelos_trimestrales: [303]  # solo si tiene actividad economica sujeta
    modelos_anuales: [200, 347]
    libros_obligatorios:
      - diario
      - inventarios
      - socios
    estados_financieros: [balance, pyg, memoria]
    cuentas_anuales: true
    notas: "IS al 10% (tipo reducido ENL). 303 solo si actividad economica."

  comunidad_bienes:
    nombre: "Comunidad de bienes (C.B.)"
    pgc: pymes
    sujeto_iva: true
    sujeto_is: false
    sujeto_irpf: false
    tipo_impositivo_is: 0
    modelos_trimestrales: [303]
    modelos_anuales: [184, 347]
    libros_obligatorios:
      - ingresos
      - gastos
      - facturas_emitidas
      - facturas_recibidas
    estados_financieros: []
    cuentas_anuales: false
    notas: "Regimen atribucion rentas. Cada comunero declara su % en IRPF/IS."

  cooperativa:
    nombre: "Sociedad cooperativa"
    pgc: adaptado_coop
    sujeto_iva: true
    sujeto_is: true
    sujeto_irpf: false
    tipo_impositivo_is: 20
    modelos_trimestrales: [303, 111]
    modelos_anuales: [200, 347]
    libros_obligatorios:
      - diario
      - mayor
      - inventarios
      - socios
      - actas
      - facturas_emitidas
      - facturas_recibidas
    estados_financieros: [balance, pyg, memoria]
    cuentas_anuales: true
    notas: "IS al 20% (tipo reducido cooperativas). Fondo educacion y promocion obligatorio."

  fundacion:
    nombre: "Fundacion"
    pgc: sectorial_enl
    sujeto_iva: parcial
    sujeto_is: true
    sujeto_irpf: false
    tipo_impositivo_is: 10
    modelos_trimestrales: [303]
    modelos_anuales: [200, 347]
    libros_obligatorios:
      - diario
      - inventarios
      - patronos
    estados_financieros: [balance, pyg, memoria]
    cuentas_anuales: true
    notas: "Obligacion de destinar >= 70% rentas a fines fundacionales."

  sociedad_civil:
    nombre: "Sociedad civil"
    pgc: pymes
    sujeto_iva: true
    sujeto_is: false       # si no tiene personalidad juridica
    sujeto_irpf: false
    tipo_impositivo_is: 0
    modelos_trimestrales: [303]
    modelos_anuales: [184, 347]
    libros_obligatorios:
      - ingresos
      - gastos
      - facturas_emitidas
      - facturas_recibidas
    estados_financieros: []
    cuentas_anuales: false
    notas: "Si tiene personalidad juridica y objeto mercantil: IS 25% y modelo 200."
    variante_con_pj:
      sujeto_is: true
      tipo_impositivo_is: 25
      modelos_anuales: [200, 347]
```

**Step 2: Actualizar config.py para cargar tipos_entidad.yaml**

Anadir a `cargar_config()`:
1. Cargar `reglas/tipos_entidad.yaml`
2. Validar que el `tipo` del config.yaml del cliente existe en el catalogo
3. Inyectar las obligaciones del tipo en el ConfigCliente como propiedad

```python
# Anadir a ConfigCliente:

@property
def obligaciones(self) -> dict:
    """Devuelve obligaciones fiscales/contables segun tipo de entidad."""
    return self._tipo_entidad or {}

@property
def modelos_trimestrales(self) -> list:
    return self.obligaciones.get("modelos_trimestrales", [])

@property
def modelos_anuales(self) -> list:
    return self.obligaciones.get("modelos_anuales", [])

@property
def sujeto_iva(self) -> bool:
    return self.obligaciones.get("sujeto_iva", True)

@property
def sujeto_is(self) -> bool:
    return self.obligaciones.get("sujeto_is", False)

@property
def libros_obligatorios(self) -> list:
    return self.obligaciones.get("libros_obligatorios", [])
```

**Step 3: Commit**
```bash
git add reglas/tipos_entidad.yaml scripts/core/config.py
git commit -m "feat: catalogo tipos de entidad con obligaciones fiscales/contables"
```

---

## Tarea 7: Config Pastorino Costa del Sol

**Files:**
- Create: `clientes/pastorino-costa-del-sol/config.yaml`

**Step 1: Crear config completa basada en datos reales del CLAUDE.md**

Usar los datos exactos de proveedores, clientes, CIFs, regimenes ya configurados en FS.

Contenido: ver seccion "Configuracion por Cliente" del documento de diseno.
Incluir TODOS los 10 proveedores y 2 clientes con sus datos reales.
Incluir reglas especiales: IVA PT para Primatransit, autoliquidacion para Odoo/Transitainer,
pendiente_fiscal para Maersk.

**Step 2: Commit**
```bash
git add clientes/pastorino-costa-del-sol/config.yaml
git commit -m "feat: config.yaml completo para Pastorino Costa del Sol"
```

---

## Tarea 8: Config Gerardo Gonzalez Callejon

**Files:**
- Create: `clientes/gerardo-gonzalez-callejon/config.yaml`

**Step 1: Crear config basica**

Config minima para autonomo con dos actividades (podologia exenta + estetica 21%).
Proveedores y clientes aun vacios (pendiente documentacion 2025).

**Step 2: Commit**
```bash
git add clientes/gerardo-gonzalez-callejon/config.yaml
git commit -m "feat: config.yaml basico para Gerardo Gonzalez"
```

---

## Tarea 9: Fase 0 — Intake (Extraccion de documentos)

**Files:**
- Create: `scripts/phases/__init__.py`
- Create: `scripts/phases/intake.py`

**Step 1: Implementar fase intake**

Funcionalidad:
1. Escanear inbox/ buscando PDFs nuevos (no en pipeline_state)
2. Hash SHA256 por PDF (deduplicacion)
3. pdfplumber: extraer texto raw de cada PDF
4. Si hay texto: llamar GPT-4o con el texto para parsear JSON estructurado
5. Si no hay texto: llamar GPT-4o Vision con imagen del PDF
6. Identificar proveedor/cliente por CIF contra config.yaml
7. Clasificar tipo documento (FC/FV/NC/ANT/etc.)
8. Calcular confianza por campo
9. Guardar intake_results.json

Esquema JSON de salida GPT (prompt del sistema):
```json
{
  "tipo": "factura_proveedor|factura_cliente|nota_credito|anticipo|recibo|otro",
  "emisor_nombre": "...",
  "emisor_cif": "...",
  "receptor_nombre": "...",
  "receptor_cif": "...",
  "numero_factura": "...",
  "fecha": "YYYY-MM-DD",
  "base_imponible": 0.00,
  "iva_porcentaje": 0,
  "iva_importe": 0.00,
  "total": 0.00,
  "divisa": "EUR",
  "lineas": [{"descripcion": "...", "cantidad": 1, "precio": 0.00, "iva": 0}]
}
```

Dependencias: pdfplumber, openai

**Step 2: Commit**
```bash
git add scripts/phases/
git commit -m "feat: fase 0 intake - extraccion dual pdfplumber + GPT-4o"
```

---

## Tarea 10: Fase 1 — Validacion pre-FS

**Files:**
- Create: `scripts/phases/pre_validation.py`

**Step 1: Implementar validaciones pre-registro**

Validaciones:
1. CIF/NIF formato valido (regex adaptado por pais)
2. Proveedor/cliente existe en config.yaml
3. Divisa = esperada para el proveedor
4. Tipo IVA = esperado segun regimen
5. Fecha dentro del ejercicio activo
6. Importe > 0 (NC negativo OK)
7. Base + IVA = Total (tolerancia configurable)
8. No duplicado: hash + numero factura + CIF proveedor
9. No existe ya en FS (consulta API)

Entrada: intake_results.json
Salida: validated_batch.json (documentos que pasan) + excluidos con razon

**Step 2: Commit**
```bash
git add scripts/phases/pre_validation.py
git commit -m "feat: fase 1 validacion pre-FS con 9 checks"
```

---

## Tarea 11: Fase 2 — Registro en FS

**Files:**
- Create: `scripts/phases/registration.py`

**Step 1: Implementar registro de facturas con verificacion post-registro**

Por cada factura validada:
1. Construir form-data segun config (codproveedor, coddivisa, tasaconv, lineas json.dumps, codimpuesto)
2. POST a crearFacturaProveedor o crearFacturaCliente
3. GET factura recien creada -> comparar campo por campo (VERIFICACION 2)
4. PUT pagada=1
5. GET pagada -> verificar marcada

Si verificacion falla: DELETE factura + registrar error.

Entrada: validated_batch.json + config.yaml
Salida: registered.json (IDs facturas en FS)

**Step 2: Commit**
```bash
git add scripts/phases/registration.py
git commit -m "feat: fase 2 registro en FS con verificacion post-registro"
```

---

## Tarea 12: Fase 3 — Generacion de asientos

**Files:**
- Create: `scripts/phases/asientos.py`

**Step 1: Implementar generacion y verificacion de asientos**

Nota: FS puede no permitir generar asientos via API. En ese caso, el pipeline
para y pide generacion manual en UI. Se reanuda con --resume.

Pasos:
1. Intentar generar asientos via API (si endpoint disponible)
2. Si no disponible: guardar estado + instrucciones para generacion manual
3. Verificar que cada factura registrada tiene su asiento vinculado
4. Obtener todas las partidas de cada asiento

Entrada: registered.json
Salida: asientos_generados.json

**Step 2: Commit**
```bash
git add scripts/phases/asientos.py
git commit -m "feat: fase 3 generacion y verificacion de asientos"
```

---

## Tarea 13: Fase 4 — Correccion automatica

**Files:**
- Create: `scripts/phases/correction.py`

**Step 1: Implementar VERIFICACION 3 completa (la mas critica)**

Integrar logica de validar_asientos.py existente + nuevas validaciones:

1. **Cuadre**: sum(DEBE) == sum(HABER) por asiento
2. **Divisas**: si factura USD, convertir partidas a EUR via PUT
3. **NC serie R**: invertir DEBE/HABER via PUT
4. **Intracomunitarias**: crear partidas 472/477 si faltan (config.autoliquidacion)
5. **Reglas especiales**: aplicar reglas_especiales del config (ej: IVA PT a 4709)
6. **Subcuenta correcta**: verificar que subcuenta gasto/proveedor coincide con config
7. **Importe correcto**: importe asiento == importe factura en EUR

Cada correccion:
- Verificar con GET posterior
- Registrar en auditoria
- Registrar ocurrencia en catalogo de errores

Si proveedor marcado `pendiente_fiscal: true` -> solo AVISO, no auto-fix.

Entrada: asientos_generados.json + config.yaml + errores_conocidos.yaml
Salida: asientos_corregidos.json

**Step 2: Commit**
```bash
git add scripts/phases/correction.py
git commit -m "feat: fase 4 correccion automatica con 7 validaciones"
```

---

## Tarea 14: Fase 5 — Verificacion cruzada

**Files:**
- Create: `scripts/phases/cross_validation.py`

**Step 1: Implementar cruces globales**

Integrar logica de pestana VALIDACION de crear_libros_contables.py + nuevos cruces:

1. Total facturas proveedor == 600 neto + 4709
2. Total facturas cliente == 700
3. IVA repercutido facturas + autoliq == 477
4. IVA soportado facturas + autoliq == 472
5. Autoliquidacion 472 == autoliquidacion 477
6. Num facturas == num asientos
7. Libro diario cuadra (sum DEBE global == sum HABER global)
8. 303 calculado == 303 desde subcuentas
9. Balance: Activo == Pasivo + PN (si SL)

Tolerancia configurable desde config.yaml.

Entrada: API FS completa + config.yaml
Salida: cross_validation_report.json

**Step 2: Commit**
```bash
git add scripts/phases/cross_validation.py
git commit -m "feat: fase 5 verificacion cruzada con 9 checks globales"
```

---

## Tarea 15: Fase 6 — Generacion de salidas

**Files:**
- Create: `scripts/phases/output.py`

**Step 1: Implementar generacion de salidas finales**

Reutilizar logica de scripts existentes:
1. Excel libros contables (10 pestanas) — reutilizar crear_libros_contables.py
2. Pestana AUDITORIA adicional con resultados del pipeline
3. Archivos .txt modelos fiscales — reutilizar generar_modelos_fiscales.py
4. Mover PDFs de inbox/ a procesado/{trimestre}/{tipo}/ — reutilizar renombrar_documentos.py
5. Informe .log con resumen de auditoria
6. Actualizar pipeline_state.json con historial confianza

Pestana AUDITORIA Excel:
- Timestamp ejecucion
- Score confianza global
- Detalle verificaciones (PASS/FAIL)
- Correcciones aplicadas
- Alertas pendientes
- Historial ejecuciones anteriores

Entrada: Datos validados + auditoria completa
Salida: Excel + .txt + .log + PDFs movidos + pipeline_state.json

**Step 2: Commit**
```bash
git add scripts/phases/output.py
git commit -m "feat: fase 6 generacion salidas con auditoria Excel"
```

---

## Tarea 16: Pipeline orquestador

**Files:**
- Create: `scripts/pipeline.py`

**Step 1: Implementar orquestador principal**

Responsabilidades:
1. Parsear argumentos CLI (--cliente, --ejercicio, --dry-run, --resume, --fase, --verbose, --force)
2. Cargar config.yaml del cliente
3. Cargar reglas globales (validaciones.yaml + errores_conocidos.yaml)
4. Inicializar logger + auditoria
5. Ejecutar fases secuencialmente con quality gates entre cada una
6. Si quality gate falla y no --force: BLOQUEAR con mensaje claro
7. Si --resume: leer pipeline_state.json y continuar desde la fase interrumpida
8. Al finalizar: guardar pipeline_state.json + historial confianza

```python
# scripts/pipeline.py
"""SFCE — Pipeline de Fiabilidad Contable Evolutivo."""

def main():
    args = parsear_argumentos()

    # Cargar configuracion
    config = cargar_config(ruta_cliente)
    catalogo = CatalogoErrores(ruta_reglas / "errores_conocidos.yaml")
    auditoria = AuditoriaLogger(ruta_auditoria)

    # Estado (para --resume)
    estado = cargar_estado(ruta_cliente) if args.resume else EstadoPipeline()

    fases = [
        ("intake", ejecutar_intake),
        ("pre_validacion", ejecutar_pre_validacion),
        ("registro", ejecutar_registro),
        ("asientos", ejecutar_asientos),
        ("correccion", ejecutar_correccion),
        ("cruce", ejecutar_cruce),
        ("salidas", ejecutar_salidas),
    ]

    for nombre_fase, ejecutar in fases:
        if estado.fase_completada(nombre_fase):
            logger.info(f"Fase {nombre_fase} ya completada, saltando...")
            continue

        logger.info(f"=== FASE: {nombre_fase} ===")
        resultado = ejecutar(config, catalogo, auditoria, estado)

        if not resultado.exitoso:
            if args.force:
                logger.warning(f"Fase {nombre_fase} FALLO pero --force activo")
            else:
                logger.error(f"BLOQUEADO en fase {nombre_fase}")
                for e in resultado.errores:
                    logger.error(f"  - {e['mensaje']}")
                estado.guardar()
                auditoria.guardar()
                return 1

        estado.completar_fase(nombre_fase, resultado)
        auditoria.registrar(nombre_fase, "fase_completada", resultado.resumen())

    # Exito
    score = calcular_score_global(estado)
    logger.info(f"Pipeline completado. Score fiabilidad: {score}%")
    estado.guardar()
    auditoria.guardar()
    return 0
```

CLI:
```bash
python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025
python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025 --dry-run
python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025 --resume
python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025 --fase 4
```

**Step 2: Commit**
```bash
git add scripts/pipeline.py
git commit -m "feat: pipeline orquestador SFCE con 7 fases y quality gates"
```

---

## Tarea 17: Integracion y archivos .bat

**Files:**
- Create: `clientes/pastorino-costa-del-sol/pipeline.bat`
- Create: `clientes/gerardo-gonzalez-callejon/pipeline.bat`

**Step 1: Crear .bat por cliente**

```bat
@echo off
REM SFCE Pipeline - Pastorino Costa del Sol
cd /d "%~dp0..\.."
set FS_API_TOKEN=iOXmrA1Bbn8RDWXLv91L
python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025
pause
```

**Step 2: Crear carpeta cuarentena por cliente**

```bash
mkdir -p clientes/pastorino-costa-del-sol/cuarentena
mkdir -p clientes/gerardo-gonzalez-callejon/cuarentena
```

**Step 3: Instalar dependencias nuevas**

```bash
pip install pdfplumber pyyaml openai
```

**Step 4: Commit final**
```bash
git add clientes/*/pipeline.bat clientes/*/cuarentena/
git commit -m "feat: integracion SFCE - archivos bat y estructura"
```

---

## Orden de ejecucion

```
Tareas 1-5 (core/) ──→ Tarea 6 (reglas/) ──→ Tareas 7-8 (config clients)
                                                        │
                                                        ▼
Tarea 9 (intake) → 10 (pre-val) → 11 (registro) → 12 (asientos)
                                                        │
                                                        ▼
                          13 (correccion) → 14 (cruce) → 15 (output)
                                                        │
                                                        ▼
                                          16 (pipeline) → 17 (integracion)
```

Tareas 1-5 son independientes entre si (paralelizables).
Tareas 7-8 son independientes entre si (paralelizables).
Tareas 9-15 son secuenciales (cada fase depende de la anterior).

## Notas para el implementador

1. **No reescribir scripts existentes**. La logica de `validar_asientos.py`, `crear_libros_contables.py`, etc. se REUTILIZA importandola desde los modulos de fase. Los scripts originales siguen funcionando independientemente.

2. **GPT-4o para intake**: usar modelo `gpt-4o` con `response_format={"type": "json_object"}`. El prompt debe incluir el esquema JSON esperado y pedir que devuelva SOLO el JSON.

3. **Generacion de asientos**: FS probablemente NO permite generar asientos via API REST. En ese caso, la fase 3 debe guardar estado y mostrar instrucciones claras para hacerlo manualmente en la UI, luego `--resume`.

4. **Config.yaml de Pastorino**: los datos exactos de CIFs, nombres en FS, regimenes, etc. ya estan en el CLAUDE.md del cliente. Copiar literalmente.

5. **Este proyecto NO es un repo git**. Los commits son orientativos. Si se decide inicializar git, hacerlo antes de empezar.
