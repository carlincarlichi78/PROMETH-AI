// Pagina: KPIs Sectoriales
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { KPI } from '@/types/economico'
import { economicoApi } from './api'

const SEMAFORO_TEXT: Record<string, string> = { verde: '#16a34a', amarillo: '#ca8a04', rojo: '#dc2626' }

function KPICard({ kpi }: { kpi: KPI }) {
  const progreso = kpi.objetivo ? Math.min((kpi.valor / kpi.objetivo) * 100, 100) : null
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '16px 20px', minWidth: 220 }}>
      <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 6 }}>{kpi.nombre}</div>
      <div style={{ fontSize: 26, fontWeight: 700, color: SEMAFORO_TEXT[kpi.semaforo] ?? '#1e293b' }}>
        {kpi.unidad === 'euros'
          ? `${kpi.valor.toLocaleString('es-ES', { maximumFractionDigits: 0 })} €`
          : `${kpi.valor.toLocaleString('es-ES', { maximumFractionDigits: 2 })} ${kpi.unidad === 'porcentaje' ? '%' : kpi.unidad}`}
      </div>
      {kpi.objetivo !== null && progreso !== null && (
        <div style={{ marginTop: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#9ca3af', marginBottom: 3 }}>
            <span>Objetivo: {kpi.objetivo} {kpi.unidad === 'porcentaje' ? '%' : kpi.unidad}</span>
            <span>{progreso.toFixed(0)}%</span>
          </div>
          <div style={{ height: 4, background: '#f3f4f6', borderRadius: 2 }}>
            <div style={{ height: '100%', borderRadius: 2, background: SEMAFORO_TEXT[kpi.semaforo], width: `${progreso}%` }} />
          </div>
        </div>
      )}
    </div>
  )
}

export default function KPIsPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [kpis, setKpis] = useState<KPI[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setCargando(true)
    economicoApi.kpis(empresaId).then((d) => setKpis(d.kpis)).catch((e: Error) => setError(e.message)).finally(() => setCargando(false))
  }, [empresaId])

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1200 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>KPIs Sectoriales</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Indicadores clave del ejercicio activo</p>
      </div>
      {cargando && <p style={{ color: '#9ca3af' }}>Cargando KPIs...</p>}
      {error && <p style={{ color: '#dc2626' }}>Error: {error}</p>}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {kpis.map((kpi) => <KPICard key={kpi.nombre} kpi={kpi} />)}
      </div>
      {!cargando && kpis.length === 0 && !error && <p style={{ color: '#9ca3af', fontSize: 14 }}>Sin datos de KPIs en este ejercicio.</p>}
    </div>
  )
}
