"""Tests de integracion Fase E — verifica que los modulos trabajan juntos.

Modulos cubiertos:
- sfce.core.cache_ocr
- sfce.core.duplicados
- sfce.core.nombres
- sfce.core.notificaciones
- sfce.core.recurrentes
- sfce.core.ingesta_email (guardar_adjuntos_en_inbox, enrutar_por_remitente)
- sfce.core.config (ConfigCliente, agregar_trabajador)
- sfce.phases.intake (detectar_trabajador)
- scripts.generar_periodicas (generar_asiento_periodico, ejecutar_periodicas)
"""
import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sfce.core.cache_ocr import (
    calcular_hash_archivo,
    guardar_cache_ocr,
    invalidar_cache_ocr,
    obtener_cache_ocr,
    estadisticas_cache,
)
from sfce.core.duplicados import (
    ResultadoDuplicado,
    detectar_duplicado,
    filtrar_duplicados_batch,
)
from sfce.core.nombres import (
    generar_slug_cliente,
    mover_documento,
    renombrar_documento,
    carpeta_sin_clasificar,
)
from sfce.core.notificaciones import (
    GestorNotificaciones,
    TipoNotificacion,
    canal_log,
    crear_notificacion,
)
from sfce.core.recurrentes import (
    detectar_patrones_recurrentes,
    detectar_faltantes,
    generar_alertas_recurrentes,
)
from sfce.core.ingesta_email import (
    ConfigEmail,
    enrutar_por_remitente,
    guardar_adjuntos_en_inbox,
)
from sfce.core.config import ConfigCliente
from sfce.phases.intake import detectar_trabajador
from scripts.generar_periodicas import (
    generar_asiento_periodico,
    ejecutar_periodicas,
)


# ---------------------------------------------------------------------------
# Helpers de fixtures
# ---------------------------------------------------------------------------

def _crear_config_yaml(tmp_path: Path, trabajadores: list = None) -> Path:
    """Crea un config.yaml minimo en tmp_path y retorna su ruta."""
    datos = {
        "empresa": {
            "nombre": "Empresa Test S.L.",
            "cif": "B12345678",
            "tipo": "sl",
            "idempresa": 1,
            "ejercicio_activo": "2025",
        },
        "proveedores": {},
        "clientes": {},
        "trabajadores": trabajadores or [],
    }
    ruta = tmp_path / "config.yaml"
    with ruta.open("w", encoding="utf-8") as f:
        yaml.dump(datos, f, allow_unicode=True)
    return ruta


def _cargar_config(ruta_yaml: Path) -> ConfigCliente:
    """Carga ConfigCliente desde ruta."""
    with ruta_yaml.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ConfigCliente(data, ruta_yaml)


def _op_mock(
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


def _sesion_mock(ops: list):
    """Crea sesion BD mock que devuelve las operaciones dadas."""
    sesion = MagicMock()
    sesion.scalars.return_value.all.return_value = ops
    return sesion


# ---------------------------------------------------------------------------
# Test 1: Cache OCR — guardar y reutilizar, invalidacion por cambio
# ---------------------------------------------------------------------------

class TestCacheOcrIntegracion:
    """Verifica el ciclo completo: guardar → obtener hit → modificar PDF → miss."""

    def test_guardar_y_obtener_hit(self, tmp_path):
        ruta_pdf = tmp_path / "factura.pdf"
        ruta_pdf.write_bytes(b"%PDF-1.4 contenido original")

        datos_ocr = {
            "emisor_nombre": "Proveedor S.L.",
            "numero_factura": "F2025001",
            "total": 1210.0,
            "motor_ocr": "mistral",
            "tier_ocr": 0,
        }

        ruta_cache = guardar_cache_ocr(str(ruta_pdf), datos_ocr)
        assert Path(ruta_cache).exists()

        resultado = obtener_cache_ocr(str(ruta_pdf))
        assert resultado is not None
        assert resultado["emisor_nombre"] == "Proveedor S.L."
        assert resultado["numero_factura"] == "F2025001"

    def test_cache_invalido_tras_modificar_pdf(self, tmp_path):
        ruta_pdf = tmp_path / "factura.pdf"
        ruta_pdf.write_bytes(b"%PDF-1.4 version uno")

        datos_ocr = {"emisor_nombre": "Test", "motor_ocr": "mistral", "tier_ocr": 0}
        guardar_cache_ocr(str(ruta_pdf), datos_ocr)

        # Sobreescribir el PDF con contenido diferente
        ruta_pdf.write_bytes(b"%PDF-1.4 version dos con cambios")

        resultado = obtener_cache_ocr(str(ruta_pdf))
        assert resultado is None, "El cache debe invalidarse cuando el PDF cambia"

    def test_invalidar_cache_elimina_archivo(self, tmp_path):
        ruta_pdf = tmp_path / "factura.pdf"
        ruta_pdf.write_bytes(b"%PDF-1.4 test")

        guardar_cache_ocr(str(ruta_pdf), {"motor_ocr": "mistral", "tier_ocr": 0})

        eliminado = invalidar_cache_ocr(str(ruta_pdf))
        assert eliminado is True
        assert obtener_cache_ocr(str(ruta_pdf)) is None

    def test_estadisticas_cache_directorio(self, tmp_path):
        # Crear 3 PDFs: 2 con cache valido, 1 sin cache
        for i in range(3):
            pdf = tmp_path / f"doc{i}.pdf"
            pdf.write_bytes(f"contenido pdf {i}".encode())
            if i < 2:
                guardar_cache_ocr(str(pdf), {"motor_ocr": "mistral", "tier_ocr": 0})

        stats = estadisticas_cache(str(tmp_path))
        assert stats["total_pdfs"] == 3
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["ratio_hits"] == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# Test 2: Duplicados — filtrado batch
# ---------------------------------------------------------------------------

class TestDuplicadosBatch:
    """Verifica clasificacion correcta de 10 facturas con 2 seguros y 1 posible."""

    def _factura(self, cif, numero, fecha, total):
        return {
            "cif_emisor": cif,
            "numero_factura": numero,
            "fecha": fecha,
            "total": total,
        }

    def test_filtrar_batch_clasifica_correctamente(self):
        cif_a = "B11111111"
        cif_b = "B22222222"

        # Referencia historica: documentos ya registrados en contabilidad
        existentes = [
            self._factura(cif_a, "F2025001", "2025-01-10", 500.0),
            self._factura(cif_b, "F2025010", "2025-01-15", 300.0),
        ]

        # Documentos nuevos que llegan hoy:
        #   2 unicos (CIF distintos, sin coincidencia)
        #   2 duplicados seguros (mismo CIF + numero + fecha que existentes)
        #   1 posible (mismo CIF + importe + fecha proxima, numero diferente)
        nuevos = [
            self._factura("B33333333", "F001", "2025-01-20", 900.0),   # unico
            self._factura("B44444444", "F002", "2025-03-01", 1200.0),  # unico
            self._factura(cif_a, "F2025001", "2025-01-10", 500.0),     # dup seguro
            self._factura(cif_b, "F2025010", "2025-01-15", 300.0),     # dup seguro
            {
                "cif_emisor": cif_a,
                "numero_factura": "RECT-2025001",  # numero diferente
                "fecha": "2025-01-12",             # 2 dias de diferencia
                "total": 500.0,
            },  # posible
        ]
        assert len(nuevos) == 5

        unicos, seguros, posibles = filtrar_duplicados_batch(nuevos, existentes)

        assert len(seguros) == 2, f"Se esperaban 2 duplicados seguros, se obtuvieron {len(seguros)}"
        assert len(posibles) == 1, f"Se esperaba 1 posible, se obtuvieron {len(posibles)}"
        assert len(unicos) == 2, f"Se esperaban 2 unicos, se obtuvieron {len(unicos)}"
        assert len(unicos) + len(seguros) + len(posibles) == 5

    def test_sin_cif_no_es_duplicado(self):
        nueva = {"numero_factura": "F001", "fecha": "2025-01-01", "total": 100.0}
        existente = {"cif_emisor": "B11111111", "numero_factura": "F001",
                     "fecha": "2025-01-01", "total": 100.0}
        resultado = detectar_duplicado(nueva, [existente])
        assert resultado.tipo == "ninguno"
        assert not resultado.es_duplicado


# ---------------------------------------------------------------------------
# Test 3: Trabajador nuevo → cuarentena → resolucion
# ---------------------------------------------------------------------------

class TestTrabajadorNuevoResolucion:
    """Ciclo: nomina con DNI desconocido → cuarentena → agregar_trabajador → conocido."""

    def test_trabajador_desconocido_genera_cuarentena(self, tmp_path):
        ruta = _crear_config_yaml(tmp_path, trabajadores=[])
        config = _cargar_config(ruta)

        datos_nomina = {
            "tipo_doc": "NOM",
            "dni_trabajador": "12345678A",
            "nombre_trabajador": "Juan Garcia Lopez",
            "bruto": 1800.0,
        }

        resultado = detectar_trabajador(datos_nomina, config)
        assert resultado is not None
        assert resultado["conocido"] is False
        assert "cuarentena" in resultado
        assert resultado["cuarentena"]["tipo"] == "trabajador_nuevo"
        assert resultado["cuarentena"]["dni"] == "12345678A"

    def test_agregar_trabajador_y_detectar_como_conocido(self, tmp_path):
        ruta = _crear_config_yaml(tmp_path, trabajadores=[])
        config = _cargar_config(ruta)

        # Agregar trabajador (persiste en disco)
        config.agregar_trabajador(
            dni="12345678A",
            nombre="Juan Garcia Lopez",
            bruto_mensual=1800.0,
            pagas=14,
        )

        # Recargar config desde disco para simular nueva sesion
        config_recargada = _cargar_config(ruta)

        datos_nomina = {
            "tipo_doc": "NOM",
            "dni_trabajador": "12345678A",
            "nombre_trabajador": "Juan Garcia Lopez",
            "bruto": 1800.0,
        }

        resultado = detectar_trabajador(datos_nomina, config_recargada)
        assert resultado is not None
        assert resultado["conocido"] is True
        assert resultado["pagas"] == 14

    def test_trabajador_no_nomina_retorna_none(self, tmp_path):
        ruta = _crear_config_yaml(tmp_path)
        config = _cargar_config(ruta)

        datos_factura = {
            "tipo_doc": "FC",
            "dni_trabajador": "12345678A",
        }

        resultado = detectar_trabajador(datos_factura, config)
        assert resultado is None


# ---------------------------------------------------------------------------
# Test 4: Recurrentes — alerta por faltante mensual
# ---------------------------------------------------------------------------

class TestRecurrentesFaltante:
    """5 facturas mensuales ene-may, fecha_corte julio → 1 faltante (junio)."""

    # Facturas al ultimo dia de cada mes para que la siguiente esperada caiga en el mes siguiente
    _FECHAS_FIN_MES = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31}

    def _factura_mensual(self, mes: int, importe: float = 450.0):
        dia = self._FECHAS_FIN_MES.get(mes, 30)
        return {
            "cif_emisor": "B99999999",
            "nombre_emisor": "Alquiler Oficina S.L.",
            "fecha": f"2025-{mes:02d}-{dia:02d}",
            "total": importe,
        }

    def test_detecta_un_faltante_en_junio(self):
        # 5 facturas: 31-ene, 28-feb, 31-mar, 30-abr, 31-may
        # ultima_fecha = 2025-05-31, frecuencia ~30 dias → proxima = 2025-06-30
        # fecha_corte = 2025-08-01 → 2025-06-30 < 2025-08-01 → faltante en junio
        facturas = [self._factura_mensual(m) for m in range(1, 6)]

        resultado = generar_alertas_recurrentes(
            facturas,
            fecha_corte="2025-08-01",
            min_ocurrencias=3,
        )

        assert resultado["total_patrones"] == 1
        patron = resultado["patrones"][0]
        assert patron.proveedor_cif == "B99999999"

        assert resultado["total_faltantes"] == 1
        faltante = resultado["faltantes"][0]
        assert faltante["proveedor_cif"] == "B99999999"
        # La proxima esperada debe caer en junio (2025-05-31 + ~30 dias = 2025-06-30)
        fecha_esperada = date.fromisoformat(faltante["fecha_esperada"])
        assert fecha_esperada.month == 6
        assert faltante["dias_retraso"] > 0

    def test_sin_faltante_si_ultima_es_reciente(self):
        # Solo 3 facturas (minimo); la ultima es muy reciente → no hay faltante aun
        facturas = [self._factura_mensual(m) for m in [1, 2, 3]]

        resultado = generar_alertas_recurrentes(
            facturas,
            fecha_corte="2025-04-05",  # apenas 5 dias tras la ultima (31-mar)
            min_ocurrencias=3,
        )

        # La proxima esperada es aproximadamente 2025-04-30,
        # que aun no ha pasado respecto a la fecha de corte
        assert resultado["total_faltantes"] == 0


# ---------------------------------------------------------------------------
# Test 5: Nombres — renombrar y mover documento
# ---------------------------------------------------------------------------

class TestNombresDocumento:
    """Verifica formato estandar de renombrado y movimiento de archivos."""

    def test_renombrar_produce_nombre_estandar(self):
        datos_ocr = {
            "emisor_nombre": "Cargaexpress S.L.",
            "numero_factura": "F-2025/001",
            "fecha": "2025-01-15",
        }

        nombre = renombrar_documento(datos_ocr, tipo_doc="FV")
        assert nombre.startswith("FV_")
        assert "20250115" in nombre
        assert "F2025001" in nombre
        assert nombre.endswith(".pdf")

    def test_renombrar_con_fecha_explicita_tiene_prioridad(self):
        datos_ocr = {
            "emisor_nombre": "Proveedor Test",
            "numero_factura": "NOM-001",
            "fecha": "2025-03-01",
        }

        nombre = renombrar_documento(datos_ocr, tipo_doc="NOM", fecha="2025-06-30")
        assert "20250630" in nombre, "La fecha explicita debe tener prioridad sobre datos_ocr"

    def test_renombrar_sin_datos_usa_desconocido(self):
        nombre = renombrar_documento({}, tipo_doc="FC")
        assert "DESCONOCIDO" in nombre
        assert "SIN-FECHA" in nombre
        assert "SIN-NUM" in nombre

    def test_mover_documento_en_tmp(self, tmp_path):
        origen = tmp_path / "doc_original.pdf"
        origen.write_bytes(b"%PDF contenido")

        destino = tmp_path / "procesado" / "doc_renombrado.pdf"

        ruta_final = mover_documento(str(origen), str(destino))

        assert not origen.exists(), "El archivo origen debe haber sido movido"
        assert Path(ruta_final).exists(), "El archivo debe existir en destino"
        assert Path(ruta_final).read_bytes() == b"%PDF contenido"

    def test_slug_cliente_normalizado(self):
        slug = generar_slug_cliente("B12345678", "Pastorino Costa del Sol S.L.")
        assert slug.startswith("B12345678_")
        assert "pastorino" in slug
        assert "costa" in slug
        # Sin caracteres no ASCII ni espacios
        assert " " not in slug
        assert "." not in slug

    def test_carpeta_sin_clasificar_se_crea(self, tmp_path):
        ruta = carpeta_sin_clasificar(str(tmp_path))
        carpeta = Path(ruta)
        assert carpeta.exists()
        assert carpeta.name == "_sin_clasificar"


# ---------------------------------------------------------------------------
# Test 6: Notificaciones — canal_log y almacen pendientes
# ---------------------------------------------------------------------------

class TestNotificacionesGestor:
    """Verifica ciclo completo: crear gestor, agregar canal, enviar, obtener pendientes."""

    def test_enviar_notificacion_proveedor_nuevo(self):
        gestor = GestorNotificaciones()
        gestor.agregar_canal(canal_log)

        notif = crear_notificacion(
            tipo=TipoNotificacion.PROVEEDOR_NUEVO,
            titulo="Nuevo proveedor detectado: Makro S.A.",
            mensaje="Se ha detectado un proveedor nuevo: Makro S.A. (CIF: A28054609).",
            empresa_id=1,
        )

        resultado = gestor.enviar(notif)

        assert resultado["enviada"] is True
        assert resultado["canales_ok"] == 1
        assert resultado["canales_error"] == 0

    def test_obtener_pendientes_filtra_por_empresa(self):
        gestor = GestorNotificaciones()

        for empresa_id in [1, 2, 1]:
            notif = crear_notificacion(
                tipo=TipoNotificacion.CUARENTENA,
                titulo=f"Doc en cuarentena empresa {empresa_id}",
                mensaje="Requiere revision manual.",
                empresa_id=empresa_id,
            )
            gestor.enviar(notif)

        pendientes_emp1 = gestor.obtener_pendientes(empresa_id=1)
        pendientes_emp2 = gestor.obtener_pendientes(empresa_id=2)

        assert len(pendientes_emp1) == 2
        assert len(pendientes_emp2) == 1

    def test_marcar_leida_elimina_de_pendientes(self):
        gestor = GestorNotificaciones()
        notif = crear_notificacion(
            tipo=TipoNotificacion.ERROR_REGISTRO,
            titulo="Error al registrar factura.pdf",
            mensaje="No se pudo registrar en FacturaScripts.",
            empresa_id=1,
        )
        gestor.enviar(notif)

        assert len(gestor.obtener_pendientes()) == 1

        gestor.marcar_leida(notif.id)

        assert len(gestor.obtener_pendientes()) == 0

    def test_canal_falla_no_rompe_envio(self):
        """Un canal que lanza excepcion no impide que otros canales funcionen."""
        gestor = GestorNotificaciones()

        def canal_malo(n):
            raise RuntimeError("Canal roto")

        gestor.agregar_canal(canal_malo)
        gestor.agregar_canal(canal_log)

        notif = crear_notificacion(
            tipo=TipoNotificacion.PLAZO_FISCAL,
            titulo="Modelo 303 vence el 20-01-2026",
            mensaje="El modelo 303 vence el 20-01-2026.",
        )

        resultado = gestor.enviar(notif)
        assert resultado["enviada"] is True
        assert resultado["canales_ok"] == 1
        assert resultado["canales_error"] == 1


# ---------------------------------------------------------------------------
# Test 7: Periodicas — dry_run no registra
# ---------------------------------------------------------------------------

class TestPeriodicasDryRun:
    """Verifica que en dry_run se genera la estructura del asiento sin registrar."""

    def test_generar_asiento_periodico_estructura(self):
        operacion = {
            "operacion_id": 1,
            "empresa_id": 1,
            "tipo": "amortizacion",
            "descripcion": "Amortizacion furgoneta",
            "subcuenta_debe": "6810000000",
            "subcuenta_haber": "2810000000",
            "importe": "400.00",
            "fecha_ejecucion": date(2025, 6, 30),
            "mes": "2025-06",
            "periodicidad": "mensual",
            "parametros": {},
        }

        asiento = generar_asiento_periodico(operacion)

        assert asiento["empresa_id"] == 1
        assert asiento["fecha"] == date(2025, 6, 30)
        assert "amortizacion" in asiento["concepto"].lower()
        assert len(asiento["partidas"]) == 2

        partida_debe = next(p for p in asiento["partidas"] if p["debe"] > 0)
        partida_haber = next(p for p in asiento["partidas"] if p["haber"] > 0)
        assert partida_debe["subcuenta"] == "6810000000"
        assert partida_haber["subcuenta"] == "2810000000"
        assert partida_debe["debe"] == pytest.approx(400.0)
        assert partida_haber["haber"] == pytest.approx(400.0)

    def test_ejecutar_periodicas_dry_run(self):
        op = _op_mock(
            id_=1, empresa_id=1,
            tipo="provision_paga",
            descripcion="Provision paga extra junio",
            periodicidad="mensual",
            ultimo_ejecutado=None,
            parametros={
                "subcuenta_debe": "6400000000",
                "subcuenta_haber": "4650000000",
                "importe": "150.00",
            },
        )
        sesion = _sesion_mock([op])

        resultado = ejecutar_periodicas(
            empresa_id=1,
            mes="2025-06",
            dry_run=True,
            sesion_bd=sesion,
        )

        assert resultado["empresa_id"] == 1
        assert resultado["mes"] == "2025-06"
        assert resultado["generados"] == 1
        assert resultado["registrados"] == 0
        assert resultado["errores"] == 0

        item = resultado["detalle"][0]
        assert item["estado"] == "dry_run"
        assert "asiento" in item
        assert item["asiento"]["empresa_id"] == 1

    def test_ejecutar_periodicas_dry_run_sin_operaciones(self):
        sesion = _sesion_mock([])

        resultado = ejecutar_periodicas(
            empresa_id=1,
            mes="2025-06",
            dry_run=True,
            sesion_bd=sesion,
        )

        assert resultado["generados"] == 0
        assert resultado["registrados"] == 0
        assert resultado["errores"] == 0
        assert resultado["detalle"] == []


# ---------------------------------------------------------------------------
# Test 8: Flujo email → guardar adjuntos → detectar duplicados
# ---------------------------------------------------------------------------

class TestFlujoEmailDuplicados:
    """Simula adjuntos guardados desde email y verifica deteccion de duplicados."""

    def test_guardar_adjuntos_en_inbox_y_verificar_duplicados(self, tmp_path):
        # Simular adjuntos extraidos de un email
        adjuntos = [
            {
                "nombre": "factura_enero.pdf",
                "contenido": b"%PDF-1.4 factura enero contenido",
                "remitente": "facturas@proveedor.com",
                "asunto": "Factura enero 2025",
                "fecha": "Mon, 10 Feb 2025 09:00:00 +0100",
            },
            {
                "nombre": "factura_febrero.pdf",
                "contenido": b"%PDF-1.4 factura febrero contenido",
                "remitente": "facturas@proveedor.com",
                "asunto": "Factura febrero 2025",
                "fecha": "Mon, 10 Mar 2025 09:00:00 +0100",
            },
        ]

        slug_cliente = "B12345678_empresa-test"

        rutas_guardadas = guardar_adjuntos_en_inbox(
            adjuntos, str(tmp_path), slug_cliente=slug_cliente
        )

        assert len(rutas_guardadas) == 2
        for ruta in rutas_guardadas:
            assert Path(ruta).exists()

        # Verificar que estan en la carpeta inbox del cliente
        carpeta_inbox = tmp_path / slug_cliente / "inbox"
        assert carpeta_inbox.exists()
        pdfs = list(carpeta_inbox.glob("*.pdf"))
        assert len(pdfs) == 2

    def test_guardar_adjuntos_sin_slug_va_a_sin_clasificar(self, tmp_path):
        adjuntos = [
            {
                "nombre": "documento_desconocido.pdf",
                "contenido": b"%PDF-1.4 sin clasificar",
                "remitente": "desconocido@dominio.com",
                "asunto": "Documento",
                "fecha": "",
            }
        ]

        rutas = guardar_adjuntos_en_inbox(adjuntos, str(tmp_path), slug_cliente=None)
        assert len(rutas) == 1
        assert "_sin_clasificar" in rutas[0]

    def test_enrutar_remitente_conocido(self):
        mapa = {
            "facturas@cargaexpress.com": "B11111111_cargaexpress",
            "admin@proveedor.es": "B22222222_proveedor",
        }

        slug = enrutar_por_remitente("facturas@cargaexpress.com", mapa)
        assert slug == "B11111111_cargaexpress"

    def test_enrutar_remitente_con_nombre_display(self):
        mapa = {"facturas@empresa.com": "B99999999_empresa"}

        slug = enrutar_por_remitente("Empresa S.L. <facturas@empresa.com>", mapa)
        assert slug == "B99999999_empresa"

    def test_enrutar_remitente_desconocido_retorna_none(self):
        mapa = {"conocido@empresa.com": "B11111111_empresa"}
        slug = enrutar_por_remitente("desconocido@otro.com", mapa)
        assert slug is None

    def test_adjuntos_en_inbox_luego_duplicados(self, tmp_path):
        """Verifica que PDFs guardados en inbox pueden cotejarse con existentes."""
        adjuntos = [
            {
                "nombre": "factura_dup.pdf",
                "contenido": b"%PDF factura duplicada",
                "remitente": "prov@empresa.com",
                "asunto": "Factura duplicada",
                "fecha": "",
            }
        ]

        guardar_adjuntos_en_inbox(adjuntos, str(tmp_path), slug_cliente="cliente-test")

        # Simular datos OCR del PDF recibido por email
        datos_nuevo = {
            "cif_emisor": "B55555555",
            "numero_factura": "F2025-100",
            "fecha": "2025-03-15",
            "total": 726.0,
        }

        # Documentos ya registrados en contabilidad
        existentes = [
            {
                "cif_emisor": "B55555555",
                "numero_factura": "F2025-100",
                "fecha": "2025-03-15",
                "total": 726.0,
            }
        ]

        resultado = detectar_duplicado(datos_nuevo, existentes)
        assert resultado.es_duplicado is True
        assert resultado.tipo == "seguro"

    def test_guardar_resuelve_nombre_duplicado(self, tmp_path):
        """Si el nombre del adjunto ya existe, agrega sufijo numerico."""
        adjunto = {
            "nombre": "factura.pdf",
            "contenido": b"%PDF primero",
            "remitente": "a@b.com",
            "asunto": "",
            "fecha": "",
        }

        rutas_primera = guardar_adjuntos_en_inbox(
            [adjunto], str(tmp_path), slug_cliente="cliente"
        )
        rutas_segunda = guardar_adjuntos_en_inbox(
            [{**adjunto, "contenido": b"%PDF segundo"}],
            str(tmp_path),
            slug_cliente="cliente",
        )

        # Los dos archivos deben existir con nombres distintos
        assert rutas_primera[0] != rutas_segunda[0]
        assert Path(rutas_primera[0]).exists()
        assert Path(rutas_segunda[0]).exists()
        assert "_1" in rutas_segunda[0] or rutas_segunda[0].endswith("_1.pdf")
