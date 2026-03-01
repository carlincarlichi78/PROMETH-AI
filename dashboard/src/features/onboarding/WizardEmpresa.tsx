import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Paso1DatosBasicos } from './pasos/Paso1DatosBasicos'
import { Paso2PerfilNegocio } from './pasos/Paso2PerfilNegocio'
import { Paso3Proveedores } from './pasos/Paso3Proveedores'
import { Paso4FacturaScripts } from './pasos/Paso4FacturaScripts'
import { Paso5Fuentes } from './pasos/Paso5Fuentes'

const PASOS = [
  'Datos básicos',
  'Perfil de negocio',
  'Proveedores habituales',
  'FacturaScripts',
  'Fuentes de documentos',
]

export function WizardEmpresa() {
  const [paso, setPaso] = useState(0)
  const [empresaId, setEmpresaId] = useState<number | null>(null)
  const navigate = useNavigate()

  const avanzar = (nuevoEmpresaId?: number) => {
    if (nuevoEmpresaId !== undefined) setEmpresaId(nuevoEmpresaId)
    if (paso < PASOS.length - 1) {
      setPaso((p) => p + 1)
    } else {
      navigate(`/empresa/${empresaId}`)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Alta de empresa nueva</h1>
        <p className="text-sm text-muted-foreground">Completa los pasos para configurar la empresa en SFCE.</p>
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

      {/* Paso activo */}
      {paso === 0 && <Paso1DatosBasicos onAvanzar={(id) => avanzar(id)} />}
      {paso === 1 && empresaId !== null && (
        <Paso2PerfilNegocio empresaId={empresaId} onAvanzar={() => avanzar()} />
      )}
      {paso === 2 && empresaId !== null && (
        <Paso3Proveedores empresaId={empresaId} onAvanzar={() => avanzar()} />
      )}
      {paso === 3 && empresaId !== null && (
        <Paso4FacturaScripts empresaId={empresaId} onAvanzar={() => avanzar()} />
      )}
      {paso === 4 && empresaId !== null && (
        <Paso5Fuentes empresaId={empresaId} onAvanzar={() => avanzar()} />
      )}
    </div>
  )
}
