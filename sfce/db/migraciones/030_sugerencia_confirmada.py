"""
Migración 030 — Columna `confirmada` en sugerencias_match.

Permite distinguir la sugerencia que fue confirmada por el usuario
de las alternativas desactivadas (activa=False por colisión).
"""
from sqlalchemy import text


def aplicar(engine):
    with engine.connect() as conn:
        dialect = engine.dialect.name
        _add_column_if_missing(
            conn, dialect,
            "sugerencias_match", "confirmada",
            "BOOLEAN NOT NULL DEFAULT FALSE" if dialect == "postgresql" else "INTEGER NOT NULL DEFAULT 0",
        )
        conn.commit()


def _add_column_if_missing(conn, dialect, tabla, columna, tipo_sql):
    if dialect == "postgresql":
        existe = conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ), {"t": tabla, "c": columna}).fetchone()
    else:
        existe = conn.execute(
            text(f"PRAGMA table_info({tabla})")
        ).fetchall()
        existe = any(row[1] == columna for row in existe)

    if not existe:
        conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo_sql}"))
