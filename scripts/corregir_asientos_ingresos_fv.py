"""Agrega partidas faltantes (705x ingresos + 4730x IRPF) a los asientos FV 91-95 de Maria Isabel."""
import requests

BASE = 'https://fs-uralde.prometh-ai.es/api/3'
TOKEN = 'd0ed76fcc22785424b6c'
headers = {'Token': TOKEN}

# idasiento, base, iva, irpf
asientos = [
    {'idasiento': 91,  'idempresa': 7, 'base': 1665.11, 'iva': 349.67, 'irpf': 249.77, 'fecha': '2025-01-30', 'concepto': 'Factura Cliente FAC0007A1 (1/2025) - BLANCO ABOGADOS'},
    {'idasiento': 92,  'idempresa': 7, 'base': 2853.11, 'iva': 599.15, 'irpf': 427.97, 'fecha': '2025-03-31', 'concepto': 'Factura Cliente FAC0007A2 (6/2025) - BLANCO ABOGADOS'},
    {'idasiento': 93,  'idempresa': 7, 'base': 2900.00, 'iva': 609.00, 'irpf': 435.00, 'fecha': '2025-05-30', 'concepto': 'Factura Cliente FAC0007A3 (11/2025) - BLANCO ABOGADOS'},
    {'idasiento': 94,  'idempresa': 7, 'base': 1840.00, 'iva': 386.40, 'irpf': 276.00, 'fecha': '2025-07-30', 'concepto': 'Factura Cliente FAC0007A4 (18/2025) - BLANCO ABOGADOS'},
    {'idasiento': 95,  'idempresa': 7, 'base': 3076.00, 'iva': 645.96, 'irpf': 461.40, 'fecha': '2025-09-30', 'concepto': 'Factura Cliente FAC0007A5 (21/2025) - BLANCO ABOGADOS'},
]

for a in asientos:
    idasiento = a['idasiento']
    base = round(a['base'], 2)
    iva = round(a['iva'], 2)
    irpf = round(a['irpf'], 2)

    # Verificar partidas actuales
    partidas = requests.get(f'{BASE}/partidas', headers=headers, params={'idasiento': idasiento, 'limit': 20}, timeout=30).json()
    existing = [p for p in partidas if str(p.get('idasiento', '')) == str(idasiento)]
    cuentas_existing = [p.get('codsubcuenta', '') for p in existing]

    debe_total = sum(float(p.get('debe', 0) or 0) for p in existing)
    haber_total = sum(float(p.get('haber', 0) or 0) for p in existing)
    print(f'Asiento {idasiento}: {len(existing)} partidas | debe={debe_total:.2f} haber={haber_total:.2f}')

    # Agregar 7050000000 (ingresos) si no existe
    if not any('705' in c for c in cuentas_existing):
        p705 = {
            'idasiento': idasiento,
            'idempresa': a['idempresa'],
            'fecha': a['fecha'],
            'codsubcuenta': '7050000000',
            'concepto': a['concepto'],
            'haber': base,
            'debe': 0,
        }
        r = requests.post(f'{BASE}/partidas', headers=headers, data=p705, timeout=30)
        if r.status_code == 200:
            print(f'  OK 7050000000 HABER={base}')
        else:
            err = r.json().get('error', '?') if r.headers.get('content-type', '').startswith('application/json') else r.text[:100]
            print(f'  ERROR 7050: {r.status_code} - {err}')

    # Agregar 4730000000 (IRPF retenciones) si no existe
    if not any('473' in c for c in cuentas_existing):
        p473 = {
            'idasiento': idasiento,
            'idempresa': a['idempresa'],
            'fecha': a['fecha'],
            'codsubcuenta': '4730000000',
            'concepto': a['concepto'],
            'debe': irpf,
            'haber': 0,
        }
        r = requests.post(f'{BASE}/partidas', headers=headers, data=p473, timeout=30)
        if r.status_code == 200:
            print(f'  OK 4730000000 DEBE={irpf}')
        else:
            err = r.json().get('error', '?') if r.headers.get('content-type', '').startswith('application/json') else r.text[:100]
            print(f'  ERROR 4730: {r.status_code} - {err}')

    # Verificar cuadre final
    partidas2 = requests.get(f'{BASE}/partidas', headers=headers, params={'idasiento': idasiento, 'limit': 20}, timeout=30).json()
    existing2 = [p for p in partidas2 if str(p.get('idasiento', '')) == str(idasiento)]
    debe2 = sum(float(p.get('debe', 0) or 0) for p in existing2)
    haber2 = sum(float(p.get('haber', 0) or 0) for p in existing2)
    diff = abs(debe2 - haber2)
    estado = 'OK' if diff < 0.02 else 'DESCUADRADO'
    print(f'  Final: {len(existing2)} partidas | debe={debe2:.2f} haber={haber2:.2f} diff={diff:.4f} [{estado}]')
    print()
