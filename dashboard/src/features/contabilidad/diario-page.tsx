import { useState, useRef, useEffect } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { useVirtualizer } from '@tanstack/react-virtual'
import { ChevronDown, ChevronRight, Download } from 'lucide-react'
import { api } from '@/lib/api-client'
import { formatearImporte, formatearFecha } from '@/lib/formatters'
import { PageHeader } from '@/components/page-header'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import type { DiarioPaginado, DiarioAsiento } from '@/types'
import { LibroMayor } from '@/components/contabilidad/libro-mayor'

const LIMITE = 200

const BADGE_COLORES: Record<string, string> = {
  FC:  'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  FV:  'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  NOM: 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300',
  BAN: 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300',
  AMO: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  APE: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300',
}

const ORIGENES = [
  { value: 'todos', label: 'Todos los orígenes' },
  { value: 'FC',  label: 'FC – Fact. recibida' },
  { value: 'FV',  label: 'FV – Fact. emitida' },
  { value: 'NOM', label: 'NOM – Nóminas' },
  { value: 'BAN', label: 'BAN – Bancario' },
  { value: 'AMO', label: 'AMO – Amortización' },
  { value: 'APE', label: 'APE – Apertura' },
]

function useDebouncedValue<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

type FilaVirtual =
  | { tipo: 'asiento';  asiento: DiarioAsiento }
  | { tipo: 'partidas'; asiento: DiarioAsiento }

export default function DiarioPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const [busqueda, setBusqueda]             = useState('')
  const [origen, setOrigen]                 = useState('todos')
  const [expandidos, setExpandidos]         = useState<Set<number>>(new Set())
  const [subcuentaDetalle, setSubcuentaDetalle] = useState<string | null>(null)

  const parentRef = useRef<HTMLDivElement>(null)
  const busquedaDebounced = useDebouncedValue(busqueda, 300)

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } =
    useInfiniteQuery({
      queryKey: ['diario', empresaId, busquedaDebounced, origen],
      initialPageParam: 0,
      queryFn: async ({ pageParam }) => {
        const params = new URLSearchParams({
          offset: String(pageParam),
          limite: String(LIMITE),
        })
        if (busquedaDebounced)  params.set('busqueda', busquedaDebounced)
        if (origen !== 'todos') params.set('origen', origen)
        return api.get<DiarioPaginado>(
          `/api/contabilidad/${empresaId}/diario?${params}`,
        )
      },
      getNextPageParam: (_lastPage, pages) => {
        const cargados = pages.reduce((acc, p) => acc + p.asientos.length, 0)
        const total    = pages[0]?.total ?? 0
        return cargados < total ? cargados : undefined
      },
    })

  const asientos: DiarioAsiento[] = data?.pages.flatMap((p) => p.asientos) ?? []
  const total = data?.pages[0]?.total ?? 0

  // Aplanar asientos + filas de partidas (para expandidos) en lista virtual
  const filas: FilaVirtual[] = []
  for (const a of asientos) {
    filas.push({ tipo: 'asiento', asiento: a })
    if (expandidos.has(a.id)) {
      filas.push({ tipo: 'partidas', asiento: a })
    }
  }

  const virtualizer = useVirtualizer({
    count: filas.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => {
      const fila = filas[index]
      if (fila?.tipo === 'partidas') return fila.asiento.partidas.length * 34 + 40
      return 44
    },
    overscan: 12,
    measureElement: (el) => el.getBoundingClientRect().height,
  })

  // Cargar la siguiente página al llegar al final
  const items = virtualizer.getVirtualItems()
  useEffect(() => {
    const last = items[items.length - 1]
    if (!last) return
    if (last.index >= filas.length - 5 && hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }, [items, filas.length, hasNextPage, isFetchingNextPage, fetchNextPage])

  function toggleExpandido(asientoId: number) {
    setExpandidos((prev) => {
      const s = new Set(prev)
      s.has(asientoId) ? s.delete(asientoId) : s.add(asientoId)
      return s
    })
  }

  function exportarCSV() {
    const lineas = asientos.map((a) =>
      [a.numero ?? '', a.fecha ?? '', a.concepto ?? '', a.total_debe, a.total_haber].join(';'),
    )
    const csv  = ['Num;Fecha;Concepto;Debe;Haber', ...lineas].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url  = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `diario_${empresaId}.csv`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader titulo="Libro Diario" descripcion="Cargando asientos..." />
        <div className="space-y-2">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Libro Diario"
        descripcion={`${total.toLocaleString('es-ES')} asientos · ${asientos.length} cargados`}
      />

      {/* Filtros */}
      <div className="flex gap-3 flex-wrap items-center">
        <Input
          placeholder="Buscar concepto..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="max-w-xs h-8 text-sm"
        />
        <Select value={origen} onValueChange={setOrigen}>
          <SelectTrigger className="w-48 h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ORIGENES.map((o) => (
              <SelectItem key={o.value} value={o.value} className="text-sm">
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={exportarCSV}>
          <Download className="h-3.5 w-3.5 mr-1.5" />
          CSV
        </Button>
      </div>

      {/* Lista virtualizada */}
      <Card className="overflow-hidden">
        {/* Cabecera fija */}
        <div className="grid grid-cols-[36px_56px_84px_1fr_72px_96px_96px] border-b px-4 py-2 text-xs font-medium text-muted-foreground">
          <div />
          <div>Num.</div>
          <div>Fecha</div>
          <div>Concepto</div>
          <div>Origen</div>
          <div className="text-right">Debe</div>
          <div className="text-right">Haber</div>
        </div>

        {filas.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
            Sin asientos para los filtros seleccionados
          </div>
        ) : (
          <div ref={parentRef} className="h-[600px] overflow-y-auto">
            <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
              {virtualizer.getVirtualItems().map((vItem) => {
                const fila = filas[vItem.index]
                if (!fila) return null

                if (fila.tipo === 'asiento') {
                  const a = fila.asiento
                  const expandido = expandidos.has(a.id)
                  const badgeCls  = BADGE_COLORES[a.origen ?? ''] ?? 'bg-muted text-muted-foreground'
                  return (
                    <div
                      key={`a-${a.id}`}
                      data-index={vItem.index}
                      ref={virtualizer.measureElement}
                      style={{ position: 'absolute', top: vItem.start, left: 0, right: 0 }}
                      className="grid grid-cols-[36px_56px_84px_1fr_72px_96px_96px] px-4 h-11 items-center border-b cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => toggleExpandido(a.id)}
                    >
                      <div>
                        {expandido
                          ? <ChevronDown  className="h-3.5 w-3.5 text-muted-foreground" />
                          : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
                      </div>
                      <div className="text-xs font-mono text-muted-foreground">{a.numero ?? '-'}</div>
                      <div className="text-xs">{formatearFecha(a.fecha ?? '')}</div>
                      <div className="text-xs truncate pr-2">{a.concepto ?? '-'}</div>
                      <div>
                        {a.origen && (
                          <Badge variant="outline" className={`text-[10px] px-1.5 py-0 border-0 ${badgeCls}`}>
                            {a.origen}
                          </Badge>
                        )}
                      </div>
                      <div className="text-xs font-mono text-right">{formatearImporte(a.total_debe)}</div>
                      <div className="text-xs font-mono text-right">{formatearImporte(a.total_haber)}</div>
                    </div>
                  )
                }

                // tipo === 'partidas'
                const a = fila.asiento
                return (
                  <div
                    key={`p-${a.id}`}
                    data-index={vItem.index}
                    ref={virtualizer.measureElement}
                    style={{ position: 'absolute', top: vItem.start, left: 0, right: 0 }}
                    className="bg-muted/30 border-b px-8 py-2"
                  >
                    <div className="grid grid-cols-[1fr_1fr_80px_80px] gap-2 text-[10px] font-medium text-muted-foreground mb-1 px-2">
                      <div>Subcuenta</div>
                      <div>Concepto</div>
                      <div className="text-right">Debe</div>
                      <div className="text-right">Haber</div>
                    </div>
                    {a.partidas.map((p, i) => (
                      <div
                        key={i}
                        className="grid grid-cols-[1fr_1fr_80px_80px] gap-2 text-xs py-1 px-2 rounded hover:bg-muted/50"
                      >
                        <button
                          className="font-mono text-left text-primary hover:underline"
                          onClick={(e) => { e.stopPropagation(); setSubcuentaDetalle(p.subcuenta) }}
                        >
                          {p.subcuenta}
                          {p.nombre && (
                            <span className="text-muted-foreground ml-1.5 font-sans text-[10px]">
                              {p.nombre}
                            </span>
                          )}
                        </button>
                        <div className="text-muted-foreground truncate">{a.concepto ?? '-'}</div>
                        <div className="font-mono text-right">
                          {p.debe > 0 ? formatearImporte(p.debe) : '-'}
                        </div>
                        <div className="font-mono text-right">
                          {p.haber > 0 ? formatearImporte(p.haber) : '-'}
                        </div>
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {isFetchingNextPage && (
          <div className="flex justify-center py-3 border-t text-sm text-muted-foreground">
            Cargando más asientos…
          </div>
        )}
      </Card>

      {/* Libro Mayor slide-over */}
      {subcuentaDetalle && (
        <LibroMayor
          empresaId={empresaId}
          subcuenta={subcuentaDetalle}
          onClose={() => setSubcuentaDetalle(null)}
        />
      )}
    </div>
  )
}
