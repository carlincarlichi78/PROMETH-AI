"""Migración 010: plan_tier + limite_empresas en gestorias; plan_tier en usuarios."""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # gestorias
    cols_g = [row[1] for row in cur.execute("PRAGMA table_info(gestorias)")]
    if "plan_tier" not in cols_g:
        cur.execute("ALTER TABLE gestorias ADD COLUMN plan_tier TEXT NOT NULL DEFAULT 'basico'")
    if "limite_empresas" not in cols_g:
        cur.execute("ALTER TABLE gestorias ADD COLUMN limite_empresas INTEGER")

    # usuarios
    cols_u = [row[1] for row in cur.execute("PRAGMA table_info(usuarios)")]
    if "plan_tier" not in cols_u:
        cur.execute("ALTER TABLE usuarios ADD COLUMN plan_tier TEXT NOT NULL DEFAULT 'basico'")

    conn.commit()
    conn.close()
    print("Migracion 010 completada.")


if __name__ == "__main__":
    ejecutar()
