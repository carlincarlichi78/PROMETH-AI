import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { Button } from '@/components/ui/button'

interface ResultadoZIP {
  encolados: number
  rechazados: number
  errores: string[]
}

export function SubirZIP({ empresaId }: { empresaId: number }) {
  const [archivo, setArchivo] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)

  const mutation = useMutation({
    mutationFn: (zip: File): Promise<ResultadoZIP> => {
      const form = new FormData()
      form.append('archivo', zip)
      form.append('empresa_id', String(empresaId))
      return api.postForm<ResultadoZIP>('/api/gate0/ingestar-zip', form)
    },
    onSuccess: () => setArchivo(null),
  })

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f?.name.toLowerCase().endsWith('.zip')) setArchivo(f)
  }, [])

  return (
    <div className="space-y-4">
      <div
        onDrop={onDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        className={[
          'border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer',
          dragOver
            ? 'border-amber-400 bg-amber-50/10'
            : 'border-border hover:border-amber-400/50',
        ].join(' ')}
      >
        <p className="text-muted-foreground text-sm">
          Arrastra un <span className="font-semibold text-foreground">.zip</span> con facturas PDF
        </p>
        <p className="text-xs text-muted-foreground mt-1">o selecciona un archivo</p>
        <input
          type="file"
          accept=".zip"
          className="mt-3 text-sm file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:bg-amber-500/20 file:text-amber-300 hover:file:bg-amber-500/30"
          onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
        />
      </div>

      {archivo && !mutation.isPending && !mutation.isSuccess && (
        <div className="flex items-center justify-between p-3 bg-muted/40 rounded-lg border border-border">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">📦</span>
            <span className="truncate max-w-[240px]">{archivo.name}</span>
            <span className="text-xs text-muted-foreground">
              ({(archivo.size / 1024 / 1024).toFixed(1)} MB)
            </span>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => setArchivo(null)}>
              Cancelar
            </Button>
            <Button size="sm" onClick={() => mutation.mutate(archivo)}>
              Ingestar ZIP
            </Button>
          </div>
        </div>
      )}

      {mutation.isPending && (
        <div className="p-4 bg-muted/40 rounded-lg border border-border text-sm text-muted-foreground animate-pulse">
          Procesando ZIP...
        </div>
      )}

      {mutation.isSuccess && (
        <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg space-y-1">
          <p className="font-semibold text-green-400 text-sm">
            ✓ {mutation.data.encolados} documento{mutation.data.encolados !== 1 ? 's' : ''} encolado{mutation.data.encolados !== 1 ? 's' : ''}
          </p>
          {mutation.data.rechazados > 0 && (
            <p className="text-amber-400 text-sm">
              ⚠ {mutation.data.rechazados} rechazado{mutation.data.rechazados !== 1 ? 's' : ''} (PDF inválido o duplicado)
            </p>
          )}
          {mutation.data.errores.slice(0, 5).map((err, i) => (
            <p key={i} className="text-red-400 text-xs">{err}</p>
          ))}
          <Button variant="ghost" size="sm" className="mt-2" onClick={() => mutation.reset()}>
            Subir otro ZIP
          </Button>
        </div>
      )}

      {mutation.isError && (
        <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
          Error al procesar el ZIP. Comprueba que el archivo no supera 500 MB.
        </div>
      )}
    </div>
  )
}
