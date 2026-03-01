import { BaseLicitaciones } from './base-licitaciones'

/**
 * Scraper de licitaciones publicas de la Junta de Andalucia.
 * Filtra por lugar de ejecucion en el formulario JSF.
 */
export class ScraperLicitacionesAndalucia extends BaseLicitaciones {
  protected readonly comunidad = 'Andalucia'
  protected readonly lugarEjecucion = 'Andalucía'

  get nombre(): string {
    return 'Licitaciones Andalucia'
  }
}
