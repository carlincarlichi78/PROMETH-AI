// dashboard/src/features/advisor/product-intelligence-page.tsx
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine,
  PieChart, Pie, Cell,
} from 'recharts'
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react'
import { advisorApi } from './api'
import type { VentasDetalle, CompraProveedor, ProductoVenta } from './types'

// ─── utilidades ──────────────────────────────────────────────────────────────

function fmt(n: number, decimals = 0): string {
  return n.toLocaleString('es-ES', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

function fmtEur(n: number): string {
  return `${fmt(n, 2)} €`
}

// ─── Layout ──────────────────────────────────────────────────────────────────

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

// ─── COMPONENTE 1: MatrizBCG ──────────────────────────────────────────────────

interface PuntoProducto {
  nombre: string
  qty: number
  pvp: number  // precio medio unitario como proxy de margen
  familia: string
}

function deriveProductos(detalle: VentasDetalle | undefined): PuntoProducto[] {
  if (!detalle?.top_productos?.length) {
    // datos demo cuando no hay respuesta real
    return [
      { nombre: 'Paella Valenciana', qty: 320, pvp: 18.5, familia: 'Arroces' },
      { nombre: 'Croquetas', qty: 580, pvp: 8.2, familia: 'Entrantes' },
      { nombre: 'Dorada a la sal', qty: 140, pvp: 24.0, familia: 'Pescados' },
      { nombre: 'Tarta de queso', qty: 290, pvp: 6.5, familia: 'Postres' },
      { nombre: 'Gazpacho', qty: 95, pvp: 5.0, familia: 'Entrantes' },
      { nombre: 'Solomillo Ibérico', qty: 180, pvp: 28.0, familia: 'Carnes' },
      { nombre: 'Ensalada César', qty: 410, pvp: 9.8, familia: 'Ensaladas' },
      { nombre: 'Mousse Chocolate', qty: 70, pvp: 5.5, familia: 'Postres' },
    ]
  }
  return detalle.top_productos.map((p: ProductoVenta) => ({
    nombre: p.nombre,
    qty: p.qty,
    pvp: p.qty > 0 ? p.total / p.qty : 0,
    familia: p.familia,
  }))
}

const COLORES_FAMILIA: Record<string, string> = {
  Arroces: '#f59e0b',
  Entrantes: '#3b82f6',
  Pescados: '#10b981',
  Postres: '#8b5cf6',
  Carnes: '#ef4444',
  Ensaladas: '#06b6d4',
}

function colorFamilia(familia: string): string {
  return COLORES_FAMILIA[familia] ?? '#9ca3af'
}

function MatrizBCG({ empresaId }: { empresaId: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const hoy = new Date()
  const desde = new Date(hoy.getFullYear(), hoy.getMonth() - 2, 1).toISOString().split('T')[0]
  const hasta = hoy.toISOString().split('T')[0]

  const { data, isLoading } = useQuery<VentasDetalle>({
    queryKey: ['ventas-detalle-bcg', empresaId, desde, hasta],
    queryFn: () => advisorApi.ventasDetalle(empresaId, desde, hasta),
  })

  const productos = deriveProductos(data)
  const maxQty = Math.max(...productos.map(p => p.qty), 1)
  const maxPvp = Math.max(...productos.map(p => p.pvp), 1)
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !productos.length) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.offsetWidth || 500
    const H = canvas.offsetHeight || 360
    const dpr = window.devicePixelRatio || 1
    canvas.width = W * dpr
    canvas.height = H * dpr
    ctx.scale(dpr, dpr)

    const padL = 56, padR = 16, padT = 40, padB = 36
    const plotW = W - padL - padR
    const plotH = H - padT - padB

    ctx.clearRect(0, 0, W, H)

    // fondo cuadrantes
    const cuadrantes: { x: number; y: number; w: number; h: number; label: string; bg: string }[] = [
      { x: padL + plotW / 2, y: padT, w: plotW / 2, h: plotH / 2, label: 'Estrellas', bg: 'rgba(245,158,11,0.07)' },
      { x: padL, y: padT, w: plotW / 2, h: plotH / 2, label: 'Vacas Lecheras', bg: 'rgba(16,185,129,0.07)' },
      { x: padL + plotW / 2, y: padT + plotH / 2, w: plotW / 2, h: plotH / 2, label: 'Pesos Muertos', bg: 'rgba(239,68,68,0.07)' },
      { x: padL, y: padT + plotH / 2, w: plotW / 2, h: plotH / 2, label: 'Perros', bg: 'rgba(156,163,175,0.07)' },
    ]
    cuadrantes.forEach(q => {
      ctx.fillStyle = q.bg
      ctx.fillRect(q.x, q.y, q.w, q.h)
      ctx.fillStyle = 'rgba(156,163,175,0.5)'
      ctx.font = '10px system-ui, sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(q.label, q.x + 6, q.y + 14)
    })

    // ejes
    ctx.strokeStyle = '#374151'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(padL, padT)
    ctx.lineTo(padL, padT + plotH)
    ctx.lineTo(padL + plotW, padT + plotH)
    ctx.stroke()

    // líneas medias (separadores cuadrantes)
    ctx.setLineDash([4, 4])
    ctx.strokeStyle = 'rgba(55,65,81,0.8)'
    ctx.beginPath()
    ctx.moveTo(padL + plotW / 2, padT)
    ctx.lineTo(padL + plotW / 2, padT + plotH)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(padL, padT + plotH / 2)
    ctx.lineTo(padL + plotW, padT + plotH / 2)
    ctx.stroke()
    ctx.setLineDash([])

    // labels ejes
    ctx.fillStyle = '#9ca3af'
    ctx.font = '10px system-ui, sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('Volumen (uds)', padL + plotW / 2, padT + plotH + 28)
    ctx.save()
    ctx.translate(14, padT + plotH / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.fillText('PVP unitario (€)', 0, 0)
    ctx.restore()

    // puntos
    productos.forEach(p => {
      const x = padL + (p.qty / maxQty) * plotW
      const y = padT + plotH - (p.pvp / maxPvp) * plotH
      const r = 7

      ctx.beginPath()
      ctx.arc(x, y, r, 0, Math.PI * 2)
      ctx.fillStyle = colorFamilia(p.familia)
      ctx.globalAlpha = 0.85
      ctx.fill()
      ctx.globalAlpha = 1
      ctx.strokeStyle = 'rgba(255,255,255,0.3)'
      ctx.lineWidth = 1
      ctx.stroke()

      // etiqueta
      const maxW = 80
      const label = p.nombre.length > 12 ? p.nombre.slice(0, 11) + '…' : p.nombre
      ctx.fillStyle = '#f9fafb'
      ctx.font = '9px system-ui, sans-serif'
      ctx.textAlign = x + maxW > W ? 'right' : 'left'
      const offsetX = x + maxW > W ? -r - 3 : r + 3
      ctx.fillText(label, x + offsetX, y - 2)
    })
  }, [productos, maxQty, maxPvp])

  if (isLoading) return <ZonaSkeleton label="Matriz BCG" />

  return (
    <Zona titulo="Matriz BCG Productos" subtitulo="Volumen vs PVP unitario — cuadrantes por posición competitiva">
      <div style={{ position: 'relative', height: 360 }}>
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
      </div>
      {/* leyenda familias */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 14px', marginTop: 10 }}>
        {[...new Set(productos.map(p => p.familia))].map(f => (
          <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--adv-text-muted)' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: colorFamilia(f) }} />
            {f}
          </div>
        ))}
      </div>
    </Zona>
  )
}

// ─── COMPONENTE 2: FoodCostEvolucion ─────────────────────────────────────────

const FOOD_COST_DEMO = [
  { mes: 'Oct', foodCost: 32.4 },
  { mes: 'Nov', foodCost: 31.1 },
  { mes: 'Dic', foodCost: 29.8 },
  { mes: 'Ene', foodCost: 28.5 },
  { mes: 'Feb', foodCost: 30.2 },
  { mes: 'Mar', foodCost: 31.8 },
]

interface FoodCostTooltipProps {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
}

function FoodCostTooltipContent({ active, payload, label }: FoodCostTooltipProps) {
  if (!active || !payload?.length || payload[0] === undefined) return null
  const valor = payload[0].value
  return (
    <div style={{
      background: 'var(--adv-surface)', border: '1px solid var(--adv-border)',
      borderRadius: 8, padding: '8px 12px', fontSize: 12, color: 'var(--adv-text)',
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
      <div style={{ fontFamily: 'var(--adv-font-data)', color: valor > 30 ? 'var(--adv-rojo)' : 'var(--adv-verde)' }}>
        Food Cost: {fmt(valor, 1)}%
      </div>
      <div style={{ color: 'var(--adv-text-muted)', fontSize: 10, marginTop: 3 }}>
        Benchmark: 30%
      </div>
    </div>
  )
}

function FoodCostEvolucion({ empresaId }: { empresaId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ['compras-fc', empresaId],
    queryFn: () => advisorApi.comprasProveedores(empresaId, 6),
  })

  // TODO: reemplazar con datos reales cuando el endpoint devuelva food_cost_pct mensual
  const chartData = FOOD_COST_DEMO
  const tieneDatos = (data?.proveedores?.length ?? 0) > 0

  if (isLoading) return <ZonaSkeleton label="Food Cost" />

  return (
    <Zona titulo="Food Cost %" subtitulo="Evolución mensual — benchmark sector 30%">
      {!tieneDatos && (
        <p style={{ fontSize: 10, color: 'var(--adv-text-muted)', marginBottom: 8, marginTop: -8 }}>
          Datos de demo — conecta compras reales para cálculo automático
        </p>
      )}
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--adv-border)" />
          <XAxis dataKey="mes" tick={{ fill: 'var(--adv-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fill: 'var(--adv-text-muted)', fontSize: 10 }}
            axisLine={false} tickLine={false}
            tickFormatter={v => `${v}%`}
            domain={[20, 40]}
          />
          <Tooltip content={<FoodCostTooltipContent />} />
          <ReferenceLine y={30} stroke="var(--adv-accent)" strokeDasharray="6 3" strokeWidth={1.5}
            label={{ value: 'Benchmark 30%', position: 'insideTopRight', fill: 'var(--adv-accent)', fontSize: 10 }} />
          <Line
            type="monotone" dataKey="foodCost" name="Food Cost %"
            stroke="var(--adv-azul)" strokeWidth={2}
            dot={{ fill: 'var(--adv-azul)', r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Zona>
  )
}

// ─── COMPONENTE 3: HistorialCompras ──────────────────────────────────────────

interface MiniSparklineProps {
  valores: number[]
  tendencia: 'up' | 'down' | 'flat'
}

function MiniSparkline({ valores, tendencia }: MiniSparklineProps) {
  if (valores.length < 2) return null
  const W = 60
  const H = 20
  const min = Math.min(...valores)
  const max = Math.max(...valores)
  const rango = max - min || 1
  const paso = W / (valores.length - 1)

  const puntos = valores.map((v, i) => {
    const x = i * paso
    const y = H - ((v - min) / rango) * (H - 2) - 1
    return `${x},${y}`
  }).join(' ')

  const color = tendencia === 'up'
    ? 'var(--adv-verde)'
    : tendencia === 'down'
    ? 'var(--adv-rojo)'
    : 'var(--adv-text-muted)'

  return (
    <svg width={W} height={H} style={{ display: 'block', overflow: 'visible' }}>
      <polyline
        points={puntos}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}

function sparklineDesdeMeses(meses: Record<string, number>, pct: number): MiniSparklineProps {
  const claves = Object.keys(meses).sort()
  const valores = claves.length >= 2 ? claves.map(k => meses[k] ?? 0) : []
  const tendencia: 'up' | 'down' | 'flat' = pct > 2 ? 'up' : pct < -2 ? 'down' : 'flat'
  return { valores, tendencia }
}

function indicadorMoM(pct: number): React.ReactNode {
  const alerta = Math.abs(pct) > 15
  if (pct > 2) return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 3, color: alerta ? 'var(--adv-rojo)' : 'var(--adv-accent)', fontSize: 11 }}>
      {alerta && <AlertTriangle size={11} />}
      <TrendingUp size={11} />
      +{fmt(pct, 1)}%
    </span>
  )
  if (pct < -2) return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 3, color: 'var(--adv-verde)', fontSize: 11 }}>
      <TrendingDown size={11} />
      {fmt(pct, 1)}%
    </span>
  )
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 3, color: 'var(--adv-text-muted)', fontSize: 11 }}>
      <Minus size={11} />
      {fmt(pct, 1)}%
    </span>
  )
}

const COMPRAS_DEMO: CompraProveedor[] = [
  { nombre: 'Makro', familia: 'Alimentación', meses: { '2024-10': 1280, '2024-11': 1350, '2024-12': 1400, '2025-01': 1420, '2025-02': 1490, '2025-03': 1460 }, total: 8400, variacion_mom_pct: 3.2 },
  { nombre: 'Pescaderías del Sur', familia: 'Pescados', meses: { '2024-10': 420, '2024-11': 440, '2024-12': 390, '2025-01': 500, '2025-02': 580, '2025-03': 870 }, total: 3200, variacion_mom_pct: 18.5 },
  { nombre: 'Carnicería Hermanos López', familia: 'Carnes', meses: { '2024-10': 520, '2024-11': 490, '2024-12': 470, '2025-01': 460, '2025-02': 430, '2025-03': 430 }, total: 2800, variacion_mom_pct: -4.1 },
  { nombre: 'Distribuidora Frutas Pérez', familia: 'Frutas y Verduras', meses: { '2024-10': 260, '2024-11': 270, '2024-12': 265, '2025-01': 268, '2025-02': 270, '2025-03': 267 }, total: 1600, variacion_mom_pct: 0.8 },
  { nombre: 'Bebidas García S.L.', familia: 'Bebidas', meses: { '2024-10': 480, '2024-11': 460, '2024-12': 390, '2025-01': 340, '2025-02': 280, '2025-03': 150 }, total: 2100, variacion_mom_pct: -16.2 },
]

function HistorialCompras({ empresaId }: { empresaId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ['compras-historial', empresaId],
    queryFn: () => advisorApi.comprasProveedores(empresaId, 6),
  })

  if (isLoading) return <ZonaSkeleton label="Historial Compras" />

  const proveedores = (data?.proveedores?.length ?? 0) > 0 ? data!.proveedores : COMPRAS_DEMO
  const usandoDemo = (data?.proveedores?.length ?? 0) === 0

  return (
    <Zona titulo="Historial Compras por Proveedor" subtitulo="Tendencia MoM — alerta si variación >15%">
      {usandoDemo && (
        <p style={{ fontSize: 10, color: 'var(--adv-text-muted)', marginBottom: 8, marginTop: -8 }}>
          Datos de demo
        </p>
      )}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--adv-border)' }}>
              {['Proveedor', 'Familia', 'Total 6M', 'Tendencia', 'MoM'].map(h => (
                <th key={h} style={{ padding: '6px 8px', textAlign: 'left', color: 'var(--adv-text-muted)', fontWeight: 500 }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {proveedores.map((p, i) => {
              const sp = sparklineDesdeMeses(p.meses, p.variacion_mom_pct)
              return (
                <tr key={p.nombre} style={{
                  borderBottom: '1px solid var(--adv-border)',
                  background: i % 2 === 0 ? 'transparent' : 'rgba(31,41,55,0.3)',
                }}>
                  <td style={{ padding: '8px 8px', color: 'var(--adv-text)', fontWeight: 500 }}>{p.nombre}</td>
                  <td style={{ padding: '8px 8px', color: 'var(--adv-text-muted)' }}>{p.familia}</td>
                  <td style={{ padding: '8px 8px', fontFamily: 'var(--adv-font-data)', color: 'var(--adv-text)' }}>
                    {fmtEur(p.total)}
                  </td>
                  <td style={{ padding: '8px 8px' }}>
                    {sp.valores.length >= 2
                      ? <MiniSparkline valores={sp.valores} tendencia={sp.tendencia} />
                      : <span style={{ color: 'var(--adv-text-muted)', fontSize: 10 }}>—</span>
                    }
                  </td>
                  <td style={{ padding: '8px 8px' }}>
                    {indicadorMoM(p.variacion_mom_pct)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Zona>
  )
}

// ─── COMPONENTE 4: CostesFamilia ──────────────────────────────────────────────

interface SliceCostes {
  nombre: string
  valor: number
  color: string
}

const COSTES_FAMILIA: SliceCostes[] = [
  { nombre: 'Materia Prima', valor: 32, color: '#f59e0b' },
  { nombre: 'Personal', valor: 38, color: '#3b82f6' },
  { nombre: 'Suministros', valor: 15, color: '#10b981' },
  { nombre: 'Otros', valor: 15, color: '#8b5cf6' },
]

interface CostesTooltipProps {
  active?: boolean
  payload?: Array<{ payload: SliceCostes }>
}

function CostesTooltipContent({ active, payload }: CostesTooltipProps) {
  if (!active || !payload?.length || !payload[0]) return null
  const d = payload[0].payload
  return (
    <div style={{
      background: 'var(--adv-surface)', border: '1px solid var(--adv-border)',
      borderRadius: 8, padding: '8px 12px', fontSize: 12, color: 'var(--adv-text)',
    }}>
      <div style={{ fontWeight: 600 }}>{d.nombre}</div>
      <div style={{ fontFamily: 'var(--adv-font-data)', color: d.color }}>{d.valor}%</div>
    </div>
  )
}

function CostesFamilia() {
  const [activo, setActivo] = useState<string | null>(null)

  return (
    <Zona titulo="Estructura de Costes" subtitulo="Distribución por familia — datos sectoriales demo">
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <ResponsiveContainer width={200} height={200}>
          <PieChart>
            <Pie
              data={COSTES_FAMILIA}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={90}
              paddingAngle={3}
              dataKey="valor"
              onMouseEnter={(_, idx) => setActivo(COSTES_FAMILIA[idx]?.nombre ?? null)}
              onMouseLeave={() => setActivo(null)}
            >
              {COSTES_FAMILIA.map((s) => (
                <Cell
                  key={s.nombre}
                  fill={s.color}
                  opacity={activo === null || activo === s.nombre ? 1 : 0.4}
                  stroke="none"
                />
              ))}
            </Pie>
            <Tooltip content={<CostesTooltipContent />} />
          </PieChart>
        </ResponsiveContainer>
        <div style={{ flex: 1 }}>
          {COSTES_FAMILIA.map(s => (
            <div
              key={s.nombre}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '7px 10px', borderRadius: 8, marginBottom: 4, cursor: 'default',
                background: activo === s.nombre ? 'var(--adv-surface-2)' : 'transparent',
                transition: 'background 0.15s',
              }}
              onMouseEnter={() => setActivo(s.nombre)}
              onMouseLeave={() => setActivo(null)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: s.color }} />
                <span style={{ fontSize: 12, color: 'var(--adv-text)' }}>{s.nombre}</span>
              </div>
              <span style={{
                fontSize: 13, fontFamily: 'var(--adv-font-data)', fontWeight: 700,
                color: s.color,
              }}>
                {s.valor}%
              </span>
            </div>
          ))}
        </div>
      </div>
      {/* barra acumulada */}
      <div style={{ marginTop: 14, height: 8, borderRadius: 4, overflow: 'hidden', display: 'flex' }}>
        {COSTES_FAMILIA.map(s => (
          <div key={s.nombre} style={{ width: `${s.valor}%`, background: s.color, transition: 'opacity 0.2s',
            opacity: activo === null || activo === s.nombre ? 1 : 0.4 }} />
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--adv-text-muted)', marginTop: 4 }}>
        <span>0%</span>
        <span>100%</span>
      </div>
    </Zona>
  )
}

// ─── PÁGINA PRINCIPAL ─────────────────────────────────────────────────────────

export default function ProductIntelligencePage() {
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
          Product Intelligence
        </h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--adv-text-muted)' }}>
          Análisis de carta, food cost y estructura de compras — empresa #{empresaId}
        </p>
      </div>

      {/* Grid 4 zonas */}
      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: '1fr', maxWidth: 1400 }}>
        {/* Fila 1: BCG ocupa toda la anchura */}
        <MatrizBCG empresaId={empresaId} />

        {/* Fila 2: FoodCost + CostesFamilia */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <FoodCostEvolucion empresaId={empresaId} />
          <CostesFamilia />
        </div>

        {/* Fila 3: HistorialCompras */}
        <HistorialCompras empresaId={empresaId} />
      </div>
    </div>
  )
}
