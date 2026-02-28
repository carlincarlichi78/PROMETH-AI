import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
} from 'recharts'
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'
import { api } from '@/lib/api-client'
import { formatearImporte } from '@/lib/formatters'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import type { Balance2, BalanceLinea, BalanceRatios, BalanceAlerta } from '@/types'

// Benchmarks sectoriales hostelería (CNAE 5610)
const BENCHMARKS = {
  liquidez_corriente: 1.0,
  endeudamiento: 50,
  autonomia_financiera: 50,
  pmc_dias: 30,
  pmp_dias: 60,
}

type NivelSemaforo = 'verde' | 'amarillo' | 'rojo'

function calcularSemaforo(ratio: keyof typeof BENCHMARKS, valor: number): NivelSemaforo {
  const bench = BENCHMARKS[ratio]
  if (ratio === 'liquidez_corriente') return valor >= bench * 1.2 ? 'verde' : valor >= bench ? 'amarillo' : 'rojo'
  if (ratio === 'endeudamiento') return valor <= bench * 0.8 ? 'verde' : valor <= bench ? 'amarillo' : 'rojo'
  if (ratio === 'autonomia_financiera') return valor >= bench * 1.2 ? 'verde' : valor >= bench ? 'amarillo' : 'rojo'
  if (ratio === 'pmc_dias') return valor <= bench ? 'verde' : valor <= bench * 2 ? 'amarillo' : 'rojo'
  if (ratio === 'pmp_dias') return valor <= bench * 1.5 ? 'verde' : valor <= bench * 2 ? 'amarillo' : 'rojo'
  return 'amarillo'
}

const SEMAFORO_COLOR: Record<NivelSemaforo, string> = {
  verde: 'text-emerald-600',
  amarillo: 'text-amber-500',
  rojo: 'text-rose-600',
}
const SEMAFORO_ICONO: Record<NivelSemaforo, string> = {
  verde: '🟢', amarillo: '🟡', rojo: '🔴',
}

function FilasBalance({ secciones }: {
  secciones: Array<{ titulo: string; total: number; lineas: BalanceLinea[] }>
}) {
  return (
    <>
      {secciones.map((sec) => (
        <>
          <tr key={sec.titulo} className="bg-muted/40 border-t">
            <td className="px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {sec.titulo}
            </td>
            <td className="px-4 py-1.5 text-right tabular-nums font-semibold text-sm">
              {formatearImporte(sec.total)}
            </td>
          </tr>
          {sec.lineas.map((l) => (
            <tr key={l.id} className="border-t hover:bg-muted/20">
              <td className="px-4 py-1.5 pl-8 text-sm text-muted-foreground">
                {l.descripcion}
                {l.badge && <Badge variant="outline" className="ml-2 text-xs">{l.badge}</Badge>}
              </td>
              <td className="px-4 py-1.5 text-right tabular-nums text-sm">{formatearImporte(l.importe)}</td>
            </tr>
          ))}
        </>
      ))}
    </>
  )
}

function TablaT({ balance }: { balance: Balance2 }) {
  const { activo, patrimonio_neto, pasivo } = balance
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Activo */}
      <div className="rounded-md border overflow-hidden">
        <div className="bg-blue-50 dark:bg-blue-950 px-4 py-2 font-semibold text-sm flex justify-between">
          <span>ACTIVO</span>
          <span className="tabular-nums">{formatearImporte(activo.total)}</span>
        </div>
        <table className="w-full text-sm">
          <tbody>
            <FilasBalance secciones={[
              { titulo: 'A) Activo No Corriente', total: activo.no_corriente.total, lineas: activo.no_corriente.lineas },
              { titulo: 'B) Activo Corriente', total: activo.corriente.total, lineas: activo.corriente.lineas },
            ]} />
          </tbody>
        </table>
      </div>

      {/* Pasivo + PN */}
      <div className="rounded-md border overflow-hidden">
        <div className="bg-rose-50 dark:bg-rose-950 px-4 py-2 font-semibold text-sm flex justify-between">
          <span>PATRIMONIO NETO Y PASIVO</span>
          <span className="tabular-nums">{formatearImporte(patrimonio_neto.total + pasivo.total)}</span>
        </div>
        <table className="w-full text-sm">
          <tbody>
            <FilasBalance secciones={[
              { titulo: 'A) Patrimonio Neto', total: patrimonio_neto.total, lineas: patrimonio_neto.lineas },
              { titulo: 'B) Pasivo No Corriente', total: pasivo.no_corriente.total, lineas: pasivo.no_corriente.lineas },
              { titulo: 'C) Pasivo Corriente', total: pasivo.corriente.total, lineas: pasivo.corriente.lineas },
            ]} />
          </tbody>
        </table>
      </div>
    </div>
  )
}

function PanelRatios({ ratios }: { ratios: BalanceRatios }) {
  const items: Array<{ label: string; valor: string; semaf: NivelSemaforo }> = [
    {
      label: 'Fondo Maniobra',
      valor: formatearImporte(ratios.fondo_maniobra),
      semaf: ratios.fondo_maniobra >= 0 ? 'verde' : 'rojo',
    },
    {
      label: 'Liquidez',
      valor: ratios.liquidez_corriente.toFixed(2),
      semaf: calcularSemaforo('liquidez_corriente', ratios.liquidez_corriente),
    },
    {
      label: 'Endeudamiento',
      valor: `${ratios.endeudamiento.toFixed(1)}%`,
      semaf: calcularSemaforo('endeudamiento', ratios.endeudamiento),
    },
    {
      label: 'Autonomía',
      valor: `${ratios.autonomia_financiera.toFixed(1)}%`,
      semaf: calcularSemaforo('autonomia_financiera', ratios.autonomia_financiera),
    },
    {
      label: 'PMC',
      valor: ratios.pmc_dias != null ? `${ratios.pmc_dias} días` : '—',
      semaf: ratios.pmc_dias ? calcularSemaforo('pmc_dias', ratios.pmc_dias) : 'amarillo',
    },
    {
      label: 'PMP',
      valor: ratios.pmp_dias != null ? `${ratios.pmp_dias} días` : '—',
      semaf: ratios.pmp_dias ? calcularSemaforo('pmp_dias', ratios.pmp_dias) : 'amarillo',
    },
  ]

  // Datos para radar — normalizar sobre benchmark
  const radarData = [
    { subject: 'Liquidez', value: Math.min((ratios.liquidez_corriente / BENCHMARKS.liquidez_corriente) * 100, 200) },
    { subject: 'Autonomía', value: Math.min((ratios.autonomia_financiera / BENCHMARKS.autonomia_financiera) * 100, 200) },
    { subject: 'Solvencia', value: Math.min(((100 - ratios.endeudamiento) / (100 - BENCHMARKS.endeudamiento)) * 100, 200) },
    { subject: 'Cobro', value: ratios.pmc_dias ? Math.min((BENCHMARKS.pmc_dias / ratios.pmc_dias) * 100, 200) : 50 },
    { subject: 'Pago', value: ratios.pmp_dias ? Math.min((ratios.pmp_dias / BENCHMARKS.pmp_dias) * 100, 200) : 50 },
  ]

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Ratios financieros</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {items.map((item) => (
              <div key={item.label} className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">{item.label}</p>
                <p className={`text-lg font-bold tabular-nums ${SEMAFORO_COLOR[item.semaf]}`}>
                  {SEMAFORO_ICONO[item.semaf]} {item.valor}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Diagnóstico vs benchmark hostelería</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
              <Radar dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
            </RadarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}

function PanelAlertas({ alertas, cuadre }: { alertas: BalanceAlerta[]; cuadre: Balance2['cuadre'] }) {
  if (alertas.length === 0 && cuadre.ok) return null

  const iconoPorNivel = {
    critical: <XCircle className="h-4 w-4 text-rose-500 flex-shrink-0" />,
    warning: <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0" />,
    info: <Info className="h-4 w-4 text-blue-500 flex-shrink-0" />,
  }

  return (
    <div className="space-y-2">
      {!cuadre.ok && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 dark:bg-rose-950 p-3 text-sm">
          <XCircle className="h-4 w-4 text-rose-500 flex-shrink-0 mt-0.5" />
          <span>Balance no cuadra — diferencia: {formatearImporte(cuadre.diferencia)}</span>
        </div>
      )}
      {alertas.map((alerta) => (
        <div
          key={alerta.codigo}
          className={[
            'flex items-start gap-2 rounded-lg border p-3 text-sm',
            alerta.nivel === 'critical' ? 'border-rose-200 bg-rose-50 dark:bg-rose-950' : '',
            alerta.nivel === 'warning' ? 'border-amber-200 bg-amber-50 dark:bg-amber-950' : '',
            alerta.nivel === 'info' ? 'border-blue-200 bg-blue-50 dark:bg-blue-950' : '',
          ].join(' ')}
        >
          {iconoPorNivel[alerta.nivel]}
          <span className="mt-0.5">{alerta.mensaje}</span>
        </div>
      ))}
    </div>
  )
}

export default function BalancePage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data, isLoading, error } = useQuery<Balance2>({
    queryKey: ['contabilidad', empresaId, 'balance2'],
    queryFn: () => api.get<Balance2>(`/api/contabilidad/${empresaId}/balance2`),
    enabled: !!empresaId,
  })

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        {[1, 2, 3].map(i => <Skeleton key={i} className="h-32" />)}
      </div>
    )
  }
  if (error || !data) {
    return <div className="p-6 text-destructive">Error cargando el Balance de Situación</div>
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Balance de Situación</h1>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {data.cuadre.ok
            ? <><CheckCircle className="h-4 w-4 text-emerald-500" /> Balance cuadrado</>
            : <><XCircle className="h-4 w-4 text-rose-500" /> Diferencia: {formatearImporte(data.cuadre.diferencia)}</>
          }
          {data.ejercicio_abierto && (
            <Badge variant="outline" className="ml-2">Ejercicio abierto</Badge>
          )}
        </div>
      </div>

      {/* Alertas */}
      <PanelAlertas alertas={data.alertas} cuadre={data.cuadre} />

      {/* Ratios */}
      <PanelRatios ratios={data.ratios} />

      {/* Formato T */}
      <TablaT balance={data} />
    </div>
  )
}
