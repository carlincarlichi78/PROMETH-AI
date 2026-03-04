"""Conector IMAP con descarga incremental por UID.

La interfaz de _conn espera:
  - search(criteria) → list[bytes]       # lista de UID bytes
  - fetch(uids, fmt) → dict[bytes, dict] # {uid_bytes: {b"RFC822": raw_bytes}}

En producción, _conectar() asigna un adaptador sobre imaplib que
implementa esta interfaz. En tests, _conn se sustituye por un MagicMock.
"""
import email
import imaplib
from email.header import decode_header as _decode_header
from typing import Any


class _ImaplibAdapter:
    """Adaptador fino sobre imaplib.IMAP4 con la misma interfaz que los mocks."""

    def __init__(self, conn: imaplib.IMAP4) -> None:
        self._raw = conn

    def search(self, criterio: str) -> list[bytes]:
        _status, data = self._raw.uid("search", None, criterio)
        if not data or not data[0]:
            return []
        return data[0].split()

    def fetch(self, uids: list[bytes], fmt: str = "RFC822") -> dict[bytes, dict]:
        uid_str = b",".join(uids)
        _status, data = self._raw.uid("fetch", uid_str, f"({fmt})")
        resultado: dict[bytes, dict] = {}
        # imaplib devuelve pares (header_bytes, raw_bytes) + b")"
        # Al usar uid("fetch", ...) Gmail devuelve numero de secuencia en el header,
        # no el UID. Mapeamos por posicion usando los UIDs solicitados.
        uid_iter = iter(uids)
        for parte in data:
            if isinstance(parte, tuple):
                raw = parte[1]
                uid = next(uid_iter, None)
                if uid is not None:
                    resultado[uid] = {b"RFC822": raw}
        return resultado

    def logout(self) -> None:
        try:
            self._raw.logout()
        except Exception:
            pass


class ImapServicio:
    """Descarga emails nuevos de un buzón IMAP usando UIDs incrementales."""

    def __init__(
        self,
        servidor: str,
        puerto: int,
        ssl: bool,
        usuario: str,
        contrasena: str,
        carpeta: str = "INBOX",
    ) -> None:
        self._servidor = servidor
        self._puerto = puerto
        self._ssl = ssl
        self._usuario = usuario
        self._contrasena = contrasena
        self._carpeta = carpeta
        self._conn: Any = None  # _ImaplibAdapter o MagicMock en tests

    # Fix #12: timeout para evitar que el worker se quede colgado indefinidamente
    TIMEOUT_SEGUNDOS = 30

    def _conectar(self) -> None:
        if self._ssl:
            raw = imaplib.IMAP4_SSL(self._servidor, self._puerto, timeout=self.TIMEOUT_SEGUNDOS)
        else:
            raw = imaplib.IMAP4(self._servidor, self._puerto, timeout=self.TIMEOUT_SEGUNDOS)
        raw.login(self._usuario, self._contrasena)
        raw.select(self._carpeta)
        self._conn = _ImaplibAdapter(raw)

    def _desconectar(self) -> None:
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def descargar_nuevos(self, ultimo_uid: int = 0) -> list[dict[str, Any]]:
        """Devuelve emails con UID > ultimo_uid."""
        self._conectar()
        try:
            uids_raw = self._conn.search(f"UID {ultimo_uid + 1}:*")
            # imaplib devuelve los UIDs como un único bytes separado por espacios
            # ej: [b'9 15 22'] → hay que split antes de filtrar
            uids: list[bytes] = []
            for u in uids_raw:
                raw_b = u if isinstance(u, bytes) else str(u).encode()
                for token in raw_b.split():
                    if token:
                        uids.append(token)

            # Filtrar UIDs realmente mayores que ultimo_uid
            uids = [u for u in uids if u.isdigit() and int(u) > ultimo_uid]
            if not uids:
                return []

            fetch_result = self._conn.fetch(uids, "RFC822")
            resultados = []
            for uid in uids:
                entrada = fetch_result.get(uid)
                if not entrada:
                    continue
                raw = entrada.get(b"RFC822")
                if raw:
                    resultados.append(self._parsear_email(uid, fetch_result))
            return resultados
        finally:
            self._desconectar()

    def _parsear_email(self, uid: bytes | str, fetch_result: dict) -> dict[str, Any]:
        """Parsea un email crudo extraído de fetch_result.

        Args:
            uid: UID del mensaje (bytes o str).
            fetch_result: dict {uid_bytes: {b"RFC822": raw_bytes}} tal como
                          devuelve _conn.fetch().
        """
        uid_bytes = uid if isinstance(uid, bytes) else uid.encode()
        uid_str = uid.decode() if isinstance(uid, bytes) else uid
        entrada = fetch_result.get(uid_bytes, {})
        raw: bytes = entrada.get(b"RFC822", b"")

        msg = email.message_from_bytes(raw)
        remitente = self._decodificar_header(msg.get("From", ""))
        asunto = self._decodificar_header(msg.get("Subject", ""))
        message_id = msg.get("Message-ID", "")
        fecha = msg.get("Date", "")
        cuerpo_texto = ""
        cuerpo_html = ""
        adjuntos: list[dict] = []

        # Extracción DKIM desde Authentication-Results
        auth_results = msg.get("Authentication-Results", "")
        dkim_verificado = "dkim=pass" in auth_results.lower()

        for parte in msg.walk():
            ct = parte.get_content_type()
            cd = str(parte.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                payload = parte.get_payload(decode=True)
                if payload:
                    cuerpo_texto = payload.decode("utf-8", errors="replace")
            elif ct == "text/html" and "attachment" not in cd:
                payload = parte.get_payload(decode=True)
                if payload:
                    cuerpo_html = payload.decode("utf-8", errors="replace")
            elif "attachment" in cd or parte.get_filename():
                nombre = self._decodificar_header(parte.get_filename() or "adjunto")
                datos = parte.get_payload(decode=True)
                if datos:
                    adjuntos.append({"nombre": nombre, "datos_bytes": datos, "mime_type": ct})

        return {
            "uid": uid_str,
            "message_id": message_id,
            "remitente": remitente,
            "asunto": asunto,
            "fecha": fecha,
            "cuerpo_texto": cuerpo_texto,
            "cuerpo_html": cuerpo_html,
            "adjuntos": adjuntos,
            "dkim_verificado": dkim_verificado,
        }

    @staticmethod
    def _decodificar_header(valor: str) -> str:
        partes = _decode_header(valor)
        resultado = []
        for texto, enc in partes:
            if isinstance(texto, bytes):
                resultado.append(texto.decode(enc or "utf-8", errors="replace"))
            else:
                resultado.append(texto)
        return "".join(resultado)
