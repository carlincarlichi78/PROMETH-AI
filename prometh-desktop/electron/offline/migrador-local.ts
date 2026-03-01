import { obtenerBd } from './bd-local'
import log from 'electron-log'

export function inicializarEsquemaLocal(): void {
  const db = obtenerBd()

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
  `)

  log.info('[BdLocal] Esquema local inicializado (6 tablas)')
}
