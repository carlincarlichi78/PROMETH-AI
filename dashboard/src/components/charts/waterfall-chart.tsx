import {
  ComposedChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine,
} from 'recharts'
import { formatearImporte } from '@/lib/formatters'
import type { PyGWaterfallItem } from '@/types'

const COLORES: Record<string, string> = {
  inicio:   '#6366f1',  // indigo-500
  negativo: '#f43f5e',  // rose-500
  positivo: '#10b981',  // emerald-500
  subtotal: '#64748b',  // slate-500
  final:    '#7c3aed',  // violet-600
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; payload: PyGWaterfallItem }>
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null
  const item = payload[0]?.payload as PyGWaterfallItem
  if (!item) return null
  return (
    <div className="rounded-lg border bg-background/95 backdrop-blur-sm p-3 shadow-lg text-sm">
      <p className="font-semibold mb-1">{item.nombre}</p>
      <p className="text-foreground">{formatearImporte(item.valor)}</p>
    </div>
  )
}

interface WaterfallChartProps {
  datos: PyGWaterfallItem[]
  altura?: number
}

export function WaterfallChart({ datos, altura = 320 }: WaterfallChartProps) {
  const maximo = Math.max(...datos.map(d => d.offset + d.valor)) * 1.05

  return (
    <ResponsiveContainer width="100%" height={altura}>
      <ComposedChart data={datos} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
        <XAxis
          dataKey="nombre"
          tick={{ fontSize: 11 }}
          interval={0}
          angle={-20}
          textAnchor="end"
          height={50}
        />
        <YAxis
          tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
          domain={[0, maximo]}
          tick={{ fontSize: 11 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="#94a3b8" />

        {/* Barra transparente = offset (base invisible) */}
        <Bar dataKey="offset" stackId="wf" fill="transparent" radius={0} isAnimationActive={false} />

        {/* Barra de color = valor real */}
        <Bar dataKey="valor" stackId="wf" radius={[4, 4, 0, 0]}>
          {datos.map((entrada, idx) => (
            <Cell
              key={`cell-${idx}`}
              fill={COLORES[entrada.tipo] ?? COLORES.subtotal}
            />
          ))}
        </Bar>
      </ComposedChart>
    </ResponsiveContainer>
  )
}
