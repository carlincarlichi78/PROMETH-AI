/**
 * Panel de conciliación para la columna derecha de VistaPendientes.
 * Sección 1: Cabecera del movimiento
 * Sección 2: Sugerencias reales de la IA (endpoint /sugerencias?movimiento_id=)
 * Sección 3: Acción manual (asiento directo, Collapsible)
 */
import { useState } from 'react'
import { useEmpresaStore } from '@/stores/empresa-store'
import type { MovimientoBancario, SugerenciaOut } from '../api'
import { useSugerencias, useConfirmarMatch, useRechazarMatch, useConciliarDirecto } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible'
import {
  CheckCircle,
  XCircle,
  Sparkles,
  ChevronDown,
  PenLine,
  ArrowDownLeft,
  ArrowUpRight,
  MousePointerClick,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const CAPA_LABEL: Record<number, string> = {
  1: 'Importe exacto',
  2: 'NIF proveedor',
  3: 'Nº factura',
  4: 'Patrón aprendido',
  5: 'Importe aproximado',
}

function scoreVariant(score: number): string {
  if (score >= 0.9) return 'bg-green-100 text-green-800'
  if (score >= 0.7) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

function formatEur(n: number): string {
  return n.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

// ── Sección 1: Cabecera ───────────────────────────────────────────────────────

function CabeceraMov({ mov }: { mov: MovimientoBancario }) {
  const esAbono = mov.signo === 'H'
  const Icono = esAbono ? ArrowUpRight : ArrowDownLeft

  return (
    <Card>
      <CardContent className="pt-5 pb-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className={cn(
              'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
              esAbono ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            )}>
              <Icono className="h-4 w-4" />
            </span>
            <div>
              <p className="text-xs text-muted-foreground">Mov. #{mov.id} · {mov.fecha}</p>
              <Badge variant="outline" className="mt-0.5 text-[10px]">
                {mov.estado_conciliacion}
              </Badge>
            </div>
          </div>
          <p className={cn(
            'text-2xl font-bold tabular-nums leading-none',
            esAbono ? 'text-green-700' : 'text-red-700'
          )}>
            {esAbono ? '+' : '-'}{formatEur(Math.abs(mov.importe))}
          </p>
        </div>

        <Separator className="my-3" />

        <div className="space-y-1 text-sm">
          <p className="font-medium leading-tight">{mov.concepto_propio || '—'}</p>
          {mov.nombre_contraparte && (
            <p className="text-muted-foreground text-xs">{mov.nombre_contraparte}</p>
          )}
          {mov.tipo_clasificado && (
            <Badge variant="secondary" className="text-xs mt-1">{mov.tipo_clasificado}</Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// ── Sección 2: Sugerencias IA ─────────────────────────────────────────────────

function FilaSugerencia({
  s,
  onConfirmar,
  onRechazar,
  isPending,
}: {
  s: SugerenciaOut
  onConfirmar: () => void
  onRechazar: () => void
  isPending: boolean
}) {
  return (
    <div className="rounded-md border p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <Badge className={cn('text-xs font-semibold', scoreVariant(s.score))}>
          {Math.round(s.score * 100)}% — {CAPA_LABEL[s.capa_origen] ?? `Capa ${s.capa_origen}`}
        </Badge>
        <span className="text-xs text-muted-foreground tabular-nums font-medium">
          {s.documento?.importe_total != null ? formatEur(s.documento.importe_total) : '—'}
        </span>
      </div>

      <div className="text-sm">
        <p className="font-medium truncate">{s.documento?.numero_factura ?? '—'}</p>
        <p className="text-xs text-muted-foreground truncate">{s.documento?.nif_proveedor ?? '—'}</p>
      </div>

      <div className="flex gap-2 pt-1">
        <Button
          size="sm"
          className="flex-1 h-7 bg-green-600 hover:bg-green-700 text-xs"
          disabled={isPending}
          onClick={onConfirmar}
        >
          <CheckCircle className="h-3.5 w-3.5 mr-1" />
          Confirmar
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1 h-7 text-xs text-red-600 border-red-200 hover:bg-red-50"
          disabled={isPending}
          onClick={onRechazar}
        >
          <XCircle className="h-3.5 w-3.5 mr-1" />
          Rechazar
        </Button>
      </div>
    </div>
  )
}

function SeccionSugerencias({ empresaId, movId }: { empresaId: number; movId: number }) {
  const { data: sugerencias = [], isLoading } = useSugerencias(empresaId, movId)
  const confirmar = useConfirmarMatch(empresaId)
  const rechazar = useRechazarMatch(empresaId)
  const isPending = confirmar.isPending || rechazar.isPending

  return (
    <Card>
      <CardHeader className="pb-2 pt-4 px-4">
        <CardTitle className="text-sm flex items-center gap-1.5">
          <Sparkles className="h-4 w-4 text-yellow-500" />
          Sugerencias de la IA
          <Badge variant="secondary" className="ml-auto text-xs">{sugerencias.length}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-2">
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : sugerencias.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-3">
            No hay sugerencias para este movimiento.
          </p>
        ) : (
          sugerencias.map((s) => (
            <FilaSugerencia
              key={s.id}
              s={s}
              onConfirmar={() => confirmar.mutate({ movimiento_id: s.movimiento_id, sugerencia_id: s.id })}
              onRechazar={() => rechazar.mutate({ sugerencia_id: s.id })}
              isPending={isPending}
            />
          ))
        )}
      </CardContent>
    </Card>
  )
}

// ── Sección 3: Acción manual ──────────────────────────────────────────────────

function SeccionManual({ mov, empresaId }: { mov: MovimientoBancario; empresaId: number }) {
  const [abierto, setAbierto] = useState(false)
  const [cuenta, setCuenta] = useState('')
  const [concepto, setConcepto] = useState(mov.concepto_propio ?? '')
  const conciliarDirecto = useConciliarDirecto(empresaId)

  const handleCrear = () => {
    conciliarDirecto.mutate({
      movimiento_id: mov.id,
      cuenta_contable: cuenta,
      concepto,
    })
  }

  return (
    <Collapsible open={abierto} onOpenChange={setAbierto}>
      <Card className={cn('transition-colors', abierto && 'border-primary/40')}>
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/50 transition-colors rounded-[inherit]"
          >
            <span className="flex items-center gap-2">
              <PenLine className="h-4 w-4 text-muted-foreground" />
              Asiento manual
            </span>
            <ChevronDown className={cn(
              'h-4 w-4 text-muted-foreground transition-transform duration-150',
              abierto && 'rotate-180'
            )} />
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <Separator />
          <div className="px-4 pb-4 pt-3 space-y-3">
            <p className="text-xs text-muted-foreground">
              Usa esto si ninguna sugerencia encaja. Se creará un asiento contable directo.
            </p>

            <div className="space-y-1.5">
              <Label htmlFor="cuenta-contable" className="text-xs">Cuenta contable</Label>
              <Input
                id="cuenta-contable"
                placeholder="Ej. 6220000 — Suministros"
                value={cuenta}
                onChange={(e) => setCuenta(e.target.value)}
                className="h-8 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="concepto-manual" className="text-xs">Concepto</Label>
              <Input
                id="concepto-manual"
                placeholder="Descripción del asiento"
                value={concepto}
                onChange={(e) => setConcepto(e.target.value)}
                className="h-8 text-sm"
              />
            </div>

            {conciliarDirecto.isSuccess && (
              <p className="text-xs text-green-700 font-medium">
                Asiento creado correctamente.
              </p>
            )}
            {conciliarDirecto.isError && (
              <p className="text-xs text-destructive">
                Error: {conciliarDirecto.error?.message ?? 'No se pudo crear el asiento'}
              </p>
            )}
            <Button
              size="sm"
              className="w-full mt-1"
              disabled={!cuenta.trim() || !concepto.trim() || conciliarDirecto.isPending}
              onClick={handleCrear}
            >
              {conciliarDirecto.isPending ? 'Creando…' : 'Crear asiento directo'}
            </Button>
          </div>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  )
}

// ── Componente público ────────────────────────────────────────────────────────

export function PanelConciliacion({
  movimientoSeleccionado,
}: {
  movimientoSeleccionado: MovimientoBancario | null
}) {
  const empresaId = useEmpresaStore((s) => s.empresaActiva?.id ?? 0)

  if (!movimientoSeleccionado) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 text-muted-foreground">
        <MousePointerClick className="h-10 w-10 opacity-25" />
        <p className="text-sm font-medium">Selecciona un movimiento para ver sus sugerencias</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <CabeceraMov mov={movimientoSeleccionado} />
      <SeccionSugerencias empresaId={empresaId} movId={movimientoSeleccionado.id} />
      <SeccionManual mov={movimientoSeleccionado} empresaId={empresaId} />
    </div>
  )
}
