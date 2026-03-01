import requests
HEADERS = {'Token': 'iOXmrA1Bbn8RDWXLv91L'}
BASE_URL = 'https://contabilidad.lemonfresh-tuc.com/api/3'

total = 0
empresa4 = 0
por_ejercicio = {}
offset = 0
while True:
    r = requests.get(BASE_URL + f'/facturaclientes?limit=500&offset={offset}', headers=HEADERS)
    data = r.json()
    if not data:
        break
    total += len(data)
    for f in data:
        emp = f.get('idempresa', 0)
        ej = f.get('codejercicio', '?')
        if emp == 4:
            empresa4 += 1
            por_ejercicio[ej] = por_ejercicio.get(ej, 0) + 1
    if len(data) < 500:
        break
    offset += 500

print('Total FC en sistema:', total)
print('FC empresa 4:', empresa4)
print('Por ejercicio:', por_ejercicio)
