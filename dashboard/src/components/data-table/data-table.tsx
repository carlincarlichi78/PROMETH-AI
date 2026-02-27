import { useState, useMemo } from 'react'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

export interface ColumnaTabla<T> {
  key: string
  header: string
  render: (item: T) => React.ReactNode
  sortable?: boolean
  sortFn?: (a: T, b: T) => number
  className?: string
}

interface DataTableProps<T> {
  datos: T[]
  columnas: ColumnaTabla<T>[]
  cargando?: boolean
  busqueda?: boolean
  filtroBusqueda?: (item: T, termino: string) => boolean
  filasPorPagina?: number
  vacio?: React.ReactNode
  onClickFila?: (item: T) => void
  acciones?: React.ReactNode
}

export function DataTable<T extends { id?: number | string }>({
  datos,
  columnas,
  cargando,
  busqueda = false,
  filtroBusqueda,
  filasPorPagina = 20,
  vacio,
  onClickFila,
  acciones,
}: DataTableProps<T>) {
  const [terminoBusqueda, setTerminoBusqueda] = useState('')
  const [ordenColumna, setOrdenColumna] = useState<string | null>(null)
  const [ordenDir, setOrdenDir] = useState<'asc' | 'desc'>('asc')
  const [pagina, setPagina] = useState(0)

  const datosFiltrados = useMemo(() => {
    let resultado = datos
    if (terminoBusqueda && filtroBusqueda) {
      resultado = resultado.filter((item) => filtroBusqueda(item, terminoBusqueda))
    }
    if (ordenColumna) {
      const col = columnas.find((c) => c.key === ordenColumna)
      if (col?.sortFn) {
        resultado = [...resultado].sort((a, b) => {
          const r = col.sortFn!(a, b)
          return ordenDir === 'desc' ? -r : r
        })
      }
    }
    return resultado
  }, [datos, terminoBusqueda, filtroBusqueda, ordenColumna, ordenDir, columnas])

  const totalPaginas = Math.ceil(datosFiltrados.length / filasPorPagina)
  const datosPagina = datosFiltrados.slice(
    pagina * filasPorPagina,
    (pagina + 1) * filasPorPagina
  )

  function toggleOrden(key: string) {
    if (ordenColumna === key) {
      setOrdenDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setOrdenColumna(key)
      setOrdenDir('asc')
    }
    setPagina(0)
  }

  if (cargando) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-9 w-64" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {(busqueda || acciones) && (
        <div className="flex items-center justify-between gap-4">
          {busqueda && (
            <Input
              placeholder="Buscar..."
              value={terminoBusqueda}
              onChange={(e) => {
                setTerminoBusqueda(e.target.value)
                setPagina(0)
              }}
              className="max-w-xs h-8 text-sm"
            />
          )}
          {acciones && <div className="flex gap-2 ml-auto">{acciones}</div>}
        </div>
      )}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columnas.map((col) => (
                <TableHead key={col.key} className={col.className}>
                  {col.sortable ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="-ml-3 h-8 font-medium"
                      onClick={() => toggleOrden(col.key)}
                    >
                      {col.header}
                      {ordenColumna === col.key ? (
                        ordenDir === 'asc' ? (
                          <ArrowUp className="ml-1.5 h-3 w-3" />
                        ) : (
                          <ArrowDown className="ml-1.5 h-3 w-3" />
                        )
                      ) : (
                        <ArrowUpDown className="ml-1.5 h-3 w-3 opacity-40" />
                      )}
                    </Button>
                  ) : (
                    col.header
                  )}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {datosPagina.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columnas.length}
                  className="h-24 text-center text-muted-foreground text-sm"
                >
                  {vacio ?? 'Sin resultados'}
                </TableCell>
              </TableRow>
            ) : (
              datosPagina.map((item, idx) => (
                <TableRow
                  key={item.id ?? idx}
                  className={onClickFila ? 'cursor-pointer hover:bg-muted/50' : ''}
                  onClick={() => onClickFila?.(item)}
                >
                  {columnas.map((col) => (
                    <TableCell key={col.key} className={col.className}>
                      {col.render(item)}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {totalPaginas > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {datosFiltrados.length} registro{datosFiltrados.length !== 1 ? 's' : ''}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={pagina === 0}
              onClick={() => setPagina(pagina - 1)}
            >
              Anterior
            </Button>
            <span className="px-3 text-muted-foreground">
              {pagina + 1} / {totalPaginas}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={pagina >= totalPaginas - 1}
              onClick={() => setPagina(pagina + 1)}
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
