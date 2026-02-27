/** Claves centralizadas para React Query — previene colisiones y facilita invalidacion */
export const queryKeys = {
  empresas: {
    todas: ['empresas'] as const,
    detalle: (id: number) => ['empresas', id] as const,
    proveedores: (id: number) => ['empresas', id, 'proveedores'] as const,
    trabajadores: (id: number) => ['empresas', id, 'trabajadores'] as const,
  },
  contabilidad: {
    pyg: (empresaId: number, params?: Record<string, string>) =>
      ['contabilidad', empresaId, 'pyg', params] as const,
    balance: (empresaId: number, params?: Record<string, string>) =>
      ['contabilidad', empresaId, 'balance', params] as const,
    diario: (empresaId: number, params?: Record<string, string>) =>
      ['contabilidad', empresaId, 'diario', params] as const,
    facturas: (empresaId: number, params?: Record<string, string>) =>
      ['contabilidad', empresaId, 'facturas', params] as const,
    activos: (empresaId: number) => ['contabilidad', empresaId, 'activos'] as const,
    planCuentas: (empresaId: number) => ['contabilidad', empresaId, 'plan-cuentas'] as const,
  },
  documentos: {
    lista: (empresaId: number, params?: Record<string, string>) =>
      ['documentos', empresaId, params] as const,
    cuarentena: (empresaId: number) => ['documentos', empresaId, 'cuarentena'] as const,
    pipeline: (empresaId: number) => ['documentos', empresaId, 'pipeline'] as const,
  },
  modelos: {
    disponibles: ['modelos', 'disponibles'] as const,
    calendario: (empresaId: number) => ['modelos', empresaId, 'calendario'] as const,
    historico: (empresaId: number) => ['modelos', empresaId, 'historico'] as const,
    calcular: (empresaId: number, modelo: string, periodo: string) =>
      ['modelos', empresaId, modelo, periodo] as const,
  },
  directorio: {
    todos: ['directorio'] as const,
    buscar: (q: string) => ['directorio', 'buscar', q] as const,
    detalle: (id: number) => ['directorio', id] as const,
  },
  economico: {
    ratios: (empresaId: number) => ['economico', empresaId, 'ratios'] as const,
    kpis: (empresaId: number) => ['economico', empresaId, 'kpis'] as const,
    tesoreria: (empresaId: number) => ['economico', empresaId, 'tesoreria'] as const,
    cashflow: (empresaId: number) => ['economico', empresaId, 'cashflow'] as const,
    scoring: (empresaId: number) => ['economico', empresaId, 'scoring'] as const,
    presupuesto: (empresaId: number) => ['economico', empresaId, 'presupuesto'] as const,
    comparativa: (empresaId: number) => ['economico', empresaId, 'comparativa'] as const,
  },
} as const
