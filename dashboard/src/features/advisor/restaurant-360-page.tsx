// dashboard/src/features/advisor/restaurant-360-page.tsx
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Legend,
  ComposedChart, Cell,
} from 'recharts'
import { TrendingUp, TrendingDown, Users, Utensils, DollarSign, BarChart2 } from 'lucide-react'
import { advisorApi } from './api'
import type { VentasDetalle } from './types'

// ─── utilidades ─────────────────────────────────────────────────────────────

function fmt(n: number, decimals = 0): string {
  return n.toLocaleString('es-ES', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

function fmtEur(n: number): string {
  return `${fmt(n, 2)} €`
}

// ─── hook: contador animado ──────────────────────────────────────────────────

function useAnimatedCounter(target: number, duration = 900, decimals = 0): number {
  const [value, setValue] = useState(0)
  const factor = Math.pow(10, decimals)
  useEffect(() => {
    if (target === 0) { setValue(0); return }
    const start = Date.now()
    const tick = () => {
      const elapsed = Date.now() - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(target * eased * factor) / factor)
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [target, duration, factor])
  return value
}

// ─── ZONA 1: PulsoHoy ────────────────────────────────────────────────────────

interface KPICardProps {
  label: string
  value: number
  prefix?: string
  suffix?: string
  decimals?: number
  variacion?: number
  icon: React.ReactNode
  benchmark?: number
  benchmarkLabel?: string
}

function KPICard({ label, value, prefix = '', suffix = '', decimals = 0, variacion, icon, benchmark, benchmarkLabel }: KPICardProps) {
  const animated = useAnimatedCounter(value, 900, decimals)
  const color = variacion !== undefined ? (variacion >= 0 ? 'var(--adv-verde)' : 'var(--adv-rojo)') : 'var(--adv-text)'

  return (
    <div style={{
      background: 'var(--adv-surface)',
      border: '1px solid var(--adv-border)',
      borderRadius: 12,
      padding: '18px 20px',
      flex: 1,
      minWidth: 0,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ color: 'var(--adv-text-muted)', fontSize: 12, fontWeight: 500 }}>{label}</span>
        <span style={{ color: 'var(--adv-accent)', opacity: 0.8 }}>{icon}</span>
      </div>
      <div style={{ fontFamily: 'var(--adv-font-data)', fontSize: 28, fontWeight: 700, color: 'var(--adv-text)', marginBottom: 6 }}>
        {prefix}{fmt(animated, decimals)}{suffix}
      </div>
      {variacion !== undefined && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color }}>
          {variacion >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          <span>{variacion >= 0 ? '+' : ''}{variacion.toFixed(1)}% vs semana anterior</span>
        </div>
      )}
      {benchmark !== undefined && (
        <div style={{ marginTop: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--adv-text-muted)', marginBottom: 3 }}>
            <span>{benchmarkLabel ?? 'Benchmark sector'}</span>
            <span>{fmt(benchmark, decimals)}{suffix}</span>
          </div>
          <div style={{ height: 4, borderRadius: 2, background: 'var(--adv-surface-2)', overflow: 'hidden' }}>
            <div style={{
              width: `${Math.min((value / benchmark) * 100, 120)}%`,
              maxWidth: '100%',
              height: '100%',
              background: value >= benchmark ? 'var(--adv-verde)' : 'var(--adv-accent)',
              transition: 'width 0.8s ease',
            }} />
          </div>
        </div>
      )}
    </div>
  )
}

function PulsoHoy({ empresaId }: { empresaId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ['resumen-hoy', empresaId],
    queryFn: () => advisorApi.resumenHoy(empresaId),
    refetchInterval: 60_000,
  })

  if (isLoading) return <ZonaSkeleton label="PulsoHoy" />

  const hoy = data?.hoy ?? { ventas: 0, covers: 0, ticket_medio: 0 }
  const variacion = data?.variacion_vs_ayer_pct ?? 0
  const HORAS_APERTURA = 8 // horas operativas estandar hosteleria
  const revpash = hoy.covers > 0 ? hoy.ventas / (hoy.covers * HORAS_APERTURA) : 0

  return (
    <Zona titulo="Pulso de Hoy" subtitulo="Tiempo real vs misma franja semana anterior">
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <KPICard label="Facturación acumulada" value={hoy.ventas} prefix="€ " decimals={2}
          variacion={variacion} icon={<DollarSign size={16} />} />
        <KPICard label="Covers" value={hoy.covers}
          variacion={variacion} icon={<Users size={16} />} />
        <KPICard label="Ticket medio" value={hoy.ticket_medio} prefix="€ " decimals={2}
          icon={<Utensils size={16} />} benchmark={18} benchmarkLabel="Benchmark sector" />
        <KPICard label="RevPASH" value={revpash} suffix=" €/h"
          decimals={2} icon={<BarChart2 size={16} />} benchmark={12} benchmarkLabel="RevPASH sector p50" />
      </div>
      {(data?.alertas ?? []).length > 0 && (
        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {data!.alertas.map(a => (
            <div key={a.id} style={{
              padding: '8px 12px', borderRadius: 8, fontSize: 12,
              background: a.severidad === 'alta' ? 'rgba(239,68,68,0.12)' : a.severidad === 'media' ? 'rgba(245,158,11,0.12)' : 'rgba(16,185,129,0.12)',
              color: a.severidad === 'alta' ? 'var(--adv-rojo)' : a.severidad === 'media' ? 'var(--adv-accent)' : 'var(--adv-verde)',
              borderLeft: `3px solid ${a.severidad === 'alta' ? 'var(--adv-rojo)' : a.severidad === 'media' ? 'var(--adv-accent)' : 'var(--adv-verde)'}`,
            }}>
              {a.mensaje}
            </div>
          ))}
        </div>
      )}
    </Zona>
  )
}

// ─── ZONA 2: HeatmapSemanal (D3) ─────────────────────────────────────────────

interface CeldaHeatmap { dia: string; servicio: string; covers: number }

const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
const SERVICIOS = ['Almuerzo', 'Cena']

const DATOS_HEATMAP: CeldaHeatmap[] = [
  { dia: 'Lun', servicio: 'Almuerzo', covers: 42 },
  { dia: 'Lun', servicio: 'Cena', covers: 38 },
  { dia: 'Mar', servicio: 'Almuerzo', covers: 45 },
  { dia: 'Mar', servicio: 'Cena', covers: 40 },
  { dia: 'Mié', servicio: 'Almuerzo', covers: 51 },
  { dia: 'Mié', servicio: 'Cena', covers: 55 },
  { dia: 'Jue', servicio: 'Almuerzo', covers: 48 },
  { dia: 'Jue', servicio: 'Cena', covers: 62 },
  { dia: 'Vie', servicio: 'Almuerzo', covers: 70 },
  { dia: 'Vie', servicio: 'Cena', covers: 95 },
  { dia: 'Sáb', servicio: 'Almuerzo', covers: 110 },
  { dia: 'Sáb', servicio: 'Cena', covers: 130 },
  { dia: 'Dom', servicio: 'Almuerzo', covers: 120 },
  { dia: 'Dom', servicio: 'Cena', covers: 60 },
]

function HeatmapSemanal() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.offsetWidth
    const H = canvas.offsetHeight
    canvas.width = W
    canvas.height = H

    const padLeft = 72
    const padTop = 28
    const padRight = 16
    const padBottom = 20

    const cellW = (W - padLeft - padRight) / DIAS.length
    const cellH = (H - padTop - padBottom) / SERVICIOS.length

    const maxCovers = Math.max(...DATOS_HEATMAP.map(d => d.covers))

    ctx.clearRect(0, 0, W, H)

    // encabezados columnas
    ctx.fillStyle = '#9ca3af'
    ctx.font = '11px system-ui, sans-serif'
    ctx.textAlign = 'center'
    DIAS.forEach((dia, i) => {
      ctx.fillText(dia, padLeft + i * cellW + cellW / 2, padTop - 8)
    })

    // encabezados filas
    ctx.textAlign = 'right'
    SERVICIOS.forEach((srv, j) => {
      ctx.fillText(srv, padLeft - 8, padTop + j * cellH + cellH / 2 + 4)
    })

    // celdas
    DATOS_HEATMAP.forEach(({ dia, servicio, covers }) => {
      const i = DIAS.indexOf(dia)
      const j = SERVICIOS.indexOf(servicio)
      if (i < 0 || j < 0) return
      const intensity = covers / maxCovers
      const x = padLeft + i * cellW + 2
      const y = padTop + j * cellH + 2
      const w = cellW - 4
      const h = cellH - 4

      // color: azul oscuro → ámbar
      const r = Math.round(59 + (245 - 59) * intensity)
      const g = Math.round(130 + (158 - 130) * intensity * 0.6)
      const b = Math.round(246 - 246 * intensity)
      ctx.fillStyle = `rgba(${r},${g},${b},${0.3 + intensity * 0.7})`
      ctx.beginPath()
      ctx.roundRect(x, y, w, h, 6)
      ctx.fill()

      // valor
      ctx.fillStyle = intensity > 0.5 ? '#f9fafb' : '#9ca3af'
      ctx.textAlign = 'center'
      ctx.font = `bold ${Math.min(12, cellH * 0.35)}px system-ui`
      ctx.fillText(String(covers), x + w / 2, y + h / 2 + 4)
    })
  }, [])

  return (
    <Zona titulo="Heatmap Semanal" subtitulo="Intensidad de covers por día y servicio">
      <div style={{ position: 'relative', height: 160 }}>
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
      </div>
    </Zona>
  )
}

// ─── ZONA 3: TopVentas ────────────────────────────────────────────────────────

function TopVentas({ empresaId }: { empresaId: number }) {
  const hoy = new Date()
  const desde = new Date(hoy.getFullYear(), hoy.getMonth(), 1).toISOString().split('T')[0]
  const hasta = hoy.toISOString().split('T')[0]

  const { data, isLoading } = useQuery<VentasDetalle>({
    queryKey: ['ventas-detalle', empresaId, desde, hasta],
    queryFn: () => advisorApi.ventasDetalle(empresaId, desde, hasta),
  })

  if (isLoading) return <ZonaSkeleton label="Top Ventas" />

  const productos = (data?.top_productos ?? []).slice(0, 8)
  const maxTotal = Math.max(...productos.map(p => p.total), 1)

  return (
    <Zona titulo="Top Ventas" subtitulo="Productos más vendidos este mes por facturación">
      {productos.length === 0 ? (
        <p style={{ color: 'var(--adv-text-muted)', fontSize: 13 }}>Sin datos de ventas disponibles</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {productos.map((p, idx) => (
            <div key={p.nombre}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: 'var(--adv-text)', fontWeight: idx === 0 ? 700 : 400 }}>
                  {idx + 1}. {p.nombre}
                </span>
                <span style={{ color: 'var(--adv-text-muted)', fontFamily: 'var(--adv-font-data)' }}>
                  {fmtEur(p.total)} · {p.qty} uds
                </span>
              </div>
              <div style={{ height: 6, borderRadius: 3, background: 'var(--adv-surface-2)', overflow: 'hidden' }}>
                <div style={{
                  width: `${(p.total / maxTotal) * 100}%`,
                  height: '100%',
                  background: idx === 0 ? 'var(--adv-accent)' : 'var(--adv-azul)',
                  transition: 'width 0.6s ease',
                }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </Zona>
  )
}

// ─── ZONA 4: WaterfallPL ─────────────────────────────────────────────────────

interface WaterfallEntry {
  nombre: string
  valor: number
  inicio: number
  color: string
  esTotal?: boolean
}

const PL_DEMO: Omit<WaterfallEntry, 'inicio'>[] = [
  { nombre: 'Ventas', valor: 85000, color: 'var(--adv-verde)' },
  { nombre: 'Materia Prima', valor: -28000, color: 'var(--adv-rojo)' },
  { nombre: 'Personal', valor: -22000, color: 'var(--adv-rojo)' },
  { nombre: 'Generales', valor: -8000, color: 'var(--adv-rojo)' },
  { nombre: 'EBITDA', valor: 27000, color: 'var(--adv-accent)', esTotal: true },
]

function buildWaterfall(): WaterfallEntry[] {
  let acum = 0
  return PL_DEMO.map(e => {
    if (e.esTotal) return { ...e, inicio: 0 }
    const inicio = e.valor < 0 ? acum + e.valor : acum
    acum += e.valor
    return { ...e, inicio }
  })
}

interface WaterfallTooltipProps {
  active?: boolean
  payload?: Array<{ payload: WaterfallEntry }>
}

function WaterfallTooltip({ active, payload }: WaterfallTooltipProps) {
  if (!active || !payload?.length || !payload[0]) return null
  const d = payload[0].payload
  return (
    <div style={{
      background: 'var(--adv-surface)', border: '1px solid var(--adv-border)',
      borderRadius: 8, padding: '8px 12px', fontSize: 12, color: 'var(--adv-text)',
    }}>
      <div style={{ fontWeight: 700 }}>{d.nombre}</div>
      <div style={{ color: d.valor < 0 ? 'var(--adv-rojo)' : 'var(--adv-verde)', fontFamily: 'var(--adv-font-data)' }}>
        {d.valor > 0 ? '+' : ''}{fmtEur(d.valor)}
      </div>
    </div>
  )
}

function WaterfallPL() {
  const datos = buildWaterfall()

  return (
    <Zona titulo="Cuenta de Resultados" subtitulo="Waterfall P&L mensual (demo)">
      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart data={datos} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
          <XAxis dataKey="nombre" tick={{ fill: 'var(--adv-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: 'var(--adv-text-muted)', fontSize: 10 }} axisLine={false} tickLine={false}
            tickFormatter={v => `${Math.round(v / 1000)}k`} />
          <Tooltip content={<WaterfallTooltip />} />
          {/* barra invisible de soporte */}
          <Bar dataKey="inicio" stackId="wf" fill="transparent" />
          <Bar dataKey="valor" stackId="wf" radius={[4, 4, 0, 0]}>
            {datos.map((d, i) => (
              <Cell key={i} fill={d.color} fillOpacity={d.esTotal ? 1 : 0.85} />
            ))}
          </Bar>
        </ComposedChart>
      </ResponsiveContainer>
    </Zona>
  )
}

// ─── ZONA 5: ComparativaHistorica ─────────────────────────────────────────────

type Periodo = 'mes' | 'trimestre' | 'año'

const HISTORICO_DEMO = [
  { periodo: 'Ene', esteAno: 68000, anteriorAno: 61000 },
  { periodo: 'Feb', esteAno: 72000, anteriorAno: 64000 },
  { periodo: 'Mar', esteAno: 85000, anteriorAno: 70000 },
  { periodo: 'Abr', esteAno: 91000, anteriorAno: 75000 },
  { periodo: 'May', esteAno: 105000, anteriorAno: 88000 },
  { periodo: 'Jun', esteAno: 118000, anteriorAno: 97000 },
  { periodo: 'Jul', esteAno: 130000, anteriorAno: 110000 },
  { periodo: 'Ago', esteAno: 125000, anteriorAno: 105000 },
  { periodo: 'Sep', esteAno: 98000, anteriorAno: 85000 },
  { periodo: 'Oct', esteAno: 88000, anteriorAno: 78000 },
  { periodo: 'Nov', esteAno: 75000, anteriorAno: 68000 },
  { periodo: 'Dic', esteAno: 92000, anteriorAno: 82000 },
]

const TRIMESTRAL_DEMO = [
  { periodo: 'Q1', esteAno: 225000, anteriorAno: 195000 },
  { periodo: 'Q2', esteAno: 314000, anteriorAno: 260000 },
  { periodo: 'Q3', esteAno: 353000, anteriorAno: 300000 },
  { periodo: 'Q4', esteAno: 255000, anteriorAno: 228000 },
]

function datosParaPeriodo(p: Periodo) {
  if (p === 'trimestre') return TRIMESTRAL_DEMO
  if (p === 'año') return [{ periodo: 'Este año', esteAno: 1147000, anteriorAno: 983000 }]
  return HISTORICO_DEMO
}

function ComparativaHistorica() {
  const [periodo, setPeriodo] = useState<Periodo>('mes')
  const datos = datosParaPeriodo(periodo)

  return (
    <Zona titulo="Comparativa Histórica" subtitulo="Este año vs año anterior">
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        {(['mes', 'trimestre', 'año'] as Periodo[]).map(p => (
          <button
            key={p}
            onClick={() => setPeriodo(p)}
            style={{
              fontSize: 11, padding: '4px 10px', borderRadius: 6, cursor: 'pointer', border: 'none',
              background: periodo === p ? 'var(--adv-accent)' : 'var(--adv-surface-2)',
              color: periodo === p ? '#0a0e1a' : 'var(--adv-text-muted)',
              fontWeight: periodo === p ? 700 : 400,
            }}
          >
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </button>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={datos} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--adv-border)" />
          <XAxis dataKey="periodo" tick={{ fill: 'var(--adv-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: 'var(--adv-text-muted)', fontSize: 10 }} axisLine={false} tickLine={false}
            tickFormatter={v => `${Math.round(v / 1000)}k€`} />
          <Tooltip
            contentStyle={{ background: 'var(--adv-surface)', border: '1px solid var(--adv-border)', borderRadius: 8 }}
            labelStyle={{ color: 'var(--adv-text)', fontSize: 12 }}
            itemStyle={{ fontSize: 12 }}
            formatter={(value: number | undefined) => (value !== undefined ? fmtEur(value) : '')}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: 'var(--adv-text-muted)' }} />
          <Line type="monotone" dataKey="esteAno" name="Este año" stroke="var(--adv-accent)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
          <Line type="monotone" dataKey="anteriorAno" name="Año anterior" stroke="var(--adv-azul)" strokeWidth={2} strokeDasharray="5 5" dot={false} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </Zona>
  )
}

// ─── Componentes de layout ───────────────────────────────────────────────────

function Zona({ titulo, subtitulo, children }: { titulo: string; subtitulo?: string; children: React.ReactNode }) {
  return (
    <section style={{
      background: 'var(--adv-surface)',
      border: '1px solid var(--adv-border)',
      borderRadius: 14,
      padding: '20px 22px',
    }}>
      <div style={{ marginBottom: 14 }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: 'var(--adv-text)', letterSpacing: '-0.01em' }}>
          {titulo}
        </h3>
        {subtitulo && (
          <p style={{ margin: '3px 0 0', fontSize: 11, color: 'var(--adv-text-muted)' }}>{subtitulo}</p>
        )}
      </div>
      {children}
    </section>
  )
}

function ZonaSkeleton({ label }: { label: string }) {
  return (
    <section style={{
      background: 'var(--adv-surface)', border: '1px solid var(--adv-border)',
      borderRadius: 14, padding: '20px 22px',
    }}>
      <div style={{ color: 'var(--adv-text-muted)', fontSize: 13 }}>{label} — cargando…</div>
      <div style={{ marginTop: 12, height: 80, borderRadius: 8, background: 'var(--adv-surface-2)', opacity: 0.5 }} />
    </section>
  )
}

// ─── PÁGINA PRINCIPAL ────────────────────────────────────────────────────────

export default function Restaurant360Page() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id ?? 0)

  return (
    <div className="advisor-dark" style={{
      minHeight: '100vh',
      background: 'var(--adv-bg)',
      color: 'var(--adv-text)',
      padding: '24px',
    }}>
      {/* Cabecera */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: 'var(--adv-text)', letterSpacing: '-0.02em' }}>
          Restaurant 360°
        </h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--adv-text-muted)' }}>
          Dashboard operativo hostelería — empresa #{empresaId}
        </p>
      </div>

      {/* Grid 5 zonas */}
      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: '1fr', maxWidth: 1400 }}>
        {/* Zona 1: PulsoHoy — fila completa */}
        <PulsoHoy empresaId={empresaId} />

        {/* Zona 2 + Zona 3 — lado a lado */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <HeatmapSemanal />
          <TopVentas empresaId={empresaId} />
        </div>

        {/* Zona 4 + Zona 5 — lado a lado */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <WaterfallPL />
          <ComparativaHistorica />
        </div>
      </div>
    </div>
  )
}
