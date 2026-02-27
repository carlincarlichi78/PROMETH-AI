"""SFCE DB — Motor dual SQLite/PostgreSQL."""

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos."""
    pass


def crear_motor(config: dict | None = None):
    """Crea engine SQLAlchemy segun configuracion.

    config keys:
        tipo_bd: "sqlite" (default) | "postgresql"
        ruta_bd: path o ":memory:" (sqlite)
        db_user, db_password, db_host, db_port, db_name (postgresql)
    """
    config = config or {"tipo_bd": "sqlite", "ruta_bd": ":memory:"}
    tipo = config.get("tipo_bd", "sqlite")

    if tipo == "sqlite":
        ruta = config.get("ruta_bd", "sfce.db")
        url = f"sqlite:///{ruta}" if ruta != ":memory:" else "sqlite:///:memory:"
        engine = create_engine(url, connect_args={"check_same_thread": False})

        # WAL mode + busy timeout para concurrencia
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    elif tipo == "postgresql":
        host = config.get("db_host", "localhost")
        port = config.get("db_port", 5432)
        user = config["db_user"]
        password = config["db_password"]
        db_name = config["db_name"]
        url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        engine = create_engine(url, pool_size=10, max_overflow=20)
    else:
        raise ValueError(f"Tipo BD no soportado: {tipo}")

    return engine


def crear_sesion(engine):
    """Crea factory de sesiones para el engine dado."""
    return sessionmaker(bind=engine)


def inicializar_bd(engine):
    """Crea todas las tablas definidas en Base.metadata."""
    Base.metadata.create_all(engine)
