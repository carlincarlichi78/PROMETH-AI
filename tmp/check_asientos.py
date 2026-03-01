import requests

HEADERS = {'Token': 'iOXmrA1Bbn8RDWXLv91L'}
BASE_URL = 'https://contabilidad.lemonfresh-tuc.com/api/3'

# Buscar asiento amortizacion
offset = 0
asiento_amort = None
while not asiento_amort:
    r = requests.get(BASE_URL + f'/asientos?limit=500&offset={offset}', headers=HEADERS)
    data = r.json()
    if not data:
        break
    for a in data:
        if a.get('idempresa') == 4 and 'Amort' in (a.get('concepto') or ''):
            asiento_amort = a
            break
    if len(data) < 500:
        break
    offset += 500

idasiento = asiento_amort['idasiento']

for cod in ['6810000000', '6811000000', '6812000000', '6813000000']:
    r = requests.post(BASE_URL + '/partidas', headers=HEADERS, data={
        'idasiento': idasiento, 'idempresa': 4,
        'codsubcuenta': cod, 'debe': 100.0, 'haber': 0.0,
        'concepto': f'Test {cod}',
    })
    print(f'POST {cod}: {r.status_code}')
