import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import { api } from '@/lib/api-client'
import { formatearImporte, formatearFecha } from '@/lib/formatters'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

interface MovimientoLibro {
  fecha:          string
  concepto:       string | null
  debe:           number
  haber:          number
  saldo:          number
  numero_asiento: number | null
}

interface LibroMayorData {
  subcuenta:   string
  nombre:      string
  movimientos: MovimientoLibro[]
  saldo_final: number
}

interface LibroMayorProps {
  empresaId: number
  subcuenta: string
  onClose:   () => void
}

export function LibroMayor({ empresaId, subcuenta, onClose }: LibroMayorProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['libro-mayor', empresaId, subcuenta],
    queryFn:  () =>
      api.get<LibroMayorData>(
        `/api/contabilidad/${empresaId}/libro-mayor/${subcuenta}`,
      ),
  })

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/40 z-40"
        onClick={onClose}
      />

      {/* Panel lateral */}
      <div className="fixed right-0 top-0 h-full w-[560px] bg-background z-50 shadow-xl flex flex-col">
        {/* Cabecera */}
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <div>
            <h2 className="font-semibold font-mono text-base">{subcuenta}</h2>
            {data && (
              <p className="text-sm text-muted-foreground mt-0.5">{data.nombre}</p>
            )}
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {isLoading ? (
          <div className="p-6 space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : !data || data.movimientos.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            Sin movimientos para esta subcuenta
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto min-h-0">
            {/* Saldo final */}
            <div className="flex items-center gap-2 px-6 py-3 bg-muted/30 border-b">
              <span className="text-sm text-muted-foreground">Saldo:</span>
              <span
                className={`text-sm font-semibold ${
                  data.saldo_final < 0 ? 'text-rose-600' : 'text-emerald-600'
                }`}
              >
                {formatearImporte(data.saldo_final)}
              </span>
              <span className="text-xs text-muted-foreground ml-auto">
                {data.movimientos.length} movimiento{data.movimientos.length !== 1 ? 's' : ''}
              </span>
            </div>

            {/* Gráfico evolución */}
            <div className="px-6 pt-4 pb-2">
              <p className="text-xs font-medium text-muted-foreground mb-2">
                Evolución del saldo
              </p>
              <ResponsiveContainer width="100%" height={110}>
                <AreaChart
                  data={data.movimientos}
                  margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
                >
                  <XAxis
                    dataKey="fecha"
                    tick={{ fontSize: 9 }}
                    tickFormatter={(v: string) => v.slice(5)}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fontSize: 9 }}
                    tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                    width={38}
                  />
                  <Tooltip
                    formatter={(v: number | undefined) =>
                      [v != null ? formatearImporte(v) : '-', 'Saldo'] as [string, string]
                    }
                    labelFormatter={(l: unknown) =>
                      typeof l === 'string' ? formatearFecha(l) : String(l)
                    }
                    contentStyle={{ fontSize: 11 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="saldo"
                    stroke="#6366f1"
                    fill="#6366f1"
                    fillOpacity={0.12}
                    strokeWidth={1.5}
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Tabla de movimientos */}
            <div className="px-6 pb-8">
              <div className="grid grid-cols-[72px_1fr_72px_72px_80px] gap-1 text-[10px] font-medium text-muted-foreground py-2 border-b">
                <div>Fecha</div>
                <div>Concepto</div>
                <div className="text-right">Debe</div>
                <div className="text-right">Haber</div>
                <div className="text-right">Saldo</div>
              </div>
              {data.movimientos.map((m, i) => (
                <div
                  key={i}
                  className="grid grid-cols-[72px_1fr_72px_72px_80px] gap-1 text-xs py-1.5 border-b border-muted/40 hover:bg-muted/30 transition-colors"
                >
                  <div className="text-muted-foreground text-[10px]">
                    {formatearFecha(m.fecha)}
                  </div>
                  <div className="truncate">{m.concepto ?? '-'}</div>
                  <div className="text-right font-mono">
                    {m.debe > 0 ? formatearImporte(m.debe) : '-'}
                  </div>
                  <div className="text-right font-mono">
                    {m.haber > 0 ? formatearImporte(m.haber) : '-'}
                  </div>
                  <div
                    className={`text-right font-mono ${
                      m.saldo < 0 ? 'text-rose-600' : ''
                    }`}
                  >
                    {formatearImporte(m.saldo)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
