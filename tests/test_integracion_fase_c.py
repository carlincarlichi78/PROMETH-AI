"""Tests integracion Fase C — BD + importador + exportador + backend."""

import pytest
from datetime import date
from decimal import Decimal
from pathlib import Path

from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.modelos import Empresa, Asiento, Partida, Documento, Factura
from sfce.db.repositorio import Repositorio
from sfce.core.backend import Backend
from sfce.core.importador import Importador
from sfce.core.exportador import Exportador


@pytest.fixture
def entorno_completo():
    """Crea entorno completo: BD + empresa + datos."""
    engine = crear_motor()
    inicializar_bd(engine)
    factory = crear_sesion(engine)
    repo = Repositorio(factory)

    # Crear empresa
    emp = Empresa(cif="B12345678", nombre="Integracion S.L.", forma_juridica="sl")
    with factory() as s:
        s.add(emp)
        s.commit()
        s.refresh(emp)
        empresa_id = emp.id

    # Crear asientos con partidas (gasto + ingreso)
    a1 = repo.crear(Asiento(
        empresa_id=empresa_id, numero=1, fecha=date(2025, 3, 15),
        concepto="Factura Proveedor A", ejercicio="2025", origen="pipeline"))
    repo.crear(Partida(asiento_id=a1.id, subcuenta="6000000001",
                        debe=Decimal("1000.00"), concepto="Material oficina"))
    repo.crear(Partida(asiento_id=a1.id, subcuenta="4720000000",
                        debe=Decimal("210.00"), concepto="IVA soportado 21%"))
    repo.crear(Partida(asiento_id=a1.id, subcuenta="4000000001",
                        haber=Decimal("1210.00"), concepto="Proveedor A"))

    a2 = repo.crear(Asiento(
        empresa_id=empresa_id, numero=2, fecha=date(2025, 3, 20),
        concepto="Factura Cliente B", ejercicio="2025", origen="pipeline"))
    repo.crear(Partida(asiento_id=a2.id, subcuenta="4300000001",
                        debe=Decimal("3630.00"), concepto="Cliente B"))
    repo.crear(Partida(asiento_id=a2.id, subcuenta="7000000000",
                        haber=Decimal("3000.00"), concepto="Servicios prestados"))
    repo.crear(Partida(asiento_id=a2.id, subcuenta="4770000000",
                        haber=Decimal("630.00"), concepto="IVA repercutido 21%"))

    return repo, empresa_id, factory


class TestFlujoCompleto:
    def test_factura_en_bd_consulta_pyg(self, entorno_completo):
        """Procesar factura -> verificar en BD -> consultar PyG."""
        repo, eid, _ = entorno_completo

        # Backend modo local
        backend = Backend(modo="local", repo=repo, empresa_id=eid)

        # PyG
        pyg = backend.pyg("2025")
        assert pyg["ingresos"] == 3000.0
        assert pyg["gastos"] == 1000.0
        assert pyg["resultado"] == 2000.0

        # Balance
        balance = backend.balance()
        assert balance["activo"] > 0

        # Saldo subcuenta especifica
        saldo = backend.obtener_saldo("6000000001")
        assert saldo["saldo"] == 1000.0

    def test_auditoria_registrada(self, entorno_completo):
        """Operaciones dejan rastro en audit log."""
        repo, eid, _ = entorno_completo
        backend = Backend(modo="local", repo=repo, empresa_id=eid)
        backend.registrar_auditoria(
            "crear_asiento", entidad_tipo="asiento", entidad_id=1,
            datos_despues={"concepto": "Test"})
        # No crash = OK


class TestImportarYExportar:
    def test_csv_roundtrip(self, tmp_path):
        """Importar CSV -> exportar CSV -> reimportar = mismo resultado."""
        # Crear CSV original
        csv_orig = tmp_path / "original.csv"
        csv_orig.write_text(
            "Asiento;Fecha;Subcuenta;Debe;Haber;Concepto\n"
            "1;2025-01-15;6000000001;1000.00;0.00;Gasto\n"
            "1;2025-01-15;4720000000;210.00;0.00;IVA\n"
            "1;2025-01-15;4000000001;0.00;1210.00;Proveedor\n",
            encoding="utf-8"
        )

        # Importar
        imp = Importador()
        datos = imp.importar_csv(csv_orig)
        assert datos["estadisticas"]["total_asientos"] == 1
        assert datos["estadisticas"]["total_partidas"] == 3

        # Exportar
        exp = Exportador()
        csv_export = tmp_path / "exportado.csv"
        exp.exportar_libro_diario_csv(datos["asientos"], csv_export)
        assert csv_export.exists()

        # Reimportar
        datos2 = imp.importar_csv(csv_export)
        assert datos2["estadisticas"]["total_partidas"] == 3

    def test_importar_genera_config(self, tmp_path):
        """Importar CSV con CIF -> generar config propuesto."""
        csv_file = tmp_path / "con_cif.csv"
        csv_file.write_text(
            "Subcuenta;Debe;Haber;CIF\n"
            "6000000001;500;0;A11111111\n"
            "6020000000;300;0;B22222222\n"
            "4000000001;0;800;\n",
            encoding="utf-8"
        )
        imp = Importador()
        datos = imp.importar_csv(csv_file)
        config = imp.generar_config_propuesto(datos["mapa_cif_subcuenta"])
        assert len(config["proveedores"]) == 2

    def test_excel_export_multihoja(self, entorno_completo, tmp_path):
        """Exportar datos de BD a Excel multi-hoja."""
        repo, eid, _ = entorno_completo
        backend = Backend(modo="local", repo=repo, empresa_id=eid)

        pyg = backend.pyg("2025")
        datos_excel = {
            "Resumen": [
                {"Concepto": "Ingresos", "Importe": pyg["ingresos"]},
                {"Concepto": "Gastos", "Importe": pyg["gastos"]},
                {"Concepto": "Resultado", "Importe": pyg["resultado"]},
            ],
        }
        exp = Exportador()
        ruta = tmp_path / "resumen.xlsx"
        exp.exportar_excel_multihoja(datos_excel, ruta)
        assert ruta.exists()


class TestImportsTodosFaseC:
    """Verificar que todos los modulos de Fase C se importan."""
    def test_db_base(self):
        from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
        assert callable(crear_motor)

    def test_db_modelos(self):
        from sfce.db.modelos import Empresa, Asiento, Partida, Factura
        assert Empresa is not None

    def test_repositorio(self):
        from sfce.db.repositorio import Repositorio
        assert callable(Repositorio)

    def test_backend(self):
        from sfce.core.backend import Backend
        assert callable(Backend)

    def test_importador(self):
        from sfce.core.importador import Importador
        assert callable(Importador)

    def test_exportador(self):
        from sfce.core.exportador import Exportador
        assert callable(Exportador)

    def test_migrador(self):
        from scripts.migrar_fs_a_bd import Migrador
        assert callable(Migrador)
