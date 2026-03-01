import { randomUUID } from 'crypto'
import { basename } from 'path'
import { BrowserWindow } from 'electron'
import log from 'electron-log'
import { firmarPdfLocal, validarCertificadoParaFirma } from './firmador-local'
import { firmarConAutoFirma, detectarAutoFirma } from './autofirma'
import { registrarFirma } from './historial-firmas'
import { sincronizarFirmasConCloud } from './sincronizar-firmas'
import type {
  ModoFirma,
  OpcionesFirmaLocal,
  OpcionesFirmaAutoFirma,
  OpcionesFirmaBatch,
  ResultadoFirma,
  ResultadoSincFirma,
  ProgresoFirmaBatch,
} from './tipos-firma'

/**
 * Orquestador de firma digital.
 * Coordina firma local (PAdES) y AutoFirma, gestiona batch y progreso.
 */
export class OrquestadorFirma {
  private readonly ventana: BrowserWindow | null

  constructor(ventana?: BrowserWindow | null) {
    this.ventana = ventana ?? null
  }

  /**
   * Detecta los modos de firma disponibles en el sistema.
   * - 'local' siempre disponible (solo necesita P12 en disco)
   * - 'autofirma' solo si la app esta instalada
   */
  async obtenerModosDisponibles(): Promise<ModoFirma[]> {
    const modos: ModoFirma[] = ['local']

    const tieneAutoFirma = await detectarAutoFirma()
    if (tieneAutoFirma) {
      modos.push('autofirma')
    }

    return modos
  }

  /**
   * Firma un PDF individual con el modo especificado.
   * Registra automaticamente en el historial local.
   */
  async firmar(
    modo: ModoFirma,
    opciones: OpcionesFirmaLocal | OpcionesFirmaAutoFirma,
    certificadoSerial: string,
  ): Promise<ResultadoFirma> {
    let resultado: ResultadoFirma

    if (modo === 'local') {
      resultado = await firmarPdfLocal(opciones as OpcionesFirmaLocal)
    } else {
      resultado = await firmarConAutoFirma(opciones as OpcionesFirmaAutoFirma)
    }

    // Registrar en historial si exito
    if (resultado.exito && resultado.rutaPdfFirmado) {
      const rutaOriginal =
        'rutaPdf' in opciones ? opciones.rutaPdf : (opciones as OpcionesFirmaAutoFirma).rutaPdf

      registrarFirma({
        id: randomUUID(),
        rutaPdfOriginal: rutaOriginal,
        rutaPdfFirmado: resultado.rutaPdfFirmado,
        certificadoSerial,
        modo,
        fechaFirma: new Date().toISOString(),
        razon:
          modo === 'local'
            ? ((opciones as OpcionesFirmaLocal).razon ?? 'Firmado digitalmente con CertiGestor')
            : 'Firmado con AutoFirma',
        sincronizadoCloud: false,
      })
    }

    return resultado
  }

  /**
   * Firma multiples PDFs con el mismo certificado.
   * Ejecuta secuencialmente y emite progreso via IPC.
   */
  async firmarBatch(opciones: OpcionesFirmaBatch): Promise<ResultadoFirma[]> {
    const {
      rutasPdf,
      rutaCertificado,
      passwordCertificado,
      certificadoSerial,
      modo,
      thumbprint,
      razon,
      ubicacion,
    } = opciones

    const resultados: ResultadoFirma[] = []
    let errores = 0

    log.info(`[OrqFirma] Iniciando batch: ${rutasPdf.length} PDFs, modo=${modo}`)

    for (let i = 0; i < rutasPdf.length; i++) {
      const rutaPdf = rutasPdf[i]!

      // Emitir progreso
      this.emitirProgreso({
        total: rutasPdf.length,
        completados: i,
        actual: basename(rutaPdf),
        errores,
      })

      let opcionesIndividual: OpcionesFirmaLocal | OpcionesFirmaAutoFirma

      if (modo === 'local') {
        opcionesIndividual = {
          rutaPdf,
          rutaCertificado,
          passwordCertificado,
          razon,
          ubicacion,
        }
      } else {
        if (!thumbprint) {
          resultados.push({
            exito: false,
            modo: 'autofirma',
            error: 'Thumbprint requerido para firma con AutoFirma',
          })
          errores++
          continue
        }
        opcionesIndividual = {
          rutaPdf,
          thumbprint,
        }
      }

      const resultado = await this.firmar(modo, opcionesIndividual, certificadoSerial)
      resultados.push(resultado)

      if (!resultado.exito) {
        errores++
      }
    }

    // Progreso final
    this.emitirProgreso({
      total: rutasPdf.length,
      completados: rutasPdf.length,
      actual: '',
      errores,
    })

    const exitosos = resultados.filter((r) => r.exito).length
    log.info(
      `[OrqFirma] Batch completado: ${exitosos}/${rutasPdf.length} exitosos, ${errores} errores`,
    )

    return resultados
  }

  /**
   * Valida un certificado P12 para firma.
   * Verifica: legible, no caducado, tiene clave privada.
   */
  validarCertificado(
    ruta: string,
    password: string,
  ): { valido: boolean; error?: string; serial?: string } {
    return validarCertificadoParaFirma(ruta, password)
  }

  /**
   * Sincroniza firmas pendientes con la API cloud.
   */
  async sincronizarConCloud(
    apiUrl: string,
    token: string,
    mapaCertificados?: Record<string, string>,
  ): Promise<ResultadoSincFirma> {
    return sincronizarFirmasConCloud(apiUrl, token, mapaCertificados)
  }

  /**
   * Emite evento de progreso via IPC al renderer.
   */
  private emitirProgreso(progreso: ProgresoFirmaBatch): void {
    if (this.ventana && !this.ventana.isDestroyed()) {
      this.ventana.webContents.send('firma:progreso', progreso)
    }
  }
}
