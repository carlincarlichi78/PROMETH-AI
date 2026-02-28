import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Empresa {
  id: number
  cif: string
  nombre: string
  forma_juridica: string
  territorio: string
  regimen_iva: string
  activa: boolean
}

interface EmpresaStore {
  empresaActiva: Empresa | null
  setEmpresaActiva: (empresa: Empresa | null) => void
}

export const useEmpresaStore = create<EmpresaStore>()(
  persist(
    (set) => ({
      empresaActiva: null,
      setEmpresaActiva: (empresa) => set({ empresaActiva: empresa }),
    }),
    { name: 'sfce-empresa-activa' }
  )
)
