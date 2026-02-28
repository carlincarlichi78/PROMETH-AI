// Configuracion: Empresa
import { useState, useEffect } from 'react'

interface EmpresaForm {
  nombre: string; cifnif: string; direccion: string; codpostal: string
  ciudad: string; provincia: string; pais: string; telefono: string; email: string; web: string
}

async function apiFetch<T>(url: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem('sfce_token')
  const res = await fetch(url, { ...opts, headers: { Authorization: token ? `Bearer ${token}` : '', 'Content-Type': 'application/json', ...(opts?.headers ?? {}) } })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

function Campo({ label, value, onChange, tipo = 'text' }: { label: string; value: string; onChange: (v: string) => void; tipo?: string }) {
  return (
    <div>
      <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>{label}</label>
      <input type={tipo} value={value} onChange={(e) => onChange(e.target.value)} style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: 6, fontSize: 14, boxSizing: 'border-box' }} />
    </div>
  )
}

export default function EmpresaPage() {
  const [form, setForm] = useState<EmpresaForm>({ nombre: '', cifnif: '', direccion: '', codpostal: '', ciudad: '', provincia: '', pais: 'ESP', telefono: '', email: '', web: '' })
  const [guardando, setGuardando] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<{ empresas: { nombre: string; cifnif: string; [k: string]: string }[] }>('/api/empresas')
      .then((d) => { if (d.empresas[0]) setForm((f) => ({ ...f, ...d.empresas[0] })) })
      .catch(() => {})
  }, [])

  const set = (campo: keyof EmpresaForm) => (val: string) => setForm((f) => ({ ...f, [campo]: val }))
  const guardar = async () => {
    setGuardando(true)
    try {
      await apiFetch('/api/empresas/1', { method: 'PUT', body: JSON.stringify(form) })
      setMsg('Datos guardados'); setTimeout(() => setMsg(null), 3000)
    } catch { setMsg('Error al guardar') } finally { setGuardando(false) }
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 700 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Datos de Empresa</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Informacion fiscal y de contacto</p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <Campo label="Nombre / Razon Social" value={form.nombre} onChange={set('nombre')} />
          <Campo label="CIF / NIF" value={form.cifnif} onChange={set('cifnif')} />
        </div>
        <Campo label="Direccion" value={form.direccion} onChange={set('direccion')} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 2fr', gap: 14 }}>
          <Campo label="C.P." value={form.codpostal} onChange={set('codpostal')} />
          <Campo label="Ciudad" value={form.ciudad} onChange={set('ciudad')} />
          <Campo label="Provincia" value={form.provincia} onChange={set('provincia')} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <Campo label="Telefono" value={form.telefono} onChange={set('telefono')} tipo="tel" />
          <Campo label="Email" value={form.email} onChange={set('email')} tipo="email" />
        </div>
        <Campo label="Sitio Web" value={form.web} onChange={set('web')} tipo="url" />
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', paddingTop: 8 }}>
          <button onClick={guardar} disabled={guardando} style={{ padding: '10px 24px', background: '#1e293b', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>
            {guardando ? 'Guardando...' : 'Guardar Cambios'}
          </button>
          {msg && <span style={{ fontSize: 14, color: msg.includes('Error') ? '#dc2626' : '#16a34a' }}>{msg}</span>}
        </div>
      </div>
    </div>
  )
}
