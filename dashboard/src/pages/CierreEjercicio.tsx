import { useState } from 'react'

/** Estado posible de un paso del cierre */
type EstadoPaso = 'pendiente' | 'completado' | 'no_aplica'

/** Definicion de un paso del cierre */
interface PasoCierre {
  numero: number
  titulo: string
  descripcion: string
  estado: EstadoPaso
}

/** Los 10 pasos del cierre de ejercicio */
const PASOS_INICIALES: PasoCierre[] = [
  {
    numero: 1,
    titulo: 'Amortizaciones pendientes',
    descripcion: 'Registrar las dotaciones de amortizacion del inmovilizado material e inmaterial correspondientes al ejercicio.',
    estado: 'pendiente',
  },
  {
    numero: 2,
    titulo: 'Regularizacion de existencias',
    descripcion: 'Ajustar las cuentas de existencias (grupo 3) con el inventario final del ejercicio.',
    estado: 'pendiente',
  },
  {
    numero: 3,
    titulo: 'Provision clientes de dudoso cobro',
    descripcion: 'Dotar las provisiones por insolvencias de clientes (694/490) segun antigüedad de deuda.',
    estado: 'pendiente',
  },
  {
    numero: 4,
    titulo: 'Regularizacion prorrata definitiva',
    descripcion: 'Calcular la prorrata definitiva de IVA y ajustar el IVA soportado no deducible.',
    estado: 'pendiente',
  },
  {
    numero: 5,
    titulo: 'Regularizacion IVA bienes de inversion',
    descripcion: 'Revisar y ajustar las regularizaciones de IVA en bienes de inversion adquiridos en los ultimos 5/10 anos.',
    estado: 'pendiente',
  },
  {
    numero: 6,
    titulo: 'Periodificaciones',
    descripcion: 'Registrar ingresos y gastos anticipados, y periodificar los que corresponden a ejercicios distintos.',
    estado: 'pendiente',
  },
  {
    numero: 7,
    titulo: 'Gasto Impuesto de Sociedades',
    descripcion: 'Calcular y contabilizar el gasto por Impuesto de Sociedades (cuenta 630) con las diferencias temporarias y permanentes.',
    estado: 'pendiente',
  },
  {
    numero: 8,
    titulo: 'Asiento de REGULARIZACION',
    descripcion: 'Saldar cuentas de gastos (grupo 6) e ingresos (grupo 7) contra la cuenta 129 (Resultado del ejercicio).',
    estado: 'pendiente',
  },
  {
    numero: 9,
    titulo: 'Asiento de CIERRE',
    descripcion: 'Saldar todas las cuentas del balance dejando todos los saldos a cero.',
    estado: 'pendiente',
  },
  {
    numero: 10,
    titulo: 'Asiento de APERTURA',
    descripcion: 'Crear el asiento de apertura del siguiente ejercicio con los saldos del balance.',
    estado: 'pendiente',
  },
]

/**
 * Cierre de Ejercicio — wizard con checklist de 10 pasos.
 * Cada paso tiene un checkbox, descripcion y boton de ejecucion.
 */
export function CierreEjercicio() {
  const [pasos, setPasos] = useState<PasoCierre[]>(PASOS_INICIALES)

  /** Cuenta de pasos completados */
  const completados = pasos.filter((p) => p.estado === 'completado').length
  const aplicables = pasos.filter((p) => p.estado !== 'no_aplica').length
  const porcentaje = aplicables > 0 ? Math.round((completados / aplicables) * 100) : 0

  /** Cambia el estado de un paso */
  const cambiarEstado = (numero: number, nuevoEstado: EstadoPaso) => {
    setPasos((prev) =>
      prev.map((p) =>
        p.numero === numero ? { ...p, estado: nuevoEstado } : p
      )
    )
  }

  /** Cicla entre estados al hacer clic en el checkbox */
  const ciclarEstado = (paso: PasoCierre) => {
    const siguiente: Record<EstadoPaso, EstadoPaso> = {
      pendiente: 'completado',
      completado: 'no_aplica',
      no_aplica: 'pendiente',
    }
    cambiarEstado(paso.numero, siguiente[paso.estado])
  }

  /** Ejecutar paso (placeholder) */
  const ejecutarPaso = (paso: PasoCierre) => {
    alert(
      `Se ejecutaria: "${paso.titulo}"\n\n` +
      'Esta funcionalidad generara los asientos correspondientes automaticamente en una version futura.'
    )
  }

  /** Estilos del badge de estado */
  const estiloBadge = (estado: EstadoPaso): string => {
    switch (estado) {
      case 'pendiente':
        return 'bg-gray-100 text-gray-600'
      case 'completado':
        return 'bg-green-100 text-green-700'
      case 'no_aplica':
        return 'bg-gray-50 text-gray-400'
    }
  }

  /** Texto del badge de estado */
  const textoBadge = (estado: EstadoPaso): string => {
    switch (estado) {
      case 'pendiente':
        return 'Pendiente'
      case 'completado':
        return 'Completado'
      case 'no_aplica':
        return 'No aplica'
    }
  }

  /** Estilo del checkbox visual */
  const estiloCheckbox = (estado: EstadoPaso): string => {
    switch (estado) {
      case 'pendiente':
        return 'border-gray-300 bg-white'
      case 'completado':
        return 'border-green-500 bg-green-500'
      case 'no_aplica':
        return 'border-gray-200 bg-gray-100'
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Cierre de Ejercicio</h1>
        <p className="text-sm text-gray-500 mt-1">
          Checklist de 10 pasos para cerrar la contabilidad del ejercicio
        </p>
      </div>

      {/* Barra de progreso */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-600">
            Progreso: {completados} de {aplicables} pasos completados
          </span>
          <span className="text-sm font-medium text-blue-600">{porcentaje}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
            style={{ width: `${porcentaje}%` }}
          />
        </div>
      </div>

      {/* Lista de pasos */}
      <div className="space-y-3">
        {pasos.map((paso) => (
          <div
            key={paso.numero}
            className={`bg-white rounded-lg shadow p-5 transition-opacity ${
              paso.estado === 'no_aplica' ? 'opacity-50' : ''
            }`}
          >
            <div className="flex items-start gap-4">
              {/* Checkbox visual */}
              <button
                onClick={() => ciclarEstado(paso)}
                className={`mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${estiloCheckbox(paso.estado)}`}
                title="Clic para cambiar estado: pendiente / completado / no aplica"
              >
                {paso.estado === 'completado' && (
                  <span className="text-white text-xs font-bold">{'\u2713'}</span>
                )}
                {paso.estado === 'no_aplica' && (
                  <span className="text-gray-400 text-xs">-</span>
                )}
              </button>

              {/* Contenido */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-xs text-gray-400 font-mono">#{paso.numero}</span>
                  <h3
                    className={`text-sm font-semibold ${
                      paso.estado === 'no_aplica'
                        ? 'text-gray-400 line-through'
                        : paso.estado === 'completado'
                          ? 'text-green-700'
                          : 'text-gray-800'
                    }`}
                  >
                    {paso.titulo}
                  </h3>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${estiloBadge(paso.estado)}`}
                  >
                    {textoBadge(paso.estado)}
                  </span>
                </div>
                <p className="text-sm text-gray-500">{paso.descripcion}</p>
              </div>

              {/* Boton de ejecucion */}
              <button
                onClick={() => ejecutarPaso(paso)}
                disabled={paso.estado !== 'pendiente'}
                className="px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-md hover:bg-blue-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
              >
                Ejecutar paso
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
