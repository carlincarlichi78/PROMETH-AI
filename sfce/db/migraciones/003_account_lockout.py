"""
Migracion 003: seguridad usuarios — failed_attempts, locked_until, totp_secret, totp_habilitado.
Ejecutar UNA sola vez: python sfce/db/migraciones/003_account_lockout.py
Idempotente: comprueba columnas existentes antes de ALTER TABLE.
Soporta SQLite y PostgreSQL.
"""
import os
import sqlite3

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")
DB_TYPE = os.environ.get("SFCE_DB_TYPE", "sqlite")


def _ejecutar_sqlite():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    columnas_existentes = [row[1] for row in cur.execute("PRAGMA table_info(usuarios)")]

    if "failed_attempts" not in columnas_existentes:
        cur.execute(
            "ALTER TABLE usuarios ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0"
        )
        print("  Columna failed_attempts añadida.")
    else:
        print("  Columna failed_attempts ya existia, omitida.")

    if "locked_until" not in columnas_existentes:
        cur.execute("ALTER TABLE usuarios ADD COLUMN locked_until TEXT")
        print("  Columna locked_until añadida.")
    else:
        print("  Columna locked_until ya existia, omitida.")

    if "totp_secret" not in columnas_existentes:
        cur.execute("ALTER TABLE usuarios ADD COLUMN totp_secret TEXT")
        print("  Columna totp_secret añadida.")
    else:
        print("  Columna totp_secret ya existia, omitida.")

    if "totp_habilitado" not in columnas_existentes:
        cur.execute(
            "ALTER TABLE usuarios ADD COLUMN totp_habilitado INTEGER NOT NULL DEFAULT 0"
        )
        print("  Columna totp_habilitado añadida.")
    else:
        print("  Columna totp_habilitado ya existia, omitida.")

    conn.commit()
    conn.close()


def _ejecutar_postgresql():
    try:
        import psycopg2
    except ImportError:
        raise RuntimeError(
            "psycopg2 no instalado. Instalar con: pip install psycopg2-binary"
        )

    conn = psycopg2.connect(
        host=os.environ.get("SFCE_DB_HOST", "localhost"),
        port=int(os.environ.get("SFCE_DB_PORT", "5432")),
        user=os.environ["SFCE_DB_USER"],
        password=os.environ["SFCE_DB_PASSWORD"],
        dbname=os.environ["SFCE_DB_NAME"],
    )
    cur = conn.cursor()

    # Idempotente en PostgreSQL: ADD COLUMN IF NOT EXISTS
    try:
        cur.execute(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS failed_attempts INTEGER NOT NULL DEFAULT 0"
        )
        print("  Columna failed_attempts añadida (o ya existia).")
    except Exception as e:
        print(f"  failed_attempts: {e}")
        conn.rollback()

    try:
        cur.execute(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP"
        )
        print("  Columna locked_until añadida (o ya existia).")
    except Exception as e:
        print(f"  locked_until: {e}")
        conn.rollback()

    try:
        cur.execute(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64)"
        )
        print("  Columna totp_secret añadida (o ya existia).")
    except Exception as e:
        print(f"  totp_secret: {e}")
        conn.rollback()

    try:
        cur.execute(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS totp_habilitado BOOLEAN NOT NULL DEFAULT false"
        )
        print("  Columna totp_habilitado añadida (o ya existia).")
    except Exception as e:
        print(f"  totp_habilitado: {e}")
        conn.rollback()

    conn.commit()
    conn.close()


def ejecutar():
    print(f"Migracion 003 — account lockout (tipo BD: {DB_TYPE})")
    if DB_TYPE == "postgresql":
        _ejecutar_postgresql()
    else:
        _ejecutar_sqlite()
    print("Migracion 003 completada.")


if __name__ == "__main__":
    ejecutar()
