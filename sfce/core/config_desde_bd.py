"""Genera un objeto ConfigCliente desde la BD, compatible con el pipeline."""
import json
from pathlib import Path
from sqlalchemy.orm import Session

from sfce.db.modelos import Empresa, ProveedorCliente
from sfce.core.config import ConfigCliente

# Mapa forma_juridica → tipo aceptado por ConfigCliente (a nivel de modulo para importar en tests)
_FORMA_A_TIPO: dict[str, str] = {
    "autonomo": "autonomo",
    "sl": "sl",
    "sa": "sa",
    "slp": "sl",
    "slu": "sl",
    "cb": "comunidad_bienes",
    "sc": "sociedad_civil",
    "scp": "sociedad_civil",
    "coop": "cooperativa",
    "cooperativa": "cooperativa",
    "asociacion": "asociacion",
    "comunidad": "comunidad_propietarios",
    "fundacion": "fundacion",
    "arrendador": "arrendador",
}


def generar_config_desde_bd(empresa_id: int, sesion: Session) -> ConfigCliente:
    """Carga la configuracion de una empresa desde la BD.

    Construye un dict compatible con la estructura de config.yaml y lo envuelve
    en un ConfigCliente. Util para el pipeline SFCE cuando la empresa no tiene
    config.yaml en disco (onboarding via web).

    Args:
        empresa_id: PK de la empresa en la tabla empresas.
        sesion: Sesion SQLAlchemy activa.

    Returns:
        ConfigCliente listo para usar en el pipeline.

    Raises:
        ValueError: si la empresa no existe en la BD.
    """
    empresa = sesion.get(Empresa, empresa_id)
    if not empresa:
        raise ValueError(f"Empresa {empresa_id} no encontrada en BD")

    # config_extra puede ser dict (JSON ya deserializado) o str
    config_extra = empresa.config_extra or {}
    if isinstance(config_extra, str):
        config_extra = json.loads(config_extra)

    perfil = config_extra.get("perfil", {})

    # Determinar idempresa_fs y codejercicio_fs
    # Preferir columnas directas; caer en config_extra como fallback
    idempresa_fs = (
        empresa.idempresa_fs
        or config_extra.get("idempresa_fs", empresa_id)
    )
    codejercicio_fs = (
        empresa.codejercicio_fs
        or config_extra.get("codejercicio_fs", str(empresa_id).zfill(4))
    )
    ejercicio_activo = str(config_extra.get("ejercicio_activo", "2025"))

    # Normalizar forma_juridica usando el mapa a nivel de modulo
    tipo_empresa = _FORMA_A_TIPO.get(
        (empresa.forma_juridica or "sl").lower(), "sl"
    )

    # Normalizar regimen_iva a REGIMENES validos
    _REGIMEN_IVA_A_REGIMEN = {
        "general": "general",
        "intracomunitario": "intracomunitario",
        "extracomunitario": "extracomunitario",
        "simplificado": "general",
        "recargo_equivalencia": "general",
        "modulos": "general",
        "exento": "general",
    }
    regimen_empresa = _REGIMEN_IVA_A_REGIMEN.get(
        (empresa.regimen_iva or "general").lower(), "general"
    )

    # Cargar proveedores y clientes
    entidades = (
        sesion.query(ProveedorCliente)
        .filter_by(empresa_id=empresa_id)
        .all()
    )

    proveedores_dict: dict = {}
    clientes_dict: dict = {}

    for entidad in entidades:
        # Normalizar pais: usar ESP si nulo
        pais = entidad.pais or "ESP"

        # Normalizar regimen
        regimen = _REGIMEN_IVA_A_REGIMEN.get(
            (entidad.regimen or "general").lower(), "general"
        )

        # Normalizar divisa: solo EUR/USD/GBP aceptados por ConfigCliente
        divisa = "EUR"

        # Subcuenta contrapartida (para proveedores: 400x; para clientes: 430x)
        subcuenta_contrapartida = entidad.subcuenta_contrapartida or (
            "4000000000" if entidad.tipo == "proveedor" else "4300000000"
        )

        entrada = {
            "cif": entidad.cif,
            "nombre": entidad.nombre,
            "nombre_fs": entidad.nombre,
            "tipo": entidad.tipo,
            "subcuenta_gasto": entidad.subcuenta_gasto or "6000000000",
            "subcuenta": subcuenta_contrapartida,
            "codimpuesto": entidad.codimpuesto or "IVA21",
            "regimen": regimen,
            "pais": pais,
            "divisa": divisa,
        }

        # Anadir aliases si los hay
        if entidad.aliases:
            entrada["aliases"] = entidad.aliases

        # Anadir retencion si aplica
        if entidad.retencion_pct:
            entrada["retencion_pct"] = float(entidad.retencion_pct)

        # Clave del dict: nombre limpio (compatible con busqueda por nombre_corto)
        clave = _normalizar_clave(entidad.nombre)

        if entidad.tipo == "cliente":
            clientes_dict[clave] = entrada
        else:
            proveedores_dict[clave] = entrada

    datos = {
        "empresa": {
            "nombre": empresa.nombre,
            "cif": empresa.cif,
            "tipo": tipo_empresa,
            "idempresa": idempresa_fs,
            "ejercicio_activo": ejercicio_activo,
            "codejercicio": codejercicio_fs,
            "territorio": empresa.territorio or "peninsula",
            "regimen_iva": regimen_empresa,
            "importador": perfil.get("importador", False),
            "exportador": perfil.get("exportador", False),
            "divisas_habituales": perfil.get("divisas_habituales", ["EUR"]),
            "recc":              config_extra.get("recc", False),
            "prorrata_historico": config_extra.get("prorrata_historico", {}),
            "bins_por_anyo":     config_extra.get("bins_por_anyo", {}),
            "tipo_is":           config_extra.get("tipo_is", 25),
            "es_erd":            config_extra.get("es_erd", False),
            "retencion_facturas_pct": config_extra.get("retencion_facturas_pct", None),
            "obligaciones_adicionales": config_extra.get("obligaciones_adicionales", []),
        },
        "proveedores": proveedores_dict,
        "clientes": clientes_dict,
        "tipos_cambio": config_extra.get("tipos_cambio", {}),
        "tolerancias": {
            "cuadre_asiento": 0.01,
            "comparacion_importes": 0.02,
            "confianza_minima": 85,
        },
    }

    return ConfigCliente(data=datos, ruta=Path(f"bd://empresa_{empresa_id}"))


def _normalizar_clave(nombre: str) -> str:
    """Genera clave corta normalizada a partir del nombre de una entidad.

    Elimina caracteres especiales y limita a 30 chars para compatibilidad
    con las claves de config.yaml.
    """
    import re
    clave = re.sub(r"[^A-Za-z0-9_\-]", "_", nombre.strip())
    return clave[:30].strip("_")
