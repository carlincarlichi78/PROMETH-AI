// src/components/ui/empty-state.tsx
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface EmptyStateProps {
  icono?: React.ReactNode
  titulo: string
  descripcion: string
  accion?: {
    texto: string
    onClick: () => void
  }
  className?: string
}

export function EmptyState({ icono, titulo, descripcion, accion, className }: EmptyStateProps) {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center py-16 px-8 text-center',
      className
    )}>
      {icono && (
        <div className="mb-5 p-4 rounded-2xl bg-[var(--surface-1)] text-muted-foreground">
          {icono}
        </div>
      )}
      <h3 className="text-[18px] font-semibold text-foreground mb-2">{titulo}</h3>
      <p className="text-[14px] text-muted-foreground max-w-sm leading-relaxed mb-6">
        {descripcion}
      </p>
      {accion && (
        <Button onClick={accion.onClick} className="gap-2">
          {accion.texto}
        </Button>
      )}
    </div>
  )
}
