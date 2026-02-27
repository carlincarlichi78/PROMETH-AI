"""SFCE File Watcher — Vigila carpetas inbox de clientes para nuevos PDFs.

Tres modos de operacion:
- manual: detecta y reporta por consola (default)
- semi: detecta, pregunta al usuario, procesa si confirma
- auto: detecta y procesa automaticamente via callback

Uso:
    python scripts/watcher.py --modo manual --ruta clientes
    python scripts/watcher.py --modo auto --intervalo 3.0
"""

import argparse
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Logger propio (sin depender de scripts.core para permitir ejecucion standalone)
logger = logging.getLogger("sfce.watcher")


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
EXTENSIONES_PDF = {".pdf"}
PREFIJOS_TEMPORALES = ("~$", ".tmp", ".part", ".crdownload")
CARPETA_PROCESADO = "procesado"

# Evento WebSocket para notificacion
EVENTO_WATCHER_NUEVO_PDF = "watcher_nuevo_pdf"


# ---------------------------------------------------------------------------
# Handler watchdog
# ---------------------------------------------------------------------------
class _HandlerInbox(FileSystemEventHandler):
    """Handler interno que filtra eventos y delega al watcher."""

    def __init__(self, watcher: "WatcherSFCE") -> None:
        super().__init__()
        self._watcher = watcher

    # -- helpers --------------------------------------------------------------

    def _es_pdf_valido(self, ruta: str) -> bool:
        """Comprueba si la ruta es un PDF valido (no temporal, no en procesado/)."""
        p = Path(ruta)

        # Extension PDF (case-insensitive)
        if p.suffix.lower() not in EXTENSIONES_PDF:
            return False

        # Ignorar temporales por prefijo del nombre
        nombre = p.name
        for prefijo in PREFIJOS_TEMPORALES:
            if nombre.startswith(prefijo):
                return False

        # Ignorar si esta dentro de carpeta procesado/
        partes = p.parts
        for parte in partes:
            if parte.lower() == CARPETA_PROCESADO:
                return False

        return True

    # -- eventos watchdog -----------------------------------------------------

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        ruta = event.src_path
        if self._es_pdf_valido(ruta):
            self._watcher._registrar_pendiente(ruta)

    def on_moved(self, event) -> None:
        if event.is_directory:
            return
        # Reaccionar al destino del movimiento
        ruta = event.dest_path
        if self._es_pdf_valido(ruta):
            self._watcher._registrar_pendiente(ruta)


# ---------------------------------------------------------------------------
# WatcherSFCE
# ---------------------------------------------------------------------------
class WatcherSFCE:
    """Vigila carpetas inbox de clientes para nuevos PDFs.

    3 modos:
    - manual: solo detecta y reporta (default)
    - semi: detecta, pregunta, procesa si confirma
    - auto: detecta y procesa automaticamente
    """

    def __init__(
        self,
        ruta_base: str = "clientes",
        modo: str = "manual",
        callback: Optional[Callable] = None,
        intervalo_debounce: float = 5.0,
    ) -> None:
        self.ruta_base = Path(ruta_base)
        self.modo = modo  # manual, semi, auto
        self.callback = callback  # funcion(lista_pdfs) a llamar
        self.intervalo_debounce = intervalo_debounce  # segundos
        self._observer: Optional[Observer] = None
        self._pendientes: dict[str, float] = {}  # ruta -> timestamp deteccion
        self._lock = threading.Lock()
        self._procesados: set[str] = set()

    # -- ciclo de vida --------------------------------------------------------

    def iniciar(self) -> None:
        """Arranca el observer watchdog.

        Vigila ruta_base de forma recursiva para capturar todos los
        subdirectorios inbox/ de clientes.
        """
        if self._observer is not None:
            logger.warning("Watcher ya esta en ejecucion")
            return

        handler = _HandlerInbox(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.ruta_base), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        logger.info(
            "Watcher iniciado — modo=%s, ruta=%s, debounce=%.1fs",
            self.modo,
            self.ruta_base,
            self.intervalo_debounce,
        )

    def detener(self) -> None:
        """Para el observer."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("Watcher detenido")

    @property
    def activo(self) -> bool:
        """True si el observer esta corriendo."""
        return self._observer is not None and self._observer.is_alive()

    # -- gestion de pendientes ------------------------------------------------

    def _registrar_pendiente(self, ruta: str) -> None:
        """Registra un PDF como pendiente con timestamp actual."""
        ruta_normalizada = str(Path(ruta).resolve())
        with self._lock:
            if ruta_normalizada in self._procesados:
                return
            if ruta_normalizada not in self._pendientes:
                self._pendientes[ruta_normalizada] = time.time()
                logger.info("Nuevo PDF detectado: %s", ruta_normalizada)
                self._emitir_evento_ws(ruta_normalizada)

    def obtener_pendientes(self) -> list[str]:
        """Retorna lista de PDFs pendientes cuyo debounce ya se cumplio.

        Solo incluye archivos que llevan al menos `intervalo_debounce`
        segundos desde su deteccion (evita archivos a medio copiar).
        """
        ahora = time.time()
        listos: list[str] = []
        with self._lock:
            for ruta, ts in list(self._pendientes.items()):
                if ruta in self._procesados:
                    continue
                if (ahora - ts) >= self.intervalo_debounce:
                    listos.append(ruta)
        return sorted(listos)

    def marcar_procesado(self, ruta: str) -> None:
        """Marca un PDF como procesado (lo elimina de pendientes)."""
        ruta_normalizada = str(Path(ruta).resolve())
        with self._lock:
            self._procesados.add(ruta_normalizada)
            self._pendientes.pop(ruta_normalizada, None)

    @property
    def total_pendientes(self) -> int:
        """Numero total de PDFs en cola (incluye los que aun estan en debounce)."""
        with self._lock:
            return len(self._pendientes)

    # -- integracion WebSocket (opcional) -------------------------------------

    def _emitir_evento_ws(self, ruta: str) -> None:
        """Emite evento WebSocket si el modulo esta disponible."""
        try:
            import asyncio

            from sfce.api.websocket import EVENTO_WATCHER_NUEVO_PDF, gestor_ws

            # Determinar cliente desde la ruta
            partes = Path(ruta).relative_to(self.ruta_base.resolve()).parts
            cliente = partes[0] if partes else "desconocido"

            datos = {"ruta": ruta, "cliente": cliente}

            # Intentar emitir en loop asyncio existente o crear uno
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    gestor_ws.emitir(EVENTO_WATCHER_NUEVO_PDF, datos)
                )
            except RuntimeError:
                # No hay loop asyncio corriendo, omitir silenciosamente
                pass
        except (ImportError, AttributeError):
            # Modulo WebSocket no disponible, no falla
            pass

    # -- representacion -------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"WatcherSFCE(ruta={self.ruta_base}, modo={self.modo}, "
            f"pendientes={self.total_pendientes}, activo={self.activo})"
        )


# ---------------------------------------------------------------------------
# Bucle principal por modo
# ---------------------------------------------------------------------------
def _bucle_manual(watcher: WatcherSFCE, intervalo_reporte: float = 10.0) -> None:
    """Modo manual: imprime PDFs detectados cada N segundos."""
    logger.info("Modo manual — reportando cada %.0fs. Ctrl+C para salir.", intervalo_reporte)
    try:
        while True:
            time.sleep(intervalo_reporte)
            listos = watcher.obtener_pendientes()
            if listos:
                print(f"\n--- {len(listos)} PDF(s) pendiente(s) ---")
                for ruta in listos:
                    print(f"  {ruta}")
                print()
    except KeyboardInterrupt:
        pass


def _bucle_semi(watcher: WatcherSFCE, intervalo_reporte: float = 10.0) -> None:
    """Modo semi: detecta, pregunta al usuario, procesa si confirma."""
    logger.info("Modo semi — Ctrl+C para salir.")
    try:
        while True:
            time.sleep(intervalo_reporte)
            listos = watcher.obtener_pendientes()
            if not listos:
                continue

            print(f"\n--- {len(listos)} PDF(s) pendiente(s) ---")
            for ruta in listos:
                print(f"  {ruta}")

            respuesta = input("\nProcesar? [s/N]: ").strip().lower()
            if respuesta in ("s", "si", "sí", "y", "yes"):
                if watcher.callback:
                    watcher.callback(listos)
                for ruta in listos:
                    watcher.marcar_procesado(ruta)
                print(f"  {len(listos)} PDF(s) enviados a procesamiento.")
            else:
                print("  Omitido.")
    except KeyboardInterrupt:
        pass


def _bucle_auto(watcher: WatcherSFCE, intervalo_chequeo: float = 5.0) -> None:
    """Modo auto: procesa automaticamente cuando hay PDFs listos."""
    logger.info("Modo auto — procesamiento automatico. Ctrl+C para salir.")
    try:
        while True:
            time.sleep(intervalo_chequeo)
            listos = watcher.obtener_pendientes()
            if not listos:
                continue

            logger.info("Procesando %d PDF(s) automaticamente...", len(listos))
            if watcher.callback:
                watcher.callback(listos)
            for ruta in listos:
                watcher.marcar_procesado(ruta)
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """Punto de entrada CLI del watcher."""
    parser = argparse.ArgumentParser(
        description="SFCE File Watcher — vigila inbox de clientes para nuevos PDFs"
    )
    parser.add_argument(
        "--ruta", default="clientes", help="Ruta base de clientes (default: clientes)"
    )
    parser.add_argument(
        "--modo",
        choices=["manual", "semi", "auto"],
        default="manual",
        help="Modo de operacion (default: manual)",
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=5.0,
        help="Debounce en segundos (default: 5.0)",
    )
    args = parser.parse_args()

    # Configurar logging basico
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Crear watcher
    watcher = WatcherSFCE(
        ruta_base=args.ruta,
        modo=args.modo,
        intervalo_debounce=args.intervalo,
    )

    # Arrancar
    watcher.iniciar()

    try:
        if args.modo == "manual":
            _bucle_manual(watcher)
        elif args.modo == "semi":
            _bucle_semi(watcher)
        elif args.modo == "auto":
            _bucle_auto(watcher)
    finally:
        watcher.detener()


if __name__ == "__main__":
    main()
