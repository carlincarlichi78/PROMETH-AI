/** Datos de un plazo fiscal */
interface PlazoFiscal {
  modelo: string
  nombre: string
  inicio: string
  fin: string
  trimestre: number | null
  anual: boolean
}

/** Plazos fiscales de Espana */
const PLAZOS: PlazoFiscal[] = [
  // Trimestrales
  { modelo: '303', nombre: 'IVA trimestral', inicio: '01/04', fin: '20/04', trimestre: 1, anual: false },
  { modelo: '303', nombre: 'IVA trimestral', inicio: '01/07', fin: '20/07', trimestre: 2, anual: false },
  { modelo: '303', nombre: 'IVA trimestral', inicio: '01/10', fin: '20/10', trimestre: 3, anual: false },
  { modelo: '303', nombre: 'IVA trimestral', inicio: '01/01', fin: '30/01', trimestre: 4, anual: false },
  { modelo: '111', nombre: 'Retenciones IRPF', inicio: '01/04', fin: '20/04', trimestre: 1, anual: false },
  { modelo: '111', nombre: 'Retenciones IRPF', inicio: '01/07', fin: '20/07', trimestre: 2, anual: false },
  { modelo: '111', nombre: 'Retenciones IRPF', inicio: '01/10', fin: '20/10', trimestre: 3, anual: false },
  { modelo: '111', nombre: 'Retenciones IRPF', inicio: '01/01', fin: '30/01', trimestre: 4, anual: false },
  { modelo: '130', nombre: 'Pago fraccionado IRPF', inicio: '01/04', fin: '20/04', trimestre: 1, anual: false },
  { modelo: '130', nombre: 'Pago fraccionado IRPF', inicio: '01/07', fin: '20/07', trimestre: 2, anual: false },
  { modelo: '130', nombre: 'Pago fraccionado IRPF', inicio: '01/10', fin: '20/10', trimestre: 3, anual: false },
  { modelo: '130', nombre: 'Pago fraccionado IRPF', inicio: '01/01', fin: '30/01', trimestre: 4, anual: false },
  // Anuales
  { modelo: '390', nombre: 'Resumen anual IVA', inicio: '01/01', fin: '30/01', trimestre: null, anual: true },
  { modelo: '190', nombre: 'Resumen anual retenciones', inicio: '01/01', fin: '30/01', trimestre: null, anual: true },
  { modelo: '347', nombre: 'Operaciones con terceros', inicio: '01/02', fin: '28/02', trimestre: null, anual: true },
  { modelo: '200', nombre: 'Impuesto Sociedades', inicio: '01/07', fin: '25/07', trimestre: null, anual: true },
  { modelo: '100', nombre: 'IRPF anual', inicio: '01/04', fin: '30/06', trimestre: null, anual: true },
]

/**
 * Calendario Fiscal — plazos trimestrales y anuales.
 * Muestra tarjetas por trimestre con codigo de colores.
 */
export function Calendario() {
  const anoActual = new Date().getFullYear()
  const hoy = new Date()

  /** Parsea fecha dd/mm al ano actual y retorna Date */
  const parsearFecha = (ddmm: string): Date => {
    const [dia, mes] = ddmm.split('/')
    return new Date(anoActual, Number(mes) - 1, Number(dia))
  }

  /** Determina el estado del plazo segun la fecha actual */
  const estadoPlazo = (plazo: PlazoFiscal): 'proximo' | 'pasado' | 'vencido' => {
    const inicio = parsearFecha(plazo.inicio)
    const fin = parsearFecha(plazo.fin)

    if (hoy > fin) {
      return 'pasado'
    }
    if (hoy >= inicio && hoy <= fin) {
      return 'proximo'
    }
    // Plazo futuro — calcular si esta dentro de 30 dias
    const diasHastaInicio = Math.ceil((inicio.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24))
    if (diasHastaInicio <= 30) {
      return 'proximo'
    }
    return 'pasado' // Futuro lejano — se muestra como pasado (verde = OK)
  }

  /** Colores segun estado */
  const colorEstado = (estado: 'proximo' | 'pasado' | 'vencido'): string => {
    switch (estado) {
      case 'proximo':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      case 'pasado':
        return 'bg-green-50 border-green-200 text-green-700'
      case 'vencido':
        return 'bg-red-50 border-red-200 text-red-700'
    }
  }

  /** Color del punto indicador */
  const colorPunto = (estado: 'proximo' | 'pasado' | 'vencido'): string => {
    switch (estado) {
      case 'proximo':
        return 'bg-yellow-400'
      case 'pasado':
        return 'bg-green-400'
      case 'vencido':
        return 'bg-red-400'
    }
  }

  /** Plazos trimestrales agrupados */
  const plazosPorTrimestre = (trimestre: number): PlazoFiscal[] => {
    return PLAZOS.filter((p) => p.trimestre === trimestre)
  }

  /** Plazos anuales a mostrar en un trimestre determinado */
  const plazosAnualesEnTrimestre = (trimestre: number): PlazoFiscal[] => {
    return PLAZOS.filter((p) => {
      if (!p.anual) return false
      // Mostrar en el trimestre correspondiente a la fecha de inicio
      const mes = Number(p.inicio.split('/')[1])
      if (trimestre === 1 && mes >= 1 && mes <= 3) return true
      if (trimestre === 2 && mes >= 4 && mes <= 6) return true
      if (trimestre === 3 && mes >= 7 && mes <= 9) return true
      if (trimestre === 4 && mes >= 10 && mes <= 12) return true
      return false
    })
  }

  /** Nombre del trimestre */
  const nombreTrimestre = (t: number): string => {
    const periodos: Record<number, string> = {
      1: 'Enero - Marzo',
      2: 'Abril - Junio',
      3: 'Julio - Septiembre',
      4: 'Octubre - Diciembre',
    }
    return periodos[t] ?? ''
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Calendario Fiscal</h1>
        <p className="text-sm text-gray-500 mt-1">Plazos de presentacion {anoActual}</p>
      </div>

      {/* Leyenda */}
      <div className="flex gap-6 mb-6 text-xs text-gray-600">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-green-400" />
          Presentado / futuro
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-yellow-400" />
          Proximo / en plazo
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-400" />
          Vencido
        </div>
      </div>

      {/* Tarjetas por trimestre */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[1, 2, 3, 4].map((trimestre) => {
          const trimestrales = plazosPorTrimestre(trimestre)
          const anuales = plazosAnualesEnTrimestre(trimestre)
          const todosPlazos = [...trimestrales, ...anuales]

          return (
            <div key={trimestre} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">T{trimestre}</h2>
                <span className="text-sm text-gray-400">{nombreTrimestre(trimestre)}</span>
              </div>

              {todosPlazos.length === 0 ? (
                <p className="text-sm text-gray-400">Sin plazos en este trimestre</p>
              ) : (
                <div className="space-y-2">
                  {todosPlazos.map((plazo, idx) => {
                    const estado = estadoPlazo(plazo)
                    return (
                      <div
                        key={`${plazo.modelo}-${idx}`}
                        className={`flex items-center justify-between px-3 py-2 rounded-md border text-sm ${colorEstado(estado)}`}
                      >
                        <div className="flex items-center gap-2">
                          <span className={`inline-block w-2 h-2 rounded-full ${colorPunto(estado)}`} />
                          <span className="font-medium">Mod. {plazo.modelo}</span>
                          <span className="text-xs opacity-75">
                            {plazo.anual ? '(anual)' : ''}
                          </span>
                        </div>
                        <span className="text-xs font-mono">
                          {plazo.inicio} - {plazo.fin}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
