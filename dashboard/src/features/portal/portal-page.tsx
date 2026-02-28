// Portal Cliente — vista simplificada para el cliente final
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'

interface ResumenPortal {
  empresa_id: number; nombre: string; ejercicio: string
  resultado_acumulado: number
  facturas_pendientes_cobro: number; importe_pendiente_cobro: number
  facturas_pendientes_pago: number; importe_pendiente_pago: number
}

interface DocumentoPortal { id: number; nombre: string; tipo: string; estado: string; fecha: string | null }

async function apiFetch<T>(url: string): Promise<T> {
  const token = sessionStorage.getItem('sfce_token')
  const res = await fetch(url, { headers: { Authorization: token ? `Bearer ${token}` : '' } })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

function KPICard({ label, valor, tipo = 'euros', color = '#1e293b' }: { label: string; valor: number; tipo?: string; color?: string }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '14px 20px', minWidth: 180 }}>
      <div style={{ fontSize: 13, color: '#6b7280' }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color, marginTop: 4 }}>
        {tipo === 'euros' ? valor.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' }) : valor}
      </div>
    </div>
  )
}

export default function PortalPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id) || 1
  const [resumen, setResumen] = useState<ResumenPortal | null>(null)
  const [documentos, setDocumentos] = useState<DocumentoPortal[]>([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    setCargando(true)
    Promise.all([
      apiFetch<ResumenPortal>(`/api/portal/${empresaId}/resumen`),
      apiFetch<{ documentos: DocumentoPortal[] }>(`/api/portal/${empresaId}/documentos`),
    ])
      .then(([r, d]) => { setResumen(r); setDocumentos(d.documentos ?? []) })
      .catch(() => {})
      .finally(() => setCargando(false))
  }, [empresaId])

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1000 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Portal Cliente</h1>
        {resumen && <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>{resumen.nombre} — Ejercicio {resumen.ejercicio}</p>}
      </div>
      {cargando && <p style={{ color: '#9ca3af' }}>Cargando...</p>}
      {resumen && (
        <>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 28 }}>
            <KPICard label="Resultado Acumulado" valor={resumen.resultado_acumulado} color={resumen.resultado_acumulado >= 0 ? '#16a34a' : '#dc2626'} />
            <KPICard label="Pendiente de Cobro" valor={resumen.importe_pendiente_cobro} color="#3b82f6" />
            <KPICard label="Pendiente de Pago" valor={resumen.importe_pendiente_pago} color="#f59e0b" />
            <KPICard label="Facturas por Cobrar" valor={resumen.facturas_pendientes_cobro} tipo="count" color="#3b82f6" />
          </div>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Documentos recientes</h2>
            {documentos.length === 0 && <p style={{ color: '#9ca3af', fontSize: 14 }}>Sin documentos procesados.</p>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {documentos.slice(0, 20).map((d) => (
                <div key={d.id} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 14 }}>
                  <span style={{ padding: '2px 10px', background: '#f3f4f6', borderRadius: 10, fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase' }}>{d.tipo}</span>
                  <span style={{ flex: 1, fontSize: 14, color: '#1e293b' }}>{d.nombre}</span>
                  <span style={{ fontSize: 12, padding: '2px 10px', background: d.estado === 'procesado' ? '#dcfce7' : '#fef9c3', color: d.estado === 'procesado' ? '#16a34a' : '#ca8a04', borderRadius: 10 }}>{d.estado}</span>
                  {d.fecha && <span style={{ fontSize: 12, color: '#9ca3af' }}>{new Date(d.fecha).toLocaleDateString('es-ES')}</span>}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
