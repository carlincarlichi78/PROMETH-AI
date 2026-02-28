import type { Page } from '@playwright/test'

// Token falso para tests
export const TOKEN_TEST = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test'

export const USUARIO_TEST = {
  id: 1,
  email: 'admin@sfce.local',
  nombre: 'Admin Test',
  rol: 'admin',
}

export const EMPRESAS_TEST = [
  {
    id: 1,
    cif: 'B12345678',
    nombre: 'PASTORINO COSTA DEL SOL S.L.',
    forma_juridica: 'sl',
    territorio: 'peninsula',
    regimen_iva: 'general',
    activa: true,
    idempresa_fs: 1,
  },
  {
    id: 2,
    cif: '12345678A',
    nombre: 'GERARDO GONZALEZ CALLEJON',
    forma_juridica: 'autonomo',
    territorio: 'peninsula',
    regimen_iva: 'general',
    activa: true,
    idempresa_fs: 2,
  },
  {
    id: 3,
    cif: 'B87654321',
    nombre: 'EMPRESA PRUEBA S.L.',
    forma_juridica: 'sl',
    territorio: 'peninsula',
    regimen_iva: 'general',
    activa: false,
    idempresa_fs: 3,
  },
]

// PyG — coincide con PyGOut del backend
export const PYG_TEST = {
  ingresos: 125000,
  gastos: 87500,
  resultado: 37500,
  detalle_ingresos: {
    'Ventas de mercaderias': 125000,
  },
  detalle_gastos: {
    'Compras de mercaderias': 45000,
    'Servicios exteriores': 25000,
    'Sueldos y salarios': 17500,
  },
}

// Balance — coincide con BalanceOut
export const BALANCE_TEST = {
  activo: 125000,
  pasivo: 87500,
  patrimonio_neto: 37500,
}

// Asientos — array directo de Asiento
export const ASIENTOS_TEST = [
  {
    id: 1,
    numero: 1,
    fecha: '2025-01-15',
    concepto: 'Factura proveedor EMASAGRA',
    origen: 'FV',
    partidas: [
      { id: 1, subcuenta: '6000000000', debe: 8264.46, haber: 0, concepto: null },
      { id: 2, subcuenta: '4720000000', debe: 1735.54, haber: 0, concepto: null },
      { id: 3, subcuenta: '4000000000', debe: 0, haber: 10000, concepto: null },
    ],
  },
]

// Cuentas — array para plan de cuentas
export const CUENTAS_TEST = [
  { id: 1, codigo: '100', nombre: 'Capital social', saldo: 3000 },
  { id: 2, codigo: '129', nombre: 'Resultado del ejercicio', saldo: 37500 },
  { id: 3, codigo: '400', nombre: 'Proveedores', saldo: -25000 },
  { id: 4, codigo: '430', nombre: 'Clientes', saldo: 15000 },
]

// Calendario fiscal — array de EventoFiscal (coincide con calendario-page.tsx)
export const CALENDARIO_TEST = [
  {
    modelo: '303',
    nombre: 'IVA — Liquidacion trimestral',
    periodo: 'T1 2025',
    fecha_limite: '2025-04-20',
    estado: 'presentado' as const,
  },
  {
    modelo: '303',
    nombre: 'IVA — Liquidacion trimestral',
    periodo: 'T2 2025',
    fecha_limite: '2025-07-20',
    estado: 'pendiente' as const,
  },
]

// Pipeline — array de FasePipeline (coincide con pipeline-page.tsx)
export const PIPELINE_TEST = [
  { fase: 'Validacion', total: 10, procesados: 10, errores: 0 },
  { fase: 'OCR', total: 10, procesados: 9, errores: 1 },
  { fase: 'Registro FS', total: 9, procesados: 8, errores: 1 },
]

// Facturas — array de Factura
export const FACTURAS_TEST = [
  {
    id: 1,
    tipo: 'emitida',
    numero_factura: 'F2025-001',
    fecha_factura: '2025-01-15',
    cif_emisor: 'B12345678',
    nombre_emisor: 'PASTORINO COSTA DEL SOL',
    base_imponible: 8264.46,
    iva_importe: 1735.54,
    total: 10000,
    pagada: true,
  },
]

/**
 * Configura todos los mocks de API para una sesion autenticada.
 * Intercepta las peticiones antes de navegar.
 */
export async function configurarMocksAutenticado(page: Page, empresaId = 1) {
  // Auth
  await page.route('**/api/auth/me', (route) =>
    route.fulfill({ json: USUARIO_TEST })
  )
  await page.route('**/api/auth/login', (route) =>
    route.fulfill({ json: { access_token: TOKEN_TEST, token_type: 'bearer' } })
  )

  // Empresas
  await page.route('**/api/empresas', (route) =>
    route.fulfill({ json: EMPRESAS_TEST })
  )
  await page.route(`**/api/empresas/${empresaId}`, (route) =>
    route.fulfill({ json: EMPRESAS_TEST.find((e) => e.id === empresaId) ?? EMPRESAS_TEST[0] })
  )

  // Contabilidad
  await page.route(`**/api/contabilidad/${empresaId}/pyg`, (route) =>
    route.fulfill({ json: PYG_TEST })
  )
  await page.route(`**/api/contabilidad/${empresaId}/facturas`, (route) =>
    route.fulfill({ json: FACTURAS_TEST })
  )
  await page.route(`**/api/contabilidad/${empresaId}/balance`, (route) =>
    route.fulfill({ json: BALANCE_TEST })
  )
  await page.route(`**/api/contabilidad/${empresaId}/asientos`, (route) =>
    route.fulfill({ json: ASIENTOS_TEST })
  )
  await page.route(`**/api/contabilidad/${empresaId}/subcuentas`, (route) =>
    route.fulfill({ json: CUENTAS_TEST })
  )
  await page.route(`**/api/contabilidad/${empresaId}/activos`, (route) =>
    route.fulfill({ json: [] })
  )

  // Modelos fiscales (calendario, historico, disponibles)
  await page.route(`**/api/modelos/${empresaId}/calendario`, (route) =>
    route.fulfill({ json: CALENDARIO_TEST })
  )
  await page.route(`**/api/modelos/${empresaId}/historico`, (route) =>
    route.fulfill({ json: [] })
  )
  await page.route('**/api/modelos/disponibles', (route) =>
    route.fulfill({ json: ['303', '130', '111', '390', '347'] })
  )
  await page.route(`**/api/modelos/${empresaId}/calcular`, (route) =>
    route.fulfill({ json: {} })
  )

  // Documentos
  await page.route(`**/api/documentos/${empresaId}/pipeline`, (route) =>
    route.fulfill({ json: PIPELINE_TEST })
  )
  await page.route(`**/api/documentos/${empresaId}/cuarentena`, (route) =>
    route.fulfill({ json: [] })
  )
  await page.route(`**/api/documentos/${empresaId}`, (route) =>
    route.fulfill({ json: [] })
  )

  // RRHH
  await page.route(`**/api/rrhh/${empresaId}/trabajadores`, (route) =>
    route.fulfill({ json: [] })
  )

  // Catch-all para rutas no cubiertas (evita errores de red en paginas stub)
  await page.route(`**/api/economico/${empresaId}/**`, (route) =>
    route.fulfill({ json: {} })
  )
  await page.route('**/api/directorio**', (route) =>
    route.fulfill({ json: [] })
  )
  await page.route(`**/api/copilot/**`, (route) =>
    route.fulfill({ json: {} })
  )
  await page.route(`**/api/portal/**`, (route) =>
    route.fulfill({ json: {} })
  )
  await page.route(`**/api/configuracion/**`, (route) =>
    route.fulfill({ json: {} })
  )
  await page.route(`**/api/informes/**`, (route) =>
    route.fulfill({ json: {} })
  )
}

/**
 * Inyecta token en localStorage para simular sesion activa.
 * Limpia stores persistidos de Zustand para garantizar estado fresco en cada test.
 * Debe llamarse ANTES de page.goto().
 */
export async function inyectarToken(page: Page) {
  await page.addInitScript((token) => {
    // Limpiar stores persistidos (Zustand persist)
    localStorage.removeItem('sfce-empresa-activa')
    localStorage.removeItem('sfce-ui')
    // Inyectar token de autenticacion
    localStorage.setItem('sfce_token', token)
  }, TOKEN_TEST)
}
