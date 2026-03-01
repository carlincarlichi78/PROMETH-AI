import { BaseLicitaciones } from './base-licitaciones'

/**
 * Scraper de licitaciones publicas de la Generalitat de Catalunya.
 * Filtra por lugar de ejecucion en el formulario JSF.
 */
export class ScraperLicitacionesCatalunya extends BaseLicitaciones {
  protected readonly comunidad = 'Catalunya'
  protected readonly lugarEjecucion = 'Cataluña'

  get nombre(): string {
    return 'Licitaciones Catalunya'
  }
}
