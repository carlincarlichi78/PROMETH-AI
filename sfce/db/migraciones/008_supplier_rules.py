"""Migración 008 — tabla supplier_rules."""
import sqlite3


def migrar(ruta_bd: str = "sfce.db") -> None:
    conn = sqlite3.connect(ruta_bd)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS supplier_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER,
            emisor_cif TEXT,
            emisor_nombre_patron TEXT,
            tipo_doc_sugerido TEXT,
            subcuenta_gasto TEXT,
            codimpuesto TEXT,
            regimen TEXT,
            aplicaciones INTEGER DEFAULT 0,
            confirmaciones INTEGER DEFAULT 0,
            tasa_acierto REAL DEFAULT 0.0,
            auto_aplicable INTEGER DEFAULT 0,
            nivel TEXT DEFAULT 'empresa',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS ix_sr_empresa_cif
            ON supplier_rules(empresa_id, emisor_cif);
        CREATE INDEX IF NOT EXISTS ix_sr_auto
            ON supplier_rules(auto_aplicable);
    """)
    conn.commit()
    conn.close()
    print("Migración 008 (Supplier Rules) completada.")


if __name__ == "__main__":
    migrar()
