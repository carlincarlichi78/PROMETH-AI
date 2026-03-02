"""Tests adicionales procesador_lote — cobertura ramas sin cubrir."""
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from sfce.core.onboarding.procesador_lote import ProcesadorLote, ResultadoLote
from sfce.core.onboarding.clasificador import TipoDocOnboarding
from sfce.core.onboarding.perfil_empresa import PerfilEmpresa


def _zip_con_036_y_libros(tmp_path: Path) -> Path:
    """ZIP con un cliente con 036, libros emitidas/recibidas y saldos."""
    zip_path = tmp_path / "completo.zip"
    with zipfile.ZipFile(str(zip_path), "w") as zf:
        zf.writestr("AUTONOMO_12345678A/036.pdf", b"MODELO 036")
        zf.writestr("AUTONOMO_12345678A/emitidas.csv", "cabecera\n")
        zf.writestr("AUTONOMO_12345678A/recibidas.csv", "cabecera\n")
        zf.writestr("AUTONOMO_12345678A/saldos.csv", "cabecera\n")
    return zip_path


def test_agrupar_por_cliente_con_archivo_externo(tmp_path):
    """Archivo cuya ruta no es relativa a dir_trabajo usa archivo.parent.name."""
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    archivo_externo = tmp_path / "externo.pdf"
    archivo_externo.write_bytes(b"pdf")

    grupos = proc.agrupar_por_cliente([archivo_externo])
    # Cae en el except ValueError → grupo = archivo.parent.name
    assert len(grupos) == 1
    assert list(grupos.values())[0] == [archivo_externo]


def test_procesar_grupo_ignora_archivos_no_file(tmp_path):
    """Un directorio en la lista de archivos se ignora."""
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    # No debe lanzar excepción y devuelve perfil vacío
    perfil = proc._procesar_grupo("grupo", [subdir])
    assert isinstance(perfil, PerfilEmpresa)


def test_procesar_grupo_captura_excepcion_clasificacion(tmp_path):
    """Si clasificar_documento lanza excepción, se loguea y continúa."""
    proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
    archivo = tmp_path / "bad.pdf"
    archivo.write_bytes(b"not a pdf")

    with patch(
        "sfce.core.onboarding.procesador_lote.clasificar_documento",
        side_effect=Exception("clasificación fallida"),
    ):
        perfil = proc._procesar_grupo("grupo", [archivo])
    assert isinstance(perfil, PerfilEmpresa)


def test_procesar_zip_cuenta_aptos_automatico(tmp_path):
    """Perfiles con score>=85 se cuentan como aptos_automatico."""
    from sfce.core.onboarding.perfil_empresa import ResultadoValidacion

    zip_path = _zip_con_036_y_libros(tmp_path)
    perfil_mock = MagicMock(spec=PerfilEmpresa)

    validacion_mock = ResultadoValidacion(
        score=90.0,
        apto_creacion_automatica=True,
        bloqueado=False,
        bloqueos=[],
        advertencias=[],
    )

    with patch.object(ProcesadorLote, "_procesar_grupo", return_value=perfil_mock), \
         patch("sfce.core.onboarding.procesador_lote.Validador") as mock_val_cls:
        mock_val_cls.return_value.validar.return_value = validacion_mock
        proc = ProcesadorLote(directorio_trabajo=tmp_path / "trabajo")
        resultado = proc.procesar_zip(zip_path, lote_id=99)

    assert resultado.aptos_automatico >= 1
    assert resultado.bloqueados == 0


def test_migracion_022_idempotente(tmp_path):
    """Ejecutar migración 022 dos veces no lanza excepción (idempotente)."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import StaticPool
    import sfce.db.modelos  # noqa
    import sfce.db.modelos_auth  # noqa
    from sfce.db.base import Base
    from sfce.db.migraciones.migracion_022_email_enriquecimiento import ejecutar

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    ejecutar(engine)   # primera vez: crea columnas
    ejecutar(engine)   # segunda vez: dispara el except (columnas ya existen)

    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(emails_procesados)")).fetchall()]
    assert "enriquecimiento_pendiente_json" in cols
