export interface ModeloFiscal {
  modelo: string
  nombre: string
  periodicidad: string
  quien: string
  categoria: 'automatico' | 'semi' | 'asistido'
  descripcionCorta: string
}

export const modelosFiscales: ModeloFiscal[] = [
  { modelo: '303', nombre: 'IVA', periodicidad: 'Trimestral', quien: 'Todos (peninsula)', categoria: 'automatico', descripcionCorta: 'Liquidacion IVA: repercutido - soportado' },
  { modelo: '420', nombre: 'IGIC', periodicidad: 'Trimestral', quien: 'Canarias', categoria: 'automatico', descripcionCorta: 'Equivalente al 303 para Canarias' },
  { modelo: '390', nombre: 'Resumen anual IVA', periodicidad: 'Anual', quien: 'Todos', categoria: 'automatico', descripcionCorta: 'Resumen de los 4 trimestres de IVA' },
  { modelo: '111', nombre: 'Retenciones IRPF', periodicidad: 'Trimestral', quien: 'Con retencion', categoria: 'automatico', descripcionCorta: 'Retenciones practicadas a profesionales' },
  { modelo: '190', nombre: 'Resumen retenciones', periodicidad: 'Anual', quien: 'Con retencion', categoria: 'automatico', descripcionCorta: 'Resumen anual del 111' },
  { modelo: '115', nombre: 'Ret. alquileres', periodicidad: 'Trimestral', quien: 'Con alquiler', categoria: 'automatico', descripcionCorta: 'Retenciones sobre alquileres' },
  { modelo: '180', nombre: 'Resumen ret. alq.', periodicidad: 'Anual', quien: 'Con alquiler', categoria: 'automatico', descripcionCorta: 'Resumen anual del 115' },
  { modelo: '130', nombre: 'Pago fracc. IRPF', periodicidad: 'Trimestral', quien: 'Autonomos directa', categoria: 'automatico', descripcionCorta: '20% del rendimiento neto trimestral' },
  { modelo: '131', nombre: 'IRPF modulos', periodicidad: 'Trimestral', quien: 'Autonomos objetiva', categoria: 'automatico', descripcionCorta: 'Cuotas segun indices de actividad' },
  { modelo: '347', nombre: 'Operaciones terceros', periodicidad: 'Anual', quien: 'Todos >3.005 EUR', categoria: 'automatico', descripcionCorta: 'Operaciones >3.005,06 EUR con mismo tercero' },
  { modelo: '349', nombre: 'Intracomunitarias', periodicidad: 'Trimestral', quien: 'Intra-UE', categoria: 'automatico', descripcionCorta: 'Operaciones intracomunitarias' },
  { modelo: '200', nombre: 'Impuesto Sociedades', periodicidad: 'Anual', quien: 'S.L. / S.A.', categoria: 'semi', descripcionCorta: 'SPICE pre-rellena resultado contable. Gestor completa ajustes extracontables.' },
  { modelo: '202', nombre: 'Pago fracc. IS', periodicidad: 'Trimestral', quien: 'S.L. / S.A.', categoria: 'semi', descripcionCorta: '18% del ultimo IS. SPICE calcula, gestor valida.' },
  { modelo: 'CC.AA.', nombre: 'Cuentas anuales', periodicidad: 'Anual', quien: 'Juridicas', categoria: 'semi', descripcionCorta: 'Balance, PyG, memoria basica auto. Informe gestion manual.' },
  { modelo: '100', nombre: 'IRPF', periodicidad: 'Anual', quien: 'Personas fisicas', categoria: 'asistido', descripcionCorta: 'SPICE aporta rendimientos actividad economica. Gestor completa en Renta Web.' },
]
