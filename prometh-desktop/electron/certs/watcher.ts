import chokidar from 'chokidar'
import log from 'electron-log'

type WatcherCallback = (ruta: string) => void

let watcherActivo: chokidar.FSWatcher | null = null

/**
 * Inicia file watching en una carpeta para detectar nuevos archivos P12/PFX.
 * Solo monitorea archivos con extension .p12 y .pfx.
 */
export function iniciarWatcher(
  carpeta: string,
  onNuevoArchivo: WatcherCallback,
): void {
  if (watcherActivo) {
    log.warn('Watcher ya activo, deteniendo el anterior')
    detenerWatcher()
  }

  log.info(`Iniciando watcher en: ${carpeta}`)

  watcherActivo = chokidar.watch(
    [
      `${carpeta}/**/*.p12`,
      `${carpeta}/**/*.pfx`,
      `${carpeta}/**/*.P12`,
      `${carpeta}/**/*.PFX`,
    ],
    {
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: {
        stabilityThreshold: 2000,
        pollInterval: 100,
      },
    },
  )

  watcherActivo.on('add', (ruta) => {
    log.info(`Nuevo certificado detectado: ${ruta}`)
    onNuevoArchivo(ruta)
  })

  watcherActivo.on('error', (error) => {
    log.error('Error en watcher:', error)
  })
}

/**
 * Detiene el watcher activo.
 */
export function detenerWatcher(): void {
  if (watcherActivo) {
    watcherActivo.close()
    watcherActivo = null
    log.info('Watcher detenido')
  }
}

/**
 * Indica si hay un watcher activo.
 */
export function watcherEstaActivo(): boolean {
  return watcherActivo !== null
}
