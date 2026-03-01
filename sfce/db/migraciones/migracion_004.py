"""Migración 004: añade gestoria_id a la tabla empresas."""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(empresas)")]
    if "gestoria_id" not in cols:
        cur.execute(
            "ALTER TABLE empresas ADD COLUMN gestoria_id INTEGER REFERENCES gestorias(id)"
        )
    conn.commit()
    conn.close()
    print("Migración 004 completada.")


if __name__ == "__main__":
    ejecutar()
