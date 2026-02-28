// Pagina: Centros de Coste
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { CentroCoste } from '@/types/economico'

async function apiFetch<T>(url: string): Promise<T> {
  const token = sessionStorage.getItem('sfce_token')
  const res = await fetch(url, { headers: { Authorization: token ? `Bearer ${token}` : '' } })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

const TIPOS = ['departamento', 'proyecto', 'sucursal', 'obra'] as const

export default function CentrosCostePage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [centros, setCentros] = useState<CentroCoste[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nuevoNombre, setNuevoNombre] = useState('')
  const [nuevoTipo, setNuevoTipo] = useState<string>('departamento')
  const [guardando, setGuardando] = useState(false)

  const cargar = () => {
    setCargando(true)
    apiFetch<{ centros: CentroCoste[] }>(`/api/economico/${empresaId}/centros-coste`)
      .then((d) => setCentros(d.centros ?? []))
      .catch((e: Error) => { setError(e.message); setCentros([]) })
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [empresaId])

  const crear = async () => {
    if (!nuevoNombre.trim()) return
    setGuardando(true)
    try {
      const token = sessionStorage.getItem('sfce_token')
      await fetch(`/api/economico/${empresaId}/centros-coste`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: token ? `Bearer ${token}` : '' },
        body: JSON.stringify({ nombre: nuevoNombre, tipo: nuevoTipo }),
      })
      setNuevoNombre('')
      cargar()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setGuardando(false)
    }
  }

  const TIPO_COLOR: Record<string, string> = {
    departamento: '#3b82f6', proyecto: '#8b5cf6', sucursal: '#f59e0b', obra: '#10b981',
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 900 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Centros de Coste</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Organiza gastos por departamento, proyecto, sucursal u obra</p>
      </div>

      {/* Formulario crear */}
      <div style={{ background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: 10, padding: 16, marginBottom: 24, display: 'flex', gap: 12, alignItems: 'center' }}>
        <input
          value={nuevoNombre}
          onChange={(e) => setNuevoNombre(e.target.value)}
          placeholder="Nombre del centro..."
          style={{ flex: 1, padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: 6, fontSize: 14 }}
          onKeyDown={(e) => e.key === 'Enter' && crear()}
        />
        <select value={nuevoTipo} onChange={(e) => setNuevoTipo(e.target.value)}
          style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: 6, fontSize: 14 }}>
          {TIPOS.map((t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
        </select>
        <button onClick={crear} disabled={guardando || !nuevoNombre.trim()}
          style={{ padding: '8px 18px', background: '#1e293b', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14 }}>
          {guardando ? '...' : '+ Crear'}
        </button>
      </div>

      {cargando && <p style={{ color: '#9ca3af' }}>Cargando centros...</p>}
      {error && <p style={{ color: '#dc2626', fontSize: 14 }}>Nota: {error} — los centros se crean cuando haya datos.</p>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {centros.map((c) => (
          <div key={c.id} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: '12px 18px', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 10, height: 10, borderRadius: '50%',
              background: TIPO_COLOR[c.tipo] ?? '#6b7280',
            }} />
            <div style={{ flex: 1 }}>
              <span style={{ fontWeight: 600, color: '#1e293b' }}>{c.nombre}</span>
              <span style={{ marginLeft: 10, fontSize: 12, color: '#6b7280', textTransform: 'capitalize' }}>{c.tipo}</span>
            </div>
            <span style={{ fontSize: 12, color: c.activo ? '#16a34a' : '#9ca3af' }}>
              {c.activo ? 'Activo' : 'Inactivo'}
            </span>
          </div>
        ))}
        {!cargando && centros.length === 0 && (
          <p style={{ color: '#9ca3af', fontSize: 14 }}>No hay centros de coste. Crea el primero arriba.</p>
        )}
      </div>
    </div>
  )
}
