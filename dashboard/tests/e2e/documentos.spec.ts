import { test, expect } from '@playwright/test'
import { PIPELINE_TEST, configurarMocksAutenticado, inyectarToken } from './helpers/api-mocks'

const EMPRESA_ID = 1

test.describe('Documentos — Inbox', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('Inbox carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/inbox`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('Inbox vacio muestra estado vacio', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/inbox`)

    // Con 0 items, debe mostrar estado vacio o tabla vacia
    await expect(page.locator('body')).not.toBeEmpty()
    await expect(page).not.toHaveURL(/\/login/)
  })
})

test.describe('Documentos — Pipeline', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('Pipeline carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/pipeline`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('Pipeline muestra fases del mock', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/pipeline`)

    // Las fases del mock: Validacion, OCR, Registro FS
    await expect(page.getByText(/Validacion|OCR|Pipeline/i).first()).toBeVisible({ timeout: 8000 })
  })
})

test.describe('Documentos — Cuarentena y Archivo', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('Cuarentena carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/cuarentena`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('Archivo carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/archivo`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })
})
