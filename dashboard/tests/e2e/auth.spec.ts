import { test, expect } from '@playwright/test'
import { TOKEN_TEST, configurarMocksAutenticado, inyectarToken } from './helpers/api-mocks'

test.describe('Autenticacion', () => {
  test('redirige a /login si no hay token', async ({ page }) => {
    await page.route('**/api/auth/me', (route) => route.fulfill({ status: 401, json: { detail: 'No autenticado' } }))
    await page.route('**/api/empresas', (route) => route.fulfill({ json: [] }))

    await page.goto('/')
    await expect(page).toHaveURL(/\/login/)
  })

  test('redirige a /login si token invalido', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('sfce_token', 'token-invalido')
    })
    await page.route('**/api/auth/me', (route) =>
      route.fulfill({ status: 401, json: { detail: 'Token invalido' } })
    )
    await page.route('**/api/empresas', (route) => route.fulfill({ json: [] }))

    await page.goto('/')
    await expect(page).toHaveURL(/\/login/)
  })

  test('muestra formulario de login', async ({ page }) => {
    await page.route('**/api/auth/me', (route) => route.fulfill({ status: 401, json: {} }))

    await page.goto('/login')
    await expect(page.getByText('SFCE')).toBeVisible()
    await expect(page.getByText('Sistema Fiscal Contable Evolutivo')).toBeVisible()
    await expect(page.getByLabel('Correo electronico')).toBeVisible()
    await expect(page.getByLabel('Contrasena')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Iniciar sesion' })).toBeVisible()
  })

  test('login exitoso redirige al home', async ({ page }) => {
    await configurarMocksAutenticado(page)

    await page.goto('/login')
    await page.getByLabel('Correo electronico').fill('admin@sfce.local')
    await page.getByLabel('Contrasena').fill('admin')
    await page.getByRole('button', { name: 'Iniciar sesion' }).click()

    await expect(page).toHaveURL('/')
  })

  test('login fallido muestra error', async ({ page }) => {
    await page.route('**/api/auth/login', (route) =>
      route.fulfill({ status: 401, json: { detail: 'Credenciales incorrectas' } })
    )
    await page.route('**/api/auth/me', (route) =>
      route.fulfill({ status: 401, json: {} })
    )

    await page.goto('/login')
    await page.getByLabel('Correo electronico').fill('malo@test.com')
    await page.getByLabel('Contrasena').fill('contrasena-mal')
    await page.getByRole('button', { name: 'Iniciar sesion' }).click()

    await expect(page.getByText('Credenciales incorrectas')).toBeVisible()
    await expect(page).toHaveURL(/\/login/)
  })

  test('token se guarda en localStorage tras login', async ({ page }) => {
    await configurarMocksAutenticado(page)

    await page.goto('/login')
    await page.getByLabel('Correo electronico').fill('admin@sfce.local')
    await page.getByLabel('Contrasena').fill('admin')
    await page.getByRole('button', { name: 'Iniciar sesion' }).click()

    const token = await page.evaluate(() => localStorage.getItem('sfce_token'))
    expect(token).toBe(TOKEN_TEST)
  })

  test('boton de login deshabilitado mientras envia', async ({ page }) => {
    // Respuesta lenta para capturar estado intermedio
    await page.route('**/api/auth/login', async (route) => {
      await new Promise((r) => setTimeout(r, 500))
      route.fulfill({ json: { access_token: TOKEN_TEST } })
    })
    await page.route('**/api/auth/me', (route) =>
      route.fulfill({ status: 401, json: {} })
    )
    await page.route('**/api/empresas', (route) => route.fulfill({ json: [] }))

    await page.goto('/login')
    await page.getByLabel('Correo electronico').fill('admin@sfce.local')
    await page.getByLabel('Contrasena').fill('admin')

    const boton = page.getByRole('button', { name: /Iniciar sesion|Iniciando sesion/ })
    await boton.click()

    // Mientras procesa debe mostrar "Iniciando sesion..."
    await expect(page.getByRole('button', { name: 'Iniciando sesion...' })).toBeVisible()
  })

  test('sesion existente no muestra login al ir a /', async ({ page }) => {
    await configurarMocksAutenticado(page)
    await inyectarToken(page)

    await page.goto('/')

    // No redirige a login
    await expect(page).not.toHaveURL(/\/login/)
  })
})
