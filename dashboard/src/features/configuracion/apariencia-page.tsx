// Configuracion: Apariencia
import { useState, useEffect } from 'react'
import type { ConfigApariencia } from '@/types/config'

async function apiFetch<T>(url: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem('sfce_token')
  const res = await fetch(url, { ...opts, headers: { Authorization: token ? `Bearer ${token}` : '', 'Content-Type': 'application/json', ...(opts?.headers ?? {}) } })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

const TEMA_OPCIONES = [{ value: 'light', label: 'Claro' }, { value: 'dark', label: 'Oscuro' }, { value: 'system', label: 'Sistema' }]
const DENSIDAD_OPCIONES = [{ value: 'comoda', label: 'Comoda' }, { value: 'compacta', label: 'Compacta' }]

export default function AparienciaPage() {
  const [config, setConfig] = useState<ConfigApariencia>({ tema: 'system', densidad: 'comoda', idioma: 'es', formato_fecha: 'dd/MM/yyyy', formato_numero: 'es-ES' })
  const [guardando, setGuardando] = useState(false)
  const [mensaje, setMensaje] = useState<string | null>(null)

  useEffect(() => { apiFetch<ConfigApariencia>('/api/config/apariencia').then(setConfig).catch(() => {}) }, [])

  const guardar = async () => {
    setGuardando(true)
    try {
      await apiFetch('/api/config/apariencia', { method: 'PUT', body: JSON.stringify(config) })
      setMensaje('Configuracion guardada')
      setTimeout(() => setMensaje(null), 3000)
    } catch {
      setMensaje('Error al guardar')
    } finally { setGuardando(false) }
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 600 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Apariencia</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Personaliza la interfaz del dashboard</p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 8 }}>Tema</label>
          <div style={{ display: 'flex', gap: 10 }}>
            {TEMA_OPCIONES.map((o) => (
              <button key={o.value} onClick={() => setConfig({ ...config, tema: o.value as ConfigApariencia['tema'] })}
                style={{ padding: '8px 20px', borderRadius: 8, border: `2px solid ${config.tema === o.value ? '#1e293b' : '#e5e7eb'}`, background: config.tema === o.value ? '#1e293b' : '#fff', color: config.tema === o.value ? '#fff' : '#374151', cursor: 'pointer', fontWeight: config.tema === o.value ? 600 : 400 }}>
                {o.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 8 }}>Densidad</label>
          <div style={{ display: 'flex', gap: 10 }}>
            {DENSIDAD_OPCIONES.map((o) => (
              <button key={o.value} onClick={() => setConfig({ ...config, densidad: o.value as ConfigApariencia['densidad'] })}
                style={{ padding: '8px 20px', borderRadius: 8, border: `2px solid ${config.densidad === o.value ? '#1e293b' : '#e5e7eb'}`, background: config.densidad === o.value ? '#1e293b' : '#fff', color: config.densidad === o.value ? '#fff' : '#374151', cursor: 'pointer', fontWeight: config.densidad === o.value ? 600 : 400 }}>
                {o.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 8 }}>Idioma</label>
          <select value={config.idioma} onChange={(e) => setConfig({ ...config, idioma: e.target.value })}
            style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: 6, fontSize: 14, width: 200 }}>
            <option value="es">Espanol</option>
            <option value="en">English</option>
          </select>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', paddingTop: 8 }}>
          <button onClick={guardar} disabled={guardando}
            style={{ padding: '10px 24px', background: '#1e293b', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>
            {guardando ? 'Guardando...' : 'Guardar'}
          </button>
          {mensaje && <span style={{ fontSize: 14, color: mensaje.includes('Error') ? '#dc2626' : '#16a34a' }}>{mensaje}</span>}
        </div>
      </div>
    </div>
  )
}
