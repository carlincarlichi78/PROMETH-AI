// Hook: keyboard shortcuts globales
// G+C → Contabilidad, G+F → Fiscal, G+D → Bandeja, G+E → Ratios, G+R → Facturas, G+H → Nóminas
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEmpresaStore } from '@/stores/empresa-store'

export function useKeyboardShortcuts() {
  const navigate = useNavigate()
  const { empresaActiva } = useEmpresaStore()
  const id = empresaActiva?.id

  useEffect(() => {
    let gPresionado = false
    let gTimer: ReturnType<typeof setTimeout>

    const handler = (e: KeyboardEvent) => {
      // Ignorar si el foco está en un campo de texto
      const target = e.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) return

      if (e.key === 'g' || e.key === 'G') {
        gPresionado = true
        clearTimeout(gTimer)
        gTimer = setTimeout(() => { gPresionado = false }, 1000)
        return
      }

      if (gPresionado && id) {
        gPresionado = false
        clearTimeout(gTimer)
        const mapa: Record<string, string> = {
          c: `/empresa/${id}/pyg`,
          f: `/empresa/${id}/calendario-fiscal`,
          d: `/empresa/${id}/inbox`,
          e: `/empresa/${id}/ratios`,
          r: `/empresa/${id}/facturas-emitidas`,
          h: `/empresa/${id}/nominas`,
        }
        const ruta = mapa[e.key.toLowerCase()]
        if (ruta) {
          navigate(ruta)
          return
        }
      }
    }

    document.addEventListener('keydown', handler)
    return () => {
      document.removeEventListener('keydown', handler)
      clearTimeout(gTimer)
    }
  }, [navigate, id])
}
