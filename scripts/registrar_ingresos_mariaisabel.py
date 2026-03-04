"""Registra los 5 Ingresos (FV) de Maria Isabel en FS Uralde."""
import json
import requests

BASE = 'https://fs-uralde.prometh-ai.es/api/3'
TOKEN = 'd0ed76fcc22785424b6c'
headers = {'Token': TOKEN}

ingresos = [
    {'stem': 'Ingresos 1T -1',  'fecha': '2025-01-30', 'numero': '1/2025',  'base': 1665.11, 'iva_pct': 21, 'irpf_pct': 15},
    {'stem': 'Ingresos 1T -6',  'fecha': '2025-03-31', 'numero': '6/2025',  'base': 2853.11, 'iva_pct': 21, 'irpf_pct': 15},
    {'stem': 'Ingresos 2T-5',   'fecha': '2025-05-30', 'numero': '11/2025', 'base': 2900.0,  'iva_pct': 21, 'irpf_pct': 15},
    {'stem': 'Ingresos 3T-2',   'fecha': '2025-07-30', 'numero': '18/2025', 'base': 1840.0,  'iva_pct': 21, 'irpf_pct': 15},
    {'stem': 'Ingresos 3T-5',   'fecha': '2025-09-30', 'numero': '21/2025', 'base': 3076.0,  'iva_pct': 21, 'irpf_pct': 15},
]

resultados = []
for doc in ingresos:
    base = doc['base']
    iva_imp = round(base * doc['iva_pct'] / 100, 2)
    irpf_imp = round(base * doc['irpf_pct'] / 100, 2)
    total = round(base + iva_imp - irpf_imp, 2)

    # Paso 1: cabecera
    cab = {
        'idempresa': 7,
        'codejercicio': '0007',
        'fecha': doc['fecha'],
        'codcliente': '1',
        'cifnif': 'B92476787',
        'nombre': 'BLANCO ABOGADOS SL',
        'nombrecliente': 'BLANCO ABOGADOS SL',
        'coddivisa': 'EUR',
        'codserie': 'A',
        'codalmacen': '6',
        'codpago': '6',
        'numero2': doc['numero'],
    }
    resp = requests.post(f'{BASE}/facturaclientes', headers=headers, data=cab, timeout=30)
    if resp.status_code != 200:
        print(f'ERROR {doc["stem"]}: {resp.status_code} - {resp.json().get("error","?")}')
        continue
    idfactura = resp.json().get('data', {}).get('idfactura')
    print(f'OK cab {doc["stem"]}: idfactura={idfactura} ({doc["fecha"]})')

    # Paso 2: linea
    linea = {
        'idfactura': idfactura,
        'descripcion': f'Honorarios profesionales {doc["numero"]}',
        'cantidad': 1,
        'pvpunitario': base,
        'pvpsindto': base,
        'pvptotal': base,
        'codimpuesto': 'IVA21',
        'iva': doc['iva_pct'],
        'irpf': doc['irpf_pct'],
    }
    resp2 = requests.post(f'{BASE}/lineafacturaclientes', headers=headers, data=linea, timeout=30)
    if resp2.status_code != 200:
        print(f'  ERROR linea: {resp2.status_code} - {resp2.json().get("error","?")}')
    else:
        print(f'  Linea OK: base={base} iva={iva_imp} irpf={irpf_imp} total={total}')

    # Paso 3: PUT totales cabecera
    put_data = {
        'neto': base,
        'totaliva': iva_imp,
        'totalirpf': irpf_imp,
        'total': total,
    }
    resp3 = requests.put(f'{BASE}/facturaclientes/{idfactura}', headers=headers, data=put_data, timeout=30)
    if resp3.status_code != 200:
        print(f'  WARN PUT totales: {resp3.status_code}')

    resultados.append({'idfactura': idfactura, 'stem': doc['stem'], 'fecha': doc['fecha'], 'total': total})

print()
print('Resumen:')
for r in resultados:
    print(f'  idfactura={r["idfactura"]} | {r["stem"]} | {r["fecha"]} | total={r["total"]}')
