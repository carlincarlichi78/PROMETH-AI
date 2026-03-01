// Pagina: Configuracion — Centro de control total SFCE
import { useParams, useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { PageTitle } from '@/components/ui/page-title'
import {
  Building2, LayoutDashboard, Bell, Plug, Users, Shield,
  Database, CreditCard, Sliders, Workflow, Palette,
} from 'lucide-react'

const SECCIONES = [
  {
    grupo: 'Gestoría',
    items: [
      { id: 'general', label: 'General', icono: Building2, descripcion: 'Nombre, CIF, dirección y datos de contacto de la gestoría.' },
      { id: 'marca', label: 'Marca e identidad', icono: Palette, descripcion: 'Logo, colores corporativos y personalización del portal cliente.' },
      { id: 'notificaciones', label: 'Notificaciones', icono: Bell, descripcion: 'Canales de alerta, frecuencias y destinatarios por tipo de evento.' },
    ],
  },
  {
    grupo: 'Dashboard',
    items: [
      { id: 'tarjetas', label: 'Tarjetas de cliente', icono: LayoutDashboard, descripcion: 'Configura qué bloques se muestran en las tarjetas del panel principal.' },
      { id: 'vistas', label: 'Vistas y densidad', icono: Sliders, descripcion: 'Densidad de información, ordenación por defecto y columnas visibles.' },
    ],
  },
  {
    grupo: 'Automatización',
    items: [
      { id: 'alertas', label: 'Umbrales de alertas', icono: Bell, descripcion: 'Define los umbrales que activan alertas urgentes por empresa.' },
      { id: 'workflows', label: 'Workflows automáticos', icono: Workflow, descripcion: 'Reglas de clasificación, aprobación y notificación automáticas.' },
      { id: 'campos-custom', label: 'Campos personalizados', icono: Sliders, descripcion: 'Añade campos adicionales a empresas, facturas y documentos.' },
    ],
  },
  {
    grupo: 'Integraciones',
    items: [
      { id: 'api-keys', label: 'API Keys', icono: Plug, descripcion: 'Gestiona claves de acceso para FacturaScripts, OCR y servicios externos.' },
      { id: 'correo', label: 'Correo SMTP', icono: Plug, descripcion: 'Configura el servidor de correo para envío de notificaciones y reportes.' },
      { id: 'webhooks', label: 'Webhooks', icono: Plug, descripcion: 'Endpoints externos que reciben eventos del sistema en tiempo real.' },
    ],
  },
  {
    grupo: 'Usuarios',
    items: [
      { id: 'usuarios', label: 'Usuarios y roles', icono: Users, descripcion: 'Alta de usuarios, asignación de roles y permisos por empresa.' },
      { id: 'seguridad', label: 'Seguridad y 2FA', icono: Shield, descripcion: 'Autenticación de dos factores, política de contraseñas y lockout.' },
      { id: 'sesiones', label: 'Sesiones activas', icono: Shield, descripcion: 'Visualiza y cierra sesiones activas de todos los usuarios.' },
    ],
  },
  {
    grupo: 'Sistema',
    items: [
      { id: 'backup', label: 'Backup y restauración', icono: Database, descripcion: 'Programación de copias de seguridad y restauración de datos.' },
      { id: 'licencia', label: 'Licencia', icono: CreditCard, descripcion: 'Estado de la licencia, plan activo y límites de uso.' },
      { id: 'auditoria', label: 'Log de auditoría', icono: Shield, descripcion: 'Registro inmutable de todas las acciones realizadas en el sistema.' },
    ],
  },
]

const todas = SECCIONES.flatMap((g) => g.items)

export function ConfiguracionPage() {
  const { seccion = 'tarjetas' } = useParams()
  const navigate = useNavigate()

  const seccionActual = todas.find((i) => i.id === seccion)

  return (
    <div className="flex h-full min-h-0">
      {/* Sidebar navegacion interna */}
      <nav className="w-56 flex-shrink-0 border-r border-border/50 py-4 overflow-y-auto">
        {SECCIONES.map((grupo) => (
          <div key={grupo.grupo} className="mb-3">
            <p className="px-4 mb-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
              {grupo.grupo}
            </p>
            {grupo.items.map((item) => {
              const activo = seccion === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => navigate(`/configuracion/${item.id}`)}
                  className={cn(
                    'w-full flex items-center gap-2.5 px-4 py-2 text-[13px] text-left transition-colors',
                    activo
                      ? 'text-foreground font-medium bg-[var(--surface-1)] border-r-2 border-[var(--primary)]'
                      : 'text-muted-foreground hover:text-foreground hover:bg-[var(--surface-1)]/50',
                  )}
                >
                  <item.icono className="h-3.5 w-3.5 flex-shrink-0" />
                  {item.label}
                </button>
              )
            })}
          </div>
        ))}
      </nav>

      {/* Contenido de la seccion activa */}
      <main className="flex-1 p-6 overflow-y-auto">
        {seccionActual && (
          <PageTitle
            titulo={seccionActual.label}
            subtitulo={seccionActual.descripcion}
          />
        )}

        {/* Contenido específico de cada sección */}
        {seccion === 'tarjetas' && <SeccionTarjetas />}
        {seccion !== 'tarjetas' && (
          <div className="rounded-xl border border-border/50 bg-[var(--surface-1)] p-8 text-center">
            <p className="text-[14px] text-muted-foreground">
              Esta sección estará disponible en la próxima versión.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}

// Seccion: configuracion de tarjetas del panel principal
const BLOQUES_TARJETA = [
  { id: 'health_ring', label: 'Anillo de salud (scoring)', defecto: true },
  { id: 'bandeja', label: 'Bloque Bandeja', defecto: true },
  { id: 'fiscal', label: 'Bloque Fiscal', defecto: true },
  { id: 'ventas', label: 'Bloque Ventas', defecto: true },
  { id: 'contabilidad', label: 'Bloque Contabilidad', defecto: true },
  { id: 'sparkline', label: 'Sparkline ventas 6M', defecto: true },
  { id: 'alertas_ia', label: 'Alertas IA', defecto: true },
  { id: 'quick_actions', label: 'Acciones rápidas (footer)', defecto: true },
]

function SeccionTarjetas() {
  const clave = 'sfce-tarjeta-bloques'
  const guardado = (() => {
    try { return JSON.parse(localStorage.getItem(clave) ?? 'null') } catch { return null }
  })()
  const inicial: Record<string, boolean> = guardado ?? Object.fromEntries(BLOQUES_TARJETA.map((b) => [b.id, b.defecto]))

  const [activos, setActivos] = React.useState<Record<string, boolean>>(inicial)

  const toggle = (id: string) => {
    setActivos((prev) => {
      const nuevo = { ...prev, [id]: !prev[id] }
      localStorage.setItem(clave, JSON.stringify(nuevo))
      return nuevo
    })
  }

  return (
    <div className="space-y-3 max-w-lg">
      {BLOQUES_TARJETA.map((bloque) => (
        <div
          key={bloque.id}
          className="flex items-center justify-between rounded-lg border border-border/50 bg-[var(--surface-1)] px-4 py-3"
        >
          <span className="text-[13px] font-medium">{bloque.label}</span>
          <button
            type="button"
            onClick={() => toggle(bloque.id)}
            className={cn(
              'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent',
              'transition-colors duration-200 ease-in-out focus:outline-none',
              activos[bloque.id] ? 'bg-[var(--primary)]' : 'bg-[var(--surface-3)]',
            )}
            role="switch"
            title={activos[bloque.id] ? 'Desactivar' : 'Activar'}
            aria-checked={activos[bloque.id] ? 'true' : 'false'}
          >
            <span
              className={cn(
                'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200 ease-in-out',
                activos[bloque.id] ? 'translate-x-4' : 'translate-x-0',
              )}
            />
          </button>
        </div>
      ))}
      <p className="text-[12px] text-muted-foreground pt-2">
        Los cambios se aplican inmediatamente y se guardan en este navegador.
      </p>
    </div>
  )
}

// React necesita importarse para useState
import * as React from 'react'
