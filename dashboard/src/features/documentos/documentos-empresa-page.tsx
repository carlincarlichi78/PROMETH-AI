import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, CheckCircle2, AlertTriangle, Clock, XCircle } from 'lucide-react'
import { api } from '@/lib/api-client'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface DocumentoItem {
  id: number
  tipo_doc: string
  estado: string
  confianza: number | null
  factura_id_fs: number | null
  ejercicio: string | null
  fecha_proceso: string | null
  motivo_cuarentena: string | null
  emisor: string | null
  total: number | null
  numero_factura: string | null
  fecha_factura: string | null
}

const ESTADO_CONFIG: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; icono: React.FC<{ className?: string }> }> = {
  registrado: { label: 'Registrado', variant: 'default', icono: CheckCircle2 },
  cuarentena: { label: 'Cuarentena', variant: 'destructive', icono: AlertTriangle },
  pendiente:  { label: 'Pendiente',  variant: 'secondary', icono: Clock },
  error:      { label: 'Error',      variant: 'outline',   icono: XCircle },
}

const TIPO_LABEL: Record<string, string> = {
  FC: 'Fact. recibida', FV: 'Fact. emitida', NC: 'Nota crédito',
  NOM: 'Nómina', SUM: 'Suministro', BAN: 'Bancario',
  IMP: 'Modelo fiscal', RLC: 'Recibo',
}

function BadgeEstado({ estado }: { estado: string }) {
  const cfg = ESTADO_CONFIG[estado] ?? { label: estado, variant: 'secondary' as const, icono: FileText }
  const Icono = cfg.icono
  return (
    <Badge variant={cfg.variant} className="gap-1">
      <Icono className="h-3 w-3" />
      {cfg.label}
    </Badge>
  )
}

export default function DocumentosEmpresaPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [ejercicio, setEjercicio] = useState<string>('todos')
  const [estado, setEstado] = useState<string>('todos')
  const [tipo, setTipo] = useState<string>('todos')

  const { data, isLoading } = useQuery({
    queryKey: ['empresa-documentos', empresaId, ejercicio, estado, tipo],
    queryFn: () => {
      const params = new URLSearchParams()
      if (ejercicio !== 'todos') params.set('ejercicio', ejercicio)
      if (estado !== 'todos') params.set('estado', estado)
      if (tipo !== 'todos') params.set('tipo_doc', tipo)
      params.set('limit', '100')
      return api.get<{ total: number; items: DocumentoItem[] }>(
        `/api/empresas/${empresaId}/documentos?${params}`
      )
    },
    enabled: !!empresaId,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Documentos procesados"
        descripcion={`${total} documento${total !== 1 ? 's' : ''} registrados por el pipeline`}
      />

      {/* Filtros */}
      <div className="flex flex-wrap gap-3">
        <Select value={ejercicio} onValueChange={setEjercicio}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Ejercicio" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos los años</SelectItem>
            {['2025', '2024', '2023'].map(y => (
              <SelectItem key={y} value={y}>{y}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={estado} onValueChange={setEstado}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos los estados</SelectItem>
            <SelectItem value="registrado">Registrado</SelectItem>
            <SelectItem value="cuarentena">Cuarentena</SelectItem>
            <SelectItem value="pendiente">Pendiente</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>

        <Select value={tipo} onValueChange={setTipo}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos los tipos</SelectItem>
            {Object.entries(TIPO_LABEL).map(([k, v]) => (
              <SelectItem key={k} value={k}>{v}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Tabla */}
      {isLoading ? (
        <div className="text-muted-foreground text-sm">Cargando...</div>
      ) : items.length === 0 ? (
        <EstadoVacio
          titulo="Sin documentos"
          descripcion="El pipeline aún no ha procesado documentos para esta empresa."
          icono={FileText}
        />
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Tipo</th>
                <th className="text-left px-4 py-3 font-medium">Emisor / Concepto</th>
                <th className="text-left px-4 py-3 font-medium">Nº Factura</th>
                <th className="text-right px-4 py-3 font-medium">Total</th>
                <th className="text-left px-4 py-3 font-medium">Fecha</th>
                <th className="text-left px-4 py-3 font-medium">Estado</th>
                <th className="text-left px-4 py-3 font-medium">Confianza</th>
                <th className="text-left px-4 py-3 font-medium">ID FS</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((doc) => (
                <tr key={doc.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3">
                    <Badge variant="outline" className="font-mono text-xs">
                      {doc.tipo_doc}
                    </Badge>
                    {doc.tipo_doc in TIPO_LABEL && (
                      <span className="ml-2 text-muted-foreground text-xs">
                        {TIPO_LABEL[doc.tipo_doc]}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 max-w-[200px] truncate">
                    {doc.emisor ?? <span className="text-muted-foreground">—</span>}
                    {doc.motivo_cuarentena && (
                      <p className="text-xs text-destructive truncate">{doc.motivo_cuarentena}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {doc.numero_factura ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right font-medium">
                    {doc.total != null
                      ? new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(doc.total)
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {doc.fecha_factura ?? (doc.fecha_proceso ? doc.fecha_proceso.slice(0, 10) : '—')}
                  </td>
                  <td className="px-4 py-3">
                    <BadgeEstado estado={doc.estado} />
                  </td>
                  <td className="px-4 py-3">
                    {doc.confianza != null ? (
                      <span className={doc.confianza >= 80 ? 'text-green-600' : doc.confianza >= 50 ? 'text-amber-600' : 'text-red-500'}>
                        {doc.confianza}%
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                    {doc.factura_id_fs ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
