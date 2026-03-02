"""ExecutorEmail — envia PDF por SMTP y espera que daemon_correo lo procese."""
import smtplib
import time
import uuid
import logging
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from pathlib import Path
from scripts.motor_campo.modelos import ResultadoEjecucion

logger = logging.getLogger(__name__)
_ESTADOS_FINALES = {"procesado", "cuarentena", "duplicado", "error"}


class ExecutorEmail:
    def __init__(self, sfce_api_url: str, empresa_id: int,
                 smtp_host: str, smtp_port: int,
                 smtp_user: str, smtp_password: str,
                 email_destino: str,
                 sfce_email: str = "admin@sfce.local",
                 sfce_password: str = "admin",
                 poll_timeout_s: int = 600, poll_interval_s: int = 5):
        self.sfce_api_url = sfce_api_url
        self.empresa_id = empresa_id
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_destino = email_destino
        self.sfce_email = sfce_email
        self.sfce_password = sfce_password
        self.poll_timeout_s = poll_timeout_s
        self.poll_interval_s = poll_interval_s
        self._jwt_token = None

    def _login(self):
        r = requests.post(f"{self.sfce_api_url}/api/auth/login",
                          data={"username": self.sfce_email, "password": self.sfce_password},
                          timeout=10)
        r.raise_for_status()
        self._jwt_token = r.json()["access_token"]

    @property
    def _headers(self) -> dict:
        if not self._jwt_token:
            self._login()
        return {"Authorization": f"Bearer {self._jwt_token}"}

    def ejecutar_archivo(self, ruta_archivo: str, escenario_id: str,
                          variante_id: str) -> ResultadoEjecucion:
        inicio = time.monotonic()

        if not self.smtp_host or not self.smtp_user:
            return ResultadoEjecucion(
                escenario_id=escenario_id, variante_id=variante_id,
                canal="email", resultado="error_sistema", duracion_ms=0,
                detalles={"error": "smtp config no disponible"},
            )

        uid = uuid.uuid4().hex[:8]
        asunto = f"SFCE_TEST_{escenario_id}_{uid}"
        ruta = Path(ruta_archivo)

        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = self.email_destino
            msg["Subject"] = asunto
            msg.attach(MIMEText("Documento de testing SFCE. No responder.", "plain"))

            nombre_adjunto = f"{asunto}{ruta.suffix}"
            with open(ruta, "rb") as f:
                adjunto = MIMEApplication(f.read(), Name=nombre_adjunto)
            adjunto["Content-Disposition"] = f'attachment; filename="{nombre_adjunto}"'
            msg.attach(adjunto)

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(self.smtp_user, self.smtp_password)
                smtp.send_message(msg)
            logger.info(f"Email enviado: {asunto}")
        except Exception as e:
            return ResultadoEjecucion(
                escenario_id=escenario_id, variante_id=variante_id,
                canal="email", resultado="error_sistema",
                duracion_ms=int((time.monotonic() - inicio) * 1000),
                detalles={"error": f"SMTP error: {e}"},
            )

        # Poll cola: esperar que daemon_correo descargue el email
        doc_id = None
        deadline_cola = time.monotonic() + 90
        while time.monotonic() < deadline_cola:
            try:
                r = requests.get(
                    f"{self.sfce_api_url}/api/gate0/cola",
                    params={"empresa_id": self.empresa_id, "nombre_archivo_contains": uid},
                    headers=self._headers, timeout=10,
                )
                if r.status_code == 200:
                    items = r.json().get("items", [])
                    if items:
                        doc_id = items[0].get("doc_id")
                        break
            except Exception as e:
                logger.warning(f"Poll cola error: {e}")
            time.sleep(self.poll_interval_s)

        if not doc_id:
            return ResultadoEjecucion(
                escenario_id=escenario_id, variante_id=variante_id,
                canal="email", resultado="timeout",
                duracion_ms=int((time.monotonic() - inicio) * 1000),
                detalles={"error": "Email no descargado por daemon en 90s", "asunto": asunto},
            )

        # Poll estado documento
        deadline = time.monotonic() + self.poll_timeout_s
        while time.monotonic() < deadline:
            try:
                r = requests.get(f"{self.sfce_api_url}/api/documentos/{doc_id}",
                                 headers=self._headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    estado = (data.get("estado") or "").lower()
                    if estado in _ESTADOS_FINALES:
                        return ResultadoEjecucion(
                            escenario_id=escenario_id, variante_id=variante_id,
                            canal="email",
                            resultado="ok" if estado != "error" else "bug_pendiente",
                            duracion_ms=int((time.monotonic() - inicio) * 1000),
                            estado_doc_final=estado,
                            tipo_doc_detectado=data.get("tipo_doc"),
                            idasiento=data.get("idasiento"),
                            detalles={"doc_id": doc_id, "asunto": asunto},
                        )
            except Exception as e:
                logger.warning(f"Poll estado doc_id={doc_id}: {e}")
            time.sleep(self.poll_interval_s)

        return ResultadoEjecucion(
            escenario_id=escenario_id, variante_id=variante_id,
            canal="email", resultado="timeout",
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            detalles={"doc_id": doc_id, "error": "timeout esperando procesado"},
        )
