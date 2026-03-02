import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { CheckCircle, AlertTriangle, X, ChevronRight } from 'lucide-react'
import { PageTitle } from '@/components/ui/page-title'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const auth = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` })

interface EmpresaWizard {
  nif: string
  nombre: string
  forma_juridica: string
  territorio: string
  advertencias: string[]
  archivos_extra: File[]
  archivo_036?: File
}

type Paso = 1 | 2 | 3 | 4

// ─── Paso 1: Subir 036s ───────────────────────────────────────────────────────
function Paso1({
  loteId,
  empresas,
  onEmpresaAnadida,
  onSiguiente,
}: {
  loteId: number
  empresas: EmpresaWizard[]
  onEmpresaAnadida: (e: EmpresaWizard, archivo: File) => void
  onSiguiente: () => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [procesando, setProcesando] = useState(false)
  const [errores, setErrores] = useState<string[]>([])

  const procesarArchivos = async (archivos: FileList) => {
    setProcesando(true)
    setErrores([])
    const nuevosErrores: string[] = []

    for (const archivo of Array.from(archivos)) {
      const fd = new FormData()
      fd.append('archivo', archivo)
      const r = await fetch(`/api/onboarding/wizard/${loteId}/subir-036`, {
        method: 'POST',
        headers: auth(),
        body: fd,
      })
      const data = await r.json()
      if (data.reconocido) {
        onEmpresaAnadida(
          {
            nif: data.nif,
            nombre: data.nombre,
            forma_juridica: data.forma_juridica,
            territorio: data.territorio ?? 'peninsula',
            advertencias: data.advertencias ?? [],
            archivos_extra: [],
          },
          archivo,
        )
      } else {
        nuevosErrores.push(`${archivo.name}: ${data.advertencia}`)
      }
    }

    setErrores(nuevosErrores)
    setProcesando(false)
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Sube un modelo 036/037 por cada empresa que quieras dar de alta. El sistema
        detectará automáticamente el CIF y nombre de cada empresa.
      </p>

      <div className="border-2 border-dashed rounded-lg p-8 text-center space-y-2">
        <p className="text-sm text-muted-foreground">Arrastra los modelos 036/037 aquí</p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          title="Seleccionar modelos 036/037"
          aria-label="Seleccionar modelos 036/037"
          onChange={(e) => e.target.files && procesarArchivos(e.target.files)}
        />
        <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}
                disabled={procesando}>
          {procesando ? 'Procesando...' : 'Seleccionar archivos'}
        </Button>
      </div>

      {errores.map((err, i) => (
        <div key={i} className="flex items-start gap-2 text-sm text-destructive bg-destructive/5 rounded p-2">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          {err}
        </div>
      ))}

      {empresas.length > 0 && (
        <div className="space-y-2">
          {empresas.map((e) => (
            <div key={e.nif} className="flex items-center gap-2 p-2 bg-muted/30 rounded text-sm">
              <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
              <span className="font-medium">{e.nombre}</span>
              <span className="text-muted-foreground">({e.nif})</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-end">
        <Button onClick={onSiguiente} disabled={empresas.length === 0}>
          Continuar <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  )
}

// ─── Paso 2: Revisar empresas ─────────────────────────────────────────────────
function Paso2({
  empresas,
  onEliminar,
  onAnterior,
  onSiguiente,
}: {
  empresas: EmpresaWizard[]
  onEliminar: (nif: string) => void
  onAnterior: () => void
  onSiguiente: () => void
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Revisa las empresas detectadas. Puedes eliminar las que no quieras procesar.
      </p>

      <div className="border rounded-lg divide-y">
        {empresas.map((e) => (
          <div key={e.nif} className="flex items-start justify-between p-3 gap-2">
            <div>
              <div className="font-medium">{e.nombre}</div>
              <div className="text-xs text-muted-foreground">
                {e.nif} · {e.forma_juridica.toUpperCase()} · {e.territorio}
              </div>
              {e.advertencias.map((adv, i) => (
                <div key={i} className="flex items-center gap-1 text-xs text-amber-600 mt-0.5">
                  <AlertTriangle className="h-3 w-3" />
                  {adv}
                </div>
              ))}
            </div>
            <Button
              size="sm"
              variant="ghost"
              className="text-destructive hover:text-destructive shrink-0"
              onClick={() => onEliminar(e.nif)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onAnterior}>← Volver</Button>
        <Button onClick={onSiguiente} disabled={empresas.length === 0}>
          Continuar <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  )
}

// ─── Paso 3: Enriquecer ───────────────────────────────────────────────────────
function Paso3({
  loteId,
  empresas,
  onDocumentosAnadidos,
  onAnterior,
  onSiguiente,
}: {
  loteId: number
  empresas: EmpresaWizard[]
  onDocumentosAnadidos: (nif: string, archivos: File[]) => void
  onAnterior: () => void
  onSiguiente: () => void
}) {
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set())
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const toggle = (nif: string) =>
    setExpandidos((prev) => {
      const next = new Set(prev)
      next.has(nif) ? next.delete(nif) : next.add(nif)
      return next
    })

  const handleArchivos = async (nif: string, archivos: FileList) => {
    const arr = Array.from(archivos)
    onDocumentosAnadidos(nif, arr)
    const fd = new FormData()
    arr.forEach((f) => fd.append('archivos', f))
    await fetch(`/api/onboarding/wizard/${loteId}/empresa/${nif}/documentos`, {
      method: 'POST',
      headers: auth(),
      body: fd,
    })
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Opcional: añade documentos adicionales para enriquecer el perfil fiscal de cada empresa
        (303, 390, libros de facturas, etc.).
      </p>

      <div className="border rounded-lg divide-y">
        {empresas.map((e) => {
          const abierto = expandidos.has(e.nif)
          return (
            <div key={e.nif} className="p-3 space-y-2">
              <button
                type="button"
                className="flex items-center justify-between w-full text-left"
                onClick={() => toggle(e.nif)}
              >
                <div>
                  <span className="font-medium text-sm">{e.nombre}</span>
                  <span className="text-xs text-muted-foreground ml-2">
                    {e.archivos_extra.length > 0
                      ? `${e.archivos_extra.length} documento(s) extra`
                      : 'Sin documentos extra'}
                  </span>
                </div>
                {abierto
                  ? <ChevronDown className="h-4 w-4" />
                  : <ChevronRight className="h-4 w-4" />}
              </button>

              {abierto && (
                <div className="pt-1">
                  <input
                    ref={(el) => { fileRefs.current[e.nif] = el }}
                    type="file"
                    accept=".pdf,.csv,.xlsx"
                    multiple
                    className="hidden"
                    title={`Documentos para ${e.nombre}`}
                    aria-label={`Documentos para ${e.nombre}`}
                    onChange={(ev) =>
                      ev.target.files && handleArchivos(e.nif, ev.target.files)
                    }
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => fileRefs.current[e.nif]?.click()}
                  >
                    + Añadir documentos
                  </Button>
                  {e.archivos_extra.map((f, i) => (
                    <div key={i} className="text-xs text-muted-foreground mt-1">
                      ✅ {f.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onAnterior}>← Volver</Button>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={onSiguiente}>Saltar</Button>
          <Button onClick={onSiguiente}>
            Continuar <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Paso 4: Confirmar ────────────────────────────────────────────────────────
function Paso4({
  loteId,
  empresas,
  onAnterior,
  onProcesado,
}: {
  loteId: number
  empresas: EmpresaWizard[]
  onAnterior: () => void
  onProcesado: (nuevoLoteId: number) => void
}) {
  const [nombreLote, setNombreLote] = useState('')

  const { mutate: procesar, isPending } = useMutation({
    mutationFn: async () => {
      const r = await fetch(`/api/onboarding/wizard/${loteId}/procesar`, {
        method: 'POST',
        headers: { ...auth(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre: nombreLote.trim() || `Wizard lote ${loteId}` }),
      })
      if (!r.ok) throw new Error(await r.text())
      return r.json()
    },
    onSuccess: (data) => onProcesado(data.lote_id),
  })

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Revisa el resumen antes de procesar. Este proceso creará las empresas en el sistema.
      </p>

      <div className="border rounded-lg p-4 space-y-2">
        <p className="font-medium text-sm">{empresas.length} empresa(s) listas</p>
        {empresas.map((e) => (
          <div key={e.nif} className="text-sm text-muted-foreground flex items-center gap-2">
            <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
            {e.nombre} — 036
            {e.archivos_extra.length > 0 && ` + ${e.archivos_extra.length} doc(s) extra`}
          </div>
        ))}
      </div>

      <div>
        <label className="text-sm font-medium block mb-1">Nombre del lote</label>
        <Input
          placeholder={`Wizard lote ${loteId}`}
          value={nombreLote}
          onChange={(e) => setNombreLote(e.target.value)}
        />
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onAnterior}>← Volver</Button>
        <Button onClick={() => procesar()} disabled={isPending}>
          {isPending ? 'Procesando...' : 'Procesar lote →'}
        </Button>
      </div>
    </div>
  )
}

// ─── ChevronDown local (no incluido en el import de lucide para evitar doble) ─
function ChevronDown({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────
export function WizardOnboardingPage() {
  const navigate = useNavigate()
  const [paso, setPaso] = useState<Paso>(1)
  const [loteId, setLoteId] = useState<number | null>(null)
  const [empresas, setEmpresas] = useState<EmpresaWizard[]>([])
  const [iniciando, setIniciando] = useState(false)

  const PASOS = ['Empresas', 'Revisar', 'Enriquecer', 'Confirmar']

  const iniciarWizard = async () => {
    if (loteId) return loteId
    setIniciando(true)
    const r = await fetch('/api/onboarding/wizard/iniciar', {
      method: 'POST',
      headers: auth(),
    })
    const data = await r.json()
    setLoteId(data.lote_id)
    setIniciando(false)
    return data.lote_id as number
  }

  const handleEmpresaAnadida = (empresa: EmpresaWizard, _archivo: File) => {
    setEmpresas((prev) => {
      const existe = prev.find((e) => e.nif === empresa.nif)
      return existe ? prev : [...prev, empresa]
    })
  }

  const handleEliminar = (nif: string) => {
    setEmpresas((prev) => prev.filter((e) => e.nif !== nif))
    if (loteId)
      fetch(`/api/onboarding/wizard/${loteId}/empresa/${nif}`, {
        method: 'DELETE',
        headers: auth(),
      })
  }

  const handleDocumentosAnadidos = (nif: string, archivos: File[]) => {
    setEmpresas((prev) =>
      prev.map((e) =>
        e.nif === nif
          ? { ...e, archivos_extra: [...e.archivos_extra, ...archivos] }
          : e,
      ),
    )
  }

  const handleSiguientePaso1 = async () => {
    if (!loteId) await iniciarWizard()
    setPaso(2)
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <PageTitle
          titulo="Onboarding Guiado"
          subtitulo="Alta paso a paso de nuevas empresas"
        />
        <Button variant="ghost" size="sm" onClick={() => navigate('/onboarding/masivo')}>
          ← Volver a modo ZIP
        </Button>
      </div>

      {/* Indicador de pasos */}
      <div className="flex items-center gap-0">
        {PASOS.map((nombre, i) => {
          const num = (i + 1) as Paso
          const activo = num === paso
          const completado = num < paso
          return (
            <div key={nombre} className="flex items-center">
              <div
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm ${
                  activo
                    ? 'bg-primary text-primary-foreground font-medium'
                    : completado
                    ? 'text-muted-foreground'
                    : 'text-muted-foreground/50'
                }`}
              >
                <span className="text-xs">{num}</span>
                {nombre}
              </div>
              {i < PASOS.length - 1 && (
                <ChevronRight className="h-4 w-4 text-muted-foreground/30 mx-0.5" />
              )}
            </div>
          )
        })}
      </div>

      {/* Contenido del paso */}
      <div className="border rounded-lg p-6">
        {paso === 1 && !loteId && iniciando && (
          <p className="text-sm text-muted-foreground">Iniciando wizard...</p>
        )}

        {paso === 1 && (
          <Paso1
            loteId={loteId ?? 0}
            empresas={empresas}
            onEmpresaAnadida={handleEmpresaAnadida}
            onSiguiente={handleSiguientePaso1}
          />
        )}

        {paso === 2 && (
          <Paso2
            empresas={empresas}
            onEliminar={handleEliminar}
            onAnterior={() => setPaso(1)}
            onSiguiente={() => setPaso(3)}
          />
        )}

        {paso === 3 && loteId && (
          <Paso3
            loteId={loteId}
            empresas={empresas}
            onDocumentosAnadidos={handleDocumentosAnadidos}
            onAnterior={() => setPaso(2)}
            onSiguiente={() => setPaso(4)}
          />
        )}

        {paso === 4 && loteId && (
          <Paso4
            loteId={loteId}
            empresas={empresas}
            onAnterior={() => setPaso(3)}
            onProcesado={(id) => navigate(`/onboarding/masivo?lote=${id}`)}
          />
        )}
      </div>
    </div>
  )
}
