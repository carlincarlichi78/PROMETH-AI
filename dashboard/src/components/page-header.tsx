interface PageHeaderProps {
  titulo: string
  descripcion?: string
  acciones?: React.ReactNode
}

export function PageHeader({ titulo, descripcion, acciones }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{titulo}</h1>
        {descripcion && (
          <p className="text-muted-foreground mt-1 text-sm">{descripcion}</p>
        )}
      </div>
      {acciones && <div className="flex gap-2 flex-shrink-0">{acciones}</div>}
    </div>
  )
}
