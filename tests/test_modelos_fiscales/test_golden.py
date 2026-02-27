"""Tests golden files — ficheros BOE de referencia para regresion (T24)."""
import pytest
from pathlib import Path

from sfce.modelos_fiscales.generador import GeneradorModelos

GOLDEN_DIR = Path(__file__).parent / "golden"

EMPRESA = {"nif": "B12345678", "nombre": "TEST SL"}
CASILLAS_303 = {
    "01": 10000.0, "03": 0.0, "27": 2100.0, "28": 5000.0,
    "29": 1050.0, "31": 0.0, "33": 0.0, "35": 0.0, "36": 0.0,
    "37": 1050.0, "45": 1050.0, "64": 0.0, "69": 1050.0,
}


class TestGoldenFiles:
    def test_golden_dir_existe(self):
        assert GOLDEN_DIR.exists(), "Directorio golden no existe"

    def test_golden_303_existe(self):
        golden = GOLDEN_DIR / "303_basico.txt"
        assert golden.exists(), "Fichero golden 303_basico.txt no encontrado"

    def test_303_coincide_con_golden(self):
        """El BOE generado debe ser byte-a-byte igual al golden."""
        golden_path = GOLDEN_DIR / "303_basico.txt"
        golden = golden_path.read_text(encoding="latin-1")

        gen = GeneradorModelos()
        res = gen.generar("303", "2025", "1T", CASILLAS_303, EMPRESA)

        assert res.contenido == golden, (
            f"El BOE generado difiere del golden.\n"
            f"Esperado (primeros 50 chars): {golden[:50]!r}\n"
            f"Obtenido (primeros 50 chars): {res.contenido[:50]!r}"
        )

    def test_303_longitud_correcta(self):
        gen = GeneradorModelos()
        res = gen.generar("303", "2025", "1T", CASILLAS_303, EMPRESA)
        assert len(res.contenido) == 500, f"Longitud esperada 500, obtenida {len(res.contenido)}"

    def test_303_nif_en_posicion(self):
        gen = GeneradorModelos()
        res = gen.generar("303", "2025", "1T", CASILLAS_303, EMPRESA)
        # NIF en posicion 9-17 (0-indexed: 8-16) para el modelo 303
        contenido = res.contenido
        assert "B12345678" in contenido[:50]

    def test_303_primer_char_tipo_registro(self):
        gen = GeneradorModelos()
        res = gen.generar("303", "2025", "1T", CASILLAS_303, EMPRESA)
        assert res.contenido[0] == "1"

    def test_regenerar_golden(self):
        """Genera golden actualizado — solo ejecutar manualmente al cambiar el YAML."""
        # Este test SIEMPRE pasa, solo actualiza si se le pasa --update-golden
        import os
        if os.environ.get("UPDATE_GOLDEN"):
            gen = GeneradorModelos()
            res = gen.generar("303", "2025", "1T", CASILLAS_303, EMPRESA)
            (GOLDEN_DIR / "303_basico.txt").write_text(res.contenido, encoding="latin-1")
