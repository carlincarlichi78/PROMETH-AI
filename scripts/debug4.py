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

pdfs = [
    "20250909 Gerardo Indemnizacion Eva.pdf",
    "20251029 Gerardo Podologa Marta.pdf",
    "20250930 Gerardo PSICOLOGIA Gloria.pdf",
    "20260104 Gerardo Groupon Comision 104.53 ESTETICA.pdf",
    "20251006 Gerardo DH material medico.pdf",
    "20250606 Gerardo SkinClinic Devolucion -17,97 ESTETICA.pdf",
]

for nombre in pdfs:
    path = buscar(nombre)
    if not path:
        print(f"NO: {nombre}"); continue
    with pdfplumber.open(path) as pdf:
        texto = ' '.join(p.extract_text() or '' for p in pdf.pages)
        words = []
        for p in pdf.pages:
            words += p.extract_words()
    nums = [w['text'] for w in words if re.match(r'^-?[\d.,]+[.,]\d{2}$', w['text'])]
    print(f"=== {nombre} ===")
    print(texto[:300].replace('\n',' '))
    print(f"  NUMS: {nums[:15]}")
    print()
