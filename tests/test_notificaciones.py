"""Tests TDD para el sistema de notificaciones SFCE (Task 43)."""
import smtplib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from sfce.core.notificaciones import (
    PLANTILLAS,
    GestorNotificaciones,
    Notificacion,
    TipoNotificacion,
    canal_email,
    canal_log,
    canal_websocket,
    crear_notificacion,
    gestor_notificaciones,
    notificar,
)


# ===========================================================================
# TipoNotificacion
# ===========================================================================

class TestTipoNotificacion:
    """Verifica que el enum tiene todos los valores requeridos."""

    def test_tiene_documento_ilegible(self):
        assert TipoNotificacion.DOCUMENTO_ILEGIBLE.value == "documento_ilegible"

    def test_tiene_proveedor_nuevo(self):
        assert TipoNotificacion.PROVEEDOR_NUEVO.value == "proveedor_nuevo"

    def test_tiene_trabajador_nuevo(self):
        assert TipoNotificacion.TRABAJADOR_NUEVO.value == "trabajador_nuevo"

    def test_tiene_plazo_fiscal(self):
        assert TipoNotificacion.PLAZO_FISCAL.value == "plazo_fiscal"

    def test_tiene_factura_recurrente_faltante(self):
        assert TipoNotificacion.FACTURA_RECURRENTE_FALTANTE.value == "factura_recurrente_faltante"

    def test_tiene_error_registro(self):
        assert TipoNotificacion.ERROR_REGISTRO.value == "error_registro"

    def test_tiene_cuarentena(self):
        assert TipoNotificacion.CUARENTENA.value == "cuarentena"

    def test_total_valores(self):
        assert len(TipoNotificacion) == 8


# ===========================================================================
# crear_notificacion
# ===========================================================================

class TestCrearNotificacion:
    """Verifica la factory function crear_notificacion."""

    def test_genera_id_automatico(self):
        n = crear_notificacion(
            TipoNotificacion.CUARENTENA, "Titulo", "Mensaje"
        )
        assert n.id
        assert len(n.id) == 36  # UUID formato estandar

    def test_genera_timestamp_automatico(self):
        n = crear_notificacion(
            TipoNotificacion.CUARENTENA, "Titulo", "Mensaje"
        )
        assert n.timestamp
        # Debe ser parseable como ISO8601
        dt = datetime.fromisoformat(n.timestamp.replace("Z", "+00:00"))
        assert dt.year >= 2026

    def test_leida_false_por_defecto(self):
        n = crear_notificacion(
            TipoNotificacion.CUARENTENA, "Titulo", "Mensaje"
        )
        assert n.leida is False

    def test_empresa_id_none_por_defecto(self):
        n = crear_notificacion(
            TipoNotificacion.CUARENTENA, "Titulo", "Mensaje"
        )
        assert n.empresa_id is None

    def test_empresa_id_se_asigna(self):
        n = crear_notificacion(
            TipoNotificacion.CUARENTENA, "Titulo", "Mensaje", empresa_id=5
        )
        assert n.empresa_id == 5

    def test_datos_extra_se_almacenan(self):
        n = crear_notificacion(
            TipoNotificacion.CUARENTENA,
            "Titulo",
            "Mensaje",
            empresa_id=1,
            nombre="factura.pdf",
            motivo="OCR fallido",
        )
        assert n.datos_extra["nombre"] == "factura.pdf"
        assert n.datos_extra["motivo"] == "OCR fallido"

    def test_tipo_asignado(self):
        n = crear_notificacion(
            TipoNotificacion.PROVEEDOR_NUEVO, "Titulo", "Mensaje"
        )
        assert n.tipo == TipoNotificacion.PROVEEDOR_NUEVO

    def test_ids_son_unicos(self):
        ids = {
            crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M").id
            for _ in range(10)
        }
        assert len(ids) == 10


# ===========================================================================
# GestorNotificaciones
# ===========================================================================

class TestGestorNotificaciones:
    """Verifica el gestor de notificaciones."""

    def _gestor_limpio(self):
        """Crea instancia fresca para cada test."""
        return GestorNotificaciones()

    def test_enviar_almacena_notificacion(self):
        gestor = self._gestor_limpio()
        n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M", empresa_id=1)
        resultado = gestor.enviar(n)
        assert resultado["enviada"] is True
        assert len(gestor.historial()) == 1

    def test_enviar_sin_canales_ok_cero(self):
        gestor = self._gestor_limpio()
        n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M")
        resultado = gestor.enviar(n)
        assert resultado["canales_ok"] == 0
        assert resultado["canales_error"] == 0

    def test_enviar_despacha_a_canal(self):
        gestor = self._gestor_limpio()
        recibidas = []
        gestor.agregar_canal(lambda notif: recibidas.append(notif) or True)
        n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M")
        gestor.enviar(n)
        assert len(recibidas) == 1
        assert recibidas[0] is n

    def test_enviar_contabiliza_canales_ok(self):
        gestor = self._gestor_limpio()
        gestor.agregar_canal(lambda n: True)
        gestor.agregar_canal(lambda n: True)
        n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M")
        resultado = gestor.enviar(n)
        assert resultado["canales_ok"] == 2
        assert resultado["canales_error"] == 0

    def test_canal_que_falla_contabiliza_error(self):
        gestor = self._gestor_limpio()
        gestor.agregar_canal(lambda n: True)

        def canal_malo(notif):
            raise RuntimeError("Fallo intencional")

        gestor.agregar_canal(canal_malo)
        n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M")
        resultado = gestor.enviar(n)
        assert resultado["canales_ok"] == 1
        assert resultado["canales_error"] == 1
        # La notificacion igual se almacena
        assert resultado["enviada"] is True

    def test_canal_que_retorna_false_cuenta_como_error(self):
        gestor = self._gestor_limpio()
        gestor.agregar_canal(lambda n: False)
        n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M")
        resultado = gestor.enviar(n)
        assert resultado["canales_error"] == 1

    def test_obtener_pendientes_filtra_no_leidas(self):
        gestor = self._gestor_limpio()
        n1 = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M", empresa_id=1)
        n2 = crear_notificacion(TipoNotificacion.PROVEEDOR_NUEVO, "T", "M", empresa_id=1)
        gestor.enviar(n1)
        gestor.enviar(n2)
        gestor.marcar_leida(n1.id)
        pendientes = gestor.obtener_pendientes()
        assert len(pendientes) == 1
        assert pendientes[0].id == n2.id

    def test_obtener_pendientes_filtra_por_empresa(self):
        gestor = self._gestor_limpio()
        n1 = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M", empresa_id=1)
        n2 = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M", empresa_id=2)
        n3 = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M", empresa_id=1)
        gestor.enviar(n1)
        gestor.enviar(n2)
        gestor.enviar(n3)
        pendientes = gestor.obtener_pendientes(empresa_id=1)
        assert len(pendientes) == 2
        assert all(p.empresa_id == 1 for p in pendientes)

    def test_obtener_pendientes_sin_empresa_devuelve_todas_no_leidas(self):
        gestor = self._gestor_limpio()
        for i in range(3):
            n = crear_notificacion(
                TipoNotificacion.CUARENTENA, "T", "M", empresa_id=i
            )
            gestor.enviar(n)
        assert len(gestor.obtener_pendientes()) == 3

    def test_marcar_leida_cambia_estado(self):
        gestor = self._gestor_limpio()
        n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M")
        gestor.enviar(n)
        resultado = gestor.marcar_leida(n.id)
        assert resultado is True
        assert gestor.historial()[0].leida is True

    def test_marcar_leida_id_inexistente_devuelve_false(self):
        gestor = self._gestor_limpio()
        resultado = gestor.marcar_leida("id-que-no-existe")
        assert resultado is False

    def test_historial_devuelve_todas(self):
        gestor = self._gestor_limpio()
        for _ in range(5):
            n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M")
            gestor.enviar(n)
        assert len(gestor.historial()) == 5

    def test_historial_filtra_por_empresa(self):
        gestor = self._gestor_limpio()
        for i in range(4):
            n = crear_notificacion(
                TipoNotificacion.CUARENTENA, "T", "M", empresa_id=i % 2
            )
            gestor.enviar(n)
        assert len(gestor.historial(empresa_id=0)) == 2
        assert len(gestor.historial(empresa_id=1)) == 2

    def test_historial_respeta_limite(self):
        gestor = self._gestor_limpio()
        for _ in range(20):
            n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M")
            gestor.enviar(n)
        assert len(gestor.historial(limite=5)) == 5

    def test_historial_limite_devuelve_ultimas(self):
        """El limite debe devolver las ultimas N notificaciones."""
        gestor = self._gestor_limpio()
        ids_insertados = []
        for i in range(10):
            n = crear_notificacion(
                TipoNotificacion.CUARENTENA, f"T{i}", "M"
            )
            gestor.enviar(n)
            ids_insertados.append(n.id)
        ultimas_3 = gestor.historial(limite=3)
        assert len(ultimas_3) == 3
        # Deben ser las ultimas insertadas
        assert {n.id for n in ultimas_3} == set(ids_insertados[-3:])

    def test_agregar_canal_multiple(self):
        gestor = self._gestor_limpio()
        llamadas = []
        gestor.agregar_canal(lambda n: llamadas.append(1) or True)
        gestor.agregar_canal(lambda n: llamadas.append(2) or True)
        gestor.agregar_canal(lambda n: llamadas.append(3) or True)
        gestor.enviar(crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M"))
        assert len(llamadas) == 3


# ===========================================================================
# canal_log
# ===========================================================================

class TestCanalLog:
    """Verifica que canal_log escribe al logger y no falla."""

    def test_canal_log_retorna_true(self):
        n = crear_notificacion(
            TipoNotificacion.ERROR_REGISTRO, "Error", "Detalles del error"
        )
        with patch("sfce.core.notificaciones._logger") as mock_log:
            resultado = canal_log(n)
        assert resultado is True

    def test_canal_log_llama_a_logger(self):
        n = crear_notificacion(
            TipoNotificacion.PLAZO_FISCAL, "Plazo", "Vence el 20 de enero"
        )
        with patch("sfce.core.notificaciones._logger") as mock_log:
            canal_log(n)
            assert mock_log.log.called or mock_log.info.called or mock_log.warning.called or mock_log.error.called

    def test_canal_log_no_lanza_excepcion(self):
        n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M")
        # No debe lanzar aunque logger falle internamente
        with patch("sfce.core.notificaciones._logger") as mock_log:
            mock_log.log.side_effect = RuntimeError("Logger caido")
            resultado = canal_log(n)
        assert resultado is False  # Fallo, pero no propagacion


# ===========================================================================
# canal_email
# ===========================================================================

class TestCanalEmail:
    """Verifica canal_email con mock de smtplib."""

    def _config_smtp(self):
        return {
            "servidor": "smtp.ejemplo.com",
            "puerto": 587,
            "usuario": "user@ejemplo.com",
            "contrasena": "secreto123",
            "destinatario": "gestor@ejemplo.com",
        }

    def test_canal_email_retorna_true_con_smtp_ok(self):
        n = crear_notificacion(
            TipoNotificacion.PLAZO_FISCAL, "Plazo IVA", "Vence manana"
        )
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            resultado = canal_email(n, self._config_smtp())
        assert resultado is True

    def test_canal_email_llama_sendmail(self):
        n = crear_notificacion(
            TipoNotificacion.PLAZO_FISCAL, "Plazo IVA", "Vence manana"
        )
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            canal_email(n, self._config_smtp())
            assert mock_smtp.sendmail.called

    def test_canal_email_retorna_false_si_smtp_falla(self):
        n = crear_notificacion(
            TipoNotificacion.PLAZO_FISCAL, "Plazo IVA", "Vence manana"
        )
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.side_effect = smtplib.SMTPException("Fallo")
            resultado = canal_email(n, self._config_smtp())
        assert resultado is False

    def test_canal_email_usa_config_correcta(self):
        n = crear_notificacion(
            TipoNotificacion.ERROR_REGISTRO, "Error", "Detalle"
        )
        config = self._config_smtp()
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            canal_email(n, config)
            mock_smtp_cls.assert_called_with(config["servidor"], config["puerto"])


# ===========================================================================
# canal_websocket
# ===========================================================================

class TestCanalWebSocket:
    """Verifica canal_websocket con mock de gestor_ws."""

    def test_canal_websocket_retorna_true_con_empresa(self):
        import asyncio

        n = crear_notificacion(
            TipoNotificacion.CUARENTENA, "Doc en cuarentena", "Revisar", empresa_id=3
        )
        mock_ws = MagicMock()

        async def _coro(*args, **kwargs):
            return None

        mock_ws.emitir_a_empresa = MagicMock(return_value=_coro())
        with patch("sfce.core.notificaciones._obtener_gestor_ws", return_value=mock_ws):
            resultado = canal_websocket(n)
        assert resultado is True

    def test_canal_websocket_llama_emitir_a_empresa(self):
        import asyncio

        n = crear_notificacion(
            TipoNotificacion.CUARENTENA, "T", "M", empresa_id=7
        )
        mock_ws = MagicMock()

        llamadas = []

        async def _coro(empresa_id, evento, datos):
            llamadas.append((empresa_id, evento, datos))

        mock_ws.emitir_a_empresa = _coro
        with patch("sfce.core.notificaciones._obtener_gestor_ws", return_value=mock_ws):
            canal_websocket(n)
        assert len(llamadas) == 1
        empresa_id_llamado, evento_llamado, datos_llamados = llamadas[0]
        assert empresa_id_llamado == 7
        assert evento_llamado == "notificacion"
        assert datos_llamados["tipo"] == "cuarentena"

    def test_canal_websocket_sin_empresa_retorna_false(self):
        n = crear_notificacion(TipoNotificacion.CUARENTENA, "T", "M")
        resultado = canal_websocket(n)
        assert resultado is False

    def test_canal_websocket_retorna_false_si_falla(self):
        n = crear_notificacion(
            TipoNotificacion.CUARENTENA, "T", "M", empresa_id=1
        )
        with patch(
            "sfce.core.notificaciones._obtener_gestor_ws",
            side_effect=ImportError("No disponible"),
        ):
            resultado = canal_websocket(n)
        assert resultado is False


# ===========================================================================
# PLANTILLAS
# ===========================================================================

class TestPlantillas:
    """Verifica que PLANTILLAS tiene entradas para cada TipoNotificacion."""

    def test_plantillas_cubre_todos_los_tipos(self):
        for tipo in TipoNotificacion:
            assert tipo in PLANTILLAS, f"Falta plantilla para {tipo}"

    def test_cada_plantilla_tiene_titulo_y_mensaje(self):
        for tipo, plantilla in PLANTILLAS.items():
            assert "titulo" in plantilla, f"Falta titulo en {tipo}"
            assert "mensaje" in plantilla, f"Falta mensaje en {tipo}"

    def test_plantilla_documento_ilegible_con_nombre(self):
        plantilla = PLANTILLAS[TipoNotificacion.DOCUMENTO_ILEGIBLE]
        titulo = plantilla["titulo"].format(nombre="factura.pdf", motivo="OCR")
        mensaje = plantilla["mensaje"].format(nombre="factura.pdf", motivo="OCR")
        assert "factura.pdf" in titulo
        assert "factura.pdf" in mensaje

    def test_plantilla_proveedor_nuevo_con_nombre_cif(self):
        plantilla = PLANTILLAS[TipoNotificacion.PROVEEDOR_NUEVO]
        titulo = plantilla["titulo"].format(nombre="Empresa SA", cif="B12345678")
        assert "Empresa SA" in titulo or "B12345678" in titulo

    def test_plantilla_plazo_fiscal_con_fecha(self):
        plantilla = PLANTILLAS[TipoNotificacion.PLAZO_FISCAL]
        titulo = plantilla["titulo"].format(modelo="303", fecha="20/01/2026")
        assert "303" in titulo or "20/01/2026" in titulo

    def test_plantilla_error_registro_con_nombre(self):
        plantilla = PLANTILLAS[TipoNotificacion.ERROR_REGISTRO]
        titulo = plantilla["titulo"].format(nombre="factura_01.pdf")
        assert "factura_01.pdf" in titulo

    def test_plantilla_cuarentena_con_nombre(self):
        plantilla = PLANTILLAS[TipoNotificacion.CUARENTENA]
        titulo = plantilla["titulo"].format(nombre="factura.pdf")
        assert "factura.pdf" in titulo

    def test_plantilla_trabajador_nuevo_con_nombre(self):
        plantilla = PLANTILLAS[TipoNotificacion.TRABAJADOR_NUEVO]
        titulo = plantilla["titulo"].format(nombre="Juan Perez", nif="12345678A")
        assert "Juan Perez" in titulo or "12345678A" in titulo

    def test_plantilla_factura_recurrente_faltante(self):
        plantilla = PLANTILLAS[TipoNotificacion.FACTURA_RECURRENTE_FALTANTE]
        titulo = plantilla["titulo"].format(
            nombre="Endesa", periodo="2026-01"
        )
        assert "Endesa" in titulo or "2026-01" in titulo


# ===========================================================================
# notificar (shortcut global)
# ===========================================================================

class TestNotificar:
    """Verifica el shortcut notificar end-to-end."""

    def test_notificar_retorna_notificacion(self):
        with patch.object(gestor_notificaciones, "enviar") as mock_enviar:
            mock_enviar.return_value = {"enviada": True, "canales_ok": 0, "canales_error": 0}
            n = notificar(
                TipoNotificacion.CUARENTENA,
                empresa_id=1,
                nombre="factura.pdf",
            )
        assert isinstance(n, Notificacion)

    def test_notificar_usa_plantilla(self):
        with patch.object(gestor_notificaciones, "enviar") as mock_enviar:
            mock_enviar.return_value = {"enviada": True, "canales_ok": 0, "canales_error": 0}
            n = notificar(
                TipoNotificacion.DOCUMENTO_ILEGIBLE,
                empresa_id=1,
                nombre="archivo.pdf",
                motivo="Imagen borrosa",
            )
        assert "archivo.pdf" in n.titulo
        assert "archivo.pdf" in n.mensaje

    def test_notificar_llama_a_gestor_enviar(self):
        with patch.object(gestor_notificaciones, "enviar") as mock_enviar:
            mock_enviar.return_value = {"enviada": True, "canales_ok": 0, "canales_error": 0}
            notificar(TipoNotificacion.PLAZO_FISCAL, modelo="303", fecha="20/01")
        assert mock_enviar.called

    def test_notificar_asigna_empresa_id(self):
        with patch.object(gestor_notificaciones, "enviar") as mock_enviar:
            mock_enviar.return_value = {"enviada": True, "canales_ok": 0, "canales_error": 0}
            n = notificar(
                TipoNotificacion.PROVEEDOR_NUEVO,
                empresa_id=42,
                nombre="Proveedor Test",
                cif="B00000001",
            )
        assert n.empresa_id == 42

    def test_notificar_con_placeholder_faltante_no_falla(self):
        """Si faltan kwargs para el template, debe usar el template tal cual."""
        with patch.object(gestor_notificaciones, "enviar") as mock_enviar:
            mock_enviar.return_value = {"enviada": True, "canales_ok": 0, "canales_error": 0}
            # Sin pasar nombre ni motivo para DOCUMENTO_ILEGIBLE
            n = notificar(TipoNotificacion.DOCUMENTO_ILEGIBLE)
        assert isinstance(n, Notificacion)


# ===========================================================================
# gestor_notificaciones (instancia global)
# ===========================================================================

class TestGestorGlobal:
    """Verifica que la instancia global existe y es del tipo correcto."""

    def test_gestor_global_existe(self):
        assert gestor_notificaciones is not None

    def test_gestor_global_es_gestor_notificaciones(self):
        assert isinstance(gestor_notificaciones, GestorNotificaciones)
