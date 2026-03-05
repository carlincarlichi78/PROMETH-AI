# tests/test_proveedor_discovery.py
"""Tests para sfce/core/proveedor_discovery.py — TDD RED first."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config_mock():
    config = MagicMock()
    config.empresa = {
        "tipo": "autonomo",
        "regimen_iva": "general",
        "nombre": "CLIENTE TEST SL",
    }
    config.cif = "12345678A"
    return config


@pytest.fixture
def datos_ocr_conocido():
    return {
        "emisor_cif": "B67718361",
        "emisor_nombre": "CoLoS0 SAN 46 S.L.u",
    }


@pytest.fixture
def respuesta_gpt_valida():
    return {
        "nombre_fs": "COLOSO ALGECIRAS AV SLU",
        "aliases": ["COLOSO SAN ISIDRO", "COLOSO"],
        "subcuenta": "6290000000",
        "codimpuesto": "IVA21",
        "regimen": "general",
        "pais": "ESP",
        "divisa": "EUR",
        "nota": "Gasolinera / combustible",
    }


def _crear_client_mock(respuesta: dict):
    """Crea un cliente OpenAI mock que devuelve la respuesta dada."""
    client = MagicMock()
    completion = MagicMock()
    completion.choices[0].message.content = json.dumps(respuesta)
    client.chat.completions.create.return_value = completion
    return client


# ---------------------------------------------------------------------------
# Tests: descubrir_proveedor
# ---------------------------------------------------------------------------

def test_descubrir_proveedor_llama_gpt_con_cif_y_nombre(
    config_mock, datos_ocr_conocido, respuesta_gpt_valida, tmp_path
):
    """descubrir_proveedor llama GPT-4o con el CIF y nombre del emisor."""
    from sfce.core.proveedor_discovery import descubrir_proveedor

    client_mock = _crear_client_mock(respuesta_gpt_valida)
    resultado = descubrir_proveedor(
        datos_ocr_conocido, config_mock, _openai_client=client_mock
    )

    assert client_mock.chat.completions.create.called
    call_kwargs = client_mock.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "gpt-4o"
    prompt = call_kwargs.kwargs["messages"][0]["content"]
    assert "B67718361" in prompt
    assert "CoLoS0 SAN 46" in prompt


def test_descubrir_proveedor_devuelve_campos_correctos(
    config_mock, datos_ocr_conocido, respuesta_gpt_valida, tmp_path
):
    """descubrir_proveedor devuelve dict con campos obligatorios + cif añadido."""
    from sfce.core.proveedor_discovery import descubrir_proveedor

    client_mock = _crear_client_mock(respuesta_gpt_valida)
    resultado = descubrir_proveedor(
        datos_ocr_conocido, config_mock, _openai_client=client_mock
    )

    assert resultado is not None
    assert resultado["nombre_fs"] == "COLOSO ALGECIRAS AV SLU"
    assert resultado["subcuenta"] == "6290000000"
    assert resultado["codimpuesto"] == "IVA21"
    assert resultado["regimen"] == "general"
    assert resultado["cif"] == "B67718361"
    assert resultado["_nombre_ocr"] == "CoLoS0 SAN 46 S.L.u"


def test_descubrir_proveedor_devuelve_none_si_cif_vacio(config_mock):
    """No llama a GPT si el CIF está vacío o ausente."""
    from sfce.core.proveedor_discovery import descubrir_proveedor

    client_mock = MagicMock()
    resultado = descubrir_proveedor(
        {"emisor_cif": "", "emisor_nombre": "Sin CIF"},
        config_mock,
        _openai_client=client_mock,
    )

    assert resultado is None
    assert not client_mock.chat.completions.create.called


def test_descubrir_proveedor_devuelve_none_si_cif_none(config_mock):
    """No llama a GPT si emisor_cif es None."""
    from sfce.core.proveedor_discovery import descubrir_proveedor

    client_mock = MagicMock()
    resultado = descubrir_proveedor(
        {"emisor_cif": None, "emisor_nombre": "Sin CIF"},
        config_mock,
        _openai_client=client_mock,
    )

    assert resultado is None


def test_descubrir_proveedor_devuelve_none_si_gpt_falla(config_mock, datos_ocr_conocido):
    """Devuelve None si GPT lanza excepción."""
    from sfce.core.proveedor_discovery import descubrir_proveedor

    client_mock = MagicMock()
    client_mock.chat.completions.create.side_effect = Exception("API error")

    resultado = descubrir_proveedor(
        datos_ocr_conocido, config_mock, _openai_client=client_mock
    )

    assert resultado is None


def test_descubrir_proveedor_devuelve_none_si_json_invalido(
    config_mock, datos_ocr_conocido
):
    """Devuelve None si GPT devuelve JSON inválido."""
    from sfce.core.proveedor_discovery import descubrir_proveedor

    client_mock = MagicMock()
    completion = MagicMock()
    completion.choices[0].message.content = "esto no es json { malformado"
    client_mock.chat.completions.create.return_value = completion

    resultado = descubrir_proveedor(
        datos_ocr_conocido, config_mock, _openai_client=client_mock
    )

    assert resultado is None


def test_descubrir_proveedor_devuelve_none_si_campos_incompletos(
    config_mock, datos_ocr_conocido
):
    """Devuelve None si GPT devuelve JSON sin campos obligatorios."""
    from sfce.core.proveedor_discovery import descubrir_proveedor

    respuesta_incompleta = {"nombre_fs": "ALGO SL"}  # faltan subcuenta, codimpuesto, regimen
    client_mock = _crear_client_mock(respuesta_incompleta)

    resultado = descubrir_proveedor(
        datos_ocr_conocido, config_mock, _openai_client=client_mock
    )

    assert resultado is None


def test_descubrir_proveedor_acepta_json_con_markdown(
    config_mock, datos_ocr_conocido, respuesta_gpt_valida
):
    """Limpia markdown si GPT envuelve JSON en ```json ... ```."""
    from sfce.core.proveedor_discovery import descubrir_proveedor

    client_mock = MagicMock()
    completion = MagicMock()
    completion.choices[0].message.content = (
        "```json\n" + json.dumps(respuesta_gpt_valida) + "\n```"
    )
    client_mock.chat.completions.create.return_value = completion

    resultado = descubrir_proveedor(
        datos_ocr_conocido, config_mock, _openai_client=client_mock
    )

    assert resultado is not None
    assert resultado["nombre_fs"] == "COLOSO ALGECIRAS AV SLU"


def test_descubrir_proveedor_incluye_categorias_en_prompt(
    config_mock, datos_ocr_conocido, respuesta_gpt_valida, tmp_path
):
    """El prompt incluye categorías de gasto cuando se pasa el YAML."""
    from sfce.core.proveedor_discovery import descubrir_proveedor

    # Crear YAML de categorías mínimo
    ruta_cats = tmp_path / "categorias_gasto.yaml"
    ruta_cats.write_text(
        "version: '2025-01'\ncategorias:\n"
        "  combustible:\n"
        "    descripcion: 'Combustible vehículo'\n"
        "    subcuenta: '6280000000'\n"
        "    iva_codimpuesto: IVA21\n"
        "    keywords_proveedor: ['gasolinera', 'combustible']\n",
        encoding="utf-8",
    )

    client_mock = _crear_client_mock(respuesta_gpt_valida)
    descubrir_proveedor(
        datos_ocr_conocido, config_mock,
        ruta_categorias=ruta_cats,
        _openai_client=client_mock,
    )

    prompt = client_mock.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "combustible" in prompt.lower()
    assert "6280000000" in prompt


# ---------------------------------------------------------------------------
# Tests: cargar_cifs_sugeridos
# ---------------------------------------------------------------------------

def test_cargar_cifs_sugeridos_devuelve_set_vacio_si_no_existe(tmp_path):
    """Devuelve set vacío si el archivo de sugerencias no existe."""
    from sfce.core.proveedor_discovery import cargar_cifs_sugeridos

    ruta = tmp_path / "config_sugerencias.yaml"
    resultado = cargar_cifs_sugeridos(ruta)

    assert resultado == set()


def test_cargar_cifs_sugeridos_extrae_cifs_del_archivo(tmp_path):
    """Lee los CIFs presentes en el archivo de sugerencias."""
    from sfce.core.proveedor_discovery import cargar_cifs_sugeridos

    ruta = tmp_path / "config_sugerencias.yaml"
    ruta.write_text(
        '# === PROVEEDORES SUGERIDOS POR GPT-4o ===\n'
        '# Fuente: "COLOSO" (CIF: B67718361) — factura.pdf\n'
        '# coloso_algeciras:\n'
        '#   cif: "B67718361"\n'
        '#   nombre_fs: "COLOSO ALGECIRAS"\n'
        '\n'
        '# Fuente: "DROPBOX" (CIF: IE9852817) — otro.pdf\n'
        '#   cif: "IE9852817"\n',
        encoding="utf-8",
    )

    resultado = cargar_cifs_sugeridos(ruta)

    assert "B67718361" in resultado
    assert "IE9852817" in resultado


def test_cargar_cifs_sugeridos_normaliza_a_mayusculas(tmp_path):
    """Los CIFs se normalizan a mayúsculas."""
    from sfce.core.proveedor_discovery import cargar_cifs_sugeridos

    ruta = tmp_path / "config_sugerencias.yaml"
    ruta.write_text('#   cif: "b67718361"\n', encoding="utf-8")

    resultado = cargar_cifs_sugeridos(ruta)

    assert "B67718361" in resultado


# ---------------------------------------------------------------------------
# Tests: guardar_sugerencias
# ---------------------------------------------------------------------------

def test_guardar_sugerencias_crea_archivo_comentado(tmp_path, respuesta_gpt_valida):
    """Crea el archivo de sugerencias con bloques YAML comentados."""
    from sfce.core.proveedor_discovery import guardar_sugerencias

    ruta = tmp_path / "config_sugerencias.yaml"
    sugerencia = {**respuesta_gpt_valida, "cif": "B67718361",
                  "_nombre_ocr": "CoLoS0", "_archivo": "factura.pdf"}

    guardar_sugerencias(ruta, [sugerencia])

    contenido = ruta.read_text(encoding="utf-8")
    assert "B67718361" in contenido
    assert "COLOSO ALGECIRAS AV SLU" in contenido
    # Todos los campos deben ser comentarios
    lineas_datos = [l for l in contenido.splitlines()
                    if l.strip() and not l.strip().startswith("#")]
    assert len(lineas_datos) == 0, f"Hay lineas sin comentar: {lineas_datos}"


def test_guardar_sugerencias_no_escribe_si_lista_vacia(tmp_path):
    """No crea el archivo si la lista de sugerencias está vacía."""
    from sfce.core.proveedor_discovery import guardar_sugerencias

    ruta = tmp_path / "config_sugerencias.yaml"
    guardar_sugerencias(ruta, [])

    assert not ruta.exists()


def test_guardar_sugerencias_no_duplica_cifs_existentes(tmp_path, respuesta_gpt_valida):
    """No vuelve a escribir sugerencias para CIFs ya presentes en el archivo."""
    from sfce.core.proveedor_discovery import guardar_sugerencias

    ruta = tmp_path / "config_sugerencias.yaml"
    sugerencia = {**respuesta_gpt_valida, "cif": "B67718361",
                  "_nombre_ocr": "CoLoS0", "_archivo": "factura.pdf"}

    # Primera escritura
    guardar_sugerencias(ruta, [sugerencia])
    contenido_1 = ruta.read_text(encoding="utf-8")
    count_1 = contenido_1.count("B67718361")

    # Segunda escritura con mismo CIF
    guardar_sugerencias(ruta, [sugerencia])
    contenido_2 = ruta.read_text(encoding="utf-8")
    count_2 = contenido_2.count("B67718361")

    assert count_2 == count_1, "El CIF se duplicó en el archivo de sugerencias"


def test_guardar_sugerencias_anade_nuevos_cifs(tmp_path, respuesta_gpt_valida):
    """Añade nuevas sugerencias para CIFs distintos al final del archivo."""
    from sfce.core.proveedor_discovery import guardar_sugerencias

    ruta = tmp_path / "config_sugerencias.yaml"
    sug1 = {**respuesta_gpt_valida, "cif": "B67718361",
             "_nombre_ocr": "COLOSO", "_archivo": "a.pdf"}
    sug2 = {
        "nombre_fs": "OTRO PROVEEDOR SL", "aliases": [],
        "subcuenta": "6290000000", "codimpuesto": "IVA21",
        "regimen": "general", "pais": "ESP", "divisa": "EUR",
        "nota": "otro", "cif": "A12345678",
        "_nombre_ocr": "OTRO", "_archivo": "b.pdf",
    }

    guardar_sugerencias(ruta, [sug1])
    guardar_sugerencias(ruta, [sug2])

    contenido = ruta.read_text(encoding="utf-8")
    assert "B67718361" in contenido
    assert "A12345678" in contenido


def test_guardar_sugerencias_incluye_cabecera_solo_en_archivo_nuevo(tmp_path, respuesta_gpt_valida):
    """La cabecera === PROVEEDORES SUGERIDOS === aparece solo la primera vez."""
    from sfce.core.proveedor_discovery import guardar_sugerencias

    ruta = tmp_path / "config_sugerencias.yaml"
    sug1 = {**respuesta_gpt_valida, "cif": "B67718361",
             "_nombre_ocr": "A", "_archivo": "a.pdf"}
    sug2 = {**respuesta_gpt_valida, "cif": "A12345678",
             "_nombre_ocr": "B", "_archivo": "b.pdf"}

    guardar_sugerencias(ruta, [sug1])
    guardar_sugerencias(ruta, [sug2])

    contenido = ruta.read_text(encoding="utf-8")
    assert contenido.count("PROVEEDORES SUGERIDOS POR GPT-4o") == 1
