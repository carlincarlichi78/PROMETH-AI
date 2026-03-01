// src/features/omnisearch/omnisearch.tsx
import * as React from 'react'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from 'cmdk'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { useNavigate } from 'react-router-dom'
import { useEmpresaStore } from '@/stores/empresa-store'
import { LayoutDashboard, FileText, Calendar, Zap, Settings } from 'lucide-react'

interface OmniSearchProps {
  abierto: boolean
  onCerrar: () => void
}

const PAGINAS = [
  { titulo: 'Panel Principal', ruta: '/', icono: LayoutDashboard },
  { titulo: 'Directorio', ruta: '/directorio', icono: FileText },
  { titulo: 'Configuración', ruta: '/configuracion', icono: Settings },
]

const PAGINAS_EMPRESA = [
  { titulo: 'Cuenta de Resultados', ruta: 'pyg', icono: FileText },
  { titulo: 'Balance de Situación', ruta: 'balance', icono: FileText },
  { titulo: 'Libro Diario', ruta: 'diario', icono: FileText },
  { titulo: 'Facturas Emitidas', ruta: 'facturas-emitidas', icono: FileText },
  { titulo: 'Facturas Recibidas', ruta: 'facturas-recibidas', icono: FileText },
  { titulo: 'Calendario Fiscal', ruta: 'calendario-fiscal', icono: Calendar },
  { titulo: 'Modelos Fiscales', ruta: 'modelos-fiscales', icono: FileText },
  { titulo: 'Bandeja de Entrada', ruta: 'inbox', icono: FileText },
  { titulo: 'Ratios Financieros', ruta: 'ratios', icono: FileText },
  { titulo: 'KPIs Sectoriales', ruta: 'kpis', icono: FileText },
  { titulo: 'Tesorería', ruta: 'tesoreria', icono: FileText },
]

export function OmniSearch({ abierto, onCerrar }: OmniSearchProps) {
  const navigate = useNavigate()
  const { empresaActiva } = useEmpresaStore()
  const [query, setQuery] = React.useState('')

  const irA = (ruta: string) => {
    navigate(ruta)
    onCerrar()
    setQuery('')
  }

  return (
    <Dialog open={abierto} onOpenChange={onCerrar}>
      <DialogContent className="p-0 max-w-[560px] overflow-hidden bg-[var(--surface-2)] border-border/60">
        <Command className="bg-transparent" shouldFilter={true}>
          <CommandInput
            placeholder="Buscar o ejecutar un comando..."
            value={query}
            onValueChange={setQuery}
            className="text-[15px] border-0 bg-transparent focus:ring-0 px-4 py-3.5"
            autoFocus
          />
          <CommandList className="max-h-[380px] overflow-y-auto px-2 pb-2">
            <CommandEmpty className="py-8 text-center text-[14px] text-muted-foreground">
              Sin resultados para &ldquo;{query}&rdquo;
            </CommandEmpty>

            <CommandGroup heading="Acciones rápidas">
              <CommandItem onSelect={() => irA('/')} className="gap-2.5 rounded-lg cursor-pointer">
                <Zap className="h-4 w-4 text-[var(--state-warning)]" />
                <span>Panel Principal</span>
              </CommandItem>
              {empresaActiva && (
                <CommandItem
                  onSelect={() => irA(`/empresa/${empresaActiva.id}/inbox`)}
                  className="gap-2.5 rounded-lg cursor-pointer"
                >
                  <Zap className="h-4 w-4 text-[var(--state-warning)]" />
                  <span>Ir a Bandeja — {empresaActiva.nombre}</span>
                </CommandItem>
              )}
              <CommandItem onSelect={() => irA('/onboarding/nueva-empresa')} className="gap-2.5 rounded-lg cursor-pointer">
                <Zap className="h-4 w-4 text-[var(--state-warning)]" />
                <span>Nueva empresa</span>
              </CommandItem>
            </CommandGroup>

            <CommandSeparator className="my-1" />

            {empresaActiva && (
              <CommandGroup heading={`Páginas — ${empresaActiva.nombre}`}>
                {PAGINAS_EMPRESA.map(p => (
                  <CommandItem
                    key={p.ruta}
                    onSelect={() => irA(`/empresa/${empresaActiva.id}/${p.ruta}`)}
                    className="gap-2.5 rounded-lg cursor-pointer"
                  >
                    <p.icono className="h-4 w-4 text-muted-foreground" />
                    <span>{p.titulo}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}

            <CommandSeparator className="my-1" />

            <CommandGroup heading="Navegación global">
              {PAGINAS.map(p => (
                <CommandItem
                  key={p.ruta}
                  onSelect={() => irA(p.ruta)}
                  className="gap-2.5 rounded-lg cursor-pointer"
                >
                  <p.icono className="h-4 w-4 text-muted-foreground" />
                  <span>{p.titulo}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  )
}
