// dashboard/src/features/advisor/sala-estrategia-page.tsx
import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import { TrendingUp, TrendingDown } from 'lucide-react'

// ─── Tipos ────────────────────────────────────────────────────────────────────

interface ParametrosSimulacion {
  ventas_actuales: number
  covers_dia: number
  precio_menu_actual: number
  food_cost_pct: number
  gasto_personal: number
  gastos_fijos: number
}

interface ResultadoSimulacion {
  ventas_nuevas: number
  covers_retenidos: number
  ebitda_actual: number
  ebitda_nuevo: number
  delta_ebitda: number
  break_even_dias_menos: number
}

// ─── Lógica de simulación ─────────────────────────────────────────────────────

function simular(
  params: ParametrosSimulacion,
  nuevo_precio: number,
  retencion_pct: number,
): ResultadoSimulacion {
  const covers_retenidos = Math.round(params.covers_dia * (retencion_pct / 100))
  const ventas_nuevas = covers_retenidos * nuevo_precio * 30
  const food_cost = ventas_nuevas * (params.food_cost_pct / 100)
  const ebitda_nuevo =
    ventas_nuevas - food_cost - params.gasto_personal - params.gastos_fijos
  const ebitda_actual =
    params.ventas_actuales -
    (params.ventas_actuales * params.food_cost_pct) / 100 -
    params.gasto_personal -
    params.gastos_fijos
  const margen_dia_actual =
    (params.ventas_actuales -
      (params.ventas_actuales * params.food_cost_pct) / 100 -
      params.gasto_personal) /
    30
  const margen_dia_nuevo = (ventas_nuevas - food_cost - params.gasto_personal) / 30
  const be_actual =
    margen_dia_actual > 0 ? params.gastos_fijos / margen_dia_actual : 999
  const be_nuevo =
    margen_dia_nuevo > 0 ? params.gastos_fijos / margen_dia_nuevo : 999
  return {
    ventas_nuevas,
    covers_retenidos,
    ebitda_actual,
    ebitda_nuevo,
    delta_ebitda: ebitda_nuevo - ebitda_actual,
    break_even_dias_menos: Math.round(be_actual - be_nuevo),
  }
}

// ─── Utilidades de formato ────────────────────────────────────────────────────

function fmtEur(n: number): string {
  return n.toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' €'
}

function fmtSigEur(n: number): string {
  const signo = n >= 0 ? '+' : ''
  return signo + fmtEur(n)
}

// ─── Componentes UI ───────────────────────────────────────────────────────────

function Panel({
  titulo,
  children,
}: {
  titulo: string
  children: React.ReactNode
}) {
  return (
    <div
      style={{
        background: 'var(--adv-surface)',
        border: '1px solid var(--adv-border)',
        borderRadius: 14,
        padding: '20px 22px',
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}
    >
      <h3
        style={{
          margin: 0,
          fontSize: 14,
          fontWeight: 700,
          color: 'var(--adv-text)',
          letterSpacing: '-0.01em',
          borderBottom: '1px solid var(--adv-border)',
          paddingBottom: 12,
        }}
      >
        {titulo}
      </h3>
      {children}
    </div>
  )
}

function InputSlider({
  label,
  value,
  min,
  max,
  step,
  onChange,
  suffix,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
  suffix?: string
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
        }}
      >
        <label
          style={{
            fontSize: 12,
            color: 'var(--adv-text-muted)',
            fontWeight: 500,
          }}
        >
          {label}
        </label>
        <span
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: 'var(--adv-accent)',
          }}
        >
          {value.toLocaleString('es-ES')}
          {suffix ? ` ${suffix}` : ''}
        </span>
      </div>
      <input
        type="range"
        aria-label={label}
        title={label}
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{
          width: '100%',
          accentColor: 'var(--adv-accent)',
          cursor: 'pointer',
        }}
      />
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 10,
          color: 'var(--adv-text-muted)',
          opacity: 0.6,
        }}
      >
        <span>{min.toLocaleString('es-ES')}</span>
        <span>{max.toLocaleString('es-ES')}</span>
      </div>
    </div>
  )
}

function MetricaResultado({
  label,
  valor,
  color,
  grande,
}: {
  label: string
  valor: string
  color?: string
  grande?: boolean
}) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        padding: '10px 14px',
        background: 'var(--adv-surface-2)',
        borderRadius: 10,
      }}
    >
      <span style={{ fontSize: 11, color: 'var(--adv-text-muted)', fontWeight: 500 }}>
        {label}
      </span>
      <span
        style={{
          fontSize: grande ? 22 : 16,
          fontWeight: 800,
          color: color ?? 'var(--adv-text)',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {valor}
      </span>
    </div>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────

export default function SalaEstrategiaPage() {
  const { id: _empresaId } = useParams<{ id: string }>()

  // Parámetros base del negocio
  const [params, setParams] = useState<ParametrosSimulacion>({
    ventas_actuales: 25000,
    covers_dia: 80,
    precio_menu_actual: 20,
    food_cost_pct: 30,
    gasto_personal: 8000,
    gastos_fijos: 5000,
  })

  // Controles del escenario
  const [nuevoPrecio, setNuevoPrecio] = useState<number>(20)
  const [retencionPct, setRetencionPct] = useState<number>(85)

  function setParam<K extends keyof ParametrosSimulacion>(key: K, value: number) {
    setParams(prev => ({ ...prev, [key]: value }))
  }

  // Cálculo en tiempo real (sin API)
  const resultado: ResultadoSimulacion = useMemo(
    () => simular(params, nuevoPrecio, retencionPct),
    [params, nuevoPrecio, retencionPct],
  )

  const deltaPositivo = resultado.delta_ebitda >= 0
  const colorNuevo = resultado.ebitda_nuevo >= 0 ? 'var(--adv-verde)' : 'var(--adv-rojo)'
  const colorDelta = deltaPositivo ? 'var(--adv-verde)' : 'var(--adv-rojo)'

  const datosGrafico = [
    { nombre: 'EBITDA actual', valor: resultado.ebitda_actual },
    { nombre: 'EBITDA nuevo', valor: resultado.ebitda_nuevo },
  ]

  return (
    <div className="advisor-dark" style={{ minHeight: '100vh', padding: '24px' }}>
      {/* Cabecera */}
      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            margin: 0,
            fontSize: 22,
            fontWeight: 800,
            color: 'var(--adv-text)',
            letterSpacing: '-0.02em',
          }}
        >
          Sala de Estrategia
        </h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--adv-text-muted)' }}>
          Simulador what-if — impacto EBITDA en tiempo real
        </p>
      </div>

      {/* Grid de tres columnas */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 20,
          alignItems: 'start',
        }}
      >
        {/* PANEL IZQUIERDO — Parámetros base */}
        <Panel titulo="Parámetros del negocio">
          <InputSlider
            label="Ventas actuales (€/mes)"
            value={params.ventas_actuales}
            min={5000}
            max={100000}
            step={500}
            onChange={v => setParam('ventas_actuales', v)}
            suffix="€"
          />
          <InputSlider
            label="Covers / día"
            value={params.covers_dia}
            min={10}
            max={300}
            step={5}
            onChange={v => setParam('covers_dia', v)}
          />
          <InputSlider
            label="Precio menú actual (€)"
            value={params.precio_menu_actual}
            min={5}
            max={100}
            step={1}
            onChange={v => {
              setParam('precio_menu_actual', v)
              // Ajustar nuevo precio si coincidía con el anterior
              setNuevoPrecio(prev => (prev === params.precio_menu_actual ? v : prev))
            }}
            suffix="€"
          />
          <InputSlider
            label="Food cost %"
            value={params.food_cost_pct}
            min={10}
            max={60}
            step={1}
            onChange={v => setParam('food_cost_pct', v)}
            suffix="%"
          />
          <InputSlider
            label="Gasto personal (€/mes)"
            value={params.gasto_personal}
            min={1000}
            max={50000}
            step={500}
            onChange={v => setParam('gasto_personal', v)}
            suffix="€"
          />
          <InputSlider
            label="Gastos fijos (€/mes)"
            value={params.gastos_fijos}
            min={500}
            max={30000}
            step={500}
            onChange={v => setParam('gastos_fijos', v)}
            suffix="€"
          />
        </Panel>

        {/* PANEL CENTRAL — Controles del escenario */}
        <Panel titulo="Escenario a simular">
          <div
            style={{
              padding: '14px',
              background: 'var(--adv-surface-2)',
              borderRadius: 10,
              marginBottom: 4,
            }}
          >
            <p style={{ margin: '0 0 12px', fontSize: 12, color: 'var(--adv-text-muted)' }}>
              Ajusta los controles para ver el impacto instantáneo en el panel de resultados.
            </p>
          </div>

          <InputSlider
            label="Nuevo precio (€)"
            value={nuevoPrecio}
            min={10}
            max={50}
            step={0.5}
            onChange={v => setNuevoPrecio(v)}
            suffix="€"
          />

          <InputSlider
            label="Retención de clientes (%)"
            value={retencionPct}
            min={50}
            max={100}
            step={1}
            onChange={v => setRetencionPct(v)}
            suffix="%"
          />

          {/* Resumen del escenario */}
          <div
            style={{
              padding: '14px',
              background: 'var(--adv-surface-2)',
              borderRadius: 10,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              marginTop: 8,
            }}
          >
            <h4
              style={{
                margin: 0,
                fontSize: 12,
                fontWeight: 700,
                color: 'var(--adv-text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Resumen del escenario
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                <span style={{ color: 'var(--adv-text-muted)' }}>Precio actual</span>
                <span style={{ color: 'var(--adv-text)', fontWeight: 600 }}>
                  {params.precio_menu_actual} €
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                <span style={{ color: 'var(--adv-text-muted)' }}>Precio nuevo</span>
                <span style={{ color: 'var(--adv-accent)', fontWeight: 700 }}>
                  {nuevoPrecio} €
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                <span style={{ color: 'var(--adv-text-muted)' }}>Δ precio</span>
                <span
                  style={{
                    fontWeight: 700,
                    color:
                      nuevoPrecio >= params.precio_menu_actual
                        ? 'var(--adv-verde)'
                        : 'var(--adv-rojo)',
                  }}
                >
                  {fmtSigEur(nuevoPrecio - params.precio_menu_actual)}
                </span>
              </div>
              <hr style={{ margin: '4px 0', border: 'none', borderTop: '1px solid var(--adv-border)' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                <span style={{ color: 'var(--adv-text-muted)' }}>Covers retenidos/día</span>
                <span style={{ color: 'var(--adv-text)', fontWeight: 600 }}>
                  {resultado.covers_retenidos} de {params.covers_dia}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                <span style={{ color: 'var(--adv-text-muted)' }}>Ventas nuevas/mes</span>
                <span style={{ color: 'var(--adv-text)', fontWeight: 600 }}>
                  {fmtEur(resultado.ventas_nuevas)}
                </span>
              </div>
            </div>
          </div>
        </Panel>

        {/* PANEL DERECHO — Resultados en tiempo real */}
        <Panel titulo="Resultados en tiempo real">
          <MetricaResultado
            label="EBITDA actual"
            valor={fmtEur(resultado.ebitda_actual)}
            color={resultado.ebitda_actual >= 0 ? 'var(--adv-text)' : 'var(--adv-rojo)'}
          />
          <MetricaResultado
            label="EBITDA nuevo"
            valor={fmtEur(resultado.ebitda_nuevo)}
            color={colorNuevo}
            grande
          />

          {/* Delta EBITDA */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 14px',
              background: deltaPositivo ? 'rgba(52,211,153,0.08)' : 'rgba(248,113,113,0.08)',
              border: `1px solid ${deltaPositivo ? 'var(--adv-verde)' : 'var(--adv-rojo)'}`,
              borderRadius: 10,
            }}
          >
            {deltaPositivo ? (
              <TrendingUp size={20} color="var(--adv-verde)" />
            ) : (
              <TrendingDown size={20} color="var(--adv-rojo)" />
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <span style={{ fontSize: 11, color: 'var(--adv-text-muted)', fontWeight: 500 }}>
                Δ EBITDA mensual
              </span>
              <span style={{ fontSize: 18, fontWeight: 800, color: colorDelta, fontVariantNumeric: 'tabular-nums' }}>
                {fmtSigEur(resultado.delta_ebitda)}
              </span>
            </div>
          </div>

          {/* Break-even */}
          <div
            style={{
              padding: '10px 14px',
              background: 'var(--adv-surface-2)',
              borderRadius: 10,
            }}
          >
            <span style={{ fontSize: 11, color: 'var(--adv-text-muted)', fontWeight: 500 }}>
              Break-even
            </span>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--adv-text)', marginTop: 4 }}>
              {resultado.break_even_dias_menos === 0
                ? 'Sin cambios'
                : resultado.break_even_dias_menos > 0
                  ? `${resultado.break_even_dias_menos} días menos`
                  : `${Math.abs(resultado.break_even_dias_menos)} días más`}
            </div>
          </div>

          {/* Gráfico comparativo EBITDA */}
          <div style={{ marginTop: 4 }}>
            <p
              style={{
                margin: '0 0 8px',
                fontSize: 11,
                color: 'var(--adv-text-muted)',
                fontWeight: 500,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              EBITDA: actual vs nuevo
            </p>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart
                data={datosGrafico}
                margin={{ top: 4, right: 8, left: 8, bottom: 4 }}
                barCategoryGap="30%"
              >
                <CartesianGrid
                  vertical={false}
                  stroke="var(--adv-border)"
                  strokeDasharray="3 3"
                />
                <XAxis
                  dataKey="nombre"
                  tick={{ fill: 'var(--adv-text-muted)', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: 'var(--adv-text-muted)', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={v => `${(v / 1000).toFixed(0)}k`}
                  width={32}
                />
                <Tooltip
                  contentStyle={{
                    background: 'var(--adv-surface)',
                    border: '1px solid var(--adv-border)',
                    borderRadius: 8,
                    fontSize: 12,
                    color: 'var(--adv-text)',
                  }}
                  formatter={(value: number | undefined) => [fmtEur(value ?? 0), 'EBITDA']}
                />
                <Bar dataKey="valor" radius={[6, 6, 0, 0]}>
                  {datosGrafico.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={
                        index === 0
                          ? 'var(--adv-text-muted)'
                          : entry.valor >= 0
                            ? 'var(--adv-verde)'
                            : 'var(--adv-rojo)'
                      }
                      opacity={index === 0 ? 0.5 : 1}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>
    </div>
  )
}
