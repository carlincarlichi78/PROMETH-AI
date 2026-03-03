# -*- coding: utf-8 -*-
import pdfplumber, os, unicodedata, re

CARPETA = "c:/Users/carli/PROYECTOS/CONTABILIDAD/clientes/gerardo-gonzalez-callejon/FACTURAS 2025"

def buscar(nombre):
    for f in os.listdir(CARPETA):
        fn = unicodedata.normalize('NFD', f).encode('ascii','ignore').decode().lower()
        nn = unicodedata.normalize('NFD', nombre).encode('ascii','ignore').decode().lower()
        if fn == nn:
            return os.path.join(CARPETA, f)
    return None

for nombre in [
    "20250430 Gerardo Autonomos.pdf",
    "20250430 Gerardo Seguro.pdf",
    "20250401 Gerardo Internet.pdf",
    "20250402 Gerardo Local.pdf",
    "20250501 Gerardo Alarma.pdf",
]:
    path = buscar(nombre)
    if not path:
        # buscar sin acentos
        for f in os.listdir(CARPETA):
            fn = unicodedata.normalize('NFD', f).encode('ascii','ignore').decode().lower()
            nn = unicodedata.normalize('NFD', nombre).encode('ascii','ignore').decode().lower()
            if fn == nn:
                path = os.path.join(CARPETA, f)
                break
    if not path:
        print(f"NO: {nombre}")
        continue
    with pdfplumber.open(path) as pdf:
        words_all = []
        for page in pdf.pages:
            words_all += page.extract_words()
    nums = [w['text'] for w in words_all if re.match(r'^\d+[.,]\d{2}$', w['text'])]
    print(f"{nombre}: nums={nums[:10]}")
