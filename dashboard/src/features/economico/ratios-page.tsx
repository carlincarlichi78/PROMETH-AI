// Pagina: Ratios Financieros (modulo economico)
// Importa componentes de Stream A — disponibles tras merge

import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { RatiosEmpresa, Ratio } from '@/types/economico'
import { economicoApi } from './api'

// NOTE: Los siguientes componentes son de Stream A.
// Mientras Stream A no se haya ejecutado, esta pagina usa implementacion inline.
// Tras el merge, se puede sustituir por los componentes compartidos.

const CATEGORIAS = ['liquidez', 'solvencia', 'rentabilidad', 'eficiencia', 'estructura'] as const

const SEMAFORO_BG: Record<string, string> = {
  verde: '#dcfce7', amarillo: '#fef9c3', rojo: '#fee2e2',
}
const SEMAFORO_TEXT: Record<string, string> = {
  verde: '#16a34a', amarillo: '#ca8a04', rojo: '#dc2626',
}

function Badge({ semaforo }: { semaforo: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: 12,
      background: SEMAFORO_BG[semaforo] ?? '#f3f4f6',
      color: SEMAFORO_TEXT[semaforo] ?? '#6b7280',
      fontSize: 11, fontWeight: 600, textTransform: 'capitalize',
    }}>
      {semaforo}
    </span>
  )
}

function RatioCard({ ratio }: { ratio: Ratio }) {
  return (
    <div style={{
      border: `1.5px solid ${SEMAFORO_TEXT[ratio.semaforo] ?? '#e5e7eb'}`,
      borderRadius: 10, padding: '14px 18px', background: '#fff', minWidth: 200,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontSize: 13, color: '#6b7280', fontWeight: 500 }}>{ratio.nombre}</span>
        <Badge semaforo={ratio.semaforo} />
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: SEMAFORO_TEXT[ratio.semaforo] ?? '#1e293b' }}>
        {ratio.valor.toLocaleString('es-ES', { maximumFractionDigits: 2 })}
        <span style={{ fontSize: 13, fontWeight: 400, color: '#9ca3af', marginLeft: 4 }}>{ratio.unidad}</span>
      </div>
      {ratio.benchmark !== null && (
        <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>
          Benchmark sectorial: {ratio.benchmark} {ratio.unidad}
        </div>
      )}
      {ratio.explicacion && (
        <div style={{ fontSize: 11, color: '#6b7280', marginTop: 8, lineHeight: 1.4 }}>
          {ratio.explicacion}
        </div>
      )}
    </div>
  )
}

export default function RatiosPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [datos, setDatos] = useState<RatiosEmpresa | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [categoria, setCategoria] = useState<string>('liquidez')

  useEffect(() => {
    setCargando(true)
    setError(null)
    economicoApi.ratios(empresaId)
      .then(setDatos)
      .catch((e: Error) => setError(e.message))
      .finally(() => setCargando(false))
  }, [empresaId])

  if (cargando) {
    return (
      <div style={{ padding: 32 }}>
        <div style={{ height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ height: '100%', background: '#1e293b', width: '60%', borderRadius: 3, animation: 'none' }} />
        </div>
        <p style={{ color: '#9ca3af', marginTop: 12 }}>Calculando ratios financieros...</p>
      </div>
    )
  }
  if (error) {
    return (
      <div style={{ padding: 32, color: '#dc2626' }}>
        <strong>Error al cargar ratios:</strong> {error}
      </div>
    )
  }
  if (!datos) return null

  const ratiosFiltrados = datos.ratios.filter((r) => r.categoria === categoria)
  const totalVerde = datos.ratios.filter((r) => r.semaforo === 'verde').length
  const totalAmarillo = datos.ratios.filter((r) => r.semaforo === 'amarillo').length
  const totalRojo = datos.ratios.filter((r) => r.semaforo === 'rojo').length

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Ratios Financieros</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>
          Calculados a {new Date(datos.fecha_calculo).toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' })}
        </p>
      </div>

      {/* Semaforo resumen */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 28 }}>
        {[
          { label: 'Positivos', value: totalVerde, semaforo: 'verde' },
          { label: 'Atencion', value: totalAmarillo, semaforo: 'amarillo' },
          { label: 'Criticos', value: totalRojo, semaforo: 'rojo' },
        ].map(({ label, value, semaforo }) => (
          <div key={semaforo} style={{
            padding: '10px 22px', borderRadius: 10,
            background: SEMAFORO_BG[semaforo],
            border: `1px solid ${SEMAFORO_TEXT[semaforo]}20`,
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: SEMAFORO_TEXT[semaforo] }}>{value}</div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Tabs categoria */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 24, borderBottom: '1px solid #e5e7eb', paddingBottom: 0 }}>
        {CATEGORIAS.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategoria(cat)}
            style={{
              padding: '8px 18px', border: 'none', background: 'none', cursor: 'pointer',
              borderBottom: categoria === cat ? '2px solid #1e293b' : '2px solid transparent',
              color: categoria === cat ? '#1e293b' : '#6b7280',
              fontWeight: categoria === cat ? 600 : 400,
              fontSize: 14, textTransform: 'capitalize', transition: 'all 0.15s',
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Grid ratios */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        {ratiosFiltrados.length === 0 ? (
          <p style={{ color: '#9ca3af', fontSize: 14 }}>Sin datos para esta categoría en el ejercicio activo.</p>
        ) : (
          ratiosFiltrados.map((r) => <RatioCard key={r.nombre} ratio={r} />)
        )}
      </div>
    </div>
  )
}
