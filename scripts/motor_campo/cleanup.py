import requests
import logging

logger = logging.getLogger(__name__)


class Cleanup:
    def __init__(self, fs_base_url: str, fs_token: str, empresa_id: int):
        self.base = fs_base_url
        self.headers = {"Token": fs_token}
        self.empresa_id = empresa_id
        self._pendientes: list[tuple[str, int]] = []
        self._asientos_pendientes: list[int] = []
        self._docs_bd: list[int] = []

    def registrar_factura(self, tipo: str, idfactura: int):
        self._pendientes.append((tipo, idfactura))

    def registrar_asiento(self, idasiento: int):
        self._asientos_pendientes.append(idasiento)

    def registrar_doc_bd(self, doc_id: int):
        self._docs_bd.append(doc_id)

    def limpiar_escenario(self, sesion_ids: list):
        for tipo, idf in self._pendientes:
            endpoint = "facturaclientes" if tipo == "FC" else "facturaproveedores"
            try:
                r = requests.delete(
                    f"{self.base}/{endpoint}/{idf}",
                    headers=self.headers,
                    timeout=10,
                )
                if r.status_code not in (200, 204, 404):
                    logger.warning(f"Cleanup {endpoint}/{idf}: HTTP {r.status_code}")
            except Exception as e:
                logger.warning(f"Cleanup error {endpoint}/{idf}: {e}")

        for ida in self._asientos_pendientes:
            try:
                r = requests.delete(
                    f"{self.base}/asientos/{ida}",
                    headers=self.headers,
                    timeout=10,
                )
                if r.status_code not in (200, 204, 404):
                    logger.warning(f"Cleanup asiento/{ida}: HTTP {r.status_code}")
            except Exception as e:
                logger.warning(f"Cleanup error asiento/{ida}: {e}")

        self._pendientes.clear()
        self._asientos_pendientes.clear()
        self._docs_bd.clear()
