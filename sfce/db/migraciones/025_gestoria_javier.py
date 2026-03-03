"""Migración 025 — crea gestoría "Javier Independiente" y ajusta roles.

Cambios:
- Inserta gestoria_id=3 (Javier Independiente) en gestorias
- Javier: asesor_independiente → admin_gestoria, gestoria_id=3
- Empresas 10-13: gestoria_id=3
- gestor1, gestor2: asesor → admin_gestoria (socios iguales en Gestoría A)
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def upgrade(sesion) -> None:
    # 1. Crear gestoría Javier
    from datetime import datetime
    sesion.execute(text("""
        INSERT INTO gestorias (nombre, email_contacto, activa, plan_tier, modulos, plan_asesores, plan_clientes_tramo, fecha_alta)
        VALUES ('Javier Independiente', 'javier@prometh-ai.es', :activa, 'basico', '[]', 1, '1-10', :fecha)
    """), {"activa": True, "fecha": datetime.utcnow()})
    sesion.flush()

    # Obtener el id asignado (compatible SQLite + PG)
    result = sesion.execute(text(
        "SELECT id FROM gestorias WHERE email_contacto='javier@prometh-ai.es' ORDER BY id DESC LIMIT 1"
    )).fetchone()
    gestoria_javier_id = result[0]
    logger.info("025: gestoría Javier creada con id=%s", gestoria_javier_id)

    # 2. Javier → admin_gestoria de su propia gestoría
    sesion.execute(text("""
        UPDATE usuarios SET rol='admin_gestoria', gestoria_id=:gid
        WHERE email='javier@prometh-ai.es'
    """), {"gid": gestoria_javier_id})

    # 3. Empresas 10-13 → gestoria_id de Javier
    sesion.execute(text("""
        UPDATE empresas SET gestoria_id=:gid WHERE id IN (10, 11, 12, 13)
    """), {"gid": gestoria_javier_id})

    # 4. gestor1 y gestor2 → admin_gestoria (socios iguales en Gestoría A)
    sesion.execute(text("""
        UPDATE usuarios SET rol='admin_gestoria'
        WHERE email IN ('gestor1@prometh-ai.es', 'gestor2@prometh-ai.es')
    """))

    sesion.commit()
    logger.info("025: roles y gestoría Javier actualizados correctamente")


def downgrade(sesion) -> None:
    result = sesion.execute(text(
        "SELECT id FROM gestorias WHERE email_contacto='javier@prometh-ai.es'"
    )).fetchone()
    if result:
        gid = result[0]
        sesion.execute(text("UPDATE empresas SET gestoria_id=NULL WHERE gestoria_id=:gid"), {"gid": gid})
        sesion.execute(text(
            "UPDATE usuarios SET rol='asesor_independiente', gestoria_id=NULL WHERE email='javier@prometh-ai.es'"
        ))
        sesion.execute(text(
            "UPDATE usuarios SET rol='asesor' WHERE email IN ('gestor1@prometh-ai.es','gestor2@prometh-ai.es')"
        ))
        sesion.execute(text("DELETE FROM gestorias WHERE id=:gid"), {"gid": gid})
    sesion.commit()


if __name__ == "__main__":
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    dsn = os.environ.get("DATABASE_URL", "sqlite:///sfce.db")
    engine = create_engine(dsn)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        upgrade(s)
        print("Migración 025 aplicada.")
