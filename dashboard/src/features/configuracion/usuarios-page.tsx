// Configuracion: Usuarios y Roles
import { useState, useEffect } from 'react'
import type { Usuario } from '@/types/config'

async function apiFetch<T>(url: string): Promise<T> {
  const token = localStorage.getItem('sfce_token')
  const res = await fetch(url, { headers: { Authorization: token ? `Bearer ${token}` : '' } })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

const ROL_COLOR: Record<string, { bg: string; text: string }> = {
  admin: { bg: '#fef3c7', text: '#d97706' },
  gestor: { bg: '#eff6ff', text: '#3b82f6' },
  cliente: { bg: '#f0fdf4', text: '#16a34a' },
}

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    apiFetch<{ usuarios?: Usuario[] }>('/api/auth/usuarios')
      .then((d) => setUsuarios(d.usuarios ?? []))
      .catch(() => {})
      .finally(() => setCargando(false))
  }, [])

  return (
    <div style={{ padding: '24px 32px', maxWidth: 900 }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Usuarios y Roles</h1>
          <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Gestion de accesos al dashboard</p>
        </div>
        <button style={{ padding: '8px 18px', background: '#1e293b', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>
          + Nuevo Usuario
        </button>
      </div>
      {cargando && <p style={{ color: '#9ca3af' }}>Cargando usuarios...</p>}
      {!cargando && usuarios.length === 0 && (
        <p style={{ color: '#9ca3af', fontSize: 14 }}>No hay usuarios adicionales configurados.</p>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {usuarios.map((u) => {
          const rol = ROL_COLOR[u.rol] ?? ROL_COLOR.gestor
          return (
            <div key={u.id} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: '12px 18px', display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{ width: 38, height: 38, borderRadius: '50%', background: '#f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, color: '#475569', fontSize: 15 }}>
                {u.nombre?.[0]?.toUpperCase() ?? u.email[0].toUpperCase()}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, color: '#1e293b' }}>{u.nombre || u.email}</div>
                <div style={{ fontSize: 12, color: '#9ca3af' }}>{u.email}</div>
              </div>
              <span style={{ padding: '3px 12px', borderRadius: 20, background: rol.bg, color: rol.text, fontSize: 12, fontWeight: 600, textTransform: 'capitalize' }}>
                {u.rol}
              </span>
              <span style={{ fontSize: 12, color: u.activo ? '#16a34a' : '#9ca3af' }}>
                {u.activo ? 'Activo' : 'Inactivo'}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
