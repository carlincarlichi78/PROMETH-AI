export interface Territorio {
  id: string
  nombre: string
  impuesto: string
  tipos: { nombre: string; pct: number }[]
  is: string
  color: string
  modelos: string
}

export const territorios: Territorio[] = [
  {
    id: 'peninsula',
    nombre: 'Peninsula + Baleares',
    impuesto: 'IVA',
    tipos: [
      { nombre: 'General', pct: 21 },
      { nombre: 'Reducido', pct: 10 },
      { nombre: 'Superreducido', pct: 4 },
    ],
    is: '25% general / 23% pymes / 15% nueva creacion',
    color: '#10b981',
    modelos: '303, 390, 111, 130, 347',
  },
  {
    id: 'canarias',
    nombre: 'Canarias',
    impuesto: 'IGIC',
    tipos: [
      { nombre: 'General', pct: 7 },
      { nombre: 'Reducido', pct: 3 },
      { nombre: 'Tipo cero', pct: 0 },
      { nombre: 'Incrementado', pct: 9.5 },
      { nombre: 'Especial', pct: 15 },
    ],
    is: '25% general / 23% pymes / 15% nueva creacion',
    color: '#d4a017',
    modelos: '420 (equiv. 303), 390, 347',
  },
  {
    id: 'ceuta',
    nombre: 'Ceuta y Melilla',
    impuesto: 'IPSI',
    tipos: [
      { nombre: 'Tipo 1', pct: 0.5 },
      { nombre: 'Tipo 4', pct: 4 },
      { nombre: 'Tipo 8', pct: 8 },
      { nombre: 'Tipo 10', pct: 10 },
    ],
    is: '25% con bonificacion 50%',
    color: '#06b6d4',
    modelos: 'IPSI propio, 347',
  },
  {
    id: 'navarra',
    nombre: 'Navarra',
    impuesto: 'IVA (foral)',
    tipos: [
      { nombre: 'General', pct: 21 },
      { nombre: 'Reducido', pct: 10 },
      { nombre: 'Superreducido', pct: 4 },
    ],
    is: '28% general / 23% pequena / 20% micro',
    color: '#8b5cf6',
    modelos: '303 foral, 390, 347',
  },
  {
    id: 'pais_vasco',
    nombre: 'Pais Vasco',
    impuesto: 'IVA (foral)',
    tipos: [
      { nombre: 'General', pct: 21 },
      { nombre: 'Reducido', pct: 10 },
      { nombre: 'Superreducido', pct: 4 },
    ],
    is: '24% general / 22% pequena / 20% micro',
    color: '#f97316',
    modelos: '303 foral, 390, 347',
  },
]
