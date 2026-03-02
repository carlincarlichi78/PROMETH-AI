interface Lote {
  lote_id: number
  nombre: string
  estado: string
  total_clientes: number
  completados: number
  en_revision: number
  bloqueados: number
}

export function LoteProgressCard({ lote }: { lote: Lote }) {
  const pct = lote.total_clientes > 0
    ? Math.round((lote.completados / lote.total_clientes) * 100)
    : 0

  return (
    <div className="border rounded-lg p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="font-semibold">{lote.nombre}</h2>
        <span className="text-sm text-muted-foreground capitalize">
          {lote.estado}
        </span>
      </div>
      <div className="h-2 bg-muted rounded-full">
        <div className="h-2 bg-primary rounded-full transition-all"
             style={{ width: `${pct}%` }} />
      </div>
      <div className="grid grid-cols-4 gap-4 text-center">
        {[
          { label: 'Total', value: lote.total_clientes, color: '' },
          { label: '✅ Creados', value: lote.completados, color: 'text-green-600' },
          { label: '⚠ Revisión', value: lote.en_revision, color: 'text-yellow-600' },
          { label: '🔒 Bloqueados', value: lote.bloqueados, color: 'text-red-600' },
        ].map(({ label, value, color }) => (
          <div key={label}>
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
            <div className="text-xs text-muted-foreground">{label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
