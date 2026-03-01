import forge from 'node-forge'
import { readFileSync } from 'fs'
import type { CertificadoLocal } from './tipos'

/**
 * Busca el valor de un atributo en la lista de atributos del certificado.
 * Acepta shortName (CN, O, etc.) o name completo.
 */
function obtenerAtributo(
  attrs: forge.pki.CertificateField[],
  shortName: string,
): string | null {
  const attr = attrs.find(
    (a) =>
      (a as unknown as { shortName: string }).shortName === shortName ||
      a.name === shortName,
  )
  if (!attr) return null
  return (attr.value as string) ?? null
}

/**
 * Busca el DNI/CIF del titular en el subject del certificado.
 * En certificados españoles (FNMT), el DNI/CIF puede estar en:
 * - OID: 2.5.4.5 (serialNumber del subject)
 * - shortName: serialName, SERIALNUMBER, SN
 */
function extraerDniCif(attrs: forge.pki.CertificateField[]): string {
  const porOid = attrs.find(
    (a) => (a as unknown as { type: string }).type === '2.5.4.5',
  )
  if (porOid?.value) return porOid.value as string

  return (
    obtenerAtributo(attrs, 'serialName') ??
    obtenerAtributo(attrs, 'SERIALNUMBER') ??
    obtenerAtributo(attrs, 'SN') ??
    'Sin DNI/CIF'
  )
}

/**
 * Lee y parsea un archivo P12/PFX del filesystem.
 * Extrae metadatos del certificado X.509 con node-forge.
 */
export function leerCertificadoP12(
  ruta: string,
  password: string,
): CertificadoLocal {
  const buffer = readFileSync(ruta)
  const derString = buffer.toString('binary')
  const asn1 = forge.asn1.fromDer(derString)
  const p12 = forge.pkcs12.pkcs12FromAsn1(asn1, password)

  const certBags = p12.getBags({ bagType: forge.pki.oids.certBag })
  const listaBags = certBags[forge.pki.oids.certBag]

  if (!listaBags || listaBags.length === 0) {
    throw new Error('No se encontro certificado en el archivo P12/PFX')
  }

  const cert = listaBags[0]?.cert
  if (!cert) {
    throw new Error('No se pudo leer el certificado del archivo P12/PFX')
  }

  const attrsSubject = cert.subject.attributes
  const attrsEmisor = cert.issuer.attributes

  return {
    ruta,
    nombreTitular: obtenerAtributo(attrsSubject, 'CN') ?? 'Sin nombre',
    dniCif: extraerDniCif(attrsSubject),
    emisor:
      obtenerAtributo(attrsEmisor, 'CN') ??
      obtenerAtributo(attrsEmisor, 'O'),
    organizacion: obtenerAtributo(attrsSubject, 'O'),
    numeroSerie: cert.serialNumber ?? null,
    fechaExpedicion: cert.validity.notBefore?.toISOString() ?? null,
    fechaVencimiento: cert.validity.notAfter.toISOString(),
    instaladoEnWindows: false,
  }
}

/**
 * Lee buffer P12/PFX en memoria sin acceder al filesystem.
 * Util para watcher donde ya tenemos el buffer.
 */
export function leerCertificadoDesdeBuffer(
  buffer: Buffer,
  ruta: string,
  password: string,
): CertificadoLocal {
  const derString = buffer.toString('binary')
  const asn1 = forge.asn1.fromDer(derString)
  const p12 = forge.pkcs12.pkcs12FromAsn1(asn1, password)

  const certBags = p12.getBags({ bagType: forge.pki.oids.certBag })
  const listaBags = certBags[forge.pki.oids.certBag]

  if (!listaBags || listaBags.length === 0) {
    throw new Error('No se encontro certificado en el archivo P12/PFX')
  }

  const cert = listaBags[0]?.cert
  if (!cert) {
    throw new Error('No se pudo leer el certificado del archivo P12/PFX')
  }

  const attrsSubject = cert.subject.attributes
  const attrsEmisor = cert.issuer.attributes

  return {
    ruta,
    nombreTitular: obtenerAtributo(attrsSubject, 'CN') ?? 'Sin nombre',
    dniCif: extraerDniCif(attrsSubject),
    emisor:
      obtenerAtributo(attrsEmisor, 'CN') ??
      obtenerAtributo(attrsEmisor, 'O'),
    organizacion: obtenerAtributo(attrsSubject, 'O'),
    numeroSerie: cert.serialNumber ?? null,
    fechaExpedicion: cert.validity.notBefore?.toISOString() ?? null,
    fechaVencimiento: cert.validity.notAfter.toISOString(),
    instaladoEnWindows: false,
  }
}
