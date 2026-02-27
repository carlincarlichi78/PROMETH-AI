"""SFCE — Migrador FacturaScripts -> BD local.

Script one-time para cargar datos existentes de FS en la BD local.
Lee via API REST y crea registros en SQLite.

Uso:
  export FS_API_TOKEN='...'
  python scripts/migrar_fs_a_bd.py --empresa 1 --ejercicio 2025 --bd sfce.db
"""
import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))

from scripts.core.logger import crear_logger
from scripts.core.fs_api import api_get

from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.modelos import (
    Empresa, ProveedorCliente, Asiento, Partida, Factura, AuditLog,
)
from sfce.db.repositorio import Repositorio

logger = crear_logger("migrador")


class Migrador:
    """Migra datos de FacturaScripts a BD local."""

    def __init__(self, repo, idempresa_fs: int, ejercicio: str):
        self.repo = repo
        self.idempresa_fs = idempresa_fs
        self.ejercicio = ejercicio
        self.empresa_id = None
        self.stats = {
            "proveedores": 0, "clientes": 0,
            "asientos": 0, "partidas": 0, "facturas": 0,
        }

    def ejecutar(self) -> dict:
        """Ejecuta migracion completa."""
        logger.info(f"Migrando empresa FS {self.idempresa_fs}, ejercicio {self.ejercicio}")

        # 1. Crear/obtener empresa
        self._migrar_empresa()

        # 2. Proveedores y clientes
        self._migrar_proveedores()
        self._migrar_clientes()

        # 3. Asientos y partidas
        self._migrar_asientos()

        # 4. Facturas
        self._migrar_facturas_proveedor()
        self._migrar_facturas_cliente()

        logger.info(f"Migracion completada: {self.stats}")
        return self.stats

    def _migrar_empresa(self):
        """Crea empresa en BD local si no existe."""
        # Buscar info de la empresa en FS
        empresas = api_get("empresas", {})
        info = None
        for emp in empresas:
            if emp.get("idempresa") == self.idempresa_fs:
                info = emp
                break

        if not info:
            raise ValueError(f"Empresa {self.idempresa_fs} no encontrada en FS")

        cif = info.get("cifnif", f"MIGRADO-{self.idempresa_fs}")
        existente = self.repo.buscar_empresa_por_cif(cif)
        if existente:
            self.empresa_id = existente.id
            logger.info(f"Empresa ya existe en BD local: {existente.nombre}")
            return

        emp = Empresa(
            cif=cif,
            nombre=info.get("nombre", ""),
            forma_juridica="sl",  # default, ajustar manualmente
            idempresa_fs=self.idempresa_fs,
        )
        emp = self.repo.crear(emp)
        self.empresa_id = emp.id
        logger.info(f"Empresa creada: {emp.nombre}")

    def _migrar_proveedores(self):
        """Migra proveedores de FS."""
        proveedores = api_get("proveedores", {})
        for prov in proveedores:
            cif = prov.get("cifnif", "")
            if not cif:
                continue
            existente = self.repo.buscar_proveedor_por_cif(self.empresa_id, cif)
            if existente:
                continue
            nuevo = ProveedorCliente(
                empresa_id=self.empresa_id,
                cif=cif,
                nombre=prov.get("nombre", ""),
                tipo="proveedor",
                persona_fisica=bool(prov.get("personafisica")),
                pais=prov.get("codpais"),
            )
            try:
                self.repo.crear(nuevo)
                self.stats["proveedores"] += 1
            except Exception as e:
                logger.warning(f"Error proveedor {cif}: {e}")

    def _migrar_clientes(self):
        """Migra clientes de FS."""
        clientes = api_get("clientes", {})
        for cli in clientes:
            cif = cli.get("cifnif", "")
            if not cif:
                continue
            nuevo = ProveedorCliente(
                empresa_id=self.empresa_id,
                cif=cif,
                nombre=cli.get("nombre", ""),
                tipo="cliente",
                persona_fisica=bool(cli.get("personafisica")),
                pais=cli.get("codpais"),
            )
            try:
                self.repo.crear(nuevo)
                self.stats["clientes"] += 1
            except Exception:
                pass  # Duplicado

    def _migrar_asientos(self):
        """Migra asientos y partidas de FS."""
        asientos_fs = api_get("asientos", {})
        partidas_fs = api_get("partidas", {})

        # Post-filtrar por empresa (filtro no funciona en API)
        asientos_empresa = [a for a in asientos_fs
                            if str(a.get("idempresa")) == str(self.idempresa_fs)]

        ids_asientos = {a["idasiento"] for a in asientos_empresa}

        for asiento_fs in asientos_empresa:
            asiento = Asiento(
                empresa_id=self.empresa_id,
                numero=asiento_fs.get("numero"),
                fecha=self._parsear_fecha(asiento_fs.get("fecha")),
                concepto=asiento_fs.get("concepto", ""),
                idasiento_fs=asiento_fs.get("idasiento"),
                ejercicio=self.ejercicio,
                origen="migrado_fs",
                sincronizado_fs=True,
            )
            asiento = self.repo.crear(asiento)
            self.stats["asientos"] += 1

            # Partidas de este asiento
            partidas_asiento = [p for p in partidas_fs
                                if p.get("idasiento") == asiento_fs.get("idasiento")]
            for part_fs in partidas_asiento:
                partida = Partida(
                    asiento_id=asiento.id,
                    subcuenta=part_fs.get("codsubcuenta", ""),
                    debe=Decimal(str(part_fs.get("debe", 0))),
                    haber=Decimal(str(part_fs.get("haber", 0))),
                    concepto=part_fs.get("concepto", ""),
                    idpartida_fs=part_fs.get("idpartida"),
                )
                self.repo.crear(partida)
                self.stats["partidas"] += 1

    def _migrar_facturas_proveedor(self):
        """Migra facturas de proveedor."""
        facturas = api_get("facturaproveedores", {})
        facturas_empresa = [f for f in facturas
                            if str(f.get("idempresa")) == str(self.idempresa_fs)]

        for fac in facturas_empresa:
            from sfce.db.modelos import Documento
            doc = Documento(
                empresa_id=self.empresa_id,
                tipo_doc="FC",
                estado="registrado",
                factura_id_fs=fac.get("idfactura"),
                ejercicio=self.ejercicio,
            )
            doc = self.repo.crear(doc)

            factura = Factura(
                documento_id=doc.id,
                empresa_id=self.empresa_id,
                tipo="recibida",
                numero_factura=fac.get("numproveedor", fac.get("codigo")),
                fecha_factura=self._parsear_fecha(fac.get("fecha")),
                cif_emisor=fac.get("cifnif", ""),
                nombre_emisor=fac.get("nombre", ""),
                base_imponible=Decimal(str(fac.get("neto", 0))),
                iva_importe=Decimal(str(fac.get("totaliva", 0))),
                irpf_importe=Decimal(str(fac.get("totalirpf", 0))),
                total=Decimal(str(fac.get("total", 0))),
                pagada=bool(fac.get("pagada")),
                idfactura_fs=fac.get("idfactura"),
            )
            self.repo.crear(factura)
            self.stats["facturas"] += 1

    def _migrar_facturas_cliente(self):
        """Migra facturas de cliente (emitidas)."""
        facturas = api_get("facturaclientes", {})
        facturas_empresa = [f for f in facturas
                            if str(f.get("idempresa")) == str(self.idempresa_fs)]

        for fac in facturas_empresa:
            from sfce.db.modelos import Documento
            doc = Documento(
                empresa_id=self.empresa_id,
                tipo_doc="FV",
                estado="registrado",
                factura_id_fs=fac.get("idfactura"),
                ejercicio=self.ejercicio,
            )
            doc = self.repo.crear(doc)

            factura = Factura(
                documento_id=doc.id,
                empresa_id=self.empresa_id,
                tipo="emitida",
                numero_factura=fac.get("codigo"),
                fecha_factura=self._parsear_fecha(fac.get("fecha")),
                cif_receptor=fac.get("cifnif", ""),
                nombre_receptor=fac.get("nombre", ""),
                base_imponible=Decimal(str(fac.get("neto", 0))),
                iva_importe=Decimal(str(fac.get("totaliva", 0))),
                total=Decimal(str(fac.get("total", 0))),
                pagada=bool(fac.get("pagada")),
                idfactura_fs=fac.get("idfactura"),
            )
            self.repo.crear(factura)
            self.stats["facturas"] += 1

    def _parsear_fecha(self, fecha_str) -> date:
        """Parsea fecha string a date."""
        if not fecha_str:
            return date.today()
        try:
            return date.fromisoformat(str(fecha_str)[:10])
        except ValueError:
            return date.today()


def main():
    parser = argparse.ArgumentParser(description="Migrar FS -> BD local")
    parser.add_argument("--empresa", type=int, required=True, help="idempresa en FS")
    parser.add_argument("--ejercicio", required=True, help="Ejercicio (ej: 2025)")
    parser.add_argument("--bd", default="sfce.db", help="Ruta BD SQLite")
    args = parser.parse_args()

    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": args.bd})
    inicializar_bd(engine)
    factory = crear_sesion(engine)
    repo = Repositorio(factory)

    migrador = Migrador(repo, args.empresa, args.ejercicio)
    stats = migrador.ejecutar()
    print(f"\nMigracion completada: {stats}")


if __name__ == "__main__":
    main()
