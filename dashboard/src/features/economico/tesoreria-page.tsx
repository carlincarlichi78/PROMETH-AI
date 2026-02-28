// Pagina: Tesoreria y Cash Flow
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { Tesoreria, CashflowMensual } from '@/types/economico'
import { economicoApi } from './api'

function KPIBox({ label, valor, subtext }: { label: string; valor: number; subtext?: string }) {
  const color = valor >= 0 ? '#16a34a' : '#dc2626'
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '16px 24px', minWidth: 200 }}>
      <div style={{ fontSize: 13, color: '#6b7280' }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700, color, marginTop: 4 }}>
        {valor.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
      </div>
      {subtext && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>{subtext}</div>}
    </div>
  )
}

export default function TesoreriaPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [tesorer, setTesorer] = useState<Tesoreria | null>(null)
  const [cashflow, setCashflow] = useState<CashflowMensual | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setCargando(true)
    Promise.all([economicoApi.tesoreria(empresaId), economicoApi.cashflow(empresaId)])
      .then(([t, c]) => { setTesorer(t); setCashflow(c) })
      .catch((e: Error) => setError(e.message))
      .finally(() => setCargando(false))
  }, [empresaId])

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1200 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', margin: 0 }}>Tesoreria</h1>
        <p style={{ color: '#6b7280', marginTop: 4, fontSize: 14 }}>Estado de caja y prevision de liquidez</p>
      </div>
      {cargando && <p style={{ color: '#9ca3af' }}>Cargando tesoreria...</p>}
      {error && <p style={{ color: '#dc2626' }}>Error: {error}</p>}
      {tesorer && (
        <>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 28 }}>
            <KPIBox label="Saldo Actual" valor={tesorer.saldo_actual} subtext="Cuentas grupo 57" />
            <KPIBox label="Flujo Operativo" valor={tesorer.flujo_operativo} subtext="Ingresos - Gastos" />
            <KPIBox label="Flujo Inversion" valor={tesorer.flujo_inversion} subtext="Activos fijos" />
            <KPIBox label="Flujo Financiacion" valor={tesorer.flujo_financiacion} subtext="Deuda / PN" />
          </div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 28 }}>
            <KPIBox label="Prevision 30 dias" valor={tesorer.prevision_30d} />
            <KPIBox label="Prevision 60 dias" valor={tesorer.prevision_60d} />
            <KPIBox label="Prevision 90 dias" valor={tesorer.prevision_90d} />
          </div>
        </>
      )}
      {cashflow && cashflow.cashflow_mensual.length > 0 && (
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Cash Flow Mensual — {cashflow.ejercicio}</h2>
          <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 120 }}>
            {cashflow.cashflow_mensual.map(({ mes, flujo }) => {
              const max = Math.max(...cashflow.cashflow_mensual.map((m) => Math.abs(m.flujo)), 1)
              const h = Math.round((Math.abs(flujo) / max) * 100)
              return (
                <div key={mes} title={`${mes}: ${flujo.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}`}
                  style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <div style={{ width: '100%', height: `${h}%`, background: flujo >= 0 ? '#4ade80' : '#f87171', borderRadius: 3, minHeight: 4 }} />
                  <span style={{ fontSize: 10, color: '#9ca3af' }}>{mes.slice(5)}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
