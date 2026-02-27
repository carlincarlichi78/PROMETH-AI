"""Tests para sfce/core/backend.py — Doble destino BD local."""

import pytest
from datetime import date
from decimal import Decimal

from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.modelos import Empresa, Asiento, Partida
from sfce.db.repositorio import Repositorio
from sfce.core.backend import Backend


@pytest.fixture
def repo_y_empresa():
    engine = crear_motor()
    inicializar_bd(engine)
    factory = crear_sesion(engine)
    repo = Repositorio(factory)
    emp = Empresa(cif="B12345678", nombre="Test S.L.", forma_juridica="sl")
    with factory() as s:
        s.add(emp)
        s.commit()
        s.refresh(emp)
        empresa_id = emp.id
    return repo, empresa_id


class TestModoLocal:
    def test_crear_backend_local(self, repo_y_empresa):
        repo, eid = repo_y_empresa
        backend = Backend(modo="local", repo=repo, empresa_id=eid)
        assert backend.modo == "local"

    def test_obtener_saldo_local(self, repo_y_empresa):
        repo, eid = repo_y_empresa
        backend = Backend(modo="local", repo=repo, empresa_id=eid)

        # Crear asiento con partidas directamente
        asiento = repo.crear(Asiento(
            empresa_id=eid, numero=1, fecha=date(2025, 3, 15),
            concepto="Test", ejercicio="2025", origen="pipeline"))
        repo.crear(Partida(asiento_id=asiento.id, subcuenta="6000000001",
                            debe=Decimal("500.00")))
        repo.crear(Partida(asiento_id=asiento.id, subcuenta="4000000001",
                            haber=Decimal("500.00")))

        saldo = backend.obtener_saldo("6000000001")
        assert saldo is not None
        assert saldo["saldo"] == 500.0

    def test_pyg_local(self, repo_y_empresa):
        repo, eid = repo_y_empresa
        backend = Backend(modo="local", repo=repo, empresa_id=eid)

        # Gasto
        a1 = repo.crear(Asiento(empresa_id=eid, numero=1, fecha=date(2025, 1, 1),
                                 concepto="Gasto", ejercicio="2025"))
        repo.crear(Partida(asiento_id=a1.id, subcuenta="6000000001",
                            debe=Decimal("1000.00")))
        repo.crear(Partida(asiento_id=a1.id, subcuenta="4000000001",
                            haber=Decimal("1000.00")))
        # Ingreso
        a2 = repo.crear(Asiento(empresa_id=eid, numero=2, fecha=date(2025, 1, 15),
                                 concepto="Venta", ejercicio="2025"))
        repo.crear(Partida(asiento_id=a2.id, subcuenta="4300000001",
                            debe=Decimal("3000.00")))
        repo.crear(Partida(asiento_id=a2.id, subcuenta="7000000000",
                            haber=Decimal("3000.00")))

        pyg = backend.pyg("2025")
        assert pyg["ingresos"] == 3000.0
        assert pyg["gastos"] == 1000.0
        assert pyg["resultado"] == 2000.0

    def test_balance_local(self, repo_y_empresa):
        repo, eid = repo_y_empresa
        backend = Backend(modo="local", repo=repo, empresa_id=eid)
        bal = backend.balance()
        assert bal is not None
        assert "activo" in bal

    def test_obtener_facturas_local_vacio(self, repo_y_empresa):
        repo, eid = repo_y_empresa
        backend = Backend(modo="local", repo=repo, empresa_id=eid)
        facturas = backend.obtener_facturas("proveedores")
        assert isinstance(facturas, list)


class TestModoDual:
    def test_crear_asiento_fs_falla_guarda_local(self, repo_y_empresa):
        repo, eid = repo_y_empresa
        backend = Backend(modo="dual", repo=repo, empresa_id=eid)

        # Simular fallo FS
        def _api_post_falla(endpoint, data):
            raise ConnectionError("FS no disponible")

        backend._api_post = _api_post_falla

        resultado = backend.crear_asiento({
            "concepto": "Test fallback",
            "codejercicio": "2025",
        })
        assert resultado.get("_pendiente_sync") is True

    def test_registrar_auditoria(self, repo_y_empresa):
        repo, eid = repo_y_empresa
        backend = Backend(modo="local", repo=repo, empresa_id=eid)
        backend.registrar_auditoria("test_accion", detalle="Test")
        # No error = OK

    def test_sincronizar_pendientes_placeholder(self, repo_y_empresa):
        repo, eid = repo_y_empresa
        backend = Backend(modo="dual", repo=repo, empresa_id=eid)
        backend._api_post = lambda *a: {}
        resultado = backend.sincronizar_pendientes()
        assert resultado == {"sincronizados": 0, "errores": 0}


class TestModoFS:
    def test_modo_fs_sin_repo(self):
        """Modo FS legacy no necesita repo."""
        # No podemos testear FS real, solo verificar que no crashea
        # al crear sin repo
        try:
            backend = Backend(modo="fs")
            assert backend.modo == "fs"
            assert backend.repo is None
        except ImportError:
            # fs_api puede fallar sin token configurado
            pass
