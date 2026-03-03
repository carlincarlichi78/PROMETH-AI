# -*- coding: utf-8 -*-
"""Muestra texto de los PDFs sin datos para diagnosticar parsers."""
import pdfplumber, os

CARPETA = "c:/Users/carli/PROYECTOS/CONTABILIDAD/clientes/gerardo-gonzalez-callejon/FACTURAS 2025"

muestra = [
    "20250115 Gerardo Electrodo ESTETICA.pdf",
    "20250228 Gerardo Google.pdf",
    "20250415 Gerardo WakeUp Consultoria ESTETICA.pdf",
    "20250423 Gerardo Vectem Cremas Podologia.pdf",
    "20250424 Gerardo Aquaservice.pdf",
    "20250501 Gerardo Local.pdf",
    "20250514 Gerardo DH Material Medico ESTETICA.pdf",
    "20250606 Gerardo SkinClinic Devolucion -17,97 ESTETICA.pdf",
    "20250630 Gerardo Fresco Cremas.pdf",
    "20250909 Gerardo Indemnizacion Eva.pdf",
    "20251001 Gerardo Letra Local.pdf",
    "20251001 Gerardo META ESTETICA.pdf",
]

import unicodedata

def buscar(nombre):
    n = unicodedata.normalize('NFD', nombre).encode('ascii','ignore').decode().lower()
    for f in os.listdir(CARPETA):
        fn = unicodedata.normalize('NFD', f).encode('ascii','ignore').decode().lower()
        if fn == n:
            return os.path.join(CARPETA, f)
    return None

for nombre in muestra:
    path = buscar(nombre)
    if not path:
        print(f"NO: {nombre}")
        continue
    with pdfplumber.open(path) as pdf:
        texto = ' '.join(p.extract_text() or '' for p in pdf.pages)
        words = []
        for p in pdf.pages:
            words += p.extract_words()
    nums = [w['text'] for w in words if any(c.isdigit() for c in w['text'])]
    print(f"=== {nombre} ===")
    print(texto[:400].replace('\n', ' '))
    print(f"  words numeros: {nums[:15]}")
    print()
