"""Organiza las facturas PDF en la estructura de carpetas procesado/ por trimestre y tipo."""
import os, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')

base_dest = 'C:/Users/carli/PROYECTOS/CONTABILIDAD/clientes/pastorino-costa-del-sol/2025/procesado'
base_src = 'C:/Users/carli/PROYECTOS/PROYECTO PASTORINO/dashboard/documentos/gestor'

# Crear estructura
carpetas = [
    'T2/gastos/flete-maritimo',
    'T3/ingresos',
    'T3/gastos/flete-maritimo', 'T3/gastos/transporte-nacional',
    'T3/gastos/despacho-aduanero', 'T3/gastos/naviera',
    'T3/gastos/software', 'T3/gastos/publicidad',
    'T3/gastos/material-oficina', 'T3/gastos/compra-mercaderia',
    'T3/documentos-importacion/dau', 'T3/documentos-importacion/bl',
    'T3/documentos-importacion/phyto', 'T3/documentos-importacion/container',
    'T3/documentos-importacion/packing-list',
    'T3/liquidaciones', 'T3/banco', 'T3/otros',
    'T4/gastos/despacho-aduanero', 'T4/gastos/software',
]
for c in carpetas:
    os.makedirs(os.path.join(base_dest, c), exist_ok=True)

def copiar(src_carpeta, archivo, dest_carpeta):
    src = os.path.join(base_src, src_carpeta, archivo)
    dest = os.path.join(base_dest, dest_carpeta, archivo)
    if os.path.exists(src):
        shutil.copy2(src, dest)
        print(f"  -> {dest_carpeta}/{archivo}")
    else:
        print(f"  !! NO ENCONTRADO: {src}")

def copiar_carpeta(src_carpeta, dest_carpeta):
    src_dir = os.path.join(base_src, src_carpeta)
    if os.path.exists(src_dir):
        for f in os.listdir(src_dir):
            if f.endswith('.pdf'):
                copiar(src_carpeta, f, dest_carpeta)

print("=== FACTURAS EMITIDAS (INGRESOS) ===")
for f in ['INV_2025_00001.pdf', 'INV_2025_00002.pdf', 'INV_2025_00003.pdf', 'INV_2025_00004.pdf']:
    copiar('factura', f, 'T3/ingresos')

print("\n=== FLETE MARITIMO (LOGINET) ===")
for f in ['doc FC B 0003-00026826.pdf', 'FC B 0003-00026855.pdf', 'NC B 0003-00003967.pdf']:
    copiar('factura', f, 'T2/gastos/flete-maritimo')
for f in ['FC B 0003-00027144.pdf', 'FC 0003-00027760.pdf']:
    copiar('factura', f, 'T3/gastos/flete-maritimo')

print("\n=== COMPRA MERCADERIA (CAUQUEN) ===")
copiar('factura', 'Invoice E 00005-00004696.pdf', 'T3/gastos/compra-mercaderia')

print("\n=== TRANSPORTE NACIONAL (PRIMAFRIO) ===")
for f in ['1090161585.pdf', '1090165048.pdf', '1090167087.pdf', '1090168047.pdf']:
    copiar('factura', f, 'T3/gastos/transporte-nacional')

print("\n=== DESPACHO ADUANERO (PRIMATRANSIT + TRANSITAINER) ===")
for f in ['2390101398.pdf', '2390101399.pdf', '2390101400.pdf', '2390101460.pdf']:
    copiar('factura', f, 'T3/gastos/despacho-aduanero')
copiar('factura', 'Fatura TT FT25S_000116.pdf', 'T3/gastos/despacho-aduanero')
for f in ['2390102446.pdf', '2390400070.pdf']:
    copiar('factura', f, 'T4/gastos/despacho-aduanero')

print("\n=== NAVIERA (MAERSK) ===")
maersk = ['7532745537.pdf', '7533441178.pdf', '7533441271.pdf', '7533442509.pdf',
           '7533463809.pdf', '7533463896.pdf', '7533589808.pdf', '7533590105.pdf',
           '7533642938.pdf', '7533642998.pdf', '7533658621.pdf', '7533658622.pdf',
           '7533677478.pdf', '7537075071.pdf', '7532598836.pdf', '7532598836 (1).pdf']
for f in maersk:
    copiar('factura', f, 'T3/gastos/naviera')

print("\n=== SOFTWARE (ODOO) ===")
for f in ['2025_07_000004.pdf', '2025_09_000020.pdf']:
    copiar('factura', f, 'T3/gastos/software')
copiar('factura', 'INV_2025_10_00669.pdf', 'T4/gastos/software')

print("\n=== PUBLICIDAD (COPYRAP) ===")
copiar('factura', 'Factura 23355T.pdf', 'T3/gastos/publicidad')

print("\n=== MATERIAL OFICINA (EL CORTE INGLES) ===")
for f in ['FACTURA Pastorino.pdf', 'Factura Pastorino 2.pdf']:
    copiar('factura', f, 'T3/gastos/material-oficina')

print("\n=== DOCUMENTOS IMPORTACION ===")
copiar_carpeta('dau', 'T3/documentos-importacion/dau')
copiar_carpeta('bl', 'T3/documentos-importacion/bl')
copiar_carpeta('phyto', 'T3/documentos-importacion/phyto')
copiar_carpeta('container', 'T3/documentos-importacion/container')
copiar_carpeta('packing_list', 'T3/documentos-importacion/packing-list')

print("\n=== LIQUIDACIONES ===")
copiar_carpeta('liquidacion', 'T3/liquidaciones')
for f in ['Factura proveedores - Borrador_20250807_090407.pdf',
          'Factura proveedores segundo envio - Borrador_20250816_075941.pdf',
          'Factura proveedores tercer envio - Borrador_20250816_080043.pdf',
          'Factura proveedores - cuarto envio Borrador_20250816_080156.pdf']:
    copiar('factura', f, 'T3/liquidaciones')

print("\n=== BANCO ===")
copiar('factura', '20250000103889442236022[1].pdf', 'T3/banco')
for f in ['C20C1E.pdf', 'Justificante_transferencia_2025-07-11-11.12.55.885000.pdf']:
    copiar('otro', f, 'T3/banco')

print("\n=== OTROS ===")
for f in ['Factura Proforma 1.pdf', 'Factura Proforma 1 (1).pdf']:
    copiar('factura', f, 'T3/otros')
for f in ['01PRMR523886.pdf', 'Compra_Tarj_So.pdf', 'datos empresa malaga natural.pdf',
          'doc33865720250725104301.pdf', 'DB_aabhfcidgcdg0x088E.pdf', 'DB_aabhfcifahfc0x0E22.pdf']:
    copiar('otro', f, 'T3/otros')

print("\n=== LEGAL ===")
legal_dest = os.path.join(os.path.dirname(base_dest), 'legal')
os.makedirs(legal_dest, exist_ok=True)
legal_src = os.path.join(base_src, 'legal')
for f in os.listdir(legal_src):
    if f.endswith('.pdf'):
        shutil.copy2(os.path.join(legal_src, f), os.path.join(legal_dest, f))
        print(f"  -> legal/{f}")

print("\n=== COMPLETADO ===")
# Contar archivos copiados
total = 0
for root, dirs, files in os.walk(base_dest):
    total += len([f for f in files if f.endswith('.pdf')])
print(f"Total PDFs organizados: {total}")
