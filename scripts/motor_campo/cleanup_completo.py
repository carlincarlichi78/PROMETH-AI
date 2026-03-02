from __future__ import annotations
import shutil
import logging
from pathlib import Path
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class CleanupCompleto:
    def __init__(self, fs_base_url: str, fs_token: str, empresa_id: int,
                 sfce_api_url: str, jwt_token: str):
        self.fs_base = fs_base_url
        self.fs_headers = {"Token": fs_token}
        self.empresa_id = empresa_id
        self.sfce_api_url = sfce_api_url
        self.jwt_token = jwt_token

    def limpiar(self, contexto: dict, sesion_bd: Session, docs_base: str) -> None:
        """Limpia 3 capas. Ejecuta siempre, incluso si hay errores parciales."""
        try:
            self.limpiar_facturascripts(contexto.get("facturas_creadas", []))
        except Exception as e:
            logger.warning(f"Cleanup FS error: {e}")
        try:
            self.limpiar_bd(sesion_bd)
        except Exception as e:
            logger.warning(f"Cleanup BD error: {e}")
        try:
            self.limpiar_disco(docs_base)
        except Exception as e:
            logger.warning(f"Cleanup disco error: {e}")

    def limpiar_facturascripts(self, facturas_creadas: list[tuple[str, int]]) -> None:
        for tipo, idf in facturas_creadas:
            endpoint = "facturaclientes" if tipo == "FC" else "facturaproveedores"
            try:
                r = requests.delete(f"{self.fs_base}/{endpoint}/{idf}",
                                    headers=self.fs_headers, timeout=10)
                if r.status_code not in (200, 204, 404):
                    logger.warning(f"Cleanup FS {endpoint}/{idf}: HTTP {r.status_code}")
            except Exception as e:
                logger.warning(f"Cleanup FS {endpoint}/{idf}: {e}")

    def limpiar_bd(self, sesion: Session) -> None:
        """Borra datos de empresa_id en 10 tablas, respetando FK constraints."""
        eid = self.empresa_id
        # Orden FK: primero hijos, luego padres
        sesion.execute(text("DELETE FROM cola_procesamiento WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM documentos WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM asientos WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM facturas WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM pagos WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(
            text("""DELETE FROM movimientos_bancarios WHERE cuenta_bancaria_id IN
                    (SELECT id FROM cuentas_bancarias WHERE empresa_id = :e)"""), {"e": eid}
        )
        sesion.execute(text("DELETE FROM notificaciones_usuario WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM supplier_rules WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM archivos_ingestados WHERE empresa_id = :e"), {"e": eid})
        sesion.execute(text("DELETE FROM centros_coste WHERE empresa_id = :e"), {"e": eid})
        sesion.commit()

    def limpiar_disco(self, docs_base: str) -> None:
        """Borra uploads/{empresa_id}/ del disco."""
        carpeta = Path(docs_base) / "uploads" / str(self.empresa_id)
        if carpeta.exists():
            shutil.rmtree(carpeta)
            logger.info(f"Disco limpio: {carpeta}")
