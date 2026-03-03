"""Cargador y validador de configuracion por cliente."""
import yaml
from pathlib import Path
from typing import Optional
from .logger import crear_logger
from .perfil_fiscal import PerfilFiscal

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


class ConfigCliente:
    """Configuracion cargada y validada de un cliente."""

    def __init__(self, data: dict, ruta: Path):
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
        self.trabajadores = data.get("trabajadores", [])

        # PerfilFiscal: desde seccion explica o derivado del tipo
        if "perfil_fiscal" in data:
            self.perfil_fiscal = PerfilFiscal.desde_dict(data["perfil_fiscal"])
        else:
            self.perfil_fiscal = self._generar_perfil_desde_tipo()

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
    def codagente_fs(self) -> str | None:
        """Codigo del agente FS asignado a esta empresa (para filtro por grupo de usuarios)."""
        return self.empresa.get("codagente_fs")

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

    def buscar_proveedor_por_cif(self, cif: str) -> Optional[dict]:
        """Busca proveedor en config por CIF (normalizado)."""
        cif_norm = _normalizar_cif(cif)
        for nombre, datos in self.proveedores.items():
            if _normalizar_cif(datos.get("cif", "")) == cif_norm:
                return {**datos, "_nombre_corto": nombre}
        return None

    def buscar_proveedor_por_nombre(self, nombre: str) -> Optional[dict]:
        """Busca proveedor por nombre o aliases."""
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
        """Busca cliente en config por CIF (normalizado)."""
        cif_norm = _normalizar_cif(cif)
        for nombre, datos in self.clientes.items():
            if _normalizar_cif(datos.get("cif", "")) == cif_norm:
                return {**datos, "_nombre_corto": nombre}
        return None

    def buscar_cliente_por_nombre(self, nombre: str) -> Optional[dict]:
        """Busca cliente por nombre o aliases (case-insensitive, coincidencia parcial)."""
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

    def buscar_cliente_fallback_sin_cif(self) -> Optional[dict]:
        """Devuelve el cliente marcado como fallback_sin_cif (ej: CLIENTES VARIOS).

        Se usa cuando una FV no tiene receptor CIF identificable.
        Criterio RD 1619/2012: facturas simplificadas sin NIF receptor.
        """
        for clave, datos in self.clientes.items():
            if datos.get("fallback_sin_cif"):
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

    def buscar_trabajador_por_dni(self, dni: str) -> Optional[dict]:
        """Busca trabajador por DNI."""
        for trab in self.trabajadores:
            if trab.get("dni") == dni:
                return trab
        return None

    def agregar_trabajador(self, dni: str, nombre: str, bruto_mensual: float,
                           pagas: int = 14) -> dict:
        """Agrega o actualiza un trabajador en la lista en memoria y en el YAML en disco.

        Si ya existe un trabajador con el mismo DNI, actualiza sus datos.
        Siempre marca el trabajador como confirmado=True.

        Args:
            dni: DNI del trabajador.
            nombre: Nombre completo.
            bruto_mensual: Salario bruto mensual en EUR.
            pagas: Numero de pagas anuales (defecto 14).

        Returns:
            dict con los datos del trabajador agregado/actualizado.
        """
        nuevo = {
            "dni": dni,
            "nombre": nombre,
            "bruto_mensual": bruto_mensual,
            "pagas": pagas,
            "confirmado": True,
        }

        # Actualizar en memoria: si ya existe el DNI, reemplazar; si no, agregar
        indice_existente = next(
            (i for i, t in enumerate(self.trabajadores) if t.get("dni") == dni),
            None,
        )
        if indice_existente is not None:
            self.trabajadores[indice_existente] = nuevo
        else:
            self.trabajadores.append(nuevo)

        # Persistir en disco: leer YAML actual, sustituir seccion trabajadores, reescribir
        with open(self.ruta, "r", encoding="utf-8") as f:
            data_yaml = yaml.safe_load(f) or {}

        data_yaml["trabajadores"] = self.trabajadores

        with open(self.ruta, "w", encoding="utf-8") as f:
            yaml.dump(data_yaml, f, allow_unicode=True, default_flow_style=False)

        logger.info(f"Trabajador {dni} ({nombre}) guardado en {self.ruta}")
        return nuevo

    def _generar_perfil_desde_tipo(self) -> PerfilFiscal:
        """Genera PerfilFiscal basico a partir del campo empresa.tipo."""
        _TIPO_A_FORMA = {
            "sl": "sl", "sa": "sa", "autonomo": "autonomo",
            "comunidad_propietarios": "comunidad_propietarios",
            "asociacion": "asociacion", "comunidad_bienes": "cb",
            "cooperativa": "cooperativa", "fundacion": "asociacion",
            "sociedad_civil": "scp",
        }
        forma = _TIPO_A_FORMA.get(self.tipo, "sl")
        return PerfilFiscal(forma_juridica=forma)


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
