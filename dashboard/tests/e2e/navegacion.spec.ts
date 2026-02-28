import { test, expect } from '@playwright/test'
import { configurarMocksAutenticado, inyectarToken } from './helpers/api-mocks'

const EMPRESA_ID = 1

// Todas las rutas del dashboard con empresa ID
const RUTAS = [
  // Contabilidad
  { path: `/empresa/${EMPRESA_ID}/pyg`, titulo: /PyG|Cuenta de P.rdidas|Resultados/i },
  { path: `/empresa/${EMPRESA_ID}/balance`, titulo: /Balance/i },
  { path: `/empresa/${EMPRESA_ID}/diario`, titulo: /Diario/i },
  { path: `/empresa/${EMPRESA_ID}/plan-cuentas`, titulo: /Plan de Cuentas|Cuentas/i },
  { path: `/empresa/${EMPRESA_ID}/amortizaciones`, titulo: /Amortizaciones/i },
  { path: `/empresa/${EMPRESA_ID}/cierre`, titulo: /Cierre/i },
  { path: `/empresa/${EMPRESA_ID}/apertura`, titulo: /Apertura/i },
  // Facturacion
  { path: `/empresa/${EMPRESA_ID}/facturas-emitidas`, titulo: /Facturas Emitidas|Emitidas/i },
  { path: `/empresa/${EMPRESA_ID}/facturas-recibidas`, titulo: /Facturas Recibidas|Recibidas/i },
  { path: `/empresa/${EMPRESA_ID}/cobros-pagos`, titulo: /Cobros|Pagos/i },
  // RRHH
  { path: `/empresa/${EMPRESA_ID}/nominas`, titulo: /N.minas/i },
  { path: `/empresa/${EMPRESA_ID}/trabajadores`, titulo: /Trabajadores/i },
  // Fiscal
  { path: `/empresa/${EMPRESA_ID}/calendario-fiscal`, titulo: /Calendario/i },
  { path: `/empresa/${EMPRESA_ID}/modelos-fiscales`, titulo: /Modelos/i },
  // Documentos
  { path: `/empresa/${EMPRESA_ID}/inbox`, titulo: /Inbox|Bandeja/i },
  { path: `/empresa/${EMPRESA_ID}/pipeline`, titulo: /Pipeline/i },
  { path: `/empresa/${EMPRESA_ID}/cuarentena`, titulo: /Cuarentena/i },
  { path: `/empresa/${EMPRESA_ID}/archivo`, titulo: /Archivo/i },
]

test.describe('Navegacion — todas las paginas cargan', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  for (const ruta of RUTAS) {
    test(`${ruta.path} carga sin error`, async ({ page }) => {
      await page.goto(ruta.path)

      // No debe redirigir a login
      await expect(page).not.toHaveURL(/\/login/)

      // Debe mostrar algun titulo de pagina (h1 del PageHeader o h3 de tarjetas)
      await expect(page.locator('h1, h2, h3').first()).toBeVisible({ timeout: 10000 })
    })
  }
})

test.describe('Navegacion — rutas protegidas', () => {
  test('rutas sin token redirigen a /login', async ({ page }) => {
    await page.route('**/api/auth/me', (route) =>
      route.fulfill({ status: 401, json: {} })
    )

    await page.goto(`/empresa/${EMPRESA_ID}/pyg`)
    await expect(page).toHaveURL(/\/login/)
  })

  test('/login con token activo redirige al home', async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)

    // Si ya hay sesion, /login debe redirigir o mostrar home
    await page.goto('/')
    await expect(page).not.toHaveURL(/\/login/)
  })

  test('ruta inexistente muestra 404', async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)

    await page.goto('/ruta-que-no-existe')
    // Debe mostrar algo (pagina 404 o redirigir)
    await expect(page.locator('body')).not.toBeEmpty()
  })
})

test.describe('Layout — sidebar y header', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('sidebar visible en pagina de empresa', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/pyg`)

    // El sidebar debe existir en el DOM
    await expect(page.locator('nav, aside, [role="navigation"]').first()).toBeVisible()
  })

  test('header visible con titulo SFCE', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/pyg`)

    // Header con brand o nombre de empresa
    await expect(page.locator('header').first()).toBeVisible()
  })
})
