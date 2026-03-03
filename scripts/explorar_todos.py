# -*- coding: utf-8 -*-
"""Analiza todos los PDFs para ver cuantos extraen texto y cuantos no."""
import pdfplumber, os, unicodedata, re
from collections import Counter

CARPETA = "c:/Users/carli/PROYECTOS/CONTABILIDAD/clientes/gerardo-gonzalez-callejon/FACTURAS 2025"

pdfs = sorted(f for f in os.listdir(CARPETA) if f.lower().endswith('.pdf'))
print(f"Total PDFs: {len(pdfs)}")

sin_texto = []
con_texto = []

for f in pdfs:
    path = os.path.join(CARPETA, f)
    with pdfplumber.open(path) as pdf:
        words_all = []
        texto = ''
        for page in pdf.pages:
            t = page.extract_text() or ''
            texto += t
            words_all += page.extract_words()

    nums = [w['text'] for w in words_all if re.match(r'^\d+[.,]\d{2}$', w['text'])]

    if not texto.strip() and not words_all:
        sin_texto.append(f)
    elif not nums:
        con_texto.append((f, 'sin_nums', texto[:80].replace('\n', ' ')))
    else:
        con_texto.append((f, nums[:5], ''))

print(f"\nSIN TEXTO (probablemente escaneados): {len(sin_texto)}")
for f in sin_texto:
    print(f"  {f}")

sin_nums = [(f, t) for f, tipo, t in con_texto if tipo == 'sin_nums']
print(f"\nCON TEXTO pero SIN NUMEROS XX,XX: {len(sin_nums)}")
for f, t in sin_nums:
    print(f"  {f}: {t[:70]}")
