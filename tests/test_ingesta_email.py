"""Tests para sfce/core/ingesta_email.py — Ingesta de email via IMAP (Task 42).

TDD: estos tests se escriben antes de la implementacion.
Todos los tests usan mocks para evitar conexiones reales a servidores IMAP.
"""
import email
import email.mime.multipart
import email.mime.base
import email.mime.text
import imaplib
from email.encoders import encode_base64
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from sfce.core.ingesta_email import (
    ConfigEmail,
    conectar_imap,
    buscar_emails_no_leidos,
    extraer_adjuntos_pdf,
    enrutar_por_remitente,
    guardar_adjuntos_en_inbox,
    procesar_correo,
)


# ---------------------------------------------------------------------------
# Helpers para construir mensajes MIME falsos
# ---------------------------------------------------------------------------

def _construir_email_con_pdf(remitente: str, asunto: str, nombre_pdf: str, contenido_pdf: bytes) -> bytes:
    """Construye un mensaje MIME con un adjunto PDF fake."""
    msg = email.mime.multipart.MIMEMultipart()
    msg["From"] = remitente
    msg["To"] = "contabilidad@ejemplo.com"
    msg["Subject"] = asunto
    msg["Date"] = "Thu, 27 Feb 2026 10:00:00 +0100"

    # Cuerpo texto
    cuerpo = email.mime.text.MIMEText("Adjunto factura en PDF.", "plain")
    msg.attach(cuerpo)

    # Adjunto PDF
    adjunto = email.mime.base.MIMEBase("application", "pdf")
    adjunto.set_payload(contenido_pdf)
    encode_base64(adjunto)
    adjunto.add_header("Content-Disposition", "attachment", filename=nombre_pdf)
    msg.attach(adjunto)

    return msg.as_bytes()


def _construir_email_sin_adjuntos(remitente: str, asunto: str) -> bytes:
    """Construye un mensaje MIME sin adjuntos."""
    msg = email.mime.multipart.MIMEMultipart()
    msg["From"] = remitente
    msg["To"] = "contabilidad@ejemplo.com"
    msg["Subject"] = asunto
    msg["Date"] = "Thu, 27 Feb 2026 11:00:00 +0100"
    cuerpo = email.mime.text.MIMEText("Sin adjuntos.", "plain")
    msg.attach(cuerpo)
    return msg.as_bytes()


def _construir_email_con_imagen(remitente: str) -> bytes:
    """Construye un mensaje con adjunto que NO es PDF (imagen JPG)."""
    msg = email.mime.multipart.MIMEMultipart()
    msg["From"] = remitente
    msg["To"] = "contabilidad@ejemplo.com"
    msg["Subject"] = "Imagen adjunta"
    msg["Date"] = "Thu, 27 Feb 2026 12:00:00 +0100"

    adjunto = email.mime.base.MIMEBase("image", "jpeg")
    adjunto.set_payload(b"\xff\xd8\xff")  # cabecera JPEG minima
    encode_base64(adjunto)
    adjunto.add_header("Content-Disposition", "attachment", filename="foto.jpg")
    msg.attach(adjunto)
    return msg.as_bytes()


# ---------------------------------------------------------------------------
# Tests: ConfigEmail — campos por defecto
# ---------------------------------------------------------------------------

class TestConfigEmail:
    def test_campos_requeridos(self):
        cfg = ConfigEmail(servidor="imap.gmail.com", usuario="x@gmail.com", contrasena="pass")
        assert cfg.servidor == "imap.gmail.com"
        assert cfg.usuario == "x@gmail.com"
        assert cfg.contrasena == "pass"

    def test_valores_por_defecto(self):
        cfg = ConfigEmail(servidor="imap.gmail.com", usuario="x@gmail.com", contrasena="pass")
        assert cfg.puerto == 993
        assert cfg.carpeta == "INBOX"
        assert cfg.ssl is True
        assert cfg.marcar_leidos is True

    def test_valores_personalizados(self):
        cfg = ConfigEmail(
            servidor="mail.empresa.com",
            puerto=143,
            usuario="gestor@empresa.com",
            contrasena="s3cr3t",
            carpeta="Facturas",
            ssl=False,
            marcar_leidos=False,
        )
        assert cfg.puerto == 143
        assert cfg.carpeta == "Facturas"
        assert cfg.ssl is False
        assert cfg.marcar_leidos is False


# ---------------------------------------------------------------------------
# Tests: conectar_imap
# ---------------------------------------------------------------------------

class TestConectarImap:
    @patch("sfce.core.ingesta_email.imaplib.IMAP4_SSL")
    def test_conecta_exitosamente_ssl(self, mock_imap_cls):
        mock_conn = MagicMock()
        mock_conn.login.return_value = ("OK", [b"LOGIN OK"])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_imap_cls.return_value = mock_conn

        cfg = ConfigEmail(servidor="imap.gmail.com", usuario="x@gmail.com", contrasena="pass")
        conn = conectar_imap(cfg)

        mock_imap_cls.assert_called_once_with("imap.gmail.com", 993)
        mock_conn.login.assert_called_once_with("x@gmail.com", "pass")
        mock_conn.select.assert_called_once_with("INBOX")
        assert conn is mock_conn

    @patch("sfce.core.ingesta_email.imaplib.IMAP4_SSL")
    def test_carpeta_personalizada(self, mock_imap_cls):
        mock_conn = MagicMock()
        mock_conn.login.return_value = ("OK", [b"OK"])
        mock_conn.select.return_value = ("OK", [b"5"])
        mock_imap_cls.return_value = mock_conn

        cfg = ConfigEmail(
            servidor="imap.gmail.com", usuario="x@gmail.com",
            contrasena="pass", carpeta="Facturas"
        )
        conectar_imap(cfg)
        mock_conn.select.assert_called_once_with("Facturas")

    @patch("sfce.core.ingesta_email.imaplib.IMAP4_SSL")
    def test_lanza_connection_error_si_login_falla(self, mock_imap_cls):
        mock_conn = MagicMock()
        mock_conn.login.side_effect = imaplib.IMAP4.error("Login failed")
        mock_imap_cls.return_value = mock_conn

        cfg = ConfigEmail(servidor="imap.gmail.com", usuario="x@gmail.com", contrasena="bad")
        with pytest.raises(ConnectionError):
            conectar_imap(cfg)

    @patch("sfce.core.ingesta_email.imaplib.IMAP4_SSL")
    def test_lanza_connection_error_si_servidor_inaccesible(self, mock_imap_cls):
        mock_imap_cls.side_effect = OSError("Connection refused")

        cfg = ConfigEmail(servidor="noexiste.invalid", usuario="x@x.com", contrasena="p")
        with pytest.raises(ConnectionError):
            conectar_imap(cfg)


# ---------------------------------------------------------------------------
# Tests: buscar_emails_no_leidos
# ---------------------------------------------------------------------------

class TestBuscarEmailsNoLeidos:
    def test_retorna_lista_uids(self):
        mock_conn = MagicMock()
        mock_conn.uid.return_value = ("OK", [b"1 2 3"])

        uids = buscar_emails_no_leidos(mock_conn)

        mock_conn.uid.assert_called_once_with("SEARCH", "UNSEEN")
        assert uids == ["1", "2", "3"]

    def test_retorna_lista_vacia_si_no_hay_no_leidos(self):
        mock_conn = MagicMock()
        mock_conn.uid.return_value = ("OK", [b""])

        uids = buscar_emails_no_leidos(mock_conn)
        assert uids == []

    def test_retorna_lista_vacia_si_respuesta_nula(self):
        mock_conn = MagicMock()
        mock_conn.uid.return_value = ("OK", [None])

        uids = buscar_emails_no_leidos(mock_conn)
        assert uids == []

    def test_uid_unico(self):
        mock_conn = MagicMock()
        mock_conn.uid.return_value = ("OK", [b"42"])

        uids = buscar_emails_no_leidos(mock_conn)
        assert uids == ["42"]


# ---------------------------------------------------------------------------
# Tests: extraer_adjuntos_pdf
# ---------------------------------------------------------------------------

class TestExtraerAdjuntosPdf:
    def test_extrae_pdf_correctamente(self):
        contenido_pdf = b"%PDF-1.4 fake content"
        raw_bytes = _construir_email_con_pdf(
            remitente="proveedor@empresa.com",
            asunto="Factura enero",
            nombre_pdf="factura_enero.pdf",
            contenido_pdf=contenido_pdf,
        )

        mock_conn = MagicMock()
        mock_conn.uid.return_value = ("OK", [(b"1 (RFC822 {100})", raw_bytes)])

        adjuntos = extraer_adjuntos_pdf(mock_conn, "1")

        assert len(adjuntos) == 1
        adj = adjuntos[0]
        assert adj["nombre"] == "factura_enero.pdf"
        assert adj["contenido"] == contenido_pdf
        assert adj["remitente"] == "proveedor@empresa.com"
        assert adj["asunto"] == "Factura enero"
        assert adj["fecha"] == "Thu, 27 Feb 2026 10:00:00 +0100"

    def test_email_sin_adjuntos_retorna_lista_vacia(self):
        raw_bytes = _construir_email_sin_adjuntos(
            remitente="alguien@empresa.com",
            asunto="Hola",
        )

        mock_conn = MagicMock()
        mock_conn.uid.return_value = ("OK", [(b"2 (RFC822 {50})", raw_bytes)])

        adjuntos = extraer_adjuntos_pdf(mock_conn, "2")
        assert adjuntos == []

    def test_adjunto_no_pdf_ignorado(self):
        raw_bytes = _construir_email_con_imagen(remitente="foto@empresa.com")

        mock_conn = MagicMock()
        mock_conn.uid.return_value = ("OK", [(b"3 (RFC822 {50})", raw_bytes)])

        adjuntos = extraer_adjuntos_pdf(mock_conn, "3")
        assert adjuntos == []

    def test_multiples_pdfs_en_un_email(self):
        msg = email.mime.multipart.MIMEMultipart()
        msg["From"] = "proveedor@empresa.com"
        msg["To"] = "cont@ejemplo.com"
        msg["Subject"] = "Dos facturas"
        msg["Date"] = "Thu, 27 Feb 2026 10:00:00 +0100"

        for nombre, contenido in [("f1.pdf", b"%PDF-f1"), ("f2.pdf", b"%PDF-f2")]:
            parte = email.mime.base.MIMEBase("application", "pdf")
            parte.set_payload(contenido)
            encode_base64(parte)
            parte.add_header("Content-Disposition", "attachment", filename=nombre)
            msg.attach(parte)

        raw_bytes = msg.as_bytes()
        mock_conn = MagicMock()
        mock_conn.uid.return_value = ("OK", [(b"4 (RFC822 {200})", raw_bytes)])

        adjuntos = extraer_adjuntos_pdf(mock_conn, "4")
        assert len(adjuntos) == 2
        nombres = {a["nombre"] for a in adjuntos}
        assert nombres == {"f1.pdf", "f2.pdf"}


# ---------------------------------------------------------------------------
# Tests: enrutar_por_remitente
# ---------------------------------------------------------------------------

class TestEnrutarPorRemitente:
    def test_match_exacto(self):
        mapa = {"proveedor@empresa.com": "empresa-sl", "otro@dominio.es": "otro-cliente"}
        slug = enrutar_por_remitente("proveedor@empresa.com", mapa)
        assert slug == "empresa-sl"

    def test_sin_match_retorna_none(self):
        mapa = {"proveedor@empresa.com": "empresa-sl"}
        slug = enrutar_por_remitente("desconocido@random.com", mapa)
        assert slug is None

    def test_mapa_vacio_retorna_none(self):
        slug = enrutar_por_remitente("x@y.com", {})
        assert slug is None

    def test_multiples_clientes(self):
        mapa = {
            "facturas@iberdrola.es": "cliente-iberdrola",
            "facturas@vodafone.es": "cliente-vodafone",
            "facturas@endesa.es": "cliente-endesa",
        }
        assert enrutar_por_remitente("facturas@vodafone.es", mapa) == "cliente-vodafone"
        assert enrutar_por_remitente("facturas@endesa.es", mapa) == "cliente-endesa"
        assert enrutar_por_remitente("facturas@otros.es", mapa) is None

    def test_case_insensitive(self):
        mapa = {"Proveedor@Empresa.COM": "empresa-sl"}
        slug = enrutar_por_remitente("proveedor@empresa.com", mapa)
        assert slug == "empresa-sl"

    def test_remitente_con_nombre_display(self):
        """Soporta formato 'Nombre Empresa <email@dominio.com>'."""
        mapa = {"proveedor@empresa.com": "empresa-sl"}
        slug = enrutar_por_remitente("Proveedor SA <proveedor@empresa.com>", mapa)
        assert slug == "empresa-sl"


# ---------------------------------------------------------------------------
# Tests: guardar_adjuntos_en_inbox
# ---------------------------------------------------------------------------

class TestGuardarAdjuntosEnInbox:
    def test_guarda_con_slug_conocido(self, tmp_path):
        adjuntos = [
            {"nombre": "factura.pdf", "contenido": b"%PDF-1.4 ok", "remitente": "x@y.com", "asunto": "F1", "fecha": "2026-02-27"},
        ]
        rutas = guardar_adjuntos_en_inbox(adjuntos, str(tmp_path), slug_cliente="empresa-sl")

        assert len(rutas) == 1
        ruta = Path(rutas[0])
        assert ruta.exists()
        assert ruta.parent == tmp_path / "empresa-sl" / "inbox"
        assert ruta.name == "factura.pdf"
        assert ruta.read_bytes() == b"%PDF-1.4 ok"

    def test_guarda_sin_slug_en_sin_clasificar(self, tmp_path):
        adjuntos = [
            {"nombre": "desconocida.pdf", "contenido": b"%PDF desconocida", "remitente": "x@y.com", "asunto": "?", "fecha": "2026-02-27"},
        ]
        rutas = guardar_adjuntos_en_inbox(adjuntos, str(tmp_path), slug_cliente=None)

        assert len(rutas) == 1
        ruta = Path(rutas[0])
        assert ruta.exists()
        assert ruta.parent == tmp_path / "_sin_clasificar"

    def test_crea_directorio_si_no_existe(self, tmp_path):
        adjuntos = [{"nombre": "nuevo.pdf", "contenido": b"x", "remitente": "a@b.com", "asunto": "N", "fecha": ""}]
        guardar_adjuntos_en_inbox(adjuntos, str(tmp_path), slug_cliente="cliente-nuevo")
        assert (tmp_path / "cliente-nuevo" / "inbox").is_dir()

    def test_lista_vacia_retorna_lista_vacia(self, tmp_path):
        rutas = guardar_adjuntos_en_inbox([], str(tmp_path), slug_cliente="cliente")
        assert rutas == []

    def test_multiples_adjuntos(self, tmp_path):
        adjuntos = [
            {"nombre": f"factura_{i}.pdf", "contenido": bytes([i]), "remitente": "x@y.com", "asunto": f"F{i}", "fecha": ""}
            for i in range(3)
        ]
        rutas = guardar_adjuntos_en_inbox(adjuntos, str(tmp_path), slug_cliente="cliente-a")
        assert len(rutas) == 3
        for ruta in rutas:
            assert Path(ruta).exists()

    def test_nombre_duplicado_agrega_sufijo(self, tmp_path):
        """Si ya existe el archivo, debe renombrarse para no sobreescribir."""
        adjuntos = [{"nombre": "factura.pdf", "contenido": b"v1", "remitente": "x@y.com", "asunto": "F", "fecha": ""}]
        guardar_adjuntos_en_inbox(adjuntos, str(tmp_path), slug_cliente="cliente-dup")
        # Segunda vez con mismo nombre
        adjuntos2 = [{"nombre": "factura.pdf", "contenido": b"v2", "remitente": "x@y.com", "asunto": "F", "fecha": ""}]
        rutas2 = guardar_adjuntos_en_inbox(adjuntos2, str(tmp_path), slug_cliente="cliente-dup")
        ruta2 = Path(rutas2[0])
        assert ruta2.name != "factura.pdf"  # debe tener sufijo
        assert ruta2.read_bytes() == b"v2"


# ---------------------------------------------------------------------------
# Tests: procesar_correo — orquestacion completa
# ---------------------------------------------------------------------------

class TestProcesarCorreo:
    def _mock_imap(self, uids: list[str], emails_raw: dict[str, bytes]):
        """Construye un mock de conexion IMAP con respuestas predefinidas."""
        mock_conn = MagicMock()

        # buscar_emails_no_leidos
        uids_bytes = b" ".join(u.encode() for u in uids) if uids else b""
        mock_conn.uid.side_effect = self._uid_side_effect(uids_bytes, emails_raw)
        return mock_conn

    def _uid_side_effect(self, uids_bytes, emails_raw):
        """Simula las llamadas uid(SEARCH) y uid(FETCH) del mock."""
        llamadas = []
        def side_effect(comando, *args):
            if comando == "SEARCH":
                return ("OK", [uids_bytes])
            elif comando == "FETCH":
                uid = args[0]
                raw = emails_raw.get(uid, b"")
                return ("OK", [(b"fetch response", raw)])
            elif comando == "STORE":
                return ("OK", [b"stored"])
            return ("NO", [b"unknown"])
        return side_effect

    def test_flujo_completo_un_email_clasificado(self, tmp_path):
        contenido_pdf = b"%PDF-1.4 factura"
        raw = _construir_email_con_pdf(
            remitente="proveedor@empresa.com",
            asunto="Factura 001",
            nombre_pdf="factura_001.pdf",
            contenido_pdf=contenido_pdf,
        )
        mapa = {"proveedor@empresa.com": "empresa-sl"}

        with patch("sfce.core.ingesta_email.conectar_imap") as mock_conectar:
            mock_conn = self._mock_imap(["1"], {"1": raw})
            mock_conectar.return_value = mock_conn

            cfg = ConfigEmail(servidor="imap.test", usuario="u", contrasena="p")
            resultado = procesar_correo(cfg, mapa, str(tmp_path))

        assert resultado["procesados"] == 1
        assert resultado["clasificados"] == 1
        assert resultado["sin_clasificar"] == 0
        assert resultado["errores"] == 0
        assert len(resultado["detalle"]) == 1

    def test_flujo_email_sin_clasificar(self, tmp_path):
        raw = _construir_email_con_pdf(
            remitente="desconocido@random.com",
            asunto="Algo",
            nombre_pdf="doc.pdf",
            contenido_pdf=b"%PDF unknown",
        )
        mapa = {}  # sin mapeos

        with patch("sfce.core.ingesta_email.conectar_imap") as mock_conectar:
            mock_conn = self._mock_imap(["5"], {"5": raw})
            mock_conectar.return_value = mock_conn

            cfg = ConfigEmail(servidor="imap.test", usuario="u", contrasena="p")
            resultado = procesar_correo(cfg, mapa, str(tmp_path))

        assert resultado["procesados"] == 1
        assert resultado["clasificados"] == 0
        assert resultado["sin_clasificar"] == 1

    def test_flujo_sin_emails_no_leidos(self, tmp_path):
        with patch("sfce.core.ingesta_email.conectar_imap") as mock_conectar:
            mock_conn = MagicMock()
            mock_conn.uid.return_value = ("OK", [b""])
            mock_conectar.return_value = mock_conn

            cfg = ConfigEmail(servidor="imap.test", usuario="u", contrasena="p")
            resultado = procesar_correo(cfg, {}, str(tmp_path))

        assert resultado["procesados"] == 0
        assert resultado["clasificados"] == 0
        assert resultado["sin_clasificar"] == 0
        assert resultado["errores"] == 0

    def test_flujo_email_sin_adjuntos_no_cuenta_como_error(self, tmp_path):
        raw = _construir_email_sin_adjuntos("info@empresa.com", "Aviso sin adjunto")

        with patch("sfce.core.ingesta_email.conectar_imap") as mock_conectar:
            mock_conn = self._mock_imap(["7"], {"7": raw})
            mock_conectar.return_value = mock_conn

            cfg = ConfigEmail(servidor="imap.test", usuario="u", contrasena="p")
            resultado = procesar_correo(cfg, {}, str(tmp_path))

        # Email procesado (leido), pero sin adjuntos → 0 guardados
        assert resultado["errores"] == 0
        assert resultado["sin_clasificar"] == 0

    def test_marcar_leidos_llama_store(self, tmp_path):
        raw = _construir_email_con_pdf(
            remitente="x@y.com", asunto="F", nombre_pdf="f.pdf", contenido_pdf=b"%PDF"
        )

        with patch("sfce.core.ingesta_email.conectar_imap") as mock_conectar:
            mock_conn = self._mock_imap(["9"], {"9": raw})
            mock_conectar.return_value = mock_conn

            cfg = ConfigEmail(servidor="imap.test", usuario="u", contrasena="p", marcar_leidos=True)
            procesar_correo(cfg, {}, str(tmp_path))

        # Debe haberse llamado STORE con \Seen
        store_calls = [c for c in mock_conn.uid.call_args_list if c[0][0] == "STORE"]
        assert len(store_calls) >= 1

    def test_conexion_fallida_lanza_error(self, tmp_path):
        with patch("sfce.core.ingesta_email.conectar_imap") as mock_conectar:
            mock_conectar.side_effect = ConnectionError("No se pudo conectar")

            cfg = ConfigEmail(servidor="imap.test", usuario="u", contrasena="p")
            with pytest.raises(ConnectionError):
                procesar_correo(cfg, {}, str(tmp_path))

    def test_multiples_emails_mixtos(self, tmp_path):
        """Varios emails: algunos clasificados, uno sin adjuntos, uno sin clasificar."""
        raw_clasificado = _construir_email_con_pdf(
            remitente="proveedor@empresa.com", asunto="Factura", nombre_pdf="f.pdf", contenido_pdf=b"%PDF c"
        )
        raw_sin_clasificar = _construir_email_con_pdf(
            remitente="random@web.net", asunto="Spam", nombre_pdf="s.pdf", contenido_pdf=b"%PDF s"
        )
        raw_sin_adj = _construir_email_sin_adjuntos("info@empresa.com", "Info")
        mapa = {"proveedor@empresa.com": "empresa-sl"}

        with patch("sfce.core.ingesta_email.conectar_imap") as mock_conectar:
            mock_conn = self._mock_imap(
                ["10", "11", "12"],
                {"10": raw_clasificado, "11": raw_sin_clasificar, "12": raw_sin_adj},
            )
            mock_conectar.return_value = mock_conn

            cfg = ConfigEmail(servidor="imap.test", usuario="u", contrasena="p")
            resultado = procesar_correo(cfg, mapa, str(tmp_path))

        assert resultado["clasificados"] == 1
        assert resultado["sin_clasificar"] == 1
        assert resultado["errores"] == 0
