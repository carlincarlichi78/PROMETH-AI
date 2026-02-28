"""Tests E2E modelos 111, 130 y 347 — datos → BOE → disco."""
import pytest
from pathlib import Path

from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.repositorio import Repositorio
from sfce.db.modelos import Empresa
from sfce.core.servicio_fiscal import ServicioFiscal
from sfce.modelos_fiscales.generador import GeneradorModelos
from sfce.normativa.vigente import Normativa


# ─────────────────────────── fixtures compartidos ────────────────

@pytest.fixture
def motor_bd():
    """Motor SQLite en memoria para cada test."""
    motor = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
    inicializar_bd(motor)
    return motor


@pytest.fixture
def repo(motor_bd):
    """Repositorio con BD en memoria limpia."""
    sesion_factory = crear_sesion(motor_bd)
    return Repositorio(sesion_factory)


@pytest.fixture
def empresa_prueba(repo):
    """Inserta empresa de prueba y retorna instancia."""
    empresa = Empresa(
        nombre="AUTONOMO TEST",
        cif="12345678Z",
        forma_juridica="autonomo",
        activa=True,
    )
    repo.crear(empresa)
    return empresa


@pytest.fixture
def servicio(repo):
    """ServicioFiscal con normativa real."""
    normativa = Normativa()
    return ServicioFiscal(repo, normativa)


@pytest.fixture
def empresa_datos():
    return {"nif": "12345678Z", "nombre": "AUTONOMO TEST"}


@pytest.fixture
def generador():
    return GeneradorModelos()


# ─────────────────────────── helpers ─────────────────────────────

def _verificar_boe_basico(contenido: str, modelo: str, longitud_esperada: int = 500):
    """Verifica propiedades minimas de un fichero BOE posicional."""
    assert contenido, "El contenido BOE no debe estar vacio"
    assert len(contenido) == longitud_esperada, (
        f"Longitud BOE debe ser {longitud_esperada}, es {len(contenido)}"
    )
    assert contenido[0] == "1", (
        f"Primer caracter debe ser '1' (tipo_registro), es '{contenido[0]}'"
    )
    assert contenido[1:4] == modelo, (
        f"Posiciones 2-4 deben ser '{modelo}', son '{contenido[1:4]}'"
    )


def _verificar_nombre_fichero(nombre: str, nif: str, ejercicio: str,
                               periodo: str, modelo: str):
    """Verifica el formato del nombre de fichero BOE."""
    esperado = f"{nif}_{ejercicio}_{periodo}.{modelo}"
    assert nombre == esperado, (
        f"Nombre fichero esperado '{esperado}', obtenido '{nombre}'"
    )


# ─────────────────────────── modelo 111 ──────────────────────────

CASILLAS_111 = {
    "02": 5000.0,   # importe rendimientos trabajo
    "03": 500.0,    # retenciones trabajo
    "05": 2000.0,   # importe actividades profesionales
    "06": 200.0,    # retenciones profesionales
    "28": 700.0,    # total retenciones
    "30": 700.0,    # resultado
}


class TestE2E111:
    """Tests E2E para el modelo 111 — Retenciones trabajo/profesionales."""

    def test_casillas_devuelven_dict_no_vacio(self, servicio, empresa_prueba):
        resultado = servicio.calcular_casillas(
            empresa_id=empresa_prueba.id,
            modelo="111",
            ejercicio="2025",
            periodo="1T",
        )
        assert isinstance(resultado["casillas"], dict)
        assert len(resultado["casillas"]) > 0

    def test_generar_boe_111(self, generador, empresa_datos):
        resultado = generador.generar(
            modelo="111",
            ejercicio="2025",
            periodo="1T",
            casillas=CASILLAS_111,
            empresa=empresa_datos,
        )
        assert resultado.contenido
        assert len(resultado.contenido) > 0

    def test_boe_111_longitud_500(self, generador, empresa_datos):
        resultado = generador.generar(
            modelo="111",
            ejercicio="2025",
            periodo="1T",
            casillas=CASILLAS_111,
            empresa=empresa_datos,
        )
        _verificar_boe_basico(resultado.contenido, "111")

    def test_boe_111_nombre_fichero(self, generador, empresa_datos):
        resultado = generador.generar(
            modelo="111",
            ejercicio="2025",
            periodo="1T",
            casillas=CASILLAS_111,
            empresa=empresa_datos,
        )
        _verificar_nombre_fichero(
            resultado.nombre_fichero, "12345678Z", "2025", "1T", "111"
        )

    def test_guardar_111_en_disco(self, generador, empresa_datos, tmp_path):
        resultado = generador.generar(
            modelo="111",
            ejercicio="2025",
            periodo="1T",
            casillas=CASILLAS_111,
            empresa=empresa_datos,
        )
        ruta = generador.guardar(resultado, tmp_path)
        assert ruta.exists()
        assert ruta.stat().st_size > 0
        assert ruta.name == "12345678Z_2025_1T.111"

    def test_111_flujo_completo_via_servicio(self, servicio, empresa_prueba, empresa_datos):
        """Flujo completo con override de casillas via ServicioFiscal."""
        resultado = servicio.generar_modelo(
            empresa_id=empresa_prueba.id,
            modelo="111",
            ejercicio="2025",
            periodo="1T",
            casillas_override=CASILLAS_111,
            empresa_datos=empresa_datos,
        )
        assert "contenido_boe" in resultado
        assert len(resultado["contenido_boe"]) > 0
        assert resultado["nombre_fichero"] == "12345678Z_2025_1T.111"

    def test_111_validacion_casillas(self, generador):
        resultado = generador.validar("111", CASILLAS_111)
        assert hasattr(resultado, "valido")
        # Casillas coherentes no deben tener errores criticos
        assert isinstance(resultado.errores, list)


# ─────────────────────────── modelo 130 ──────────────────────────

CASILLAS_130 = {
    "01": 50000.0,  # ingresos acumulados
    "02": 20000.0,  # gastos deducibles acumulados
    "03": 30000.0,  # rendimiento neto (01 - 02)
    "05": 6000.0,   # cuota (03 × 20%)
    "18": 6000.0,   # resultado
    "19": 6000.0,   # resultado de la liquidacion
}


class TestE2E130:
    """Tests E2E para el modelo 130 — Pago fraccionado IRPF."""

    def test_casillas_devuelven_dict_no_vacio(self, servicio, empresa_prueba):
        resultado = servicio.calcular_casillas(
            empresa_id=empresa_prueba.id,
            modelo="130",
            ejercicio="2025",
            periodo="1T",
        )
        assert isinstance(resultado["casillas"], dict)
        assert len(resultado["casillas"]) > 0

    def test_generar_boe_130(self, generador, empresa_datos):
        resultado = generador.generar(
            modelo="130",
            ejercicio="2025",
            periodo="1T",
            casillas=CASILLAS_130,
            empresa=empresa_datos,
        )
        assert resultado.contenido
        assert len(resultado.contenido) > 0

    def test_boe_130_longitud_500(self, generador, empresa_datos):
        resultado = generador.generar(
            modelo="130",
            ejercicio="2025",
            periodo="1T",
            casillas=CASILLAS_130,
            empresa=empresa_datos,
        )
        _verificar_boe_basico(resultado.contenido, "130")

    def test_boe_130_nombre_fichero(self, generador, empresa_datos):
        resultado = generador.generar(
            modelo="130",
            ejercicio="2025",
            periodo="1T",
            casillas=CASILLAS_130,
            empresa=empresa_datos,
        )
        _verificar_nombre_fichero(
            resultado.nombre_fichero, "12345678Z", "2025", "1T", "130"
        )

    def test_guardar_130_en_disco(self, generador, empresa_datos, tmp_path):
        resultado = generador.generar(
            modelo="130",
            ejercicio="2025",
            periodo="1T",
            casillas=CASILLAS_130,
            empresa=empresa_datos,
        )
        ruta = generador.guardar(resultado, tmp_path)
        assert ruta.exists()
        assert ruta.stat().st_size > 0
        assert ruta.name == "12345678Z_2025_1T.130"

    def test_130_flujo_completo_via_servicio(self, servicio, empresa_prueba, empresa_datos):
        resultado = servicio.generar_modelo(
            empresa_id=empresa_prueba.id,
            modelo="130",
            ejercicio="2025",
            periodo="1T",
            casillas_override=CASILLAS_130,
            empresa_datos=empresa_datos,
        )
        assert "contenido_boe" in resultado
        assert len(resultado["contenido_boe"]) > 0
        assert resultado["nombre_fichero"] == "12345678Z_2025_1T.130"

    def test_130_periodos_distintos(self, generador, empresa_datos):
        """El modelo 130 puede generarse para todos los trimestres."""
        for periodo in ["1T", "2T", "3T", "4T"]:
            resultado = generador.generar(
                modelo="130",
                ejercicio="2025",
                periodo=periodo,
                casillas=CASILLAS_130,
                empresa=empresa_datos,
            )
            assert len(resultado.contenido) == 500
            assert resultado.nombre_fichero.endswith(f".130")
            assert periodo in resultado.nombre_fichero

    def test_130_validacion_casillas(self, generador):
        resultado = generador.validar("130", CASILLAS_130)
        assert hasattr(resultado, "valido")
        assert isinstance(resultado.errores, list)


# ─────────────────────────── modelo 347 ──────────────────────────

CASILLAS_347_VACIO = {
    "num_declarados": 0,
    "declarados": [],
}


class TestE2E347:
    """Tests E2E para el modelo 347 — Operaciones con terceros."""

    def test_casillas_bd_vacia_devuelven_dict(self, servicio, empresa_prueba):
        resultado = servicio.calcular_casillas(
            empresa_id=empresa_prueba.id,
            modelo="347",
            ejercicio="2025",
            periodo="0A",
        )
        assert isinstance(resultado["casillas"], dict)
        assert resultado["modelo"] == "347"

    def test_347_sin_declarados_genera_boe(self, generador, empresa_datos):
        """El 347 puede estar vacio (sin operaciones > 3.005 EUR)."""
        resultado = generador.generar(
            modelo="347",
            ejercicio="2025",
            periodo="0A",
            casillas=CASILLAS_347_VACIO,
            empresa=empresa_datos,
        )
        assert resultado.contenido
        assert len(resultado.contenido) > 0

    def test_347_boe_registros_posicionales(self, generador, empresa_datos):
        """El 347 genera registro tipo1 (cabecera) siempre de 500 chars.
        El tipo2 (detalle) se genera aunque no haya declarados (registro vacio).
        """
        resultado = generador.generar(
            modelo="347",
            ejercicio="2025",
            periodo="0A",
            casillas=CASILLAS_347_VACIO,
            empresa=empresa_datos,
        )
        # El 347 genera tipo1 + tipo2 (aunque vacio). El contenido puede ser
        # un registro (500) o dos registros separados por \r\n (1002).
        assert len(resultado.contenido) >= 500
        # El primer registro siempre empieza con "1347"
        primer_registro = resultado.contenido[:500]
        assert primer_registro[0] == "1"
        assert primer_registro[1:4] == "347"

    def test_347_nombre_fichero_formato(self, generador, empresa_datos):
        resultado = generador.generar(
            modelo="347",
            ejercicio="2025",
            periodo="0A",
            casillas=CASILLAS_347_VACIO,
            empresa=empresa_datos,
        )
        _verificar_nombre_fichero(
            resultado.nombre_fichero, "12345678Z", "2025", "0A", "347"
        )

    def test_guardar_347_en_disco(self, generador, empresa_datos, tmp_path):
        resultado = generador.generar(
            modelo="347",
            ejercicio="2025",
            periodo="0A",
            casillas=CASILLAS_347_VACIO,
            empresa=empresa_datos,
        )
        ruta = generador.guardar(resultado, tmp_path)
        assert ruta.exists()
        assert ruta.stat().st_size > 0
        assert ruta.name == "12345678Z_2025_0A.347"

    def test_347_con_declarados_genera_mas_de_un_registro(self, generador, empresa_datos):
        """Con declarados explicitos, el 347 genera tipo1 + N registros tipo2."""
        declarados = [
            {"nif": "B87654321", "nombre": "PROVEEDOR GRANDE S.L.",
             "importe_anual": 15000.0, "importe_1t": 15000.0,
             "importe_2t": 0.0, "importe_3t": 0.0, "importe_4t": 0.0,
             "clave_operacion": "A", "provincia": "29"},
        ]
        casillas_con_declarados = {
            "num_declarados": 1,
            "importe_total": 15000.0,
        }
        resultado = generador.generar(
            modelo="347",
            ejercicio="2025",
            periodo="0A",
            casillas=casillas_con_declarados,
            empresa=empresa_datos,
            declarados=declarados,
        )
        # Tipo1 (500) + \r\n (2) + Tipo2 (500) = 1002 chars
        assert len(resultado.contenido) > 500
        # El segundo registro empieza con "2" (tipo_registro detalle)
        lineas = resultado.contenido.split("\r\n")
        assert len(lineas) >= 2
        assert lineas[1][0] == "2"

    def test_347_flujo_completo_via_servicio(self, servicio, empresa_prueba, empresa_datos):
        resultado = servicio.generar_modelo(
            empresa_id=empresa_prueba.id,
            modelo="347",
            ejercicio="2025",
            periodo="0A",
            casillas_override=CASILLAS_347_VACIO,
            empresa_datos=empresa_datos,
        )
        assert "contenido_boe" in resultado
        assert len(resultado["contenido_boe"]) > 0
        assert resultado["nombre_fichero"] == "12345678Z_2025_0A.347"
