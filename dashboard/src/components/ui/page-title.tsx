// src/components/ui/page-title.tsx
import { cn } from '@/lib/utils'

interface PageTitleProps {
  titulo: string
  subtitulo?: string
  acciones?: React.ReactNode
  className?: string
}

export function PageTitle({ titulo, subtitulo, acciones, className }: PageTitleProps) {
  return (
    <div className={cn('flex items-start justify-between mb-6', className)}>
      <div>
        <h1 className="text-[28px] font-bold tracking-tight bg-gradient-to-r from-[var(--primary)] to-foreground bg-clip-text text-transparent">
          {titulo}
        </h1>
        {subtitulo && (
          <p className="text-[14px] text-muted-foreground mt-1">{subtitulo}</p>
        )}
      </div>
      {acciones && <div className="flex items-center gap-2">{acciones}</div>}
    </div>
  )
}
