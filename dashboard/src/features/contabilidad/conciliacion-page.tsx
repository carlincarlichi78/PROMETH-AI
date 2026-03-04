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
import { AlertTriangle } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { PanelSugerencias } from '@/features/conciliacion/components/panel-sugerencias'
import { TablaMovimientos } from '@/features/conciliacion/components/tabla-movimientos'
import { TablaPatrones } from '@/features/conciliacion/components/tabla-patrones'
import { SubirExtracto } from '@/features/conciliacion/components/subir-extracto'
import { conciliacionApi } from '@/features/conciliacion/api'

export default function ConciliacionPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [tab, setTab] = useState('sugeridos')

  const { data: movPendientes = [] } = useQuery({
    queryKey: ['movimientos-bancarios', empresaId, 'pendiente'],
    queryFn: () => conciliacionApi.listarMovimientos(empresaId, 'pendiente'),
    enabled: empresaId > 0,
  })

  const { data: movSugeridos = [] } = useQuery({
    queryKey: ['movimientos-bancarios', empresaId, 'sugerido'],
    queryFn: () => conciliacionApi.listarMovimientos(empresaId, 'sugerido'),
    enabled: empresaId > 0,
  })

  const { data: movRevision = [] } = useQuery({
    queryKey: ['movimientos-bancarios', empresaId, 'revision'],
    queryFn: () => conciliacionApi.listarMovimientos(empresaId, 'revision'),
    enabled: empresaId > 0,
  })

  const { data: movConciliados = [] } = useQuery({
    queryKey: ['movimientos-bancarios', empresaId, 'conciliado'],
    queryFn: () => conciliacionApi.listarMovimientos(empresaId, 'conciliado'),
    enabled: empresaId > 0,
  })

  const { data: descuadres = [] } = useQuery({
    queryKey: ['descuadre', empresaId],
    queryFn: () => conciliacionApi.saldoDescuadre(empresaId),
    enabled: empresaId > 0,
  })

  const alertasDescuadre = descuadres.filter(d => d.alerta)
  const totalSugeridos = movSugeridos.length + movRevision.length

  return (
    <div className="space-y-4">
      <PageHeader
        titulo="Conciliación Bancaria"
        descripcion="Empareja movimientos del extracto bancario con asientos contables"
      />

      <SubirExtracto empresaId={empresaId} />

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

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="pendientes">
            Pendientes
            {movPendientes.length > 0 && (
              <Badge variant="secondary" className="ml-2 text-xs">
                {movPendientes.length}
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
          <TablaMovimientos
            movimientos={movPendientes}
            titulo="Movimientos sin match"
          />
        </TabsContent>

        <TabsContent value="sugeridos" className="mt-4">
          <PanelSugerencias empresaId={empresaId} />
        </TabsContent>

        <TabsContent value="conciliados" className="mt-4">
          <TablaMovimientos
            movimientos={movConciliados}
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
                    d.alerta
                      ? 'border-red-300 bg-red-50'
                      : 'border-green-300 bg-green-50'
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
                          {d.saldo_bancario.toLocaleString('es-ES', {
                            style: 'currency',
                            currency: 'EUR',
                          })}
                        </span>
                      </p>
                      <p className="text-sm">
                        Saldo contable:{' '}
                        <span className="font-mono">
                          {d.saldo_contable.toLocaleString('es-ES', {
                            style: 'currency',
                            currency: 'EUR',
                          })}
                        </span>
                      </p>
                      {d.alerta && (
                        <p className="text-red-600 text-sm font-semibold">
                          Diferencia:{' '}
                          {d.diferencia.toLocaleString('es-ES', {
                            style: 'currency',
                            currency: 'EUR',
                          })}
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
