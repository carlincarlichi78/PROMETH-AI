/**
 * Script de firma de codigo para electron-builder.
 *
 * Lee las variables de entorno:
 *   - CERTIGESTOR_CERT_PATH: ruta al certificado .pfx
 *   - CERTIGESTOR_CERT_PASSWORD: password del certificado
 *
 * Si no estan configuradas, salta la firma silenciosamente (dev sin certificado).
 * Para activar: comprar certificado OV Code Signing (~200 EUR/anio)
 * y configurar las env vars en el entorno de build.
 *
 * @see docs/code-signing.md
 */

const { execSync } = require('child_process')

exports.default = async function firmarEjecutable(configuration) {
  const certPath = process.env.CERTIGESTOR_CERT_PATH
  const certPassword = process.env.CERTIGESTOR_CERT_PASSWORD

  if (!certPath || !certPassword) {
    console.log('[sign] Saltando firma: CERTIGESTOR_CERT_PATH no configurado')
    return
  }

  const archivoAFirmar = configuration.path
  console.log(`[sign] Firmando: ${archivoAFirmar}`)

  try {
    execSync(
      `signtool sign /f "${certPath}" /p "${certPassword}" /fd sha256 /t http://timestamp.digicert.com /v "${archivoAFirmar}"`,
      { stdio: 'inherit' },
    )
    console.log('[sign] Firma completada correctamente')
  } catch (error) {
    console.error('[sign] Error firmando:', error.message)
    // No lanzar error — permite builds sin firma en desarrollo
  }
}
