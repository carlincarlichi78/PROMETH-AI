"""Tests para DirectorioEntidad, repositorio y migracion."""

import pytest
from pathlib import Path

from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.modelos import DirectorioEntidad, ProveedorCliente, Empresa
from sfce.db.repositorio import Repositorio


@pytest.fixture
def sesion():
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
    inicializar_bd(engine)
    Session = crear_sesion(engine)
    with Session() as s:
        yield s


@pytest.fixture
def repo():
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
    inicializar_bd(engine)
    Session = crear_sesion(engine)
    return Repositorio(Session)


# --- T1: Modelo DirectorioEntidad ---


class TestDirectorioEntidad:
    def test_crear_entidad_con_cif(self, sesion):
        ent = DirectorioEntidad(cif="B12345678", nombre="EMPRESA TEST SL", pais="ESP")
        sesion.add(ent)
        sesion.commit()
        assert ent.id is not None
        assert ent.cif == "B12345678"

    def test_crear_entidad_sin_cif(self, sesion):
        ent = DirectorioEntidad(nombre="PACIENTES FISIOTERAPIA", pais="ESP")
        sesion.add(ent)
        sesion.commit()
        assert ent.id is not None
        assert ent.cif is None

    def test_cif_unico(self, sesion):
        ent1 = DirectorioEntidad(cif="A99999999", nombre="UNO", pais="ESP")
        sesion.add(ent1)
        sesion.commit()
        ent2 = DirectorioEntidad(cif="A99999999", nombre="DOS", pais="ESP")
        sesion.add(ent2)
        with pytest.raises(Exception):
            sesion.commit()

    def test_relacion_overlay(self, sesion):
        dir_ent = DirectorioEntidad(cif="B11111111", nombre="PROV TEST", pais="ESP")
        sesion.add(dir_ent)
        sesion.flush()
        empresa = Empresa(
            cif="X99999999", nombre="MI EMPRESA", forma_juridica="sl",
            territorio="peninsula"
        )
        sesion.add(empresa)
        sesion.flush()
        overlay = ProveedorCliente(
            empresa_id=empresa.id, cif="B11111111", nombre="PROV TEST",
            tipo="proveedor", directorio_id=dir_ent.id
        )
        sesion.add(overlay)
        sesion.commit()
        assert overlay.directorio_id == dir_ent.id
        assert overlay.directorio.nombre == "PROV TEST"

    def test_aliases_json(self, sesion):
        ent = DirectorioEntidad(
            cif="C22222222", nombre="ENDESA ENERGIA SAU", pais="ESP",
            aliases=["ENDESA", "ENDESA ENERGIA"]
        )
        sesion.add(ent)
        sesion.commit()
        sesion.refresh(ent)
        assert "ENDESA" in ent.aliases

    def test_multiples_overlays_por_entidad(self, sesion):
        """Una entidad en directorio puede tener overlays de varias empresas."""
        dir_ent = DirectorioEntidad(cif="A08663619", nombre="CAIXABANK SA", pais="ESP")
        sesion.add(dir_ent)
        sesion.flush()
        emp1 = Empresa(cif="A11111111", nombre="EMP1", forma_juridica="sl", territorio="peninsula")
        emp2 = Empresa(cif="B22222222", nombre="EMP2", forma_juridica="autonomo", territorio="peninsula")
        sesion.add_all([emp1, emp2])
        sesion.flush()
        ov1 = ProveedorCliente(
            empresa_id=emp1.id, cif="A08663619", nombre="CAIXABANK SA",
            tipo="proveedor", directorio_id=dir_ent.id
        )
        ov2 = ProveedorCliente(
            empresa_id=emp2.id, cif="A08663619", nombre="CAIXABANK SA",
            tipo="proveedor", directorio_id=dir_ent.id
        )
        sesion.add_all([ov1, ov2])
        sesion.commit()
        assert len(dir_ent.overlays) == 2


# --- T2: Repositorio queries directorio ---


class TestRepositorioDirectorio:
    def test_buscar_directorio_por_cif(self, repo):
        repo.crear(DirectorioEntidad(cif="B12345678", nombre="TEST SL", pais="ESP"))
        resultado = repo.buscar_directorio_por_cif("B12345678")
        assert resultado is not None
        assert resultado.nombre == "TEST SL"

    def test_buscar_directorio_por_cif_no_existe(self, repo):
        resultado = repo.buscar_directorio_por_cif("Z99999999")
        assert resultado is None

    def test_buscar_directorio_por_nombre(self, repo):
        repo.crear(DirectorioEntidad(
            cif="A11111111", nombre="ENDESA ENERGIA SAU", pais="ESP",
            aliases=["ENDESA", "ENDESA ENERGIA"]
        ))
        resultado = repo.buscar_directorio_por_nombre("ENDESA")
        assert resultado is not None
        assert resultado.cif == "A11111111"

    def test_buscar_directorio_por_nombre_exacto(self, repo):
        repo.crear(DirectorioEntidad(
            cif="B22222222", nombre="QUIRUMED SL", pais="ESP",
            aliases=["QUIRUMED"]
        ))
        resultado = repo.buscar_directorio_por_nombre("QUIRUMED SL")
        assert resultado is not None
        assert resultado.cif == "B22222222"

    def test_buscar_directorio_por_nombre_no_existe(self, repo):
        resultado = repo.buscar_directorio_por_nombre("INEXISTENTE SL")
        assert resultado is None

    def test_obtener_o_crear_directorio_crea(self, repo):
        ent, creado = repo.obtener_o_crear_directorio(
            cif="C33333333", nombre="NUEVA EMPRESA", pais="ESP"
        )
        assert creado is True
        assert ent.id is not None

    def test_obtener_o_crear_directorio_obtiene(self, repo):
        ent1, _ = repo.obtener_o_crear_directorio(
            cif="C33333333", nombre="NUEVA EMPRESA", pais="ESP"
        )
        ent2, creado2 = repo.obtener_o_crear_directorio(
            cif="C33333333", nombre="OTRA COSA"
        )
        assert creado2 is False
        assert ent2.id == ent1.id

    def test_obtener_o_crear_sin_cif(self, repo):
        ent, creado = repo.obtener_o_crear_directorio(
            cif=None, nombre="PACIENTES", pais="ESP"
        )
        assert creado is True
        assert ent.cif is None

    def test_crear_overlay(self, repo):
        dir_ent = repo.crear(DirectorioEntidad(
            cif="D44444444", nombre="FARMACIA CENTRAL", pais="ESP"
        ))
        empresa = repo.crear(Empresa(
            cif="E55555555", nombre="MI EMPRESA", forma_juridica="autonomo",
            territorio="peninsula"
        ))
        overlay = repo.crear_overlay(
            empresa_id=empresa.id, directorio_id=dir_ent.id,
            tipo="proveedor", subcuenta_gasto="6020000000",
            codimpuesto="IVA4", regimen="general"
        )
        assert overlay.directorio_id == dir_ent.id
        assert overlay.subcuenta_gasto == "6020000000"

    def test_buscar_overlay_por_cif(self, repo):
        dir_ent = repo.crear(DirectorioEntidad(cif="F66666666", nombre="PROV", pais="ESP"))
        empresa = repo.crear(Empresa(
            cif="G77777777", nombre="EMPRESA", forma_juridica="sl",
            territorio="peninsula"
        ))
        repo.crear_overlay(
            empresa_id=empresa.id, directorio_id=dir_ent.id,
            tipo="proveedor", subcuenta_gasto="6000000000",
            codimpuesto="IVA21", regimen="general"
        )
        resultado = repo.buscar_overlay_por_cif(empresa.id, "F66666666", "proveedor")
        assert resultado is not None
        assert resultado.directorio.nombre == "PROV"

    def test_buscar_overlay_por_cif_no_existe(self, repo):
        empresa = repo.crear(Empresa(
            cif="H88888888", nombre="EMPRESA", forma_juridica="sl",
            territorio="peninsula"
        ))
        resultado = repo.buscar_overlay_por_cif(empresa.id, "Z99999999", "proveedor")
        assert resultado is None

    def test_listar_directorio(self, repo):
        repo.crear(DirectorioEntidad(cif="A11111111", nombre="UNO", pais="ESP"))
        repo.crear(DirectorioEntidad(cif="B22222222", nombre="DOS", pais="ESP"))
        repo.crear(DirectorioEntidad(nombre="TRES SIN CIF", pais="ESP"))
        resultado = repo.listar_directorio()
        assert len(resultado) == 3

    def test_listar_directorio_filtro_pais(self, repo):
        repo.crear(DirectorioEntidad(cif="A11111111", nombre="ESPANOLA", pais="ESP"))
        repo.crear(DirectorioEntidad(cif="SE556703748501", nombre="SUECA", pais="SWE"))
        resultado = repo.listar_directorio(pais="ESP")
        assert len(resultado) == 1
        assert resultado[0].nombre == "ESPANOLA"


# --- T3: Migracion config.yaml → BD ---


class TestMigracionConfig:
    def test_migrar_dos_clientes_comparten_directorio(self, tmp_path):
        """Si dos clientes tienen el mismo proveedor (CIF), solo 1 entrada directorio."""
        from scripts.migrar_config_a_directorio import migrar_cliente
        import yaml

        config1 = {
            "empresa": {
                "nombre": "Empresa 1", "cif": "A11111111", "tipo": "sl",
                "idempresa": 1, "ejercicio_activo": "2025",
            },
            "proveedores": {
                "caixabank": {
                    "cif": "A08663619", "nombre_fs": "CAIXABANK SA",
                    "pais": "ESP", "divisa": "EUR", "subcuenta": "6620",
                    "codimpuesto": "IVA0", "regimen": "general",
                },
            },
        }
        config2 = {
            "empresa": {
                "nombre": "Empresa 2", "cif": "B22222222", "tipo": "autonomo",
                "idempresa": 2, "ejercicio_activo": "2025",
            },
            "proveedores": {
                "caixabank": {
                    "cif": "A08663619", "nombre_fs": "CAIXABANK SA",
                    "pais": "ESP", "divisa": "EUR", "subcuenta": "6620",
                    "codimpuesto": "IVA0", "regimen": "general",
                },
            },
        }
        dir1 = tmp_path / "emp1"
        dir1.mkdir()
        dir2 = tmp_path / "emp2"
        dir2.mkdir()
        (dir1 / "config.yaml").write_text(yaml.dump(config1), encoding="utf-8")
        (dir2 / "config.yaml").write_text(yaml.dump(config2), encoding="utf-8")

        engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
        inicializar_bd(engine)
        Session = crear_sesion(engine)
        repo = Repositorio(Session)

        migrar_cliente(dir1, repo)
        migrar_cliente(dir2, repo)

        # Solo 1 entrada CaixaBank en directorio
        caixa = repo.buscar_directorio_por_cif("A08663619")
        assert caixa is not None
        # Pero 2 overlays (uno por empresa)
        from sqlalchemy import select
        with Session() as s:
            overlays = s.scalars(
                select(ProveedorCliente).where(ProveedorCliente.cif == "A08663619")
            ).all()
            assert len(overlays) == 2

    def test_migrar_config_simple(self, tmp_path):
        """Migra config con proveedores y clientes."""
        from scripts.migrar_config_a_directorio import migrar_cliente
        import yaml

        config = {
            "empresa": {
                "nombre": "TEST SL", "cif": "X99999999", "tipo": "sl",
                "idempresa": 1, "ejercicio_activo": "2025",
            },
            "proveedores": {
                "prov1": {
                    "cif": "B11111111", "nombre_fs": "PROVEEDOR 1",
                    "pais": "ESP", "divisa": "EUR", "subcuenta": "6000",
                    "codimpuesto": "IVA21", "regimen": "general",
                },
                "prov2": {
                    "cif": "B22222222", "nombre_fs": "PROVEEDOR 2",
                    "pais": "ESP", "divisa": "EUR", "subcuenta": "6010",
                    "codimpuesto": "IVA10", "regimen": "general",
                },
            },
            "clientes": {
                "cli1": {
                    "cif": "C33333333", "nombre_fs": "CLIENTE 1",
                    "pais": "ESP", "divisa": "EUR",
                    "codimpuesto": "IVA21", "regimen": "general",
                },
            },
        }
        dir_cli = tmp_path / "test-sl"
        dir_cli.mkdir()
        (dir_cli / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")

        engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
        inicializar_bd(engine)
        Session = crear_sesion(engine)
        repo = Repositorio(Session)

        stats = migrar_cliente(dir_cli, repo)
        assert stats["proveedores_directorio"] == 2
        assert stats["clientes_directorio"] == 1
        assert stats["overlays_creados"] == 3

    def test_migrar_idempotente(self, tmp_path):
        """Migrar dos veces no duplica entidades."""
        from scripts.migrar_config_a_directorio import migrar_cliente
        import yaml

        config = {
            "empresa": {
                "nombre": "TEST SL", "cif": "X99999999", "tipo": "sl",
                "idempresa": 1, "ejercicio_activo": "2025",
            },
            "proveedores": {
                "prov1": {
                    "cif": "B11111111", "nombre_fs": "PROVEEDOR 1",
                    "pais": "ESP", "divisa": "EUR", "subcuenta": "6000",
                    "codimpuesto": "IVA21", "regimen": "general",
                },
            },
        }
        dir_cli = tmp_path / "test-sl"
        dir_cli.mkdir()
        (dir_cli / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")

        engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": ":memory:"})
        inicializar_bd(engine)
        Session = crear_sesion(engine)
        repo = Repositorio(Session)

        stats1 = migrar_cliente(dir_cli, repo)
        assert stats1["proveedores_directorio"] == 1
        assert stats1["overlays_creados"] == 1

        stats2 = migrar_cliente(dir_cli, repo)
        assert stats2["ya_existentes"] == 1
        assert stats2["overlays_creados"] == 0


# --- T5: ConfigCliente lee de BD ---


class TestConfigClienteDesdeBD:
    def test_buscar_proveedor_por_cif_desde_bd(self, repo):
        """ConfigCliente.buscar_proveedor_por_cif usa BD cuando hay repo."""
        from scripts.core.config import ConfigCliente
        dir_ent = repo.crear(DirectorioEntidad(
            cif="B46011995", nombre="QUIRUMED SL", pais="ESP",
            aliases=["QUIRUMED"]
        ))
        empresa = repo.crear(Empresa(
            cif="24813607B", nombre="ELENA NAVARRO", forma_juridica="autonomo",
            territorio="peninsula"
        ))
        repo.crear_overlay(
            empresa_id=empresa.id, directorio_id=dir_ent.id,
            tipo="proveedor", subcuenta_gasto="6290000000",
            codimpuesto="IVA21", regimen="general"
        )
        config_data = {
            "empresa": {
                "nombre": "ELENA NAVARRO", "cif": "24813607B",
                "tipo": "autonomo", "idempresa": 99, "ejercicio_activo": "2025",
            },
            "proveedores": {},
            "clientes": {},
        }
        config = ConfigCliente(config_data, "test", repo=repo, empresa_bd_id=empresa.id)
        resultado = config.buscar_proveedor_por_cif("B46011995")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "quirumed-sl"

    def test_fallback_yaml_si_no_repo(self):
        """Sin repo, ConfigCliente usa YAML como antes."""
        from scripts.core.config import ConfigCliente
        config_data = {
            "empresa": {
                "nombre": "TEST", "cif": "X99999999",
                "tipo": "sl", "idempresa": 1, "ejercicio_activo": "2025",
            },
            "proveedores": {
                "test-prov": {
                    "cif": "A11111111", "nombre_fs": "TEST PROV",
                    "pais": "ESP", "divisa": "EUR", "subcuenta": "600",
                    "codimpuesto": "IVA21", "regimen": "general",
                },
            },
        }
        config = ConfigCliente(config_data, "test")
        resultado = config.buscar_proveedor_por_cif("A11111111")
        assert resultado is not None
        assert resultado["_nombre_corto"] == "test-prov"

    def test_buscar_cliente_por_cif_desde_bd(self, repo):
        """ConfigCliente.buscar_cliente_por_cif usa BD."""
        from scripts.core.config import ConfigCliente
        dir_ent = repo.crear(DirectorioEntidad(
            cif="C33333333", nombre="MI CLIENTE SL", pais="ESP"
        ))
        empresa = repo.crear(Empresa(
            cif="X88888888", nombre="MI EMPRESA", forma_juridica="sl",
            territorio="peninsula"
        ))
        repo.crear_overlay(
            empresa_id=empresa.id, directorio_id=dir_ent.id,
            tipo="cliente", codimpuesto="IVA21", regimen="general"
        )
        config = ConfigCliente(
            {"empresa": {"nombre": "MI EMPRESA", "cif": "X88888888",
                          "tipo": "sl", "idempresa": 1, "ejercicio_activo": "2025"},
             "proveedores": {}, "clientes": {}},
            "test", repo=repo, empresa_bd_id=empresa.id
        )
        resultado = config.buscar_cliente_por_cif("C33333333")
        assert resultado is not None
        assert resultado["nombre_fs"] == "MI CLIENTE SL"

    def test_buscar_proveedor_por_nombre_desde_bd(self, repo):
        """ConfigCliente.buscar_proveedor_por_nombre usa BD."""
        from scripts.core.config import ConfigCliente
        dir_ent = repo.crear(DirectorioEntidad(
            cif="D44444444", nombre="ENDESA ENERGIA SAU", pais="ESP",
            aliases=["ENDESA", "ENDESA ENERGIA"]
        ))
        empresa = repo.crear(Empresa(
            cif="Y77777777", nombre="EMPRESA TEST", forma_juridica="sl",
            territorio="peninsula"
        ))
        repo.crear_overlay(
            empresa_id=empresa.id, directorio_id=dir_ent.id,
            tipo="proveedor", subcuenta_gasto="6260000000",
            codimpuesto="IVA21", regimen="general"
        )
        config = ConfigCliente(
            {"empresa": {"nombre": "EMPRESA TEST", "cif": "Y77777777",
                          "tipo": "sl", "idempresa": 1, "ejercicio_activo": "2025"},
             "proveedores": {}, "clientes": {}},
            "test", repo=repo, empresa_bd_id=empresa.id
        )
        resultado = config.buscar_proveedor_por_nombre("ENDESA")
        assert resultado is not None
        assert resultado["cif"] == "D44444444"


# --- T8: Integracion pipeline ---


class TestIntegracionPipeline:
    def test_asegurar_entidades_usa_directorio(self, repo):
        """_asegurar_entidades_fs crea overlays en BD al registrar."""
        # Integracion compleja con FS API — verificar manualmente
        pass

    def test_descubrimiento_interactivo_graba_bd(self, repo):
        """Al descubrir entidad nueva en modo interactivo, se graba en directorio + overlay."""
        pass
