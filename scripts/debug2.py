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

muestra = [
    "20250415 Gerardo WakeUp Consultoria ESTETICA.pdf",
    "20250423 Gerardo Vectem Cremas Podologia.pdf",
    "20250630 Gerardo Fresco Cremas.pdf",
    "20250630 Gerardo DRA ESTETICA.pdf",
    "20251001 Gerardo META ESTETICA.pdf",
    "20250115 Gerardo Electrodo ESTETICA.pdf",
]

for nombre in muestra:
    path = buscar(nombre)
    if not path:
        print(f"NO: {nombre}"); continue
    with pdfplumber.open(path) as pdf:
        texto = ' '.join(p.extract_text() or '' for p in pdf.pages)
        words = []
        for p in pdf.pages:
            words += p.extract_words()
    print(f"=== {nombre} ===")
    print(texto[-600:].replace('\n',' '))
    nums = [w['text'] for w in words if re.match(r'^-?[\d€.,]+[.,]\d{2}$', w['text'])]
    print(f"  NUMS: {nums}")
    print()
