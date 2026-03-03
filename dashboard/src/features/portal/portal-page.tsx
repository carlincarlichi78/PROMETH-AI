// Portal Cliente — vista simplificada para el cliente final
import { useState, useEffect } from 'react'
import { useParams, Navigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Download, FileText, Receipt, TrendingUp, TrendingDown, Clock, AlertCircle, Upload } from 'lucide-react'
import { useRef } from 'react'

interface ResumenPortal {
  empresa_id: number
  nombre: string
  ejercicio: string
  resultado_acumulado: number
  facturas_pendientes_cobro: number
  importe_pendiente_cobro: number
  facturas_pendientes_pago: number
  importe_pendiente_pago: number
}

interface DocumentoPortal {
  id: number
  nombre: string
  tipo: string
  estado: string
  fecha: string | null
}

const CLAVE_TOKEN = 'sfce_token'

function fmt(n: number) {
  return n.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

async function apiFetch<T>(url: string, token: string): Promise<T> {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export default function PortalPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id) || 1
  const token = sessionStorage.getItem(CLAVE_TOKEN)

  const [resumen, setResumen] = useState<ResumenPortal | null>(null)
  const [documentos, setDocumentos] = useState<DocumentoPortal[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [descargando, setDescargando] = useState(false)
  const [subiendo, setSubiendo] = useState(false)
  const [mensajeSubida, setMensajeSubida] = useState<string | null>(null)
  const inputFileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!token) return
    setCargando(true)
    setError(null)
    Promise.all([
      apiFetch<ResumenPortal>(`/api/portal/${empresaId}/resumen`, token),
      apiFetch<{ documentos: DocumentoPortal[] }>(`/api/portal/${empresaId}/documentos`, token),
    ])
      .then(([r, d]) => {
        setResumen(r)
        setDocumentos(d.documentos ?? [])
      })
      .catch(() => setError('No se pudo cargar la información. Verifica tu conexión.'))
      .finally(() => setCargando(false))
  }, [empresaId, token])

  // Sin token → redirigir a login (después de todos los hooks)
  if (!token) {
    return <Navigate to="/login" state={{ from: { pathname: `/portal/${empresaId}` } }} replace />
  }

  if (cargando) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-muted-foreground text-sm">Cargando...</div>
      </div>
    )
  }

  const subirDocumento = async (archivo: File) => {
    if (!token) return
    setSubiendo(true)
    setMensajeSubida(null)
    try {
      const form = new FormData()
      form.append('archivo', archivo)
      form.append('tipo', 'Factura')
      const res = await fetch(`/api/portal/${empresaId}/documentos/subir`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      if (!res.ok) throw new Error(`${res.status}`)
      setMensajeSubida('Documento enviado correctamente. Se procesará en breve.')
      // Recargar lista documentos
      const d = await apiFetch<{ documentos: DocumentoPortal[] }>(`/api/portal/${empresaId}/documentos`, token)
      setDocumentos(d.documentos ?? [])
    } catch {
      setMensajeSubida('No se pudo enviar el documento. Inténtalo de nuevo.')
    } finally {
      setSubiendo(false)
      if (inputFileRef.current) inputFileRef.current.value = ''
    }
  }

  const descargarDatos = async () => {
    if (!token) return
    setDescargando(true)
    try {
      const res = await fetch(`/api/empresas/${empresaId}/exportar-datos`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Error al solicitar exportación')
      const { url_descarga } = await res.json() as { url_descarga: string }
      window.open(url_descarga, '_blank')
    } catch {
      setError('No se pudo iniciar la descarga. Contacta con tu gestoría.')
    } finally {
      setDescargando(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Encabezado empresa */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">
            {resumen?.nombre ?? 'Mi empresa'}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Ejercicio {resumen?.ejercicio} · Vista cliente
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={descargarDatos}
          disabled={descargando}
          className="gap-2"
        >
          <Download className="h-4 w-4" />
          {descargando ? 'Preparando...' : 'Descargar mis datos'}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* KPIs */}
      {resumen && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
                {resumen.resultado_acumulado >= 0
                  ? <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                  : <TrendingDown className="h-3.5 w-3.5 text-red-500" />}
                Resultado acumulado
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className={`text-lg font-bold ${resumen.resultado_acumulado >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {fmt(resumen.resultado_acumulado)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
                <Receipt className="h-3.5 w-3.5 text-blue-500" />
                Pendiente cobro
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-lg font-bold text-blue-600">{fmt(resumen.importe_pendiente_cobro)}</p>
              <p className="text-xs text-slate-400">{resumen.facturas_pendientes_cobro} facturas</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-amber-500" />
                Pendiente pago
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-lg font-bold text-amber-600">{fmt(resumen.importe_pendiente_pago)}</p>
              <p className="text-xs text-slate-400">{resumen.facturas_pendientes_pago} facturas</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs font-medium text-slate-500 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-slate-400" />
                Documentos
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-lg font-bold text-slate-700">{documentos.length}</p>
              <p className="text-xs text-slate-400">procesados</p>
            </CardContent>
          </Card>
        </div>
      )}

      <Separator />

      {/* Subir documento */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-700">Enviar documento</h2>
        <div className="rounded-lg border-2 border-dashed border-slate-200 bg-white px-6 py-8 text-center">
          <Upload className="h-8 w-8 mx-auto text-slate-300 mb-3" />
          <p className="text-sm text-slate-500 mb-4">
            Sube tus facturas, tickets o cualquier documento contable
          </p>
          <input
            ref={inputFileRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            aria-label="Seleccionar documento a subir"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) subirDocumento(f)
            }}
          />
          <Button
            variant="outline"
            size="sm"
            disabled={subiendo}
            onClick={() => inputFileRef.current?.click()}
            className="gap-2"
          >
            <Upload className="h-4 w-4" />
            {subiendo ? 'Enviando...' : 'Seleccionar archivo'}
          </Button>
          {mensajeSubida && (
            <p className={`mt-3 text-xs ${mensajeSubida.includes('correctamente') ? 'text-emerald-600' : 'text-red-500'}`}>
              {mensajeSubida}
            </p>
          )}
        </div>
      </div>

      <Separator />

      {/* Documentos recientes */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-700">Documentos recientes</h2>
        {documentos.length === 0 ? (
          <p className="text-sm text-slate-400 py-4 text-center">Sin documentos procesados.</p>
        ) : (
          <div className="space-y-2">
            {documentos.slice(0, 20).map((d) => (
              <div
                key={d.id}
                className="flex items-center gap-3 rounded-lg border bg-white px-4 py-2.5 text-sm"
              >
                <Badge variant="secondary" className="text-[10px] uppercase tracking-wide shrink-0">
                  {d.tipo}
                </Badge>
                <span className="flex-1 text-slate-700 truncate">{d.nombre}</span>
                <Badge
                  variant={d.estado === 'procesado' ? 'default' : 'outline'}
                  className={`shrink-0 text-[10px] ${d.estado === 'procesado' ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-50' : 'text-amber-600 border-amber-200'}`}
                >
                  {d.estado}
                </Badge>
                {d.fecha && (
                  <span className="text-xs text-slate-400 shrink-0">
                    {new Date(d.fecha).toLocaleDateString('es-ES')}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
