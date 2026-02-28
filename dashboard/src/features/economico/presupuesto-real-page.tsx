// Pagina: Presupuesto vs Real
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { PresupuestoLinea } from '@/types/economico'
import { economicoApi } from './api'

const SEMAFORO_TEXT: Record<string, string> = { verde: '#16a34a', amarillo: '#ca8a04', rojo: '#dc2626' }
const SEMAFORO_BG: Record<string, string> = { verde: '#dcfce7', amarillo: '#fef9c3', rojo: '#fee2e2' }

export default function PresupuestoRealPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [lineas, setLineas] = useState<PresupuestoLinea[]>([])
  const [ejercicio, setEjercicio] = useState<string>('')
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    setCargando(true)
    economicoApi.presupuesto(empresaId)
      .then((d) => { setLineas(d.lineas); setEjercicio(d.ejercicio) })
      .catch(() => {})
      .finally(() => setCargando(false))
  }, [empresaId])

  const totalPres = lineas.reduce((s, l) => s + l.presupuestado, 0)
  const totalReal = lineas.reduce((s, l) => s + l.real, 0)
  const desvTotal = totalReal - totalPres
  const desvPct = totalPres !== 0 ? (desvTotal / totalPres * 100) : 0

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1100 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Presupuesto vs Real</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Ejercicio {ejercicio} — Desviacion por partida contable</p>
      </div>

      {cargando && <p style={{ color: '#9ca3af' }}>Cargando presupuesto...</p>}

      {!cargando && lineas.length === 0 && (
        <div style={{ padding: 32, background: '#f8fafc', borderRadius: 10, textAlign: 'center', color: '#6b7280' }}>
          <p>No hay presupuestos configurados para este ejercicio.</p>
          <p style={{ fontSize: 13 }}>Los presupuestos se crean desde la API POST /api/economico/{'{empresaId}'}/presupuesto</p>
        </div>
      )}

      {lineas.length > 0 && (
        <>
          {/* Resumen */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
            {[
              { label: 'Total Presupuestado', valor: totalPres },
              { label: 'Total Real', valor: totalReal },
              { label: 'Desviacion', valor: desvTotal, pct: desvPct },
            ].map(({ label, valor, pct }) => (
              <div key={label} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '14px 20px', minWidth: 200 }}>
                <div style={{ fontSize: 13, color: '#6b7280' }}>{label}</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: (valor ?? 0) < 0 ? '#dc2626' : '#1e293b' }}>
                  {(valor ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                </div>
                {pct !== undefined && (
                  <div style={{ fontSize: 12, color: Math.abs(pct) <= 10 ? '#16a34a' : '#dc2626' }}>
                    {pct > 0 ? '+' : ''}{pct.toFixed(1)}%
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Tabla */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  {['Subcuenta', 'Descripcion', 'Presupuestado', 'Real', 'Desviacion', 'Estado'].map((h) => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: '#6b7280', fontWeight: 600, fontSize: 12 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {lineas.map((l) => (
                  <tr key={l.subcuenta} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#6b7280' }}>{l.subcuenta}</td>
                    <td style={{ padding: '10px 12px' }}>{l.descripcion}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'right' }}>{l.presupuestado.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'right' }}>{l.real.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', color: l.desviacion >= 0 ? '#16a34a' : '#dc2626' }}>
                      {l.desviacion > 0 ? '+' : ''}{l.desviacion.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                      <span style={{ fontSize: 11, marginLeft: 4, color: '#9ca3af' }}>({l.desviacion_pct > 0 ? '+' : ''}{l.desviacion_pct.toFixed(1)}%)</span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ padding: '2px 10px', borderRadius: 12, background: SEMAFORO_BG[l.semaforo], color: SEMAFORO_TEXT[l.semaforo], fontSize: 11, fontWeight: 600 }}>
                        {l.semaforo}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
