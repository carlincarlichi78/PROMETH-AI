import { useEffect } from 'react'
import { useUIStore } from '@/stores/ui-store'

/**
 * Aplica la clase `dark` en <html> segun el tema del UIStore.
 * Escucha cambios del sistema cuando tema === 'system'.
 * Debe usarse una sola vez, en AppShell o raiz de la app.
 */
export function useThemeEffect() {
  const tema = useUIStore((s) => s.tema)

  useEffect(() => {
    const root = document.documentElement

    const aplicarTema = (oscuro: boolean) => {
      root.classList.toggle('dark', oscuro)
    }

    if (tema === 'dark') {
      aplicarTema(true)
      return
    }

    if (tema === 'light') {
      aplicarTema(false)
      return
    }

    // tema === 'system'
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    aplicarTema(mediaQuery.matches)

    const handler = (e: MediaQueryListEvent) => aplicarTema(e.matches)
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [tema])
}
