"""Resumen comparativo final con diferencias exactas."""

# Datos extraidos de la API

facturas = [
    # (empresa, codigo, numero_orig, neto, iva_factura, total)
    (1, "FAC2025A131", "2390101398", 7294.33, 483.53, 7777.86),
    (1, "FAC2025A132", "2390101399", 7608.29, 378.26, 7986.55),
    (1, "FAC2025A133", "2390101400", 7372.26, 374.59, 7746.85),
    (1, "FAC2025A135", "2390102446", 1880.30, 258.78, 2139.08),
    (3, "FAC2025A218", "2390101398", 7294.33, 1018.38, 8312.71),
    (3, "FAC2025A219", "2390101399", 7608.29, 1597.74, 9206.03),
    (3, "FAC2025A220", "2390101400", 7372.26, 970.74, 8343.00),
    (3, "FAC2025A228", "2390102446", 1880.30, 394.86, 2275.16),
]

# Partidas por factura (empresa, numero_orig, subcuenta, debe, haber)
partidas = [
    # Pastorino - FAC2025A131 (2390101398)
    (1, "2390101398", "4000000004", 0, 7777.86),
    (1, "2390101398", "4709000000", 2444.89, 0),
    (1, "2390101398", "4720000000", 0, 0),
    (1, "2390101398", "4720000021", 483.53, 0),
    (1, "2390101398", "6000000000", 4849.44, 0),
    # Pastorino - FAC2025A132 (2390101399)
    (1, "2390101399", "4000000004", 0, 7986.55),
    (1, "2390101399", "4709000000", 2846.99, 0),
    (1, "2390101399", "4720000000", 0, 0),
    (1, "2390101399", "4720000021", 378.26, 0),
    (1, "2390101399", "6000000000", 4761.30, 0),
    # Pastorino - FAC2025A133 (2390101400)
    (1, "2390101400", "4000000004", 0, 7746.85),
    (1, "2390101400", "4709000000", 2749.68, 0),
    (1, "2390101400", "4720000000", 0, 0),
    (1, "2390101400", "4720000021", 374.59, 0),
    (1, "2390101400", "6000000000", 4622.58, 0),
    # Pastorino - FAC2025A135 (2390102446) - sin IVA ADUANA
    (1, "2390102446", "4000000004", 0, 2139.08),
    (1, "2390102446", "4720000000", 0, 0),
    (1, "2390102446", "4720000021", 258.78, 0),
    (1, "2390102446", "6000000000", 1880.30, 0),
    # EMPRESA PRUEBA - FAC2025A218 (2390101398)
    (3, "2390101398", "4000000014", 0, 8312.71),
    (3, "2390101398", "4720000000", 0, 0),
    (3, "2390101398", "4720000021", 1018.38, 0),
    (3, "2390101398", "6000000000", 7294.33, 0),
    # EMPRESA PRUEBA - FAC2025A219 (2390101399)
    (3, "2390101399", "4000000014", 0, 9206.03),
    (3, "2390101399", "4720000021", 1597.74, 0),
    (3, "2390101399", "6000000000", 7608.29, 0),
    # EMPRESA PRUEBA - FAC2025A220 (2390101400)
    (3, "2390101400", "4000000014", 0, 8343.00),
    (3, "2390101400", "4720000000", 0, 0),
    (3, "2390101400", "4720000021", 970.74, 0),
    (3, "2390101400", "6000000000", 7372.26, 0),
    # EMPRESA PRUEBA - FAC2025A228 (2390102446)
    (3, "2390102446", "4000000014", 0, 2275.16),
    (3, "2390102446", "4720000021", 394.86, 0),
    (3, "2390102446", "6000000000", 1880.30, 0),
]

print("=" * 110)
print("COMPARATIVA FACTURA A FACTURA: PRIMATRANSIT (emp 1) vs CARGAEXPRESS (emp 3)")
print("=" * 110)

# Agrupar por numero original
numeros = ["2390101398", "2390101399", "2390101400", "2390102446"]

for num in numeros:
    f1 = [f for f in facturas if f[0] == 1 and f[2] == num][0]
    f3 = [f for f in facturas if f[0] == 3 and f[2] == num][0]

    print(f"\n--- Factura original: {num} ---")
    print(f"  {'Concepto':<25} {'Pastorino (emp 1)':>20} {'Emp Prueba (emp 3)':>20} {'Diferencia':>15}")
    print(f"  {'-'*80}")
    print(f"  {'Neto':<25} {f1[3]:>20.2f} {f3[3]:>20.2f} {f3[3]-f1[3]:>15.2f}")
    print(f"  {'IVA factura':<25} {f1[4]:>20.2f} {f3[4]:>20.2f} {f3[4]-f1[4]:>15.2f}")
    print(f"  {'Total factura':<25} {f1[5]:>20.2f} {f3[5]:>20.2f} {f3[5]-f1[5]:>15.2f}")

    # Partidas
    p1 = [(p[2], p[3], p[4]) for p in partidas if p[0] == 1 and p[1] == num]
    p3 = [(p[2], p[3], p[4]) for p in partidas if p[0] == 3 and p[1] == num]

    subs_all = sorted(set(p[0] for p in p1 + p3))
    print(f"\n  {'Subcuenta':<15} {'DEBE emp1':>12} {'HABER emp1':>12}  |  {'DEBE emp3':>12} {'HABER emp3':>12}")
    print(f"  {'-'*70}")
    for sub in subs_all:
        d1 = sum(p[1] for p in p1 if p[0] == sub or (sub[:4] in p[0][:4] and sub == sub))
        h1 = sum(p[2] for p in p1 if p[0] == sub)
        d3 = sum(p[1] for p in p3 if p[0] == sub or (sub.startswith("400") and p[0].startswith("400")))
        h3 = sum(p[2] for p in p3 if p[0] == sub or (sub.startswith("400") and p[0].startswith("400")))

        # Buscar exacto
        d1 = sum(p[1] for p in p1 if p[0] == sub)
        h1 = sum(p[2] for p in p1 if p[0] == sub)
        d3 = sum(p[1] for p in p3 if p[0] == sub)
        h3 = sum(p[2] for p in p3 if p[0] == sub)

        marker = ""
        if sub == "4709000000" and d1 > 0 and d3 == 0:
            marker = " <-- FALTA en emp3"
        elif sub == "6000000000" and abs(d3 - d1) > 1:
            marker = f" <-- INFLADO +{d3 - d1:.2f}"
        elif sub.startswith("472") and abs(d3 - d1) > 1:
            marker = f" <-- IVA exceso +{d3 - d1:.2f}"

        print(f"  {sub:<15} {d1:>12.2f} {h1:>12.2f}  |  {d3:>12.2f} {h3:>12.2f}{marker}")


# Totales globales
print(f"\n\n{'='*110}")
print("RESUMEN GLOBAL — IMPACTO EN CONTABILIDAD")
print(f"{'='*110}")

# Pastorino
g600_p = sum(p[3] - p[4] for p in partidas if p[0] == 1 and p[2] == "6000000000")
g472_p = sum(p[3] - p[4] for p in partidas if p[0] == 1 and p[2] == "4720000021")
g4709_p = sum(p[3] - p[4] for p in partidas if p[0] == 1 and p[2] == "4709000000")
g400_p = sum(p[3] - p[4] for p in partidas if p[0] == 1 and p[2].startswith("400"))

# EMPRESA PRUEBA
g600_e = sum(p[3] - p[4] for p in partidas if p[0] == 3 and p[2] == "6000000000")
g472_e = sum(p[3] - p[4] for p in partidas if p[0] == 3 and p[2] == "4720000021")
g4709_e = sum(p[3] - p[4] for p in partidas if p[0] == 3 and p[2] == "4709000000")
g400_e = sum(p[3] - p[4] for p in partidas if p[0] == 3 and p[2].startswith("400"))

print(f"\n  {'Cuenta':<25} {'Pastorino':>15} {'Emp Prueba':>15} {'Diferencia':>15} {'Impacto':>30}")
print(f"  {'-'*100}")
print(f"  {'600 Gastos':<25} {g600_p:>15.2f} {g600_e:>15.2f} {g600_e-g600_p:>15.2f} {'Gasto inflado en emp3':>30}")
print(f"  {'472 IVA soportado':<25} {g472_p:>15.2f} {g472_e:>15.2f} {g472_e-g472_p:>15.2f} {'IVA deducible inflado':>30}")
print(f"  {'4709 IVA PT (extraj)':<25} {g4709_p:>15.2f} {g4709_e:>15.2f} {g4709_e-g4709_p:>15.2f} {'Falta reclasificacion':>30}")
print(f"  {'400 Proveedores':<25} {g400_p:>15.2f} {g400_e:>15.2f} {g400_e-g400_p:>15.2f} {'Deuda proveedor':>30}")

print(f"\n  CAUSA RAIZ:")
print(f"  En Pastorino, las lineas 'IVA ADUANA' se reclasificaron correctamente:")
print(f"    - Se sacaron de 6000000000 (gastos) y se pusieron en 4709000000 (IVA PT no deducible)")
print(f"    - Y el IVA de esas lineas se puso a 0% (IVA0) en vez de 21%")
print(f"")
print(f"  En EMPRESA PRUEBA, las lineas 'IVA ADUANA' NO se reclasificaron:")
print(f"    - Todo el neto de la factura fue a 6000000000 (gastos) — incluido el suplido IVA PT")
print(f"    - El IVA de las lineas 'IVA ADUANA' se calculo al 21% en vez de 0%")
print(f"    - No existe partida 4709000000 (falta reclasificacion del suplido)")
print(f"")
print(f"  IMPACTO CUANTIFICADO:")
iva_exceso = g472_e - g472_p
gasto_exceso = g600_e - g600_p
print(f"    - IVA soportado inflado: +{iva_exceso:.2f} EUR (afecta modelo 303 - IVA a compensar)")
print(f"    - Gastos inflados: +{gasto_exceso:.2f} EUR (afecta resultado explotacion)")
print(f"    - Falta 4709: -{g4709_p:.2f} EUR (IVA PT no registrado como HP deudora)")
print(f"    - Deuda proveedor inflada: {abs(g400_e - g400_p):.2f} EUR (total facturas mayor)")
print(f"")
print(f"  DOS PROBLEMAS DISTINTOS:")
print(f"    1. LINEAS FACTURA: el pipeline SFCE NO aplico codimpuesto=IVA0 a lineas 'IVA ADUANA'")
print(f"       -> FS calculo IVA 21% sobre el suplido, inflando totaliva y total de la factura")
print(f"    2. ASIENTOS: tras crear la factura, NO se hizo la reclasificacion 600->4709")
print(f"       -> El importe del suplido IVA PT quedo en gastos (600) en vez de HP deudora (4709)")
