import { ArrowDown, ArrowUp, Minus } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface KPICardProps {
  titulo: string
  valor: string
  variacion?: number // porcentaje vs periodo anterior (ej: 5.2 significa +5.2%)
  descripcion?: string
  icono?: React.ElementType
  className?: string
  cargando?: boolean
  /** Si true, valores negativos se muestran en verde (ej: gastos bajos = bueno) */
  invertirColor?: boolean
}

export function KPICard({
  titulo,
  valor,
  variacion,
  descripcion,
  icono: Icono,
  className,
  cargando,
  invertirColor,
}: KPICardProps) {
  const IconoVariacion =
    variacion != null && variacion > 0
      ? ArrowUp
      : variacion != null && variacion < 0
        ? ArrowDown
        : Minus

  const colorVariacion =
    variacion != null && variacion > 0
      ? invertirColor
        ? 'text-red-600 dark:text-red-400'
        : 'text-green-600 dark:text-green-400'
      : variacion != null && variacion < 0
        ? invertirColor
          ? 'text-green-600 dark:text-green-400'
          : 'text-red-600 dark:text-red-400'
        : 'text-muted-foreground'

  if (cargando) {
    return (
      <Card className={cn('border-l-2 border-l-primary/30', className)}>
        <CardHeader className="pb-2">
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-7 w-28" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn('border-l-2 border-l-primary/60 hover:border-l-primary transition-all duration-200', className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{titulo}</CardTitle>
        {Icono && <Icono className="h-4 w-4 text-primary/70" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tracking-tight">{valor}</div>
        {(variacion != null || descripcion) && (
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            {variacion != null && (
              <span
                className={cn('flex items-center text-xs font-medium', colorVariacion)}
              >
                <IconoVariacion className="h-3 w-3 mr-0.5" />
                {Math.abs(variacion).toFixed(1)}%
              </span>
            )}
            {descripcion && (
              <span className="text-xs text-muted-foreground">{descripcion}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
