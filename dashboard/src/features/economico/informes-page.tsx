// Pagina: Informes PDF
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { PlantillaInforme } from '@/types/economico'
import { economicoApi } from './api'

export default function InformesPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [plantillas, setPlantillas] = useState<PlantillaInforme[]>([])
  const [seleccionada, setSeleccionada] = useState<string>('mensual')
  const [generando, setGenerando] = useState(false)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    economicoApi.plantillasInformes().then((d) => setPlantillas(d.plantillas)).catch(() => {}).finally(() => setCargando(false))
  }, [])

  const generar = () => {
    setGenerando(true)
    try { economicoApi.generarInforme(empresaId, seleccionada) } finally { setTimeout(() => setGenerando(false), 2000) }
  }

  const plantillaActiva = plantillas.find((p) => p.id === seleccionada)

  return (
    <div style={{ padding: '24px 32px', maxWidth: 900 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Informes PDF</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Genera informes financieros en PDF</p>
      </div>
      {cargando && <p style={{ color: '#9ca3af' }}>Cargando plantillas...</p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 14, marginBottom: 24 }}>
        {plantillas.map((p) => (
          <div key={p.id} onClick={() => setSeleccionada(p.id)}
            style={{ background: '#fff', border: `2px solid ${seleccionada === p.id ? '#1e293b' : '#e5e7eb'}`, borderRadius: 10, padding: '14px 16px', cursor: 'pointer' }}>
            <div style={{ fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>{p.nombre}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>{p.descripcion}</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {p.secciones.map((s) => (
                <span key={s} style={{ padding: '2px 8px', background: '#f3f4f6', borderRadius: 10, fontSize: 11, color: '#6b7280' }}>{s}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
      {plantillaActiva && (
        <div style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 10, padding: 20, marginBottom: 20 }}>
          <h3 style={{ margin: '0 0 8px', color: '#1e293b' }}>{plantillaActiva.nombre}</h3>
          <p style={{ color: '#6b7280', fontSize: 14, margin: '0 0 12px' }}>{plantillaActiva.descripcion}</p>
          <p style={{ fontSize: 12, color: '#9ca3af', margin: 0 }}>Periodicidad: {plantillaActiva.periodicidad}</p>
        </div>
      )}
      <button onClick={generar} disabled={generando || !seleccionada}
        style={{ padding: '10px 28px', background: '#1e293b', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 15, fontWeight: 600 }}>
        {generando ? 'Generando...' : 'Generar y Descargar PDF'}
      </button>
    </div>
  )
}
