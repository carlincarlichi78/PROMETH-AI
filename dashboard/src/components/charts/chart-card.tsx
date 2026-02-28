import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface ChartCardProps {
  titulo: string
  children: React.ReactNode
  periodos?: string[]
  periodoActual?: string
  onCambioPeriodo?: (periodo: string) => void
  cargando?: boolean
  className?: string
  altura?: number
  acciones?: React.ReactNode
}

export function ChartCard({
  titulo,
  children,
  periodos,
  periodoActual,
  onCambioPeriodo,
  cargando,
  className,
  altura = 300,
  acciones,
}: ChartCardProps) {
  return (
    <Card className={cn('', className)}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">{titulo}</CardTitle>
        <div className="flex items-center gap-2">
          {acciones}
          {periodos && periodos.length > 0 && (
            <Select value={periodoActual} onValueChange={onCambioPeriodo}>
              <SelectTrigger className="w-32 h-7 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {periodos.map((p) => (
                  <SelectItem key={p} value={p} className="text-xs">
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {cargando ? (
          <Skeleton className="w-full rounded-md" style={{ height: altura }} />
        ) : (
          <div style={{ height: altura }}>{children}</div>
        )}
      </CardContent>
    </Card>
  )
}
