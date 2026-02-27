import { format, parseISO } from 'date-fns'
import { es } from 'date-fns/locale'

/** Formatea importe en EUR: 1234.56 → "1.234,56 EUR" */
export function formatearImporte(valor: number | null | undefined, moneda = 'EUR'): string {
  if (valor == null) return '-'
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: moneda }).format(valor)
}

/** Formatea porcentaje: 0.1234 → "12,34%" */
export function formatearPorcentaje(
  valor: number | null | undefined,
  decimales = 2
): string {
  if (valor == null) return '-'
  return new Intl.NumberFormat('es-ES', {
    style: 'percent',
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(valor)
}

/** Formatea fecha: "2025-01-15" → "15 ene 2025" */
export function formatearFecha(
  fecha: string | null | undefined,
  patron = 'd MMM yyyy'
): string {
  if (!fecha) return '-'
  try {
    return format(parseISO(fecha), patron, { locale: es })
  } catch {
    return fecha
  }
}

/** Formatea numero: 1234567.89 → "1.234.567,89" */
export function formatearNumero(valor: number | null | undefined, decimales = 2): string {
  if (valor == null) return '-'
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(valor)
}

/** Clase CSS segun variacion positiva/negativa */
export function colorVariacion(valor: number): string {
  if (valor > 0) return 'text-green-600 dark:text-green-400'
  if (valor < 0) return 'text-red-600 dark:text-red-400'
  return 'text-muted-foreground'
}
