// Configuracion: Backup
import { useState, useEffect } from 'react'
import type { Backup } from '@/types/config'

async function apiFetch<T>(url: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem('sfce_token')
  const res = await fetch(url, { ...opts, headers: { Authorization: token ? `Bearer ${token}` : '', ...(opts?.headers ?? {}) } })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export default function BackupPage() {
  const [backups, setBackups] = useState<Backup[]>([])
  const [cargando, setCargando] = useState(true)
  const [creando, setCreando] = useState(false)
  const [restaurando, setRestaurando] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  const cargar = () => {
    setCargando(true)
    apiFetch<Backup[]>('/api/config/backup/listar').then(setBackups).catch(() => {}).finally(() => setCargando(false))
  }

  useEffect(cargar, [])

  const crear = async () => {
    setCreando(true)
    try {
      const r = await apiFetch<{ id: string }>('/api/config/backup/crear', { method: 'POST' })
      setMsg(`Backup creado: ${r.id}`)
      cargar()
    } catch { setMsg('Error al crear backup') } finally { setCreando(false) }
  }

  const restaurar = async (id: string) => {
    if (!confirm(`Restaurar backup "${id}"? La BD actual se sobreescribira.`)) return
    setRestaurando(id)
    try {
      await apiFetch(`/api/config/backup/restaurar/${id}`, { method: 'POST' })
      setMsg(`Backup ${id} restaurado`)
    } catch { setMsg('Error al restaurar') } finally { setRestaurando(null) }
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 800 }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Backup</h1>
          <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Copias de seguridad de la base de datos</p>
        </div>
        <button onClick={crear} disabled={creando}
          style={{ padding: '8px 20px', background: '#1e293b', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>
          {creando ? '...' : 'Crear Backup'}
        </button>
      </div>
      {msg && <div style={{ padding: '10px 16px', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 8, color: '#16a34a', fontSize: 14, marginBottom: 16 }}>{msg}</div>}
      {cargando && <p style={{ color: '#9ca3af' }}>Cargando backups...</p>}
      {!cargando && backups.length === 0 && <p style={{ color: '#9ca3af', fontSize: 14 }}>No hay backups disponibles. Crea el primero con el boton superior.</p>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {backups.map((b) => (
          <div key={b.id} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: '#1e293b', fontSize: 14 }}>{b.id}</div>
              <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 2 }}>
                {new Date(b.fecha).toLocaleString('es-ES')} &bull; {b.tamano} &bull;
                <span style={{ marginLeft: 6, padding: '1px 8px', background: b.tipo === 'manual' ? '#eff6ff' : '#f0fdf4', color: b.tipo === 'manual' ? '#3b82f6' : '#16a34a', borderRadius: 10, fontSize: 11 }}>{b.tipo}</span>
              </div>
            </div>
            <button onClick={() => restaurar(b.id)} disabled={restaurando === b.id}
              style={{ padding: '6px 14px', border: '1px solid #e5e7eb', background: '#fff', borderRadius: 6, cursor: 'pointer', fontSize: 13, color: '#374151' }}>
              {restaurando === b.id ? '...' : 'Restaurar'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
