"""Tests del generador de informe de cuarentena."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sfce.core.informe_cuarentena import (
    ItemCuarentena,
    generar_informe_cuarentena,
    _texto_informe,
)


# ─────────────────────────── helpers ────────────────────────────────────────

def _item_pendiente(tipo: str = "entidad", archivo: str = "factura.pdf") -> ItemCuarentena:
    return ItemCuarentena(
        origen="bd",
        archivo=archivo,
        tipo_pregunta=tipo,
        pregunta=f"Pregunta de tipo {tipo}",
        opciones=[{"valor": "nuevo", "descripcion": "Crear nuevo", "confianza": 0.8}],
        respuesta=None,
        resuelta=False,
        fecha_creacion="2025-03-01T10:00:00",
        motivo_raw="motivo",
    )


def _item_resuelto(tipo: str = "iva") -> ItemCuarentena:
    return ItemCuarentena(
        origen="bd",
        archivo="factura_resuelta.pdf",
        tipo_pregunta=tipo,
        pregunta="Pregunta resuelta",
        opciones=[],
        respuesta="opcion_a",
        resuelta=True,
        fecha_creacion="2025-02-15T08:30:00",
        motivo_raw="motivo",
    )


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 1: ItemCuarentena helpers
# ═════════════════════════════════════════════════════════════════════════════

class TestItemCuarentena:
    def test_estado_label_pendiente(self):
        item = _item_pendiente()
        assert item.estado_label == "PENDIENTE"

    def test_estado_label_resuelta(self):
        item = _item_resuelto()
        assert item.estado_label == "RESUELTA"

    def test_prioridad_entidad_es_mayor(self):
        entidad = _item_pendiente("entidad")
        iva = _item_pendiente("iva")
        otro = _item_pendiente("otro")
        assert entidad.prioridad < iva.prioridad < otro.prioridad

    def test_prioridad_default_para_tipo_desconocido(self):
        item = _item_pendiente("tipo_nuevo_raro")
        assert item.prioridad == 99


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 2: _texto_informe
# ═════════════════════════════════════════════════════════════════════════════

class TestTextoInforme:
    def test_informe_vacio(self):
        texto = _texto_informe([], empresa_id=1, ejercicio="2025")
        assert "No hay documentos" in texto

    def test_informe_con_pendiente(self):
        items = [_item_pendiente("entidad")]
        texto = _texto_informe(items, empresa_id=1, ejercicio="2025")
        assert "PENDIENTE" in texto
        assert "factura.pdf" in texto
        assert "Pendientes: 1" in texto

    def test_informe_con_resuelta(self):
        items = [_item_resuelto()]
        texto = _texto_informe(items, empresa_id=1, ejercicio="2025")
        assert "RESUELTA" in texto
        assert "Resueltas: 1" in texto

    def test_informe_agrupa_por_tipo(self):
        items = [
            _item_pendiente("entidad"),
            _item_pendiente("iva", "factura2.pdf"),
        ]
        texto = _texto_informe(items, empresa_id=1, ejercicio="2025")
        assert "PROVEEDOR/CLIENTE DESCONOCIDO" in texto.upper() or "ENTIDAD" in texto.upper()
        assert "IVA" in texto.upper()

    def test_informe_muestra_opciones(self):
        item = _item_pendiente("entidad")
        item.opciones = [{"valor": "nuevo", "descripcion": "Crear nuevo proveedor", "confianza": 0.8}]
        texto = _texto_informe([item], empresa_id=1, ejercicio="2025")
        assert "Crear nuevo proveedor" in texto

    def test_informe_muestra_sugerencia_mcf(self):
        item = _item_pendiente("entidad")
        item.sugerencia_mcf = {
            "categoria": "suministros_telefono",
            "descripcion": "Suministro teléfono/internet",
            "iva_codimpuesto": "IVA21",
            "iva_deducible_pct": 100,
            "irpf_pct": None,
            "subcuenta": "6290000000",
            "confianza": 0.85,
            "preguntas_pendientes": [],
            "razonamiento": "B12345 → ESP/general | movistar",
        }
        texto = _texto_informe([item], empresa_id=1, ejercicio="2025")
        assert "MCF" in texto
        assert "85%" in texto

    def test_informe_mcf_con_preguntas_pendientes(self):
        item = _item_pendiente("entidad")
        item.sugerencia_mcf = {
            "categoria": "suministros_combustible",
            "descripcion": "Combustible",
            "iva_codimpuesto": "IVA21",
            "iva_deducible_pct": None,
            "irpf_pct": None,
            "subcuenta": None,
            "confianza": 0.75,
            "preguntas_pendientes": ["tipo_vehiculo"],
            "razonamiento": "",
        }
        texto = _texto_informe([item], empresa_id=1, ejercicio="2025")
        assert "tipo_vehiculo" in texto

    def test_informe_contiene_separadores(self):
        items = [_item_pendiente()]
        texto = _texto_informe(items, empresa_id=1, ejercicio="2025")
        assert "=" * 30 in texto

    def test_informe_contiene_ejercicio(self):
        texto = _texto_informe([], empresa_id=1, ejercicio="2025")
        assert "2025" in texto


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 3: generar_informe_cuarentena — carpeta vacía
# ═════════════════════════════════════════════════════════════════════════════

class TestGenerarInformeCarpetaVacia:
    def test_informe_cliente_sin_cuarentena(self, tmp_path):
        ruta_cliente = tmp_path / "cliente"
        ruta_cliente.mkdir()
        # No existe carpeta cuarentena ni BD

        informe = generar_informe_cuarentena(
            ruta_cliente=ruta_cliente,
            ejercicio="2025",
            ruta_bd=tmp_path / "no_existe.db",
            enriquecer_mcf=False,
        )

        assert informe["total"] == 0
        assert informe["pendientes"] == 0
        assert informe["resueltas"] == 0
        assert "No hay documentos" in informe["resumen_texto"]

    def test_informe_retorna_estructura_completa(self, tmp_path):
        ruta_cliente = tmp_path / "cliente"
        ruta_cliente.mkdir()

        informe = generar_informe_cuarentena(
            ruta_cliente=ruta_cliente,
            ruta_bd=tmp_path / "no_existe.db",
            enriquecer_mcf=False,
        )

        assert "items" in informe
        assert "total" in informe
        assert "pendientes" in informe
        assert "resueltas" in informe
        assert "por_tipo" in informe
        assert "resumen_texto" in informe
        assert "ruta_guardado" in informe

    def test_informe_con_pdfs_en_carpeta(self, tmp_path):
        ruta_cliente = tmp_path / "cliente"
        ruta_cuarentena = ruta_cliente / "cuarentena"
        ruta_cuarentena.mkdir(parents=True)

        # Crear PDF falso
        (ruta_cuarentena / "factura_01.pdf").write_bytes(b"%PDF-1.4 fake")
        (ruta_cuarentena / "factura_02.pdf").write_bytes(b"%PDF-1.4 fake")

        informe = generar_informe_cuarentena(
            ruta_cliente=ruta_cliente,
            ruta_bd=tmp_path / "no_existe.db",
            enriquecer_mcf=False,
        )

        assert informe["total"] == 2
        assert informe["pendientes"] == 2
        assert "sin_bd" in informe["por_tipo"]

    def test_json_guardado_en_auditoria(self, tmp_path):
        ruta_cliente = tmp_path / "cliente"
        ruta_cliente.mkdir()

        informe = generar_informe_cuarentena(
            ruta_cliente=ruta_cliente,
            ejercicio="2025",
            ruta_bd=tmp_path / "no_existe.db",
            enriquecer_mcf=False,
        )

        assert informe["ruta_guardado"] is not None
        ruta_json = Path(informe["ruta_guardado"])
        assert ruta_json.exists()

        with open(ruta_json) as f:
            datos = json.load(f)
        assert datos["total"] == 0
        assert datos["ejercicio"] == "2025"
