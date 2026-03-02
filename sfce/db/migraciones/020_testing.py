"""Crea tablas testing_sesiones, testing_ejecuciones, testing_bugs."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from sfce.db.base import Base, crear_motor
import sfce.db.modelos_testing  # noqa: F401

if __name__ == "__main__":
    engine = crear_motor()
    Base.metadata.create_all(engine, tables=[
        sfce.db.modelos_testing.TestingSesion.__table__,
        sfce.db.modelos_testing.TestingEjecucion.__table__,
        sfce.db.modelos_testing.TestingBug.__table__,
    ])
    print("OK: tablas testing_* creadas")
