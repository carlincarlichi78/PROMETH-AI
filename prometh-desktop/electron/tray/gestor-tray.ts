import { Tray, Menu, Notification, nativeImage, app, type BrowserWindow } from 'electron'
import { join } from 'path'
import log from 'electron-log'
import { obtenerEstadoTray, marcarTodasLeidas } from './persistencia-tray'
import type { NotificacionDesktop } from './tipos-tray'

/**
 * Gestiona el icono del system tray con badge numerico y notificaciones nativas.
 */
export class GestorTray {
  private ventana: BrowserWindow
  private tray: Tray | null = null

  constructor(ventana: BrowserWindow) {
    this.ventana = ventana
  }

  /** Crea el tray icon e inicia el menu contextual */
  iniciar(): void {
    try {
      // Icono: usar icono de la app
      const iconoRuta = join(__dirname, '../../resources/icon.png')
      const icono = nativeImage.createFromPath(iconoRuta)
      // Fallback si no existe el icono
      const iconoFinal = icono.isEmpty()
        ? nativeImage.createEmpty()
        : icono.resize({ width: 16, height: 16 })

      this.tray = new Tray(iconoFinal)
      this.tray.setToolTip('CertiGestor Desktop')

      // Click en tray → mostrar ventana
      this.tray.on('click', () => {
        this.ventana.show()
        this.ventana.focus()
      })

      this.actualizarMenu()
      log.info('[Tray] Icono de tray inicializado')
    } catch (error) {
      log.error('[Tray] Error inicializando tray:', error)
    }
  }

  /** Destruye el tray (al cerrar la app) */
  destruir(): void {
    if (this.tray) {
      this.tray.destroy()
      this.tray = null
    }
  }

  /** Actualiza el menu contextual con el conteo actual */
  actualizarMenu(): void {
    if (!this.tray) return

    const estado = obtenerEstadoTray()

    const menu = Menu.buildFromTemplate([
      {
        label: 'Abrir CertiGestor',
        click: () => {
          this.ventana.show()
          this.ventana.focus()
        },
      },
      { type: 'separator' },
      {
        label: estado.pendientes > 0
          ? `${estado.pendientes} notificacion(es) pendiente(s)`
          : 'Sin notificaciones pendientes',
        enabled: false,
      },
      {
        label: 'Marcar todas como leidas',
        enabled: estado.pendientes > 0,
        click: () => {
          marcarTodasLeidas()
          this.actualizarBadge(0)
        },
      },
      { type: 'separator' },
      {
        label: 'Salir',
        click: () => {
          app.quit()
        },
      },
    ])

    this.tray.setContextMenu(menu)
  }

  /** Actualiza el badge numerico (overlay icon en Windows taskbar) */
  actualizarBadge(conteo: number): void {
    if (!this.tray) return

    // Tooltip con conteo
    this.tray.setToolTip(
      conteo > 0 ? `CertiGestor — ${conteo} pendiente(s)` : 'CertiGestor Desktop'
    )

    // Overlay en la ventana de Windows (badge en taskbar)
    if (conteo > 0) {
      this.ventana.setOverlayIcon(
        this.crearBadgeIcon(conteo),
        `${conteo} notificaciones`
      )
    } else {
      this.ventana.setOverlayIcon(null, '')
    }

    this.actualizarMenu()
  }

  /** Envia una notificacion nativa de Windows */
  enviarNativa(notif: NotificacionDesktop): void {
    if (!Notification.isSupported()) return

    try {
      const notifNativa = new Notification({
        title: notif.titulo,
        body: notif.mensaje,
        silent: false,
      })

      notifNativa.on('click', () => {
        this.ventana.show()
        this.ventana.focus()
      })

      notifNativa.show()
    } catch (error) {
      log.error('[Tray] Error enviando notificacion nativa:', error)
    }
  }

  /** Crea un icono de badge con numero para el overlay */
  private crearBadgeIcon(conteo: number): Electron.NativeImage {
    // Icono simple con texto — en Windows, el overlay se muestra sobre el taskbar icon
    // Para un overlay minimo, creamos una imagen 16x16 roja con el numero
    const texto = conteo > 99 ? '99+' : String(conteo)

    // Usar nativeImage con un data URL SVG
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">
        <circle cx="8" cy="8" r="8" fill="#ef4444"/>
        <text x="8" y="12" text-anchor="middle" fill="white" font-size="${texto.length > 2 ? 7 : 10}" font-family="Arial" font-weight="bold">${texto}</text>
      </svg>
    `
    return nativeImage.createFromBuffer(
      Buffer.from(svg)
    )
  }
}
