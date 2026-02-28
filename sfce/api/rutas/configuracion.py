"""SFCE API — Endpoints de configuracion del sistema."""

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.api.schemas import ConfigAparienciaIn, BackupOut

router = APIRouter(prefix="/api/config", tags=["configuracion"])

# Directorio de backups (relativo al CWD donde corre uvicorn)
BACKUP_DIR = Path("backups")


def _tamano_legible(bytes_: int) -> str:
    """Convierte bytes a representacion legible."""
    for unidad in ["B", "KB", "MB", "GB"]:
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unidad}"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


@router.get("/apariencia")
def obtener_apariencia(
    request: Request,
    user=Depends(obtener_usuario_actual),
):
    """Obtiene la configuracion de apariencia del usuario."""
    # Por ahora retorna valores por defecto — en produccion se persiste por usuario
    return {
        "tema": "system",
        "densidad": "comoda",
        "idioma": "es",
        "formato_fecha": "dd/MM/yyyy",
        "formato_numero": "es-ES",
    }


@router.put("/apariencia")
def actualizar_apariencia(
    body: ConfigAparienciaIn,
    request: Request,
    user=Depends(obtener_usuario_actual),
):
    """Actualiza la configuracion de apariencia del usuario."""
    # En produccion: persistir en tabla configuracion_usuario
    return {"ok": True, "config": body.model_dump()}


@router.get("/backup/listar")
def listar_backups(
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Lista los backups disponibles de la BD."""
    BACKUP_DIR.mkdir(exist_ok=True)
    archivos = sorted(BACKUP_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    resultado = []
    for archivo in archivos[:20]:
        stat = archivo.stat()
        tipo = "automatico" if "auto" in archivo.name else "manual"
        resultado.append({
            "id": archivo.stem,
            "fecha": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "tamano": _tamano_legible(stat.st_size),
            "tipo": tipo,
        })
    return resultado


@router.post("/backup/crear")
def crear_backup(
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Crea un backup manual de la BD SQLite."""
    db_path = os.environ.get("SFCE_DB_PATH", str(Path.cwd() / "sfce.db"))
    if not Path(db_path).exists():
        raise HTTPException(404, "Archivo de BD no encontrado")

    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_id = f"manual_{ts}_{uuid.uuid4().hex[:6]}"
    destino = BACKUP_DIR / f"{backup_id}.db"
    shutil.copy2(db_path, destino)

    return {
        "ok": True,
        "id": backup_id,
        "fecha": datetime.now().isoformat(),
        "tamano": _tamano_legible(destino.stat().st_size),
    }


@router.post("/backup/restaurar/{backup_id}")
def restaurar_backup(
    backup_id: str,
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Restaura un backup de la BD (crea copia de seguridad antes)."""
    archivo = BACKUP_DIR / f"{backup_id}.db"
    if not archivo.exists():
        raise HTTPException(404, f"Backup '{backup_id}' no encontrado")

    db_path = os.environ.get("SFCE_DB_PATH", str(Path.cwd() / "sfce.db"))

    # Copia de seguridad antes de restaurar
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pre_restauracion = BACKUP_DIR / f"pre_restauracion_{ts}.db"
    if Path(db_path).exists():
        shutil.copy2(db_path, pre_restauracion)

    shutil.copy2(archivo, db_path)
    return {"ok": True, "restaurado": backup_id, "pre_backup": pre_restauracion.stem}


@router.get("/integraciones")
def obtener_integraciones(
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Estado de las integraciones externas."""
    return {
        "integraciones": [
            {
                "nombre": "FacturaScripts",
                "tipo": "erp",
                "estado": "conectado" if os.environ.get("FS_API_TOKEN") else "desconectado",
                "url": os.environ.get("FS_BASE_URL", ""),
            },
            {
                "nombre": "Mistral OCR",
                "tipo": "ocr",
                "estado": "conectado" if os.environ.get("MISTRAL_API_KEY") else "desconectado",
            },
            {
                "nombre": "OpenAI GPT",
                "tipo": "ia",
                "estado": "conectado" if os.environ.get("OPENAI_API_KEY") else "desconectado",
            },
            {
                "nombre": "Gemini",
                "tipo": "ia",
                "estado": "conectado" if os.environ.get("GEMINI_API_KEY") else "desconectado",
            },
            {
                "nombre": "Claude (Copiloto)",
                "tipo": "ia",
                "estado": "conectado" if os.environ.get("ANTHROPIC_API_KEY") else "desconectado",
            },
        ]
    }


@router.get("/licencia")
def obtener_licencia(
    request: Request,
    _user=Depends(obtener_usuario_actual),
):
    """Estado de la licencia del SFCE."""
    return {
        "plan": "desarrollo",
        "max_empresas": 10,
        "max_usuarios": 5,
        "modulos": ["contabilidad", "facturacion", "fiscal", "documentos", "economico", "copilot"],
        "valida_hasta": None,
        "version": "2.0.0",
    }
