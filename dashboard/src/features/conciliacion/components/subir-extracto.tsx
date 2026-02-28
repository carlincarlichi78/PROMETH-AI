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

  const handleArchivo = (e: React.ChangeEvent<HTMLInputElement>) => {
    const archivo = e.target.files?.[0]
    if (!archivo || !ibanSeleccionado) return
    ingestar.mutate({ archivo, iban: ibanSeleccionado })
    // Reset input para permitir subir el mismo archivo otra vez si es necesario
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
        disabled={!ibanSeleccionado || ingestar.isPending}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="w-4 h-4 mr-2" />
        {ingestar.isPending ? 'Procesando...' : 'Subir extracto'}
      </Button>

      {/* Acepta C43 TXT y XLS CaixaBank */}
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.c43,.xls,.xlsx"
        className="hidden"
        onChange={handleArchivo}
      />

      {ingestar.isSuccess && (
        <span className="flex items-center gap-1 text-sm text-green-600">
          <CheckCircle className="w-4 h-4" />
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
