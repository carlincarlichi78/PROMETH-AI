"""Tests para sfce/core/pipeline_runner.py."""
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SFCE_JWT_SECRET", "test_secret_key_para_tests_unitarios_longitud")

import sfce.db.modelos_auth  # noqa: F401
from sfce.db.modelos import Base, Empresa, Documento, ColaProcesamiento

PDF_MINIMO = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\n0 1\ntrailer<</Root 1 0 R>>\nstartxref\n9\n%%EOF"


@pytest.fixture
def sf_con_empresa(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine)
    with sf() as s:
        emp = Empresa(
            id=5, nombre="Elena", cif="X1234567L", slug="elena-navarro",
            idempresa_fs=5, forma_juridica="autonomo",
        )
        s.add(emp)
        dir_pdf = tmp_path / "uploads" / "5"
        dir_pdf.mkdir(parents=True)
        ruta = dir_pdf / "test_20260301.pdf"
        ruta.write_bytes(PDF_MINIMO)
        doc = Documento(
            empresa_id=5, tipo_doc="FV", ruta_pdf="test.pdf",
            ruta_disco=str(ruta), estado="pendiente", hash_pdf="abc",
        )
        s.add(doc)
        s.flush()
        cola = ColaProcesamiento(
            empresa_id=5, documento_id=doc.id,
            nombre_archivo="test.pdf", ruta_archivo=str(ruta),
            estado="PENDIENTE", trust_level="ALTA",
        )
        s.add(cola)
        s.commit()
    return sf, tmp_path


def test_resultado_pipeline_runner_tiene_estructura(sf_con_empresa):
    """ResultadoPipeline tiene campos obligatorios."""
    from sfce.core.pipeline_runner import ResultadoPipeline
    r = ResultadoPipeline(empresa_id=5, docs_procesados=2, docs_cuarentena=1, docs_error=0)
    assert r.empresa_id == 5
    assert r.docs_procesados == 2
    assert r.docs_cuarentena == 1
    assert r.exito is True  # al menos 1 procesado


def test_resultado_sin_procesados_no_es_exito():
    from sfce.core.pipeline_runner import ResultadoPipeline
    r = ResultadoPipeline(empresa_id=5, docs_procesados=0, docs_cuarentena=0, docs_error=1)
    assert r.exito is False


def test_ejecutar_pipeline_empresa_retorna_resultado(sf_con_empresa):
    """ejecutar_pipeline_empresa retorna ResultadoPipeline."""
    sf, tmp_path = sf_con_empresa
    from sfce.core.pipeline_runner import ejecutar_pipeline_empresa

    with patch("sfce.core.pipeline_runner._lanzar_pipeline_interno") as mock_pipe:
        mock_pipe.return_value = {"procesados": 1, "cuarentena": 0, "errores": 0, "fases_completadas": []}
        resultado = ejecutar_pipeline_empresa(empresa_id=5, sesion_factory=sf)

    assert resultado.empresa_id == 5
    assert isinstance(resultado.docs_procesados, int)
    assert resultado.docs_error == 0


def test_pipeline_error_no_propagado(sf_con_empresa):
    """Errores del pipeline interno no se propagan — se capturan en ResultadoPipeline."""
    sf, _ = sf_con_empresa
    from sfce.core.pipeline_runner import ejecutar_pipeline_empresa

    with patch("sfce.core.pipeline_runner._lanzar_pipeline_interno", side_effect=RuntimeError("fallo")):
        resultado = ejecutar_pipeline_empresa(empresa_id=5, sesion_factory=sf)

    assert resultado.docs_error == 1
    assert "fallo" in resultado.errores[0]


def test_resolver_credenciales_fs_sin_gestoria(sf_con_empresa):
    """Sin gestoría, _resolver_credenciales_fs devuelve dict vacío."""
    sf, _ = sf_con_empresa
    from sfce.core.pipeline_runner import _resolver_credenciales_fs

    with sf() as sesion:
        empresa = sesion.get(__import__("sfce.db.modelos", fromlist=["Empresa"]).Empresa, 5)
        env = _resolver_credenciales_fs(empresa, sesion)

    assert env == {}


def test_resolver_credenciales_fs_con_gestoria_configurada(sf_con_empresa):
    """Con gestoría que tiene fs_url y fs_token_enc, devuelve FS_API_URL y FS_API_TOKEN."""
    import os
    os.environ.setdefault("SFCE_FERNET_KEY", __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode())

    from sfce.core.cifrado import cifrar
    from sfce.core.pipeline_runner import _resolver_credenciales_fs
    from sfce.db.modelos_auth import Gestoria
    from sfce.db.modelos import Empresa

    sf, _ = sf_con_empresa
    with sf() as sesion:
        g = Gestoria(
            id=10, nombre="Gestoría Test FS", email_contacto="g@test.com",
            fs_url="https://fs.migestoria.es/api/3",
            fs_token_enc=cifrar("token-secreto-gestoria"),
        )
        sesion.add(g)
        emp = sesion.get(Empresa, 5)
        emp.gestoria_id = 10
        sesion.flush()
        sesion.refresh(g)
        env = _resolver_credenciales_fs(emp, sesion)

    assert env["FS_API_URL"] == "https://fs.migestoria.es/api/3"
    assert env["FS_API_TOKEN"] == "token-secreto-gestoria"


def test_lanzar_pipeline_pasa_env_fs_al_subprocess(sf_con_empresa):
    """_lanzar_pipeline_interno pasa FS_API_URL/TOKEN al env del subprocess."""
    import os, subprocess
    os.environ.setdefault("SFCE_FERNET_KEY", __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode())

    from sfce.core.cifrado import cifrar
    from sfce.db.modelos_auth import Gestoria
    from sfce.db.modelos import Empresa

    sf, _ = sf_con_empresa
    with sf() as sesion:
        g = Gestoria(
            id=11, nombre="Gestoría SubP", email_contacto="sp@test.com",
            fs_url="https://fs.subp.es/api/3",
            fs_token_enc=cifrar("tok-subprocess"),
        )
        sesion.add(g)
        emp = sesion.get(Empresa, 5)
        emp.gestoria_id = 11
        sesion.commit()

    env_capturado = {}

    def mock_subprocess_run(cmd, **kwargs):
        env_capturado.update(kwargs.get("env", {}))
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    with patch("sfce.core.pipeline_runner.subprocess.run", side_effect=mock_subprocess_run):
        from sfce.core.pipeline_runner import _lanzar_pipeline_interno
        _lanzar_pipeline_interno(5, sf, None, {}, False)

    assert env_capturado.get("FS_API_URL") == "https://fs.subp.es/api/3"
    assert env_capturado.get("FS_API_TOKEN") == "tok-subprocess"


def test_lock_evita_concurrencia(sf_con_empresa):
    """No se puede lanzar el pipeline para la misma empresa dos veces a la vez."""
    from sfce.core.pipeline_runner import adquirir_lock_empresa, liberar_lock_empresa

    lock = adquirir_lock_empresa(999)
    assert lock is True

    segundo_intento = adquirir_lock_empresa(999)
    assert segundo_intento is False  # ya está bloqueado

    liberar_lock_empresa(999)
    tercer_intento = adquirir_lock_empresa(999)
    assert tercer_intento is True
    liberar_lock_empresa(999)
