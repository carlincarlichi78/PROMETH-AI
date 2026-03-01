"""
Migración 013: tabla config_procesamiento_empresa + campo slug en empresas
              + campos ruta_disco y cola_id en documentos.

Idempotente: comprueba existencia antes de crear.
"""
from sqlalchemy import text


def ejecutar_migracion(engine) -> None:
    with engine.begin() as conn:
        # Tabla config_procesamiento_empresa
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS config_procesamiento_empresa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL UNIQUE,
                modo VARCHAR(20) NOT NULL DEFAULT 'revision',
                schedule_minutos INTEGER DEFAULT NULL,
                ocr_previo BOOLEAN NOT NULL DEFAULT 1,
                notif_calidad_cliente BOOLEAN NOT NULL DEFAULT 1,
                notif_contable_gestor BOOLEAN NOT NULL DEFAULT 1,
                ultimo_pipeline DATETIME DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        """))

        # Campo slug en empresas (ignorar si ya existe)
        try:
            conn.execute(text("ALTER TABLE empresas ADD COLUMN slug VARCHAR(50)"))
        except Exception:
            pass  # Ya existe

        # Campo ruta_disco en documentos
        try:
            conn.execute(text("ALTER TABLE documentos ADD COLUMN ruta_disco VARCHAR(1000)"))
        except Exception:
            pass

        # Campo cola_id en documentos
        try:
            conn.execute(text("ALTER TABLE documentos ADD COLUMN cola_id INTEGER"))
        except Exception:
            pass


if __name__ == "__main__":
    import os
    from sfce.db.base import crear_motor
    dsn = os.getenv("SFCE_DB_DSN", "sqlite:///sfce.db")
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": dsn.replace("sqlite:///", "")})
    ejecutar_migracion(engine)
    print("Migración 013 completada.")
