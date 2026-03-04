// dashboard/src/features/pipeline/components/SubirDocumentos.tsx
import { useState, useCallback, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { Button } from '@/components/ui/button'

interface ResultadoIngestar {
  documento_id?: number
  estado?: string
  mensaje?: string
}

interface ResultadoZIP {
  encolados: number
  rechazados: number
  errores: string[]
}

interface Props {
  empresaId: number | undefined
  empresas: Array<{ id: number; nombre: string }>
}

export function SubirDocumentos({ empresaId, empresas }: Props) {
  const [abierto, setAbierto] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [empresaLocal, setEmpresaLocal] = useState<number | ''>(empresaId ?? '')
  const inputRef = useRef<HTMLInputElement>(null)
  const qc = useQueryClient()

  const empresaEfectiva = empresaId ?? (empresaLocal !== '' ? Number(empresaLocal) : undefined)

  const mutPdf = useMutation({
    mutationFn: (archivo: File): Promise<ResultadoIngestar> => {
      const form = new FormData()
      form.append('archivo', archivo)
      form.append('empresa_id', String(empresaEfectiva))
      return api.postForm<ResultadoIngestar>('/api/gate0/ingestar', form)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-status'] }),
  })

  const mutZip = useMutation({
    mutationFn: (archivo: File): Promise<ResultadoZIP> => {
      const form = new FormData()
      form.append('archivo', archivo)
      form.append('empresa_id', String(empresaEfectiva))
      return api.postForm<ResultadoZIP>('/api/gate0/ingestar-zip', form)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-status'] }),
  })

  const procesarArchivo = useCallback((archivo: File) => {
    if (!empresaEfectiva) return
    mutPdf.reset(); mutZip.reset()
    if (archivo.name.toLowerCase().endsWith('.zip')) {
      mutZip.mutate(archivo)
    } else {
      mutPdf.mutate(archivo)
    }
  }, [empresaEfectiva, mutPdf, mutZip])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const archivo = e.dataTransfer.files[0]
    if (archivo) procesarArchivo(archivo)
  }, [procesarArchivo])

  const isPending = mutPdf.isPending || mutZip.isPending
  const isError   = mutPdf.isError   || mutZip.isError

  return (
    <div className="px-4 pb-3">
      {/* Botón toggle */}
      <button
        type="button"
        onClick={() => setAbierto(v => !v)}
        className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <span className="text-amber-400">+</span>
        <span>{abierto ? 'Ocultar zona de subida' : 'Subir documentos manualmente'}</span>
        <span className="text-muted-foreground/50">{abierto ? '▲' : '▼'}</span>
      </button>

      {abierto && (
        <div className="mt-3 p-4 rounded-xl border border-border bg-background/40 backdrop-blur-sm space-y-3">
          {/* Selector de empresa si no hay una seleccionada */}
          {!empresaId && (
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Empresa destino</label>
              <select
                aria-label="Empresa destino"
                className="w-full text-sm bg-muted/40 border border-border rounded-md px-2 py-1.5 text-foreground"
                value={empresaLocal}
                onChange={e => setEmpresaLocal(e.target.value === '' ? '' : Number(e.target.value))}
              >
                <option value="">— seleccionar empresa —</option>
                {empresas.map(emp => (
                  <option key={emp.id} value={emp.id}>{emp.nombre}</option>
                ))}
              </select>
            </div>
          )}

          {/* Zona drop */}
          <div
            onDrop={onDrop}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => inputRef.current?.click()}
            className={[
              'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all',
              !empresaEfectiva
                ? 'opacity-40 pointer-events-none border-border'
                : dragOver
                  ? 'border-amber-400 bg-amber-400/5 scale-[1.01]'
                  : 'border-border hover:border-amber-400/50 hover:bg-amber-400/5',
            ].join(' ')}
          >
            {isPending ? (
              <div className="flex flex-col items-center gap-2">
                <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
                <p className="text-xs text-muted-foreground">Procesando...</p>
              </div>
            ) : (
              <>
                <p className="text-2xl mb-1">📄</p>
                <p className="text-sm text-muted-foreground">
                  Arrastra un <span className="text-foreground font-medium">PDF</span> o{' '}
                  <span className="text-foreground font-medium">.zip</span> de facturas
                </p>
                <p className="text-xs text-muted-foreground/60 mt-1">o haz clic para seleccionar</p>
              </>
            )}
          </div>

          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.zip"
            aria-label="Seleccionar PDF o ZIP para ingestar"
            className="hidden"
            onChange={e => {
              const f = e.target.files?.[0]
              if (f) { procesarArchivo(f); e.target.value = '' }
            }}
          />

          {/* Resultado PDF */}
          {mutPdf.isSuccess && (
            <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-sm text-green-400">
              Documento encolado correctamente
            </div>
          )}

          {/* Resultado ZIP */}
          {mutZip.isSuccess && (
            <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg space-y-1">
              <p className="text-sm font-medium text-green-400">
                {mutZip.data.encolados} documento{mutZip.data.encolados !== 1 ? 's' : ''} encolado{mutZip.data.encolados !== 1 ? 's' : ''}
              </p>
              {mutZip.data.rechazados > 0 && (
                <p className="text-xs text-amber-400">{mutZip.data.rechazados} rechazados (duplicado o PDF inválido)</p>
              )}
              {mutZip.data.errores.slice(0, 3).map((err, i) => (
                <p key={i} className="text-xs text-red-400">{err}</p>
              ))}
              <Button variant="ghost" size="sm" className="mt-1 text-xs h-6" onClick={() => mutZip.reset()}>
                Subir otro
              </Button>
            </div>
          )}

          {isError && (
            <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-xs text-destructive">
              {mutPdf.error instanceof Error ? mutPdf.error.message : mutZip.error instanceof Error ? mutZip.error.message : 'Error al ingestar'}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
