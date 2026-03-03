# -*- coding: utf-8 -*-
import pdfplumber, os

CARPETA = "c:/Users/carli/PROYECTOS/CONTABILIDAD/clientes/gerardo-gonzalez-callejon/FACTURAS 2025"

for nombre in [
    "20250122 Gerardo Clinni ESTETICA.pdf",
    "20250325 Gerardo Facebook.pdf",
    "20250401 Gerardo Internet.pdf",
    "20250909 Gerardo Indemnizacion Eva.pdf",
]:
    path = None
    import unicodedata
    nombre_n = unicodedata.normalize('NFD', nombre).encode('ascii','ignore').decode().lower()
    for f in os.listdir(CARPETA):
        fn = unicodedata.normalize('NFD', f).encode('ascii','ignore').decode().lower()
        if fn == nombre_n:
            path = os.path.join(CARPETA, f)
            break
    if not path:
        print(f"NO: {nombre}")
        continue
    with pdfplumber.open(path) as pdf:
        words = []
        for page in pdf.pages:
            words += page.extract_words()
    print(f"=== {nombre} ===")
    print("Words:", [w['text'] for w in words[:40]])
    print()
