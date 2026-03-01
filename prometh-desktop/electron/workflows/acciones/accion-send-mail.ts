import { existsSync, readdirSync } from 'fs'
import { join, extname } from 'path'
import nodemailer from 'nodemailer'
const { createTransport } = nodemailer
import log from 'electron-log'
import { AccionBase } from './accion-base'
import type {
  ConfigSendMail,
  ContextoEjecucionDesktop,
  ResultadoAccionDesktop,
} from '../tipos-workflows-desktop'

/**
 * Accion: enviar email con adjuntos via SMTP (Nodemailer).
 *
 * Soporta templates en asunto y cuerpo: {nif}, {fecha}, {modelo}, etc.
 * Adjunta todos los archivos de carpetaAdjuntos (filtrados por extensiones).
 */
export class AccionSendMail extends AccionBase {
  constructor(config: ConfigSendMail) {
    super('send_mail', config)
  }

  private get cfg(): ConfigSendMail {
    return this.config as ConfigSendMail
  }

  async preRun(_contexto: ContextoEjecucionDesktop): Promise<void> {
    if (!this.cfg.emailDestino) {
      throw new Error('Email destino es obligatorio')
    }
    if (!this.cfg.smtpHost || !this.cfg.smtpUser) {
      throw new Error('Configuracion SMTP incompleta (host y user requeridos)')
    }

    if (this.cfg.carpetaAdjuntos && !existsSync(this.cfg.carpetaAdjuntos)) {
      throw new Error(`Carpeta de adjuntos no existe: ${this.cfg.carpetaAdjuntos}`)
    }
  }

  async run(contexto: ContextoEjecucionDesktop): Promise<ResultadoAccionDesktop> {
    const transporter = createTransport({
      host: this.cfg.smtpHost,
      port: this.cfg.smtpPort,
      secure: this.cfg.smtpSecure,
      auth: {
        user: this.cfg.smtpUser,
        pass: this.cfg.smtpPass,
      },
    })

    // Recoger adjuntos
    const adjuntos = this.recogerAdjuntos()

    // Reemplazar templates en asunto y cuerpo
    const asunto = this.reemplazarTemplates(this.cfg.asunto, contexto)
    const cuerpo = this.reemplazarTemplates(this.cfg.cuerpo, contexto)

    // Destinos multiples separados por ;
    const destinatarios = this.cfg.emailDestino
      .split(';')
      .map((e) => e.trim())
      .filter(Boolean)

    const info = await transporter.sendMail({
      from: this.cfg.emailOrigen,
      to: destinatarios.join(', '),
      subject: asunto,
      html: cuerpo,
      attachments: adjuntos.map((ruta) => ({ path: ruta })),
    })

    log.info(`[SendMail] Email enviado: ${info.messageId}, ${adjuntos.length} adjuntos`)

    return {
      tipo: 'send_mail',
      exito: true,
      mensaje: `Email enviado a ${destinatarios.length} destinatario(s) con ${adjuntos.length} adjunto(s)`,
      archivosResultado: adjuntos,
      tiempoMs: 0,
    }
  }

  async postRun(_resultado: ResultadoAccionDesktop): Promise<void> {
    // Sin limpieza necesaria
  }

  /**
   * Recoge archivos adjuntos de la carpeta configurada.
   * Filtra por extensiones si se especifican.
   */
  private recogerAdjuntos(): string[] {
    if (!this.cfg.carpetaAdjuntos || !existsSync(this.cfg.carpetaAdjuntos)) {
      return []
    }

    const archivos = readdirSync(this.cfg.carpetaAdjuntos)
    const extensiones = this.cfg.extensiones ?? []

    return archivos
      .filter((archivo) => {
        if (extensiones.length === 0) return true
        const ext = extname(archivo).toLowerCase()
        return extensiones.includes(ext)
      })
      .map((archivo) => join(this.cfg.carpetaAdjuntos!, archivo))
  }
}
