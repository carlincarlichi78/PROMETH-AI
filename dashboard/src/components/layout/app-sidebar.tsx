import { useNavigate, useLocation } from 'react-router-dom'
import {
  Home,
  BookOpen,
  Scale,
  FileText,
  Calculator,
  TrendingUp,
  BarChart3,
  Building2,
  Settings,
  Users,
  Upload,
  FolderOpen,
  AlertTriangle,
  Calendar,
  DoorClosed,
  DoorOpen,
  Wallet,
  PiggyBank,
  Target,
  GitCompare,
  CreditCard,
  FileBarChart,
  ExternalLink,
  Database,
  Palette,
  HardDrive,
  Key,
  UserCog,
  Briefcase,
  Receipt,
  Activity,
  Archive,
} from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
} from '@/components/ui/sidebar'
import { useEmpresaStore } from '@/stores/empresa-store'
import { useAuth } from '@/context/AuthContext'

interface ItemMenu {
  titulo: string
  ruta: string
  icono: React.ElementType
}

interface GrupoMenu {
  label: string
  items: ItemMenu[]
}

export function AppSidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { usuario, logout } = useAuth()
  const empresaActiva = useEmpresaStore((s) => s.empresaActiva)
  const eId = empresaActiva?.id

  const gruposGenerales: GrupoMenu[] = [
    {
      label: '',
      items: [
        { titulo: 'Panel Principal', ruta: '/', icono: Home },
        { titulo: 'Directorio', ruta: '/directorio', icono: Database },
      ],
    },
  ]

  const gruposEmpresa: GrupoMenu[] = eId
    ? [
        {
          label: 'Contabilidad',
          items: [
            { titulo: 'Cuenta de Resultados', ruta: `/empresa/${eId}/pyg`, icono: TrendingUp },
            { titulo: 'Balance de Situacion', ruta: `/empresa/${eId}/balance`, icono: Scale },
            { titulo: 'Libro Diario', ruta: `/empresa/${eId}/diario`, icono: BookOpen },
            { titulo: 'Plan de Cuentas', ruta: `/empresa/${eId}/plan-cuentas`, icono: FileText },
            {
              titulo: 'Conciliacion Bancaria',
              ruta: `/empresa/${eId}/conciliacion`,
              icono: GitCompare,
            },
            {
              titulo: 'Amortizaciones',
              ruta: `/empresa/${eId}/amortizaciones`,
              icono: Calculator,
            },
            { titulo: 'Cierre Ejercicio', ruta: `/empresa/${eId}/cierre`, icono: DoorClosed },
            { titulo: 'Apertura Ejercicio', ruta: `/empresa/${eId}/apertura`, icono: DoorOpen },
          ],
        },
        {
          label: 'Facturacion',
          items: [
            {
              titulo: 'Facturas Emitidas',
              ruta: `/empresa/${eId}/facturas-emitidas`,
              icono: FileBarChart,
            },
            {
              titulo: 'Facturas Recibidas',
              ruta: `/empresa/${eId}/facturas-recibidas`,
              icono: Receipt,
            },
            { titulo: 'Cobros y Pagos', ruta: `/empresa/${eId}/cobros-pagos`, icono: Wallet },
            { titulo: 'Presupuestos', ruta: `/empresa/${eId}/presupuestos`, icono: FileText },
            {
              titulo: 'Contratos Recurrentes',
              ruta: `/empresa/${eId}/contratos`,
              icono: Briefcase,
            },
          ],
        },
        {
          label: 'RRHH',
          items: [
            { titulo: 'Nominas', ruta: `/empresa/${eId}/nominas`, icono: PiggyBank },
            { titulo: 'Trabajadores', ruta: `/empresa/${eId}/trabajadores`, icono: Users },
          ],
        },
        {
          label: 'Fiscal',
          items: [
            {
              titulo: 'Calendario Fiscal',
              ruta: `/empresa/${eId}/calendario-fiscal`,
              icono: Calendar,
            },
            {
              titulo: 'Modelos Fiscales',
              ruta: `/empresa/${eId}/modelos-fiscales`,
              icono: FileText,
            },
            {
              titulo: 'Generar Modelo',
              ruta: `/empresa/${eId}/modelos-fiscales/generar`,
              icono: Calculator,
            },
            {
              titulo: 'Historico Modelos',
              ruta: `/empresa/${eId}/modelos-fiscales/historico`,
              icono: FolderOpen,
            },
          ],
        },
        {
          label: 'Documentos',
          items: [
            { titulo: 'Bandeja Entrada', ruta: `/empresa/${eId}/inbox`, icono: Upload },
            { titulo: 'Pipeline', ruta: `/empresa/${eId}/pipeline`, icono: Activity },
            { titulo: 'Cuarentena', ruta: `/empresa/${eId}/cuarentena`, icono: AlertTriangle },
            { titulo: 'Archivo Digital', ruta: `/empresa/${eId}/archivo`, icono: Archive },
          ],
        },
        {
          label: 'Economico-Financiero',
          items: [
            { titulo: 'Ratios Financieros', ruta: `/empresa/${eId}/ratios`, icono: TrendingUp },
            { titulo: 'KPIs Sectoriales', ruta: `/empresa/${eId}/kpis`, icono: Target },
            { titulo: 'Tesoreria', ruta: `/empresa/${eId}/tesoreria`, icono: PiggyBank },
            {
              titulo: 'Centros de Coste',
              ruta: `/empresa/${eId}/centros-coste`,
              icono: Building2,
            },
            {
              titulo: 'Presupuesto vs Real',
              ruta: `/empresa/${eId}/presupuesto-real`,
              icono: GitCompare,
            },
            {
              titulo: 'Comparativa Interanual',
              ruta: `/empresa/${eId}/comparativa`,
              icono: BarChart3,
            },
            { titulo: 'Credit Scoring', ruta: `/empresa/${eId}/scoring`, icono: CreditCard },
            { titulo: 'Informes PDF', ruta: `/empresa/${eId}/informes`, icono: FileBarChart },
          ],
        },
        {
          label: 'Portal Cliente',
          items: [
            { titulo: 'Vista Cliente', ruta: `/empresa/${eId}/portal`, icono: ExternalLink },
          ],
        },
        {
          label: 'Configuracion',
          items: [
            {
              titulo: 'Empresa',
              ruta: `/empresa/${eId}/config/empresa`,
              icono: Building2,
            },
            {
              titulo: 'Usuarios y Roles',
              ruta: `/empresa/${eId}/config/usuarios`,
              icono: UserCog,
            },
            {
              titulo: 'Integraciones',
              ruta: `/empresa/${eId}/config/integraciones`,
              icono: Settings,
            },
            {
              titulo: 'Backup / Restore',
              ruta: `/empresa/${eId}/config/backup`,
              icono: HardDrive,
            },
            { titulo: 'Licencia', ruta: `/empresa/${eId}/config/licencia`, icono: Key },
            { titulo: 'Apariencia', ruta: `/empresa/${eId}/config/apariencia`, icono: Palette },
          ],
        },
      ]
    : []

  const todosLosGrupos = [...gruposGenerales, ...gruposEmpresa]

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-sm flex-shrink-0">
            S
          </div>
          <div className="flex flex-col group-data-[collapsible=icon]:hidden overflow-hidden">
            <span className="text-sm font-semibold truncate">SFCE</span>
            <span className="text-[10px] text-muted-foreground truncate">
              Sistema Fiscal Contable
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {todosLosGrupos.map((grupo, idx) => (
          <SidebarGroup key={grupo.label || `gen-${idx}`}>
            {grupo.label && <SidebarGroupLabel>{grupo.label}</SidebarGroupLabel>}
            <SidebarGroupContent>
              <SidebarMenu>
                {grupo.items.map((item) => (
                  <SidebarMenuItem key={item.ruta}>
                    <SidebarMenuButton
                      isActive={location.pathname === item.ruta}
                      onClick={() => navigate(item.ruta)}
                      tooltip={item.titulo}
                    >
                      <item.icono className="h-4 w-4" />
                      <span>{item.titulo}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter className="border-t p-3">
        <div className="flex items-center gap-2 group-data-[collapsible=icon]:justify-center">
          <div className="h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-semibold flex-shrink-0">
            {usuario?.nombre?.charAt(0)?.toUpperCase() ?? '?'}
          </div>
          <div className="flex flex-col group-data-[collapsible=icon]:hidden overflow-hidden">
            <span className="text-sm font-medium truncate">{usuario?.nombre}</span>
            <button
              onClick={logout}
              className="text-xs text-muted-foreground hover:text-foreground text-left transition-colors"
            >
              Cerrar sesion
            </button>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
