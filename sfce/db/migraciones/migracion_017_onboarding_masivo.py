"""Migración 017: tablas onboarding masivo + bienes_inversion_iva."""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_lotes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            gestoria_id     INTEGER NOT NULL REFERENCES gestorias(id),
            nombre          TEXT NOT NULL,
            fecha_subida    TEXT NOT NULL,
            estado          TEXT NOT NULL DEFAULT 'procesando',
            total_clientes  INTEGER DEFAULT 0,
            completados     INTEGER DEFAULT 0,
            en_revision     INTEGER DEFAULT 0,
            bloqueados      INTEGER DEFAULT 0,
            con_error       INTEGER DEFAULT 0,
            usuario_id      INTEGER REFERENCES usuarios(id),
            notas           TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_perfiles (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id             INTEGER NOT NULL REFERENCES onboarding_lotes(id),
            empresa_id          INTEGER REFERENCES empresas(id),
            nif                 TEXT NOT NULL,
            nombre_detectado    TEXT,
            forma_juridica      TEXT,
            territorio          TEXT,
            confianza           REAL DEFAULT 0,
            estado              TEXT NOT NULL DEFAULT 'borrador',
            datos_json          TEXT NOT NULL DEFAULT '{}',
            advertencias_json   TEXT NOT NULL DEFAULT '[]',
            bloqueos_json       TEXT NOT NULL DEFAULT '[]',
            revisado_por        INTEGER REFERENCES usuarios(id),
            fecha_revision      TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_documentos (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            perfil_id               INTEGER NOT NULL REFERENCES onboarding_perfiles(id),
            nombre_archivo          TEXT NOT NULL,
            tipo_detectado          TEXT,
            confianza_deteccion     REAL DEFAULT 0,
            datos_extraidos_json    TEXT DEFAULT '{}',
            ruta_archivo            TEXT,
            fecha_procesado         TEXT,
            error                   TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bienes_inversion_iva (
            id                              INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id                      INTEGER NOT NULL REFERENCES empresas(id),
            descripcion                     TEXT NOT NULL,
            fecha_adquisicion               TEXT NOT NULL,
            fecha_puesta_servicio           TEXT,
            precio_adquisicion              REAL NOT NULL DEFAULT 0,
            iva_soportado_deducido          REAL NOT NULL DEFAULT 0,
            pct_deduccion_anyo_adquisicion  REAL NOT NULL DEFAULT 100,
            tipo_bien                       TEXT NOT NULL DEFAULT 'resto',
            anyos_regularizacion_total      INTEGER NOT NULL DEFAULT 5,
            anyos_regularizacion_restantes  INTEGER NOT NULL DEFAULT 5,
            transmitido                     INTEGER DEFAULT 0,
            fecha_transmision               TEXT,
            activo                          INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()
    print("Migracion 017 completada.")


if __name__ == "__main__":
    ejecutar()
