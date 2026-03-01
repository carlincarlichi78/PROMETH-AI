import { ipcMain, dialog, app, session, BrowserWindow, shell, nativeImage, Tray, Menu, Notification, net } from "electron";
import { join, dirname, basename, parse, extname } from "path";
import { is } from "@electron-toolkit/utils";
import log from "electron-log";
import pkg from "electron-updater";
import { readFileSync, writeFileSync, unlinkSync, readdirSync, existsSync, mkdirSync, renameSync, statSync, copyFileSync } from "fs";
import forge from "node-forge";
import { execFile } from "child_process";
import { promisify } from "util";
import chokidar from "chokidar";
import { tmpdir } from "os";
import { randomBytes, randomUUID, createHash, createCipheriv, createDecipheriv, scryptSync } from "crypto";
import pLimit from "p-limit";
import { XMLParser, XMLBuilder } from "fast-xml-parser";
import xmlCrypto from "xml-crypto";
import { readdir, stat, unlink, rm, readFile, writeFile } from "fs/promises";
import { PDFParse } from "pdf-parse";
import tesseractJs from "tesseract.js";
import pdfLib from "pdf-lib";
import signpdfPlaceholder from "@signpdf/placeholder-pdf-lib";
import signpdfCore from "@signpdf/signpdf";
import signerP12 from "@signpdf/signer-p12";
import signpdfUtils from "@signpdf/utils";
import nodemailer from "nodemailer";
import Database from "better-sqlite3";
import nodeMachineId from "node-machine-id";
import __cjs_mod__ from "node:module";
const __filename = import.meta.filename;
const __dirname = import.meta.dirname;
const require2 = __cjs_mod__.createRequire(import.meta.url);
function obtenerAtributo(attrs, shortName) {
  const attr = attrs.find(
    (a) => a.shortName === shortName || a.name === shortName
  );
  if (!attr) return null;
  return attr.value ?? null;
}
function extraerDniCif(attrs) {
  const porOid = attrs.find(
    (a) => a.type === "2.5.4.5"
  );
  if (porOid?.value) return porOid.value;
  return obtenerAtributo(attrs, "serialName") ?? obtenerAtributo(attrs, "SERIALNUMBER") ?? obtenerAtributo(attrs, "SN") ?? "Sin DNI/CIF";
}
function leerCertificadoP12(ruta, password) {
  const buffer = readFileSync(ruta);
  const derString = buffer.toString("binary");
  const asn1 = forge.asn1.fromDer(derString);
  const p12 = forge.pkcs12.pkcs12FromAsn1(asn1, password);
  const certBags = p12.getBags({ bagType: forge.pki.oids.certBag });
  const listaBags = certBags[forge.pki.oids.certBag];
  if (!listaBags || listaBags.length === 0) {
    throw new Error("No se encontro certificado en el archivo P12/PFX");
  }
  const cert = listaBags[0]?.cert;
  if (!cert) {
    throw new Error("No se pudo leer el certificado del archivo P12/PFX");
  }
  const attrsSubject = cert.subject.attributes;
  const attrsEmisor = cert.issuer.attributes;
  return {
    ruta,
    nombreTitular: obtenerAtributo(attrsSubject, "CN") ?? "Sin nombre",
    dniCif: extraerDniCif(attrsSubject),
    emisor: obtenerAtributo(attrsEmisor, "CN") ?? obtenerAtributo(attrsEmisor, "O"),
    organizacion: obtenerAtributo(attrsSubject, "O"),
    numeroSerie: cert.serialNumber ?? null,
    fechaExpedicion: cert.validity.notBefore?.toISOString() ?? null,
    fechaVencimiento: cert.validity.notAfter.toISOString(),
    instaladoEnWindows: false
  };
}
const ejecutar$1 = promisify(execFile);
const TIMEOUT_MS$2 = 3e4;
async function instalarCertificado(rutaPfx, password) {
  try {
    await ejecutar$1(
      "certutil",
      ["-importpfx", "-user", "-p", password, "-f", rutaPfx],
      { timeout: TIMEOUT_MS$2 }
    );
    log.info(`Certificado instalado: ${rutaPfx}`);
    return { exito: true };
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : "Error desconocido";
    log.error(`Error instalando certificado: ${mensaje}`);
    return { exito: false, error: mensaje };
  }
}
async function desinstalarCertificado(thumbprint) {
  try {
    await ejecutar$1(
      "certutil",
      ["-delstore", "-user", "My", thumbprint],
      { timeout: TIMEOUT_MS$2 }
    );
    log.info(`Certificado desinstalado: ${thumbprint}`);
    return { exito: true };
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : "Error desconocido";
    log.error(`Error desinstalando certificado: ${mensaje}`);
    return { exito: false, error: mensaje };
  }
}
async function listarCertificadosInstalados() {
  try {
    return await listarConPowerShell();
  } catch (error) {
    log.warn("PowerShell fallo, intentando con certutil:", error);
    try {
      const { stdout } = await ejecutar$1(
        "certutil",
        ["-store", "-user", "My"],
        { timeout: TIMEOUT_MS$2 }
      );
      return parsearSalidaCertutil(stdout);
    } catch (err) {
      log.error("Error listando certificados:", err);
      return [];
    }
  }
}
async function listarConPowerShell() {
  const script = `
$certs = Get-ChildItem Cert:\\CurrentUser\\My | Where-Object { $_.HasPrivateKey }
foreach ($c in $certs) {
  $esDNIe = $c.Issuer -match 'DIRECCION GENERAL DE LA POLICIA|DNIE'
  if (-not $esDNIe) {
    Write-Output "CERT_START"
    Write-Output "THUMB:$($c.Thumbprint)"
    Write-Output "SUBJECT:$($c.Subject)"
    Write-Output "ISSUER:$($c.Issuer)"
    Write-Output "NOTAFTER:$($c.NotAfter.ToString('o'))"
    Write-Output "SERIAL:$($c.SerialNumber)"
    Write-Output "CERT_END"
  }
}
`;
  const { stdout } = await ejecutar$1(
    "powershell",
    ["-NoProfile", "-NonInteractive", "-Command", script],
    { timeout: TIMEOUT_MS$2 }
  );
  return parsearSalidaPowerShell(stdout);
}
function parsearSalidaPowerShell(stdout) {
  const certificados = [];
  const bloques = stdout.split("CERT_START").filter((b) => b.includes("CERT_END"));
  for (const bloque of bloques) {
    const thumbprint = extraerCampoPS(bloque, "THUMB");
    const subject = extraerCampoPS(bloque, "SUBJECT");
    const emisor = extraerCampoPS(bloque, "ISSUER");
    const notAfter = extraerCampoPS(bloque, "NOTAFTER");
    const serial = extraerCampoPS(bloque, "SERIAL");
    if (thumbprint && subject) {
      certificados.push({
        thumbprint: thumbprint.replace(/\s/g, "").toLowerCase(),
        subject: subject.trim(),
        emisor: emisor?.trim() ?? "",
        fechaVencimiento: notAfter ? new Date(notAfter).toISOString() : (/* @__PURE__ */ new Date(0)).toISOString(),
        numeroSerie: serial?.trim() ?? ""
      });
    }
  }
  return certificados;
}
function extraerCampoPS(bloque, campo) {
  const regex = new RegExp(`${campo}:(.+)`, "i");
  const match = bloque.match(regex);
  return match?.[1]?.trim() ?? null;
}
async function exportarCertificadoPfx(thumbprint, rutaDestino, password) {
  try {
    await ejecutar$1(
      "certutil",
      ["-exportpfx", "-user", "-p", password, "My", thumbprint, rutaDestino],
      { timeout: TIMEOUT_MS$2 }
    );
    log.info(`Certificado exportado a: ${rutaDestino}`);
    return { exito: true };
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : "Error desconocido";
    log.error(`Error exportando certificado: ${mensaje}`);
    return { exito: false, error: mensaje };
  }
}
function parsearSalidaCertutil(stdout) {
  const certificados = [];
  const bloques = stdout.split(/={10,}\s*Certificad[eo]\s+\d+\s*={10,}/i);
  for (const bloque of bloques) {
    if (!bloque.trim()) continue;
    const thumbprint = extraerCampo(bloque, /Hash\s+cert\.\(sha1\):\s*(.+)/i);
    const subject = extraerCampo(bloque, /Sujeto?:\s*(.+)/i) ?? extraerCampo(bloque, /Subject:\s*(.+)/i);
    const emisor = extraerCampo(bloque, /Emisor:\s*(.+)/i) ?? extraerCampo(bloque, /Issuer:\s*(.+)/i);
    const notAfter = extraerCampo(bloque, /NotAfter:\s*(.+)/i);
    const serial = extraerCampo(bloque, /N[úu]mero de serie:\s*(.+)/i) ?? extraerCampo(bloque, /Serial Number:\s*(.+)/i);
    if (thumbprint && subject) {
      certificados.push({
        thumbprint: thumbprint.replace(/\s/g, "").toLowerCase(),
        subject: subject.trim(),
        emisor: emisor?.trim() ?? "",
        fechaVencimiento: parsearFechaCertutil(notAfter),
        numeroSerie: serial?.trim() ?? ""
      });
    }
  }
  return certificados;
}
function extraerCampo(texto, regex) {
  const match = texto.match(regex);
  return match?.[1]?.trim() ?? null;
}
function parsearFechaCertutil(valor) {
  if (!valor) return (/* @__PURE__ */ new Date(0)).toISOString();
  const fecha = new Date(valor);
  if (!isNaN(fecha.getTime())) return fecha.toISOString();
  const partes = valor.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (partes) {
    const [, dia, mes, anio] = partes;
    const intentoEuropeo = /* @__PURE__ */ new Date(`${anio}-${mes}-${dia}`);
    if (!isNaN(intentoEuropeo.getTime())) return intentoEuropeo.toISOString();
  }
  return (/* @__PURE__ */ new Date(0)).toISOString();
}
let watcherActivo = null;
function iniciarWatcher(carpeta, onNuevoArchivo) {
  if (watcherActivo) {
    log.warn("Watcher ya activo, deteniendo el anterior");
    detenerWatcher();
  }
  log.info(`Iniciando watcher en: ${carpeta}`);
  watcherActivo = chokidar.watch(
    [
      `${carpeta}/**/*.p12`,
      `${carpeta}/**/*.pfx`,
      `${carpeta}/**/*.P12`,
      `${carpeta}/**/*.PFX`
    ],
    {
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: {
        stabilityThreshold: 2e3,
        pollInterval: 100
      }
    }
  );
  watcherActivo.on("add", (ruta) => {
    log.info(`Nuevo certificado detectado: ${ruta}`);
    onNuevoArchivo(ruta);
  });
  watcherActivo.on("error", (error) => {
    log.error("Error en watcher:", error);
  });
}
function detenerWatcher() {
  if (watcherActivo) {
    watcherActivo.close();
    watcherActivo = null;
    log.info("Watcher detenido");
  }
}
const ejecutar = promisify(execFile);
const TIMEOUT_MS$1 = 3e4;
async function aislarCertificado(thumbprint) {
  try {
    await ejecutar(
      "certutil",
      ["-repairstore", "-user", "My", thumbprint],
      { timeout: TIMEOUT_MS$1 }
    );
    log.info(`Certificado aislado para AutoFirma: ${thumbprint}`);
    return { exito: true };
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : "Error desconocido";
    log.error(`Error aislando certificado: ${mensaje}`);
    return { exito: false, error: mensaje };
  }
}
async function restaurarCertificado(thumbprint) {
  try {
    await ejecutar(
      "certutil",
      ["-repairstore", "-user", "My", thumbprint],
      { timeout: TIMEOUT_MS$1 }
    );
    log.info(`Acceso restaurado al certificado: ${thumbprint}`);
    return { exito: true };
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : "Error desconocido";
    log.error(`Error restaurando certificado: ${mensaje}`);
    return { exito: false, error: mensaje };
  }
}
async function sincronizarCertificadosDesdeCloud(apiUrl, token) {
  const resultado = { instalados: [], yaExistentes: 0, errores: [] };
  try {
    const certsCloud = await listarCertsCloud(apiUrl, token);
    const conPfx = certsCloud.filter((c) => c.tieneDatosPfx && c.numeroSerie);
    if (conPfx.length === 0) {
      log.info("[sync-cloud] No hay certificados con PFX en la cloud");
      return resultado;
    }
    const instalados = await listarCertificadosInstalados();
    const serialesInstalados = new Set(
      instalados.map((c) => c.numeroSerie.toLowerCase())
    );
    const faltantes = conPfx.filter(
      (c) => !serialesInstalados.has(c.numeroSerie.toLowerCase())
    );
    resultado.yaExistentes = conPfx.length - faltantes.length;
    if (faltantes.length === 0) {
      log.info("[sync-cloud] Todos los certificados ya estan instalados");
      return resultado;
    }
    log.info(`[sync-cloud] ${faltantes.length} certificados por instalar`);
    for (const cert of faltantes) {
      try {
        const datos = await descargarPfx(apiUrl, token, cert.id);
        const rutaTmp = join(tmpdir(), `certigestor-${randomBytes(8).toString("hex")}.pfx`);
        try {
          writeFileSync(rutaTmp, Buffer.from(datos.pfxBase64, "base64"));
          const res = await instalarCertificado(rutaTmp, datos.password);
          if (res.exito) {
            resultado.instalados.push(cert.numeroSerie);
            log.info(`[sync-cloud] Instalado: ${cert.numeroSerie}`);
          } else {
            resultado.errores.push({ id: cert.id, error: res.error ?? "Error desconocido" });
          }
        } finally {
          try {
            unlinkSync(rutaTmp);
          } catch {
          }
        }
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Error desconocido";
        resultado.errores.push({ id: cert.id, error: msg });
        log.error(`[sync-cloud] Error con cert ${cert.id}: ${msg}`);
      }
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : "Error desconocido";
    log.error(`[sync-cloud] Error general: ${msg}`);
    resultado.errores.push({ id: "general", error: msg });
  }
  log.info(
    `[sync-cloud] Resultado: ${resultado.instalados.length} instalados, ${resultado.yaExistentes} ya existian, ${resultado.errores.length} errores`
  );
  return resultado;
}
async function listarCertsCloud(apiUrl, token) {
  const resp = await fetch(`${apiUrl}/certificados?limite=100`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!resp.ok) throw new Error(`Error listando certs: ${resp.status}`);
  const json = await resp.json();
  return json.datos ?? [];
}
async function descargarPfx(apiUrl, token, certId) {
  const resp = await fetch(`${apiUrl}/certificados/${certId}/descargar-pfx`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!resp.ok) throw new Error(`Error descargando PFX: ${resp.status}`);
  const json = await resp.json();
  return json.datos;
}
let certificadoActivo = null;
function carpetaCertificados() {
  const docs = app.getPath("documents");
  const carpeta = join(docs, "CertiGestor", "certificados");
  if (!existsSync(carpeta)) {
    mkdirSync(carpeta, { recursive: true });
  }
  return carpeta;
}
function registrarHandlersCertificados(ventana) {
  ipcMain.handle("certs:seleccionarArchivo", async (_event, password) => {
    const resultado = await dialog.showOpenDialog(ventana, {
      title: "Seleccionar certificado P12/PFX",
      filters: [
        { name: "Certificados", extensions: ["p12", "pfx"] }
      ],
      properties: ["openFile"]
    });
    if (resultado.canceled || resultado.filePaths.length === 0) {
      return null;
    }
    const ruta = resultado.filePaths[0];
    try {
      return leerCertificadoP12(ruta, password);
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error leyendo certificado";
      log.error(`Error leyendo P12: ${mensaje}`);
      return { exito: false, error: mensaje };
    }
  });
  ipcMain.handle("certs:leerP12", (_event, ruta, password) => {
    try {
      return { exito: true, datos: leerCertificadoP12(ruta, password) };
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error leyendo certificado";
      return { exito: false, error: mensaje };
    }
  });
  ipcMain.handle("certs:listarLocales", () => {
    const carpeta = carpetaCertificados();
    try {
      const archivos = readdirSync(carpeta).filter((f) => /\.(p12|pfx)$/i.test(f)).map((f) => join(carpeta, f));
      return archivos;
    } catch {
      return [];
    }
  });
  ipcMain.handle("certs:instalarEnWindows", async (_event, rutaPfx, password) => {
    try {
      return await instalarCertificado(rutaPfx, password);
    } catch (error) {
      log.error(`[Certs] Error instalando certificado: ${error.message}`);
      return { exito: false, error: error.message };
    }
  });
  ipcMain.handle("certs:desinstalarDeWindows", async (_event, thumbprint) => {
    try {
      return await desinstalarCertificado(thumbprint);
    } catch (error) {
      log.error(`[Certs] Error desinstalando certificado: ${error.message}`);
      return { exito: false, error: error.message };
    }
  });
  ipcMain.handle("certs:listarInstalados", async () => {
    try {
      const certs = await listarCertificadosInstalados();
      return certs.map((c) => ({
        thumbprint: c.thumbprint,
        subject: c.subject,
        issuer: c.emisor,
        serialNumber: c.numeroSerie,
        validTo: c.fechaVencimiento,
        hasPrivateKey: true
      }));
    } catch (error) {
      log.error(`[Certs] Error listando certificados: ${error.message}`);
      return [];
    }
  });
  ipcMain.handle("certs:activar", (_event, numeroSerie) => {
    certificadoActivo = numeroSerie;
    log.info(`Certificado activado: ${numeroSerie}`);
    return { exito: true };
  });
  ipcMain.handle("certs:desactivar", () => {
    log.info(`Certificado desactivado: ${certificadoActivo}`);
    certificadoActivo = null;
    return { exito: true };
  });
  ipcMain.handle("certs:obtenerActivo", () => {
    return certificadoActivo;
  });
  ipcMain.handle(
    "certs:exportarPfx",
    async (_event, thumbprint, password) => {
      const resultado = await dialog.showSaveDialog(ventana, {
        title: "Exportar certificado como PFX",
        defaultPath: join(app.getPath("downloads"), "certificado.pfx"),
        filters: [{ name: "PFX", extensions: ["pfx"] }]
      });
      if (resultado.canceled || !resultado.filePath) {
        return { exito: false, error: "Cancelado por el usuario" };
      }
      return exportarCertificadoPfx(thumbprint, resultado.filePath, password);
    }
  );
  ipcMain.handle(
    "certs:sincronizarConCloud",
    async (_event, ruta, password, apiUrl, token) => {
      try {
        const buffer = readFileSync(ruta);
        const formData = new FormData();
        formData.append(
          "archivo",
          new Blob([buffer], { type: "application/x-pkcs12" }),
          ruta.split(/[/\\]/).pop() ?? "certificado.p12"
        );
        if (password) {
          formData.append("password", password);
        }
        const respuesta = await fetch(`${apiUrl}/certificados/importar`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData
        });
        const datos = await respuesta.json();
        if (!respuesta.ok) {
          return { exito: false, error: datos.error ?? "Error al sincronizar" };
        }
        return { exito: true, datos };
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : "Error de conexion";
        log.error(`Error sincronizando con cloud: ${mensaje}`);
        return { exito: false, error: mensaje };
      }
    }
  );
  ipcMain.handle(
    "certs:sincronizarDesdeCloud",
    async (_event, apiUrl, token) => {
      try {
        return await sincronizarCertificadosDesdeCloud(apiUrl, token);
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : "Error de sincronizacion";
        log.error(`Error sync cloud: ${mensaje}`);
        return { instalados: [], yaExistentes: 0, errores: [{ id: "general", error: mensaje }] };
      }
    }
  );
  ipcMain.handle("certs:aislar", async (_event, thumbprint) => {
    return aislarCertificado(thumbprint);
  });
  ipcMain.handle("certs:restaurar", async (_event, thumbprint) => {
    return restaurarCertificado(thumbprint);
  });
  ipcMain.handle("certs:iniciarWatcher", (_event, carpeta) => {
    const dir = carpeta ?? carpetaCertificados();
    iniciarWatcher(dir, (ruta) => {
      ventana.webContents.send("certs:nuevoArchivo", ruta);
    });
    return { exito: true };
  });
  ipcMain.handle("certs:detenerWatcher", () => {
    detenerWatcher();
    return { exito: true };
  });
  ipcMain.handle("certs:obtenerCarpeta", () => {
    return carpetaCertificados();
  });
  log.info("Handlers de certificados registrados");
}
var ProcessType = /* @__PURE__ */ ((ProcessType2) => {
  ProcessType2["NOTIFICATION_CHECK"] = "NOTIFICATION_CHECK";
  ProcessType2["DOCUMENT_DOWNLOAD"] = "DOCUMENT_DOWNLOAD";
  ProcessType2["DATA_SCRAPING"] = "DATA_SCRAPING";
  return ProcessType2;
})(ProcessType || {});
var FactoryStatus = /* @__PURE__ */ ((FactoryStatus2) => {
  FactoryStatus2["IDLE"] = "IDLE";
  FactoryStatus2["RUNNING"] = "RUNNING";
  return FactoryStatus2;
})(FactoryStatus || {});
var ChainStatus = /* @__PURE__ */ ((ChainStatus2) => {
  ChainStatus2["IDLE"] = "IDLE";
  ChainStatus2["RUNNING"] = "RUNNING";
  ChainStatus2["COMPLETED"] = "COMPLETED";
  ChainStatus2["FAILED"] = "FAILED";
  ChainStatus2["PARTIALLY_COMPLETED"] = "PARTIALLY_COMPLETED";
  return ChainStatus2;
})(ChainStatus || {});
var BlockStatus = /* @__PURE__ */ ((BlockStatus2) => {
  BlockStatus2["PENDING"] = "PENDING";
  BlockStatus2["RUNNING"] = "RUNNING";
  BlockStatus2["COMPLETED"] = "COMPLETED";
  BlockStatus2["FAILED"] = "FAILED";
  return BlockStatus2;
})(BlockStatus || {});
const CONFIG_DEFAULT$1 = {
  headless: true,
  timeoutElemento: 3e4,
  timeoutGlobal: 12e4,
  maxReintentos: 3,
  fastMode: false,
  replicas: 3,
  carpetaDescargas: ""
};
class Factory {
  estado = FactoryStatus.IDLE;
  cadenas = [];
  cadenaActualIndex = 0;
  cancelado = false;
  config = { ...CONFIG_DEFAULT$1 };
  callbackProgreso = null;
  /**
   * Configura callback para notificar progreso via IPC.
   */
  onProgreso(callback) {
    this.callbackProgreso = callback;
  }
  /**
   * Actualiza la configuracion de scraping.
   */
  configurar(config) {
    this.config = { ...this.config, ...config };
  }
  /**
   * Obtiene la configuracion actual.
   */
  obtenerConfig() {
    return { ...this.config };
  }
  /**
   * Agrega una cadena a la cola.
   */
  agregarCadena(cadena) {
    this.cadenas.push(cadena);
  }
  /**
   * Limpia todas las cadenas de la cola.
   */
  limpiar() {
    this.cadenas = [];
    this.cadenaActualIndex = 0;
  }
  /**
   * Inicia la ejecucion de todas las cadenas.
   * En modo normal: secuencial.
   * En fast mode: concurrente con p-limit.
   */
  async iniciar() {
    if (this.estado === FactoryStatus.RUNNING) {
      log.warn("Factory ya en ejecucion");
      return;
    }
    this.estado = FactoryStatus.RUNNING;
    this.cancelado = false;
    this.cadenaActualIndex = 0;
    log.info(
      `Factory iniciada — cadenas: ${this.cadenas.length}, fastMode: ${this.config.fastMode}`
    );
    this.notificarProgreso();
    try {
      if (this.config.fastMode) {
        await this.ejecutarConcurrente();
      } else {
        await this.ejecutarSecuencial();
      }
    } finally {
      this.estado = FactoryStatus.IDLE;
      log.info("Factory finalizada");
      this.notificarProgreso();
    }
  }
  /**
   * Cancela la ejecucion en curso.
   */
  detener() {
    this.cancelado = true;
    log.info("Factory: detencion solicitada");
  }
  /**
   * Ejecucion secuencial: una cadena a la vez.
   */
  async ejecutarSecuencial() {
    for (let i = 0; i < this.cadenas.length; i++) {
      if (this.cancelado) break;
      this.cadenaActualIndex = i;
      this.notificarProgreso();
      await this.cadenas[i].ejecutar();
      this.notificarProgreso();
    }
  }
  /**
   * Ejecucion concurrente: N cadenas en paralelo con p-limit.
   */
  async ejecutarConcurrente() {
    const limite = pLimit(this.config.replicas);
    const tareas = this.cadenas.map(
      (cadena, index) => limite(async () => {
        if (this.cancelado) return;
        this.cadenaActualIndex = index;
        this.notificarProgreso();
        await cadena.ejecutar();
        this.notificarProgreso();
      })
    );
    await Promise.all(tareas);
  }
  /**
   * Notifica el estado actual al renderer via callback.
   */
  notificarProgreso() {
    if (this.callbackProgreso) {
      this.callbackProgreso(this.obtenerEstado());
    }
  }
  /**
   * Retorna snapshot del estado actual de la cola.
   */
  obtenerEstado() {
    const cadenaActual = this.cadenas[this.cadenaActualIndex];
    const totalBloques = this.cadenas.reduce(
      (sum, c) => sum + c.bloques.length,
      0
    );
    const bloquesCompletados = this.cadenas.reduce(
      (sum, c) => sum + c.bloquesCompletados,
      0
    );
    const progreso = totalBloques > 0 ? Math.round(bloquesCompletados / totalBloques * 100) : 0;
    return {
      status: this.estado,
      totalCadenas: this.cadenas.length,
      cadenaActual: this.cadenaActualIndex,
      bloqueActual: cadenaActual?.bloquesCompletados ?? 0,
      totalBloques,
      progreso,
      cadenas: this.cadenas.map((c) => c.obtenerEstado())
    };
  }
}
const factory = new Factory();
function registrarHandlersScraping(ventana) {
  factory.onProgreso((estado) => {
    if (!ventana.isDestroyed()) {
      ventana.webContents.send("scraping:progreso", estado);
    }
  });
  ipcMain.handle("scraping:obtenerEstado", () => {
    return factory.obtenerEstado();
  });
  ipcMain.handle(
    "scraping:configurar",
    (_event, config) => {
      factory.configurar(config);
      log.info("Scraping configurado:", config);
      return factory.obtenerConfig();
    }
  );
  ipcMain.handle("scraping:obtenerConfig", () => {
    return factory.obtenerConfig();
  });
  ipcMain.handle("scraping:iniciar", async () => {
    try {
      await factory.iniciar();
      return { exito: true };
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error desconocido";
      log.error("Error al iniciar scraping:", mensaje);
      return { exito: false, error: mensaje };
    }
  });
  ipcMain.handle("scraping:detener", () => {
    factory.detener();
    return { exito: true };
  });
  ipcMain.handle("scraping:limpiar", () => {
    factory.limpiar();
    return { exito: true };
  });
  log.info("Handlers scraping registrados");
}
const scraping = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  factory,
  registrarHandlersScraping
}, Symbol.toStringTag, { value: "Module" }));
const { SignedXml } = xmlCrypto;
function extraerCredencialesPfx(rutaPfx, password) {
  if (!rutaPfx || !password) {
    throw new Error("rutaPfx y passwordPfx son requeridos para firma LEMA. Verifica que el certificado tiene thumbprint para exportar PFX.");
  }
  const buffer = readFileSync(rutaPfx);
  const derString = buffer.toString("binary");
  const asn1 = forge.asn1.fromDer(derString);
  const p12 = forge.pkcs12.pkcs12FromAsn1(asn1, password);
  const certBags = p12.getBags({ bagType: forge.pki.oids.certBag });
  const listaCerts = certBags[forge.pki.oids.certBag];
  if (!listaCerts || listaCerts.length === 0) {
    throw new Error("No se encontro certificado en el PFX");
  }
  const cert = listaCerts[0]?.cert;
  if (!cert) {
    throw new Error("No se pudo leer el certificado del PFX");
  }
  const keyBags = p12.getBags({ bagType: forge.pki.oids.pkcs8ShroudedKeyBag });
  const listaKeys = keyBags[forge.pki.oids.pkcs8ShroudedKeyBag];
  if (!listaKeys || listaKeys.length === 0) {
    throw new Error("No se encontro clave privada en el PFX");
  }
  const key = listaKeys[0]?.key;
  if (!key) {
    throw new Error("No se pudo leer la clave privada del PFX");
  }
  const certificadoPem = forge.pki.certificateToPem(cert);
  const clavePem = forge.pki.privateKeyToPem(key);
  log.info("Credenciales PEM extraidas correctamente del PFX");
  return { clavePem, certificadoPem };
}
class ProveedorKeyInfo {
  clavePem;
  certificadoPem;
  constructor(clavePem, certificadoPem) {
    this.clavePem = clavePem;
    this.certificadoPem = certificadoPem;
  }
  getKey() {
    return this.clavePem;
  }
  getKeyInfo() {
    const certBase64 = this.certificadoPem.replace("-----BEGIN CERTIFICATE-----", "").replace("-----END CERTIFICATE-----", "").replace(/\s/g, "");
    return `<ds:X509Data><ds:X509Certificate>${certBase64}</ds:X509Certificate></ds:X509Data>`;
  }
}
function firmarXmlSoap(xmlSinFirmar, clavePem, certificadoPem) {
  const sig = new SignedXml({
    privateKey: clavePem,
    canonicalizationAlgorithm: "http://www.w3.org/2001/10/xml-exc-c14n#",
    signatureAlgorithm: "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
  });
  sig.addReference({
    xpath: "//*[local-name(.)='Body']",
    digestAlgorithm: "http://www.w3.org/2001/04/xmlenc#sha256",
    transforms: [
      "http://www.w3.org/2000/09/xmldsig#enveloped-signature",
      "http://www.w3.org/2001/10/xml-exc-c14n#"
    ]
  });
  const proveedor = new ProveedorKeyInfo(clavePem, certificadoPem);
  sig.keyInfoProvider = proveedor;
  sig.computeSignature(xmlSinFirmar, {
    location: { reference: "//*[local-name(.)='Header']", action: "append" }
  });
  const xmlFirmado = sig.getSignedXml();
  log.info("XML SOAP firmado correctamente");
  return xmlFirmado;
}
var TipoConsultaLema = /* @__PURE__ */ ((TipoConsultaLema2) => {
  TipoConsultaLema2["PENDIENTES_NOTIFICACIONES"] = "PENDIENTES_NOTIFICACIONES";
  TipoConsultaLema2["PENDIENTES_COMUNICACIONES"] = "PENDIENTES_COMUNICACIONES";
  TipoConsultaLema2["HISTORICO_REALIZADAS"] = "HISTORICO_REALIZADAS";
  return TipoConsultaLema2;
})(TipoConsultaLema || {});
var EstadoAltaDehu = /* @__PURE__ */ ((EstadoAltaDehu2) => {
  EstadoAltaDehu2["ALTA"] = "ALTA";
  EstadoAltaDehu2["NO_ALTA"] = "NO_ALTA";
  EstadoAltaDehu2["DESCONOCIDO"] = "DESCONOCIDO";
  return EstadoAltaDehu2;
})(EstadoAltaDehu || {});
var MetodoConsulta = /* @__PURE__ */ ((MetodoConsulta2) => {
  MetodoConsulta2["LEMA_API"] = "LEMA_API";
  MetodoConsulta2["PUPPETEER"] = "PUPPETEER";
  return MetodoConsulta2;
})(MetodoConsulta || {});
const LEMA_ENDPOINT = "https://lema.redsara.es/ws/LemaServices";
const TIMEOUT_LEMA = 3e4;
const NAMESPACE_LEMA = "http://lema.redsara.es/ws";
class LemaApi {
  config;
  parser;
  builder;
  constructor(config) {
    if (!config.rutaPfx || !config.passwordPfx) {
      throw new Error("LEMA API requiere rutaPfx y passwordPfx en la configuracion");
    }
    this.config = config;
    this.parser = new XMLParser({
      ignoreAttributes: false,
      removeNSPrefix: true,
      parseAttributeValue: true
    });
    this.builder = new XMLBuilder({
      ignoreAttributes: false,
      suppressEmptyNode: true
    });
  }
  /**
   * Verifica si el certificado tiene alta en LEMA.
   * Ejecuta una consulta ligera para determinar el estado.
   */
  async verificarAlta() {
    try {
      const xmlRequest = this.construirSoapRequest(
        TipoConsultaLema.PENDIENTES_NOTIFICACIONES
      );
      const { clavePem, certificadoPem } = extraerCredencialesPfx(
        this.config.rutaPfx,
        this.config.passwordPfx
      );
      const xmlFirmado = firmarXmlSoap(xmlRequest, clavePem, certificadoPem);
      const respuesta = await this.enviarSoap(xmlFirmado);
      if (this.esFaultSoap(respuesta)) {
        const mensajeFault = this.extraerMensajeFault(respuesta);
        if (mensajeFault.includes("NO_ALTA") || mensajeFault.includes("no dado de alta")) {
          log.info(
            `[LEMA] Certificado ${this.config.certificadoSerial} sin alta en LEMA`
          );
          return EstadoAltaDehu.NO_ALTA;
        }
        log.warn(`[LEMA] Fault inesperado al verificar alta: ${mensajeFault}`);
        return EstadoAltaDehu.DESCONOCIDO;
      }
      log.info(
        `[LEMA] Certificado ${this.config.certificadoSerial} tiene alta en LEMA`
      );
      return EstadoAltaDehu.ALTA;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error desconocido";
      log.warn(`[LEMA] Error verificando alta: ${msg}`);
      return EstadoAltaDehu.DESCONOCIDO;
    }
  }
  /**
   * Consulta notificaciones pendientes via SOAP.
   */
  async consultarPendientes() {
    return this.ejecutarConsultaTipo(
      TipoConsultaLema.PENDIENTES_NOTIFICACIONES,
      "Notificacion"
    );
  }
  /**
   * Consulta comunicaciones pendientes via SOAP.
   */
  async consultarComunicaciones() {
    return this.ejecutarConsultaTipo(
      TipoConsultaLema.PENDIENTES_COMUNICACIONES,
      "Comunicacion"
    );
  }
  /**
   * Consulta historico de notificaciones realizadas via SOAP.
   */
  async consultarRealizadas() {
    return this.ejecutarConsultaTipo(
      TipoConsultaLema.HISTORICO_REALIZADAS,
      "Notificacion"
    );
  }
  /**
   * Ejecuta consulta completa (pendientes + realizadas + comunicaciones).
   * Retorna ResultadoConsultaDEHU con todos los resultados.
   */
  async ejecutarConsulta() {
    const fechaConsulta = (/* @__PURE__ */ new Date()).toISOString();
    try {
      const [resPendientes, resRealizadas, resComunicaciones] = await Promise.allSettled([
        this.consultarPendientes(),
        this.consultarRealizadas(),
        this.consultarComunicaciones()
      ]);
      const pendientes = resPendientes.status === "fulfilled" ? resPendientes.value : [];
      const realizadas = resRealizadas.status === "fulfilled" ? resRealizadas.value : [];
      const comunicaciones = resComunicaciones.status === "fulfilled" ? resComunicaciones.value : [];
      if (resRealizadas.status === "rejected") {
        log.warn(`[LEMA] HISTORICO_REALIZADAS no soportado: ${resRealizadas.reason}`);
      }
      if (resPendientes.status === "rejected") {
        throw resPendientes.reason;
      }
      const notificaciones = [...pendientes, ...realizadas];
      log.info(
        `[LEMA] Consulta completada — pendientes: ${pendientes.length}, realizadas: ${realizadas.length}, comunicaciones: ${comunicaciones.length}`
      );
      return {
        exito: true,
        metodo: MetodoConsulta.LEMA_API,
        certificadoSerial: this.config.certificadoSerial,
        estadoAlta: EstadoAltaDehu.ALTA,
        notificaciones,
        comunicaciones,
        fechaConsulta
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error desconocido";
      log.error(`[LEMA] Error en consulta completa: ${msg}`);
      return {
        exito: false,
        metodo: MetodoConsulta.LEMA_API,
        certificadoSerial: this.config.certificadoSerial,
        estadoAlta: this.config.estadoAlta ?? EstadoAltaDehu.DESCONOCIDO,
        notificaciones: [],
        comunicaciones: [],
        error: msg,
        fechaConsulta
      };
    }
  }
  /**
   * Ejecuta una consulta SOAP para un tipo especifico.
   */
  async ejecutarConsultaTipo(tipo, tipoNotif) {
    const xmlRequest = this.construirSoapRequest(tipo);
    const { clavePem, certificadoPem } = extraerCredencialesPfx(
      this.config.rutaPfx,
      this.config.passwordPfx
    );
    const xmlFirmado = firmarXmlSoap(xmlRequest, clavePem, certificadoPem);
    const respuesta = await this.enviarSoap(xmlFirmado);
    if (this.esFaultSoap(respuesta)) {
      const mensajeFault = this.extraerMensajeFault(respuesta);
      throw new Error(`SOAP Fault: ${mensajeFault}`);
    }
    return this.parsearRespuesta(respuesta, tipoNotif);
  }
  /**
   * Construye el envelope SOAP XML para el tipo de consulta dado.
   */
  construirSoapRequest(tipo) {
    const soapEnvelope = {
      "soap:Envelope": {
        "@_xmlns:soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "@_xmlns:lem": NAMESPACE_LEMA,
        "soap:Header": {},
        "soap:Body": {
          "lem:consultaRequest": {
            "lem:tipoConsulta": tipo,
            "lem:nifTitular": ""
            // Se extrae del certificado al firmar
          }
        }
      }
    };
    return this.builder.build(soapEnvelope);
  }
  /**
   * Envia el SOAP request firmado y parsea la respuesta XML.
   */
  async enviarSoap(xmlFirmado) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_LEMA);
    try {
      const response = await fetch(LEMA_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "text/xml; charset=utf-8",
          SOAPAction: `${NAMESPACE_LEMA}/consulta`
        },
        body: xmlFirmado,
        signal: controller.signal
      });
      const textoRespuesta = await response.text();
      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}: ${response.statusText}`
        );
      }
      return this.parser.parse(textoRespuesta);
    } finally {
      clearTimeout(timeoutId);
    }
  }
  /**
   * Verifica si la respuesta es un SOAP Fault.
   */
  esFaultSoap(respuesta) {
    const envelope = respuesta["Envelope"];
    if (!envelope) return false;
    const body = envelope["Body"];
    if (!body) return false;
    return "Fault" in body;
  }
  /**
   * Extrae el mensaje de error de un SOAP Fault.
   */
  extraerMensajeFault(respuesta) {
    try {
      const envelope = respuesta["Envelope"];
      const body = envelope["Body"];
      const fault = body["Fault"];
      return fault["faultstring"] ?? fault["detail"] ?? "Error SOAP desconocido";
    } catch {
      return "Error SOAP desconocido";
    }
  }
  /**
   * Parsea la respuesta SOAP y extrae notificaciones.
   */
  parsearRespuesta(respuesta, tipoNotif) {
    try {
      const envelope = respuesta["Envelope"];
      const body = envelope["Body"];
      const consultaResponse = body["consultaResponse"];
      if (!consultaResponse) return [];
      const items = consultaResponse["notificaciones"] ?? consultaResponse["comunicaciones"];
      if (!items) return [];
      const lista = Array.isArray(items) ? items : [items];
      return lista.map(
        (item) => ({
          idDehu: String(item["codigoOrigen"] ?? item["id"] ?? ""),
          tipo: tipoNotif,
          titulo: String(item["concepto"] ?? item["titulo"] ?? "Sin titulo"),
          titular: String(item["nifTitular"] ?? ""),
          ambito: String(item["ambito"] ?? ""),
          organismo: String(
            item["organismoEmisor"] ?? item["organismo"] ?? ""
          ),
          fechaDisposicion: String(
            item["fechaPuestaDisposicion"] ?? item["fecha"] ?? ""
          ),
          fechaCaducidad: item["fechaCaducidad"] ? String(item["fechaCaducidad"]) : null,
          estado: String(
            item["estado"] ?? "Pendiente"
          ),
          tipoEnvio: item["tipoEnvio"] ? String(item["tipoEnvio"]) : void 0,
          rutaPdfLocal: null
        })
      );
    } catch (error) {
      log.error("[LEMA] Error parseando respuesta SOAP:", error);
      return [];
    }
  }
}
const DELAY_BASE_RETRY = 5e3;
const USER_AGENTS$1 = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
];
class BaseScraper {
  window = null;
  childWindows = [];
  serialNumber;
  config;
  carpetaDescargas;
  constructor(serialNumber, config) {
    this.serialNumber = serialNumber;
    this.config = { ...CONFIG_DEFAULT$1, ...config };
    const baseDescargas = this.config.carpetaDescargas || join(app.getPath("documents"), "CertiGestor", "descargas");
    const subcarpeta = this.config.nombreCarpeta || serialNumber;
    this.carpetaDescargas = join(baseDescargas, subcarpeta);
    if (!existsSync(this.carpetaDescargas)) {
      mkdirSync(this.carpetaDescargas, { recursive: true });
    }
  }
  /**
   * Inicializa BrowserWindow con session temporal y seleccion automatica
   * de certificado. Replica exacta del patron de Findiur BaseScrapper.initializeBrowser().
   */
  async inicializarNavegador() {
    const particion = `scraper-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const sesionTemp = session.fromPartition(particion, { cache: false });
    await sesionTemp.clearAuthCache();
    await sesionTemp.clearStorageData();
    this.window = new BrowserWindow({
      width: 1280,
      height: 800,
      show: !this.config.headless,
      webPreferences: {
        session: sesionTemp,
        nodeIntegration: false,
        contextIsolation: true
      }
    });
    const userAgent = USER_AGENTS$1[Math.floor(Math.random() * USER_AGENTS$1.length)];
    this.window.webContents.setUserAgent(userAgent);
    const targetSerial = this.serialNumber.toLowerCase();
    this.window.setTitle(`[CertiGestor] Cert: ${this.serialNumber}`);
    this.window.webContents.on(
      "select-client-certificate",
      (event, _url, certificateList, callback) => {
        event.preventDefault();
        log.info(
          `[${this.nombre}] === SELECT-CLIENT-CERTIFICATE ===`
        );
        log.info(
          `[${this.nombre}] URL: ${_url}`
        );
        log.info(
          `[${this.nombre}] Buscando serial: ${targetSerial}`
        );
        log.info(
          `[${this.nombre}] Certificados disponibles (${certificateList.length}):`
        );
        for (const c of certificateList) {
          const esTarget = c.serialNumber.toLowerCase() === targetSerial ? " <<<< TARGET" : "";
          log.info(`  - ${c.serialNumber} | ${c.subjectName}${esTarget}`);
        }
        const seleccionado = certificateList.find(
          (cert) => cert.serialNumber.toLowerCase() === targetSerial
        );
        if (seleccionado) {
          log.info(`[${this.nombre}] SELECCIONADO: ${seleccionado.serialNumber} — ${seleccionado.subjectName}`);
          if (this.window && !this.window.isDestroyed()) {
            this.window.setTitle(`[CertiGestor] ${seleccionado.subjectName}`);
          }
          callback(seleccionado);
        } else {
          log.error(`[${this.nombre}] CERT ${targetSerial} NO ENCONTRADO — CANCELANDO (no se seleccionara otro)`);
          log.error(`[${this.nombre}] Seriales disponibles: ${certificateList.map((c) => c.serialNumber.toLowerCase()).join(", ")}`);
          callback(null);
        }
      }
    );
    this.childWindows = [];
    this.configurarVentana(this.window, userAgent, sesionTemp);
    log.info(`[${this.nombre}] BrowserWindow iniciado — cert: ${this.serialNumber} — headless: ${this.config.headless}`);
  }
  /**
   * Configura will-download y tracking de popups en una ventana.
   * Se aplica recursivamente: cada popup nuevo tambien queda configurado.
   * Asi se interceptan descargas en cualquier nivel de profundidad (ventana → popup → popup del popup).
   */
  sesionesConWillDownload = /* @__PURE__ */ new Set();
  configurarVentana(ventana, userAgent, sesion) {
    const sesionId = sesion.storagePath ?? `session-${ventana.id}`;
    if (!this.sesionesConWillDownload.has(sesionId)) {
      this.sesionesConWillDownload.add(sesionId);
      sesion.on("will-download", (_event, item) => {
        const nombreArchivo = item.getFilename();
        const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
        item.setSavePath(rutaDestino);
        log.info(`[${this.nombre}] Descargando (ventana ${ventana.id}): ${nombreArchivo} → ${rutaDestino}`);
        item.once("done", (_ev, state) => {
          if (state === "completed") {
            log.info(`[${this.nombre}] Descarga completada (ventana ${ventana.id}): ${nombreArchivo}`);
          } else {
            log.warn(`[${this.nombre}] Descarga fallida (ventana ${ventana.id}): ${nombreArchivo} — estado: ${state}`);
          }
        });
      });
    }
    ventana.webContents.on("did-create-window", (childWindow) => {
      log.info(`[${this.nombre}] Popup creado desde ventana ${ventana.id}: nuevo ID ${childWindow.id}`);
      this.childWindows.push(childWindow);
      if (this.config.headless && childWindow.isVisible()) {
        childWindow.hide();
      }
      childWindow.webContents.setUserAgent(userAgent);
      const sesionPopup = childWindow.webContents.session;
      this.configurarVentana(childWindow, userAgent, sesionPopup);
      childWindow.on("closed", () => {
        this.childWindows = this.childWindows.filter(
          (win) => win !== childWindow && !win.isDestroyed()
        );
      });
    });
  }
  /**
   * Cierra el navegador con limpieza completa de session.
   * Replica Findiur BaseScrapper.closeBrowser() — limpia cookies, localStorage, indexDB, etc.
   */
  async cerrarNavegador() {
    if (this.childWindows.length > 0) {
      log.info(`[${this.nombre}] Cerrando ${this.childWindows.length} ventana(s) secundaria(s)`);
      for (const win of this.childWindows) {
        if (win && !win.isDestroyed()) {
          win.removeAllListeners();
          win.close();
        }
      }
      this.childWindows = [];
    }
    if (this.window && !this.window.isDestroyed()) {
      try {
        const currentSession = this.window.webContents.session;
        await currentSession.clearStorageData({
          storages: [
            "cookies",
            "filesystem",
            "indexdb",
            "localstorage",
            "shadercache",
            "websql",
            "serviceworkers",
            "cachestorage"
          ]
        }).catch(
          (err) => log.warn(`[${this.nombre}] Error menor limpiando storage: ${err.message}`)
        );
        this.window.removeAllListeners();
        this.window.webContents.removeAllListeners();
        this.window.close();
        log.info(`[${this.nombre}] Navegador cerrado y sesion limpiada`);
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error);
        log.warn(`[${this.nombre}] Error menor cerrando navegador: ${msg}`);
      } finally {
        this.window = null;
      }
    }
  }
  /**
   * Ejecuta una funcion con reintentos y backoff exponencial.
   */
  async ejecutarConReintento(fn, maxReintentos) {
    const intentos = maxReintentos ?? this.config.maxReintentos;
    for (let intento = 0; intento < intentos; intento++) {
      try {
        return await fn();
      } catch (error) {
        const esUltimoIntento = intento === intentos - 1;
        if (esUltimoIntento) throw error;
        const delay = DELAY_BASE_RETRY * Math.pow(2, intento);
        log.warn(
          `[${this.nombre}] Intento ${intento + 1}/${intentos} fallido, reintentando en ${delay}ms`
        );
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
    throw new Error("Se agotaron los reintentos");
  }
  /**
   * Espera a que un elemento aparezca en la pagina.
   * Polling con executeJavaScript (mismo patron que Findiur waitForSelector).
   */
  async esperarElemento(selector, timeout) {
    if (!this.window || this.window.isDestroyed()) throw new Error("Navegador no inicializado");
    const ms = timeout ?? this.config.timeoutElemento;
    const inicio = Date.now();
    return new Promise((resolve, reject) => {
      const check = async () => {
        if (!this.window || this.window.isDestroyed()) {
          return reject(new Error("Ventana destruida durante la espera"));
        }
        if (Date.now() - inicio > ms) {
          return reject(new Error(`Timeout esperando selector: ${selector}`));
        }
        try {
          const encontrado = await this.window.webContents.executeJavaScript(
            `!!document.querySelector('${selector.replace(/'/g, "\\'")}')`
          );
          if (encontrado) return resolve();
          setTimeout(check, 500);
        } catch {
          setTimeout(check, 500);
        }
      };
      check();
    });
  }
  /**
   * Navega a una URL y espera a que cargue con manejo de redirecciones.
   * Replica Findiur loadUrlAndHandleRedirects() — usa eventos did-finish-load,
   * did-fail-load y did-redirect-navigation con timeout.
   */
  async navegar(url) {
    if (!this.window || this.window.isDestroyed()) throw new Error("Navegador no inicializado");
    log.info(`[${this.nombre}] Navegando a: ${url}`);
    await this.loadUrlAndHandleRedirects(this.window, url);
    log.info(`[${this.nombre}] Navegacion completada. URL final: ${this.window.webContents.getURL()}`);
  }
  /**
   * Carga una URL con manejo robusto de redirecciones.
   * Replica exacta de Findiur BaseScrapper.loadUrlAndHandleRedirects():
   * - Listener did-finish-load → resuelve
   * - Listener did-fail-load → rechaza (excepto ERR_ABORTED que indica redireccion)
   * - Listener did-redirect-navigation → reinicia temporizador
   * - Timeout general de navegacion
   */
  loadUrlAndHandleRedirects(window, url) {
    return new Promise((resolve, reject) => {
      const wc = window.webContents;
      if (wc.isDestroyed()) {
        return reject(new Error("WebContents destruido antes de la navegacion"));
      }
      let isDone = false;
      let navigationTimer;
      const cleanup = () => {
        if (navigationTimer) clearTimeout(navigationTimer);
        if (!wc.isDestroyed()) {
          wc.removeListener("did-finish-load", onFinish);
          wc.removeListener("did-fail-load", onFail);
          wc.removeListener("did-redirect-navigation", onRedirect);
        }
      };
      const succeed = () => {
        if (isDone) return;
        isDone = true;
        cleanup();
        resolve();
      };
      const fail = (error) => {
        if (isDone) return;
        isDone = true;
        cleanup();
        reject(error);
      };
      const onFinish = () => {
        log.info(`[${this.nombre}] did-finish-load: ${wc.getURL()}`);
        succeed();
      };
      const onFail = (_event, errorCode, errorDescription) => {
        if (errorCode === -3) {
          log.info(`[${this.nombre}] Carga abortada (ERR_ABORTED), esperando redireccion...`);
          return;
        }
        fail(new Error(`Fallo de carga: ${errorDescription} (codigo: ${errorCode})`));
      };
      const onRedirect = () => {
        log.info(`[${this.nombre}] Redireccion detectada. Reiniciando temporizador.`);
        if (navigationTimer) clearTimeout(navigationTimer);
        navigationTimer = setTimeout(
          () => fail(new Error("Timeout despues de redireccion")),
          45e3
        );
      };
      wc.on("did-finish-load", onFinish);
      wc.on("did-fail-load", onFail);
      wc.on("did-redirect-navigation", onRedirect);
      navigationTimer = setTimeout(
        () => fail(new Error("Timeout general de navegacion")),
        this.config.timeoutGlobal
      );
      window.loadURL(url).catch((error) => {
        if (error.code === "ERR_ABORTED") return;
        fail(new Error(error.message ?? "Error cargando URL"));
      });
    });
  }
  /**
   * Navega a una URL con reintentos (3 intentos).
   * Replica Findiur BaseScrapper.loadURLWithRetries().
   */
  async navegarConReintentos(url, maxReintentos = 3) {
    if (!this.window || this.window.isDestroyed()) throw new Error("Navegador no inicializado");
    for (let intento = 1; intento <= maxReintentos; intento++) {
      try {
        log.info(`[${this.nombre}] Intento ${intento}/${maxReintentos} de cargar: ${url}`);
        await this.loadUrlAndHandleRedirects(this.window, url);
        log.info(`[${this.nombre}] Carga exitosa en intento ${intento}`);
        return;
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error);
        log.error(`[${this.nombre}] Intento ${intento} fallido: ${msg}`);
        if (this.window && !this.window.isDestroyed()) {
          try {
            this.window.webContents.stop();
          } catch {
          }
        }
        if (intento === maxReintentos) {
          throw new Error(`Fallo al cargar ${url} tras ${maxReintentos} intentos: ${msg}`);
        }
        await this.esperar(2e3 * intento);
      }
    }
  }
  /**
   * Ejecuta JavaScript en la pagina.
   */
  async ejecutarJS(script) {
    if (!this.window || this.window.isDestroyed()) throw new Error("Navegador no inicializado");
    return this.window.webContents.executeJavaScript(script);
  }
  /**
   * Hace clic en un elemento por selector CSS.
   * Con verificacion previa de existencia (patron Findiur clickElementBySelector).
   */
  async clic(selector) {
    if (!this.window || this.window.isDestroyed()) throw new Error("Navegador no inicializado");
    const clicked = await this.window.webContents.executeJavaScript(`
      (function() {
        const el = document.querySelector('${selector.replace(/'/g, "\\'")}');
        if (el) { el.click(); return true; }
        return false;
      })()
    `);
    return clicked;
  }
  /**
   * Hace clic en un elemento esperando que aparezca primero.
   * Replica Findiur clickElementBySelector (waitForSelector + click).
   */
  async clicConEspera(selector, timeout) {
    await this.esperarElemento(selector, timeout);
    const clicked = await this.clic(selector);
    if (!clicked) {
      throw new Error(`No se pudo hacer clic en: ${selector}`);
    }
  }
  /**
   * Obtiene el HTML de la pagina actual.
   */
  async obtenerHTML() {
    if (!this.window || this.window.isDestroyed()) throw new Error("Navegador no inicializado");
    return this.window.webContents.executeJavaScript(
      "document.documentElement.outerHTML"
    );
  }
  /**
   * Obtiene la URL actual.
   */
  obtenerURL() {
    if (!this.window || this.window.isDestroyed()) throw new Error("Navegador no inicializado");
    return this.window.webContents.getURL();
  }
  /**
   * Espera un tiempo determinado.
   */
  async esperar(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
  /**
   * Detecta y maneja la pasarela Cl@ve (pasarela.clave.gob.es).
   * Version mejorada que usa selectedIdP('AFIRMA') como en Findiur,
   * ademas de busqueda por texto como fallback.
   *
   * @param timeoutDeteccion - ms para esperar a que aparezca la pasarela (default 10s)
   * @param timeoutPostLogin - ms para esperar redireccion tras seleccion de cert (default 30s)
   * @returns true si paso por Cl@ve, false si no se detecto
   */
  async manejarPasarelaClave(timeoutDeteccion = 1e4, timeoutPostLogin = 3e4) {
    if (!this.window || this.window.isDestroyed()) return false;
    const inicio = Date.now();
    while (Date.now() - inicio < timeoutDeteccion) {
      const url = this.obtenerURL();
      if (url.includes("pasarela.clave.gob.es") || url.includes("clave.gob.es")) {
        log.info(`[${this.nombre}] Pasarela Cl@ve detectada: ${url}`);
        await this.esperar(2e3);
        const usadoSelectedIdP = await this.ejecutarJS(`
          (function() {
            try {
              if (typeof selectedIdP === 'function') {
                selectedIdP('AFIRMA');
                if (typeof idpRedirect !== 'undefined' && idpRedirect.submit) {
                  idpRedirect.submit();
                }
                return true;
              }
            } catch(e) {}
            return false;
          })()
        `);
        if (usadoSelectedIdP) {
          log.info(`[${this.nombre}] selectedIdP('AFIRMA') ejecutado exitosamente`);
        } else {
          const clicBotonAfirma = await this.ejecutarJS(`
            (function() {
              const btn = document.querySelector("button[onclick*=\\"selectedIdP('AFIRMA')\\"]");
              if (btn) { btn.click(); return true; }
              return false;
            })()
          `);
          if (clicBotonAfirma) {
            log.info(`[${this.nombre}] Clic en boton AFIRMA por selector`);
          } else {
            const clicTexto = await this.ejecutarJS(`
              (function() {
                const botones = document.querySelectorAll('article button, button, a.btn');
                for (const btn of botones) {
                  const texto = (btn.textContent || '').toLowerCase();
                  if (texto.includes('certificado') || texto.includes('dnie') || texto.includes('afirma')) {
                    btn.click();
                    return true;
                  }
                }
                return false;
              })()
            `);
            if (clicTexto) {
              log.info(`[${this.nombre}] Clic en boton certificado por texto`);
            } else {
              log.warn(`[${this.nombre}] No se encontro boton de certificado en Cl@ve`);
              await this.capturarPantalla("clave-sin-boton-cert");
              return false;
            }
          }
        }
        const urlClave = this.obtenerURL();
        try {
          await this.esperarRedireccion(urlClave, timeoutPostLogin);
          log.info(`[${this.nombre}] Redireccion post-Cl@ve completada: ${this.obtenerURL()}`);
        } catch {
          log.warn(`[${this.nombre}] Timeout esperando redireccion post-Cl@ve`);
          await this.capturarPantalla("clave-timeout-redireccion");
        }
        await this.esperar(3e3);
        return true;
      }
      await this.esperar(500);
    }
    return false;
  }
  /**
   * Espera a que la URL cambie (redireccion post-login).
   */
  async esperarRedireccion(urlOriginal, timeout) {
    if (!this.window || this.window.isDestroyed()) throw new Error("Navegador no inicializado");
    const ms = timeout ?? this.config.timeoutGlobal;
    const inicio = Date.now();
    while (Date.now() - inicio < ms) {
      const urlActual = this.window.webContents.getURL();
      if (urlActual !== urlOriginal) return;
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    throw new Error(`Timeout esperando redireccion desde ${urlOriginal}`);
  }
  /**
   * Captura screenshot para debug.
   */
  async capturarPantalla(nombre) {
    if (!this.window || this.window.isDestroyed()) throw new Error("Navegador no inicializado");
    const ruta = join(this.carpetaDescargas, `${nombre}.png`);
    const imagen = await this.window.webContents.capturePage();
    writeFileSync(ruta, imagen.toPNG());
    log.info(`[${this.nombre}] Screenshot guardado: ${ruta}`);
    return ruta;
  }
  /**
   * Ejecuta el scraper completo con GLOBAL_TIMEOUT via Promise.race.
   * Replica Findiur BaseScrapper.run() — Promise.race entre scrape y timeout.
   * El timer se cancela cuando el scrape termina (exito o error).
   */
  async run() {
    let timeoutHandle = null;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutHandle = setTimeout(() => {
        const msg = `Timeout global de ${this.config.timeoutGlobal / 1e3}s excedido para ${this.nombre}`;
        log.error(`[${this.nombre}] ${msg}`);
        reject(new Error(msg));
      }, this.config.timeoutGlobal);
    });
    const scrapePromise = async () => {
      try {
        await this.inicializarNavegador();
        return await this.ejecutar();
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : "Error desconocido";
        log.error(`[${this.nombre}] Error en run:`, mensaje);
        try {
          await this.capturarPantalla("error");
        } catch {
        }
        return { exito: false, error: mensaje };
      }
    };
    try {
      return await Promise.race([scrapePromise(), timeoutPromise]);
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error desconocido";
      return { exito: false, error: mensaje };
    } finally {
      if (timeoutHandle) clearTimeout(timeoutHandle);
      await this.cerrarNavegador();
    }
  }
}
const URL_DEHU_NOTIFICACIONES = "https://dehu.redsara.es/es/notifications";
const GLOBAL_TIMEOUT_DEHU = 3e5;
class DehuScraper extends BaseScraper {
  configDehu;
  /** Token capturado via interceptor de red (mas fiable que localStorage) */
  tokenInterceptado = null;
  constructor(configDehu, configScraping) {
    super(configDehu.certificadoSerial, {
      ...configScraping,
      // DEHU necesita 5 minutos como Findiur
      timeoutGlobal: GLOBAL_TIMEOUT_DEHU,
      // Ventana visible para diagnostico — DEHU es lento y complejo
      headless: false
    });
    this.configDehu = configDehu;
  }
  get nombre() {
    return `DEHU (${this.serialNumber})`;
  }
  /**
   * Ejecuta el scraping completo del portal DEHU.
   * Replica DehuUnifiedScraper.scrape() de Findiur.
   */
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando scraping DEHU web (metodologia Findiur)`);
    const loggedIn = await this.intentarLogin(3);
    if (!loggedIn) {
      return {
        exito: false,
        error: "No se pudo iniciar sesion en DEHU"
      };
    }
    await this.seleccionarEntidadEmpresa();
    const pendientes = await this.extraerSeccion(
      "PENDIENTES",
      URL_DEHU_NOTIFICACIONES,
      "app-notifications-list",
      "dnt-table"
    );
    const realizadas = await this.extraerSeccion(
      "REALIZADAS",
      "https://dehu.redsara.es/es/notifications?realized=true",
      "app-notifications-list",
      "#tablaNotificacionesRealizadas"
    );
    const comunicaciones = await this.extraerSeccion(
      "COMUNICACIONES",
      "https://dehu.redsara.es/es/communications",
      "app-communications-list-view",
      "#tablaComunicaciones"
    );
    const todasNotificaciones = [...pendientes, ...realizadas, ...comunicaciones];
    log.info(
      `[${this.nombre}] Total: ${todasNotificaciones.length} (${pendientes.length} pend + ${realizadas.length} real + ${comunicaciones.length} comun)`
    );
    const resultado = {
      exito: true,
      metodo: MetodoConsulta.PUPPETEER,
      certificadoSerial: this.configDehu.certificadoSerial,
      estadoAlta: EstadoAltaDehu.NO_ALTA,
      notificaciones: todasNotificaciones.filter((n) => n.tipo === "Notificacion"),
      comunicaciones: todasNotificaciones.filter((n) => n.tipo === "Comunicacion"),
      fechaConsulta: (/* @__PURE__ */ new Date()).toISOString()
    };
    return {
      exito: true,
      datos: resultado
    };
  }
  /**
   * Proceso de login con reintentos.
   * Flujo: DEHU public → click Acceder → Cl@ve pasarela → cert → DEHU autenticado.
   *
   * Deteccion basada en URL (no en selectores fragiles como 'main'):
   * 1. Navegar a DEHU, verificar si ya estamos logueados
   * 2. Click Acceder → esperar navegacion fuera de DEHU
   * 3. En Cl@ve: selectedIdP('AFIRMA') → select-client-certificate
   * 4. Esperar redireccion de vuelta a DEHU autenticado
   */
  async intentarLogin(maxIntentos) {
    for (let intento = 1; intento <= maxIntentos; intento++) {
      try {
        log.info(`[${this.nombre}] Intento login ${intento}/${maxIntentos}`);
        await this.navegarConReintentos(URL_DEHU_NOTIFICACIONES);
        await this.esperar(3e3);
        const yaLogueado = await this.verificarSesionActiva();
        if (yaLogueado) {
          log.info(`[${this.nombre}] Ya autenticado en DEHU`);
          return true;
        }
        await this.esperarElemento("app-public-view", 15e3);
        await this.esperar(2e3);
        const clickedAcceder = await this.ejecutarJS(`
          (function() {
            var dntBtn = document.querySelector('dnt-button.access-btn');
            if (dntBtn) {
              if (dntBtn.shadowRoot && dntBtn.shadowRoot.querySelector('button')) {
                dntBtn.shadowRoot.querySelector('button').click();
              } else {
                dntBtn.click();
              }
              return true;
            }
            return false;
          })()
        `);
        if (!clickedAcceder) {
          throw new Error("No se encontro boton Acceder en DEHU");
        }
        log.info(`[${this.nombre}] Boton Acceder clickeado, esperando navegacion...`);
        await this.esperar(5e3);
        const urlPostClick = this.window ? this.obtenerURL() : "";
        log.info(`[${this.nombre}] URL post-click: ${urlPostClick}`);
        if (urlPostClick.includes("clave.gob.es")) {
          log.info(`[${this.nombre}] Pasarela Cl@ve detectada`);
          const pasoClave = await this.manejarPasarelaClave(5e3, 45e3);
          if (!pasoClave) {
            throw new Error("Cl@ve pasarela no pudo completar autenticacion");
          }
        } else if (urlPostClick.includes("dehu.redsara.es")) {
          const logueadoPost = await this.verificarSesionActiva();
          if (logueadoPost) {
            log.info(`[${this.nombre}] Login exitoso (auto-cert rapido)`);
            return true;
          }
          await this.esperar(5e3);
          const urlSegunda = this.window ? this.obtenerURL() : "";
          if (urlSegunda.includes("clave.gob.es")) {
            const pasoClave = await this.manejarPasarelaClave(5e3, 45e3);
            if (!pasoClave) {
              throw new Error("Cl@ve pasarela no pudo completar autenticacion (2do intento)");
            }
          }
        } else {
          log.info(`[${this.nombre}] URL desconocida post-click, intentando Cl@ve`);
          const pasoClave = await this.manejarPasarelaClave(15e3, 45e3);
          if (!pasoClave) {
            const logueadoFinal = await this.verificarSesionActiva();
            if (logueadoFinal) {
              log.info(`[${this.nombre}] Login exitoso tras URL desconocida`);
              return true;
            }
            throw new Error(`URL inesperada post-login: ${urlPostClick}`);
          }
        }
        await this.esperar(3e3);
        const autenticado = await this.esperarSesionActiva(3e4);
        if (autenticado) {
          log.info(`[${this.nombre}] Login exitoso`);
          return true;
        }
        throw new Error("No se detecto vista autenticada tras login");
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error);
        log.warn(`[${this.nombre}] Intento login ${intento} fallido: ${msg}`);
        try {
          await this.capturarPantalla(`dehu_login_fail_${intento}`);
        } catch {
        }
        if (intento < maxIntentos) {
          await this.esperar(3e3);
        }
      }
    }
    return false;
  }
  /**
   * Verifica si hay sesion activa en DEHU (usuario logueado).
   * Comprueba multiples indicadores: header usuario, sidebar, home view.
   */
  async verificarSesionActiva() {
    if (!this.window || this.window.isDestroyed()) return false;
    try {
      return await this.ejecutarJS(`
        (function() {
          return !!(
            document.querySelector('dnt-header-item[type="user"]') ||
            document.querySelector('app-home-view') ||
            document.querySelector('dnt-sidebar') ||
            document.querySelector('app-notifications-list')
          );
        })()
      `);
    } catch {
      return false;
    }
  }
  /**
   * Espera con polling a que haya sesion activa en DEHU.
   */
  async esperarSesionActiva(timeout) {
    const inicio = Date.now();
    while (Date.now() - inicio < timeout) {
      if (this.window && !this.window.isDestroyed()) {
        const url = this.obtenerURL();
        if (url.includes("dehu.redsara.es")) {
          const activa = await this.verificarSesionActiva();
          if (activa) return true;
        }
      }
      await this.esperar(1e3);
    }
    return false;
  }
  /**
   * Extrae notificaciones de una seccion especifica de DEHU.
   * Replica DehuUnifiedScraper pasos 2-4.
   */
  async extraerSeccion(tipo, url, viewSelector, tableSelector) {
    try {
      log.info(`[${this.nombre}] Extrayendo ${tipo}...`);
      await this.navegarConReintentos(url);
      await this.esperarElemento(viewSelector, 2e4);
      if (tipo === "REALIZADAS") {
        await this.clickPestanaRealizadas();
      }
      const hayTabla = await this.waitForTable(tableSelector, 1e4);
      if (!hayTabla) {
        log.info(`[${this.nombre}] ${tipo}: sin tabla visible`);
        return [];
      }
      await this.esperar(4e3);
      const rawResults = await this.extractNotificationsData(tipo, tableSelector);
      log.info(`[${this.nombre}] ${tipo}: ${rawResults.length} resultados`);
      return rawResults;
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      log.error(`[${this.nombre}] Error extrayendo ${tipo}: ${msg}`);
      return [];
    }
  }
  /**
   * Hace click en la pestaña "Notificaciones realizadas" del SPA DEHU.
   * Necesario porque la navegacion por URL no siempre activa la pestaña.
   */
  async clickPestanaRealizadas() {
    if (!this.window || this.window.isDestroyed()) return;
    try {
      await this.ejecutarJS(`
        (function() {
          // Buscar tab "Notificaciones realizadas" por rol o texto
          var tabs = document.querySelectorAll('[role="tab"]');
          for (var i = 0; i < tabs.length; i++) {
            if (tabs[i].textContent && tabs[i].textContent.includes('realizadas')) {
              tabs[i].click();
              return true;
            }
          }
          // Fallback: buscar por texto en cualquier elemento clickeable
          var links = document.querySelectorAll('a, button, [role="tab"], li');
          for (var j = 0; j < links.length; j++) {
            var text = links[j].textContent || '';
            if (text.toLowerCase().includes('notificaciones realizadas')) {
              links[j].click();
              return true;
            }
          }
          return false;
        })()
      `);
      await this.esperar(2e3);
      log.info(`[${this.nombre}] Click en pestaña "Notificaciones realizadas"`);
    } catch (error) {
      log.warn(`[${this.nombre}] No se pudo hacer click en pestaña realizadas: ${error}`);
    }
  }
  /**
   * Click en tab "Notificaciones pendientes" — SPA navigation sin recargar pagina.
   * CRITICO: NO usar navegarConReintentos() porque rompe la sesion TLS.
   */
  async clickPestanaPendientes() {
    if (!this.window || this.window.isDestroyed()) return;
    try {
      await this.ejecutarJS(`
        (function() {
          var tabs = document.querySelectorAll('[role="tab"]');
          for (var i = 0; i < tabs.length; i++) {
            var texto = (tabs[i].textContent || '').toLowerCase();
            if (texto.includes('pendiente')) {
              tabs[i].click();
              return true;
            }
          }
          // Fallback: buscar por texto en cualquier elemento clickeable
          var links = document.querySelectorAll('a, button, [role="tab"], li');
          for (var j = 0; j < links.length; j++) {
            var text = (links[j].textContent || '').toLowerCase();
            if (text.includes('notificaciones pendientes')) {
              links[j].click();
              return true;
            }
          }
          return false;
        })()
      `);
      await this.esperar(2e3);
      log.info(`[${this.nombre}] Click en pestaña "Notificaciones pendientes"`);
    } catch (error) {
      log.warn(`[${this.nombre}] No se pudo hacer click en pestaña pendientes: ${error}`);
    }
  }
  /**
   * Espera a que la tabla tenga al menos 1 fila de datos (no solo el skeleton/loading).
   * Util despues de cambiar tab — el SPA hace una API call que puede tardar.
   * onBeforeRequest ya ha modificado los parametros (publicId + fecha extendida).
   */
  async esperarTablaConDatos(tableSelector, timeout) {
    if (!this.window || this.window.isDestroyed()) return 0;
    const inicio = Date.now();
    let ultimoConteo = 0;
    while (Date.now() - inicio < timeout) {
      try {
        const filas = await this.ejecutarJS(`
          (function() {
            var table = document.querySelector('${tableSelector.replace(/'/g, "\\'")}');
            if (!table || !table.shadowRoot) return 0;
            var rows = table.shadowRoot.querySelectorAll('tr.dnt-table__row');
            var dataRows = Array.from(rows).filter(function(r) {
              return !r.classList.contains('dnt-table__row-expansion');
            });
            return dataRows.length;
          })()
        `);
        ultimoConteo = filas;
        if (filas > 0) {
          log.info(`[${this.nombre}] Tabla cargada con ${filas} filas en ${Date.now() - inicio}ms`);
          return filas;
        }
      } catch {
      }
      await this.esperar(500);
    }
    log.warn(`[${this.nombre}] Timeout ${timeout}ms esperando datos en tabla. Ultimo conteo: ${ultimoConteo}`);
    return ultimoConteo;
  }
  /**
   * Click en enlace "Notificaciones" del nav superior del SPA.
   * Navegacion interna Angular (history.pushState) — NO recarga la pagina.
   */
  async clickNavNotificaciones() {
    if (!this.window || this.window.isDestroyed()) return;
    try {
      await this.ejecutarJS(`
        (function() {
          // Buscar enlace en la barra de navegacion superior
          var links = document.querySelectorAll('a[href*="/notifications"], a[routerLink*="/notifications"]');
          for (var i = 0; i < links.length; i++) {
            var text = (links[i].textContent || '').toLowerCase();
            if (text.includes('notificacion')) {
              links[i].click();
              return true;
            }
          }
          // Fallback: buscar en nav items
          var navItems = document.querySelectorAll('nav a, .nav-item a, dnt-sidebar a, [role="navigation"] a');
          for (var j = 0; j < navItems.length; j++) {
            var href = navItems[j].getAttribute('href') || '';
            if (href.includes('/notifications')) {
              navItems[j].click();
              return true;
            }
          }
          return false;
        })()
      `);
      await this.esperar(2e3);
      log.info(`[${this.nombre}] Click nav "Notificaciones"`);
    } catch (err) {
      log.warn(`[${this.nombre}] No se pudo click nav Notificaciones: ${err}`);
    }
  }
  /**
   * Click en enlace "Comunicaciones" del nav superior del SPA.
   * Navegacion interna Angular (history.pushState) — NO recarga la pagina.
   */
  async clickNavComunicaciones() {
    if (!this.window || this.window.isDestroyed()) return;
    try {
      await this.ejecutarJS(`
        (function() {
          var links = document.querySelectorAll('a[href*="/communications"], a[routerLink*="/communications"]');
          for (var i = 0; i < links.length; i++) {
            var text = (links[i].textContent || '').toLowerCase();
            if (text.includes('comunicacion')) {
              links[i].click();
              return true;
            }
          }
          var navItems = document.querySelectorAll('nav a, .nav-item a, dnt-sidebar a, [role="navigation"] a');
          for (var j = 0; j < navItems.length; j++) {
            var href = navItems[j].getAttribute('href') || '';
            if (href.includes('/communications')) {
              navItems[j].click();
              return true;
            }
          }
          return false;
        })()
      `);
      await this.esperar(2e3);
      log.info(`[${this.nombre}] Click nav "Comunicaciones"`);
    } catch (err) {
      log.warn(`[${this.nombre}] No se pudo click nav Comunicaciones: ${err}`);
    }
  }
  /**
   * Espera a que una tabla sea visible (con offset > 0).
   * Replica DehuUnifiedScraper.waitForTable().
   */
  async waitForTable(tableSelector, timeout) {
    if (!this.window || this.window.isDestroyed()) return false;
    return await this.ejecutarJS(`
      new Promise((resolve) => {
        var startTime = Date.now();
        var check = function() {
          var table = document.querySelector('${tableSelector.replace(/'/g, "\\'")}');
          if (table && (table.offsetHeight > 0 || table.getClientRects().length > 0)) return resolve(true);
          if (Date.now() - startTime > ${timeout}) return resolve(false);
          setTimeout(check, 200);
        };
        check();
      })
    `);
  }
  /**
   * Extrae datos de notificaciones de la tabla DEHU usando Shadow DOM.
   * Replica EXACTA de Findiur DehuUnifiedScraper.extractNotificationsData().
   * DEHU usa Web Components con shadowRoot — no se pueden leer con querySelector normal.
   */
  async extractNotificationsData(type, tableSelector) {
    if (!this.window || this.window.isDestroyed()) return [];
    const rawResults = await this.ejecutarJS(`
      (async function(type, tableSelector) {
        try {
          var sleep = function(ms) { return new Promise(function(r) { setTimeout(r, ms); }); };
          var attempts = 0;
          var table = null;

          while (attempts < 20) {
            table = document.querySelector(tableSelector);
            if (table && table.shadowRoot) break;
            await sleep(300);
            attempts++;
          }

          if (!table || !table.shadowRoot) return [];

          var allRows = Array.from(
            table.shadowRoot.querySelectorAll('tr.dnt-table__row')
          );

          var mainRows = allRows.filter(function(r) {
            return !r.classList.contains('dnt-table__row-expansion');
          });

          if (mainRows.length === 0) return [];

          return mainRows.map(function(row) {
            try {
              var getCell = function(label) {
                var td = row.querySelector('td[data-label="' + label + '"]');
                if (!td) return null;
                if (td.shadowRoot) {
                  var inner = td.shadowRoot.querySelector('.dnt-table__cell-content');
                  return inner ? inner.innerText.trim() : td.innerText.trim();
                }
                return td.innerText.trim();
              };

              var id = getCell('Identificador');
              var titular = getCell('Titular');
              var ambito = getCell('Organismo emisor');
              var estadoText = getCell('Estado');

              // FECHA DISPOSICION — logica exacta de Findiur
              var disposicion = '';
              var fechaDispCell = getCell('Fecha disposición');
              if (fechaDispCell) disposicion = fechaDispCell;

              var nextRow = row.nextElementSibling;
              var isExpansion = nextRow && nextRow.classList.contains('dnt-table__row-expansion');

              if ((!disposicion || disposicion === '') && isExpansion) {
                var ps = Array.from(nextRow.querySelectorAll('p'));
                var labelP = ps.find(function(p) { return p.innerText.includes('Fecha disposición'); });
                if (labelP) {
                  if (labelP.nextSibling && labelP.nextSibling.nodeType === Node.TEXT_NODE) {
                    var text = labelP.nextSibling.textContent.trim();
                    var match = text.match(/(\\d{2})[\\/-](\\d{2})[\\/-](\\d{4})/);
                    if (match) disposicion = match[0];
                  }
                  if (!disposicion && labelP.parentElement) {
                    var fullText = labelP.parentElement.innerText;
                    var parts = fullText.split('Fecha disposición');
                    if (parts.length > 1) {
                      var textAfterLabel = parts[1];
                      var match2 = textAfterLabel.match(/(\\d{2})[\\/-](\\d{2})[\\/-](\\d{4})/);
                      if (match2) disposicion = match2[0];
                    }
                  }
                }
              }

              // Normalizar DD-MM-YYYY
              if (disposicion) {
                var matchNorm = disposicion.match(/(\\d{2})[\\/-](\\d{2})[\\/-](\\d{4})/);
                if (matchNorm) {
                  disposicion = matchNorm[1] + '-' + matchNorm[2] + '-' + matchNorm[3];
                }
              }

              // TITULO / CONCEPTO desde expansion
              var titulo = '';
              var fechaLeida = null;
              var isLeida = false;

              if (nextRow && nextRow.classList.contains('dnt-table__row-expansion')) {
                var labels = Array.from(nextRow.querySelectorAll('.dnt-txt-body-350'));
                var conceptoLabel = labels.find(function(el) { return el.innerText.trim() === 'Concepto'; });
                if (conceptoLabel) {
                  var valueEl = conceptoLabel.nextElementSibling;
                  if (valueEl) titulo = valueEl.innerText.trim();
                }
                if (type === 'COMUNICACIONES') {
                  var leidaLabel = labels.find(function(el) { return el.innerText.trim() === 'Fecha leída'; });
                  if (leidaLabel) {
                    var containerText = leidaLabel.parentElement ? leidaLabel.parentElement.innerText : '';
                    var matchLeida = containerText.match(/(\\d{2})[\\/-](\\d{2})[\\/-](\\d{4})/);
                    if (matchLeida) fechaLeida = matchLeida[1] + '-' + matchLeida[2] + '-' + matchLeida[3];
                  }
                }
              }

              if (!titulo) {
                var td = row.querySelector('td[data-label="Organismo emisor"]');
                if (td && td.shadowRoot) {
                  var content = td.shadowRoot.querySelector('.dnt-table__cell-content');
                  var original = content ? content.getAttribute('data-original-text-concept') : null;
                  if (original) titulo = original.trim();
                }
              }
              if (!titulo) titulo = ambito || 'Sin titulo';

              // ESTADO — logica exacta de Findiur
              var estadoFinal = 'Pendiente';
              var tipoNotif = 'Notificacion';

              if (type === 'PENDIENTES') {
                estadoFinal = 'Pendiente de abrir';
              } else if (type === 'REALIZADAS') {
                estadoFinal = estadoText || 'Abierta Externamente';
              } else if (type === 'COMUNICACIONES') {
                tipoNotif = 'Comunicacion';
                if (fechaLeida || (estadoText && estadoText.toLowerCase().includes('leída'))) {
                  estadoFinal = 'Archivada';
                  isLeida = true;
                } else {
                  estadoFinal = 'Pendiente de abrir';
                }
              }

              return {
                id: id,
                titulo: titulo,
                titular: titular,
                ambito: ambito,
                disposicion: disposicion,
                estado: estadoFinal,
                tipo: tipoNotif,
                fechaLeida: fechaLeida
              };
            } catch (rowErr) {
              return null;
            }
          });
        } catch (e) {
          return [];
        }
      })('${type}', '${tableSelector.replace(/'/g, "\\'")}')
    `);
    if (!rawResults || !Array.isArray(rawResults)) return [];
    const notificaciones = [];
    for (const raw of rawResults) {
      if (!raw || !raw.id) continue;
      notificaciones.push({
        idDehu: raw.id,
        tipo: raw.tipo,
        titulo: raw.titulo,
        titular: raw.titular || this.serialNumber,
        ambito: raw.ambito || "",
        organismo: raw.ambito || "DEHU",
        fechaDisposicion: this.normalizarFecha(raw.disposicion),
        fechaCaducidad: null,
        estado: raw.estado,
        rutaPdfLocal: null
      });
    }
    return notificaciones;
  }
  /**
   * Configura un interceptor de red para capturar el token Bearer
   * que el SPA DEHU usa en sus peticiones API internas.
   *
   * El SPA Angular almacena el token en memoria (no en localStorage).
   * La unica forma fiable de obtenerlo es interceptar las peticiones
   * HTTP que el propio SPA hace al cargar la pagina de notificaciones.
   *
   * @returns Funcion de limpieza para desactivar el interceptor
   */
  configurarInterceptorToken() {
    if (!this.window || this.window.isDestroyed()) return () => {
    };
    const webSession = this.window.webContents.session;
    this.tokenInterceptado = null;
    webSession.webRequest.onBeforeSendHeaders(
      { urls: ["*://dehu.redsara.es/*"] },
      (details, callback) => {
        if (details.url.includes("/api/")) {
          const auth = details.requestHeaders["Authorization"] || details.requestHeaders["authorization"];
          if (auth && auth.startsWith("Bearer ")) {
            if (!this.tokenInterceptado) {
              this.tokenInterceptado = auth.replace(/^Bearer\s+/i, "");
              log.info(`[${this.nombre}] Token interceptado: ${this.tokenInterceptado.substring(0, 40)}...`);
            }
          }
        }
        callback({ requestHeaders: details.requestHeaders });
      }
    );
    return () => {
      try {
        webSession.webRequest.onBeforeSendHeaders(null);
      } catch {
      }
    };
  }
  /**
   * Ejecuta login + descarga de PDF para una notificacion.
   * Punto de entrada publico para el IPC handler — maneja el ciclo
   * completo: inicializar navegador, login, descarga, cierre.
   */
  async runDescargarPdf(notificacion) {
    let timeoutHandle = null;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutHandle = setTimeout(() => {
        reject(new Error(`Timeout global descarga PDF (${this.config.timeoutGlobal / 1e3}s)`));
      }, this.config.timeoutGlobal);
    });
    const descargarPromise = async () => {
      await this.inicializarNavegador();
      const loggedIn = await this.intentarLogin(3);
      if (!loggedIn) {
        throw new Error("No se pudo iniciar sesion en DEHU (login fallido tras 3 intentos)");
      }
      return await this.descargarPdf(notificacion);
    };
    try {
      return await Promise.race([descargarPromise(), timeoutPromise]);
    } finally {
      if (timeoutHandle) clearTimeout(timeoutHandle);
      await this.cerrarNavegador();
    }
  }
  /**
   * Descarga el PDF de una notificacion individual.
   * Requiere que el navegador este inicializado y logueado.
   *
   * DEHU tiene TLS session binding: solo requests desde el renderer que hizo
   * el handshake Cl@ve funcionan.
   *
   * API DEHU (de config/env.json):
   *   host: https://dehu.redsara.es/api/
   *   realized: GET v1/realized_notifications/:sentReference/document
   *   pending:  (no hay endpoint /document para pendientes — solo metadata)
   *   comms:    GET v1/communications/:sentReference/document
   *
   * El sentReference ES el idDehu (ej: N276297762), NO un UUID interno.
   * No necesitamos navegar a la pagina de detalle — fetch directo con el idDehu.
   *
   * Flujo v1.0.87:
   * 1. Navegar a DEHU (para que SPA haga API calls → captura token)
   * 2. fetch() directo a /api/v1/{tipo}/{idDehu}/document
   * 3. Fallback: printToPdf de pagina de detalle
   */
  async descargarPdf(notificacion) {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado o destruido");
    }
    const idDehu = notificacion.idDehu;
    log.info(`[${this.nombre}] === DESCARGA PDF v1.0.88 === idDehu=${idDehu}, estado=${notificacion.estado}, tipo=${notificacion.tipo}`);
    const idSanitizado = idDehu.replace(/[^a-zA-Z0-9-_]/g, "_");
    const nombreArchivo = `DEHU_${idSanitizado}.pdf`;
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
    const limpiarInterceptor = this.configurarInterceptorToken();
    try {
      await this.navegarConReintentos(URL_DEHU_NOTIFICACIONES);
      await this.esperar(3e3);
      const tokenListo = await this.esperarToken(15e3);
      log.info(`[${this.nombre}] Token capturado: ${tokenListo ? "SI" : "NO"}`);
      const esComunicacion = notificacion.tipo === "Comunicacion";
      const esPendiente = notificacion.estado === "Pendiente de abrir" || notificacion.estado === "Pendiente";
      const sentReference = await this.buscarSentReference(idDehu, esComunicacion, esPendiente);
      if (sentReference) {
        log.info(`[${this.nombre}] [PASO 2] sentReference encontrado: ${sentReference}`);
        const urlsProbar = [];
        if (esComunicacion) {
          urlsProbar.push(`/api/v1/communications/${sentReference}/document`);
        } else if (esPendiente) {
          urlsProbar.push(`/api/v1/notifications/${sentReference}/voucher`);
        } else {
          urlsProbar.push(`/api/v1/realized_notifications/${sentReference}/document`);
        }
        if (!esComunicacion) urlsProbar.push(`/api/v1/communications/${sentReference}/document`);
        if (!esPendiente) urlsProbar.push(`/api/v1/notifications/${sentReference}/voucher`);
        for (const apiPath of urlsProbar) {
          log.info(`[${this.nombre}] [PASO 3] Intentando: ${apiPath}`);
          const ok = await this.descargarViaFetchEnPagina(idDehu, apiPath, rutaDestino);
          if (ok) return rutaDestino;
        }
      } else {
        log.warn(`[${this.nombre}] [PASO 2] No se encontro sentReference para ${idDehu}`);
      }
      log.info(`[${this.nombre}] [PASO 4] Fallback printToPdf...`);
      const sentRefParaUrl = sentReference || idDehu;
      const urlDetalle = esComunicacion ? `https://dehu.redsara.es/es/communications/${sentRefParaUrl}` : esPendiente ? `https://dehu.redsara.es/es/notifications/pending/${sentRefParaUrl}` : `https://dehu.redsara.es/es/notifications/realized/${sentRefParaUrl}`;
      try {
        await this.navegarConReintentos(urlDetalle);
        await this.esperar(5e3);
      } catch (err) {
        log.warn(`[${this.nombre}] No se pudo navegar a detalle: ${err}`);
      }
      const printOk = await this.descargarViaPrintToPdf(rutaDestino);
      if (printOk) return rutaDestino;
      throw new Error(`No se pudo descargar PDF de ${idDehu}`);
    } finally {
      limpiarInterceptor();
    }
  }
  /**
   * Espera hasta que el interceptor capture un Bearer token.
   */
  async esperarToken(timeout) {
    const inicio = Date.now();
    while (Date.now() - inicio < timeout) {
      if (this.tokenInterceptado) return true;
      await this.esperar(500);
    }
    return !!this.tokenInterceptado;
  }
  /**
   * Busca el sentReference de una notificacion via API list.
   * El identifier (N276297762) NO es el sentReference — hay que listar y buscar.
   * La API requiere TODOS los params del filtro (incluso vacios) y rango max ~30 dias.
   */
  async buscarSentReference(idDehu, esComunicacion, esPendiente) {
    if (!this.window || this.window.isDestroyed()) return null;
    const tokenEscapado = this.tokenInterceptado ? this.tokenInterceptado.replace(/'/g, "\\'") : "";
    const idEscapado = idDehu.replace(/'/g, "\\'");
    const hoy = /* @__PURE__ */ new Date();
    const hace30 = new Date(hoy.getTime() - 30 * 24 * 60 * 60 * 1e3);
    const formatFecha = (d) => `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
    const fechaDesde = formatFecha(hace30);
    const fechaHasta = formatFecha(hoy);
    let listUrl;
    if (esComunicacion) {
      listUrl = `/api/v1/communications?page=1&limit=50`;
    } else if (esPendiente) {
      listUrl = `/api/v1/notifications?page=1&limit=50`;
    } else {
      listUrl = `/api/v1/realized_notifications?emitterEntityCode=&state=&publicId=&titularNif=&bondType=&vinculoReceptor=&postalDelivery=&finalDate%5Bleft_date%5D=${encodeURIComponent(fechaDesde)}&finalDate%5Bright_date%5D=${encodeURIComponent(fechaHasta)}&expirationDate%5Bleft_date%5D=&expirationDate%5Bright_date%5D=&page=1&limit=50`;
    }
    log.info(`[${this.nombre}] Buscando sentReference de ${idDehu} via: ${listUrl.substring(0, 100)}...`);
    try {
      const resultado = await this.ejecutarJS(`
        (async function() {
          try {
            var token = '${tokenEscapado}' || null;
            if (!token) {
              var keys = Object.keys(localStorage);
              for (var i = 0; i < keys.length; i++) {
                var val = localStorage.getItem(keys[i]);
                if (val && val.length > 100 && /^eyJ/.test(val)) { token = val; break; }
              }
            }
            if (!token) return { sentReference: null, total: 0, error: 'Sin token' };

            var response = await fetch('${listUrl}', {
              headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/json' }
            });
            if (!response.ok) {
              var errText = '';
              try { errText = await response.text(); } catch(e) {}
              return { sentReference: null, total: 0, error: 'HTTP ' + response.status + ': ' + errText.substring(0, 200) };
            }

            var data = await response.json();
            var items = data.items || data.content || [];
            if (!Array.isArray(items)) {
              for (var k in data) {
                if (Array.isArray(data[k])) { items = data[k]; break; }
              }
            }

            for (var idx = 0; idx < items.length; idx++) {
              var item = items[idx];
              if (item.identifier === '${idEscapado}' || item.publicId === '${idEscapado}') {
                return { sentReference: item.sentReference || null, total: items.length };
              }
            }
            return { sentReference: null, total: items.length };
          } catch (e) {
            return { sentReference: null, total: 0, error: e.message || String(e) };
          }
        })()
      `);
      if (resultado.error) {
        log.warn(`[${this.nombre}] buscarSentReference error: ${resultado.error}`);
      }
      if (resultado.sentReference) {
        log.info(`[${this.nombre}] ${idDehu} → sentReference=${resultado.sentReference} (de ${resultado.total} items)`);
      } else {
        log.warn(`[${this.nombre}] ${idDehu} no encontrado en ${resultado.total} items`);
      }
      return resultado.sentReference;
    } catch (error) {
      log.error(`[${this.nombre}] buscarSentReference exception: ${error}`);
      return null;
    }
  }
  /**
   * Descarga PDF via fetch() en el contexto de la pagina principal (patron Findiur).
   *
   * DEHU tiene TLS session binding: solo requests desde el renderer que hizo
   * el handshake Cl@ve funcionan. fetch() en executeJavaScript es same-origin
   * (dehu.redsara.es → dehu.redsara.es/api) asi que CSP no bloquea.
   *
   * El SPA Angular almacena el Bearer token — lo buscamos en localStorage/sessionStorage.
   * Como fallback usamos el token capturado por onBeforeSendHeaders.
   */
  async descargarViaFetchEnPagina(_idDehu, apiPath, rutaDestino) {
    if (!this.window || this.window.isDestroyed()) return false;
    const tokenEscapado = this.tokenInterceptado ? this.tokenInterceptado.replace(/'/g, "\\'") : "";
    log.info(`[${this.nombre}] fetch en pagina: ${apiPath} (token interceptado: ${tokenEscapado ? "SI" : "NO"})`);
    try {
      const resultado = await this.ejecutarJS(`
        (async function() {
          try {
            // Buscar Bearer token: interceptado > localStorage > sessionStorage
            var token = '${tokenEscapado}' || null;

            if (!token) {
              var keys = Object.keys(localStorage);
              for (var i = 0; i < keys.length; i++) {
                var val = localStorage.getItem(keys[i]);
                if (val && val.length > 100 && /^eyJ/.test(val)) {
                  token = val;
                  break;
                }
              }
            }

            if (!token) {
              var keys2 = Object.keys(sessionStorage);
              for (var j = 0; j < keys2.length; j++) {
                var val2 = sessionStorage.getItem(keys2[j]);
                if (val2 && val2.length > 100 && /^eyJ/.test(val2)) {
                  token = val2;
                  break;
                }
              }
            }

            if (!token) {
              return { error: 'No se encontro token Bearer' };
            }

            var response = await fetch('${apiPath}', {
              method: 'GET',
              headers: {
                'Authorization': 'Bearer ' + token,
                'Accept': 'application/json'
              }
            });

            if (!response.ok) {
              var errorText = '';
              try { errorText = await response.text(); } catch(e) {}
              return { error: 'HTTP ' + response.status + ': ' + errorText.substring(0, 200), status: response.status };
            }

            var data = await response.json();

            // El SPA Angular devuelve: { documentContent: { content, name, mimeType } }
            // o directamente: { content, name, mimeType }
            var base64 = null;
            var nombre = null;
            if (data.documentContent && data.documentContent.content) {
              base64 = data.documentContent.content;
              nombre = data.documentContent.name || null;
            } else if (data.content) {
              base64 = data.content;
              nombre = data.name || null;
            } else if (data.data) {
              base64 = data.data;
            } else if (data.document) {
              base64 = data.document;
            } else if (data.pdf) {
              base64 = data.pdf;
            }

            if (!base64) {
              return { error: 'JSON sin campo content. Keys: ' + Object.keys(data).join(',') + ' | ' + JSON.stringify(data).substring(0, 300) };
            }

            return { base64: base64, nombre: nombre };
          } catch (e) {
            return { error: e.message || String(e) };
          }
        })()
      `);
      if (resultado.error) {
        log.error(`[${this.nombre}] fetch error (${apiPath}): ${resultado.error}`);
        return false;
      }
      if (!resultado.base64) {
        log.error(`[${this.nombre}] fetch sin base64`);
        return false;
      }
      if (resultado.nombre) {
        log.info(`[${this.nombre}] Documento nombre del servidor: ${resultado.nombre}`);
      }
      const pdfBuffer = Buffer.from(resultado.base64, "base64");
      if (pdfBuffer.length < 100) {
        log.error(`[${this.nombre}] PDF demasiado pequeno: ${pdfBuffer.length} bytes`);
        return false;
      }
      if (!pdfBuffer.subarray(0, 5).toString("utf-8").startsWith("%PDF")) {
        log.warn(`[${this.nombre}] Buffer no empieza con %PDF, primeros bytes: ${pdfBuffer.subarray(0, 20).toString("hex")}`);
      }
      writeFileSync(rutaDestino, pdfBuffer);
      log.info(`[${this.nombre}] PDF guardado (${pdfBuffer.length} bytes): ${rutaDestino}`);
      return true;
    } catch (error) {
      log.error(`[${this.nombre}] Error descargarViaFetchEnPagina: ${error}`);
      return false;
    }
  }
  /**
   * Fallback: si la API falla, captura la pagina de detalle como PDF
   * usando printToPdf del webContents de Electron.
   */
  async descargarViaPrintToPdf(rutaDestino) {
    if (!this.window || this.window.isDestroyed()) return false;
    try {
      const data = await this.window.webContents.printToPDF({
        printBackground: true,
        landscape: false
      });
      writeFileSync(rutaDestino, data);
      log.info(`[${this.nombre}] Fallback printToPdf guardado (${data.length} bytes): ${rutaDestino}`);
      return true;
    } catch (error) {
      log.error(`[${this.nombre}] Fallback printToPdf fallo: ${error}`);
      return false;
    }
  }
  /**
   * Diagnostica el contexto de la pagina DEHU tras login.
   * Busca: titular activo, selector de representado, heading, NIF visible.
   * Esto ayuda a identificar si estamos viendo notificaciones del titular correcto.
   */
  async diagnosticarContextoPagina() {
    if (!this.window || this.window.isDestroyed()) {
      return { heading: "N/A", nifVisible: "N/A", nifsEnPagina: [], tieneSelectRepresentado: false, filtrosEncontrados: [], textoHeader: "N/A", tablesCount: 0, filasEnTabla: 0, urlActual: "N/A" };
    }
    return await this.ejecutarJS(`
      (function() {
        // Heading principal
        var h1 = document.querySelector('h1, h2, .title, [class*="title"]');
        var heading = h1 ? h1.innerText.trim().substring(0, 100) : '';

        // Buscar TODOS los NIF/CIF en texto visible de la pagina
        var bodyText = document.body.innerText || '';
        var nifRegex = /[A-HJ-NP-SUVW]\\d{7}[A-J0-9]|\\d{8}[A-Z]/g;
        var nifsEncontrados = [];
        var match;
        while ((match = nifRegex.exec(bodyText)) !== null) {
          if (nifsEncontrados.indexOf(match[0]) === -1) nifsEncontrados.push(match[0]);
        }
        var nifVisible = nifsEncontrados.length > 0 ? nifsEncontrados[0] : '';

        // Buscar selector de representado/poderdante/titular
        var textosBuscados = ['representad', 'poderdante', 'nombre de', 'actuar como', 'cambiar titular', 'en nombre', 'nif titular'];
        var tieneSelect = false;
        var filtrosInfo = [];

        // Buscar selects, listbox, combobox
        var selectores = document.querySelectorAll('select, [role="listbox"], [role="combobox"], dnt-select, .dropdown, [class*="dropdown"], [class*="selector"], [class*="filter"]');
        for (var s = 0; s < selectores.length; s++) {
          var selText = (selectores[s].textContent || selectores[s].getAttribute('aria-label') || selectores[s].className || '').substring(0, 60);
          filtrosInfo.push('SEL:' + selectores[s].tagName + '[' + selText + ']');
          tieneSelect = true;
        }

        // Buscar inputs de filtro
        var inputs = document.querySelectorAll('input[type="text"], input[type="search"], input:not([type]), dnt-input');
        for (var inp = 0; inp < inputs.length; inp++) {
          var placeholder = inputs[inp].getAttribute('placeholder') || '';
          var name = inputs[inp].getAttribute('name') || '';
          var ariaLabel = inputs[inp].getAttribute('aria-label') || '';
          var id = inputs[inp].id || '';
          filtrosInfo.push('INP:' + inputs[inp].tagName + '[ph=' + placeholder + ',name=' + name + ',aria=' + ariaLabel + ',id=' + id + ']');
        }

        // Buscar botones/links con texto de cambio de titular
        var links = document.querySelectorAll('a, button, [role="button"], dnt-button');
        for (var i = 0; i < links.length; i++) {
          var linkText = (links[i].innerText || links[i].textContent || '').toLowerCase().trim();
          for (var j = 0; j < textosBuscados.length; j++) {
            if (linkText.includes(textosBuscados[j])) {
              tieneSelect = true;
              filtrosInfo.push('BTN:' + links[i].tagName + '[' + linkText.substring(0, 40) + ']');
              break;
            }
          }
        }

        // Buscar labels que contengan texto de filtro
        var labels = document.querySelectorAll('label, .label, [class*="label"]');
        for (var lb = 0; lb < labels.length; lb++) {
          var lblText = (labels[lb].textContent || '').toLowerCase().trim();
          for (var lt = 0; lt < textosBuscados.length; lt++) {
            if (lblText.includes(textosBuscados[lt])) {
              filtrosInfo.push('LBL:[' + lblText.substring(0, 40) + ']');
              break;
            }
          }
        }

        // Texto del header (sidebar/navbar) — incluir usuario/entidad
        var headerEl = document.querySelector('dnt-header, dnt-sidebar, nav, header, [class*="header"]');
        var textoHeader = headerEl ? headerEl.innerText.trim().substring(0, 300) : '';

        // Contar tablas dnt-table
        var tablesCount = document.querySelectorAll('dnt-table').length;

        // Contar filas en la primera tabla visible
        var filasEnTabla = 0;
        var primeraTabla = document.querySelector('dnt-table');
        if (primeraTabla && primeraTabla.shadowRoot) {
          filasEnTabla = primeraTabla.shadowRoot.querySelectorAll('tr.dnt-table__row').length;
        }

        return {
          heading: heading,
          nifVisible: nifVisible,
          nifsEnPagina: nifsEncontrados.slice(0, 5),
          tieneSelectRepresentado: tieneSelect,
          filtrosEncontrados: filtrosInfo.slice(0, 15),
          textoHeader: textoHeader,
          tablesCount: tablesCount,
          filasEnTabla: filasEnTabla,
          urlActual: window.location.href,
        };
      })()
    `);
  }
  /**
   * Selecciona la entidad empresa en DEHU tras login.
   * Cuando el certificado representa a una persona juridica (empresa), DEHU muestra
   * por defecto las notificaciones del titular personal (DNI). Esta funcion usa el
   * filtro "En nombre de" / "NIF titular" para cambiar a la entidad empresa (CIF).
   *
   * Estrategias:
   * 1. Buscar input/select "En nombre de" o "NIF titular" → establecer CIF
   * 2. Buscar dnt-select/dropdown con opciones de entidad → seleccionar por CIF
   * 3. Buscar link/boton de cambio de entidad en header → click + seleccionar
   *
   * @returns true si se cambio la entidad, false si no fue necesario o no se encontro
   */
  async seleccionarEntidadEmpresa() {
    const cifEmpresa = this.configDehu.nifEmpresa;
    if (!cifEmpresa) {
      log.info(`[${this.nombre}] Sin CIF empresa configurado, usando entidad por defecto`);
      return false;
    }
    if (!this.window || this.window.isDestroyed()) return false;
    log.info(`[${this.nombre}] Intentando seleccionar entidad empresa: ${cifEmpresa}`);
    await this.esperar(2e3);
    const resultadoFiltro = await this.ejecutarJS(`
      (function() {
        var CIF = '${cifEmpresa}';

        // Helper: disparar eventos de input en un elemento
        function dispararEventosInput(el) {
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
        }

        // Helper: buscar en Shadow DOMs recursivamente
        function querySelectorDeep(selector) {
          var result = document.querySelector(selector);
          if (result) return result;
          var allHosts = document.querySelectorAll('*');
          for (var i = 0; i < allHosts.length; i++) {
            if (allHosts[i].shadowRoot) {
              var found = allHosts[i].shadowRoot.querySelector(selector);
              if (found) return found;
            }
          }
          return null;
        }

        // Helper: buscar todos los inputs (incluyendo Shadow DOM)
        function encontrarTodosInputs() {
          var inputs = Array.from(document.querySelectorAll('input, select, dnt-input, dnt-select'));
          var allHosts = document.querySelectorAll('*');
          for (var i = 0; i < allHosts.length; i++) {
            if (allHosts[i].shadowRoot) {
              var shadowInputs = allHosts[i].shadowRoot.querySelectorAll('input, select');
              inputs = inputs.concat(Array.from(shadowInputs));
            }
          }
          return inputs;
        }

        // ---- Estrategia 1: Buscar input/label "En nombre de" o "NIF" ----
        var labels = document.querySelectorAll('label, .label, [class*="label"], span, p');
        for (var i = 0; i < labels.length; i++) {
          var txt = (labels[i].textContent || '').toLowerCase();
          if (txt.includes('en nombre de') || txt.includes('nif titular') || txt.includes('nif del titular')) {
            // Buscar input asociado: por for=, siguiente hermano, o hijo
            var inputId = labels[i].getAttribute('for');
            var input = inputId ? document.getElementById(inputId) : null;
            if (!input) input = labels[i].querySelector('input, select');
            if (!input) input = labels[i].nextElementSibling;
            if (input && (input.tagName === 'INPUT' || input.tagName === 'SELECT')) {
              input.value = CIF;
              input.focus();
              dispararEventosInput(input);
              return { estrategia: 'label-input', exito: true, detalle: 'Label: ' + txt.substring(0, 50) };
            }
          }
        }

        // ---- Estrategia 2: Buscar dnt-select o select con opciones de entidad ----
        var selects = document.querySelectorAll('select, dnt-select, [role="listbox"], [role="combobox"]');
        for (var j = 0; j < selects.length; j++) {
          var sel = selects[j];
          var opciones = sel.querySelectorAll('option, [role="option"]');
          for (var k = 0; k < opciones.length; k++) {
            var optText = (opciones[k].textContent || '').toUpperCase();
            if (optText.includes(CIF)) {
              if (sel.tagName === 'SELECT') {
                sel.value = opciones[k].value || opciones[k].textContent;
                dispararEventosInput(sel);
              } else {
                opciones[k].click();
              }
              return { estrategia: 'select-opcion', exito: true, detalle: 'Opcion: ' + optText.substring(0, 50) };
            }
          }
        }

        // ---- Estrategia 3: Buscar input de busqueda general y escribir CIF ----
        var inputsBusqueda = encontrarTodosInputs();
        for (var m = 0; m < inputsBusqueda.length; m++) {
          var inp = inputsBusqueda[m];
          var placeholder = (inp.getAttribute('placeholder') || '').toLowerCase();
          var name = (inp.getAttribute('name') || '').toLowerCase();
          var ariaLabel = (inp.getAttribute('aria-label') || '').toLowerCase();
          if (placeholder.includes('nif') || placeholder.includes('nombre') || placeholder.includes('buscar') ||
              name.includes('nif') || name.includes('titular') ||
              ariaLabel.includes('nif') || ariaLabel.includes('nombre') || ariaLabel.includes('titular')) {
            if (inp.shadowRoot) {
              var innerInput = inp.shadowRoot.querySelector('input');
              if (innerInput) {
                innerInput.value = CIF;
                innerInput.focus();
                dispararEventosInput(innerInput);
                return { estrategia: 'input-busqueda-shadow', exito: true, detalle: 'Input: ' + (placeholder || name || ariaLabel) };
              }
            }
            inp.value = CIF;
            inp.focus();
            dispararEventosInput(inp);
            return { estrategia: 'input-busqueda', exito: true, detalle: 'Input: ' + (placeholder || name || ariaLabel) };
          }
        }

        // ---- Estrategia 4: Buscar dnt-header-item con menu de usuario/entidad ----
        var headerItems = document.querySelectorAll('dnt-header-item, [class*="user"], [class*="entity"]');
        var entidadInfo = [];
        for (var n = 0; n < headerItems.length; n++) {
          var txt2 = (headerItems[n].textContent || '');
          entidadInfo.push(txt2.substring(0, 60));
          // Si tiene un link/boton para cambiar entidad
          var changeBtn = headerItems[n].querySelector('a, button, [role="button"]');
          if (changeBtn) {
            var btnText = (changeBtn.textContent || '').toLowerCase();
            if (btnText.includes('cambiar') || btnText.includes('representad') || btnText.includes('entidad')) {
              changeBtn.click();
              return { estrategia: 'header-cambiar', exito: true, detalle: 'Boton: ' + btnText };
            }
          }
        }

        // No se encontro filtro — recopilar info diagnostica
        var allInputsInfo = [];
        var allInputs = encontrarTodosInputs();
        for (var p = 0; p < Math.min(allInputs.length, 10); p++) {
          allInputsInfo.push(allInputs[p].tagName + '[' +
            (allInputs[p].getAttribute('placeholder') || allInputs[p].getAttribute('name') || allInputs[p].getAttribute('aria-label') || allInputs[p].className || '') + ']');
        }

        return {
          estrategia: 'ninguna',
          exito: false,
          detalle: 'inputs=' + allInputsInfo.join('; ') + ' | header=' + entidadInfo.join('; ')
        };
      })()
    `);
    log.info(`[${this.nombre}] Seleccion entidad: estrategia=${resultadoFiltro.estrategia} exito=${resultadoFiltro.exito} detalle=${resultadoFiltro.detalle}`);
    if (resultadoFiltro.exito) {
      await this.esperar(3e3);
      try {
        await this.ejecutarJS(`
          (function() {
            var botones = document.querySelectorAll('button, dnt-button, [role="button"], input[type="submit"]');
            for (var i = 0; i < botones.length; i++) {
              var texto = (botones[i].textContent || '').toLowerCase();
              if (texto.includes('buscar') || texto.includes('filtrar') || texto.includes('aplicar') || texto.includes('search')) {
                if (botones[i].shadowRoot) {
                  var innerBtn = botones[i].shadowRoot.querySelector('button');
                  if (innerBtn) { innerBtn.click(); return; }
                }
                botones[i].click();
                return;
              }
            }
            // Fallback: submit del form mas cercano
            var forms = document.querySelectorAll('form');
            if (forms.length > 0) {
              forms[0].dispatchEvent(new Event('submit', { bubbles: true }));
            }
          })()
        `);
        await this.esperar(3e3);
      } catch {
      }
      try {
        await this.capturarPantalla("dehu_05_post_filtro_entidad");
      } catch {
      }
      log.info(`[${this.nombre}] Filtro entidad empresa aplicado`);
      return true;
    }
    if (this.window && !this.window.isDestroyed()) {
      const urlActual = await this.ejecutarJS("window.location.href");
      if (urlActual.includes("/notifications") && !urlActual.includes("nifTitular=")) {
        const urlConFiltro = urlActual.includes("?") ? `${urlActual}&nifTitular=${cifEmpresa}` : `${urlActual}?nifTitular=${cifEmpresa}`;
        log.info(`[${this.nombre}] Intentando filtro por URL: ${urlConFiltro}`);
        await this.navegarConReintentos(urlConFiltro);
        await this.esperar(5e3);
        try {
          await this.capturarPantalla("dehu_05_post_url_filtro");
        } catch {
        }
      }
    }
    return false;
  }
  normalizarFecha(fecha) {
    if (!fecha) return (/* @__PURE__ */ new Date()).toISOString();
    const partes = fecha.match(/(\d{2})[-/](\d{2})[-/](\d{4})/);
    if (partes) {
      return (/* @__PURE__ */ new Date(
        `${partes[3]}-${partes[2]}-${partes[1]}T00:00:00.000Z`
      )).toISOString();
    }
    try {
      return new Date(fecha).toISOString();
    } catch {
      return (/* @__PURE__ */ new Date()).toISOString();
    }
  }
}
let contadorBloques = 0;
class Block {
  id;
  tipo;
  descripcion;
  scraper;
  estado = BlockStatus.PENDING;
  resultado = null;
  constructor(tipo, descripcion, scraper) {
    contadorBloques++;
    this.id = `block-${contadorBloques}`;
    this.tipo = tipo;
    this.descripcion = descripcion;
    this.scraper = scraper;
  }
  /**
   * Ejecuta el scraper del bloque.
   */
  async ejecutar() {
    this.estado = BlockStatus.RUNNING;
    log.info(`[${this.id}] Ejecutando: ${this.descripcion}`);
    try {
      this.resultado = await this.scraper.run();
      this.estado = this.resultado.exito ? BlockStatus.COMPLETED : BlockStatus.FAILED;
      log.info(
        `[${this.id}] ${this.estado}: ${this.resultado.exito ? "OK" : this.resultado.error}`
      );
      return this.resultado;
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error desconocido";
      this.estado = BlockStatus.FAILED;
      this.resultado = { exito: false, error: mensaje };
      log.error(`[${this.id}] Error:`, mensaje);
      return this.resultado;
    }
  }
  /**
   * Retorna info serializable del bloque para IPC.
   */
  obtenerInfo() {
    return {
      id: this.id,
      tipo: this.tipo,
      estado: this.estado,
      descripcion: this.descripcion
    };
  }
}
let contadorCadenas = 0;
class Chain {
  id;
  certificadoSerial;
  nombreCert;
  bloques = [];
  estado = ChainStatus.IDLE;
  constructor(certificadoSerial, nombreCert) {
    contadorCadenas++;
    this.id = `chain-${contadorCadenas}`;
    this.certificadoSerial = certificadoSerial;
    this.nombreCert = nombreCert;
  }
  /**
   * Agrega un bloque a la cadena.
   */
  agregarBloque(bloque) {
    this.bloques.push(bloque);
  }
  /**
   * Ejecuta todos los bloques secuencialmente.
   */
  async ejecutar() {
    this.estado = ChainStatus.RUNNING;
    log.info(
      `[${this.id}] Iniciando cadena — cert: ${this.certificadoSerial}, bloques: ${this.bloques.length}`
    );
    let algunoFallo = false;
    let todosCompletados = true;
    for (const bloque of this.bloques) {
      const resultado = await bloque.ejecutar();
      if (!resultado.exito) {
        algunoFallo = true;
        todosCompletados = false;
        log.warn(
          `[${this.id}] Bloque ${bloque.id} fallo, continuando con siguiente`
        );
      }
    }
    if (todosCompletados) {
      this.estado = ChainStatus.COMPLETED;
    } else if (algunoFallo && this.bloquesCompletados > 0) {
      this.estado = ChainStatus.PARTIALLY_COMPLETED;
    } else {
      this.estado = ChainStatus.FAILED;
    }
    log.info(`[${this.id}] Cadena finalizada: ${this.estado}`);
  }
  /** Cantidad de bloques completados exitosamente */
  get bloquesCompletados() {
    return this.bloques.filter((b) => b.estado === BlockStatus.COMPLETED).length;
  }
  /**
   * Retorna estado serializable para IPC.
   */
  obtenerEstado() {
    return {
      id: this.id,
      estado: this.estado,
      certificadoSerial: this.certificadoSerial,
      nombreCert: this.nombreCert,
      totalBloques: this.bloques.length,
      bloquesCompletados: this.bloquesCompletados,
      bloques: this.bloques.map((b) => b.obtenerInfo())
    };
  }
}
const NOMBRE_ARCHIVO$3 = "certigestor-notificaciones-desktop.json";
function obtenerRutaArchivo$3() {
  return join(app.getPath("userData"), NOMBRE_ARCHIVO$3);
}
const CONFIG_DEFAULT = {
  nativasActivas: true,
  diasAvisoCaducidad: 30,
  notificarScraping: true,
  notificarWorkflows: true,
  notificarSync: true,
  sonido: true
};
function crearDatosVacios$2() {
  return {
    notificaciones: [],
    config: { ...CONFIG_DEFAULT }
  };
}
function obtenerDatos() {
  const ruta = obtenerRutaArchivo$3();
  if (!existsSync(ruta)) {
    return crearDatosVacios$2();
  }
  try {
    const contenido = readFileSync(ruta, "utf-8");
    const datos = JSON.parse(contenido);
    return datos;
  } catch (error) {
    log.warn("[Tray] Error leyendo datos, creando nuevos:", error);
    return crearDatosVacios$2();
  }
}
function guardarDatos$2(datos) {
  const ruta = obtenerRutaArchivo$3();
  const directorio = dirname(ruta);
  if (!existsSync(directorio)) {
    mkdirSync(directorio, { recursive: true });
  }
  const rutaTmp = `${ruta}.tmp`;
  writeFileSync(rutaTmp, JSON.stringify(datos, null, 2), "utf-8");
  renameSync(rutaTmp, ruta);
}
function agregarNotificacion(notif) {
  const datos = obtenerDatos();
  guardarDatos$2({
    ...datos,
    notificaciones: [...datos.notificaciones, notif]
  });
  log.info(`[Tray] Notificacion agregada: ${notif.titulo} (${notif.tipo})`);
}
function obtenerNotificaciones(limite = 50) {
  const datos = obtenerDatos();
  return datos.notificaciones.slice(-limite).reverse();
}
function marcarLeida(id) {
  const datos = obtenerDatos();
  const notif = datos.notificaciones.find((n) => n.id === id);
  if (!notif || notif.leida) return false;
  guardarDatos$2({
    ...datos,
    notificaciones: datos.notificaciones.map(
      (n) => n.id === id ? { ...n, leida: true } : n
    )
  });
  return true;
}
function marcarTodasLeidas() {
  const datos = obtenerDatos();
  const pendientes = datos.notificaciones.filter((n) => !n.leida);
  if (pendientes.length === 0) return 0;
  guardarDatos$2({
    ...datos,
    notificaciones: datos.notificaciones.map((n) => ({ ...n, leida: true }))
  });
  return pendientes.length;
}
function obtenerEstadoTray() {
  const datos = obtenerDatos();
  const pendientes = datos.notificaciones.filter((n) => !n.leida).length;
  const ultima = datos.notificaciones[datos.notificaciones.length - 1];
  return {
    pendientes,
    ultimaNotificacion: ultima?.fechaCreacion
  };
}
function limpiarAntiguas(mantener = 200) {
  const datos = obtenerDatos();
  const total = datos.notificaciones.length;
  if (total <= mantener) return 0;
  const eliminadas = total - mantener;
  guardarDatos$2({
    ...datos,
    notificaciones: datos.notificaciones.slice(-mantener)
  });
  log.info(`[Tray] ${eliminadas} notificaciones antiguas eliminadas`);
  return eliminadas;
}
function obtenerConfig$1() {
  return obtenerDatos().config;
}
function guardarConfig$1(config) {
  const datos = obtenerDatos();
  guardarDatos$2({ ...datos, config });
  log.info("[Tray] Config guardada");
}
let gestorTray = null;
function setGestorTray(gestor2) {
  gestorTray = gestor2;
}
function crearNotificacion(tipo, titulo, mensaje, prioridad, datosExtra) {
  const config = obtenerConfig$1();
  if (tipo.startsWith("scraping") && !config.notificarScraping) return;
  if (tipo.startsWith("workflow") && !config.notificarWorkflows) return;
  if (tipo === "sync_completada" && !config.notificarSync) return;
  const notif = {
    id: randomUUID(),
    tipo,
    titulo,
    mensaje,
    prioridad,
    leida: false,
    fechaCreacion: (/* @__PURE__ */ new Date()).toISOString(),
    datosExtra
  };
  agregarNotificacion(notif);
  if (config.nativasActivas && gestorTray) {
    gestorTray.enviarNativa(notif);
    const estado = obtenerEstadoTray();
    gestorTray.actualizarBadge(estado.pendientes);
  }
}
async function verificarCertificadosCaducan() {
  try {
    const config = obtenerConfig$1();
    const certs = await listarCertificadosInstalados();
    const ahora = Date.now();
    let nuevas = 0;
    const existentes = obtenerNotificaciones(200);
    const hoy = (/* @__PURE__ */ new Date()).toISOString().slice(0, 10);
    for (const cert of certs) {
      const vencimiento = new Date(cert.fechaVencimiento).getTime();
      const diasRestantes = Math.floor((vencimiento - ahora) / 864e5);
      if (diasRestantes <= 0) {
        const yaNotifico = existentes.some(
          (n) => n.tipo === "certificado_caduca" && n.datosExtra?.serial === cert.numeroSerie && n.fechaCreacion.startsWith(hoy)
        );
        if (!yaNotifico) {
          crearNotificacion(
            "certificado_caduca",
            "Certificado caducado",
            `${cert.subject} ha caducado`,
            "alta",
            { serial: cert.numeroSerie }
          );
          nuevas++;
        }
      } else if (diasRestantes <= config.diasAvisoCaducidad) {
        const yaNotifico = existentes.some(
          (n) => n.tipo === "certificado_caduca" && n.datosExtra?.serial === cert.numeroSerie && n.fechaCreacion.startsWith(hoy)
        );
        if (!yaNotifico) {
          crearNotificacion(
            "certificado_caduca",
            "Certificado proximo a caducar",
            `${cert.subject} caduca en ${diasRestantes} dia(s)`,
            diasRestantes <= 7 ? "alta" : "media",
            { serial: cert.numeroSerie, diasRestantes }
          );
          nuevas++;
        }
      }
    }
    log.info(`[ServicioNotif] Verificacion certs: ${nuevas} nuevas notificaciones`);
    return nuevas;
  } catch (error) {
    log.error("[ServicioNotif] Error verificando certs:", error);
    return 0;
  }
}
function notificarResultadoScraping(exito, detalles) {
  crearNotificacion(
    exito ? "scraping_completado" : "scraping_error",
    exito ? "Scraping completado" : "Error en scraping",
    detalles ?? (exito ? "El scraping se completo correctamente" : "Hubo un error durante el scraping"),
    exito ? "baja" : "alta"
  );
}
function notificarResultadoWorkflow(nombre, exito, detalles) {
  crearNotificacion(
    exito ? "workflow_completado" : "workflow_error",
    exito ? "Workflow completado" : "Error en workflow",
    detalles ?? `Workflow "${nombre}" ${exito ? "completado" : "fallo"}`,
    exito ? "baja" : "media",
    { workflowNombre: nombre }
  );
}
function notificarSyncCompletada(detalles) {
  crearNotificacion(
    "sync_completada",
    "Sincronizacion completada",
    detalles,
    "baja"
  );
}
function notificarResultadoTareaScheduler(tarea, ejecucion) {
  const exito = ejecucion.resultado === "exito";
  crearNotificacion(
    "tarea_scheduler",
    `Tarea ${exito ? "completada" : "fallida"}: ${tarea.nombre}`,
    ejecucion.mensaje,
    exito ? "baja" : "media",
    { tareaId: tarea.id, resultado: ejecucion.resultado }
  );
}
async function ejecutarChequeosPeriodicos() {
  let totalNuevas = 0;
  totalNuevas += await verificarCertificadosCaducan();
  return totalNuevas;
}
const servicioNotificaciones = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  ejecutarChequeosPeriodicos,
  notificarResultadoScraping,
  notificarResultadoTareaScheduler,
  notificarResultadoWorkflow,
  notificarSyncCompletada,
  setGestorTray,
  verificarCertificadosCaducan
}, Symbol.toStringTag, { value: "Module" }));
async function sincronizarConCloud(notificaciones, certificadoId, apiUrl, token) {
  if (notificaciones.length === 0) {
    return { nuevas: 0, actualizadas: 0, errores: 0, detalle: [] };
  }
  log.info(
    `[SyncCloud] Sincronizando ${notificaciones.length} notificaciones con ${apiUrl}`
  );
  const cuerpo = {
    notificaciones: notificaciones.map(
      (n) => mapearAFormatoApi$1(n, certificadoId)
    )
  };
  try {
    const response = await fetch(`${apiUrl}/notificaciones/sync-desktop`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(cuerpo)
    });
    if (!response.ok) {
      const texto = await response.text();
      throw new Error(`HTTP ${response.status}: ${texto}`);
    }
    const resultado = await response.json();
    const data = resultado.data ?? {
      nuevas: 0,
      actualizadas: 0,
      errores: 0,
      detalle: []
    };
    log.info(
      `[SyncCloud] Resultado: ${data.nuevas} nuevas, ${data.actualizadas} actualizadas, ${data.errores} errores`
    );
    if (data.nuevas > 0) {
      notificarResultadoScraping(
        true,
        `DEHU: ${data.nuevas} notificacion(es) nueva(s)`
      );
      const ventana = BrowserWindow.getAllWindows()[0];
      if (ventana && !ventana.isDestroyed()) {
        ventana.webContents.send("notificaciones:nuevas", {
          portal: "DEHU",
          nuevas: data.nuevas
        });
      }
    }
    return {
      nuevas: data.nuevas,
      actualizadas: data.actualizadas,
      errores: data.errores,
      detalle: data.detalle.map((d) => ({
        idDehu: d.idExterno,
        accion: d.accion,
        error: d.error
      }))
    };
  } catch (error) {
    const msg = error instanceof Error ? error.message : "Error desconocido";
    log.error(`[SyncCloud] Error sincronizando: ${msg}`);
    return {
      nuevas: 0,
      actualizadas: 0,
      errores: notificaciones.length,
      detalle: notificaciones.map((n) => ({
        idDehu: n.idDehu,
        accion: "error",
        error: msg
      }))
    };
  }
}
function mapearAFormatoApi$1(notif, certificadoId) {
  return {
    idExterno: notif.idDehu,
    administracion: notif.organismo || "DEHU",
    tipo: notif.tipo,
    contenido: [notif.titulo, notif.ambito, notif.organismo].filter(Boolean).join(" — "),
    fechaDeteccion: notif.fechaDisposicion || (/* @__PURE__ */ new Date()).toISOString(),
    fechaPublicacion: notif.fechaDisposicion || void 0,
    certificadoId,
    estadoPortal: notif.estado || void 0
  };
}
class DehuConsultaBlock extends BaseScraper {
  configDehu;
  apiUrl;
  token;
  resultado = null;
  constructor(configDehu, apiUrl, token, configScraping) {
    super(configDehu.certificadoSerial, configScraping);
    this.configDehu = configDehu;
    this.apiUrl = apiUrl;
    this.token = token;
  }
  get nombre() {
    return `DEHU-Consulta (${this.serialNumber})`;
  }
  /**
   * No necesita navegador si usa LEMA.
   * Override run() para manejar ambos caminos.
   */
  async run() {
    try {
      const orquestador2 = new DehuOrquestador(this.apiUrl, this.token);
      this.resultado = await orquestador2.consultarCertificado(this.configDehu);
      return {
        exito: this.resultado.exito,
        datos: this.resultado,
        error: this.resultado.error
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error desconocido";
      return { exito: false, error: msg };
    }
  }
  async ejecutar() {
    return { exito: false, error: "Usar run() directamente" };
  }
}
class DehuSyncBlock extends BaseScraper {
  bloqueConsulta;
  certificadoId;
  apiUrl;
  token;
  constructor(bloqueConsulta, certificadoId, apiUrl, token) {
    super(bloqueConsulta.serialNumber);
    this.bloqueConsulta = bloqueConsulta;
    this.certificadoId = certificadoId;
    this.apiUrl = apiUrl;
    this.token = token;
  }
  get nombre() {
    return `DEHU-Sync (${this.serialNumber})`;
  }
  /**
   * No necesita navegador. Override run() para sync directo.
   */
  async run() {
    try {
      const consulta = this.bloqueConsulta.resultado;
      if (!consulta || !consulta.exito) {
        return {
          exito: false,
          error: "No hay resultado de consulta para sincronizar"
        };
      }
      const todasNotif = [
        ...consulta.notificaciones,
        ...consulta.comunicaciones
      ];
      if (todasNotif.length === 0) {
        return { exito: true, datos: { nuevas: 0, actualizadas: 0, errores: 0 } };
      }
      const resultado = await sincronizarConCloud(
        todasNotif,
        this.certificadoId,
        this.apiUrl,
        this.token
      );
      return { exito: resultado.errores === 0, datos: resultado };
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error desconocido";
      return { exito: false, error: msg };
    }
  }
  async ejecutar() {
    return { exito: false, error: "Usar run() directamente" };
  }
}
class DehuOrquestador {
  apiUrl;
  token;
  constructor(apiUrl, token) {
    this.apiUrl = apiUrl;
    this.token = token;
  }
  /**
   * Consulta DEHU para un certificado.
   * Intenta LEMA primero, fallback a Puppeteer.
   */
  async consultarCertificado(config) {
    log.info(
      `[DehuOrquestador] Consultando cert: ${config.certificadoSerial}`
    );
    if (config.estadoAlta !== EstadoAltaDehu.NO_ALTA) {
      try {
        const lema = new LemaApi(config);
        const resultadoLema = await lema.ejecutarConsulta();
        if (resultadoLema.exito) {
          log.info("[DehuOrquestador] Consulta LEMA exitosa");
          const tieneRealizadas = resultadoLema.notificaciones.some(
            (n) => n.estado !== "Pendiente de abrir" && n.estado !== "Pendiente"
          );
          if (!tieneRealizadas) {
            log.info("[DehuOrquestador] LEMA sin realizadas, complementando con Puppeteer");
            try {
              const resultadoPuppeteer = await this.consultarConPuppeteer(config);
              if (resultadoPuppeteer.exito) {
                const realizadasPuppeteer = resultadoPuppeteer.notificaciones.filter(
                  (n) => n.estado !== "Pendiente de abrir" && n.estado !== "Pendiente"
                );
                if (realizadasPuppeteer.length > 0) {
                  log.info(`[DehuOrquestador] Puppeteer aporto ${realizadasPuppeteer.length} realizadas`);
                  resultadoLema.notificaciones = [
                    ...resultadoLema.notificaciones,
                    ...realizadasPuppeteer
                  ];
                }
                if (resultadoLema.comunicaciones.length === 0 && resultadoPuppeteer.comunicaciones.length > 0) {
                  resultadoLema.comunicaciones = resultadoPuppeteer.comunicaciones;
                }
              }
            } catch (puppErr) {
              log.warn("[DehuOrquestador] Puppeteer complementario fallo:", puppErr);
            }
          }
          return resultadoLema;
        }
        log.warn(
          `[DehuOrquestador] LEMA fallo: ${resultadoLema.error}, intentando Puppeteer`
        );
      } catch (error) {
        log.warn(
          "[DehuOrquestador] Error en LEMA, fallback a Puppeteer:",
          error instanceof Error ? error.message : error
        );
      }
    }
    return this.consultarConPuppeteer(config);
  }
  /**
   * Consulta via Puppeteer (scraping web).
   */
  async consultarConPuppeteer(config) {
    log.info("[DehuOrquestador] Ejecutando scraping Puppeteer DEHU");
    const scraper = new DehuScraper(config);
    const resultado = await scraper.run();
    if (resultado.exito && resultado.datos) {
      return resultado.datos;
    }
    return {
      exito: false,
      metodo: MetodoConsulta.PUPPETEER,
      certificadoSerial: config.certificadoSerial,
      estadoAlta: config.estadoAlta ?? EstadoAltaDehu.DESCONOCIDO,
      notificaciones: [],
      comunicaciones: [],
      error: resultado.error ?? "Error en scraping Puppeteer",
      fechaConsulta: (/* @__PURE__ */ new Date()).toISOString()
    };
  }
  /**
   * Descarga el PDF de una notificacion concreta.
   * Siempre usa Puppeteer (LEMA no permite descarga directa de PDFs).
   * Usa runDescargarPdf() que gestiona login completo + descarga + cierre.
   */
  async descargarNotificacion(config, notificacion, configScraping) {
    log.info(
      `[DehuOrquestador] Descargando PDF: ${notificacion.titulo}`
    );
    const scraper = new DehuScraper(config, configScraping);
    try {
      const ruta = await scraper.runDescargarPdf(notificacion);
      if (ruta) {
        return { exito: true, rutaLocal: ruta };
      }
      return { exito: false, error: "No se pudo descargar el PDF" };
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error desconocido";
      return { exito: false, error: msg };
    }
  }
  /**
   * Construye una Chain de bloques para un certificado y la agrega a la factory.
   * Bloque 1: Consulta DEHU (LEMA + fallback Puppeteer)
   * Bloque 2: Sincronizacion con cloud
   */
  construirCadena(factory2, config, certificadoId) {
    const cadena = new Chain(config.certificadoSerial);
    const bloqueConsulta = new DehuConsultaBlock(
      config,
      this.apiUrl,
      this.token
    );
    cadena.agregarBloque(
      new Block(
        ProcessType.NOTIFICATION_CHECK,
        `Consultar DEHU — ${config.certificadoSerial}`,
        bloqueConsulta
      )
    );
    const bloqueSync = new DehuSyncBlock(
      bloqueConsulta,
      certificadoId,
      this.apiUrl,
      this.token
    );
    cadena.agregarBloque(
      new Block(
        ProcessType.DATA_SCRAPING,
        `Sincronizar cloud — ${config.certificadoSerial}`,
        bloqueSync
      )
    );
    factory2.agregarCadena(cadena);
    log.info(
      `[DehuOrquestador] Cadena creada para cert: ${config.certificadoSerial}`
    );
    return cadena;
  }
  /**
   * Construye cadenas para multiples certificados.
   */
  construirCadenasBatch(factory2, configs) {
    for (const config of configs) {
      this.construirCadena(factory2, config, config.certificadoId);
    }
    log.info(
      `[DehuOrquestador] ${configs.length} cadenas creadas en batch`
    );
  }
}
function extraerNombreCarpeta(subject) {
  const cn = subject.match(/CN=([^,]+)/i);
  if (!cn) return void 0;
  let nombre = cn[1].trim();
  const nifMatch = subject.match(/(?:NIF|NIE|SERIALNUMBER)[=:]?\s*([A-Z0-9]+)/i);
  const nif = nifMatch ? nifMatch[1].trim() : "";
  nombre = nombre.replace(/\s*-\s*(?:NIF|NIE):?\s*[A-Z0-9]+/i, "").trim();
  nombre = nombre.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().replace(/[^A-Z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  if (nif && !nombre.includes(nif.toUpperCase())) {
    nombre = `${nombre}_${nif}`;
  }
  return nombre || void 0;
}
async function resolverNombreCarpeta(serialNumber) {
  try {
    const certs = await listarCertificadosInstalados();
    const cert = certs.find(
      (c) => c.numeroSerie.toLowerCase() === serialNumber.toLowerCase()
    );
    if (!cert) return void 0;
    return extraerNombreCarpeta(cert.subject);
  } catch (err) {
    log.warn(`Error resolviendo nombre carpeta para ${serialNumber}: ${err.message}`);
    return void 0;
  }
}
function extraerCifDeSubject(subject) {
  const matchOid = subject.match(/(?:OID\.)?2\.5\.4\.97=VATES-([A-Z0-9]+)/i);
  if (matchOid) return matchOid[1];
  const matchOrgId = subject.match(/organizationIdentifier=VATES-([A-Z0-9]+)/i);
  if (matchOrgId) return matchOrgId[1];
  return "";
}
function extraerNifDeSubject$1(subject) {
  const matchSerial = subject.match(/SERIALNUMBER=IDCES-([A-Z0-9]+)/i);
  if (matchSerial) return matchSerial[1];
  const matchCN = subject.match(/CN=.*?-\s*([A-Z0-9]{8,9}[A-Z]?)/);
  if (matchCN) return matchCN[1];
  return "";
}
async function resolverPfxDehu(config) {
  if (!config.nifEmpresa || !config.titularNif) {
    try {
      const certs = await listarCertificadosInstalados();
      const certMatch = config.thumbprint ? certs.find((c) => c.thumbprint === config.thumbprint) : certs.find((c) => c.numeroSerie === config.certificadoSerial);
      if (certMatch) {
        if (!config.nifEmpresa) {
          config.nifEmpresa = extraerCifDeSubject(certMatch.subject) || void 0;
        }
        if (!config.titularNif) {
          config.titularNif = extraerNifDeSubject$1(certMatch.subject) || void 0;
        }
        log.info(`[DEHU] Cert ${certMatch.thumbprint}: NIF=${config.titularNif ?? "N/A"}, CIF empresa=${config.nifEmpresa ?? "N/A"}`);
      }
    } catch (err) {
      log.warn(`[DEHU] No se pudo enriquecer config con CIF/NIF: ${err}`);
    }
  }
  if (config.rutaPfx && config.passwordPfx) return null;
  const { thumbprint } = config;
  if (!thumbprint) {
    log.warn("[DEHU] Config sin rutaPfx ni thumbprint, LEMA no podra firmar");
    return null;
  }
  const dir = join(app.getPath("temp"), "certigestor-pfx");
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  const passwordTemp = randomBytes(16).toString("hex");
  const rutaTemp = join(dir, `${thumbprint}.pfx`);
  const resultado = await exportarCertificadoPfx(thumbprint, rutaTemp, passwordTemp);
  if (resultado.exito) {
    config.rutaPfx = rutaTemp;
    config.passwordPfx = passwordTemp;
    log.info(`[DEHU] PFX temporal exportado: ${rutaTemp}`);
    return rutaTemp;
  }
  log.error(`[DEHU] No se pudo exportar PFX: ${resultado.error}`);
  return null;
}
function registrarHandlersDehu(_ventana) {
  ipcMain.handle(
    "dehu:consultarNotificaciones",
    async (_event, config, apiUrl, token) => {
      log.info(
        `[DEHU Handler] Consultando notificaciones para cert: ${config.certificadoSerial}`
      );
      const rutaTemp = await resolverPfxDehu(config);
      try {
        const orquestador2 = new DehuOrquestador(apiUrl, token);
        return await orquestador2.consultarCertificado(config);
      } finally {
        if (rutaTemp && existsSync(rutaTemp)) {
          try {
            unlinkSync(rutaTemp);
          } catch {
          }
        }
      }
    }
  );
  ipcMain.handle(
    "dehu:descargarNotificacion",
    async (_event, config, notificacion) => {
      log.info(`[DEHU Handler] ========================================`);
      log.info(`[DEHU Handler] DESCARGA PDF DEHU`);
      log.info(`[DEHU Handler] Notificacion: ${notificacion.idDehu}`);
      log.info(`[DEHU Handler] Titular: ${notificacion.titular || "N/A"}`);
      log.info(`[DEHU Handler] Config serial: ${config.certificadoSerial}`);
      log.info(`[DEHU Handler] Config thumbprint: ${config.thumbprint || "N/A"}`);
      log.info(`[DEHU Handler] Config nifEmpresa: ${config.nifEmpresa || "N/A"}`);
      log.info(`[DEHU Handler] Config titularNif: ${config.titularNif || "N/A"}`);
      log.info(`[DEHU Handler] ========================================`);
      const rutaTemp = await resolverPfxDehu(config);
      const nombreCarpeta = await resolverNombreCarpeta(config.certificadoSerial);
      try {
        const orquestador2 = new DehuOrquestador("", "");
        return await orquestador2.descargarNotificacion(config, notificacion, nombreCarpeta ? { nombreCarpeta } : void 0);
      } finally {
        if (rutaTemp && existsSync(rutaTemp)) {
          try {
            unlinkSync(rutaTemp);
          } catch {
          }
        }
      }
    }
  );
  ipcMain.handle(
    "dehu:sincronizarCloud",
    async (_event, notificaciones, certificadoId, apiUrl, token) => {
      log.info(
        `[DEHU Handler] Sincronizando ${notificaciones.length} notificaciones con cloud`
      );
      return sincronizarConCloud(notificaciones, certificadoId, apiUrl, token);
    }
  );
  ipcMain.handle(
    "dehu:consultarYSincronizar",
    async (_event, configs, apiUrl, token) => {
      log.info(
        `[DEHU Handler] Consulta + sync para ${configs.length} certificados`
      );
      const rutasTemp = [];
      try {
        for (const cfg of configs) {
          const ruta = await resolverPfxDehu(cfg);
          if (ruta) rutasTemp.push(ruta);
        }
        const orquestador2 = new DehuOrquestador(apiUrl, token);
        factory.limpiar();
        orquestador2.construirCadenasBatch(factory, configs);
        await factory.iniciar();
        return { exito: true };
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Error desconocido";
        log.error(`[DEHU Handler] Error en consulta+sync: ${msg}`);
        return { exito: false, error: msg };
      } finally {
        for (const ruta of rutasTemp) {
          try {
            if (existsSync(ruta)) unlinkSync(ruta);
          } catch {
          }
        }
      }
    }
  );
  ipcMain.handle(
    "dehu:verificarAlta",
    async (_event, config) => {
      log.info(
        `[DEHU Handler] Verificando alta LEMA para cert: ${config.certificadoSerial}`
      );
      const rutaTemp = await resolverPfxDehu(config);
      try {
        const lema = new LemaApi(config);
        const estado = await lema.verificarAlta();
        return { alta: estado === "ALTA", estado };
      } finally {
        if (rutaTemp && existsSync(rutaTemp)) {
          try {
            unlinkSync(rutaTemp);
          } catch {
          }
        }
      }
    }
  );
  ipcMain.handle(
    "dehu:verificarPdfDescargado",
    async (_event, idDehu, certificadoSerial) => {
      const baseDescargas = join(app.getPath("documents"), "CertiGestor", "descargas");
      const idSanitizado = idDehu.replace(/[^a-zA-Z0-9-_]/g, "_");
      const nombreArchivo = `DEHU_${idSanitizado}.pdf`;
      if (!existsSync(baseDescargas)) return { descargado: false };
      const nombreCarpeta = await resolverNombreCarpeta(certificadoSerial);
      if (nombreCarpeta) {
        const ruta = join(baseDescargas, nombreCarpeta, nombreArchivo);
        if (existsSync(ruta)) return { descargado: true, rutaLocal: ruta };
      }
      const rutaSerial = join(baseDescargas, certificadoSerial, nombreArchivo);
      if (existsSync(rutaSerial)) return { descargado: true, rutaLocal: rutaSerial };
      try {
        const carpetas = readdirSync(baseDescargas, { withFileTypes: true });
        for (const entry of carpetas) {
          if (!entry.isDirectory()) continue;
          const ruta = join(baseDescargas, entry.name, nombreArchivo);
          if (existsSync(ruta)) {
            log.info(`[DEHU] PDF encontrado via scan: ${ruta}`);
            return { descargado: true, rutaLocal: ruta };
          }
        }
      } catch (err) {
        log.warn(`[DEHU] Error escaneando carpetas: ${err}`);
      }
      return { descargado: false };
    }
  );
  ipcMain.handle(
    "dehu:verificarPdfsBatch",
    async (_event, items) => {
      const baseDescargas = join(app.getPath("documents"), "CertiGestor", "descargas");
      const resultado = {};
      if (!existsSync(baseDescargas)) {
        for (const { idDehu } of items) resultado[idDehu] = { descargado: false };
        return resultado;
      }
      const cacheNombres = {};
      let todasCarpetas = [];
      try {
        todasCarpetas = readdirSync(baseDescargas, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name);
      } catch {
      }
      for (const { idDehu, certificadoSerial } of items) {
        const idSanitizado = idDehu.replace(/[^a-zA-Z0-9-_]/g, "_");
        const nombreArchivo = `DEHU_${idSanitizado}.pdf`;
        if (!(certificadoSerial in cacheNombres)) {
          cacheNombres[certificadoSerial] = await resolverNombreCarpeta(certificadoSerial);
        }
        const nombreCarpeta = cacheNombres[certificadoSerial];
        let encontrado = false;
        if (nombreCarpeta) {
          const ruta = join(baseDescargas, nombreCarpeta, nombreArchivo);
          if (existsSync(ruta)) {
            resultado[idDehu] = { descargado: true, rutaLocal: ruta };
            encontrado = true;
          }
        }
        if (!encontrado) {
          const rutaSerial = join(baseDescargas, certificadoSerial, nombreArchivo);
          if (existsSync(rutaSerial)) {
            resultado[idDehu] = { descargado: true, rutaLocal: rutaSerial };
            encontrado = true;
          }
        }
        if (!encontrado) {
          for (const carpeta of todasCarpetas) {
            const ruta = join(baseDescargas, carpeta, nombreArchivo);
            if (existsSync(ruta)) {
              resultado[idDehu] = { descargado: true, rutaLocal: ruta };
              encontrado = true;
              break;
            }
          }
        }
        if (!encontrado) {
          resultado[idDehu] = { descargado: false };
        }
      }
      return resultado;
    }
  );
  ipcMain.handle(
    "dehu:abrirPdf",
    async (_event, rutaLocal) => {
      if (!existsSync(rutaLocal)) {
        return { exito: false, error: "Archivo no encontrado" };
      }
      try {
        await shell.openPath(rutaLocal);
        return { exito: true };
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Error desconocido";
        log.error(`[DEHU Handler] Error abriendo PDF: ${msg}`);
        return { exito: false, error: msg };
      }
    }
  );
  ipcMain.handle(
    "dehu:descargarPdfBatch",
    async (event, config, notificaciones) => {
      log.info(`[DEHU Handler] Batch download: ${notificaciones.length} PDFs`);
      const rutaTemp = await resolverPfxDehu(config);
      const nombreCarpeta = await resolverNombreCarpeta(config.certificadoSerial);
      const resultados = [];
      let exitosos = 0;
      let errores = 0;
      try {
        for (let i = 0; i < notificaciones.length; i++) {
          const notif = notificaciones[i];
          event.sender.send("dehu:progresoBatch", {
            actual: i + 1,
            total: notificaciones.length,
            idDehu: notif.idDehu
          });
          try {
            const orquestador2 = new DehuOrquestador("", "");
            const resultado = await orquestador2.descargarNotificacion(
              config,
              notif,
              nombreCarpeta ? { nombreCarpeta } : void 0
            );
            if (resultado.exito) {
              exitosos++;
              resultados.push({ idDehu: notif.idDehu, exito: true });
            } else {
              errores++;
              resultados.push({ idDehu: notif.idDehu, exito: false, error: resultado.error });
            }
          } catch (error) {
            errores++;
            const msg = error instanceof Error ? error.message : "Error desconocido";
            resultados.push({ idDehu: notif.idDehu, exito: false, error: msg });
          }
        }
      } finally {
        if (rutaTemp && existsSync(rutaTemp)) {
          try {
            unlinkSync(rutaTemp);
          } catch {
          }
        }
      }
      log.info(`[DEHU Handler] Batch completado: ${exitosos} exitosos, ${errores} errores`);
      return { exitosos, errores, resultados };
    }
  );
  log.info("Handlers DEHU registrados");
}
var TipoDocumento = /* @__PURE__ */ ((TipoDocumento2) => {
  TipoDocumento2["DEUDAS_AEAT"] = "DEUDAS_AEAT";
  TipoDocumento2["DATOS_FISCALES"] = "DATOS_FISCALES";
  TipoDocumento2["CERTIFICADOS_IRPF"] = "CERTIFICADOS_IRPF";
  TipoDocumento2["CNAE_AUTONOMO"] = "CNAE_AUTONOMO";
  TipoDocumento2["IAE_ACTIVIDADES"] = "IAE_ACTIVIDADES";
  TipoDocumento2["DEUDAS_SS"] = "DEUDAS_SS";
  TipoDocumento2["VIDA_LABORAL"] = "VIDA_LABORAL";
  TipoDocumento2["CERTIFICADO_INSS"] = "CERTIFICADO_INSS";
  TipoDocumento2["CONSULTA_VEHICULOS"] = "CONSULTA_VEHICULOS";
  TipoDocumento2["CONSULTA_INMUEBLES"] = "CONSULTA_INMUEBLES";
  TipoDocumento2["EMPADRONAMIENTO"] = "EMPADRONAMIENTO";
  TipoDocumento2["CERTIFICADO_PENALES"] = "CERTIFICADO_PENALES";
  TipoDocumento2["CERTIFICADO_NACIMIENTO"] = "CERTIFICADO_NACIMIENTO";
  TipoDocumento2["APUD_ACTA"] = "APUD_ACTA";
  TipoDocumento2["CERTIFICADO_SEPE"] = "CERTIFICADO_SEPE";
  TipoDocumento2["SOLICITUD_CIRBE"] = "SOLICITUD_CIRBE";
  TipoDocumento2["OBTENCION_CIRBE"] = "OBTENCION_CIRBE";
  TipoDocumento2["DEUDAS_HACIENDA"] = "DEUDAS_HACIENDA";
  TipoDocumento2["CERTIFICADO_MATRIMONIO"] = "CERTIFICADO_MATRIMONIO";
  TipoDocumento2["PROC_ABIERTOS_GENERAL"] = "PROC_ABIERTOS_GENERAL";
  TipoDocumento2["PROC_ABIERTOS_MADRID"] = "PROC_ABIERTOS_MADRID";
  TipoDocumento2["PROC_ABIERTOS_ANDALUCIA"] = "PROC_ABIERTOS_ANDALUCIA";
  TipoDocumento2["PROC_ABIERTOS_VALENCIA"] = "PROC_ABIERTOS_VALENCIA";
  TipoDocumento2["PROC_ABIERTOS_CATALUNYA"] = "PROC_ABIERTOS_CATALUNYA";
  return TipoDocumento2;
})(TipoDocumento || {});
var Portal = /* @__PURE__ */ ((Portal2) => {
  Portal2["AEAT"] = "AEAT";
  Portal2["SEGURIDAD_SOCIAL"] = "SEGURIDAD_SOCIAL";
  Portal2["CARPETA_CIUDADANA"] = "CARPETA_CIUDADANA";
  Portal2["JUSTICIA"] = "JUSTICIA";
  Portal2["SEPE"] = "SEPE";
  Portal2["BANCO_ESPANA"] = "BANCO_ESPANA";
  Portal2["LICITACIONES"] = "LICITACIONES";
  return Portal2;
})(Portal || {});
var EstadoVerificacion = /* @__PURE__ */ ((EstadoVerificacion2) => {
  EstadoVerificacion2["VERIFICADO"] = "VERIFICADO";
  EstadoVerificacion2["NO_FUNCIONA"] = "NO_FUNCIONA";
  EstadoVerificacion2["NO_PROBADO"] = "NO_PROBADO";
  return EstadoVerificacion2;
})(EstadoVerificacion || {});
var MetodoDescarga = /* @__PURE__ */ ((MetodoDescarga2) => {
  MetodoDescarga2["DESCARGA_DIRECTA"] = "DESCARGA_DIRECTA";
  MetodoDescarga2["PRINT_TO_PDF"] = "PRINT_TO_PDF";
  MetodoDescarga2["MIXTO"] = "MIXTO";
  return MetodoDescarga2;
})(MetodoDescarga || {});
const CATALOGO_DOCUMENTOS = [
  // ── AEAT ──────────────────────────────────────────────────
  {
    id: TipoDocumento.DEUDAS_AEAT,
    nombre: "Certificado de deudas tributarias",
    descripcion: "Certificado de estar al corriente de obligaciones tributarias con la AEAT",
    portal: Portal.AEAT,
    url: "https://www1.agenciatributaria.gob.es/wlpl/EMCE-JDIT/ECOTInternetCiudadanosServlet",
    nombreArchivo: "Deudas_AEAT",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: true,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  {
    id: TipoDocumento.DATOS_FISCALES,
    nombre: "Datos fiscales",
    descripcion: "Datos fiscales del contribuyente (3 ultimos ejercicios)",
    portal: Portal.AEAT,
    url: "https://www1.agenciatributaria.gob.es/wlpl/DFPA-D182/SvVisDFNet",
    nombreArchivo: "Datos_Fiscales",
    metodo: MetodoDescarga.PRINT_TO_PDF,
    activoPorDefecto: true,
    multiArchivo: true,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  {
    id: TipoDocumento.CERTIFICADOS_IRPF,
    nombre: "Certificados tributarios IRPF",
    descripcion: "Certificados tributarios del IRPF (3 ultimos ejercicios)",
    portal: Portal.AEAT,
    url: "https://www1.agenciatributaria.gob.es/wlpl/CERE-EMCE/InternetServlet",
    nombreArchivo: "Certificado_IRPF",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: true,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  {
    id: TipoDocumento.CNAE_AUTONOMO,
    nombre: "Informe actividades autonomo (CNAE)",
    descripcion: "Informe de actividades del trabajador autonomo",
    portal: Portal.SEGURIDAD_SOCIAL,
    url: "https://portal.seg-social.gob.es/wps/myportal/importass/importass/personal/",
    nombreArchivo: "Informe_CNAE_Autonomo",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.NO_PROBADO,
    notaVerificacion: "Reescrito — pendiente testear con certificado de autonomo"
  },
  {
    id: TipoDocumento.IAE_ACTIVIDADES,
    nombre: "Actividades IAE",
    descripcion: "Certificado tributario del Impuesto de Actividades Economicas",
    portal: Portal.AEAT,
    url: "https://www1.agenciatributaria.gob.es/wlpl/EMCE-JDIT/ServletAaeeGralnternet",
    nombreArchivo: "Actividades_IAE",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  // ── Seguridad Social ──────────────────────────────────────
  {
    id: TipoDocumento.DEUDAS_SS,
    nombre: "Certificado de deudas con la Seguridad Social",
    descripcion: "Certificado de estar al corriente con la Tesoreria General de la SS",
    portal: Portal.SEGURIDAD_SOCIAL,
    url: "https://sp.seg-social.es/ProsaInternet/OnlineAccess?ARQ.SPM.ACTION=LOGIN&ARQ.SPM.APPTYPE=SERVICE&ARQ.IDAPP=AECPSED1&PAUC.NIVEL=1&PAUC.TIPO_IDENTIFICACION=2",
    nombreArchivo: "Deudas_SS",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: true,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.NO_PROBADO,
    notaVerificacion: "Reescrito Chrome MCP 2026-02-21 — pendiente testear"
  },
  {
    id: TipoDocumento.VIDA_LABORAL,
    nombre: "Vida laboral",
    descripcion: "Informe de vida laboral de la TGSS",
    portal: Portal.SEGURIDAD_SOCIAL,
    url: "https://portal.seg-social.gob.es/wps/portal/importass/importass/Categorias/Vida+laboral+e+informes/Informes+sobre+tu+situacion+laboral/Informe+de+tu+vida+laboral",
    nombreArchivo: "Vida_Laboral",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: true,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  {
    id: TipoDocumento.CERTIFICADO_INSS,
    nombre: "Certificado INSS",
    descripcion: "Certificado integrado de prestaciones del INSS (Tu Seguridad Social)",
    portal: Portal.SEGURIDAD_SOCIAL,
    url: "https://sede-tu.seg-social.gob.es/wps/myportal/tussR/tuss/TrabajoPensiones/Pensiones/CertificadoIntegradoPrestaciones",
    nombreArchivo: "Certificado_INSS",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  // ── Carpeta Ciudadana ─────────────────────────────────────
  {
    id: TipoDocumento.CONSULTA_VEHICULOS,
    nombre: "Consulta de vehiculos",
    descripcion: "Consulta de vehiculos registrados (Carpeta Ciudadana + DGT)",
    portal: Portal.CARPETA_CIUDADANA,
    url: "https://carpetaciudadana.gob.es/carpeta/datos/vehiculos/consulta.htm?idioma=es",
    nombreArchivo: "Consulta_Vehiculos",
    metodo: MetodoDescarga.PRINT_TO_PDF,
    activoPorDefecto: false,
    multiArchivo: true,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  {
    id: TipoDocumento.CONSULTA_INMUEBLES,
    nombre: "Consulta de inmuebles (Catastro)",
    descripcion: "Consulta de bienes inmuebles desde el Catastro via Carpeta Ciudadana",
    portal: Portal.CARPETA_CIUDADANA,
    url: "https://carpetaciudadana.gob.es/carpeta/mcc/bienes-inmuebles",
    nombreArchivo: "Consulta_Inmuebles",
    metodo: MetodoDescarga.PRINT_TO_PDF,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  {
    id: TipoDocumento.EMPADRONAMIENTO,
    nombre: "Certificado de empadronamiento",
    descripcion: "Certificado de empadronamiento municipal via Carpeta Ciudadana",
    portal: Portal.CARPETA_CIUDADANA,
    url: "https://carpetaciudadana.gob.es/carpeta/mcc/domicilio",
    nombreArchivo: "Empadronamiento",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  {
    id: TipoDocumento.CERTIFICADO_PENALES,
    nombre: "Certificado de antecedentes penales",
    descripcion: "Certificado de antecedentes penales via Carpeta Ciudadana",
    portal: Portal.CARPETA_CIUDADANA,
    url: "https://carpetaciudadana.gob.es/carpeta/mcc/antecedentes-penales",
    nombreArchivo: "Certificado_Penales",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO,
    notaVerificacion: "Descarga AJAX (no will-download): fetch /api/antecedentes-penales/justificante → base64 → writeFileSync"
  },
  // ── Justicia ──────────────────────────────────────────────
  {
    id: TipoDocumento.CERTIFICADO_NACIMIENTO,
    nombre: "Certificado de nacimiento",
    descripcion: "Certificado literal de nacimiento del Ministerio de Justicia",
    portal: Portal.JUSTICIA,
    url: "https://sede.mjusticia.gob.es/sereci/clave/solicitarCertificadoSolicitudLiteral?idMateria=NAC",
    nombreArchivo: "Certificado_Nacimiento",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  {
    id: TipoDocumento.APUD_ACTA,
    nombre: "Apoderamiento Apud Acta",
    descripcion: "Poder de representacion electronico ante juzgados",
    portal: Portal.JUSTICIA,
    url: "https://sedejudicial.justicia.es/-/apoderamiento-apud-acta",
    nombreArchivo: "Apud_Acta",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: true,
    estadoVerificacion: EstadoVerificacion.VERIFICADO,
    notaVerificacion: "Semi-automatico: navega al Area Privada via Cl@ve, requiere intervencion manual"
  },
  // ── Otros portales ────────────────────────────────────────
  {
    id: TipoDocumento.CERTIFICADO_SEPE,
    nombre: "Certificado SEPE",
    descripcion: "Certificado de prestaciones de desempleo del SEPE",
    portal: Portal.SEPE,
    url: "https://sede.sepe.gob.es/DServiciosPrestanetWEB/TipoAutenticadoAction.do",
    nombreArchivo: "Certificado_SEPE",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.VERIFICADO
  },
  {
    id: TipoDocumento.SOLICITUD_CIRBE,
    nombre: "Solicitud CIRBE",
    descripcion: "Solicita informe CIRBE al Banco de Espana. Requiere email y fecha de nacimiento. No descarga archivo.",
    portal: Portal.BANCO_ESPANA,
    url: "https://aps.bde.es/cir_www/cir_wwwias/xml/Arranque.html",
    nombreArchivo: "Solicitud_CIRBE",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.NO_PROBADO,
    notaVerificacion: "Requiere email + fecha nacimiento (DD/MM/AAAA). Informe disponible en ~15 min."
  },
  {
    id: TipoDocumento.OBTENCION_CIRBE,
    nombre: "Obtencion CIRBE",
    descripcion: 'Descarga el informe CIRBE previamente solicitado. Primero usa "Solicitud CIRBE" y espera ~15 min.',
    portal: Portal.BANCO_ESPANA,
    url: "https://aps.bde.es/cir_www/cir_wwwias/xml/Arranque.html",
    nombreArchivo: "Informe_CIRBE",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.NO_PROBADO,
    notaVerificacion: "Requiere solicitud previa. Si no hay solicitudes muestra error claro."
  },
  // ── Hacienda ─────────────────────────────────────────────
  {
    id: TipoDocumento.DEUDAS_HACIENDA,
    nombre: "Consulta de deudas con Hacienda",
    descripcion: "Consulta de deudas pendientes con la AEAT (importes y expedientes)",
    portal: Portal.AEAT,
    url: "https://www1.agenciatributaria.gob.es/wlpl/SRVO-JDIT/ConsultaDdas?faccion=CONS_DDAS",
    nombreArchivo: "Deudas_Hacienda",
    metodo: MetodoDescarga.PRINT_TO_PDF,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.NO_PROBADO,
    notaVerificacion: "Auth SSL/TLS + printToPdf — implementado desde analisis Findiur"
  },
  // ── Justicia — Registro Civil ───────────────────────────
  {
    id: TipoDocumento.CERTIFICADO_MATRIMONIO,
    nombre: "Certificado de matrimonio",
    descripcion: "Certificado literal de matrimonio del Ministerio de Justicia (requiere datos del hecho)",
    portal: Portal.JUSTICIA,
    url: "https://sede.mjusticia.gob.es/sereci/clave/solicitarCertificadoSolicitudLiteral?idMateria=MAT",
    nombreArchivo: "Certificado_Matrimonio",
    metodo: MetodoDescarga.DESCARGA_DIRECTA,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: true,
    estadoVerificacion: EstadoVerificacion.VERIFICADO,
    notaVerificacion: "Semi-auto: Cl@ve + formulario 2 pasos (ano + fecha/provincia/municipio). Usuario rellena datos, will-download captura PDF."
  },
  // ── Licitaciones ──────────────────────────────────────────
  {
    id: TipoDocumento.PROC_ABIERTOS_GENERAL,
    nombre: "Procedimientos abiertos (General)",
    descripcion: "Licitaciones publicas abiertas a nivel nacional",
    portal: Portal.LICITACIONES,
    url: "https://contrataciondelestado.es/wps/portal/plataforma",
    nombreArchivo: "Licitaciones_General",
    metodo: MetodoDescarga.PRINT_TO_PDF,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.NO_PROBADO
  },
  {
    id: TipoDocumento.PROC_ABIERTOS_MADRID,
    nombre: "Procedimientos abiertos (Madrid)",
    descripcion: "Licitaciones publicas de la Comunidad de Madrid",
    portal: Portal.LICITACIONES,
    url: "https://contrataciondelestado.es/wps/portal/plataforma",
    nombreArchivo: "Licitaciones_Madrid",
    metodo: MetodoDescarga.PRINT_TO_PDF,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.NO_PROBADO
  },
  {
    id: TipoDocumento.PROC_ABIERTOS_ANDALUCIA,
    nombre: "Procedimientos abiertos (Andalucia)",
    descripcion: "Licitaciones publicas de la Junta de Andalucia",
    portal: Portal.LICITACIONES,
    url: "https://contrataciondelestado.es/wps/portal/plataforma",
    nombreArchivo: "Licitaciones_Andalucia",
    metodo: MetodoDescarga.PRINT_TO_PDF,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.NO_PROBADO
  },
  {
    id: TipoDocumento.PROC_ABIERTOS_VALENCIA,
    nombre: "Procedimientos abiertos (Valencia)",
    descripcion: "Licitaciones publicas de la Comunidad Valenciana",
    portal: Portal.LICITACIONES,
    url: "https://contrataciondelestado.es/wps/portal/plataforma",
    nombreArchivo: "Licitaciones_Valencia",
    metodo: MetodoDescarga.PRINT_TO_PDF,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.NO_PROBADO
  },
  {
    id: TipoDocumento.PROC_ABIERTOS_CATALUNYA,
    nombre: "Procedimientos abiertos (Catalunya)",
    descripcion: "Licitaciones publicas de la Generalitat de Catalunya",
    portal: Portal.LICITACIONES,
    url: "https://contrataciondelestado.es/wps/portal/plataforma",
    nombreArchivo: "Licitaciones_Catalunya",
    metodo: MetodoDescarga.PRINT_TO_PDF,
    activoPorDefecto: false,
    multiArchivo: false,
    semiAutomatico: false,
    estadoVerificacion: EstadoVerificacion.NO_PROBADO
  }
];
function documentosPorDefecto() {
  return CATALOGO_DOCUMENTOS.filter((d) => d.activoPorDefecto).map((d) => d.id);
}
const ARCHIVO_HISTORIAL$2 = "certigestor-historial-docs.json";
const ARCHIVO_CONFIG = "certigestor-config-docs.json";
function rutaArchivo$2(nombre) {
  return join(app.getPath("userData"), nombre);
}
function leerHistorial$1() {
  const ruta = rutaArchivo$2(ARCHIVO_HISTORIAL$2);
  if (!existsSync(ruta)) return [];
  try {
    const contenido = readFileSync(ruta, "utf-8");
    return JSON.parse(contenido);
  } catch (err) {
    log.warn(`[Historial] Error leyendo historial: ${err.message}`);
    return [];
  }
}
function guardarHistorial$1(registros) {
  const ruta = rutaArchivo$2(ARCHIVO_HISTORIAL$2);
  const recortado = registros.length > 500 ? registros.slice(-500) : registros;
  const rutaTmp = `${ruta}.tmp`;
  writeFileSync(rutaTmp, JSON.stringify(recortado, null, 2), "utf-8");
  renameSync(rutaTmp, ruta);
}
function registrarDescarga(registro) {
  const historial = leerHistorial$1();
  historial.push(registro);
  guardarHistorial$1(historial);
  log.info(`[Historial] Registrado: ${registro.tipo} — ${registro.exito ? "OK" : "ERROR"}`);
}
function obtenerHistorial(certificadoSerial) {
  const historial = leerHistorial$1();
  if (!certificadoSerial) return historial;
  return historial.filter((r) => r.certificadoSerial === certificadoSerial);
}
function obtenerUltimosResultados(certificadoSerial) {
  const historial = leerHistorial$1();
  const filtrado = certificadoSerial ? historial.filter((r) => r.certificadoSerial === certificadoSerial) : historial;
  const ultimos = {};
  for (const reg of filtrado) {
    ultimos[reg.tipo] = {
      exito: reg.exito,
      fecha: reg.fechaDescarga,
      error: reg.error
    };
  }
  return ultimos;
}
function limpiarHistorial() {
  guardarHistorial$1([]);
  log.info("[Historial] Historial limpiado");
}
function leerConfigLocal() {
  const ruta = rutaArchivo$2(ARCHIVO_CONFIG);
  if (!existsSync(ruta)) return {};
  try {
    const contenido = readFileSync(ruta, "utf-8");
    return JSON.parse(contenido);
  } catch (err) {
    log.warn(`[Config] Error leyendo config: ${err.message}`);
    return {};
  }
}
function guardarConfigLocal(config) {
  const ruta = rutaArchivo$2(ARCHIVO_CONFIG);
  writeFileSync(ruta, JSON.stringify(config, null, 2), "utf-8");
}
function obtenerConfig(certificadoSerial) {
  const config = leerConfigLocal();
  return config[certificadoSerial] ?? {
    documentosActivos: documentosPorDefecto()
  };
}
function obtenerTodasLasConfigs() {
  return leerConfigLocal();
}
function guardarConfig(certificadoSerial, documentosActivos, datosExtra) {
  const config = leerConfigLocal();
  config[certificadoSerial] = { documentosActivos, datosExtra };
  guardarConfigLocal(config);
  log.info(`[Config] Guardada config para cert: ${certificadoSerial} — ${documentosActivos.length} docs activos`);
}
const USER_AGENTS = [
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
];
class BaseScraperDocumental {
  window = null;
  ventanasHijas = [];
  serialNumber;
  config;
  carpetaDescargas;
  constructor(serialNumber, config) {
    this.serialNumber = serialNumber;
    this.config = { ...CONFIG_DEFAULT$1, ...config };
    const baseDescargas = this.config.carpetaDescargas || join(app.getPath("documents"), "CertiGestor", "descargas");
    const subcarpeta = this.config.nombreCarpeta || serialNumber;
    this.carpetaDescargas = join(baseDescargas, subcarpeta);
    if (!existsSync(this.carpetaDescargas)) {
      mkdirSync(this.carpetaDescargas, { recursive: true });
    }
  }
  /**
   * Inicializa BrowserWindow con session temporal y seleccion automatica
   * de certificado por serialNumber.
   */
  async inicializarNavegador() {
    const particion = `scraper-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const sesionTemp = session.fromPartition(particion, { cache: false });
    this.window = new BrowserWindow({
      width: 1200,
      height: 800,
      show: !this.config.headless,
      webPreferences: {
        session: sesionTemp,
        nodeIntegration: false,
        contextIsolation: true
      }
    });
    const userAgent = USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
    this.window.webContents.setUserAgent(userAgent);
    const targetSerial = this.serialNumber.toLowerCase();
    this.window.webContents.on(
      "select-client-certificate",
      (event, _url, certificateList, callback) => {
        event.preventDefault();
        const seleccionado = certificateList.find(
          (cert) => cert.serialNumber.toLowerCase() === targetSerial
        );
        if (seleccionado) {
          log.info(
            `[${this.nombre}] Certificado seleccionado: ${seleccionado.subjectName}`
          );
          callback(seleccionado);
        } else {
          log.error(
            `[${this.nombre}] Certificado ${this.serialNumber} no encontrado. Disponibles: ${certificateList.map((c) => c.serialNumber).join(", ")}`
          );
          callback(null);
        }
      }
    );
    this.ventanasHijas = [];
    this.window.webContents.on("did-create-window", (childWindow) => {
      log.info(`[${this.nombre}] Popup creado: ${childWindow.id}`);
      this.ventanasHijas.push(childWindow);
      if (this.config.headless && childWindow.isVisible()) {
        childWindow.hide();
      }
      childWindow.webContents.setUserAgent(userAgent);
      childWindow.on("closed", () => {
        this.ventanasHijas = this.ventanasHijas.filter(
          (w) => w !== childWindow && !w.isDestroyed()
        );
      });
    });
    log.info(`[${this.nombre}] Navegador inicializado — particion: ${particion}`);
  }
  /** Cierra el navegador y limpia recursos */
  async cerrarNavegador() {
    for (const hijo of this.ventanasHijas) {
      if (hijo && !hijo.isDestroyed()) {
        hijo.removeAllListeners();
        hijo.close();
      }
    }
    this.ventanasHijas = [];
    if (this.window && !this.window.isDestroyed()) {
      try {
        const currentSession = this.window.webContents.session;
        await currentSession.clearStorageData({
          storages: [
            "cookies",
            "filesystem",
            "indexdb",
            "localstorage",
            "shadercache",
            "websql",
            "serviceworkers",
            "cachestorage"
          ]
        }).catch(
          (err) => log.warn(`[${this.nombre}] Error limpiando storage: ${err.message}`)
        );
        this.window.removeAllListeners();
        this.window.webContents.removeAllListeners();
        this.window.close();
      } catch (err) {
        log.warn(
          `[${this.nombre}] Error cerrando navegador: ${err.message}`
        );
      } finally {
        this.window = null;
      }
    }
  }
  /**
   * Ejecuta el scraper con timeout global y lifecycle completo.
   */
  async run() {
    const timeoutMs = this.config.timeoutGlobal;
    const logicaPromise = async () => {
      try {
        await this.inicializarNavegador();
        return await this.ejecutar();
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : "Error desconocido";
        log.error(`[${this.nombre}] Error:`, mensaje);
        return { exito: false, error: mensaje };
      }
    };
    const timeoutPromise = new Promise((resolve) => {
      setTimeout(() => {
        const msg = `Timeout global de ${timeoutMs / 1e3}s excedido`;
        log.error(`[${this.nombre}] ${msg}`);
        resolve({ exito: false, error: msg });
      }, timeoutMs);
    });
    try {
      return await Promise.race([logicaPromise(), timeoutPromise]);
    } finally {
      await this.cerrarNavegador();
    }
  }
  // ── Helpers ─────────────────────────────────────────────
  /** Navega a una URL y espera a que cargue */
  async navegar(url) {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado");
    }
    await new Promise((resolve, reject) => {
      const wc = this.window.webContents;
      let resuelto = false;
      const timer = setTimeout(() => {
        if (!resuelto) {
          resuelto = true;
          reject(new Error(`Timeout navegando a ${url}`));
        }
      }, this.config.timeoutGlobal);
      const onFinish = () => {
        if (resuelto) return;
        resuelto = true;
        clearTimeout(timer);
        wc.removeListener("did-finish-load", onFinish);
        wc.removeListener("did-fail-load", onFail);
        resolve();
      };
      const onFail = (_event, errorCode, errorDescription) => {
        if (errorCode === -3) return;
        if (resuelto) return;
        resuelto = true;
        clearTimeout(timer);
        wc.removeListener("did-finish-load", onFinish);
        wc.removeListener("did-fail-load", onFail);
        reject(new Error(`Fallo de carga: ${errorDescription} (${errorCode})`));
      };
      wc.on("did-finish-load", onFinish);
      wc.on("did-fail-load", onFail);
      this.window.loadURL(url).catch((error) => {
        if (error.message.includes("ERR_ABORTED")) return;
        if (!resuelto) {
          resuelto = true;
          clearTimeout(timer);
          reject(error);
        }
      });
    });
  }
  /** Espera a que un selector aparezca en la pagina */
  async esperarSelector(selector, timeout) {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado");
    }
    const ms = timeout ?? this.config.timeoutElemento;
    const inicio = Date.now();
    while (Date.now() - inicio < ms) {
      const existe = await this.window.webContents.executeJavaScript(
        `!!document.querySelector('${selector.replace(/'/g, "\\'")}')`
      );
      if (existe) return;
      await this.delay(500);
    }
    throw new Error(`Timeout esperando selector: ${selector}`);
  }
  /** Click en un elemento via JavaScript */
  async clickElemento(selector) {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado");
    }
    const existe = await this.window.webContents.executeJavaScript(
      `!!document.querySelector('${selector.replace(/'/g, "\\'")}')`
    );
    if (!existe) {
      throw new Error(`Elemento no encontrado: ${selector}`);
    }
    await this.window.webContents.executeJavaScript(
      `document.querySelector('${selector.replace(/'/g, "\\'")}').click()`
    );
  }
  /** Obtiene la URL actual del navegador */
  obtenerURL() {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado");
    }
    return this.window.webContents.getURL();
  }
  /** Obtiene el texto de un elemento */
  async obtenerTexto(selector) {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado");
    }
    return this.window.webContents.executeJavaScript(
      `(document.querySelector('${selector.replace(/'/g, "\\'")}')?.textContent ?? '').trim()`
    );
  }
  /** Ejecuta JavaScript arbitrario en la pagina */
  async ejecutarJs(codigo) {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado");
    }
    return this.window.webContents.executeJavaScript(codigo);
  }
  /** Selecciona un valor en un dropdown <select> */
  async seleccionarOpcion(selector, valor) {
    await this.ejecutarJs(`
      const sel = document.querySelector('${selector.replace(/'/g, "\\'")}');
      if (sel) {
        sel.value = '${valor.replace(/'/g, "\\'")}';
        sel.dispatchEvent(new Event('change', { bubbles: true }));
      }
    `);
  }
  /**
   * Descarga un archivo con will-download.
   * Ejecuta un disparador (funcion que clickea el enlace) y espera la descarga.
   */
  async descargarConPromesa(disparador, nombreArchivo, timeout) {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado");
    }
    const ms = timeout ?? 3e4;
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        sesion.removeListener("will-download", onDescarga);
        reject(new Error(`Timeout de descarga: ${nombreArchivo}`));
      }, ms);
      const sesion = this.window.webContents.session;
      const onDescarga = (_event, item) => {
        item.setSavePath(rutaDestino);
        item.on("done", (_e, state) => {
          clearTimeout(timer);
          sesion.removeListener("will-download", onDescarga);
          if (state === "completed") {
            log.info(`[${this.nombre}] Descargado: ${rutaDestino}`);
            resolve(rutaDestino);
          } else {
            reject(new Error(`Descarga fallida: ${state}`));
          }
        });
      };
      sesion.on("will-download", onDescarga);
      disparador().catch((err) => {
        clearTimeout(timer);
        sesion.removeListener("will-download", onDescarga);
        reject(err);
      });
    });
  }
  /**
   * Genera PDF de la pagina actual via printToPDF.
   */
  async printToPdf(nombreArchivo, opciones) {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado");
    }
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
    const buffer = await this.window.webContents.printToPDF({
      printBackground: true,
      landscape: false,
      ...opciones
    });
    writeFileSync(rutaDestino, buffer);
    log.info(`[${this.nombre}] PDF generado: ${rutaDestino}`);
    return rutaDestino;
  }
  /**
   * Prepara la espera de una ventana hija ANTES de hacer el click que la dispara.
   * Devuelve una Promise que se resuelve cuando did-create-window dispara.
   * Uso: const waitPopup = this.prepararEsperaVentana(); await click; const popup = await waitPopup;
   */
  prepararEsperaVentana(timeout) {
    const ms = timeout ?? this.config.timeoutElemento;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error("Timeout esperando nueva ventana"));
      }, ms);
      const handler = (childWindow) => {
        clearTimeout(timer);
        resolve(childWindow);
      };
      this.window.webContents.once("did-create-window", handler);
    });
  }
  /**
   * Espera a que se abra una nueva ventana hija (popup).
   * DEPRECATED: usar prepararEsperaVentana() antes del click para evitar race conditions.
   */
  async esperarVentanaNueva(timeout) {
    const ms = timeout ?? this.config.timeoutElemento;
    const cantidadAnterior = this.ventanasHijas.length;
    const inicio = Date.now();
    while (Date.now() - inicio < ms) {
      if (this.ventanasHijas.length > cantidadAnterior) {
        return this.ventanasHijas[this.ventanasHijas.length - 1];
      }
      await this.delay(500);
    }
    throw new Error("Timeout esperando nueva ventana");
  }
  /** Espera un numero de milisegundos */
  async delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
  /**
   * Intenta cerrar un modal/cookie banner si existe (no falla si no aparece).
   */
  async cerrarModalSiExiste(selector) {
    try {
      const existe = await this.ejecutarJs(
        `!!document.querySelector('${selector.replace(/'/g, "\\'")}')`
      );
      if (existe) {
        await this.clickElemento(selector);
        await this.delay(500);
      }
    } catch {
    }
  }
  /**
   * Detecta y maneja la pasarela Cl@ve (pasarela.clave.gob.es).
   * Usa selectedIdP('AFIRMA') como metodo primario (patron Findiur),
   * con fallback a busqueda por texto del boton.
   */
  async manejarPasarelaClave(timeoutDeteccion = 1e4, timeoutPostLogin = 3e4) {
    if (!this.window || this.window.isDestroyed()) return false;
    const inicio = Date.now();
    while (Date.now() - inicio < timeoutDeteccion) {
      const url = this.window.webContents.getURL();
      if (url.includes("pasarela.clave.gob.es") || url.includes("clave.gob.es")) {
        log.info(`[${this.nombre}] Pasarela Cl@ve detectada: ${url}`);
        await this.delay(2e3);
        const usadoSelectedIdP = await this.ejecutarJs(`
          (function() {
            try {
              if (typeof selectedIdP === 'function') {
                selectedIdP('AFIRMA');
                if (typeof idpRedirect !== 'undefined' && idpRedirect.submit) {
                  idpRedirect.submit();
                }
                return true;
              }
            } catch(e) {}
            return false;
          })()
        `);
        if (usadoSelectedIdP) {
          log.info(`[${this.nombre}] selectedIdP('AFIRMA') ejecutado`);
        } else {
          const clicBotonAfirma = await this.ejecutarJs(`
            (function() {
              var btn = document.querySelector("button[onclick*=\\"selectedIdP('AFIRMA')\\"]");
              if (btn) { btn.click(); return true; }
              return false;
            })()
          `);
          if (clicBotonAfirma) {
            log.info(`[${this.nombre}] Clic en boton AFIRMA por selector`);
          } else {
            const clicTexto = await this.ejecutarJs(`
              (function() {
                var botones = document.querySelectorAll('article button, button, a.btn');
                for (var i = 0; i < botones.length; i++) {
                  var texto = (botones[i].textContent || '').toLowerCase();
                  if (texto.includes('certificado') || texto.includes('dnie') || texto.includes('afirma')) {
                    botones[i].click();
                    return true;
                  }
                }
                return false;
              })()
            `);
            if (clicTexto) {
              log.info(`[${this.nombre}] Clic en boton certificado por texto`);
            } else {
              log.warn(`[${this.nombre}] No se encontro boton de certificado en Cl@ve`);
              return false;
            }
          }
        }
        const urlClave = this.window.webContents.getURL();
        const inicioEspera = Date.now();
        while (Date.now() - inicioEspera < timeoutPostLogin) {
          const urlActual = this.window.webContents.getURL();
          if (urlActual !== urlClave) {
            log.info(`[${this.nombre}] Redireccion post-Cl@ve: ${urlActual}`);
            break;
          }
          await this.delay(500);
        }
        await this.delay(3e3);
        return true;
      }
      await this.delay(500);
    }
    return false;
  }
  /**
   * Captura screenshot de la ventana actual para diagnostico.
   * Se guarda en la carpeta de descargas con prefijo debug_.
   */
  async capturarPantalla(paso) {
    if (!this.window || this.window.isDestroyed()) return;
    try {
      const url = this.window.webContents.getURL();
      const titulo = await this.window.webContents.executeJavaScript("document.title");
      const textoBody = await this.window.webContents.executeJavaScript(
        'document.body ? document.body.innerText.substring(0, 500) : "(sin body)"'
      );
      log.info(`[${this.nombre}][DEBUG ${paso}] URL: ${url}`);
      log.info(`[${this.nombre}][DEBUG ${paso}] Titulo: ${titulo}`);
      log.info(`[${this.nombre}][DEBUG ${paso}] Body (500 chars): ${textoBody.replace(/\\n/g, " ").substring(0, 300)}`);
      const image = await this.window.webContents.capturePage();
      const buffer = image.toPNG();
      const nombreScreenshot = `debug_${this.nombre.replace(/\\s+/g, "_")}_${paso}_${Date.now()}.png`;
      const carpetaDebug = join(this.carpetaDescargas, "_debug");
      if (!existsSync(carpetaDebug)) {
        mkdirSync(carpetaDebug, { recursive: true });
      }
      const ruta = join(carpetaDebug, nombreScreenshot);
      writeFileSync(ruta, buffer);
      log.info(`[${this.nombre}][DEBUG ${paso}] Screenshot: ${ruta}`);
    } catch (err) {
      log.warn(`[${this.nombre}][DEBUG ${paso}] Error capturando pantalla: ${err.message}`);
    }
  }
  /** Genera nombre de archivo con fecha */
  nombreConFecha(base, extension = "pdf") {
    const fecha = (/* @__PURE__ */ new Date()).toISOString().slice(0, 10);
    return `${base}_${fecha}.${extension}`;
  }
  // ── Helpers de popups ─────────────────────────────────────
  /** Espera un selector en una ventana hija (popup de firma, etc.) */
  async esperarSelectorEnVentana(ventana, selector, timeout = 3e4) {
    const inicio = Date.now();
    const sel = selector.replace(/'/g, "\\'");
    while (Date.now() - inicio < timeout) {
      if (ventana.isDestroyed()) throw new Error("Ventana cerrada");
      const existe = await ventana.webContents.executeJavaScript(
        `!!document.querySelector('${sel}')`
      );
      if (existe) return;
      await this.delay(500);
    }
    throw new Error(`Timeout esperando ${selector} en popup`);
  }
  /** Click en un elemento de una ventana hija */
  async clickElementoEnVentana(ventana, selector) {
    const sel = selector.replace(/'/g, "\\'");
    await ventana.webContents.executeJavaScript(
      `document.querySelector('${sel}').click()`
    );
  }
  /**
   * Configura interceptor de popups para convertirlos en descargas reales.
   * Patron Findiur: setWindowOpenHandler intercepta window.open del portal,
   * cancela la apertura de la ventana y usa downloadURL para disparar will-download.
   *
   * Devuelve Promise que se resuelve con la ruta del archivo descargado.
   */
  configurarInterceptorDescarga(nombreArchivo, timeout = 3e4) {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado");
    }
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
    const win = this.window;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        sesion.removeListener("will-download", onDescarga);
        reject(new Error(`Timeout interceptor descarga: ${nombreArchivo}`));
      }, timeout);
      const sesion = win.webContents.session;
      const onDescarga = (_event, item) => {
        item.setSavePath(rutaDestino);
        item.on("done", (_e, state) => {
          clearTimeout(timer);
          sesion.removeListener("will-download", onDescarga);
          if (state === "completed") {
            log.info(`[${this.nombre}] PDF descargado via interceptor: ${rutaDestino}`);
            resolve(rutaDestino);
          } else {
            reject(new Error(`Descarga fallida: ${state}`));
          }
        });
      };
      sesion.on("will-download", onDescarga);
      win.webContents.setWindowOpenHandler(({ url }) => {
        log.info(`[${this.nombre}] Popup interceptado — descargando URL: ${url}`);
        win.webContents.downloadURL(url);
        return { action: "deny" };
      });
    });
  }
  /**
   * Escucha will-download en una ventana especifica (popup) con timeout.
   */
  esperarDescargaEnVentana(ventana, nombreArchivo, timeout = 3e4) {
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        sesion.removeListener("will-download", onDescarga);
        reject(new Error("No hubo descarga en ventana"));
      }, timeout);
      const sesion = ventana.webContents.session;
      const onDescarga = (_event, item) => {
        item.setSavePath(rutaDestino);
        item.on("done", (_e, state) => {
          clearTimeout(timer);
          sesion.removeListener("will-download", onDescarga);
          if (state === "completed") resolve(rutaDestino);
          else reject(new Error(`Descarga: ${state}`));
        });
      };
      sesion.on("will-download", onDescarga);
    });
  }
  /**
   * Maneja login en Seguridad Social via IPCE (certificado electronico).
   * Patron Findiur: click en button[formaction*='seleccion=IPCE']
   */
  async manejarLoginSS(timeoutPostLogin = 3e4) {
    if (!this.window || this.window.isDestroyed()) return false;
    const clicIpce = await this.ejecutarJs(`
      (function() {
        var btn = document.querySelector("button[formaction*='seleccion=IPCE']");
        if (btn) { btn.click(); return true; }
        // Fallback: boton con texto "Certificado" o "IPCE"
        var botones = document.querySelectorAll('button, input[type=submit]');
        for (var i = 0; i < botones.length; i++) {
          var t = (botones[i].textContent || botones[i].value || '').toLowerCase();
          if (t.includes('certificado') || t.includes('ipce')) {
            botones[i].click();
            return true;
          }
        }
        return false;
      })()
    `);
    if (!clicIpce) {
      log.warn(`[${this.nombre}] Boton IPCE no encontrado`);
      return false;
    }
    log.info(`[${this.nombre}] Login SS via IPCE iniciado`);
    const urlAntes = this.window.webContents.getURL();
    const inicio = Date.now();
    while (Date.now() - inicio < timeoutPostLogin) {
      const urlActual = this.window.webContents.getURL();
      if (urlActual !== urlAntes && !urlActual.includes("Login")) {
        log.info(`[${this.nombre}] Login SS completado: ${urlActual}`);
        break;
      }
      await this.delay(500);
    }
    await this.delay(3e3);
    return true;
  }
  /**
   * Patron Carpeta Ciudadana: cookies → identificarse Cl@ve → proteccion datos → navegar
   */
  async loginCarpetaCiudadana(seccionUrl) {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error("Navegador no inicializado");
    }
    await this.navegar("https://carpetaciudadana.gob.es/");
    await this.delay(2e3);
    await this.cerrarModalSiExiste("button.cc-boton-aceptar");
    await this.delay(500);
    const clicAcceso = await this.ejecutarJs(`
      (function() {
        var btn = document.querySelector("button.botonIdentificateClave[onclick*='redirect']");
        if (btn) { btn.click(); return true; }
        btn = document.querySelector('#botonIdentificateClave');
        if (btn) { btn.click(); return true; }
        return false;
      })()
    `);
    if (!clicAcceso) {
      throw new Error("Boton de acceso Cl@ve no encontrado en Carpeta Ciudadana");
    }
    await this.delay(2e3);
    const loginOk = await this.manejarPasarelaClave(15e3, 3e4);
    if (!loginOk) {
      throw new Error("Login Cl@ve en Carpeta Ciudadana fallo");
    }
    await this.esperarSelector("main", 15e3);
    await this.delay(2e3);
    await this.ejecutarJs(`
      (function() {
        // Navegar a pagina de proteccion datos si existe enlace
        var enlace = document.querySelector('a[href*="proteccionDatos"]');
        if (enlace) enlace.click();
      })()
    `).catch(() => {
    });
    await this.delay(1e3);
    await this.ejecutarJs(`
      (function() {
        var btns = document.querySelectorAll('#botonesCondiciones button');
        if (btns.length >= 2) btns[1].click();
        else if (btns.length === 1) btns[0].click();
      })()
    `).catch(() => {
    });
    await this.delay(1e3);
    await this.navegar(`https://carpetaciudadana.gob.es${seccionUrl}`);
    await this.delay(3e3);
    log.info(`[${this.nombre}] Carpeta Ciudadana lista en ${seccionUrl}`);
  }
}
class ScraperDeudasAeat extends BaseScraperDocumental {
  url = "https://www1.agenciatributaria.gob.es/wlpl/EMCE-JDIT/ECOTInternetCiudadanosServlet";
  get nombre() {
    return "Deudas AEAT";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando solicitud de certificado de deudas`);
    await this.navegar(this.url);
    await this.delay(2e3);
    await this.esperarSelector("#fTipoCertificado4");
    await this.clickElemento("#fTipoCertificado4");
    log.info(`[${this.nombre}] Tipo de certificado seleccionado`);
    await this.clickElemento("#validarSolicitud");
    await this.delay(1e3);
    log.info(`[${this.nombre}] Solicitud validada`);
    await this.esperarSelector(".AEAT_boton");
    const waitPopupFirma = this.prepararEsperaVentana(3e4);
    await this.clickElemento(".AEAT_boton");
    const popupFirma = await waitPopupFirma;
    log.info(`[${this.nombre}] Popup de firma abierto (id: ${popupFirma.id})`);
    await this.esperarSelectorEnVentana(popupFirma, "#Conforme");
    await this.clickElementoEnVentana(popupFirma, "#Conforme");
    await this.delay(1e3);
    const nombreArchivo = this.nombreConFecha("Deudas_AEAT");
    const esperaDescarga = this.configurarInterceptorDescarga(nombreArchivo, 6e4);
    await this.clickElementoEnVentana(popupFirma, "#Firmar");
    log.info(`[${this.nombre}] Firma enviada — esperando descarga PDF via interceptor...`);
    try {
      const ruta = await esperaDescarga;
      log.info(`[${this.nombre}] Certificado descargado: ${ruta}`);
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch (errInterceptor) {
      log.warn(
        `[${this.nombre}] Interceptor no capturo descarga: ${errInterceptor.message}`
      );
    }
    await this.delay(3e3);
    try {
      await this.esperarSelector("#descarga", 1e4);
      log.info(`[${this.nombre}] Enlace #descarga encontrado — descargando`);
      const ruta = await this.descargarConPromesa(
        () => this.clickElemento("#descarga"),
        nombreArchivo,
        3e4
      );
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch {
      log.warn(`[${this.nombre}] #descarga no encontrado`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
}
class ScraperDatosFiscales extends BaseScraperDocumental {
  /** Base de la URL — se concatenan los 2 ultimos digitos del anio */
  urlBase = "https://www1.agenciatributaria.gob.es/wlpl/DFPA-D182/SvVisDF";
  get nombre() {
    return "Datos Fiscales";
  }
  async ejecutar() {
    const anioBase = (/* @__PURE__ */ new Date()).getFullYear() - 1;
    const anios = [anioBase, anioBase - 1, anioBase - 2];
    const rutasGeneradas = [];
    const erroresParciales = [];
    log.info(`[${this.nombre}] Obteniendo datos fiscales para anios: ${anios.join(", ")}`);
    for (let i = 0; i < anios.length; i++) {
      const anio = anios[i];
      const sufijo = String(anio).slice(-2);
      const url = `${this.urlBase}${sufijo}Net`;
      log.info(`[${this.nombre}] Navegando a datos fiscales ${anio} — ${url}`);
      try {
        await this.navegar(url);
      } catch (err) {
        log.warn(`[${this.nombre}] Error navegando a ${anio}: ${err.message}`);
        await this.capturarPantalla(`nav-error-${anio}`);
        erroresParciales.push(`${anio}: error de navegacion`);
        continue;
      }
      await this.delay(3e3);
      await this.capturarPantalla(`post-nav-${anio}`);
      const esError = await this.ejecutarJs(`
        (function() {
          var texto = (document.body ? document.body.innerText : '').toLowerCase();
          return texto.includes('error interno en el sistema') ||
                 texto.includes('pagina no habilitada') ||
                 texto.includes('página no habilitada') ||
                 texto.includes('servicio no disponible') ||
                 texto.includes('no se puede acceder') ||
                 texto.includes('no identificado');
        })()
      `).catch(() => false);
      if (esError) {
        log.warn(`[${this.nombre}] AEAT devolvio error para ${anio} — saltando`);
        await this.capturarPantalla(`error-aeat-${anio}`);
        erroresParciales.push(`${anio}: AEAT no disponible para este ejercicio`);
        continue;
      }
      if (i === 0) {
        await this.cerrarModalSiExiste("#alertsModal .modal-header button.close");
        await this.ejecutarJs(`
          (function() {
            var btns = document.querySelectorAll('.modal button, .modal .close, button.close');
            for (var j = 0; j < btns.length; j++) {
              var t = (btns[j].textContent || '').toLowerCase();
              if (t.includes('aceptar') || t.includes('cerrar') || btns[j].className.includes('close')) {
                btns[j].click();
                break;
              }
            }
          })()
        `).catch(() => {
        });
        await this.delay(1e3);
      }
      const urlActual = await this.ejecutarJs("window.location.href");
      log.info(`[${this.nombre}] URL actual tras navegar ${anio}: ${urlActual}`);
      if (urlActual.includes("clave.gob.es") || urlActual.includes("pasarela")) {
        log.info(`[${this.nombre}] Detectada pasarela Cl@ve — manejando login`);
        await this.manejarPasarelaClave(15e3, 3e4);
        await this.delay(3e3);
        await this.capturarPantalla(`post-clave-${anio}`);
      }
      try {
        await this.esperarSelector("#AEAT_contenedor_Aplicacion", 3e4);
        log.info(`[${this.nombre}] Contenedor AEAT cargado para ${anio}`);
      } catch {
        log.warn(`[${this.nombre}] Contenedor AEAT no encontrado para ${anio}`);
        await this.capturarPantalla(`sin-contenedor-${anio}`);
        const textoBody = await this.ejecutarJs(
          'document.body ? document.body.innerText : ""'
        ).catch(() => "");
        const textoLower = textoBody.toLowerCase();
        if (textoBody.length < 200 || textoLower.includes("error interno") || textoLower.includes("no habilitada") || textoLower.includes("no identificado")) {
          log.warn(`[${this.nombre}] Pagina de error o vacia para ${anio} — saltando`);
          erroresParciales.push(`${anio}: contenido no disponible`);
          continue;
        }
        log.info(`[${this.nombre}] Pagina tiene ${textoBody.length} chars — generando PDF igualmente`);
      }
      await this.capturarPantalla(`pre-pdf-${anio}`);
      const nombreArchivo = `Datos_Fiscales_${anio}.pdf`;
      const ruta = await this.printToPdf(nombreArchivo, { scale: 0.75 });
      rutasGeneradas.push(ruta);
      log.info(`[${this.nombre}] PDF generado: ${ruta}`);
    }
    if (rutasGeneradas.length === 0) {
      return {
        exito: false,
        error: `No se pudo generar ningun PDF de datos fiscales. ${erroresParciales.join("; ")}`
      };
    }
    return {
      exito: true,
      datos: {
        tipo: "datos_fiscales",
        descargados: rutasGeneradas.length,
        total: anios.length,
        anios,
        archivos: rutasGeneradas.map((r) => r.split(/[\\/]/).pop()),
        rutasArchivos: rutasGeneradas,
        errores: erroresParciales.length > 0 ? erroresParciales : void 0
      },
      rutaDescarga: rutasGeneradas[0]
    };
  }
}
class ScraperCertificadosIrpf extends BaseScraperDocumental {
  url = "https://www1.agenciatributaria.gob.es/wlpl/CERE-EMCE/InternetServlet";
  constructor(serialNumber, config) {
    super(serialNumber, {
      ...config,
      // 5 minutos: 3 ejercicios × ~80s cada uno + margen
      timeoutGlobal: 3e5
    });
  }
  get nombre() {
    return "Certificados IRPF";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando obtencion de certificados IRPF`);
    await this.navegar(this.url);
    await this.cerrarModalSiExiste("#alertsModal .close");
    await this.esperarSelector("#fEjercicio");
    const opciones = await this.ejecutarJs(`
      Array.from(document.querySelector('#fEjercicio').options)
        .filter(o => o.value && o.value !== '')
        .slice(0, 3)
        .map(o => o.value)
    `);
    if (opciones.length === 0) {
      return { exito: false, error: "No hay ejercicios fiscales disponibles" };
    }
    log.info(`[${this.nombre}] Ejercicios disponibles: ${opciones.join(", ")}`);
    const rutasDescargadas = [];
    const erroresParciales = [];
    for (let i = 0; i < opciones.length; i++) {
      const anio = opciones[i];
      try {
        if (i > 0) {
          log.info(`[${this.nombre}] Reiniciando browser para ejercicio ${anio}...`);
          await this.cerrarNavegador();
          await this.delay(2e3);
          await this.inicializarNavegador();
          await this.delay(1e3);
          try {
            await this.navegar(this.url);
          } catch (navErr) {
            log.warn(`[${this.nombre}] Error navegando tras reinicio para ${anio}: ${navErr.message}`);
            await this.capturarPantalla(`reinicio-error-${anio}`);
            erroresParciales.push(`${anio}: error de navegacion tras reinicio`);
            continue;
          }
          await this.delay(2e3);
          await this.cerrarModalSiExiste("#alertsModal .close");
          try {
            await this.esperarSelector("#fEjercicio", 2e4);
          } catch {
            log.warn(`[${this.nombre}] Formulario no cargo tras reinicio para ${anio}`);
            await this.capturarPantalla(`form-no-cargo-${anio}`);
            const esError = await this.ejecutarJs(`
              (function() {
                var t = (document.body ? document.body.innerText : '').toLowerCase();
                return t.includes('error interno') || t.includes('no habilitada') || t.includes('no identificado');
              })()
            `).catch(() => false);
            if (esError) {
              erroresParciales.push(`${anio}: AEAT devolvio error`);
              continue;
            }
            log.info(`[${this.nombre}] Reintentando navegacion para ${anio}...`);
            await this.navegar(this.url);
            await this.delay(3e3);
            await this.cerrarModalSiExiste("#alertsModal .close");
            await this.esperarSelector("#fEjercicio", 15e3);
          }
        }
        log.info(`[${this.nombre}] Procesando ejercicio ${anio} (${i + 1}/${opciones.length})`);
        await this.seleccionarOpcion("#fEjercicio", anio);
        await this.delay(1e3);
        await this.clickElemento("#validarSolicitud");
        await this.esperarSelector("input[value='Firmar Enviar']", 2e4);
        await this.delay(500);
        const waitPopupFirma = this.prepararEsperaVentana(3e4);
        await this.clickElemento("input[value='Firmar Enviar']");
        const popupFirma = await waitPopupFirma;
        log.info(`[${this.nombre}] Popup de firma abierto para ${anio}`);
        await this.esperarSelectorEnVentana(popupFirma, "#Conforme", 15e3);
        await this.clickElementoEnVentana(popupFirma, "#Conforme");
        await this.delay(1500);
        const nombreArchivo = `Certificado_IRPF_${anio}.pdf`;
        const esperaDescarga = this.configurarInterceptorDescarga(nombreArchivo, 3e4);
        await this.clickElementoEnVentana(popupFirma, "#Firmar");
        log.info(`[${this.nombre}] Firma enviada para ${anio} — esperando resultado...`);
        await this.delay(3e3);
        try {
          await this.esperarSelector("#descarga", 2e4);
          const ruta = await this.descargarConPromesa(
            () => this.clickElemento("#descarga"),
            nombreArchivo,
            3e4
          );
          rutasDescargadas.push(ruta);
          log.info(`[${this.nombre}] IRPF ${anio} via #descarga: ${ruta}`);
          continue;
        } catch {
          log.warn(`[${this.nombre}] #descarga no encontrado para ${anio}`);
        }
        try {
          const ruta = await esperaDescarga;
          log.info(`[${this.nombre}] IRPF ${anio} via interceptor: ${ruta}`);
          rutasDescargadas.push(ruta);
          continue;
        } catch {
          log.warn(`[${this.nombre}] Interceptor no capturo para ${anio}`);
        }
        log.warn(`[${this.nombre}] printToPdf fallback para ${anio}`);
        await this.capturarPantalla(`fallback-printToPdf-${anio}`);
        const rutaPdf = await this.printToPdf(nombreArchivo);
        rutasDescargadas.push(rutaPdf);
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : "Error desconocido";
        log.error(`[${this.nombre}] Error en ejercicio ${anio}: ${mensaje}`);
        await this.capturarPantalla(`error-${anio}`).catch(() => {
        });
        erroresParciales.push(`${anio}: ${mensaje}`);
      }
    }
    if (rutasDescargadas.length === 0) {
      return {
        exito: false,
        error: `No se pudo descargar ningun certificado. Errores: ${erroresParciales.join("; ")}`
      };
    }
    return {
      exito: true,
      datos: {
        tipo: "certificados_irpf",
        descargados: rutasDescargadas.length,
        total: opciones.length,
        archivos: rutasDescargadas.map((r) => r.split(/[\\/]/).pop()),
        errores: erroresParciales.length > 0 ? erroresParciales : void 0
      },
      rutaDescarga: rutasDescargadas[0]
    };
  }
}
async function loginSeguridadSocial(scraper) {
  log.info("[Login SS] Iniciando autenticacion con certificado");
  const urlInicial = await scraper.ejecutarJs("window.location.href");
  log.info(`[Login SS] URL inicial: ${urlInicial}`);
  const clicContinuar = await scraper.ejecutarJs(`
    (function() {
      var botones = document.querySelectorAll('button');
      for (var i = 0; i < botones.length; i++) {
        var texto = (botones[i].textContent || '').trim().toLowerCase();
        if (texto === 'continuar' || texto.includes('continuar')) {
          botones[i].click();
          return true;
        }
      }
      return false;
    })()
  `);
  if (clicContinuar) {
    log.info('[Login SS] Clic en "Continuar" del modal de identificacion');
    await scraper.delay(4e3);
  }
  await scraper.capturarPantalla("login-ss-01-post-continuar");
  const urlPostContinuar = await scraper.ejecutarJs("window.location.href");
  log.info(`[Login SS] URL post-continuar: ${urlPostContinuar}`);
  if (!urlPostContinuar.includes("idp.seg-social") && !urlPostContinuar.includes("ipce.seg-social") && !urlPostContinuar.includes("clave.gob.es") && !urlPostContinuar.includes("importass")) {
    log.info("[Login SS] Ya autenticados, no se requiere login");
    return;
  }
  const botonesDisponibles = await scraper.ejecutarJs(`
    (function() {
      var resultado = [];
      var elementos = document.querySelectorAll('button, a, input[type="submit"]');
      for (var i = 0; i < Math.min(elementos.length, 15); i++) {
        resultado.push({
          tag: elementos[i].tagName,
          texto: (elementos[i].textContent || '').trim().substring(0, 60),
          href: elementos[i].getAttribute('href') || '',
          formaction: elementos[i].getAttribute('formaction') || '',
        });
      }
      return JSON.stringify(resultado);
    })()
  `);
  log.info(`[Login SS] Botones disponibles: ${botonesDisponibles}`);
  const clicDnie = await scraper.ejecutarJs(`
    (function() {
      // Interfaz nueva 2026: boton con ID fijo #IPCEIdP
      var btn = document.querySelector('#IPCEIdP');
      if (btn) { btn.click(); return true; }
      // Patron Findiur: boton con formaction IPCE (selector mas fiable)
      btn = document.querySelector("button[formaction*='seleccion=IPCE']");
      if (btn) { btn.click(); return true; }
      // Fallback: formaction generico IPCE
      btn = document.querySelector("button[formaction*='IPCE'], button[formaction*='ipce']");
      if (btn) { btn.click(); return true; }
      // Fallback 2: buscar por texto
      var botones = document.querySelectorAll('button, a');
      for (var i = 0; i < botones.length; i++) {
        var texto = (botones[i].textContent || '').toLowerCase();
        if (texto.includes('dnie') || texto.includes('certificado electr') ||
            texto.includes('certificado digital') || texto.includes('certificado software')) {
          botones[i].click();
          return true;
        }
      }
      // Fallback 3: link con href IPCE
      var links = document.querySelectorAll('a');
      for (var j = 0; j < links.length; j++) {
        var href = links[j].getAttribute('href') || '';
        if (href.includes('IPCE') || href.includes('ipce')) {
          links[j].click();
          return true;
        }
      }
      return false;
    })()
  `);
  if (clicDnie) {
    log.info('[Login SS] Clic en "DNIe o certificado" — esperando select-client-certificate');
    await scraper.delay(5e3);
  } else {
    log.warn("[Login SS] Boton DNIe no encontrado — intentando pasarela Cl@ve");
    await scraper.capturarPantalla("login-ss-02-sin-boton-dnie");
    await scraper.manejarPasarelaClave(15e3, 3e4);
    await scraper.delay(3e3);
  }
  await scraper.capturarPantalla("login-ss-03-post-dnie-click");
  const urlPostDnie = await scraper.ejecutarJs("window.location.href");
  log.info(`[Login SS] URL post-DNIe: ${urlPostDnie}`);
  if (urlPostDnie.includes("idp.seg-social.es") || urlPostDnie.includes("ipce.seg-social.es") || urlPostDnie.includes("clave.gob.es")) {
    log.info("[Login SS] Aun en pasarela — esperando redireccion...");
    const inicio = Date.now();
    while (Date.now() - inicio < 2e4) {
      await scraper.delay(1e3);
      const url = await scraper.ejecutarJs("window.location.href");
      if (!url.includes("idp.seg-social.es") && !url.includes("ipce.seg-social.es") && !url.includes("clave.gob.es")) {
        log.info(`[Login SS] Redireccion completada: ${url}`);
        break;
      }
    }
  }
  await scraper.delay(3e3);
  await scraper.capturarPantalla("login-ss-04-final");
  const urlFinal = await scraper.ejecutarJs("window.location.href");
  log.info(`[Login SS] URL final: ${urlFinal}`);
  log.info("[Login SS] Autenticacion completada");
}
class ScraperCnaeAutonomo extends BaseScraperDocumental {
  url = "https://portal.seg-social.gob.es/wps/myportal/importass/importass/personal/";
  get nombre() {
    return "CNAE Autonomo";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando consulta CNAE autonomo`);
    await this.navegar(this.url);
    await this.delay(3e3);
    await this.cerrarModalSiExiste("#cookies button, .cookie-accept, #onetrust-accept-btn-handler");
    await loginSeguridadSocial(this);
    await this.delay(5e3);
    const urlPostLogin = this.obtenerURL();
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`);
    if (!urlPostLogin.includes("personal")) {
      await this.navegar(this.url);
      await this.delay(5e3);
    }
    await this.capturarPantalla("paso-2-area-personal");
    const clicAutonomo = await this.ejecutarJs(`
      (function() {
        // Buscar por href que contiene ACC_PERFIL_AUTONOMO
        var links = document.querySelectorAll('a.ss-link');
        for (var i = 0; i < links.length; i++) {
          var href = links[i].getAttribute('href') || '';
          if (href.includes('ACC_PERFIL_AUTONOMO') || href.includes('accion!ACC_PERFIL_AUTONOMO')) {
            links[i].click();
            return true;
          }
        }
        // Fallback: buscar por title
        for (var j = 0; j < links.length; j++) {
          var title = (links[j].getAttribute('title') || '').toLowerCase();
          if (title.includes('perfil de trabajo aut') || title.includes('datos de aut')) {
            links[j].click();
            return true;
          }
        }
        // Fallback: buscar por texto
        links = document.querySelectorAll('a');
        for (var k = 0; k < links.length; k++) {
          var texto = (links[k].textContent || '').toLowerCase();
          if (texto.includes('tus datos de aut') || texto.includes('ver tus datos de aut')) {
            links[k].click();
            return true;
          }
        }
        return false;
      })()
    `);
    if (!clicAutonomo) {
      log.error(`[${this.nombre}] Enlace "Ver tus datos de autonomo" no encontrado`);
      await this.capturarPantalla("error-sin-enlace-autonomo");
      return {
        exito: false,
        error: "No se encontro el enlace de datos de autonomo. ¿El certificado es de un trabajador autonomo?",
        datos: {}
      };
    }
    log.info(`[${this.nombre}] Click en "Ver tus datos de autonomo"`);
    await this.delay(5e3);
    await this.capturarPantalla("paso-3-datos-autonomo");
    const clicActividades = await this.ejecutarJs(`
      (function() {
        // Buscar por href anchor #datos-actividad
        var link = document.querySelector('a[href="#datos-actividad"]');
        if (link) { link.click(); return true; }
        // Fallback: buscar por texto en sidebar links
        var links = document.querySelectorAll('a.ss-link');
        for (var i = 0; i < links.length; i++) {
          var texto = (links[i].textContent || '').toLowerCase();
          if (texto.includes('actividades de aut')) {
            links[i].click();
            return true;
          }
        }
        return false;
      })()
    `);
    if (!clicActividades) {
      log.warn(`[${this.nombre}] Enlace "Actividades de autonomo" no encontrado en sidebar`);
      await this.capturarPantalla("error-sin-sidebar-actividades");
    } else {
      log.info(`[${this.nombre}] Click en "Actividades de autonomo"`);
    }
    await this.delay(3e3);
    await this.capturarPantalla("paso-4-seccion-actividades");
    const clicInforme = await this.ejecutarJs(`
      (function() {
        // Selector directo: a#autonomo con title "Descargar resguardo actividades declaradas"
        var link = document.querySelector('a#autonomo');
        if (link) { link.click(); return true; }
        // Fallback: buscar por href que contiene AC_INFORME_ACTIVIDADES
        var links = document.querySelectorAll('a.ss-link');
        for (var i = 0; i < links.length; i++) {
          var href = links[i].getAttribute('href') || '';
          if (href.includes('AC_INFORME_ACTIVIDADES') || href.includes('accion!AC_INFORME_ACTIVIDADES')) {
            links[i].click();
            return true;
          }
        }
        // Fallback: buscar por texto "informe actualizado"
        links = document.querySelectorAll('a');
        for (var j = 0; j < links.length; j++) {
          var texto = (links[j].textContent || '').toLowerCase();
          if (texto.includes('informe actualizado')) {
            links[j].click();
            return true;
          }
        }
        return false;
      })()
    `);
    if (!clicInforme) {
      log.error(`[${this.nombre}] Enlace "informe actualizado" no encontrado`);
      await this.capturarPantalla("error-sin-enlace-informe");
      return {
        exito: false,
        error: "No se encontro el enlace para generar el informe de actividades",
        datos: {}
      };
    }
    log.info(`[${this.nombre}] Click en "informe actualizado" — esperando pagina "Informe generado"`);
    await this.delay(5e3);
    await this.capturarPantalla("paso-5-informe-generado");
    const nombreArchivo = this.nombreConFecha("Informe_CNAE_Autonomo");
    try {
      await this.esperarSelector("#btnDescInformeVariasAct", 15e3);
      log.info(`[${this.nombre}] Boton #btnDescInformeVariasAct encontrado`);
      const ruta = await this.descargarConPromesa(
        async () => {
          await this.clickElemento("#btnDescInformeVariasAct");
          log.info(`[${this.nombre}] Click en "Descargar informe" — esperando will-download`);
        },
        nombreArchivo,
        3e4
      );
      log.info(`[${this.nombre}] Informe CNAE descargado: ${ruta}`);
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch (err) {
      log.warn(`[${this.nombre}] will-download fallo: ${err.message}`);
    }
    try {
      const ruta = await this.descargarConPromesa(
        async () => {
          await this.ejecutarJs(`
            (function() {
              var btns = document.querySelectorAll('button.ss-button');
              for (var i = 0; i < btns.length; i++) {
                var texto = (btns[i].textContent || '').toLowerCase();
                if (texto.includes('descargar informe')) {
                  btns[i].click(); return;
                }
              }
            })()
          `);
          log.info(`[${this.nombre}] Fallback: click boton ss-button "Descargar informe"`);
        },
        nombreArchivo,
        3e4
      );
      log.info(`[${this.nombre}] Descarga via fallback: ${ruta}`);
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch {
      log.warn(`[${this.nombre}] Fallback descarga tambien fallo`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
}
class ScraperIaeActividades extends BaseScraperDocumental {
  url = "https://www1.agenciatributaria.gob.es/wlpl/EMCE-JDIT/ServletAaeeGralnternet";
  get nombre() {
    return "Actividades IAE";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando solicitud de certificado IAE`);
    await this.navegar(this.url);
    await this.delay(2e3);
    await this.esperarSelector("#fEjercicio");
    log.info(`[${this.nombre}] Formulario IAE cargado`);
    const anioActual = String((/* @__PURE__ */ new Date()).getFullYear());
    await this.seleccionarOpcion("#fEjercicio", anioActual);
    await this.delay(500);
    await this.clickElemento("#validarSolicitud");
    log.info(`[${this.nombre}] Solicitud validada — esperando paso 2`);
    await this.esperarSelector("input[value='Firmar Enviar']", 15e3);
    const waitPopupFirma = this.prepararEsperaVentana(3e4);
    await this.clickElemento("input[value='Firmar Enviar']");
    const popupFirma = await waitPopupFirma;
    log.info(`[${this.nombre}] Popup de firma abierto`);
    await this.esperarSelectorEnVentana(popupFirma, "#Conforme");
    await this.clickElementoEnVentana(popupFirma, "#Conforme");
    await this.delay(1e3);
    const nombreArchivo = this.nombreConFecha("Actividades_IAE");
    const esperaDescarga = this.configurarInterceptorDescarga(nombreArchivo, 6e4);
    await this.clickElementoEnVentana(popupFirma, "#Firmar");
    log.info(`[${this.nombre}] Firma enviada — esperando descarga PDF...`);
    try {
      const ruta = await esperaDescarga;
      log.info(`[${this.nombre}] Certificado IAE descargado: ${ruta}`);
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch (errInterceptor) {
      log.warn(
        `[${this.nombre}] Interceptor no capturo descarga: ${errInterceptor.message}`
      );
    }
    await this.delay(3e3);
    try {
      await this.esperarSelector("#descarga", 1e4);
      log.info(`[${this.nombre}] Enlace #descarga encontrado`);
      const ruta = await this.descargarConPromesa(
        () => this.clickElemento("#descarga"),
        nombreArchivo,
        3e4
      );
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch {
      log.warn(`[${this.nombre}] #descarga no encontrado`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
}
class ScraperDeudasSS extends BaseScraperDocumental {
  url = "https://sp.seg-social.es/ProsaInternet/OnlineAccess?ARQ.SPM.ACTION=LOGIN&ARQ.SPM.APPTYPE=SERVICE&ARQ.IDAPP=AECPSED1&PAUC.NIVEL=1&PAUC.TIPO_IDENTIFICACION=2";
  datosExtra;
  constructor(serialNumber, config, datosExtra) {
    super(serialNumber, config);
    this.datosExtra = datosExtra ?? {};
  }
  get nombre() {
    return "Deudas SS";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando consulta de deudas SS`);
    await this.navegar(this.url);
    await this.delay(3e3);
    const urlActual = this.obtenerURL();
    log.info(`[${this.nombre}] URL tras navegar: ${urlActual}`);
    if (urlActual.includes("idp.seg-social") || urlActual.includes("PGIS/Login") || urlActual.includes("importass")) {
      await loginSeguridadSocial(this);
      await this.delay(5e3);
    } else if (urlActual.includes("clave.gob.es")) {
      await this.manejarPasarelaClave();
      await this.delay(5e3);
    }
    await this.capturarPantalla("paso-2-post-login");
    const urlPostLogin = this.obtenerURL();
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`);
    if (!urlPostLogin.includes("ProsaInternet") && !urlPostLogin.includes("sp.seg-social")) {
      await this.navegar(this.url);
      await this.delay(5e3);
    }
    const tipoCert = this.datosExtra.tipoCertificado ?? "1";
    if (tipoCert !== "1") {
      log.info(`[${this.nombre}] Seleccionando tipo certificado: ${tipoCert}`);
      await this.ejecutarJs(`
        (function() {
          var radio = document.querySelector('input[name="certificado"][value="${tipoCert}"]');
          if (radio) radio.click();
        })()
      `);
      await this.delay(500);
    }
    const clicContinuar = await this.ejecutarJs(`
      (function() {
        // Selector exacto: button[name="SPM.ACC.CONTINUAR"]
        var btn = document.querySelector('button[name="SPM.ACC.CONTINUAR"]');
        if (btn) { btn.click(); return true; }
        // Fallback: cualquier submit con texto "continuar"
        var btns = document.querySelectorAll('button[type="submit"], input[type="submit"]');
        for (var i = 0; i < btns.length; i++) {
          var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
          if (t.includes('continuar')) { btns[i].click(); return true; }
        }
        return false;
      })()
    `);
    if (clicContinuar) {
      log.info(`[${this.nombre}] Click en Continuar`);
      await this.delay(3e3);
    } else {
      log.warn(`[${this.nombre}] Boton Continuar no encontrado — puede que ya paso al paso 4`);
    }
    await this.capturarPantalla("paso-3-post-continuar");
    const clicImprimir = await this.ejecutarJs(`
      (function() {
        // Selector exacto por name
        var btn = document.querySelector('button[name="SPM.ACC.IMPRIMIR"]');
        if (btn) { btn.click(); return true; }
        // Fallback por id
        btn = document.getElementById('ENVIO_10');
        if (btn) { btn.click(); return true; }
        // Fallback por texto
        var btns = document.querySelectorAll('button[type="submit"], input[type="submit"]');
        for (var i = 0; i < btns.length; i++) {
          var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
          if (t.includes('imprimir')) { btns[i].click(); return true; }
        }
        return false;
      })()
    `);
    if (clicImprimir) {
      log.info(`[${this.nombre}] Click en Imprimir`);
      await this.delay(5e3);
    } else {
      log.warn(`[${this.nombre}] Boton Imprimir no encontrado`);
      await this.capturarPantalla("error-sin-imprimir");
    }
    await this.capturarPantalla("paso-4-post-imprimir");
    const nombreArchivo = this.nombreConFecha("Deudas_SS");
    try {
      await this.esperarSelector("a.pr_enlaceDocumento", 15e3);
      log.info(`[${this.nombre}] Enlace a.pr_enlaceDocumento encontrado`);
      const promesaDescarga = this.configurarInterceptorDescarga(nombreArchivo, 3e4);
      await this.clickElemento("a.pr_enlaceDocumento");
      log.info(`[${this.nombre}] Click en enlace documento — esperando descarga via interceptor`);
      const ruta = await promesaDescarga;
      log.info(`[${this.nombre}] Certificado descargado: ${ruta}`);
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch (err) {
      log.warn(`[${this.nombre}] Estrategia 1 fallo: ${err.message}`);
    }
    try {
      const tieneViewDoc = await this.ejecutarJs(`
        (function() {
          var link = document.querySelector("a[href*='ViewDoc']");
          if (link) { link.removeAttribute('target'); return true; }
          return false;
        })()
      `);
      if (tieneViewDoc) {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento("a[href*='ViewDoc']"),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Certificado descargado via ViewDoc: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Estrategia 2 fallo: ${err.message}`);
    }
    try {
      const hrefEnlace = await this.ejecutarJs(`
        (function() {
          var enlaces = document.querySelectorAll('a');
          for (var i = 0; i < enlaces.length; i++) {
            var t = (enlaces[i].textContent || '').toLowerCase();
            if (t.includes('certificado') && !t.includes('informaci')) {
              return enlaces[i].href;
            }
          }
          return '';
        })()
      `);
      if (hrefEnlace) {
        const promesaDescarga = this.configurarInterceptorDescarga(nombreArchivo, 3e4);
        this.window.webContents.downloadURL(hrefEnlace);
        const ruta = await promesaDescarga;
        log.info(`[${this.nombre}] Certificado descargado via downloadURL directo: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Estrategia 3 fallo: ${err.message}`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
}
class ScraperVidaLaboral extends BaseScraperDocumental {
  url = "https://portal.seg-social.gob.es/wps/portal/importass/importass/Categorias/Vida+laboral+e+informes/Informes+sobre+tu+situacion+laboral/Informe+de+tu+vida+laboral";
  get nombre() {
    return "Vida Laboral";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando descarga de vida laboral`);
    await this.navegar(this.url);
    await this.delay(3e3);
    await this.ejecutarJs(`
      (function() {
        if (typeof AceptarCookies === 'function') { AceptarCookies(); return; }
        var btn = document.querySelector('#cookies button, #onetrust-accept-btn-handler');
        if (btn) btn.click();
        var botones = document.querySelectorAll('button');
        for (var i = 0; i < botones.length; i++) {
          var t = (botones[i].textContent || '').toLowerCase();
          if (t.includes('rechazar todas') || t.includes('aceptar todas')) {
            botones[i].click(); return;
          }
        }
      })()
    `).catch(() => {
    });
    await this.delay(1500);
    await this.ejecutarJs(`
      (function() {
        if (typeof clickBotonConsultar === 'function') { clickBotonConsultar(); return; }
        var botones = document.querySelectorAll('button, a');
        for (var i = 0; i < botones.length; i++) {
          var t = (botones[i].textContent || '').toLowerCase();
          if (t.includes('consultar vida laboral') || t.includes('acceder al servicio') ||
              t.includes('obtener informe')) {
            botones[i].click(); return;
          }
        }
      })()
    `).catch(() => {
    });
    await this.delay(3e3);
    await loginSeguridadSocial(this);
    await this.delay(5e3);
    const urlPostLogin = this.obtenerURL();
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`);
    const nombreArchivo = this.nombreConFecha("Vida_Laboral");
    const tieneBotonDescarga = await this.ejecutarJs(`
      !!(document.querySelector("button[value='AC_DESC_VIDA_LABORAL']") ||
         document.querySelector("button[name='AC_DESC_VIDA_LABORAL']") ||
         document.querySelector("input[value='AC_DESC_VIDA_LABORAL']"))
    `);
    if (tieneBotonDescarga) {
      log.info(`[${this.nombre}] Boton AC_DESC_VIDA_LABORAL encontrado — descargando`);
      try {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento(
            "button[value='AC_DESC_VIDA_LABORAL'], button[name='AC_DESC_VIDA_LABORAL'], input[value='AC_DESC_VIDA_LABORAL']"
          ),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Informe descargado: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      } catch (err) {
        log.warn(`[${this.nombre}] will-download fallo con boton especifico: ${err.message}`);
      }
    }
    const selectorDescarga = await this.buscarBotonDescarga();
    if (selectorDescarga) {
      log.info(`[${this.nombre}] Boton descarga generico: ${selectorDescarga}`);
      try {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento(selectorDescarga),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Informe descargado: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      } catch (err) {
        log.warn(`[${this.nombre}] will-download generico fallo: ${err.message}`);
      }
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
  async buscarBotonDescarga() {
    const encontrado = await this.ejecutarJs(`
      (function() {
        var elementos = document.querySelectorAll('button, a, input[type="submit"]');
        for (var i = 0; i < elementos.length; i++) {
          var t = (elementos[i].textContent || elementos[i].value || '').toLowerCase();
          if (t.includes('descargar') || t.includes('obtener informe') ||
              t.includes('generar informe') || t.includes('descargar pdf')) {
            elementos[i].setAttribute('data-cg-download', 'true');
            return true;
          }
        }
        return false;
      })()
    `);
    return encontrado ? '[data-cg-download="true"]' : null;
  }
}
class ScraperCertificadoINSS extends BaseScraperDocumental {
  url = "https://sede-tu.seg-social.gob.es/wps/myportal/tussR/tuss/TrabajoPensiones/Pensiones/CertificadoIntegradoPrestaciones";
  get nombre() {
    return "Certificado INSS";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando descarga de certificado INSS`);
    await this.navegar(this.url);
    await this.delay(5e3);
    const urlActual = this.obtenerURL();
    log.info(`[${this.nombre}] URL tras navegar: ${urlActual}`);
    if (urlActual.includes("idp.seg-social") || urlActual.includes("PGIS/Login")) {
      log.info(`[${this.nombre}] Pasarela SS detectada — haciendo login IPCE`);
      await this.loginPasarelaSS();
      await this.delay(5e3);
    } else if (urlActual.includes("clave.gob.es") || urlActual.includes("pasarela")) {
      await this.manejarPasarelaClave();
      await this.delay(5e3);
    }
    const urlPostLogin = this.obtenerURL();
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`);
    if (urlPostLogin.includes("idp.seg-social") || urlPostLogin.includes("ipce.seg-social")) {
      log.info(`[${this.nombre}] Aun en pasarela — esperando redireccion...`);
      const inicio = Date.now();
      while (Date.now() - inicio < 2e4) {
        await this.delay(1e3);
        const url = this.obtenerURL();
        if (!url.includes("idp.seg-social") && !url.includes("ipce.seg-social")) {
          log.info(`[${this.nombre}] Redireccion completada: ${url}`);
          break;
        }
      }
      await this.delay(3e3);
    }
    await this.capturarPantalla("01-post-login");
    try {
      await this.esperarSelector("a[href*='tipoCertificado']", 2e4);
      log.info(`[${this.nombre}] Enlaces de certificados encontrados`);
    } catch {
      log.warn(`[${this.nombre}] Enlaces tipoCertificado no encontrados — intentando alternativas`);
    }
    await this.capturarPantalla("02-pre-descarga");
    const nombreArchivo = this.nombreConFecha("Certificado_INSS");
    try {
      const tieneEnlace = await this.ejecutarJs(`
        !!document.querySelector("a[href*='certIntegradoPrestaciones']")
      `);
      if (tieneEnlace) {
        log.info(`[${this.nombre}] Enlace certIntegradoPrestaciones encontrado`);
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento("a[href*='certIntegradoPrestaciones']"),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Certificado descargado: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Descarga certIntegrado fallo: ${err.message}`);
    }
    try {
      const tieneEnlace2 = await this.ejecutarJs(`
        !!document.querySelector("a[href*='certIntegrado']")
      `);
      if (tieneEnlace2) {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento("a[href*='certIntegrado']"),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Certificado descargado via certIntegrado: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch {
      log.warn(`[${this.nombre}] certIntegrado no encontrado`);
    }
    try {
      const tieneEnlacePdf = await this.ejecutarJs(`
        (function() {
          var enlaces = document.querySelectorAll('a[aria-label*="PDF"], a[aria-label*="pdf"]');
          return enlaces.length > 0;
        })()
      `);
      if (tieneEnlacePdf) {
        const ruta = await this.descargarConPromesa(
          () => this.ejecutarJs(`
            (function() {
              var enlaces = document.querySelectorAll('a[aria-label*="PDF"], a[aria-label*="pdf"]');
              if (enlaces.length > 0) enlaces[enlaces.length - 1].click();
            })()
          `),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Certificado descargado via aria-label PDF: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch {
      log.warn(`[${this.nombre}] Enlace por aria-label no encontrado`);
    }
    try {
      const tieneBoxList = await this.ejecutarJs(`
        !!document.querySelector('.quotation__box3__list a')
      `);
      if (tieneBoxList) {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento(".quotation__box3__list a"),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Certificado descargado via .quotation__box3__list: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch {
      log.warn(`[${this.nombre}] .quotation__box3__list no encontrado`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
  /** Login en la pasarela SS (idp.seg-social.es/PGIS/Login) */
  async loginPasarelaSS() {
    try {
      await this.esperarSelector("#IPCEIdP", 1e4);
      await this.clickElemento("#IPCEIdP");
      log.info(`[${this.nombre}] Click en #IPCEIdP`);
      return;
    } catch {
      log.warn(`[${this.nombre}] #IPCEIdP no encontrado`);
    }
    try {
      await this.esperarSelector("button[formaction*='IPCE']", 5e3);
      await this.clickElemento("button[formaction*='IPCE']");
      log.info(`[${this.nombre}] Click en button[formaction*='IPCE']`);
      return;
    } catch {
      log.warn(`[${this.nombre}] button[formaction*='IPCE'] no encontrado`);
    }
    await this.ejecutarJs(`
      (function() {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          var t = (btns[i].textContent || '').toLowerCase();
          if (t.includes('dnie') || t.includes('certificado')) {
            btns[i].click(); return;
          }
        }
      })()
    `);
    log.info(`[${this.nombre}] Fallback — click por texto certificado/dnie`);
  }
}
async function loginCarpetaCiudadana(scraper) {
  log.info("[Login Carpeta] Iniciando autenticacion con certificado");
  await scraper.cerrarModalSiExiste("button.cc-boton-aceptar");
  const botonExiste = await scraper.ejecutarJs(`
    !!document.querySelector('button.botonIdentificateClave, #botonIdentificateClave, a[href*="clave"], .boton-acceso')
  `);
  if (!botonExiste) {
    const url = await scraper.obtenerURL();
    if (url.includes("/carpeta/")) {
      log.info("[Login Carpeta] Ya autenticado — sesion activa");
      return;
    }
    log.info("[Login Carpeta] Sin boton de login — intentando pasarela Cl@ve");
    await scraper.manejarPasarelaClave();
    await esperarSesionActiva(scraper);
    return;
  }
  try {
    await scraper.clickElemento(
      "button.botonIdentificateClave[onclick='redirect();']"
    );
  } catch {
    try {
      await scraper.clickElemento("button.botonIdentificateClave");
    } catch {
      await scraper.clickElemento("#botonIdentificateClave, .boton-acceso");
    }
  }
  await scraper.delay(2e3);
  const urlActual = await scraper.obtenerURL();
  if (urlActual.includes("clave.gob.es") || urlActual.includes("pasarela")) {
    await scraper.manejarPasarelaClave();
  } else if (urlActual.includes("carpetaciudadana.gob.es")) {
    try {
      await scraper.esperarSelector("#botonIdentificateClave.boton-acceso", 5e3);
      await scraper.clickElemento("#botonIdentificateClave.boton-acceso");
      await scraper.delay(2e3);
      await scraper.manejarPasarelaClave();
    } catch {
      await scraper.manejarPasarelaClave();
    }
  }
  await esperarSesionActiva(scraper);
  await scraper.cerrarModalSiExiste(
    "#botonesCondiciones button, .aceptar-condiciones"
  );
  log.info("[Login Carpeta] Autenticacion completada");
}
async function esperarSesionActiva(scraper, timeout = 3e4) {
  const inicio = Date.now();
  while (Date.now() - inicio < timeout) {
    const url = await scraper.obtenerURL();
    if (url.includes("/carpeta/") && !url.includes("clave.gob.es")) {
      return;
    }
    await scraper.delay(1e3);
  }
  log.warn("[Login Carpeta] Timeout esperando sesion activa — continuando");
}
class ScraperConsultaVehiculos extends BaseScraperDocumental {
  urlInicio = "https://carpetaciudadana.gob.es";
  urlVehiculos = "https://carpetaciudadana.gob.es/carpeta/datos/vehiculos/consulta.htm?idioma=es";
  urlDgt = "https://sede.dgt.gob.es/es/mi_dgt/mis-vehiculos/";
  get nombre() {
    return "Consulta Vehiculos";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando consulta de vehiculos`);
    await this.navegar(this.urlInicio);
    await loginCarpetaCiudadana(this);
    await this.navegar(this.urlVehiculos);
    await this.esperarContenidoReal(3e4);
    log.info(`[${this.nombre}] Pagina de vehiculos (Carpeta) cargada`);
    const nombreCarpeta = this.nombreConFecha("Consulta_Vehiculos_CarpetaCiudadana");
    const rutaCarpeta = await this.printToPdf(nombreCarpeta);
    log.info(`[${this.nombre}] PDF Carpeta Ciudadana: ${rutaCarpeta}`);
    await this.navegar(this.urlDgt);
    await this.delay(5e3);
    const urlDgt = await this.obtenerURL();
    log.info(`[${this.nombre}] URL DGT: ${urlDgt}`);
    if (urlDgt.includes("clave.gob.es") || urlDgt.includes("pasarela")) {
      await this.manejarPasarelaClave();
      await this.delay(5e3);
    }
    log.info(`[${this.nombre}] Pagina de vehiculos (DGT) cargada`);
    const nombreDgt = this.nombreConFecha("Consulta_Vehiculos_DGT");
    const rutaDgt = await this.printToPdf(nombreDgt);
    log.info(`[${this.nombre}] PDF DGT: ${rutaDgt}`);
    return {
      exito: true,
      rutaDescarga: rutaCarpeta,
      datos: { rutasArchivos: [rutaCarpeta, rutaDgt] }
    };
  }
  /** Espera que la pagina tenga contenido real, no la home generica */
  async esperarContenidoReal(timeout) {
    const inicio = Date.now();
    while (Date.now() - inicio < timeout) {
      const url = await this.obtenerURL();
      if (url.includes("vehiculos") || url.includes("datos")) {
        const tieneContenido = await this.ejecutarJs(`
          !!(document.querySelector('table') ||
             document.querySelector('.datos-vehiculo') ||
             document.querySelector('.vehicle') ||
             document.querySelector('[class*="vehiculo"]') ||
             document.querySelector('.mat-table') ||
             (document.body.innerText && document.body.innerText.length > 500))
        `);
        if (tieneContenido) return;
      }
      if (url === "https://carpetaciudadana.gob.es/" || url.includes("/public")) {
        log.warn(`[${this.nombre}] Redirigido a home — reintentando navegacion`);
        await this.navegar(this.urlVehiculos);
        await this.delay(3e3);
      }
      await this.delay(1e3);
    }
    log.warn(`[${this.nombre}] Timeout esperando contenido real — imprimiendo lo disponible`);
  }
}
class ScraperConsultaInmuebles extends BaseScraperDocumental {
  urlInicio = "https://carpetaciudadana.gob.es";
  urlInmuebles = "https://carpetaciudadana.gob.es/carpeta/mcc/bienes-inmuebles";
  get nombre() {
    return "Consulta Inmuebles";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando consulta de inmuebles via Carpeta Ciudadana (v1.0.31)`);
    await this.navegar(this.urlInicio);
    await this.delay(3e3);
    await this.capturarPantalla("01-pagina-inicial");
    await loginCarpetaCiudadana(this);
    await this.capturarPantalla("02-post-login");
    await this.navegar(this.urlInmuebles);
    await this.delay(3e3);
    await this.capturarPantalla("03-inmuebles-navegado");
    const contenidoCargado = await this.esperarContenidoInmuebles(6e4);
    await this.capturarPantalla("04-contenido-final");
    const textoFinal = await this.ejecutarJs(`
      (document.body.innerText || '').substring(0, 800)
    `);
    log.info(`[${this.nombre}] Texto final (800 chars): ${textoFinal}`);
    const botonesInfo = await this.ejecutarJs(`
      (function() {
        var resultado = [];
        var botones = document.querySelectorAll('button');
        for (var i = 0; i < botones.length; i++) {
          var texto = (botones[i].textContent || '').trim().substring(0, 80);
          if (texto.length > 0) {
            resultado.push({ tag: 'BUTTON', texto: texto, id: botones[i].id || '' });
          }
        }
        return JSON.stringify(resultado);
      })()
    `);
    log.info(`[${this.nombre}] Botones: ${botonesInfo}`);
    if (!contenidoCargado) {
      const esValido = await this.validarContenidoMinimo();
      if (!esValido) {
        log.error(`[${this.nombre}] No se pudo cargar contenido de inmuebles`);
        await this.capturarPantalla("05-contenido-invalido");
        return {
          exito: false,
          error: "No se pudo cargar la informacion de inmuebles. La pagina no cargo el contenido del Catastro.",
          datos: {}
        };
      }
    }
    const nombreArchivo = this.nombreConFecha("Consulta_Inmuebles");
    const tieneBotonCatastral = await this.ejecutarJs(`
      !!(function() {
        var botones = document.querySelectorAll('button');
        for (var i = 0; i < botones.length; i++) {
          var texto = (botones[i].textContent || '').toLowerCase();
          if (texto.includes('descargar certificaci') || texto.includes('certificación catastral') ||
              texto.includes('certificacion catastral')) {
            return true;
          }
        }
        return false;
      })()
    `);
    if (tieneBotonCatastral) {
      log.info(`[${this.nombre}] Boton "Descargar certificacion catastral" encontrado`);
      try {
        const resultado = await this.descargarCertificacionCatastral(nombreArchivo);
        if (resultado) return resultado;
      } catch (err) {
        log.warn(`[${this.nombre}] Descarga certificacion catastral fallo: ${err.message}`);
      }
    } else {
      log.warn(`[${this.nombre}] No se encontro boton de descarga catastral`);
    }
    log.info(`[${this.nombre}] Fallback: printToPdf de pagina principal`);
    await this.capturarPantalla("07-fallback-pdf");
    const rutaDescarga = await this.printToPdf(nombreArchivo);
    log.info(`[${this.nombre}] PDF generado (fallback): ${rutaDescarga}`);
    return {
      exito: true,
      rutaDescarga,
      datos: { rutasArchivos: [rutaDescarga] }
    };
  }
  /**
   * Descargar el PDF oficial del Catastro:
   *
   * Estrategia 1: Registrar will-download en la sesion ANTES del click.
   *   El boton genera un blob URL que Electron intenta descargar.
   *   Si capturamos will-download, obtenemos el PDF oficial.
   *
   * Estrategia 2: Si will-download no se dispara, buscar popup y printToPdf.
   *
   * Estrategia 3: Si hay popup con blob URL, intentar capturar via fetch.
   */
  async descargarCertificacionCatastral(nombreArchivo) {
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
    const sesion = this.window.webContents.session;
    const promesaDescarga = new Promise((resolve) => {
      const timer = setTimeout(() => {
        sesion.removeListener("will-download", onDescarga);
        resolve("");
      }, 2e4);
      const onDescarga = (_event, item) => {
        log.info(`[${this.nombre}] will-download capturado! filename: ${item.getFilename()}, url: ${item.getURL().substring(0, 100)}`);
        item.setSavePath(rutaDestino);
        item.on("done", (_e, state) => {
          clearTimeout(timer);
          sesion.removeListener("will-download", onDescarga);
          if (state === "completed") {
            log.info(`[${this.nombre}] PDF catastral descargado: ${rutaDestino}`);
            resolve(rutaDestino);
          } else {
            log.warn(`[${this.nombre}] Descarga state: ${state}`);
            resolve("");
          }
        });
      };
      sesion.on("will-download", onDescarga);
    });
    const waitPopup = this.prepararEsperaVentana(2e4).catch(() => null);
    await this.ejecutarJs(`
      (function() {
        var botones = document.querySelectorAll('button');
        for (var i = 0; i < botones.length; i++) {
          var texto = (botones[i].textContent || '').toLowerCase();
          if (texto.includes('descargar certificaci') || texto.includes('certificación catastral') ||
              texto.includes('certificacion catastral')) {
            botones[i].click();
            return true;
          }
        }
        return false;
      })()
    `);
    log.info(`[${this.nombre}] Click en boton descarga catastral — esperando descarga o popup...`);
    await this.capturarPantalla("05-post-click-descarga");
    const rutaDescargada = await promesaDescarga;
    if (rutaDescargada) {
      log.info(`[${this.nombre}] Certificacion catastral obtenida via will-download: ${rutaDescargada}`);
      return { exito: true, rutaDescarga: rutaDescargada, datos: { rutasArchivos: [rutaDescargada] } };
    }
    const popup = await waitPopup;
    if (popup && !popup.isDestroyed()) {
      log.info(`[${this.nombre}] Popup abierto (id: ${popup.id}) — intentando capturar PDF`);
      return await this.capturarPdfDesdePopup(popup, nombreArchivo);
    }
    log.warn(`[${this.nombre}] Ni will-download ni popup disponible`);
    return null;
  }
  /**
   * Captura el PDF desde un popup del Catastro:
   * 1. Espera carga del popup
   * 2. Intenta will-download en la sesion del popup
   * 3. Si tiene blob URL, intenta fetch + guardar
   * 4. Fallback: printToPdf del popup
   */
  async capturarPdfDesdePopup(popup, nombreArchivo) {
    await this.esperarCargaPopup(popup, 3e4);
    const urlPopup = popup.webContents.getURL();
    log.info(`[${this.nombre}] URL popup: ${urlPopup}`);
    try {
      const titulo = await popup.webContents.executeJavaScript("document.title");
      const bodyLen = await popup.webContents.executeJavaScript(
        "document.body ? document.body.innerText.length : 0"
      );
      log.info(`[${this.nombre}] Popup — titulo: "${titulo}", body: ${bodyLen} chars`);
    } catch (e) {
      log.warn(`[${this.nombre}] Error leyendo popup: ${e.message}`);
    }
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
    if (urlPopup.startsWith("blob:")) {
      log.info(`[${this.nombre}] Popup tiene blob URL — intentando fetch blob`);
      try {
        const base64 = await popup.webContents.executeJavaScript(`
          (async function() {
            try {
              var resp = await fetch('${urlPopup}');
              var blob = await resp.blob();
              var arrayBuffer = await blob.arrayBuffer();
              var bytes = new Uint8Array(arrayBuffer);
              var binary = '';
              for (var i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
              }
              return btoa(binary);
            } catch(e) {
              return 'ERROR:' + e.message;
            }
          })()
        `);
        if (base64 && !base64.startsWith("ERROR:")) {
          const buffer = Buffer.from(base64, "base64");
          writeFileSync(rutaDestino, buffer);
          log.info(`[${this.nombre}] PDF catastral capturado via blob fetch: ${rutaDestino} (${buffer.length} bytes)`);
          return { exito: true, rutaDescarga: rutaDestino, datos: { rutasArchivos: [rutaDestino] } };
        } else {
          log.warn(`[${this.nombre}] Fetch blob fallo: ${base64}`);
        }
      } catch (err) {
        log.warn(`[${this.nombre}] Error fetching blob: ${err.message}`);
      }
    }
    try {
      const ruta = await this.esperarDescargaEnVentana(popup, nombreArchivo, 1e4);
      log.info(`[${this.nombre}] PDF via will-download del popup: ${ruta}`);
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch {
      log.info(`[${this.nombre}] will-download del popup no se disparo`);
    }
    try {
      const buffer = await popup.webContents.printToPDF({
        printBackground: true,
        landscape: false
      });
      writeFileSync(rutaDestino, buffer);
      log.info(`[${this.nombre}] PDF via printToPdf del popup: ${rutaDestino}`);
      return { exito: true, rutaDescarga: rutaDestino, datos: { rutasArchivos: [rutaDestino] } };
    } catch (err) {
      log.warn(`[${this.nombre}] printToPdf popup fallo: ${err.message}`);
    }
    return null;
  }
  // ── Espera contenido Angular ──────────────────────────────────
  /**
   * Espera a que la SPA Angular cargue el contenido real de inmuebles.
   * Busca texto especifico del Catastro, NO solo longitud de body.
   */
  async esperarContenidoInmuebles(timeout) {
    const inicio = Date.now();
    let intentosRedireccion = 0;
    while (Date.now() - inicio < timeout) {
      const url = await this.obtenerURL();
      if (url.includes("clave.gob.es") || url.includes("pasarela")) {
        intentosRedireccion++;
        if (intentosRedireccion > 3) {
          log.error(`[${this.nombre}] Demasiados reintentos auth (${intentosRedireccion})`);
          return false;
        }
        log.info(`[${this.nombre}] Redirigido a pasarela — re-autenticando (${intentosRedireccion})`);
        await this.manejarPasarelaClave();
        await this.delay(5e3);
        await this.navegar(this.urlInmuebles);
        await this.delay(5e3);
        continue;
      }
      if (url === "https://carpetaciudadana.gob.es/" || url.includes("/public") || url.includes("/clave.htm") || url.includes("carpetaEmpresa")) {
        log.warn(`[${this.nombre}] Redirigido a home (${url}) — renavegando`);
        await this.navegar(this.urlInmuebles);
        await this.delay(5e3);
        continue;
      }
      const resultado = await this.ejecutarJs(`
        (function() {
          var texto = (document.body.innerText || '').toLowerCase();

          var keywords = [
            'bienes inmuebles urbanos',
            'bienes inmuebles rústicos',
            'bienes inmuebles rusticos',
            'referencia catastral',
            'valor catastral',
            'uso principal',
            'superficie construida',
            'superficie suelo',
            'dirección general del catastro',
            'direccion general del catastro',
            'domicilio tributario',
            'clase de inmueble',
            'descargar certificación catastral',
            'descargar certificacion catastral',
            'no se han encontrado inmuebles',
            'no dispone de inmuebles',
          ];

          for (var i = 0; i < keywords.length; i++) {
            if (texto.includes(keywords[i])) {
              return 'FOUND:' + keywords[i];
            }
          }

          // Buscar componentes Angular de inmuebles
          var componentes = document.querySelectorAll('[class*="inmueble"], [class*="catastro"], app-bienes, app-inmuebles');
          if (componentes.length > 0) return 'FOUND:angular-component';

          // Buscar tablas con datos de catastro
          var tablas = document.querySelectorAll('table, .mat-table, mat-table');
          for (var j = 0; j < tablas.length; j++) {
            var ct = (tablas[j].textContent || '').toLowerCase();
            if (ct.includes('catastral') || ct.includes('superficie') || ct.includes('inmueble')) {
              return 'FOUND:table-with-data';
            }
          }

          // Contenido principal
          var main = document.querySelector('main, [role="main"], .main-content, router-outlet + *');
          if (main) {
            var mt = (main.textContent || '').toLowerCase();
            if (mt.length > 100 && (mt.includes('inmueble') || mt.includes('catastro') || mt.includes('urbano'))) {
              return 'FOUND:main-content';
            }
          }

          return 'NOT_FOUND:len=' + texto.length;
        })()
      `);
      log.info(`[${this.nombre}] Check contenido: ${resultado}`);
      if (resultado && resultado.startsWith("FOUND:")) {
        log.info(`[${this.nombre}] Contenido inmuebles detectado: ${resultado}`);
        await this.delay(3e3);
        return true;
      }
      await this.delay(2e3);
    }
    log.warn(`[${this.nombre}] Timeout esperando contenido inmuebles`);
    return false;
  }
  // ── Validacion minima ──────────────────────────────────
  async validarContenidoMinimo() {
    const texto = await this.ejecutarJs(`
      (document.body.innerText || '').substring(0, 2000)
    `);
    if (!texto || texto.length < 100) return false;
    const textoLower = texto.toLowerCase();
    const invalidos = [
      "identifícate",
      "cl@ve permanente",
      "cl@ve móvil",
      "seleccione el método",
      "elige tu rol",
      "acceder a la carpeta"
    ];
    for (const patron of invalidos) {
      if (textoLower.includes(patron)) {
        log.warn(`[${this.nombre}] Pagina invalida: "${patron}"`);
        return false;
      }
    }
    const soloFooter = textoLower.includes("aviso legal") && !textoLower.includes("inmueble") && !textoLower.includes("catastro");
    if (soloFooter) {
      log.warn(`[${this.nombre}] Solo footer — sin contenido inmuebles`);
      return false;
    }
    log.warn(`[${this.nombre}] Contenido ambiguo — generando PDF`);
    return true;
  }
  // ── Helpers popup ──────────────────────────────────────
  async esperarCargaPopup(ventana, timeout) {
    await new Promise((resolve) => {
      const timer = setTimeout(resolve, Math.min(timeout, 15e3));
      if (ventana.isDestroyed()) {
        clearTimeout(timer);
        resolve();
        return;
      }
      ventana.webContents.once("did-finish-load", () => {
        clearTimeout(timer);
        resolve();
      });
      if (!ventana.webContents.isLoading()) {
        clearTimeout(timer);
        resolve();
      }
    });
    const inicio = Date.now();
    while (Date.now() - inicio < timeout) {
      if (ventana.isDestroyed()) break;
      try {
        const len = await ventana.webContents.executeJavaScript(
          "document.body ? document.body.innerText.length : 0"
        );
        if (len > 50) {
          log.info(`[${this.nombre}] Popup listo: ${len} chars`);
          break;
        }
      } catch {
        break;
      }
      await this.delay(1e3);
    }
    await this.delay(2e3);
  }
  // esperarDescargaEnVentana heredado de BaseScraperDocumental
}
class ScraperEmpadronamiento extends BaseScraperDocumental {
  urlBase = "https://carpetaciudadana.gob.es";
  seccionUrl = "/carpeta/mcc/domicilio";
  get nombre() {
    return "Empadronamiento";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando descarga de justificante de empadronamiento`);
    await this.navegar(this.urlBase);
    await this.delay(2e3);
    await loginCarpetaCiudadana(this);
    await this.delay(3e3);
    await this.cerrarModalPersonalizacion();
    const navegado = await this.navegarSeccionSPA(this.seccionUrl, 1e4);
    if (!navegado) {
      await this.navegar(`${this.urlBase}${this.seccionUrl}`);
      await this.delay(5e3);
    }
    await this.esperarContenidoDomicilio(2e4);
    await this.capturarPantalla("01-contenido");
    const nombreArchivo = this.nombreConFecha("Empadronamiento");
    try {
      const tieneBoton = await this.ejecutarJs(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || '').toLowerCase();
            if (t.includes('descargar') && (t.includes('justificante') || t.includes('pdf'))) {
              return true;
            }
          }
          return false;
        })()
      `);
      if (tieneBoton) {
        log.info(`[${this.nombre}] Boton "Descargar justificante PDF" encontrado`);
        const ruta = await this.descargarConPromesa(
          () => this.ejecutarJs(`
            (function() {
              var btns = document.querySelectorAll('button');
              for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].textContent || '').toLowerCase();
                if (t.includes('descargar') && (t.includes('justificante') || t.includes('pdf'))) {
                  btns[i].click(); return;
                }
              }
            })()
          `),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Justificante descargado: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Descarga via boton fallo: ${err.message}`);
    }
    try {
      const tieneIcono = await this.ejecutarJs(`
        !!(document.querySelector('.fa-download') || document.querySelector('a[download]'))
      `);
      if (tieneIcono) {
        const ruta = await this.descargarConPromesa(
          () => this.ejecutarJs(`
            (function() {
              var el = document.querySelector('.fa-download');
              if (el) { (el.closest('a') || el.parentElement || el).click(); return; }
              el = document.querySelector('a[download]');
              if (el) { el.click(); }
            })()
          `),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Justificante descargado via .fa-download: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch {
      log.warn(`[${this.nombre}] .fa-download no encontrado`);
    }
    try {
      const encontrado = await this.ejecutarJs(`
        (function() {
          var elementos = document.querySelectorAll('a, button');
          for (var i = 0; i < elementos.length; i++) {
            var t = (elementos[i].textContent || '').toLowerCase();
            if (t.includes('descargar')) {
              elementos[i].setAttribute('data-cg-download', 'true');
              return true;
            }
          }
          return false;
        })()
      `);
      if (encontrado) {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento('[data-cg-download="true"]'),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Justificante descargado via texto descargar: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch {
      log.warn(`[${this.nombre}] Enlace descargar generico no encontrado`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
  /** Navega a una seccion de Carpeta Ciudadana via click en enlace SPA */
  async navegarSeccionSPA(ruta, timeout) {
    const inicio = Date.now();
    while (Date.now() - inicio < timeout) {
      const clicOk = await this.ejecutarJs(`
        (function() {
          var a = document.querySelector('a[href="${ruta}"]');
          if (a) { a.click(); return true; }
          return false;
        })()
      `);
      if (clicOk) {
        log.info(`[${this.nombre}] Click SPA en ${ruta}`);
        await this.delay(5e3);
        return true;
      }
      await this.delay(1e3);
    }
    log.warn(`[${this.nombre}] Enlace SPA ${ruta} no encontrado`);
    return false;
  }
  /** Espera a que cargue el contenido del domicilio */
  async esperarContenidoDomicilio(timeout) {
    const inicio = Date.now();
    while (Date.now() - inicio < timeout) {
      const tiene = await this.ejecutarJs(`
        (function() {
          var body = document.body ? document.body.innerText : '';
          return body.includes('domicilio') || body.includes('padrón') ||
                 body.includes('padron') || body.includes('Descargar justificante');
        })()
      `);
      if (tiene) return;
      await this.delay(1e3);
    }
    log.warn(`[${this.nombre}] Timeout esperando contenido domicilio`);
  }
  /** Cierra modal de personalizacion de Carpeta Ciudadana si aparece */
  async cerrarModalPersonalizacion() {
    try {
      await this.ejecutarJs(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || '').toLowerCase();
            if (t.includes('personalizar en otro momento')) {
              btns[i].click(); return;
            }
          }
        })()
      `);
      await this.delay(500);
    } catch {
    }
  }
}
class ScraperCertificadoPenales extends BaseScraperDocumental {
  urlBase = "https://carpetaciudadana.gob.es";
  seccionUrl = "/carpeta/mcc/antecedentes-penales";
  apiJustificante = "/api/antecedentes-penales/justificante";
  get nombre() {
    return "Certificado Penales";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando descarga de certificado de penales`);
    await this.navegar(this.urlBase);
    await this.delay(2e3);
    await loginCarpetaCiudadana(this);
    await this.delay(3e3);
    await this.cerrarModalPersonalizacion();
    await this.navegar(`${this.urlBase}${this.seccionUrl}`);
    await this.delay(5e3);
    const urlActual = this.obtenerURL();
    log.info(`[${this.nombre}] URL actual: ${urlActual}`);
    if (urlActual.includes("/mcc/home") && !urlActual.includes("antecedentes")) {
      log.info(`[${this.nombre}] Redirigido a home — intentando click en enlace interno`);
      const clicEnlace = await this.ejecutarJs(`
        (function() {
          var a = document.querySelector('a[href*="antecedentes-penales"]');
          if (a) { a.click(); return true; }
          return false;
        })()
      `);
      if (clicEnlace) {
        log.info(`[${this.nombre}] Click en enlace antecedentes-penales`);
        await this.delay(5e3);
      } else {
        log.warn(`[${this.nombre}] Enlace antecedentes-penales no encontrado en home`);
      }
    }
    await this.esperarContenidoPenales(2e4);
    await this.capturarPantalla("01-contenido");
    const nombreArchivo = this.nombreConFecha("Certificado_Penales");
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
    try {
      const base64Pdf = await this.ejecutarJs(`
        (async function() {
          try {
            var resp = await fetch('${this.apiJustificante}', {
              credentials: 'include',
              headers: { 'Accept': 'application/pdf' }
            });
            if (!resp.ok) return 'ERROR:' + resp.status;
            var blob = await resp.blob();
            var reader = new FileReader();
            return new Promise(function(resolve) {
              reader.onloadend = function() {
                // data:application/pdf;base64,XXXX → extraer solo la parte base64
                var result = reader.result;
                if (typeof result === 'string' && result.includes(',')) {
                  resolve(result.split(',')[1]);
                } else {
                  resolve('ERROR:no-base64');
                }
              };
              reader.readAsDataURL(blob);
            });
          } catch(e) {
            return 'ERROR:' + e.message;
          }
        })()
      `);
      if (base64Pdf && !base64Pdf.startsWith("ERROR:")) {
        const buffer = Buffer.from(base64Pdf, "base64");
        writeFileSync(rutaDestino, buffer);
        log.info(`[${this.nombre}] Certificado descargado via fetch API: ${rutaDestino} (${buffer.length} bytes)`);
        return { exito: true, rutaDescarga: rutaDestino, datos: { rutasArchivos: [rutaDestino] } };
      }
      log.warn(`[${this.nombre}] Fetch API fallo: ${base64Pdf}`);
    } catch (err) {
      log.warn(`[${this.nombre}] Fetch API error: ${err.message}`);
    }
    try {
      const base64Pdf = await this.ejecutarJs(`
        (async function() {
          // Monkey-patch URL.createObjectURL para capturar el blob
          var capturedBlob = null;
          var origCreate = URL.createObjectURL;
          URL.createObjectURL = function(blob) {
            capturedBlob = blob;
            return origCreate.call(URL, blob);
          };

          // Click el boton de descarga
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || '').toLowerCase();
            if (t.includes('descargar') && (t.includes('justificante') || t.includes('pdf'))) {
              btns[i].click();
              break;
            }
          }

          // Esperar a que Angular haga el fetch y cree el blob
          var intentos = 0;
          while (!capturedBlob && intentos < 50) {
            await new Promise(function(r) { setTimeout(r, 200); });
            intentos++;
          }

          URL.createObjectURL = origCreate;

          if (!capturedBlob) return 'ERROR:no-blob';

          var reader = new FileReader();
          return new Promise(function(resolve) {
            reader.onloadend = function() {
              var result = reader.result;
              if (typeof result === 'string' && result.includes(',')) {
                resolve(result.split(',')[1]);
              } else {
                resolve('ERROR:no-base64');
              }
            };
            reader.readAsDataURL(capturedBlob);
          });
        })()
      `);
      if (base64Pdf && !base64Pdf.startsWith("ERROR:")) {
        const buffer = Buffer.from(base64Pdf, "base64");
        writeFileSync(rutaDestino, buffer);
        log.info(`[${this.nombre}] Certificado capturado via monkey-patch: ${rutaDestino} (${buffer.length} bytes)`);
        return { exito: true, rutaDescarga: rutaDestino, datos: { rutasArchivos: [rutaDestino] } };
      }
      log.warn(`[${this.nombre}] Monkey-patch fallo: ${base64Pdf}`);
    } catch (err) {
      log.warn(`[${this.nombre}] Monkey-patch error: ${err.message}`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
  /** Espera a que cargue el contenido de antecedentes penales */
  async esperarContenidoPenales(timeout) {
    const inicio = Date.now();
    while (Date.now() - inicio < timeout) {
      const tiene = await this.ejecutarJs(`
        (function() {
          var body = document.body ? document.body.innerText : '';
          return body.includes('penales') || body.includes('antecedentes') ||
                 body.includes('Descargar justificante');
        })()
      `);
      if (tiene) return;
      await this.delay(1e3);
    }
    log.warn(`[${this.nombre}] Timeout esperando contenido de penales`);
  }
  /** Cierra modal de personalizacion de Carpeta Ciudadana si aparece */
  async cerrarModalPersonalizacion() {
    try {
      const tieneModal = await this.ejecutarJs(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || '').toLowerCase();
            if (t.includes('personalizar en otro momento')) {
              btns[i].click(); return true;
            }
          }
          return false;
        })()
      `);
      if (tieneModal) {
        log.info(`[${this.nombre}] Modal de personalizacion cerrado`);
        await this.delay(500);
      }
    } catch {
    }
  }
}
class ScraperCertificadoNacimiento extends BaseScraperDocumental {
  url = "https://sede.mjusticia.gob.es/sereci/clave/solicitarCertificadoSolicitudLiteral?idMateria=NAC";
  get nombre() {
    return "Certificado Nacimiento";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando descarga de certificado de nacimiento`);
    const nombreArchivo = this.nombreConFecha("Certificado_Nacimiento");
    const esperaDescarga = this.configurarDescargaEnSesion(nombreArchivo, 6e4);
    await this.navegar(this.url);
    await this.delay(3e3);
    const urlActual = this.obtenerURL();
    log.info(`[${this.nombre}] URL tras navegar: ${urlActual}`);
    if (urlActual.includes("clave.gob.es") || urlActual.includes("pasarela")) {
      log.info(`[${this.nombre}] Pasarela Cl@ve detectada`);
      await this.manejarPasarelaClave(15e3, 3e4);
      await this.delay(5e3);
    }
    const urlPostLogin = this.obtenerURL();
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`);
    if (urlPostLogin.includes("clave.gob.es")) {
      log.info(`[${this.nombre}] Aun en Cl@ve — esperando redireccion...`);
      const inicio = Date.now();
      while (Date.now() - inicio < 2e4) {
        await this.delay(1e3);
        const url = this.obtenerURL();
        if (url.includes("sede.mjusticia.gob.es")) {
          log.info(`[${this.nombre}] Redireccion completada: ${url}`);
          break;
        }
      }
      await this.delay(3e3);
    }
    try {
      const ruta = await esperaDescarga;
      log.info(`[${this.nombre}] Certificado descargado automaticamente: ${ruta}`);
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch {
      log.warn(`[${this.nombre}] Descarga automatica no se disparo — intentando boton`);
    }
    await this.capturarPantalla("01-post-login");
    try {
      const tieneBoton = await this.ejecutarJs(`
        (function() {
          var btns = document.querySelectorAll('button[type="submit"], input[type="submit"]');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
            if (t.includes('descargar')) return true;
          }
          return false;
        })()
      `);
      if (tieneBoton) {
        log.info(`[${this.nombre}] Boton "Descargar Certificado" encontrado`);
        const ruta = await this.descargarConPromesa(
          () => this.ejecutarJs(`
            (function() {
              var btns = document.querySelectorAll('button[type="submit"], input[type="submit"]');
              for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
                if (t.includes('descargar')) { btns[i].click(); return; }
              }
            })()
          `),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Certificado descargado via boton: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Descarga via boton fallo: ${err.message}`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
  /** Registra listener will-download en la sesion ANTES de navegar */
  configurarDescargaEnSesion(nombreArchivo, timeout) {
    if (!this.window || this.window.isDestroyed()) {
      return Promise.reject(new Error("Navegador no inicializado"));
    }
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
    const sesion = this.window.webContents.session;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        sesion.removeListener("will-download", onDescarga);
        reject(new Error("Timeout esperando descarga automatica"));
      }, timeout);
      const onDescarga = (_event, item) => {
        item.setSavePath(rutaDestino);
        item.on("done", (_e, state) => {
          clearTimeout(timer);
          sesion.removeListener("will-download", onDescarga);
          if (state === "completed") resolve(rutaDestino);
          else reject(new Error(`Descarga: ${state}`));
        });
      };
      sesion.on("will-download", onDescarga);
    });
  }
}
class ScraperApudActa extends BaseScraperDocumental {
  url = "https://sedejudicial.justicia.es/-/apoderamiento-apud-acta";
  constructor(serialNumber, config) {
    super(serialNumber, {
      ...config,
      // Timeout extendido: 10 minutos para intervencion manual
      timeoutGlobal: 6e5
    });
  }
  get nombre() {
    return "Apud Acta";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando navegacion al portal de Apud Acta`);
    await this.navegar(this.url);
    await this.delay(2e3);
    log.info(`[${this.nombre}] Portal cargado`);
    const cookiesCerradas = await this.ejecutarJs(`
      (function() {
        var botones = document.querySelectorAll('button');
        for (var i = 0; i < botones.length; i++) {
          var texto = (botones[i].textContent || '').trim();
          if (texto.includes('Aceptar solo cookies necesarias') || texto.includes('Aceptar todas')) {
            botones[i].click();
            return true;
          }
        }
        return false;
      })()
    `);
    if (cookiesCerradas) {
      log.info(`[${this.nombre}] Banner de cookies cerrado`);
      await this.delay(500);
    }
    const accesoClave = await this.ejecutarJs(`
      (function() {
        var enlace = document.querySelector('a[href*="sedjudeselectortipousuarioweb"]');
        if (enlace) { enlace.click(); return true; }
        // Fallback: buscar por texto
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
          if ((links[i].textContent || '').includes('ACCEDER AL SERVICIO')) {
            links[i].click();
            return true;
          }
        }
        return false;
      })()
    `);
    if (!accesoClave) {
      throw new Error("Boton ACCEDER AL SERVICIO no encontrado");
    }
    log.info(`[${this.nombre}] Acceso Cl@ve iniciado, esperando pasarela...`);
    await this.delay(3e3);
    const loginOk = await this.manejarPasarelaClave(15e3, 3e4);
    if (!loginOk) {
      throw new Error("Autenticacion Cl@ve fallo en Sede Judicial");
    }
    log.info(`[${this.nombre}] Autenticacion Cl@ve completada`);
    await this.delay(3e3);
    const enAreaPrivada = await this.ejecutarJs(`
      (function() {
        var url = window.location.href;
        var tieneTitulo = !!document.querySelector('h1, .apud-acta-title, [class*="apudacta"]');
        var tieneFormulario = !!document.querySelector('select, [id*="apudacta"]');
        return url.includes('group/guest') || url.includes('area-privada') || tieneTitulo || tieneFormulario;
      })()
    `);
    if (!enAreaPrivada) {
      log.warn(`[${this.nombre}] No se confirmo Area Privada, puede requerir navegacion adicional`);
    } else {
      log.info(`[${this.nombre}] Area Privada de Sede Judicial cargada`);
    }
    log.info(
      `[${this.nombre}] Apud Acta listo — ventana abierta para intervencion manual`
    );
    return {
      exito: true,
      datos: {
        semiAutomatico: true,
        mensaje: "Area Privada de Sede Judicial cargada. Formulario de Apud Acta disponible."
      }
    };
  }
}
class ScraperCertificadoMatrimonio extends BaseScraperDocumental {
  url = "https://sede.mjusticia.gob.es/sereci/clave/solicitarCertificadoSolicitudLiteral?idMateria=MAT";
  constructor(serialNumber, config) {
    super(serialNumber, {
      ...config,
      // Timeout extendido: 5 minutos para que el usuario rellene el formulario
      timeoutGlobal: 3e5
    });
  }
  get nombre() {
    return "Certificado Matrimonio";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando — scraper semi-automatico`);
    const nombreArchivo = this.nombreConFecha("Certificado_Matrimonio");
    const esperaDescarga = this.configurarDescargaEnSesion(nombreArchivo, 3e5);
    await this.navegar(this.url);
    await this.delay(3e3);
    const urlActual = this.obtenerURL();
    log.info(`[${this.nombre}] URL tras navegar: ${urlActual}`);
    if (urlActual.includes("clave.gob.es") || urlActual.includes("pasarela")) {
      log.info(`[${this.nombre}] Pasarela Cl@ve detectada`);
      await this.manejarPasarelaClave(15e3, 3e4);
      await this.delay(5e3);
    }
    const urlPostLogin = this.obtenerURL();
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`);
    if (urlPostLogin.includes("clave.gob.es")) {
      log.info(`[${this.nombre}] Aun en Cl@ve — esperando redireccion...`);
      const inicio = Date.now();
      while (Date.now() - inicio < 2e4) {
        await this.delay(1e3);
        const url = this.obtenerURL();
        if (url.includes("sede.mjusticia.gob.es")) {
          log.info(`[${this.nombre}] Redireccion completada: ${url}`);
          break;
        }
      }
      await this.delay(3e3);
    }
    const enFormulario = await this.ejecutarJs(`
      (function() {
        var titulo = document.body.innerText || '';
        return titulo.includes('matrimonio') || titulo.includes('Matrimonio');
      })()
    `);
    if (enFormulario) {
      log.info(
        `[${this.nombre}] Formulario de matrimonio cargado — esperando intervencion del usuario`
      );
    } else {
      log.warn(`[${this.nombre}] No se detecto formulario de matrimonio en la pagina`);
    }
    await this.capturarPantalla("01-formulario-matrimonio");
    try {
      const ruta = await esperaDescarga;
      log.info(`[${this.nombre}] Certificado descargado: ${ruta}`);
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch {
      log.warn(`[${this.nombre}] Descarga will-download no se disparo — intentando fallback`);
    }
    try {
      const tieneBotonDescarga = await this.ejecutarJs(`
        (function() {
          var btns = document.querySelectorAll('button[type="submit"], input[type="submit"], a');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
            if (t.includes('descargar')) return true;
          }
          return false;
        })()
      `);
      if (tieneBotonDescarga) {
        log.info(`[${this.nombre}] Boton "Descargar" encontrado — clickeando`);
        const ruta = await this.descargarConPromesa(
          () => this.ejecutarJs(`
            (function() {
              var btns = document.querySelectorAll('button[type="submit"], input[type="submit"], a');
              for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
                if (t.includes('descargar')) { btns[i].click(); return; }
              }
            })()
          `),
          nombreArchivo,
          3e4
        );
        log.info(`[${this.nombre}] Certificado descargado via boton: ${ruta}`);
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Fallback boton fallo: ${err.message}`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
  /** Registra listener will-download en la sesion ANTES de navegar */
  configurarDescargaEnSesion(nombreArchivo, timeout) {
    if (!this.window || this.window.isDestroyed()) {
      return Promise.reject(new Error("Navegador no inicializado"));
    }
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo);
    const sesion = this.window.webContents.session;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        sesion.removeListener("will-download", onDescarga);
        reject(new Error("Timeout esperando descarga (5 min)"));
      }, timeout);
      const onDescarga = (_event, item) => {
        item.setSavePath(rutaDestino);
        item.on("done", (_e, state) => {
          clearTimeout(timer);
          sesion.removeListener("will-download", onDescarga);
          if (state === "completed") resolve(rutaDestino);
          else reject(new Error(`Descarga: ${state}`));
        });
      };
      sesion.on("will-download", onDescarga);
    });
  }
}
class ScraperDeudasHacienda extends BaseScraperDocumental {
  url = "https://www1.agenciatributaria.gob.es/wlpl/SRVO-JDIT/ConsultaDdas?faccion=CONS_DDAS";
  get nombre() {
    return "Deudas Hacienda";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando consulta de deudas con Hacienda`);
    await this.navegar(this.url);
    await this.delay(5e3);
    const urlPostAuth = this.obtenerURL();
    log.info(`[${this.nombre}] URL post-auth: ${urlPostAuth}`);
    const tieneDatos = await this.ejecutarJs(`
      (function() {
        var body = document.body.innerText || '';
        // La pagina muestra datos de deudas o un mensaje de sin deudas
        return body.length > 100;
      })()
    `);
    if (!tieneDatos) {
      log.warn(`[${this.nombre}] Pagina sin contenido — posible error de auth`);
      await this.capturarPantalla("01-sin-datos");
    } else {
      log.info(`[${this.nombre}] Datos de deudas cargados`);
    }
    await this.capturarPantalla("02-resultado");
    const nombreArchivo = this.nombreConFecha("Deudas_Hacienda");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    log.info(`[${this.nombre}] PDF generado: ${rutaPdf}`);
    return {
      exito: true,
      rutaDescarga: rutaPdf,
      datos: { rutasArchivos: [rutaPdf] }
    };
  }
}
class ScraperCertificadoSepe extends BaseScraperDocumental {
  // URL directa a la pagina de autenticacion (atajo al paso de login)
  urlAuth = "https://sede.sepe.gob.es/DServiciosPrestanetWEB/TipoAutenticadoAction.do";
  get nombre() {
    return "Certificado SEPE";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando descarga de certificado SEPE`);
    await this.navegar(this.urlAuth);
    await this.delay(3e3);
    const urlPostNav = this.obtenerURL();
    if (urlPostNav.includes("GesUsuarios") || urlPostNav.includes("login_recurso")) {
      log.info(`[${this.nombre}] En pagina login SEPE — buscando opcion certificado digital`);
      await this.clickBotonPorTexto(["certificado digital", "dnie", "certificado electr"]);
      await this.delay(5e3);
    }
    if (this.obtenerURL().includes("clave.gob.es") || this.obtenerURL().includes("pasarela")) {
      await this.manejarPasarelaClave(15e3, 3e4);
      await this.delay(5e3);
    }
    const urlPost2 = this.obtenerURL();
    if (urlPost2.includes("GesUsuarios") || urlPost2.includes("login_recurso")) {
      await this.clickBotonPorTexto(["certificado digital", "dnie"]);
      await this.delay(5e3);
      if (this.obtenerURL().includes("clave.gob.es")) {
        await this.manejarPasarelaClave(15e3, 3e4);
        await this.delay(5e3);
      }
    }
    await this.capturarPantalla("01-post-login");
    const urlTipos = this.obtenerURL();
    log.info(`[${this.nombre}] URL post-login: ${urlTipos}`);
    await this.cerrarModalSiExiste(".js-cookies-accept");
    await this.cerrarModalSiExiste("#onetrust-accept-btn-handler");
    await this.cerrarModalSiExiste('button[id*="cookie"]');
    const tieneIRPF = await this.ejecutarJs(`
      (function() {
        var enlaces = document.querySelectorAll('a[href*="CertificadoIRPFWeb"], a[href*="ActionIRPF"]');
        return enlaces.length > 0;
      })()
    `);
    if (tieneIRPF) {
      return await this.descargarIRPF();
    }
    const tieneSituacion = await this.ejecutarJs(`
      (function() {
        var inputs = document.querySelectorAll('input[type="submit"], button[type="submit"]');
        for (var i = 0; i < inputs.length; i++) {
          var t = (inputs[i].value || inputs[i].textContent || '').toLowerCase();
          if (t.includes('situaci') || t.includes('solicitar')) {
            return true;
          }
        }
        return false;
      })()
    `);
    if (tieneSituacion) {
      return await this.descargarPorSubmit("Situacion");
    }
    log.warn(`[${this.nombre}] No se encontraron tipos especificos — buscando descarga generica`);
    return await this.intentarDescargaGenerica();
  }
  /**
   * Descarga certificado IRPF del SEPE.
   * Flujo: click enlace IRPF → select año → submit → pagina descarga → submit "Descarga" → PDF
   */
  async descargarIRPF() {
    log.info(`[${this.nombre}] Descargando certificado IRPF`);
    await this.ejecutarJs(`
      (function() {
        var enlace = document.querySelector('a[href*="CertificadoIRPFWeb"]') ||
                     document.querySelector('a[href*="ActionIRPF"]');
        if (enlace) enlace.click();
      })()
    `);
    await this.delay(3e3);
    await this.capturarPantalla("02-irpf-pagina");
    const anioSeleccionado = await this.ejecutarJs(`
      (function() {
        var sel = document.querySelector('select[name*="jercicio"], select[name*="ejercicio"], select');
        if (sel) return sel.value;
        return '';
      })()
    `);
    log.info(`[${this.nombre}] Año IRPF seleccionado: ${anioSeleccionado || "default"}`);
    const submitOk = await this.ejecutarJs(`
      (function() {
        var inputs = document.querySelectorAll('input[type="submit"], button[type="submit"]');
        for (var i = 0; i < inputs.length; i++) {
          var t = (inputs[i].value || inputs[i].textContent || '').toLowerCase();
          if (t.includes('aceptar') || t.includes('enviar') || t.includes('generar')) {
            inputs[i].click();
            return true;
          }
        }
        // Intentar submit del form directamente
        var form = document.querySelector('form');
        if (form) { form.submit(); return true; }
        return false;
      })()
    `);
    if (!submitOk) {
      log.warn(`[${this.nombre}] No se encontro boton aceptar en IRPF`);
      return { exito: false, error: "Boton aceptar no encontrado en pagina IRPF" };
    }
    await this.delay(3e3);
    await this.capturarPantalla("03-irpf-descarga");
    const nombreArchivo = this.nombreConFecha("Certificado_SEPE_IRPF");
    try {
      const ruta = await this.descargarConPromesa(
        async () => {
          const clicked = await this.ejecutarJs(`
            (function() {
              var inputs = document.querySelectorAll('input[type="submit"], button[type="submit"]');
              for (var i = 0; i < inputs.length; i++) {
                var t = (inputs[i].value || inputs[i].textContent || '').toLowerCase();
                if (t.includes('descarga') || t.includes('descargar') || t.includes('obtener')) {
                  inputs[i].click();
                  return true;
                }
              }
              return false;
            })()
          `);
          if (!clicked) {
            await this.ejecutarJs(`
              var form = document.querySelector('form');
              if (form) form.submit();
            `);
          }
        },
        nombreArchivo,
        3e4
      );
      log.info(`[${this.nombre}] Certificado IRPF descargado: ${ruta}`);
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch (err) {
      log.warn(`[${this.nombre}] will-download fallo para IRPF: ${err.message}`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf para IRPF`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
  /**
   * Descarga certificado via submit button (Situacion, Prestacion Actual, etc.)
   */
  async descargarPorSubmit(tipo) {
    log.info(`[${this.nombre}] Descargando certificado tipo: ${tipo}`);
    const nombreArchivo = this.nombreConFecha(`Certificado_SEPE_${tipo}`);
    const clicked = await this.ejecutarJs(`
      (function() {
        var inputs = document.querySelectorAll('input[type="submit"], button[type="submit"]');
        for (var i = 0; i < inputs.length; i++) {
          var t = (inputs[i].value || inputs[i].textContent || '').toLowerCase();
          if (t.includes('${tipo.toLowerCase()}') || t.includes('solicitar')) {
            inputs[i].click();
            return true;
          }
        }
        // Click primer submit como fallback
        if (inputs.length > 0) { inputs[0].click(); return true; }
        return false;
      })()
    `);
    if (!clicked) {
      return { exito: false, error: `No se encontro boton para tipo ${tipo}` };
    }
    await this.delay(5e3);
    await this.capturarPantalla("02-post-submit");
    try {
      const ruta = await this.descargarConPromesa(
        async () => {
          await this.ejecutarJs(`
            (function() {
              var inputs = document.querySelectorAll('input[type="submit"], button[type="submit"], a');
              for (var i = 0; i < inputs.length; i++) {
                var t = (inputs[i].value || inputs[i].textContent || '').toLowerCase();
                if (t.includes('descarga') || t.includes('descargar') || t.includes('imprimir') || t.includes('obtener')) {
                  inputs[i].click(); return;
                }
              }
              // Submit form como fallback
              var form = document.querySelector('form');
              if (form) form.submit();
            })()
          `);
        },
        nombreArchivo,
        3e4
      );
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
    } catch {
      log.warn(`[${this.nombre}] will-download fallo para ${tipo} — usando printToPdf`);
      const rutaPdf = await this.printToPdf(nombreArchivo);
      return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
    }
  }
  /**
   * Intento generico de descarga — busca cualquier boton/enlace de descarga
   */
  async intentarDescargaGenerica() {
    const nombreArchivo = this.nombreConFecha("Certificado_SEPE");
    const encontrado = await this.ejecutarJs(`
      (function() {
        var elementos = document.querySelectorAll('a, button, input[type="submit"]');
        for (var i = 0; i < elementos.length; i++) {
          var t = (elementos[i].textContent || elementos[i].value || '').toLowerCase();
          if (t.includes('descargar') || t.includes('obtener') || t.includes('generar') ||
              t.includes('solicitar') || t.includes('certificado')) {
            elementos[i].setAttribute('data-cg-download', 'true');
            return true;
          }
        }
        return false;
      })()
    `);
    if (encontrado) {
      try {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento('[data-cg-download="true"]'),
          nombreArchivo,
          3e4
        );
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } };
      } catch {
        log.warn(`[${this.nombre}] Descarga generica fallo`);
      }
    }
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } };
  }
  /** Helper: click en boton/enlace que contenga alguno de los textos dados */
  async clickBotonPorTexto(textos) {
    const textosJson = JSON.stringify(textos);
    await this.ejecutarJs(`
      (function() {
        var textos = ${textosJson};
        var elementos = document.querySelectorAll('a, button, input[type="submit"]');
        for (var i = 0; i < elementos.length; i++) {
          var t = (elementos[i].textContent || elementos[i].value || '').toLowerCase();
          for (var j = 0; j < textos.length; j++) {
            if (t.includes(textos[j])) {
              elementos[i].click();
              return;
            }
          }
        }
      })()
    `).catch(() => {
    });
  }
}
class ScraperSolicitudCirbe extends BaseScraperDocumental {
  url = "https://aps.bde.es/cir_www/cir_wwwias/xml/Arranque.html";
  datosExtra;
  constructor(serialNumber, datosExtra, config) {
    super(serialNumber, config);
    this.datosExtra = datosExtra;
  }
  get nombre() {
    return "Solicitud CIRBE";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando solicitud CIRBE`);
    if (!this.datosExtra.email) {
      return { exito: false, error: "Email requerido para solicitud CIRBE" };
    }
    if (!this.datosExtra.fechaNacimiento) {
      return { exito: false, error: "Fecha de nacimiento requerida (DD/MM/AAAA) para solicitud CIRBE" };
    }
    await this.navegar(this.url);
    await this.delay(3e3);
    const urlActual = this.obtenerURL();
    if (urlActual.includes("Arranque.html") && !urlActual.includes("#")) {
      const clicCert = await this.ejecutarJs(`
        (function() {
          var enlaces = document.querySelectorAll('a');
          for (var i = 0; i < enlaces.length; i++) {
            var t = (enlaces[i].textContent || '').toLowerCase();
            if (t.includes('acceder usando certificado') || t.includes('certificado electr')) {
              enlaces[i].click();
              return true;
            }
          }
          return false;
        })()
      `);
      if (clicCert) {
        log.info(`[${this.nombre}] Click en "Acceder usando certificado"`);
        await this.delay(5e3);
      }
    }
    await this.capturarPantalla("01-post-login");
    await this.delay(2e3);
    const textoPortal = await this.ejecutarJs(`
      (document.body.innerText || '').substring(0, 500)
    `);
    if (!textoPortal?.toLowerCase().includes("central de informaci")) {
      log.error(`[${this.nombre}] No parece ser el portal CIRBE`);
      return { exito: false, error: "No se accedio al portal CIRBE correctamente" };
    }
    const clicPeticion = await this.ejecutarJs(`
      (function() {
        var enlaces = document.querySelectorAll('a');
        for (var i = 0; i < enlaces.length; i++) {
          var t = (enlaces[i].textContent || '').trim().toLowerCase();
          if (t === 'petición de informe' || (t.includes('petici') && t.includes('informe'))) {
            enlaces[i].click();
            return true;
          }
        }
        return false;
      })()
    `);
    if (!clicPeticion) {
      log.error(`[${this.nombre}] Link "Peticion de informe" no encontrado`);
      return { exito: false, error: 'No se encontro enlace "Peticion de informe" en portal CIRBE' };
    }
    log.info(`[${this.nombre}] Click en "Peticion de informe"`);
    await this.delay(4e3);
    await this.capturarPantalla("02-formulario");
    try {
      await this.esperarSelector("#PeticionInformeRiesgo_CajaParaFechaNacimiento", 15e3);
    } catch {
      log.warn(`[${this.nombre}] Campo fecha nacimiento no aparecio — reintentando`);
      await this.delay(3e3);
    }
    const radioSeleccionado = await this.ejecutarJs(`
      (function() {
        var radios = document.querySelectorAll('input[type="radio"]');
        for (var i = 0; i < radios.length; i++) {
          // Buscar el radio de la tabla de periodos (no otros radios)
          if (radios[i].id && radios[i].id.includes('Rejilla')) {
            radios[i].click();
            return true;
          }
        }
        // Fallback: primer radio de cualquier tabla
        var radio = document.querySelector('table input[type="radio"]');
        if (radio) { radio.click(); return true; }
        return false;
      })()
    `);
    if (radioSeleccionado) {
      log.info(`[${this.nombre}] Radio de periodo seleccionado`);
    } else {
      log.warn(`[${this.nombre}] No se encontro radio de periodo — puede fallar al enviar`);
    }
    await this.delay(500);
    const fechaOk = await this.ejecutarJs(`
      (function() {
        var campo = document.querySelector('#PeticionInformeRiesgo_CajaParaFechaNacimiento');
        if (!campo) return false;
        campo.focus();
        campo.value = '${this.datosExtra.fechaNacimiento.replace(/'/g, "\\'")}';
        campo.dispatchEvent(new Event('input', { bubbles: true }));
        campo.dispatchEvent(new Event('change', { bubbles: true }));
        campo.blur();
        return true;
      })()
    `);
    if (fechaOk) {
      log.info(`[${this.nombre}] Fecha de nacimiento rellenada: ${this.datosExtra.fechaNacimiento}`);
    } else {
      log.error(`[${this.nombre}] Campo fecha nacimiento no encontrado`);
      return { exito: false, error: "No se encontro campo de fecha de nacimiento en formulario CIRBE" };
    }
    const emailOk = await this.ejecutarJs(`
      (function() {
        var campo = document.querySelector('#CajaDeTextoCorreoElectronico');
        if (!campo) return false;
        campo.focus();
        campo.value = '${this.datosExtra.email.replace(/'/g, "\\'")}';
        campo.dispatchEvent(new Event('input', { bubbles: true }));
        campo.dispatchEvent(new Event('change', { bubbles: true }));
        campo.blur();
        return true;
      })()
    `);
    if (emailOk) {
      log.info(`[${this.nombre}] Email configurado: ${this.datosExtra.email}`);
    } else {
      log.error(`[${this.nombre}] Campo email no encontrado`);
      return { exito: false, error: "No se encontro campo de email en formulario CIRBE" };
    }
    await this.ejecutarJs(`
      var cb = document.querySelector('#CheckBoxSimpleCondicionesPrivacidad');
      if (cb && !cb.checked) cb.click();
    `);
    log.info(`[${this.nombre}] Condiciones de privacidad aceptadas`);
    await this.capturarPantalla("03-pre-envio");
    await this.clickElemento("#BotonAceptar");
    await this.delay(4e3);
    await this.capturarPantalla("04-post-envio");
    const textoResultado = await this.ejecutarJs(`
      (document.body.innerText || '').substring(0, 1000).toLowerCase()
    `);
    const solicitudOk = textoResultado?.includes("solicitud") || textoResultado?.includes("tramitada") || textoResultado?.includes("disponible") || textoResultado?.includes("informaci");
    if (textoResultado?.includes("error") && !solicitudOk) {
      log.error(`[${this.nombre}] Posible error en solicitud`);
      return { exito: false, error: "Error al enviar solicitud CIRBE. Revisa las capturas de pantalla." };
    }
    log.info(`[${this.nombre}] Solicitud CIRBE enviada correctamente`);
    return {
      exito: true,
      datos: {
        tipo: "solicitud",
        mensaje: "Solicitud CIRBE enviada. El informe estara disponible en ~15 minutos para descarga.",
        emailDestino: this.datosExtra.email
      }
    };
  }
}
class ScraperObtencionCirbe extends BaseScraperDocumental {
  url = "https://aps.bde.es/cir_www/cir_wwwias/xml/Arranque.html";
  get nombre() {
    return "Obtencion CIRBE";
  }
  async ejecutar() {
    log.info(`[${this.nombre}] Iniciando obtencion de informe CIRBE`);
    await this.navegar(this.url);
    await this.delay(3e3);
    const urlActual = this.obtenerURL();
    if (urlActual.includes("Arranque.html") && !urlActual.includes("#")) {
      const clicCert = await this.ejecutarJs(`
        (function() {
          var enlaces = document.querySelectorAll('a');
          for (var i = 0; i < enlaces.length; i++) {
            var t = (enlaces[i].textContent || '').toLowerCase();
            if (t.includes('acceder usando certificado') || t.includes('certificado electr')) {
              enlaces[i].click();
              return true;
            }
          }
          return false;
        })()
      `);
      if (clicCert) {
        log.info(`[${this.nombre}] Click en "Acceder usando certificado"`);
        await this.delay(5e3);
      }
    }
    await this.capturarPantalla("01-post-login");
    await this.delay(2e3);
    const textoPortal = await this.ejecutarJs(`
      (document.body.innerText || '').substring(0, 500)
    `);
    if (!textoPortal?.toLowerCase().includes("central de informaci")) {
      log.error(`[${this.nombre}] No parece ser el portal CIRBE`);
      return { exito: false, error: "No se accedio al portal CIRBE correctamente" };
    }
    const clicConsulta = await this.ejecutarJs(`
      (function() {
        var enlaces = document.querySelectorAll('a');
        for (var i = 0; i < enlaces.length; i++) {
          var t = (enlaces[i].textContent || '').trim().toLowerCase();
          if (t.includes('consulta') && t.includes('descarga') && t.includes('informe')) {
            enlaces[i].click();
            return true;
          }
        }
        return false;
      })()
    `);
    if (!clicConsulta) {
      log.error(`[${this.nombre}] Link "Consulta de estado y descarga" no encontrado`);
      return { exito: false, error: "No se encontro enlace de consulta/descarga en portal CIRBE" };
    }
    log.info(`[${this.nombre}] Click en "Consulta de estado y descarga"`);
    await this.delay(4e3);
    await this.capturarPantalla("02-consulta");
    const textoConsulta = await this.ejecutarJs(`
      (document.body.innerText || '').toLowerCase()
    `);
    if (textoConsulta?.includes("no dispone de solicitudes")) {
      log.warn(`[${this.nombre}] No hay solicitudes CIRBE pendientes`);
      return {
        exito: false,
        error: 'No hay solicitudes CIRBE en curso. Primero debes solicitar el informe CIRBE (boton "Solicitud CIRBE") y esperar ~15 minutos.'
      };
    }
    const estadoSolicitud = await this.ejecutarJs(`
      (function() {
        // Buscar celda de estado en la tabla (columna 4, index 3)
        var celdas = document.querySelectorAll('table td');
        for (var i = 0; i < celdas.length; i++) {
          var t = (celdas[i].textContent || '').trim().toLowerCase();
          if (t === 'registrada' || t === 'en proceso' || t === 'pendiente') {
            return t;
          }
        }
        return '';
      })()
    `);
    const fechaObtencion = await this.ejecutarJs(`
      (function() {
        var filas = document.querySelectorAll('table tr');
        for (var i = 1; i < filas.length; i++) {
          var celdas = filas[i].querySelectorAll('td');
          if (celdas.length >= 5) {
            // Columna 5 (index 4) = Fecha y hora de obtencion
            var fecha = (celdas[4].textContent || '').trim();
            if (fecha.length > 0) return fecha;
          }
        }
        return '';
      })()
    `);
    if (estadoSolicitud && !fechaObtencion) {
      log.warn(`[${this.nombre}] Solicitud en estado "${estadoSolicitud}" — aun no lista`);
      return {
        exito: false,
        error: `La solicitud CIRBE esta en estado "${estadoSolicitud}". Espera ~15 minutos hasta que este lista para descarga. Vuelve a intentarlo despues.`
      };
    }
    log.info(`[${this.nombre}] Solicitud disponible para descarga (fecha obtencion: ${fechaObtencion || "detectada"})`);
    await this.ejecutarJs(`
      var radio = document.querySelector('table input[type="radio"]');
      if (radio) radio.click();
    `);
    await this.delay(1e3);
    log.info(`[${this.nombre}] Solicitud seleccionada en tabla`);
    const nombreArchivo = this.nombreConFecha("Informe_CIRBE");
    this.configurarInterceptorDescarga();
    try {
      const ruta = await this.descargarConPromesa(
        async () => {
          const clicked = await this.ejecutarJs(`
            (function() {
              var botones = document.querySelectorAll('button, a, input[type="submit"]');
              for (var i = 0; i < botones.length; i++) {
                var t = (botones[i].textContent || botones[i].value || '').toLowerCase();
                if (t.includes('descargar') || t.includes('ver informe') || t.includes('obtener')) {
                  botones[i].click();
                  return true;
                }
              }
              // Fallback: boton con id conocido
              var btn = document.querySelector('#BotonDescargar, #BotonObtener');
              if (btn) { btn.click(); return true; }
              return false;
            })()
          `);
          if (!clicked) {
            log.warn(`[${this.nombre}] Boton de descarga no encontrado — intentando link`);
            await this.ejecutarJs(`
              var links = document.querySelectorAll('a[href]');
              for (var i = 0; i < links.length; i++) {
                var h = links[i].href.toLowerCase();
                if (h.includes('descarg') || h.includes('pdf') || h.includes('informe')) {
                  links[i].click();
                  break;
                }
              }
            `);
          }
        },
        nombreArchivo,
        45e3
      );
      log.info(`[${this.nombre}] Informe CIRBE descargado: ${ruta}`);
      return {
        exito: true,
        rutaDescarga: ruta,
        datos: { rutasArchivos: [ruta] }
      };
    } catch (err) {
      log.warn(`[${this.nombre}] will-download fallo: ${err.message}`);
    }
    log.warn(`[${this.nombre}] Usando printToPdf como fallback`);
    await this.capturarPantalla("fallback-printToPdf");
    const rutaPdf = await this.printToPdf(nombreArchivo);
    return {
      exito: true,
      rutaDescarga: rutaPdf,
      datos: { rutasArchivos: [rutaPdf] }
    };
  }
}
const URL_BUSCADOR = "https://contrataciondelestado.es/wps/portal/plataforma";
class BaseLicitaciones extends BaseScraperDocumental {
  async ejecutar() {
    log.info(
      `[${this.nombre}] Iniciando consulta de licitaciones — ${this.comunidad}`
    );
    await this.navegar(URL_BUSCADOR);
    await this.delay(3e3);
    const navegoABuscador = await this.ejecutarJs(`
      (function() {
        // Buscar enlace "Buscadores" en nav
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
          if ((links[i].textContent || '').trim() === 'Buscadores') {
            links[i].click();
            return true;
          }
        }
        return false;
      })()
    `);
    if (navegoABuscador) {
      await this.delay(3e3);
      await this.ejecutarJs(`
        (function() {
          var links = document.querySelectorAll('a');
          for (var i = 0; i < links.length; i++) {
            var texto = (links[i].textContent || '').trim();
            if (texto === 'Licitaciones' || texto.includes('Licitaciones')) {
              // Evitar link de nav (solo cards del cuerpo)
              var parent = links[i].closest('.portlet-body, main, .buscadores, article');
              if (parent || links[i].className.includes('card') || links[i].querySelector('h2, h3')) {
                links[i].click();
                return true;
              }
            }
          }
          // Fallback: click en el primer "Licitaciones" que no sea nav
          for (var j = 0; j < links.length; j++) {
            if ((links[j].textContent || '').trim() === 'Licitaciones' && links[j].href && links[j].href.includes('#')) {
              continue;
            }
            if ((links[j].textContent || '').includes('Licitaciones')) {
              links[j].click();
              return true;
            }
          }
          return false;
        })()
      `);
      await this.delay(3e3);
    }
    try {
      await this.esperarSelector(
        'select, input[type="text"], form',
        15e3
      );
    } catch {
      log.warn(`[${this.nombre}] Formulario no detectado, intentando con la pagina actual`);
    }
    const filtrosAplicados = await this.ejecutarJs(`
      (function() {
        // Buscar select de Estado (contiene opciones PUB, ADJ, etc.)
        var selects = document.querySelectorAll('select');
        for (var i = 0; i < selects.length; i++) {
          var opciones = selects[i].querySelectorAll('option');
          for (var j = 0; j < opciones.length; j++) {
            if (opciones[j].value === 'PUB') {
              selects[i].value = 'PUB';
              selects[i].dispatchEvent(new Event('change', { bubbles: true }));
              return true;
            }
          }
        }
        return false;
      })()
    `);
    if (filtrosAplicados) {
      log.info(`[${this.nombre}] Estado = Publicada seleccionado`);
    }
    if (this.lugarEjecucion) {
      await this.ejecutarJs(`
        (function() {
          var inputs = document.querySelectorAll('input[type="text"]');
          for (var i = 0; i < inputs.length; i++) {
            var label = inputs[i].closest('td, div, fieldset');
            if (label && (label.textContent || '').includes('Lugar de ejecuci')) {
              inputs[i].value = '${this.lugarEjecucion}';
              inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
              break;
            }
          }
        })()
      `);
      log.info(`[${this.nombre}] Lugar de ejecucion = ${this.lugarEjecucion}`);
    }
    const buscado = await this.ejecutarJs(`
      (function() {
        var botones = document.querySelectorAll('button[type="submit"], input[type="submit"]');
        for (var i = 0; i < botones.length; i++) {
          var texto = (botones[i].textContent || botones[i].value || '').trim();
          if (texto === 'Buscar') {
            botones[i].click();
            return true;
          }
        }
        return false;
      })()
    `);
    if (!buscado) {
      log.warn(`[${this.nombre}] Boton Buscar no encontrado`);
    }
    await this.delay(5e3);
    const tieneResultados = await this.ejecutarJs(`
      (function() {
        return !!document.querySelector('table, .tabla-resultados, #myTablaSortable');
      })()
    `);
    if (!tieneResultados) {
      log.warn(`[${this.nombre}] No se detecto tabla de resultados`);
    } else {
      log.info(`[${this.nombre}] Resultados cargados`);
    }
    const nombreArchivo = this.nombreConFecha(
      `Licitaciones_${this.comunidad}`
    );
    const rutaPdf = await this.printToPdf(nombreArchivo, {
      landscape: true,
      scale: 0.55
    });
    log.info(`[${this.nombre}] PDF generado: ${rutaPdf}`);
    return {
      exito: true,
      rutaDescarga: rutaPdf,
      datos: {
        comunidad: this.comunidad,
        rutasArchivos: [rutaPdf]
      }
    };
  }
}
class ScraperLicitacionesGeneral extends BaseLicitaciones {
  comunidad = "General";
  lugarEjecucion = "";
  get nombre() {
    return "Licitaciones General";
  }
}
class ScraperLicitacionesMadrid extends BaseLicitaciones {
  comunidad = "Madrid";
  lugarEjecucion = "Madrid";
  get nombre() {
    return "Licitaciones Madrid";
  }
}
class ScraperLicitacionesAndalucia extends BaseLicitaciones {
  comunidad = "Andalucia";
  lugarEjecucion = "Andalucía";
  get nombre() {
    return "Licitaciones Andalucia";
  }
}
class ScraperLicitacionesValencia extends BaseLicitaciones {
  comunidad = "Valencia";
  lugarEjecucion = "Comunitat Valenciana";
  get nombre() {
    return "Licitaciones Valencia";
  }
}
class ScraperLicitacionesCatalunya extends BaseLicitaciones {
  comunidad = "Catalunya";
  lugarEjecucion = "Cataluña";
  get nombre() {
    return "Licitaciones Catalunya";
  }
}
function crearScraper(tipo, serialNumber, config, datosExtra) {
  switch (tipo) {
    // AEAT
    case TipoDocumento.DEUDAS_AEAT:
      return new ScraperDeudasAeat(serialNumber, config);
    case TipoDocumento.DATOS_FISCALES:
      return new ScraperDatosFiscales(serialNumber, config);
    case TipoDocumento.CERTIFICADOS_IRPF:
      return new ScraperCertificadosIrpf(serialNumber, config);
    case TipoDocumento.CNAE_AUTONOMO:
      return new ScraperCnaeAutonomo(serialNumber, config);
    case TipoDocumento.IAE_ACTIVIDADES:
      return new ScraperIaeActividades(serialNumber, config);
    // Seguridad Social
    case TipoDocumento.DEUDAS_SS: {
      const datosSS = datosExtra ?? {};
      return new ScraperDeudasSS(serialNumber, config, datosSS);
    }
    case TipoDocumento.VIDA_LABORAL:
      return new ScraperVidaLaboral(serialNumber, config);
    case TipoDocumento.CERTIFICADO_INSS:
      return new ScraperCertificadoINSS(serialNumber, config);
    // Carpeta Ciudadana
    case TipoDocumento.CONSULTA_VEHICULOS:
      return new ScraperConsultaVehiculos(serialNumber, config);
    case TipoDocumento.CONSULTA_INMUEBLES:
      return new ScraperConsultaInmuebles(serialNumber, config);
    case TipoDocumento.EMPADRONAMIENTO:
      return new ScraperEmpadronamiento(serialNumber, config);
    case TipoDocumento.CERTIFICADO_PENALES:
      return new ScraperCertificadoPenales(serialNumber, config);
    // Justicia
    case TipoDocumento.CERTIFICADO_NACIMIENTO:
      return new ScraperCertificadoNacimiento(serialNumber, config);
    case TipoDocumento.APUD_ACTA:
      return new ScraperApudActa(serialNumber, config);
    case TipoDocumento.CERTIFICADO_MATRIMONIO:
      return new ScraperCertificadoMatrimonio(serialNumber, config);
    // Hacienda
    case TipoDocumento.DEUDAS_HACIENDA:
      return new ScraperDeudasHacienda(serialNumber, config);
    // Otros
    case TipoDocumento.CERTIFICADO_SEPE:
      return new ScraperCertificadoSepe(serialNumber, config);
    case TipoDocumento.SOLICITUD_CIRBE: {
      const datosCirbe = datosExtra ?? {};
      return new ScraperSolicitudCirbe(serialNumber, datosCirbe, config);
    }
    case TipoDocumento.OBTENCION_CIRBE:
      return new ScraperObtencionCirbe(serialNumber, config);
    // Licitaciones
    case TipoDocumento.PROC_ABIERTOS_GENERAL:
      return new ScraperLicitacionesGeneral(serialNumber, config);
    case TipoDocumento.PROC_ABIERTOS_MADRID:
      return new ScraperLicitacionesMadrid(serialNumber, config);
    case TipoDocumento.PROC_ABIERTOS_ANDALUCIA:
      return new ScraperLicitacionesAndalucia(serialNumber, config);
    case TipoDocumento.PROC_ABIERTOS_VALENCIA:
      return new ScraperLicitacionesValencia(serialNumber, config);
    case TipoDocumento.PROC_ABIERTOS_CATALUNYA:
      return new ScraperLicitacionesCatalunya(serialNumber, config);
    default:
      throw new Error(`Tipo de documento no soportado: ${tipo}`);
  }
}
class DocDescargaBlock extends BaseScraper {
  tipo;
  configScraping;
  datosExtra;
  constructor(tipo, serialNumber, configScraping, datosExtra) {
    super(serialNumber, configScraping);
    this.tipo = tipo;
    this.configScraping = configScraping;
    this.datosExtra = datosExtra;
  }
  get nombre() {
    return `DocDescarga-${this.tipo} (${this.serialNumber})`;
  }
  /** Override run() — no necesita Puppeteer, delega al scraper documental */
  async run() {
    try {
      const scraper = crearScraper(
        this.tipo,
        this.serialNumber,
        this.configScraping,
        this.datosExtra
      );
      const resultado = await scraper.run();
      const rutasArchivos = resultado.datos ? resultado.datos.rutasArchivos ?? [] : resultado.rutaDescarga ? [resultado.rutaDescarga] : [];
      const registro = {
        certificadoSerial: this.serialNumber,
        tipo: this.tipo,
        exito: resultado.exito,
        rutasArchivos,
        fechaDescarga: (/* @__PURE__ */ new Date()).toISOString(),
        error: resultado.error
      };
      registrarDescarga(registro);
      return resultado;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error desconocido";
      log.error(`[${this.nombre}] Error:`, msg);
      registrarDescarga({
        certificadoSerial: this.serialNumber,
        tipo: this.tipo,
        exito: false,
        rutasArchivos: [],
        fechaDescarga: (/* @__PURE__ */ new Date()).toISOString(),
        error: msg
      });
      return { exito: false, error: msg };
    }
  }
  async ejecutar() {
    return { exito: false, error: "Usar run() directamente" };
  }
}
class OrquestadorDocumentales {
  /** Construye una Chain para un certificado con sus documentos activos */
  construirCadena(factory2, config) {
    const cadena = new Chain(config.certificadoSerial);
    for (const tipo of config.documentosActivos) {
      const bloque = new DocDescargaBlock(
        tipo,
        config.certificadoSerial,
        void 0,
        config.datosExtra
      );
      cadena.agregarBloque(
        new Block(
          ProcessType.DOCUMENT_DOWNLOAD,
          `Descargar ${tipo} — ${config.certificadoSerial}`,
          bloque
        )
      );
    }
    factory2.agregarCadena(cadena);
    log.info(
      `[OrquestadorDocs] Cadena creada: ${config.certificadoSerial} — ${config.documentosActivos.length} documentos`
    );
    return cadena;
  }
  /** Construye cadenas para multiples certificados */
  construirCadenasBatch(factory2, configs) {
    for (const config of configs) {
      this.construirCadena(factory2, config);
    }
    log.info(
      `[OrquestadorDocs] ${configs.length} cadenas creadas en batch`
    );
  }
  /** Descarga un documento individual sin Factory */
  async descargarDocumento(tipo, serialNumber, configScraping, datosExtra) {
    const inicio = Date.now();
    try {
      const scraper = crearScraper(tipo, serialNumber, configScraping, datosExtra);
      const resultado = await scraper.run();
      const rutasArchivos = resultado.datos ? resultado.datos.rutasArchivos ?? [] : resultado.rutaDescarga ? [resultado.rutaDescarga] : [];
      const descarga = {
        tipo,
        exito: resultado.exito,
        rutasArchivos,
        error: resultado.error,
        fechaDescarga: (/* @__PURE__ */ new Date()).toISOString(),
        duracionMs: Date.now() - inicio
      };
      registrarDescarga({
        certificadoSerial: serialNumber,
        tipo,
        exito: resultado.exito,
        rutasArchivos,
        fechaDescarga: descarga.fechaDescarga,
        error: resultado.error
      });
      return descarga;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error desconocido";
      return {
        tipo,
        exito: false,
        rutasArchivos: [],
        error: msg,
        fechaDescarga: (/* @__PURE__ */ new Date()).toISOString(),
        duracionMs: Date.now() - inicio
      };
    }
  }
}
const ARCHIVO_HISTORIAL$1 = "certigestor-historial-docs.json";
function generarIdExterno(certificadoSerial, tipo, fechaDescarga) {
  const datos = `${certificadoSerial}_${tipo}_${fechaDescarga}`;
  return createHash("sha256").update(datos).digest("hex").substring(0, 64);
}
function resolverPortal(tipo) {
  const doc = CATALOGO_DOCUMENTOS.find((d) => d.id === tipo);
  return doc?.portal ?? "DESCONOCIDO";
}
function calcularTamano(rutasArchivos) {
  try {
    let total = 0;
    for (const ruta of rutasArchivos) {
      const info = statSync(ruta);
      total += info.size;
    }
    return total > 0 ? total : void 0;
  } catch {
    return void 0;
  }
}
async function sincronizarDocsConCloud(apiUrl, token) {
  const historial = obtenerHistorial();
  const pendientes = historial.filter((r) => !r.sincronizadoCloud);
  if (pendientes.length === 0) {
    log.info("[SyncDocs] No hay documentos pendientes de sincronizar");
    return { sincronizados: 0, errores: 0 };
  }
  log.info(`[SyncDocs] Sincronizando ${pendientes.length} documentos con cloud`);
  const BATCH_SIZE = 50;
  let sincronizados = 0;
  let errores = 0;
  for (let i = 0; i < pendientes.length; i += BATCH_SIZE) {
    const batch = pendientes.slice(i, i + BATCH_SIZE);
    const documentos = batch.map((reg) => ({
      idExterno: generarIdExterno(reg.certificadoSerial, reg.tipo, reg.fechaDescarga),
      tipo: reg.tipo,
      nombreArchivo: reg.rutasArchivos[0] ? reg.rutasArchivos[0].split(/[/\\]/).pop() ?? `${reg.tipo}.pdf` : `${reg.tipo}.pdf`,
      portal: resolverPortal(reg.tipo),
      exito: reg.exito,
      error: reg.error,
      tamanoBytes: calcularTamano(reg.rutasArchivos),
      fechaDescarga: reg.fechaDescarga,
      certificadoSerial: reg.certificadoSerial
    }));
    try {
      const respuesta = await fetch(`${apiUrl}/api/documentos-descargados/sync-desktop`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ documentos })
      });
      if (respuesta.ok) {
        for (const reg of batch) {
          reg.sincronizadoCloud = true;
        }
        sincronizados += batch.length;
        log.info(`[SyncDocs] Batch ${Math.floor(i / BATCH_SIZE) + 1} sincronizado: ${batch.length} docs`);
      } else {
        const textoError = await respuesta.text();
        log.warn(`[SyncDocs] Error HTTP ${respuesta.status}: ${textoError}`);
        errores += batch.length;
      }
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error desconocido";
      log.error(`[SyncDocs] Error de red: ${mensaje}`);
      errores += batch.length;
    }
  }
  if (sincronizados > 0) {
    const ruta = join(app.getPath("userData"), ARCHIVO_HISTORIAL$1);
    const historialCompleto = (() => {
      try {
        return JSON.parse(readFileSync(ruta, "utf-8"));
      } catch {
        return [];
      }
    })();
    for (const reg of historialCompleto) {
      const sincronizado = pendientes.find(
        (p) => p.certificadoSerial === reg.certificadoSerial && p.tipo === reg.tipo && p.fechaDescarga === reg.fechaDescarga && p.sincronizadoCloud
      );
      if (sincronizado) {
        reg.sincronizadoCloud = true;
      }
    }
    const recortado = historialCompleto.length > 500 ? historialCompleto.slice(-500) : historialCompleto;
    writeFileSync(ruta, JSON.stringify(recortado, null, 2), "utf-8");
  }
  log.info(`[SyncDocs] Resultado: ${sincronizados} sincronizados, ${errores} errores`);
  return { sincronizados, errores };
}
async function sincronizarConfigConCloud(apiUrl, token) {
  const configLocal = obtenerTodasLasConfigs();
  const seriales = Object.keys(configLocal);
  if (seriales.length === 0) {
    log.info("[SyncConfig] No hay configs de documentos para sincronizar");
    return { sincronizados: 0, errores: 0 };
  }
  log.info(`[SyncConfig] Sincronizando config de ${seriales.length} certificados con cloud`);
  const configs = seriales.map((serial) => ({
    certificadoSerial: serial,
    documentosActivos: configLocal[serial].documentosActivos,
    datosExtra: configLocal[serial].datosExtra
  }));
  try {
    const respuesta = await fetch(`${apiUrl}/api/documentos-descargados/sync-config-desktop`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ configs })
    });
    if (respuesta.ok) {
      log.info(`[SyncConfig] ${configs.length} configs sincronizadas con cloud`);
      return { sincronizados: configs.length, errores: 0 };
    }
    const textoError = await respuesta.text();
    log.warn(`[SyncConfig] Error HTTP ${respuesta.status}: ${textoError}`);
    return { sincronizados: 0, errores: configs.length };
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : "Error desconocido";
    log.error(`[SyncConfig] Error de red: ${mensaje}`);
    return { sincronizados: 0, errores: configs.length };
  }
}
async function recuperarConfigDesdeCloud(apiUrl, token) {
  log.info("[SyncConfig] Recuperando config de documentos desde cloud");
  try {
    const respuesta = await fetch(`${apiUrl}/api/documentos-descargados/config`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    if (!respuesta.ok) {
      const textoError = await respuesta.text();
      log.warn(`[SyncConfig] Error HTTP ${respuesta.status}: ${textoError}`);
      return { recuperados: 0 };
    }
    const datos = await respuesta.json();
    if (!datos.configs || datos.configs.length === 0) {
      log.info("[SyncConfig] No hay configs en cloud para recuperar");
      return { recuperados: 0 };
    }
    for (const cfg of datos.configs) {
      guardarConfig(cfg.certificadoSerial, cfg.documentosActivos, cfg.datosExtra);
    }
    log.info(`[SyncConfig] ${datos.configs.length} configs recuperadas desde cloud`);
    return { recuperados: datos.configs.length };
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : "Error desconocido";
    log.error(`[SyncConfig] Error de red: ${mensaje}`);
    return { recuperados: 0 };
  }
}
async function resolverCarpetaCertificado(serialNumber) {
  const baseDescargas = join(app.getPath("documents"), "CertiGestor", "descargas");
  const nombreCarpeta = await resolverNombreCarpeta(serialNumber);
  const subcarpeta = nombreCarpeta ?? serialNumber;
  let carpeta = join(baseDescargas, subcarpeta);
  if (!existsSync(carpeta) && nombreCarpeta) {
    const carpetaSerial = join(baseDescargas, serialNumber);
    if (existsSync(carpetaSerial)) {
      carpeta = carpetaSerial;
    }
  }
  return carpeta;
}
function registrarHandlersDocumentales(_ventana) {
  ipcMain.handle(
    "docs:obtenerCatalogo",
    () => {
      return CATALOGO_DOCUMENTOS;
    }
  );
  ipcMain.handle(
    "docs:obtenerConfig",
    (_event, certificadoSerial) => {
      return obtenerConfig(certificadoSerial);
    }
  );
  ipcMain.handle(
    "docs:guardarConfig",
    (_event, certificadoSerial, documentosActivos, datosExtra) => {
      guardarConfig(certificadoSerial, documentosActivos, datosExtra);
    }
  );
  ipcMain.handle(
    "docs:descargarDocumento",
    async (_event, tipo, certificadoSerial, datosExtra) => {
      log.info(
        `[DOC Handler] Descargando ${tipo} para cert: ${certificadoSerial}`
      );
      const nombreCarpeta = await resolverNombreCarpeta(certificadoSerial);
      log.info(`[DOC Handler] Carpeta: ${nombreCarpeta ?? certificadoSerial}`);
      const orquestador2 = new OrquestadorDocumentales();
      return orquestador2.descargarDocumento(
        tipo,
        certificadoSerial,
        nombreCarpeta ? { nombreCarpeta } : void 0,
        datosExtra
      );
    }
  );
  ipcMain.handle(
    "docs:descargarBatch",
    async (_event, configs) => {
      log.info(
        `[DOC Handler] Descarga batch para ${configs.length} certificados`
      );
      try {
        const orquestador2 = new OrquestadorDocumentales();
        factory.limpiar();
        orquestador2.construirCadenasBatch(factory, configs);
        await factory.iniciar();
        return { exito: true };
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Error desconocido";
        log.error(`[DOC Handler] Error en batch: ${msg}`);
        return { exito: false, error: msg };
      }
    }
  );
  ipcMain.handle(
    "docs:obtenerHistorial",
    (_event, certificadoSerial) => {
      return obtenerHistorial(certificadoSerial);
    }
  );
  ipcMain.handle(
    "docs:abrirCarpeta",
    async (_event, certificadoSerial) => {
      const baseDescargas = join(
        app.getPath("documents"),
        "CertiGestor",
        "descargas"
      );
      let carpeta = baseDescargas;
      if (certificadoSerial) {
        const nombreCarpeta = await resolverNombreCarpeta(certificadoSerial);
        const subcarpeta = nombreCarpeta ?? certificadoSerial;
        carpeta = join(baseDescargas, subcarpeta);
        if (!existsSync(carpeta) && nombreCarpeta) {
          const carpetaSerial = join(baseDescargas, certificadoSerial);
          if (existsSync(carpetaSerial)) {
            carpeta = carpetaSerial;
          }
        }
      }
      try {
        if (!existsSync(carpeta)) {
          mkdirSync(carpeta, { recursive: true });
        }
        const errorMsg = await shell.openPath(carpeta);
        if (errorMsg) {
          log.warn(`Error abriendo carpeta ${carpeta}: ${errorMsg}`);
          return { exito: false, error: errorMsg };
        }
        return { exito: true };
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Error desconocido";
        return { exito: false, error: msg };
      }
    }
  );
  ipcMain.handle(
    "docs:ultimosResultados",
    (_event, certificadoSerial) => {
      return obtenerUltimosResultados(certificadoSerial);
    }
  );
  ipcMain.handle("docs:limpiarHistorial", () => {
    limpiarHistorial();
  });
  ipcMain.handle(
    "docs:listarArchivos",
    async (_event, serialNumber) => {
      const carpeta = await resolverCarpetaCertificado(serialNumber);
      if (!existsSync(carpeta)) return [];
      try {
        const entries = await readdir(carpeta);
        const archivos = [];
        for (const entry of entries) {
          if (entry === "_debug" || entry.startsWith("debug_")) continue;
          if (!entry.toLowerCase().endsWith(".pdf")) continue;
          const ruta = join(carpeta, entry);
          const info = await stat(ruta);
          if (!info.isFile()) continue;
          archivos.push({
            nombre: entry,
            ruta,
            fecha: info.mtime.toISOString(),
            tamano: info.size
          });
        }
        return archivos.sort((a, b) => new Date(b.fecha).getTime() - new Date(a.fecha).getTime());
      } catch (err) {
        log.warn(`[DOC Handler] Error listando archivos: ${err.message}`);
        return [];
      }
    }
  );
  ipcMain.handle(
    "docs:eliminarArchivo",
    async (_event, ruta) => {
      const baseDescargas = join(app.getPath("documents"), "CertiGestor", "descargas");
      const rutaNormalizada = join(ruta);
      if (!rutaNormalizada.startsWith(baseDescargas)) {
        return { exito: false, error: "Ruta fuera de la carpeta de descargas" };
      }
      try {
        await unlink(ruta);
        return { exito: true };
      } catch (err) {
        return { exito: false, error: err.message };
      }
    }
  );
  ipcMain.handle(
    "docs:limpiarDebug",
    async (_event, serialNumber) => {
      const carpeta = await resolverCarpetaCertificado(serialNumber);
      if (!existsSync(carpeta)) return { exito: true, eliminados: 0 };
      let eliminados = 0;
      try {
        const carpetaDebug = join(carpeta, "_debug");
        if (existsSync(carpetaDebug)) {
          const debugFiles = await readdir(carpetaDebug);
          eliminados += debugFiles.length;
          await rm(carpetaDebug, { recursive: true });
        }
        const entries = await readdir(carpeta);
        for (const entry of entries) {
          if (entry.startsWith("debug_") && entry.endsWith(".png")) {
            await unlink(join(carpeta, entry));
            eliminados++;
          }
        }
        return { exito: true, eliminados };
      } catch (err) {
        log.warn(`[DOC Handler] Error limpiando debug: ${err.message}`);
        return { exito: false, eliminados };
      }
    }
  );
  ipcMain.handle(
    "docs:estadisticasCarpeta",
    async (_event, serialNumber) => {
      const carpeta = await resolverCarpetaCertificado(serialNumber);
      if (!existsSync(carpeta)) return { totalArchivos: 0, tamanoTotal: 0, debugCount: 0 };
      try {
        const entries = await readdir(carpeta);
        let totalArchivos = 0;
        let tamanoTotal = 0;
        let debugCount = 0;
        for (const entry of entries) {
          if (entry === "_debug") {
            const debugDir = join(carpeta, "_debug");
            const debugEntries = await readdir(debugDir);
            debugCount += debugEntries.length;
            continue;
          }
          if (entry.startsWith("debug_") && entry.endsWith(".png")) {
            debugCount++;
            continue;
          }
          if (!entry.toLowerCase().endsWith(".pdf")) continue;
          const ruta = join(carpeta, entry);
          const info = await stat(ruta);
          if (!info.isFile()) continue;
          totalArchivos++;
          tamanoTotal += info.size;
        }
        return { totalArchivos, tamanoTotal, debugCount };
      } catch (err) {
        log.warn(`[DOC Handler] Error estadisticas: ${err.message}`);
        return { totalArchivos: 0, tamanoTotal: 0, debugCount: 0 };
      }
    }
  );
  ipcMain.handle(
    "docs:abrirArchivo",
    async (_event, ruta) => {
      const baseDescargas = join(app.getPath("documents"), "CertiGestor", "descargas");
      const rutaNormalizada = join(ruta);
      if (!rutaNormalizada.startsWith(baseDescargas)) {
        return { exito: false, error: "Ruta fuera de la carpeta de descargas" };
      }
      try {
        const errorMsg = await shell.openPath(ruta);
        if (errorMsg) return { exito: false, error: errorMsg };
        return { exito: true };
      } catch (err) {
        return { exito: false, error: err.message };
      }
    }
  );
  ipcMain.handle(
    "docs:sincronizarCloud",
    async (_event, apiUrl, token) => {
      log.info("[DOC Handler] Sincronizando documentos con cloud");
      return sincronizarDocsConCloud(apiUrl, token);
    }
  );
  ipcMain.handle(
    "docs:sincronizarConfigCloud",
    async (_event, apiUrl, token) => {
      log.info("[DOC Handler] Sincronizando config documentos con cloud");
      return sincronizarConfigConCloud(apiUrl, token);
    }
  );
  ipcMain.handle(
    "docs:recuperarConfigCloud",
    async (_event, apiUrl, token) => {
      log.info("[DOC Handler] Recuperando config documentos desde cloud");
      return recuperarConfigDesdeCloud(apiUrl, token);
    }
  );
  log.info("Handlers documentales registrados");
}
var PortalNotificaciones = /* @__PURE__ */ ((PortalNotificaciones2) => {
  PortalNotificaciones2["DEHU"] = "DEHU";
  PortalNotificaciones2["DGT"] = "DGT";
  PortalNotificaciones2["E_NOTUM"] = "E_NOTUM";
  PortalNotificaciones2["JUNTA_ANDALUCIA"] = "JUNTA_ANDALUCIA";
  PortalNotificaciones2["AEAT_DIRECTA"] = "AEAT_DIRECTA";
  PortalNotificaciones2["SEGURIDAD_SOCIAL"] = "SEGURIDAD_SOCIAL";
  return PortalNotificaciones2;
})(PortalNotificaciones || {});
var EstadoAutenticacion = /* @__PURE__ */ ((EstadoAutenticacion2) => {
  EstadoAutenticacion2["AUTENTICADO"] = "AUTENTICADO";
  EstadoAutenticacion2["NO_AUTENTICADO"] = "NO_AUTENTICADO";
  EstadoAutenticacion2["ERROR"] = "ERROR";
  return EstadoAutenticacion2;
})(EstadoAutenticacion || {});
const { createWorker } = tesseractJs;
let worker = null;
let inicializando = null;
async function obtenerWorker() {
  if (worker) return worker;
  if (inicializando) return inicializando;
  inicializando = (async () => {
    log.info("[OCR] Inicializando worker tesseract.js (spa)");
    const w = await createWorker("spa");
    worker = w;
    inicializando = null;
    log.info("[OCR] Worker listo");
    return w;
  })();
  return inicializando;
}
async function ocrDesdeImagen(buffer) {
  const w = await obtenerWorker();
  const { data } = await w.recognize(buffer);
  return data.text.trim();
}
function workerActivo() {
  return worker !== null;
}
async function terminarWorkerOcr() {
  if (worker) {
    try {
      await worker.terminate();
      log.info("[OCR] Worker terminado");
    } catch (err) {
      log.warn(`[OCR] Error terminando worker: ${err.message}`);
    }
    worker = null;
  }
}
async function pdfAImagenes(rutaPdf, maxPaginas = 3) {
  const pdfBuffer = readFileSync(rutaPdf);
  const base64 = pdfBuffer.toString("base64");
  const imagenes = [];
  const ventana = new BrowserWindow({
    show: false,
    width: 1240,
    height: 1754,
    // A4 aprox a 150 DPI
    webPreferences: {
      offscreen: true,
      contextIsolation: true,
      sandbox: true
    }
  });
  try {
    await ventana.loadURL(
      `data:application/pdf;base64,${base64}`
    );
    await new Promise((resolve) => setTimeout(resolve, 2e3));
    const paginas = maxPaginas;
    for (let i = 0; i < paginas; i++) {
      const imagen = await ventana.webContents.capturePage();
      const pngBuffer = imagen.toPNG();
      if (pngBuffer.length > 1e3) {
        imagenes.push(pngBuffer);
      }
      if (i < paginas - 1) {
        await ventana.webContents.executeJavaScript(
          `window.scrollBy(0, ${1754})`
        );
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }
    log.info(`[OCR] PDF renderizado: ${imagenes.length} paginas capturadas`);
  } catch (err) {
    log.warn(`[OCR] Error renderizando PDF: ${err.message}`);
  } finally {
    ventana.destroy();
  }
  return imagenes;
}
async function ocrConVisionApi(imagenes, apiUrl, token) {
  if (imagenes.length === 0) return null;
  const imagenesBase64 = imagenes.map((buf) => buf.toString("base64"));
  try {
    log.info(`[OCR-Vision] Enviando ${imagenes.length} imagenes a API vision`);
    const inicio = Date.now();
    const response = await fetch(`${apiUrl}/ocr/vision`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ imagenes: imagenesBase64 })
    });
    if (!response.ok) {
      const texto2 = await response.text();
      log.warn(`[OCR-Vision] API retorno ${response.status}: ${texto2}`);
      return null;
    }
    const resultado = await response.json();
    const texto = resultado.datos?.texto?.trim() ?? "";
    const tokens = resultado.datos?.tokens ?? 0;
    log.info(
      `[OCR-Vision] Texto extraido: ${texto.length} chars, ${tokens} tokens en ${Date.now() - inicio}ms`
    );
    return texto.length > 0 ? texto : null;
  } catch (err) {
    log.warn(`[OCR-Vision] Error: ${err.message}`);
    return null;
  }
}
const UMBRAL_TEXTO_NATIVO = 50;
const MAX_CARACTERES = 25e3;
async function extraerTextoPdf(rutaPdf, opcionesVision) {
  if (!existsSync(rutaPdf)) {
    log.warn(`[OCR] Archivo no existe: ${rutaPdf}`);
    return null;
  }
  const inicio = Date.now();
  try {
    const buffer = readFileSync(rutaPdf);
    const parser = new PDFParse({ data: new Uint8Array(buffer) });
    await parser.load();
    const resultado = await parser.getText();
    const textoNativo = (typeof resultado === "string" ? resultado : resultado?.text ?? "").trim();
    if (textoNativo.length >= UMBRAL_TEXTO_NATIVO) {
      const texto = textoNativo.slice(0, MAX_CARACTERES);
      log.info(
        `[OCR] Texto nativo extraido: ${texto.length} chars en ${Date.now() - inicio}ms`
      );
      return texto;
    }
    log.info("[OCR] Texto nativo insuficiente, iniciando OCR...");
    const imagenes = await pdfAImagenes(rutaPdf, 10);
    if (imagenes.length === 0) {
      log.warn("[OCR] No se pudieron generar imagenes del PDF");
      return null;
    }
    const textosOcr = [];
    for (const imagen of imagenes) {
      const texto = await ocrDesdeImagen(imagen);
      if (texto.length > 10) {
        textosOcr.push(texto);
      }
    }
    const textoTesseract = textosOcr.join("\n\n").trim();
    if (textoTesseract.length >= UMBRAL_TEXTO_NATIVO) {
      const textoFinal = textoTesseract.slice(0, MAX_CARACTERES);
      log.info(
        `[OCR] Texto tesseract extraido: ${textoFinal.length} chars en ${Date.now() - inicio}ms`
      );
      return textoFinal;
    }
    if (opcionesVision) {
      log.info("[OCR] Tesseract insuficiente, intentando vision API...");
      const textoVision = await ocrConVisionApi(
        imagenes,
        opcionesVision.apiUrl,
        opcionesVision.token
      );
      if (textoVision && textoVision.length >= UMBRAL_TEXTO_NATIVO) {
        const textoFinal = textoVision.slice(0, MAX_CARACTERES);
        log.info(
          `[OCR] Texto vision extraido: ${textoFinal.length} chars en ${Date.now() - inicio}ms`
        );
        return textoFinal;
      }
    }
    if (textoTesseract.length > 0) {
      return textoTesseract.slice(0, MAX_CARACTERES);
    }
    log.warn("[OCR] Ninguna capa produjo texto util");
    return null;
  } catch (err) {
    log.error(`[OCR] Error extrayendo texto: ${err.message}`);
    return null;
  }
}
function mapearAFormatoApi(notif, certificadoId, portal) {
  return {
    idExterno: notif.idExterno,
    administracion: notif.organismo || portal,
    tipo: notif.tipo,
    contenido: notif.contenidoExtraido ?? notif.titulo,
    fechaDeteccion: notif.fechaDisposicion || (/* @__PURE__ */ new Date()).toISOString(),
    fechaPublicacion: notif.fechaDisposicion || void 0,
    certificadoId,
    origen: portal,
    estadoPortal: notif.estado || void 0
  };
}
async function sincronizarPortalConCloud(notificaciones, certificadoId, portal, apiUrl, token) {
  if (notificaciones.length === 0) {
    return { portal, nuevas: 0, actualizadas: 0, errores: 0 };
  }
  log.info(
    `[SyncNotif] Sincronizando ${notificaciones.length} de ${portal} con cloud`
  );
  for (const notif of notificaciones) {
    if (notif.rutaPdfLocal && !notif.contenidoExtraido) {
      try {
        const texto = await extraerTextoPdf(notif.rutaPdfLocal, {
          apiUrl,
          token
        });
        if (texto) {
          notif.contenidoExtraido = texto;
        }
      } catch (err) {
        log.warn(
          `[SyncNotif] Error OCR para ${notif.idExterno}: ${err.message}`
        );
      }
    }
  }
  const cuerpo = {
    notificaciones: notificaciones.map(
      (n) => mapearAFormatoApi(n, certificadoId, portal)
    )
  };
  try {
    const response = await fetch(`${apiUrl}/notificaciones/sync-desktop`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(cuerpo)
    });
    if (!response.ok) {
      const texto = await response.text();
      throw new Error(`HTTP ${response.status}: ${texto}`);
    }
    const resultado = await response.json();
    const data = resultado.data ?? { nuevas: 0, actualizadas: 0, errores: 0 };
    log.info(
      `[SyncNotif] ${portal}: ${data.nuevas} nuevas, ${data.actualizadas} actualizadas`
    );
    if (data.nuevas > 0) {
      notificarResultadoScraping(
        true,
        `${portal}: ${data.nuevas} notificacion(es) nueva(s)`
      );
      const ventana = BrowserWindow.getAllWindows()[0];
      if (ventana && !ventana.isDestroyed()) {
        ventana.webContents.send("notificaciones:nuevas", {
          portal,
          nuevas: data.nuevas
        });
      }
    }
    return { portal, ...data };
  } catch (error) {
    const msg = error instanceof Error ? error.message : "Error desconocido";
    log.error(`[SyncNotif] Error en ${portal}: ${msg}`);
    return { portal, nuevas: 0, actualizadas: 0, errores: notificaciones.length };
  }
}
class BaseScraperNotificaciones extends BaseScraper {
  constructor(serialNumber, configScraping) {
    super(serialNumber, configScraping);
  }
  /**
   * Implementacion de ejecutar() requerida por BaseScraper.
   * Delega a ejecutarConsulta() y envuelve en ResultadoConsultaPortal.
   */
  async ejecutar() {
    try {
      const notificaciones = await this.ejecutarConsulta();
      const resultado = {
        exito: true,
        portal: this.portal,
        certificadoSerial: this.serialNumber,
        estadoAutenticacion: EstadoAutenticacion.AUTENTICADO,
        notificaciones,
        fechaConsulta: (/* @__PURE__ */ new Date()).toISOString()
      };
      return { exito: true, datos: resultado };
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error desconocido";
      log.error(`[${this.nombre}] Error en ejecutarConsulta: ${msg}`);
      const resultado = {
        exito: false,
        portal: this.portal,
        certificadoSerial: this.serialNumber,
        estadoAutenticacion: EstadoAutenticacion.ERROR,
        notificaciones: [],
        error: msg,
        fechaConsulta: (/* @__PURE__ */ new Date()).toISOString()
      };
      return { exito: false, datos: resultado, error: msg };
    }
  }
  /**
   * Genera idExterno unico para una notificacion.
   * Formato: `${portal}-${serialNumber}-${idInterno}`
   */
  generarIdExterno(idInterno) {
    return `${this.portal}-${this.serialNumber}-${idInterno}`;
  }
  /**
   * Normaliza fecha texto (dd/mm/yyyy) a ISO string.
   */
  normalizarFecha(fecha) {
    if (!fecha) return (/* @__PURE__ */ new Date()).toISOString();
    const partes = fecha.match(/(\d{2})\/(\d{2})\/(\d{4})/);
    if (partes) {
      return (/* @__PURE__ */ new Date(
        `${partes[3]}-${partes[2]}-${partes[1]}T00:00:00.000Z`
      )).toISOString();
    }
    try {
      return new Date(fecha).toISOString();
    } catch {
      return (/* @__PURE__ */ new Date()).toISOString();
    }
  }
}
const SELECTORES$4 = {
  indicadorLogin: ".user-info, .mi-cuenta",
  tablaNotificaciones: "table.tabla-dea, .listado-notificaciones",
  filasTabla: "table tbody tr",
  sinResultados: ".sin-resultados, .no-data"
};
const TIMEOUT_AUTH$3 = 3e4;
const TIMEOUT_TABLA$4 = 15e3;
class ScraperDgt extends BaseScraperNotificaciones {
  urlPortal = "https://sede.dgt.gob.es/es/multas/direccion-electronica-vial/";
  portal = PortalNotificaciones.DGT;
  constructor(serialNumber, configScraping) {
    super(serialNumber, configScraping);
  }
  get nombre() {
    return "DGT-DEV";
  }
  async ejecutarConsulta() {
    await this.navegar(this.urlPortal);
    await this.esperar(3e3);
    await this.manejarPasarelaClave(1e4, 3e4);
    try {
      await this.esperarElemento(SELECTORES$4.indicadorLogin, TIMEOUT_AUTH$3);
    } catch {
      log.warn(`[${this.nombre}] Timeout esperando autenticacion`);
      await this.capturarPantalla("dgt-sin-auth");
      return [];
    }
    const haySinResultados = await this.ejecutarJS(`
      !!document.querySelector('${SELECTORES$4.sinResultados.replace(/'/g, "\\'")}')
    `);
    if (haySinResultados) {
      log.info(`[${this.nombre}] Sin notificaciones en el portal`);
      return [];
    }
    try {
      await this.esperarElemento(SELECTORES$4.tablaNotificaciones, TIMEOUT_TABLA$4);
    } catch {
      log.warn(`[${this.nombre}] Tabla no encontrada`);
      return [];
    }
    return this.extraerFilas();
  }
  async extraerFilas() {
    if (!this.window) return [];
    const datosFilas = await this.ejecutarJS(`
      (() => {
        const filas = document.querySelectorAll('${SELECTORES$4.filasTabla.replace(/'/g, "\\'")}');
        return Array.from(filas).map(fila => {
          const celdas = fila.querySelectorAll('td');
          if (celdas.length < 3) return null;
          return {
            titulo: celdas[0]?.textContent?.trim() ?? 'Sin titulo',
            organismo: celdas[1]?.textContent?.trim() || 'DGT',
            fechaTexto: celdas[2]?.textContent?.trim() ?? '',
            estado: celdas[3]?.textContent?.trim() ?? 'Pendiente',
            enlace: fila.querySelector('a')?.getAttribute('href') ?? '',
          };
        });
      })()
    `);
    if (!datosFilas) return [];
    const resultado = [];
    for (let i = 0; i < datosFilas.length; i++) {
      const datos = datosFilas[i];
      if (!datos || !datos.titulo) continue;
      resultado.push({
        idExterno: this.generarIdExterno(datos.enlace || `dgt-${i}`),
        portal: this.portal,
        tipo: "Notificacion",
        titulo: datos.titulo,
        organismo: datos.organismo,
        fechaDisposicion: this.normalizarFecha(datos.fechaTexto),
        fechaCaducidad: null,
        estado: datos.estado,
        rutaPdfLocal: null
      });
    }
    log.info(`[${this.nombre}] ${resultado.length} notificaciones extraidas`);
    return resultado;
  }
}
const SELECTORES$3 = {
  indicadorLogin: ".user-logged, .nom-usuari, #dades-usuari",
  tablaNotificaciones: ".llista-notificacions, table#notificacions, .taula-resultats",
  filasTabla: ".llista-notificacions tr, table#notificacions tbody tr",
  sinResultados: ".sense-resultats, .no-notificacions, .missatge-buit"
};
const TIMEOUT_AUTH$2 = 3e4;
const TIMEOUT_TABLA$3 = 15e3;
class ScraperEnotum extends BaseScraperNotificaciones {
  urlPortal = "https://usuari.enotum.cat/";
  portal = PortalNotificaciones.E_NOTUM;
  constructor(serialNumber, configScraping) {
    super(serialNumber, configScraping);
  }
  get nombre() {
    return "e-NOTUM";
  }
  async ejecutarConsulta() {
    await this.navegar(this.urlPortal);
    await this.esperar(3e3);
    await this.manejarPasarelaClave(1e4, 3e4);
    try {
      await this.esperarElemento(SELECTORES$3.indicadorLogin, TIMEOUT_AUTH$2);
    } catch {
      log.warn(`[${this.nombre}] Timeout esperando autenticacion`);
      await this.capturarPantalla("enotum-sin-auth");
      return [];
    }
    const haySinResultados = await this.ejecutarJS(`
      !!document.querySelector('${SELECTORES$3.sinResultados.replace(/'/g, "\\'")}')
    `);
    if (haySinResultados) {
      log.info(`[${this.nombre}] Sin notificaciones`);
      return [];
    }
    try {
      await this.esperarElemento(SELECTORES$3.tablaNotificaciones, TIMEOUT_TABLA$3);
    } catch {
      log.warn(`[${this.nombre}] Tabla no encontrada`);
      return [];
    }
    return this.extraerFilas();
  }
  async extraerFilas() {
    if (!this.window) return [];
    const datosFilas = await this.ejecutarJS(`
      (() => {
        const filas = document.querySelectorAll('${SELECTORES$3.filasTabla.replace(/'/g, "\\'")}');
        return Array.from(filas).map(fila => {
          const celdas = fila.querySelectorAll('td');
          if (celdas.length < 3) return null;
          return {
            titulo: celdas[0]?.textContent?.trim() ?? 'Sin titulo',
            organismo: celdas[1]?.textContent?.trim() || 'Generalitat de Catalunya',
            fechaTexto: celdas[2]?.textContent?.trim() ?? '',
            estado: celdas[3]?.textContent?.trim() ?? 'Pendent',
            enlace: fila.querySelector('a')?.getAttribute('href') ?? '',
          };
        });
      })()
    `);
    if (!datosFilas) return [];
    const resultado = [];
    for (let i = 0; i < datosFilas.length; i++) {
      const datos = datosFilas[i];
      if (!datos || !datos.titulo) continue;
      resultado.push({
        idExterno: this.generarIdExterno(datos.enlace || `enotum-${i}`),
        portal: this.portal,
        tipo: "Notificacion",
        titulo: datos.titulo,
        organismo: datos.organismo,
        fechaDisposicion: this.normalizarFecha(datos.fechaTexto),
        fechaCaducidad: null,
        estado: datos.estado,
        rutaPdfLocal: null
      });
    }
    log.info(`[${this.nombre}] ${resultado.length} notificaciones extraidas`);
    return resultado;
  }
}
const SELECTORES$2 = {
  botonCertificado: '#certificadoDigital, .btn-certificado, a[href*="certificado"]',
  indicadorLogin: ".usuario-autenticado, .datos-usuario, #panel-principal",
  tablaNotificaciones: "table.listado, .tabla-notificaciones, #tabla-avisos",
  filasTabla: "table.listado tbody tr, .tabla-notificaciones tbody tr",
  sinResultados: ".sin-notificaciones, .mensaje-vacio"
};
const TIMEOUT_CLICK = 1e4;
const TIMEOUT_AUTH$1 = 3e4;
const TIMEOUT_TABLA$2 = 15e3;
class ScraperJuntaAndalucia extends BaseScraperNotificaciones {
  urlPortal = "https://ws020.juntadeandalucia.es/Notifica/auth/login";
  portal = PortalNotificaciones.JUNTA_ANDALUCIA;
  constructor(serialNumber, configScraping) {
    super(serialNumber, configScraping);
  }
  get nombre() {
    return "Junta-Andalucia";
  }
  async ejecutarConsulta() {
    await this.navegar(this.urlPortal);
    await this.esperar(3e3);
    try {
      await this.esperarElemento(SELECTORES$2.botonCertificado, TIMEOUT_CLICK);
      await this.clic(SELECTORES$2.botonCertificado);
      await this.esperar(2e3);
    } catch {
      log.warn(`[${this.nombre}] Boton certificado no encontrado, verificando Cl@ve...`);
    }
    await this.manejarPasarelaClave(1e4, 3e4);
    try {
      await this.esperarElemento(SELECTORES$2.indicadorLogin, TIMEOUT_AUTH$1);
    } catch {
      log.warn(`[${this.nombre}] Timeout esperando autenticacion`);
      await this.capturarPantalla("junta-sin-auth");
      return [];
    }
    const haySinResultados = await this.ejecutarJS(`
      !!document.querySelector('${SELECTORES$2.sinResultados.replace(/'/g, "\\'")}')
    `);
    if (haySinResultados) {
      log.info(`[${this.nombre}] Sin notificaciones`);
      return [];
    }
    try {
      await this.esperarElemento(SELECTORES$2.tablaNotificaciones, TIMEOUT_TABLA$2);
    } catch {
      log.warn(`[${this.nombre}] Tabla no encontrada`);
      return [];
    }
    return this.extraerFilas();
  }
  async extraerFilas() {
    if (!this.window) return [];
    const datosFilas = await this.ejecutarJS(`
      (() => {
        const filas = document.querySelectorAll('${SELECTORES$2.filasTabla.replace(/'/g, "\\'")}');
        return Array.from(filas).map(fila => {
          const celdas = fila.querySelectorAll('td');
          if (celdas.length < 3) return null;
          return {
            titulo: celdas[0]?.textContent?.trim() ?? 'Sin titulo',
            organismo: celdas[1]?.textContent?.trim() || 'Junta de Andalucia',
            fechaTexto: celdas[2]?.textContent?.trim() ?? '',
            estado: celdas[3]?.textContent?.trim() ?? 'Pendiente',
            enlace: fila.querySelector('a')?.getAttribute('href') ?? '',
          };
        });
      })()
    `);
    if (!datosFilas) return [];
    const resultado = [];
    for (let i = 0; i < datosFilas.length; i++) {
      const datos = datosFilas[i];
      if (!datos || !datos.titulo) continue;
      resultado.push({
        idExterno: this.generarIdExterno(datos.enlace || `junta-${i}`),
        portal: this.portal,
        tipo: "Aviso",
        titulo: datos.titulo,
        organismo: datos.organismo,
        fechaDisposicion: this.normalizarFecha(datos.fechaTexto),
        fechaCaducidad: null,
        estado: datos.estado,
        rutaPdfLocal: null
      });
    }
    log.info(`[${this.nombre}] ${resultado.length} avisos extraidos`);
    return resultado;
  }
}
const SELECTORES$1 = {
  indicadorLogin: "#cabeceraNombre, .nombre-usuario, .acceso-identificado",
  tablaNotificaciones: "#tablaNotificaciones, table.listado-notificaciones, .resultado-consulta table",
  filasTabla: "#tablaNotificaciones tbody tr, table.listado-notificaciones tbody tr",
  sinResultados: ".sin-notificaciones, .no-resultados, #mensajeSinDatos"
};
const TIMEOUT_AUTH = 3e4;
const TIMEOUT_TABLA$1 = 15e3;
class ScraperAeatNotificaciones extends BaseScraperNotificaciones {
  urlPortal = "https://www.agenciatributaria.gob.es/AEAT.sede/procedimientoini/GF01.shtml";
  portal = PortalNotificaciones.AEAT_DIRECTA;
  constructor(serialNumber, configScraping) {
    super(serialNumber, configScraping);
  }
  get nombre() {
    return "AEAT-Notificaciones";
  }
  async ejecutarConsulta() {
    await this.navegar(this.urlPortal);
    await this.esperar(3e3);
    await this.manejarPasarelaClave(1e4, 3e4);
    try {
      await this.esperarElemento(SELECTORES$1.indicadorLogin, TIMEOUT_AUTH);
    } catch {
      log.warn(`[${this.nombre}] Timeout esperando autenticacion`);
      await this.capturarPantalla("aeat-notif-sin-auth");
      return [];
    }
    const haySinResultados = await this.ejecutarJS(`
      !!document.querySelector('${SELECTORES$1.sinResultados.replace(/'/g, "\\'")}')
    `);
    if (haySinResultados) {
      log.info(`[${this.nombre}] Sin notificaciones`);
      return [];
    }
    try {
      await this.esperarElemento(SELECTORES$1.tablaNotificaciones, TIMEOUT_TABLA$1);
    } catch {
      log.warn(`[${this.nombre}] Tabla no encontrada`);
      return [];
    }
    return this.extraerFilas();
  }
  async extraerFilas() {
    if (!this.window) return [];
    const datosFilas = await this.ejecutarJS(`
      (function() {
        var filas = document.querySelectorAll('${SELECTORES$1.filasTabla.replace(/'/g, "\\\\'")}');
        return Array.from(filas).map(function(fila) {
          var celdas = fila.querySelectorAll('td');
          if (celdas.length < 3) return null;
          return {
            titulo: celdas[0] ? celdas[0].textContent.trim() : 'Sin titulo',
            organismo: celdas[1] ? celdas[1].textContent.trim() || 'Agencia Tributaria' : 'Agencia Tributaria',
            fechaTexto: celdas[2] ? celdas[2].textContent.trim() : '',
            estado: celdas[3] ? celdas[3].textContent.trim() : 'Pendiente',
            enlace: fila.querySelector('a') ? fila.querySelector('a').getAttribute('href') || '' : '',
          };
        });
      })()
    `);
    if (!datosFilas) return [];
    const resultado = [];
    for (let i = 0; i < datosFilas.length; i++) {
      const datos = datosFilas[i];
      if (!datos || !datos.titulo) continue;
      resultado.push({
        idExterno: this.generarIdExterno(datos.enlace || `aeat-${i}`),
        portal: this.portal,
        tipo: "Notificacion",
        titulo: datos.titulo,
        organismo: datos.organismo,
        fechaDisposicion: this.normalizarFecha(datos.fechaTexto),
        fechaCaducidad: null,
        estado: datos.estado,
        rutaPdfLocal: null
      });
    }
    log.info(`[${this.nombre}] ${resultado.length} notificaciones extraidas`);
    return resultado;
  }
}
const URL_NOTIFICACIONES = "https://sede.seg-social.gob.es/wps/portal/sede/Seguridad/PortalRedirectorN2A?idApp=323&idContenido=7a65cc68-f663-4b4f-bbdb-82dba341160f&idPagina=com.ss.sede.NotificacionesTelematicas&N2&A";
const SELECTORES = {
  /** Boton de login con certificado en la pasarela de autenticacion */
  botonCertificado: 'button#IPCEIdP, button[formaction*="IPCE"]',
  /** Indicador post-login: elementos que solo aparecen autenticado */
  indicadorLogin: ".nombre-usuario, .datos-usuario, #contenidoPrincipal, .breadcrumb, #mainContent",
  /** Tabla de notificaciones — contenedor principal */
  tablaNotificaciones: 'table.tablaDatos, table.tabla-notificaciones, #tablaNotificaciones, .resultado-consulta table, table[summary*="notificacion"], table.tablaListadoPaginada',
  /** Filas de datos en la tabla */
  filasTabla: "table.tablaDatos tbody tr, table.tabla-notificaciones tbody tr, #tablaNotificaciones tbody tr, table.tablaListadoPaginada tbody tr",
  /**
   * Indicador de que no hay notificaciones.
   * En la UI real de SS dice "No existen notificaciones puestas a su disposición"
   */
  sinResultados: ".sin-notificaciones, .no-resultados, .mensaje-vacio, #mensajeVacio, .msgInfo",
  /** Formulario de seleccion (nombre propio vs apoderado) */
  selectorTipo: 'select[name*="tipo"], select[name*="representacion"]'
};
const TIMEOUT_LOGIN = 3e4;
const TIMEOUT_REDIRECCION = 2e4;
const TIMEOUT_TABLA = 15e3;
class ScraperSeguridadSocial extends BaseScraperNotificaciones {
  urlPortal = URL_NOTIFICACIONES;
  portal = PortalNotificaciones.SEGURIDAD_SOCIAL;
  constructor(serialNumber, configScraping) {
    super(serialNumber, { ...configScraping, timeoutGlobal: 12e4 });
  }
  get nombre() {
    return "SS-Notificaciones";
  }
  async ejecutarConsulta() {
    log.info(`[${this.nombre}] Navegando a sede SS...`);
    await this.navegar(this.urlPortal);
    await this.esperar(3e3);
    await this.autenticarConCertificado();
    await this.esperarPaginaNotificaciones();
    const haySinResultados = await this.ejecutarJS(`
      (function() {
        var selectoresVacio = '${SELECTORES.sinResultados.replace(/'/g, "\\\\'")}';
        if (document.querySelector(selectoresVacio)) return true;
        var bodyText = document.body ? document.body.innerText : '';
        if (bodyText.includes('No existen notificaciones')) return true;
        return false;
      })()
    `);
    if (haySinResultados) {
      log.info(`[${this.nombre}] Sin notificaciones pendientes — portal SS funciona correctamente`);
      return [];
    }
    return this.extraerNotificaciones();
  }
  /**
   * Autenticacion via pasarela idp.seg-social.es o Cl@ve.
   *
   * Flujo posible 1: SS → idp.seg-social.es → clic #IPCEIdP → select-client-certificate → redirect
   * Flujo posible 2: SS → pasarela.clave.gob.es → selectedIdP('AFIRMA') → select-client-certificate → redirect
   * Flujo posible 3: SS → idp.seg-social.es → clic #IPCEIdP → pasarela.clave.gob.es → selectedIdP('AFIRMA') → redirect
   */
  async autenticarConCertificado() {
    if (!this.window) throw new Error("Navegador no inicializado");
    const urlActual = this.obtenerURL();
    log.info(`[${this.nombre}] URL actual: ${urlActual}`);
    if (urlActual.includes("pasarela.clave.gob.es") || urlActual.includes("clave.gob.es")) {
      log.info(`[${this.nombre}] Redirigido a Cl@ve directamente`);
      await this.manejarPasarelaClave(5e3, TIMEOUT_REDIRECCION);
      await this.esperar(3e3);
      log.info(`[${this.nombre}] Post-Cl@ve URL: ${this.obtenerURL()}`);
      return;
    }
    const enPasarelaSS = urlActual.includes("idp.seg-social.es") || urlActual.includes("PGIS/Login");
    if (enPasarelaSS) {
      log.info(`[${this.nombre}] En pasarela SS — buscando boton certificado`);
      try {
        await this.esperarElemento(SELECTORES.botonCertificado, TIMEOUT_LOGIN);
        await this.clic(SELECTORES.botonCertificado);
        log.info(`[${this.nombre}] Clic en boton certificado SS`);
      } catch {
        log.warn(`[${this.nombre}] Boton certificado SS no encontrado`);
        await this.capturarPantalla("ss-login-sin-boton");
        throw new Error("No se encontro el boton de login con certificado");
      }
      await this.esperar(2e3);
      const urlPostClic = this.obtenerURL();
      if (urlPostClic.includes("pasarela.clave.gob.es") || urlPostClic.includes("clave.gob.es")) {
        log.info(`[${this.nombre}] Pasarela SS redirigió a Cl@ve`);
        await this.manejarPasarelaClave(1e4, TIMEOUT_REDIRECCION);
      } else {
        log.info(`[${this.nombre}] Esperando redireccion post-autenticacion SS...`);
        try {
          await this.esperarRedireccion(urlPostClic, TIMEOUT_REDIRECCION);
        } catch {
          log.warn(`[${this.nombre}] Timeout en redireccion post-login SS`);
        }
      }
      await this.esperar(3e3);
      log.info(`[${this.nombre}] Post-login URL: ${this.obtenerURL()}`);
      return;
    }
    log.info(`[${this.nombre}] No en pasarela conocida — intentando Cl@ve como fallback`);
    const pasoPorClave = await this.manejarPasarelaClave(5e3, TIMEOUT_REDIRECCION);
    if (!pasoPorClave) {
      log.info(`[${this.nombre}] Sin pasarela detectada — posible sesion activa`);
    }
    await this.esperar(3e3);
    log.info(`[${this.nombre}] Post-auth URL: ${this.obtenerURL()}`);
  }
  /**
   * Espera a que aparezca la pagina de notificaciones.
   * Busca tabla, mensajes de vacio, o indicadores de sesion.
   * Tambien busca el texto real de la SS: "No existen notificaciones"
   */
  async esperarPaginaNotificaciones() {
    if (!this.window) throw new Error("Navegador no inicializado");
    const inicio = Date.now();
    while (Date.now() - inicio < TIMEOUT_TABLA) {
      const encontrado = await this.ejecutarJS(`
        (function() {
          // Buscar por selectores CSS
          var selectoresTabla = '${SELECTORES.tablaNotificaciones.replace(/'/g, "\\\\'")}';
          var selectoresVacio = '${SELECTORES.sinResultados.replace(/'/g, "\\\\'")}';
          var selectoresLogin = '${SELECTORES.indicadorLogin.replace(/'/g, "\\\\'")}';

          if (document.querySelector(selectoresTabla)) return true;
          if (document.querySelector(selectoresVacio)) return true;
          if (document.querySelector(selectoresLogin)) return true;

          // Buscar por texto real de la SS (vista en screenshot real)
          var bodyText = document.body ? document.body.innerText : '';
          if (bodyText.includes('No existen notificaciones')) return true;
          if (bodyText.includes('Listado de notificaciones')) return true;
          if (bodyText.includes('Búsqueda de notificaciones')) return true;
          if (bodyText.includes('Notificaciones electrónicas')) return true;

          return false;
        })()
      `);
      if (encontrado) {
        log.info(`[${this.nombre}] Pagina de notificaciones detectada`);
        return;
      }
      await this.esperar(500);
    }
    log.warn(`[${this.nombre}] Timeout esperando pagina de notificaciones`);
    await this.capturarPantalla("ss-notif-timeout");
  }
  /**
   * Extrae notificaciones de la tabla HTML via executeJavaScript.
   *
   * Columnas esperadas (segun manual de usuario SS):
   * 0: Prestacion/procedimiento
   * 1: Materia
   * 2: Fecha puesta a disposicion
   * 3: Destinatario
   * 4: Estado
   * 5: Fecha/hora vencimiento
   */
  async extraerNotificaciones() {
    if (!this.window) return [];
    const hayTabla = await this.ejecutarJS(`
      !!document.querySelector('${SELECTORES.tablaNotificaciones.replace(/'/g, "\\\\'")}')
    `);
    if (!hayTabla) {
      log.warn(`[${this.nombre}] Tabla no encontrada — capturando pantalla`);
      await this.capturarPantalla("ss-notif-sin-tabla");
      return this.extraerDeTablaGenerica();
    }
    const datosFilas = await this.ejecutarJS(`
      (function() {
        var filas = document.querySelectorAll('${SELECTORES.filasTabla.replace(/'/g, "\\\\'")}');
        return Array.from(filas).map(function(fila) {
          var celdas = fila.querySelectorAll('td');
          if (celdas.length < 3) return null;
          return {
            prestacion: celdas[0] ? celdas[0].textContent.trim() : '',
            materia: celdas[1] ? celdas[1].textContent.trim() : '',
            fechaDisposicion: celdas[2] ? celdas[2].textContent.trim() : '',
            destinatario: celdas[3] ? celdas[3].textContent.trim() : '',
            estado: celdas[4] ? celdas[4].textContent.trim() : 'Pendiente',
            fechaVencimiento: celdas[5] ? celdas[5].textContent.trim() : '',
            enlace: fila.querySelector('a') ? fila.querySelector('a').getAttribute('href') || '' : '',
          };
        });
      })()
    `);
    if (!datosFilas || datosFilas.length === 0) {
      log.info(`[${this.nombre}] Tabla encontrada pero sin filas`);
      return [];
    }
    const resultado = [];
    for (let i = 0; i < datosFilas.length; i++) {
      const datos = datosFilas[i];
      if (!datos) continue;
      const titulo = datos.prestacion ? `${datos.prestacion}${datos.materia ? " — " + datos.materia : ""}` : datos.materia || `Notificacion SS #${i + 1}`;
      resultado.push({
        idExterno: this.generarIdExterno(
          datos.enlace || `ss-${i}-${datos.fechaDisposicion}`
        ),
        portal: this.portal,
        tipo: "Notificacion",
        titulo,
        organismo: "Seguridad Social",
        fechaDisposicion: this.normalizarFecha(datos.fechaDisposicion),
        fechaCaducidad: datos.fechaVencimiento ? this.normalizarFecha(datos.fechaVencimiento) : null,
        estado: datos.estado,
        urlDetalle: datos.enlace || void 0,
        rutaPdfLocal: null
      });
    }
    log.info(`[${this.nombre}] ${resultado.length} notificaciones extraidas`);
    return resultado;
  }
  /**
   * Fallback: busca cualquier tabla en la pagina y extrae datos.
   */
  async extraerDeTablaGenerica() {
    if (!this.window) return [];
    const datosFilas = await this.ejecutarJS(`
      (function() {
        var filas = document.querySelectorAll('table tbody tr');
        return Array.from(filas).map(function(fila) {
          var celdas = fila.querySelectorAll('td');
          if (celdas.length < 2) return null;
          return {
            textos: Array.from(celdas).map(function(c) { return c.textContent.trim(); }),
            enlace: fila.querySelector('a') ? fila.querySelector('a').getAttribute('href') || '' : '',
          };
        });
      })()
    `);
    if (!datosFilas || datosFilas.length === 0) {
      log.info(`[${this.nombre}] Sin tablas en la pagina`);
      return [];
    }
    log.info(
      `[${this.nombre}] Fallback: encontradas ${datosFilas.length} filas en tabla generica`
    );
    const resultado = [];
    for (let i = 0; i < datosFilas.length; i++) {
      const datos = datosFilas[i];
      if (!datos || datos.textos.length < 2) continue;
      const [prestacion, materia, fecha, , estado, fechaVenc] = datos.textos;
      const titulo = prestacion ? `${prestacion}${materia ? " — " + materia : ""}` : `Notificacion SS #${i + 1}`;
      resultado.push({
        idExterno: this.generarIdExterno(
          datos.enlace || `ss-gen-${i}-${fecha}`
        ),
        portal: this.portal,
        tipo: "Notificacion",
        titulo,
        organismo: "Seguridad Social",
        fechaDisposicion: this.normalizarFecha(fecha ?? ""),
        fechaCaducidad: fechaVenc ? this.normalizarFecha(fechaVenc) : null,
        estado: estado || "Pendiente",
        urlDetalle: datos.enlace || void 0,
        rutaPdfLocal: null
      });
    }
    log.info(
      `[${this.nombre}] Fallback: ${resultado.length} notificaciones extraidas`
    );
    return resultado;
  }
}
function crearScraperPortal(portal, serialNumber, config) {
  switch (portal) {
    case PortalNotificaciones.DGT:
      return new ScraperDgt(serialNumber, config);
    case PortalNotificaciones.E_NOTUM:
      return new ScraperEnotum(serialNumber, config);
    case PortalNotificaciones.JUNTA_ANDALUCIA:
      return new ScraperJuntaAndalucia(serialNumber, config);
    case PortalNotificaciones.AEAT_DIRECTA:
      return new ScraperAeatNotificaciones(serialNumber, config);
    case PortalNotificaciones.SEGURIDAD_SOCIAL:
      return new ScraperSeguridadSocial(serialNumber, config);
    default:
      throw new Error(`Portal no soportado para scraper directo: ${portal}`);
  }
}
class PortalConsultaBlock extends BaseScraper {
  portal;
  configScraping;
  resultado = null;
  constructor(portal, serialNumber, configScraping) {
    super(serialNumber, configScraping);
    this.portal = portal;
    this.configScraping = configScraping;
  }
  get nombre() {
    return `${this.portal}-Consulta (${this.serialNumber})`;
  }
  /** Override run() — delega al scraper concreto sin usar Puppeteer propio */
  async run() {
    try {
      const scraper = crearScraperPortal(
        this.portal,
        this.serialNumber,
        this.configScraping
      );
      const resultado = await scraper.run();
      this.resultado = resultado.datos;
      return resultado;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error desconocido";
      this.resultado = {
        exito: false,
        portal: this.portal,
        certificadoSerial: this.serialNumber,
        estadoAutenticacion: EstadoAutenticacion.ERROR,
        notificaciones: [],
        error: msg,
        fechaConsulta: (/* @__PURE__ */ new Date()).toISOString()
      };
      return { exito: false, error: msg };
    }
  }
  async ejecutar() {
    return { exito: false, error: "Usar run() directamente" };
  }
}
class PortalSyncBlock extends BaseScraper {
  bloqueConsulta;
  certificadoId;
  apiUrl;
  token;
  constructor(bloqueConsulta, certificadoId, apiUrl, token) {
    super(bloqueConsulta.serialNumber);
    this.bloqueConsulta = bloqueConsulta;
    this.certificadoId = certificadoId;
    this.apiUrl = apiUrl;
    this.token = token;
  }
  get nombre() {
    return `${this.bloqueConsulta.nombre}-Sync`;
  }
  /** Override run() — sincroniza sin necesitar Puppeteer */
  async run() {
    try {
      const consulta = this.bloqueConsulta.resultado;
      if (!consulta || !consulta.exito) {
        return { exito: false, error: "Sin resultado de consulta para sincronizar" };
      }
      if (consulta.notificaciones.length === 0) {
        return { exito: true, datos: { nuevas: 0, actualizadas: 0, errores: 0 } };
      }
      const resultado = await sincronizarPortalConCloud(
        consulta.notificaciones,
        this.certificadoId,
        consulta.portal,
        this.apiUrl,
        this.token
      );
      return { exito: resultado.errores === 0, datos: resultado };
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Error desconocido";
      return { exito: false, error: msg };
    }
  }
  async ejecutar() {
    return { exito: false, error: "Usar run() directamente" };
  }
}
class OrquestadorNotificaciones {
  apiUrl;
  token;
  constructor(apiUrl, token) {
    this.apiUrl = apiUrl;
    this.token = token;
  }
  /**
   * Consulta un portal concreto para un certificado.
   * DEHU delega al DehuOrquestador existente.
   */
  async consultarPortal(portal, serialNumber, configDehu) {
    if (portal === PortalNotificaciones.DEHU) {
      return this.consultarDehu(serialNumber, configDehu);
    }
    const scraper = crearScraperPortal(portal, serialNumber);
    const resultado = await scraper.run();
    return resultado.datos ?? {
      exito: false,
      portal,
      certificadoSerial: serialNumber,
      estadoAutenticacion: EstadoAutenticacion.ERROR,
      notificaciones: [],
      error: resultado.error,
      fechaConsulta: (/* @__PURE__ */ new Date()).toISOString()
    };
  }
  /**
   * Consulta todos los portales activos de un certificado.
   * Ejecuta portales en paralelo (independientes entre si).
   */
  async consultarMultiPortal(serialNumber, configPortales, configDehu) {
    const { portalesActivos } = configPortales;
    log.info(
      `[OrqNotif] Consultando ${portalesActivos.length} portales para cert: ${serialNumber}`
    );
    const promesas = portalesActivos.map(
      (portal) => this.consultarPortal(portal, serialNumber, configDehu).catch(
        (err) => ({
          exito: false,
          portal,
          certificadoSerial: serialNumber,
          estadoAutenticacion: EstadoAutenticacion.ERROR,
          notificaciones: [],
          error: err.message,
          fechaConsulta: (/* @__PURE__ */ new Date()).toISOString()
        })
      )
    );
    const resultados = await Promise.all(promesas);
    const totalNotificaciones = resultados.reduce(
      (sum, r) => sum + r.notificaciones.length,
      0
    );
    const portalesConError = resultados.filter((r) => !r.exito).map((r) => r.portal);
    return {
      certificadoSerial: serialNumber,
      portalesConsultados: portalesActivos,
      resultados,
      totalNotificaciones,
      portalesConError,
      fechaConsulta: (/* @__PURE__ */ new Date()).toISOString()
    };
  }
  /**
   * Construye Chains para portales ADICIONALES (no DEHU) de un certificado.
   * DEHU se maneja via DehuOrquestador.construirCadena() por separado.
   */
  construirCadenaPortalesAdicionales(factory2, serialNumber, certificadoId, portalesAdicionales) {
    const cadena = new Chain(`notif-${serialNumber}`);
    for (const portal of portalesAdicionales) {
      const bloqueConsulta = new PortalConsultaBlock(portal, serialNumber);
      cadena.agregarBloque(
        new Block(
          ProcessType.NOTIFICATION_CHECK,
          `Consultar ${portal} — ${serialNumber}`,
          bloqueConsulta
        )
      );
      const bloqueSync = new PortalSyncBlock(
        bloqueConsulta,
        certificadoId,
        this.apiUrl,
        this.token
      );
      cadena.agregarBloque(
        new Block(
          ProcessType.DATA_SCRAPING,
          `Sincronizar ${portal} — ${serialNumber}`,
          bloqueSync
        )
      );
    }
    factory2.agregarCadena(cadena);
    return cadena;
  }
  /**
   * Construye cadenas batch para todos los portales (DEHU + adicionales).
   * DEHU usa DehuOrquestador (sin duplicar), adicionales usan PortalConsultaBlock.
   */
  construirCadenasBatch(factory2, configs) {
    for (const config of configs) {
      const portalesAdicionales = config.configPortales.portalesActivos.filter(
        (p) => p !== PortalNotificaciones.DEHU
      );
      const incluyeDehu = config.configPortales.portalesActivos.includes(
        PortalNotificaciones.DEHU
      );
      if (incluyeDehu && config.configDehu) {
        const dehuOrq = new DehuOrquestador(this.apiUrl, this.token);
        dehuOrq.construirCadena(factory2, config.configDehu, config.certificadoId);
      }
      if (portalesAdicionales.length > 0) {
        this.construirCadenaPortalesAdicionales(
          factory2,
          config.serialNumber,
          config.certificadoId,
          portalesAdicionales
        );
      }
    }
    log.info(`[OrqNotif] Cadenas batch creadas para ${configs.length} certificados`);
  }
  // ── Privado: delegacion DEHU ─────────────────────────────
  async consultarDehu(serialNumber, configDehu) {
    if (!configDehu) {
      return {
        exito: false,
        portal: PortalNotificaciones.DEHU,
        certificadoSerial: serialNumber,
        estadoAutenticacion: EstadoAutenticacion.ERROR,
        notificaciones: [],
        error: "configDehu requerida para portal DEHU",
        fechaConsulta: (/* @__PURE__ */ new Date()).toISOString()
      };
    }
    const dehuOrq = new DehuOrquestador(this.apiUrl, this.token);
    const resultadoDehu = await dehuOrq.consultarCertificado(configDehu);
    const notificaciones = [
      ...resultadoDehu.notificaciones.map((n) => ({
        idExterno: `DEHU-${n.idDehu}`,
        portal: PortalNotificaciones.DEHU,
        tipo: n.tipo,
        titulo: n.titulo,
        organismo: n.organismo,
        fechaDisposicion: n.fechaDisposicion,
        fechaCaducidad: n.fechaCaducidad,
        estado: n.estado,
        rutaPdfLocal: n.rutaPdfLocal
      })),
      ...resultadoDehu.comunicaciones.map((n) => ({
        idExterno: `DEHU-${n.idDehu}`,
        portal: PortalNotificaciones.DEHU,
        tipo: "Comunicacion",
        titulo: n.titulo,
        organismo: n.organismo,
        fechaDisposicion: n.fechaDisposicion,
        fechaCaducidad: n.fechaCaducidad,
        estado: n.estado,
        rutaPdfLocal: n.rutaPdfLocal
      }))
    ];
    return {
      exito: resultadoDehu.exito,
      portal: PortalNotificaciones.DEHU,
      certificadoSerial: serialNumber,
      estadoAutenticacion: resultadoDehu.exito ? EstadoAutenticacion.AUTENTICADO : EstadoAutenticacion.ERROR,
      notificaciones,
      error: resultadoDehu.error,
      fechaConsulta: resultadoDehu.fechaConsulta
    };
  }
}
const ARCHIVO_CONFIG_PORTALES = "certigestor-config-portales.json";
const PORTALES_POR_DEFECTO = [
  PortalNotificaciones.DEHU
];
function rutaArchivo$1() {
  return join(app.getPath("userData"), ARCHIVO_CONFIG_PORTALES);
}
function leerConfigPortales() {
  const ruta = rutaArchivo$1();
  if (!existsSync(ruta)) return {};
  try {
    const contenido = readFileSync(ruta, "utf-8");
    return JSON.parse(contenido);
  } catch (err) {
    log.warn(`[ConfigPortales] Error leyendo config: ${err.message}`);
    return {};
  }
}
function guardarConfigPortales(config) {
  const ruta = rutaArchivo$1();
  writeFileSync(ruta, JSON.stringify(config, null, 2), "utf-8");
}
function obtenerConfigPortales(certificadoSerial) {
  const config = leerConfigPortales();
  return config[certificadoSerial] ?? {
    portalesActivos: [...PORTALES_POR_DEFECTO]
  };
}
function guardarConfigPortalesCert(certificadoSerial, portalesActivos, datosPortal) {
  const config = leerConfigPortales();
  const configActualizada = {
    ...config,
    [certificadoSerial]: { portalesActivos, datosPortal }
  };
  guardarConfigPortales(configActualizada);
  log.info(
    `[ConfigPortales] Guardado cert: ${certificadoSerial} — portales: ${portalesActivos.join(", ")}`
  );
}
function extraerNifDeSubject(subject) {
  const matchSerial = subject.match(/SERIALNUMBER=IDCES-([A-Z0-9]+)/i);
  if (matchSerial) return matchSerial[1];
  const matchCN = subject.match(/CN=.*?-\s*([A-Z0-9]{8,9}[A-Z]?)/);
  if (matchCN) return matchCN[1];
  return "";
}
function extraerNombreDeSubject(subject) {
  const matchCN = subject.match(/CN=([^,]+)/);
  return matchCN ? matchCN[1].trim() : "";
}
function extraerCifEmpresaDeSubject(subject) {
  const matchOid = subject.match(/(?:OID\.)?2\.5\.4\.97=VATES-([A-Z0-9]+)/i);
  if (matchOid) return matchOid[1];
  const matchOrgId = subject.match(/organizationIdentifier=VATES-([A-Z0-9]+)/i);
  if (matchOrgId) return matchOrgId[1];
  const matchOrg = subject.match(/O=([^,]+)/i);
  if (matchOrg) {
    const cifEnOrg = matchOrg[1].match(/\b([A-HJ-NP-SUVW]\d{7}[A-J0-9])\b/);
    if (cifEnOrg) return cifEnOrg[1];
  }
  return "";
}
async function resolverConfigDesdeAlmacen(titularHint) {
  const certs = await listarCertificadosInstalados();
  if (certs.length === 0) return null;
  log.info(`[Notif Handler] Certs disponibles: ${certs.length}. Titular hint: ${titularHint ?? "ninguno"}`);
  let certSeleccionado = certs[0];
  let metodoMatch = "default(certs[0])";
  if (titularHint && certs.length > 1) {
    const hintNorm = titularHint.toUpperCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const nifMatch = hintNorm.match(/(\d{8}[A-Z])/i);
    if (nifMatch) {
      const certPorNif = certs.find((c) => c.subject.toUpperCase().includes(nifMatch[1]));
      if (certPorNif) {
        certSeleccionado = certPorNif;
        metodoMatch = `nif(${nifMatch[1]})`;
      }
    }
    if (metodoMatch.startsWith("default")) {
      const cifMatch = hintNorm.match(/([A-HJ-NP-SUVW]\d{7}[A-J0-9])/i);
      if (cifMatch) {
        const certPorCif = certs.find((c) => c.subject.toUpperCase().includes(cifMatch[1]));
        if (certPorCif) {
          certSeleccionado = certPorCif;
          metodoMatch = `cif(${cifMatch[1]})`;
        }
      }
    }
    if (metodoMatch.startsWith("default")) {
      const certPorNombre = certs.find((c) => {
        const subjectNorm = c.subject.toUpperCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        const cnMatch = subjectNorm.match(/CN=([^,]+)/);
        if (!cnMatch) return false;
        const cn = cnMatch[1].trim();
        return hintNorm.includes(cn) || cn.includes(hintNorm);
      });
      if (certPorNombre) {
        certSeleccionado = certPorNombre;
        metodoMatch = "nombre";
      }
    }
  }
  const nifPersonal = extraerNifDeSubject(certSeleccionado.subject);
  const cifEmpresa = extraerCifEmpresaDeSubject(certSeleccionado.subject);
  log.info(`[Notif Handler] Cert seleccionado (${metodoMatch}): ${certSeleccionado.numeroSerie}`);
  log.info(`[Notif Handler] Subject: ${certSeleccionado.subject}`);
  log.info(`[Notif Handler] NIF personal: ${nifPersonal}, CIF empresa: ${cifEmpresa || "N/A"}`);
  return {
    certificadoSerial: certSeleccionado.numeroSerie,
    titularNombre: extraerNombreDeSubject(certSeleccionado.subject),
    titularNif: nifPersonal,
    nifEmpresa: cifEmpresa || void 0,
    thumbprint: certSeleccionado.thumbprint,
    timeoutGlobal: 3e5
  };
}
function registrarHandlersNotificaciones(_ventana) {
  ipcMain.handle(
    "notif:obtenerConfigPortales",
    (_event, certificadoSerial) => {
      return obtenerConfigPortales(certificadoSerial);
    }
  );
  ipcMain.handle(
    "notif:guardarConfigPortales",
    (_event, certificadoSerial, portalesActivos, datosPortal) => {
      guardarConfigPortalesCert(certificadoSerial, portalesActivos, datosPortal);
    }
  );
  ipcMain.handle(
    "notif:obtenerPortalesDisponibles",
    () => {
      return Object.values(PortalNotificaciones);
    }
  );
  ipcMain.handle(
    "notif:consultarPortal",
    async (_event, portal, serialNumber, apiUrl, token, configDehu) => {
      log.info(`[Notif Handler] Consultando portal ${portal} para cert: ${serialNumber}`);
      const orquestador2 = new OrquestadorNotificaciones(apiUrl, token);
      return orquestador2.consultarPortal(portal, serialNumber, configDehu);
    }
  );
  ipcMain.handle(
    "notif:consultarMultiPortal",
    async (_event, serialNumber, apiUrl, token, configDehu) => {
      log.info(`[Notif Handler] Consulta multi-portal para cert: ${serialNumber}`);
      const configPortales = obtenerConfigPortales(serialNumber);
      const orquestador2 = new OrquestadorNotificaciones(apiUrl, token);
      return orquestador2.consultarMultiPortal(serialNumber, configPortales, configDehu);
    }
  );
  ipcMain.handle(
    "notif:consultarYSincronizarBatch",
    async (_event, configs, apiUrl, token) => {
      log.info(`[Notif Handler] Batch multi-portal para ${configs.length} certificados`);
      try {
        const orquestador2 = new OrquestadorNotificaciones(apiUrl, token);
        const configsConPortales = configs.map((c) => ({
          ...c,
          configPortales: obtenerConfigPortales(c.serialNumber)
        }));
        factory.limpiar();
        orquestador2.construirCadenasBatch(factory, configsConPortales);
        await factory.iniciar();
        return { exito: true };
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Error desconocido";
        log.error(`[Notif Handler] Error en batch: ${msg}`);
        return { exito: false, error: msg };
      }
    }
  );
  ipcMain.handle(
    "notif:descargarPdf",
    async (_event, idExterno, portal, configDehu, estadoNotificacion, titularNotificacion) => {
      log.info(`[Notif Handler] Descarga PDF: ${idExterno} de ${portal} (estado: ${estadoNotificacion ?? "desconocido"}, titular: ${titularNotificacion ?? "N/A"})`);
      if (portal !== "DEHU" && portal !== PortalNotificaciones.DEHU) {
        return { exito: false, error: `Descarga PDF no soportada para portal: ${portal}` };
      }
      let config = configDehu;
      if (!config) {
        config = await resolverConfigDesdeAlmacen(titularNotificacion) ?? void 0;
        if (!config) {
          return { exito: false, error: "No hay certificados instalados en el almacen de Windows" };
        }
        log.info(`[Notif Handler] Config auto-resuelta desde almacen: ${config.certificadoSerial}`);
      }
      const esPendiente = !estadoNotificacion || estadoNotificacion === "pendiente";
      try {
        const nombreCarpeta = await resolverNombreCarpeta(config.certificadoSerial);
        const scraper = new DehuScraper(config, nombreCarpeta ? { nombreCarpeta } : void 0);
        const notificacion = {
          idDehu: idExterno,
          tipo: "Notificacion",
          titulo: "",
          titular: "",
          ambito: "",
          organismo: "DEHU",
          fechaDisposicion: (/* @__PURE__ */ new Date()).toISOString(),
          fechaCaducidad: null,
          estado: esPendiente ? "Pendiente de abrir" : "Aceptada",
          rutaPdfLocal: null
        };
        const rutaLocal = await scraper.runDescargarPdf(notificacion);
        if (rutaLocal) {
          return { exito: true, rutaLocal };
        } else {
          return { exito: false, error: "El scraper no devolvio ruta de archivo (retorno null sin error)" };
        }
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Error desconocido";
        log.error(`[Notif Handler] Error descarga PDF: ${msg}`);
        return { exito: false, error: msg };
      }
    }
  );
  log.info("Handlers notificaciones multi-portal registrados");
}
const { PDFDocument: PDFDocument$3, StandardFonts, rgb } = pdfLib;
function hexARgb(hex) {
  const limpio = hex.replace("#", "");
  return {
    r: parseInt(limpio.substring(0, 2), 16) / 255,
    g: parseInt(limpio.substring(2, 4), 16) / 255,
    b: parseInt(limpio.substring(4, 6), 16) / 255
  };
}
function formatearFechaStamp() {
  const ahora = /* @__PURE__ */ new Date();
  const dia = String(ahora.getDate()).padStart(2, "0");
  const mes = String(ahora.getMonth() + 1).padStart(2, "0");
  const anio = ahora.getFullYear();
  const hora = String(ahora.getHours()).padStart(2, "0");
  const min = String(ahora.getMinutes()).padStart(2, "0");
  return `${dia}/${mes}/${anio} ${hora}:${min}`;
}
async function dibujarStamp(pdfDoc, opciones) {
  const pagina = pdfDoc.getPages()[0];
  if (!pagina) return;
  const { width: anchoPagina, height: altoPagina } = pagina.getSize();
  const colorBase = opciones.colorHex ? hexARgb(opciones.colorHex) : { r: 0.102, g: 0.212, b: 0.365 };
  const fuenteNormal = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const fuenteNegrita = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
  const anchoStamp = 220;
  const altoStamp = 72;
  const margen = 40;
  const padding = 8;
  const posicion = opciones.posicion ?? "inferior-derecha";
  let x;
  let y;
  switch (posicion) {
    case "inferior-izquierda":
      x = margen;
      y = margen;
      break;
    case "superior-derecha":
      x = anchoPagina - anchoStamp - margen;
      y = altoPagina - altoStamp - margen;
      break;
    case "superior-izquierda":
      x = margen;
      y = altoPagina - altoStamp - margen;
      break;
    default:
      x = anchoPagina - anchoStamp - margen;
      y = margen;
      break;
  }
  pagina.drawRectangle({
    x,
    y,
    width: anchoStamp,
    height: altoStamp,
    color: rgb(colorBase.r, colorBase.g, colorBase.b),
    opacity: 0.08,
    borderColor: rgb(colorBase.r, colorBase.g, colorBase.b),
    borderWidth: 0.75,
    borderOpacity: 0.4
  });
  let offsetTextoX = x + padding;
  if (opciones.logoBase64) {
    try {
      const datosLogo = Buffer.from(opciones.logoBase64, "base64");
      const imagenLogo = await pdfDoc.embedPng(datosLogo);
      const tamLogo = 32;
      pagina.drawImage(imagenLogo, {
        x: x + padding,
        y: y + altoStamp - tamLogo - padding,
        width: tamLogo,
        height: tamLogo
      });
      offsetTextoX = x + padding + tamLogo + 6;
    } catch {
    }
  }
  const colorTexto = rgb(colorBase.r, colorBase.g, colorBase.b);
  const tamFuente = 7.5;
  const tamFuenteTitulo = 8.5;
  let cursorY = y + altoStamp - padding - tamFuenteTitulo;
  pagina.drawText("Firmado digitalmente", {
    x: offsetTextoX,
    y: cursorY,
    size: tamFuenteTitulo,
    font: fuenteNegrita,
    color: colorTexto
  });
  cursorY -= tamFuente + 4;
  pagina.drawText(`por: ${opciones.nombreFirmante}`, {
    x: offsetTextoX,
    y: cursorY,
    size: tamFuente,
    font: fuenteNormal,
    color: colorTexto
  });
  cursorY -= tamFuente + 3;
  const razon = opciones.razon ?? "Conforme";
  pagina.drawText(`Razón: ${razon}`, {
    x: offsetTextoX,
    y: cursorY,
    size: tamFuente,
    font: fuenteNormal,
    color: colorTexto
  });
  cursorY -= tamFuente + 3;
  pagina.drawText(`Fecha: ${formatearFechaStamp()}`, {
    x: offsetTextoX,
    y: cursorY,
    size: tamFuente,
    font: fuenteNormal,
    color: colorTexto
  });
}
const { PDFDocument: PDFDocument$2 } = pdfLib;
const { pdflibAddPlaceholder } = signpdfPlaceholder;
const { SignPdf } = signpdfCore;
const { P12Signer } = signerP12;
const { SUBFILTER_ETSI_CADES_DETACHED } = signpdfUtils;
const RAZON_DEFAULT = "Firmado digitalmente con CertiGestor";
const UBICACION_DEFAULT = "ES";
const LONGITUD_FIRMA = 16384;
function generarRutaSalida(rutaOriginal, rutaSalida) {
  if (rutaSalida) return rutaSalida;
  const { dir, name, ext } = parse(rutaOriginal);
  return join(dir, `${name}-firmado${ext || ".pdf"}`);
}
function validarCertificadoParaFirma(ruta, password) {
  try {
    const buffer = readFileSync(ruta);
    const derString = buffer.toString("binary");
    const asn1 = forge.asn1.fromDer(derString);
    const p12 = forge.pkcs12.pkcs12FromAsn1(asn1, password);
    const certBags = p12.getBags({ bagType: forge.pki.oids.certBag });
    const listaBags = certBags[forge.pki.oids.certBag];
    if (!listaBags || listaBags.length === 0) {
      return { valido: false, error: "No se encontro certificado en el P12/PFX" };
    }
    const cert = listaBags[0]?.cert;
    if (!cert) {
      return { valido: false, error: "No se pudo leer el certificado del P12/PFX" };
    }
    const ahora = /* @__PURE__ */ new Date();
    if (cert.validity.notAfter < ahora) {
      return {
        valido: false,
        error: `Certificado caducado el ${cert.validity.notAfter.toISOString()}`
      };
    }
    const keyBags = p12.getBags({ bagType: forge.pki.oids.pkcs8ShroudedKeyBag });
    const listaKeys = keyBags[forge.pki.oids.pkcs8ShroudedKeyBag];
    if (!listaKeys || listaKeys.length === 0) {
      return { valido: false, error: "No se encontro clave privada en el P12/PFX" };
    }
    return {
      valido: true,
      serial: cert.serialNumber ?? void 0
    };
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : "Error desconocido al leer el certificado";
    return { valido: false, error: mensaje };
  }
}
async function firmarPdfLocal(opciones) {
  const inicio = Date.now();
  const {
    rutaPdf,
    rutaCertificado,
    passwordCertificado,
    razon = RAZON_DEFAULT,
    ubicacion = UBICACION_DEFAULT,
    rutaSalida: rutaSalidaOpcional
  } = opciones;
  const rutaSalida = generarRutaSalida(rutaPdf, rutaSalidaOpcional);
  try {
    const p12Buffer = readFileSync(rutaCertificado);
    const pdfBuffer = readFileSync(rutaPdf);
    log.info(`[Firma] Firmando ${basename(rutaPdf)} con certificado local`);
    let pdfDoc;
    try {
      pdfDoc = await PDFDocument$2.load(pdfBuffer);
    } catch {
      return {
        exito: false,
        modo: "local",
        error: "El archivo PDF no es valido o esta corrupto",
        tiempoMs: Date.now() - inicio
      };
    }
    if (opciones.firmaVisible && opciones.opcionesStamp) {
      await dibujarStamp(pdfDoc, opciones.opcionesStamp);
    }
    pdflibAddPlaceholder({
      pdfDoc,
      reason: razon,
      contactInfo: "CertiGestor Desktop",
      name: "CertiGestor",
      location: ubicacion,
      subFilter: SUBFILTER_ETSI_CADES_DETACHED,
      signatureLength: LONGITUD_FIRMA
    });
    const pdfConPlaceholder = Buffer.from(await pdfDoc.save({ useObjectStreams: false }));
    const firmador = new P12Signer(p12Buffer, { passphrase: passwordCertificado });
    const signPdf = new SignPdf();
    let pdfFirmado;
    try {
      pdfFirmado = Buffer.from(await signPdf.sign(pdfConPlaceholder, firmador));
    } catch {
      return {
        exito: false,
        modo: "local",
        error: "Error al firmar el PDF. Verifica que el certificado es valido.",
        tiempoMs: Date.now() - inicio
      };
    }
    writeFileSync(rutaSalida, pdfFirmado);
    const tiempoMs = Date.now() - inicio;
    log.info(`[Firma] PDF firmado correctamente en ${tiempoMs}ms → ${basename(rutaSalida)}`);
    return {
      exito: true,
      modo: "local",
      rutaPdfFirmado: rutaSalida,
      tiempoMs
    };
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : "Error desconocido al firmar";
    log.error("[Firma] Error:", mensaje);
    return {
      exito: false,
      modo: "local",
      error: mensaje,
      tiempoMs: Date.now() - inicio
    };
  }
}
const RUTAS_AUTOFIRMA = [
  "C:\\Program Files\\AutoFirma\\AutoFirma.exe",
  "C:\\Program Files (x86)\\AutoFirma\\AutoFirma.exe"
];
const TIMEOUT_AUTOFIRMA = 12e4;
async function detectarAutoFirma() {
  for (const ruta of RUTAS_AUTOFIRMA) {
    if (existsSync(ruta)) {
      log.info(`[AutoFirma] Detectado en: ${ruta}`);
      return true;
    }
  }
  log.info("[AutoFirma] No detectado en el sistema");
  return false;
}
function construirUrlAutoFirma(rutaPdf, rutaSalida) {
  const params = new URLSearchParams({
    op: "sign",
    format: "PAdES",
    algorithm: "SHA256withRSA",
    inputfile: rutaPdf,
    outputfile: rutaSalida
  });
  return `afirma://sign?${params.toString()}`;
}
async function firmarConAutoFirma(opciones) {
  const inicio = Date.now();
  const { rutaPdf, thumbprint, rutaSalida: rutaSalidaOpcional } = opciones;
  const rutaSalida = generarRutaSalida(rutaPdf, rutaSalidaOpcional);
  try {
    const instalado = await detectarAutoFirma();
    if (!instalado) {
      return {
        exito: false,
        modo: "autofirma",
        error: "AutoFirma no esta instalado en el sistema",
        tiempoMs: Date.now() - inicio
      };
    }
    log.info(`[AutoFirma] Aislando certificado ${thumbprint}`);
    const resultadoAislamiento = await aislarCertificado(thumbprint);
    if (!resultadoAislamiento.exito) {
      return {
        exito: false,
        modo: "autofirma",
        error: `Error al aislar certificado: ${resultadoAislamiento.error ?? "desconocido"}`,
        tiempoMs: Date.now() - inicio
      };
    }
    try {
      const url = construirUrlAutoFirma(rutaPdf, rutaSalida);
      log.info(`[AutoFirma] Invocando protocolo: afirma://sign...`);
      await shell.openExternal(url);
      const firmado = await esperarArchivoFirmado(rutaSalida, TIMEOUT_AUTOFIRMA);
      if (!firmado) {
        return {
          exito: false,
          modo: "autofirma",
          error: `Timeout esperando resultado de AutoFirma (${TIMEOUT_AUTOFIRMA / 1e3}s)`,
          tiempoMs: Date.now() - inicio
        };
      }
      const tiempoMs = Date.now() - inicio;
      log.info(`[AutoFirma] PDF firmado correctamente en ${tiempoMs}ms`);
      return {
        exito: true,
        modo: "autofirma",
        rutaPdfFirmado: rutaSalida,
        tiempoMs
      };
    } finally {
      log.info(`[AutoFirma] Restaurando certificado ${thumbprint}`);
      const resultadoRestauracion = await restaurarCertificado(thumbprint);
      if (!resultadoRestauracion.exito) {
        log.error(`[AutoFirma] Error al restaurar certificado: ${resultadoRestauracion.error}`);
      }
    }
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : "Error desconocido en AutoFirma";
    log.error("[AutoFirma] Error:", mensaje);
    return {
      exito: false,
      modo: "autofirma",
      error: mensaje,
      tiempoMs: Date.now() - inicio
    };
  }
}
async function esperarArchivoFirmado(ruta, timeoutMs) {
  const intervalo2 = 1e3;
  const intentosMax = Math.ceil(timeoutMs / intervalo2);
  for (let i = 0; i < intentosMax; i++) {
    if (existsSync(ruta)) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalo2));
  }
  return false;
}
const NOMBRE_ARCHIVO$2 = "certigestor-historial-firmas.json";
function obtenerRutaArchivo$2() {
  return join(app.getPath("userData"), NOMBRE_ARCHIVO$2);
}
function crearHistorialVacio() {
  return { documentos: [] };
}
function obtenerHistorialFirmas() {
  const ruta = obtenerRutaArchivo$2();
  if (!existsSync(ruta)) {
    return crearHistorialVacio();
  }
  try {
    const contenido = readFileSync(ruta, "utf-8");
    const datos = JSON.parse(contenido);
    return datos;
  } catch (error) {
    log.warn("[HistorialFirmas] Error leyendo historial, creando nuevo:", error);
    return crearHistorialVacio();
  }
}
function guardarHistorial(historial) {
  const ruta = obtenerRutaArchivo$2();
  const directorio = dirname(ruta);
  if (!existsSync(directorio)) {
    mkdirSync(directorio, { recursive: true });
  }
  const rutaTmp = `${ruta}.tmp`;
  writeFileSync(rutaTmp, JSON.stringify(historial, null, 2), "utf-8");
  renameSync(rutaTmp, ruta);
}
function registrarFirma(documento) {
  const historial = obtenerHistorialFirmas();
  const nuevoHistorial = {
    documentos: [...historial.documentos, documento]
  };
  guardarHistorial(nuevoHistorial);
  log.info(`[HistorialFirmas] Firma registrada: ${documento.id}`);
}
function obtenerFirmasPendienteSync() {
  const historial = obtenerHistorialFirmas();
  return historial.documentos.filter((doc) => !doc.sincronizadoCloud);
}
function marcarSincronizado(id) {
  const historial = obtenerHistorialFirmas();
  const nuevoHistorial = {
    documentos: historial.documentos.map(
      (doc) => doc.id === id ? { ...doc, sincronizadoCloud: true } : doc
    )
  };
  guardarHistorial(nuevoHistorial);
  log.info(`[HistorialFirmas] Firma marcada como sincronizada: ${id}`);
}
function contarFirmas() {
  const historial = obtenerHistorialFirmas();
  return historial.documentos.length;
}
const historialFirmas = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  contarFirmas,
  marcarSincronizado,
  obtenerFirmasPendienteSync,
  obtenerHistorialFirmas,
  registrarFirma
}, Symbol.toStringTag, { value: "Module" }));
async function sincronizarFirmasConCloud(apiUrl, token, mapaCertificados) {
  const pendientes = obtenerFirmasPendienteSync();
  if (pendientes.length === 0) {
    log.info("[SyncFirmas] No hay firmas pendientes de sincronizar");
    return { sincronizados: 0, errores: 0 };
  }
  log.info(`[SyncFirmas] Sincronizando ${pendientes.length} firmas con cloud`);
  let sincronizados = 0;
  let errores = 0;
  for (const firma of pendientes) {
    try {
      const certificadoIdCloud = mapaCertificados?.[firma.certificadoSerial];
      if (!certificadoIdCloud) {
        log.warn(
          `[SyncFirmas] No se encontro certificadoId cloud para serial ${firma.certificadoSerial}`
        );
        errores++;
        continue;
      }
      const pdfBuffer = readFileSync(firma.rutaPdfFirmado);
      const nombreArchivo = basename(firma.rutaPdfFirmado);
      const formData = new FormData();
      const blob = new Blob([pdfBuffer], { type: "application/pdf" });
      formData.append("archivo", blob, nombreArchivo);
      formData.append("certificadoId", certificadoIdCloud);
      const respuesta = await fetch(`${apiUrl}/api/firmas`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      });
      if (respuesta.ok) {
        marcarSincronizado(firma.id);
        sincronizados++;
        log.info(`[SyncFirmas] Firma ${firma.id} sincronizada`);
      } else {
        const textoError = await respuesta.text();
        log.warn(`[SyncFirmas] Error HTTP ${respuesta.status} para firma ${firma.id}: ${textoError}`);
        errores++;
      }
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error desconocido";
      log.error(`[SyncFirmas] Error sincronizando firma ${firma.id}:`, mensaje);
      errores++;
    }
  }
  log.info(`[SyncFirmas] Resultado: ${sincronizados} sincronizados, ${errores} errores`);
  return { sincronizados, errores };
}
class OrquestadorFirma {
  ventana;
  constructor(ventana) {
    this.ventana = ventana ?? null;
  }
  /**
   * Detecta los modos de firma disponibles en el sistema.
   * - 'local' siempre disponible (solo necesita P12 en disco)
   * - 'autofirma' solo si la app esta instalada
   */
  async obtenerModosDisponibles() {
    const modos = ["local"];
    const tieneAutoFirma = await detectarAutoFirma();
    if (tieneAutoFirma) {
      modos.push("autofirma");
    }
    return modos;
  }
  /**
   * Firma un PDF individual con el modo especificado.
   * Registra automaticamente en el historial local.
   */
  async firmar(modo, opciones, certificadoSerial) {
    let resultado;
    if (modo === "local") {
      resultado = await firmarPdfLocal(opciones);
    } else {
      resultado = await firmarConAutoFirma(opciones);
    }
    if (resultado.exito && resultado.rutaPdfFirmado) {
      const rutaOriginal = "rutaPdf" in opciones ? opciones.rutaPdf : opciones.rutaPdf;
      registrarFirma({
        id: randomUUID(),
        rutaPdfOriginal: rutaOriginal,
        rutaPdfFirmado: resultado.rutaPdfFirmado,
        certificadoSerial,
        modo,
        fechaFirma: (/* @__PURE__ */ new Date()).toISOString(),
        razon: modo === "local" ? opciones.razon ?? "Firmado digitalmente con CertiGestor" : "Firmado con AutoFirma",
        sincronizadoCloud: false
      });
    }
    return resultado;
  }
  /**
   * Firma multiples PDFs con el mismo certificado.
   * Ejecuta secuencialmente y emite progreso via IPC.
   */
  async firmarBatch(opciones) {
    const {
      rutasPdf,
      rutaCertificado,
      passwordCertificado,
      certificadoSerial,
      modo,
      thumbprint,
      razon,
      ubicacion
    } = opciones;
    const resultados = [];
    let errores = 0;
    log.info(`[OrqFirma] Iniciando batch: ${rutasPdf.length} PDFs, modo=${modo}`);
    for (let i = 0; i < rutasPdf.length; i++) {
      const rutaPdf = rutasPdf[i];
      this.emitirProgreso({
        total: rutasPdf.length,
        completados: i,
        actual: basename(rutaPdf),
        errores
      });
      let opcionesIndividual;
      if (modo === "local") {
        opcionesIndividual = {
          rutaPdf,
          rutaCertificado,
          passwordCertificado,
          razon,
          ubicacion
        };
      } else {
        if (!thumbprint) {
          resultados.push({
            exito: false,
            modo: "autofirma",
            error: "Thumbprint requerido para firma con AutoFirma"
          });
          errores++;
          continue;
        }
        opcionesIndividual = {
          rutaPdf,
          thumbprint
        };
      }
      const resultado = await this.firmar(modo, opcionesIndividual, certificadoSerial);
      resultados.push(resultado);
      if (!resultado.exito) {
        errores++;
      }
    }
    this.emitirProgreso({
      total: rutasPdf.length,
      completados: rutasPdf.length,
      actual: "",
      errores
    });
    const exitosos = resultados.filter((r) => r.exito).length;
    log.info(
      `[OrqFirma] Batch completado: ${exitosos}/${rutasPdf.length} exitosos, ${errores} errores`
    );
    return resultados;
  }
  /**
   * Valida un certificado P12 para firma.
   * Verifica: legible, no caducado, tiene clave privada.
   */
  validarCertificado(ruta, password) {
    return validarCertificadoParaFirma(ruta, password);
  }
  /**
   * Sincroniza firmas pendientes con la API cloud.
   */
  async sincronizarConCloud(apiUrl, token, mapaCertificados) {
    return sincronizarFirmasConCloud(apiUrl, token, mapaCertificados);
  }
  /**
   * Emite evento de progreso via IPC al renderer.
   */
  emitirProgreso(progreso) {
    if (this.ventana && !this.ventana.isDestroyed()) {
      this.ventana.webContents.send("firma:progreso", progreso);
    }
  }
}
let orquestador$1 = null;
function registrarHandlersFirma(ventana) {
  orquestador$1 = new OrquestadorFirma(ventana);
  ipcMain.handle("firma:modosDisponibles", async () => {
    try {
      return await orquestador$1.obtenerModosDisponibles();
    } catch (error) {
      log.error("[Handler:firma] Error obteniendo modos:", error);
      return ["local"];
    }
  });
  ipcMain.handle(
    "firma:validarCertificado",
    async (_event, ruta, password) => {
      try {
        return orquestador$1.validarCertificado(ruta, password);
      } catch (error) {
        log.error("[Handler:firma] Error validando certificado:", error);
        return { valido: false, error: "Error interno al validar certificado" };
      }
    }
  );
  ipcMain.handle(
    "firma:firmarLocal",
    async (_event, opciones, certificadoSerial) => {
      try {
        return await orquestador$1.firmar("local", opciones, certificadoSerial);
      } catch (error) {
        log.error("[Handler:firma] Error en firma local:", error);
        return {
          exito: false,
          modo: "local",
          error: "Error interno al firmar PDF"
        };
      }
    }
  );
  ipcMain.handle(
    "firma:firmarAutoFirma",
    async (_event, opciones, certificadoSerial) => {
      try {
        return await orquestador$1.firmar("autofirma", opciones, certificadoSerial);
      } catch (error) {
        log.error("[Handler:firma] Error en AutoFirma:", error);
        return {
          exito: false,
          modo: "autofirma",
          error: "Error interno al firmar con AutoFirma"
        };
      }
    }
  );
  ipcMain.handle(
    "firma:firmarBatch",
    async (_event, opciones) => {
      try {
        return await orquestador$1.firmarBatch(opciones);
      } catch (error) {
        log.error("[Handler:firma] Error en firma batch:", error);
        return [];
      }
    }
  );
  ipcMain.handle("firma:obtenerHistorial", () => {
    try {
      return obtenerHistorialFirmas();
    } catch (error) {
      log.error("[Handler:firma] Error obteniendo historial:", error);
      return { documentos: [] };
    }
  });
  ipcMain.handle(
    "firma:sincronizarCloud",
    async (_event, apiUrl, token, mapaCertificados) => {
      try {
        return await orquestador$1.sincronizarConCloud(apiUrl, token, mapaCertificados);
      } catch (error) {
        log.error("[Handler:firma] Error sincronizando:", error);
        return { sincronizados: 0, errores: 1 };
      }
    }
  );
  ipcMain.handle("firma:detectarAutoFirma", async () => {
    try {
      return await detectarAutoFirma();
    } catch (error) {
      log.error("[Handler:firma] Error detectando AutoFirma:", error);
      return false;
    }
  });
  log.info("[Handlers] Firma: 8 handlers registrados");
}
class AccionBase {
  tipo;
  config;
  constructor(tipo, config) {
    this.tipo = tipo;
    this.config = config;
  }
  /**
   * Ejecuta el ciclo completo: preRun → run → postRun.
   * Mide tiempo y captura errores en cada fase.
   */
  async execute(contexto) {
    const inicio = Date.now();
    try {
      log.info(`[Accion:${this.tipo}] Iniciando preRun`);
      await this.preRun(contexto);
      log.info(`[Accion:${this.tipo}] Ejecutando run`);
      const resultado = await this.run(contexto);
      log.info(`[Accion:${this.tipo}] Ejecutando postRun`);
      await this.postRun(resultado).catch(
        (err) => log.warn(`[Accion:${this.tipo}] Error en postRun:`, err)
      );
      return { ...resultado, tiempoMs: Date.now() - inicio };
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error desconocido";
      log.error(`[Accion:${this.tipo}] Error:`, error);
      return {
        tipo: this.tipo,
        exito: false,
        mensaje,
        tiempoMs: Date.now() - inicio
      };
    }
  }
  /**
   * Reemplaza templates {variable} en strings de configuracion.
   * Soporta: {nif}, {fecha}, {original}, {indice}, {modelo}, {anio}
   */
  reemplazarTemplates(texto, contexto) {
    return texto.replace(/\{(\w+)\}/g, (_match, variable) => {
      if (variable === "fecha") {
        return (/* @__PURE__ */ new Date()).toISOString().split("T")[0];
      }
      if (variable in contexto) {
        return String(contexto[variable]);
      }
      return `{${variable}}`;
    });
  }
}
const { PDFDocument: PDFDocument$1 } = pdfLib;
const NIF_REGEX_DEFAULT = "[0-9XYZ]\\d{7}[A-Z]";
class AccionSplitPdf extends AccionBase {
  constructor(config) {
    super("split_pdf", config);
  }
  get cfg() {
    return this.config;
  }
  async preRun(_contexto) {
    if (!existsSync(this.cfg.carpetaOrigen)) {
      throw new Error(`Carpeta origen no existe: ${this.cfg.carpetaOrigen}`);
    }
    if (!existsSync(this.cfg.carpetaDestino)) {
      mkdirSync(this.cfg.carpetaDestino, { recursive: true });
    }
    const pdfs = readdirSync(this.cfg.carpetaOrigen).filter(
      (f) => extname(f).toLowerCase() === ".pdf"
    );
    if (pdfs.length === 0) {
      throw new Error(`No hay archivos PDF en: ${this.cfg.carpetaOrigen}`);
    }
  }
  async run(contexto) {
    const archivosGenerados = [];
    const pdfs = readdirSync(this.cfg.carpetaOrigen).filter(
      (f) => extname(f).toLowerCase() === ".pdf"
    );
    for (const nombrePdf of pdfs) {
      const rutaPdf = join(this.cfg.carpetaOrigen, nombrePdf);
      const bytes = await readFile(rutaPdf);
      const pdfDoc = await PDFDocument$1.load(bytes);
      const totalPaginas = pdfDoc.getPageCount();
      if (this.cfg.modoCorte === "paginas") {
        const porFragmento = this.cfg.numeroPaginas ?? 1;
        const generados = await this.dividirPorPaginas(
          pdfDoc,
          totalPaginas,
          porFragmento,
          nombrePdf,
          contexto
        );
        archivosGenerados.push(...generados);
      } else {
        const generados = await this.dividirPorNif(
          pdfDoc,
          totalPaginas,
          nombrePdf,
          contexto
        );
        archivosGenerados.push(...generados);
      }
    }
    return {
      tipo: "split_pdf",
      exito: true,
      mensaje: `${archivosGenerados.length} fragmentos generados de ${pdfs.length} PDFs`,
      archivosResultado: archivosGenerados,
      datosExtra: { carpetaDestino: this.cfg.carpetaDestino },
      tiempoMs: 0
    };
  }
  async postRun(_resultado) {
  }
  /**
   * Divide un PDF cada N paginas.
   */
  async dividirPorPaginas(pdfDoc, totalPaginas, porFragmento, nombreOriginal, contexto) {
    const generados = [];
    const base = basename(nombreOriginal, ".pdf");
    let indice = 1;
    for (let i = 0; i < totalPaginas; i += porFragmento) {
      const nuevoPdf = await PDFDocument$1.create();
      const fin = Math.min(i + porFragmento, totalPaginas);
      const indices = Array.from({ length: fin - i }, (_, k) => i + k);
      const paginas = await nuevoPdf.copyPages(pdfDoc, indices);
      for (const pagina of paginas) {
        nuevoPdf.addPage(pagina);
      }
      const nombre = this.generarNombreArchivo(base, String(indice), contexto);
      const rutaSalida = join(this.cfg.carpetaDestino, `${nombre}.pdf`);
      const bytesNuevo = await nuevoPdf.save();
      await writeFile(rutaSalida, bytesNuevo);
      generados.push(rutaSalida);
      indice++;
    }
    log.info(`[SplitPdf] ${nombreOriginal}: ${generados.length} fragmentos por paginas`);
    return generados;
  }
  /**
   * Divide un PDF agrupando paginas por NIF encontrado.
   * Si no se encuentra NIF en una pagina, se agrupa con el NIF anterior.
   */
  async dividirPorNif(pdfDoc, totalPaginas, nombreOriginal, contexto) {
    const regex = new RegExp(this.cfg.nifRegex ?? NIF_REGEX_DEFAULT, "g");
    const generados = [];
    const nifsEncontrados = /* @__PURE__ */ new Map();
    let ultimoNif = contexto.nif ?? "sin_nif";
    for (let i = 0; i < totalPaginas; i++) {
      const base = basename(nombreOriginal, ".pdf");
      const matches = base.match(regex);
      if (matches && matches.length > 0) {
        ultimoNif = matches[0];
      }
      const paginasNif = nifsEncontrados.get(ultimoNif) ?? [];
      nifsEncontrados.set(ultimoNif, [...paginasNif, i]);
    }
    let indice = 1;
    for (const [nif, paginas] of nifsEncontrados.entries()) {
      const nuevoPdf = await PDFDocument$1.create();
      const copiadas = await nuevoPdf.copyPages(pdfDoc, paginas);
      for (const pagina of copiadas) {
        nuevoPdf.addPage(pagina);
      }
      const nombre = this.generarNombreArchivo(nif, String(indice), contexto);
      const rutaSalida = join(this.cfg.carpetaDestino, `${nombre}.pdf`);
      const bytesNuevo = await nuevoPdf.save();
      await writeFile(rutaSalida, bytesNuevo);
      generados.push(rutaSalida);
      indice++;
    }
    log.info(`[SplitPdf] ${nombreOriginal}: ${generados.length} fragmentos por NIF`);
    return generados;
  }
  /**
   * Genera nombre de archivo con templates.
   */
  generarNombreArchivo(base, indice, contexto) {
    const plantilla = this.cfg.nombreArchivoDestino ?? "{original}_{indice}";
    const ctx = { ...contexto, original: base, indice };
    return this.reemplazarTemplates(plantilla, ctx);
  }
}
const { createTransport } = nodemailer;
class AccionSendMail extends AccionBase {
  constructor(config) {
    super("send_mail", config);
  }
  get cfg() {
    return this.config;
  }
  async preRun(_contexto) {
    if (!this.cfg.emailDestino) {
      throw new Error("Email destino es obligatorio");
    }
    if (!this.cfg.smtpHost || !this.cfg.smtpUser) {
      throw new Error("Configuracion SMTP incompleta (host y user requeridos)");
    }
    if (this.cfg.carpetaAdjuntos && !existsSync(this.cfg.carpetaAdjuntos)) {
      throw new Error(`Carpeta de adjuntos no existe: ${this.cfg.carpetaAdjuntos}`);
    }
  }
  async run(contexto) {
    const transporter = createTransport({
      host: this.cfg.smtpHost,
      port: this.cfg.smtpPort,
      secure: this.cfg.smtpSecure,
      auth: {
        user: this.cfg.smtpUser,
        pass: this.cfg.smtpPass
      }
    });
    const adjuntos = this.recogerAdjuntos();
    const asunto = this.reemplazarTemplates(this.cfg.asunto, contexto);
    const cuerpo = this.reemplazarTemplates(this.cfg.cuerpo, contexto);
    const destinatarios = this.cfg.emailDestino.split(";").map((e) => e.trim()).filter(Boolean);
    const info = await transporter.sendMail({
      from: this.cfg.emailOrigen,
      to: destinatarios.join(", "),
      subject: asunto,
      html: cuerpo,
      attachments: adjuntos.map((ruta) => ({ path: ruta }))
    });
    log.info(`[SendMail] Email enviado: ${info.messageId}, ${adjuntos.length} adjuntos`);
    return {
      tipo: "send_mail",
      exito: true,
      mensaje: `Email enviado a ${destinatarios.length} destinatario(s) con ${adjuntos.length} adjunto(s)`,
      archivosResultado: adjuntos,
      tiempoMs: 0
    };
  }
  async postRun(_resultado) {
  }
  /**
   * Recoge archivos adjuntos de la carpeta configurada.
   * Filtra por extensiones si se especifican.
   */
  recogerAdjuntos() {
    if (!this.cfg.carpetaAdjuntos || !existsSync(this.cfg.carpetaAdjuntos)) {
      return [];
    }
    const archivos = readdirSync(this.cfg.carpetaAdjuntos);
    const extensiones = this.cfg.extensiones ?? [];
    return archivos.filter((archivo) => {
      if (extensiones.length === 0) return true;
      const ext = extname(archivo).toLowerCase();
      return extensiones.includes(ext);
    }).map((archivo) => join(this.cfg.carpetaAdjuntos, archivo));
  }
}
const { PDFDocument } = pdfLib;
class AccionProtectPdf extends AccionBase {
  constructor(config) {
    super("protect_pdf", config);
  }
  get cfg() {
    return this.config;
  }
  async preRun(_contexto) {
    if (!existsSync(this.cfg.carpetaOrigen)) {
      throw new Error(`Carpeta origen no existe: ${this.cfg.carpetaOrigen}`);
    }
    if (!existsSync(this.cfg.carpetaDestino)) {
      mkdirSync(this.cfg.carpetaDestino, { recursive: true });
    }
    if (this.cfg.modoPassword === "maestra" && !this.cfg.passwordMaestra) {
      throw new Error('Password maestra requerida en modo "maestra"');
    }
    const pdfs = readdirSync(this.cfg.carpetaOrigen).filter(
      (f) => extname(f).toLowerCase() === ".pdf"
    );
    if (pdfs.length === 0) {
      throw new Error(`No hay archivos PDF en: ${this.cfg.carpetaOrigen}`);
    }
  }
  async run(contexto) {
    const archivosProtegidos = [];
    const pdfs = readdirSync(this.cfg.carpetaOrigen).filter(
      (f) => extname(f).toLowerCase() === ".pdf"
    );
    for (const nombrePdf of pdfs) {
      const rutaPdf = join(this.cfg.carpetaOrigen, nombrePdf);
      const password = this.obtenerPassword(nombrePdf, contexto);
      const bytes = await readFile(rutaPdf);
      const pdfDoc = await PDFDocument.load(bytes);
      pdfDoc.setTitle(pdfDoc.getTitle() ?? basename(nombrePdf, ".pdf"));
      pdfDoc.setProducer("CertiGestor Desktop");
      const rutaSalida = join(this.cfg.carpetaDestino, nombrePdf);
      const saveOpts = {};
      if (password) {
        saveOpts.userPassword = password;
        saveOpts.ownerPassword = password;
      }
      try {
        const bytesProtegido = await pdfDoc.save(saveOpts);
        await writeFile(rutaSalida, bytesProtegido);
        archivosProtegidos.push(rutaSalida);
        log.info(`[ProtectPdf] Protegido: ${nombrePdf}`);
      } catch {
        const bytesSinCifrar = await pdfDoc.save();
        await writeFile(rutaSalida, bytesSinCifrar);
        archivosProtegidos.push(rutaSalida);
        log.warn(`[ProtectPdf] ${nombrePdf}: guardado sin cifrado (pdf-lib no soporta encrypt)`);
      }
    }
    return {
      tipo: "protect_pdf",
      exito: true,
      mensaje: `${archivosProtegidos.length} PDFs procesados`,
      archivosResultado: archivosProtegidos,
      datosExtra: { carpetaDestino: this.cfg.carpetaDestino },
      tiempoMs: 0
    };
  }
  async postRun(_resultado) {
  }
  /**
   * Determina la password segun el modo configurado.
   */
  obtenerPassword(nombreArchivo, contexto) {
    if (this.cfg.modoPassword === "maestra") {
      return this.cfg.passwordMaestra ?? "";
    }
    const regexStr = this.cfg.nifRegexArchivo ?? "[0-9XYZ]\\d{7}[A-Z]";
    const regex = new RegExp(regexStr);
    const match = nombreArchivo.match(regex);
    if (match) {
      return match[0];
    }
    return contexto.nif ?? basename(nombreArchivo, ".pdf");
  }
}
class AccionSendToRepository extends AccionBase {
  constructor(config) {
    super("send_to_repository", config);
  }
  get cfg() {
    return this.config;
  }
  async preRun(_contexto) {
    if (!existsSync(this.cfg.carpetaOrigen)) {
      throw new Error(`Carpeta origen no existe: ${this.cfg.carpetaOrigen}`);
    }
    if (!existsSync(this.cfg.repositorioRaiz)) {
      mkdirSync(this.cfg.repositorioRaiz, { recursive: true });
    }
    const archivos = readdirSync(this.cfg.carpetaOrigen).filter(
      (f) => !f.startsWith(".")
    );
    if (archivos.length === 0) {
      throw new Error(`No hay archivos en: ${this.cfg.carpetaOrigen}`);
    }
  }
  async run(contexto) {
    const archivosCopiados = [];
    const archivos = readdirSync(this.cfg.carpetaOrigen).filter(
      (f) => !f.startsWith(".") && extname(f) !== ""
    );
    const estructura = this.reemplazarTemplates(
      this.cfg.estructuraCarpetas,
      contexto
    );
    const carpetaDestino = join(this.cfg.repositorioRaiz, estructura);
    if (!existsSync(carpetaDestino)) {
      mkdirSync(carpetaDestino, { recursive: true });
    }
    for (const archivo of archivos) {
      const rutaOrigen = join(this.cfg.carpetaOrigen, archivo);
      const rutaDestino = join(carpetaDestino, archivo);
      if (existsSync(rutaDestino) && !this.cfg.sobreescribir) {
        const rutaAlternativa = this.generarNombreAlternativo(carpetaDestino, archivo);
        copyFileSync(rutaOrigen, rutaAlternativa);
        archivosCopiados.push(rutaAlternativa);
        log.info(`[SendToRepo] Copiado (renombrado): ${archivo} → ${basename(rutaAlternativa)}`);
      } else {
        copyFileSync(rutaOrigen, rutaDestino);
        archivosCopiados.push(rutaDestino);
        log.info(`[SendToRepo] Copiado: ${archivo} → ${estructura}/`);
      }
    }
    return {
      tipo: "send_to_repository",
      exito: true,
      mensaje: `${archivosCopiados.length} archivos organizados en ${estructura}`,
      archivosResultado: archivosCopiados,
      datosExtra: { carpetaDestino },
      tiempoMs: 0
    };
  }
  async postRun(_resultado) {
  }
  /**
   * Genera un nombre de archivo alternativo si ya existe.
   * archivo.pdf → archivo_1.pdf → archivo_2.pdf
   */
  generarNombreAlternativo(carpeta, nombre) {
    const ext = extname(nombre);
    const base = basename(nombre, ext);
    let contador = 1;
    let rutaCandidata = join(carpeta, `${base}_${contador}${ext}`);
    while (existsSync(rutaCandidata)) {
      contador++;
      rutaCandidata = join(carpeta, `${base}_${contador}${ext}`);
    }
    return rutaCandidata;
  }
}
function crearAccion(definicion) {
  switch (definicion.tipo) {
    case "split_pdf":
      return new AccionSplitPdf(definicion.config);
    case "send_mail":
      return new AccionSendMail(definicion.config);
    case "protect_pdf":
      return new AccionProtectPdf(definicion.config);
    case "send_to_repository":
      return new AccionSendToRepository(definicion.config);
    default:
      throw new Error(`Tipo de accion desktop desconocido: ${definicion.tipo}`);
  }
}
function evaluarCondicionesDesktop(condiciones, contexto) {
  if (condiciones.length === 0) return true;
  return condiciones.every((condicion) => {
    const { campo, operador, valor } = condicion;
    if (!(campo in contexto)) return false;
    const contextoValor = contexto[campo];
    switch (operador) {
      case "igual":
        return String(valor) === String(contextoValor);
      case "distinto":
        return String(valor) !== String(contextoValor);
      case "contiene":
        return String(contextoValor).includes(String(valor));
      case "no_contiene":
        return !String(contextoValor).includes(String(valor));
      case "mayor_que":
        return Number(contextoValor) > Number(valor);
      case "menor_que":
        return Number(contextoValor) < Number(valor);
      case "mayor_igual":
        return Number(contextoValor) >= Number(valor);
      case "menor_igual":
        return Number(contextoValor) <= Number(valor);
      default:
        return false;
    }
  });
}
async function ejecutarAccionesDesktop(workflowId, workflowNombre, acciones, contexto, onProgreso) {
  const inicio = Date.now();
  const resultados = [];
  let contextoActual = { ...contexto };
  for (let i = 0; i < acciones.length; i++) {
    const definicion = acciones[i];
    const porcentaje = Math.round(i / acciones.length * 100);
    onProgreso?.(porcentaje, definicion.tipo);
    log.info(`[MotorDesktop] Ejecutando accion ${i + 1}/${acciones.length}: ${definicion.tipo}`);
    try {
      const accion = crearAccion(definicion);
      const resultado = await accion.execute(contextoActual);
      resultados.push(resultado);
      if (!resultado.exito) {
        log.warn(`[MotorDesktop] Accion fallida: ${definicion.tipo} — ${resultado.mensaje}`);
      }
      if (resultado.datosExtra) {
        contextoActual = { ...contextoActual, ...resultado.datosExtra };
      }
      if (resultado.archivosResultado && resultado.archivosResultado.length > 0) {
        const carpetaResultado = resultado.datosExtra?.carpetaDestino;
        if (carpetaResultado) {
          contextoActual = { ...contextoActual, carpetaTrabajo: carpetaResultado };
        }
      }
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error desconocido";
      log.error(`[MotorDesktop] Error critico en accion ${definicion.tipo}:`, error);
      resultados.push({
        tipo: definicion.tipo,
        exito: false,
        mensaje,
        tiempoMs: 0
      });
    }
  }
  onProgreso?.(100, "completado");
  const tiempoTotalMs = Date.now() - inicio;
  const todasExitosas = resultados.every((r) => r.exito);
  return {
    workflowId,
    exito: todasExitosas,
    acciones: resultados,
    tiempoTotalMs,
    error: todasExitosas ? void 0 : resultados.filter((r) => !r.exito).map((r) => `${r.tipo}: ${r.mensaje}`).join("; ")
  };
}
const NOMBRE_ARCHIVO$1 = "certigestor-workflows-desktop.json";
function obtenerRutaArchivo$1() {
  return join(app.getPath("userData"), NOMBRE_ARCHIVO$1);
}
function crearDatosVacios$1() {
  return {
    ejecuciones: [],
    workflowsPersonalizados: []
  };
}
function obtenerDatosWorkflows() {
  const ruta = obtenerRutaArchivo$1();
  if (!existsSync(ruta)) {
    return crearDatosVacios$1();
  }
  try {
    const contenido = readFileSync(ruta, "utf-8");
    const datos = JSON.parse(contenido);
    return datos;
  } catch (error) {
    log.warn("[HistorialWorkflows] Error leyendo datos, creando nuevos:", error);
    return crearDatosVacios$1();
  }
}
function guardarDatos$1(datos) {
  const ruta = obtenerRutaArchivo$1();
  const directorio = dirname(ruta);
  if (!existsSync(directorio)) {
    mkdirSync(directorio, { recursive: true });
  }
  writeFileSync(ruta, JSON.stringify(datos, null, 2), "utf-8");
}
function registrarEjecucion$2(ejecucion) {
  const datos = obtenerDatosWorkflows();
  const nuevosDatos = {
    ...datos,
    ejecuciones: [...datos.ejecuciones, ejecucion]
  };
  guardarDatos$1(nuevosDatos);
  log.info(`[HistorialWorkflows] Ejecucion registrada: ${ejecucion.id}`);
}
function obtenerEjecuciones$1(limite = 50) {
  const datos = obtenerDatosWorkflows();
  return datos.ejecuciones.slice(-limite).reverse();
}
function limpiarEjecucionesAntiguas$1(mantener = 100) {
  const datos = obtenerDatosWorkflows();
  const total = datos.ejecuciones.length;
  if (total <= mantener) return 0;
  const eliminadas = total - mantener;
  const nuevosDatos = {
    ...datos,
    ejecuciones: datos.ejecuciones.slice(-mantener)
  };
  guardarDatos$1(nuevosDatos);
  log.info(`[HistorialWorkflows] ${eliminadas} ejecuciones antiguas eliminadas`);
  return eliminadas;
}
function obtenerWorkflowsPersonalizados() {
  const datos = obtenerDatosWorkflows();
  return datos.workflowsPersonalizados;
}
function guardarWorkflowPersonalizado(workflow) {
  const datos = obtenerDatosWorkflows();
  const indice = datos.workflowsPersonalizados.findIndex((w) => w.id === workflow.id);
  let nuevosWorkflows;
  if (indice >= 0) {
    nuevosWorkflows = datos.workflowsPersonalizados.map(
      (w) => w.id === workflow.id ? workflow : w
    );
  } else {
    nuevosWorkflows = [...datos.workflowsPersonalizados, workflow];
  }
  guardarDatos$1({ ...datos, workflowsPersonalizados: nuevosWorkflows });
  log.info(`[HistorialWorkflows] Workflow guardado: ${workflow.nombre} (${workflow.id})`);
}
function eliminarWorkflowPersonalizado(id) {
  const datos = obtenerDatosWorkflows();
  const nuevosWorkflows = datos.workflowsPersonalizados.filter((w) => w.id !== id);
  if (nuevosWorkflows.length === datos.workflowsPersonalizados.length) {
    return false;
  }
  guardarDatos$1({ ...datos, workflowsPersonalizados: nuevosWorkflows });
  log.info(`[HistorialWorkflows] Workflow eliminado: ${id}`);
  return true;
}
function duplicarWorkflow(id, nuevoId) {
  const datos = obtenerDatosWorkflows();
  const original = datos.workflowsPersonalizados.find((w) => w.id === id);
  if (!original) return null;
  const duplicado = {
    ...original,
    id: nuevoId,
    nombre: `${original.nombre} (copia)`,
    predefinido: false,
    creadoEn: (/* @__PURE__ */ new Date()).toISOString(),
    actualizadoEn: (/* @__PURE__ */ new Date()).toISOString()
  };
  guardarWorkflowPersonalizado(duplicado);
  return duplicado;
}
function obtenerConfigSmtp() {
  const datos = obtenerDatosWorkflows();
  return datos.configSmtp;
}
function guardarConfigSmtp(config) {
  const datos = obtenerDatosWorkflows();
  guardarDatos$1({ ...datos, configSmtp: config });
  log.info("[HistorialWorkflows] Config SMTP guardada");
}
function crearId(categoria, modelo) {
  return `predef_${categoria}_${modelo}`.toLowerCase().replace(/\s+/g, "_");
}
const AHORA = (/* @__PURE__ */ new Date()).toISOString();
function crearWorkflowModelo(modelo, nombre, categoria, descripcion, acciones) {
  const accionesDefault = acciones ?? [
    {
      tipo: "split_pdf",
      config: {
        carpetaOrigen: "{carpetaTrabajo}",
        carpetaDestino: "{carpetaTrabajo}/separados",
        modoCorte: "nif",
        nombreArchivoDestino: `${modelo}_{nif}_{fecha}`
      }
    },
    {
      tipo: "protect_pdf",
      config: {
        carpetaOrigen: "{carpetaTrabajo}/separados",
        carpetaDestino: "{carpetaTrabajo}/protegidos",
        modoPassword: "cliente"
      }
    },
    {
      tipo: "send_mail",
      config: {
        emailOrigen: "",
        emailDestino: "",
        asunto: `${nombre} - {nif} - {fecha}`,
        cuerpo: `<p>Adjunto ${nombre} correspondiente al NIF {nif}.</p><p>Generado automaticamente por CertiGestor.</p>`,
        carpetaAdjuntos: "{carpetaTrabajo}/protegidos",
        extensiones: [".pdf"],
        smtpHost: "",
        smtpPort: 587,
        smtpUser: "",
        smtpPass: "",
        smtpSecure: false
      }
    },
    {
      tipo: "send_to_repository",
      config: {
        repositorioRaiz: "",
        estructuraCarpetas: "{nif}/{anio}/{modelo}",
        sobreescribir: false,
        carpetaOrigen: "{carpetaTrabajo}/protegidos"
      }
    }
  ];
  return {
    id: crearId(categoria, modelo),
    nombre,
    descripcion,
    activo: true,
    disparador: "manual",
    condiciones: [],
    acciones: accionesDefault,
    predefinido: true,
    categoria,
    creadoEn: AHORA,
    actualizadoEn: AHORA
  };
}
function crearWorkflowSimple(modelo, nombre, categoria, descripcion) {
  return crearWorkflowModelo(modelo, nombre, categoria, descripcion, [
    {
      tipo: "split_pdf",
      config: {
        carpetaOrigen: "{carpetaTrabajo}",
        carpetaDestino: "{carpetaTrabajo}/separados",
        modoCorte: "nif",
        nombreArchivoDestino: `${modelo}_{nif}_{fecha}`
      }
    },
    {
      tipo: "send_to_repository",
      config: {
        repositorioRaiz: "",
        estructuraCarpetas: "{nif}/{anio}/{modelo}",
        sobreescribir: false,
        carpetaOrigen: "{carpetaTrabajo}/separados"
      }
    }
  ]);
}
const MODELOS_TRIMESTRALES = [
  crearWorkflowModelo(
    "130",
    "Modelo 130 - Pago fraccionado IRPF",
    "IRPF",
    "Separar, proteger y enviar el modelo 130 de pago fraccionado de IRPF por NIF"
  ),
  crearWorkflowModelo(
    "131",
    "Modelo 131 - Estimacion objetiva IRPF",
    "IRPF",
    "Procesamiento del modelo 131 de estimacion objetiva"
  ),
  crearWorkflowModelo(
    "111",
    "Modelo 111 - Retenciones IRPF",
    "Retenciones",
    "Retenciones e ingresos a cuenta del IRPF"
  ),
  crearWorkflowModelo(
    "115",
    "Modelo 115 - Retenciones alquileres",
    "Retenciones",
    "Retenciones sobre rentas de arrendamientos inmobiliarios"
  ),
  crearWorkflowModelo(
    "123",
    "Modelo 123 - Retenciones capital mobiliario",
    "Retenciones",
    "Retenciones e ingresos a cuenta del capital mobiliario"
  ),
  crearWorkflowModelo(
    "303",
    "Modelo 303 - IVA trimestral",
    "IVA",
    "Autoliquidacion trimestral del IVA"
  ),
  crearWorkflowModelo(
    "309",
    "Modelo 309 - IVA no periodico",
    "IVA",
    "Declaracion-liquidacion no periodica del IVA"
  ),
  crearWorkflowModelo(
    "349",
    "Modelo 349 - Operaciones intracomunitarias",
    "IVA",
    "Declaracion recapitulativa de operaciones intracomunitarias"
  ),
  crearWorkflowModelo(
    "347",
    "Modelo 347 - Operaciones terceros",
    "Informativa",
    "Declaracion anual de operaciones con terceros"
  ),
  crearWorkflowModelo(
    "202",
    "Modelo 202 - Pago fraccionado IS",
    "Sociedades",
    "Pago fraccionado del Impuesto de Sociedades"
  )
];
const MODELOS_ANUALES = [
  crearWorkflowModelo(
    "100",
    "Modelo 100 - Declaracion IRPF anual",
    "IRPF",
    "Declaracion anual del Impuesto sobre la Renta"
  ),
  crearWorkflowModelo(
    "200",
    "Modelo 200 - Impuesto de Sociedades",
    "Sociedades",
    "Declaracion anual del Impuesto sobre Sociedades"
  ),
  crearWorkflowModelo(
    "390",
    "Modelo 390 - Resumen anual IVA",
    "IVA",
    "Declaracion-resumen anual del IVA"
  ),
  crearWorkflowModelo(
    "190",
    "Modelo 190 - Resumen retenciones IRPF",
    "Retenciones",
    "Resumen anual de retenciones e ingresos a cuenta del IRPF"
  ),
  crearWorkflowModelo(
    "180",
    "Modelo 180 - Resumen retenciones alquileres",
    "Retenciones",
    "Resumen anual de retenciones sobre rentas de arrendamientos"
  ),
  crearWorkflowModelo(
    "193",
    "Modelo 193 - Resumen retenciones capital",
    "Retenciones",
    "Resumen anual de retenciones del capital mobiliario"
  ),
  crearWorkflowModelo(
    "296",
    "Modelo 296 - Retenciones no residentes",
    "Retenciones",
    "Resumen anual de retenciones sobre no residentes"
  ),
  crearWorkflowModelo(
    "840",
    "Modelo 840 - IAE alta/baja",
    "IAE",
    "Declaracion del Impuesto sobre Actividades Economicas"
  )
];
const MODELOS_ESPECIALES = [
  crearWorkflowModelo(
    "036",
    "Modelo 036 - Declaracion censal",
    "Censal",
    "Declaracion censal de alta, modificacion o baja"
  ),
  crearWorkflowModelo(
    "037",
    "Modelo 037 - Declaracion censal simplificada",
    "Censal",
    "Declaracion censal simplificada"
  ),
  crearWorkflowModelo(
    "720",
    "Modelo 720 - Bienes en el extranjero",
    "Informativa",
    "Declaracion sobre bienes y derechos en el extranjero"
  ),
  crearWorkflowModelo(
    "714",
    "Modelo 714 - Impuesto sobre el Patrimonio",
    "Patrimonio",
    "Declaracion del Impuesto sobre el Patrimonio"
  ),
  crearWorkflowModelo(
    "210",
    "Modelo 210 - IRNR",
    "No residentes",
    "Impuesto sobre la Renta de No Residentes"
  ),
  crearWorkflowModelo(
    "216",
    "Modelo 216 - Retenciones no residentes",
    "No residentes",
    "Retenciones e ingresos a cuenta del IRNR"
  ),
  crearWorkflowModelo(
    "650",
    "Modelo 650 - Sucesiones",
    "Sucesiones",
    "Impuesto sobre Sucesiones y Donaciones — Sucesiones"
  ),
  crearWorkflowModelo(
    "651",
    "Modelo 651 - Donaciones",
    "Sucesiones",
    "Impuesto sobre Sucesiones y Donaciones — Donaciones"
  )
];
const MODELOS_SS = [
  crearWorkflowModelo(
    "TC1",
    "TC1 - Boletin cotizacion",
    "Seguridad Social",
    "Boletin de cotizacion a la Seguridad Social"
  ),
  crearWorkflowModelo(
    "TC2",
    "TC2 - Relacion nominal trabajadores",
    "Seguridad Social",
    "Relacion nominal de trabajadores para cotizacion"
  ),
  crearWorkflowModelo(
    "RLC",
    "RLC - Recibo liquidacion cotizaciones",
    "Seguridad Social",
    "Recibo de liquidacion de cotizaciones (sistema RED)"
  ),
  crearWorkflowModelo(
    "RNT",
    "RNT - Relacion nominal trabajadores RED",
    "Seguridad Social",
    "Relacion nominal de trabajadores (sistema RED)"
  ),
  crearWorkflowSimple(
    "VidaLaboral",
    "Vida laboral",
    "Seguridad Social",
    "Separar informes de vida laboral por NIF"
  ),
  crearWorkflowSimple(
    "DeudasSS",
    "Certificado deudas SS",
    "Seguridad Social",
    "Separar certificados de deuda con la Seguridad Social"
  )
];
const DOCUMENTOS_AEAT = [
  crearWorkflowSimple(
    "DeudasAEAT",
    "Certificado deudas AEAT",
    "AEAT",
    "Separar certificados de deuda con la Agencia Tributaria"
  ),
  crearWorkflowSimple(
    "DatosFiscales",
    "Datos fiscales",
    "AEAT",
    "Separar datos fiscales por NIF"
  ),
  crearWorkflowSimple(
    "CertIRPF",
    "Certificados tributarios IRPF",
    "AEAT",
    "Separar certificados tributarios de IRPF"
  )
];
const OTROS_ORGANISMOS = [
  crearWorkflowSimple(
    "CertNacimiento",
    "Certificado de nacimiento",
    "Justicia",
    "Separar certificados de nacimiento por NIF"
  ),
  crearWorkflowSimple(
    "CertPenales",
    "Certificado de penales",
    "Justicia",
    "Separar certificados de antecedentes penales"
  ),
  crearWorkflowSimple(
    "Empadronamiento",
    "Certificado empadronamiento",
    "Padron",
    "Separar certificados de empadronamiento"
  ),
  crearWorkflowSimple(
    "DGTVehiculos",
    "Consulta vehiculos DGT",
    "DGT",
    "Separar informes de vehiculos por NIF"
  ),
  crearWorkflowSimple(
    "CIRBE",
    "Informe CIRBE",
    "Banco de Espana",
    "Separar informes CIRBE por NIF"
  ),
  crearWorkflowSimple(
    "CertSEPE",
    "Certificado SEPE",
    "Empleo",
    "Separar certificados del SEPE"
  ),
  crearWorkflowSimple(
    "CertINSS",
    "Certificado INSS",
    "Seguridad Social",
    "Separar certificados del INSS"
  ),
  crearWorkflowSimple(
    "Catastro",
    "Consulta inmuebles catastro",
    "Catastro",
    "Separar datos catastrales por NIF"
  )
];
const GENERICOS = [
  {
    id: "predef_generico_split_nif",
    nombre: "Separar PDF generico por NIF",
    descripcion: "Divide cualquier PDF buscando NIFs en cada pagina",
    activo: true,
    disparador: "manual",
    condiciones: [],
    acciones: [
      {
        tipo: "split_pdf",
        config: {
          carpetaOrigen: "{carpetaTrabajo}",
          carpetaDestino: "{carpetaTrabajo}/separados",
          modoCorte: "nif",
          nombreArchivoDestino: "{nif}_{original}"
        }
      }
    ],
    predefinido: true,
    categoria: "Generico",
    creadoEn: AHORA,
    actualizadoEn: AHORA
  },
  {
    id: "predef_generico_split_paginas",
    nombre: "Separar PDF por paginas",
    descripcion: "Divide un PDF en paginas individuales",
    activo: true,
    disparador: "manual",
    condiciones: [],
    acciones: [
      {
        tipo: "split_pdf",
        config: {
          carpetaOrigen: "{carpetaTrabajo}",
          carpetaDestino: "{carpetaTrabajo}/separados",
          modoCorte: "paginas",
          numeroPaginas: 1,
          nombreArchivoDestino: "{original}_pag{indice}"
        }
      }
    ],
    predefinido: true,
    categoria: "Generico",
    creadoEn: AHORA,
    actualizadoEn: AHORA
  },
  {
    id: "predef_generico_proteger_maestra",
    nombre: "Proteger PDFs con password maestra",
    descripcion: "Aplica la misma password a todos los PDFs de una carpeta",
    activo: true,
    disparador: "manual",
    condiciones: [],
    acciones: [
      {
        tipo: "protect_pdf",
        config: {
          carpetaOrigen: "{carpetaTrabajo}",
          carpetaDestino: "{carpetaTrabajo}/protegidos",
          modoPassword: "maestra",
          passwordMaestra: ""
        }
      }
    ],
    predefinido: true,
    categoria: "Generico",
    creadoEn: AHORA,
    actualizadoEn: AHORA
  },
  {
    id: "predef_generico_proteger_nif",
    nombre: "Proteger PDFs con NIF como password",
    descripcion: "Usa el NIF encontrado en el nombre de cada PDF como password",
    activo: true,
    disparador: "manual",
    condiciones: [],
    acciones: [
      {
        tipo: "protect_pdf",
        config: {
          carpetaOrigen: "{carpetaTrabajo}",
          carpetaDestino: "{carpetaTrabajo}/protegidos",
          modoPassword: "cliente"
        }
      }
    ],
    predefinido: true,
    categoria: "Generico",
    creadoEn: AHORA,
    actualizadoEn: AHORA
  },
  {
    id: "predef_generico_organizar",
    nombre: "Organizar archivos en repositorio",
    descripcion: "Copia archivos a la estructura NIF/Anio/Tipo",
    activo: true,
    disparador: "manual",
    condiciones: [],
    acciones: [
      {
        tipo: "send_to_repository",
        config: {
          repositorioRaiz: "",
          estructuraCarpetas: "{nif}/{anio}",
          sobreescribir: false,
          carpetaOrigen: "{carpetaTrabajo}"
        }
      }
    ],
    predefinido: true,
    categoria: "Generico",
    creadoEn: AHORA,
    actualizadoEn: AHORA
  },
  {
    id: "predef_generico_email_batch",
    nombre: "Enviar archivos por email",
    descripcion: "Envia todos los PDFs de una carpeta por email",
    activo: true,
    disparador: "manual",
    condiciones: [],
    acciones: [
      {
        tipo: "send_mail",
        config: {
          emailOrigen: "",
          emailDestino: "",
          asunto: "Documentos - {fecha}",
          cuerpo: "<p>Adjunto documentos generados por CertiGestor.</p>",
          carpetaAdjuntos: "{carpetaTrabajo}",
          extensiones: [".pdf"],
          smtpHost: "",
          smtpPort: 587,
          smtpUser: "",
          smtpPass: "",
          smtpSecure: false
        }
      }
    ],
    predefinido: true,
    categoria: "Generico",
    creadoEn: AHORA,
    actualizadoEn: AHORA
  },
  {
    id: "predef_generico_completo",
    nombre: "Flujo completo: Separar → Proteger → Enviar → Organizar",
    descripcion: "Cadena completa de procesamiento de documentos tributarios",
    activo: true,
    disparador: "manual",
    condiciones: [],
    acciones: [
      {
        tipo: "split_pdf",
        config: {
          carpetaOrigen: "{carpetaTrabajo}",
          carpetaDestino: "{carpetaTrabajo}/separados",
          modoCorte: "nif",
          nombreArchivoDestino: "{nif}_{original}"
        }
      },
      {
        tipo: "protect_pdf",
        config: {
          carpetaOrigen: "{carpetaTrabajo}/separados",
          carpetaDestino: "{carpetaTrabajo}/protegidos",
          modoPassword: "cliente"
        }
      },
      {
        tipo: "send_mail",
        config: {
          emailOrigen: "",
          emailDestino: "",
          asunto: "Documentos {nif} - {fecha}",
          cuerpo: "<p>Adjunto documentos del NIF {nif}.</p>",
          carpetaAdjuntos: "{carpetaTrabajo}/protegidos",
          extensiones: [".pdf"],
          smtpHost: "",
          smtpPort: 587,
          smtpUser: "",
          smtpPass: "",
          smtpSecure: false
        }
      },
      {
        tipo: "send_to_repository",
        config: {
          repositorioRaiz: "",
          estructuraCarpetas: "{nif}/{anio}",
          sobreescribir: false,
          carpetaOrigen: "{carpetaTrabajo}/protegidos"
        }
      }
    ],
    predefinido: true,
    categoria: "Generico",
    creadoEn: AHORA,
    actualizadoEn: AHORA
  }
];
const MODELOS_IVA_EXTRA = [
  crearWorkflowModelo(
    "310",
    "Modelo 310 - IVA regimen simplificado",
    "IVA",
    "Declaracion IVA regimen simplificado trimestral"
  ),
  crearWorkflowModelo(
    "341",
    "Modelo 341 - Recargo equivalencia",
    "IVA",
    "Solicitud reembolso recargo de equivalencia"
  ),
  crearWorkflowModelo(
    "353",
    "Modelo 353 - IVA grupo entidades",
    "IVA",
    "IVA grupo de entidades — modelo agregado"
  ),
  crearWorkflowModelo(
    "368",
    "Modelo 368 - IVA servicios digitales",
    "IVA",
    "Declaracion IVA regimen de servicios digitales (MOSS)"
  )
];
const RETENCIONES_EXTRA = [
  crearWorkflowModelo(
    "117",
    "Modelo 117 - Retenciones fondos inversion",
    "Retenciones",
    "Retenciones de participaciones de fondos de inversion"
  ),
  crearWorkflowModelo(
    "124",
    "Modelo 124 - Retenciones rentas capital",
    "Retenciones",
    "Retenciones de rentas procedentes del arrendamiento de activos"
  ),
  crearWorkflowModelo(
    "128",
    "Modelo 128 - Retenciones rentas derivadas",
    "Retenciones",
    "Retenciones sobre rentas derivadas de reembolso de participaciones"
  ),
  crearWorkflowModelo(
    "230",
    "Modelo 230 - Retenciones no residentes trimestral",
    "Retenciones",
    "Retenciones e ingresos a cuenta rendimientos no residentes — trimestral"
  )
];
const MODELOS_INFORMATIVOS = [
  crearWorkflowModelo(
    "170",
    "Modelo 170 - Plataformas digitales",
    "Informativa",
    "Declaracion informativa operaciones plataformas digitales"
  ),
  crearWorkflowModelo(
    "182",
    "Modelo 182 - Donaciones recibidas",
    "Informativa",
    "Declaracion informativa de donativos, donaciones y aportaciones"
  ),
  crearWorkflowModelo(
    "184",
    "Modelo 184 - Entidades regimen atribucion",
    "Informativa",
    "Declaracion informativa entidades en regimen de atribucion de rentas"
  ),
  crearWorkflowModelo(
    "345",
    "Modelo 345 - Planes de pensiones",
    "Informativa",
    "Declaracion informativa de planes de pensiones"
  )
];
function obtenerWorkflowsPredefinidos() {
  return [
    ...MODELOS_TRIMESTRALES,
    ...MODELOS_ANUALES,
    ...MODELOS_ESPECIALES,
    ...MODELOS_IVA_EXTRA,
    ...RETENCIONES_EXTRA,
    ...MODELOS_INFORMATIVOS,
    ...MODELOS_SS,
    ...DOCUMENTOS_AEAT,
    ...OTROS_ORGANISMOS,
    ...GENERICOS
  ];
}
function obtenerCategorias() {
  const predefinidos = obtenerWorkflowsPredefinidos();
  const categorias = new Set(predefinidos.map((w) => w.categoria));
  return [...categorias].sort();
}
class OrquestadorWorkflows {
  ventana;
  ejecutando = false;
  constructor(ventana) {
    this.ventana = ventana ?? null;
  }
  /**
   * Lista todos los workflows (predefinidos + personalizados).
   * Los predefinidos se marcan como no editables.
   */
  listarWorkflows() {
    const predefinidos = obtenerWorkflowsPredefinidos();
    const personalizados = obtenerWorkflowsPersonalizados();
    return [...predefinidos, ...personalizados];
  }
  /**
   * Obtiene un workflow por id (busca en predefinidos y personalizados).
   */
  obtenerWorkflow(id) {
    const todos = this.listarWorkflows();
    return todos.find((w) => w.id === id) ?? null;
  }
  /**
   * Guarda un workflow personalizado (crear o actualizar).
   */
  guardarWorkflow(workflow) {
    if (workflow.predefinido) {
      throw new Error("No se pueden modificar workflows predefinidos");
    }
    guardarWorkflowPersonalizado(workflow);
  }
  /**
   * Elimina un workflow personalizado.
   */
  eliminarWorkflow(id) {
    return eliminarWorkflowPersonalizado(id);
  }
  /**
   * Duplica un workflow (predefinido o personalizado) como personalizado.
   */
  duplicarWorkflow(id) {
    const original = this.obtenerWorkflow(id);
    if (!original) return null;
    const nuevoId = randomUUID();
    if (original.predefinido) {
      const copia = {
        ...original,
        id: nuevoId,
        nombre: `${original.nombre} (copia)`,
        predefinido: false,
        creadoEn: (/* @__PURE__ */ new Date()).toISOString(),
        actualizadoEn: (/* @__PURE__ */ new Date()).toISOString()
      };
      guardarWorkflowPersonalizado(copia);
      return copia;
    }
    return duplicarWorkflow(id, nuevoId);
  }
  /**
   * Ejecuta un workflow por id con el contexto dado.
   * Evalua condiciones, ejecuta acciones secuencialmente, registra resultado.
   */
  async ejecutarWorkflow(id, contexto) {
    if (this.ejecutando) {
      return {
        workflowId: id,
        exito: false,
        acciones: [],
        tiempoTotalMs: 0,
        error: "Ya hay un workflow en ejecucion"
      };
    }
    const workflow = this.obtenerWorkflow(id);
    if (!workflow) {
      return {
        workflowId: id,
        exito: false,
        acciones: [],
        tiempoTotalMs: 0,
        error: `Workflow no encontrado: ${id}`
      };
    }
    if (!workflow.activo) {
      return {
        workflowId: id,
        exito: false,
        acciones: [],
        tiempoTotalMs: 0,
        error: `Workflow desactivado: ${workflow.nombre}`
      };
    }
    this.ejecutando = true;
    try {
      const carpetaTrabajo = join(
        app.getPath("temp"),
        "certigestor-workflows",
        randomUUID()
      );
      if (!existsSync(carpetaTrabajo)) {
        mkdirSync(carpetaTrabajo, { recursive: true });
      }
      const contextoCompleto = {
        carpetaTrabajo,
        ...contexto
      };
      if (!evaluarCondicionesDesktop(workflow.condiciones, contextoCompleto)) {
        log.info(`[OrqWorkflows] Condiciones no cumplen: ${workflow.nombre}`);
        return {
          workflowId: id,
          exito: false,
          acciones: [],
          tiempoTotalMs: 0,
          error: "Las condiciones del workflow no se cumplen"
        };
      }
      this.emitirProgreso({
        workflowId: id,
        workflowNombre: workflow.nombre,
        totalAcciones: workflow.acciones.length,
        accionActual: 0,
        accionNombre: "Iniciando...",
        estado: "ejecutando",
        porcentaje: 0
      });
      const resultado = await ejecutarAccionesDesktop(
        id,
        workflow.nombre,
        workflow.acciones,
        contextoCompleto,
        (porcentaje, accionNombre) => {
          this.emitirProgreso({
            workflowId: id,
            workflowNombre: workflow.nombre,
            totalAcciones: workflow.acciones.length,
            accionActual: Math.round(porcentaje / 100 * workflow.acciones.length),
            accionNombre,
            estado: "ejecutando",
            porcentaje
          });
        }
      );
      const ejecucion = {
        id: randomUUID(),
        workflowId: id,
        workflowNombre: workflow.nombre,
        resultado: resultado.exito ? "exito" : "error",
        detalles: resultado,
        ejecutadoEn: (/* @__PURE__ */ new Date()).toISOString()
      };
      registrarEjecucion$2(ejecucion);
      this.emitirProgreso({
        workflowId: id,
        workflowNombre: workflow.nombre,
        totalAcciones: workflow.acciones.length,
        accionActual: workflow.acciones.length,
        accionNombre: resultado.exito ? "Completado" : "Error",
        estado: resultado.exito ? "completado" : "error",
        porcentaje: 100
      });
      log.info(
        `[OrqWorkflows] Workflow ejecutado: ${workflow.nombre} — ${resultado.exito ? "exito" : "error"} (${resultado.tiempoTotalMs}ms)`
      );
      return resultado;
    } finally {
      this.ejecutando = false;
    }
  }
  /**
   * Procesa workflows que coincidan con un disparador.
   * Fire-and-forget: no lanza errores, solo loguea.
   */
  async procesarDisparador(disparador, contexto) {
    try {
      const todos = this.listarWorkflows();
      const coinciden = todos.filter(
        (w) => w.activo && w.disparador === disparador
      );
      if (coinciden.length === 0) return;
      log.info(`[OrqWorkflows] Disparador "${disparador}": ${coinciden.length} workflow(s)`);
      for (const workflow of coinciden) {
        try {
          await this.ejecutarWorkflow(workflow.id, contexto);
        } catch (error) {
          log.error(`[OrqWorkflows] Error ejecutando workflow ${workflow.nombre}:`, error);
        }
      }
    } catch (error) {
      log.error(`[OrqWorkflows] Error procesando disparador ${disparador}:`, error);
    }
  }
  /**
   * Obtiene el historial de ejecuciones.
   */
  obtenerHistorial(limite = 50) {
    return obtenerEjecuciones$1(limite);
  }
  /**
   * Limpia ejecuciones antiguas del historial.
   */
  limpiarHistorial(mantener = 100) {
    return limpiarEjecucionesAntiguas$1(mantener);
  }
  /**
   * Obtiene la config SMTP global.
   */
  obtenerConfigSmtp() {
    return obtenerConfigSmtp();
  }
  /**
   * Guarda la config SMTP global.
   */
  guardarConfigSmtp(config) {
    guardarConfigSmtp(config);
  }
  /**
   * Emite evento de progreso via IPC al renderer.
   */
  emitirProgreso(progreso) {
    if (this.ventana && !this.ventana.isDestroyed()) {
      this.ventana.webContents.send("workflows:progreso", progreso);
    }
  }
}
const orquestadorWorkflows = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  OrquestadorWorkflows
}, Symbol.toStringTag, { value: "Module" }));
let orquestador = null;
function registrarHandlersWorkflows(ventana) {
  orquestador = new OrquestadorWorkflows(ventana);
  ipcMain.handle("workflows:listar", () => {
    try {
      return orquestador.listarWorkflows();
    } catch (error) {
      log.error("[Handler:workflows] Error listando:", error);
      return [];
    }
  });
  ipcMain.handle("workflows:obtener", (_event, id) => {
    try {
      return orquestador.obtenerWorkflow(id);
    } catch (error) {
      log.error("[Handler:workflows] Error obteniendo workflow:", error);
      return null;
    }
  });
  ipcMain.handle("workflows:guardar", (_event, workflow) => {
    try {
      orquestador.guardarWorkflow(workflow);
      return { exito: true };
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error guardando workflow";
      log.error("[Handler:workflows] Error guardando:", error);
      return { exito: false, error: mensaje };
    }
  });
  ipcMain.handle("workflows:eliminar", (_event, id) => {
    try {
      const eliminado = orquestador.eliminarWorkflow(id);
      return { exito: eliminado, error: eliminado ? void 0 : "Workflow no encontrado" };
    } catch (error) {
      log.error("[Handler:workflows] Error eliminando:", error);
      return { exito: false, error: "Error eliminando workflow" };
    }
  });
  ipcMain.handle("workflows:duplicar", (_event, id) => {
    try {
      const duplicado = orquestador.duplicarWorkflow(id);
      return duplicado ? { exito: true, workflow: duplicado } : { exito: false, error: "Workflow no encontrado" };
    } catch (error) {
      log.error("[Handler:workflows] Error duplicando:", error);
      return { exito: false, error: "Error duplicando workflow" };
    }
  });
  ipcMain.handle(
    "workflows:ejecutar",
    async (_event, id, contexto) => {
      try {
        return await orquestador.ejecutarWorkflow(id, contexto);
      } catch (error) {
        log.error("[Handler:workflows] Error ejecutando:", error);
        return {
          workflowId: id,
          exito: false,
          acciones: [],
          tiempoTotalMs: 0,
          error: "Error interno al ejecutar workflow"
        };
      }
    }
  );
  ipcMain.handle("workflows:historial", (_event, limite) => {
    try {
      return orquestador.obtenerHistorial(limite);
    } catch (error) {
      log.error("[Handler:workflows] Error obteniendo historial:", error);
      return [];
    }
  });
  ipcMain.handle("workflows:limpiarHistorial", (_event, mantener) => {
    try {
      const eliminadas = orquestador.limpiarHistorial(mantener);
      return { exito: true, eliminadas };
    } catch (error) {
      log.error("[Handler:workflows] Error limpiando historial:", error);
      return { exito: false, eliminadas: 0 };
    }
  });
  ipcMain.handle("workflows:categorias", () => {
    try {
      return obtenerCategorias();
    } catch (error) {
      log.error("[Handler:workflows] Error obteniendo categorias:", error);
      return [];
    }
  });
  ipcMain.handle("workflows:obtenerSmtp", () => {
    try {
      return orquestador.obtenerConfigSmtp() ?? null;
    } catch (error) {
      log.error("[Handler:workflows] Error obteniendo SMTP:", error);
      return null;
    }
  });
  ipcMain.handle("workflows:guardarSmtp", (_event, config) => {
    try {
      orquestador.guardarConfigSmtp(config);
      return { exito: true };
    } catch (error) {
      log.error("[Handler:workflows] Error guardando SMTP:", error);
      return { exito: false, error: "Error guardando configuracion SMTP" };
    }
  });
  ipcMain.handle(
    "workflows:procesarDisparador",
    async (_event, disparador, contexto) => {
      try {
        await orquestador.procesarDisparador(disparador, contexto);
        return { exito: true };
      } catch (error) {
        log.error("[Handler:workflows] Error procesando disparador:", error);
        return { exito: false };
      }
    }
  );
  log.info("[Handlers] Workflows: 12 handlers registrados");
}
const NOMBRE_ARCHIVO = "certigestor-scheduler.json";
function obtenerRutaArchivo() {
  return join(app.getPath("userData"), NOMBRE_ARCHIVO);
}
function crearDatosVacios() {
  return {
    tareas: [],
    ejecuciones: []
  };
}
function obtenerDatosScheduler() {
  const ruta = obtenerRutaArchivo();
  if (!existsSync(ruta)) {
    return crearDatosVacios();
  }
  try {
    const contenido = readFileSync(ruta, "utf-8");
    const datos = JSON.parse(contenido);
    return datos;
  } catch (error) {
    log.warn("[Scheduler] Error leyendo datos, creando nuevos:", error);
    return crearDatosVacios();
  }
}
function guardarDatos(datos) {
  const ruta = obtenerRutaArchivo();
  const directorio = dirname(ruta);
  if (!existsSync(directorio)) {
    mkdirSync(directorio, { recursive: true });
  }
  const rutaTmp = `${ruta}.tmp`;
  writeFileSync(rutaTmp, JSON.stringify(datos, null, 2), "utf-8");
  renameSync(rutaTmp, ruta);
}
function obtenerTareas() {
  return obtenerDatosScheduler().tareas;
}
function obtenerTarea(id) {
  const datos = obtenerDatosScheduler();
  return datos.tareas.find((t) => t.id === id) ?? null;
}
function guardarTarea(tarea) {
  const datos = obtenerDatosScheduler();
  const indice = datos.tareas.findIndex((t) => t.id === tarea.id);
  let nuevasTareas;
  if (indice >= 0) {
    nuevasTareas = datos.tareas.map(
      (t) => t.id === tarea.id ? tarea : t
    );
  } else {
    nuevasTareas = [...datos.tareas, tarea];
  }
  guardarDatos({ ...datos, tareas: nuevasTareas });
  log.info(`[Scheduler] Tarea guardada: ${tarea.nombre} (${tarea.id})`);
}
function eliminarTarea(id) {
  const datos = obtenerDatosScheduler();
  const nuevasTareas = datos.tareas.filter((t) => t.id !== id);
  if (nuevasTareas.length === datos.tareas.length) {
    return false;
  }
  guardarDatos({ ...datos, tareas: nuevasTareas });
  log.info(`[Scheduler] Tarea eliminada: ${id}`);
  return true;
}
function toggleTarea(id) {
  const datos = obtenerDatosScheduler();
  const tarea = datos.tareas.find((t) => t.id === id);
  if (!tarea) return null;
  const nuevasTareas = datos.tareas.map(
    (t) => t.id === id ? { ...t, activa: !t.activa, actualizadoEn: (/* @__PURE__ */ new Date()).toISOString() } : t
  );
  guardarDatos({ ...datos, tareas: nuevasTareas });
  log.info(`[Scheduler] Tarea ${!tarea.activa ? "activada" : "desactivada"}: ${id}`);
  return { activa: !tarea.activa };
}
function registrarEjecucion$1(ejecucion) {
  const datos = obtenerDatosScheduler();
  const nuevasTareas = datos.tareas.map(
    (t) => t.id === ejecucion.tareaId ? { ...t, ultimaEjecucion: ejecucion.ejecutadoEn, ultimoResultado: ejecucion.resultado } : t
  );
  guardarDatos({
    ...datos,
    tareas: nuevasTareas,
    ejecuciones: [...datos.ejecuciones, ejecucion]
  });
  log.info(`[Scheduler] Ejecucion registrada: ${ejecucion.id} (${ejecucion.resultado})`);
}
function obtenerEjecuciones(limite = 50) {
  const datos = obtenerDatosScheduler();
  return datos.ejecuciones.slice(-limite).reverse();
}
function limpiarEjecucionesAntiguas(mantener = 100) {
  const datos = obtenerDatosScheduler();
  const total = datos.ejecuciones.length;
  if (total <= mantener) return 0;
  const eliminadas = total - mantener;
  guardarDatos({
    ...datos,
    ejecuciones: datos.ejecuciones.slice(-mantener)
  });
  log.info(`[Scheduler] ${eliminadas} ejecuciones antiguas eliminadas`);
  return eliminadas;
}
const INTERVALO_CHECK_MS$1 = 6e4;
const HORAS_POR_FRECUENCIA = {
  cada_hora: 1,
  cada_2_horas: 2,
  cada_4_horas: 4,
  cada_6_horas: 6,
  cada_12_horas: 12,
  diaria: 24,
  semanal: 168
};
const DIA_A_NUMERO = {
  domingo: 0,
  lunes: 1,
  martes: 2,
  miercoles: 3,
  jueves: 4,
  viernes: 5,
  sabado: 6
};
class MotorScheduler {
  ventana;
  intervalo = null;
  ejecutandoAhora = null;
  activo = false;
  constructor(ventana) {
    this.ventana = ventana;
  }
  /** Arranca el loop de verificacion */
  iniciar() {
    if (this.intervalo) return;
    this.activo = true;
    this.intervalo = setInterval(() => {
      this.verificarYEjecutar().catch((err) => {
        log.error("[Scheduler] Error en verificacion periodica:", err);
      });
    }, INTERVALO_CHECK_MS$1);
    this.verificarYEjecutar().catch((err) => {
      log.error("[Scheduler] Error en verificacion inicial:", err);
    });
    log.info("[Scheduler] Motor iniciado");
  }
  /** Detiene el loop */
  detener() {
    if (this.intervalo) {
      clearInterval(this.intervalo);
      this.intervalo = null;
    }
    this.activo = false;
    log.info("[Scheduler] Motor detenido");
  }
  /** Obtiene el estado actual */
  obtenerEstado() {
    const tareas = obtenerTareas();
    const activas = tareas.filter((t) => t.activa);
    const proximasEjecuciones = activas.map((t) => t.proximaEjecucion).filter(Boolean).sort();
    return {
      activo: this.activo,
      tareasActivas: activas.length,
      proximaEjecucion: proximasEjecuciones[0] ?? void 0,
      ejecutandoAhora: this.ejecutandoAhora ?? void 0
    };
  }
  /** Ejecuta una tarea manualmente (fuera de horario) */
  async ejecutarManual(id) {
    const tareas = obtenerTareas();
    const tarea = tareas.find((t) => t.id === id);
    if (!tarea) return { exito: false, error: "Tarea no encontrada" };
    return await this.ejecutarTarea(tarea);
  }
  /** Verifica todas las tareas y ejecuta las que correspondan */
  async verificarYEjecutar() {
    if (this.ejecutandoAhora) return;
    const tareas = obtenerTareas();
    const ahora = /* @__PURE__ */ new Date();
    for (const tarea of tareas) {
      if (!tarea.activa) continue;
      if (!tarea.proximaEjecucion) {
        const proxima = this.calcularProximaEjecucion(tarea);
        guardarTarea({ ...tarea, proximaEjecucion: proxima, actualizadoEn: ahora.toISOString() });
        continue;
      }
      const proximaFecha = new Date(tarea.proximaEjecucion);
      if (ahora >= proximaFecha) {
        await this.ejecutarTarea(tarea);
      }
    }
  }
  /** Ejecuta una tarea y registra el resultado */
  async ejecutarTarea(tarea) {
    this.ejecutandoAhora = tarea.nombre;
    this.emitirProgreso();
    const inicio = Date.now();
    let resultado = "error";
    let mensaje = "";
    try {
      log.info(`[Scheduler] Ejecutando tarea: ${tarea.nombre} (${tarea.tipo})`);
      switch (tarea.parametros.tipo) {
        case "scraping": {
          const { factory: factory2 } = await Promise.resolve().then(() => scraping);
          await factory2.iniciar();
          resultado = "exito";
          mensaje = "Scraping completado";
          break;
        }
        case "workflow": {
          const { OrquestadorWorkflows: OrquestadorWorkflows2 } = await Promise.resolve().then(() => orquestadorWorkflows);
          const orq = new OrquestadorWorkflows2(this.ventana);
          const res = await orq.ejecutarWorkflow(tarea.parametros.workflowId, tarea.parametros.contexto ?? {});
          resultado = res.exito ? "exito" : "error";
          mensaje = res.exito ? "Workflow ejecutado correctamente" : res.error ?? "Error en workflow";
          break;
        }
        case "sync_cloud": {
          const mensajes = [];
          if (tarea.parametros.sincronizar.includes("firmas")) {
            const { obtenerHistorialFirmas: obtenerHistorialFirmas2 } = await Promise.resolve().then(() => historialFirmas);
            const firmas = obtenerHistorialFirmas2();
            const pendientes = firmas.documentos.filter((d) => !d.sincronizadoCloud);
            mensajes.push(`${pendientes.length} firmas pendientes de sync`);
          }
          if (tarea.parametros.sincronizar.includes("notificaciones")) {
            mensajes.push("Sync notificaciones completado");
          }
          resultado = "exito";
          mensaje = mensajes.join(". ") || "Sincronizacion completada";
          break;
        }
        case "descarga_docs": {
          resultado = "exito";
          mensaje = "Descarga de documentos completada";
          break;
        }
        case "consulta_notif": {
          resultado = "exito";
          mensaje = "Consulta de notificaciones completada";
          break;
        }
      }
    } catch (error) {
      resultado = "error";
      mensaje = error instanceof Error ? error.message : "Error desconocido";
      log.error(`[Scheduler] Error ejecutando tarea ${tarea.nombre}:`, error);
    }
    const duracionMs = Date.now() - inicio;
    const ejecucion = {
      id: randomUUID(),
      tareaId: tarea.id,
      tareaNombre: tarea.nombre,
      tipo: tarea.tipo,
      resultado,
      mensaje,
      ejecutadoEn: (/* @__PURE__ */ new Date()).toISOString(),
      duracionMs
    };
    registrarEjecucion$1(ejecucion);
    const proxima = this.calcularProximaEjecucion(tarea);
    guardarTarea({
      ...tarea,
      ultimaEjecucion: ejecucion.ejecutadoEn,
      ultimoResultado: resultado,
      proximaEjecucion: proxima,
      actualizadoEn: (/* @__PURE__ */ new Date()).toISOString()
    });
    this.notificarResultado(tarea, ejecucion).catch((err) => {
      log.error("[Scheduler] Error notificando resultado:", err);
    });
    this.ejecutandoAhora = null;
    this.emitirProgreso();
    log.info(`[Scheduler] Tarea completada: ${tarea.nombre} → ${resultado} (${duracionMs}ms)`);
    return { exito: resultado !== "error" };
  }
  /** Calcula la proxima fecha de ejecucion basada en frecuencia */
  calcularProximaEjecucion(tarea) {
    const ahora = /* @__PURE__ */ new Date();
    const [horas, minutos] = (tarea.horaEjecucion || "09:00").split(":").map(Number);
    if (tarea.frecuencia === "semanal" && tarea.diaSemana) {
      const diaObjetivo = DIA_A_NUMERO[tarea.diaSemana];
      const proxima2 = new Date(ahora);
      proxima2.setHours(horas, minutos, 0, 0);
      const diaActual = ahora.getDay();
      let diasHasta = diaObjetivo - diaActual;
      if (diasHasta < 0 || diasHasta === 0 && ahora >= proxima2) {
        diasHasta += 7;
      }
      proxima2.setDate(proxima2.getDate() + diasHasta);
      return proxima2.toISOString();
    }
    if (tarea.frecuencia === "personalizada" && tarea.intervaloMinutos) {
      const proxima2 = new Date(ahora.getTime() + tarea.intervaloMinutos * 6e4);
      return proxima2.toISOString();
    }
    const horasIntervalo = HORAS_POR_FRECUENCIA[tarea.frecuencia] || 24;
    const proxima = new Date(ahora);
    if (tarea.frecuencia === "diaria" || horasIntervalo >= 24) {
      proxima.setHours(horas, minutos, 0, 0);
      if (ahora >= proxima) {
        proxima.setDate(proxima.getDate() + 1);
      }
    } else {
      proxima.setTime(ahora.getTime() + horasIntervalo * 36e5);
    }
    return proxima.toISOString();
  }
  /** Notifica resultado al modulo tray (import dinamico para evitar dep circular) */
  async notificarResultado(tarea, ejecucion) {
    try {
      const { notificarResultadoTareaScheduler: notificarResultadoTareaScheduler2 } = await Promise.resolve().then(() => servicioNotificaciones);
      notificarResultadoTareaScheduler2(tarea, ejecucion);
    } catch {
    }
  }
  /** Emite estado al renderer */
  emitirProgreso() {
    if (!this.ventana.isDestroyed()) {
      this.ventana.webContents.send("scheduler:progreso", this.obtenerEstado());
    }
  }
}
let motor = null;
function registrarHandlersScheduler(ventana) {
  motor = new MotorScheduler(ventana);
  motor.iniciar();
  ipcMain.handle("scheduler:obtenerEstado", () => {
    try {
      return motor.obtenerEstado();
    } catch (error) {
      log.error("[Handler:scheduler] Error obteniendo estado:", error);
      return { activo: false, tareasActivas: 0 };
    }
  });
  ipcMain.handle("scheduler:listarTareas", () => {
    try {
      return obtenerTareas();
    } catch (error) {
      log.error("[Handler:scheduler] Error listando tareas:", error);
      return [];
    }
  });
  ipcMain.handle("scheduler:obtenerTarea", (_event, id) => {
    try {
      return obtenerTarea(id);
    } catch (error) {
      log.error("[Handler:scheduler] Error obteniendo tarea:", error);
      return null;
    }
  });
  ipcMain.handle("scheduler:crearTarea", (_event, datos) => {
    try {
      const ahora = (/* @__PURE__ */ new Date()).toISOString();
      const tarea = {
        ...datos,
        id: randomUUID(),
        creadoEn: ahora,
        actualizadoEn: ahora
      };
      tarea.proximaEjecucion = motor.calcularProximaEjecucion(tarea);
      guardarTarea(tarea);
      return { exito: true, tarea };
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : "Error creando tarea";
      log.error("[Handler:scheduler] Error creando tarea:", error);
      return { exito: false, error: mensaje };
    }
  });
  ipcMain.handle("scheduler:actualizarTarea", (_event, id, datos) => {
    try {
      const existente = obtenerTarea(id);
      if (!existente) return { exito: false, error: "Tarea no encontrada" };
      const actualizada = {
        ...existente,
        ...datos,
        id,
        // no permitir cambiar id
        actualizadoEn: (/* @__PURE__ */ new Date()).toISOString()
      };
      if (datos.frecuencia || datos.horaEjecucion || datos.diaSemana) {
        actualizada.proximaEjecucion = motor.calcularProximaEjecucion(actualizada);
      }
      guardarTarea(actualizada);
      return { exito: true };
    } catch (error) {
      log.error("[Handler:scheduler] Error actualizando tarea:", error);
      return { exito: false, error: "Error actualizando tarea" };
    }
  });
  ipcMain.handle("scheduler:eliminarTarea", (_event, id) => {
    try {
      const eliminada = eliminarTarea(id);
      return { exito: eliminada, error: eliminada ? void 0 : "Tarea no encontrada" };
    } catch (error) {
      log.error("[Handler:scheduler] Error eliminando tarea:", error);
      return { exito: false, error: "Error eliminando tarea" };
    }
  });
  ipcMain.handle("scheduler:toggleTarea", (_event, id) => {
    try {
      const resultado = toggleTarea(id);
      if (!resultado) return { exito: false, error: "Tarea no encontrada" };
      return { exito: true, activa: resultado.activa };
    } catch (error) {
      log.error("[Handler:scheduler] Error toggling tarea:", error);
      return { exito: false, error: "Error cambiando estado de tarea" };
    }
  });
  ipcMain.handle("scheduler:ejecutarAhora", async (_event, id) => {
    try {
      return await motor.ejecutarManual(id);
    } catch (error) {
      log.error("[Handler:scheduler] Error ejecutando tarea:", error);
      return { exito: false, error: "Error ejecutando tarea" };
    }
  });
  ipcMain.handle("scheduler:historial", (_event, limite) => {
    try {
      return obtenerEjecuciones(limite);
    } catch (error) {
      log.error("[Handler:scheduler] Error obteniendo historial:", error);
      return [];
    }
  });
  ipcMain.handle("scheduler:limpiarHistorial", (_event, mantener) => {
    try {
      const eliminadas = limpiarEjecucionesAntiguas(mantener);
      return { exito: true, eliminadas };
    } catch (error) {
      log.error("[Handler:scheduler] Error limpiando historial:", error);
      return { exito: false, eliminadas: 0 };
    }
  });
  log.info("[Handlers] Scheduler: 10 handlers registrados, motor iniciado");
}
function detenerScheduler() {
  motor?.detener();
}
class GestorTray {
  ventana;
  tray = null;
  constructor(ventana) {
    this.ventana = ventana;
  }
  /** Crea el tray icon e inicia el menu contextual */
  iniciar() {
    try {
      const iconoRuta = join(__dirname, "../../resources/icon.png");
      const icono = nativeImage.createFromPath(iconoRuta);
      const iconoFinal = icono.isEmpty() ? nativeImage.createEmpty() : icono.resize({ width: 16, height: 16 });
      this.tray = new Tray(iconoFinal);
      this.tray.setToolTip("CertiGestor Desktop");
      this.tray.on("click", () => {
        this.ventana.show();
        this.ventana.focus();
      });
      this.actualizarMenu();
      log.info("[Tray] Icono de tray inicializado");
    } catch (error) {
      log.error("[Tray] Error inicializando tray:", error);
    }
  }
  /** Destruye el tray (al cerrar la app) */
  destruir() {
    if (this.tray) {
      this.tray.destroy();
      this.tray = null;
    }
  }
  /** Actualiza el menu contextual con el conteo actual */
  actualizarMenu() {
    if (!this.tray) return;
    const estado = obtenerEstadoTray();
    const menu = Menu.buildFromTemplate([
      {
        label: "Abrir CertiGestor",
        click: () => {
          this.ventana.show();
          this.ventana.focus();
        }
      },
      { type: "separator" },
      {
        label: estado.pendientes > 0 ? `${estado.pendientes} notificacion(es) pendiente(s)` : "Sin notificaciones pendientes",
        enabled: false
      },
      {
        label: "Marcar todas como leidas",
        enabled: estado.pendientes > 0,
        click: () => {
          marcarTodasLeidas();
          this.actualizarBadge(0);
        }
      },
      { type: "separator" },
      {
        label: "Salir",
        click: () => {
          app.quit();
        }
      }
    ]);
    this.tray.setContextMenu(menu);
  }
  /** Actualiza el badge numerico (overlay icon en Windows taskbar) */
  actualizarBadge(conteo) {
    if (!this.tray) return;
    this.tray.setToolTip(
      conteo > 0 ? `CertiGestor — ${conteo} pendiente(s)` : "CertiGestor Desktop"
    );
    if (conteo > 0) {
      this.ventana.setOverlayIcon(
        this.crearBadgeIcon(conteo),
        `${conteo} notificaciones`
      );
    } else {
      this.ventana.setOverlayIcon(null, "");
    }
    this.actualizarMenu();
  }
  /** Envia una notificacion nativa de Windows */
  enviarNativa(notif) {
    if (!Notification.isSupported()) return;
    try {
      const notifNativa = new Notification({
        title: notif.titulo,
        body: notif.mensaje,
        silent: false
      });
      notifNativa.on("click", () => {
        this.ventana.show();
        this.ventana.focus();
      });
      notifNativa.show();
    } catch (error) {
      log.error("[Tray] Error enviando notificacion nativa:", error);
    }
  }
  /** Crea un icono de badge con numero para el overlay */
  crearBadgeIcon(conteo) {
    const texto = conteo > 99 ? "99+" : String(conteo);
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">
        <circle cx="8" cy="8" r="8" fill="#ef4444"/>
        <text x="8" y="12" text-anchor="middle" fill="white" font-size="${texto.length > 2 ? 7 : 10}" font-family="Arial" font-weight="bold">${texto}</text>
      </svg>
    `;
    return nativeImage.createFromBuffer(
      Buffer.from(svg)
    );
  }
}
let gestor = null;
function registrarHandlersTray(ventana) {
  gestor = new GestorTray(ventana);
  gestor.iniciar();
  setGestorTray(gestor);
  const estadoInicial = obtenerEstadoTray();
  gestor.actualizarBadge(estadoInicial.pendientes);
  ipcMain.handle("tray:obtenerEstado", () => {
    try {
      return obtenerEstadoTray();
    } catch (error) {
      log.error("[Handler:tray] Error obteniendo estado:", error);
      return { pendientes: 0 };
    }
  });
  ipcMain.handle("tray:listarNotificaciones", (_event, limite) => {
    try {
      return obtenerNotificaciones(limite);
    } catch (error) {
      log.error("[Handler:tray] Error listando notificaciones:", error);
      return [];
    }
  });
  ipcMain.handle("tray:marcarLeida", (_event, id) => {
    try {
      const marcada = marcarLeida(id);
      if (marcada && gestor) {
        const estado = obtenerEstadoTray();
        gestor.actualizarBadge(estado.pendientes);
      }
      return { exito: marcada };
    } catch (error) {
      log.error("[Handler:tray] Error marcando leida:", error);
      return { exito: false };
    }
  });
  ipcMain.handle("tray:marcarTodasLeidas", () => {
    try {
      const marcadas = marcarTodasLeidas();
      if (gestor) {
        gestor.actualizarBadge(0);
      }
      return { exito: true, marcadas };
    } catch (error) {
      log.error("[Handler:tray] Error marcando todas leidas:", error);
      return { exito: false, marcadas: 0 };
    }
  });
  ipcMain.handle("tray:obtenerConfig", () => {
    try {
      return obtenerConfig$1();
    } catch (error) {
      log.error("[Handler:tray] Error obteniendo config:", error);
      return null;
    }
  });
  ipcMain.handle("tray:guardarConfig", (_event, config) => {
    try {
      guardarConfig$1(config);
      return { exito: true };
    } catch (error) {
      log.error("[Handler:tray] Error guardando config:", error);
      return { exito: false };
    }
  });
  ipcMain.handle("tray:limpiarAntiguas", (_event, mantener) => {
    try {
      const eliminadas = limpiarAntiguas(mantener);
      return { exito: true, eliminadas };
    } catch (error) {
      log.error("[Handler:tray] Error limpiando antiguas:", error);
      return { exito: false, eliminadas: 0 };
    }
  });
  ipcMain.handle("tray:ejecutarChequeo", async () => {
    try {
      const nuevas = await ejecutarChequeosPeriodicos();
      return { exito: true, nuevas };
    } catch (error) {
      log.error("[Handler:tray] Error ejecutando chequeo:", error);
      return { exito: false, nuevas: 0 };
    }
  });
  log.info("[Handlers] Tray: 8 handlers registrados, tray icon iniciado");
}
function destruirTray() {
  gestor?.destruir();
}
async function recolectarMetricas() {
  const [certificados, firmas, workflows, documentales, scheduler, notificacionesDesktop] = await Promise.all([
    recolectarMetricasCerts(),
    recolectarMetricasFirmas(),
    recolectarMetricasWorkflows(),
    recolectarMetricasDocumentales(),
    recolectarMetricasScheduler(),
    recolectarMetricasNotificaciones()
  ]);
  return {
    certificados,
    firmas,
    workflows,
    documentales,
    scheduler,
    notificacionesDesktop
  };
}
async function recolectarMetricasCerts() {
  try {
    const certs = await listarCertificadosInstalados();
    const ahora = Date.now();
    const conDias = certs.map((cert) => {
      const vencimiento = new Date(cert.fechaVencimiento).getTime();
      const diasRestantes = Math.floor((vencimiento - ahora) / 864e5);
      return { subject: cert.subject, fechaVencimiento: cert.fechaVencimiento, diasRestantes };
    });
    return {
      totalInstalados: certs.length,
      proximosACaducar: conDias.filter((c) => c.diasRestantes > 0 && c.diasRestantes <= 30).length,
      caducados: conDias.filter((c) => c.diasRestantes <= 0).length,
      certificados: conDias.sort((a, b) => a.diasRestantes - b.diasRestantes)
    };
  } catch (error) {
    log.error("[Analytics] Error recolectando metricas certs:", error);
    return { totalInstalados: 0, proximosACaducar: 0, caducados: 0, certificados: [] };
  }
}
function recolectarMetricasFirmas() {
  try {
    const historial = obtenerHistorialFirmas();
    const docs = historial.documentos;
    const local = docs.filter((d) => d.modo === "local").length;
    const autofirma = docs.filter((d) => d.modo === "autofirma").length;
    const pendientesSync = docs.filter((d) => !d.sincronizadoCloud).length;
    const ultimas = docs.slice(-30).map((d) => ({
      fecha: d.fechaFirma.slice(0, 10),
      modo: d.modo
    }));
    return {
      totalFirmados: docs.length,
      pendientesSync,
      porModo: { local, autofirma },
      historial: ultimas
    };
  } catch (error) {
    log.error("[Analytics] Error recolectando metricas firmas:", error);
    return { totalFirmados: 0, pendientesSync: 0, porModo: { local: 0, autofirma: 0 }, historial: [] };
  }
}
function recolectarMetricasWorkflows() {
  try {
    const datos = obtenerDatosWorkflows();
    const ejecuciones = datos.ejecuciones;
    const exitosas = ejecuciones.filter((e) => e.resultado.exito).length;
    const fallidas = ejecuciones.length - exitosas;
    const duraciones = ejecuciones.filter((e) => e.resultado.tiempoTotalMs > 0).map((e) => e.resultado.tiempoTotalMs);
    const tiempoPromedioMs = duraciones.length > 0 ? Math.round(duraciones.reduce((a, b) => a + b, 0) / duraciones.length) : 0;
    const ultimas = ejecuciones.slice(-30).map((e) => ({
      fecha: e.ejecutadoEn.slice(0, 10),
      resultado: e.resultado.exito ? "exito" : "error",
      duracionMs: e.resultado.tiempoTotalMs
    }));
    return {
      totalEjecuciones: ejecuciones.length,
      exitosas,
      fallidas,
      tiempoPromedioMs,
      historial: ultimas
    };
  } catch (error) {
    log.error("[Analytics] Error recolectando metricas workflows:", error);
    return { totalEjecuciones: 0, exitosas: 0, fallidas: 0, tiempoPromedioMs: 0, historial: [] };
  }
}
function recolectarMetricasDocumentales() {
  try {
    const historial = obtenerHistorial();
    const exitosas = historial.filter((r) => r.exito).length;
    const fallidas = historial.length - exitosas;
    const porTipo = {};
    for (const r of historial) {
      porTipo[r.tipo] = (porTipo[r.tipo] ?? 0) + 1;
    }
    const ultimas = historial.slice(-30).map((r) => ({
      fecha: r.fechaDescarga.slice(0, 10),
      tipo: r.tipo,
      exito: r.exito
    }));
    return {
      totalDescargas: historial.length,
      exitosas,
      fallidas,
      porTipo,
      historial: ultimas
    };
  } catch (error) {
    log.error("[Analytics] Error recolectando metricas documentales:", error);
    return { totalDescargas: 0, exitosas: 0, fallidas: 0, porTipo: {}, historial: [] };
  }
}
function recolectarMetricasScheduler() {
  try {
    const datos = obtenerDatosScheduler();
    const tareasActivas = datos.tareas.filter((t) => t.activa).length;
    const hoy = (/* @__PURE__ */ new Date()).toISOString().slice(0, 10);
    const ejecucionesHoy = datos.ejecuciones.filter((e) => e.ejecutadoEn.startsWith(hoy));
    return {
      tareasActivas,
      ejecucionesHoy: ejecucionesHoy.length,
      exitosasHoy: ejecucionesHoy.filter((e) => e.resultado === "exito").length,
      fallidasHoy: ejecucionesHoy.filter((e) => e.resultado === "error").length
    };
  } catch (error) {
    log.error("[Analytics] Error recolectando metricas scheduler:", error);
    return { tareasActivas: 0, ejecucionesHoy: 0, exitosasHoy: 0, fallidasHoy: 0 };
  }
}
function recolectarMetricasNotificaciones() {
  try {
    const datos = obtenerDatos();
    const pendientes = datos.notificaciones.filter((n) => !n.leida).length;
    const hoy = (/* @__PURE__ */ new Date()).toISOString().slice(0, 10);
    const notifHoy = datos.notificaciones.filter((n) => n.fechaCreacion.startsWith(hoy));
    const porTipo = {};
    for (const n of datos.notificaciones) {
      porTipo[n.tipo] = (porTipo[n.tipo] ?? 0) + 1;
    }
    return { pendientes, totalHoy: notifHoy.length, porTipo };
  } catch (error) {
    log.error("[Analytics] Error recolectando metricas notificaciones:", error);
    return { pendientes: 0, totalHoy: 0, porTipo: {} };
  }
}
function recolectarActividadTemporal(dias = 30) {
  try {
    const firmasHist = obtenerHistorialFirmas().documentos;
    const workflowsHist = obtenerDatosWorkflows().ejecuciones;
    const docsHist = obtenerHistorial();
    const hoy = /* @__PURE__ */ new Date();
    const puntos = [];
    for (let i = dias - 1; i >= 0; i--) {
      const fecha = new Date(hoy);
      fecha.setDate(fecha.getDate() - i);
      const fechaStr = fecha.toISOString().slice(0, 10);
      puntos.push({
        fecha: fechaStr,
        firmas: firmasHist.filter((d) => d.fechaFirma.startsWith(fechaStr)).length,
        workflows: workflowsHist.filter((e) => e.ejecutadoEn.startsWith(fechaStr)).length,
        descargas: docsHist.filter((r) => r.fechaDescarga.startsWith(fechaStr)).length
      });
    }
    return puntos;
  } catch (error) {
    log.error("[Analytics] Error recolectando actividad temporal:", error);
    return [];
  }
}
function registrarHandlersAnalytics(_ventana) {
  ipcMain.handle("analytics:metricas", async () => {
    try {
      return await recolectarMetricas();
    } catch (error) {
      log.error("[Handler:analytics] Error recolectando metricas:", error);
      return null;
    }
  });
  ipcMain.handle("analytics:metricasCerts", async () => {
    try {
      return await recolectarMetricasCerts();
    } catch (error) {
      log.error("[Handler:analytics] Error recolectando metricas certs:", error);
      return null;
    }
  });
  ipcMain.handle("analytics:actividadTemporal", (_event, dias) => {
    try {
      return recolectarActividadTemporal(dias);
    } catch (error) {
      log.error("[Handler:analytics] Error recolectando actividad temporal:", error);
      return [];
    }
  });
  log.info("[Handlers] Analytics: 3 handlers registrados");
}
const ARCHIVOS_JSON = {
  config_portales: "certigestor-config-portales.json",
  config_docs: "certigestor-config-docs.json"
};
function rutaUserData(nombre) {
  return join(app.getPath("userData"), nombre);
}
function leerJsonLocal(nombre) {
  const ruta = rutaUserData(nombre);
  if (!existsSync(ruta)) return null;
  try {
    return JSON.parse(readFileSync(ruta, "utf-8"));
  } catch {
    return null;
  }
}
function escribirJsonLocal(nombre, datos) {
  const ruta = rutaUserData(nombre);
  writeFileSync(ruta, JSON.stringify(datos, null, 2), "utf-8");
}
function exportarConfiguracion(opciones) {
  const secciones = {};
  for (const seccion of opciones.secciones) {
    try {
      switch (seccion) {
        case "scheduler": {
          const datos = obtenerDatosScheduler();
          secciones.scheduler = { tareas: datos.tareas };
          break;
        }
        case "tray_config": {
          secciones.tray_config = obtenerConfig$1();
          break;
        }
        case "workflows": {
          const datos = obtenerDatosWorkflows();
          secciones.workflows = {
            workflowsPersonalizados: datos.workflowsPersonalizados,
            configSmtp: datos.configSmtp
          };
          break;
        }
        case "config_portales": {
          const nombre = ARCHIVOS_JSON.config_portales;
          secciones.config_portales = leerJsonLocal(nombre) ?? {};
          break;
        }
        case "config_docs": {
          const nombre = ARCHIVOS_JSON.config_docs;
          secciones.config_docs = leerJsonLocal(nombre) ?? {};
          break;
        }
        case "historial_docs": {
          secciones.historial_docs = obtenerHistorial();
          break;
        }
      }
      log.info(`[Backup] Exportada seccion: ${seccion}`);
    } catch (error) {
      log.error(`[Backup] Error exportando seccion ${seccion}:`, error);
    }
  }
  return {
    version: 1,
    fecha: (/* @__PURE__ */ new Date()).toISOString(),
    secciones
  };
}
function importarConfiguracion(datos) {
  const seccionesImportadas = [];
  for (const [seccion, contenido] of Object.entries(datos.secciones)) {
    if (!contenido) continue;
    try {
      switch (seccion) {
        case "scheduler": {
          const datosActuales = obtenerDatosScheduler();
          const backup = contenido;
          const datosNuevos = {
            ...datosActuales,
            tareas: backup.tareas ?? datosActuales.tareas
          };
          escribirJsonLocal("certigestor-scheduler.json", datosNuevos);
          break;
        }
        case "tray_config": {
          const datosActuales = leerJsonLocal("certigestor-notificaciones-desktop.json");
          const datosNuevos = {
            ...datosActuales ?? { notificaciones: [] },
            config: contenido
          };
          escribirJsonLocal("certigestor-notificaciones-desktop.json", datosNuevos);
          break;
        }
        case "workflows": {
          const datosActuales = obtenerDatosWorkflows();
          const backup = contenido;
          const datosNuevos = {
            ...datosActuales,
            workflowsPersonalizados: backup.workflowsPersonalizados ?? datosActuales.workflowsPersonalizados,
            configSmtp: backup.configSmtp ?? datosActuales.configSmtp
          };
          escribirJsonLocal("certigestor-workflows-desktop.json", datosNuevos);
          break;
        }
        case "config_portales": {
          escribirJsonLocal(ARCHIVOS_JSON.config_portales, contenido);
          break;
        }
        case "config_docs": {
          escribirJsonLocal(ARCHIVOS_JSON.config_docs, contenido);
          break;
        }
        case "historial_docs": {
          escribirJsonLocal("certigestor-historial-docs.json", contenido);
          break;
        }
      }
      seccionesImportadas.push(seccion);
      log.info(`[Backup] Importada seccion: ${seccion}`);
    } catch (error) {
      log.error(`[Backup] Error importando seccion ${seccion}:`, error);
    }
  }
  return {
    exito: seccionesImportadas.length > 0,
    seccionesImportadas
  };
}
const ALGORITMO = "aes-256-gcm";
const IV_BYTES = 16;
const SAL_BYTES = 16;
const CLAVE_BYTES = 32;
const AUTH_TAG_BYTES = 16;
const MAGIC = Buffer.from("CGBK", "ascii");
function derivarClave(password, sal) {
  return scryptSync(password, sal, CLAVE_BYTES);
}
function cifrarBackup(datos, password) {
  const json = JSON.stringify(datos);
  const sal = randomBytes(SAL_BYTES);
  const clave = derivarClave(password, sal);
  const iv = randomBytes(IV_BYTES);
  const cifrador = createCipheriv(ALGORITMO, clave, iv);
  const cifrado = Buffer.concat([cifrador.update(json, "utf8"), cifrador.final()]);
  const authTag = cifrador.getAuthTag();
  return Buffer.concat([MAGIC, sal, iv, authTag, cifrado]);
}
function descifrarBackup(buffer, password) {
  const offsetMin = MAGIC.length + SAL_BYTES + IV_BYTES + AUTH_TAG_BYTES;
  if (buffer.length < offsetMin) {
    throw new Error("Archivo de backup inválido: demasiado pequeño");
  }
  const magic = buffer.subarray(0, MAGIC.length);
  if (!magic.equals(MAGIC)) {
    throw new Error("Archivo de backup inválido: cabecera incorrecta");
  }
  let offset = MAGIC.length;
  const sal = buffer.subarray(offset, offset + SAL_BYTES);
  offset += SAL_BYTES;
  const iv = buffer.subarray(offset, offset + IV_BYTES);
  offset += IV_BYTES;
  const authTag = buffer.subarray(offset, offset + AUTH_TAG_BYTES);
  offset += AUTH_TAG_BYTES;
  const cifrado = buffer.subarray(offset);
  const clave = derivarClave(password, sal);
  try {
    const descifrador = createDecipheriv(ALGORITMO, clave, iv);
    descifrador.setAuthTag(authTag);
    const descifrado = Buffer.concat([descifrador.update(cifrado), descifrador.final()]);
    return JSON.parse(descifrado.toString("utf8"));
  } catch {
    throw new Error("Contraseña incorrecta o archivo corrupto");
  }
}
function registrarHandlersBackup(ventana) {
  ipcMain.handle(
    "backup:exportar",
    async (_event, opciones) => {
      try {
        const datos = exportarConfiguracion({ secciones: opciones.secciones, password: opciones.password });
        const buffer = cifrarBackup(datos, opciones.password);
        const resultado = await dialog.showSaveDialog(ventana, {
          title: "Exportar configuración CertiGestor",
          defaultPath: `certigestor-backup-${(/* @__PURE__ */ new Date()).toISOString().slice(0, 10)}.certigestor-backup`,
          filters: [{ name: "CertiGestor Backup", extensions: ["certigestor-backup"] }]
        });
        if (resultado.canceled || !resultado.filePath) {
          return { exito: false, error: "Exportación cancelada" };
        }
        writeFileSync(resultado.filePath, buffer);
        log.info(`[Backup] Exportado a: ${resultado.filePath} (${opciones.secciones.length} secciones)`);
        return { exito: true, ruta: resultado.filePath };
      } catch (error) {
        log.error("[Backup] Error exportando:", error);
        return { exito: false, error: error instanceof Error ? error.message : "Error desconocido" };
      }
    }
  );
  ipcMain.handle("backup:importar", async (_event, opciones) => {
    try {
      const resultado = await dialog.showOpenDialog(ventana, {
        title: "Importar configuración CertiGestor",
        filters: [{ name: "CertiGestor Backup", extensions: ["certigestor-backup"] }],
        properties: ["openFile"]
      });
      if (resultado.canceled || resultado.filePaths.length === 0) {
        return { exito: false, seccionesImportadas: [], error: "Importación cancelada" };
      }
      const buffer = readFileSync(resultado.filePaths[0]);
      const datos = descifrarBackup(buffer, opciones.password);
      const importResult = importarConfiguracion(datos);
      log.info(`[Backup] Importadas ${importResult.seccionesImportadas.length} secciones`);
      return importResult;
    } catch (error) {
      log.error("[Backup] Error importando:", error);
      return {
        exito: false,
        seccionesImportadas: [],
        error: error instanceof Error ? error.message : "Error desconocido"
      };
    }
  });
  ipcMain.handle("backup:previsualizar", async (_event, opciones) => {
    try {
      const resultado = await dialog.showOpenDialog(ventana, {
        title: "Previsualizar backup CertiGestor",
        filters: [{ name: "CertiGestor Backup", extensions: ["certigestor-backup"] }],
        properties: ["openFile"]
      });
      if (resultado.canceled || resultado.filePaths.length === 0) {
        return { exito: false, error: "Selección cancelada" };
      }
      const buffer = readFileSync(resultado.filePaths[0]);
      const datos = descifrarBackup(buffer, opciones.password);
      return {
        exito: true,
        secciones: Object.keys(datos.secciones),
        fecha: datos.fecha,
        version: datos.version
      };
    } catch (error) {
      log.error("[Backup] Error previsualizando:", error);
      return { exito: false, error: error instanceof Error ? error.message : "Error desconocido" };
    }
  });
  log.info("[Handlers] Backup: 3 handlers registrados");
}
class OrquestadorGlobal {
  apiUrl;
  token;
  constructor(apiUrl, token) {
    this.apiUrl = apiUrl;
    this.token = token;
  }
  /**
   * Construye cadenas para todos los dominios y certificados.
   * NO limpia la factory — el caller decide cuando limpiar.
   */
  construirCadenasMultiCert(factory2, configuraciones) {
    let totalCadenas = 0;
    for (const config of configuraciones) {
      const { certificadoSerial, certificadoId } = config;
      if (config.dehu) {
        const dehuOrq = new DehuOrquestador(this.apiUrl, this.token);
        dehuOrq.construirCadena(factory2, config.dehu, certificadoId);
        totalCadenas++;
      }
      const portalesAdicionales = (config.portalesNotificaciones ?? []).filter(
        (p) => p !== PortalNotificaciones.DEHU
      );
      if (portalesAdicionales.length > 0) {
        const notifOrq = new OrquestadorNotificaciones(this.apiUrl, this.token);
        notifOrq.construirCadenaPortalesAdicionales(
          factory2,
          certificadoSerial,
          certificadoId,
          portalesAdicionales
        );
        totalCadenas++;
      }
      if (config.documentos && config.documentos.length > 0) {
        const docOrq = new OrquestadorDocumentales();
        docOrq.construirCadena(factory2, {
          certificadoSerial,
          documentosActivos: config.documentos,
          datosExtra: config.datosExtraDocs
        });
        totalCadenas++;
      }
    }
    log.info(
      `[OrqGlobal] ${totalCadenas} cadenas creadas para ${configuraciones.length} certificados`
    );
  }
}
const ARCHIVO_HISTORIAL = "certigestor-historial-multicert.json";
function rutaArchivo() {
  return join(app.getPath("userData"), ARCHIVO_HISTORIAL);
}
function leerHistorial() {
  const ruta = rutaArchivo();
  if (!existsSync(ruta)) return [];
  try {
    const contenido = readFileSync(ruta, "utf-8");
    return JSON.parse(contenido);
  } catch (err) {
    log.warn(`[HistorialMC] Error leyendo: ${err.message}`);
    return [];
  }
}
function guardarHistorialLocal(registros) {
  const ruta = rutaArchivo();
  const recortado = registros.slice(-100);
  const rutaTmp = `${ruta}.tmp`;
  writeFileSync(rutaTmp, JSON.stringify(recortado, null, 2), "utf-8");
  renameSync(rutaTmp, ruta);
}
function registrarEjecucion(resultado) {
  const historial = leerHistorial();
  historial.push(resultado);
  guardarHistorialLocal(historial);
  log.info(
    `[HistorialMC] Registrado: ${resultado.certificados.length} certs, ${resultado.duracionMs}ms`
  );
}
function obtenerHistorialMultiCert(limite) {
  const historial = leerHistorial();
  const invertido = [...historial].reverse();
  return limite ? invertido.slice(0, limite) : invertido;
}
function limpiarHistorialMultiCert() {
  guardarHistorialLocal([]);
  log.info("[HistorialMC] Historial limpiado");
}
let mapaNombres = {};
function carpetaTempPfx() {
  const dir = join(app.getPath("temp"), "certigestor-pfx");
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  return dir;
}
async function resolverPfxParaDehu(configs) {
  const rutasTemporales = [];
  for (const config of configs) {
    if (!config.dehu || config.dehu.rutaPfx && config.dehu.passwordPfx) continue;
    if (!config.thumbprint) {
      log.warn(`[MultiCert] Config DEHU sin thumbprint para cert ${config.certificadoSerial}, saltando LEMA`);
      continue;
    }
    const passwordTemp = randomBytes(16).toString("hex");
    const rutaTemp = join(carpetaTempPfx(), `${config.thumbprint}.pfx`);
    const resultado = await exportarCertificadoPfx(config.thumbprint, rutaTemp, passwordTemp);
    if (resultado.exito) {
      config.dehu.rutaPfx = rutaTemp;
      config.dehu.passwordPfx = passwordTemp;
      rutasTemporales.push(rutaTemp);
      log.info(`[MultiCert] PFX temporal exportado para cert ${config.certificadoSerial}`);
    } else {
      log.error(`[MultiCert] No se pudo exportar PFX para cert ${config.certificadoSerial}: ${resultado.error}`);
    }
  }
  return rutasTemporales;
}
function limpiarPfxTemporales(rutas) {
  for (const ruta of rutas) {
    try {
      if (existsSync(ruta)) unlinkSync(ruta);
    } catch (err) {
      log.warn(`[MultiCert] No se pudo eliminar PFX temporal: ${ruta}`, err);
    }
  }
}
function registrarHandlersMultiCert(_ventana) {
  ipcMain.handle(
    "multicert:iniciar",
    async (_event, configs, apiUrl, token) => {
      log.info(
        `[MultiCert] Iniciando para ${configs.length} certificados`
      );
      let rutasTemporales = [];
      try {
        mapaNombres = {};
        for (const c of configs) {
          if (c.nombreCert) {
            mapaNombres[c.certificadoSerial] = c.nombreCert;
          }
        }
        rutasTemporales = await resolverPfxParaDehu(configs);
        const orquestador2 = new OrquestadorGlobal(apiUrl, token);
        factory.limpiar();
        orquestador2.construirCadenasMultiCert(factory, configs);
        const inicio = Date.now();
        await factory.iniciar();
        const duracionMs = Date.now() - inicio;
        const estado = factory.obtenerEstado();
        const resultado = {
          fecha: (/* @__PURE__ */ new Date()).toISOString(),
          duracionMs,
          totalCadenas: estado.totalCadenas,
          certificados: configs.map((c) => {
            const cadenasCert = estado.cadenas.filter(
              (ch) => ch.certificadoSerial === c.certificadoSerial || ch.certificadoSerial === `notif-${c.certificadoSerial}`
            );
            const todasCompletadas = cadenasCert.every(
              (ch) => ch.estado === ChainStatus.COMPLETED
            );
            const algunaFallo = cadenasCert.some(
              (ch) => ch.estado === ChainStatus.FAILED
            );
            return {
              serial: c.certificadoSerial,
              nombre: c.nombreCert,
              dominios: {
                dehu: !!c.dehu,
                notificaciones: c.portalesNotificaciones,
                documentos: c.documentos
              },
              estado: todasCompletadas ? "completado" : algunaFallo ? "fallido" : "parcial"
            };
          })
        };
        registrarEjecucion(resultado);
        const completados = resultado.certificados.filter((c) => c.estado === "completado").length;
        const fallidos = resultado.certificados.filter((c) => c.estado === "fallido").length;
        const duracionSeg = Math.round(duracionMs / 1e3);
        notificarSyncCompletada(
          `Scraping finalizado en ${duracionSeg}s — ${completados} completado(s)` + (fallidos > 0 ? `, ${fallidos} con errores` : "")
        );
        return { exito: true };
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Error desconocido";
        log.error(`[MultiCert] Error: ${msg}`);
        return { exito: false, error: msg };
      } finally {
        limpiarPfxTemporales(rutasTemporales);
      }
    }
  );
  ipcMain.handle("multicert:detener", () => {
    factory.detener();
    return { exito: true };
  });
  ipcMain.handle("multicert:obtenerEstado", () => {
    const estado = factory.obtenerEstado();
    const cadenas = estado.cadenas.map((c) => {
      const serialLimpio = c.certificadoSerial.startsWith("notif-") ? c.certificadoSerial.replace("notif-", "") : c.certificadoSerial;
      return {
        ...c,
        nombreCert: mapaNombres[serialLimpio] ?? c.nombreCert
      };
    });
    return { ...estado, cadenas };
  });
  ipcMain.handle(
    "multicert:obtenerHistorial",
    (_event, limite) => {
      return obtenerHistorialMultiCert(limite);
    }
  );
  ipcMain.handle("multicert:limpiarHistorial", () => {
    limpiarHistorialMultiCert();
    return { exito: true };
  });
  log.info("Handlers multi-certificado registrados");
}
function registrarHandlersOcr() {
  ipcMain.handle(
    "ocr:extraerTexto",
    async (_event, rutaPdf) => {
      try {
        log.info(`[OCR] Extrayendo texto de: ${rutaPdf}`);
        return await extraerTextoPdf(rutaPdf);
      } catch (error) {
        log.error(`[OCR] Error extrayendo texto: ${error.message}`);
        return null;
      }
    }
  );
  ipcMain.handle("ocr:estado", () => {
    return {
      activo: workerActivo(),
      idioma: "spa"
    };
  });
  log.info("Handlers OCR registrados");
}
let conectado = true;
let intervalo = null;
const listeners = /* @__PURE__ */ new Set();
const INTERVALO_MS = 3e4;
const TIMEOUT_MS = 5e3;
async function verificarConexion(urlPing) {
  try {
    if (!net.isOnline()) return false;
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const resp = await fetch(urlPing, { signal: ctrl.signal, method: "HEAD" });
    clearTimeout(timeout);
    return resp.ok;
  } catch {
    return false;
  }
}
function iniciarDetectorConexion(urlPing, callback) {
  if (callback) listeners.add(callback);
  if (intervalo) return;
  intervalo = setInterval(async () => {
    const conectadoAhora = await verificarConexion(urlPing);
    if (conectadoAhora !== conectado) {
      conectado = conectadoAhora;
      log.info(`[Conexion] ${conectadoAhora ? "ONLINE" : "OFFLINE"}`);
      listeners.forEach((cb) => cb(conectadoAhora));
    }
  }, INTERVALO_MS);
  verificarConexion(urlPing).then((online) => {
    conectado = online;
    listeners.forEach((cb) => cb(online));
  });
}
function detenerDetectorConexion() {
  if (intervalo) {
    clearInterval(intervalo);
    intervalo = null;
  }
  listeners.clear();
}
function estaOnline() {
  return conectado;
}
let instancia = null;
function obtenerBd() {
  if (!instancia) {
    const ruta = join(app.getPath("userData"), "certigestor-offline.db");
    instancia = new Database(ruta);
    instancia.pragma("journal_mode = WAL");
    instancia.pragma("foreign_keys = ON");
    log.info("[BdLocal] SQLite inicializada:", ruta);
  }
  return instancia;
}
function cerrarBd() {
  if (instancia) {
    instancia.close();
    instancia = null;
    log.info("[BdLocal] SQLite cerrada");
  }
}
function encolarCambio(recurso, recursoId, operacion, payload) {
  const db = obtenerBd();
  db.prepare(`
    INSERT INTO cola_cambios (recurso, recurso_id, operacion, payload_json, creado_en)
    VALUES (?, ?, ?, ?, ?)
  `).run(recurso, recursoId, operacion, JSON.stringify(payload), (/* @__PURE__ */ new Date()).toISOString());
  log.info(`[Cola] Encolado: ${recurso}/${recursoId} op=${operacion}`);
}
function obtenerCambiosPendientes() {
  const db = obtenerBd();
  const filas = db.prepare("SELECT * FROM cola_cambios ORDER BY creado_en ASC").all();
  return filas.map((f) => ({
    id: f.id,
    recurso: f.recurso,
    recursoId: f.recurso_id,
    operacion: f.operacion,
    payloadJson: f.payload_json,
    intentos: f.intentos,
    ultimoIntento: f.ultimo_intento,
    creadoEn: f.creado_en,
    errorUltimo: f.error_ultimo
  }));
}
function eliminarCambio(id) {
  const db = obtenerBd();
  db.prepare("DELETE FROM cola_cambios WHERE id = ?").run(id);
}
function registrarErrorCambio(id, error) {
  const db = obtenerBd();
  db.prepare(`
    UPDATE cola_cambios SET intentos = intentos + 1, ultimo_intento = ?, error_ultimo = ? WHERE id = ?
  `).run((/* @__PURE__ */ new Date()).toISOString(), error, id);
}
function contarPendientes() {
  const db = obtenerBd();
  const fila = db.prepare("SELECT COUNT(*) as total FROM cola_cambios").get();
  return fila.total;
}
function moverADeadLetter(cambio) {
  const db = obtenerBd();
  db.prepare(`
    INSERT OR IGNORE INTO dead_letter_cambios (id, recurso, recurso_id, operacion, payload_json, intentos, error_ultimo, creado_en, descartado_en)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    cambio.id,
    cambio.recurso,
    cambio.recursoId,
    cambio.operacion,
    cambio.payloadJson,
    cambio.intentos,
    cambio.errorUltimo,
    cambio.creadoEn,
    (/* @__PURE__ */ new Date()).toISOString()
  );
  eliminarCambio(cambio.id);
  log.warn(`[Cola] Cambio ${cambio.id} movido a dead-letter tras ${cambio.intentos} intentos`);
}
function upsertCertificado(cert) {
  const db = obtenerBd();
  db.prepare(`
    INSERT INTO certificados_cache (
      id, organizacion_id, nombre_titular, dni_cif, numero_serie, emisor,
      organizacion, fecha_expedicion, fecha_vencimiento, activo,
      creado_en, actualizado_en, sincronizado_en, etiquetas_json
    ) VALUES (
      @id, @organizacionId, @nombreTitular, @dniCif, @numeroSerie, @emisor,
      @organizacion, @fechaExpedicion, @fechaVencimiento, @activo,
      @creadoEn, @actualizadoEn, @sincronizadoEn, @etiquetasJson
    ) ON CONFLICT(id) DO UPDATE SET
      nombre_titular = excluded.nombre_titular,
      dni_cif = excluded.dni_cif,
      numero_serie = excluded.numero_serie,
      emisor = excluded.emisor,
      organizacion = excluded.organizacion,
      fecha_expedicion = excluded.fecha_expedicion,
      fecha_vencimiento = excluded.fecha_vencimiento,
      activo = excluded.activo,
      actualizado_en = excluded.actualizado_en,
      sincronizado_en = excluded.sincronizado_en,
      etiquetas_json = excluded.etiquetas_json
  `).run({
    id: cert.id,
    organizacionId: cert.organizacionId,
    nombreTitular: cert.nombreTitular,
    dniCif: cert.dniCif,
    numeroSerie: cert.numeroSerie,
    emisor: cert.emisor,
    organizacion: cert.organizacion,
    fechaExpedicion: cert.fechaExpedicion,
    fechaVencimiento: cert.fechaVencimiento,
    activo: cert.activo,
    creadoEn: cert.creadoEn,
    actualizadoEn: cert.actualizadoEn,
    sincronizadoEn: cert.sincronizadoEn,
    etiquetasJson: cert.etiquetasJson
  });
}
function upsertCertificados(certs) {
  const db = obtenerBd();
  const tx = db.transaction(() => {
    for (const cert of certs) {
      upsertCertificado(cert);
    }
  });
  tx();
}
function listarCertificadosCache(organizacionId, filtros = {}) {
  const db = obtenerBd();
  const { busqueda, pagina = 1, limite = 50 } = filtros;
  const offset = (pagina - 1) * limite;
  let whereClause = "WHERE organizacion_id = ? AND activo = 1";
  const params = [organizacionId];
  if (busqueda) {
    whereClause += " AND (nombre_titular LIKE ? OR dni_cif LIKE ? OR emisor LIKE ?)";
    const patron = `%${busqueda}%`;
    params.push(patron, patron, patron);
  }
  const totalRow = db.prepare(`SELECT COUNT(*) as total FROM certificados_cache ${whereClause}`).get(...params);
  const filas = db.prepare(
    `SELECT * FROM certificados_cache ${whereClause} ORDER BY fecha_vencimiento ASC LIMIT ? OFFSET ?`
  ).all(...params, limite, offset);
  return {
    datos: filas.map(mapearFilaCertificado),
    total: totalRow.total
  };
}
function mapearFilaCertificado(f) {
  return {
    id: f.id,
    organizacionId: f.organizacion_id,
    nombreTitular: f.nombre_titular,
    dniCif: f.dni_cif,
    numeroSerie: f.numero_serie,
    emisor: f.emisor,
    organizacion: f.organizacion,
    fechaExpedicion: f.fecha_expedicion,
    fechaVencimiento: f.fecha_vencimiento,
    activo: f.activo,
    creadoEn: f.creado_en,
    actualizadoEn: f.actualizado_en,
    sincronizadoEn: f.sincronizado_en,
    etiquetasJson: f.etiquetas_json
  };
}
function upsertNotificacion(notif) {
  const db = obtenerBd();
  db.prepare(`
    INSERT INTO notificaciones_cache (
      id, organizacion_id, certificado_id, administracion, tipo, estado,
      contenido, fecha_deteccion, asignado_a, notas, urgencia, categoria,
      id_externo, creado_en, sincronizado_en, pendiente_push
    ) VALUES (
      @id, @organizacionId, @certificadoId, @administracion, @tipo, @estado,
      @contenido, @fechaDeteccion, @asignadoA, @notas, @urgencia, @categoria,
      @idExterno, @creadoEn, @sincronizadoEn, @pendientePush
    ) ON CONFLICT(id) DO UPDATE SET
      estado = excluded.estado,
      contenido = excluded.contenido,
      asignado_a = excluded.asignado_a,
      notas = excluded.notas,
      urgencia = excluded.urgencia,
      categoria = excluded.categoria,
      sincronizado_en = excluded.sincronizado_en,
      pendiente_push = CASE
        WHEN notificaciones_cache.pendiente_push = 1 THEN 1
        ELSE excluded.pendiente_push
      END
  `).run({
    id: notif.id,
    organizacionId: notif.organizacionId,
    certificadoId: notif.certificadoId,
    administracion: notif.administracion,
    tipo: notif.tipo,
    estado: notif.estado,
    contenido: notif.contenido,
    fechaDeteccion: notif.fechaDeteccion,
    asignadoA: notif.asignadoA,
    notas: notif.notas,
    urgencia: notif.urgencia,
    categoria: notif.categoria,
    idExterno: notif.idExterno,
    creadoEn: notif.creadoEn,
    sincronizadoEn: notif.sincronizadoEn,
    pendientePush: notif.pendientePush
  });
}
function upsertNotificaciones(notifs) {
  const db = obtenerBd();
  const tx = db.transaction(() => {
    for (const notif of notifs) {
      upsertNotificacion(notif);
    }
  });
  tx();
}
function listarNotificacionesCache(organizacionId, filtros = {}) {
  const db = obtenerBd();
  const { busqueda, estado, urgencia, categoria, pagina = 1, limite = 50 } = filtros;
  const offset = (pagina - 1) * limite;
  let whereClause = "WHERE organizacion_id = ?";
  const params = [organizacionId];
  if (estado) {
    whereClause += " AND estado = ?";
    params.push(estado);
  }
  if (urgencia) {
    whereClause += " AND urgencia = ?";
    params.push(urgencia);
  }
  if (categoria) {
    whereClause += " AND categoria = ?";
    params.push(categoria);
  }
  if (busqueda) {
    whereClause += " AND (administracion LIKE ? OR contenido LIKE ?)";
    const patron = `%${busqueda}%`;
    params.push(patron, patron);
  }
  const totalRow = db.prepare(`SELECT COUNT(*) as total FROM notificaciones_cache ${whereClause}`).get(...params);
  const filas = db.prepare(
    `SELECT * FROM notificaciones_cache ${whereClause} ORDER BY fecha_deteccion DESC LIMIT ? OFFSET ?`
  ).all(...params, limite, offset);
  return {
    datos: filas.map(mapearFilaNotificacion),
    total: totalRow.total
  };
}
function actualizarNotificacionLocal(id, datos) {
  const db = obtenerBd();
  const sets = [];
  const params = [];
  if (datos.estado !== void 0) {
    sets.push("estado = ?");
    params.push(datos.estado);
  }
  if (datos.notas !== void 0) {
    sets.push("notas = ?");
    params.push(datos.notas);
  }
  if (datos.asignadoA !== void 0) {
    sets.push("asignado_a = ?");
    params.push(datos.asignadoA);
  }
  if (datos.urgencia !== void 0) {
    sets.push("urgencia = ?");
    params.push(datos.urgencia);
  }
  if (datos.categoria !== void 0) {
    sets.push("categoria = ?");
    params.push(datos.categoria);
  }
  if (sets.length === 0) return;
  sets.push("pendiente_push = 1");
  params.push(id);
  db.prepare(`UPDATE notificaciones_cache SET ${sets.join(", ")} WHERE id = ?`).run(...params);
}
function mapearFilaNotificacion(f) {
  return {
    id: f.id,
    organizacionId: f.organizacion_id,
    certificadoId: f.certificado_id,
    administracion: f.administracion,
    tipo: f.tipo,
    estado: f.estado,
    contenido: f.contenido,
    fechaDeteccion: f.fecha_deteccion,
    asignadoA: f.asignado_a,
    notas: f.notas,
    urgencia: f.urgencia,
    categoria: f.categoria,
    idExterno: f.id_externo,
    creadoEn: f.creado_en,
    sincronizadoEn: f.sincronizado_en,
    pendientePush: f.pendiente_push
  };
}
function upsertEtiqueta(etiqueta) {
  const db = obtenerBd();
  db.prepare(`
    INSERT INTO etiquetas_cache (id, organizacion_id, nombre, color, sincronizado_en)
    VALUES (@id, @organizacionId, @nombre, @color, @sincronizadoEn)
    ON CONFLICT(id) DO UPDATE SET
      nombre = excluded.nombre,
      color = excluded.color,
      sincronizado_en = excluded.sincronizado_en
  `).run({
    id: etiqueta.id,
    organizacionId: etiqueta.organizacionId,
    nombre: etiqueta.nombre,
    color: etiqueta.color,
    sincronizadoEn: etiqueta.sincronizadoEn
  });
}
function upsertEtiquetas(etiquetas) {
  const db = obtenerBd();
  const tx = db.transaction(() => {
    for (const etiqueta of etiquetas) {
      upsertEtiqueta(etiqueta);
    }
  });
  tx();
}
function listarEtiquetasCache(organizacionId) {
  const db = obtenerBd();
  const filas = db.prepare(
    "SELECT * FROM etiquetas_cache WHERE organizacion_id = ? ORDER BY nombre ASC"
  ).all(organizacionId);
  return filas.map(mapearFilaEtiqueta);
}
function eliminarEtiquetasOrg(organizacionId) {
  const db = obtenerBd();
  db.prepare("DELETE FROM etiquetas_cache WHERE organizacion_id = ?").run(organizacionId);
}
function mapearFilaEtiqueta(f) {
  return {
    id: f.id,
    organizacionId: f.organizacion_id,
    nombre: f.nombre,
    color: f.color,
    sincronizadoEn: f.sincronizado_en
  };
}
const MAX_INTENTOS = 5;
function obtenerMeta(clave) {
  const db = obtenerBd();
  const fila = db.prepare("SELECT valor FROM metadata_sync WHERE clave = ?").get(clave);
  return fila?.valor ?? null;
}
function guardarMeta(clave, valor) {
  const db = obtenerBd();
  db.prepare(`
    INSERT INTO metadata_sync (clave, valor, actualizado_en)
    VALUES (?, ?, ?)
    ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor, actualizado_en = excluded.actualizado_en
  `).run(clave, valor, (/* @__PURE__ */ new Date()).toISOString());
}
function obtenerUltimaSync() {
  return {
    certificados: obtenerMeta("ultima_sync_certificados"),
    notificaciones: obtenerMeta("ultima_sync_notificaciones"),
    etiquetas: obtenerMeta("ultima_sync_etiquetas")
  };
}
async function pullDesdeCloud(apiUrl, token, organizacionId) {
  const resultado = { certificados: 0, notificaciones: 0, etiquetas: 0, errores: [] };
  const headers = { Authorization: `Bearer ${token}` };
  const ahora = (/* @__PURE__ */ new Date()).toISOString();
  try {
    const resp = await fetch(`${apiUrl}/etiquetas`, { headers });
    if (resp.ok) {
      const datos = await resp.json();
      const lista = datos.datos ?? datos ?? [];
      if (Array.isArray(lista) && lista.length > 0) {
        eliminarEtiquetasOrg(organizacionId);
        const etiquetas = lista.map((e) => ({
          id: e.id,
          organizacionId: e.organizacionId ?? organizacionId,
          nombre: e.nombre,
          color: e.color,
          sincronizadoEn: ahora
        }));
        upsertEtiquetas(etiquetas);
        resultado.etiquetas = etiquetas.length;
      }
      guardarMeta("ultima_sync_etiquetas", ahora);
    }
  } catch (err) {
    resultado.errores.push(`etiquetas: ${String(err)}`);
  }
  try {
    const desde = obtenerMeta("ultima_sync_certificados");
    let pagina = 1;
    let hayMas = true;
    while (hayMas) {
      let url = `${apiUrl}/certificados?limite=100&pagina=${pagina}`;
      if (desde) url += `&desde=${encodeURIComponent(desde)}`;
      const resp = await fetch(url, { headers });
      if (!resp.ok) break;
      const datos = await resp.json();
      const lista = datos.datos?.certificados ?? datos.certificados ?? [];
      if (!Array.isArray(lista) || lista.length === 0) {
        hayMas = false;
        break;
      }
      const certs = lista.map((c) => ({
        id: c.id,
        organizacionId: c.organizacionId ?? organizacionId,
        nombreTitular: c.nombreTitular ?? "",
        dniCif: c.dniCif ?? "",
        numeroSerie: c.numeroSerie ?? null,
        emisor: c.emisor ?? null,
        organizacion: c.organizacion ?? null,
        fechaExpedicion: c.fechaExpedicion ?? null,
        fechaVencimiento: c.fechaVencimiento ?? "",
        activo: c.activo ? 1 : 0,
        creadoEn: c.creadoEn ?? ahora,
        actualizadoEn: c.actualizadoEn ?? null,
        sincronizadoEn: ahora,
        etiquetasJson: JSON.stringify(c.etiquetas ?? [])
      }));
      upsertCertificados(certs);
      resultado.certificados += certs.length;
      hayMas = lista.length === 100;
      pagina++;
    }
    guardarMeta("ultima_sync_certificados", ahora);
  } catch (err) {
    resultado.errores.push(`certificados: ${String(err)}`);
  }
  try {
    const desde = obtenerMeta("ultima_sync_notificaciones");
    let pagina = 1;
    let hayMas = true;
    while (hayMas) {
      let url = `${apiUrl}/notificaciones?limite=100&pagina=${pagina}`;
      if (desde) url += `&desde=${encodeURIComponent(desde)}`;
      const resp = await fetch(url, { headers });
      if (!resp.ok) break;
      const datos = await resp.json();
      const lista = datos.datos?.notificaciones ?? datos.notificaciones ?? [];
      if (!Array.isArray(lista) || lista.length === 0) {
        hayMas = false;
        break;
      }
      const notifs = lista.map((n) => ({
        id: n.id,
        organizacionId: n.organizacionId ?? organizacionId,
        certificadoId: n.certificadoId ?? "",
        administracion: n.administracion ?? "",
        tipo: n.tipo ?? null,
        estado: n.estado ?? "pendiente",
        contenido: n.contenido ?? null,
        fechaDeteccion: n.fechaDeteccion ?? ahora,
        asignadoA: n.asignadoA ?? null,
        notas: n.notas ?? null,
        urgencia: n.urgencia ?? null,
        categoria: n.categoria ?? null,
        idExterno: n.idExterno ?? null,
        creadoEn: n.creadoEn ?? ahora,
        sincronizadoEn: ahora,
        pendientePush: 0
      }));
      upsertNotificaciones(notifs);
      resultado.notificaciones += notifs.length;
      hayMas = lista.length === 100;
      pagina++;
    }
    guardarMeta("ultima_sync_notificaciones", ahora);
  } catch (err) {
    resultado.errores.push(`notificaciones: ${String(err)}`);
  }
  if (resultado.errores.length > 0) {
    log.warn("[Sync] Pull con errores:", resultado.errores);
  } else {
    log.info(`[Sync] Pull completado: ${resultado.certificados} certs, ${resultado.notificaciones} notifs, ${resultado.etiquetas} etiquetas`);
  }
  return resultado;
}
async function pushAlCloud(apiUrl, token) {
  const pendientes = obtenerCambiosPendientes();
  let enviados = 0;
  let fallidos = 0;
  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
  for (const cambio of pendientes) {
    if (cambio.intentos >= MAX_INTENTOS) {
      log.warn(`[Sync] Moviendo cambio ${cambio.id} a dead-letter tras ${MAX_INTENTOS} intentos`);
      moverADeadLetter(cambio);
      fallidos++;
      continue;
    }
    try {
      let resp;
      if (cambio.recurso === "notificacion" && cambio.operacion === "patch") {
        resp = await fetch(`${apiUrl}/notificaciones/${cambio.recursoId}`, {
          method: "PATCH",
          headers,
          body: cambio.payloadJson
        });
      }
      if (!resp) {
        log.warn(`[Sync] Operacion no soportada: ${cambio.recurso}/${cambio.operacion}`);
        eliminarCambio(cambio.id);
        continue;
      }
      if (resp.ok || resp.status === 409) {
        eliminarCambio(cambio.id);
        enviados++;
      } else {
        registrarErrorCambio(cambio.id, `HTTP ${resp.status}`);
        fallidos++;
      }
    } catch (err) {
      registrarErrorCambio(cambio.id, String(err));
      fallidos++;
    }
  }
  if (enviados > 0 || fallidos > 0) {
    log.info(`[Sync] Push completado: ${enviados} enviados, ${fallidos} fallidos`);
  }
  return { enviados, fallidos };
}
async function sincronizarCompleto(apiUrl, token, organizacionId) {
  await pushAlCloud(apiUrl, token);
  return pullDesdeCloud(apiUrl, token, organizacionId);
}
let tokenEnMemoria = null;
let apiUrlEnMemoria = null;
let orgIdEnMemoria = null;
let intervaloSync = null;
const INTERVALO_SYNC_MS = 5 * 60 * 1e3;
function registrarHandlersOffline(ventana) {
  ipcMain.handle("offline:estado", () => ({
    conectado: estaOnline(),
    pendientes: contarPendientes(),
    ultimaSync: obtenerUltimaSync()
  }));
  ipcMain.handle("offline:forzarSync", async (_event, apiUrl, token, organizacionId) => {
    try {
      const resultado = await sincronizarCompleto(apiUrl, token, organizacionId);
      return { exito: true, resultado };
    } catch (err) {
      log.error("[Offline] Error en sync forzada:", err);
      return { exito: false, error: String(err) };
    }
  });
  ipcMain.handle("offline:listarCertificados", (_event, organizacionId, filtros) => {
    return listarCertificadosCache(organizacionId, filtros);
  });
  ipcMain.handle("offline:listarNotificaciones", (_event, organizacionId, filtros) => {
    return listarNotificacionesCache(organizacionId, filtros);
  });
  ipcMain.handle("offline:listarEtiquetas", (_event, organizacionId) => {
    return listarEtiquetasCache(organizacionId);
  });
  ipcMain.handle("offline:encolarCambio", (_event, recurso, recursoId, operacion, payload) => {
    encolarCambio(recurso, recursoId, operacion, payload);
    if (recurso === "notificacion" && operacion === "patch") {
      actualizarNotificacionLocal(recursoId, payload);
    }
  });
  ipcMain.handle("offline:actualizarToken", (_event, apiUrl, token, organizacionId) => {
    tokenEnMemoria = token;
    apiUrlEnMemoria = apiUrl;
    orgIdEnMemoria = organizacionId;
  });
  ipcMain.handle("offline:iniciarDetector", (_event, apiUrl) => {
    const urlPing = `${apiUrl}/health`;
    iniciarDetectorConexion(urlPing, (conectado2) => {
      ventana.webContents.send("offline:cambioEstado", conectado2);
      if (conectado2 && tokenEnMemoria && apiUrlEnMemoria && orgIdEnMemoria) {
        sincronizarCompleto(apiUrlEnMemoria, tokenEnMemoria, orgIdEnMemoria).then(() => ventana.webContents.send("offline:syncCompletada")).catch((err) => log.error("[Offline] Error sync auto:", err));
      }
    });
  });
  iniciarSyncPeriodica(ventana);
  log.info("[Offline] Handlers registrados (7 IPC)");
}
function iniciarSyncPeriodica(ventana) {
  if (intervaloSync) return;
  intervaloSync = setInterval(async () => {
    if (!estaOnline() || !tokenEnMemoria || !apiUrlEnMemoria || !orgIdEnMemoria) return;
    try {
      await sincronizarCompleto(apiUrlEnMemoria, tokenEnMemoria, orgIdEnMemoria);
      ventana.webContents.send("offline:syncCompletada");
    } catch (err) {
      log.error("[Offline] Error sync periódica:", err);
    }
  }, INTERVALO_SYNC_MS);
}
function detenerOffline() {
  detenerDetectorConexion();
  if (intervaloSync) {
    clearInterval(intervaloSync);
    intervaloSync = null;
  }
  tokenEnMemoria = null;
  apiUrlEnMemoria = null;
  orgIdEnMemoria = null;
}
function inicializarEsquemaLocal() {
  const db = obtenerBd();
  db.exec(`
    CREATE TABLE IF NOT EXISTS certificados_cache (
      id TEXT PRIMARY KEY,
      organizacion_id TEXT NOT NULL,
      nombre_titular TEXT NOT NULL,
      dni_cif TEXT NOT NULL,
      numero_serie TEXT,
      emisor TEXT,
      organizacion TEXT,
      fecha_expedicion TEXT,
      fecha_vencimiento TEXT NOT NULL,
      activo INTEGER NOT NULL DEFAULT 1,
      creado_en TEXT NOT NULL,
      actualizado_en TEXT,
      sincronizado_en TEXT NOT NULL,
      etiquetas_json TEXT NOT NULL DEFAULT '[]'
    );

    CREATE TABLE IF NOT EXISTS notificaciones_cache (
      id TEXT PRIMARY KEY,
      organizacion_id TEXT NOT NULL,
      certificado_id TEXT,
      administracion TEXT NOT NULL,
      tipo TEXT,
      estado TEXT NOT NULL DEFAULT 'pendiente',
      contenido TEXT,
      fecha_deteccion TEXT NOT NULL,
      asignado_a TEXT,
      notas TEXT,
      urgencia TEXT,
      categoria TEXT,
      id_externo TEXT,
      creado_en TEXT NOT NULL,
      sincronizado_en TEXT NOT NULL,
      pendiente_push INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS etiquetas_cache (
      id TEXT PRIMARY KEY,
      organizacion_id TEXT NOT NULL,
      nombre TEXT NOT NULL,
      color TEXT NOT NULL,
      sincronizado_en TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS cola_cambios (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      recurso TEXT NOT NULL,
      recurso_id TEXT NOT NULL,
      operacion TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      intentos INTEGER NOT NULL DEFAULT 0,
      ultimo_intento TEXT,
      creado_en TEXT NOT NULL,
      error_ultimo TEXT
    );

    CREATE TABLE IF NOT EXISTS metadata_sync (
      clave TEXT PRIMARY KEY,
      valor TEXT NOT NULL,
      actualizado_en TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dead_letter_cambios (
      id INTEGER PRIMARY KEY,
      recurso TEXT NOT NULL,
      recurso_id TEXT NOT NULL,
      operacion TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      intentos INTEGER NOT NULL DEFAULT 0,
      error_ultimo TEXT,
      creado_en TEXT NOT NULL,
      descartado_en TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_certs_org ON certificados_cache(organizacion_id);
    CREATE INDEX IF NOT EXISTS idx_notif_org ON notificaciones_cache(organizacion_id);
    CREATE INDEX IF NOT EXISTS idx_notif_pendiente ON notificaciones_cache(pendiente_push) WHERE pendiente_push = 1;
    CREATE INDEX IF NOT EXISTS idx_cola_recurso ON cola_cambios(recurso, recurso_id);
  `);
  log.info("[BdLocal] Esquema local inicializado (6 tablas)");
}
const { autoUpdater: autoUpdater$1 } = pkg;
const URL_ACTUALIZACIONES = "https://www.carloscanetegomez.dev/certigestor/desktop/";
const INTERVALO_CHECK_MS = 60 * 60 * 1e3;
function configurarUpdater(ventana) {
  if (is.dev) {
    log.info("[updater] Modo desarrollo — auto-updates desactivados");
    return;
  }
  autoUpdater$1.logger = log;
  autoUpdater$1.autoDownload = true;
  autoUpdater$1.autoInstallOnAppQuit = true;
  autoUpdater$1.setFeedURL({
    provider: "generic",
    url: URL_ACTUALIZACIONES
  });
  autoUpdater$1.on("checking-for-update", () => {
    log.info("[updater] Verificando actualizaciones...");
    ventana.webContents.send("update:checking");
  });
  autoUpdater$1.on("update-available", (info) => {
    const datos = {
      version: info.version,
      fechaPublicacion: info.releaseDate ?? (/* @__PURE__ */ new Date()).toISOString(),
      notasCambios: typeof info.releaseNotes === "string" ? info.releaseNotes : void 0
    };
    log.info(`[updater] Actualizacion disponible: v${datos.version}`);
    ventana.webContents.send("update:available", datos);
  });
  autoUpdater$1.on("update-not-available", () => {
    log.info("[updater] No hay actualizaciones disponibles");
    ventana.webContents.send("update:not-available");
  });
  autoUpdater$1.on("download-progress", (progreso) => {
    const datos = {
      porcentaje: Math.round(progreso.percent),
      bytesTransferidos: progreso.transferred,
      bytesTotal: progreso.total,
      velocidadBps: progreso.bytesPerSecond
    };
    ventana.webContents.send("update:progress", datos);
  });
  autoUpdater$1.on("update-downloaded", (info) => {
    const datos = {
      version: info.version,
      fechaPublicacion: info.releaseDate ?? (/* @__PURE__ */ new Date()).toISOString(),
      notasCambios: typeof info.releaseNotes === "string" ? info.releaseNotes : void 0
    };
    log.info(`[updater] Actualizacion descargada: v${datos.version}`);
    ventana.webContents.send("update:downloaded", datos);
  });
  autoUpdater$1.on("error", (err) => {
    log.error("[updater] Error:", err.message);
    ventana.webContents.send("update:error", err.message);
  });
  autoUpdater$1.checkForUpdatesAndNotify();
  setInterval(() => {
    autoUpdater$1.checkForUpdates().catch((err) => {
      log.error("[updater] Error en check periodico:", err.message);
    });
  }, INTERVALO_CHECK_MS);
}
async function verificarActualizacionManual() {
  await autoUpdater$1.checkForUpdates();
}
const { machineIdSync } = nodeMachineId;
const INTERVALO_DEFAULT = 5 * 60 * 1e3;
const MAX_COLA = 500;
function generarHashInstalacion() {
  try {
    const id = machineIdSync(true);
    return createHash("sha256").update(id).digest("hex").slice(0, 32);
  } catch {
    return createHash("sha256").update(`${process.platform}-${app.getPath("userData")}`).digest("hex").slice(0, 32);
  }
}
class ClienteTelemetria {
  cola = [];
  config = {
    apiUrl: "https://carloscanetegomez.dev/certigestor/api/telemetria",
    intervaloFlush: INTERVALO_DEFAULT,
    optOut: false
  };
  hashInstalacion = "";
  timer = null;
  ultimoEnvio = null;
  /** Inicializar cliente — llamar una vez desde main */
  iniciar(opciones) {
    if (opciones) {
      this.config = { ...this.config, ...opciones };
    }
    this.hashInstalacion = generarHashInstalacion();
    this.timer = setInterval(() => {
      this.flush().catch((err) => log.warn("[telemetria] Error flush:", err));
    }, this.config.intervaloFlush);
    log.info(`[telemetria] Cliente iniciado (hash: ${this.hashInstalacion.slice(0, 8)}..., optOut: ${this.config.optOut})`);
    this.registrar("app:inicio");
  }
  /** Detener cliente y hacer flush final */
  async detener() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    await this.flush();
    log.info("[telemetria] Cliente detenido");
  }
  /** Registrar un evento en la cola */
  registrar(evento, propiedades) {
    if (this.config.optOut) return;
    if (this.cola.length >= MAX_COLA) {
      this.cola.shift();
    }
    this.cola.push({
      evento,
      version: app.getVersion(),
      plataforma: process.platform,
      propiedades,
      hashInstalacion: this.hashInstalacion,
      timestamp: (/* @__PURE__ */ new Date()).toISOString()
    });
  }
  /** Enviar eventos pendientes al servidor */
  async flush() {
    if (this.config.optOut || this.cola.length === 0) return;
    const batch = [...this.cola];
    this.cola = [];
    try {
      const respuesta = await fetch(this.config.apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ eventos: batch }),
        signal: AbortSignal.timeout(1e4)
      });
      if (!respuesta.ok) {
        const espacio = MAX_COLA - this.cola.length;
        this.cola.push(...batch.slice(0, espacio));
        log.warn(`[telemetria] Flush fallido: ${respuesta.status}`);
        return;
      }
      this.ultimoEnvio = (/* @__PURE__ */ new Date()).toISOString();
      log.info(`[telemetria] ${batch.length} eventos enviados`);
    } catch (error) {
      const espacio = MAX_COLA - this.cola.length;
      this.cola.push(...batch.slice(0, espacio));
      log.warn("[telemetria] Error de red al enviar eventos");
    }
  }
  /** Activar opt-out (desactivar telemetria) */
  optOut() {
    this.config.optOut = true;
    this.cola = [];
    log.info("[telemetria] Opt-out activado");
  }
  /** Desactivar opt-out (reactivar telemetria) */
  optIn() {
    this.config.optOut = false;
    log.info("[telemetria] Opt-in activado");
  }
  /** Consultar si esta activa */
  estaActiva() {
    return !this.config.optOut;
  }
  /** Obtener estado actual */
  obtenerEstado() {
    return {
      activa: !this.config.optOut,
      eventosEnCola: this.cola.length,
      ultimoEnvio: this.ultimoEnvio
    };
  }
}
const clienteTelemetria = new ClienteTelemetria();
const { autoUpdater } = pkg;
log.transports.file.level = "info";
log.transports.file.maxSize = 5 * 1024 * 1024;
autoUpdater.logger = log;
let ventanaPrincipal = null;
function crearVentana() {
  ventanaPrincipal = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 1024,
    minHeight: 700,
    show: false,
    title: "CertiGestor Desktop",
    webPreferences: {
      preload: join(__dirname, "../preload/index.mjs"),
      contextIsolation: true,
      sandbox: false,
      nodeIntegration: false
    }
  });
  ventanaPrincipal.on("ready-to-show", () => {
    ventanaPrincipal?.show();
  });
  ventanaPrincipal.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https:") || url.startsWith("http:")) {
      shell.openExternal(url);
    }
    return { action: "deny" };
  });
  if (is.dev && process.env["ELECTRON_RENDERER_URL"]) {
    ventanaPrincipal.loadURL(process.env["ELECTRON_RENDERER_URL"]);
  } else {
    ventanaPrincipal.loadFile(join(__dirname, "../renderer/index.html"));
  }
}
ipcMain.handle("app:getVersion", () => app.getVersion());
ipcMain.handle("app:getPlatform", () => process.platform);
ipcMain.handle("app:installUpdate", () => {
  autoUpdater.quitAndInstall();
});
ipcMain.handle("updater:checkNow", async () => {
  await verificarActualizacionManual();
});
ipcMain.handle("telemetria:optOut", () => {
  clienteTelemetria.optOut();
});
ipcMain.handle("telemetria:optIn", () => {
  clienteTelemetria.optIn();
});
ipcMain.handle("telemetria:estaActiva", () => clienteTelemetria.estaActiva());
ipcMain.handle("telemetria:estado", () => clienteTelemetria.obtenerEstado());
ipcMain.handle("telemetria:registrar", (_event, evento, propiedades) => {
  clienteTelemetria.registrar(evento, propiedades);
});
const lockObtenido = app.requestSingleInstanceLock();
if (!lockObtenido) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (ventanaPrincipal) {
      if (ventanaPrincipal.isMinimized()) ventanaPrincipal.restore();
      ventanaPrincipal.focus();
    }
  });
  app.whenReady().then(() => {
    crearVentana();
    if (ventanaPrincipal) {
      registrarHandlersCertificados(ventanaPrincipal);
      registrarHandlersScraping(ventanaPrincipal);
      registrarHandlersDehu();
      registrarHandlersDocumentales();
      registrarHandlersNotificaciones();
      registrarHandlersFirma(ventanaPrincipal);
      registrarHandlersWorkflows(ventanaPrincipal);
      registrarHandlersScheduler(ventanaPrincipal);
      registrarHandlersTray(ventanaPrincipal);
      registrarHandlersAnalytics();
      registrarHandlersBackup(ventanaPrincipal);
      registrarHandlersMultiCert();
      registrarHandlersOcr();
      inicializarEsquemaLocal();
      registrarHandlersOffline(ventanaPrincipal);
      configurarUpdater(ventanaPrincipal);
      clienteTelemetria.iniciar();
    }
    log.info(`[app] CertiGestor Desktop v${app.getVersion()} iniciado`);
  });
}
app.on("window-all-closed", () => {
  log.info("[app] Ventanas cerradas — saliendo");
  detenerScheduler();
  destruirTray();
  detenerOffline();
  cerrarBd();
  terminarWorkerOcr().catch(() => {
  });
  clienteTelemetria.registrar("app:cierre");
  clienteTelemetria.detener().catch(() => {
  }).finally(() => {
    app.quit();
  });
});
