import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  FileText, CheckCircle2, AlertTriangle, Clock, XCircle,
  Mail, Upload, FolderOpen, Terminal, Download, ChevronRight,
} from 'lucide-react'
import { api } from '@/lib/api-client'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Separator } from '@/components/ui/separator'

// ─── Tipos ───────────────────────────────────────────────────────────────────

interface PartidaDoc {
  subcuenta: string
  debe: number
  haber: number
  concepto?: string
}

interface AsientoDoc {
  id: number
  numero?: number
  idasiento_fs?: number
  fecha?: string
  concepto?: string
  partidas: PartidaDoc[]
}

interface DocumentoItem {
  id: number
  tipo_doc: string
  estado: string
  confianza: number | null
  ocr_tier: number | null
  ruta_pdf: string | null
  origen: string
  factura_id_fs: number | null
  ejercicio: string | null
  fecha_proceso: string | null
  motivo_cuarentena: string | null
  emisor: string | null
  emisor_cif: string | null
  total: number | string | null
  base_imponible: number | string | null
  iva_importe: number | string | null
  numero_factura: string | null
  fecha_factura: string | null
  asiento: AsientoDoc | null
}

// ─── Constantes ──────────────────────────────────────────────────────────────

const ESTADO_CONFIG: Record<string, {
  label: string
  variant: 'default' | 'secondary' | 'destructive' | 'outline'
  icono: React.FC<{ className?: string }>
}> = {
  registrado: { label: 'Registrado', variant: 'default',     icono: CheckCircle2 },
  cuarentena: { label: 'Cuarentena', variant: 'destructive', icono: AlertTriangle },
  pendiente:  { label: 'Pendiente',  variant: 'secondary',   icono: Clock },
  error:      { label: 'Error',      variant: 'outline',     icono: XCircle },
}

const TIPO_LABEL: Record<string, string> = {
  FC: 'Factura recibida', FV: 'Factura emitida', NC: 'Nota de crédito',
  NOM: 'Nómina', SUM: 'Suministro', BAN: 'Extracto bancario',
  IMP: 'Modelo fiscal', RLC: 'Recibo', ANT: 'Anticipo',
}

const OCR_TIER: Record<number, { label: string; api: string; color: string }> = {
  0: { label: 'T0', api: 'pdfplumber — texto nativo, sin API',   color: 'text-blue-400' },
  1: { label: 'T1', api: 'Mistral OCR — scan / imagen',          color: 'text-amber-400' },
  2: { label: 'T2', api: 'GPT-4o / Gemini Flash — fallback',     color: 'text-purple-400' },
}

const ORIGEN_META: Record<string, { icono: React.FC<{ className?: string }>; label: string }> = {
  email:    { icono: Mail,       label: 'Email (IMAP)' },
  portal:   { icono: Upload,     label: 'Portal cliente' },
  watcher:  { icono: FolderOpen, label: 'Carpeta vigilada' },
  pipeline: { icono: Terminal,   label: 'Pipeline manual' },
}
const ORIGEN_FALLBACK = { icono: Terminal, label: 'Pipeline manual' }

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtEur(n: number | string | null | undefined): string {
  if (n == null) return '—'
  const v = typeof n === 'string' ? parseFloat(n) : n
  if (isNaN(v)) return '—'
  return new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v) + ' €'
}

// ─── Componentes panel ────────────────────────────────────────────────────────

function Campo({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-1.5">
      <span className="text-muted-foreground text-sm shrink-0">{label}</span>
      <span className="text-sm font-medium text-right">{value ?? <span className="text-muted-foreground">—</span>}</span>
    </div>
  )
}

function SeccionPanel({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">{titulo}</p>
      {children}
    </div>
  )
}

function DocumentoPanel({ doc, empresaId }: { doc: DocumentoItem; empresaId: number }) {
  const origenMeta = ORIGEN_META[doc.origen] ?? ORIGEN_FALLBACK
  const OrigenIcono = origenMeta.icono
  const tier = doc.ocr_tier != null ? OCR_TIER[doc.ocr_tier] : null
  const tieneOcr = doc.emisor || doc.emisor_cif || doc.numero_factura || doc.total != null

  return (
    <div className="space-y-5 py-2">

      {/* Cabecera tipo + estado */}
      <div className="flex items-center gap-3">
        <Badge variant="outline" className="font-mono text-sm px-3 py-1">
          {doc.tipo_doc}
        </Badge>
        <span className="text-muted-foreground">{TIPO_LABEL[doc.tipo_doc] ?? doc.tipo_doc}</span>
        <div className="ml-auto">
          <BadgeEstado estado={doc.estado} />
        </div>
      </div>

      {/* Descargar PDF */}
      {doc.ruta_pdf && (
        <Button
          variant="outline"
          size="sm"
          className="w-full gap-2"
          asChild
        >
          <a
            href={`/api/documentos/${empresaId}/${doc.id}/descargar`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Download className="h-4 w-4" />
            Descargar PDF original
          </a>
        </Button>
      )}

      <Separator />

      {/* Origen */}
      <SeccionPanel titulo="Origen">
        <Campo
          label="Canal"
          value={
            <span className="flex items-center gap-1.5 justify-end">
              <OrigenIcono className="h-3.5 w-3.5" />
              {origenMeta.label}
            </span>
          }
        />
        {doc.ruta_pdf && (
          <Campo label="Archivo" value={<span className="font-mono text-xs break-all">{doc.ruta_pdf}</span>} />
        )}
        {doc.ejercicio && <Campo label="Ejercicio" value={doc.ejercicio} />}
        {doc.fecha_proceso && (
          <Campo label="Procesado el" value={doc.fecha_proceso.slice(0, 16).replace('T', ' ')} />
        )}
      </SeccionPanel>

      <Separator />

      {/* Datos extraídos */}
      <SeccionPanel titulo="Datos extraídos por OCR">
        {tieneOcr ? (
          <>
            {doc.emisor && <Campo label="Emisor" value={doc.emisor} />}
            {doc.emisor_cif && <Campo label="CIF emisor" value={<span className="font-mono">{doc.emisor_cif}</span>} />}
            {doc.numero_factura && <Campo label="Nº factura" value={<span className="font-mono">{doc.numero_factura}</span>} />}
            {doc.fecha_factura && <Campo label="Fecha factura" value={doc.fecha_factura} />}
            {doc.base_imponible != null && <Campo label="Base imponible" value={fmtEur(doc.base_imponible)} />}
            {doc.iva_importe != null && <Campo label="Cuota IVA" value={fmtEur(doc.iva_importe)} />}
            {doc.total != null && (
              <Campo label="Total" value={<span className="font-bold text-base">{fmtEur(doc.total)}</span>} />
            )}
          </>
        ) : (
          <p className="text-muted-foreground text-sm">Sin datos OCR disponibles</p>
        )}
      </SeccionPanel>

      <Separator />

      {/* Pipeline OCR */}
      <SeccionPanel titulo="Pipeline de extracción">
        {tier ? (
          <div className="flex items-center gap-2 py-1">
            <span className={`font-bold text-sm ${tier.color}`}>{tier.label}</span>
            <span className="text-muted-foreground text-sm">—</span>
            <span className="text-sm">{tier.api}</span>
          </div>
        ) : (
          <p className="text-muted-foreground text-sm">Tier no registrado</p>
        )}
        {doc.confianza != null && (
          <Campo
            label="Confianza"
            value={
              <span className={`font-bold ${doc.confianza >= 80 ? 'text-green-400' : doc.confianza >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                {doc.confianza}%
              </span>
            }
          />
        )}
        {doc.motivo_cuarentena && (
          <div className="mt-2 rounded-md bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive">
            {doc.motivo_cuarentena}
          </div>
        )}
      </SeccionPanel>

      {/* Contabilización FS */}
      {doc.asiento && (
        <>
          <Separator />
          <SeccionPanel titulo="Contabilización en FacturaScripts">
            {doc.asiento.numero != null && (
              <Campo label="Asiento contable" value={`#${doc.asiento.numero}`} />
            )}
            {doc.asiento.fecha && <Campo label="Fecha asiento" value={doc.asiento.fecha} />}
            {doc.asiento.concepto && <Campo label="Concepto" value={doc.asiento.concepto} />}
            {doc.factura_id_fs && (
              <Campo label="idfactura FS" value={<span className="font-mono">{doc.factura_id_fs}</span>} />
            )}
            {doc.asiento.idasiento_fs && (
              <Campo label="idasiento FS" value={<span className="font-mono">{doc.asiento.idasiento_fs}</span>} />
            )}
            {doc.asiento.partidas.length > 0 && (
              <div className="mt-3">
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">Partidas</p>
                <div className="rounded-md border overflow-hidden">
                  <table className="w-full text-xs font-mono">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left px-2 py-1.5 font-medium">Subcuenta</th>
                        <th className="text-left px-2 py-1.5 font-medium">Concepto</th>
                        <th className="text-right px-2 py-1.5 font-medium text-blue-400">Debe</th>
                        <th className="text-right px-2 py-1.5 font-medium text-amber-400">Haber</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {doc.asiento.partidas.map((p, i) => (
                        <tr key={i} className="hover:bg-muted/20">
                          <td className="px-2 py-1.5 text-muted-foreground">{p.subcuenta}</td>
                          <td className="px-2 py-1.5 max-w-[120px] truncate text-muted-foreground">{p.concepto ?? ''}</td>
                          <td className="px-2 py-1.5 text-right">{p.debe > 0 ? <span className="text-blue-400">{p.debe.toFixed(2)}</span> : ''}</td>
                          <td className="px-2 py-1.5 text-right">{p.haber > 0 ? <span className="text-amber-400">{p.haber.toFixed(2)}</span> : ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </SeccionPanel>
        </>
      )}
    </div>
  )
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

// ─── Página principal ─────────────────────────────────────────────────────────

export default function DocumentosEmpresaPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [ejercicio, setEjercicio] = useState<string>('todos')
  const [estado, setEstado] = useState<string>('todos')
  const [tipo, setTipo] = useState<string>('todos')
  const [docSeleccionado, setDocSeleccionado] = useState<DocumentoItem | null>(null)

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
          <SelectTrigger className="w-36"><SelectValue placeholder="Ejercicio" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos los años</SelectItem>
            {['2025', '2024', '2023'].map(y => <SelectItem key={y} value={y}>{y}</SelectItem>)}
          </SelectContent>
        </Select>

        <Select value={estado} onValueChange={setEstado}>
          <SelectTrigger className="w-40"><SelectValue placeholder="Estado" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos los estados</SelectItem>
            <SelectItem value="registrado">Registrado</SelectItem>
            <SelectItem value="cuarentena">Cuarentena</SelectItem>
            <SelectItem value="pendiente">Pendiente</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>

        <Select value={tipo} onValueChange={setTipo}>
          <SelectTrigger className="w-44"><SelectValue placeholder="Tipo" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos los tipos</SelectItem>
            {Object.entries(TIPO_LABEL).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
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
                <th className="px-2 py-3 w-6 sr-only">Abrir</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((doc) => (
                <tr
                  key={doc.id}
                  className="hover:bg-muted/40 transition-colors cursor-pointer"
                  onClick={() => setDocSeleccionado(doc)}
                >
                  <td className="px-4 py-3">
                    <Badge variant="outline" className="font-mono text-xs">{doc.tipo_doc}</Badge>
                    {doc.tipo_doc in TIPO_LABEL && (
                      <span className="ml-2 text-muted-foreground text-xs hidden xl:inline">
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
                    {doc.total != null ? fmtEur(doc.total) : '—'}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {doc.fecha_factura ?? (doc.fecha_proceso ? doc.fecha_proceso.slice(0, 10) : '—')}
                  </td>
                  <td className="px-4 py-3"><BadgeEstado estado={doc.estado} /></td>
                  <td className="px-4 py-3">
                    {doc.confianza != null ? (
                      <span className={doc.confianza >= 80 ? 'text-green-500' : doc.confianza >= 50 ? 'text-amber-500' : 'text-red-500'}>
                        {doc.confianza}%
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                    {doc.factura_id_fs ?? '—'}
                  </td>
                  <td className="px-2 py-3 text-muted-foreground/40">
                    <ChevronRight className="h-3.5 w-3.5" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Panel lateral de detalles */}
      <Sheet open={!!docSeleccionado} onOpenChange={(open) => { if (!open) setDocSeleccionado(null) }}>
        <SheetContent className="w-[480px] sm:max-w-[480px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Documento #{docSeleccionado?.id}
            </SheetTitle>
          </SheetHeader>
          {docSeleccionado && (
            <DocumentoPanel doc={docSeleccionado} empresaId={empresaId} />
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
