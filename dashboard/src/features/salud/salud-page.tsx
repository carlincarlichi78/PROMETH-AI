import { Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { useSesiones, useTendencias } from './api'
import { CHART_COLORS } from '@/components/ui/chart-wrapper'
import type { SesionSalud } from './types'

function KpiCard({ label, value, color = '#f59e0b' }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-slate-800 rounded-lg p-4 text-center min-w-[120px]">
      <div className="text-2xl font-bold" style={{ color }}>{value}</div>
      <div className="text-slate-400 text-sm mt-1">{label}</div>
    </div>
  )
}

function BadgeEstado({ estado }: { estado: string }) {
  const color = estado === 'completada' ? 'bg-green-900 text-green-300' : 'bg-yellow-900 text-yellow-300'
  return <span className={`px-2 py-0.5 rounded text-xs ${color}`}>{estado}</span>
}

export default function SaludPage() {
  const { data: sesiones = [], isLoading } = useSesiones()
  const { data: tendencias } = useTendencias()

  const ultima = sesiones[0]

  if (isLoading) return <div className="p-8 text-slate-400">Cargando...</div>

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-amber-400">Salud del Sistema</h1>

      {ultima && (
        <div className="flex flex-wrap gap-4">
          <KpiCard label="Cobertura global" value={`${ultima.cobertura_pct.toFixed(1)}%`} />
          <KpiCard label="Tests totales" value={ultima.tests_total} color="#60a5fa" />
          <KpiCard label="Fallos" value={ultima.tests_fail} color={ultima.tests_fail > 0 ? '#f87171' : '#4ade80'} />
          <KpiCard label="Ultimo run" value={ultima.fecha.slice(0, 10)} color="#94a3b8" />
        </div>
      )}

      {tendencias && tendencias.sesiones.length > 1 && (
        <div className="bg-slate-800 rounded-lg p-4">
          <h2 className="text-slate-300 font-semibold mb-3">Tendencias</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={tendencias.sesiones}>
              <XAxis dataKey="fecha" tickFormatter={(v: string) => v.slice(5, 10)} stroke="#64748b" />
              <YAxis stroke="#64748b" />
              <Tooltip contentStyle={{ background: '#1e293b', border: 'none' }} />
              <Legend />
              <Line type="monotone" dataKey="cobertura_pct" stroke={CHART_COLORS.primary} name="Cobertura %" dot={false} />
              <Line type="monotone" dataKey="tests_fail" stroke={CHART_COLORS.danger} name="Fallos" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="bg-slate-800 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-700 text-slate-300">
              <th className="p-3 text-left">Fecha</th>
              <th className="p-3 text-left">Rama</th>
              <th className="p-3 text-right">Tests</th>
              <th className="p-3 text-right">Fallos</th>
              <th className="p-3 text-right">Cobertura</th>
              <th className="p-3 text-left">Estado</th>
              <th className="p-3"></th>
            </tr>
          </thead>
          <tbody>
            {sesiones.map((s: SesionSalud) => (
              <tr key={s.id} className="border-t border-slate-700 hover:bg-slate-700/40">
                <td className="p-3 text-slate-300">{s.fecha.slice(0, 19).replace('T', ' ')}</td>
                <td className="p-3 text-slate-400 font-mono text-xs">{s.rama_git}</td>
                <td className="p-3 text-right text-slate-300">{s.tests_total}</td>
                <td className="p-3 text-right" style={{ color: s.tests_fail > 0 ? '#f87171' : '#4ade80' }}>
                  {s.tests_fail}
                </td>
                <td className="p-3 text-right" style={{ color: s.cobertura_pct >= 80 ? '#4ade80' : '#f87171' }}>
                  {s.cobertura_pct.toFixed(1)}%
                </td>
                <td className="p-3"><BadgeEstado estado={s.estado} /></td>
                <td className="p-3">
                  <Link to={`/salud/${s.id}`} className="text-amber-400 hover:underline text-xs">
                    Detalle &rarr;
                  </Link>
                </td>
              </tr>
            ))}
            {sesiones.length === 0 && (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-500">
                  Sin sesiones aun. Ejecuta /test-engine para empezar.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
