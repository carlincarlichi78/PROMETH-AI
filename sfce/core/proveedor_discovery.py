"""Descubrimiento automático de proveedores desconocidos usando GPT-4o.

Cuando el OCR lee un CIF válido pero no hay match en config.yaml,
llama a GPT-4o para identificar el proveedor y generar una sugerencia
de bloque YAML que el usuario revisa antes del siguiente run.

El doc SIGUE yendo a cuarentena — este módulo solo produce sugerencias.
"""
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from .logger import crear_logger

logger = crear_logger("proveedor_discovery")

_MODELO = "gpt-4o"
_TIMEOUT = 30
_MAX_RETRIES = 1


# ---------------------------------------------------------------------------
# Carga de categorías
# ---------------------------------------------------------------------------

def _cargar_categorias(ruta_categorias: Path) -> list[dict]:
    """Carga categorías de gasto del YAML para incluir en el prompt."""
    with open(ruta_categorias, "r", encoding="utf-8") as f:
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


# ---------------------------------------------------------------------------
# Construcción del prompt
# ---------------------------------------------------------------------------

def _construir_prompt(cif: str, nombre: str, config, categorias: list[dict]) -> str:
    """Construye el prompt para GPT-4o."""
    perfil = config.empresa.get("tipo", "")
    regimen_iva = config.empresa.get("regimen_iva", "general")

    cats_resumen = "\n".join(
        f"- {c['nombre']}: {c['descripcion']} | subcuenta={c['subcuenta']} | {c['codimpuesto']}"
        + (f" | keywords: {', '.join(str(k) for k in c['keywords'][:5])}"
           if c['keywords'] else "")
        for c in categorias
    )

    return (
        "Eres un asesor fiscal español. Identifica al proveedor y clasifícalo contablemente.\n\n"
        "DATOS DEL PROVEEDOR (extraídos por OCR de una factura):\n"
        f"- CIF/NIF: {cif}\n"
        f"- Nombre en factura: {nombre}\n\n"
        "PERFIL DEL CLIENTE:\n"
        f"- Tipo empresa: {perfil}\n"
        f"- Régimen IVA: {regimen_iva}\n\n"
        "CATEGORÍAS DISPONIBLES (nombre: descripción | subcuenta | IVA):\n"
        f"{cats_resumen}\n\n"
        "INSTRUCCIONES:\n"
        "1. Identifica la empresa española con ese CIF si la conoces\n"
        "2. Elige la categoría más apropiada\n"
        "3. Determina el régimen: general | intracomunitario | extracomunitario\n"
        "4. Si el CIF empieza por código de país UE (IE, FR, DE...) → intracomunitario + IVA0\n\n"
        "Responde SOLO con JSON válido, sin markdown:\n"
        "{\n"
        '  "nombre_fs": "nombre oficial normalizado en mayúsculas",\n'
        '  "aliases": ["alias1", "alias2"],\n'
        '  "subcuenta": "código 10 dígitos",\n'
        '  "codimpuesto": "IVA0|IVA4|IVA5|IVA10|IVA21",\n'
        '  "regimen": "general|intracomunitario|extracomunitario",\n'
        '  "pais": "código ISO 3 letras (ESP, IRL, FRA...)",\n'
        '  "divisa": "EUR|USD|GBP",\n'
        '  "nota": "descripción breve del proveedor"\n'
        "}"
    )


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def descubrir_proveedor(
    datos_ocr: dict,
    config,
    ruta_categorias: Optional[Path] = None,
    _openai_client=None,
) -> Optional[dict]:
    """Llama a GPT-4o para identificar un proveedor desconocido.

    Solo se debe llamar cuando el CIF está presente pero no hay match en config.yaml.

    Args:
        datos_ocr: dict con datos extraídos por OCR (necesita emisor_cif, emisor_nombre)
        config: ConfigCliente del cliente activo
        ruta_categorias: ruta a categorias_gasto.yaml (autodetecta si None)
        _openai_client: cliente OpenAI inyectado (para tests)

    Returns:
        dict con campos del bloque YAML sugerido + cif + _nombre_ocr, o None si falla
    """
    cif = (datos_ocr.get("emisor_cif") or "").strip()
    nombre = (datos_ocr.get("emisor_nombre") or "").strip()

    if not cif:
        return None

    if ruta_categorias is None:
        ruta_categorias = (
            Path(__file__).parent.parent.parent / "reglas" / "categorias_gasto.yaml"
        )

    try:
        categorias = _cargar_categorias(ruta_categorias)
    except Exception as e:
        logger.warning(f"No se pudo cargar categorias_gasto.yaml: {e}")
        categorias = []

    prompt = _construir_prompt(cif, nombre, config, categorias)

    if _openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY no configurada — proveedor discovery deshabilitado")
            return None
        from openai import OpenAI
        _openai_client = OpenAI(api_key=api_key, timeout=_TIMEOUT)

    for intento in range(_MAX_RETRIES + 1):
        try:
            respuesta = _openai_client.chat.completions.create(
                model=_MODELO,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=400,
            )
            texto = respuesta.choices[0].message.content.strip()
            # Limpiar markdown si GPT lo incluye
            texto = re.sub(r"^```(?:json)?\s*", "", texto)
            texto = re.sub(r"\s*```$", "", texto)
            datos = json.loads(texto)

            # Validar campos mínimos
            campos_req = {"nombre_fs", "subcuenta", "codimpuesto", "regimen"}
            if not campos_req.issubset(datos.keys()):
                logger.warning(
                    f"GPT-4o devolvió campos incompletos para {cif}: {list(datos.keys())}"
                )
                return None

            # Añadir CIF y nombre original para referencia al escribir sugerencias
            datos["cif"] = cif
            datos["_nombre_ocr"] = nombre
            return datos

        except json.JSONDecodeError as e:
            logger.warning(f"GPT-4o devolvió JSON inválido para {cif} (intento {intento}): {e}")
            if intento < _MAX_RETRIES:
                continue
            return None
        except Exception as e:
            logger.error(f"Error llamando GPT-4o para discovery {cif}: {e}")
            return None

    return None


# ---------------------------------------------------------------------------
# Deduplicación y escritura de sugerencias
# ---------------------------------------------------------------------------

def cargar_cifs_sugeridos(ruta_sugerencias: Path) -> set[str]:
    """Lee los CIFs ya sugeridos en el archivo de sugerencias previo.

    Evita llamar a GPT-4o si el CIF ya fue procesado en un run anterior.

    Returns:
        Conjunto de CIFs en mayúsculas ya presentes en el archivo
    """
    if not ruta_sugerencias.exists():
        return set()

    cifs: set[str] = set()
    patron = re.compile(r'#\s+cif:\s+"?([A-Z0-9a-z]+)"?', re.IGNORECASE)
    try:
        contenido = ruta_sugerencias.read_text(encoding="utf-8")
        for match in patron.finditer(contenido):
            cifs.add(match.group(1).upper())
    except Exception as e:
        logger.warning(f"Error leyendo {ruta_sugerencias}: {e}")
    return cifs


def guardar_sugerencias(ruta_sugerencias: Path, sugerencias: list[dict]) -> None:
    """Escribe o actualiza el archivo config_sugerencias.yaml con nuevas sugerencias.

    Si el archivo ya existe, añade al final sin duplicar CIFs ya presentes.
    Formato: bloques YAML comentados que el usuario puede copiar a config.yaml.

    Args:
        ruta_sugerencias: ruta donde escribir/actualizar
        sugerencias: lista de dicts con campos del bloque YAML
                     (deben incluir 'cif', '_nombre_ocr', '_archivo')
    """
    if not sugerencias:
        return

    cifs_existentes = cargar_cifs_sugeridos(ruta_sugerencias)
    nuevas = [s for s in sugerencias if s.get("cif", "").upper() not in cifs_existentes]

    if not nuevas:
        return

    hoy = date.today().isoformat()
    lineas: list[str] = []

    if not ruta_sugerencias.exists():
        lineas.append("# === PROVEEDORES SUGERIDOS POR GPT-4o ===\n")
        lineas.append("# Revisar y copiar los aprobados a config.yaml, luego reprocesar.\n")

    lineas.append(f"\n# --- Sugerencias {hoy} ({len(nuevas)} proveedor(es)) ---\n")

    for sug in nuevas:
        cif = sug.get("cif", "")
        nombre_ocr = sug.get("_nombre_ocr", "")
        archivo = sug.get("_archivo", "")
        nombre_clave = _cif_a_clave(cif, sug.get("nombre_fs", ""))

        lineas.append(f"\n# Fuente: \"{nombre_ocr}\" (CIF: {cif}) — {archivo}\n")
        lineas.append(f"# {nombre_clave}:\n")

        campos = [
            ("cif", f'"{cif}"'),
            ("nombre_fs", f'"{sug.get("nombre_fs", "")}"'),
            ("aliases", _formatear_aliases(sug.get("aliases", []))),
            ("pais", sug.get("pais", "ESP")),
            ("divisa", sug.get("divisa", "EUR")),
            ("subcuenta", f'"{sug.get("subcuenta", "")}"'),
            ("codimpuesto", sug.get("codimpuesto", "IVA21")),
            ("regimen", sug.get("regimen", "general")),
            ("notas", f'"{sug.get("nota", "")}"'),
        ]
        for campo, valor in campos:
            lineas.append(f"#   {campo}: {valor}\n")

    with open(ruta_sugerencias, "a", encoding="utf-8") as f:
        f.writelines(lineas)

    logger.info(f"Sugerencias guardadas en {ruta_sugerencias}: {len(nuevas)} nuevas")


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _cif_a_clave(cif: str, nombre_fs: str) -> str:
    """Genera clave YAML del proveedor desde CIF y nombre."""
    if nombre_fs:
        palabras = re.sub(r"[^a-zA-Z0-9\s]", "", nombre_fs).lower().split()
        stopwords = {
            "sl", "sa", "slu", "sau", "srl", "de", "del", "la", "el",
            "los", "las", "y", "e", "s", "a",
        }
        palabras = [p for p in palabras if p not in stopwords][:3]
        if palabras:
            return "_".join(palabras)
    return f"prov_{cif.lower()}"


def _formatear_aliases(aliases: list) -> str:
    """Formatea lista de aliases para YAML comentado."""
    if not aliases:
        return "[]"
    items = ", ".join(f'"{a}"' for a in aliases)
    return f"[{items}]"
