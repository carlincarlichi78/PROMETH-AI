import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { AppShell } from '@/components/layout/app-shell'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AdvisorGate } from '@/features/advisor/advisor-gate'
import { Skeleton } from '@/components/ui/skeleton'

// --- Auth ---
const Login = lazy(() => import('@/features/auth/login-page'))
const AceptarInvitacion = lazy(() => import('@/features/auth/aceptar-invitacion-page'))
const NotFound = lazy(() => import('@/features/not-found'))
const OfflinePage = lazy(() => import('@/features/offline/offline-page'))

// --- Home ---
const Home = lazy(() => import('@/features/home/home-page'))

// --- Contabilidad ---
const PyG = lazy(() => import('@/features/contabilidad/pyg-page'))
const Balance = lazy(() => import('@/features/contabilidad/balance-page'))
const Diario = lazy(() => import('@/features/contabilidad/diario-page'))
const PlanCuentas = lazy(() => import('@/features/contabilidad/plan-cuentas-page'))
const Conciliacion = lazy(() => import('@/features/contabilidad/conciliacion-page'))
const Amortizaciones = lazy(() => import('@/features/contabilidad/amortizaciones-page'))
const CierreEjercicio = lazy(() => import('@/features/contabilidad/cierre-page'))
const AperturaEjercicio = lazy(() => import('@/features/contabilidad/apertura-page'))

// --- Facturacion ---
const FacturasEmitidas = lazy(() => import('@/features/facturacion/emitidas-page'))
const FacturasRecibidas = lazy(() => import('@/features/facturacion/recibidas-page'))
const CobrosPagos = lazy(() => import('@/features/facturacion/cobros-pagos-page'))
const Presupuestos = lazy(() => import('@/features/facturacion/presupuestos-page'))
const Contratos = lazy(() => import('@/features/facturacion/contratos-page'))

// --- RRHH ---
const Nominas = lazy(() => import('@/features/rrhh/nominas-page'))
const Trabajadores = lazy(() => import('@/features/rrhh/trabajadores-page'))

// --- Fiscal ---
const CalendarioFiscal = lazy(() => import('@/features/fiscal/calendario-page'))
const ModelosFiscales = lazy(() => import('@/features/fiscal/modelos-page'))
const GenerarModelo = lazy(() => import('@/features/fiscal/generar-page'))
const HistoricoModelos = lazy(() => import('@/features/fiscal/historico-page'))

// --- Documentos ---
const Inbox = lazy(() => import('@/features/documentos/inbox-page'))
const PipelinePage = lazy(() => import('@/features/documentos/pipeline-page'))
const CuarentenaPage = lazy(() => import('@/features/documentos/cuarentena-page'))
const Archivo = lazy(() => import('@/features/documentos/archivo-page'))
const RevisionPage = lazy(() => import('@/features/documentos/revision-page').then(m => ({ default: m.RevisionPage })))

// --- Economico-Financiero (Stream B) ---
const Ratios = lazy(() => import('@/features/economico/ratios-page'))
const KPIs = lazy(() => import('@/features/economico/kpis-page'))
const Tesoreria = lazy(() => import('@/features/economico/tesoreria-page'))
const CentrosCoste = lazy(() => import('@/features/economico/centros-coste-page'))
const PresupuestoReal = lazy(() => import('@/features/economico/presupuesto-real-page'))
const Comparativa = lazy(() => import('@/features/economico/comparativa-page'))
const Scoring = lazy(() => import('@/features/economico/scoring-page'))
const Informes = lazy(() => import('@/features/economico/informes-page'))

// --- Colas de revisión ---
const ColaRevision = lazy(() => import('@/features/colas/cola-revision-page'))

// --- Salud del Sistema ---
const SaludPage = lazy(() => import('@/features/salud/salud-page'))
const SesionDetallePage = lazy(() => import('@/features/salud/sesion-detalle-page'))

// --- Configuración global ---
const ConfiguracionPage = lazy(() => import('@/features/configuracion/configuracion-page').then(m => ({ default: m.ConfiguracionPage })))

// --- Correo ---
const CorreoPage = lazy(() => import('@/features/correo/index'))
const CuentasCorreoPage = lazy(() =>
  import('@/features/correo/cuentas-correo-page').then((m) => ({ default: m.CuentasCorreoPage }))
)

// --- Onboarding ---
const WizardEmpresa = lazy(() => import('@/features/onboarding/WizardEmpresa').then((m) => ({ default: m.WizardEmpresa })))
const WizardOnboardingClienteWrapper = lazy(() => import('@/features/onboarding/WizardOnboardingCliente').then((m) => ({ default: m.WizardOnboardingClienteWrapper })))
const OnboardingMasivoPage = lazy(() => import('@/features/onboarding/onboarding-masivo-page').then((m) => ({ default: m.OnboardingMasivoPage })))

// --- Advisor ---
const CommandCenter = lazy(() => import('@/features/advisor/command-center-page'))
const Restaurant360 = lazy(() => import('@/features/advisor/restaurant-360-page'))
const ProductIntelligence = lazy(() => import('@/features/advisor/product-intelligence-page'))
const SalaEstrategia = lazy(() => import('@/features/advisor/sala-estrategia-page'))
const AutopilotPage = lazy(() => import('@/features/advisor/autopilot-page'))

// --- Admin ---
const GestoriasPage = lazy(() => import('@/features/admin/gestorias-page'))

// --- Mi Gestoria ---
const MiGestoriaPage = lazy(() => import('@/features/mi-gestoria/mi-gestoria-page'))

// --- Portal, Directorio, Configuracion (Stream B) ---
const Portal = lazy(() => import('@/features/portal/portal-page'))
const PortalLayout = lazy(() => import('@/features/portal/portal-layout'))
const MisEmpresasPage = lazy(() => import('@/features/portal/mis-empresas-page'))
const Directorio = lazy(() => import('@/features/directorio/directorio-page'))
const ConfigEmpresa = lazy(() => import('@/features/configuracion/empresa-page'))
const ConfigUsuarios = lazy(() => import('@/features/configuracion/usuarios-page'))
const ConfigIntegraciones = lazy(() => import('@/features/configuracion/integraciones-page'))
const ConfigBackup = lazy(() => import('@/features/configuracion/backup-page'))
const ConfigLicencia = lazy(() => import('@/features/configuracion/licencia-page'))
const ConfigApariencia = lazy(() => import('@/features/configuracion/apariencia-page'))
const ConfigProcesamientoPage = lazy(() => import('@/features/configuracion/config-procesamiento-page'))

function SuspenseFallback() {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-96" />
      <div className="grid grid-cols-3 gap-4 mt-6">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    </div>
  )
}

export function App() {
  return (
    <Suspense fallback={<SuspenseFallback />}>
      <Routes>
        {/* Sin layout */}
        <Route path="/login" element={<Login />} />
        <Route path="/auth/aceptar-invitacion" element={<AceptarInvitacion />} />

        {/* Rutas protegidas con AppShell */}
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Home />} />
          <Route path="/directorio" element={<Directorio />} />

          {/* Contabilidad */}
          <Route path="/empresa/:id/pyg" element={<PyG />} />
          <Route path="/empresa/:id/balance" element={<Balance />} />
          <Route path="/empresa/:id/diario" element={<Diario />} />
          <Route path="/empresa/:id/plan-cuentas" element={<PlanCuentas />} />
          <Route path="/empresa/:id/conciliacion" element={<Conciliacion />} />
          <Route path="/empresa/:id/amortizaciones" element={<Amortizaciones />} />
          <Route path="/empresa/:id/cierre" element={<CierreEjercicio />} />
          <Route path="/empresa/:id/apertura" element={<AperturaEjercicio />} />

          {/* Facturacion */}
          <Route path="/empresa/:id/facturas-emitidas" element={<FacturasEmitidas />} />
          <Route path="/empresa/:id/facturas-recibidas" element={<FacturasRecibidas />} />
          <Route path="/empresa/:id/cobros-pagos" element={<CobrosPagos />} />
          <Route path="/empresa/:id/presupuestos" element={<Presupuestos />} />
          <Route path="/empresa/:id/contratos" element={<Contratos />} />

          {/* RRHH */}
          <Route path="/empresa/:id/nominas" element={<Nominas />} />
          <Route path="/empresa/:id/trabajadores" element={<Trabajadores />} />

          {/* Fiscal */}
          <Route path="/empresa/:id/calendario-fiscal" element={<CalendarioFiscal />} />
          <Route path="/empresa/:id/modelos-fiscales" element={<ModelosFiscales />} />
          <Route path="/empresa/:id/modelos-fiscales/generar" element={<GenerarModelo />} />
          <Route path="/empresa/:id/modelos-fiscales/historico" element={<HistoricoModelos />} />

          {/* Documentos */}
          <Route path="/empresa/:id/cola-revision" element={<ColaRevision />} />
          <Route path="/empresa/:id/inbox" element={<Inbox />} />
          <Route path="/empresa/:id/pipeline" element={<PipelinePage />} />
          <Route path="/empresa/:id/cuarentena" element={<CuarentenaPage />} />
          <Route path="/empresa/:id/archivo" element={<Archivo />} />
          <Route path="/revision" element={<RevisionPage />} />

          {/* Economico-Financiero */}
          <Route path="/empresa/:id/ratios" element={<Ratios />} />
          <Route path="/empresa/:id/kpis" element={<KPIs />} />
          <Route path="/empresa/:id/tesoreria" element={<Tesoreria />} />
          <Route path="/empresa/:id/centros-coste" element={<CentrosCoste />} />
          <Route path="/empresa/:id/presupuesto-real" element={<PresupuestoReal />} />
          <Route path="/empresa/:id/comparativa" element={<Comparativa />} />
          <Route path="/empresa/:id/scoring" element={<Scoring />} />
          <Route path="/empresa/:id/informes" element={<Informes />} />

          {/* Advisor */}
          <Route path="/advisor" element={<AdvisorGate><CommandCenter /></AdvisorGate>} />
          <Route path="/empresa/:id/advisor" element={<AdvisorGate><Restaurant360 /></AdvisorGate>} />
          <Route path="/empresa/:id/advisor/productos" element={<AdvisorGate><ProductIntelligence /></AdvisorGate>} />
          <Route path="/empresa/:id/advisor/estrategia" element={<AdvisorGate><SalaEstrategia /></AdvisorGate>} />
          <Route path="/advisor/autopilot" element={<AdvisorGate><AutopilotPage /></AdvisorGate>} />

          {/* Admin */}
          <Route path="/admin/gestorias" element={<GestoriasPage />} />

          {/* Mi Gestoria */}
          <Route path="/mi-gestoria" element={<MiGestoriaPage />} />

          {/* Onboarding */}
          <Route path="/onboarding/nueva-empresa" element={<WizardEmpresa />} />
          <Route path="/onboarding/cliente/:id" element={<WizardOnboardingClienteWrapper />} />
          <Route path="/onboarding/masivo" element={<OnboardingMasivoPage />} />

          {/* Correo */}
          <Route path="/empresa/:id/correo" element={<CorreoPage />} />
          <Route path="/correo/cuentas" element={<CuentasCorreoPage />} />

          {/* Salud del Sistema */}
          <Route path="/salud" element={<SaludPage />} />
          <Route path="/salud/:id" element={<SesionDetallePage />} />

          {/* Configuración global */}
          <Route path="/configuracion" element={<ConfiguracionPage />} />
          <Route path="/configuracion/:seccion" element={<ConfiguracionPage />} />

          {/* Portal Cliente */}
          <Route path="/empresa/:id/portal" element={<Portal />} />

          {/* Configuracion */}
          <Route path="/empresa/:id/config/empresa" element={<ConfigEmpresa />} />
          <Route path="/empresa/:id/config/usuarios" element={<ConfigUsuarios />} />
          <Route path="/empresa/:id/config/integraciones" element={<ConfigIntegraciones />} />
          <Route path="/empresa/:id/config/backup" element={<ConfigBackup />} />
          <Route path="/empresa/:id/config/licencia" element={<ConfigLicencia />} />
          <Route path="/empresa/:id/config/apariencia" element={<ConfigApariencia />} />
          <Route path="/empresa/:id/config/procesamiento" element={<ConfigProcesamientoPage />} />
        </Route>

        {/* Portal Cliente — layout propio, sin AppShell */}
        <Route element={<PortalLayout />}>
          <Route path="/portal" element={<MisEmpresasPage />} />
          <Route path="/portal/:id" element={<Portal />} />
        </Route>

        <Route path="/offline" element={<OfflinePage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}
