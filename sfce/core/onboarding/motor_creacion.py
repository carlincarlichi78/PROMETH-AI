"""Motor de creación de empresa desde PerfilEmpresa."""
from __future__ import annotations
import re
import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sfce.core.onboarding.perfil_empresa import PerfilEmpresa

logger = logging.getLogger(__name__)

_PGC_POR_TIPO = {
    "sl": "general", "sa": "general", "slp": "general", "slu": "general",
    "cb": "general", "sc": "general",
    "autonomo": "pymes",
    "comunidad": "pymes",
    "arrendador": "pymes",
    "asociacion": "esfl",
    "fundacion": "esfl",
    "coop": "cooperativas",
}

_SUBDIRS = ["inbox", "procesados", "cuarentena",
            "modelos_fiscales", "onboarding", "onboarding/libros_facturas"]


@dataclass
class ResultadoCreacion:
    empresa_id: Optional[int] = None
    idempresa_fs: Optional[int] = None
    slug: Optional[str] = None
    ok: bool = False
    errores: list = field(default_factory=list)


class MotorCreacion:
    def __init__(self, base_clientes: Path):
        self.base_clientes = Path(base_clientes)

    def verificar_cuota(self, gestoria, empresas_actuales: int,
                         total_lote: int) -> bool:
        """True si la gestoría tiene cuota para crear total_lote empresas más."""
        limite = getattr(gestoria, "limite_empresas", None)
        if limite is None:
            return True
        return (empresas_actuales + total_lote) <= limite

    def _generar_slug(self, perfil: PerfilEmpresa) -> str:
        nombre_limpio = re.sub(r"[^a-zA-Z0-9\s]", "", perfil.nombre.lower())
        nombre_limpio = re.sub(r"\s+", "-", nombre_limpio.strip())[:30]
        nif = perfil.nif.lower()
        slug = f"{nif}-{nombre_limpio}".strip("-")
        slug = re.sub(r"-+", "-", slug)
        return slug

    def _tipo_pgc(self, forma_juridica: str) -> str:
        return _PGC_POR_TIPO.get(forma_juridica.lower(), "general")

    def _crear_estructura_disco(self, slug: str,
                                 perfil: PerfilEmpresa) -> Path:
        base = self.base_clientes / slug
        base.mkdir(parents=True, exist_ok=True)
        for subdir in _SUBDIRS:
            (base / subdir).mkdir(parents=True, exist_ok=True)
        return base

    def _generar_config_yaml(self, slug: str, perfil: PerfilEmpresa,
                              idempresa_fs: int, codejercicio: str) -> Path:
        ruta = self.base_clientes / slug / "config.yaml"
        config = {
            "cliente": perfil.nombre,
            "cif": perfil.nif,
            "idempresa": idempresa_fs,
            "codejercicio": codejercicio,
            "ejercicio_activo": "2025",
            "tipo_entidad": perfil.forma_juridica,
            "territorio": perfil.territorio,
            "fiscal": {
                "regimen_iva": perfil.regimen_iva,
                "recc": perfil.recc,
                "prorrata": perfil.prorrata_historico or None,
                "es_erd": perfil.es_erd,
                "tipo_is": perfil.tipo_is,
                "presenta_modelos": _modelos_a_presentar(perfil),
            },
            "proveedores_habituales": {
                _slug_clave(p["nombre"]): {
                    "cif": p.get("cif", ""),
                    "nombre": p.get("nombre", ""),
                    "nombre_fs": p.get("nombre", ""),
                    "tipo": "proveedor",
                }
                for p in perfil.proveedores_habituales
            },
            "clientes_habituales": {
                _slug_clave(c["nombre"]): {
                    "cif": c.get("cif", ""),
                    "nombre": c.get("nombre", ""),
                    "nombre_fs": c.get("nombre", ""),
                    "tipo": "cliente",
                }
                for c in perfil.clientes_habituales
            },
        }
        ruta.write_text(
            yaml.dump(config, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        logger.info("config.yaml generado en %s", ruta)
        return ruta

    def crear_empresa_bd(self, perfil: PerfilEmpresa, gestoria_id: int,
                          sesion) -> int:
        """Crea la empresa en BD. Devuelve empresa.id."""
        from sfce.db.modelos import Empresa, EstadoOnboarding, OnboardingCliente
        slug = self._generar_slug(perfil)
        empresa = Empresa(
            cif=perfil.nif,
            nombre=perfil.nombre,
            forma_juridica=perfil.forma_juridica,
            territorio=perfil.territorio,
            regimen_iva=perfil.regimen_iva,
            slug=slug,
            gestoria_id=gestoria_id,
            estado_onboarding=EstadoOnboarding.CREADA_MASIVO,
            config_extra={
                "recc": perfil.recc,
                "prorrata_historico": perfil.prorrata_historico,
                "bins_por_anyo": perfil.bins_por_anyo,
                "bins_total": perfil.bins_total,
                "tipo_is": perfil.tipo_is,
                "es_erd": perfil.es_erd,
                "retencion_facturas_pct": perfil.retencion_facturas_pct,
                "obligaciones_adicionales": perfil.obligaciones_adicionales,
            },
        )
        sesion.add(empresa)
        sesion.flush()
        # Crear registro onboarding_cliente vacío
        oc = OnboardingCliente(empresa_id=empresa.id)
        sesion.add(oc)
        return empresa.id

    def crear_estructura_completa(
        self,
        perfil: PerfilEmpresa,
        gestoria_id: int,
        sesion,
        fs_setup,
        anio: int = 2025,
    ) -> ResultadoCreacion:
        resultado = ResultadoCreacion()
        try:
            empresa_id = self.crear_empresa_bd(perfil, gestoria_id, sesion)
            slug = self._generar_slug(perfil)
            self._crear_estructura_disco(slug, perfil)

            tipo_pgc = self._tipo_pgc(perfil.forma_juridica)
            r_fs = fs_setup.setup_completo(
                nombre=perfil.nombre,
                cif=perfil.nif,
                anio=anio,
                tipo_pgc=tipo_pgc,
            )
            # Actualizar empresa con datos FS
            from sfce.db.modelos import Empresa
            empresa = sesion.get(Empresa, empresa_id)
            empresa.idempresa_fs = r_fs.idempresa_fs
            empresa.codejercicio_fs = r_fs.codejercicio

            self._generar_config_yaml(
                slug, perfil, r_fs.idempresa_fs, r_fs.codejercicio)

            self._cargar_proveedores_bd(perfil, empresa_id, sesion)
            self._cargar_bienes_inversion(perfil, empresa_id, sesion)

            sesion.commit()

            resultado.empresa_id = empresa_id
            resultado.idempresa_fs = r_fs.idempresa_fs
            resultado.slug = slug
            resultado.ok = True
            logger.info("Empresa %s creada OK (id=%s, fs=%s)",
                        perfil.nif, empresa_id, r_fs.idempresa_fs)
        except Exception as exc:
            sesion.rollback()
            resultado.errores.append(str(exc))
            logger.error("Error creando empresa %s: %s", perfil.nif, exc)
        return resultado

    def _cargar_proveedores_bd(self, perfil: PerfilEmpresa,
                                empresa_id: int, sesion) -> None:
        from sfce.db.modelos import ProveedorCliente
        for p in perfil.proveedores_habituales:
            if not p.get("cif"):
                continue
            pv = ProveedorCliente(
                empresa_id=empresa_id,
                cif=p["cif"],
                nombre=p["nombre"],
                tipo="proveedor",
                subcuenta_gasto="6000000000",
            )
            sesion.add(pv)
        for c in perfil.clientes_habituales:
            if not c.get("cif"):
                continue
            cl = ProveedorCliente(
                empresa_id=empresa_id,
                cif=c["cif"],
                nombre=c["nombre"],
                tipo="cliente",
            )
            sesion.add(cl)

    def _cargar_bienes_inversion(self, perfil: PerfilEmpresa,
                                  empresa_id: int, sesion) -> None:
        if not perfil.bienes_inversion_iva:
            return
        from sqlalchemy import text
        for bien in perfil.bienes_inversion_iva:
            sesion.execute(text("""
                INSERT INTO bienes_inversion_iva
                  (empresa_id, descripcion, fecha_adquisicion,
                   precio_adquisicion, iva_soportado_deducido,
                   pct_deduccion_anyo_adquisicion, tipo_bien,
                   anyos_regularizacion_total, anyos_regularizacion_restantes)
                VALUES (:empresa_id, :desc, :fecha, :precio, :iva,
                        :pct, :tipo, :total, :restantes)
            """), {
                "empresa_id": empresa_id,
                "desc": bien.get("descripcion", ""),
                "fecha": bien.get("fecha_adquisicion"),
                "precio": bien.get("precio_adquisicion", 0),
                "iva": bien.get("iva_soportado_deducido", 0),
                "pct": bien.get("pct_deduccion_anyo_adquisicion", 100),
                "tipo": bien.get("tipo_bien", "resto"),
                "total": bien.get("anyos_regularizacion_total", 5),
                "restantes": bien.get("anyos_regularizacion_restantes", 5),
            })


def _modelos_a_presentar(perfil: PerfilEmpresa) -> list:
    modelos = []
    fj = perfil.forma_juridica
    if fj in ("sl", "sa", "slp", "slu", "coop"):
        modelos += ["303", "390", "200", "347"]
        if perfil.tiene_trabajadores:
            modelos += ["111", "190"]
    elif fj == "autonomo":
        modelos += ["303", "390", "130", "100", "347"]
        if perfil.tiene_trabajadores:
            modelos += ["111", "190"]
    elif fj == "comunidad":
        if perfil.tiene_trabajadores:
            modelos += ["111", "190"]
        modelos += ["347"]
    elif fj in ("asociacion", "fundacion"):
        modelos += ["347"]
    elif fj in ("cb", "sc"):
        modelos += ["303", "390", "184"]
    return modelos


def _slug_clave(nombre: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", nombre.strip())[:30]
