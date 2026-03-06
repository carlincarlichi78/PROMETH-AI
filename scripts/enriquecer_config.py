"""Enriquecimiento automático de config.yaml con campos avanzados vía GPT-4o.

Para cada proveedor/cliente que le falten campos avanzados (formato_pdf, frecuencia,
importe_rango, concepto_keywords, validacion, asiento), consulta GPT-4o y mergea
los campos nuevos sin pisar los existentes.

Uso:
    python scripts/enriquecer_config.py --cliente maria-isabel-navarro-lopez [--dry-run] [--force]
"""
import argparse
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_MODELO = "gpt-4o"
_TIMEOUT = 30
_MAX_RETRIES = 1

_CAMPOS_AVANZADOS_PROVEEDOR = {
    "formato_pdf", "frecuencia", "importe_rango", "concepto_keywords",
    "validacion", "asiento",
}

_CAMPOS_AVANZADOS_CLIENTE = {
    "frecuencia", "importe_rango", "concepto_keywords", "validacion",
}

_RAIZ = Path(__file__).parent.parent
_RUTA_CATEGORIAS = _RAIZ / "reglas" / "categorias_gasto.yaml"


# ---------------------------------------------------------------------------
# Carga de categorías (reutiliza patrón de proveedor_discovery.py)
# ---------------------------------------------------------------------------

def _cargar_categorias(ruta: Path) -> list[dict]:
    with open(ruta, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    categorias = []
    for nombre, cat in data.get("categorias", {}).items():
        categorias.append({
            "nombre": nombre,
            "descripcion": cat.get("descripcion", ""),
            "subcuenta": cat.get("subcuenta", ""),
            "codimpuesto": cat.get("iva_codimpuesto", "IVA21"),
            "keywords": cat.get("keywords_proveedor", []),
        })
    return categorias


def _resumen_categorias(categorias: list[dict]) -> str:
    return "\n".join(
        f"- {c['nombre']}: {c['descripcion']} | subcuenta={c['subcuenta']} | {c['codimpuesto']}"
        + (f" | keywords: {', '.join(str(k) for k in c['keywords'][:5])}"
           if c['keywords'] else "")
        for c in categorias
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def _prompt_proveedor(entidad: dict, perfil: dict, cats_texto: str) -> str:
    return (
        "Eres un asesor fiscal español experto en contabilidad de autónomos y pymes.\n\n"
        "PROVEEDOR:\n"
        f"- CIF: {entidad.get('cif', '')}\n"
        f"- Nombre: {entidad.get('nombre_fs', '')}\n"
        f"- Subcuenta actual: {entidad.get('subcuenta', '')}\n"
        f"- codimpuesto: {entidad.get('codimpuesto', '')}\n"
        f"- Régimen: {entidad.get('regimen', 'general')}\n"
        f"- Notas: {entidad.get('notas', '')}\n\n"
        "PERFIL DEL CLIENTE:\n"
        f"- Nombre: {perfil.get('nombre', '')}\n"
        f"- Tipo: {perfil.get('tipo', '')}\n"
        f"- Régimen IVA: {perfil.get('regimen_iva', 'general')}\n"
        f"- Descripción: {perfil.get('descripcion', '')}\n\n"
        "CATEGORÍAS DE GASTO DISPONIBLES:\n"
        f"{cats_texto}\n\n"
        "INSTRUCCIONES:\n"
        "Genera SOLO un JSON válido (sin markdown) con estos campos exactos:\n"
        "{\n"
        '  "formato_pdf": "digital|escaneado|ticket_termico",\n'
        '  "frecuencia": "diario|semanal|quincenal|mensual|trimestral|anual|puntual",\n'
        '  "importe_rango": [min, max],\n'
        '  "concepto_keywords": ["kw1", "kw2", ...],\n'
        '  "persona_fisica": true/false,\n'
        '  "validacion": {\n'
        '    "iva_esperado": [21],\n'
        '    "irpf_obligatorio": false,\n'
        '    "total_max": 500,\n'
        '    "deducibilidad_iva": 100,\n'
        '    "deducibilidad_gasto": 100\n'
        '  },\n'
        '  "asiento": {\n'
        '    "subcuenta_gasto": "6280000000",\n'
        '    "intracom": false\n'
        '  }\n'
        "}\n\n"
        "REGLAS:\n"
        "- Si es intracomunitario (régimen intracomunitario o país UE no ESP), "
        "asiento.intracom=true y añadir asiento.iva_autorepercusion=21\n"
        "- Si persona_fisica=true y tiene IRPF (codretencion), "
        "añadir asiento.subcuenta_irpf=\"4751000000\"\n"
        "- importe_rango: estimación razonable [min, max] en euros\n"
        "- concepto_keywords: 3-6 palabras clave que aparecerían en sus facturas\n"
        "- formato_pdf: digital para empresas grandes, ticket_termico para gasolineras/peajes, "
        "escaneado para oficinas pequeñas\n"
        "- subcuenta_gasto en asiento: usar la subcuenta que ya tiene el proveedor "
        f"({entidad.get('subcuenta', '')}), solo cambiar si es incorrecta\n"
        "- Responde SOLO con JSON válido, sin explicaciones."
    )


def _prompt_cliente(entidad: dict, perfil: dict) -> str:
    return (
        "Eres un asesor fiscal español experto en contabilidad de autónomos y pymes.\n\n"
        "CLIENTE (a quien facturamos):\n"
        f"- CIF: {entidad.get('cif', '')}\n"
        f"- Nombre: {entidad.get('nombre_fs', '')}\n"
        f"- codimpuesto: {entidad.get('codimpuesto', '')}\n"
        f"- Régimen: {entidad.get('regimen', 'general')}\n"
        f"- IRPF que retienen: {entidad.get('irpf_que_retienen', 'no')}\n"
        f"- Notas: {entidad.get('notas', '')}\n\n"
        "PERFIL DEL EMISOR (nosotros):\n"
        f"- Nombre: {perfil.get('nombre', '')}\n"
        f"- Tipo: {perfil.get('tipo', '')}\n"
        f"- Régimen IVA: {perfil.get('regimen_iva', 'general')}\n"
        f"- Descripción: {perfil.get('descripcion', '')}\n\n"
        "INSTRUCCIONES:\n"
        "Genera SOLO un JSON válido (sin markdown) con estos campos exactos:\n"
        "{\n"
        '  "subcuenta_cliente": "4300000001",\n'
        '  "subcuenta_ingreso": "7050000000",\n'
        '  "irpf_que_retienen": 15,\n'
        '  "frecuencia": "mensual|trimestral|anual|puntual",\n'
        '  "importe_rango": [min, max],\n'
        '  "concepto_keywords": ["kw1", "kw2"],\n'
        '  "validacion": {\n'
        '    "iva_emitido": [21],\n'
        '    "irpf_retenido": 15\n'
        '  }\n'
        "}\n\n"
        "REGLAS:\n"
        "- Si el cliente es una SL/SA, probablemente retienen IRPF 15% a profesionales\n"
        "- Si es particular/comunidad, irpf_que_retienen=0\n"
        "- Responde SOLO con JSON válido, sin explicaciones."
    )


# ---------------------------------------------------------------------------
# Llamada a GPT-4o (patrón de proveedor_discovery.py)
# ---------------------------------------------------------------------------

def _llamar_gpt(prompt: str, openai_client=None) -> Optional[dict]:
    """Llama a GPT-4o y devuelve el JSON parseado, o None si falla."""
    if openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OPENAI_API_KEY no configurada")
            return None
        from openai import OpenAI
        openai_client = OpenAI(api_key=api_key, timeout=_TIMEOUT)

    for intento in range(_MAX_RETRIES + 1):
        try:
            respuesta = openai_client.chat.completions.create(
                model=_MODELO,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=600,
            )
            texto = respuesta.choices[0].message.content.strip()
            # Limpiar markdown si GPT lo incluye
            texto = re.sub(r"^```(?:json)?\s*", "", texto)
            texto = re.sub(r"\s*```$", "", texto)
            return json.loads(texto)
        except json.JSONDecodeError:
            if intento < _MAX_RETRIES:
                continue
            return None
        except Exception as e:
            print(f"  ERROR GPT-4o: {e}")
            return None

    return None


# ---------------------------------------------------------------------------
# Merge sin sobrescribir
# ---------------------------------------------------------------------------

def _merge_sin_pisar(existente: dict, nuevo: dict) -> dict:
    """Añade campos de `nuevo` a `existente` sin sobrescribir valores existentes.

    Para dicts anidados (validacion, asiento), merge recursivo.
    """
    resultado = dict(existente)
    for clave, valor in nuevo.items():
        if clave not in resultado:
            resultado[clave] = valor
        elif isinstance(resultado[clave], dict) and isinstance(valor, dict):
            resultado[clave] = _merge_sin_pisar(resultado[clave], valor)
        # Si ya existe y no es dict, NO pisar
    return resultado


# ---------------------------------------------------------------------------
# Detección de campos faltantes
# ---------------------------------------------------------------------------

def _necesita_enriquecimiento(entidad: dict, campos_avanzados: set) -> bool:
    """True si le falta al menos un campo avanzado."""
    for campo in campos_avanzados:
        if campo not in entidad:
            return True
    return False


def _campos_faltantes(entidad: dict, campos_avanzados: set) -> set:
    return campos_avanzados - set(entidad.keys())


# ---------------------------------------------------------------------------
# Perfil fiscal por defecto
# ---------------------------------------------------------------------------

_PERFIL_FISCAL_DEFAULT = {
    "territorio": "peninsula",
    "regimen_iva": "general",
    "regimen_irpf": "estimacion_directa_simplificada",
    "cuentas": {
        "proveedor_default": "4000000000",
        "cliente_default": "4300000000",
        "gasto_default": "6290000000",
        "ingreso_default": "7050000000",
        "iva_soportado": "4720000000",
        "iva_repercutido": "4770000000",
        "irpf_retenido_a_mi": "4730000000",
        "irpf_yo_retengo": "4751000000",
        "banco": "5720000000",
    },
    "deducibilidad": {
        "vehiculo_turismo": {"iva": 50, "gasto": 50},
        "vehiculo_comercial": {"iva": 100, "gasto": 100},
    },
}


def _generar_perfil_fiscal(config_data: dict) -> dict:
    """Genera perfil_fiscal basado en datos del cliente, con defaults."""
    perfil = dict(_PERFIL_FISCAL_DEFAULT)
    empresa = config_data.get("empresa", {})

    regimen_iva = empresa.get("regimen_iva")
    if regimen_iva:
        perfil["regimen_iva"] = regimen_iva

    return perfil


# ---------------------------------------------------------------------------
# Lógica principal
# ---------------------------------------------------------------------------

def enriquecer_config(
    ruta_config: Path,
    dry_run: bool = False,
    force: bool = False,
    openai_client=None,
) -> dict:
    """Enriquece un config.yaml con campos avanzados vía GPT-4o.

    Args:
        ruta_config: ruta al config.yaml del cliente
        dry_run: si True, no escribe cambios
        force: si True, enriquece todos (no solo los que faltan campos)
        openai_client: cliente OpenAI inyectable para tests

    Returns:
        dict con estadísticas: proveedores_enriquecidos, clientes_enriquecidos,
        campos_añadidos, llamadas_gpt, perfil_fiscal_añadido
    """
    with open(ruta_config, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    empresa = config_data.get("empresa", {})
    perfil_seccion = config_data.get("perfil", {})
    perfil_info = {
        "nombre": empresa.get("nombre", ""),
        "tipo": empresa.get("tipo", ""),
        "regimen_iva": empresa.get("regimen_iva", "general"),
        "descripcion": perfil_seccion.get("descripcion", ""),
    }

    # Cargar categorías
    ruta_cats = _RUTA_CATEGORIAS
    try:
        categorias = _cargar_categorias(ruta_cats)
        cats_texto = _resumen_categorias(categorias)
    except Exception:
        categorias = []
        cats_texto = "(no disponible)"

    stats = {
        "proveedores_enriquecidos": 0,
        "clientes_enriquecidos": 0,
        "campos_añadidos": {},
        "llamadas_gpt": 0,
        "perfil_fiscal_añadido": False,
    }

    # --- Enriquecer proveedores ---
    proveedores = config_data.get("proveedores", {})
    for clave, prov in proveedores.items():
        if not force and not _necesita_enriquecimiento(prov, _CAMPOS_AVANZADOS_PROVEEDOR):
            continue

        faltantes = _campos_faltantes(prov, _CAMPOS_AVANZADOS_PROVEEDOR) if not force else _CAMPOS_AVANZADOS_PROVEEDOR
        print(f"  Enriqueciendo proveedor: {clave} ({prov.get('nombre_fs', '')}) — faltan: {', '.join(sorted(faltantes))}")

        prompt = _prompt_proveedor(prov, perfil_info, cats_texto)
        datos_gpt = _llamar_gpt(prompt, openai_client)
        stats["llamadas_gpt"] += 1

        if datos_gpt is None:
            print(f"    SKIP: GPT-4o no devolvió datos para {clave}")
            continue

        # Post-procesar: intracom
        asiento = datos_gpt.get("asiento", {})
        if prov.get("regimen") == "intracomunitario" or asiento.get("intracom"):
            asiento["intracom"] = True
            asiento.setdefault("iva_autorepercusion", 21)
            datos_gpt["asiento"] = asiento

        # Post-procesar: persona_fisica + IRPF
        if datos_gpt.get("persona_fisica") and prov.get("codretencion"):
            asiento = datos_gpt.get("asiento", {})
            asiento.setdefault("subcuenta_irpf", "4751000000")
            datos_gpt["asiento"] = asiento

        # Merge sin pisar
        prov_nuevo = _merge_sin_pisar(prov, datos_gpt)
        proveedores[clave] = prov_nuevo
        stats["proveedores_enriquecidos"] += 1

        for campo in faltantes:
            if campo in datos_gpt:
                stats["campos_añadidos"][campo] = stats["campos_añadidos"].get(campo, 0) + 1

    # --- Enriquecer clientes ---
    clientes = config_data.get("clientes", {})
    for clave, cli in clientes.items():
        if cli.get("fallback"):
            continue

        if not force and not _necesita_enriquecimiento(cli, _CAMPOS_AVANZADOS_CLIENTE):
            continue

        faltantes = _campos_faltantes(cli, _CAMPOS_AVANZADOS_CLIENTE) if not force else _CAMPOS_AVANZADOS_CLIENTE
        print(f"  Enriqueciendo cliente: {clave} ({cli.get('nombre_fs', '')}) — faltan: {', '.join(sorted(faltantes))}")

        prompt = _prompt_cliente(cli, perfil_info)
        datos_gpt = _llamar_gpt(prompt, openai_client)
        stats["llamadas_gpt"] += 1

        if datos_gpt is None:
            print(f"    SKIP: GPT-4o no devolvió datos para {clave}")
            continue

        cli_nuevo = _merge_sin_pisar(cli, datos_gpt)
        clientes[clave] = cli_nuevo
        stats["clientes_enriquecidos"] += 1

        for campo in faltantes:
            if campo in datos_gpt:
                stats["campos_añadidos"][campo] = stats["campos_añadidos"].get(campo, 0) + 1

    # --- Perfil fiscal ---
    if "perfil_fiscal" not in config_data:
        config_data["perfil_fiscal"] = _generar_perfil_fiscal(config_data)
        stats["perfil_fiscal_añadido"] = True
        print("  Añadido bloque perfil_fiscal")

    # --- Escribir resultado ---
    if not dry_run:
        hoy = date.today().strftime("%Y%m%d")
        backup = ruta_config.parent / f"config.yaml.bak.{hoy}"
        shutil.copy2(ruta_config, backup)
        print(f"\n  Backup: {backup.name}")

        with open(ruta_config, "w", encoding="utf-8") as f:
            yaml.dump(
                config_data, f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                width=120,
            )
        print(f"  Escrito: {ruta_config}")
    else:
        print("\n  [DRY-RUN] No se escribieron cambios.")

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Enriquecer config.yaml de un cliente con GPT-4o")
    parser.add_argument("--cliente", required=True, help="Slug del cliente (ej: maria-isabel-navarro-lopez)")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin escribir")
    parser.add_argument("--force", action="store_true", help="Enriquecer todos, no solo los que faltan campos")
    args = parser.parse_args()

    ruta_config = _RAIZ / "clientes" / args.cliente / "config.yaml"
    if not ruta_config.exists():
        print(f"ERROR: No existe {ruta_config}")
        return

    print(f"Enriqueciendo config.yaml de: {args.cliente}")
    print(f"  Modo: {'DRY-RUN' if args.dry_run else 'REAL'} | Force: {args.force}\n")

    stats = enriquecer_config(ruta_config, dry_run=args.dry_run, force=args.force)

    # Resumen
    print(f"\n{'='*60}")
    print(f"  Enriquecidos: {stats['proveedores_enriquecidos']} proveedores, {stats['clientes_enriquecidos']} clientes")
    campos = stats["campos_añadidos"]
    if campos:
        detalle = ", ".join(f"{k}({v})" for k, v in sorted(campos.items()))
        print(f"  Campos añadidos: {detalle}")
    if stats["perfil_fiscal_añadido"]:
        print("  Perfil fiscal: añadido")
    coste = stats["llamadas_gpt"] * 0.01  # ~$0.01 por llamada GPT-4o
    print(f"  Coste estimado: ${coste:.2f} ({stats['llamadas_gpt']} llamadas GPT-4o)")
    if not args.dry_run:
        hoy = date.today().strftime("%Y%m%d")
        print(f"  Backup: config.yaml.bak.{hoy}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
