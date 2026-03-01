import { useParams, Link } from 'react-router-dom'
import { useSesionDetalle } from './api'
import type { FalloTest, CoberturaMod } from './types'

export default function SesionDetallePage() {
  const { id } = useParams<{ id: string }>()
  const { data: sesion, isLoading } = useSesionDetalle(Number(id))

  if (isLoading) return <div className="p-8 text-slate-400">Cargando...</div>
  if (!sesion) return <div className="p-8 text-red-400">Sesion no encontrada</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/salud" className="text-slate-400 hover:text-amber-400">&larr; Salud</Link>
        <h1 className="text-xl font-bold text-amber-400">
          Sesion #{sesion.id} &mdash; {sesion.fecha.slice(0, 19).replace('T', ' ')}
        </h1>
      </div>

      <div className="flex flex-wrap gap-3 text-sm text-slate-400">
        <span>Rama: <span className="text-slate-200 font-mono">{sesion.rama_git}</span></span>
        <span>Commit: <span className="text-slate-200 font-mono">{sesion.commit_hash}</span></span>
        <span>Duracion: <span className="text-slate-200">{sesion.duracion_seg.toFixed(1)}s</span></span>
      </div>

      <div className="flex flex-wrap gap-4">
        {[
          { label: 'Pasados', value: sesion.tests_pass, color: '#4ade80' },
          { label: 'Fallidos', value: sesion.tests_fail, color: sesion.tests_fail > 0 ? '#f87171' : '#4ade80' },
          { label: 'Cobertura', value: `${sesion.cobertura_pct.toFixed(1)}%`, color: '#f59e0b' },
        ].map(k => (
          <div key={k.label} className="bg-slate-800 rounded-lg p-4 text-center min-w-[120px]">
            <div className="text-2xl font-bold" style={{ color: k.color }}>{k.value}</div>
            <div className="text-slate-400 text-sm mt-1">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="bg-slate-800 rounded-lg p-4">
        <h2 className="text-slate-300 font-semibold mb-3">Fallos ({sesion.fallos.length})</h2>
        {sesion.fallos.length === 0
          ? <p className="text-slate-500 text-sm">Sin fallos</p>
          : sesion.fallos.map((f: FalloTest) => (
            <details key={f.id} className="mb-2 border border-slate-700 rounded">
              <summary className="p-3 cursor-pointer text-red-300 hover:bg-slate-700/40 text-sm">
                {f.nombre}
              </summary>
              <pre className="p-3 text-xs text-slate-400 overflow-auto max-h-40 bg-slate-900">
                {f.error_msg || 'Sin detalle'}
              </pre>
            </details>
          ))
        }
      </div>

      <div className="bg-slate-800 rounded-lg p-4">
        <h2 className="text-slate-300 font-semibold mb-3">Cobertura por modulo</h2>
        <div className="space-y-2">
          {sesion.cobertura.map((c: CoberturaMod) => (
            <div key={c.id} className="flex items-center gap-3">
              <span className="text-xs text-slate-400 font-mono w-64 truncate" title={c.modulo}>
                {c.modulo}
              </span>
              <div className="flex-1 bg-slate-700 rounded-full h-2">
                <div
                  className="h-2 rounded-full"
                  style={{
                    width: `${c.pct_cobertura}%`,
                    background: c.pct_cobertura >= 80 ? '#4ade80' : '#f87171',
                  }}
                />
              </div>
              <span
                className="text-xs w-12 text-right"
                style={{ color: c.pct_cobertura >= 80 ? '#4ade80' : '#f87171' }}
              >
                {c.pct_cobertura.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
