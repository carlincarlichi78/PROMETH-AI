"""Migración 005: Módulo de correo — 5 tablas nuevas."""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")

_SQL_TABLAS = [
    """
    CREATE TABLE IF NOT EXISTS cuentas_correo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
        nombre TEXT NOT NULL,
        protocolo TEXT NOT NULL CHECK(protocolo IN ('imap', 'graph')),
        servidor TEXT,
        puerto INTEGER DEFAULT 993,
        ssl INTEGER DEFAULT 1,
        usuario TEXT NOT NULL,
        contrasena_enc TEXT,
        oauth_token_enc TEXT,
        oauth_refresh_enc TEXT,
        oauth_expires_at TEXT,
        carpeta_entrada TEXT DEFAULT 'INBOX',
        ultimo_uid INTEGER DEFAULT 0,
        activa INTEGER DEFAULT 1,
        polling_intervalo_segundos INTEGER DEFAULT 120,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS emails_procesados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta_id INTEGER NOT NULL REFERENCES cuentas_correo(id) ON DELETE CASCADE,
        uid_servidor TEXT NOT NULL,
        message_id TEXT,
        remitente TEXT NOT NULL,
        asunto TEXT DEFAULT '',
        fecha_email TEXT,
        estado TEXT NOT NULL DEFAULT 'PENDIENTE'
            CHECK(estado IN ('PENDIENTE','CLASIFICADO','CUARENTENA','PROCESADO','ERROR','IGNORADO')),
        nivel_clasificacion TEXT
            CHECK(nivel_clasificacion IN ('REGLA','IA','MANUAL')),
        empresa_destino_id INTEGER REFERENCES empresas(id),
        confianza_ia REAL,
        procesado_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(cuenta_id, uid_servidor)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS adjuntos_email (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id INTEGER NOT NULL REFERENCES emails_procesados(id) ON DELETE CASCADE,
        nombre_original TEXT NOT NULL,
        nombre_renombrado TEXT,
        ruta_archivo TEXT,
        mime_type TEXT DEFAULT 'application/pdf',
        tamano_bytes INTEGER DEFAULT 0,
        documento_id INTEGER,
        estado TEXT NOT NULL DEFAULT 'PENDIENTE'
            CHECK(estado IN ('PENDIENTE','OCR_OK','OCR_ERROR','DUPLICADO')),
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS enlaces_email (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id INTEGER NOT NULL REFERENCES emails_procesados(id) ON DELETE CASCADE,
        url TEXT NOT NULL,
        dominio TEXT,
        patron_detectado TEXT DEFAULT 'OTRO'
            CHECK(patron_detectado IN ('AEAT','BANCO','SUMINISTRO','CLOUD','OTRO')),
        estado TEXT NOT NULL DEFAULT 'PENDIENTE'
            CHECK(estado IN ('PENDIENTE','DESCARGANDO','DESCARGADO','ERROR','IGNORADO')),
        nombre_archivo TEXT,
        ruta_archivo TEXT,
        tamano_bytes INTEGER,
        adjunto_id INTEGER REFERENCES adjuntos_email(id),
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reglas_clasificacion_correo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER REFERENCES empresas(id),
        tipo TEXT NOT NULL
            CHECK(tipo IN ('REMITENTE_EXACTO','DOMINIO','ASUNTO_CONTIENE','COMPOSITE')),
        condicion_json TEXT NOT NULL DEFAULT '{}',
        accion TEXT NOT NULL DEFAULT 'CLASIFICAR'
            CHECK(accion IN ('CLASIFICAR','IGNORAR','APROBAR_MANUAL')),
        slug_destino TEXT,
        confianza REAL DEFAULT 1.0,
        origen TEXT DEFAULT 'MANUAL'
            CHECK(origen IN ('MANUAL','APRENDIZAJE')),
        activa INTEGER DEFAULT 1,
        prioridad INTEGER DEFAULT 100,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_emails_cuenta ON emails_procesados(cuenta_id)",
    "CREATE INDEX IF NOT EXISTS idx_emails_estado ON emails_procesados(estado)",
    "CREATE INDEX IF NOT EXISTS idx_adjuntos_email ON adjuntos_email(email_id)",
    "CREATE INDEX IF NOT EXISTS idx_enlaces_email ON enlaces_email(email_id)",
    "CREATE INDEX IF NOT EXISTS idx_reglas_empresa ON reglas_clasificacion_correo(empresa_id)",
]


def ejecutar_migracion() -> None:
    """Ejecuta la migración 005 en la BD configurada por SFCE_DB_PATH."""
    db_path = os.environ.get("SFCE_DB_PATH", DB_PATH)
    conn = sqlite3.connect(db_path)
    try:
        for sql in _SQL_TABLAS:
            sql = sql.strip()
            if sql:
                conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    ejecutar_migracion()
    print("Migración 005 completada.")
