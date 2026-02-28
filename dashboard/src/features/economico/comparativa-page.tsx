// Pagina: Comparativa Interanual
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { ComparativaItem } from '@/types/economico'
import { economicoApi } from './api'

export default function ComparativaPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [items, setItems] = useState<ComparativaItem[]>([])
  const [ejercicios, setEjercicios] = useState<string[]>([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    setCargando(true)
    economicoApi.comparativa(empresaId)
      .then((d) => { setItems(d.comparativa); setEjercicios(d.ejercicios) })
      .catch(() => {})
      .finally(() => setCargando(false))
  }, [empresaId])

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1100 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Comparativa Interanual</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>
          {ejercicios.length > 0 ? `Ejercicios: ${ejercicios.join(' vs ')}` : 'Evolucion de metricas clave'}
        </p>
      </div>
      {cargando && <p style={{ color: '#9ca3af' }}>Cargando comparativa...</p>}
      {items.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ padding: '10px 12px', textAlign: 'left', color: '#6b7280', fontWeight: 600, fontSize: 12 }}>Concepto</th>
                {ejercicios.map((ej) => (
                  <th key={ej} style={{ padding: '10px 12px', textAlign: 'right', color: '#6b7280', fontWeight: 600, fontSize: 12 }}>{ej}</th>
                ))}
                <th style={{ padding: '10px 12px', textAlign: 'right', color: '#6b7280', fontWeight: 600, fontSize: 12 }}>Variacion</th>
                <th style={{ padding: '10px 12px', textAlign: 'right', color: '#6b7280', fontWeight: 600, fontSize: 12 }}>CAGR</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.concepto} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '12px', fontWeight: 600, color: '#1e293b' }}>{item.concepto}</td>
                  {ejercicios.map((ej) => (
                    <td key={ej} style={{ padding: '12px', textAlign: 'right' }}>
                      {(item.valores[ej] ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                    </td>
                  ))}
                  <td style={{ padding: '12px', textAlign: 'right', color: (item.variacion ?? 0) >= 0 ? '#16a34a' : '#dc2626', fontWeight: 600 }}>
                    {item.variacion !== null ? `${item.variacion > 0 ? '+' : ''}${item.variacion.toFixed(1)}%` : '-'}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right', color: '#6b7280' }}>
                    {item.cagr !== null ? `${item.cagr > 0 ? '+' : ''}${item.cagr.toFixed(1)}%` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!cargando && items.length === 0 && (
        <p style={{ color: '#9ca3af', fontSize: 14 }}>Sin datos comparativos disponibles.</p>
      )}
    </div>
  )
}
