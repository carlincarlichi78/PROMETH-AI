"""Migración 011 — tabla notificaciones_usuario."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sfce.db.base import Base, crear_motor
from sfce.db.modelos import NotificacionUsuario  # noqa: F401 — registra el modelo


def ejecutar():
    motor = crear_motor()
    Base.metadata.create_all(motor, tables=[
        Base.metadata.tables["notificaciones_usuario"]
    ])
    print("OK Migracion 011: tabla notificaciones_usuario creada")


if __name__ == "__main__":
    ejecutar()
