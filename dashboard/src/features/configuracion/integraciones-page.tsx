// Configuracion: Integraciones
import { useState, useEffect } from 'react'
import type { Integracion } from '@/types/config'

async function apiFetch<T>(url: string): Promise<T> {
  const token = localStorage.getItem('sfce_token')
  const res = await fetch(url, { headers: { Authorization: token ? `Bearer ${token}` : '' } })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

const ESTADO_COLOR: Record<string, { bg: string; text: string; label: string }> = {
  conectado: { bg: '#dcfce7', text: '#16a34a', label: 'Conectado' },
  desconectado: { bg: '#f3f4f6', text: '#6b7280', label: 'Desconectado' },
  error: { bg: '#fee2e2', text: '#dc2626', label: 'Error' },
}

const TIPO_ICON: Record<string, string> = { erp: 'ERP', ocr: 'OCR', ia: 'IA', email: 'Email' }

export default function IntegracionesPage() {
  const [integraciones, setIntegraciones] = useState<Integracion[]>([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    apiFetch<{ integraciones: Integracion[] }>('/api/config/integraciones').then((d) => setIntegraciones(d.integraciones)).catch(() => {}).finally(() => setCargando(false))
  }, [])

  return (
    <div style={{ padding: '24px 32px', maxWidth: 800 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Integraciones</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Estado de conexiones con servicios externos</p>
      </div>
      {cargando && <p style={{ color: '#9ca3af' }}>Cargando integraciones...</p>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {integraciones.map((integ) => {
          const est = ESTADO_COLOR[integ.estado] ?? ESTADO_COLOR['desconectado']!
          return (
            <div key={integ.nombre} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{ width: 44, height: 44, borderRadius: 8, background: '#f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#475569' }}>
                {TIPO_ICON[integ.tipo] ?? integ.tipo.toUpperCase()}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, color: '#1e293b' }}>{integ.nombre}</div>
                {integ.url && <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 2 }}>{integ.url}</div>}
              </div>
              <span style={{ padding: '4px 12px', borderRadius: 20, background: est.bg, color: est.text, fontSize: 12, fontWeight: 600 }}>
                {est.label}
              </span>
            </div>
          )
        })}
      </div>
      <p style={{ color: '#9ca3af', fontSize: 13, marginTop: 20 }}>
        Las credenciales se configuran en el archivo .env del servidor.
      </p>
    </div>
  )
}
