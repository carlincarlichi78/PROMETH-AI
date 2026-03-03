"""
Pipeline invocable programáticamente desde worker o API.
Complementa scripts/pipeline.py (CLI) sin reemplazarlo.
"""
from __future__ import annotations

import logging
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lock por empresa para evitar procesamiento concurrente
_LOCKS_EMPRESA: dict[int, bool] = {}
_LOCK_GLOBAL = threading.Lock()


def adquirir_lock_empresa(empresa_id: int) -> bool:
    """Retorna True si se adquirió el lock, False si ya estaba bloqueado."""
    with _LOCK_GLOBAL:
        if _LOCKS_EMPRESA.get(empresa_id, False):
            return False
        _LOCKS_EMPRESA[empresa_id] = True
        return True


def liberar_lock_empresa(empresa_id: int) -> None:
    with _LOCK_GLOBAL:
        _LOCKS_EMPRESA[empresa_id] = False


@dataclass
class ResultadoPipeline:
    empresa_id: int
    docs_procesados: int = 0
    docs_cuarentena: int = 0
    docs_error: int = 0
    fases_completadas: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)

    @property
    def exito(self) -> bool:
        return self.docs_procesados > 0 or self.docs_cuarentena > 0


def ejecutar_pipeline_empresa(
    empresa_id: int,
    sesion_factory,
    documentos_ids: Optional[list[int]] = None,
    hints: Optional[dict[int, dict]] = None,
    dry_run: bool = False,
) -> ResultadoPipeline:
    """
    Lanza el pipeline para una empresa desde BD.
    Lee config desde BD (config_desde_bd.py).
    Lee PDFs desde ruta_disco de cada Documento/ColaProcesamiento.

    Args:
        empresa_id: ID de la empresa en BD
        sesion_factory: SQLAlchemy sessionmaker
        documentos_ids: Lista de IDs de Documento a procesar. None = todos los PENDIENTE/APROBADO.
        hints: Dict {doc_id: {tipo_doc, proveedor_cif, ...}} para enriquecer antes del pipeline.
        dry_run: Solo fases 0 y 1 (sin registrar en FacturaScripts).
    """
    resultado = ResultadoPipeline(empresa_id=empresa_id)

    try:
        raw = _lanzar_pipeline_interno(
            empresa_id=empresa_id,
            sesion_factory=sesion_factory,
            documentos_ids=documentos_ids,
            hints=hints or {},
            dry_run=dry_run,
        )
        resultado.docs_procesados = raw.get("procesados", 0)
        resultado.docs_cuarentena = raw.get("cuarentena", 0)
        resultado.docs_error = raw.get("errores", 0)
        resultado.fases_completadas = raw.get("fases_completadas", [])
    except Exception as e:
        logger.error(f"Pipeline empresa {empresa_id} falló: {e}", exc_info=True)
        resultado.docs_error = 1
        resultado.errores.append(str(e))

    return resultado


def _resolver_credenciales_fs(empresa, sesion) -> dict[str, str]:
    """Devuelve env vars FS para el subprocess según gestoría de la empresa.

    Si la gestoría tiene fs_url + fs_token_enc propios, los descifra y
    los devuelve como FS_API_URL / FS_API_TOKEN.
    Si no, devuelve dict vacío (el subprocess usa sus propias variables de entorno).
    """
    try:
        gestoria = getattr(empresa, "gestoria", None)
        if gestoria is None and getattr(empresa, "gestoria_id", None):
            from sfce.db.modelos_auth import Gestoria
            gestoria = sesion.get(Gestoria, empresa.gestoria_id)
        if gestoria and gestoria.fs_url and gestoria.fs_token_enc:
            from sfce.core.cifrado import descifrar
            token = descifrar(gestoria.fs_token_enc)
            logger.info(
                "Empresa %s: usando FS propio de gestoría %s (%s)",
                empresa.id, gestoria.id, gestoria.fs_url,
            )
            return {"FS_API_URL": gestoria.fs_url, "FS_API_TOKEN": token}
    except Exception as exc:
        logger.warning("No se pudieron resolver credenciales FS de gestoría: %s", exc)
    return {}


def _lanzar_pipeline_interno(
    empresa_id: int,
    sesion_factory,
    documentos_ids: Optional[list[int]],
    hints: dict,
    dry_run: bool,
) -> dict:
    """
    Implementación real del pipeline.
    Delega a scripts/pipeline.py vía subprocess.
    En la siguiente fase se integrará directamente con sfce/phases/.
    """
    import os
    from sfce.db.modelos import Empresa

    env_fs: dict[str, str] = {}
    with sesion_factory() as sesion:
        empresa = sesion.get(Empresa, empresa_id)
        if not empresa or not empresa.slug:
            raise ValueError(f"Empresa {empresa_id} no tiene slug configurado")
        slug = empresa.slug
        env_fs = _resolver_credenciales_fs(empresa, sesion)

    cmd = [
        sys.executable, "scripts/pipeline.py",
        "--cliente", slug,
        "--no-interactivo",
    ]
    if dry_run:
        cmd.append("--dry-run")

    # Heredar env del proceso padre y sobrescribir credenciales FS si la gestoría tiene las suyas
    env_subprocess = {**os.environ, **env_fs}

    raiz_proyecto = Path(__file__).parent.parent.parent
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=raiz_proyecto,
        env=env_subprocess,
    )

    if proc.returncode not in (0, 1):
        raise RuntimeError(f"Pipeline terminó con código {proc.returncode}: {proc.stderr[:500]}")

    # Parsear resultado básico del log (provisional hasta refactor completo)
    procesados = proc.stdout.count("REGISTRADO") + proc.stdout.count("registrado")
    cuarentena = proc.stdout.count("cuarentena") + proc.stdout.count("CUARENTENA")

    return {
        "procesados": procesados,
        "cuarentena": cuarentena,
        "errores": 1 if proc.returncode == 1 else 0,
        "fases_completadas": (
            ["intake", "pre_validacion", "registro", "asientos", "correccion", "cruce", "salidas"]
            if proc.returncode == 0 else []
        ),
    }
