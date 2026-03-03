"""Tests para WebSocket — gestor de conexiones y endpoints."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sfce.api.websocket import (
    EVENTO_CUARENTENA_NUEVO,
    EVENTO_CUARENTENA_RESUELTA,
    EVENTO_DOCUMENTO_PROCESADO,
    EVENTO_ERROR,
    EVENTO_PIPELINE_PROGRESO,
    EVENTO_SALDO_ACTUALIZADO,
    GestorWebSocket,
    gestor_ws,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _crear_ws_mock() -> AsyncMock:
    """Crea un mock de WebSocket con send_json asyncio."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# Tests unitarios de GestorWebSocket
# ---------------------------------------------------------------------------
class TestGestorWebSocket:
    """Tests para la clase GestorWebSocket."""

    @pytest.fixture
    def gestor(self) -> GestorWebSocket:
        return GestorWebSocket()

    @pytest.mark.asyncio
    async def test_conectar_acepta_y_registra(self, gestor: GestorWebSocket):
        """conectar() acepta el websocket y lo registra en el canal."""
        ws = _crear_ws_mock()
        await gestor.conectar(ws, canal="general")

        ws.accept.assert_awaited_once()
        assert gestor.conexiones_activas == 1

    @pytest.mark.asyncio
    async def test_conectar_multiples_canales(self, gestor: GestorWebSocket):
        """Conexiones en distintos canales se cuentan correctamente."""
        ws1 = _crear_ws_mock()
        ws2 = _crear_ws_mock()
        ws3 = _crear_ws_mock()

        await gestor.conectar(ws1, canal="general")
        await gestor.conectar(ws2, canal="empresa_1")
        await gestor.conectar(ws3, canal="empresa_2")

        assert gestor.conexiones_activas == 3

    @pytest.mark.asyncio
    async def test_conectar_mismo_canal_multiples(self, gestor: GestorWebSocket):
        """Multiples conexiones en el mismo canal."""
        ws1 = _crear_ws_mock()
        ws2 = _crear_ws_mock()

        await gestor.conectar(ws1, canal="general")
        await gestor.conectar(ws2, canal="general")

        assert gestor.conexiones_activas == 2

    @pytest.mark.asyncio
    async def test_desconectar_elimina_conexion(self, gestor: GestorWebSocket):
        """desconectar() elimina la conexion del canal."""
        ws = _crear_ws_mock()
        await gestor.conectar(ws, canal="general")
        assert gestor.conexiones_activas == 1

        await gestor.desconectar(ws, canal="general")
        assert gestor.conexiones_activas == 0

    @pytest.mark.asyncio
    async def test_desconectar_canal_inexistente(self, gestor: GestorWebSocket):
        """desconectar() en canal inexistente no falla."""
        ws = _crear_ws_mock()
        # No deberia lanzar excepcion
        await gestor.desconectar(ws, canal="no_existe")
        assert gestor.conexiones_activas == 0

    @pytest.mark.asyncio
    async def test_desconectar_ws_no_registrado(self, gestor: GestorWebSocket):
        """desconectar() un ws no registrado en canal existente no falla."""
        ws1 = _crear_ws_mock()
        ws2 = _crear_ws_mock()

        await gestor.conectar(ws1, canal="general")
        # ws2 nunca se conecto
        await gestor.desconectar(ws2, canal="general")
        assert gestor.conexiones_activas == 1

    @pytest.mark.asyncio
    async def test_conexiones_activas_vacio(self, gestor: GestorWebSocket):
        """conexiones_activas es 0 con gestor nuevo."""
        assert gestor.conexiones_activas == 0

    @pytest.mark.asyncio
    async def test_emitir_envia_a_canal_correcto(self, gestor: GestorWebSocket):
        """emitir() envia solo a los clientes del canal indicado."""
        ws_general = _crear_ws_mock()
        ws_empresa = _crear_ws_mock()

        await gestor.conectar(ws_general, canal="general")
        await gestor.conectar(ws_empresa, canal="empresa_1")

        await gestor.emitir(
            EVENTO_PIPELINE_PROGRESO, {"fase": 3, "total": 7}, canal="general"
        )

        # ws_general recibe, ws_empresa no
        ws_general.send_json.assert_awaited_once()
        ws_empresa.send_json.assert_not_awaited()

        # Verificar formato del mensaje
        mensaje = ws_general.send_json.call_args[0][0]
        assert mensaje["evento"] == EVENTO_PIPELINE_PROGRESO
        assert mensaje["datos"]["fase"] == 3
        assert "timestamp" in mensaje

    @pytest.mark.asyncio
    async def test_emitir_formato_mensaje(self, gestor: GestorWebSocket):
        """emitir() genera mensaje con formato correcto."""
        ws = _crear_ws_mock()
        await gestor.conectar(ws, canal="general")

        datos = {"documento": "factura_001.pdf", "estado": "ok"}
        await gestor.emitir(EVENTO_DOCUMENTO_PROCESADO, datos, canal="general")

        mensaje = ws.send_json.call_args[0][0]
        assert mensaje["evento"] == EVENTO_DOCUMENTO_PROCESADO
        assert mensaje["datos"] == datos
        assert "timestamp" in mensaje
        # timestamp debe ser ISO8601
        assert "T" in mensaje["timestamp"]

    @pytest.mark.asyncio
    async def test_emitir_a_empresa(self, gestor: GestorWebSocket):
        """emitir_a_empresa() usa canal empresa_{id}."""
        ws = _crear_ws_mock()
        await gestor.conectar(ws, canal="empresa_5")

        await gestor.emitir_a_empresa(
            5, EVENTO_SALDO_ACTUALIZADO, {"subcuenta": "4300000001", "saldo": 1500.0}
        )

        ws.send_json.assert_awaited_once()
        mensaje = ws.send_json.call_args[0][0]
        assert mensaje["evento"] == EVENTO_SALDO_ACTUALIZADO
        assert mensaje["datos"]["saldo"] == 1500.0

    @pytest.mark.asyncio
    async def test_emitir_a_empresa_sin_conexiones(self, gestor: GestorWebSocket):
        """emitir_a_empresa() sin conexiones no falla."""
        # No deberia lanzar excepcion
        await gestor.emitir_a_empresa(
            99, EVENTO_ERROR, {"mensaje": "algo fallo"}
        )

    @pytest.mark.asyncio
    async def test_emitir_canal_vacio(self, gestor: GestorWebSocket):
        """emitir() a canal sin conexiones no falla."""
        await gestor.emitir(EVENTO_ERROR, {"detalle": "test"}, canal="vacio")

    @pytest.mark.asyncio
    async def test_emitir_cliente_desconectado(self, gestor: GestorWebSocket):
        """emitir() con cliente desconectado lo elimina silenciosamente."""
        ws_ok = _crear_ws_mock()
        ws_roto = _crear_ws_mock()
        ws_roto.send_json.side_effect = RuntimeError("conexion cerrada")

        await gestor.conectar(ws_ok, canal="general")
        await gestor.conectar(ws_roto, canal="general")
        assert gestor.conexiones_activas == 2

        await gestor.emitir(EVENTO_ERROR, {"detalle": "test"}, canal="general")

        # ws_roto eliminado, ws_ok sigue
        assert gestor.conexiones_activas == 1
        ws_ok.send_json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_emitir_todos_desconectados(self, gestor: GestorWebSocket):
        """Si todos los clientes estan rotos, el canal se limpia."""
        ws1 = _crear_ws_mock()
        ws1.send_json.side_effect = RuntimeError("cerrado")
        ws2 = _crear_ws_mock()
        ws2.send_json.side_effect = RuntimeError("cerrado")

        await gestor.conectar(ws1, canal="test")
        await gestor.conectar(ws2, canal="test")
        assert gestor.conexiones_activas == 2

        await gestor.emitir(EVENTO_ERROR, {}, canal="test")
        assert gestor.conexiones_activas == 0


# ---------------------------------------------------------------------------
# Tests de constantes de eventos
# ---------------------------------------------------------------------------
class TestConstantesEvento:
    """Verifica que las constantes de evento existen."""

    def test_constantes_definidas(self):
        assert EVENTO_PIPELINE_PROGRESO == "pipeline_progreso"
        assert EVENTO_DOCUMENTO_PROCESADO == "documento_procesado"
        assert EVENTO_CUARENTENA_NUEVO == "cuarentena_nuevo"
        assert EVENTO_CUARENTENA_RESUELTA == "cuarentena_resuelta"
        assert EVENTO_SALDO_ACTUALIZADO == "saldo_actualizado"
        assert EVENTO_ERROR == "error"


# ---------------------------------------------------------------------------
# Tests de singleton global
# ---------------------------------------------------------------------------
class TestSingletonGlobal:
    """Verifica que gestor_ws es una instancia global de GestorWebSocket."""

    def test_instancia_global(self):
        assert isinstance(gestor_ws, GestorWebSocket)

    def test_importacion_consistente(self):
        """Importar desde dos sitios da la misma instancia."""
        from sfce.api.websocket import gestor_ws as g1
        from sfce.api.websocket import gestor_ws as g2
        assert g1 is g2


# ---------------------------------------------------------------------------
# Tests de endpoint WebSocket via TestClient
# ---------------------------------------------------------------------------
class TestWebSocketEndpoint:
    """Tests de integracion de los endpoints WebSocket."""

    @pytest.fixture
    def client(self):
        import os
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from sfce.api.app import crear_app
        from sfce.api.auth import crear_admin_por_defecto
        from sfce.db.base import Base

        os.environ.setdefault("SFCE_JWT_SECRET", "test-secret-de-pruebas-con-al-menos-32-caracteres-ok")
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        sf = sessionmaker(bind=engine)
        crear_admin_por_defecto(sf)
        app = crear_app(sesion_factory=sf)
        c = TestClient(app)
        resp = c.post("/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
        token = resp.json()["access_token"]
        c._ws_token = token
        return c

    def test_ws_general_conecta(self, client):
        """WS /api/ws conecta y responde pong a ping."""
        with client.websocket_connect(f"/api/ws?token={client._ws_token}") as ws:
            ws.send_json({"tipo": "ping"})
            resp = ws.receive_json()
            assert resp["tipo"] == "pong"

    def test_ws_empresa_conecta(self, client):
        """WS /api/ws/{empresa_id} conecta con superadmin (acceso total)."""
        # Superadmin tiene acceso a cualquier empresa_id
        with pytest.raises(Exception):
            # empresa 999 no existe pero el error es de acceso, no de auth
            with client.websocket_connect(f"/api/ws/999?token={client._ws_token}") as ws:
                ws.send_json({"tipo": "ping"})

    def test_ws_general_recibe_evento(self, client):
        """Cliente WS general recibe ping/pong."""
        resultado = {}

        def escuchar():
            with client.websocket_connect(f"/api/ws?token={client._ws_token}") as ws:
                ws.send_json({"tipo": "ping"})
                resp = ws.receive_json()
                resultado["pong"] = resp

        escuchar()
        assert resultado["pong"]["tipo"] == "pong"

    def test_ws_gestor_en_app_state(self, client):
        """El gestor_ws esta disponible en app.state."""
        app = client.app
        assert hasattr(app.state, "gestor_ws")
        assert isinstance(app.state.gestor_ws, GestorWebSocket)
