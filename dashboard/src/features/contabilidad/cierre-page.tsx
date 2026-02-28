import { CheckCircle, Circle, Calculator, FileText, Archive, BookOpen } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface PasoCierre {
  titulo: string
  descripcion: string
  icono: React.ElementType
  detalle: string
  completado: boolean
}

const PASOS: PasoCierre[] = [
  {
    titulo: 'Verificar asientos',
    descripcion: 'Comprobar cuadre debe/haber',
    icono: Calculator,
    detalle:
      'Revisa que todos los asientos del ejercicio cuadren: la suma del debe debe ser igual a la suma del haber. Se comprueba tambien que no existan partidas huerfanas.',
    completado: false,
  },
  {
    titulo: 'Regularizacion',
    descripcion: 'Asientos de regularizacion 129/xxx',
    icono: FileText,
    detalle:
      'Genera el asiento de regularizacion que traslada los saldos de las cuentas de ingresos y gastos (grupos 6 y 7) a la cuenta 129 (Resultado del ejercicio).',
    completado: false,
  },
  {
    titulo: 'Cierre contable',
    descripcion: 'Asiento de cierre del ejercicio',
    icono: Archive,
    detalle:
      'Genera el asiento de cierre que salda todas las cuentas del balance (grupos 1-5) con cargo o abono a sus respectivas contrapartidas.',
    completado: false,
  },
  {
    titulo: 'Apertura nuevo ejercicio',
    descripcion: 'Asiento de apertura del nuevo ejercicio',
    icono: BookOpen,
    detalle:
      'Crea el asiento de apertura del nuevo ejercicio invirtiendo el asiento de cierre, trasladando los saldos al nuevo periodo contable.',
    completado: false,
  },
]

export default function CierrePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Cierre de Ejercicio"
        descripcion="Proceso de cierre contable — verificacion, regularizacion, cierre y apertura"
        acciones={
          <Badge variant="secondary" className="text-xs">
            En desarrollo
          </Badge>
        }
      />

      <div className="rounded-lg border bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800 p-4">
        <p className="text-sm text-amber-800 dark:text-amber-300">
          El proceso de cierre automatico esta en desarrollo. Por ahora puedes realizar el
          cierre manualmente desde FacturaScripts. Los botones se habilitaran en la proxima
          version.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PASOS.map((paso, index) => {
          const Icono = paso.icono
          const IconoEstado = paso.completado ? CheckCircle : Circle
          return (
            <Card key={paso.titulo} className="relative">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted">
                      <span className="text-sm font-bold text-muted-foreground">
                        {index + 1}
                      </span>
                    </div>
                    <div>
                      <CardTitle className="text-sm font-medium">{paso.titulo}</CardTitle>
                      <p className="text-xs text-muted-foreground mt-0.5">{paso.descripcion}</p>
                    </div>
                  </div>
                  <IconoEstado
                    className={`h-5 w-5 flex-shrink-0 ${
                      paso.completado
                        ? 'text-green-500'
                        : 'text-muted-foreground/30'
                    }`}
                  />
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-start gap-3">
                  <Icono className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {paso.detalle}
                  </p>
                </div>
                <div className="mt-4">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span>
                          <Button size="sm" disabled className="w-full">
                            Ejecutar
                          </Button>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="text-xs">Funcionalidad en desarrollo</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
