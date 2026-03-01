import { chromium } from 'playwright'
import { resolve } from 'path'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

async function generar() {
  const htmlPath = resolve(__dirname, 'icon.html')
  const pngPath = resolve(__dirname, 'icon.png')

  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 512, height: 512 } })
  await page.goto(`file:///${htmlPath.replace(/\\/g, '/')}`)
  await page.screenshot({ path: pngPath, omitBackground: true })
  await browser.close()

  console.log(`icon.png generado en ${pngPath}`)
}

generar().catch(console.error)
