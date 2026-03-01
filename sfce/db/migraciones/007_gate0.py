"""Migración 007 — tablas Gate 0: cola_procesamiento + documento_tracking."""
import sqlite3


def migrar(ruta_bd: str = "sfce.db") -> None:
    conn = sqlite3.connect(ruta_bd)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS cola_procesamiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            documento_id INTEGER,
            nombre_archivo TEXT NOT NULL DEFAULT '',
            ruta_archivo TEXT NOT NULL DEFAULT '',
            estado TEXT DEFAULT 'PENDIENTE',
            trust_level TEXT DEFAULT 'BAJA',
            score_final REAL,
            decision TEXT,
            hints_json TEXT DEFAULT '{}',
            sha256 TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS ix_cola_estado ON cola_procesamiento(estado);
        CREATE INDEX IF NOT EXISTS ix_cola_sha256 ON cola_procesamiento(sha256);

        CREATE TABLE IF NOT EXISTS documento_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            documento_id INTEGER NOT NULL,
            estado TEXT NOT NULL,
            timestamp TEXT DEFAULT (datetime('now')),
            actor TEXT DEFAULT 'sistema',
            detalle_json TEXT DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS ix_tracking_doc ON documento_tracking(documento_id);
    """)
    conn.commit()
    conn.close()
    print("Migracion 007 (Gate 0) completada.")


if __name__ == "__main__":
    migrar()
