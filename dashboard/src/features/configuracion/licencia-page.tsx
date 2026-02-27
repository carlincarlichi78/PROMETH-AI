// Configuracion: Licencia
import { useState, useEffect } from 'react'
import type { EstadoLicencia } from '@/types/config'

async function apiFetch<T>(url: string): Promise<T> {
  const token = localStorage.getItem('sfce_token')
  const res = await fetch(url, { headers: { Authorization: token ? `Bearer ${token}` : '' } })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export default function LicenciaPage() {
  const [licencia, setLicencia] = useState<EstadoLicencia | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    apiFetch<EstadoLicencia>('/api/config/licencia').then(setLicencia).catch(() => {}).finally(() => setCargando(false))
  }, [])

  return (
    <div style={{ padding: '24px 32px', maxWidth: 700 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Licencia</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Estado y limite del plan activo</p>
      </div>
      {cargando && <p style={{ color: '#9ca3af' }}>Cargando licencia...</p>}
      {licencia && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ background: '#1e293b', borderRadius: 12, padding: '20px 24px', color: '#fff' }}>
            <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 4 }}>Plan activo</div>
            <div style={{ fontSize: 24, fontWeight: 700, textTransform: 'capitalize' }}>{licencia.plan}</div>
            <div style={{ fontSize: 13, opacity: 0.7, marginTop: 4 }}>Version {licencia.version}</div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { label: 'Max Empresas', value: licencia.max_empresas },
              { label: 'Max Usuarios', value: licencia.max_usuarios },
              { label: 'Valido hasta', value: licencia.valida_hasta ?? 'Sin limite' },
              { label: 'Modulos', value: licencia.modulos.length },
            ].map(({ label, value }) => (
              <div key={label} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: '14px 18px' }}>
                <div style={{ fontSize: 12, color: '#6b7280' }}>{label}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#1e293b', marginTop: 2 }}>{value}</div>
              </div>
            ))}
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 8 }}>Modulos incluidos</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {licencia.modulos.map((m) => (
                <span key={m} style={{ padding: '4px 12px', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 20, fontSize: 12, color: '#16a34a', textTransform: 'capitalize' }}>{m}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
