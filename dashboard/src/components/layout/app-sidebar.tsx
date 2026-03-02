import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Home, BookOpen, Scale, FileText, Calculator, TrendingUp, BarChart3,
  Building2, Settings, Users, Upload, FolderOpen, AlertTriangle, Calendar,
  DoorClosed, DoorOpen, Wallet, PiggyBank, Target, GitCompare, CreditCard,
  FileBarChart, ExternalLink, Database, Palette, HardDrive, Key, UserCog,
  Briefcase, Receipt, Activity, Archive, HeartPulse, ChevronRight, ChevronsUpDown,
  Shield, ClipboardCheck, Zap, Mail,
} from 'lucide-react'
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent, SidebarGroupLabel,
  SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarFooter,
} from '@/components/ui/sidebar'
import { useEmpresaStore } from '@/stores/empresa-store'
import { useAuth } from '@/context/AuthContext'
import { useTiene } from '@/hooks/useTiene'
import { cn } from '@/lib/utils'

interface ItemMenu { titulo: string; ruta: string; icono: React.ElementType }
interface GrupoMenu { label: string; items: ItemMenu[] }


export function AppSidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { usuario, logout } = useAuth()
  const empresaActiva = useEmpresaStore((s) => s.empresaActiva)
  const eId = empresaActiva?.id
  const tieneAdvisor = useTiene('advisor_premium')

  // Estado de grupos colapsados — persistido en localStorage
  const [gruposAbiertos, setGruposAbiertos] = React.useState<Record<string, boolean>>(() => {
    try {
      const guardado = localStorage.getItem('sfce-sidebar-grupos')
      return guardado ? JSON.parse(guardado) as Record<string, boolean> : {}
    } catch { return {} }
  })

  const toggleGrupo = (label: string) => {
    setGruposAbiertos(prev => {
      const nuevo = { ...prev, [label]: !prev[label] }
      localStorage.setItem('sfce-sidebar-grupos', JSON.stringify(nuevo))
      return nuevo
    })
  }

  const gruposEmpresa: GrupoMenu[] = eId ? [
    {
      label: 'Contabilidad',
      items: [
        { titulo: 'Cuenta de Resultados', ruta: `/empresa/${eId}/pyg`, icono: TrendingUp },
        { titulo: 'Balance de Situacion', ruta: `/empresa/${eId}/balance`, icono: Scale },
        { titulo: 'Libro Diario', ruta: `/empresa/${eId}/diario`, icono: BookOpen },
        { titulo: 'Plan de Cuentas', ruta: `/empresa/${eId}/plan-cuentas`, icono: FileText },
        { titulo: 'Conciliacion Bancaria', ruta: `/empresa/${eId}/conciliacion`, icono: GitCompare },
        { titulo: 'Amortizaciones', ruta: `/empresa/${eId}/amortizaciones`, icono: Calculator },
        { titulo: 'Cierre Ejercicio', ruta: `/empresa/${eId}/cierre`, icono: DoorClosed },
        { titulo: 'Apertura Ejercicio', ruta: `/empresa/${eId}/apertura`, icono: DoorOpen },
      ],
    },
    {
      label: 'Facturacion',
      items: [
        { titulo: 'Facturas Emitidas', ruta: `/empresa/${eId}/facturas-emitidas`, icono: FileBarChart },
        { titulo: 'Facturas Recibidas', ruta: `/empresa/${eId}/facturas-recibidas`, icono: Receipt },
        { titulo: 'Cobros y Pagos', ruta: `/empresa/${eId}/cobros-pagos`, icono: Wallet },
        { titulo: 'Presupuestos', ruta: `/empresa/${eId}/presupuestos`, icono: FileText },
        { titulo: 'Contratos Recurrentes', ruta: `/empresa/${eId}/contratos`, icono: Briefcase },
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
        { titulo: 'Calendario Fiscal', ruta: `/empresa/${eId}/calendario-fiscal`, icono: Calendar },
        { titulo: 'Modelos Fiscales', ruta: `/empresa/${eId}/modelos-fiscales`, icono: FileText },
        { titulo: 'Generar Modelo', ruta: `/empresa/${eId}/modelos-fiscales/generar`, icono: Calculator },
        { titulo: 'Historico Modelos', ruta: `/empresa/${eId}/modelos-fiscales/historico`, icono: FolderOpen },
        { titulo: 'Modelo 190', ruta: `/empresa/${eId}/modelo-190`, icono: FileText },
      ],
    },
    {
      label: 'Documentos',
      items: [
        { titulo: 'Bandeja Entrada', ruta: `/empresa/${eId}/inbox`, icono: Upload },
        { titulo: 'Pipeline', ruta: `/empresa/${eId}/pipeline`, icono: Activity },
        { titulo: 'Revisión Docs', ruta: `/revision`, icono: ClipboardCheck },
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
        { titulo: 'Centros de Coste', ruta: `/empresa/${eId}/centros-coste`, icono: Building2 },
        { titulo: 'Presupuesto vs Real', ruta: `/empresa/${eId}/presupuesto-real`, icono: GitCompare },
        { titulo: 'Comparativa Interanual', ruta: `/empresa/${eId}/comparativa`, icono: BarChart3 },
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
      label: 'Configuracion Empresa',
      items: [
        { titulo: 'Empresa', ruta: `/empresa/${eId}/config/empresa`, icono: Building2 },
        { titulo: 'Usuarios y Roles', ruta: `/empresa/${eId}/config/usuarios`, icono: UserCog },
        { titulo: 'Integraciones', ruta: `/empresa/${eId}/config/integraciones`, icono: Settings },
        { titulo: 'Backup / Restore', ruta: `/empresa/${eId}/config/backup`, icono: HardDrive },
        { titulo: 'Licencia', ruta: `/empresa/${eId}/config/licencia`, icono: Key },
        { titulo: 'Apariencia', ruta: `/empresa/${eId}/config/apariencia`, icono: Palette },
        { titulo: 'Pipeline Docs', ruta: `/empresa/${eId}/config/procesamiento`, icono: Activity },
      ],
    },
  ] : []

  // Detectar qué grupo está activo según la ruta actual
  const grupoActivo = React.useMemo(() => {
    const ruta = location.pathname
    for (const grupo of gruposEmpresa) {
      if (grupo.items.some(item => ruta === item.ruta || ruta.startsWith(item.ruta + '/'))) {
        return grupo.label
      }
    }
    return null
  }, [location.pathname, eId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Abrir automáticamente el grupo activo si aún no está abierto
  React.useEffect(() => {
    if (grupoActivo) {
      setGruposAbiertos(prev => {
        if (prev[grupoActivo]) return prev
        const nuevo = { ...prev, [grupoActivo]: true }
        localStorage.setItem('sfce-sidebar-grupos', JSON.stringify(nuevo))
        return nuevo
      })
    }
  }, [grupoActivo])

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="logo-amber flex h-8 w-8 items-center justify-center rounded-lg font-bold text-sm flex-shrink-0 text-[oklch(0.13_0.015_50)]">
            S
          </div>
          <div className="flex flex-col group-data-[collapsible=icon]:hidden overflow-hidden">
            <span className="text-sm font-semibold truncate text-gradient">SFCE</span>
            <span className="text-[10px] text-muted-foreground truncate">Sistema Fiscal Contable</span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {/* General: Panel + Directorio */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {[
                { titulo: 'Panel Principal', ruta: '/', icono: Home },
                { titulo: 'Directorio', ruta: '/directorio', icono: Database },
              ].map((item) => (
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

        {/* Empresa pill — visible solo si hay empresa activa */}
        {empresaActiva && (
          <div className="px-3 py-1 group-data-[collapsible=icon]:hidden">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg
                         bg-[var(--surface-1)] border border-border/50
                         hover:bg-[var(--surface-2)] transition-all duration-150 text-left group"
            >
              <div
                className={`h-7 w-7 rounded-md flex items-center justify-center text-[11px] font-bold text-white flex-shrink-0 empresa-avatar-${((empresaActiva.id - 1) % 8) + 1}`}
              >
                {empresaActiva.nombre.charAt(0)}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[12px] font-semibold truncate leading-tight">
                  {empresaActiva.nombre.length > 22
                    ? empresaActiva.nombre.substring(0, 22) + '…'
                    : empresaActiva.nombre}
                </p>
                <p className="text-[11px] text-muted-foreground">{empresaActiva.cif}</p>
              </div>
              <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0 group-hover:text-foreground" />
            </button>
          </div>
        )}

        {/* Grupos de empresa — colapsables */}
        {gruposEmpresa.map((grupo) => {
          const estaAbierto = gruposAbiertos[grupo.label] ?? (grupo.label === grupoActivo)

          return (
            <SidebarGroup key={grupo.label}>
              <SidebarGroupLabel
                className="flex items-center justify-between cursor-pointer select-none hover:text-foreground transition-colors group-data-[collapsible=icon]:hidden"
                onClick={() => toggleGrupo(grupo.label)}
              >
                <span>{grupo.label}</span>
                <ChevronRight className={cn(
                  'h-3 w-3 transition-transform duration-150',
                  estaAbierto && 'rotate-90'
                )} />
              </SidebarGroupLabel>

              {estaAbierto && (
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
              )}
            </SidebarGroup>
          )
        })}

        {/* Advisor — solo tier premium */}
        {tieneAdvisor && (
          <SidebarGroup>
            <SidebarGroupLabel className="group-data-[collapsible=icon]:hidden">
              Advisor
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={location.pathname === '/advisor'}
                    onClick={() => navigate('/advisor')}
                    tooltip="Command Center"
                  >
                    <BarChart3 className="h-4 w-4" />
                    <span>Command Center</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={location.pathname === '/advisor/autopilot'}
                    onClick={() => navigate('/advisor/autopilot')}
                    tooltip="Autopilot"
                  >
                    <Zap className="h-4 w-4" />
                    <span>Autopilot</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Admin — solo superadmin */}
        {usuario?.rol === 'admin' && (
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={location.pathname.startsWith('/admin/gestorias')}
                    onClick={() => navigate('/admin/gestorias')}
                    tooltip="Gestorias"
                  >
                    <Shield className="h-4 w-4" />
                    <span>Gestorias</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Cuentas correo — solo superadmin */}
        {usuario?.rol === 'superadmin' && (
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={location.pathname === '/correo/cuentas'}
                    onClick={() => navigate('/correo/cuentas')}
                    tooltip="Cuentas correo"
                  >
                    <Mail className="h-4 w-4" />
                    <span>Cuentas correo</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Onboarding Masivo — superadmin, admin_gestoria, asesor */}
        {['superadmin', 'admin_gestoria', 'asesor'].includes(usuario?.rol ?? '') && (
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={location.pathname === '/onboarding/masivo'}
                    onClick={() => navigate('/onboarding/masivo')}
                    tooltip="Onboarding Masivo"
                  >
                    <Upload className="h-4 w-4" />
                    <span>Onboarding Masivo</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Mi Gestoria — solo admin_gestoria */}
        {usuario?.rol === 'admin_gestoria' && (
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={location.pathname === '/mi-gestoria'}
                    onClick={() => navigate('/mi-gestoria')}
                    tooltip="Mi equipo"
                  >
                    <Users className="h-4 w-4" />
                    <span>Mi equipo</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {/* Sistema — siempre visible */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={location.pathname === '/ayuda/correo'}
                  onClick={() => navigate('/ayuda/correo')}
                  tooltip="Guía de envío por email"
                >
                  <BookOpen className="h-4 w-4" />
                  <span>Guía de envío por email</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={location.pathname === '/salud'}
                  onClick={() => navigate('/salud')}
                  tooltip="Salud del Sistema"
                >
                  <HeartPulse className="h-4 w-4" />
                  <span>Salud del Sistema</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={location.pathname === '/testing'}
                  onClick={() => navigate('/testing')}
                  tooltip="SFCE Health"
                >
                  <Activity className="h-4 w-4" />
                  <span>SFCE Health</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={location.pathname.startsWith('/configuracion')}
                  onClick={() => navigate('/configuracion')}
                  tooltip="Configuración"
                  className="text-[var(--primary)] hover:text-[var(--primary)] font-medium"
                >
                  <Settings className="h-4 w-4" />
                  <span>Configuración</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
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
