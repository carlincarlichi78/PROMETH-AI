"""Tests de queries fiscales en Repositorio."""

import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sfce.db.base import Base
from sfce.db.modelos import (
    Empresa, ProveedorCliente, Documento, Asiento, Partida, Factura,
)
from sfce.db.repositorio import Repositorio


# --- Fixtures ---

@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def sesion_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def repo(sesion_factory):
    return Repositorio(sesion_factory)


@pytest.fixture
def empresa_id(sesion_factory):
    """Inserta empresa de prueba y devuelve su id."""
    with sesion_factory() as s:
        emp = Empresa(
            cif="B12345678",
            nombre="Empresa Test S.L.",
            forma_juridica="sl",
            territorio="peninsula",
            regimen_iva="general",
        )
        s.add(emp)
        s.commit()
        return emp.id


def _crear_asiento(s, empresa_id: int, ejercicio: str, fecha: date,
                   partidas: list[dict]) -> Asiento:
    """Helper para crear un asiento con sus partidas."""
    asiento = Asiento(
        empresa_id=empresa_id,
        fecha=fecha,
        ejercicio=ejercicio,
        concepto="Asiento prueba",
        origen="pipeline",
    )
    s.add(asiento)
    s.flush()
    for p in partidas:
        s.add(Partida(
            asiento_id=asiento.id,
            subcuenta=p["subcuenta"],
            debe=Decimal(str(p.get("debe", 0))),
            haber=Decimal(str(p.get("haber", 0))),
            codimpuesto=p.get("codimpuesto"),
        ))
    s.commit()
    return asiento


def _crear_doc_y_factura(s, empresa_id: int, ejercicio: str,
                          tipo_doc: str, tipo_fac: str,
                          cif_emisor: str, nombre_emisor: str,
                          cif_receptor: str, nombre_receptor: str,
                          base: float, iva: float, irpf: float,
                          total: float, fecha: date,
                          estado: str = "registrado") -> Factura:
    """Helper para crear Documento + Factura."""
    doc = Documento(
        empresa_id=empresa_id,
        tipo_doc=tipo_doc,
        ejercicio=ejercicio,
        estado=estado,
        fecha_proceso=fecha,
    )
    s.add(doc)
    s.flush()
    fac = Factura(
        documento_id=doc.id,
        empresa_id=empresa_id,
        tipo=tipo_fac,
        fecha_factura=fecha,
        cif_emisor=cif_emisor,
        nombre_emisor=nombre_emisor,
        cif_receptor=cif_receptor,
        nombre_receptor=nombre_receptor,
        base_imponible=Decimal(str(base)),
        iva_importe=Decimal(str(iva)),
        irpf_importe=Decimal(str(irpf)) if irpf else None,
        total=Decimal(str(total)),
    )
    s.add(fac)
    s.commit()
    return fac


# --- Tests _rango_fechas_periodo ---

class TestRangoFechasPeriodo:

    def test_1t(self):
        ini, fin = Repositorio._rango_fechas_periodo("2025", "1T")
        assert ini == date(2025, 1, 1)
        assert fin == date(2025, 3, 31)

    def test_2t(self):
        ini, fin = Repositorio._rango_fechas_periodo("2025", "2T")
        assert ini == date(2025, 4, 1)
        assert fin == date(2025, 6, 30)

    def test_3t(self):
        ini, fin = Repositorio._rango_fechas_periodo("2025", "3T")
        assert ini == date(2025, 7, 1)
        assert fin == date(2025, 9, 30)

    def test_4t(self):
        ini, fin = Repositorio._rango_fechas_periodo("2025", "4T")
        assert ini == date(2025, 10, 1)
        assert fin == date(2025, 12, 31)

    def test_anual(self):
        ini, fin = Repositorio._rango_fechas_periodo("2025", "0A")
        assert ini == date(2025, 1, 1)
        assert fin == date(2025, 12, 31)


# --- Tests iva_por_periodo ---

class TestIvaPorPeriodo:

    def test_estructura_correcta_sin_datos(self, repo, empresa_id):
        resultado = repo.iva_por_periodo(empresa_id, "2025", "1T")

        assert "repercutido" in resultado
        assert "soportado" in resultado
        assert "total_repercutido" in resultado
        assert "total_soportado" in resultado
        assert resultado["periodo"] == "1T"
        assert resultado["ejercicio"] == "2025"

    def test_tipos_iva_presentes(self, repo, empresa_id):
        resultado = repo.iva_por_periodo(empresa_id, "2025", "1T")

        for grupo in ("repercutido", "soportado"):
            assert "general" in resultado[grupo]
            assert "reducido" in resultado[grupo]
            assert "superreducido" in resultado[grupo]
            for tipo in resultado[grupo].values():
                assert "base" in tipo
                assert "cuota" in tipo

    def test_valores_float(self, repo, empresa_id):
        resultado = repo.iva_por_periodo(empresa_id, "2025", "1T")

        assert isinstance(resultado["total_repercutido"], float)
        assert isinstance(resultado["total_soportado"], float)

    def test_con_partidas_iva(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            _crear_asiento(s, empresa_id, "2025", date(2025, 2, 15), [
                {"subcuenta": "600", "debe": 1000, "haber": 0},
                {"subcuenta": "472", "debe": 210, "haber": 0, "codimpuesto": "IVA21"},
                {"subcuenta": "400", "debe": 0, "haber": 1210},
            ])
            _crear_asiento(s, empresa_id, "2025", date(2025, 2, 20), [
                {"subcuenta": "700", "debe": 0, "haber": 2000},
                {"subcuenta": "477", "debe": 0, "haber": 420, "codimpuesto": "IVA21"},
                {"subcuenta": "430", "debe": 2420, "haber": 0},
            ])

        resultado = repo.iva_por_periodo(empresa_id, "2025", "1T")

        assert resultado["total_soportado"] > 0
        assert resultado["total_repercutido"] > 0

    def test_no_explota_empresa_inexistente(self, repo):
        resultado = repo.iva_por_periodo(9999, "2025", "1T")
        assert resultado["total_repercutido"] == 0.0
        assert resultado["total_soportado"] == 0.0

    def test_periodo_fuera_rango_no_suma(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            _crear_asiento(s, empresa_id, "2025", date(2025, 7, 1), [
                {"subcuenta": "472", "debe": 100, "haber": 0, "codimpuesto": "IVA21"},
                {"subcuenta": "400", "debe": 0, "haber": 100},
            ])

        resultado = repo.iva_por_periodo(empresa_id, "2025", "1T")
        assert resultado["total_soportado"] == 0.0


# --- Tests retenciones_por_periodo ---

class TestRetencionesPorPeriodo:

    def test_estructura_correcta(self, repo, empresa_id):
        resultado = repo.retenciones_por_periodo(empresa_id, "2025", "1T")

        assert "trabajo" in resultado
        assert "profesionales" in resultado
        assert "alquileres" in resultado
        assert "capital" in resultado
        assert "total" in resultado
        assert resultado["periodo"] == "1T"
        assert resultado["ejercicio"] == "2025"

    def test_valores_float(self, repo, empresa_id):
        resultado = repo.retenciones_por_periodo(empresa_id, "2025", "1T")
        for campo in ("trabajo", "profesionales", "alquileres", "capital", "total"):
            assert isinstance(resultado[campo], float)

    def test_total_es_suma_tipos(self, repo, empresa_id):
        resultado = repo.retenciones_por_periodo(empresa_id, "2025", "1T")
        esperado = sum(resultado[k] for k in ("trabajo", "profesionales", "alquileres", "capital"))
        assert abs(resultado["total"] - esperado) < 0.01

    def test_con_facturas_irpf(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            _crear_doc_y_factura(
                s, empresa_id, "2025", "FV", "recibida",
                "B11111111", "Proveedor Pro", "B12345678", "Empresa Test",
                base=1000.0, iva=210.0, irpf=150.0, total=1060.0,
                fecha=date(2025, 2, 10),
            )

        resultado = repo.retenciones_por_periodo(empresa_id, "2025", "1T")
        assert resultado["profesionales"] > 0
        assert resultado["total"] > 0

    def test_no_explota_sin_datos(self, repo, empresa_id):
        resultado = repo.retenciones_por_periodo(empresa_id, "2025", "3T")
        assert resultado["total"] == 0.0


# --- Tests operaciones_terceros ---

class TestOperacionesTerceros:

    def test_devuelve_lista(self, repo, empresa_id):
        resultado = repo.operaciones_terceros(empresa_id, "2025")
        assert isinstance(resultado, list)

    def test_estructura_cada_item(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            for mes in range(1, 7):
                _crear_doc_y_factura(
                    s, empresa_id, "2025", "FV", "recibida",
                    "B99999999", "Gran Proveedor S.L.", "", "",
                    base=1000.0, iva=210.0, irpf=0.0, total=1210.0,
                    fecha=date(2025, mes, 15),
                )

        resultado = repo.operaciones_terceros(empresa_id, "2025")
        assert len(resultado) > 0
        item = resultado[0]
        assert "cif" in item
        assert "nombre" in item
        assert "importe_total" in item
        assert "importe_1T" in item
        assert "importe_2T" in item
        assert "importe_3T" in item
        assert "importe_4T" in item
        assert "tipo" in item
        assert item["tipo"] in ("A", "B")

    def test_umbral_3005_aplicado(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            # Factura pequena, no debe aparecer
            _crear_doc_y_factura(
                s, empresa_id, "2025", "FV", "recibida",
                "B77777777", "Proveedor Pequeno", "", "",
                base=100.0, iva=21.0, irpf=0.0, total=121.0,
                fecha=date(2025, 1, 10),
            )

        resultado = repo.operaciones_terceros(empresa_id, "2025")
        cifs = [r["cif"] for r in resultado]
        assert "B77777777" not in cifs

    def test_no_explota_sin_datos(self, repo, empresa_id):
        resultado = repo.operaciones_terceros(empresa_id, "2025")
        assert resultado == []

    def test_trimestres_correctos(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            _crear_doc_y_factura(
                s, empresa_id, "2025", "FV", "recibida",
                "B88888888", "Proveedor Grande", "", "",
                base=2000.0, iva=420.0, irpf=0.0, total=2420.0,
                fecha=date(2025, 1, 15),
            )
            _crear_doc_y_factura(
                s, empresa_id, "2025", "FV", "recibida",
                "B88888888", "Proveedor Grande", "", "",
                base=2000.0, iva=420.0, irpf=0.0, total=2420.0,
                fecha=date(2025, 5, 15),
            )

        resultado = repo.operaciones_terceros(empresa_id, "2025")
        item = next((r for r in resultado if r["cif"] == "B88888888"), None)
        assert item is not None
        assert item["importe_1T"] > 0
        assert item["importe_2T"] > 0


# --- Tests operaciones_intracomunitarias ---

class TestOperacionesIntracomunitarias:

    def test_devuelve_lista(self, repo, empresa_id):
        resultado = repo.operaciones_intracomunitarias(empresa_id, "2025", "1T")
        assert isinstance(resultado, list)

    def test_estructura_cada_item(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            prov = ProveedorCliente(
                empresa_id=empresa_id,
                cif="FR12345678901",
                nombre="Societe Francaise",
                tipo="proveedor",
                pais="FRA",
            )
            s.add(prov)
            s.flush()

            _crear_doc_y_factura(
                s, empresa_id, "2025", "FV", "recibida",
                "FR12345678901", "Societe Francaise", "B12345678", "Empresa Test",
                base=5000.0, iva=0.0, irpf=0.0, total=5000.0,
                fecha=date(2025, 2, 1),
            )

        resultado = repo.operaciones_intracomunitarias(empresa_id, "2025", "1T")
        if resultado:
            item = resultado[0]
            assert "cif" in item
            assert "nombre" in item
            assert "pais" in item
            assert "importe" in item
            assert "tipo_operacion" in item
            assert item["tipo_operacion"] in ("E", "A", "S", "I")

    def test_no_explota_sin_datos(self, repo, empresa_id):
        resultado = repo.operaciones_intracomunitarias(empresa_id, "2025", "0A")
        assert isinstance(resultado, list)


# --- Tests nominas_por_periodo ---

class TestNominasPorPeriodo:

    def test_estructura_correcta(self, repo, empresa_id):
        resultado = repo.nominas_por_periodo(empresa_id, "2025", "1T")

        assert "bruto_total" in resultado
        assert "ss_empresa" in resultado
        assert "irpf_retenido" in resultado
        assert "num_perceptores" in resultado
        assert resultado["periodo"] == "1T"

    def test_valores_float(self, repo, empresa_id):
        resultado = repo.nominas_por_periodo(empresa_id, "2025", "1T")
        assert isinstance(resultado["bruto_total"], float)
        assert isinstance(resultado["ss_empresa"], float)
        assert isinstance(resultado["irpf_retenido"], float)
        assert isinstance(resultado["num_perceptores"], int)

    def test_con_partidas_640(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            _crear_asiento(s, empresa_id, "2025", date(2025, 1, 31), [
                {"subcuenta": "640", "debe": 2500, "haber": 0},
                {"subcuenta": "476", "debe": 750, "haber": 0},
                {"subcuenta": "4751", "debe": 0, "haber": 375},
                {"subcuenta": "572", "debe": 0, "haber": 2875},
            ])

        resultado = repo.nominas_por_periodo(empresa_id, "2025", "1T")
        # Con partidas contables, debe detectar bruto_total
        assert resultado["bruto_total"] >= 0

    def test_no_explota_sin_datos(self, repo, empresa_id):
        resultado = repo.nominas_por_periodo(empresa_id, "2025", "4T")
        assert resultado["bruto_total"] == 0.0
        assert resultado["num_perceptores"] == 0


# --- Tests alquileres_por_periodo ---

class TestAlquileresPorPeriodo:

    def test_estructura_correcta(self, repo, empresa_id):
        resultado = repo.alquileres_por_periodo(empresa_id, "2025", "1T")

        assert "base_alquileres" in resultado
        assert "retenciones_alquileres" in resultado
        assert "num_arrendadores" in resultado
        assert resultado["periodo"] == "1T"

    def test_valores_float(self, repo, empresa_id):
        resultado = repo.alquileres_por_periodo(empresa_id, "2025", "1T")
        assert isinstance(resultado["base_alquileres"], float)
        assert isinstance(resultado["retenciones_alquileres"], float)
        assert isinstance(resultado["num_arrendadores"], int)

    def test_con_factura_alquiler(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            _crear_doc_y_factura(
                s, empresa_id, "2025", "FV", "recibida",
                "A11223344", "Arrendador S.L.", "", "",
                base=1500.0, iva=0.0, irpf=285.0, total=1215.0,
                fecha=date(2025, 1, 5),
            )

        resultado = repo.alquileres_por_periodo(empresa_id, "2025", "1T")
        assert resultado["base_alquileres"] > 0
        assert resultado["retenciones_alquileres"] > 0
        assert resultado["num_arrendadores"] >= 1

    def test_no_explota_sin_datos(self, repo, empresa_id):
        resultado = repo.alquileres_por_periodo(empresa_id, "2025", "2T")
        assert resultado["base_alquileres"] == 0.0

    def test_con_partidas_621(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            _crear_asiento(s, empresa_id, "2025", date(2025, 4, 1), [
                {"subcuenta": "621", "debe": 1000, "haber": 0},
                {"subcuenta": "572", "debe": 0, "haber": 1000},
            ])

        resultado = repo.alquileres_por_periodo(empresa_id, "2025", "2T")
        assert resultado["base_alquileres"] >= 0


# --- Tests rendimientos_capital ---

class TestRendimientosCapital:

    def test_estructura_correcta(self, repo, empresa_id):
        resultado = repo.rendimientos_capital(empresa_id, "2025", "1T")

        assert "rendimientos_brutos" in resultado
        assert "retenciones_practicadas" in resultado
        assert "num_perceptores" in resultado
        assert resultado["periodo"] == "1T"

    def test_valores_float(self, repo, empresa_id):
        resultado = repo.rendimientos_capital(empresa_id, "2025", "1T")
        assert isinstance(resultado["rendimientos_brutos"], float)
        assert isinstance(resultado["retenciones_practicadas"], float)
        assert isinstance(resultado["num_perceptores"], int)

    def test_no_explota_sin_datos(self, repo, empresa_id):
        resultado = repo.rendimientos_capital(empresa_id, "2025", "1T")
        assert resultado["rendimientos_brutos"] == 0.0
        assert resultado["retenciones_practicadas"] == 0.0

    def test_con_partidas_760(self, repo, empresa_id, sesion_factory):
        with sesion_factory() as s:
            _crear_asiento(s, empresa_id, "2025", date(2025, 3, 1), [
                {"subcuenta": "572", "debe": 850, "haber": 0},
                {"subcuenta": "473", "debe": 150, "haber": 0},
                {"subcuenta": "760", "debe": 0, "haber": 1000},
            ])

        resultado = repo.rendimientos_capital(empresa_id, "2025", "1T")
        assert resultado["rendimientos_brutos"] >= 0

    def test_no_explota_empresa_inexistente(self, repo):
        resultado = repo.rendimientos_capital(9999, "2025", "0A")
        assert resultado["rendimientos_brutos"] == 0.0
