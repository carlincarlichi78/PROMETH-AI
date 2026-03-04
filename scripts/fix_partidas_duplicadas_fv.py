"""Elimina partidas duplicadas de los asientos FV 91-95 que se añadieron por error."""
import requests

BASE = 'https://fs-uralde.prometh-ai.es/api/3'
TOKEN = 'd0ed76fcc22785424b6c'
headers = {'Token': TOKEN}

# Obtener TODAS las partidas
todas = []
offset = 0
while True:
    r = requests.get(f'{BASE}/partidas', headers=headers, params={'limit': 200, 'offset': offset}, timeout=30)
    lote = r.json()
    if not lote:
        break
    todas.extend(lote)
    if len(lote) < 200:
        break
    offset += 200

print(f'Total partidas: {len(todas)}')

for idasiento in [91, 92, 93, 94, 95]:
    ps = [p for p in todas if str(p.get('idasiento', '')) == str(idasiento)]
    print(f'\nAsiento {idasiento}: {len(ps)} partidas')

    # Contar duplicados por codsubcuenta
    from collections import defaultdict
    grupos = defaultdict(list)
    for p in ps:
        grupos[p.get('codsubcuenta', '')].append(p)

    for cuenta, parts in grupos.items():
        if len(parts) > 1:
            print(f'  DUPLICADO: {cuenta} x{len(parts)}')
            # Eliminar las de más (mantener el primero por idpartida más bajo)
            parts_sorted = sorted(parts, key=lambda x: int(x.get('idpartida', 0)))
            for p_to_del in parts_sorted[1:]:  # mantener el primero, borrar el resto
                idpart = p_to_del.get('idpartida')
                r = requests.delete(f'{BASE}/partidas/{idpart}', headers=headers, timeout=30)
                print(f'    DELETE partidas/{idpart}: {r.status_code}')

    # Eliminar 7050000000 si existe (error mío: FS ya tiene 7000000000)
    if '7050000000' in grupos:
        for p in grupos['7050000000']:
            idpart = p.get('idpartida')
            r = requests.delete(f'{BASE}/partidas/{idpart}', headers=headers, timeout=30)
            print(f'  DELETE 7050000000 idpartida={idpart}: {r.status_code}')

    # Verificar cuadre final
    todas2 = []
    offset2 = 0
    while True:
        r = requests.get(f'{BASE}/partidas', headers=headers, params={'limit': 200, 'offset': offset2}, timeout=30)
        lote = r.json()
        if not lote:
            break
        todas2.extend(lote)
        if len(lote) < 200:
            break
        offset2 += 200

    ps2 = [p for p in todas2 if str(p.get('idasiento', '')) == str(idasiento)]
    debe = sum(float(p.get('debe', 0) or 0) for p in ps2)
    haber = sum(float(p.get('haber', 0) or 0) for p in ps2)
    diff = abs(debe - haber)
    estado = 'CUADRADO' if diff < 0.02 else 'DESCUADRADO'
    print(f'  Final: {len(ps2)} partidas | debe={debe:.2f} haber={haber:.2f} [{estado}]')
    for p in ps2:
        d = float(p.get('debe', 0) or 0)
        h = float(p.get('haber', 0) or 0)
        print(f'    {p.get("codsubcuenta")} debe={d:.2f} haber={h:.2f}')
