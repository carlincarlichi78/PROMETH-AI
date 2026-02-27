export interface TipoDocumento {
  codigo: string
  nombre: string
  descripcion: string
  asiento: string
  ejemplo: {
    concepto: string
    partidas: { subcuenta: string; nombre: string; debe?: number; haber?: number }[]
  }
  grupo: 'factura' | 'otro'
}

export const tiposDocumento: TipoDocumento[] = [
  {
    codigo: 'FC',
    nombre: 'Factura compra',
    descripcion: 'Facturas recibidas de proveedores',
    asiento: '6xx+472 @ 400',
    ejemplo: {
      concepto: 'Compra material oficina — 1.210 EUR',
      partidas: [
        { subcuenta: '629', nombre: 'Otros servicios', debe: 1000 },
        { subcuenta: '472', nombre: 'IVA soportado 21%', debe: 210 },
        { subcuenta: '400', nombre: 'Proveedor', haber: 1210 },
      ],
    },
    grupo: 'factura',
  },
  {
    codigo: 'FV',
    nombre: 'Factura venta',
    descripcion: 'Facturas emitidas a clientes',
    asiento: '430 @ 7xx+477',
    ejemplo: {
      concepto: 'Prestacion servicios — 2.420 EUR',
      partidas: [
        { subcuenta: '430', nombre: 'Cliente', debe: 2420 },
        { subcuenta: '705', nombre: 'Prestacion servicios', haber: 2000 },
        { subcuenta: '477', nombre: 'IVA repercutido 21%', haber: 420 },
      ],
    },
    grupo: 'factura',
  },
  {
    codigo: 'NC',
    nombre: 'Nota credito',
    descripcion: 'Abono o devolucion parcial',
    asiento: 'Inverso de FC/FV',
    ejemplo: {
      concepto: 'Abono parcial — 242 EUR',
      partidas: [
        { subcuenta: '400', nombre: 'Proveedor', debe: 242 },
        { subcuenta: '629', nombre: 'Otros servicios', haber: 200 },
        { subcuenta: '472', nombre: 'IVA soportado', haber: 42 },
      ],
    },
    grupo: 'factura',
  },
  {
    codigo: 'ANT',
    nombre: 'Anticipo',
    descripcion: 'Pago anticipado a proveedor',
    asiento: '407 @ 572',
    ejemplo: {
      concepto: 'Anticipo proveedor — 500 EUR',
      partidas: [
        { subcuenta: '407', nombre: 'Anticipos proveedores', debe: 500 },
        { subcuenta: '572', nombre: 'Bancos', haber: 500 },
      ],
    },
    grupo: 'factura',
  },
  {
    codigo: 'REC',
    nombre: 'Recargo equivalencia',
    descripcion: 'Factura con recargo de equivalencia',
    asiento: '6xx+472+472RE @ 400',
    ejemplo: {
      concepto: 'Compra mercaderia RE — 1.262 EUR',
      partidas: [
        { subcuenta: '600', nombre: 'Compras', debe: 1000 },
        { subcuenta: '472', nombre: 'IVA soportado 21%', debe: 210 },
        { subcuenta: '472', nombre: 'Recargo equiv. 5.2%', debe: 52 },
        { subcuenta: '400', nombre: 'Proveedor', haber: 1262 },
      ],
    },
    grupo: 'factura',
  },
  {
    codigo: 'NOM',
    nombre: 'Nomina',
    descripcion: 'Nominas de empleados',
    asiento: '640+642 @ 476+4751+572',
    ejemplo: {
      concepto: 'Nomina enero — 2.500 EUR bruto',
      partidas: [
        { subcuenta: '640', nombre: 'Sueldos y salarios', debe: 2500 },
        { subcuenta: '642', nombre: 'SS empresa', debe: 750 },
        { subcuenta: '476', nombre: 'SS acreedora', haber: 908 },
        { subcuenta: '4751', nombre: 'IRPF retenciones', haber: 375 },
        { subcuenta: '572', nombre: 'Bancos (neto)', haber: 1967 },
      ],
    },
    grupo: 'otro',
  },
  {
    codigo: 'SUM',
    nombre: 'Suministro',
    descripcion: 'Luz, agua, gas, telefono',
    asiento: '628+472 @ 410',
    ejemplo: {
      concepto: 'Factura electrica — 181.50 EUR',
      partidas: [
        { subcuenta: '628', nombre: 'Suministros', debe: 150 },
        { subcuenta: '472', nombre: 'IVA soportado 21%', debe: 31.50 },
        { subcuenta: '410', nombre: 'Acreedor', haber: 181.50 },
      ],
    },
    grupo: 'otro',
  },
  {
    codigo: 'BAN',
    nombre: 'Bancario',
    descripcion: 'Comisiones y movimientos bancarios',
    asiento: '626/662 @ 572',
    ejemplo: {
      concepto: 'Comision mantenimiento — 15 EUR',
      partidas: [
        { subcuenta: '626', nombre: 'Servicios bancarios', debe: 15 },
        { subcuenta: '572', nombre: 'Bancos', haber: 15 },
      ],
    },
    grupo: 'otro',
  },
  {
    codigo: 'RLC',
    nombre: 'Seguridad Social',
    descripcion: 'Recibos liquidacion cotizaciones',
    asiento: '642 @ 476',
    ejemplo: {
      concepto: 'Cuota SS autonomo — 294 EUR',
      partidas: [
        { subcuenta: '642', nombre: 'SS a cargo empresa', debe: 294 },
        { subcuenta: '476', nombre: 'SS acreedora', haber: 294 },
      ],
    },
    grupo: 'otro',
  },
  {
    codigo: 'IMP',
    nombre: 'Impuestos y tasas',
    descripcion: 'IBI, IAE, tasas municipales',
    asiento: '631 @ 572',
    ejemplo: {
      concepto: 'IBI local comercial — 450 EUR',
      partidas: [
        { subcuenta: '631', nombre: 'Otros tributos', debe: 450 },
        { subcuenta: '572', nombre: 'Bancos', haber: 450 },
      ],
    },
    grupo: 'otro',
  },
]
