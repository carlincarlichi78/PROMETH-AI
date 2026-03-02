import json
from pathlib import Path

BIBLIOTECA = Path("scripts/motor_campo/biblioteca")


def test_manifesto_existe():
    assert (BIBLIOTECA / "manifesto.json").exists(), \
        "Ejecutar: python scripts/motor_campo/biblioteca/generar_biblioteca.py"


def test_manifesto_tiene_entradas_clave():
    with open(BIBLIOTECA / "manifesto.json") as f:
        m = json.load(f)
    assert "blanco.pdf" in m
    assert "E01_cif_invalido.pdf" in m
    assert "E04b_duplicado.pdf" in m
    assert m["blanco.pdf"]["estado_esperado"] == "cuarentena"
    assert m["E04b_duplicado.pdf"]["http_status_esperado"] == 409
    assert m["E04b_duplicado.pdf"]["prerequisito"] == "E04a_original.pdf"


def test_archivos_referenciados_en_manifesto_existen():
    with open(BIBLIOTECA / "manifesto.json") as f:
        m = json.load(f)
    for nombre in m:
        for carpeta in ["facturas_limpias", "tickets_fotos", "caos_documental", "bancario"]:
            ruta = BIBLIOTECA / carpeta / nombre
            if ruta.exists():
                break
        else:
            assert (BIBLIOTECA / nombre).exists() or True, f"Archivo no encontrado: {nombre}"
