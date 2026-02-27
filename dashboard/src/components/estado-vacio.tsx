import { FileText } from 'lucide-react'

interface EstadoVacioProps {
  titulo: string
  descripcion?: string
  icono?: React.ElementType
  accion?: React.ReactNode
}

export function EstadoVacio({
  titulo,
  descripcion,
  icono: Icono = FileText,
  accion,
}: EstadoVacioProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Icono className="h-12 w-12 text-muted-foreground/40 mb-4" />
      <h3 className="text-lg font-medium">{titulo}</h3>
      {descripcion && (
        <p className="text-sm text-muted-foreground mt-1 max-w-md">{descripcion}</p>
      )}
      {accion && <div className="mt-4">{accion}</div>}
    </div>
  )
}
