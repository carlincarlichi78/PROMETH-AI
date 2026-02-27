// Pagina: Credit Scoring
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { ScoringEmpresa } from '@/types/economico'
import { economicoApi } from './api'

function ScoreBadge({ puntuacion }: { puntuacion: number }) {
  const color = puntuacion >= 70 ? '#16a34a' : puntuacion >= 40 ? '#ca8a04' : '#dc2626'
  const bg = puntuacion >= 70 ? '#dcfce7' : puntuacion >= 40 ? '#fef9c3' : '#fee2e2'
  return (
    <div style={{ width: 40, height: 40, borderRadius: '50%', background: bg, border: `2px solid ${color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 13, color }}>
      {puntuacion}
    </div>
  )
}

export default function ScoringPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [tipo, setTipo] = useState<'proveedor' | 'cliente'>('proveedor')
  const [datos, setDatos] = useState<ScoringEmpresa | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    setCargando(true)
    economicoApi.scoring(empresaId, tipo).then(setDatos).catch(() => {}).finally(() => setCargando(false))
  }, [empresaId, tipo])

  return (
    <div style={{ padding: '24px 32px', maxWidth: 900 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Credit Scoring</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Puntuacion de solvencia de clientes y proveedores</p>
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {(['proveedor', 'cliente'] as const).map((t) => (
          <button key={t} onClick={() => setTipo(t)}
            style={{ padding: '6px 18px', borderRadius: 20, border: '1px solid #e5e7eb', background: tipo === t ? '#1e293b' : '#fff', color: tipo === t ? '#fff' : '#374151', cursor: 'pointer', textTransform: 'capitalize', fontWeight: tipo === t ? 600 : 400 }}>
            {t === 'proveedor' ? 'Proveedores' : 'Clientes'}
          </button>
        ))}
      </div>
      {cargando && <p style={{ color: '#9ca3af' }}>Calculando scoring...</p>}
      {datos && datos.scoring.length === 0 && !cargando && (
        <p style={{ color: '#9ca3af', fontSize: 14 }}>Sin datos de scoring. Los scores se calculan con historial de pagos.</p>
      )}
      {datos && datos.scoring.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {datos.scoring.map((s) => (
            <div key={s.entidad_id} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: '12px 18px', display: 'flex', alignItems: 'center', gap: 16 }}>
              <ScoreBadge puntuacion={s.puntuacion} />
              <div style={{ flex: 1 }}>
                <span style={{ fontWeight: 600, color: '#1e293b' }}>Entidad #{s.entidad_id}</span>
                {s.fecha && <span style={{ fontSize: 12, color: '#9ca3af', marginLeft: 10 }}>{new Date(s.fecha).toLocaleDateString('es-ES')}</span>}
              </div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>
                {Object.entries(s.factores).map(([k, v]) => `${k}: ${v}`).join(' | ') || 'Sin factores'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
