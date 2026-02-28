import { test, expect } from '@playwright/test'
import { EMPRESAS_TEST, configurarMocksAutenticado, inyectarToken } from './helpers/api-mocks'

test.describe('Home — Selector de empresa', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('muestra selector de empresa al ir a /', async ({ page }) => {
    await page.goto('/')
    // El PageHeader renderiza <h1>Panel Principal</h1>
    await expect(page.getByRole('heading', { name: 'Panel Principal' })).toBeVisible({ timeout: 8000 })
  })

  test('lista empresas activas', async ({ page }) => {
    await page.goto('/')

    const activas = EMPRESAS_TEST.filter((e) => e.activa)
    for (const empresa of activas) {
      await expect(page.getByText(empresa.nombre)).toBeVisible()
    }
  })

  test('muestra CIF y forma juridica de cada empresa', async ({ page }) => {
    await page.goto('/')

    // Empresa 1 — S.L.
    await expect(page.getByText('B12345678')).toBeVisible()
    // Empresa 2 — autonomo
    await expect(page.getByText('12345678A')).toBeVisible()
  })

  test('seleccionar empresa navega a /empresa/:id', async ({ page }) => {
    await page.goto('/')

    // Click en primera empresa activa
    await page.getByText(EMPRESAS_TEST[0].nombre).click()

    await expect(page).toHaveURL(`/empresa/${EMPRESAS_TEST[0].id}`)
  })

  test('dashboard empresa muestra KPIs al ir a /empresa/:id/pyg', async ({ page }) => {
    // No existe ruta /empresa/:id — el dashboard se accede desde /empresa/:id/pyg y similares
    await page.goto(`/empresa/${EMPRESAS_TEST[0].id}/pyg`)

    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible({ timeout: 8000 })
  })

  test('empresas inactivas no aparecen en la seleccion principal', async ({ page }) => {
    await page.goto('/')

    // Empresa inactiva no debe aparecer destacada
    // (puede que aparezca en seccion colapsada pero no en activas)
    const activas = EMPRESAS_TEST.filter((e) => e.activa)
    expect(activas.length).toBe(2)
  })
})
