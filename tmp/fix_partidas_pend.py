"""
Script puntual: añade partidas faltantes a asientos de nomina y amortizacion:
- Nomina: falta 4650000000 (rem_pend)
- Amort: falta 6810000000 (amort_dot)
"""
import requests, json, time
from pathlib import Path

HEADERS = {'Token': 'iOXmrA1Bbn8RDWXLv91L'}
BASE_URL = 'https://contabilidad.lemonfresh-tuc.com/api/3'
IDEMPRESA = 4
ESTADO_PATH = Path('tmp/estado_inyeccion_chiringuito.json')

estado = json.loads(ESTADO_PATH.read_text(encoding='utf-8'))

INGRESOS_ANUALES = {2022: 360_000, 2023: 440_000, 2024: 510_000, 2025: 475_000}
CUOTA_AMORT_ANUAL = 8_000
meses_plenos = list(range(4, 11))

creadas_nom = 0
creadas_amort = 0
errores = 0

for anyo in [2022, 2023, 2024, 2025]:
    masa = INGRESOS_ANUALES[anyo] * 0.28
    cuota_mens = round(CUOTA_AMORT_ANUAL / 12, 2)

    for item in estado['asientos'].get(str(anyo), []):
        idasiento = item.get('id')
        if not idasiento:
            continue
        clave = item['clave']
        # solo nom_ y amort_ (no iva_ ni cierre_)
        if not (clave.startswith('nom_') or clave.startswith('amort_')):
            continue
        mes = int(clave.split('_')[2])

        if clave.startswith('nom_'):
            # Anadir partida rem_pend faltante
            sueldo = round((masa / 7) if mes in meses_plenos else (masa * 0.15 / 5), 2)
            irpf = round(sueldo * 0.15, 2)
            ss_trab = round(sueldo * 0.0635, 2)
            neto = round(sueldo - irpf - ss_trab, 2)
            r = requests.post(BASE_URL + '/partidas', headers=HEADERS, data={
                'idasiento': idasiento, 'idempresa': IDEMPRESA,
                'codsubcuenta': '4650000000', 'debe': 0.0, 'haber': neto,
                'concepto': f'Rem pend {mes:02d}/{anyo}',
            })
            if r.status_code == 200:
                creadas_nom += 1
            else:
                errores += 1
                print(f'ERROR nom {anyo}/{mes}: {r.status_code} {r.text[:100]}')

        elif clave.startswith('amort_'):
            # Anadir partida amort_dot faltante
            r = requests.post(BASE_URL + '/partidas', headers=HEADERS, data={
                'idasiento': idasiento, 'idempresa': IDEMPRESA,
                'codsubcuenta': '6810000000', 'debe': cuota_mens, 'haber': 0.0,
                'concepto': f'Amort inmovilizado {mes:02d}/{anyo}',
            })
            if r.status_code == 200:
                creadas_amort += 1
            else:
                errores += 1
                print(f'ERROR amort {anyo}/{mes}: {r.status_code} {r.text[:100]}')
        time.sleep(0.05)

print(f'Partidas nom rem_pend creadas: {creadas_nom}')
print(f'Partidas amort_dot creadas: {creadas_amort}')
print(f'Errores: {errores}')
