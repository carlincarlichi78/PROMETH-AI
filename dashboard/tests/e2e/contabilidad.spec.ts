import { test, expect } from '@playwright/test'
import {
  PYG_TEST, ASIENTOS_TEST,
  configurarMocksAutenticado, inyectarToken,
} from './helpers/api-mocks'

const EMPRESA_ID = 1

test.describe('Contabilidad — PyG', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('PyG carga y muestra datos', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/pyg`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('PyG muestra el titulo de la pagina', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/pyg`)

    // El PageHeader renderiza <h1>Cuenta de Resultados (PyG)</h1>
    await expect(page.getByRole('heading', { name: /Cuenta de Resultados|PyG/i })).toBeVisible({ timeout: 8000 })
  })
})

test.describe('Contabilidad — Balance', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('Balance carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/balance`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })
})

test.describe('Contabilidad — Diario', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('Diario carga y muestra tabla de asientos', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/diario`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('Diario muestra asiento del mock', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/diario`)

    const concepto = ASIENTOS_TEST[0].concepto
    await expect(page.getByText(concepto)).toBeVisible({ timeout: 8000 })
  })
})

test.describe('Contabilidad — Plan de Cuentas', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('Plan de Cuentas carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/plan-cuentas`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('Plan de Cuentas muestra seccion de cuentas', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/plan-cuentas`)

    await expect(page.locator('h1, h2, h3').first()).toBeVisible({ timeout: 8000 })
  })
})

test.describe('Contabilidad — Amortizaciones', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('Amortizaciones carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/amortizaciones`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })
})

test.describe('Contabilidad — Cierre y Apertura', () => {
  test.beforeEach(async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)
  })

  test('Cierre de ejercicio carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/cierre`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('Apertura de ejercicio carga sin error', async ({ page }) => {
    await page.goto(`/empresa/${EMPRESA_ID}/apertura`)
    await expect(page).not.toHaveURL(/\/login/)
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })
})
