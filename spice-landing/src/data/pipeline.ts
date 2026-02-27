export interface FasePipeline {
  numero: number
  nombre: string
  descripcion: string
  detalle: string
  datoClave: string
  icono: string
}

export const fases: FasePipeline[] = [
  {
    numero: 1,
    nombre: 'LECTURA',
    descripcion: 'Lectura inteligente del documento',
    detalle: 'Tres motores de inteligencia artificial leen cada documento y extraen todos los datos: emisor, CIF, fecha, base imponible, tipo de IVA, total, concepto y lineas de detalle.',
    datoClave: '15+ datos extraidos',
    icono: 'scan',
  },
  {
    numero: 2,
    nombre: 'COMPROBACIONES',
    descripcion: '9 verificaciones previas',
    detalle: 'Antes de contabilizar, se verifica: formato del CIF, cuadre aritmetico (base + IVA = total), que no sea duplicado, que la fecha este dentro del ejercicio y que el proveedor este dado de alta.',
    datoClave: '9 verificaciones',
    icono: 'shield-check',
  },
  {
    numero: 3,
    nombre: 'REGISTRO',
    descripcion: 'Contabilizacion automatica',
    detalle: 'Crea el apunte contable en el programa de gestion. Si algo falla (proveedor desconocido, subcuenta inexistente...), intenta resolverlo automaticamente antes de pedir ayuda al gestor.',
    datoClave: '6 estrategias de resolucion',
    icono: 'file-plus',
  },
  {
    numero: 4,
    nombre: 'VERIFICACION',
    descripcion: 'Comprobacion del asiento',
    detalle: 'Verifica que el asiento generado es correcto: que las partidas estan en el debe y haber correspondientes, que las subcuentas son las adecuadas y que los importes coinciden.',
    datoClave: 'Verificacion completa',
    icono: 'book-open',
  },
  {
    numero: 5,
    nombre: 'CORRECCION',
    descripcion: '7 correcciones automaticas',
    detalle: 'Convierte divisas extranjeras a euros, reclasifica suplidos aduaneros (de gasto a HP deudora), invierte notas de credito, genera autorepercusion en intracomunitarias y corrige subcuentas.',
    datoClave: '7 tipos de correccion',
    icono: 'wrench',
  },
  {
    numero: 6,
    nombre: 'COMPROBACION GLOBAL',
    descripcion: '13 verificaciones cruzadas',
    detalle: 'Verifica que el balance cuadra, que el IVA repercutido coincide con las facturas emitidas, que el IVA soportado coincide con las recibidas, coherencia con modelo 347, y revision adicional por IA.',
    datoClave: '13 verificaciones + auditoria IA',
    icono: 'check-circle',
  },
  {
    numero: 7,
    nombre: 'RESULTADO',
    descripcion: 'Libros contables e informes',
    detalle: 'Genera el libro diario en Excel, los datos para los modelos fiscales, y un informe de auditoria completo con el indice de fiabilidad.',
    datoClave: 'Todo documentado',
    icono: 'file-output',
  },
]
