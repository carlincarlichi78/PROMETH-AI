"""Tests para scripts/watcher.py — File Watcher SFCE."""

import time
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from watchdog.events import FileCreatedEvent, FileMovedEvent, DirCreatedEvent

from scripts.watcher import WatcherSFCE, _HandlerInbox


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def watcher_tmp(tmp_path):
    """Watcher con ruta temporal y debounce corto para tests rapidos."""
    # Crear estructura minima
    inbox = tmp_path / "cliente-test" / "inbox"
    inbox.mkdir(parents=True)
    w = WatcherSFCE(
        ruta_base=str(tmp_path),
        modo="manual",
        intervalo_debounce=0.1,  # 100ms para tests rapidos
    )
    return w


@pytest.fixture
def handler(watcher_tmp):
    """Handler watchdog vinculado al watcher temporal."""
    return _HandlerInbox(watcher_tmp)


# ---------------------------------------------------------------------------
# Tests: _HandlerInbox — filtrado de archivos
# ---------------------------------------------------------------------------
class TestHandlerFiltrado:
    """Verifica que el handler solo reacciona a PDFs validos."""

    def test_acepta_pdf_minuscula(self, handler):
        """Archivos .pdf se aceptan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/factura.pdf") is True

    def test_acepta_pdf_mayuscula(self, handler):
        """Archivos .PDF se aceptan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/Factura.PDF") is True

    def test_acepta_pdf_mixto(self, handler):
        """Archivos .Pdf se aceptan (case-insensitive)."""
        assert handler._es_pdf_valido("/clientes/test/inbox/factura.Pdf") is True

    def test_rechaza_xlsx(self, handler):
        """Archivos no-PDF se rechazan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/datos.xlsx") is False

    def test_rechaza_jpg(self, handler):
        """Imagenes se rechazan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/foto.jpg") is False

    def test_rechaza_txt(self, handler):
        """Archivos de texto se rechazan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/notas.txt") is False

    def test_rechaza_temporal_tilde(self, handler):
        """Archivos temporales ~$ se rechazan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/~$factura.pdf") is False

    def test_rechaza_temporal_tmp(self, handler):
        """Archivos .tmp se rechazan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/.tmp_factura.pdf") is False

    def test_rechaza_temporal_part(self, handler):
        """Archivos .part se rechazan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/.part_descarga.pdf") is False

    def test_rechaza_temporal_crdownload(self, handler):
        """Archivos .crdownload (Chrome) se rechazan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/.crdownload_x.pdf") is False

    def test_rechaza_en_procesado(self, handler):
        """Archivos dentro de procesado/ se rechazan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/procesado/factura.pdf") is False

    def test_rechaza_en_procesado_mayuscula(self, handler):
        """Carpeta Procesado/ (case-insensitive) se rechaza."""
        assert handler._es_pdf_valido("/clientes/test/inbox/Procesado/factura.pdf") is False

    def test_rechaza_directorio(self, handler):
        """Eventos de directorio se ignoran."""
        evento = DirCreatedEvent("/clientes/test/inbox/nueva_carpeta")
        handler.on_created(evento)
        # No deberia registrar nada
        assert handler._watcher.total_pendientes == 0

    def test_sin_extension(self, handler):
        """Archivos sin extension se rechazan."""
        assert handler._es_pdf_valido("/clientes/test/inbox/factura") is False


# ---------------------------------------------------------------------------
# Tests: _HandlerInbox — eventos watchdog
# ---------------------------------------------------------------------------
class TestHandlerEventos:
    """Verifica que on_created y on_moved registran PDFs correctamente."""

    def test_on_created_pdf(self, handler, tmp_path):
        """on_created con PDF valido registra pendiente."""
        ruta = str(tmp_path / "cliente-test" / "inbox" / "factura.pdf")
        evento = FileCreatedEvent(ruta)
        handler.on_created(evento)
        assert handler._watcher.total_pendientes == 1

    def test_on_created_no_pdf(self, handler, tmp_path):
        """on_created con archivo no-PDF no registra."""
        ruta = str(tmp_path / "cliente-test" / "inbox" / "datos.xlsx")
        evento = FileCreatedEvent(ruta)
        handler.on_created(evento)
        assert handler._watcher.total_pendientes == 0

    def test_on_moved_destino_pdf(self, handler, tmp_path):
        """on_moved registra el destino si es PDF."""
        origen = str(tmp_path / "cliente-test" / "inbox" / "factura.pdf.part")
        destino = str(tmp_path / "cliente-test" / "inbox" / "factura.pdf")
        evento = FileMovedEvent(origen, destino)
        handler.on_moved(evento)
        assert handler._watcher.total_pendientes == 1

    def test_on_moved_destino_no_pdf(self, handler, tmp_path):
        """on_moved no registra si destino no es PDF."""
        origen = str(tmp_path / "cliente-test" / "inbox" / "datos.tmp")
        destino = str(tmp_path / "cliente-test" / "inbox" / "datos.xlsx")
        evento = FileMovedEvent(origen, destino)
        handler.on_moved(evento)
        assert handler._watcher.total_pendientes == 0

    def test_on_created_ignora_procesado(self, handler, tmp_path):
        """on_created ignora PDFs en procesado/."""
        procesado = tmp_path / "cliente-test" / "inbox" / "procesado"
        procesado.mkdir(parents=True, exist_ok=True)
        ruta = str(procesado / "vieja.pdf")
        evento = FileCreatedEvent(ruta)
        handler.on_created(evento)
        assert handler._watcher.total_pendientes == 0


# ---------------------------------------------------------------------------
# Tests: WatcherSFCE — debounce
# ---------------------------------------------------------------------------
class TestDebounce:
    """Verifica que el debounce funciona correctamente."""

    def test_pendiente_no_listo_inmediatamente(self, watcher_tmp, tmp_path):
        """Un PDF recien detectado NO aparece en obtener_pendientes."""
        # Debounce = 0.1s, registrar y consultar inmediatamente
        watcher_tmp.intervalo_debounce = 1.0  # 1 segundo para que no pase
        ruta = str(tmp_path / "cliente-test" / "inbox" / "factura.pdf")
        watcher_tmp._registrar_pendiente(ruta)

        listos = watcher_tmp.obtener_pendientes()
        assert listos == []
        assert watcher_tmp.total_pendientes == 1

    def test_pendiente_listo_tras_debounce(self, watcher_tmp, tmp_path):
        """Un PDF aparece en obtener_pendientes tras pasar el debounce."""
        watcher_tmp.intervalo_debounce = 0.05  # 50ms
        ruta = str(tmp_path / "cliente-test" / "inbox" / "factura.pdf")
        watcher_tmp._registrar_pendiente(ruta)

        # Esperar mas que el debounce
        time.sleep(0.1)

        listos = watcher_tmp.obtener_pendientes()
        assert len(listos) == 1
        assert Path(listos[0]).name == "factura.pdf"

    def test_debounce_multiples_archivos(self, watcher_tmp, tmp_path):
        """Multiples PDFs con diferentes tiempos de deteccion."""
        watcher_tmp.intervalo_debounce = 0.1

        ruta1 = str(tmp_path / "cliente-test" / "inbox" / "factura1.pdf")
        watcher_tmp._registrar_pendiente(ruta1)

        time.sleep(0.05)  # 50ms entre detecciones

        ruta2 = str(tmp_path / "cliente-test" / "inbox" / "factura2.pdf")
        watcher_tmp._registrar_pendiente(ruta2)

        # A los 120ms: solo el primero deberia estar listo
        time.sleep(0.07)
        listos = watcher_tmp.obtener_pendientes()
        assert len(listos) == 1
        assert Path(listos[0]).name == "factura1.pdf"

        # A los 200ms: ambos deberian estar listos
        time.sleep(0.1)
        listos = watcher_tmp.obtener_pendientes()
        assert len(listos) == 2

    def test_no_duplica_pendientes(self, watcher_tmp, tmp_path):
        """Registrar el mismo PDF dos veces no lo duplica."""
        ruta = str(tmp_path / "cliente-test" / "inbox" / "factura.pdf")
        watcher_tmp._registrar_pendiente(ruta)
        watcher_tmp._registrar_pendiente(ruta)
        assert watcher_tmp.total_pendientes == 1


# ---------------------------------------------------------------------------
# Tests: WatcherSFCE — marcar_procesado
# ---------------------------------------------------------------------------
class TestMarcarProcesado:
    """Verifica que marcar_procesado elimina PDFs de pendientes."""

    def test_marcar_procesado_elimina(self, watcher_tmp, tmp_path):
        """marcar_procesado quita el PDF de pendientes."""
        watcher_tmp.intervalo_debounce = 0.01
        ruta = str(tmp_path / "cliente-test" / "inbox" / "factura.pdf")
        watcher_tmp._registrar_pendiente(ruta)
        time.sleep(0.05)

        listos = watcher_tmp.obtener_pendientes()
        assert len(listos) == 1

        watcher_tmp.marcar_procesado(listos[0])

        listos2 = watcher_tmp.obtener_pendientes()
        assert listos2 == []
        assert watcher_tmp.total_pendientes == 0

    def test_procesado_no_se_vuelve_a_registrar(self, watcher_tmp, tmp_path):
        """Un PDF ya procesado no se vuelve a registrar como pendiente."""
        ruta = str(tmp_path / "cliente-test" / "inbox" / "factura.pdf")
        watcher_tmp._registrar_pendiente(ruta)
        ruta_normalizada = str(Path(ruta).resolve())
        watcher_tmp.marcar_procesado(ruta_normalizada)

        # Intentar registrar de nuevo
        watcher_tmp._registrar_pendiente(ruta)
        assert watcher_tmp.total_pendientes == 0

    def test_marcar_procesado_inexistente_no_falla(self, watcher_tmp):
        """Marcar un PDF no registrado no lanza error."""
        watcher_tmp.marcar_procesado("/ruta/inexistente.pdf")
        assert watcher_tmp.total_pendientes == 0


# ---------------------------------------------------------------------------
# Tests: WatcherSFCE — ciclo de vida (iniciar/detener)
# ---------------------------------------------------------------------------
class TestCicloVida:
    """Verifica iniciar/detener del watcher."""

    def test_iniciar_activa_observer(self, watcher_tmp):
        """iniciar() pone el watcher activo."""
        watcher_tmp.iniciar()
        try:
            assert watcher_tmp.activo is True
        finally:
            watcher_tmp.detener()

    def test_detener_desactiva_observer(self, watcher_tmp):
        """detener() para el watcher."""
        watcher_tmp.iniciar()
        watcher_tmp.detener()
        assert watcher_tmp.activo is False

    def test_detener_sin_iniciar_no_falla(self, watcher_tmp):
        """detener() sin haber iniciado no lanza error."""
        watcher_tmp.detener()
        assert watcher_tmp.activo is False

    def test_iniciar_doble_no_duplica(self, watcher_tmp):
        """Llamar iniciar() dos veces no crea observers duplicados."""
        watcher_tmp.iniciar()
        observer1 = watcher_tmp._observer
        watcher_tmp.iniciar()  # segunda vez
        observer2 = watcher_tmp._observer
        try:
            assert observer1 is observer2
        finally:
            watcher_tmp.detener()

    def test_repr(self, watcher_tmp):
        """__repr__ muestra info util."""
        r = repr(watcher_tmp)
        assert "WatcherSFCE" in r
        assert "modo=manual" in r

    def test_detecta_pdf_real(self, watcher_tmp, tmp_path):
        """Integracion: escribir un PDF real y verificar deteccion."""
        inbox = tmp_path / "cliente-test" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)

        watcher_tmp.intervalo_debounce = 0.1
        watcher_tmp.iniciar()
        try:
            # Crear archivo PDF en inbox
            pdf = inbox / "test_deteccion.pdf"
            pdf.write_bytes(b"%PDF-1.4 test content")

            # Dar tiempo al observer para detectar
            time.sleep(0.5)

            # Verificar deteccion
            listos = watcher_tmp.obtener_pendientes()
            assert len(listos) >= 1
            nombres = [Path(r).name for r in listos]
            assert "test_deteccion.pdf" in nombres
        finally:
            watcher_tmp.detener()


# ---------------------------------------------------------------------------
# Tests: WatcherSFCE — callback en modo auto
# ---------------------------------------------------------------------------
class TestCallback:
    """Verifica que el callback se invoca correctamente."""

    def test_callback_recibe_lista_pdfs(self, watcher_tmp, tmp_path):
        """El callback recibe la lista de PDFs listos."""
        recibidos = []
        watcher_tmp.callback = lambda pdfs: recibidos.extend(pdfs)
        watcher_tmp.intervalo_debounce = 0.01

        ruta = str(tmp_path / "cliente-test" / "inbox" / "factura.pdf")
        watcher_tmp._registrar_pendiente(ruta)
        time.sleep(0.05)

        listos = watcher_tmp.obtener_pendientes()
        if watcher_tmp.callback:
            watcher_tmp.callback(listos)

        assert len(recibidos) == 1
        assert Path(recibidos[0]).name == "factura.pdf"


# ---------------------------------------------------------------------------
# Tests: thread safety
# ---------------------------------------------------------------------------
class TestThreadSafety:
    """Verifica que operaciones concurrentes no rompen el estado."""

    def test_registros_concurrentes(self, watcher_tmp, tmp_path):
        """Multiples threads registrando PDFs simultaneamente."""
        n_threads = 10
        inbox = tmp_path / "cliente-test" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)

        def registrar(indice):
            ruta = str(inbox / f"factura_{indice}.pdf")
            watcher_tmp._registrar_pendiente(ruta)

        threads = [threading.Thread(target=registrar, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert watcher_tmp.total_pendientes == n_threads

    def test_marcar_procesado_concurrente(self, watcher_tmp, tmp_path):
        """Marcar procesados desde multiples threads."""
        inbox = tmp_path / "cliente-test" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)

        rutas = []
        for i in range(5):
            ruta = str(inbox / f"factura_{i}.pdf")
            watcher_tmp._registrar_pendiente(ruta)
            rutas.append(str(Path(ruta).resolve()))

        def marcar(ruta):
            watcher_tmp.marcar_procesado(ruta)

        threads = [threading.Thread(target=marcar, args=(r,)) for r in rutas]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert watcher_tmp.total_pendientes == 0
