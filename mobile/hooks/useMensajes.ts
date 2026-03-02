// mobile/hooks/useMensajes.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

export interface Mensaje {
  id: number
  autor_id: number
  contenido: string
  contexto_tipo: string | null
  contexto_desc: string | null
  fecha: string
  leido: boolean
}

interface EnviarBody {
  contenido: string
  contexto_tipo?: string
  contexto_desc?: string
  contexto_id?: number
}

export function useMensajes(empresaId: number | undefined, rol: 'cliente' | 'gestor') {
  const ruta = rol === 'cliente'
    ? `/api/portal/${empresaId}/mensajes`
    : `/api/gestor/empresas/${empresaId}/mensajes`

  const qc = useQueryClient()

  const query = useQuery({
    queryKey: ['mensajes', empresaId, rol],
    queryFn: () => apiFetch<{ mensajes: Mensaje[] }>(ruta),
    enabled: !!empresaId,
    refetchInterval: 30_000,
  })

  const enviar = useMutation({
    mutationFn: (body: EnviarBody) =>
      apiFetch(ruta, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mensajes', empresaId, rol] }),
  })

  return { ...query, enviar }
}
