"""Migración 019 — Soporte Zoho por gestoría en cuentas_correo.

Cambios en cuentas_correo:
  - gestoria_id INTEGER nullable (FK lógica a gestorias)
  - tipo_cuenta TEXT default 'empresa' ('dedicada'|'gestoria'|'sistema'|'empresa')
  - empresa_id pasa a ser nullable

Compatible con SQLite y PostgreSQL.
"""
from sqlalchemy import Engine, text


# --- Helpers dialect-aware ---

def _columnas_existentes(conn, dialecto: str) -> set[str]:
    if dialecto == "sqlite":
        rows = conn.execute(text("PRAGMA table_info(cuentas_correo)")).fetchall()
        return {row[1] for row in rows}
    # PostgreSQL / otros
    rows = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'cuentas_correo'"
    )).fetchall()
    return {row[0] for row in rows}


def _empresa_id_es_nullable(conn, dialecto: str) -> bool:
    if dialecto == "sqlite":
        rows = conn.execute(text("PRAGMA table_info(cuentas_correo)")).fetchall()
        return any(row[1] == "empresa_id" and row[3] == 0 for row in rows)
    # PostgreSQL
    row = conn.execute(text(
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_name = 'cuentas_correo' AND column_name = 'empresa_id'"
    )).fetchone()
    return row is not None and row[0] == "YES"


# --- Lógica SQLite: recrear tabla para hacer empresa_id nullable ---

_SCHEMA_NUEVO_SQLITE = """
    CREATE TABLE cuentas_correo_new (
        id INTEGER PRIMARY KEY,
        empresa_id INTEGER,
        gestoria_id INTEGER,
        tipo_cuenta TEXT NOT NULL DEFAULT 'empresa',
        nombre TEXT NOT NULL,
        protocolo TEXT NOT NULL,
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
        created_at TEXT
    )
"""

_COLUMNAS_DESTINO = [
    "id", "empresa_id", "gestoria_id", "tipo_cuenta", "nombre", "protocolo",
    "servidor", "puerto", "ssl", "usuario", "contrasena_enc",
    "oauth_token_enc", "oauth_refresh_enc", "oauth_expires_at",
    "carpeta_entrada", "ultimo_uid", "activa",
    "polling_intervalo_segundos", "created_at",
]


def _hacer_nullable_sqlite(conn, col_names: set) -> None:
    cols_origen = [c for c in _COLUMNAS_DESTINO if c in col_names]
    lista = ", ".join(cols_origen)
    select_lista = ", ".join(
        "COALESCE(tipo_cuenta, 'empresa')" if c == "tipo_cuenta" else c
        for c in cols_origen
    )
    conn.execute(text(_SCHEMA_NUEVO_SQLITE))
    conn.execute(text(f"""
        INSERT INTO cuentas_correo_new ({lista})
        SELECT {select_lista} FROM cuentas_correo
    """))
    conn.execute(text("DROP TABLE cuentas_correo"))
    conn.execute(text("ALTER TABLE cuentas_correo_new RENAME TO cuentas_correo"))


# --- Entry point ---

def ejecutar(engine: Engine) -> None:
    dialecto = engine.dialect.name  # "sqlite" | "postgresql"

    with engine.begin() as conn:
        col_names = _columnas_existentes(conn, dialecto)

        # Paso 1: añadir columnas nuevas si faltan
        if "gestoria_id" not in col_names:
            conn.execute(text(
                "ALTER TABLE cuentas_correo ADD COLUMN gestoria_id INTEGER"
            ))
            col_names.add("gestoria_id")

        if "tipo_cuenta" not in col_names:
            conn.execute(text(
                "ALTER TABLE cuentas_correo ADD COLUMN "
                "tipo_cuenta TEXT NOT NULL DEFAULT 'empresa'"
            ))
            col_names.add("tipo_cuenta")

        # Paso 2: hacer empresa_id nullable si aún no lo es
        if not _empresa_id_es_nullable(conn, dialecto):
            if dialecto == "postgresql":
                conn.execute(text(
                    "ALTER TABLE cuentas_correo ALTER COLUMN empresa_id DROP NOT NULL"
                ))
            else:
                # SQLite no soporta ALTER COLUMN → recrear tabla
                _hacer_nullable_sqlite(conn, col_names)

    print("Migración 019 aplicada.")


if __name__ == "__main__":
    from sfce.api.app import _leer_config_bd
    from sfce.db.base import crear_motor
    ejecutar(crear_motor(_leer_config_bd()))
