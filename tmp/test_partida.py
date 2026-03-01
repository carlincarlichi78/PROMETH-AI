import requests

HEADERS = {'Token': 'iOXmrA1Bbn8RDWXLv91L'}
BASE_URL = 'https://contabilidad.lemonfresh-tuc.com/api/3'

# Obtener asientos con paginacion para encontrar empresa 4
offset = 0
asiento_emp4 = None
while not asiento_emp4:
    r = requests.get(BASE_URL + f'/asientos?limit=500&offset={offset}', headers=HEADERS)
    data = r.json()
    if not data:
        break
    for a in data:
        if a.get('idempresa') == 4:
            asiento_emp4 = a
            break
    if len(data) < 500:
        break
    offset += 500

print('Asiento empresa 4:', asiento_emp4)

if asiento_emp4:
    idasiento = asiento_emp4['idasiento']
    # Comprobar si la subcuenta existe en empresa 4
    r2 = requests.get(BASE_URL + '/subcuentas?limit=10&codsubcuenta=6400000000', headers=HEADERS)
    scs = r2.json()
    for s in scs:
        if s.get('idempresa') == 4:
            print('Subcuenta 640 existe:', s)
            break
    else:
        print('Subcuenta 6400000000 NO encontrada en empresa 4')

    # Probar POST partida
    data = {
        'idasiento': idasiento,
        'idempresa': 4,
        'codsubcuenta': '6400000000',
        'debe': 1000.0,
        'haber': 0.0,
        'concepto': 'Test nomina',
    }
    r3 = requests.post(BASE_URL + '/partidas', headers=HEADERS, data=data)
    print('Status POST partida:', r3.status_code)
    print('Response:', r3.text[:500])
