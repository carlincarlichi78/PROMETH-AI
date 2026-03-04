"""
Migración 029 — Conciliación Bancaria Inteligente.

Añade:
  - sugerencias_match: candidatos múltiples por movimiento
  - patrones_conciliacion: aprendizaje de confirmaciones manuales
  - conciliaciones_parciales: N:1 (una transferencia cubre N facturas)
  - cuentas_bancarias: saldo_bancario_ultimo, fecha_saldo_ultimo
  - movimientos_bancarios: documento_id, score_confianza, metadata_match, capa_match
"""
from sqlalchemy import text


def aplicar(engine):
    with engine.connect() as conn:
        dialect = engine.dialect.name

        # --- documentos (campos conciliación) ---
        _add_column_if_missing(conn, dialect, "documentos", "gestoria_id", "INTEGER")
        _add_column_if_missing(conn, dialect, "documentos", "nombre_archivo", "VARCHAR(300)")
        _add_column_if_missing(conn, dialect, "documentos", "importe_total", "NUMERIC(12,2)")
        _add_column_if_missing(conn, dialect, "documentos", "nif_proveedor", "VARCHAR(20)")
        _add_column_if_missing(conn, dialect, "documentos", "numero_factura", "VARCHAR(50)")
        _add_column_if_missing(conn, dialect, "documentos", "fecha_documento", "DATE")

        # --- cuentas_bancarias ---
        _add_column_if_missing(conn, dialect, "cuentas_bancarias", "saldo_bancario_ultimo", "NUMERIC(12,2)")
        _add_column_if_missing(conn, dialect, "cuentas_bancarias", "fecha_saldo_ultimo", "DATE")

        # --- movimientos_bancarios ---
        _add_column_if_missing(conn, dialect, "movimientos_bancarios", "documento_id", "INTEGER")
        _add_column_if_missing(conn, dialect, "movimientos_bancarios", "score_confianza", "FLOAT")
        _add_column_if_missing(conn, dialect, "movimientos_bancarios", "metadata_match", "TEXT")
        _add_column_if_missing(conn, dialect, "movimientos_bancarios", "capa_match", "INTEGER")

        # --- sugerencias_match ---
        if not _tabla_existe(conn, dialect, "sugerencias_match"):
            pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if dialect == "sqlite" else "SERIAL PRIMARY KEY"
            default_bool = "DEFAULT 1" if dialect == "sqlite" else "DEFAULT TRUE"
            conn.execute(text(f"""
                CREATE TABLE sugerencias_match (
                    id            {pk},
                    movimiento_id INTEGER NOT NULL,
                    documento_id  INTEGER NOT NULL,
                    score         FLOAT NOT NULL,
                    capa_origen   INTEGER NOT NULL,
                    activa        BOOLEAN NOT NULL {default_bool},
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(movimiento_id, documento_id)
                )
            """))
            conn.execute(text(
                "CREATE INDEX idx_sugerencias_mov ON sugerencias_match(movimiento_id, activa)"
            ))

        # --- patrones_conciliacion ---
        if not _tabla_existe(conn, dialect, "patrones_conciliacion"):
            pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if dialect == "sqlite" else "SERIAL PRIMARY KEY"
            conn.execute(text(f"""
                CREATE TABLE patrones_conciliacion (
                    id                   {pk},
                    empresa_id           INTEGER NOT NULL,
                    patron_texto         VARCHAR(500) NOT NULL,
                    patron_limpio        VARCHAR(500),
                    nif_proveedor        VARCHAR(20),
                    cuenta_contable      VARCHAR(10),
                    rango_importe_aprox  VARCHAR(20) NOT NULL,
                    frecuencia_exito     INTEGER NOT NULL DEFAULT 1,
                    ultima_confirmacion  DATE,
                    UNIQUE(empresa_id, patron_texto, rango_importe_aprox)
                )
            """))
            conn.execute(text(
                "CREATE INDEX idx_patrones_emp ON patrones_conciliacion(empresa_id, patron_limpio, rango_importe_aprox)"
            ))

        # --- conciliaciones_parciales ---
        if not _tabla_existe(conn, dialect, "conciliaciones_parciales"):
            pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if dialect == "sqlite" else "SERIAL PRIMARY KEY"
            conn.execute(text(f"""
                CREATE TABLE conciliaciones_parciales (
                    id               {pk},
                    movimiento_id    INTEGER NOT NULL,
                    documento_id     INTEGER NOT NULL,
                    importe_asignado NUMERIC(12,2) NOT NULL,
                    confirmado_en    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(movimiento_id, documento_id)
                )
            """))

        conn.commit()


def _tabla_existe(conn, dialect, nombre):
    if dialect == "sqlite":
        r = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
            {"n": nombre},
        ).fetchone()
        return r is not None
    else:
        r = conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_name=:n"),
            {"n": nombre},
        ).fetchone()
        return r is not None


def _add_column_if_missing(conn, dialect, tabla, columna, tipo):
    if dialect == "sqlite":
        cols = conn.execute(text(f"PRAGMA table_info({tabla})")).fetchall()
        nombres = [c[1] for c in cols]
    else:
        cols = conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name=:t AND column_name=:c"),
            {"t": tabla, "c": columna},
        ).fetchall()
        nombres = [c[0] for c in cols]

    if columna not in nombres:
        conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}"))
