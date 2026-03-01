import { BaseLicitaciones } from './base-licitaciones'

/**
 * Scraper de licitaciones publicas de la Comunidad Valenciana.
 * Filtra por lugar de ejecucion en el formulario JSF.
 */
export class ScraperLicitacionesValencia extends BaseLicitaciones {
  protected readonly comunidad = 'Valencia'
  protected readonly lugarEjecucion = 'Comunitat Valenciana'

  get nombre(): string {
    return 'Licitaciones Valencia'
  }
}
