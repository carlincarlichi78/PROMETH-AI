"""Cargador y validador de configuracion por cliente."""
import re
import yaml
from pathlib import Path
from typing import Optional
from .logger import crear_logger

logger = crear_logger("config")

# Campos obligatorios por seccion
CAMPOS_EMPRESA = {"nombre", "cif", "tipo", "idempresa", "ejercicio_activo"}
CAMPOS_PROVEEDOR = {"cif", "nombre_fs", "pais", "divisa", "subcuenta", "codimpuesto", "regimen"}
CAMPOS_CLIENTE = {"cif", "nombre_fs", "pais", "divisa", "codimpuesto", "regimen"}
TIPOS_EMPRESA = {"sl", "autonomo", "sa", "comunidad_propietarios", "asociacion",
                 "comunidad_bienes", "cooperativa", "fundacion", "sociedad_civil"}
REGIMENES = {"general", "intracomunitario", "extracomunitario"}
DIVISAS = {"EUR", "USD", "GBP"}
PAISES_UE = {
    "AUT", "BEL", "BGR", "CYP", "CZE", "DEU", "DNK", "ESP", "EST",
    "FIN", "FRA", "GRC", "HRV", "HUN", "IRL", "ITA", "LTU", "LUX",
    "LVA", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "SWE"
}


def _normalizar_cif(cif: str) -> str:
    """Normaliza CIF removiendo espacios, puntos y guiones para comparacion."""
    import re
    return re.sub(r'[\s\.\-/]', '', cif).upper()


def _slugificar(nombre: str) -> str:
    """Convierte nombre a slug (minusculas, guiones, sin acentos)."""
    slug = nombre.lower().strip()
    slug = re.sub(r'[áà]', 'a', slug)
    slug = re.sub(r'[éè]', 'e', slug)
    slug = re.sub(r'[íì]', 'i', slug)
    slug = re.sub(r'[óò]', 'o', slug)
    slug = re.sub(r'[úù]', 'u', slug)
    slug = re.sub(r'[ñ]', 'n', slug)
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')


class ConfigCliente:
    """Configuracion cargada y validada de un cliente."""

    def __init__(self, data: dict, ruta: Path, repo=None, empresa_bd_id: int = None):
        self.data = data
        self.ruta = ruta
        self.empresa = data.get("empresa", {})
        self.proveedores = data.get("proveedores", {})
        self.clientes = data.get("clientes", {})
        self.tipos_cambio = data.get("tipos_cambio", {})
        self.tolerancias = data.get("tolerancias", {
            "cuadre_asiento": 0.01,
            "comparacion_importes": 0.02,
            "confianza_minima": 85
        })
        self._tipo_entidad = None
        self._repo = repo
        self._empresa_bd_id = empresa_bd_id

    @property
    def nombre(self) -> str:
        return self.empresa.get("nombre", "")

    @property
    def cif(self) -> str:
        return self.empresa.get("cif", "")

    @property
    def tipo(self) -> str:
        return self.empresa.get("tipo", "sl")

    @property
    def idempresa(self) -> int:
        return self.empresa.get("idempresa", 1)

    @property
    def ejercicio(self) -> str:
        return self.empresa.get("ejercicio_activo", "2025")

    @property
    def codejercicio(self) -> str:
        """Codigo de ejercicio en FS (puede diferir del ano, ej: '0004' vs '2025')."""
        return self.empresa.get("codejercicio", self.ejercicio)

    @property
    def obligaciones(self) -> dict:
        """Devuelve obligaciones fiscales/contables segun tipo de entidad."""
        return self._tipo_entidad or {}

    @property
    def modelos_trimestrales(self) -> list:
        return self.obligaciones.get("modelos_trimestrales", [])

    @property
    def modelos_anuales(self) -> list:
        return self.obligaciones.get("modelos_anuales", [])

    @property
    def sujeto_iva(self) -> bool:
        return self.obligaciones.get("sujeto_iva", True)

    @property
    def sujeto_is(self) -> bool:
        return self.obligaciones.get("sujeto_is", False)

    @property
    def libros_obligatorios(self) -> list:
        return self.obligaciones.get("libros_obligatorios", [])

    def _overlay_a_dict(self, overlay) -> dict:
        """Convierte overlay SQLAlchemy a dict compatible con interfaz YAML."""
        nombre_corto = _slugificar(overlay.nombre)
        return {
            "cif": overlay.cif,
            "nombre_fs": overlay.nombre,
            "pais": overlay.pais or "ESP",
            "divisa": "EUR",
            "subcuenta": overlay.subcuenta_gasto or "",
            "codimpuesto": overlay.codimpuesto or "IVA21",
            "regimen": overlay.regimen or "general",
            "aliases": overlay.aliases or [],
            "_nombre_corto": nombre_corto,
        }

    def buscar_proveedor_por_cif(self, cif: str) -> Optional[dict]:
        """Busca proveedor por CIF. BD primero, fallback YAML."""
        if self._repo and self._empresa_bd_id:
            cif_norm = _normalizar_cif(cif)
            if cif_norm:
                overlay = self._repo.buscar_overlay_por_cif(
                    self._empresa_bd_id, cif_norm, "proveedor"
                )
                if overlay:
                    return self._overlay_a_dict(overlay)
        # Fallback YAML
        cif_norm = _normalizar_cif(cif)
        for nombre, datos in self.proveedores.items():
            if _normalizar_cif(datos.get("cif", "")) == cif_norm:
                return {**datos, "_nombre_corto": nombre}
        return None

    def buscar_proveedor_por_nombre(self, nombre: str) -> Optional[dict]:
        """Busca proveedor por nombre o aliases. BD primero, fallback YAML."""
        if self._repo and self._empresa_bd_id:
            from sfce.db.repositorio import Repositorio
            resultado = self._repo.buscar_directorio_por_nombre(nombre)
            if resultado:
                overlay = self._repo.buscar_overlay_por_cif(
                    self._empresa_bd_id, resultado.cif or "", "proveedor"
                )
                if overlay:
                    return self._overlay_a_dict(overlay)
        # Fallback YAML
        nombre_upper = nombre.upper()
        for clave, datos in self.proveedores.items():
            if clave.upper() == nombre_upper:
                return {**datos, "_nombre_corto": clave}
            if datos.get("nombre_fs", "").upper() == nombre_upper:
                return {**datos, "_nombre_corto": clave}
            for alias in datos.get("aliases", []):
                if alias.upper() == nombre_upper:
                    return {**datos, "_nombre_corto": clave}
        return None

    def buscar_cliente_por_cif(self, cif: str) -> Optional[dict]:
        """Busca cliente por CIF. BD primero, fallback YAML."""
        cif_norm = _normalizar_cif(cif)
        if not cif_norm:
            return None
        if self._repo and self._empresa_bd_id:
            overlay = self._repo.buscar_overlay_por_cif(
                self._empresa_bd_id, cif_norm, "cliente"
            )
            if overlay:
                return self._overlay_a_dict(overlay)
        # Fallback YAML
        for nombre, datos in self.clientes.items():
            cif_config = _normalizar_cif(datos.get("cif", ""))
            if cif_config and cif_config == cif_norm:
                return {**datos, "_nombre_corto": nombre}
        return None

    def buscar_cliente_por_nombre(self, nombre: str) -> Optional[dict]:
        """Busca cliente por nombre o aliases. BD primero, fallback YAML."""
        if self._repo and self._empresa_bd_id:
            resultado = self._repo.buscar_directorio_por_nombre(nombre)
            if resultado:
                overlay = self._repo.buscar_overlay_por_cif(
                    self._empresa_bd_id, resultado.cif or "", "cliente"
                )
                if overlay:
                    return self._overlay_a_dict(overlay)
        # Fallback YAML
        nombre_upper = nombre.upper()
        for clave, datos in self.clientes.items():
            if clave.upper() == nombre_upper:
                return {**datos, "_nombre_corto": clave}
            if datos.get("nombre_fs", "").upper() == nombre_upper:
                return {**datos, "_nombre_corto": clave}
            for alias in datos.get("aliases", []):
                if alias.upper() in nombre_upper or nombre_upper in alias.upper():
                    return {**datos, "_nombre_corto": clave}
        return None

    def es_intracomunitario(self, nombre_prov: str) -> bool:
        """Verifica si proveedor es intracomunitario."""
        for clave, datos in self.proveedores.items():
            if clave.upper() == nombre_prov.upper():
                return datos.get("regimen") == "intracomunitario"
        return False

    def tiene_autoliquidacion(self, nombre_prov: str) -> bool:
        """Verifica si proveedor requiere autoliquidacion."""
        for clave, datos in self.proveedores.items():
            if clave.upper() == nombre_prov.upper():
                return "autoliquidacion" in datos
        return False

    def reglas_especiales(self, nombre_prov: str) -> list:
        """Devuelve reglas especiales del proveedor."""
        for clave, datos in self.proveedores.items():
            if clave.upper() == nombre_prov.upper():
                return datos.get("reglas_especiales", [])
        return []

    def tc_defecto(self, divisa: str) -> float:
        """Devuelve tipo de cambio por defecto para una divisa."""
        clave = f"{divisa}_EUR"
        return self.tipos_cambio.get(clave, 1.0)


def cargar_config(ruta_cliente: Path) -> ConfigCliente:
    """Carga y valida config.yaml de un cliente.

    Args:
        ruta_cliente: ruta a la carpeta del cliente

    Returns:
        ConfigCliente validado

    Raises:
        FileNotFoundError: si no existe config.yaml
        ValueError: si la config tiene errores de validacion
    """
    ruta_config = ruta_cliente / "config.yaml"

    if not ruta_config.exists():
        raise FileNotFoundError(f"No existe {ruta_config}")

    with open(ruta_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    errores = validar_config(data)
    if errores:
        for e in errores:
            logger.error(f"Config invalida: {e}")
        raise ValueError(f"Config {ruta_config} tiene {len(errores)} errores")

    config = ConfigCliente(data, ruta_config)

    # Cargar tipo de entidad desde catalogo
    ruta_tipos = Path(__file__).parent.parent.parent / "reglas" / "tipos_entidad.yaml"
    if ruta_tipos.exists():
        with open(ruta_tipos, "r", encoding="utf-8") as f:
            tipos_data = yaml.safe_load(f)
        tipo = config.tipo
        if tipo in tipos_data.get("tipos", {}):
            config._tipo_entidad = tipos_data["tipos"][tipo]
        else:
            logger.warning(f"Tipo '{tipo}' no encontrado en catalogo tipos_entidad.yaml")

    logger.info(f"Config cargada: {data['empresa']['nombre']}")
    return config


def validar_config(data: dict) -> list[str]:
    """Valida estructura y contenido del config.yaml.

    Returns:
        Lista de errores (vacia si todo OK)
    """
    errores = []

    # Empresa
    if "empresa" not in data:
        errores.append("Falta seccion 'empresa'")
        return errores

    empresa = data["empresa"]
    faltantes = CAMPOS_EMPRESA - set(empresa.keys())
    if faltantes:
        errores.append(f"Empresa: faltan campos {faltantes}")

    if empresa.get("tipo") not in TIPOS_EMPRESA:
        errores.append(f"Empresa: tipo '{empresa.get('tipo')}' no valido. Usar: {TIPOS_EMPRESA}")

    # Proveedores
    for nombre, prov in data.get("proveedores", {}).items():
        faltantes = CAMPOS_PROVEEDOR - set(prov.keys())
        if faltantes:
            errores.append(f"Proveedor {nombre}: faltan campos {faltantes}")

        if prov.get("regimen") not in REGIMENES:
            errores.append(f"Proveedor {nombre}: regimen '{prov.get('regimen')}' no valido")

        if prov.get("divisa") not in DIVISAS:
            errores.append(f"Proveedor {nombre}: divisa '{prov.get('divisa')}' no valida")

        if prov.get("regimen") == "intracomunitario" and prov.get("pais") not in PAISES_UE:
            errores.append(f"Proveedor {nombre}: pais '{prov.get('pais')}' no es UE pero regimen es intracomunitario")

        # Autoliquidacion solo si intracomunitario
        if "autoliquidacion" in prov and prov.get("regimen") != "intracomunitario":
            errores.append(f"Proveedor {nombre}: autoliquidacion solo aplica a intracomunitarios")

    # Clientes
    for nombre, cli in data.get("clientes", {}).items():
        faltantes = CAMPOS_CLIENTE - set(cli.keys())
        if faltantes:
            errores.append(f"Cliente {nombre}: faltan campos {faltantes}")

    return errores
