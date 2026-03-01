import { BaseLicitaciones } from './base-licitaciones'

/**
 * Scraper de licitaciones publicas a nivel nacional.
 * Sin filtro de lugar — muestra todos los procedimientos abiertos publicados.
 */
export class ScraperLicitacionesGeneral extends BaseLicitaciones {
  protected readonly comunidad = 'General'
  protected readonly lugarEjecucion = ''

  get nombre(): string {
    return 'Licitaciones General'
  }
}
