import { useState, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { PageTitle } from '@/components/ui/page-title'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { LoteProgressCard } from './lote-progress-card'
import { PerfilRevisionCard } from './perfil-revision-card'

const API = (path: string) => `/api${path}`

interface Lote {
  lote_id: number
  nombre: string
  estado: string
  total_clientes: number
  completados: number
  en_revision: number
  bloqueados: number
}

export function OnboardingMasivoPage() {
  const [nombre, setNombre] = useState('')
  const [loteActual, setLoteActual] = useState<number | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const qc = useQueryClient()

  const { mutate: subirLote, isPending } = useMutation({
    mutationFn: async (formData: FormData) => {
      const r = await fetch(API('/onboarding/lotes'), {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        body: formData,
      })
      if (!r.ok) throw new Error(await r.text())
      return r.json()
    },
    onSuccess: (data) => {
      setLoteActual(data.lote_id)
      qc.invalidateQueries({ queryKey: ['lote', data.lote_id] })
    },
  })

  const { data: lote } = useQuery<Lote>({
    queryKey: ['lote', loteActual],
    queryFn: async () => {
      const r = await fetch(API(`/onboarding/lotes/${loteActual}`), {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
      return r.json()
    },
    enabled: !!loteActual,
    refetchInterval: loteActual ? 3000 : false,
  })

  const handleSubir = () => {
    const archivo = fileRef.current?.files?.[0]
    if (!archivo || !nombre.trim()) return
    const fd = new FormData()
    fd.append('nombre', nombre)
    fd.append('archivo', archivo)
    subirLote(fd)
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <PageTitle
        titulo="Onboarding Masivo"
        subtitulo="Alta automatizada de todos los clientes de una gestoría"
      />

      {!loteActual && (
        <div className="border rounded-lg p-6 space-y-4">
          <h2 className="font-semibold text-lg">Nuevo lote</h2>
          <Input
            placeholder="Nombre del lote (ej: Gestoria XYZ — Marzo 2026)"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
          <div className="border-2 border-dashed rounded-lg p-8 text-center">
            <p className="text-muted-foreground mb-3">
              ZIP, PDFs, CSVs, Excel — todo vale
            </p>
            <input ref={fileRef} type="file" accept=".zip,.pdf,.csv,.xlsx"
                   className="hidden" id="file-input"
                   title="Seleccionar archivos de onboarding"
                   aria-label="Seleccionar archivos de onboarding" />
            <Button variant="outline" onClick={() =>
              fileRef.current?.click()}>
              Seleccionar archivos
            </Button>
          </div>
          <Button onClick={handleSubir} disabled={isPending || !nombre.trim()}>
            {isPending ? 'Subiendo...' : 'Subir y procesar →'}
          </Button>
        </div>
      )}

      {lote && <LoteProgressCard lote={lote} />}

      {lote && lote.en_revision > 0 && loteActual && (
        <PerfilRevisionCard loteId={loteActual} />
      )}
    </div>
  )
}
