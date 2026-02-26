"""Onboarding interactivo para alta de clientes nuevos.

Genera config.yaml completo y estructura de carpetas.
Se ejecuta UNA VEZ al dar de alta un cliente nuevo.

Uso:
  python scripts/onboarding.py
  python scripts/onboarding.py --desde-yaml plantilla.yaml
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).parent.parent

sys.path.insert(0, str(RAIZ))

from scripts.core.logger import crear_logger

logger = crear_logger("onboarding")


def _slugify(texto: str) -> str:
    """Convierte texto a slug para nombre de carpeta."""
    slug = texto.lower().strip()
    slug = re.sub(r'[áà]', 'a', slug)
    slug = re.sub(r'[éè]', 'e', slug)
    slug = re.sub(r'[íì]', 'i', slug)
    slug = re.sub(r'[óò]', 'o', slug)
    slug = re.sub(r'[úù]', 'u', slug)
    slug = re.sub(r'[ñ]', 'n', slug)
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


def _input_requerido(pregunta: str) -> str:
    """Pide input hasta obtener respuesta no vacia."""
    while True:
        resp = input(f"  {pregunta}: ").strip()
        if resp:
            return resp
        print("    (campo obligatorio)")


def _input_opcional(pregunta: str, defecto: str = "") -> str:
    """Pide input con valor por defecto."""
    sufijo = f" [{defecto}]" if defecto else ""
    resp = input(f"  {pregunta}{sufijo}: ").strip()
    return resp or defecto


def _input_opcion(pregunta: str, opciones: list, defecto: str = "") -> str:
    """Pide input con opciones predefinidas."""
    opciones_str = "/".join(opciones)
    sufijo = f" [{defecto}]" if defecto else ""
    while True:
        resp = input(f"  {pregunta} ({opciones_str}){sufijo}: ").strip().lower()
        if not resp and defecto:
            return defecto
        if resp in [o.lower() for o in opciones]:
            return resp
        print(f"    Opciones validas: {opciones_str}")


def _input_numero(pregunta: str, defecto: int = 0) -> int:
    """Pide input numerico."""
    while True:
        resp = input(f"  {pregunta} [{defecto}]: ").strip()
        if not resp:
            return defecto
        try:
            return int(resp)
        except ValueError:
            print("    Introduce un numero")


def _input_si_no(pregunta: str, defecto: bool = False) -> bool:
    """Pide si/no."""
    d = "s" if defecto else "n"
    resp = input(f"  {pregunta} (s/n) [{d}]: ").strip().lower()
    if not resp:
        return defecto
    return resp in ("s", "si", "yes", "y")


# === Secciones del cuestionario ===

def seccion_datos_basicos() -> dict:
    """SECCION 1: Datos basicos de la empresa."""
    print("\n" + "=" * 50)
    print("  SECCION 1: DATOS BASICOS")
    print("=" * 50)

    nombre = _input_requerido("Razon social")
    cif = _input_requerido("CIF/NIF").upper().replace(" ", "").replace("-", "")

    # Cargar tipos disponibles
    ruta_tipos = RAIZ / "reglas" / "tipos_entidad.yaml"
    tipos_disponibles = []
    if ruta_tipos.exists():
        with open(ruta_tipos, "r", encoding="utf-8") as f:
            tipos_data = yaml.safe_load(f)
        tipos_disponibles = list(tipos_data.get("tipos", {}).keys())
        print(f"\n  Tipos disponibles:")
        for t in tipos_disponibles:
            info = tipos_data["tipos"][t]
            print(f"    - {t}: {info.get('nombre', '')}")

    tipo = _input_opcion("Tipo de entidad", tipos_disponibles, "autonomo")

    direccion = _input_opcional("Direccion fiscal")
    cp = _input_opcional("Codigo postal")
    ciudad = _input_opcional("Ciudad")
    provincia = _input_opcional("Provincia")
    email = _input_opcional("Email")
    telefono = _input_opcional("Telefono")
    iban = _input_opcional("IBAN bancario")

    idempresa = _input_numero("ID empresa en FacturaScripts", 0)
    ejercicio = _input_opcional("Ejercicio activo", "2025")

    empresa = {
        "nombre": nombre,
        "cif": cif,
        "tipo": tipo,
        "idempresa": idempresa,
        "ejercicio_activo": ejercicio,
    }
    if direccion:
        empresa["direccion"] = direccion
    if cp:
        empresa["cp"] = cp
    if ciudad:
        empresa["ciudad"] = ciudad
    if provincia:
        empresa["provincia"] = provincia
    if email:
        empresa["email"] = email
    if telefono:
        empresa["telefono"] = telefono
    if iban:
        empresa["iban"] = iban

    return empresa


def seccion_actividades() -> dict:
    """SECCION 2: Actividades economicas."""
    print("\n" + "=" * 50)
    print("  SECCION 2: ACTIVIDADES ECONOMICAS")
    print("=" * 50)

    num = _input_numero("Numero de actividades economicas", 1)
    actividades = []

    for i in range(num):
        print(f"\n  --- Actividad {i+1} ---")
        actividad = {
            "codigo": _input_opcional("Codigo IAE/CNAE"),
            "descripcion": _input_requerido("Descripcion"),
            "iva_venta": _input_numero("IVA aplicable a ventas (%)", 21),
        }
        if actividad["iva_venta"] == 0:
            actividad["exenta"] = True
            actividad["base_legal"] = _input_opcional("Base legal exencion")
        else:
            actividad["exenta"] = False

        notas = _input_opcional("Notas especiales")
        if notas:
            actividad["notas"] = notas

        actividades.append(actividad)

    perfil = {
        "actividades": actividades,
    }

    # Prorrata si multiples actividades con IVA diferente
    if num > 1:
        ivas = {a["iva_venta"] for a in actividades}
        if len(ivas) > 1:
            print("\n  Tiene multiples actividades con IVA diferente.")
            tipo_prorrata = _input_opcion(
                "Tipo de prorrata",
                ["sectores_diferenciados", "prorrata_general"],
                "sectores_diferenciados"
            )
            perfil["prorrata"] = {
                "tipo": tipo_prorrata,
                "criterio_reparto": _input_opcional(
                    "Criterio de reparto para gastos compartidos",
                    "metros cuadrados"
                ),
            }

    return perfil


def seccion_regimen_fiscal() -> dict:
    """SECCION 3: Regimen fiscal."""
    print("\n" + "=" * 50)
    print("  SECCION 3: REGIMEN FISCAL")
    print("=" * 50)

    particularidades = []

    empleados = _input_si_no("¿Tiene empleados?")
    importador = _input_si_no("¿Importa bienes?")
    exportador = _input_si_no("¿Exporta bienes?")

    divisas = []
    if _input_si_no("¿Usa divisas extranjeras habitualmente?"):
        divisas_str = _input_opcional("Divisas habituales (separadas por coma)", "USD")
        divisas = [d.strip().upper() for d in divisas_str.split(",")]

    print("\n  Particularidades del negocio (texto libre, Enter para terminar):")
    while True:
        linea = input("    > ").strip()
        if not linea:
            break
        particularidades.append(linea)

    descripcion = _input_opcional("Descripcion breve del negocio (1-2 frases)")
    modelo_negocio = _input_opcional("Modelo de negocio (como opera)")

    perfil_extra = {
        "empleados": empleados,
        "importador": importador,
        "exportador": exportador,
    }
    if divisas:
        perfil_extra["divisas_habituales"] = divisas
    if particularidades:
        perfil_extra["particularidades"] = particularidades
    if descripcion:
        perfil_extra["descripcion"] = descripcion
    if modelo_negocio:
        perfil_extra["modelo_negocio"] = modelo_negocio

    return perfil_extra


def seccion_proveedores() -> dict:
    """SECCION 4: Proveedores conocidos."""
    print("\n" + "=" * 50)
    print("  SECCION 4: PROVEEDORES CONOCIDOS")
    print("=" * 50)

    num = _input_numero("Numero de proveedores habituales", 0)
    proveedores = {}

    for i in range(num):
        print(f"\n  --- Proveedor {i+1} ---")
        nombre_corto = _input_requerido("Nombre corto (clave, ej: 'amazon')")
        prov = {
            "cif": _input_requerido("CIF").upper().replace(" ", ""),
            "nombre_fs": _input_requerido("Nombre completo en FacturaScripts"),
            "pais": _input_opcional("Pais (codigo 3 letras)", "ESP").upper(),
            "divisa": _input_opcion("Divisa", ["EUR", "USD", "GBP"], "EUR").upper(),
            "subcuenta": _input_opcional("Subcuenta contable", "600"),
            "codimpuesto": _input_opcion("Codigo IVA", ["IVA0", "IVA4", "IVA10", "IVA21"], "IVA21"),
            "regimen": _input_opcion("Regimen IVA",
                                     ["general", "intracomunitario", "extracomunitario"],
                                     "general"),
        }

        # Autoliquidacion si intracomunitario
        if prov["regimen"] == "intracomunitario":
            if _input_si_no("¿Requiere autoliquidacion?", True):
                prov["autoliquidacion"] = {
                    "iva_pct": _input_numero("IVA autoliquidacion (%)", 21),
                    "subcuenta_soportado": _input_opcional("Subcuenta 472", "4720000000"),
                    "subcuenta_repercutido": _input_opcional("Subcuenta 477", "4770000000"),
                }

        notas = _input_opcional("Notas especiales")
        if notas:
            prov["notas"] = notas

        proveedores[nombre_corto] = prov

    return proveedores


def seccion_clientes() -> dict:
    """SECCION 5: Clientes conocidos."""
    print("\n" + "=" * 50)
    print("  SECCION 5: CLIENTES CONOCIDOS")
    print("=" * 50)

    num = _input_numero("Numero de clientes habituales", 0)
    clientes = {}

    for i in range(num):
        print(f"\n  --- Cliente {i+1} ---")
        nombre_corto = _input_requerido("Nombre corto (clave)")
        cli = {
            "cif": _input_requerido("CIF").upper().replace(" ", ""),
            "nombre_fs": _input_requerido("Nombre completo en FacturaScripts"),
            "pais": _input_opcional("Pais (codigo 3 letras)", "ESP").upper(),
            "divisa": _input_opcion("Divisa", ["EUR", "USD", "GBP"], "EUR").upper(),
            "codimpuesto": _input_opcion("Codigo IVA", ["IVA0", "IVA4", "IVA10", "IVA21"], "IVA21"),
            "regimen": _input_opcion("Regimen",
                                     ["general", "intracomunitario", "extracomunitario"],
                                     "general"),
        }
        clientes[nombre_corto] = cli

    return clientes


def crear_estructura_carpetas(ruta_cliente: Path, ejercicio: str):
    """Crea estructura de carpetas del cliente."""
    carpetas = [
        ruta_cliente / "inbox",
        ruta_cliente / "cuarentena",
        ruta_cliente / ejercicio / "procesado" / "T1",
        ruta_cliente / ejercicio / "procesado" / "T2",
        ruta_cliente / ejercicio / "procesado" / "T3",
        ruta_cliente / ejercicio / "procesado" / "T4",
        ruta_cliente / ejercicio / "auditoria",
        ruta_cliente / ejercicio / "modelos_fiscales",
    ]
    for carpeta in carpetas:
        carpeta.mkdir(parents=True, exist_ok=True)

    # Crear .gitkeep en carpetas vacias
    for carpeta in carpetas:
        gitkeep = carpeta / ".gitkeep"
        if not gitkeep.exists() and not any(carpeta.iterdir()):
            gitkeep.touch()

    logger.info(f"Estructura de carpetas creada en {ruta_cliente}")


def generar_config(empresa: dict, perfil: dict, perfil_extra: dict,
                    proveedores: dict, clientes: dict) -> dict:
    """Genera el dict completo de config.yaml."""
    config = {"empresa": empresa}

    # Perfil
    perfil_completo = {**perfil, **perfil_extra}
    if perfil_completo:
        config["perfil"] = perfil_completo

    # Proveedores
    if proveedores:
        config["proveedores"] = proveedores

    # Clientes
    if clientes:
        config["clientes"] = clientes

    # Tipos de cambio por defecto si hay divisas
    divisas = perfil_extra.get("divisas_habituales", [])
    if divisas:
        tipos_cambio = {}
        for d in divisas:
            if d != "EUR":
                tipos_cambio[f"{d}_EUR"] = 1.0
        if tipos_cambio:
            config["tipos_cambio"] = tipos_cambio

    # Tolerancias por defecto
    config["tolerancias"] = {
        "cuadre_asiento": 0.01,
        "comparacion_importes": 0.02,
        "confianza_minima": 85,
    }

    return config


def main():
    parser = argparse.ArgumentParser(
        description="Onboarding interactivo para alta de clientes SFCE"
    )
    parser.add_argument(
        "--desde-yaml",
        help="Importar datos desde un YAML plantilla existente"
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  SFCE — Onboarding de cliente nuevo")
    print("=" * 60)

    if args.desde_yaml:
        # Importar desde plantilla
        ruta_plantilla = Path(args.desde_yaml)
        if not ruta_plantilla.exists():
            logger.error(f"No existe plantilla: {ruta_plantilla}")
            return 1

        with open(ruta_plantilla, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        nombre = config_data.get("empresa", {}).get("nombre", "cliente")
        slug = _slugify(nombre)
        ejercicio = config_data.get("empresa", {}).get("ejercicio_activo", "2025")
    else:
        # Cuestionario interactivo
        empresa = seccion_datos_basicos()
        perfil = seccion_actividades()
        perfil_extra = seccion_regimen_fiscal()
        proveedores = seccion_proveedores()
        clientes = seccion_clientes()

        config_data = generar_config(empresa, perfil, perfil_extra,
                                      proveedores, clientes)
        slug = _slugify(empresa["nombre"])
        ejercicio = empresa.get("ejercicio_activo", "2025")

    # Crear carpeta y guardar config
    ruta_cliente = RAIZ / "clientes" / slug

    if ruta_cliente.exists():
        print(f"\n  La carpeta {ruta_cliente} ya existe.")
        if not _input_si_no("¿Sobreescribir config.yaml?"):
            print("  Cancelado.")
            return 0

    crear_estructura_carpetas(ruta_cliente, ejercicio)

    ruta_config = ruta_cliente / "config.yaml"
    with open(ruta_config, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, allow_unicode=True,
                  default_flow_style=False, sort_keys=False)

    print("\n" + "=" * 60)
    print(f"  Cliente creado: {slug}")
    print(f"  Config: {ruta_config}")
    print(f"  Carpeta: {ruta_cliente}")
    print("")
    print(f"  Para ejecutar el pipeline:")
    print(f"    python scripts/pipeline.py --cliente {slug} --ejercicio {ejercicio}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
