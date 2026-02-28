# Inyección Datos Chiringuito Sol y Arena — Plan de Implementación

> **Para Claude:** Usar superpowers:executing-plans para ejecutar este plan tarea a tarea.

**Goal:** Poblar empresa 4 (CHIRINGUITO SOL Y ARENA S.L.) con ~2000 facturas + asientos realistas para ejercicios 2022, 2023, 2024 (cerrados) y 2025 (abierto hasta 31/12), para testing completo del dashboard SFCE.

**Architecture:** Un script Python autocontenido `scripts/inyectar_datos_chiringuito.py` que llama directamente a la API FS. Fase previa via browser para crear ejercicios e importar PGC. El script es idempotente (JSON de estado), soporta `--fase` y `--dry-run`.

**Tech Stack:** Python + requests (sin deps extra), API FS REST form-encoded, Claude in Chrome para browser steps.

---

## Datos de negocio (referencia para el generador)

### Distribución mensual FC (actividad estacional)
| Mes | % anual | Mes | % anual |
|-----|---------|-----|---------|
| Ene | 1% | Jul | 22% |
| Feb | 1% | Ago | 25% |
| Mar | 2% | Sep | 12% |
| Abr | 8% | Oct | 5% |
| May | 10% | Nov | 2% |
| Jun | 10% | Dic | 2% |

### Ingresos por ejercicio
| Año | Ingresos brutos | FC (300/año) | Ticket medio |
|-----|----------------|--------------|--------------|
| 2022 | 360.000 € | 300 | 1.200 € |
| 2023 | 440.000 € | 300 | 1.467 € |
| 2024 | 510.000 € | 300 | 1.700 € |
| 2025 | 475.000 € | 300 | 1.583 € |

### Gastos por proveedor (FV ~200/año)
| Proveedor | Tipo | Frecuencia | % s/ingresos |
|-----------|------|-----------|--------------|
| Makro | Compras alimentación+bebidas | 3x/sem en temporada | 32% |
| Ayto Marbella | Canon concesión | 1 anual | 4% |
| Renting Mobiliario | Cuota mensual | 12/año | 3% |
| Grupo Gastro | Management fee trimestral | 4/año | 2.5% |
| Endesa (suministros) | Electricidad mensual | 12/año | 2% |

### Asientos directos (no facturas)
- **NOM**: 12/año — sueldos fijos discontinuos (alta en abril, baja en octubre)
- **Amortizaciones**: 12/año — equipo de cocina, mobiliario, instalaciones
- **IVA trimestral**: 4/año — liquidación 303 (resultado IVA rep - IVA sop)
- **Cierre ejercicio**: 1/año (solo 2022, 2023, 2024) — regularización 6xx/7xx → 129

### Codejercicio para nuevos ejercicios
- 2022 → `C422`
- 2023 → `C423`
- 2024 → `C424`
- 2025 → `0004` (ya existe)

---

## Task 1: Crear ejercicios + importar PGC (browser)

**Files:** ninguno (browser automation)

**Contexto:** Empresa 4 solo tiene ejercicio `0004` (2025) y sin subcuentas (PGC no importado). Hay que crear 3 ejercicios históricos e importar PGC en todos (incluido 0004).

**URL base FS:** `https://contabilidad.lemonfresh-tuc.com`

**Step 1: Abrir FacturaScripts en el navegador**

Navegar a `https://contabilidad.lemonfresh-tuc.com/admin/` (o el panel de empresa).
Seleccionar empresa 4 (CHIRINGUITO SOL Y ARENA).

**Step 2: Crear ejercicio 2022**

Ir a: `Contabilidad → Ejercicios → Nuevo`
Campos:
- Nombre: `2022`
- Código: `C422`
- Fecha inicio: `01-01-2022`
- Fecha fin: `31-12-2022`
- Empresa: 4

**Step 3: Importar PGC para C422**

Ir a: `EditEjercicio?code=C422` → botón "Importar plan contable" → Aceptar (sin archivo = PGC general español 2007).
Verificar que aparecen cuentas (debería crear ~800 cuentas + ~721 subcuentas).

**Step 4: Repetir para 2023 (C423) y 2024 (C424)**

Mismo proceso. Cada importación tarda ~30 segundos.

**Step 5: Importar PGC para 0004 (2025)**

También necesita PGC (actualmente vacío).

**Step 6: Verificar via API**

```bash
python -c "
import requests
H = {'Token': 'iOXmrA1Bbn8RDWXLv91L'}
API = 'https://contabilidad.lemonfresh-tuc.com/api/3'
for cod in ['C422','C423','C424','0004']:
    r = requests.get(f'{API}/subcuentas', headers=H, params={'codejercicio':cod,'limit':1})
    data = r.json()
    print(f'{cod}: {len(data)} subcuentas (muestra OK si >0)')
"
```
Esperado: cada ejercicio devuelve >=1 subcuenta.

**Step 7: Commit**
```bash
git add -A
git commit -m "chore: ejercicios 2022/2023/2024 + PGC importado empresa 4"
```

---

## Task 2: Script scaffold + estado

**Files:**
- Crear: `scripts/inyectar_datos_chiringuito.py`

**Step 1: Crear estructura base del script**

```python
#!/usr/bin/env python3
"""
Inyeccion de datos de prueba en empresa 4 (CHIRINGUITO SOL Y ARENA S.L.)
para testing del dashboard SFCE.

Genera ~2000 facturas + asientos para ejercicios 2022-2025.

Uso:
    python scripts/inyectar_datos_chiringuito.py --fase todo
    python scripts/inyectar_datos_chiringuito.py --fase fc --anyo 2023
    python scripts/inyectar_datos_chiringuito.py --dry-run
    python scripts/inyectar_datos_chiringuito.py --limpiar-estado
"""
import argparse
import json
import os
import random
import time
from datetime import date, timedelta
from pathlib import Path

import requests

# --- Configuracion ---
API_BASE = "https://contabilidad.lemonfresh-tuc.com/api/3"
TOKEN = os.getenv("FS_API_TOKEN", "iOXmrA1Bbn8RDWXLv91L")
HEADERS = {"Token": TOKEN}
IDEMPRESA = 4
DELAY = 0.25  # segundos entre llamadas API

EJERCICIOS = {
    2022: "C422",
    2023: "C423",
    2024: "C424",
    2025: "0004",
}

ESTADO_PATH = Path(__file__).parent.parent / "tmp" / "estado_inyeccion_chiringuito.json"
ESTADO_PATH.parent.mkdir(exist_ok=True)

# --- Helpers API ---
def api_get(endpoint, params=None):
    r = requests.get(f"{API_BASE}/{endpoint}", headers=HEADERS,
                     params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()

def api_post_form(endpoint, data):
    r = requests.post(f"{API_BASE}/{endpoint}", headers=HEADERS,
                      data=data, timeout=30)
    r.raise_for_status()
    return r.json()

def api_put_form(endpoint, data):
    r = requests.put(f"{API_BASE}/{endpoint}", headers=HEADERS,
                     data=data, timeout=30)
    r.raise_for_status()
    return r.json()

# --- Estado ---
def cargar_estado():
    if ESTADO_PATH.exists():
        return json.loads(ESTADO_PATH.read_text())
    return {"fc": {}, "fv": {}, "asientos": {}, "entidades": {}}

def guardar_estado(estado):
    ESTADO_PATH.write_text(json.dumps(estado, indent=2))

# --- Argparse ---
def main():
    parser = argparse.ArgumentParser(description="Inyeccion datos chiringuito")
    parser.add_argument("--fase", choices=["entidades","fc","fv","asientos","cierre","todo"],
                        default="todo")
    parser.add_argument("--anyo", type=int, choices=[2022,2023,2024,2025], default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limpiar-estado", action="store_true")
    args = parser.parse_args()

    if args.limpiar_estado:
        ESTADO_PATH.unlink(missing_ok=True)
        print("Estado limpiado.")
        return

    estado = cargar_estado()
    anyos = [args.anyo] if args.anyo else list(EJERCICIOS.keys())

    if args.fase in ("entidades", "todo"):
        asegurar_entidades(estado, dry_run=args.dry_run)

    if args.fase in ("fc", "todo"):
        for anyo in anyos:
            generar_fc(anyo, estado, dry_run=args.dry_run)

    if args.fase in ("fv", "todo"):
        for anyo in anyos:
            generar_fv(anyo, estado, dry_run=args.dry_run)

    if args.fase in ("asientos", "todo"):
        for anyo in anyos:
            generar_asientos_directos(anyo, estado, dry_run=args.dry_run)

    if args.fase in ("cierre", "todo"):
        for anyo in [2022, 2023, 2024]:
            if args.anyo is None or args.anyo == anyo:
                cerrar_ejercicio(anyo, estado, dry_run=args.dry_run)

    guardar_estado(estado)
    print("\n=== RESUMEN ===")
    print(f"FC creadas: {sum(len(v) for v in estado['fc'].values())}")
    print(f"FV creadas: {sum(len(v) for v in estado['fv'].values())}")
    print(f"Asientos creados: {sum(len(v) for v in estado['asientos'].values())}")

if __name__ == "__main__":
    main()
```

**Step 2: Verificar que el script arranca**

```bash
python scripts/inyectar_datos_chiringuito.py --dry-run --fase entidades
```
Esperado: no errores de importación.

**Step 3: Commit**
```bash
git add scripts/inyectar_datos_chiringuito.py
git commit -m "feat: scaffold script inyeccion datos chiringuito"
```

---

## Task 3: Asegurar entidades (clientes + proveedores)

**Files:**
- Modificar: `scripts/inyectar_datos_chiringuito.py` — añadir `asegurar_entidades()`

**Step 1: Añadir datos maestros + función**

Insertar antes de `main()`:

```python
# --- Datos maestros ---
PROVEEDORES = [
    {"cod": "MAKRO", "cif": "A28054609", "nombre": "MAKRO AUTOSERVICIO S.A.",
     "codimpuesto": "IVA21", "codpais": "ESP"},
    {"cod": "AYTOMARB", "cif": "P2906010J", "nombre": "AYUNTAMIENTO DE MARBELLA",
     "codimpuesto": "IVA21", "codpais": "ESP"},
    {"cod": "RENTMOB", "cif": "B29022340", "nombre": "RENTING MOBILIARIO TERRAZA S.L.",
     "codimpuesto": "IVA21", "codpais": "ESP"},
    {"cod": "GASTROCOSTA", "cif": "B29055407", "nombre": "GRUPO GASTRO COSTA DEL SOL S.L.",
     "codimpuesto": "IVA21", "codpais": "ESP"},
    {"cod": "ENDESA", "cif": "A81948077", "nombre": "ENDESA ENERGIA S.A.U.",
     "codimpuesto": "IVA21", "codpais": "ESP"},
]

CLIENTES = [
    {"cod": "VENTASD", "cif": "00000000T", "nombre": "VENTAS DIARIAS PLAYA",
     "codimpuesto": "IVA10", "codpais": "ESP"},
    {"cod": "EVENTOS", "cif": "00000001R", "nombre": "EVENTOS PRIVADOS PLAYA",
     "codimpuesto": "IVA10", "codpais": "ESP"},
]


def _entidad_existe(tipo, cod):
    """Verifica si cliente/proveedor existe en FS."""
    ep = "clientes" if tipo == "cliente" else "proveedores"
    try:
        data = api_get(f"{ep}/{cod}")
        return bool(data)
    except Exception:
        return False


def asegurar_entidades(estado, dry_run=False):
    """Crea clientes y proveedores si no existen."""
    print("\n[ENTIDADES] Verificando...")

    for prov in PROVEEDORES:
        cod = prov["cod"]
        if estado["entidades"].get(f"prov_{cod}"):
            print(f"  Proveedor {cod}: ya registrado (estado)")
            continue
        if _entidad_existe("proveedor", cod):
            estado["entidades"][f"prov_{cod}"] = True
            print(f"  Proveedor {cod}: ya existe en FS")
            continue
        if dry_run:
            print(f"  [DRY] Crearía proveedor {cod}")
            continue
        data = {
            "idempresa": IDEMPRESA,
            "codproveedor": cod,
            "cifnif": prov["cif"],
            "nombre": prov["nombre"],
            "codimpuesto": prov["codimpuesto"],
            "codpais": prov["codpais"],
            "coddivisa": "EUR",
        }
        api_post_form("proveedores", data)
        estado["entidades"][f"prov_{cod}"] = True
        print(f"  Proveedor {cod}: CREADO")
        time.sleep(DELAY)

    for cli in CLIENTES:
        cod = cli["cod"]
        if estado["entidades"].get(f"cli_{cod}"):
            print(f"  Cliente {cod}: ya registrado (estado)")
            continue
        if _entidad_existe("cliente", cod):
            estado["entidades"][f"cli_{cod}"] = True
            print(f"  Cliente {cod}: ya existe en FS")
            continue
        if dry_run:
            print(f"  [DRY] Crearía cliente {cod}")
            continue
        data = {
            "idempresa": IDEMPRESA,
            "codcliente": cod,
            "cifnif": cli["cif"],
            "nombre": cli["nombre"],
            "codimpuesto": cli["codimpuesto"],
            "codpais": cli["codpais"],
            "coddivisa": "EUR",
        }
        api_post_form("clientes", data)
        estado["entidades"][f"cli_{cod}"] = True
        print(f"  Cliente {cod}: CREADO")
        time.sleep(DELAY)
```

**Step 2: Probar**
```bash
python scripts/inyectar_datos_chiringuito.py --fase entidades --dry-run
python scripts/inyectar_datos_chiringuito.py --fase entidades
```
Esperado: 5 proveedores + 2 clientes creados (o "ya existe").

**Step 3: Verificar via API**
```bash
python -c "
import requests
H = {'Token': 'iOXmrA1Bbn8RDWXLv91L'}
r = requests.get('https://contabilidad.lemonfresh-tuc.com/api/3/proveedores', headers=H, params={'limit':50})
print([x['codproveedor'] for x in r.json()])
"
```

**Step 4: Commit**
```bash
git add scripts/inyectar_datos_chiringuito.py tmp/
git commit -m "feat: inyeccion — asegurar entidades clientes/proveedores empresa 4"
```

---

## Task 4: Generar facturas cliente (FC)

**Files:**
- Modificar: `scripts/inyectar_datos_chiringuito.py` — añadir `generar_fc()`

**Step 1: Añadir distribución mensual + función FC**

```python
# Distribución % mensual de ventas (actividad estacional)
DIST_MENSUAL = [0.01, 0.01, 0.02, 0.08, 0.10, 0.10, 0.22, 0.25, 0.12, 0.05, 0.02, 0.02]

# Ingresos anuales por ejercicio
INGRESOS_ANUALES = {2022: 360_000, 2023: 440_000, 2024: 510_000, 2025: 475_000}

# 300 FC por año: ~70% ventas diarias, ~30% eventos
FC_POR_ANYO = 300


def _fecha_aleatoria_mes(anyo, mes):
    """Devuelve una fecha aleatoria dentro del mes (días laborables aprox.)."""
    inicio = date(anyo, mes, 1)
    if mes == 12:
        fin = date(anyo, 12, 31)
    else:
        fin = date(anyo, mes + 1, 1) - timedelta(days=1)
    dias = (fin - inicio).days
    return inicio + timedelta(days=random.randint(0, dias))


def _distribuir_por_mes(total_docs, distribucion):
    """Reparte total_docs en lista de 12 enteros según distribución %."""
    por_mes = [max(1, round(total_docs * p)) for p in distribucion]
    # Ajustar para que sumen exactamente total_docs
    diferencia = total_docs - sum(por_mes)
    if diferencia > 0:
        por_mes[7] += diferencia  # agosto absorbe diferencia
    elif diferencia < 0:
        por_mes[7] += diferencia
    return por_mes


def generar_fc(anyo, estado, dry_run=False):
    """Genera 300 facturas cliente para el ejercicio dado."""
    clave = str(anyo)
    if clave not in estado["fc"]:
        estado["fc"][clave] = []

    ya_creadas = len(estado["fc"][clave])
    if ya_creadas >= FC_POR_ANYO:
        print(f"\n[FC {anyo}] Ya completas ({ya_creadas}/{FC_POR_ANYO})")
        return

    codejercicio = EJERCICIOS[anyo]
    ingresos = INGRESOS_ANUALES[anyo]
    por_mes = _distribuir_por_mes(FC_POR_ANYO, DIST_MENSUAL)
    ticket_medio = ingresos / FC_POR_ANYO

    print(f"\n[FC {anyo}] Generando {FC_POR_ANYO - ya_creadas} facturas...")
    creadas = 0
    idx_global = 0

    for mes_idx, num_mes in enumerate(por_mes):
        mes = mes_idx + 1
        for _ in range(num_mes):
            if idx_global < ya_creadas:
                idx_global += 1
                continue  # resume: saltar ya creadas

            # 70% ventas diarias (IVA10), 30% eventos (IVA10 también)
            es_evento = random.random() < 0.30
            codcliente = "EVENTOS" if es_evento else "VENTASD"
            concepto = "Servicio de restauracion y hosteleria en playa" if not es_evento \
                       else "Servicio de catering y organizacion de evento privado"

            # Importe: variacion +-40% sobre ticket medio, más alto en eventos
            factor = random.uniform(0.6, 1.4)
            if es_evento:
                factor = random.uniform(1.5, 4.0)
            base = round(ticket_medio * factor * (0.8 if es_evento else 1.0), 2)
            iva = round(base * 0.10, 2)
            total = round(base + iva, 2)

            fecha = _fecha_aleatoria_mes(anyo, mes)

            if dry_run:
                print(f"  [DRY] FC {anyo}/{mes:02d}: {codcliente} {base}€ base")
                idx_global += 1
                continue

            lineas = json.dumps([{
                "descripcion": concepto,
                "cantidad": 1,
                "pvpunitario": base,
                "codimpuesto": "IVA10",
            }])

            form = {
                "idempresa": IDEMPRESA,
                "codejercicio": codejercicio,
                "codcliente": codcliente,
                "fecha": fecha.strftime("%d-%m-%Y"),
                "coddivisa": "EUR",
                "lineas": lineas,
            }

            try:
                resp = api_post_form("crearFacturaCliente", form)
                idfactura = resp.get("doc", {}).get("idfactura") or resp.get("idfactura")
                estado["fc"][clave].append({"id": idfactura, "fecha": str(fecha), "base": base})
                creadas += 1
                if creadas % 20 == 0:
                    guardar_estado(estado)
                    print(f"  ... {creadas} creadas")
            except Exception as e:
                print(f"  ERROR FC {fecha}: {e}")

            time.sleep(DELAY)
            idx_global += 1

    guardar_estado(estado)
    print(f"[FC {anyo}] COMPLETADO: {creadas} nuevas (total {len(estado['fc'][clave])})")
```

**Step 2: Probar con un año en dry-run**
```bash
python scripts/inyectar_datos_chiringuito.py --fase fc --anyo 2022 --dry-run
```
Esperado: imprime 300 líneas "[DRY] FC 2022/..."

**Step 3: Crear primer lote real (2022)**
```bash
python scripts/inyectar_datos_chiringuito.py --fase fc --anyo 2022
```
Esperado: 300 facturas creadas (~4 min con delay 0.25s).

**Step 4: Verificar en FS**
```bash
python -c "
import requests
H = {'Token': 'iOXmrA1Bbn8RDWXLv91L'}
r = requests.get('https://contabilidad.lemonfresh-tuc.com/api/3/facturaclientes',
    headers=H, params={'limit':500})
e4 = [x for x in r.json() if x.get('idempresa') == 4]
print(f'FC empresa 4: {len(e4)}')
"
```

**Step 5: Crear el resto (2023, 2024, 2025)**
```bash
python scripts/inyectar_datos_chiringuito.py --fase fc --anyo 2023
python scripts/inyectar_datos_chiringuito.py --fase fc --anyo 2024
python scripts/inyectar_datos_chiringuito.py --fase fc --anyo 2025
```

**Step 6: Commit**
```bash
git add scripts/inyectar_datos_chiringuito.py tmp/
git commit -m "feat: inyeccion — 1200 facturas cliente FC empresa 4 (2022-2025)"
```

---

## Task 5: Generar facturas proveedor (FV)

**Files:**
- Modificar: `scripts/inyectar_datos_chiringuito.py` — añadir `generar_fv()`

**Step 1: Añadir función FV**

```python
# Distribución FV por proveedor y temporada
# Makro: 3x/sem en temporada (abr-oct), 1x/sem en invierno
# Resto: según frecuencia mensual

FV_POR_ANYO = 200  # objetivo por año


def _gastos_anuales(anyo):
    ingresos = INGRESOS_ANUALES[anyo]
    return {
        "MAKRO":      {"pct": 0.32, "concepto": "Suministro alimentacion y bebidas temporada"},
        "AYTOMARB":   {"pct": 0.04, "concepto": "Canon anual licencia ocupacion dominio publico maritimo"},
        "RENTMOB":    {"pct": 0.03, "concepto": "Cuota renting hamacas, sombrillas y mobiliario playa"},
        "GASTROCOSTA":{"pct": 0.025,"concepto": "Management fee gestion operaciones hosteleria"},
        "ENDESA":     {"pct": 0.02, "concepto": "Suministro electrico instalaciones chiringuito"},
    }


def _num_facturas_proveedor(cod, total_fv):
    """Reparte FV entre proveedores según frecuencia realista."""
    reparto = {"MAKRO": 0.60, "RENTMOB": 0.12, "ENDESA": 0.12,
               "GASTROCOSTA": 0.08, "AYTOMARB": 0.08}
    return max(1, round(total_fv * reparto.get(cod, 0.1)))


def generar_fv(anyo, estado, dry_run=False):
    """Genera ~200 facturas proveedor para el ejercicio dado."""
    clave = str(anyo)
    if clave not in estado["fv"]:
        estado["fv"][clave] = []

    ya_creadas = len(estado["fv"][clave])
    if ya_creadas >= FV_POR_ANYO:
        print(f"\n[FV {anyo}] Ya completas ({ya_creadas}/{FV_POR_ANYO})")
        return

    codejercicio = EJERCICIOS[anyo]
    gastos = _gastos_anuales(anyo)
    ingresos = INGRESOS_ANUALES[anyo]
    print(f"\n[FV {anyo}] Generando facturas proveedor...")

    creadas = 0
    idx_global = 0

    for cod, info in gastos.items():
        num = _num_facturas_proveedor(cod, FV_POR_ANYO)
        gasto_total = ingresos * info["pct"]
        importe_medio = gasto_total / num

        # Distribución mensual según proveedor
        if cod == "AYTOMARB":
            fechas = [date(anyo, 3, 15)]  # canon anual en marzo
        elif cod in ("RENTMOB", "ENDESA"):
            fechas = [date(anyo, mes, random.randint(1, 28)) for mes in range(1, 13)]
        elif cod == "GASTROCOSTA":
            fechas = [date(anyo, mes, random.randint(1, 28)) for mes in [3, 6, 9, 12]]
        else:
            # Makro: concentrado en temporada
            por_mes = _distribuir_por_mes(num, DIST_MENSUAL)
            fechas = []
            for mes_idx, n in enumerate(por_mes):
                mes = mes_idx + 1
                for _ in range(n):
                    fechas.append(_fecha_aleatoria_mes(anyo, mes))

        for i, fecha in enumerate(fechas[:num]):
            if idx_global < ya_creadas:
                idx_global += 1
                continue

            factor = random.uniform(0.7, 1.3)
            base = round(importe_medio * factor, 2)
            iva_pct = 0.21
            iva = round(base * iva_pct, 2)

            num_factura = f"{cod[:3]}{anyo}{i+1:03d}"

            if dry_run:
                print(f"  [DRY] FV {anyo} {cod}: {base}€ base {fecha}")
                idx_global += 1
                continue

            lineas = json.dumps([{
                "descripcion": info["concepto"],
                "cantidad": 1,
                "pvpunitario": base,
                "codimpuesto": "IVA21",
            }])

            form = {
                "idempresa": IDEMPRESA,
                "codejercicio": codejercicio,
                "codproveedor": cod,
                "numproveedor": num_factura,
                "fecha": fecha.strftime("%d-%m-%Y"),
                "coddivisa": "EUR",
                "lineas": lineas,
            }

            try:
                resp = api_post_form("crearFacturaProveedor", form)
                idfactura = resp.get("doc", {}).get("idfactura") or resp.get("idfactura")
                estado["fv"][clave].append({"id": idfactura, "cod": cod,
                                            "fecha": str(fecha), "base": base})
                creadas += 1
                if creadas % 20 == 0:
                    guardar_estado(estado)
                    print(f"  ... {creadas} FV creadas")
            except Exception as e:
                print(f"  ERROR FV {cod} {fecha}: {e}")

            time.sleep(DELAY)
            idx_global += 1

    guardar_estado(estado)
    print(f"[FV {anyo}] COMPLETADO: {creadas} nuevas")
```

**Step 2: Probar dry-run**
```bash
python scripts/inyectar_datos_chiringuito.py --fase fv --anyo 2022 --dry-run
```

**Step 3: Crear FV para todos los años**
```bash
python scripts/inyectar_datos_chiringuito.py --fase fv --anyo 2022
python scripts/inyectar_datos_chiringuito.py --fase fv --anyo 2023
python scripts/inyectar_datos_chiringuito.py --fase fv --anyo 2024
python scripts/inyectar_datos_chiringuito.py --fase fv --anyo 2025
```

**Step 4: Commit**
```bash
git add scripts/inyectar_datos_chiringuito.py tmp/
git commit -m "feat: inyeccion — 800 facturas proveedor FV empresa 4 (2022-2025)"
```

---

## Task 6: Asientos directos (NOM + amortizaciones)

**Files:**
- Modificar: `scripts/inyectar_datos_chiringuito.py` — añadir `generar_asientos_directos()`

**Step 1: Añadir función asientos directos**

Nóminas: sueldos 640, SS empresa 642, IRPF retención 4751, SS acred 476, rem. pendiente 4651.
Amortizaciones: dotación 681, amortización acumulada 2813/2817.

```python
def _crear_asiento(concepto, fecha, codejercicio, partidas, dry_run=False):
    """Crea asiento + partidas en FS. Retorna idasiento o None."""
    if dry_run:
        print(f"  [DRY] Asiento '{concepto}' {fecha}: {len(partidas)} partidas")
        return None

    form_asiento = {
        "idempresa": IDEMPRESA,
        "codejercicio": codejercicio,
        "fecha": fecha.strftime("%d-%m-%Y"),
        "concepto": concepto,
    }
    resp = api_post_form("asientos", form_asiento)
    idasiento = resp.get("data", {}).get("idasiento") or resp.get("idasiento")
    if not idasiento:
        print(f"  ERROR: no idasiento en respuesta: {resp}")
        return None

    for p in partidas:
        p["idasiento"] = idasiento
        p["idempresa"] = IDEMPRESA
        try:
            api_post_form("partidas", p)
        except Exception as e:
            print(f"  ERROR partida {p}: {e}")
        time.sleep(DELAY * 0.5)

    time.sleep(DELAY)
    return idasiento


# Subcuentas usadas (deben existir tras importar PGC)
SC = {
    "sueldos":    "6400000000",
    "ss_empresa": "6420000000",
    "irpf_ret":   "4751000000",
    "ss_acred":   "4760000000",
    "rem_pend":   "4651000000",
    "banco":      "5720000000",
    "amort_dot":  "6811000000",  # dotacion amortizacion inmov material
    "amort_acum": "2813000000",  # amort acum maquinaria/equipo
}

# Masa salarial anual (aprox 28% ingresos)
def _masa_salarial(anyo):
    return INGRESOS_ANUALES[anyo] * 0.28

# Activos fijos amortizables (comprados en 2022, coef 10% lineal)
ACTIVO_BRUTO = 80_000  # equipo cocina, mobiliario, instalaciones
CUOTA_AMORT_ANUAL = ACTIVO_BRUTO * 0.10


def generar_asientos_directos(anyo, estado, dry_run=False):
    """Genera 12 asientos nómina + 12 amortizaciones mensuales."""
    clave = str(anyo)
    if clave not in estado["asientos"]:
        estado["asientos"][clave] = []

    codejercicio = EJERCICIOS[anyo]
    masa = _masa_salarial(anyo)
    cuota_amort_mens = round(CUOTA_AMORT_ANUAL / 12, 2)
    print(f"\n[ASIENTOS {anyo}] Generando nóminas + amortizaciones...")

    # Solo meses de actividad tienen nómina completa (fijos discontinuos)
    # Ene-Mar y Nov-Dic: 1 empleado (encargado), Abr-Oct: 8 empleados
    meses_plenos = list(range(4, 11))  # abril a octubre

    for mes in range(1, 13):
        fecha = date(anyo, mes, 28)  # fin de mes
        factor_mes = 1.0 if mes in meses_plenos else 0.15  # esqueleto en invierno

        sueldo_bruto = round((masa / 7) * factor_mes if mes in meses_plenos
                             else (masa * 0.15 / 5), 2)
        ss_emp = round(sueldo_bruto * 0.295, 2)
        irpf = round(sueldo_bruto * 0.15, 2)
        ss_trab = round(sueldo_bruto * 0.0635, 2)
        neto = round(sueldo_bruto - irpf - ss_trab, 2)

        clave_nom = f"nom_{anyo}_{mes:02d}"
        if any(a.get("clave") == clave_nom for a in estado["asientos"][clave]):
            continue

        partidas_nom = [
            {"codsubcuenta": SC["sueldos"],    "debe": sueldo_bruto, "haber": 0, "concepto": f"Nomina {mes:02d}/{anyo}"},
            {"codsubcuenta": SC["ss_empresa"], "debe": ss_emp, "haber": 0,       "concepto": f"SS empresa {mes:02d}/{anyo}"},
            {"codsubcuenta": SC["irpf_ret"],   "debe": 0, "haber": irpf,         "concepto": f"IRPF retencion {mes:02d}/{anyo}"},
            {"codsubcuenta": SC["ss_acred"],   "debe": 0, "haber": ss_emp + ss_trab, "concepto": f"SS acreedora {mes:02d}/{anyo}"},
            {"codsubcuenta": SC["rem_pend"],   "debe": 0, "haber": neto,         "concepto": f"Remuneracion pendiente pago {mes:02d}/{anyo}"},
        ]

        idasiento = _crear_asiento(f"Nomina {mes:02d}/{anyo}", fecha,
                                   codejercicio, partidas_nom, dry_run)
        if idasiento or dry_run:
            estado["asientos"][clave].append({"clave": clave_nom, "id": idasiento})

        # Amortización mensual
        clave_amort = f"amort_{anyo}_{mes:02d}"
        if any(a.get("clave") == clave_amort for a in estado["asientos"][clave]):
            continue

        partidas_amort = [
            {"codsubcuenta": SC["amort_dot"],  "debe": cuota_amort_mens, "haber": 0,
             "concepto": f"Amortizacion inmovilizado {mes:02d}/{anyo}"},
            {"codsubcuenta": SC["amort_acum"], "debe": 0, "haber": cuota_amort_mens,
             "concepto": f"Amortizacion acumulada {mes:02d}/{anyo}"},
        ]
        idasiento2 = _crear_asiento(f"Amortizacion {mes:02d}/{anyo}", fecha,
                                    codejercicio, partidas_amort, dry_run)
        if idasiento2 or dry_run:
            estado["asientos"][clave].append({"clave": clave_amort, "id": idasiento2})

    guardar_estado(estado)
    print(f"[ASIENTOS {anyo}] COMPLETADO")
```

**Step 2: Probar**
```bash
python scripts/inyectar_datos_chiringuito.py --fase asientos --anyo 2022 --dry-run
```

**Step 3: Crear asientos reales**
```bash
python scripts/inyectar_datos_chiringuito.py --fase asientos
```
Esperado: 24 asientos/año × 4 años = 96 asientos totales.

**Step 4: Commit**
```bash
git add scripts/inyectar_datos_chiringuito.py tmp/
git commit -m "feat: inyeccion — asientos nomina+amortizacion 2022-2025 empresa 4"
```

---

## Task 7: Regularización IVA trimestral

**Files:**
- Modificar: `scripts/inyectar_datos_chiringuito.py` — añadir IVA a `generar_asientos_directos()`

**Step 1: Añadir subcuentas IVA y función**

```python
SC["iva_rep"]    = "4770000000"  # IVA repercutido (acreedor)
SC["iva_sop"]    = "4720000000"  # IVA soportado (deudor)
SC["hp_acr"]     = "4750000000"  # HP acreedora por IVA (resultado liquidacion)


def generar_iva_trimestral(anyo, estado, dry_run=False):
    """Genera 4 asientos de liquidación IVA (uno por trimestre)."""
    clave = str(anyo)
    codejercicio = EJERCICIOS[anyo]
    ingresos = INGRESOS_ANUALES[anyo]
    # Aprox: IVA rep = ingresos * 10% (restauracion), IVA sop = gastos * 21% (compras)
    gastos_totales = ingresos * (0.32 + 0.03 + 0.02 + 0.025 + 0.04)
    iva_rep_anual = ingresos * 0.10
    iva_sop_anual = gastos_totales * 0.21

    # Distribución trimestral por estacionalidad
    dist_trim = [0.12, 0.23, 0.55, 0.10]  # T1 invierno, T3 verano pico
    fechas_trim = [date(anyo, 4, 20), date(anyo, 7, 20),
                   date(anyo, 10, 20), date(anyo, 12, 30)]
    nombres_trim = ["T1", "T2", "T3", "T4"]

    print(f"\n[IVA {anyo}] Generando liquidaciones trimestrales...")

    for i, (fecha, nombre, pct) in enumerate(zip(fechas_trim, nombres_trim, dist_trim)):
        clave_iva = f"iva_{anyo}_{nombre}"
        if any(a.get("clave") == clave_iva for a in estado["asientos"].get(clave, [])):
            continue

        iva_rep = round(iva_rep_anual * pct, 2)
        iva_sop = round(iva_sop_anual * pct, 2)
        resultado = round(iva_rep - iva_sop, 2)

        if resultado >= 0:
            partidas = [
                {"codsubcuenta": SC["iva_rep"], "debe": iva_rep, "haber": 0,
                 "concepto": f"Liquidacion IVA {nombre} {anyo}"},
                {"codsubcuenta": SC["iva_sop"], "debe": 0, "haber": iva_sop,
                 "concepto": f"Liquidacion IVA {nombre} {anyo}"},
                {"codsubcuenta": SC["hp_acr"],  "debe": 0, "haber": resultado,
                 "concepto": f"HP acreedora IVA {nombre} {anyo}"},
            ]
        else:
            # Resultado negativo: HP deudora (devolucion)
            partidas = [
                {"codsubcuenta": SC["iva_rep"], "debe": iva_rep, "haber": 0,
                 "concepto": f"Liquidacion IVA {nombre} {anyo}"},
                {"codsubcuenta": SC["iva_sop"], "debe": 0, "haber": iva_sop,
                 "concepto": f"Liquidacion IVA {nombre} {anyo}"},
                {"codsubcuenta": SC["iva_sop"], "debe": abs(resultado), "haber": 0,
                 "concepto": f"HP deudora IVA {nombre} {anyo}"},
            ]

        idasiento = _crear_asiento(f"Liquidacion IVA {nombre} {anyo}",
                                   fecha, codejercicio, partidas, dry_run)
        if clave not in estado["asientos"]:
            estado["asientos"][clave] = []
        if idasiento or dry_run:
            estado["asientos"][clave].append({"clave": clave_iva, "id": idasiento})

    guardar_estado(estado)
```

Añadir llamada en `main()` dentro del bloque `asientos`:
```python
if args.fase in ("asientos", "todo"):
    for anyo in anyos:
        generar_asientos_directos(anyo, estado, dry_run=args.dry_run)
        generar_iva_trimestral(anyo, estado, dry_run=args.dry_run)
```

**Step 2: Probar y crear**
```bash
python scripts/inyectar_datos_chiringuito.py --fase asientos --dry-run
python scripts/inyectar_datos_chiringuito.py --fase asientos
```

**Step 3: Commit**
```bash
git add scripts/inyectar_datos_chiringuito.py tmp/
git commit -m "feat: inyeccion — liquidacion IVA trimestral 2022-2025 empresa 4"
```

---

## Task 8: Cierre ejercicios 2022, 2023, 2024

**Files:**
- Modificar: `scripts/inyectar_datos_chiringuito.py` — añadir `cerrar_ejercicio()`

**Step 1: Añadir cierre**

El cierre contable consiste en:
1. Asiento de regularización: cerrar cuentas 6xx (gastos) y 7xx (ingresos) contra cuenta 129 (resultado del ejercicio).
2. Marcar ejercicio como CERRADO via PUT `/ejercicios/{cod}`.

```python
SC["resultado"]  = "1290000000"  # resultado del ejercicio
SC["ventas"]     = "7000000000"  # ventas y prestaciones servicios


def cerrar_ejercicio(anyo, estado, dry_run=False):
    """Asiento de regularización + cierre ejercicio."""
    clave = str(anyo)
    codejercicio = EJERCICIOS[anyo]
    clave_cierre = f"cierre_{anyo}"

    if any(a.get("clave") == clave_cierre
           for a in estado["asientos"].get(clave, [])):
        print(f"\n[CIERRE {anyo}] Ya realizado")
        return

    ingresos = INGRESOS_ANUALES[anyo]
    gastos_totales = ingresos * 0.88  # margen neto ~12%
    resultado_neto = round(ingresos - gastos_totales, 2)
    fecha_cierre = date(anyo, 12, 31)

    # Asiento regularización: ingresos → 129, gastos ← 129
    partidas = [
        {"codsubcuenta": SC["ventas"],    "debe": ingresos, "haber": 0,
         "concepto": f"Regularizacion ingresos {anyo}"},
        {"codsubcuenta": SC["sueldos"],   "debe": 0, "haber": round(ingresos * 0.28, 2),
         "concepto": f"Regularizacion gastos personal {anyo}"},
        {"codsubcuenta": "6000000000",    "debe": 0, "haber": round(ingresos * 0.32, 2),
         "concepto": f"Regularizacion compras {anyo}"},
        {"codsubcuenta": SC["amort_dot"], "debe": 0, "haber": CUOTA_AMORT_ANUAL,
         "concepto": f"Regularizacion amortizacion {anyo}"},
        {"codsubcuenta": SC["resultado"], "debe": 0, "haber": resultado_neto,
         "concepto": f"Resultado ejercicio {anyo}"},
    ]

    print(f"\n[CIERRE {anyo}] Resultado neto estimado: {resultado_neto:,.2f}€")
    idasiento = _crear_asiento(f"Regularizacion y cierre {anyo}",
                               fecha_cierre, codejercicio, partidas, dry_run)

    if not dry_run:
        # Marcar ejercicio como cerrado
        try:
            api_put_form(f"ejercicios/{codejercicio}", {"estado": "CERRADO"})
            print(f"[CIERRE {anyo}] Ejercicio {codejercicio} marcado CERRADO")
        except Exception as e:
            print(f"  AVISO: no se pudo cerrar ejercicio via API: {e}")

    if clave not in estado["asientos"]:
        estado["asientos"][clave] = []
    estado["asientos"][clave].append({"clave": clave_cierre, "id": idasiento})
    guardar_estado(estado)
    print(f"[CIERRE {anyo}] COMPLETADO")
```

**Step 2: Probar y ejecutar**
```bash
python scripts/inyectar_datos_chiringuito.py --fase cierre --dry-run
python scripts/inyectar_datos_chiringuito.py --fase cierre
```

**Step 3: Commit**
```bash
git add scripts/inyectar_datos_chiringuito.py tmp/
git commit -m "feat: inyeccion — cierre ejercicios 2022/2023/2024 empresa 4"
```

---

## Task 9: Verificación final

**Files:** ninguno (solo comandos de verificación)

**Step 1: Ejecutar resumen**
```bash
python scripts/inyectar_datos_chiringuito.py --fase todo --dry-run
```
Esperado: "FC creadas: 1200, FV creadas: 800, Asientos: 112+"

**Step 2: Verificar en FS via API**
```bash
python -c "
import requests
API = 'https://contabilidad.lemonfresh-tuc.com/api/3'
H = {'Token': 'iOXmrA1Bbn8RDWXLv91L'}

fc = [x for x in requests.get(f'{API}/facturaclientes', headers=H, params={'limit':2000}).json()
      if x.get('idempresa') == 4]
fv = [x for x in requests.get(f'{API}/facturaproveedores', headers=H, params={'limit':2000}).json()
      if x.get('idempresa') == 4]
asientos = [x for x in requests.get(f'{API}/asientos', headers=H, params={'limit':500}).json()
            if x.get('idempresa') == 4]

print(f'FC empresa 4: {len(fc)}')
print(f'FV empresa 4: {len(fv)}')
print(f'Asientos empresa 4: {len(asientos)}')
print(f'Total documentos: {len(fc) + len(fv)}')
"
```
Esperado: FC ~1200, FV ~800, Asientos ~112.

**Step 3: Arrancar dashboard y verificar visualmente**
```bash
# Terminal 1
cd sfce && uvicorn sfce.api.app:crear_app --factory --reload --port 8000

# Terminal 2
cd dashboard && npm run dev
```
Abrir `http://localhost:5173` → seleccionar empresa 4 → navegar PyG, Balance, Ingresos/Gastos.
Verificar que los charts muestran 4 años de datos con variación estacional.

**Step 4: Commit final**
```bash
git add docs/plans/2026-02-28-inyeccion-datos-chiringuito.md
git commit -m "docs: plan inyeccion datos chiringuito 2022-2025"
```

---

## Estimaciones

| Fase | Registros | Tiempo estimado |
|------|-----------|----------------|
| Ejercicios + PGC (browser) | 3 ejercicios | ~10 min manual |
| Entidades | 7 | <1 min |
| FC (1200 facturas) | 1.200 | ~8 min |
| FV (800 facturas) | 800 | ~5 min |
| Asientos NOM+amort (96) | 96 × 5 partidas | ~4 min |
| IVA trimestral (16) | 16 × 3 partidas | ~1 min |
| Cierre (3) | 3 × 5 partidas | <1 min |
| **TOTAL** | **~2.200** | **~30 min** |

## Riesgos

1. **PGC no importado**: crearFactura* falla si no existen subcuentas. Verificar Task 1 antes de continuar.
2. **codejercicio en facturas históricas**: FS puede no asignar fecha 2022 a ejercicio C422 automáticamente si la fecha no está dentro de su rango. Verificar con una FC de prueba primero.
3. **Rate limiting API**: delay 0.25s entre calls. Si hay errores 429, subir a 0.5s.
4. **Asientos invertidos FV**: bug conocido de FS. Para datos de prueba es aceptable no corregirlos (afecta asientos, no a los charts de facturas).
