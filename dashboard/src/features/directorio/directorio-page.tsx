// Directorio Global de Entidades — rewrite Stream B
import { useState, useEffect, useCallback } from 'react'

interface EntidadDirectorio {
  id: number; cif: string | null; nombre: string; nombre_comercial: string | null
  pais: string; tipo_persona: string | null; forma_juridica: string | null
  validado_aeat: boolean; validado_vies: boolean; sector: string | null; cnae: string | null
}

async function apiFetch<T>(url: string): Promise<T> {
  const token = localStorage.getItem('sfce_token')
  const res = await fetch(url, { headers: { Authorization: token ? `Bearer ${token}` : '' } })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

function BadgeValidacion({ label, activo }: { label: string; activo: boolean }) {
  return <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600, background: activo ? '#dcfce7' : '#f3f4f6', color: activo ? '#16a34a' : '#9ca3af' }}>{label}</span>
}

export default function DirectorioPage() {
  const [entidades, setEntidades] = useState<EntidadDirectorio[]>([])
  const [total, setTotal] = useState(0)
  const [pagina, setPagina] = useState(1)
  const [busqueda, setBusqueda] = useState('')
  const [cargando, setCargando] = useState(true)
  const [seleccionada, setSeleccionada] = useState<EntidadDirectorio | null>(null)

  const cargar = useCallback((p = 1, q = busqueda) => {
    setCargando(true)
    const qs = new URLSearchParams({ limit: '25', offset: String((p - 1) * 25), ...(q ? { q } : {}) })
    apiFetch<{ entidades: EntidadDirectorio[]; total: number }>(`/api/directorio/buscar?${qs}`)
      .then((d) => { setEntidades(d.entidades ?? []); setTotal(d.total ?? 0); setPagina(p) })
      .catch(() => {})
      .finally(() => setCargando(false))
  }, [busqueda])

  useEffect(() => { cargar(1) }, [])

  const totalPaginas = Math.ceil(total / 25)

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1200 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Directorio Global</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>{total} entidades registradas</p>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input value={busqueda} onChange={(e) => setBusqueda(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && cargar(1, busqueda)}
          placeholder="Buscar por nombre, CIF, CNAE..." style={{ flex: 1, padding: '9px 14px', border: '1px solid #e5e7eb', borderRadius: 8, fontSize: 14 }} />
        <button onClick={() => cargar(1, busqueda)} style={{ padding: '9px 20px', background: '#1e293b', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>Buscar</button>
        <button onClick={() => { setBusqueda(''); cargar(1, '') }} style={{ padding: '9px 16px', border: '1px solid #e5e7eb', background: '#fff', borderRadius: 8, cursor: 'pointer', color: '#6b7280' }}>Limpiar</button>
      </div>
      {cargando && <p style={{ color: '#9ca3af' }}>Cargando directorio...</p>}
      <div style={{ display: 'flex', gap: 20 }}>
        <div style={{ flex: 1, overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                {['CIF', 'Nombre', 'Forma Juridica', 'Pais', 'Validacion', 'Sector'].map((h) => (
                  <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: '#6b7280', fontWeight: 600, fontSize: 12 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entidades.map((e) => (
                <tr key={e.id} onClick={() => setSeleccionada(seleccionada?.id === e.id ? null : e)}
                  style={{ borderBottom: '1px solid #f3f4f6', cursor: 'pointer', background: seleccionada?.id === e.id ? '#f8fafc' : '#fff' }}>
                  <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#6b7280', fontSize: 13 }}>{e.cif ?? '—'}</td>
                  <td style={{ padding: '10px 12px', fontWeight: 500, color: '#1e293b' }}>
                    {e.nombre}
                    {e.nombre_comercial && e.nombre_comercial !== e.nombre && <div style={{ fontSize: 11, color: '#9ca3af' }}>{e.nombre_comercial}</div>}
                  </td>
                  <td style={{ padding: '10px 12px', color: '#6b7280' }}>{e.forma_juridica ?? '—'}</td>
                  <td style={{ padding: '10px 12px', color: '#6b7280' }}>{e.pais}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {e.pais === 'ESP' && <BadgeValidacion label="AEAT" activo={e.validado_aeat} />}
                      {e.pais !== 'ESP' && <BadgeValidacion label="VIES" activo={e.validado_vies} />}
                    </div>
                  </td>
                  <td style={{ padding: '10px 12px', color: '#6b7280', fontSize: 12 }}>{e.sector ?? (e.cnae ? `CNAE ${e.cnae}` : '—')}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!cargando && entidades.length === 0 && <p style={{ color: '#9ca3af', fontSize: 14, padding: '20px 0' }}>Sin resultados.</p>}
          {totalPaginas > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 20 }}>
              <button disabled={pagina === 1} onClick={() => cargar(pagina - 1)} style={{ padding: '6px 14px', border: '1px solid #e5e7eb', borderRadius: 6, cursor: 'pointer' }}>Anterior</button>
              <span style={{ padding: '6px 14px', color: '#6b7280', fontSize: 14 }}>Pag. {pagina} / {totalPaginas}</span>
              <button disabled={pagina >= totalPaginas} onClick={() => cargar(pagina + 1)} style={{ padding: '6px 14px', border: '1px solid #e5e7eb', borderRadius: 6, cursor: 'pointer' }}>Siguiente</button>
            </div>
          )}
        </div>
        {seleccionada && (
          <div style={{ width: 260, background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 18, alignSelf: 'flex-start', flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#1e293b' }}>Ficha</h3>
              <button onClick={() => setSeleccionada(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', fontSize: 18 }}>×</button>
            </div>
            {[['Nombre', seleccionada.nombre], ['CIF', seleccionada.cif ?? '—'], ['Tipo', seleccionada.tipo_persona ?? '—'], ['Forma juridica', seleccionada.forma_juridica ?? '—'], ['Pais', seleccionada.pais], ['CNAE', seleccionada.cnae ?? '—'], ['Sector', seleccionada.sector ?? '—']].map(([l, v]) => (
              <div key={l} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 11, color: '#9ca3af', fontWeight: 600, textTransform: 'uppercase' }}>{l}</div>
                <div style={{ fontSize: 14, color: '#1e293b', marginTop: 2 }}>{v}</div>
              </div>
            ))}
            <div style={{ marginTop: 12, display: 'flex', gap: 6 }}>
              <BadgeValidacion label="AEAT" activo={seleccionada.validado_aeat} />
              <BadgeValidacion label="VIES" activo={seleccionada.validado_vies} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
