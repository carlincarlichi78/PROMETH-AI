// src/features/home/empresa-card.tsx
import { useNavigate } from 'react-router-dom'
import { useResumenEmpresa } from './api'
import { useEmpresaWebSocket } from './use-empresa-websocket'
import { Inbox, Calendar, TrendingUp, CreditCard, AlertCircle, ChevronRight } from 'lucide-react'
import type { Empresa } from '@/types'

function tiempoRelativo(isoStr: string): string {
  const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000)
  if (diff < 60) return 'ahora'
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`
  return `hace ${Math.floor(diff / 3600)} h`
}

function nombreCorto(ruta: string): string {
  return ruta.split('/').pop() ?? ruta
}

// Anillo de salud — muestra el scoring como círculo SVG
function HealthRing({ score }: { score: number | null }) {
  if (score === null) return (
    <div className="h-12 w-12 rounded-full border-2 border-border/50 flex items-center justify-center flex-shrink-0">
      <span className="text-[10px] text-muted-foreground">—</span>
    </div>
  )
  const color = score >= 70 ? 'var(--state-success)' : score >= 40 ? 'var(--state-warning)' : 'var(--state-danger)'
  const circunferencia = 2 * Math.PI * 20
  const offset = circunferencia - (score / 100) * circunferencia
  return (
    <div className="relative h-12 w-12 flex-shrink-0">
      <svg className="rotate-[-90deg]" width="48" height="48" viewBox="0 0 48 48">
        <circle cx="24" cy="24" r="20" fill="none" strokeWidth="3" stroke="var(--surface-2)" />
        <circle cx="24" cy="24" r="20" fill="none" strokeWidth="3"
          stroke={color} strokeLinecap="round"
          strokeDasharray={circunferencia} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.6s ease-out' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[11px] font-bold leading-none" style={{ color }}>{score}</span>
        <span className="text-[8px] text-muted-foreground">/100</span>
      </div>
    </div>
  )
}

// Sparkline inline de ventas 6 meses
function Sparkline({ datos }: { datos: number[] }) {
  if (!datos.length || datos.length < 2) return null
  const max = Math.max(...datos)
  const min = Math.min(...datos)
  const rango = max - min || 1
  const ancho = 120
  const alto = 28
  const puntos = datos.map((v, i) => {
    const x = (i / (datos.length - 1)) * ancho
    const y = alto - ((v - min) / rango) * alto
    return `${x},${y}`
  }).join(' ')
  const ultimo = datos[datos.length - 1] ?? 0
  const penultimo = datos[datos.length - 2] ?? ultimo
  const sube = ultimo >= penultimo

  return (
    <div className="flex items-center gap-2">
      <svg width={ancho} height={alto} className="overflow-visible">
        <polyline fill="none" stroke="var(--chart-1)" strokeWidth="1.5"
          strokeLinecap="round" strokeLinejoin="round" points={puntos} />
      </svg>
      <span className={`text-[11px] font-medium ${sube ? 'text-[var(--state-success)]' : 'text-[var(--state-danger)]'}`}>
        {sube ? '↗' : '↘'}
      </span>
    </div>
  )
}

interface EmpresaCardProps {
  empresa: Empresa
}

export function EmpresaCard({ empresa }: EmpresaCardProps) {
  const navigate = useNavigate()
  const { data: resumen, isLoading } = useResumenEmpresa(empresa.id)
  const { procesandoAhora, ultimaActividad, alertaCuarentena, clearAlertaCuarentena } =
    useEmpresaWebSocket(empresa.id)

  const ir = (ruta: string, e?: React.MouseEvent) => {
    e?.stopPropagation()
    navigate(ruta)
  }

  const fiscal = resumen?.fiscal
  const semaforo = fiscal?.dias_restantes == null ? 'neutral'
    : fiscal.dias_restantes <= 7 ? 'danger'
    : fiscal.dias_restantes <= 30 ? 'warning'
    : 'success'

  const semaforoColor = {
    neutral: 'text-muted-foreground',
    success: 'text-[var(--state-success)]',
    warning: 'text-[var(--state-warning)]',
    danger:  'text-[var(--state-danger)]',
  }

  return (
    <div className="rounded-xl border border-border/50 bg-[var(--surface-1)] overflow-hidden
                    hover:border-[var(--primary)]/30 hover:-translate-y-0.5
                    transition-all duration-150 group flex flex-col">
      {/* Cabecera */}
      <div
        className="p-4 pb-3 cursor-pointer"
        onClick={() => ir(`/empresa/${empresa.id}/pyg`)}
      >
        <div className="flex items-start gap-3">
          <HealthRing score={resumen?.scoring ?? null} />
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-[13px] font-bold leading-tight truncate">{empresa.nombre}</h3>
              <button
                type="button"
                onClick={(e) => ir(`/empresa/${empresa.id}/pyg`, e)}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-[var(--surface-2)]"
              >
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5 font-mono">{empresa.cif}</p>
            <p className="text-[11px] text-muted-foreground truncate capitalize">
              {empresa.forma_juridica} · {empresa.regimen_iva}
            </p>
            {empresa.estado_onboarding === 'pendiente_cliente' && (
              <span className="inline-flex items-center rounded-full border border-amber-300 px-1.5 py-0.5 text-[10px] text-amber-600 mt-1">
                Pendiente cliente
              </span>
            )}
            {empresa.estado_onboarding === 'cliente_completado' && (
              <span className="inline-flex items-center rounded-full border border-blue-300 px-1.5 py-0.5 text-[10px] text-blue-600 mt-1">
                Completar config
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Bloque Bandeja + Fiscal */}
      <div className="border-t border-border/30 grid grid-cols-2 divide-x divide-border/30">
        <button
          type="button"
          className="p-3 text-left hover:bg-[var(--surface-2)] transition-colors"
          onClick={() => ir(`/empresa/${empresa.id}/inbox`)}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <Inbox className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Bandeja</span>
          </div>
          {isLoading ? (
            <div className="h-5 w-16 bg-[var(--surface-2)] rounded animate-pulse" />
          ) : (
            <>
              <div className="flex items-center gap-2">
                <p className="text-[15px] font-bold tabular-nums">
                  {resumen?.bandeja.pendientes.toLocaleString('es') ?? 0}
                </p>
                {procesandoAhora && (
                  <span className="inline-flex items-center gap-1 text-[10px] text-amber-400 font-medium">
                    <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                    Procesando
                  </span>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground">pendientes</p>
              {ultimaActividad && (
                <p className="text-[10px] text-muted-foreground/70 mt-0.5 truncate max-w-[120px]"
                   title={nombreCorto(ultimaActividad.nombreArchivo)}>
                  {tiempoRelativo(ultimaActividad.timestamp)} · {nombreCorto(ultimaActividad.nombreArchivo)}
                </p>
              )}
              {(resumen?.bandeja.errores_ocr ?? 0) > 0 && (
                <p className="text-[11px] text-[var(--state-danger)] mt-0.5">
                  ⚠ {resumen!.bandeja.errores_ocr} errores OCR
                </p>
              )}
            </>
          )}
        </button>

        <button
          type="button"
          className="p-3 text-left hover:bg-[var(--surface-2)] transition-colors"
          onClick={() => ir(`/empresa/${empresa.id}/calendario-fiscal`)}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Fiscal</span>
          </div>
          {isLoading ? (
            <div className="h-5 w-20 bg-[var(--surface-2)] rounded animate-pulse" />
          ) : fiscal?.proximo_modelo ? (
            <>
              <p className={`text-[15px] font-bold ${semaforoColor[semaforo]}`}>
                {fiscal.proximo_modelo}
              </p>
              <p className="text-[11px] text-muted-foreground">
                {fiscal.dias_restantes}d · {fiscal.fecha_limite}
              </p>
            </>
          ) : (
            <p className="text-[12px] text-muted-foreground">Sin obligaciones</p>
          )}
        </button>
      </div>

      {/* Bloque Ventas + Contabilidad */}
      <div className="border-t border-border/30 grid grid-cols-2 divide-x divide-border/30">
        <button
          type="button"
          className="p-3 text-left hover:bg-[var(--surface-2)] transition-colors"
          onClick={() => ir(`/empresa/${empresa.id}/facturas-emitidas`)}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <TrendingUp className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Ventas</span>
          </div>
          {isLoading ? (
            <div className="h-5 w-24 bg-[var(--surface-2)] rounded animate-pulse" />
          ) : (
            <>
              <p className="text-[15px] font-bold tabular-nums">
                {resumen?.facturacion.ventas_ytd
                  ? `${(resumen.facturacion.ventas_ytd / 1000).toFixed(0)}K€`
                  : '—'}
              </p>
              {(resumen?.facturacion.facturas_vencidas ?? 0) > 0 && (
                <p className="text-[11px] text-[var(--state-danger)]">
                  ⚠ {resumen!.facturacion.facturas_vencidas} vencidas
                </p>
              )}
            </>
          )}
        </button>

        <button
          type="button"
          className="p-3 text-left hover:bg-[var(--surface-2)] transition-colors"
          onClick={() => ir(`/empresa/${empresa.id}/pyg`)}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <CreditCard className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Contabilidad</span>
          </div>
          {isLoading ? (
            <div className="h-5 w-16 bg-[var(--surface-2)] rounded animate-pulse" />
          ) : (
            <>
              <p className={`text-[13px] font-semibold ${
                (resumen?.contabilidad.errores_asientos ?? 0) === 0
                  ? 'text-[var(--state-success)]'
                  : 'text-[var(--state-danger)]'
              }`}>
                {(resumen?.contabilidad.errores_asientos ?? 0) === 0
                  ? '✓ Sin errores'
                  : `✗ ${resumen!.contabilidad.errores_asientos} errores`}
              </p>
              {resumen?.contabilidad.ultimo_asiento && (
                <p className="text-[11px] text-muted-foreground">
                  Último: {new Date(resumen.contabilidad.ultimo_asiento).toLocaleDateString('es')}
                </p>
              )}
            </>
          )}
        </button>
      </div>

      {/* Sparkline ventas 6M */}
      {resumen?.ventas_6m && resumen.ventas_6m.some(v => v > 0) && (
        <div className="border-t border-border/30 px-4 py-2.5 flex items-center justify-between">
          <span className="text-[11px] text-muted-foreground">Ventas 6M</span>
          <Sparkline datos={resumen.ventas_6m} />
        </div>
      )}

      {/* Alerta IA / Cuarentena */}
      {((resumen?.alertas_ia && resumen.alertas_ia.length > 0) || alertaCuarentena) && (
        <div className="border-t border-amber-500/20 bg-amber-500/10 px-3 py-1.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <AlertCircle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
            <p className="text-[11px] text-amber-300 truncate">
              {alertaCuarentena
                ? `Cuarentena: ${nombreCorto(alertaCuarentena.nombreArchivo)}`
                : resumen!.alertas_ia[0]}
            </p>
          </div>
          {alertaCuarentena && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); clearAlertaCuarentena() }}
              className="text-amber-400/60 hover:text-amber-300 text-[11px] shrink-0"
            >
              ✕
            </button>
          )}
        </div>
      )}

    </div>
  )
}
