import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Activity, Settings2 } from 'lucide-react'

interface ConfigProcesamiento {
  modo: 'auto' | 'revision'
  schedule_minutos: number | null
  ocr_previo: boolean
  notif_calidad_cliente: boolean
  notif_contable_gestor: boolean
  ultimo_pipeline: string | null
}

interface Props {
  empresaId: number
}

export function ConfigProcesamientoCard({ empresaId }: Props) {
  const qc = useQueryClient()
  const qk = ['config-procesamiento', empresaId]

  const { data, isLoading } = useQuery<ConfigProcesamiento>({
    queryKey: qk,
    queryFn: () => api.get(`/api/admin/empresas/${empresaId}/config-procesamiento`),
  })

  const [form, setForm] = useState<ConfigProcesamiento | null>(null)
  const config = form ?? data

  const guardar = useMutation({
    mutationFn: (payload: Partial<ConfigProcesamiento>) =>
      api.put(`/api/admin/empresas/${empresaId}/config-procesamiento`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk })
      setForm(null)
    },
  })

  if (isLoading || !config) return null

  const cambiar = (campo: keyof ConfigProcesamiento, valor: unknown) =>
    setForm({ ...(form ?? data!), [campo]: valor })

  const haycambios = form !== null

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm font-semibold">Pipeline de documentos</CardTitle>
          </div>
          {config.ultimo_pipeline && (
            <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <Activity className="h-3 w-3" />
              {new Date(config.ultimo_pipeline).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })}
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Modo */}
        <div className="flex items-center justify-between">
          <div>
            <Label className="text-xs font-medium">Modo de procesamiento</Label>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {config.modo === 'auto' ? 'Los docs se procesan automáticamente' : 'El gestor revisa antes de procesar'}
            </p>
          </div>
          <Select
            value={config.modo}
            onValueChange={(v) => cambiar('modo', v)}
          >
            <SelectTrigger className="w-28 h-7 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">
                <Badge variant="secondary" className="text-[10px]">Auto</Badge>
              </SelectItem>
              <SelectItem value="revision">
                <Badge variant="outline" className="text-[10px]">Revisión</Badge>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Schedule */}
        <div className="flex items-center justify-between">
          <div>
            <Label className="text-xs font-medium">Intervalo pipeline (min)</Label>
            <p className="text-[11px] text-muted-foreground mt-0.5">Vacío = inmediato tras subida</p>
          </div>
          <Input
            className="w-20 h-7 text-xs text-right"
            type="number"
            min={0}
            placeholder="—"
            value={config.schedule_minutos ?? ''}
            onChange={(e) => cambiar('schedule_minutos', e.target.value ? parseInt(e.target.value) : null)}
          />
        </div>

        {/* OCR previo */}
        <div className="flex items-center justify-between">
          <Label className="text-xs font-medium">OCR antes de encolar</Label>
          <Switch
            checked={config.ocr_previo}
            onCheckedChange={(v) => cambiar('ocr_previo', v)}
            className="h-4 w-8"
          />
        </div>

        {/* Notificaciones */}
        <div className="border-t pt-3 space-y-2">
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Notificaciones</p>
          <div className="flex items-center justify-between">
            <Label className="text-xs">Calidad al cliente</Label>
            <Switch
              checked={config.notif_calidad_cliente}
              onCheckedChange={(v) => cambiar('notif_calidad_cliente', v)}
              className="h-4 w-8"
            />
          </div>
          <div className="flex items-center justify-between">
            <Label className="text-xs">Aviso contable al gestor</Label>
            <Switch
              checked={config.notif_contable_gestor}
              onCheckedChange={(v) => cambiar('notif_contable_gestor', v)}
              className="h-4 w-8"
            />
          </div>
        </div>

        {haycambios && (
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setForm(null)}>
              Cancelar
            </Button>
            <Button
              size="sm"
              className="h-7 text-xs"
              onClick={() => guardar.mutate(form!)}
              disabled={guardar.isPending}
            >
              {guardar.isPending ? 'Guardando...' : 'Guardar'}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
