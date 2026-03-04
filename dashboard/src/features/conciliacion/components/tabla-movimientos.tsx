import { Badge } from '@/components/ui/badge'
import type { MovimientoBancario } from '../api'

const ESTADO_VARIANT: Record<string, 'secondary' | 'default' | 'outline' | 'destructive'> = {
  pendiente: 'secondary',
  sugerido: 'outline',
  conciliado: 'default',
  revision: 'outline',
  parcial: 'secondary',
  manual: 'destructive',
}

interface Props {
  movimientos: MovimientoBancario[]
  isLoading?: boolean
  titulo?: string
  mostrarDocumento?: boolean
}

export function TablaMovimientos({
  movimientos,
  isLoading = false,
  titulo,
  mostrarDocumento = false,
}: Props) {
  if (isLoading) {
    return (
      <div className="py-12 text-center text-muted-foreground text-sm">
        Cargando movimientos...
      </div>
    )
  }

  const colSpan = mostrarDocumento ? 7 : 6

  return (
    <div className="space-y-2">
      {titulo && <h3 className="text-sm font-medium text-muted-foreground">{titulo}</h3>}
      <div className="rounded-md border overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-2 text-left font-medium">Fecha</th>
              <th className="px-4 py-2 text-left font-medium">Contraparte</th>
              <th className="px-4 py-2 text-left font-medium">Concepto</th>
              <th className="px-4 py-2 text-left font-medium">Tipo</th>
              <th className="px-4 py-2 text-right font-medium">Importe</th>
              <th className="px-4 py-2 text-center font-medium">Estado</th>
              {mostrarDocumento && (
                <th className="px-4 py-2 text-center font-medium">Doc. ID</th>
              )}
            </tr>
          </thead>
          <tbody>
            {movimientos.map(m => (
              <tr key={m.id} className="border-t hover:bg-muted/20 transition-colors">
                <td className="px-4 py-2 tabular-nums text-muted-foreground whitespace-nowrap">
                  {m.fecha}
                </td>
                <td className="px-4 py-2 font-medium max-w-[160px] truncate">
                  {m.nombre_contraparte || '—'}
                </td>
                <td className="px-4 py-2 text-muted-foreground max-w-[260px] truncate">
                  {m.concepto_propio || '—'}
                </td>
                <td className="px-4 py-2 text-muted-foreground">
                  {m.tipo_clasificado ?? '—'}
                </td>
                <td
                  className={`px-4 py-2 text-right tabular-nums font-semibold ${
                    m.signo === 'H' ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {m.signo === 'H' ? '+' : '−'}
                  {m.importe.toFixed(2)} €
                </td>
                <td className="px-4 py-2 text-center">
                  <Badge variant={ESTADO_VARIANT[m.estado_conciliacion] ?? 'secondary'}>
                    {m.estado_conciliacion}
                  </Badge>
                </td>
                {mostrarDocumento && (
                  <td className="px-4 py-2 text-center text-xs text-muted-foreground">
                    {m.documento_id ?? '—'}
                  </td>
                )}
              </tr>
            ))}

            {movimientos.length === 0 && (
              <tr>
                <td
                  colSpan={colSpan}
                  className="px-4 py-12 text-center text-muted-foreground text-sm"
                >
                  Sin movimientos. Sube un extracto C43 o XLS para comenzar.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
