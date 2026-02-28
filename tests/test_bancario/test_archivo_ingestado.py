"""Tests Task 4: tabla ArchivoIngestado — idempotencia por hash."""
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sfce.db.modelos import Base, ArchivoIngestado


def test_crear_archivo_ingestado():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        archivo = ArchivoIngestado(
            hash_archivo="sha256delejemplo",
            nombre_original="TT181225.754.txt",
            fuente="manual",
            tipo="c43",
            empresa_id=1,
            gestoria_id=1,
            fecha_proceso=datetime.utcnow(),
            movimientos_totales=42,
            movimientos_nuevos=40,
            movimientos_duplicados=2,
        )
        db.add(archivo)
        db.commit()
        assert archivo.id is not None


def test_hash_idempotente():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for _ in range(2):
            db.add(ArchivoIngestado(
                hash_archivo="mismoHash", nombre_original="f.txt",
                fuente="manual", tipo="c43", empresa_id=1, gestoria_id=1,
                fecha_proceso=datetime.utcnow(), movimientos_totales=1,
                movimientos_nuevos=1, movimientos_duplicados=0,
            ))
        import pytest
        with pytest.raises(Exception):
            db.commit()
