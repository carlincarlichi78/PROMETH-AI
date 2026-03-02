"""Migración 018 — Email ingesta mejorada.

Añade:
  - Tabla remitentes_autorizados (whitelist por empresa)
  - Tabla contrasenas_zip (contraseñas para ZIPs protegidos)
  - Campos en emails_procesados: es_respuesta_ack, score_confianza, motivo_cuarentena
  - Campo en cola_procesamiento: empresa_origen_correo_id
"""
from sqlalchemy import Engine, text


def ejecutar(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS remitentes_autorizados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id),
                email TEXT NOT NULL,
                nombre TEXT,
                activo INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS contrasenas_zip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL REFERENCES empresas(id),
                remitente_patron TEXT,
                contrasenas_json TEXT NOT NULL DEFAULT '[]',
                activo INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """))
        # Añadir columnas a emails_procesados si no existen
        cols_existentes = {
            row[1] for row in conn.execute(
                text("PRAGMA table_info(emails_procesados)")
            ).fetchall()
        }
        if "es_respuesta_ack" not in cols_existentes:
            conn.execute(text(
                "ALTER TABLE emails_procesados ADD COLUMN "
                "es_respuesta_ack INTEGER NOT NULL DEFAULT 0"
            ))
        if "score_confianza" not in cols_existentes:
            conn.execute(text(
                "ALTER TABLE emails_procesados ADD COLUMN "
                "score_confianza REAL"
            ))
        if "motivo_cuarentena" not in cols_existentes:
            conn.execute(text(
                "ALTER TABLE emails_procesados ADD COLUMN "
                "motivo_cuarentena TEXT"
            ))
        # Añadir columna a cola_procesamiento si no existe
        cols_cola = {
            row[1] for row in conn.execute(
                text("PRAGMA table_info(cola_procesamiento)")
            ).fetchall()
        }
        if "empresa_origen_correo_id" not in cols_cola:
            conn.execute(text(
                "ALTER TABLE cola_procesamiento ADD COLUMN "
                "empresa_origen_correo_id INTEGER"
            ))


if __name__ == "__main__":
    from sfce.db.base import crear_motor
    ejecutar(crear_motor())
    print("Migración 018 aplicada.")
