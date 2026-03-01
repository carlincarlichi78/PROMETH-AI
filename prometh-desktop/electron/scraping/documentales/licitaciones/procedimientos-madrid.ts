import { BaseLicitaciones } from './base-licitaciones'

/**
 * Scraper de licitaciones publicas de la Comunidad de Madrid.
 * Filtra por lugar de ejecucion en el formulario JSF.
 */
export class ScraperLicitacionesMadrid extends BaseLicitaciones {
  protected readonly comunidad = 'Madrid'
  protected readonly lugarEjecucion = 'Madrid'

  get nombre(): string {
    return 'Licitaciones Madrid'
  }
}
