import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { confirmarEnriquecimiento } from './api'

const CAMPO_LABELS: Record<string, string> = {
  iva_deducible_pct: '% IVA deducible (0-100)',
  categoria_gasto: 'Categoría de gasto',
  subcuenta_contable: 'Subcuenta contable',
  ejercicio_override: 'Ejercicio (ej: 2024)',
  tipo_doc_override: 'Tipo documento (FC/FV/NC/NOM)',
  regimen_especial: 'Régimen especial',
  notas: 'Notas para el contable',
}

interface Props {
  emailId: number
  camposPendientes: string[]
  empresaId: number
  onClose: () => void
}

export function ConfirmarEnriquecimientoDialog({ emailId, camposPendientes, empresaId, onClose }: Props) {
  const [valores, setValores] = useState<Record<string, string>>({})
  const qc = useQueryClient()

  const mut = useMutation({
    mutationFn: () => confirmarEnriquecimiento(emailId, valores),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['emails-gestor', empresaId] })
      onClose()
    },
  })

  const campos = camposPendientes.length > 0 ? camposPendientes : Object.keys(CAMPO_LABELS)

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Confirmar instrucciones contables</DialogTitle>
          <p className="text-sm text-muted-foreground">
            El sistema detectó estas instrucciones con baja confianza.
            Confirma o corrige los valores antes de procesar.
          </p>
        </DialogHeader>
        <div className="space-y-4 py-2">
          {campos.map(campo => (
            <div key={campo} className="space-y-1">
              <Label>{CAMPO_LABELS[campo] ?? campo}</Label>
              <Input
                placeholder={`Valor para ${CAMPO_LABELS[campo] ?? campo}`}
                value={valores[campo] ?? ''}
                onChange={e => setValores(v => ({ ...v, [campo]: e.target.value }))}
              />
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={() => mut.mutate()}
            disabled={mut.isPending || Object.keys(valores).length === 0}
          >
            {mut.isPending ? 'Guardando...' : 'Confirmar y aplicar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
