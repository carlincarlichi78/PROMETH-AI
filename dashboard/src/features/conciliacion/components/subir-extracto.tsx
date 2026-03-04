import { useRef, useState } from 'react'
import { Upload, CheckCircle, AlertCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCuentas, useIngestarExtracto } from '../api'

interface Props {
  empresaId: number
}

export function SubirExtracto({ empresaId }: Props) {
  const { data: cuentas = [] } = useCuentas(empresaId)
  const ingestar = useIngestarExtracto(empresaId)
  const inputRef = useRef<HTMLInputElement>(null)
  const [ibanSeleccionado, setIbanSeleccionado] = useState('')

  const esXls = (nombre: string) => /\.(xls|xlsx)$/i.test(nombre)

  const handleArchivo = (e: React.ChangeEvent<HTMLInputElement>) => {
    const archivo = e.target.files?.[0]
    if (!archivo) return
    // XLS requiere IBAN; C43/TXT usa JIT onboarding (no requiere IBAN)
    if (esXls(archivo.name) && !ibanSeleccionado) return
    ingestar.mutate({
      archivo,
      iban: esXls(archivo.name) ? ibanSeleccionado : undefined,
    })
    e.target.value = ''
  }

  return (
    <div className="flex flex-wrap items-center gap-3 p-4 border rounded-lg bg-muted/30">
      <Select onValueChange={setIbanSeleccionado} disabled={cuentas.length === 0}>
        <SelectTrigger className="w-64">
          <SelectValue
            placeholder={
              cuentas.length === 0 ? 'Sin cuentas configuradas' : 'Seleccionar cuenta...'
            }
          />
        </SelectTrigger>
        <SelectContent>
          {cuentas.map(c => (
            <SelectItem key={c.id} value={c.iban}>
              {c.alias || c.banco_nombre} — ···{c.iban.slice(-4)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button
        variant="outline"
        disabled={ingestar.isPending}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="w-4 h-4 mr-2" />
        {ingestar.isPending ? 'Procesando...' : 'Subir extracto'}
      </Button>

      {/* Acepta C43 TXT y XLS CaixaBank — oculto, activado por el botón */}
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.c43,.xls,.xlsx"
        aria-label="Seleccionar extracto bancario"
        className="hidden"
        onChange={handleArchivo}
      />

      {ingestar.isSuccess && (
        <span className="flex items-center gap-1 text-sm text-green-600">
          <CheckCircle className="w-4 h-4" />
          {ingestar.data.cuentas_creadas
            ? `${ingestar.data.cuentas_creadas} cuenta(s) creadas · `
            : ''}
          {ingestar.data.movimientos_nuevos} nuevos
          {ingestar.data.movimientos_duplicados > 0
            ? ` / ${ingestar.data.movimientos_duplicados} duplicados`
            : ''}
          {ingestar.data.ya_procesado ? ' (ya procesado)' : ''}
        </span>
      )}

      {ingestar.isError && (
        <span className="flex items-center gap-1 text-sm text-destructive">
          <AlertCircle className="w-4 h-4" />
          {ingestar.error?.message ?? 'Error al procesar'}
        </span>
      )}
    </div>
  )
}
