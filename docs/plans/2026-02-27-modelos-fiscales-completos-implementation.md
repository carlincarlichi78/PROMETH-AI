# Modelos Fiscales Completos — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Sistema completo de generacion de ~28 modelos fiscales AEAT con fichero BOE posicional/XML, PDF visual y dashboard para el gestor.

**Architecture:** Motor generico (MotorBOE) lee especificaciones YAML por modelo y genera ficheros posicionales. CalculadorModelos expandido calcula casillas. GeneradorPDF rellena PDFs oficiales. API FastAPI expone endpoints. Dashboard React con 4 paginas nuevas.

**Tech Stack:** Python 3.11+, pytest, FastAPI, SQLAlchemy, React 18, TypeScript, Tailwind v4, pdfrw, WeasyPrint, openpyxl, lxml

**Design doc:** `docs/plans/2026-02-27-modelos-fiscales-completos-design.md`

---

## Fase A: Motor generico (T1-T8)

### Task 1: Estructura base modulos + tipos

**Files:**
- Create: `sfce/modelos_fiscales/__init__.py`
- Create: `sfce/modelos_fiscales/tipos.py`
- Create: `sfce/modelos_fiscales/disenos/`
- Test: `tests/test_modelos_fiscales/test_tipos.py`

**Step 1: Write the failing test**

```python
# tests/test_modelos_fiscales/__init__.py
# (vacio)

# tests/test_modelos_fiscales/test_tipos.py
from sfce.modelos_fiscales.tipos import (
    CampoSpec, RegistroSpec, ValidacionSpec, DisenoModelo,
    TipoCampo, ResultadoGeneracion, ResultadoValidacion
)

class TestTipos:
    def test_campo_spec_alfanumerico(self):
        campo = CampoSpec(
            nombre="nif",
            posicion=(9, 17),
            tipo=TipoCampo.ALFANUMERICO,
            fuente="nif_declarante"
        )
        assert campo.longitud == 9
        assert campo.tipo == TipoCampo.ALFANUMERICO

    def test_campo_spec_numerico_con_decimales(self):
        campo = CampoSpec(
            nombre="casilla_01",
            posicion=(68, 85),
            tipo=TipoCampo.NUMERICO_SIGNO,
            decimales=2,
            fuente="casillas.01"
        )
        assert campo.longitud == 18
        assert campo.decimales == 2

    def test_campo_spec_valor_fijo(self):
        campo = CampoSpec(
            nombre="tipo_registro",
            posicion=(1, 1),
            tipo=TipoCampo.ALFANUMERICO,
            valor_fijo="1"
        )
        assert campo.valor_fijo == "1"
        assert campo.fuente is None

    def test_registro_spec(self):
        campos = [
            CampoSpec(nombre="tipo", posicion=(1, 1), tipo=TipoCampo.ALFANUMERICO, valor_fijo="1"),
            CampoSpec(nombre="modelo", posicion=(2, 4), tipo=TipoCampo.NUMERICO, valor_fijo="303"),
        ]
        registro = RegistroSpec(tipo="cabecera", campos=campos)
        assert registro.tipo == "cabecera"
        assert len(registro.campos) == 2

    def test_validacion_spec(self):
        val = ValidacionSpec(
            regla="casilla_27 == casilla_01 + casilla_03",
            nivel="error",
            mensaje="IVA devengado no cuadra"
        )
        assert val.nivel == "error"

    def test_diseno_modelo(self):
        diseno = DisenoModelo(
            modelo="303",
            version="2025",
            tipo_formato="posicional",
            longitud_registro=500,
            registros=[],
            validaciones=[]
        )
        assert diseno.modelo == "303"
        assert diseno.tipo_formato == "posicional"

    def test_resultado_generacion(self):
        res = ResultadoGeneracion(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            contenido="1303202500000...",
            formato="posicional",
            nombre_fichero="B12345678_2025_1T.303"
        )
        assert res.nombre_fichero == "B12345678_2025_1T.303"

    def test_resultado_validacion_ok(self):
        res = ResultadoValidacion(valido=True, errores=[], advertencias=[])
        assert res.valido is True

    def test_resultado_validacion_con_errores(self):
        res = ResultadoValidacion(
            valido=False,
            errores=["Casilla 27 no cuadra"],
            advertencias=["Casilla 78 vacia"]
        )
        assert not res.valido
        assert len(res.errores) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_modelos_fiscales/test_tipos.py -v`
Expected: FAIL (imports no existen)

**Step 3: Write minimal implementation**

```python
# sfce/modelos_fiscales/__init__.py
"""Motor de generacion de modelos fiscales AEAT."""

# sfce/modelos_fiscales/tipos.py
"""Tipos base para especificaciones de modelos fiscales."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TipoCampo(Enum):
    ALFANUMERICO = "alfanumerico"
    NUMERICO = "numerico"
    NUMERICO_SIGNO = "numerico_signo"
    FECHA = "fecha"
    TELEFONO = "telefono"


@dataclass
class CampoSpec:
    """Especificacion de un campo en el diseno de registro."""
    nombre: str
    posicion: tuple[int, int]  # (inicio, fin) — 1-indexed inclusive
    tipo: TipoCampo
    fuente: Optional[str] = None
    valor_fijo: Optional[str] = None
    decimales: int = 0
    descripcion: str = ""

    @property
    def longitud(self) -> int:
        return self.posicion[1] - self.posicion[0] + 1


@dataclass
class RegistroSpec:
    """Especificacion de un tipo de registro (cabecera, detalle, etc.)."""
    tipo: str
    campos: list[CampoSpec] = field(default_factory=list)


@dataclass
class ValidacionSpec:
    """Regla de validacion interna del modelo."""
    regla: str
    nivel: str = "error"  # "error" | "advertencia"
    mensaje: str = ""


@dataclass
class DisenoModelo:
    """Especificacion completa de un modelo fiscal."""
    modelo: str
    version: str
    tipo_formato: str  # "posicional" | "xml"
    longitud_registro: int
    registros: list[RegistroSpec] = field(default_factory=list)
    validaciones: list[ValidacionSpec] = field(default_factory=list)


@dataclass
class ResultadoGeneracion:
    """Resultado de generar un fichero BOE."""
    modelo: str
    ejercicio: str
    periodo: str
    contenido: str
    formato: str
    nombre_fichero: str


@dataclass
class ResultadoValidacion:
    """Resultado de validar casillas contra reglas AEAT."""
    valido: bool
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_modelos_fiscales/test_tipos.py -v`
Expected: PASS (9 tests)

**Step 5: Commit**

```bash
git add sfce/modelos_fiscales/ tests/test_modelos_fiscales/
git commit -m "feat: tipos base modelos fiscales (CampoSpec, DisenoModelo, etc.)"
```

---

### Task 2: Cargador YAML — leer especificaciones de disco

**Files:**
- Create: `sfce/modelos_fiscales/cargador.py`
- Create: `sfce/modelos_fiscales/disenos/303.yaml` (spec minima para test)
- Test: `tests/test_modelos_fiscales/test_cargador.py`

**Step 1: Write the failing test**

```python
# tests/test_modelos_fiscales/test_cargador.py
import pytest
from pathlib import Path
from sfce.modelos_fiscales.cargador import CargadorDisenos
from sfce.modelos_fiscales.tipos import DisenoModelo, TipoCampo


class TestCargadorDisenos:
    def test_cargar_303(self):
        cargador = CargadorDisenos()
        diseno = cargador.cargar("303")
        assert isinstance(diseno, DisenoModelo)
        assert diseno.modelo == "303"
        assert diseno.tipo_formato == "posicional"
        assert diseno.longitud_registro > 0
        assert len(diseno.registros) >= 1

    def test_cargar_modelo_inexistente(self):
        cargador = CargadorDisenos()
        with pytest.raises(FileNotFoundError):
            cargador.cargar("999")

    def test_cargar_desde_directorio_custom(self, tmp_path):
        yaml_content = """
modelo: "TEST"
version: "2025"
tipo_formato: posicional
longitud_registro: 100
registros:
  - tipo: cabecera
    campos:
      - nombre: tipo_registro
        posicion: [1, 1]
        tipo: alfanumerico
        valor_fijo: "1"
      - nombre: modelo
        posicion: [2, 5]
        tipo: numerico
        valor_fijo: "0TEST"
validaciones: []
"""
        (tmp_path / "TEST.yaml").write_text(yaml_content, encoding="utf-8")
        cargador = CargadorDisenos(directorio=tmp_path)
        diseno = cargador.cargar("TEST")
        assert diseno.modelo == "TEST"
        assert diseno.registros[0].campos[0].tipo == TipoCampo.ALFANUMERICO

    def test_campos_parseados_correctamente(self):
        cargador = CargadorDisenos()
        diseno = cargador.cargar("303")
        cabecera = diseno.registros[0]
        assert cabecera.tipo == "cabecera"
        primer_campo = cabecera.campos[0]
        assert primer_campo.nombre == "tipo_registro"
        assert primer_campo.posicion == (1, 1)

    def test_listar_modelos_disponibles(self):
        cargador = CargadorDisenos()
        disponibles = cargador.listar_disponibles()
        assert "303" in disponibles

    def test_validaciones_parseadas(self):
        cargador = CargadorDisenos()
        diseno = cargador.cargar("303")
        assert len(diseno.validaciones) >= 1
        assert diseno.validaciones[0].nivel in ("error", "advertencia")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_modelos_fiscales/test_cargador.py -v`
Expected: FAIL (imports no existen)

**Step 3: Create 303.yaml minimal spec + CargadorDisenos**

Crear `sfce/modelos_fiscales/disenos/303.yaml` con especificacion inicial del modelo 303 (cabecera + detalle con casillas principales: 01, 03, 05, 07, 09, 11, 27, 28, 29, 31, 33, 35, 37, 45, 69, 78). Las posiciones deben seguir el diseno de registro oficial publicado en la Sede AEAT.

```python
# sfce/modelos_fiscales/cargador.py
"""Cargador de especificaciones YAML de modelos fiscales."""
import yaml
from pathlib import Path
from sfce.modelos_fiscales.tipos import (
    CampoSpec, RegistroSpec, ValidacionSpec, DisenoModelo, TipoCampo
)

_DIRECTORIO_DEFECTO = Path(__file__).parent / "disenos"


class CargadorDisenos:
    """Carga y parsea YAMLs de diseno de registro."""

    def __init__(self, directorio: Path | None = None):
        self._directorio = directorio or _DIRECTORIO_DEFECTO

    def cargar(self, modelo: str) -> DisenoModelo:
        ruta = self._directorio / f"{modelo}.yaml"
        if not ruta.exists():
            raise FileNotFoundError(f"Diseno no encontrado: {ruta}")

        with open(ruta, encoding="utf-8") as f:
            datos = yaml.safe_load(f)

        return self._parsear(datos)

    def listar_disponibles(self) -> list[str]:
        return sorted(
            p.stem for p in self._directorio.glob("*.yaml")
        )

    def _parsear(self, datos: dict) -> DisenoModelo:
        registros = []
        for reg_data in datos.get("registros", []):
            campos = [self._parsear_campo(c) for c in reg_data.get("campos", [])]
            registros.append(RegistroSpec(tipo=reg_data["tipo"], campos=campos))

        validaciones = [
            ValidacionSpec(
                regla=v["regla"],
                nivel=v.get("nivel", "error"),
                mensaje=v.get("mensaje", "")
            )
            for v in datos.get("validaciones", [])
        ]

        return DisenoModelo(
            modelo=datos["modelo"],
            version=datos["version"],
            tipo_formato=datos.get("tipo_formato", "posicional"),
            longitud_registro=datos.get("longitud_registro", 0),
            registros=registros,
            validaciones=validaciones
        )

    def _parsear_campo(self, datos: dict) -> CampoSpec:
        pos = datos["posicion"]
        return CampoSpec(
            nombre=datos["nombre"],
            posicion=(pos[0], pos[1]),
            tipo=TipoCampo(datos["tipo"]),
            fuente=datos.get("fuente"),
            valor_fijo=datos.get("valor_fijo"),
            decimales=datos.get("decimales", 0),
            descripcion=datos.get("descripcion", "")
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_modelos_fiscales/test_cargador.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add sfce/modelos_fiscales/cargador.py sfce/modelos_fiscales/disenos/ tests/test_modelos_fiscales/test_cargador.py
git commit -m "feat: cargador YAML disenos de registro + spec 303 inicial"
```

---

### Task 3: MotorBOE — generador posicional generico

**Files:**
- Create: `sfce/modelos_fiscales/motor_boe.py`
- Test: `tests/test_modelos_fiscales/test_motor_boe.py`

**Step 1: Write the failing test**

```python
# tests/test_modelos_fiscales/test_motor_boe.py
import pytest
from sfce.modelos_fiscales.motor_boe import MotorBOE
from sfce.modelos_fiscales.tipos import (
    CampoSpec, RegistroSpec, DisenoModelo, TipoCampo, ResultadoGeneracion
)


def _diseno_simple() -> DisenoModelo:
    """Diseno de test: 50 chars, 3 campos."""
    return DisenoModelo(
        modelo="TEST",
        version="2025",
        tipo_formato="posicional",
        longitud_registro=50,
        registros=[
            RegistroSpec(tipo="unico", campos=[
                CampoSpec(nombre="tipo", posicion=(1, 1), tipo=TipoCampo.ALFANUMERICO, valor_fijo="1"),
                CampoSpec(nombre="modelo", posicion=(2, 5), tipo=TipoCampo.NUMERICO, valor_fijo="0303"),
                CampoSpec(nombre="nif", posicion=(6, 14), tipo=TipoCampo.ALFANUMERICO, fuente="nif_declarante"),
                CampoSpec(nombre="importe", posicion=(15, 30), tipo=TipoCampo.NUMERICO_SIGNO, decimales=2, fuente="casillas.01"),
            ])
        ],
        validaciones=[]
    )


class TestMotorBOE:
    def test_generar_linea_basica(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno,
            ejercicio="2025",
            periodo="1T",
            casillas={"01": 15234.50},
            empresa={"nif": "B12345678", "nombre": "TEST SL"}
        )
        assert isinstance(resultado, ResultadoGeneracion)
        assert len(resultado.contenido) == 50
        # tipo_registro
        assert resultado.contenido[0] == "1"
        # modelo
        assert resultado.contenido[1:5] == "0303"
        # nif (9 chars, relleno espacios derecha)
        assert resultado.contenido[5:14] == "B12345678"

    def test_numerico_signo_positivo(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={"01": 15234.50},
            empresa={"nif": "B12345678"}
        )
        # posicion 15-30 = 16 chars, numerico_signo: " 00000001523450"
        campo_importe = resultado.contenido[14:30]
        assert campo_importe[0] == " "  # positivo
        assert "1523450" in campo_importe

    def test_numerico_signo_negativo(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={"01": -500.25},
            empresa={"nif": "B12345678"}
        )
        campo_importe = resultado.contenido[14:30]
        assert campo_importe[0] == "N"  # negativo

    def test_nombre_fichero(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={"01": 0},
            empresa={"nif": "B12345678"}
        )
        assert resultado.nombre_fichero == "B12345678_2025_1T.TEST"

    def test_casilla_faltante_usa_cero(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={},  # sin casilla 01
            empresa={"nif": "B12345678"}
        )
        # debe generar sin error, con 0
        assert len(resultado.contenido) == 50

    def test_alfanumerico_trunca_si_largo(self):
        motor = MotorBOE()
        diseno = _diseno_simple()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={"01": 0},
            empresa={"nif": "B12345678901234"}  # mas largo que 9 chars
        )
        # trunca a longitud del campo
        assert len(resultado.contenido) == 50

    def test_multiples_registros(self):
        diseno = DisenoModelo(
            modelo="MULTI", version="2025", tipo_formato="posicional",
            longitud_registro=20,
            registros=[
                RegistroSpec(tipo="cabecera", campos=[
                    CampoSpec(nombre="tipo", posicion=(1, 1), tipo=TipoCampo.ALFANUMERICO, valor_fijo="1"),
                ]),
                RegistroSpec(tipo="detalle", campos=[
                    CampoSpec(nombre="tipo", posicion=(1, 1), tipo=TipoCampo.ALFANUMERICO, valor_fijo="2"),
                ]),
            ],
            validaciones=[]
        )
        motor = MotorBOE()
        resultado = motor.generar(
            diseno=diseno, ejercicio="2025", periodo="1T",
            casillas={}, empresa={"nif": "X"}
        )
        lineas = resultado.contenido.split("\r\n")
        assert len(lineas) == 2
        assert lineas[0][0] == "1"
        assert lineas[1][0] == "2"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_modelos_fiscales/test_motor_boe.py -v`
Expected: FAIL (MotorBOE no existe)

**Step 3: Write MotorBOE implementation**

```python
# sfce/modelos_fiscales/motor_boe.py
"""Motor generico de generacion de ficheros BOE posicionales."""
from sfce.modelos_fiscales.tipos import (
    CampoSpec, DisenoModelo, TipoCampo, ResultadoGeneracion
)


class MotorBOE:
    """Genera ficheros en formato BOE posicional desde un DisenoModelo."""

    def generar(
        self,
        diseno: DisenoModelo,
        ejercicio: str,
        periodo: str,
        casillas: dict,
        empresa: dict
    ) -> ResultadoGeneracion:
        lineas = []
        for registro in diseno.registros:
            linea = self._generar_registro(
                registro, diseno.longitud_registro,
                ejercicio, periodo, casillas, empresa
            )
            lineas.append(linea)

        nif = empresa.get("nif", "")
        nombre_fichero = f"{nif}_{ejercicio}_{periodo}.{diseno.modelo}"
        contenido = "\r\n".join(lineas) if len(lineas) > 1 else lineas[0]

        return ResultadoGeneracion(
            modelo=diseno.modelo,
            ejercicio=ejercicio,
            periodo=periodo,
            contenido=contenido,
            formato=diseno.tipo_formato,
            nombre_fichero=nombre_fichero
        )

    def _generar_registro(
        self, registro, longitud, ejercicio, periodo, casillas, empresa
    ) -> str:
        linea = list(" " * longitud)
        for campo in registro.campos:
            valor = self._resolver_valor(campo, ejercicio, periodo, casillas, empresa)
            formateado = self._formatear_campo(campo, valor)
            inicio = campo.posicion[0] - 1  # 1-indexed -> 0-indexed
            for i, char in enumerate(formateado):
                if inicio + i < longitud:
                    linea[inicio + i] = char
        return "".join(linea)

    def _resolver_valor(self, campo, ejercicio, periodo, casillas, empresa):
        if campo.valor_fijo is not None:
            return campo.valor_fijo
        fuente = campo.fuente or ""
        if fuente == "ejercicio":
            return ejercicio
        if fuente == "periodo":
            return periodo
        if fuente == "nif_declarante":
            return empresa.get("nif", "")
        if fuente.startswith("casillas."):
            clave = fuente.split(".", 1)[1]
            return casillas.get(clave, 0)
        if fuente.startswith("empresa."):
            clave = fuente.split(".", 1)[1]
            return empresa.get(clave, "")
        return ""

    def _formatear_campo(self, campo: CampoSpec, valor) -> str:
        longitud = campo.longitud
        if campo.tipo == TipoCampo.ALFANUMERICO:
            texto = str(valor)[:longitud]
            return texto.ljust(longitud)
        if campo.tipo == TipoCampo.NUMERICO:
            texto = str(int(valor)) if isinstance(valor, (int, float)) else str(valor)
            texto = texto[:longitud]
            return texto.zfill(longitud)
        if campo.tipo == TipoCampo.NUMERICO_SIGNO:
            num = float(valor) if valor else 0.0
            signo = "N" if num < 0 else " "
            abs_val = abs(num)
            entero = int(abs_val * (10 ** campo.decimales))
            parte_num = str(entero).zfill(longitud - 1)[:longitud - 1]
            return signo + parte_num
        if campo.tipo == TipoCampo.FECHA:
            texto = str(valor)[:longitud]
            return texto.zfill(longitud)
        if campo.tipo == TipoCampo.TELEFONO:
            texto = str(valor)[:longitud]
            return texto.zfill(longitud)
        return str(valor)[:longitud].ljust(longitud)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_modelos_fiscales/test_motor_boe.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add sfce/modelos_fiscales/motor_boe.py tests/test_modelos_fiscales/test_motor_boe.py
git commit -m "feat: MotorBOE generico — generacion ficheros posicionales AEAT"
```

---

### Task 4: Validador — reglas AEAT por modelo

**Files:**
- Create: `sfce/modelos_fiscales/validador.py`
- Test: `tests/test_modelos_fiscales/test_validador.py`

**Step 1: Write the failing test**

```python
# tests/test_modelos_fiscales/test_validador.py
import pytest
from sfce.modelos_fiscales.validador import ValidadorModelo
from sfce.modelos_fiscales.tipos import ValidacionSpec, ResultadoValidacion


class TestValidadorModelo:
    def test_validacion_ok(self):
        validaciones = [
            ValidacionSpec(regla="casilla_27 == casilla_01 + casilla_03", nivel="error", mensaje="No cuadra")
        ]
        casillas = {"casilla_01": 1000, "casilla_03": 500, "casilla_27": 1500}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True
        assert len(resultado.errores) == 0

    def test_validacion_falla(self):
        validaciones = [
            ValidacionSpec(regla="casilla_27 == casilla_01 + casilla_03", nivel="error", mensaje="IVA no cuadra")
        ]
        casillas = {"casilla_01": 1000, "casilla_03": 500, "casilla_27": 999}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is False
        assert "IVA no cuadra" in resultado.errores[0]

    def test_advertencia_no_invalida(self):
        validaciones = [
            ValidacionSpec(regla="casilla_78 > 0", nivel="advertencia", mensaje="Compensacion vacia")
        ]
        casillas = {"casilla_78": 0}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True  # advertencia no invalida
        assert len(resultado.advertencias) == 1

    def test_multiples_validaciones(self):
        validaciones = [
            ValidacionSpec(regla="casilla_27 == casilla_01", nivel="error", mensaje="E1"),
            ValidacionSpec(regla="casilla_45 == casilla_27 - casilla_37", nivel="error", mensaje="E2"),
            ValidacionSpec(regla="casilla_78 >= 0", nivel="advertencia", mensaje="W1"),
        ]
        casillas = {"casilla_01": 100, "casilla_27": 100, "casilla_37": 30, "casilla_45": 70, "casilla_78": -5}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True  # las reglas error pasan
        assert len(resultado.advertencias) == 1  # casilla_78 < 0

    def test_casilla_faltante_es_cero(self):
        validaciones = [
            ValidacionSpec(regla="casilla_99 == 0", nivel="error", mensaje="Debe ser cero")
        ]
        casillas = {}  # casilla_99 no existe, debe ser 0
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True

    def test_operaciones_soportadas(self):
        """Soporta: ==, !=, >, >=, <, <=, +, -, *, abs()"""
        validaciones = [
            ValidacionSpec(regla="abs(casilla_01 - casilla_02) < 0.01", nivel="error", mensaje="Diff")
        ]
        casillas = {"casilla_01": 100.005, "casilla_02": 100.001}
        resultado = ValidadorModelo.validar(casillas, validaciones)
        assert resultado.valido is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_modelos_fiscales/test_validador.py -v`
Expected: FAIL

**Step 3: Write ValidadorModelo**

Implementar `ValidadorModelo.validar(casillas, validaciones)` que:
- Parsea cada `regla` como expresion Python segura (solo aritmetica + comparacion)
- Reemplaza `casilla_XX` por el valor del dict (0 si no existe)
- Evalua con `eval()` restringido (solo builtins: abs, round, min, max)
- Clasifica resultado segun `nivel`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_modelos_fiscales/test_validador.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add sfce/modelos_fiscales/validador.py tests/test_modelos_fiscales/test_validador.py
git commit -m "feat: validador reglas AEAT por modelo (expresiones aritmeticas seguras)"
```

---

### Task 5: Orquestador — clase GeneradorModelos que une todo

**Files:**
- Create: `sfce/modelos_fiscales/generador.py`
- Test: `tests/test_modelos_fiscales/test_generador.py`

**Step 1: Write the failing test**

```python
# tests/test_modelos_fiscales/test_generador.py
import pytest
from pathlib import Path
from sfce.modelos_fiscales.generador import GeneradorModelos
from sfce.modelos_fiscales.tipos import ResultadoGeneracion, ResultadoValidacion


class TestGeneradorModelos:
    def test_generar_303(self):
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303",
            ejercicio="2025",
            periodo="1T",
            casillas={
                "01": 10000.00,  # base general
                "03": 2100.00,   # cuota general
                "27": 2100.00,   # total devengado
                "28": 10000.00,  # total bases soportado
                "29": 2100.00,   # total cuotas soportado
                "37": 2100.00,   # total deducible
                "45": 0.00,      # resultado
                "69": 0.00,      # resultado liquidacion
            },
            empresa={"nif": "B12345678", "nombre": "TEST SL", "nombre_fiscal": "TEST SL"}
        )
        assert isinstance(resultado, ResultadoGeneracion)
        assert resultado.modelo == "303"
        assert len(resultado.contenido) > 0

    def test_validar_303(self):
        gen = GeneradorModelos()
        resultado = gen.validar(
            modelo="303",
            casillas={"01": 10000, "03": 2100, "27": 2100, "37": 2100, "45": 0}
        )
        assert isinstance(resultado, ResultadoValidacion)
        assert resultado.valido is True

    def test_validar_303_falla(self):
        gen = GeneradorModelos()
        resultado = gen.validar(
            modelo="303",
            casillas={"01": 10000, "03": 2100, "27": 999, "37": 2100, "45": 0}
        )
        assert resultado.valido is False

    def test_modelos_disponibles(self):
        gen = GeneradorModelos()
        disponibles = gen.modelos_disponibles()
        assert "303" in disponibles

    def test_guardar_fichero(self, tmp_path):
        gen = GeneradorModelos()
        resultado = gen.generar(
            modelo="303", ejercicio="2025", periodo="1T",
            casillas={"01": 0, "27": 0, "37": 0, "45": 0, "69": 0},
            empresa={"nif": "B12345678"}
        )
        ruta = gen.guardar(resultado, directorio=tmp_path)
        assert ruta.exists()
        assert ruta.name == "B12345678_2025_1T.303"
        contenido = ruta.read_text(encoding="latin-1")
        assert len(contenido) > 0
```

**Step 2: Run test, Step 3: Implement, Step 4: Verify, Step 5: Commit**

```python
# sfce/modelos_fiscales/generador.py
"""Orquestador: une cargador + motor + validador."""
from pathlib import Path
from sfce.modelos_fiscales.cargador import CargadorDisenos
from sfce.modelos_fiscales.motor_boe import MotorBOE
from sfce.modelos_fiscales.validador import ValidadorModelo
from sfce.modelos_fiscales.tipos import ResultadoGeneracion, ResultadoValidacion


class GeneradorModelos:
    def __init__(self, directorio_disenos: Path | None = None):
        self._cargador = CargadorDisenos(directorio=directorio_disenos)
        self._motor = MotorBOE()

    def generar(self, modelo, ejercicio, periodo, casillas, empresa) -> ResultadoGeneracion:
        diseno = self._cargador.cargar(modelo)
        return self._motor.generar(diseno, ejercicio, periodo, casillas, empresa)

    def validar(self, modelo, casillas) -> ResultadoValidacion:
        diseno = self._cargador.cargar(modelo)
        casillas_prefijadas = {f"casilla_{k}": v for k, v in casillas.items()}
        return ValidadorModelo.validar(casillas_prefijadas, diseno.validaciones)

    def modelos_disponibles(self) -> list[str]:
        return self._cargador.listar_disponibles()

    def guardar(self, resultado: ResultadoGeneracion, directorio: Path) -> Path:
        directorio.mkdir(parents=True, exist_ok=True)
        ruta = directorio / resultado.nombre_fichero
        ruta.write_text(resultado.contenido, encoding="latin-1")
        return ruta
```

Commit: `feat: GeneradorModelos orquestador (cargador + motor + validador)`

---

### Task 6: Disenos YAML — modelos IVA (303, 390, 349, 347)

**Files:**
- Create: `sfce/modelos_fiscales/disenos/390.yaml`
- Create: `sfce/modelos_fiscales/disenos/349.yaml`
- Create: `sfce/modelos_fiscales/disenos/347.yaml`
- Test: `tests/test_modelos_fiscales/test_disenos_iva.py`

**Contexto**: Los disenos de registro oficiales se publican en [Sede AEAT — Disenos de registro](https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro.html). Cada uno es un Excel con posiciones, tipos y longitudes. Para esta tarea:

1. Descargar los Excel DR de cada modelo desde la AEAT
2. Extraer posiciones de campos y casillas
3. Crear YAML con la estructura definida en Task 2
4. Test: cargar cada YAML, verificar que tiene registros y campos coherentes

**Step 1: Write tests que verifican estructura de cada YAML**

```python
# tests/test_modelos_fiscales/test_disenos_iva.py
import pytest
from sfce.modelos_fiscales.cargador import CargadorDisenos


class TestDisenos:
    @pytest.fixture
    def cargador(self):
        return CargadorDisenos()

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_carga_sin_error(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert diseno.modelo == modelo

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_tiene_registros(self, cargador, modelo):
        diseno = cargador.cargar(modelo)
        assert len(diseno.registros) >= 1

    @pytest.mark.parametrize("modelo", ["303", "390", "349", "347"])
    def test_campos_no_se_solapan(self, cargador, modelo):
        """Verifica que las posiciones de campos no se solapan."""
        diseno = cargador.cargar(modelo)
        for registro in diseno.registros:
            posiciones = sorted(campo.posicion for campo in registro.campos)
            for i in range(1, len(posiciones)):
                assert posiciones[i][0] > posiciones[i-1][1], \
                    f"Solapamiento en {modelo}: {posiciones[i-1]} y {posiciones[i]}"

    def test_303_tiene_casillas_principales(self, cargador):
        diseno = cargador.cargar("303")
        nombres = {c.nombre for reg in diseno.registros for c in reg.campos}
        for casilla in ["casilla_01", "casilla_03", "casilla_27", "casilla_37", "casilla_45"]:
            assert casilla in nombres, f"Falta {casilla} en 303"

    def test_347_tiene_registro_declarados(self, cargador):
        """347 tiene cabecera + N registros de declarados."""
        diseno = cargador.cargar("347")
        tipos = [r.tipo for r in diseno.registros]
        assert "cabecera" in tipos or "tipo1" in tipos
```

**Step 2-5**: Crear YAMLs, run tests, commit.

Commit: `feat: disenos YAML IVA (303, 390, 349, 347)`

---

### Task 7: Disenos YAML — retenciones + IRPF (111, 190, 115, 180, 123, 193, 130, 131)

**Files:**
- Create: 8 YAMLs en `sfce/modelos_fiscales/disenos/`
- Test: `tests/test_modelos_fiscales/test_disenos_retenciones.py`

Mismo patron que Task 6. Parametrizar tests para los 8 modelos.
Verificar: registros, no solapamiento, casillas principales.

Commit: `feat: disenos YAML retenciones + IRPF (111, 190, 115, 180, 123, 193, 130, 131)`

---

### Task 8: Disenos YAML — sociedades, censal, no residentes, otros (200, 202, 220, 036, 037, 210, 211, 216, 296, 184, 345, 720, 360, 340, 420, 100)

**Files:**
- Create: 16 YAMLs en `sfce/modelos_fiscales/disenos/`
- Create: `sfce/modelos_fiscales/motor_xml.py` (para modelo 200 que usa XML/XSD)
- Test: `tests/test_modelos_fiscales/test_disenos_resto.py`
- Test: `tests/test_modelos_fiscales/test_motor_xml.py`

**Nota modelo 200**: usa formato XML con esquema XSD (`mod200YYYY.xsd`). Crear `MotorXML` que genera XML desde YAML con estructura de nodos en vez de posiciones.

```python
# sfce/modelos_fiscales/motor_xml.py
class MotorXML:
    """Genera ficheros XML para modelos que usan formato XSD (ej: 200)."""
    def generar(self, diseno, ejercicio, periodo, casillas, empresa) -> ResultadoGeneracion:
        # Construir arbol XML desde diseno.registros (tipo="nodo_xml")
        # Validar contra XSD si disponible
        ...
```

Commit: `feat: disenos YAML restantes + MotorXML para modelo 200`

---

## Fase B: Calculadores expandidos (T9-T16)

Referencia: `sfce/core/calculador_modelos.py` tiene 7 metodos. Necesitamos ~12 mas.
Referencia: `sfce/db/repositorio.py` tiene `pyg()`, `balance()`, `saldo_subcuenta()`.

### Task 9: Queries repositorio — datos para calculadores

**Files:**
- Modify: `sfce/db/repositorio.py`
- Test: `tests/test_modelos_fiscales/test_repositorio_fiscal.py`

**Nuevos metodos en Repositorio**:

```python
def iva_por_periodo(self, empresa_id: int, ejercicio: str, periodo: str) -> dict:
    """Retorna IVA repercutido/soportado agrupado por tipo.
    Returns: {
        repercutido: {general: {base, cuota}, reducido: {...}, ...},
        soportado: {general: {base, cuota}, ...},
        total_repercutido: float,
        total_soportado: float
    }"""

def retenciones_por_periodo(self, empresa_id: int, ejercicio: str, periodo: str) -> dict:
    """Retenciones practicadas agrupadas por tipo.
    Returns: {trabajo: float, profesionales: float, alquileres: float, capital: float}"""

def operaciones_terceros(self, empresa_id: int, ejercicio: str) -> list[dict]:
    """Ops >3.005,06 EUR para modelo 347.
    Returns: [{cif, nombre, importe_total, tipo}]"""

def operaciones_intracomunitarias(self, empresa_id: int, ejercicio: str, periodo: str) -> list[dict]:
    """Ops intra-UE para modelo 349.
    Returns: [{cif, nombre, pais, importe, tipo_operacion}]"""

def nominas_por_periodo(self, empresa_id: int, ejercicio: str, periodo: str) -> dict:
    """Datos de nominas para modelos 111/190.
    Returns: {bruto_total, ss_empresa, irpf_retenido, num_perceptores}"""

def alquileres_por_periodo(self, empresa_id: int, ejercicio: str, periodo: str) -> dict:
    """Datos alquileres para modelos 115/180."""

def rendimientos_capital(self, empresa_id: int, ejercicio: str, periodo: str) -> dict:
    """Datos capital mobiliario para modelos 123/193."""
```

Tests: verificar que cada query retorna estructura correcta con datos de test en SQLite.

Commit: `feat: queries repositorio fiscal (IVA, retenciones, ops terceros, intracomunitarias)`

---

### Task 10: Expandir CalculadorModelos — retenciones (115, 180, 123, 193)

**Files:**
- Modify: `sfce/core/calculador_modelos.py`
- Modify: `tests/test_calculador_modelos.py`

**Nuevos metodos**:

```python
def calcular_115(self, retenciones_alquileres: float, trimestre: str, ejercicio: int) -> dict:
    """Modelo 115 — retenciones arrendamientos."""

def calcular_180(self, datos_anuales: list[dict], ejercicio: int) -> dict:
    """Modelo 180 — resumen anual retenciones alquileres.
    datos_anuales: [{nif_arrendador, nombre, importe, retencion}]"""

def calcular_123(self, rendimientos_capital: float, retenciones: float,
                  trimestre: str, ejercicio: int) -> dict:
    """Modelo 123 — retenciones capital mobiliario."""

def calcular_193(self, datos_anuales: list[dict], ejercicio: int) -> dict:
    """Modelo 193 — resumen anual capital mobiliario."""
```

Tests: 2 tests por metodo (caso basico + caso borde).
Commit: `feat: calculadores 115, 180, 123, 193 (retenciones alquileres + capital)`

---

### Task 11: Expandir CalculadorModelos — IRPF modulos + IS (131, 202)

**Files:**
- Modify: `sfce/core/calculador_modelos.py`
- Modify: `tests/test_calculador_modelos.py`

```python
def calcular_131(self, rendimiento_modulos: float, pagos_anteriores: float,
                  trimestre: str, ejercicio: int) -> dict:
    """Modelo 131 — pago fraccionado IRPF regimen objetiva/modulos."""

def calcular_202(self, cuota_is_anterior: float, base_imponible_acumulada: float,
                  modalidad: str, ejercicio: int) -> dict:
    """Modelo 202 — pagos fraccionados IS.
    modalidad: 'art40.2' (cuota anterior) | 'art40.3' (base imponible periodo)"""
```

Commit: `feat: calculadores 131, 202 (IRPF modulos + pagos fraccionados IS)`

---

### Task 12: Expandir CalculadorModelos — no residentes + especiales (210, 216, 349 completo, 420)

**Files:**
- Modify: `sfce/core/calculador_modelos.py`
- Modify: `tests/test_calculador_modelos.py`

```python
def calcular_349(self, operaciones: list[dict], periodo: str, ejercicio: int) -> dict:
    """Modelo 349 — declaracion recapitulativa operaciones intracomunitarias.
    Expandir el existente con desglose por tipo operacion (A/E/T/S/I/M)."""

def calcular_420(self, igic_repercutido: float, igic_soportado: float,
                  trimestre: str, ejercicio: int) -> dict:
    """Modelo 420 — IGIC Canarias (equivalente 303 pero con tipos IGIC)."""

def calcular_210(self, tipo_renta: str, base_imponible: float,
                  tipo_gravamen: float, ejercicio: int) -> dict:
    """Modelo 210 — IRNR sin establecimiento permanente."""

def calcular_216(self, retenciones_no_residentes: float, trimestre: str, ejercicio: int) -> dict:
    """Modelo 216 — retenciones no residentes."""
```

Commit: `feat: calculadores 349, 420, 210, 216 (intracomunitarias, IGIC, no residentes)`

---

### Task 13: Servicio fiscal — orquesta repositorio + calculador + generador

**Files:**
- Create: `sfce/core/servicio_fiscal.py`
- Test: `tests/test_modelos_fiscales/test_servicio_fiscal.py`

Clase `ServicioFiscal` que:
1. Recibe `empresa_id`, `modelo`, `ejercicio`, `periodo`
2. Consulta datos del `Repositorio` apropiados para ese modelo
3. Pasa datos al `CalculadorModelos` para obtener casillas
4. Pasa casillas al `GeneradorModelos` para generar BOE + validar
5. Retorna casillas + fichero + validacion

```python
class ServicioFiscal:
    def __init__(self, repositorio: Repositorio, normativa: Normativa):
        self.repo = repositorio
        self.calculador = CalculadorModelos(normativa)
        self.generador = GeneradorModelos()

    def calcular_casillas(self, empresa_id, modelo, ejercicio, periodo) -> dict:
        """Calcula casillas desde datos contables."""

    def generar_modelo(self, empresa_id, modelo, ejercicio, periodo,
                        casillas_override: dict | None = None) -> dict:
        """Genera modelo completo: casillas + fichero BOE + validacion.
        casillas_override: casillas editadas manualmente por el gestor."""

    def calendario_fiscal(self, empresa_id, ejercicio) -> list[dict]:
        """Modelos obligatorios + plazos + estado (pendiente/generado/presentado)."""
```

Commit: `feat: ServicioFiscal orquestador (repositorio + calculador + generador)`

---

## Fase C: GeneradorPDF (T14-T15)

### Task 14: GeneradorPDF — rellenar PDFs oficiales AEAT

**Files:**
- Create: `sfce/modelos_fiscales/generador_pdf.py`
- Create: `sfce/modelos_fiscales/plantillas_pdf/` (directorio)
- Test: `tests/test_modelos_fiscales/test_generador_pdf.py`

**Dependencia**: `pip install pdfrw` (o `pypdf`)

Implementar `GeneradorPDF`:
1. Lee PDF plantilla (formulario rellenable) desde `plantillas_pdf/`
2. Mapeo campo_pdf → casilla via YAML (`mapeo_pdf` seccion nueva en diseno)
3. Rellena campos del formulario
4. Genera PDF final

```python
class GeneradorPDF:
    def generar(self, modelo: str, casillas: dict, empresa: dict,
                ejercicio: str, periodo: str) -> bytes:
        """Retorna bytes del PDF rellenado."""

    def guardar(self, pdf_bytes: bytes, directorio: Path, nombre: str) -> Path:
        """Guarda PDF en disco."""
```

**Nota**: Las plantillas PDF se descargan manualmente de la AEAT (formularios en blanco) y se almacenan en `plantillas_pdf/`. Si un modelo no tiene PDF rellenable, usar fallback HTML.

Commit: `feat: GeneradorPDF — rellena PDFs oficiales AEAT`

---

### Task 15: Fallback HTML→PDF con WeasyPrint

**Files:**
- Create: `sfce/modelos_fiscales/plantillas_html/base_modelo.html`
- Modify: `sfce/modelos_fiscales/generador_pdf.py` (agregar fallback)
- Test: `tests/test_modelos_fiscales/test_generador_pdf.py` (agregar test fallback)

Plantilla Jinja2 generica que:
- Muestra cabecera con datos del modelo (numero, nombre, ejercicio, periodo)
- Tabla de casillas con numero, descripcion, valor
- Pie con datos empresa

Commit: `feat: fallback HTML→PDF para modelos sin formulario AEAT`

---

## Fase D: API + Dashboard (T16-T22)

### Task 16: Schemas Pydantic para modelos fiscales

**Files:**
- Modify: `sfce/api/schemas.py`
- Test: `tests/test_modelos_fiscales/test_schemas.py`

**Nuevos schemas**:

```python
class CasillaOut(BaseModel):
    numero: str
    descripcion: str
    valor: float
    editable: bool = False

class ModeloFiscalCalcOut(BaseModel):
    modelo: str
    ejercicio: str
    periodo: str
    casillas: list[CasillaOut]
    validacion: ResultadoValidacionOut

class ResultadoValidacionOut(BaseModel):
    valido: bool
    errores: list[str]
    advertencias: list[str]

class GenerarModeloIn(BaseModel):
    empresa_id: int
    modelo: str
    ejercicio: str
    periodo: str
    casillas_override: dict[str, float] | None = None

class CalendarioFiscalOut(BaseModel):
    modelo: str
    nombre: str
    periodo: str
    fecha_limite: str
    estado: str  # "pendiente" | "generado" | "presentado"

class HistoricoModeloOut(BaseModel):
    modelo: str
    ejercicio: str
    periodo: str
    fecha_generacion: str
    ruta_boe: str | None
    ruta_pdf: str | None
```

Commit: `feat: schemas Pydantic modelos fiscales`

---

### Task 17: Router API /api/modelos/

**Files:**
- Create: `sfce/api/rutas/modelos.py`
- Modify: `sfce/api/app.py` (registrar router)
- Test: `tests/test_modelos_fiscales/test_api_modelos.py`

**Endpoints**:

```python
router = APIRouter(prefix="/api/modelos", tags=["modelos"])

@router.get("/disponibles")
async def listar_modelos() -> list[str]:
    """Lista modelos con diseno YAML disponible."""

@router.post("/calcular")
async def calcular_casillas(datos: GenerarModeloIn) -> ModeloFiscalCalcOut:
    """Calcula casillas desde datos contables."""

@router.post("/validar")
async def validar_modelo(datos: GenerarModeloIn) -> ResultadoValidacionOut:
    """Valida casillas contra reglas AEAT."""

@router.post("/generar-boe")
async def generar_boe(datos: GenerarModeloIn) -> FileResponse:
    """Genera fichero BOE y lo retorna como descarga."""

@router.post("/generar-pdf")
async def generar_pdf(datos: GenerarModeloIn) -> FileResponse:
    """Genera PDF visual y lo retorna como descarga."""

@router.get("/calendario/{empresa_id}/{ejercicio}")
async def calendario_fiscal(empresa_id: int, ejercicio: str) -> list[CalendarioFiscalOut]:
    """Calendario de obligaciones fiscales."""

@router.get("/historico/{empresa_id}")
async def historico(empresa_id: int) -> list[HistoricoModeloOut]:
    """Modelos generados anteriormente."""
```

Commit: `feat: router API /api/modelos/ (7 endpoints)`

---

### Task 18: Dashboard — pagina CalendarioFiscal

**Files:**
- Create: `dashboard/src/pages/ModelosFiscales.tsx`
- Modify: `dashboard/src/App.tsx` (agregar ruta)

Pagina con:
- Vista trimestral (T1/T2/T3/T4) + anuales
- Cards por modelo: nombre, estado (pendiente/generado/presentado), fecha limite
- Color: rojo si vencido, amarillo si proximo, verde si presentado
- Boton "Generar" en cada card

Commit: `feat: dashboard pagina CalendarioFiscal`

---

### Task 19: Dashboard — pagina GenerarModelo

**Files:**
- Create: `dashboard/src/pages/GenerarModelo.tsx`
- Modify: `dashboard/src/App.tsx` (agregar ruta)

Pagina con:
- Selector: empresa, modelo, periodo
- Boton "Calcular" → llama POST /api/modelos/calcular
- Tabla de casillas: numero, descripcion, valor (editables las marcadas)
- Indicador validacion (OK/errores/advertencias)
- Botones: "Descargar BOE" y "Descargar PDF"

Commit: `feat: dashboard pagina GenerarModelo (casillas + descarga)`

---

### Task 20: Dashboard — pagina HistoricoModelos

**Files:**
- Create: `dashboard/src/pages/HistoricoModelos.tsx`
- Modify: `dashboard/src/App.tsx` (agregar ruta)

Pagina con:
- Tabla: modelo, ejercicio, periodo, fecha generacion, acciones (descargar BOE/PDF)
- Filtros: empresa, ejercicio, modelo
- Paginacion

Commit: `feat: dashboard pagina HistoricoModelos`

---

### Task 21: Integration test E2E — generar 303 completo

**Files:**
- Test: `tests/test_modelos_fiscales/test_e2e_303.py`

Test end-to-end:
1. Insertar datos contables de prueba en SQLite (facturas con IVA)
2. Calcular casillas via ServicioFiscal
3. Validar casillas
4. Generar fichero BOE
5. Verificar formato posicional (longitudes, tipos, posiciones)
6. Generar PDF
7. Verificar que PDF tiene contenido

Commit: `test: E2E modelo 303 — datos → casillas → BOE → PDF`

---

### Task 22: Integration test — generar 111 + 130 + 347

**Files:**
- Test: `tests/test_modelos_fiscales/test_e2e_otros.py`

Mismo patron que Task 21 pero para modelos 111, 130, 347.
Verificar que cada uno genera fichero BOE valido con datos coherentes.

Commit: `test: E2E modelos 111, 130, 347`

---

## Fase E: Polish + actualizacion anual (T23-T26)

### Task 23: Script actualizar_disenos.py — Excel AEAT → YAML

**Files:**
- Create: `scripts/actualizar_disenos.py`
- Test: `tests/test_modelos_fiscales/test_actualizar_disenos.py`

Script CLI que:
1. Lee un Excel de diseno de registro AEAT (openpyxl)
2. Parsea columnas: posicion, longitud, tipo, descripcion, casilla
3. Genera YAML con la estructura de `DisenoModelo`
4. Compara con version anterior y reporta cambios

```bash
python scripts/actualizar_disenos.py --excel DR303e25v101.xlsx --modelo 303 --ejercicio 2025
```

Commit: `feat: script conversor Excel AEAT → YAML disenos de registro`

---

### Task 24: Tests golden files — ficheros BOE de referencia

**Files:**
- Create: `tests/test_modelos_fiscales/golden/` (directorio)
- Create: `tests/test_modelos_fiscales/golden/303_basico.txt`
- Test: `tests/test_modelos_fiscales/test_golden.py`

Generar ficheros BOE de referencia con datos conocidos. Comparar byte a byte en tests.
Si el formato cambia (bug o actualizacion), el test falla y hay que actualizar el golden file.

Commit: `test: golden files — ficheros BOE de referencia para regresion`

---

### Task 25: Almacenar modelos generados en BD

**Files:**
- Modify: `sfce/db/modelos.py` (nueva tabla ModeloFiscalGenerado)
- Modify: `sfce/db/repositorio.py` (CRUD modelos generados)
- Modify: `sfce/core/servicio_fiscal.py` (persistir al generar)
- Test: `tests/test_modelos_fiscales/test_persistencia.py`

Nueva tabla:

```python
class ModeloFiscalGenerado(Base):
    __tablename__ = "modelos_fiscales_generados"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    modelo = Column(String(10), nullable=False)
    ejercicio = Column(String(4), nullable=False)
    periodo = Column(String(10), nullable=False)
    casillas_json = Column(Text)  # JSON con todas las casillas
    ruta_boe = Column(String(500))
    ruta_pdf = Column(String(500))
    estado = Column(String(20), default="generado")  # generado|presentado
    fecha_generacion = Column(DateTime, default=func.now())
    fecha_presentacion = Column(DateTime, nullable=True)
    validacion_ok = Column(Boolean, default=True)
    notas = Column(Text, nullable=True)
```

Commit: `feat: persistencia modelos fiscales generados en BD`

---

### Task 26: Documentacion + tests finales

**Files:**
- Modify: tests existentes (verificar coverage >80%)
- Run: `pytest tests/test_modelos_fiscales/ -v --tb=short`

Verificar:
- Todos los tests pasan
- Coverage >80% en `sfce/modelos_fiscales/`
- Todos los YAMLs cargan sin error
- Al menos 303, 111, 130, 347 generan fichero BOE valido

Commit: `test: cobertura completa modelos fiscales (>80%)`

---

## Resumen

| Fase | Tasks | Descripcion |
|------|-------|-------------|
| A | T1-T8 | Motor generico (tipos, cargador, MotorBOE, validador, orquestador, 28 YAMLs, MotorXML) |
| B | T9-T13 | Calculadores expandidos (queries repo, 115/180/123/193, 131/202, 349/420/210/216, servicio fiscal) |
| C | T14-T15 | GeneradorPDF (rellenar PDF AEAT + fallback HTML) |
| D | T16-T22 | API + Dashboard (schemas, router, 3 paginas, 2 tests E2E) |
| E | T23-T26 | Polish (conversor Excel, golden files, persistencia BD, tests finales) |

**Total: 26 tasks, ~28 modelos fiscales.**
**Estimacion**: Los YAMLs de diseno (T6-T8) son los mas laboriosos porque requieren parsear los Excel oficiales de la AEAT. El motor generico (T1-T5) y los calculadores (T9-T12) son mas directos.
