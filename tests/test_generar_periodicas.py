"""Tests para scripts/generar_periodicas.py — Operaciones periodicas automaticas.

TDD: tests primero, implementacion despues.
Estructura: obtener_operaciones_pendientes, generar_asiento_periodico, ejecutar_periodicas
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch, call


# Importaciones del modulo a implementar
from scripts.generar_periodicas import (
    obtener_operaciones_pendientes,
    generar_asiento_periodico,
    ejecutar_periodicas,
    _es_pendiente_en_mes,
    _fecha_ejecucion_en_mes,
)


# ---------------------------------------------------------------------------
# Fixtures de datos de prueba
# ---------------------------------------------------------------------------

def _op(
    id_=1, empresa_id=1,
    tipo="amortizacion", descripcion="Amort. vehiculo",
    periodicidad="mensual", dia_ejecucion=1,
    ultimo_ejecutado=None, activa=True,
    parametros=None,
):
    """Crea un objeto mock de OperacionPeriodica."""
    op = MagicMock()
    op.id = id_
    op.empresa_id = empresa_id
    op.tipo = tipo
    op.descripcion = descripcion
    op.periodicidad = periodicidad
    op.dia_ejecucion = dia_ejecucion
    op.ultimo_ejecutado = ultimo_ejecutado
    op.activa = activa
    op.parametros = parametros or {
        "subcuenta_debe": "6810000000",
        "subcuenta_haber": "2810000000",
        "importe": "400.00",
    }
    return op


def _sesion_mock_con_ops(ops: list):
    """Crea una sesion BD mock que devuelve las operaciones dadas."""
    sesion = MagicMock()
    # scalars().all() pattern
    sesion.scalars.return_value.all.return_value = ops
    return sesion


# ---------------------------------------------------------------------------
# Tests: _es_pendiente_en_mes
# ---------------------------------------------------------------------------

class TestEsPendienteEnMes:
    def test_mensual_nunca_ejecutada(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=None)
        assert _es_pendiente_en_mes(op, "2025-06") is True

    def test_mensual_ejecutada_mismo_mes(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=date(2025, 6, 1))
        assert _es_pendiente_en_mes(op, "2025-06") is False

    def test_mensual_ejecutada_mes_anterior(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=date(2025, 5, 31))
        assert _es_pendiente_en_mes(op, "2025-06") is True

    def test_trimestral_mes_correcto(self):
        # Trimestral: meses 1,4,7,10
        op = _op(periodicidad="trimestral", ultimo_ejecutado=None)
        assert _es_pendiente_en_mes(op, "2025-01") is True
        assert _es_pendiente_en_mes(op, "2025-04") is True
        assert _es_pendiente_en_mes(op, "2025-07") is True
        assert _es_pendiente_en_mes(op, "2025-10") is True

    def test_trimestral_mes_incorrecto(self):
        op = _op(periodicidad="trimestral", ultimo_ejecutado=None)
        assert _es_pendiente_en_mes(op, "2025-02") is False
        assert _es_pendiente_en_mes(op, "2025-03") is False
        assert _es_pendiente_en_mes(op, "2025-05") is False
        assert _es_pendiente_en_mes(op, "2025-06") is False
        assert _es_pendiente_en_mes(op, "2025-08") is False
        assert _es_pendiente_en_mes(op, "2025-11") is False

    def test_trimestral_ya_ejecutada_en_trimestre(self):
        op = _op(periodicidad="trimestral", ultimo_ejecutado=date(2025, 4, 1))
        # Ya ejecutada en el Q2, no volver a ejecutar en abril
        assert _es_pendiente_en_mes(op, "2025-04") is False

    def test_anual_mes_correcto(self):
        # Anual: solo el mes de inicio (1 = enero por defecto)
        op = _op(periodicidad="anual", ultimo_ejecutado=None)
        assert _es_pendiente_en_mes(op, "2025-01") is True

    def test_anual_mes_incorrecto(self):
        op = _op(periodicidad="anual", ultimo_ejecutado=None)
        assert _es_pendiente_en_mes(op, "2025-06") is False

    def test_anual_ya_ejecutada_este_ano(self):
        op = _op(periodicidad="anual", ultimo_ejecutado=date(2025, 1, 1))
        assert _es_pendiente_en_mes(op, "2025-01") is False

    def test_anual_ejecutada_ano_anterior_pendiente(self):
        op = _op(periodicidad="anual", ultimo_ejecutado=date(2024, 1, 1))
        assert _es_pendiente_en_mes(op, "2025-01") is True

    def test_inactiva_nunca_pendiente(self):
        op = _op(activa=False, periodicidad="mensual", ultimo_ejecutado=None)
        assert _es_pendiente_en_mes(op, "2025-06") is False


# ---------------------------------------------------------------------------
# Tests: _fecha_ejecucion_en_mes
# ---------------------------------------------------------------------------

class TestFechaEjecucionEnMes:
    def test_dia_1(self):
        op = _op(dia_ejecucion=1)
        fecha = _fecha_ejecucion_en_mes(op, "2025-06")
        assert fecha == date(2025, 6, 1)

    def test_dia_15(self):
        op = _op(dia_ejecucion=15)
        fecha = _fecha_ejecucion_en_mes(op, "2025-06")
        assert fecha == date(2025, 6, 15)

    def test_dia_31_en_mes_30(self):
        # Febrero tiene 28/29 dias — ajustar al ultimo dia del mes
        op = _op(dia_ejecucion=31)
        fecha = _fecha_ejecucion_en_mes(op, "2025-02")
        assert fecha == date(2025, 2, 28)

    def test_dia_31_en_mes_31(self):
        op = _op(dia_ejecucion=31)
        fecha = _fecha_ejecucion_en_mes(op, "2025-01")
        assert fecha == date(2025, 1, 31)


# ---------------------------------------------------------------------------
# Tests: obtener_operaciones_pendientes
# ---------------------------------------------------------------------------

class TestObtenerOperacionesPendientes:
    def test_sin_operaciones(self):
        sesion = _sesion_mock_con_ops([])
        resultado = obtener_operaciones_pendientes(1, "2025-06", sesion_bd=sesion)
        assert resultado == []

    def test_una_operacion_pendiente_mensual(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=None)
        sesion = _sesion_mock_con_ops([op])
        resultado = obtener_operaciones_pendientes(1, "2025-06", sesion_bd=sesion)
        assert len(resultado) == 1
        assert resultado[0]["operacion_id"] == 1
        assert resultado[0]["fecha_ejecucion"] == date(2025, 6, 1)

    def test_excluye_ya_ejecutada_mismo_mes(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=date(2025, 6, 1))
        sesion = _sesion_mock_con_ops([op])
        resultado = obtener_operaciones_pendientes(1, "2025-06", sesion_bd=sesion)
        assert resultado == []

    def test_excluye_inactiva(self):
        op = _op(activa=False, periodicidad="mensual")
        sesion = _sesion_mock_con_ops([op])
        resultado = obtener_operaciones_pendientes(1, "2025-06", sesion_bd=sesion)
        assert resultado == []

    def test_filtra_trimestral_mes_incorrecto(self):
        op = _op(periodicidad="trimestral", ultimo_ejecutado=None)
        sesion = _sesion_mock_con_ops([op])
        resultado = obtener_operaciones_pendientes(1, "2025-06", sesion_bd=sesion)
        assert resultado == []

    def test_filtra_trimestral_mes_correcto(self):
        op = _op(periodicidad="trimestral", ultimo_ejecutado=None)
        sesion = _sesion_mock_con_ops([op])
        resultado = obtener_operaciones_pendientes(1, "2025-07", sesion_bd=sesion)
        assert len(resultado) == 1

    def test_multiples_ops_mezcla(self):
        op_activa = _op(id_=1, periodicidad="mensual", ultimo_ejecutado=None)
        op_ya_ejecutada = _op(id_=2, periodicidad="mensual", ultimo_ejecutado=date(2025, 6, 1))
        op_inactiva = _op(id_=3, activa=False)
        sesion = _sesion_mock_con_ops([op_activa, op_ya_ejecutada, op_inactiva])
        resultado = obtener_operaciones_pendientes(1, "2025-06", sesion_bd=sesion)
        assert len(resultado) == 1
        assert resultado[0]["operacion_id"] == 1

    def test_resultado_contiene_datos_operacion(self):
        op = _op(
            id_=5, tipo="provision_paga", descripcion="Provision paga extra",
            periodicidad="mensual",
            parametros={"subcuenta_debe": "6400000000", "subcuenta_haber": "4650000000", "importe": "416.67"},
        )
        sesion = _sesion_mock_con_ops([op])
        resultado = obtener_operaciones_pendientes(1, "2025-06", sesion_bd=sesion)
        r = resultado[0]
        assert r["operacion_id"] == 5
        assert r["tipo"] == "provision_paga"
        assert r["descripcion"] == "Provision paga extra"
        assert r["subcuenta_debe"] == "6400000000"
        assert r["subcuenta_haber"] == "4650000000"
        assert float(r["importe"]) == pytest.approx(416.67, abs=0.01)
        assert r["fecha_ejecucion"] == date(2025, 6, 1)


# ---------------------------------------------------------------------------
# Tests: generar_asiento_periodico
# ---------------------------------------------------------------------------

class TestGenerarAsientoPeriodico:
    def _operacion_base(self, tipo="amortizacion", mes="2025-06"):
        return {
            "operacion_id": 1,
            "empresa_id": 1,
            "tipo": tipo,
            "descripcion": "Amort. vehiculo",
            "subcuenta_debe": "6810000000",
            "subcuenta_haber": "2810000000",
            "importe": "400.00",
            "fecha_ejecucion": date(2025, 6, 1),
            "mes": mes,
        }

    def test_estructura_asiento(self):
        op = self._operacion_base()
        asiento = generar_asiento_periodico(op)
        assert "fecha" in asiento
        assert "concepto" in asiento
        assert "partidas" in asiento
        assert "empresa_id" in asiento

    def test_fecha_es_fecha_ejecucion(self):
        op = self._operacion_base()
        asiento = generar_asiento_periodico(op)
        assert asiento["fecha"] == date(2025, 6, 1)

    def test_concepto_incluye_tipo_y_mes(self):
        op = self._operacion_base(tipo="amortizacion", mes="2025-06")
        asiento = generar_asiento_periodico(op)
        assert "amortizacion" in asiento["concepto"].lower()
        assert "2025-06" in asiento["concepto"] or "06/2025" in asiento["concepto"]

    def test_dos_partidas(self):
        op = self._operacion_base()
        asiento = generar_asiento_periodico(op)
        assert len(asiento["partidas"]) == 2

    def test_partidas_cuadran(self):
        op = self._operacion_base()
        asiento = generar_asiento_periodico(op)
        partidas = asiento["partidas"]
        total_debe = sum(float(p.get("debe", 0)) for p in partidas)
        total_haber = sum(float(p.get("haber", 0)) for p in partidas)
        assert abs(total_debe - total_haber) < 0.01

    def test_partida_debe_correcto(self):
        op = self._operacion_base()
        asiento = generar_asiento_periodico(op)
        partidas = asiento["partidas"]
        partida_debe = next(p for p in partidas if float(p.get("debe", 0)) > 0)
        assert partida_debe["subcuenta"] == "6810000000"
        assert float(partida_debe["debe"]) == pytest.approx(400.0)

    def test_partida_haber_correcto(self):
        op = self._operacion_base()
        asiento = generar_asiento_periodico(op)
        partidas = asiento["partidas"]
        partida_haber = next(p for p in partidas if float(p.get("haber", 0)) > 0)
        assert partida_haber["subcuenta"] == "2810000000"
        assert float(partida_haber["haber"]) == pytest.approx(400.0)

    def test_empresa_id_propagado(self):
        op = self._operacion_base()
        op["empresa_id"] = 3
        asiento = generar_asiento_periodico(op)
        assert asiento["empresa_id"] == 3

    def test_tipo_provision_paga(self):
        op = {
            "operacion_id": 2,
            "empresa_id": 1,
            "tipo": "provision_paga",
            "descripcion": "Provision paga extra julio",
            "subcuenta_debe": "6400000000",
            "subcuenta_haber": "4650000000",
            "importe": "416.67",
            "fecha_ejecucion": date(2025, 6, 1),
            "mes": "2025-06",
        }
        asiento = generar_asiento_periodico(op)
        assert "provision_paga" in asiento["concepto"].lower() or "provision" in asiento["concepto"].lower()
        partidas = asiento["partidas"]
        total_debe = sum(float(p.get("debe", 0)) for p in partidas)
        total_haber = sum(float(p.get("haber", 0)) for p in partidas)
        assert abs(total_debe - total_haber) < 0.01


# ---------------------------------------------------------------------------
# Tests: ejecutar_periodicas
# ---------------------------------------------------------------------------

class TestEjecutarPeriodicas:
    def _mock_sesion_con_ops(self, ops):
        sesion = MagicMock()
        sesion.scalars.return_value.all.return_value = ops
        return sesion

    def test_sin_operaciones_retorna_cero(self):
        sesion = self._mock_sesion_con_ops([])
        resultado = ejecutar_periodicas(1, "2025-06", dry_run=True, sesion_bd=sesion)
        assert resultado["generados"] == 0
        assert resultado["registrados"] == 0
        assert resultado["errores"] == 0

    def test_retorna_estructura_completa(self):
        sesion = self._mock_sesion_con_ops([])
        resultado = ejecutar_periodicas(1, "2025-06", dry_run=True, sesion_bd=sesion)
        assert "empresa_id" in resultado
        assert "mes" in resultado
        assert "generados" in resultado
        assert "registrados" in resultado
        assert "errores" in resultado
        assert "detalle" in resultado

    def test_empresa_id_y_mes_en_resultado(self):
        sesion = self._mock_sesion_con_ops([])
        resultado = ejecutar_periodicas(5, "2025-09", dry_run=True, sesion_bd=sesion)
        assert resultado["empresa_id"] == 5
        assert resultado["mes"] == "2025-09"

    def test_dry_run_genera_sin_registrar(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=None)
        sesion = self._mock_sesion_con_ops([op])
        resultado = ejecutar_periodicas(1, "2025-06", dry_run=True, sesion_bd=sesion)
        assert resultado["generados"] == 1
        assert resultado["registrados"] == 0
        # En dry_run NO debe actualizar ultimo_ejecutado
        assert op.ultimo_ejecutado is None or op.ultimo_ejecutado != date(2025, 6, 1)

    def test_dry_run_detalle_contiene_asientos(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=None)
        sesion = self._mock_sesion_con_ops([op])
        resultado = ejecutar_periodicas(1, "2025-06", dry_run=True, sesion_bd=sesion)
        assert len(resultado["detalle"]) == 1
        item = resultado["detalle"][0]
        assert "asiento" in item
        assert item["estado"] == "dry_run"

    def test_sin_dry_run_llama_backend(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=None)
        sesion = self._mock_sesion_con_ops([op])

        backend_mock = MagicMock()
        backend_mock.crear_asiento.return_value = {"ok": True, "data": {"idasiento": 42}}

        resultado = ejecutar_periodicas(
            1, "2025-06", dry_run=False, sesion_bd=sesion, backend=backend_mock
        )
        assert resultado["generados"] == 1
        assert resultado["registrados"] == 1
        assert backend_mock.crear_asiento.call_count == 1

    def test_sin_dry_run_actualiza_ultimo_ejecutado(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=None)
        sesion = self._mock_sesion_con_ops([op])

        backend_mock = MagicMock()
        backend_mock.crear_asiento.return_value = {"ok": True}

        ejecutar_periodicas(1, "2025-06", dry_run=False, sesion_bd=sesion, backend=backend_mock)
        # Debe haberse actualizado ultimo_ejecutado
        assert op.ultimo_ejecutado == date(2025, 6, 1)

    def test_error_backend_incrementa_errores(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=None)
        sesion = self._mock_sesion_con_ops([op])

        backend_mock = MagicMock()
        backend_mock.crear_asiento.side_effect = Exception("Error de conexion")

        resultado = ejecutar_periodicas(
            1, "2025-06", dry_run=False, sesion_bd=sesion, backend=backend_mock
        )
        assert resultado["errores"] == 1
        assert resultado["registrados"] == 0
        item = resultado["detalle"][0]
        assert item["estado"] == "error"
        assert "Error de conexion" in item.get("error", "")

    def test_multiples_ops_varias_pendientes(self):
        ops = [
            _op(id_=1, periodicidad="mensual", ultimo_ejecutado=None),
            _op(id_=2, periodicidad="mensual", ultimo_ejecutado=None,
                parametros={"subcuenta_debe": "6250000000", "subcuenta_haber": "5280000000", "importe": "200.00"}),
            _op(id_=3, periodicidad="mensual", ultimo_ejecutado=date(2025, 6, 1)),  # ya ejecutada
        ]
        sesion = self._mock_sesion_con_ops(ops)
        resultado = ejecutar_periodicas(1, "2025-06", dry_run=True, sesion_bd=sesion)
        assert resultado["generados"] == 2
        assert resultado["registrados"] == 0

    def test_detalle_contiene_operacion_id(self):
        op = _op(id_=7, periodicidad="mensual", ultimo_ejecutado=None)
        sesion = self._mock_sesion_con_ops([op])
        resultado = ejecutar_periodicas(1, "2025-06", dry_run=True, sesion_bd=sesion)
        item = resultado["detalle"][0]
        assert item["operacion_id"] == 7


# ---------------------------------------------------------------------------
# Tests: frecuencias especificas
# ---------------------------------------------------------------------------

class TestFrecuencias:
    def test_mensual_pendiente_cada_mes(self):
        op = _op(periodicidad="mensual", ultimo_ejecutado=None)
        for mes in ["2025-01", "2025-02", "2025-03", "2025-12"]:
            assert _es_pendiente_en_mes(op, mes) is True

    def test_trimestral_solo_meses_1_4_7_10(self):
        op = _op(periodicidad="trimestral", ultimo_ejecutado=None)
        meses_ok = ["2025-01", "2025-04", "2025-07", "2025-10"]
        meses_no = ["2025-02", "2025-03", "2025-05", "2025-06", "2025-08", "2025-09", "2025-11", "2025-12"]
        for mes in meses_ok:
            assert _es_pendiente_en_mes(op, mes) is True, f"Fallo en {mes}"
        for mes in meses_no:
            assert _es_pendiente_en_mes(op, mes) is False, f"Fallo en {mes}"

    def test_anual_solo_enero(self):
        op = _op(periodicidad="anual", ultimo_ejecutado=None)
        assert _es_pendiente_en_mes(op, "2025-01") is True
        for mes in ["2025-02", "2025-06", "2025-12"]:
            assert _es_pendiente_en_mes(op, mes) is False

    def test_anual_con_mes_inicio_personalizado(self):
        # Si parametros tiene mes_inicio, usarlo
        op = _op(
            periodicidad="anual", ultimo_ejecutado=None,
            parametros={"subcuenta_debe": "6810000000", "subcuenta_haber": "2810000000",
                        "importe": "400.00", "mes_inicio": 6},
        )
        assert _es_pendiente_en_mes(op, "2025-06") is True
        assert _es_pendiente_en_mes(op, "2025-01") is False


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empresa_sin_periodicas(self):
        sesion = _sesion_mock_con_ops([])
        resultado = obtener_operaciones_pendientes(99, "2025-06", sesion_bd=sesion)
        assert resultado == []

    def test_mes_formato_invalido_lanza_error(self):
        sesion = _sesion_mock_con_ops([])
        with pytest.raises((ValueError, Exception)):
            obtener_operaciones_pendientes(1, "junio-2025", sesion_bd=sesion)

    def test_importe_cero_genera_asiento(self):
        op_data = {
            "operacion_id": 1,
            "empresa_id": 1,
            "tipo": "amortizacion",
            "descripcion": "Sin importe",
            "subcuenta_debe": "6810000000",
            "subcuenta_haber": "2810000000",
            "importe": "0.00",
            "fecha_ejecucion": date(2025, 6, 1),
            "mes": "2025-06",
        }
        asiento = generar_asiento_periodico(op_data)
        partidas = asiento["partidas"]
        total_debe = sum(float(p.get("debe", 0)) for p in partidas)
        total_haber = sum(float(p.get("haber", 0)) for p in partidas)
        assert abs(total_debe - total_haber) < 0.01
