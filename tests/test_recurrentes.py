"""Tests para deteccion de facturas recurrentes faltantes (Task 44 Fase E).

TDD: tests escritos antes de la implementacion.
Cubre: deteccion de patrones, facturas faltantes, alertas, edge cases.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from sfce.core.recurrentes import (
    PatronRecurrente,
    detectar_faltantes,
    detectar_patrones_recurrentes,
    generar_alertas_recurrentes,
)


# ---------------------------------------------------------------------------
# Helpers para generar datos de prueba
# ---------------------------------------------------------------------------

def _factura(cif: str, fecha: str, total: float, nombre: str = "Proveedor SA") -> dict:
    """Crea una factura minima para tests."""
    return {
        "cif_emisor": cif,
        "fecha": fecha,
        "total": total,
        "nombre_emisor": nombre,
    }


def _facturas_mensuales(
    cif: str,
    fecha_inicio: str,
    n: int,
    total: float = 100.0,
    nombre: str = "Proveedor SA",
) -> list[dict]:
    """Genera n facturas mensuales (~30 dias) a partir de fecha_inicio."""
    inicio = date.fromisoformat(fecha_inicio)
    facturas = []
    for i in range(n):
        fecha = inicio + timedelta(days=30 * i)
        facturas.append(_factura(cif, fecha.isoformat(), total, nombre))
    return facturas


# ---------------------------------------------------------------------------
# Tests: detectar_patrones_recurrentes
# ---------------------------------------------------------------------------

class TestDetectarPatronesRecurrentes:

    def test_patron_detectado_cuatro_facturas_mensuales(self):
        """4 facturas mensuales del mismo CIF → patron con frecuencia ~30 dias."""
        facturas = _facturas_mensuales("B12345678", "2025-01-01", 4, total=250.0)
        patrones = detectar_patrones_recurrentes(facturas)
        assert len(patrones) == 1
        p = patrones[0]
        assert p.proveedor_cif == "B12345678"
        assert 28 <= p.frecuencia_dias <= 32
        assert p.ocurrencias == 4
        assert p.importe_tipico == pytest.approx(250.0)

    def test_patron_no_detectado_solo_dos_facturas(self):
        """2 facturas es menor que min_ocurrencias=3 → no hay patron."""
        facturas = _facturas_mensuales("B12345678", "2025-01-01", 2)
        patrones = detectar_patrones_recurrentes(facturas)
        assert patrones == []

    def test_patron_no_detectado_con_min_ocurrencias_personalizado(self):
        """Con min_ocurrencias=5, 4 facturas no generan patron."""
        facturas = _facturas_mensuales("B12345678", "2025-01-01", 4)
        patrones = detectar_patrones_recurrentes(facturas, min_ocurrencias=5)
        assert patrones == []

    def test_patron_detectado_exactamente_min_ocurrencias(self):
        """Exactamente 3 facturas con min_ocurrencias=3 → patron detectado."""
        facturas = _facturas_mensuales("B12345678", "2025-01-01", 3)
        patrones = detectar_patrones_recurrentes(facturas, min_ocurrencias=3)
        assert len(patrones) == 1

    def test_patron_no_detectado_frecuencia_irregular(self):
        """Intervalos muy variables (desviacion > 15 dias) → no recurrente."""
        # Facturas en dias: 0, 5, 60, 120 → intervalos 5, 55, 60 → desv alta
        facturas = [
            _factura("B12345678", "2025-01-01", 100.0),
            _factura("B12345678", "2025-01-06", 100.0),
            _factura("B12345678", "2025-03-07", 100.0),
            _factura("B12345678", "2025-05-06", 100.0),
        ]
        patrones = detectar_patrones_recurrentes(facturas)
        assert patrones == []

    def test_patron_detectado_frecuencia_regular_con_pequena_variacion(self):
        """Intervalos ~30 dias con variacion de 2-3 dias → recurrente."""
        facturas = [
            _factura("B12345678", "2025-01-01", 100.0),
            _factura("B12345678", "2025-02-02", 100.0),   # +32 dias
            _factura("B12345678", "2025-03-01", 100.0),   # +27 dias
            _factura("B12345678", "2025-03-31", 100.0),   # +30 dias
        ]
        patrones = detectar_patrones_recurrentes(facturas)
        assert len(patrones) == 1

    def test_importe_tipico_es_media(self):
        """El importe tipico debe ser la media de los importes."""
        facturas = [
            _factura("B12345678", "2025-01-01", 100.0),
            _factura("B12345678", "2025-02-01", 120.0),
            _factura("B12345678", "2025-03-01", 110.0),
            _factura("B12345678", "2025-04-01", 90.0),
        ]
        patrones = detectar_patrones_recurrentes(facturas)
        assert len(patrones) == 1
        assert patrones[0].importe_tipico == pytest.approx(105.0)

    def test_nombre_proveedor_preservado(self):
        """El nombre del proveedor se incluye en el patron."""
        facturas = _facturas_mensuales("B12345678", "2025-01-01", 3, nombre="Makro SA")
        patrones = detectar_patrones_recurrentes(facturas)
        assert patrones[0].proveedor_nombre == "Makro SA"

    def test_ultima_fecha_es_la_mas_reciente(self):
        """La ultima_fecha debe ser la fecha mas reciente de las facturas."""
        facturas = _facturas_mensuales("B12345678", "2025-01-01", 4)
        patrones = detectar_patrones_recurrentes(facturas)
        # La ultima factura es 2025-01-01 + 30*3 = 2025-03-31 (aprox)
        fecha_esperada = (date(2025, 1, 1) + timedelta(days=90)).isoformat()
        assert patrones[0].ultima_fecha == fecha_esperada

    def test_multiples_proveedores_patrones_independientes(self):
        """Dos proveedores distintos generan dos patrones independientes."""
        facturas = (
            _facturas_mensuales("B11111111", "2025-01-01", 4, nombre="Proveedor A")
            + _facturas_mensuales("B22222222", "2025-01-15", 4, nombre="Proveedor B")
        )
        patrones = detectar_patrones_recurrentes(facturas)
        assert len(patrones) == 2
        cifs = {p.proveedor_cif for p in patrones}
        assert cifs == {"B11111111", "B22222222"}

    def test_proveedor_con_pocas_facturas_no_aparece(self):
        """Si un proveedor tiene pocas facturas, no aparece en patrones."""
        facturas = (
            _facturas_mensuales("B11111111", "2025-01-01", 4)   # ok
            + _facturas_mensuales("B22222222", "2025-01-01", 2)  # insuficiente
        )
        patrones = detectar_patrones_recurrentes(facturas)
        assert len(patrones) == 1
        assert patrones[0].proveedor_cif == "B11111111"

    def test_patrones_ordenados_por_confianza_descendente(self):
        """Los patrones se devuelven ordenados de mayor a menor confianza."""
        # Patron A: muy regular (desv ~0)
        facturas_a = [
            _factura("A00000001", "2025-01-01", 100.0, "Patron Perfecto"),
            _factura("A00000001", "2025-02-01", 100.0, "Patron Perfecto"),
            _factura("A00000001", "2025-03-01", 100.0, "Patron Perfecto"),
            _factura("A00000001", "2025-04-01", 100.0, "Patron Perfecto"),
        ]
        # Patron B: menos regular (desv ~10 dias)
        facturas_b = [
            _factura("B00000002", "2025-01-01", 100.0, "Patron Irregular"),
            _factura("B00000002", "2025-02-10", 100.0, "Patron Irregular"),
            _factura("B00000002", "2025-03-05", 100.0, "Patron Irregular"),
            _factura("B00000002", "2025-04-14", 100.0, "Patron Irregular"),
        ]
        patrones = detectar_patrones_recurrentes(facturas_a + facturas_b)
        assert len(patrones) == 2
        assert patrones[0].confianza >= patrones[1].confianza

    def test_confianza_patron_regular_mayor_que_irregular(self):
        """Patron regular (desv=2d) tiene mayor confianza que irregular (desv=10d)."""
        # Patron muy regular: intervalos exactamente 30 dias
        facturas_regular = [
            _factura("R00000001", "2025-01-01", 100.0),
            _factura("R00000001", "2025-01-31", 100.0),
            _factura("R00000001", "2025-03-02", 100.0),
            _factura("R00000001", "2025-04-01", 100.0),
        ]
        # Patron irregular: variacion de ~12 dias
        facturas_irregular = [
            _factura("I00000002", "2025-01-01", 100.0),
            _factura("I00000002", "2025-02-13", 100.0),   # +43 dias
            _factura("I00000002", "2025-03-14", 100.0),   # +29 dias
            _factura("I00000002", "2025-04-12", 100.0),   # +29 dias
        ]
        patrones_r = detectar_patrones_recurrentes(facturas_regular)
        patrones_i = detectar_patrones_recurrentes(facturas_irregular)
        # Ambos deben ser detectados (desv < 15 en ambos casos)
        assert len(patrones_r) == 1
        assert len(patrones_i) == 1
        assert patrones_r[0].confianza > patrones_i[0].confianza

    def test_lista_vacia_retorna_lista_vacia(self):
        """Sin facturas, no hay patrones."""
        assert detectar_patrones_recurrentes([]) == []

    def test_factura_usa_campo_importe_alternativo(self):
        """Si el dict tiene 'importe' en vez de 'total', debe funcionar igual."""
        facturas = []
        for i in range(4):
            f = {
                "cif_emisor": "B12345678",
                "fecha": (date(2025, 1, 1) + timedelta(days=30 * i)).isoformat(),
                "importe": 150.0,
                "nombre_emisor": "Proveedor SA",
            }
            facturas.append(f)
        patrones = detectar_patrones_recurrentes(facturas)
        assert len(patrones) == 1
        assert patrones[0].importe_tipico == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# Tests: detectar_faltantes
# ---------------------------------------------------------------------------

class TestDetectarFaltantes:

    def test_factura_mensual_con_45_dias_retraso_es_faltante(self):
        """Patron mensual, ultima factura hace 45 dias → falta una factura."""
        hoy = date.today()
        ultima = (hoy - timedelta(days=45)).isoformat()
        patron = PatronRecurrente(
            proveedor_cif="B12345678",
            proveedor_nombre="Proveedor SA",
            frecuencia_dias=30,
            ultima_fecha=ultima,
            importe_tipico=200.0,
            ocurrencias=4,
            confianza=0.9,
        )
        faltantes = detectar_faltantes([patron])
        assert len(faltantes) == 1
        f = faltantes[0]
        assert f["proveedor_cif"] == "B12345678"
        assert f["proveedor_nombre"] == "Proveedor SA"
        assert f["importe_estimado"] == pytest.approx(200.0)
        assert f["confianza"] == pytest.approx(0.9)
        assert f["dias_retraso"] > 0

    def test_factura_mensual_con_20_dias_no_es_faltante(self):
        """Patron mensual, ultima factura hace 20 dias → proxima no ha llegado."""
        hoy = date.today()
        ultima = (hoy - timedelta(days=20)).isoformat()
        patron = PatronRecurrente(
            proveedor_cif="B12345678",
            proveedor_nombre="Proveedor SA",
            frecuencia_dias=30,
            ultima_fecha=ultima,
            importe_tipico=200.0,
            ocurrencias=4,
            confianza=0.9,
        )
        faltantes = detectar_faltantes([patron])
        assert faltantes == []

    def test_detectar_faltantes_con_fecha_corte_explicita(self):
        """Fecha corte explicita controla si la factura es faltante."""
        patron = PatronRecurrente(
            proveedor_cif="B12345678",
            proveedor_nombre="Proveedor SA",
            frecuencia_dias=30,
            ultima_fecha="2025-01-01",
            importe_tipico=100.0,
            ocurrencias=3,
            confianza=0.85,
        )
        # Proxima esperada: 2025-01-31. Corte en 2025-02-15 → faltante
        faltantes = detectar_faltantes([patron], fecha_corte="2025-02-15")
        assert len(faltantes) == 1
        assert faltantes[0]["proveedor_cif"] == "B12345678"

    def test_detectar_faltantes_corte_antes_de_proxima(self):
        """Fecha corte antes de la proxima esperada → no faltante."""
        patron = PatronRecurrente(
            proveedor_cif="B12345678",
            proveedor_nombre="Proveedor SA",
            frecuencia_dias=30,
            ultima_fecha="2025-01-01",
            importe_tipico=100.0,
            ocurrencias=3,
            confianza=0.85,
        )
        # Proxima esperada: 2025-01-31. Corte en 2025-01-20 → no faltante
        faltantes = detectar_faltantes([patron], fecha_corte="2025-01-20")
        assert faltantes == []

    def test_dias_retraso_calculado_correctamente(self):
        """dias_retraso = dias entre proxima_esperada y fecha_corte."""
        patron = PatronRecurrente(
            proveedor_cif="B12345678",
            proveedor_nombre="Proveedor SA",
            frecuencia_dias=30,
            ultima_fecha="2025-01-01",
            importe_tipico=100.0,
            ocurrencias=3,
            confianza=0.85,
        )
        # Proxima: 2025-01-31. Corte: 2025-02-10 → 10 dias de retraso
        faltantes = detectar_faltantes([patron], fecha_corte="2025-02-10")
        assert len(faltantes) == 1
        assert faltantes[0]["dias_retraso"] == 10

    def test_fecha_esperada_en_resultado(self):
        """El campo fecha_esperada tiene el valor correcto."""
        patron = PatronRecurrente(
            proveedor_cif="B12345678",
            proveedor_nombre="Proveedor SA",
            frecuencia_dias=30,
            ultima_fecha="2025-01-01",
            importe_tipico=100.0,
            ocurrencias=3,
            confianza=0.85,
        )
        faltantes = detectar_faltantes([patron], fecha_corte="2025-02-15")
        assert faltantes[0]["fecha_esperada"] == "2025-01-31"

    def test_multiples_patrones_con_faltantes_mixtos(self):
        """Varios patrones, algunos con faltantes y otros no."""
        patron_faltante = PatronRecurrente(
            proveedor_cif="A00000001",
            proveedor_nombre="Con Retraso",
            frecuencia_dias=30,
            ultima_fecha="2025-01-01",
            importe_tipico=100.0,
            ocurrencias=3,
            confianza=0.9,
        )
        patron_al_dia = PatronRecurrente(
            proveedor_cif="B00000002",
            proveedor_nombre="Al Dia",
            frecuencia_dias=30,
            ultima_fecha="2025-02-10",
            importe_tipico=200.0,
            ocurrencias=3,
            confianza=0.8,
        )
        # Corte: 2025-02-20 → A tiene faltante (proxima 2025-01-31), B no (proxima 2025-03-12)
        faltantes = detectar_faltantes([patron_faltante, patron_al_dia], fecha_corte="2025-02-20")
        assert len(faltantes) == 1
        assert faltantes[0]["proveedor_cif"] == "A00000001"

    def test_lista_patrones_vacia_retorna_lista_vacia(self):
        """Sin patrones, no hay faltantes."""
        assert detectar_faltantes([]) == []


# ---------------------------------------------------------------------------
# Tests: generar_alertas_recurrentes
# ---------------------------------------------------------------------------

class TestGenerarAlertasRecurrentes:

    def test_end_to_end_basico(self):
        """Flujo completo: facturas → patrones → faltantes → alertas."""
        # 4 facturas mensuales, ultima hace 45 dias
        hoy = date.today()
        fecha_inicio = (hoy - timedelta(days=45 + 90)).isoformat()
        facturas = _facturas_mensuales("B12345678", fecha_inicio, 4, total=300.0, nombre="Telefonica")

        resultado = generar_alertas_recurrentes(facturas)

        assert "patrones" in resultado
        assert "faltantes" in resultado
        assert "total_patrones" in resultado
        assert "total_faltantes" in resultado
        assert resultado["total_patrones"] == 1
        assert resultado["total_faltantes"] >= 1

    def test_estructura_resultado_completa(self):
        """El resultado tiene todos los campos requeridos."""
        facturas = _facturas_mensuales("B12345678", "2025-01-01", 4)
        resultado = generar_alertas_recurrentes(facturas, fecha_corte="2025-06-01")
        assert isinstance(resultado["patrones"], list)
        assert isinstance(resultado["faltantes"], list)
        assert isinstance(resultado["total_patrones"], int)
        assert isinstance(resultado["total_faltantes"], int)
        assert resultado["total_patrones"] == len(resultado["patrones"])
        assert resultado["total_faltantes"] == len(resultado["faltantes"])

    def test_sin_faltantes_cuando_todo_al_dia(self):
        """Si no hay retrasos, total_faltantes == 0."""
        # Facturas mensuales, la ultima reciente (hace 5 dias)
        hoy = date.today()
        fechas = [
            (hoy - timedelta(days=5 + 30 * i)).isoformat()
            for i in range(4)
        ]
        facturas = [_factura("B12345678", f, 100.0) for f in sorted(fechas)]
        resultado = generar_alertas_recurrentes(facturas)
        assert resultado["total_faltantes"] == 0

    def test_con_lista_vacia(self):
        """Sin facturas, resultado con ceros."""
        resultado = generar_alertas_recurrentes([])
        assert resultado["total_patrones"] == 0
        assert resultado["total_faltantes"] == 0
        assert resultado["patrones"] == []
        assert resultado["faltantes"] == []

    def test_fecha_corte_respetada(self):
        """La fecha_corte se pasa correctamente a detectar_faltantes."""
        facturas = _facturas_mensuales("B12345678", "2025-01-01", 4)
        # Con corte 2025-02-15 → deberia haber faltante (ultima ~2025-04-01, pero corte antes)
        # Con corte 2025-01-10 → no hay faltante (proxima aun no ha llegado)
        resultado_sin_faltante = generar_alertas_recurrentes(facturas, fecha_corte="2025-01-10")
        resultado_con_faltante = generar_alertas_recurrentes(facturas, fecha_corte="2025-05-15")
        assert resultado_sin_faltante["total_faltantes"] == 0
        assert resultado_con_faltante["total_faltantes"] >= 1

    def test_min_ocurrencias_pasado_correctamente(self):
        """min_ocurrencias se propaga a detectar_patrones_recurrentes."""
        facturas = _facturas_mensuales("B12345678", "2025-01-01", 3)
        # Con min=3 → detecta patron
        r3 = generar_alertas_recurrentes(facturas, min_ocurrencias=3)
        # Con min=4 → no detecta patron
        r4 = generar_alertas_recurrentes(facturas, min_ocurrencias=4)
        assert r3["total_patrones"] == 1
        assert r4["total_patrones"] == 0

    def test_multiples_proveedores_algunos_con_faltantes(self):
        """Varios proveedores, solo algunos con retrasos."""
        facturas = (
            _facturas_mensuales("A00000001", "2025-01-01", 4, nombre="Con Retraso")
            + _facturas_mensuales("B00000002", "2025-01-01", 4, nombre="Sin Retraso")
        )
        resultado = generar_alertas_recurrentes(facturas, fecha_corte="2025-05-15")
        assert resultado["total_patrones"] == 2
        # Ambos tendran faltantes ya que la ultima de ambos es aprox 2025-04-01
        assert resultado["total_faltantes"] >= 1


# ---------------------------------------------------------------------------
# Tests: PatronRecurrente (dataclass)
# ---------------------------------------------------------------------------

class TestPatronRecurrente:

    def test_patron_recurrente_es_instanciable(self):
        """PatronRecurrente se puede crear con todos los campos."""
        p = PatronRecurrente(
            proveedor_cif="B12345678",
            proveedor_nombre="Test SA",
            frecuencia_dias=30,
            ultima_fecha="2025-01-31",
            importe_tipico=150.0,
            ocurrencias=4,
            confianza=0.95,
        )
        assert p.proveedor_cif == "B12345678"
        assert p.frecuencia_dias == 30
        assert p.confianza == pytest.approx(0.95)

    def test_patron_recurrente_confianza_en_rango(self):
        """La confianza calculada por detectar_patrones_recurrentes esta en [0, 1]."""
        facturas = _facturas_mensuales("B12345678", "2025-01-01", 5)
        patrones = detectar_patrones_recurrentes(facturas)
        assert len(patrones) == 1
        assert 0.0 <= patrones[0].confianza <= 1.0
