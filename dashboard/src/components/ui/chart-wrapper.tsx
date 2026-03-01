// src/components/ui/chart-wrapper.tsx
// Wrapper que inyecta la paleta ámbar cohesiva en todos los charts Recharts

export const CHART_COLORS = {
  primary:   'var(--chart-1)',
  secondary: 'var(--chart-2)',
  success:   'var(--chart-3)',
  danger:    'var(--chart-4)',
  neutral:   'var(--chart-5)',
  // Para waterfall/barras
  positivo:  'var(--chart-3)',  // emerald
  negativo:  'var(--chart-4)',  // rose
  neutro:    'var(--chart-5)',  // slate
}

export const CHART_TOOLTIP_STYLE = {
  backgroundColor: 'var(--surface-3)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  color: 'var(--foreground)',
  fontSize: '13px',
}

export const CHART_AXIS_STYLE = {
  tick: { fill: 'var(--muted-foreground)', fontSize: 12 },
  axisLine: { stroke: 'var(--border)' },
  tickLine: false as const,
}

interface ChartWrapperProps {
  children: React.ReactNode
  titulo?: string
  subtitulo?: string
  altura?: number
  className?: string
}

export function ChartWrapper({ children, titulo, subtitulo, altura = 280, className }: ChartWrapperProps) {
  return (
    <div className={`rounded-xl border border-border/50 bg-[var(--surface-1)] p-5 ${className ?? ''}`}>
      {titulo && (
        <div className="mb-4">
          <h3 className="text-[15px] font-semibold">{titulo}</h3>
          {subtitulo && <p className="text-[13px] text-muted-foreground mt-0.5">{subtitulo}</p>}
        </div>
      )}
      <div style={{ height: altura }}>
        {children}
      </div>
    </div>
  )
}
