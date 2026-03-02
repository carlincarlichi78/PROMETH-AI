"""Worker Testing — ejecuta sesiones SMOKE, VIGILANCIA, REGRESSION, MANUAL."""
from __future__ import annotations
import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import sessionmaker

BIBLIOTECA_PATH = Path("scripts/motor_campo/biblioteca")

from scripts.motor_campo.executor import Executor
from scripts.motor_campo.validator_v2 import ValidatorV2
from scripts.motor_campo.modelos import ResultadoEjecucion
from scripts.motor_campo.catalogo.fc import obtener_escenarios_fc
from scripts.motor_campo.catalogo.api_seguridad import obtener_escenarios_api
from scripts.motor_campo.catalogo.bancario import obtener_escenarios_bancario
from scripts.motor_campo.catalogo.gate0 import obtener_escenarios_gate0
from scripts.motor_campo.catalogo.dashboard import obtener_escenarios_dashboard
from sfce.db.modelos_testing import TestingSesion, TestingEjecucion, TestingBug

logger = logging.getLogger(__name__)

ESCENARIOS_SMOKE = [
    "fc_basica", "fv_basica", "nc_cliente",
    "gate0_trust_maxima", "gate0_trust_baja", "gate0_duplicado",
    "api_login", "api_login_incorrecto", "api_sin_token",
    "dash_pyg", "dash_balance", "ban_c43_estandar",
]
ESCENARIOS_VIGILANCIA = [
    "fc_basica", "api_login", "dash_pyg", "gate0_trust_maxima", "ban_c43_estandar",
]


def _escenarios_regression() -> list[dict]:
    """Retorna todos los escenarios para regression: smoke + campo + biblioteca."""
    # Smoke siempre incluido (algunos pueden no estar en catalog)
    ids_vistos: set[str] = set()
    todos: list[dict] = []
    for eid in ESCENARIOS_SMOKE:
        todos.append({"id": eid, "tipo": "campo"})
        ids_vistos.add(eid)

    # Resto del catalogo
    for e in _todos_los_escenarios():
        if e.id not in ids_vistos:
            todos.append({"id": e.id, "tipo": "campo"})
            ids_vistos.add(e.id)

    # Biblioteca de caos documental
    manifesto_path = BIBLIOTECA_PATH / "manifesto.json"
    if manifesto_path.exists():
        with open(manifesto_path) as f:
            manifesto = json.load(f)
        for nombre, meta in manifesto.items():
            todos.append({"id": nombre, "tipo": "biblioteca", "meta": meta})

    return todos


def _segundos_hasta_lunes_3am() -> float:
    """Segundos hasta el proximo lunes a las 03:00 UTC."""
    ahora = datetime.now(timezone.utc)
    dias_hasta_lunes = (7 - ahora.weekday()) % 7 or 7
    proximo_lunes = ahora.replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(days=dias_hasta_lunes)
    return max(0.0, (proximo_lunes - ahora).total_seconds())


def _todos_los_escenarios():
    return (
        obtener_escenarios_fc() + obtener_escenarios_api() +
        obtener_escenarios_bancario() + obtener_escenarios_gate0() +
        obtener_escenarios_dashboard()
    )


class WorkerTesting:
    def __init__(self, sfce_api_url: str, fs_api_url: str, fs_token: str,
                 empresa_id: int, codejercicio: str, sesion_factory: Callable):
        self.sfce_api_url = sfce_api_url
        self.fs_api_url = fs_api_url
        self.fs_token = fs_token
        self.empresa_id = empresa_id
        self.codejercicio = codejercicio
        self.sesion_factory = sesion_factory

    def ejecutar_sesion_sincrona(self, modo: str, trigger: str,
                                  escenario_ids: list[str] | None = None,
                                  commit_sha: str | None = None) -> str:
        executor = Executor(self.sfce_api_url, self.fs_api_url, self.fs_token,
                            self.empresa_id, self.codejercicio)

        ids_filtro = escenario_ids or self._ids_por_modo(modo)
        todos = _todos_los_escenarios()
        escenarios = [e for e in todos if e.id in ids_filtro]

        with self.sesion_factory() as db:
            sesion = TestingSesion(modo=modo, trigger=trigger, estado="en_curso",
                                   commit_sha=commit_sha or os.environ.get("COMMIT_SHA"))
            db.add(sesion)
            db.commit()
            sesion_id = sesion.id

        total_ok = total_bugs = total_timeout = 0

        for escenario in escenarios:
            variante = escenario.crear_variante({}, "base", "base")
            resultado = executor.ejecutar(variante)

            if resultado.resultado == "timeout":
                total_timeout += 1
            elif resultado.resultado == "ok":
                total_ok += 1
            else:
                total_bugs += 1

            with self.sesion_factory() as db:
                db.add(TestingEjecucion(
                    sesion_id=sesion_id,
                    escenario_id=resultado.escenario_id,
                    variante_id=resultado.variante_id,
                    canal=resultado.canal,
                    resultado=resultado.resultado,
                    estado_doc_final=resultado.estado_doc_final,
                    tipo_doc_detectado=resultado.tipo_doc_detectado,
                    idasiento=resultado.idasiento,
                    asiento_cuadrado=resultado.asiento_cuadrado,
                    duracion_ms=resultado.duracion_ms,
                ))
                db.commit()

        with self.sesion_factory() as db:
            db.query(TestingSesion).filter_by(id=sesion_id).update({
                "estado": "completado",
                "fin": datetime.now(timezone.utc),
                "total_ok": total_ok,
                "total_bugs": total_bugs,
                "total_timeout": total_timeout,
            })
            db.commit()

        self._enviar_heartbeat(modo, total_bugs)
        return sesion_id

    def _enviar_heartbeat(self, modo: str, bugs: int) -> None:
        """Notifica a Uptime Kuma que la sesion completo OK."""
        import os
        import requests as req
        kuma_base = os.environ.get("UPTIME_KUMA_URL", "")
        slugs = {
            "smoke": os.environ.get("KUMA_SLUG_SMOKE", ""),
            "vigilancia": os.environ.get("KUMA_SLUG_VIGILANCIA", ""),
            "regression": os.environ.get("KUMA_SLUG_REGRESSION", ""),
        }
        slug = slugs.get(modo, "")
        if not kuma_base or not slug:
            return
        if bugs > 0:
            logger.info(f"Heartbeat Kuma omitido: {bugs} bugs en sesion {modo}")
            return
        try:
            req.get(f"{kuma_base}/api/push/{slug}", timeout=5)
            logger.info(f"Heartbeat Kuma enviado: {modo}")
        except Exception as e:
            logger.warning(f"Heartbeat Kuma error: {e}")

    def _ids_por_modo(self, modo: str) -> list[str]:
        if modo == "smoke":
            return ESCENARIOS_SMOKE
        if modo == "vigilancia":
            return ESCENARIOS_VIGILANCIA
        return [e.id for e in _todos_los_escenarios()]


async def loop_worker_testing(sesion_factory: Callable):
    """Background task: vigilancia cada 5min + regression semanal lunes 03:00."""
    logger.info("Worker Testing iniciado")
    espera_regression = _segundos_hasta_lunes_3am()
    logger.info(f"Proxima regression en {espera_regression/3600:.1f}h")

    while True:
        try:
            await asyncio.sleep(300)  # 5 minutos
            sfce_url = os.environ.get("SFCE_API_URL", "http://localhost:8000")
            fs_url = os.environ.get("FS_BASE_URL", "")
            fs_token = os.environ.get("FS_API_TOKEN", "")
            if not fs_url or not fs_token:
                logger.debug("Worker Testing: FS_BASE_URL o FS_API_TOKEN no configurados, skip")
                continue

            worker = WorkerTesting(sfce_url, fs_url, fs_token, 3, "0003", sesion_factory)

            sesion_id = await asyncio.get_event_loop().run_in_executor(
                None, lambda: worker.ejecutar_sesion_sincrona("vigilancia", "schedule")
            )
            logger.info(f"Worker Testing: vigilancia completada — sesion {sesion_id}")

            # Regression: lunes entre 03:00 y 04:00 UTC
            ahora = datetime.now(timezone.utc)
            if ahora.weekday() == 0 and 3 <= ahora.hour < 4:
                logger.info("Iniciando regression semanal...")
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: worker.ejecutar_sesion_sincrona("regression", "schedule")
                )

        except asyncio.CancelledError:
            logger.info("Worker Testing detenido")
            raise
        except Exception as e:
            logger.error(f"Worker Testing error: {e}")
