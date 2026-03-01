import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { PasoOC1DatosEmpresa } from './pasos/PasoOC1DatosEmpresa'
import { PasoOC2CuentaBancaria } from './pasos/PasoOC2CuentaBancaria'
import { PasoOC3Documentacion } from './pasos/PasoOC3Documentacion'

const PASOS = ['Datos empresa', 'Cuenta bancaria', 'Documentacion']

interface Props {
  empresaId: number
}

export function WizardOnboardingCliente({ empresaId }: Props) {
  const [paso, setPaso] = useState(0)
  const [datosAcumulados, setDatosAcumulados] = useState<Record<string, unknown>>({})
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: async (datos: Record<string, unknown>) => {
      const token = sessionStorage.getItem('sfce_token')
      const r = await fetch(`/api/onboarding/cliente/${empresaId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(datos),
      })
      if (!r.ok) throw new Error('Error al guardar los datos')
      return r.json()
    },
    onSuccess: () => navigate(`/portal/${empresaId}`),
  })

  const avanzarConDatos = (nuevosDatos: Record<string, unknown>) => {
    const acumulado = { ...datosAcumulados, ...nuevosDatos }
    setDatosAcumulados(acumulado)
    if (paso < PASOS.length - 1) {
      setPaso((p) => p + 1)
    } else {
      mutation.mutate(acumulado)
    }
  }

  return (
    <div className="max-w-lg mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Completa tu alta</h1>
        <p className="text-sm text-muted-foreground">
          Tu gestoria ha iniciado el proceso. Completa los datos que solo tu conoces.
        </p>
      </div>

      {/* Stepper */}
      <div className="flex gap-1 mb-8">
        {PASOS.map((nombre, i) => (
          <div
            key={i}
            className={`flex-1 text-center text-xs py-2 px-1 rounded transition-colors ${
              i === paso
                ? 'bg-primary text-primary-foreground font-medium'
                : i < paso
                  ? 'bg-green-500 text-white'
                  : 'bg-muted text-muted-foreground'
            }`}
          >
            <span className="font-semibold">{i + 1}.</span> {nombre}
          </div>
        ))}
      </div>

      {paso === 0 && <PasoOC1DatosEmpresa onAvanzar={avanzarConDatos} />}
      {paso === 1 && <PasoOC2CuentaBancaria onAvanzar={avanzarConDatos} />}
      {paso === 2 && <PasoOC3Documentacion onAvanzar={avanzarConDatos} />}

      {mutation.isError && (
        <p className="text-sm text-red-500 mt-4 text-center">Error al guardar. Intentalo de nuevo.</p>
      )}
    </div>
  )
}

/** Wrapper con useParams para usar en el router */
export function WizardOnboardingClienteWrapper() {
  const { id } = useParams<{ id: string }>()
  return <WizardOnboardingCliente empresaId={Number(id) || 0} />
}
