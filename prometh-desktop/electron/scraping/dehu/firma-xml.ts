import forge from 'node-forge'
import xmlCrypto from 'xml-crypto'
const { SignedXml } = xmlCrypto
import { readFileSync } from 'fs'
import log from 'electron-log'

/** Credenciales PEM extraidas de un PFX */
export interface CredencialesPem {
  clavePem: string
  certificadoPem: string
}

/**
 * Extrae clave privada y certificado en formato PEM de un archivo PFX.
 * Reutiliza el patron de electron/certs/lector.ts para lectura con node-forge.
 */
export function extraerCredencialesPfx(
  rutaPfx: string,
  password: string,
): CredencialesPem {
  if (!rutaPfx || !password) {
    throw new Error('rutaPfx y passwordPfx son requeridos para firma LEMA. Verifica que el certificado tiene thumbprint para exportar PFX.')
  }
  const buffer = readFileSync(rutaPfx)
  const derString = buffer.toString('binary')
  const asn1 = forge.asn1.fromDer(derString)
  const p12 = forge.pkcs12.pkcs12FromAsn1(asn1, password)

  // Extraer certificado
  const certBags = p12.getBags({ bagType: forge.pki.oids.certBag })
  const listaCerts = certBags[forge.pki.oids.certBag]

  if (!listaCerts || listaCerts.length === 0) {
    throw new Error('No se encontro certificado en el PFX')
  }

  const cert = listaCerts[0]?.cert
  if (!cert) {
    throw new Error('No se pudo leer el certificado del PFX')
  }

  // Extraer clave privada
  const keyBags = p12.getBags({ bagType: forge.pki.oids.pkcs8ShroudedKeyBag })
  const listaKeys = keyBags[forge.pki.oids.pkcs8ShroudedKeyBag]

  if (!listaKeys || listaKeys.length === 0) {
    throw new Error('No se encontro clave privada en el PFX')
  }

  const key = listaKeys[0]?.key
  if (!key) {
    throw new Error('No se pudo leer la clave privada del PFX')
  }

  const certificadoPem = forge.pki.certificateToPem(cert)
  const clavePem = forge.pki.privateKeyToPem(key)

  log.info('Credenciales PEM extraidas correctamente del PFX')

  return { clavePem, certificadoPem }
}

/**
 * Key info provider para xml-crypto.
 * Proporciona la clave de firma y el certificado X.509 para incluir en KeyInfo.
 */
class ProveedorKeyInfo {
  private readonly clavePem: string
  private readonly certificadoPem: string

  constructor(clavePem: string, certificadoPem: string) {
    this.clavePem = clavePem
    this.certificadoPem = certificadoPem
  }

  getKey(): string {
    return this.clavePem
  }

  getKeyInfo(): string {
    // Extraer solo el base64 del PEM (sin headers/footers)
    const certBase64 = this.certificadoPem
      .replace('-----BEGIN CERTIFICATE-----', '')
      .replace('-----END CERTIFICATE-----', '')
      .replace(/\s/g, '')

    return (
      '<ds:X509Data>' +
      `<ds:X509Certificate>${certBase64}</ds:X509Certificate>` +
      '</ds:X509Data>'
    )
  }
}

/**
 * Firma un documento XML SOAP con el certificado del usuario.
 * Implementa XML-DSIG enveloped signature sobre el Body del SOAP envelope.
 *
 * @param xmlSinFirmar - XML SOAP completo sin firmar
 * @param clavePem - Clave privada en formato PEM
 * @param certificadoPem - Certificado X.509 en formato PEM
 * @returns XML firmado como string
 */
export function firmarXmlSoap(
  xmlSinFirmar: string,
  clavePem: string,
  certificadoPem: string,
): string {
  const sig = new SignedXml({
    privateKey: clavePem,
    canonicalizationAlgorithm:
      'http://www.w3.org/2001/10/xml-exc-c14n#',
    signatureAlgorithm:
      'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256',
  })

  // Referenciar el Body del SOAP envelope
  sig.addReference({
    xpath: "//*[local-name(.)='Body']",
    digestAlgorithm: 'http://www.w3.org/2001/04/xmlenc#sha256',
    transforms: [
      'http://www.w3.org/2000/09/xmldsig#enveloped-signature',
      'http://www.w3.org/2001/10/xml-exc-c14n#',
    ],
  })

  // Proveedor de KeyInfo para incluir el certificado en la firma
  const proveedor = new ProveedorKeyInfo(clavePem, certificadoPem)
  sig.keyInfoProvider = proveedor as unknown as { getKeyInfo: () => string; getKey: () => string }

  // Computar la firma
  sig.computeSignature(xmlSinFirmar, {
    location: { reference: "//*[local-name(.)='Header']", action: 'append' },
  })

  const xmlFirmado = sig.getSignedXml()

  log.info('XML SOAP firmado correctamente')

  return xmlFirmado
}
