import { test, expect } from '@playwright/test'
import { CALENDARIO_TEST, configurarMocksAutenticado, inyectarToken } from './helpers/api-mocks'

const EMPRESA_ID = 1

test.describe('Fiscal — Calendario', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('Calendario fiscal carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/calendario-fiscal`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('Calendario muestra obligaciones del mock', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/calendario-fiscal`)

    // El modelo 303 debe aparecer (columna Modelo de la tabla)
    await expect(page.getByText('303').first()).toBeVisible({ timeout: 8000 })
  })

  test('Calendario muestra estado de obligaciones', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/calendario-fiscal`)

    // Estados del mock: presentado + pendiente
    await expect(page.getByText(/presentado|pendiente/i).first()).toBeVisible({ timeout: 8000 })
  })
})

test.describe('Fiscal — Modelos fiscales', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('Modelos fiscales carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/modelos-fiscales`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('Generar modelo carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/modelos-fiscales/generar`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('Historico modelos carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/modelos-fiscales/historico`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })
})
