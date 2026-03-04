/**
 * Tarjeta de sugerencia de match para revisión humana.
 * Muestra movimiento bancario vs documento pipeline con score visual.
 */
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'
import { CheckCircle, XCircle, FileText } from 'lucide-react'
import type { SugerenciaMatch } from '../api'

interface MatchCardProps {
  sugerencia: SugerenciaMatch
  onConfirmar: (movimientoId: number, documentoId: number) => void
  onRechazar: (movimientoId: number, documentoId: number) => void
  onVerPdf?: (documentoId: number) => void
  cargando?: boolean
}

const CAPA_LABEL: Record<number, string> = {
  1: 'Importe exacto',
  2: 'NIF proveedor',
  3: 'Nº factura',
  4: 'Patrón aprendido',
  5: 'Importe ≈',
  0: 'Manual',
}

function scoreColor(score: number): string {
  if (score >= 0.9) return 'bg-green-100 text-green-800'
  if (score >= 0.7) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

export function MatchCard({
  sugerencia,
  onConfirmar,
  onRechazar,
  onVerPdf,
  cargando = false,
}: MatchCardProps) {
  const { movimiento, documento } = sugerencia

  return (
    <Card className="border-l-4 border-l-blue-400">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <div className="flex gap-2 items-center">
          <Badge variant="outline" className={scoreColor(sugerencia.score)}>
            {Math.round(sugerencia.score * 100)}% —{' '}
            {CAPA_LABEL[sugerencia.capa_origen] ?? `Capa ${sugerencia.capa_origen}`}
          </Badge>
        </div>
        <span className="text-xs text-muted-foreground">{movimiento.fecha}</span>
      </CardHeader>

      <CardContent className="grid grid-cols-2 gap-4 text-sm">
        {/* Movimiento bancario */}
        <div className="space-y-1">
          <p className="font-semibold text-blue-700 uppercase text-xs tracking-wide">Banco</p>
          <p className="font-mono text-lg font-bold">
            {movimiento.signo === 'H' ? '+' : '-'}
            {movimiento.importe.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}
          </p>
          <p className="text-muted-foreground truncate">{movimiento.concepto_propio}</p>
          <p className="text-muted-foreground">{movimiento.nombre_contraparte}</p>
        </div>

        {/* Documento pipeline */}
        <div className="space-y-1">
          <p className="font-semibold text-purple-700 uppercase text-xs tracking-wide">Documento</p>
          {documento ? (
            <>
              <p className="font-mono text-lg font-bold">
                {documento.importe_total?.toLocaleString('es-ES', {
                  style: 'currency',
                  currency: 'EUR',
                }) ?? '—'}
              </p>
              <p className="text-muted-foreground truncate">{documento.nombre_archivo}</p>
              {documento.numero_factura && (
                <p className="text-xs text-muted-foreground">Ref: {documento.numero_factura}</p>
              )}
              {documento.nif_proveedor && (
                <p className="text-xs text-muted-foreground">NIF: {documento.nif_proveedor}</p>
              )}
            </>
          ) : (
            <p className="text-muted-foreground italic">Sin documento asociado</p>
          )}
        </div>
      </CardContent>

      <CardFooter className="gap-2 pt-2">
        <Button
          size="sm"
          variant="default"
          className="flex-1 bg-green-600 hover:bg-green-700"
          disabled={cargando}
          onClick={() => onConfirmar(sugerencia.movimiento_id, sugerencia.documento_id)}
        >
          <CheckCircle className="w-4 h-4 mr-1" />
          Confirmar
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1 text-red-600 border-red-300 hover:bg-red-50"
          disabled={cargando}
          onClick={() => onRechazar(sugerencia.movimiento_id, sugerencia.documento_id)}
        >
          <XCircle className="w-4 h-4 mr-1" />
          Rechazar
        </Button>
        {onVerPdf && documento && (
          <Button size="sm" variant="ghost" onClick={() => onVerPdf(documento.id)}>
            <FileText className="w-4 h-4" />
          </Button>
        )}
      </CardFooter>
    </Card>
  )
}
