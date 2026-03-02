import { useState, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { PageTitle } from '@/components/ui/page-title'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { LoteProgressCard } from './lote-progress-card'
import { PerfilRevisionCard } from './perfil-revision-card'

const API = (path: string) => `/api${path}`
const auth = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` })

interface Lote {
  lote_id: number
  nombre: string
  estado: string
  total_clientes: number
  completados: number
  en_revision: number
  bloqueados: number
}

const DOCS_REQUERIDOS = {
  obligatorio: [
    { codigo: '036/037', desc: 'Modelo 036/037 — Censo de empresarios (uno por empresa)' },
  ],
  recomendados: [
    { codigo: '303', desc: 'Modelo 303 — IVA trimestral' },
    { codigo: '390', desc: 'Modelo 390 — IVA anual' },
    { codigo: '200', desc: 'Modelo 200 — Impuesto Sociedades' },
    { codigo: 'LFE', desc: 'Libro de facturas emitidas (CSV/Excel)' },
    { codigo: 'LFR', desc: 'Libro de facturas recibidas (CSV/Excel)' },
    { codigo: 'SS', desc: 'Sumas y saldos (Excel)' },
  ],
  opcionales: [
    { codigo: '130', desc: 'Modelo 130 — IRPF fraccionado (autónomos)' },
    { codigo: '111', desc: 'Modelo 111 — Retenciones trimestrales' },
    { codigo: '347', desc: 'Modelo 347 — Operaciones con terceros' },
  ],
}

export function OnboardingMasivoPage() {
  const [nombre, setNombre] = useState('')
  const [loteActual, setLoteActual] = useState<number | null>(null)
  const [acordeonAbierto, setAcordeonAbierto] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const qc = useQueryClient()
  const navigate = useNavigate()

  const { mutate: subirLote, isPending } = useMutation({
    mutationFn: async (formData: FormData) => {
      const r = await fetch(API('/onboarding/lotes'), {
        method: 'POST',
        headers: auth(),
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
      const r = await fetch(API(`/onboarding/lotes/${loteActual}`), { headers: auth() })
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

          {/* Drop zone */}
          <div className="border-2 border-dashed rounded-lg p-8 text-center space-y-1">
            <p className="text-muted-foreground text-sm">
              ZIP, PDFs, CSVs, Excel — organiza el ZIP con una carpeta por empresa
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".zip,.pdf,.csv,.xlsx"
              className="hidden"
              id="file-input"
              title="Seleccionar archivos de onboarding"
              aria-label="Seleccionar archivos de onboarding"
            />
            <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
              Seleccionar archivos
            </Button>
          </div>

          {/* Acordeón documentos requeridos */}
          <button
            type="button"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setAcordeonAbierto(!acordeonAbierto)}
          >
            {acordeonAbierto ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            ¿Qué documentos necesito?
          </button>

          {acordeonAbierto && (
            <div className="border rounded-md p-4 space-y-3 text-sm bg-muted/30">
              <div>
                <p className="font-medium text-destructive mb-1">Obligatorio por empresa</p>
                {DOCS_REQUERIDOS.obligatorio.map((d) => (
                  <div key={d.codigo} className="text-muted-foreground">
                    <span className="font-mono text-xs bg-destructive/10 text-destructive px-1 rounded mr-2">
                      {d.codigo}
                    </span>
                    {d.desc}
                  </div>
                ))}
              </div>
              <div>
                <p className="font-medium mb-1">Recomendados (mejoran el perfil fiscal)</p>
                {DOCS_REQUERIDOS.recomendados.map((d) => (
                  <div key={d.codigo} className="text-muted-foreground">
                    <span className="font-mono text-xs bg-muted px-1 rounded mr-2">{d.codigo}</span>
                    {d.desc}
                  </div>
                ))}
              </div>
              <div>
                <p className="font-medium text-muted-foreground mb-1">Opcionales</p>
                {DOCS_REQUERIDOS.opcionales.map((d) => (
                  <div key={d.codigo} className="text-muted-foreground/70">
                    <span className="font-mono text-xs bg-muted/50 px-1 rounded mr-2">{d.codigo}</span>
                    {d.desc}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Botones acción */}
          <div className="flex items-center gap-3">
            <Button onClick={handleSubir} disabled={isPending || !nombre.trim()}>
              {isPending ? 'Subiendo...' : 'Subir y procesar →'}
            </Button>
            <Button variant="outline" onClick={() => navigate('/onboarding/wizard')}>
              Modo guiado →
            </Button>
          </div>
        </div>
      )}

      {lote && <LoteProgressCard lote={lote} />}

      {lote && (lote.en_revision > 0 || lote.bloqueados > 0) && loteActual && (
        <PerfilRevisionCard loteId={loteActual} />
      )}
    </div>
  )
}
