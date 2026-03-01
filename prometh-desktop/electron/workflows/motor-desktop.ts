import log from 'electron-log'
import { AccionSplitPdf } from './acciones/accion-split-pdf'
import { AccionSendMail } from './acciones/accion-send-mail'
import { AccionProtectPdf } from './acciones/accion-protect-pdf'
import { AccionSendToRepository } from './acciones/accion-send-to-repository'
import type { AccionBase } from './acciones/accion-base'
import type {
  AccionWorkflowDesktop,
  CondicionWorkflowDesktop,
  ContextoEjecucionDesktop,
  ResultadoAccionDesktop,
  ResultadoWorkflowDesktop,
  ConfigSplitPdf,
  ConfigSendMail,
  ConfigProtectPdf,
  ConfigSendToRepository,
} from './tipos-workflows-desktop'

/**
 * Crea instancia de accion a partir de su definicion.
 * Factory pattern: tipo → clase concreta.
 */
export function crearAccion(definicion: AccionWorkflowDesktop): AccionBase {
  switch (definicion.tipo) {
    case 'split_pdf':
      return new AccionSplitPdf(definicion.config as ConfigSplitPdf)
    case 'send_mail':
      return new AccionSendMail(definicion.config as ConfigSendMail)
    case 'protect_pdf':
      return new AccionProtectPdf(definicion.config as ConfigProtectPdf)
    case 'send_to_repository':
      return new AccionSendToRepository(definicion.config as ConfigSendToRepository)
    default:
      throw new Error(`Tipo de accion desktop desconocido: ${(definicion as AccionWorkflowDesktop).tipo}`)
  }
}

/**
 * Evalua condiciones de un workflow desktop.
 * Logica AND: todas deben cumplirse.
 * Misma logica que el motor API (evaluarCondiciones).
 */
export function evaluarCondicionesDesktop(
  condiciones: CondicionWorkflowDesktop[],
  contexto: ContextoEjecucionDesktop
): boolean {
  if (condiciones.length === 0) return true

  return condiciones.every((condicion) => {
    const { campo, operador, valor } = condicion

    if (!(campo in contexto)) return false

    const contextoValor = contexto[campo]

    switch (operador) {
      case 'igual':
        return String(valor) === String(contextoValor)
      case 'distinto':
        return String(valor) !== String(contextoValor)
      case 'contiene':
        return String(contextoValor).includes(String(valor))
      case 'no_contiene':
        return !String(contextoValor).includes(String(valor))
      case 'mayor_que':
        return Number(contextoValor) > Number(valor)
      case 'menor_que':
        return Number(contextoValor) < Number(valor)
      case 'mayor_igual':
        return Number(contextoValor) >= Number(valor)
      case 'menor_igual':
        return Number(contextoValor) <= Number(valor)
      default:
        return false
    }
  })
}

/**
 * Ejecuta las acciones de un workflow secuencialmente.
 * Pipeline: cada accion puede pasar datos a la siguiente via datosExtra.
 *
 * @param onProgreso - Callback para emitir progreso entre acciones
 */
export async function ejecutarAccionesDesktop(
  workflowId: string,
  workflowNombre: string,
  acciones: AccionWorkflowDesktop[],
  contexto: ContextoEjecucionDesktop,
  onProgreso?: (porcentaje: number, accionNombre: string) => void
): Promise<ResultadoWorkflowDesktop> {
  const inicio = Date.now()
  const resultados: ResultadoAccionDesktop[] = []

  // Contexto mutable entre acciones (pipeline pattern)
  let contextoActual = { ...contexto }

  for (let i = 0; i < acciones.length; i++) {
    const definicion = acciones[i]!
    const porcentaje = Math.round((i / acciones.length) * 100)

    onProgreso?.(porcentaje, definicion.tipo)
    log.info(`[MotorDesktop] Ejecutando accion ${i + 1}/${acciones.length}: ${definicion.tipo}`)

    try {
      const accion = crearAccion(definicion)
      const resultado = await accion.execute(contextoActual)
      resultados.push(resultado)

      if (!resultado.exito) {
        log.warn(`[MotorDesktop] Accion fallida: ${definicion.tipo} — ${resultado.mensaje}`)
        // Continuar con las siguientes acciones (no abortar)
      }

      // Pasar datos de esta accion al contexto de la siguiente
      if (resultado.datosExtra) {
        contextoActual = { ...contextoActual, ...resultado.datosExtra }
      }

      // Si la accion genero archivos, actualizar carpetaTrabajo
      if (resultado.archivosResultado && resultado.archivosResultado.length > 0) {
        const carpetaResultado = resultado.datosExtra?.carpetaDestino as string | undefined
        if (carpetaResultado) {
          contextoActual = { ...contextoActual, carpetaTrabajo: carpetaResultado }
        }
      }
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'Error desconocido'
      log.error(`[MotorDesktop] Error critico en accion ${definicion.tipo}:`, error)
      resultados.push({
        tipo: definicion.tipo,
        exito: false,
        mensaje,
        tiempoMs: 0,
      })
    }
  }

  onProgreso?.(100, 'completado')

  const tiempoTotalMs = Date.now() - inicio
  const todasExitosas = resultados.every((r) => r.exito)

  return {
    workflowId,
    exito: todasExitosas,
    acciones: resultados,
    tiempoTotalMs,
    error: todasExitosas
      ? undefined
      : resultados
          .filter((r) => !r.exito)
          .map((r) => `${r.tipo}: ${r.mensaje}`)
          .join('; '),
  }
}
