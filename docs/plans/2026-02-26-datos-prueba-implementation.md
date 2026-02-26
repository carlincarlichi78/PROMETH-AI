# Generador Datos de Prueba SFCE - Plan de Implementacion

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Construir un generador que produzca ~1.100 PDFs realistas (facturas, nominas, recibos bancarios, etc.) para 11 entidades ficticias, incluyendo ~20% con errores deliberados y ~15% edge cases, para testear el SFCE end-to-end.

**Architecture:** Motor CLI en Python que carga definiciones YAML de entidades, usa generadores especializados por tipo de documento, renderiza plantillas HTML con weasyprint a PDF, y produce un manifiesto JSON para verificacion automatica. Estructura modular: datos/ (YAML) → generadores/ → plantillas/ (HTML+CSS) → utils/ → salida/ (PDFs + manifiesto).

**Tech Stack:** Python 3.12, weasyprint 68.0, PyYAML, Jinja2 (plantillas HTML), Pillow (ruido visual)

**Referencia de diseno:** `docs/plans/2026-02-26-datos-prueba-design.md` (secciones 1-10)

**Convenciones del proyecto:**
- Imports: `sys.path.insert(0, str(RAIZ))` para imports relativos
- Logging: `crear_logger("nombre")` de `scripts/core/logger.py`
- Patrones: pathlib, type hints, docstrings en espanol
- Sin mutaciones, funciones puras donde sea posible

---

## Fase A: Cimientos (utils + datos YAML)

### Tarea 1: Estructura de directorios + utils/cif.py

**Files:**
- Create: `tests/datos_prueba/generador/__init__.py`
- Create: `tests/datos_prueba/generador/utils/__init__.py`
- Create: `tests/datos_prueba/generador/utils/cif.py`
- Create: `tests/datos_prueba/generador/generadores/__init__.py`
- Create: `tests/datos_prueba/generador/datos/` (dir)
- Create: `tests/datos_prueba/generador/plantillas/` (dir)
- Create: `tests/datos_prueba/generador/css/variantes/` (dir)

**Paso 1: Crear estructura de directorios**

```bash
mkdir -p tests/datos_prueba/generador/{utils,generadores,datos,plantillas,css/variantes}
touch tests/__init__.py tests/datos_prueba/__init__.py tests/datos_prueba/generador/__init__.py
touch tests/datos_prueba/generador/utils/__init__.py tests/datos_prueba/generador/generadores/__init__.py
```

**Paso 2: Implementar utils/cif.py**

Genera y valida CIF/NIF espanoles realistas. Necesario para todas las entidades del YAML.

```python
"""Generacion y validacion de CIF/NIF espanoles realistas."""
import random
import string

# Letras de control NIF
_LETRAS_NIF = "TRWAGMYFPDXBNJZSQVHLCKE"

# Letras validas para primer caracter CIF
_TIPOS_CIF = "ABCDEFGHJNPQRSUVW"


def generar_nif(seed_num: int = None) -> str:
    """Genera un NIF valido (DNI + letra).

    Args:
        seed_num: numero fijo (8 digitos) o None para aleatorio
    """
    num = seed_num if seed_num else random.randint(10000000, 99999999)
    letra = _LETRAS_NIF[num % 23]
    return f"{num:08d}{letra}"


def validar_nif(nif: str) -> bool:
    """Valida que un NIF tenga letra de control correcta."""
    if len(nif) != 9 or not nif[:8].isdigit():
        return False
    return nif[8].upper() == _LETRAS_NIF[int(nif[:8]) % 23]


def generar_cif(tipo: str = "B", provincia: int = None) -> str:
    """Genera un CIF valido para sociedades.

    Args:
        tipo: letra tipo entidad (A=SA, B=SL, etc.)
        provincia: codigo provincia 2 digitos (01-52) o None para aleatorio
    """
    if tipo not in _TIPOS_CIF:
        tipo = "B"
    prov = provincia if provincia else random.randint(1, 52)
    # 5 digitos aleatorios para inscripcion
    inscripcion = random.randint(10000, 99999)
    base = f"{prov:02d}{inscripcion}"
    # Calculo digito control
    control = _calcular_control_cif(base)
    # Segun tipo, control puede ser letra o numero
    if tipo in "KPQS":
        control_str = chr(ord("A") + control)
    elif tipo in "ABEH":
        control_str = str(control)
    else:
        # Puede ser ambos, usamos numero
        control_str = str(control)
    return f"{tipo}{base}{control_str}"


def _calcular_control_cif(digitos: str) -> int:
    """Calcula digito de control CIF (algoritmo modulo)."""
    suma_pares = sum(int(d) for d in digitos[1::2])
    suma_impares = 0
    for d in digitos[0::2]:
        doble = int(d) * 2
        suma_impares += doble // 10 + doble % 10
    total = suma_pares + suma_impares
    control = (10 - (total % 10)) % 10
    return control


def validar_cif(cif: str) -> bool:
    """Valida que un CIF tenga digito de control correcto."""
    if len(cif) != 9 or cif[0] not in _TIPOS_CIF:
        return False
    base = cif[1:8]
    if not base.isdigit():
        return False
    control_esperado = _calcular_control_cif(base)
    ultimo = cif[8]
    if ultimo.isdigit():
        return int(ultimo) == control_esperado
    return (ord(ultimo.upper()) - ord("A")) == control_esperado


def generar_nie(tipo: str = "X") -> str:
    """Genera un NIE valido (extranjeros)."""
    prefijo_num = {"X": 0, "Y": 1, "Z": 2}.get(tipo, 0)
    num = random.randint(1000000, 9999999)
    base = int(f"{prefijo_num}{num:07d}")
    letra = _LETRAS_NIF[base % 23]
    return f"{tipo}{num:07d}{letra}"


def generar_vat_eu(pais: str) -> str:
    """Genera un VAT number europeo ficticio pero con formato correcto."""
    formatos = {
        "IRL": lambda: f"IE{random.randint(1000000, 9999999)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVW')}",
        "DEU": lambda: f"DE{random.randint(100000000, 999999999)}",
        "FRA": lambda: f"FR{random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)}{random.randint(100000000, 999999999)}",
        "ITA": lambda: f"IT{random.randint(10000000000, 99999999999)}",
        "PRT": lambda: f"PT{random.randint(100000000, 999999999)}",
        "SWE": lambda: f"SE{random.randint(1000000000, 9999999999)}01",
    }
    generador = formatos.get(pais, lambda: f"{pais}{random.randint(100000000, 999999999)}")
    return generador()


def generar_cif_invalido(cif_valido: str) -> str:
    """Corrompe el digito de control de un CIF valido (para error E01)."""
    ultimo = cif_valido[-1]
    if ultimo.isdigit():
        nuevo = str((int(ultimo) + 1) % 10)
    else:
        nuevo = chr(((ord(ultimo) - ord("A") + 1) % 26) + ord("A"))
    return cif_valido[:-1] + nuevo
```

**Paso 3: Test rapido de CIF**

```bash
python -c "
import sys; sys.path.insert(0, 'tests/datos_prueba/generador')
from utils.cif import generar_cif, validar_cif, generar_nif, validar_nif, generar_cif_invalido
cif = generar_cif('B', 29)  # SL Malaga
print(f'CIF: {cif}, valido: {validar_cif(cif)}')
invalido = generar_cif_invalido(cif)
print(f'CIF corrupto: {invalido}, valido: {validar_cif(invalido)}')
nif = generar_nif()
print(f'NIF: {nif}, valido: {validar_nif(nif)}')
"
```

Expected: CIF valido True, corrupto False, NIF valido True.

**Paso 4: Commit**

```bash
git add tests/
git commit -m "feat: estructura directorios + utils/cif.py generador datos prueba"
```

---

### Tarea 2: utils/fechas.py + utils/importes.py

**Files:**
- Create: `tests/datos_prueba/generador/utils/fechas.py`
- Create: `tests/datos_prueba/generador/utils/importes.py`

**Paso 1: Implementar utils/fechas.py**

Distribucion temporal realista por trimestre/mes segun diseno seccion 9.

```python
"""Distribucion temporal de documentos por mes y trimestre."""
import random
from datetime import date, timedelta
from typing import List

# Pesos por mes (segun diseno seccion 9)
PESOS_MES = {
    1: 0.08,   # Ene - media
    2: 0.06,   # Feb - media-baja
    3: 0.10,   # Mar - alta (cierre T1)
    4: 0.08,   # Abr - media
    5: 0.08,   # May - media
    6: 0.10,   # Jun - alta (pagas, cierre T2)
    7: 0.07,   # Jul - variable
    8: 0.05,   # Ago - baja
    9: 0.08,   # Sep - media-alta
    10: 0.10,  # Oct - alta (cosecha, cierre T3)
    11: 0.09,  # Nov - alta (campana navidad)
    12: 0.11,  # Dic - muy alta (cierre ejercicio)
}


def generar_fecha_en_mes(anio: int, mes: int, rng: random.Random = None) -> date:
    """Genera fecha aleatoria dentro de un mes, evitando fines de semana."""
    r = rng or random
    ultimo_dia = _ultimo_dia_mes(anio, mes)
    intentos = 0
    while intentos < 50:
        dia = r.randint(1, ultimo_dia)
        fecha = date(anio, mes, dia)
        if fecha.weekday() < 5:  # lun-vie
            return fecha
        intentos += 1
    # Fallback: devolver cualquier dia laboral
    return date(anio, mes, min(15, ultimo_dia))


def distribuir_fechas(anio: int, total_docs: int, rng: random.Random = None,
                      pesos: dict = None, meses_activos: List[int] = None) -> List[date]:
    """Distribuye N fechas a lo largo del ano con pesos por mes.

    Args:
        anio: ejercicio fiscal
        total_docs: numero total de documentos
        rng: generador aleatorio con seed
        pesos: pesos por mes (default PESOS_MES)
        meses_activos: lista de meses activos (ej: [4,5,6,7,8,9,10] para estacional)
    """
    r = rng or random
    p = pesos or PESOS_MES
    activos = meses_activos or list(range(1, 13))

    # Filtrar y renormalizar pesos
    pesos_filtrados = {m: p.get(m, 0.08) for m in activos}
    total_peso = sum(pesos_filtrados.values())
    pesos_norm = {m: v / total_peso for m, v in pesos_filtrados.items()}

    # Asignar docs por mes
    fechas = []
    docs_restantes = total_docs
    meses_ordenados = sorted(pesos_norm.keys())

    for i, mes in enumerate(meses_ordenados):
        if i == len(meses_ordenados) - 1:
            n = docs_restantes  # Ultimo mes recibe el resto
        else:
            n = round(total_docs * pesos_norm[mes])
            n = min(n, docs_restantes)
        docs_restantes -= n
        for _ in range(n):
            fechas.append(generar_fecha_en_mes(anio, mes, r))

    r.shuffle(fechas)
    return sorted(fechas)


def trimestre_de_fecha(fecha: date) -> str:
    """Devuelve T1-T4 segun el mes."""
    return f"T{(fecha.month - 1) // 3 + 1}"


def fechas_mensuales(anio: int, meses: List[int] = None, dia: int = 28) -> List[date]:
    """Genera una fecha por mes (para recibos recurrentes como nominas, suministros).

    Args:
        anio: ejercicio
        meses: lista de meses (default 1-12)
        dia: dia del mes para el recibo (default 28)
    """
    meses = meses or list(range(1, 13))
    resultado = []
    for m in meses:
        d = min(dia, _ultimo_dia_mes(anio, m))
        resultado.append(date(anio, m, d))
    return resultado


def _ultimo_dia_mes(anio: int, mes: int) -> int:
    """Devuelve ultimo dia del mes."""
    if mes == 12:
        return 31
    return (date(anio, mes + 1, 1) - timedelta(days=1)).day
```

**Paso 2: Implementar utils/importes.py**

Calculo coherente de IVA, IRPF, SS, REAGP.

```python
"""Calculo coherente de importes fiscales: IVA, IRPF, SS, REAGP."""
import random
from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class LineaFactura:
    """Linea individual de una factura."""
    concepto: str
    cantidad: float
    precio_unitario: float
    iva_tipo: float  # 0, 4, 10, 21
    descuento_pct: float = 0.0
    retencion_pct: float = 0.0
    recargo_eq_pct: float = 0.0  # Recargo equivalencia: 0, 0.5, 1.4, 5.2

    @property
    def base(self) -> float:
        subtotal = self.cantidad * self.precio_unitario
        descuento = subtotal * self.descuento_pct / 100
        return _redondear(subtotal - descuento)

    @property
    def cuota_iva(self) -> float:
        return _redondear(self.base * self.iva_tipo / 100)

    @property
    def cuota_retencion(self) -> float:
        return _redondear(self.base * self.retencion_pct / 100)

    @property
    def cuota_recargo(self) -> float:
        return _redondear(self.base * self.recargo_eq_pct / 100)

    @property
    def total_linea(self) -> float:
        return _redondear(self.base + self.cuota_iva + self.cuota_recargo - self.cuota_retencion)


@dataclass
class ResumenFactura:
    """Resumen calculado de una factura completa."""
    lineas: List[LineaFactura]
    divisa: str = "EUR"
    tasaconv: float = 1.0

    @property
    def base_imponible(self) -> float:
        return _redondear(sum(l.base for l in self.lineas))

    @property
    def total_iva(self) -> float:
        return _redondear(sum(l.cuota_iva for l in self.lineas))

    @property
    def total_retencion(self) -> float:
        return _redondear(sum(l.cuota_retencion for l in self.lineas))

    @property
    def total_recargo(self) -> float:
        return _redondear(sum(l.cuota_recargo for l in self.lineas))

    @property
    def total(self) -> float:
        return _redondear(self.base_imponible + self.total_iva
                          + self.total_recargo - self.total_retencion)

    @property
    def total_eur(self) -> float:
        """Total convertido a EUR."""
        if self.divisa == "EUR":
            return self.total
        return _redondear(self.total / self.tasaconv)

    def desglose_iva(self) -> dict:
        """Agrupa bases y cuotas por tipo de IVA."""
        desglose = {}
        for l in self.lineas:
            tipo = l.iva_tipo
            if tipo not in desglose:
                desglose[tipo] = {"base": 0.0, "cuota": 0.0}
            desglose[tipo]["base"] = _redondear(desglose[tipo]["base"] + l.base)
            desglose[tipo]["cuota"] = _redondear(desglose[tipo]["cuota"] + l.cuota_iva)
        return desglose


@dataclass
class CuotaSS:
    """Cuota Seguridad Social de un empleado."""
    base_cotizacion: float
    contingencias_comunes_pct: float = 23.60  # Empresa
    desempleo_pct: float = 5.50  # Empresa (tipo general indefinido)
    fogasa_pct: float = 0.20
    fp_pct: float = 0.60
    cc_trabajador_pct: float = 4.70
    desempleo_trabajador_pct: float = 1.55
    fp_trabajador_pct: float = 0.10

    @property
    def cuota_empresa(self) -> float:
        pct = self.contingencias_comunes_pct + self.desempleo_pct + self.fogasa_pct + self.fp_pct
        return _redondear(self.base_cotizacion * pct / 100)

    @property
    def cuota_trabajador(self) -> float:
        pct = self.cc_trabajador_pct + self.desempleo_trabajador_pct + self.fp_trabajador_pct
        return _redondear(self.base_cotizacion * pct / 100)

    @property
    def cuota_total(self) -> float:
        return _redondear(self.cuota_empresa + self.cuota_trabajador)


def calcular_irpf_nomina(bruto_anual: float, situacion_familiar: int = 1) -> float:
    """Calcula porcentaje IRPF aproximado para nominas.

    Tramos 2025 simplificados:
    - Hasta 12.450€: 19%
    - 12.450 - 20.200€: 24%
    - 20.200 - 35.200€: 30%
    - 35.200 - 60.000€: 37%
    - > 60.000€: 45%

    Returns: porcentaje IRPF redondeado (ej: 15.0, 22.0)
    """
    tramos = [
        (12450, 0.19),
        (20200, 0.24),
        (35200, 0.30),
        (60000, 0.37),
        (float("inf"), 0.45),
    ]
    cuota = 0.0
    base_previa = 0.0
    for tope, pct in tramos:
        tramo = min(bruto_anual, tope) - base_previa
        if tramo <= 0:
            break
        cuota += tramo * pct
        base_previa = tope

    # Minimo personal simplificado
    minimo = 5550 if situacion_familiar == 1 else 7700
    cuota -= min(minimo, bruto_anual) * 0.19
    cuota = max(0, cuota)

    pct_efectivo = (cuota / bruto_anual * 100) if bruto_anual > 0 else 0
    return round(pct_efectivo)


def generar_importe_aleatorio(minimo: float, maximo: float,
                              rng: random.Random = None) -> float:
    """Genera importe aleatorio redondeado a 2 decimales."""
    r = rng or random
    return _redondear(r.uniform(minimo, maximo))


def _redondear(valor: float) -> float:
    """Redondea a 2 decimales con ROUND_HALF_UP (estandar contable)."""
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
```

**Paso 3: Test rapido**

```bash
python -c "
import sys; sys.path.insert(0, 'tests/datos_prueba/generador')
from utils.importes import LineaFactura, ResumenFactura, calcular_irpf_nomina

linea1 = LineaFactura('Consultoria', 10, 150.0, 21, retencion_pct=15)
linea2 = LineaFactura('Hosting', 1, 450.0, 0)
factura = ResumenFactura([linea1, linea2])
print(f'Base: {factura.base_imponible}, IVA: {factura.total_iva}, Ret: {factura.total_retencion}, Total: {factura.total}')
print(f'Desglose IVA: {factura.desglose_iva()}')
print(f'IRPF 30k: {calcular_irpf_nomina(30000)}%')
"
```

Expected: Base 1950.0, IVA 315.0 (solo linea1), Ret 225.0, Total correctos.

**Paso 4: Commit**

```bash
git add tests/datos_prueba/generador/utils/fechas.py tests/datos_prueba/generador/utils/importes.py
git commit -m "feat: utils/fechas.py + utils/importes.py para generador datos prueba"
```

---

### Tarea 3: utils/pdf_renderer.py

**Files:**
- Create: `tests/datos_prueba/generador/utils/pdf_renderer.py`

**Paso 1: Implementar pdf_renderer.py**

Renderiza HTML (Jinja2) a PDF con weasyprint. Nucleo del generador.

```python
"""Renderizado HTML → PDF con weasyprint y Jinja2."""
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# Agregar raiz proyecto al path
RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
from scripts.core.logger import crear_logger

logger = crear_logger("pdf_renderer")

# Directorios base
DIR_GENERADOR = Path(__file__).resolve().parents[1]
DIR_PLANTILLAS = DIR_GENERADOR / "plantillas"
DIR_CSS = DIR_GENERADOR / "css"

# Entorno Jinja2
_env = Environment(
    loader=FileSystemLoader(str(DIR_PLANTILLAS)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)

# Filtros custom para plantillas
_env.filters["moneda"] = lambda v, s="EUR": f"{v:,.2f} {s}".replace(",", "X").replace(".", ",").replace("X", ".")
_env.filters["fecha_es"] = lambda d: d.strftime("%d/%m/%Y") if d else ""
_env.filters["porcentaje"] = lambda v: f"{v:.2f}%".replace(".", ",")


def renderizar_html(plantilla: str, datos: dict) -> str:
    """Renderiza una plantilla HTML con datos.

    Args:
        plantilla: nombre del archivo HTML (ej: 'factura_estandar.html')
        datos: diccionario con variables para la plantilla

    Returns:
        HTML renderizado como string
    """
    tmpl = _env.get_template(plantilla)
    return tmpl.render(**datos)


def html_a_pdf(html: str, ruta_salida: Path, css_variante: str = "corporativo") -> Path:
    """Convierte HTML a PDF usando weasyprint.

    Args:
        html: contenido HTML renderizado
        ruta_salida: ruta completa del archivo PDF de salida
        css_variante: nombre del CSS variante (sin extension)

    Returns:
        Path al archivo PDF generado
    """
    from weasyprint import HTML, CSS

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # CSS: base + variante
    hojas_css = []
    css_base = DIR_CSS / "base.css"
    if css_base.exists():
        hojas_css.append(CSS(filename=str(css_base)))

    css_var = DIR_CSS / "variantes" / f"{css_variante}.css"
    if css_var.exists():
        hojas_css.append(CSS(filename=str(css_var)))

    doc = HTML(string=html)
    doc.write_pdf(str(ruta_salida), stylesheets=hojas_css)

    logger.info(f"PDF generado: {ruta_salida.name} ({ruta_salida.stat().st_size / 1024:.1f} KB)")
    return ruta_salida


def generar_pdf(plantilla: str, datos: dict, ruta_salida: Path,
                css_variante: str = "corporativo") -> Path:
    """Genera PDF completo: renderiza HTML + convierte a PDF.

    Args:
        plantilla: nombre plantilla HTML
        datos: datos para la plantilla
        ruta_salida: ruta PDF salida
        css_variante: estilo CSS a usar

    Returns:
        Path al PDF generado
    """
    html = renderizar_html(plantilla, datos)
    return html_a_pdf(html, ruta_salida, css_variante)
```

**Paso 2: Verificar import de weasyprint**

```bash
python -c "from weasyprint import HTML; print('weasyprint OK')"
python -c "from jinja2 import Environment; print('jinja2 OK')"
```

Si jinja2 no esta instalado: `pip install jinja2`

**Paso 3: Commit**

```bash
git add tests/datos_prueba/generador/utils/pdf_renderer.py
git commit -m "feat: utils/pdf_renderer.py renderizador HTML-PDF con weasyprint+jinja2"
```

---

### Tarea 4: Archivos de datos YAML (empresas + errores + edge cases)

**Files:**
- Create: `tests/datos_prueba/generador/datos/empresas.yaml`
- Create: `tests/datos_prueba/generador/datos/catalogo_errores.yaml`
- Create: `tests/datos_prueba/generador/datos/edge_cases.yaml`
- Create: `tests/datos_prueba/generador/datos/saldos_2024.yaml`

**NOTA:** Estos archivos son extensos. El contenido proviene directamente del documento de diseno (secciones 1-9). Cada archivo se describe aqui con su estructura y debe implementarse con datos completos.

**Paso 1: empresas.yaml**

Estructura por entidad (11 en total). Ejemplo para Aurora Digital:

```yaml
entidades:
  aurora-digital:
    nombre: "AURORA DIGITAL SOLUTIONS S.L."
    nombre_comercial: "Aurora Digital"
    cif: "B29845612"  # Generado con utils/cif.py
    tipo: sl
    actividad: "Consultoria IT + desarrollo web"
    cnae: "6202"
    direccion: "C/ Tecnologia 15, 3B, 46001 Valencia"
    email: "admin@auroradigital.es"
    telefono: "961234567"
    banco: "ES12 0049 1234 5678 9012 3456"
    regimen_iva: general
    idempresa: 3
    ejercicio: "2025"
    meses_activos: [1,2,3,4,5,6,7,8,9,10,11,12]
    empleados: 4
    css_variante: corporativo
    docs_estimados: 108

    proveedores:
      aws:
        nombre: "Amazon Web Services EMEA SARL"
        cif: "LU26888617"
        vat: "IE9692928F"
        pais: IRL
        divisa: EUR
        codimpuesto: IVA0
        regimen: intracomunitario
        frecuencia: mensual
        importe_rango: [400, 800]
        concepto: "Cloud hosting services"

      microsoft:
        nombre: "Microsoft Ireland Operations Ltd"
        cif: "IE8256796U"
        vat: "IE8256796U"
        pais: IRL
        divisa: EUR
        codimpuesto: IVA0
        regimen: intracomunitario
        frecuencia: mensual
        importe_rango: [200, 350]
        concepto: "Microsoft 365 Business Premium"

      # ... (vodafone, northgate, mutua, ofiprix)

    clientes:
      ayto_valencia:
        nombre: "Ayuntamiento de Valencia"
        cif: "P4625000B"
        pais: ESP
        divisa: EUR
        codimpuesto: IVA21
        retencion: 15
        frecuencia: trimestral
        importe_rango: [3000, 8000]
        concepto: "Desarrollo y mantenimiento web"

      # ... (clinica_dental, techberlin, particulares)

    servicios_profesionales:
      gestoria:
        nombre: "Gestoria Martinez y Asociados S.L."
        cif: ""  # Generar con cif.py
        retencion: 15
        importe_mensual: 250
        concepto: "Asesoria fiscal y contable mensual"
      # ...

    empleados_detalle:
      - nombre: "Ana Garcia Lopez"
        nif: ""  # Generar
        puesto: "Desarrolladora senior"
        bruto_anual: 32000
        convenio: "Consultoria TIC"
        tipo_contrato: indefinido
        jornada: completa
        extras: {teletrabajo: 55}  # compensacion mensual
      # ... (3 empleados mas)

    productos_financieros:
      - tipo: prestamo
        nombre: "Prestamo ICO digitalizacion"
        importe: 30000
        pendiente: 24000
        plazo_meses: 60
        cuota: 550
        interes: 3.5
        cuenta: "1700/5200"
      # ... (poliza credito, leasing, renting)

  # distribuciones-levante: { ... }
  # gastro-holding: { ... }
  # restaurante-la-marea: { ... }
  # chiringuito-sol-arena: { ... }
  # catering-costa: { ... }
  # marcos-ruiz: { ... }
  # elena-navarro: { ... }
  # jose-antonio-bermudez: { ... }
  # francisco-mora: { ... }
  # comunidad-mirador: { ... }
```

Implementar las 11 entidades completas con todos los proveedores, clientes, empleados y productos financieros del diseno (secciones 2-4).

**Paso 2: catalogo_errores.yaml**

```yaml
errores:
  E01:
    nombre: "CIF invalido"
    descripcion: "Letra/digito control incorrecto"
    probabilidad: 0.02
    tipos_doc: [factura_compra, factura_venta]
    accion: "corromper_cif"

  E02:
    nombre: "IVA mal calculado"
    descripcion: "Resultado IVA no coincide con base x tipo"
    probabilidad: 0.03
    tipos_doc: [factura_compra, factura_venta]
    accion: "alterar_cuota_iva"
    parametros:
      desviacion_max: 5.0  # euros

  # E03..E15 (del diseno seccion 8)
```

**Paso 3: edge_cases.yaml**

```yaml
edge_cases:
  EC01:
    nombre: "Factura multimoneda"
    descripcion: "USD con tipo cambio BCE del dia"
    entidad_principal: distribuciones-levante
    tipos_doc: [factura_compra]
    parametros:
      divisa: USD
      tasaconv_rango: [1.05, 1.15]

  # EC02..EC25 (del diseno seccion 8)
```

**Paso 4: saldos_2024.yaml**

```yaml
saldos:
  aurora-digital:
    activo:
      inmovilizado:
        - cuenta: "217"
          concepto: "Servidores"
          importe: 15000
          amort_acum: 6000
        - cuenta: "218"
          concepto: "Vehiculo leasing"
          importe: 22000
          amort_acum: 5500
      # ...
    pasivo:
      # ...
    patrimonio_neto:
      capital: 3000
      reservas: 15000
      resultado_2024: 18500

  # ... (10 entidades mas, del diseno seccion 7)
```

**Paso 5: Validar YAML carga correctamente**

```bash
python -c "
import yaml
from pathlib import Path
for f in ['empresas', 'catalogo_errores', 'edge_cases', 'saldos_2024']:
    ruta = Path(f'tests/datos_prueba/generador/datos/{f}.yaml')
    data = yaml.safe_load(ruta.read_text(encoding='utf-8'))
    print(f'{f}.yaml: OK ({len(str(data))} chars)')
"
```

**Paso 6: Commit**

```bash
git add tests/datos_prueba/generador/datos/
git commit -m "feat: archivos datos YAML (11 entidades, errores, edge cases, saldos)"
```

---

## Fase B: Plantillas HTML + CSS

### Tarea 5: CSS base + variantes

**Files:**
- Create: `tests/datos_prueba/generador/css/base.css`
- Create: `tests/datos_prueba/generador/css/variantes/corporativo.css`
- Create: `tests/datos_prueba/generador/css/variantes/autonomo.css`
- Create: `tests/datos_prueba/generador/css/variantes/administracion.css`
- Create: `tests/datos_prueba/generador/css/variantes/extranjero.css`

**Paso 1: base.css**

CSS compartido para todas las plantillas: tipografia, layout A4, tabla de lineas, cabecera emisor/receptor, totales, pie de pagina. Usar `@page { size: A4; margin: 15mm; }`.

Incluir estilos para: `.factura`, `.cabecera`, `.emisor`, `.receptor`, `.tabla-lineas`, `.desglose-iva`, `.totales`, `.pie`, `.nomina`, `.recibo-bancario`, `.sello`, `.firma`.

**Paso 2: variantes/**

- `corporativo.css`: colores corporativos (azul oscuro #1a365d), logo placeholder, bordes gruesos
- `autonomo.css`: minimalista, grises, sin logo, tipografia mas simple
- `administracion.css`: estilo documentos oficiales (escudo placeholder, tipografia serif, numeracion formal)
- `extranjero.css`: formato anglosajón (totales abajo-derecha), terminologia inglesa en headers

**Paso 3: Commit**

```bash
git add tests/datos_prueba/generador/css/
git commit -m "feat: CSS base + 4 variantes para plantillas PDF"
```

---

### Tarea 6: Plantillas HTML principales (facturas)

**Files:**
- Create: `tests/datos_prueba/generador/plantillas/factura_estandar.html`
- Create: `tests/datos_prueba/generador/plantillas/factura_simplificada.html`
- Create: `tests/datos_prueba/generador/plantillas/factura_extranjera.html`
- Create: `tests/datos_prueba/generador/plantillas/factura_servicios.html`
- Create: `tests/datos_prueba/generador/plantillas/nota_credito.html`
- Create: `tests/datos_prueba/generador/plantillas/factura_restauracion.html`

**Paso 1: factura_estandar.html**

Plantilla Jinja2 con variables: `emisor`, `receptor`, `factura` (numero, fecha, serie), `lineas` (lista LineaFactura), `resumen` (ResumenFactura), `notas`, `forma_pago`, `cuenta_bancaria`.

Estructura: cabecera (emisor izq, receptor dcha), datos factura, tabla lineas (concepto, cantidad, precio, dto, base, IVA%, cuota IVA), desglose IVA, retenciones, total, pie (forma pago, IBAN, menciones legales).

```html
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>Factura {{ factura.numero }}</title></head>
<body>
<div class="factura">
  <div class="cabecera">
    <div class="emisor">
      <h2>{{ emisor.nombre }}</h2>
      <p>CIF: {{ emisor.cif }}</p>
      <p>{{ emisor.direccion }}</p>
      {% if emisor.email %}<p>{{ emisor.email }}</p>{% endif %}
    </div>
    <div class="datos-factura">
      <h1>FACTURA</h1>
      <p>N.º: {{ factura.numero }}</p>
      <p>Fecha: {{ factura.fecha | fecha_es }}</p>
    </div>
  </div>
  <div class="receptor">
    <h3>DATOS DEL CLIENTE</h3>
    <p>{{ receptor.nombre }}</p>
    <p>CIF/NIF: {{ receptor.cif }}</p>
    <p>{{ receptor.direccion }}</p>
  </div>
  <table class="tabla-lineas">
    <thead><tr><th>Concepto</th><th>Uds.</th><th>Precio</th><th>Dto.</th><th>Base</th><th>IVA</th><th>Cuota</th></tr></thead>
    <tbody>
    {% for l in lineas %}
    <tr>
      <td>{{ l.concepto }}</td>
      <td>{{ l.cantidad }}</td>
      <td>{{ l.precio_unitario | moneda(divisa) }}</td>
      <td>{{ l.descuento_pct | porcentaje }}</td>
      <td>{{ l.base | moneda(divisa) }}</td>
      <td>{{ l.iva_tipo | porcentaje }}</td>
      <td>{{ l.cuota_iva | moneda(divisa) }}</td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
  <!-- Desglose IVA, retenciones, total -->
  <div class="totales">
    <p>Base imponible: {{ resumen.base_imponible | moneda(divisa) }}</p>
    {% for tipo, d in resumen.desglose_iva().items() %}
    <p>IVA {{ tipo }}%: {{ d.cuota | moneda(divisa) }}</p>
    {% endfor %}
    {% if resumen.total_retencion > 0 %}
    <p>Retencion IRPF: -{{ resumen.total_retencion | moneda(divisa) }}</p>
    {% endif %}
    <p class="total-final"><strong>TOTAL: {{ resumen.total | moneda(divisa) }}</strong></p>
  </div>
  <div class="pie">
    <p>Forma de pago: {{ forma_pago }}</p>
    {% if cuenta_bancaria %}<p>IBAN: {{ cuenta_bancaria }}</p>{% endif %}
    {% for nota in notas %}<p class="nota">{{ nota }}</p>{% endfor %}
  </div>
</div>
</body>
</html>
```

**Paso 2:** Crear las 5 variantes restantes siguiendo el mismo patron pero con diferencias:

- `factura_simplificada.html`: sin datos receptor, total < 400€, mencion "factura simplificada"
- `factura_extranjera.html`: cabecera bilingue, campo divisa/tasaconv, mencion intracomunitaria o extracomunitaria
- `factura_servicios.html`: sin "cantidad", concepto como descripcion larga, mencion retencion 15%
- `nota_credito.html`: titulo "NOTA DE CREDITO", referencia a factura original, importes negativos
- `factura_restauracion.html`: estilo ticket, IVA 10%+21%, propinas opcional

**Paso 3: Test renderizado basico**

```bash
python -c "
import sys; sys.path.insert(0, 'tests/datos_prueba/generador')
from utils.pdf_renderer import renderizar_html
from utils.importes import LineaFactura, ResumenFactura
from datetime import date

lineas = [LineaFactura('Test', 1, 100, 21)]
resumen = ResumenFactura(lineas)
datos = {
    'emisor': {'nombre': 'Test S.L.', 'cif': 'B12345678', 'direccion': 'Calle Test 1', 'email': ''},
    'receptor': {'nombre': 'Cliente', 'cif': 'A87654321', 'direccion': 'Calle Cliente'},
    'factura': {'numero': 'F-001', 'fecha': date(2025,1,15)},
    'lineas': lineas,
    'resumen': resumen,
    'divisa': 'EUR',
    'forma_pago': 'Transferencia',
    'cuenta_bancaria': 'ES12 0049 1234 5678 9012',
    'notas': []
}
html = renderizar_html('factura_estandar.html', datos)
print(f'HTML renderizado: {len(html)} chars')
print('OK' if 'FACTURA' in html else 'ERROR')
"
```

**Paso 4: Commit**

```bash
git add tests/datos_prueba/generador/plantillas/factura_*.html tests/datos_prueba/generador/plantillas/nota_credito.html
git commit -m "feat: 6 plantillas HTML para facturas (estandar, simplificada, extranjera, servicios, credito, restauracion)"
```

---

### Tarea 7: Plantillas HTML secundarias (nominas, bancarios, otros)

**Files:**
- Create: `tests/datos_prueba/generador/plantillas/nomina.html`
- Create: `tests/datos_prueba/generador/plantillas/rlc_ss.html`
- Create: `tests/datos_prueba/generador/plantillas/recibo_bancario.html`
- Create: `tests/datos_prueba/generador/plantillas/recibo_suministro.html`
- Create: `tests/datos_prueba/generador/plantillas/impuesto_tasa.html`
- Create: `tests/datos_prueba/generador/plantillas/subvencion.html`
- Create: `tests/datos_prueba/generador/plantillas/dua_importacion.html`

**Paso 1: nomina.html**

Formato nomina espanola: cabecera empresa + trabajador, devengos (salario base, complementos, horas extra, pagas extra), deducciones (SS trabajador, IRPF, anticipos), liquido a percibir. Incluir periodo liquidacion, categoria profesional, grupo cotizacion.

**Paso 2: rlc_ss.html**

Formato Relacion Liquidacion Cotizaciones: datos empresa, periodo, relacion trabajadores con base cotizacion, cuotas empresa/trabajador por contingencia, total a ingresar.

**Paso 3: recibo_bancario.html**

Formato extracto bancario / recibo: cuota prestamo (desglose capital + intereses), comision bancaria, recibo leasing. Campo para tipo_recibo (prestamo, comision, leasing, renting).

**Paso 4: recibo_suministro.html**

Formato factura de suministro (luz/agua/gas/telefono): datos contrato, periodo facturacion, consumo, desglose (termino fijo + variable), impuesto electrico (si aplica), IVA, total.

**Paso 5: impuesto_tasa.html**

Formato recibo municipal: concepto (IBI, IAE, tasa basuras, IVTM), periodo, referencia catastral (si IBI), datos obligado tributario, importe, fecha limite pago.

**Paso 6: subvencion.html**

Formato resolucion subvencion: organismo concedente, expediente, beneficiario, programa, importe concedido, condiciones, fecha resolucion, firma.

**Paso 7: dua_importacion.html**

Formato simplificado DUA: numero DUA, aduana entrada, origen mercancia, partida arancelaria, valor aduanero, base IVA importacion, cuota IVA (diferido casilla 77).

**Paso 8: Commit**

```bash
git add tests/datos_prueba/generador/plantillas/
git commit -m "feat: 7 plantillas HTML secundarias (nomina, SS, bancario, suministro, impuesto, subvencion, DUA)"
```

---

## Fase C: Generadores

### Tarea 8: gen_facturas.py (facturas compra + venta)

**Files:**
- Create: `tests/datos_prueba/generador/generadores/gen_facturas.py`

**Descripcion:** Generador principal. Para cada entidad, genera facturas de compra (proveedores → entidad) y venta (entidad → clientes) segun su config en empresas.yaml. Cada factura tiene: fecha (distribuida por utils/fechas), lineas (generadas con utils/importes), y se renderiza con la plantilla adecuada.

**Funciones principales:**
- `generar_facturas_compra(entidad, anio, rng) -> List[DocGenerado]`
- `generar_facturas_venta(entidad, anio, rng) -> List[DocGenerado]`
- `_generar_factura_individual(proveedor, fecha, tipo_plantilla, ...) -> DocGenerado`
- `_seleccionar_plantilla(proveedor) -> str` (estandar, extranjera, servicios, simplificada)
- `_generar_numero_factura(proveedor, indice, anio) -> str`

**Estructura DocGenerado:**
```python
@dataclass
class DocGenerado:
    """Documento generado listo para renderizar."""
    archivo: str          # nombre archivo PDF
    tipo: str             # factura_compra, factura_venta, nomina...
    subtipo: str          # estandar, intracomunitaria, simplificada...
    plantilla: str        # nombre plantilla HTML
    css_variante: str     # estilo CSS
    datos_plantilla: dict # variables para Jinja2
    metadatos: dict       # para manifiesto.json (base, iva, total, etc.)
    error_inyectado: str | None  # ID error (E01..E15) o None
    edge_case: str | None        # ID edge case (EC01..EC25) o None
```

**Logica clave:**
- Proveedores intracomunitarios → plantilla extranjera + mencion ISP
- Proveedores extracomunitarios → plantilla extranjera + divisa USD
- Servicios profesionales → plantilla servicios + retencion
- Clientes con retencion (Aytos, etc.) → incluir IRPF en factura venta
- Facturas simplificadas → cuando perfil lo indica (Leroy Merlin, particulares)

**Paso 1:** Implementar DocGenerado dataclass y funciones auxiliares
**Paso 2:** Implementar generar_facturas_compra
**Paso 3:** Implementar generar_facturas_venta
**Paso 4:** Test generando facturas para Aurora Digital
**Paso 5:** Commit

```bash
git add tests/datos_prueba/generador/generadores/gen_facturas.py
git commit -m "feat: gen_facturas.py generador de facturas compra/venta"
```

---

### Tarea 9: gen_nominas.py (nominas + SS)

**Files:**
- Create: `tests/datos_prueba/generador/generadores/gen_nominas.py`

**Funciones:**
- `generar_nominas(entidad, anio, rng) -> List[DocGenerado]`
- `generar_ss(entidad, anio, rng) -> List[DocGenerado]`
- `_generar_nomina_mensual(empleado, mes, anio) -> DocGenerado`
- `_generar_paga_extra(empleado, tipo, anio) -> DocGenerado` (junio, diciembre)
- `_generar_rlc(entidad, mes, anio) -> DocGenerado`

**Logica:**
- 1 nomina por empleado por mes activo (considerar estacionales como Chiringuito abr-oct)
- Pagas extra en junio y diciembre (salvo prorrateadas)
- IRPF segun calcular_irpf_nomina(bruto_anual)
- SS segun CuotaSS con bases del convenio
- RLC mensual con todos los empleados activos ese mes
- Finiquitos para temporales y fin temporada

**Commit:**
```bash
git commit -m "feat: gen_nominas.py generador de nominas y SS"
```

---

### Tarea 10: gen_bancarios.py (prestamos, leasing, comisiones)

**Files:**
- Create: `tests/datos_prueba/generador/generadores/gen_bancarios.py`

**Funciones:**
- `generar_bancarios(entidad, anio, rng) -> List[DocGenerado]`
- `_generar_cuotas_prestamo(producto, anio) -> List[DocGenerado]`
- `_generar_cuotas_leasing(producto, anio) -> List[DocGenerado]`
- `_generar_recibos_renting(producto, anio) -> List[DocGenerado]`
- `_generar_comisiones(entidad, anio, rng) -> List[DocGenerado]`

**Logica:**
- Cuotas mensuales de prestamos (capital + intereses, tabla francesa)
- Cuotas leasing (IVA 21%, opcion compra en ultima cuota)
- Renting como gasto 621 (factura mensual con IVA)
- Comisiones: mantenimiento trimestral, TPV mensual (% ventas), transferencias, descuento comercial
- Poliza credito: comision apertura anual + no disposicion trimestral + intereses disposicion

**Commit:**
```bash
git commit -m "feat: gen_bancarios.py generador de recibos bancarios"
```

---

### Tarea 11: gen_suministros.py + gen_seguros.py + gen_impuestos.py

**Files:**
- Create: `tests/datos_prueba/generador/generadores/gen_suministros.py`
- Create: `tests/datos_prueba/generador/generadores/gen_seguros.py`
- Create: `tests/datos_prueba/generador/generadores/gen_impuestos.py`

**gen_suministros.py:**
- Facturas mensuales de luz, agua, gas, telefono segun perfil entidad
- Importes con variacion estacional (mas electricidad en verano para restaurantes, etc.)
- IVA 21% (electricidad), 10% (agua)

**gen_seguros.py:**
- Recibos anuales o trimestrales, exentos IVA (IPS)
- Tipos: RC, multirriesgo, vehiculos, salud, D&O, accidentes, cosechas, edificio

**gen_impuestos.py:**
- IBI anual o fraccionado, IAE (si facturacion >1M), tasa basuras, IVTM por vehiculo
- Licencia playa Chiringuito (8.000€/temporada)
- Multa no deducible para La Marea (EC20)

**Commit:**
```bash
git commit -m "feat: gen_suministros + gen_seguros + gen_impuestos"
```

---

### Tarea 12: gen_subvenciones.py + gen_intercompany.py

**Files:**
- Create: `tests/datos_prueba/generador/generadores/gen_subvenciones.py`
- Create: `tests/datos_prueba/generador/generadores/gen_intercompany.py`

**gen_subvenciones.py:**
- Resolucion + pagos (1 o 2 plazos)
- Kit Digital (Aurora), contratacion (Distrib.), PAC (Jose Antonio), FEDER (Comunidad), etc.
- Plantilla subvencion.html

**gen_intercompany.py:** (solo Grupo Gastro)
- Management fees mensuales (holding → filiales)
- Intereses prestamos intercompany (trimestrales)
- Dividendos anuales con retencion 19%
- Prestamo cruzado estacional Catering → Chiringuito

**Commit:**
```bash
git commit -m "feat: gen_subvenciones + gen_intercompany"
```

---

### Tarea 13: gen_errores.py (inyector post-generacion)

**Files:**
- Create: `tests/datos_prueba/generador/generadores/gen_errores.py`

**Funciones:**
- `inyectar_errores(documentos: List[DocGenerado], catalogo: dict, rng) -> List[DocGenerado]`
- `_aplicar_error(doc, error_id, parametros) -> DocGenerado`

**Logica:**
- Recibe lista de docs ya generados (sin errores)
- Selecciona ~20% aleatoriamente (usando probabilidades del catalogo)
- Aplica mutacion segun tipo:
  - E01: `generar_cif_invalido()` en datos emisor
  - E02: alterar cuota_iva (+/- desviacion_max)
  - E03: alterar total (no coincide con base+IVA)
  - E04: duplicar un documento (mismo numero+proveedor+fecha)
  - E05: cambiar fecha a 2024
  - E06: cambiar % retencion
  - E07: cambiar tipo IVA
  - E08: eliminar tasaconv en factura USD
  - E09: eliminar numero factura
  - E10: eliminar CIF emisor
  - E11: anadir IVA a operacion exenta
  - E12: eliminar mencion ISP
  - E13: alterar base cotizacion en RLC
  - E14: poner IRPF 0% sin justificacion
  - E15: cambiar nombre receptor
- Marcar doc.error_inyectado = error_id
- Devuelve lista completa (modificados + no modificados)

**IMPORTANTE:** El error se aplica sobre datos_plantilla (pre-renderizado). El PDF final muestra el error visualmente.

**Commit:**
```bash
git commit -m "feat: gen_errores.py inyector de errores deliberados"
```

---

## Fase D: Motor + integracion

### Tarea 14: utils/ruido.py (variacion visual)

**Files:**
- Create: `tests/datos_prueba/generador/utils/ruido.py`

**Funciones:**
- `aplicar_ruido(ruta_pdf: Path, rng) -> Path`

**Efectos aleatorios (1-2 por documento):**
- Rotacion ligera (±0.5-1.5 grados)
- Manchas/marcas de agua sutiles
- Sello "PAGADO" o "RECIBIDO" en facturas pagadas
- Firma escaneada (linea garabateada)
- Ligera variacion de brillo/contraste

**Implementacion:** usar Pillow para post-procesar el PDF renderizado como imagen y volver a guardar. Alternativa: aplicar efectos via CSS en el HTML antes de renderizar (mas simple y limpio).

**Recomendacion:** implementar via CSS/HTML (mas eficiente):
- Sello PAGADO: `<div class="sello-pagado">PAGADO</div>` con rotacion CSS
- Firma: SVG path garabateado insertado en plantilla
- Rotacion: `transform: rotate(0.5deg)` en body
- Esto evita la dependencia de manipulacion de imagenes

**Commit:**
```bash
git commit -m "feat: utils/ruido.py variacion visual para PDFs"
```

---

### Tarea 15: motor.py (orquestador CLI)

**Files:**
- Create: `tests/datos_prueba/generador/motor.py`

**Descripcion:** CLI principal que orquesta todo el proceso de generacion.

**Argumentos:**
- `--todas`: genera para las 11 entidades
- `--entidad NOMBRE`: genera solo para una
- `--trimestre T1|T2|T3|T4`: filtra por trimestre
- `--sin-errores`: no inyecta errores
- `--solo-errores`: regenera errores sobre docs existentes
- `--deploy`: copia salida a clientes/
- `--seed N`: seed para reproducibilidad
- `--año N`: ejercicio fiscal (default 2025)

**Flujo:**
```python
def main():
    args = parse_args()
    rng = random.Random(args.seed) if args.seed else random.Random()

    # 1. Cargar datos
    empresas = cargar_yaml("datos/empresas.yaml")
    errores = cargar_yaml("datos/catalogo_errores.yaml")
    saldos = cargar_yaml("datos/saldos_2024.yaml")

    entidades = filtrar_entidades(empresas, args.entidad)

    for nombre, entidad in entidades.items():
        logger.info(f"=== Generando: {entidad['nombre']} ===")
        dir_salida = DIR_SALIDA / nombre
        dir_inbox = dir_salida / "inbox"
        dir_inbox.mkdir(parents=True, exist_ok=True)

        # 2. Ejecutar generadores
        docs = []
        docs.extend(gen_facturas.generar_facturas_compra(entidad, args.año, rng))
        docs.extend(gen_facturas.generar_facturas_venta(entidad, args.año, rng))
        if entidad.get("empleados_detalle"):
            docs.extend(gen_nominas.generar_nominas(entidad, args.año, rng))
            docs.extend(gen_nominas.generar_ss(entidad, args.año, rng))
        docs.extend(gen_bancarios.generar_bancarios(entidad, args.año, rng))
        docs.extend(gen_suministros.generar_suministros(entidad, args.año, rng))
        docs.extend(gen_seguros.generar_seguros(entidad, args.año, rng))
        docs.extend(gen_impuestos.generar_impuestos(entidad, args.año, rng))
        if entidad.get("subvenciones"):
            docs.extend(gen_subvenciones.generar_subvenciones(entidad, args.año, rng))
        if entidad.get("intercompany"):
            docs.extend(gen_intercompany.generar_intercompany(entidad, args.año, rng))

        # 3. Filtrar por trimestre si aplica
        if args.trimestre:
            docs = [d for d in docs if trimestre_de_fecha(d.metadatos['fecha']) == args.trimestre]

        # 4. Inyectar errores
        if not args.sin_errores:
            docs = gen_errores.inyectar_errores(docs, errores, rng)

        # 5. Renderizar PDFs
        for doc in docs:
            html = renderizar_html(doc.plantilla, doc.datos_plantilla)
            ruta_pdf = dir_inbox / doc.archivo
            html_a_pdf(html, ruta_pdf, doc.css_variante)

        # 6. Generar manifiesto
        manifiesto = generar_manifiesto(nombre, docs, args)
        guardar_json(dir_salida / "manifiesto.json", manifiesto)

        # 7. Generar config.yaml SFCE
        generar_config_sfce(entidad, dir_salida)

        logger.info(f"  Total: {len(docs)} docs, {sum(1 for d in docs if d.error_inyectado)} errores")

    # 8. Deploy si solicitado
    if args.deploy:
        copiar_a_clientes(DIR_SALIDA)

    logger.info("=== Generacion completa ===")
```

**Commit:**
```bash
git add tests/datos_prueba/generador/motor.py
git commit -m "feat: motor.py orquestador CLI del generador de datos prueba"
```

---

### Tarea 16: Integracion - generar Aurora Digital completa

**Paso 1: Ejecutar para una entidad**

```bash
cd tests/datos_prueba/generador
python motor.py --entidad aurora-digital --seed 42
```

**Paso 2: Verificar salida**

```bash
ls -la salida/aurora-digital/inbox/ | head -20
python -c "
import json
m = json.load(open('salida/aurora-digital/manifiesto.json'))
print(f'Total docs: {m[\"total_documentos\"]}')
print(f'Errores: {m[\"errores_inyectados\"][\"total\"]}')
print(f'Edge cases: {m[\"edge_cases\"][\"total\"]}')
"
```

Expected: ~100-110 docs, ~20 con errores, ~15 edge cases.

**Paso 3: Abrir 3-4 PDFs y verificar visualmente que se ven realistas**

**Paso 4: Corregir problemas detectados**

**Paso 5: Commit**

```bash
git commit -m "fix: ajustes integracion generador Aurora Digital"
```

---

### Tarea 17: Generar todas las entidades + verificacion

**Paso 1: Ejecutar completo**

```bash
python motor.py --todas --seed 42
```

**Paso 2: Verificar totales**

```bash
python -c "
import json
from pathlib import Path
total = 0
for m in Path('salida').glob('*/manifiesto.json'):
    data = json.load(open(m))
    print(f'{data[\"entidad\"]}: {data[\"total_documentos\"]} docs ({data[\"errores_inyectados\"][\"total\"]} errores)')
    total += data['total_documentos']
print(f'TOTAL: {total} documentos')
"
```

Expected: ~1.000-1.200 documentos en total.

**Paso 3: Verificar reproducibilidad**

```bash
python motor.py --todas --seed 42
# Comparar manifiestos — deben ser identicos
```

**Paso 4: Commit final**

```bash
git add tests/datos_prueba/
git commit -m "feat: generador datos prueba SFCE completo (11 entidades, ~1100 PDFs)"
```

---

## Resumen de tareas

| # | Tarea | Fase | Archivos | Dependencias |
|---|-------|------|----------|--------------|
| 1 | Estructura + cif.py | A | 2 archivos + dirs | Ninguna |
| 2 | fechas.py + importes.py | A | 2 archivos | Ninguna |
| 3 | pdf_renderer.py | A | 1 archivo | Ninguna |
| 4 | Datos YAML (4 archivos) | A | 4 archivos | cif.py (para generar CIFs) |
| 5 | CSS base + variantes | B | 5 archivos | Ninguna |
| 6 | Plantillas HTML facturas | B | 6 archivos | Ninguna |
| 7 | Plantillas HTML secundarias | B | 7 archivos | Ninguna |
| 8 | gen_facturas.py | C | 1 archivo | 1-6 |
| 9 | gen_nominas.py | C | 1 archivo | 1-5,7 |
| 10 | gen_bancarios.py | C | 1 archivo | 1-5,7 |
| 11 | gen_suministros+seguros+impuestos | C | 3 archivos | 1-5,7 |
| 12 | gen_subvenciones+intercompany | C | 2 archivos | 1-5,7 |
| 13 | gen_errores.py | C | 1 archivo | 1 (cif.py) |
| 14 | ruido.py | D | 1 archivo | Ninguna |
| 15 | motor.py | D | 1 archivo | 1-13 |
| 16 | Integracion Aurora Digital | D | 0 (fixes) | 1-15 |
| 17 | Generacion completa + verificacion | D | 0 (fixes) | 1-16 |

**Paralelizacion posible:**
- Tareas 1, 2, 3: en paralelo (sin dependencias)
- Tareas 5, 6, 7: en paralelo (sin dependencias)
- Tareas 8-13: en paralelo entre si (todas dependen de A+B)
- Tareas 14: independiente
- Tareas 15-17: secuenciales (integracion)

**Total archivos nuevos:** ~42 archivos
**Estimacion:** 4-5 sesiones de Claude
