import { useEffect, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search, X } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface FiltrosMovimientos {
  q: string
  fechaDesde: string
  fechaHasta: string
}

interface Props {
  onChange: (filtros: FiltrosMovimientos) => void
  className?: string
}

const FILTROS_VACIOS: FiltrosMovimientos = { q: '', fechaDesde: '', fechaHasta: '' }

export function FilterBar({ onChange, className }: Props) {
  const [qLocal, setQLocal] = useState('')
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')

  // Debounce para q y fechas
  useEffect(() => {
    const t = setTimeout(() => {
      onChange({ q: qLocal, fechaDesde, fechaHasta })
    }, 400)
    return () => clearTimeout(t)
  }, [qLocal, fechaDesde, fechaHasta, onChange])

  const hayFiltros = qLocal || fechaDesde || fechaHasta

  const limpiar = () => {
    setQLocal('')
    setFechaDesde('')
    setFechaHasta('')
    onChange(FILTROS_VACIOS)
  }

  return (
    <div className={cn('flex items-center gap-2 flex-wrap', className)}>
      {/* Busqueda texto */}
      <div className="relative flex-1 min-w-[180px]">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
        <Input
          placeholder="Buscar concepto o contraparte…"
          value={qLocal}
          onChange={(e) => setQLocal(e.target.value)}
          className="pl-8 h-8 text-sm"
        />
      </div>

      {/* Fecha desde */}
      <input
        type="date"
        value={fechaDesde}
        onChange={(e) => setFechaDesde(e.target.value)}
        className="h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        title="Fecha desde"
        max={fechaHasta || undefined}
      />

      {/* Fecha hasta */}
      <input
        type="date"
        value={fechaHasta}
        onChange={(e) => setFechaHasta(e.target.value)}
        className="h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        title="Fecha hasta"
        min={fechaDesde || undefined}
      />

      {/* Limpiar filtros */}
      {hayFiltros && (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 px-2 text-muted-foreground hover:text-foreground"
          onClick={limpiar}
        >
          <X className="h-3.5 w-3.5 mr-1" />
          Limpiar
        </Button>
      )}
    </div>
  )
}
