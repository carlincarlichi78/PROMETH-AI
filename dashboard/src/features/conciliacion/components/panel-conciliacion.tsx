/**
 * Panel de conciliación para la columna derecha de VistaPendientes.
 * Sección 1: Cabecera del movimiento
 * Sección 2: Sugerencias de la IA (mockeadas hasta conectar endpoint)
 * Sección 3: Acción manual (asiento directo, Collapsible)
 */
import { useState } from 'react'
import type { MovimientoBancario } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
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
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Tipos de mock ─────────────────────────────────────────────────────────────

interface SugerenciaMock {
  id: number
  score: number
  capa: number
  capaLabel: string
  numeroDocumento: string
  nombreProveedor: string
  importeDocumento: number
  fechaDocumento: string
}

const CAPA_LABEL: Record<number, string> = {
  1: 'Importe exacto',
  2: 'NIF proveedor',
  3: 'Nº factura',
  4: 'Patrón aprendido',
  5: 'Importe aproximado',
}

// Genera sugerencias mock realistas a partir del importe del movimiento
function generarSugerenciasMock(mov: MovimientoBancario): SugerenciaMock[] {
  const base = Math.abs(mov.importe)
  return [
    {
      id: 1,
      score: 0.97,
      capa: 1,
      capaLabel: CAPA_LABEL[1] ?? 'Capa 1',
      numeroDocumento: `FV-2025-${String(mov.id + 80).padStart(3, '0')}`,
      nombreProveedor: mov.nombre_contraparte || 'Proveedor desconocido',
      importeDocumento: base,
      fechaDocumento: mov.fecha,
    },
    {
      id: 2,
      score: 0.82,
      capa: 2,
      capaLabel: CAPA_LABEL[2] ?? 'Capa 2',
      numeroDocumento: `FV-2025-${String(mov.id + 55).padStart(3, '0')}`,
      nombreProveedor: mov.nombre_contraparte || 'Proveedor desconocido',
      importeDocumento: base - 0.01,
      fechaDocumento: mov.fecha,
    },
    {
      id: 3,
      score: 0.68,
      capa: 4,
      capaLabel: CAPA_LABEL[4] ?? 'Capa 4',
      numeroDocumento: 'Regla automática',
      nombreProveedor: 'Patrón: ' + (mov.concepto_propio?.slice(0, 20) || 'Sin patrón'),
      importeDocumento: base,
      fechaDocumento: mov.fecha,
    },
  ]
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
}: {
  s: SugerenciaMock
  onConfirmar: (id: number) => void
  onRechazar: (id: number) => void
}) {
  return (
    <div className="rounded-md border p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <Badge className={cn('text-xs font-semibold', scoreVariant(s.score))}>
          {Math.round(s.score * 100)}% — {s.capaLabel}
        </Badge>
        <span className="text-xs text-muted-foreground tabular-nums font-medium">
          {formatEur(s.importeDocumento)}
        </span>
      </div>

      <div className="text-sm">
        <p className="font-medium truncate">{s.numeroDocumento}</p>
        <p className="text-xs text-muted-foreground truncate">{s.nombreProveedor}</p>
      </div>

      <div className="flex gap-2 pt-1">
        <Button
          size="sm"
          className="flex-1 h-7 bg-green-600 hover:bg-green-700 text-xs"
          onClick={() => onConfirmar(s.id)}
        >
          <CheckCircle className="h-3.5 w-3.5 mr-1" />
          Confirmar
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1 h-7 text-xs text-red-600 border-red-200 hover:bg-red-50"
          onClick={() => onRechazar(s.id)}
        >
          <XCircle className="h-3.5 w-3.5 mr-1" />
          Rechazar
        </Button>
      </div>
    </div>
  )
}

function SeccionSugerencias({ mov }: { mov: MovimientoBancario }) {
  const sugerencias = generarSugerenciasMock(mov)
  const [descartadas, setDescartadas] = useState<number[]>([])
  const visibles = sugerencias.filter((s) => !descartadas.includes(s.id))

  const handleConfirmar = (_id: number) => {
    // TODO: conectar a conciliacionApi.confirmarMatch cuando se integre con API real
  }
  const handleRechazar = (id: number) => {
    setDescartadas((prev) => [...prev, id])
  }

  return (
    <Card>
      <CardHeader className="pb-2 pt-4 px-4">
        <CardTitle className="text-sm flex items-center gap-1.5">
          <Sparkles className="h-4 w-4 text-yellow-500" />
          Sugerencias de la IA
          <Badge variant="secondary" className="ml-auto text-xs">{visibles.length}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-2">
        {visibles.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-3">
            Todas las sugerencias han sido descartadas.
          </p>
        ) : (
          visibles.map((s) => (
            <FilaSugerencia
              key={s.id}
              s={s}
              onConfirmar={handleConfirmar}
              onRechazar={handleRechazar}
            />
          ))
        )}
      </CardContent>
    </Card>
  )
}

// ── Sección 3: Acción manual ──────────────────────────────────────────────────

function SeccionManual({ mov }: { mov: MovimientoBancario }) {
  const [abierto, setAbierto] = useState(false)
  const [cuenta, setCuenta] = useState('')
  const [concepto, setConcepto] = useState(mov.concepto_propio ?? '')

  const handleCrear = () => {
    // TODO: conectar a endpoint de creación de asiento directo
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

            <Button
              size="sm"
              className="w-full mt-1"
              disabled={!cuenta.trim() || !concepto.trim()}
              onClick={handleCrear}
            >
              Crear asiento directo
            </Button>
          </div>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  )
}

// ── Componente público ────────────────────────────────────────────────────────

export function PanelConciliacion({ mov }: { mov: MovimientoBancario }) {
  return (
    <div className="space-y-3">
      <CabeceraMov mov={mov} />
      <SeccionSugerencias mov={mov} />
      <SeccionManual mov={mov} />
    </div>
  )
}
