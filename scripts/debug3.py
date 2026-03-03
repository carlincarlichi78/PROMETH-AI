# -*- coding: utf-8 -*-
import pdfplumber, os, re, unicodedata

CARPETA = "c:/Users/carli/PROYECTOS/CONTABILIDAD/clientes/gerardo-gonzalez-callejon/FACTURAS 2025"

def buscar(nombre):
    n = unicodedata.normalize('NFD', nombre).encode('ascii','ignore').decode().lower()
    for f in os.listdir(CARPETA):
        fn = unicodedata.normalize('NFD', f).encode('ascii','ignore').decode().lower()
        if fn == n:
            return os.path.join(CARPETA, f)
    return None

# Verificar Aquaservice reversal
path = buscar("20250424 Gerardo Aquaservice.pdf")
with pdfplumber.open(path) as pdf:
    texto = ' '.join(p.extract_text() or '' for p in pdf.pages)
    words = []
    for p in pdf.pages:
        words += p.extract_words()

print("=== Aquaservice words (todos) ===")
for w in words:
    print(repr(w['text']))
