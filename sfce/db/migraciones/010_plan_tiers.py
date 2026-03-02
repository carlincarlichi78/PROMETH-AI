"""Migración 010: plan_tier + limite_empresas en gestorias; plan_tier en usuarios.

Valores válidos de plan_tier: 'basico', 'pro', 'premium'
(SQLite no soporta CHECK en ALTER TABLE ADD COLUMN; se usan triggers de validación).
"""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")

# Valores de tier permitidos — deben coincidir con sfce.core.tiers.TIER_MAP
_TIERS_VALIDOS = ("'basico'", "'pro'", "'premium'")
_CHECK_TIERS = f"NEW.plan_tier IN ({', '.join(_TIERS_VALIDOS)})"


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # gestorias — columnas
    cols_g = [row[1] for row in cur.execute("PRAGMA table_info(gestorias)")]
    if "plan_tier" not in cols_g:
        cur.execute("ALTER TABLE gestorias ADD COLUMN plan_tier TEXT NOT NULL DEFAULT 'basico'")
    if "limite_empresas" not in cols_g:
        cur.execute("ALTER TABLE gestorias ADD COLUMN limite_empresas INTEGER")

    # usuarios — columna
    cols_u = [row[1] for row in cur.execute("PRAGMA table_info(usuarios)")]
    if "plan_tier" not in cols_u:
        cur.execute("ALTER TABLE usuarios ADD COLUMN plan_tier TEXT NOT NULL DEFAULT 'basico'")

    # Triggers CHECK plan_tier en gestorias (INSERT + UPDATE)
    cur.execute("DROP TRIGGER IF EXISTS chk_gestorias_plan_tier_insert")
    cur.execute(f"""
        CREATE TRIGGER chk_gestorias_plan_tier_insert
        BEFORE INSERT ON gestorias
        FOR EACH ROW
        WHEN NOT ({_CHECK_TIERS})
        BEGIN
            SELECT RAISE(ABORT, 'plan_tier inválido en gestorias: debe ser basico, pro o premium');
        END
    """)
    cur.execute("DROP TRIGGER IF EXISTS chk_gestorias_plan_tier_update")
    cur.execute(f"""
        CREATE TRIGGER chk_gestorias_plan_tier_update
        BEFORE UPDATE OF plan_tier ON gestorias
        FOR EACH ROW
        WHEN NOT ({_CHECK_TIERS})
        BEGIN
            SELECT RAISE(ABORT, 'plan_tier inválido en gestorias: debe ser basico, pro o premium');
        END
    """)

    # Triggers CHECK plan_tier en usuarios (INSERT + UPDATE)
    cur.execute("DROP TRIGGER IF EXISTS chk_usuarios_plan_tier_insert")
    cur.execute(f"""
        CREATE TRIGGER chk_usuarios_plan_tier_insert
        BEFORE INSERT ON usuarios
        FOR EACH ROW
        WHEN NOT ({_CHECK_TIERS})
        BEGIN
            SELECT RAISE(ABORT, 'plan_tier inválido en usuarios: debe ser basico, pro o premium');
        END
    """)
    cur.execute("DROP TRIGGER IF EXISTS chk_usuarios_plan_tier_update")
    cur.execute(f"""
        CREATE TRIGGER chk_usuarios_plan_tier_update
        BEFORE UPDATE OF plan_tier ON usuarios
        FOR EACH ROW
        WHEN NOT ({_CHECK_TIERS})
        BEGIN
            SELECT RAISE(ABORT, 'plan_tier inválido en usuarios: debe ser basico, pro o premium');
        END
    """)

    conn.commit()
    conn.close()
    print("Migracion 010 completada (columnas + triggers CHECK plan_tier).")


if __name__ == "__main__":
    ejecutar()
