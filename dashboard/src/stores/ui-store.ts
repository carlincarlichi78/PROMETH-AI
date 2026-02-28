import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Tema = 'light' | 'dark' | 'system'
type Densidad = 'compacta' | 'comoda'

interface UIStore {
  tema: Tema
  densidad: Densidad
  sidebarColapsado: boolean
  copilotAbierto: boolean
  setTema: (tema: Tema) => void
  setDensidad: (densidad: Densidad) => void
  toggleSidebar: () => void
  toggleCopilot: () => void
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      tema: 'system',
      densidad: 'comoda',
      sidebarColapsado: false,
      copilotAbierto: false,
      setTema: (tema) => set({ tema }),
      setDensidad: (densidad) => set({ densidad }),
      toggleSidebar: () => set((s) => ({ sidebarColapsado: !s.sidebarColapsado })),
      toggleCopilot: () => set((s) => ({ copilotAbierto: !s.copilotAbierto })),
    }),
    {
      name: 'sfce-ui',
      partialize: (s) => ({
        tema: s.tema,
        densidad: s.densidad,
        sidebarColapsado: s.sidebarColapsado,
      }),
    }
  )
)
