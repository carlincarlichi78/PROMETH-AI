"""Setup automatizado de empresa en FacturaScripts."""
import logging
import os
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class ResultadoSetup:
    idempresa_fs: int
    codejercicio: str
    pgc_importado: bool = False


class FsSetup:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self._base = (base_url or os.getenv(
            "FS_API_URL", "https://contabilidad.prometh-ai.es/api/3"
        )).rstrip("/")
        self._token = token or os.getenv("FS_API_TOKEN", "")
        self._headers = {"Token": self._token}

    def _post(self, endpoint: str, data: dict) -> dict:
        url = f"{self._base}/{endpoint}"
        resp = requests.post(url, data=data, headers=self._headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def crear_empresa(self, nombre: str, cif: str, **kwargs) -> ResultadoSetup:
        """Crea una nueva empresa en FacturaScripts."""
        data = {"nombre": nombre, "cifnif": cif, **kwargs}
        resultado = self._post("empresas", data)
        # FS puede responder {"idempresa": X} o {"ok":"...", "data": {"idempresa": X}}
        datos = resultado.get("data", resultado)
        idempresa = datos.get("idempresa") or datos.get("id")
        if not idempresa:
            raise ValueError(f"FS no devolvio idempresa: {resultado}")
        logger.info("Empresa creada en FS con id=%s", idempresa)
        return ResultadoSetup(idempresa_fs=int(idempresa), codejercicio="")

    def crear_ejercicio(self, idempresa: int, anio: int) -> ResultadoSetup:
        """Crea el ejercicio contable para la empresa."""
        codejercicio = f"{idempresa:04d}"
        data = {
            "idempresa": idempresa,
            "codejercicio": codejercicio,
            "nombre": str(anio),
            "fechainicio": f"{anio}-01-01",
            "fechafin": f"{anio}-12-31",
        }
        self._post("ejercicios", data)
        logger.info("Ejercicio %s creado para empresa %s", codejercicio, idempresa)
        return ResultadoSetup(idempresa_fs=idempresa, codejercicio=codejercicio)

    def importar_pgc(self, codejercicio: str, tipo_pgc: str = "general") -> bool:
        """Importa el Plan General Contable para el ejercicio.

        Args:
            codejercicio: Codigo del ejercicio en FacturaScripts.
            tipo_pgc: Tipo de PGC a importar. Opciones: "general" (default),
                      "pymes", "esfl", "cooperativas".
        """
        _PGC_MAP = {
            "general":      "",
            "pymes":        "pymes",
            "esfl":         "esfl",
            "cooperativas": "coops",
        }
        base_app = self._base.replace("/api/3", "")
        sufijo = _PGC_MAP.get(tipo_pgc, "")
        param_plan = f"&plan={sufijo}" if sufijo else ""
        url = f"{base_app}/EditEjercicio?action=importar&code={codejercicio}{param_plan}"
        try:
            resp = requests.get(url, headers=self._headers, timeout=60)
            resp.raise_for_status()
            logger.info("PGC '%s' importado para ejercicio %s", tipo_pgc, codejercicio)
            return True
        except Exception as exc:
            logger.error("Error importando PGC para %s: %s", codejercicio, exc)
            return False

    def setup_completo(self, nombre: str, cif: str, anio: int,
                       tipo_pgc: str = "general", **kwargs) -> ResultadoSetup:
        """Crea empresa + ejercicio + importa PGC en un solo paso."""
        r_emp = self.crear_empresa(nombre, cif, **kwargs)
        r_ej = self.crear_ejercicio(r_emp.idempresa_fs, anio)
        pgc_ok = self.importar_pgc(r_ej.codejercicio, tipo_pgc=tipo_pgc)
        return ResultadoSetup(
            idempresa_fs=r_emp.idempresa_fs,
            codejercicio=r_ej.codejercicio,
            pgc_importado=pgc_ok,
        )
