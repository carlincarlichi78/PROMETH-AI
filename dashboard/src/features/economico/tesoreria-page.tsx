// Pagina: Tesoreria y Cash Flow
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { Tesoreria, CashflowMensual } from '@/types/economico'
import { economicoApi } from './api'
import { StatCard } from '@/components/ui/stat-card'
import { PageTitle } from '@/components/ui/page-title'
import { ChartWrapper, CHART_COLORS } from '@/components/ui/chart-wrapper'
import { EmptyState } from '@/components/ui/empty-state'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { Wallet } from 'lucide-react'

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

  const formatEur = (v: number) => v.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })

  if (cargando) {
    return (
      <div className="p-6 max-w-5xl">
        <PageTitle titulo="Tesorería" subtitulo="Estado de caja y previsión de liquidez" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {Array.from({ length: 7 }).map((_, i) => <StatCard key={i} titulo="" valor="" cargando />)}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-5xl">
      <PageTitle titulo="Tesorería" subtitulo="Estado de caja y previsión de liquidez" />
      {error && <p className="text-[var(--state-danger)] text-sm mb-4">Error: {error}</p>}

      {tesorer ? (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard
              titulo="Saldo Actual"
              valor={formatEur(tesorer.saldo_actual)}
              subtitulo="Cuentas grupo 57"
              variante={tesorer.saldo_actual >= 0 ? 'success' : 'danger'}
              tendencia={tesorer.saldo_actual >= 0 ? 'up' : 'down'}
            />
            <StatCard
              titulo="Flujo Operativo"
              valor={formatEur(tesorer.flujo_operativo)}
              subtitulo="Ingresos - Gastos"
              variante={tesorer.flujo_operativo >= 0 ? 'success' : 'danger'}
              tendencia={tesorer.flujo_operativo >= 0 ? 'up' : 'down'}
            />
            <StatCard
              titulo="Flujo Inversión"
              valor={formatEur(tesorer.flujo_inversion)}
              subtitulo="Activos fijos"
            />
            <StatCard
              titulo="Flujo Financiación"
              valor={formatEur(tesorer.flujo_financiacion)}
              subtitulo="Deuda / PN"
            />
          </div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <StatCard titulo="Previsión 30 días" valor={formatEur(tesorer.prevision_30d)} />
            <StatCard titulo="Previsión 60 días" valor={formatEur(tesorer.prevision_60d)} />
            <StatCard titulo="Previsión 90 días" valor={formatEur(tesorer.prevision_90d)} />
          </div>
        </>
      ) : !error && (
        <EmptyState
          icono={<Wallet className="h-8 w-8" />}
          titulo="Sin datos de tesorería"
          descripcion="No hay movimientos de caja registrados en este ejercicio."
        />
      )}

      {cashflow && cashflow.cashflow_mensual.length > 0 && (
        <ChartWrapper titulo={`Cash Flow Mensual — ${cashflow.ejercicio}`} altura={200}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={cashflow.cashflow_mensual} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
              <XAxis dataKey="mes" tickFormatter={(v: string) => v.slice(5)} tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <Tooltip
                formatter={(v: number | undefined) => [v !== undefined ? formatEur(v) : '—', 'Flujo'] as [string, string]}
                contentStyle={{ background: 'var(--surface-3)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
              />
              <Bar dataKey="flujo" radius={[3, 3, 0, 0]}>
                {cashflow.cashflow_mensual.map(({ mes, flujo }) => (
                  <Cell key={mes} fill={flujo >= 0 ? CHART_COLORS.success : CHART_COLORS.danger} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartWrapper>
      )}
    </div>
  )
}
