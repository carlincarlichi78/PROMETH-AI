/**
 * Página principal de conciliación bancaria.
 * Tabs: Pendientes | Sugeridos | Conciliados | Patrones | Descuadre
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { PanelSugerencias } from '@/features/conciliacion/components/panel-sugerencias'
import { TablaMovimientos } from '@/features/conciliacion/components/tabla-movimientos'
import { TablaPatrones } from '@/features/conciliacion/components/tabla-patrones'
import { SubirExtracto } from '@/features/conciliacion/components/subir-extracto'
import { conciliacionApi, useCuentas, useMovimientos } from '@/features/conciliacion/api'

const PAGE_SIZE = 100

function PaginacionBar({
  total,
  offset,
  limit,
  onChange,
}: {
  total: number
  offset: number
  limit: number
  onChange: (offset: number) => void
}) {
  const pagina = Math.floor(offset / limit) + 1
  const totalPaginas = Math.ceil(total / limit)
  if (totalPaginas <= 1) return null
  return (
    <div className="flex items-center justify-between px-1 pt-2 text-sm text-muted-foreground">
      <span>
        {offset + 1}–{Math.min(offset + limit, total)} de {total}
      </span>
      <div className="flex gap-1">
        <Button
          size="icon"
          variant="ghost"
          disabled={offset === 0}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          <ChevronLeft className="w-4 h-4" />
        </Button>
        <span className="px-2 py-1">
          {pagina} / {totalPaginas}
        </span>
        <Button
          size="icon"
          variant="ghost"
          disabled={offset + limit >= total}
          onClick={() => onChange(offset + limit)}
        >
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  )
}

function TabMovimientosPaginados({
  empresaId,
  estado,
  cuentaId,
  titulo,
  mostrarDocumento = false,
}: {
  empresaId: number
  estado: string
  cuentaId?: number
  titulo?: string
  mostrarDocumento?: boolean
}) {
  const [offset, setOffset] = useState(0)
  const { data, isLoading } = useMovimientos(empresaId, {
    estado,
    cuentaId,
    offset,
    limit: PAGE_SIZE,
  })
  const movimientos = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div>
      <TablaMovimientos movimientos={movimientos} isLoading={isLoading} titulo={titulo} mostrarDocumento={mostrarDocumento} />
      <PaginacionBar total={total} offset={offset} limit={PAGE_SIZE} onChange={setOffset} />
    </div>
  )
}

export default function ConciliacionPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [tab, setTab] = useState('sugeridos')
  const [cuentaId, setCuentaId] = useState<number | undefined>(undefined)

  const { data: cuentas = [] } = useCuentas(empresaId)

  // Conteo para badges (sin filtro de cuenta para mostrar total real)
  const { data: pendientesData } = useMovimientos(empresaId, { estado: 'pendiente', cuentaId, limit: 1 })
  const { data: sugeridosData } = useMovimientos(empresaId, { estado: 'sugerido', cuentaId, limit: 1 })
  const { data: revisionData } = useMovimientos(empresaId, { estado: 'revision', cuentaId, limit: 1 })

  const totalPendientes = pendientesData?.total ?? 0
  const totalSugeridos = (sugeridosData?.total ?? 0) + (revisionData?.total ?? 0)

  const { data: descuadres = [] } = useQuery({
    queryKey: ['descuadre', empresaId],
    queryFn: () => conciliacionApi.saldoDescuadre(empresaId),
    enabled: empresaId > 0,
  })

  const alertasDescuadre = descuadres.filter(d => d.alerta)

  return (
    <div className="space-y-4">
      <PageHeader
        titulo="Conciliación Bancaria"
        descripcion="Empareja movimientos del extracto bancario con asientos contables"
      />

      <div className="flex flex-wrap items-center gap-3">
        <SubirExtracto empresaId={empresaId} />
        {cuentas.length > 1 && (
          <Select
            value={cuentaId ? String(cuentaId) : 'todas'}
            onValueChange={v => setCuentaId(v === 'todas' ? undefined : Number(v))}
          >
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Todas las cuentas" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todas">Todas las cuentas</SelectItem>
              {cuentas.map(c => (
                <SelectItem key={c.id} value={String(c.id)}>
                  {c.alias || c.banco_nombre} — ···{c.iban.slice(-4)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {alertasDescuadre.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {alertasDescuadre.map(d => (
              <div key={d.cuenta_id}>
                {d.alias}: {d.mensaje_alerta}
              </div>
            ))}
          </AlertDescription>
        </Alert>
      )}

      <Tabs value={tab} onValueChange={v => { setTab(v) }}>
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="pendientes">
            Pendientes
            {totalPendientes > 0 && (
              <Badge variant="secondary" className="ml-2 text-xs">
                {totalPendientes}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="sugeridos">
            Sugeridos
            {totalSugeridos > 0 && (
              <Badge className="ml-2 text-xs bg-blue-500 text-white">
                {totalSugeridos}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="conciliados">Conciliados</TabsTrigger>
          <TabsTrigger value="patrones">Patrones</TabsTrigger>
          <TabsTrigger value="descuadre">
            Descuadre
            {alertasDescuadre.length > 0 && (
              <Badge variant="destructive" className="ml-2 text-xs">
                {alertasDescuadre.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pendientes" className="mt-4">
          <TabMovimientosPaginados
            empresaId={empresaId}
            estado="pendiente"
            cuentaId={cuentaId}
            titulo="Movimientos sin match"
          />
        </TabsContent>

        <TabsContent value="sugeridos" className="mt-4">
          <PanelSugerencias empresaId={empresaId} />
        </TabsContent>

        <TabsContent value="conciliados" className="mt-4">
          <TabMovimientosPaginados
            empresaId={empresaId}
            estado="conciliado"
            cuentaId={cuentaId}
            titulo="Movimientos conciliados"
            mostrarDocumento
          />
        </TabsContent>

        <TabsContent value="patrones" className="mt-4">
          <TablaPatrones empresaId={empresaId} />
        </TabsContent>

        <TabsContent value="descuadre" className="mt-4">
          <div className="space-y-4">
            {descuadres.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">Sin datos de saldo.</p>
            ) : (
              descuadres.map(d => (
                <div
                  key={d.cuenta_id}
                  className={`p-4 rounded-lg border ${
                    d.alerta ? 'border-red-300 bg-red-50' : 'border-green-300 bg-green-50'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-semibold">{d.alias}</p>
                      <p className="text-sm text-muted-foreground">{d.iban}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm">
                        Saldo bancario:{' '}
                        <span className="font-mono">
                          {d.saldo_bancario.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                        </span>
                      </p>
                      <p className="text-sm">
                        Saldo contable:{' '}
                        <span className="font-mono">
                          {d.saldo_contable.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                        </span>
                      </p>
                      {d.alerta && (
                        <p className="text-red-600 text-sm font-semibold">
                          Diferencia:{' '}
                          {d.diferencia.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
                        </p>
                      )}
                    </div>
                  </div>
                  {d.mensaje_alerta && (
                    <p className="text-sm text-red-600 mt-2">{d.mensaje_alerta}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
