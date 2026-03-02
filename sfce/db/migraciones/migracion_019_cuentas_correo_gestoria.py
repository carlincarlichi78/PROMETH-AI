"""Migración 019 — Soporte Zoho por gestoría en cuentas_correo.

Cambios en cuentas_correo:
  - gestoria_id INTEGER nullable (FK lógica a gestorias)
  - tipo_cuenta TEXT default 'empresa' ('dedicada'|'gestoria'|'sistema'|'empresa')
  - empresa_id pasa a ser nullable (SQLite no soporta ALTER COLUMN → recreación de tabla)
"""
from sqlalchemy import Engine, text

_SCHEMA_NUEVO = """
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


def ejecutar(engine: Engine) -> None:
    with engine.begin() as conn:
        cols_info = conn.execute(text("PRAGMA table_info(cuentas_correo)")).fetchall()
        col_names = {row[1] for row in cols_info}
        empresa_nullable = any(
            row[1] == "empresa_id" and row[3] == 0
            for row in cols_info
        )

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

        if empresa_nullable:
            return  # ya es nullable, nada más que hacer

        # Paso 2: recrear tabla para hacer empresa_id nullable
        # Solo copiar columnas que realmente existen en la tabla original
        cols_origen = [c for c in _COLUMNAS_DESTINO if c in col_names]
        lista = ", ".join(cols_origen)
        # Para tipo_cuenta usamos COALESCE por si era NULL antes del ADD
        select_lista = ", ".join(
            f"COALESCE(tipo_cuenta, 'empresa')" if c == "tipo_cuenta" else c
            for c in cols_origen
        )

        conn.execute(text(_SCHEMA_NUEVO))
        conn.execute(text(f"""
            INSERT INTO cuentas_correo_new ({lista})
            SELECT {select_lista} FROM cuentas_correo
        """))
        conn.execute(text("DROP TABLE cuentas_correo"))
        conn.execute(text("ALTER TABLE cuentas_correo_new RENAME TO cuentas_correo"))


if __name__ == "__main__":
    from sfce.db.base import crear_motor
    ejecutar(crear_motor())
    print("Migración 019 aplicada.")
