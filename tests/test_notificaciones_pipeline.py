"""Tests para clasificar_motivo_cuarentena, notificar_cuarentena y crear_notificacion_usuario."""
from unittest.mock import MagicMock, patch


# ===========================================================================
# crear_notificacion_usuario — función unificada
# ===========================================================================

class TestCrearNotificacionUsuario:
    """Verifica que crear_notificacion_usuario persiste en BD y despacha canales."""

    def _sesion_mock(self):
        """Sesión SQLAlchemy simulada con flush/add."""
        sesion = MagicMock()
        notif_bd = MagicMock()
        notif_bd.id = 42
        # crear_notificacion_bd hace sesion.add + sesion.flush; simular el objeto retornado
        sesion.add = MagicMock()
        sesion.flush = MagicMock()
        return sesion, notif_bd

    def test_persiste_en_bd(self):
        from sfce.core.notificaciones import crear_notificacion_usuario, crear_notificacion_bd
        sesion = MagicMock()
        with patch("sfce.core.notificaciones.crear_notificacion_bd") as mock_bd:
            mock_bd.return_value = MagicMock(id=1)
            resultado = crear_notificacion_usuario(
                db=sesion,
                empresa_id=5,
                tipo="aviso_gestor",
                mensaje="Test mensaje",
                titulo="Test titulo",
            )
        mock_bd.assert_called_once()
        kwargs = mock_bd.call_args[1]
        assert kwargs["empresa_id"] == 5
        assert kwargs["tipo"] == "aviso_gestor"
        assert kwargs["descripcion"] == "Test mensaje"
        assert kwargs["titulo"] == "Test titulo"

    def test_titulo_por_defecto_trunca_mensaje(self):
        from sfce.core.notificaciones import crear_notificacion_usuario
        sesion = MagicMock()
        mensaje_largo = "A" * 200
        with patch("sfce.core.notificaciones.crear_notificacion_bd") as mock_bd:
            mock_bd.return_value = MagicMock(id=2)
            crear_notificacion_usuario(db=sesion, empresa_id=1, tipo="info", mensaje=mensaje_largo)
        kwargs = mock_bd.call_args[1]
        assert len(kwargs["titulo"]) == 100

    def test_despacha_canal_log(self):
        from sfce.core.notificaciones import crear_notificacion_usuario, gestor_notificaciones, canal_log
        sesion = MagicMock()
        llamadas = []
        canal_test = lambda n: llamadas.append(n) or True
        gestor_notificaciones._canales = [canal_test]
        with patch("sfce.core.notificaciones.crear_notificacion_bd") as mock_bd:
            mock_bd.return_value = MagicMock(id=3)
            crear_notificacion_usuario(
                db=sesion, empresa_id=7, tipo="doc_ilegible", mensaje="Foto borrosa"
            )
        assert len(llamadas) == 1
        assert llamadas[0].empresa_id == 7
        gestor_notificaciones._canales = [canal_log]  # restaurar

    def test_retorna_objeto_notificacion_bd(self):
        from sfce.core.notificaciones import crear_notificacion_usuario
        sesion = MagicMock()
        mock_retorno = MagicMock(id=99)
        with patch("sfce.core.notificaciones.crear_notificacion_bd", return_value=mock_retorno):
            resultado = crear_notificacion_usuario(
                db=sesion, empresa_id=1, tipo="info", mensaje="ok"
            )
        assert resultado is mock_retorno

    def test_fallo_en_canales_no_propaga(self):
        from sfce.core.notificaciones import crear_notificacion_usuario, gestor_notificaciones, canal_log
        sesion = MagicMock()

        def canal_malo(n):
            raise RuntimeError("canal roto")

        gestor_notificaciones._canales = [canal_malo]
        with patch("sfce.core.notificaciones.crear_notificacion_bd") as mock_bd:
            mock_bd.return_value = MagicMock(id=5)
            # No debe lanzar aunque el canal falle
            resultado = crear_notificacion_usuario(
                db=sesion, empresa_id=2, tipo="aviso_gestor", mensaje="algo"
            )
        assert resultado is not None
        gestor_notificaciones._canales = [canal_log]  # restaurar


# ===========================================================================
# clasificar_motivo_cuarentena
# ===========================================================================

def test_motivo_ilegible_notifica_cliente():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("foto borrosa") == "cliente"
    assert clasificar_motivo_cuarentena("ilegible") == "cliente"
    assert clasificar_motivo_cuarentena("duplicado") == "cliente"
    assert clasificar_motivo_cuarentena("sin datos extraibles") == "cliente"


def test_motivo_contable_notifica_gestor():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("entidad desconocida") == "gestor"
    assert clasificar_motivo_cuarentena("fecha fuera del ejercicio") == "gestor"
    assert clasificar_motivo_cuarentena("importe negativo") == "gestor"
    assert clasificar_motivo_cuarentena("cif inválido") == "gestor"


def test_motivo_desconocido_notifica_gestor():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("error desconocido") == "gestor"
    assert clasificar_motivo_cuarentena("error raro") == "gestor"


def test_clasificar_case_insensitive():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("Foto Borrosa") == "cliente"
    assert clasificar_motivo_cuarentena("ILEGIBLE") == "cliente"
