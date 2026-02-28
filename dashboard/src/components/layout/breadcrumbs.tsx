import { useLocation, Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { useEmpresaStore } from '@/stores/empresa-store'

const NOMBRES_RUTA: Record<string, string> = {
  pyg: 'Cuenta de Resultados',
  balance: 'Balance de Situacion',
  diario: 'Libro Diario',
  facturas: 'Facturas',
  'facturas-emitidas': 'Facturas Emitidas',
  'facturas-recibidas': 'Facturas Recibidas',
  'cobros-pagos': 'Cobros y Pagos',
  presupuestos: 'Presupuestos',
  contratos: 'Contratos Recurrentes',
  activos: 'Activos Fijos',
  amortizaciones: 'Amortizaciones',
  'plan-cuentas': 'Plan de Cuentas',
  conciliacion: 'Conciliacion Bancaria',
  cierre: 'Cierre Ejercicio',
  apertura: 'Apertura Ejercicio',
  inbox: 'Bandeja Entrada',
  pipeline: 'Pipeline',
  cuarentena: 'Cuarentena',
  archivo: 'Archivo Digital',
  'modelos-fiscales': 'Modelos Fiscales',
  'calendario-fiscal': 'Calendario Fiscal',
  generar: 'Generar Modelo',
  historico: 'Historico',
  nominas: 'Nominas',
  trabajadores: 'Trabajadores',
  ratios: 'Ratios Financieros',
  kpis: 'KPIs Sectoriales',
  tesoreria: 'Tesoreria',
  'centros-coste': 'Centros de Coste',
  'presupuesto-real': 'Presupuesto vs Real',
  comparativa: 'Comparativa Interanual',
  scoring: 'Credit Scoring',
  informes: 'Informes PDF',
  portal: 'Portal Cliente',
  directorio: 'Directorio',
  config: 'Configuracion',
  empresa: 'Empresa',
  usuarios: 'Usuarios y Roles',
  integraciones: 'Integraciones',
  backup: 'Backup / Restore',
  licencia: 'Licencia',
  apariencia: 'Apariencia',
}

export function Breadcrumbs() {
  const location = useLocation()
  const empresaActiva = useEmpresaStore((s) => s.empresaActiva)
  const segmentos = location.pathname.split('/').filter(Boolean)

  if (segmentos.length === 0) return null

  const migas: { label: string; ruta: string }[] = []

  for (let i = 0; i < segmentos.length; i++) {
    const seg = segmentos[i]
    if (!seg) continue
    const rutaAcumulada = '/' + segmentos.slice(0, i + 1).join('/')

    // Omitir IDs numericos
    if (/^\d+$/.test(seg)) continue

    if (seg === 'empresa' && empresaActiva) {
      migas.push({ label: empresaActiva.nombre, ruta: `/empresa/${empresaActiva.id}` })
      continue
    }

    const nombre = NOMBRES_RUTA[seg] ?? seg
    migas.push({ label: nombre, ruta: rutaAcumulada })
  }

  return (
    <nav className="flex items-center gap-1 text-sm text-muted-foreground overflow-hidden">
      {migas.map((miga, idx) => (
        <span key={miga.ruta} className="flex items-center gap-1 min-w-0">
          {idx > 0 && <ChevronRight className="h-3 w-3 flex-shrink-0" />}
          {idx < migas.length - 1 ? (
            <Link
              to={miga.ruta}
              className="hover:text-foreground transition-colors truncate"
            >
              {miga.label}
            </Link>
          ) : (
            <span className="text-foreground font-medium truncate">{miga.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
