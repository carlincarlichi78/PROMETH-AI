"""Migración 028: añade usuario_id a cuentas_correo para tipo='asesor'."""
from sqlalchemy import Engine, text, inspect


def aplicar(engine: Engine) -> None:
    cols = {c["name"] for c in inspect(engine).get_columns("cuentas_correo")}
    if "usuario_id" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE cuentas_correo ADD COLUMN usuario_id INTEGER"
        ))
    print("Migración 028 aplicada: usuario_id añadido a cuentas_correo")


if __name__ == "__main__":
    from sfce.db.base import crear_motor
    from sfce.api.app import _leer_config_bd
    aplicar(crear_motor(_leer_config_bd()))
