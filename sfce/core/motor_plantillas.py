"""Motor de Plantillas formato_pdf.

Aprende la estructura regex de cada proveedor a partir de extracciones LLM previas.
Permite extraer campos sin coste de tokens cuando la plantilla está validada.

Estados del ciclo de vida:
    auto_generado → 5 éxitos consecutivos → validado
    auto_generado → 1 fallo → fallido
    validado      → 3 fallos acumulados   → fallido
    fallido       → nueva extracción LLM exitosa → auto_generado (ciclo nuevo)
"""
import json
import re
from pathlib import Path
from typing import Optional

from .logger import crear_logger

logger = crear_logger("motor_plantillas")

# Campos que deben estar presentes en toda plantilla válida
_CAMPOS_OBLIGATORIOS = {"total", "fecha", "numero_factura"}

# Modelo Mistral por defecto para generación de plantillas
_MODELO_DEFAULT = "mistral-small-latest"

_PROMPT_GENERAR_PLANTILLA = """Eres un experto en extracción de datos de facturas PDF españolas.

Se te proporciona el texto de una factura y debes:
1. Identificar el valor actual de cada campo en este documento.
2. Crear un patrón regex que capture ese campo en documentos similares del mismo emisor.

Devuelve SOLO un JSON con esta estructura (sin explicaciones):
{
  "total": {"valor": "importe_total_aqui", "patron": "regex_para_total"},
  "fecha": {"valor": "fecha_aqui", "patron": "regex_para_fecha"},
  "numero_factura": {"valor": "numero_aqui", "patron": "regex_para_numero"}
}

Notas importantes sobre los patrones:
- Usa grupos de captura () para el valor que quieres extraer
- Los patrones deben ser robustos y funcionar en futuras facturas del mismo emisor
- Escapa correctamente los caracteres especiales de regex
- Para fechas: captura el valor completo (dd/mm/yyyy o dd-mm-yyyy)
- Para importes: captura solo los dígitos y separadores (sin símbolo de moneda)
- Para números de factura: captura el identificador completo

Texto de la factura:
"""


def _encontrar_proveedor_por_cif(config_data: dict, proveedor_cif: str) -> Optional[str]:
    """Busca la clave del proveedor en config.yaml dado su CIF.

    Returns:
        Clave del proveedor (str) o None si no se encuentra.
    """
    cif_normalizado = proveedor_cif.upper().strip()
    proveedores = config_data.get("proveedores", {})
    for clave, datos in proveedores.items():
        cif_config = (datos.get("cif") or "").upper().strip()
        if cif_config == cif_normalizado:
            return clave
    return None


def cargar_plantilla(config_path: Path, proveedor_cif: str) -> Optional[dict]:
    """Carga el bloque formato_pdf del proveedor desde config.yaml.

    Args:
        config_path: Ruta al config.yaml del cliente.
        proveedor_cif: CIF del proveedor.

    Returns:
        Dict con el bloque formato_pdf, o None si no existe.
    """
    try:
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.load(f)
    except Exception as e:
        logger.warning(f"motor_plantillas: no se pudo leer {config_path}: {e}")
        return None

    clave = _encontrar_proveedor_por_cif(config_data, proveedor_cif)
    if not clave:
        return None

    formato_pdf = config_data.get("proveedores", {}).get(clave, {}).get("formato_pdf")
    if not formato_pdf:
        return None

    # Convertir CommentedMap de ruamel a dict plano para facilitar uso
    return dict(formato_pdf)


def generar_plantilla_desde_llm(pdf_text: str, proveedor_cif: str,
                                 modelo: str = _MODELO_DEFAULT) -> dict:
    """Genera una plantilla regex llamando al LLM con un prompt combinado valor+regex.

    Args:
        pdf_text: Texto extraído del PDF.
        proveedor_cif: CIF del proveedor (usado solo para logging).
        modelo: Modelo Mistral a usar.

    Returns:
        Dict con estructura {campo: {"valor": ..., "patron": ...}} para campos obligatorios.

    Raises:
        ValueError: Si el LLM no devuelve algún campo obligatorio.
        Exception: Si la llamada al LLM falla.
    """
    import os
    from mistralai import Mistral

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY no configurada")

    client = Mistral(api_key=api_key)
    prompt_completo = _PROMPT_GENERAR_PLANTILLA + pdf_text[:3000]  # limitar tokens

    respuesta = client.chat.complete(
        model=modelo,
        messages=[{"role": "user", "content": prompt_completo}],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=800,
    )

    contenido = respuesta.choices[0].message.content
    resultado = json.loads(contenido)

    # Verificar campos obligatorios
    campos_ausentes = _CAMPOS_OBLIGATORIOS - set(resultado.keys())
    if campos_ausentes:
        raise ValueError(
            f"LLM no devolvió campos obligatorios: {', '.join(sorted(campos_ausentes))}"
        )

    # Verificar estructura interna de cada campo
    for campo in _CAMPOS_OBLIGATORIOS:
        entrada = resultado[campo]
        if not isinstance(entrada, dict) or "valor" not in entrada or "patron" not in entrada:
            raise ValueError(
                f"Campo '{campo}' no tiene estructura {{valor, patron}}: {entrada}"
            )

    logger.info(
        f"motor_plantillas: plantilla generada para CIF {proveedor_cif} "
        f"con modelo {modelo}"
    )
    return resultado


def aplicar_plantilla(pdf_text: str, plantilla: dict) -> dict:
    """Aplica los patrones regex de la plantilla al texto del PDF.

    Args:
        pdf_text: Texto del PDF.
        plantilla: Dict con bloque formato_pdf (debe tener clave 'patrones').

    Returns:
        Dict con {campo: valor_extraido}. Los campos no encontrados quedan como None.
    """
    patrones = plantilla.get("patrones") or {}
    resultado = {}

    for campo, patron in patrones.items():
        if not patron:
            resultado[campo] = None
            continue
        try:
            match = re.search(patron, pdf_text, re.IGNORECASE | re.MULTILINE)
            if match:
                # Tomar el primer grupo de captura si existe, sino el match completo
                resultado[campo] = match.group(1) if match.lastindex else match.group(0)
            else:
                resultado[campo] = None
        except re.error as e:
            logger.warning(f"motor_plantillas: patrón inválido para '{campo}': {e}")
            resultado[campo] = None

    return resultado


def actualizar_estado_plantilla(config_path: Path, proveedor_cif: str,
                                 exito: bool) -> None:
    """Aplica la lógica de strikes y persiste el estado en config.yaml.

    Lógica:
        auto_generado + exito: exitos_consecutivos++, reset fallos
            → si exitos_consecutivos >= 5: estado = "validado"
        auto_generado + fallo: estado = "fallido", reset contadores
        validado + exito: exitos_consecutivos++, reset fallos
        validado + fallo: fallos_consecutivos++
            → si fallos_consecutivos >= 3: estado = "fallido", reset contadores
        fallido: no se modifica (no debería llamarse con estado=fallido)

    Args:
        config_path: Ruta al config.yaml del cliente.
        proveedor_cif: CIF del proveedor.
        exito: True si la extracción fue exitosa, False si falló.
    """
    try:
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.load(f)
    except Exception as e:
        logger.warning(f"motor_plantillas: no se pudo leer {config_path}: {e}")
        return

    clave = _encontrar_proveedor_por_cif(config_data, proveedor_cif)
    if not clave:
        logger.warning(
            f"motor_plantillas: proveedor CIF {proveedor_cif} no encontrado en {config_path}"
        )
        return

    formato_pdf = config_data["proveedores"][clave].get("formato_pdf")
    if not formato_pdf:
        logger.warning(
            f"motor_plantillas: proveedor '{clave}' no tiene formato_pdf en {config_path}"
        )
        return

    estado = formato_pdf.get("estado", "auto_generado")

    if estado == "fallido":
        # No modificar estado fallido — se resetea solo al guardar plantilla nueva
        return

    if exito:
        formato_pdf["exitos_consecutivos"] = formato_pdf.get("exitos_consecutivos", 0) + 1
        formato_pdf["fallos_consecutivos"] = 0
        if (estado == "auto_generado"
                and formato_pdf["exitos_consecutivos"] >= 5):
            formato_pdf["estado"] = "validado"
            logger.info(
                f"motor_plantillas: '{clave}' promovido a validado "
                f"({formato_pdf['exitos_consecutivos']} éxitos)"
            )
    else:
        if estado == "auto_generado":
            formato_pdf["estado"] = "fallido"
            formato_pdf["exitos_consecutivos"] = 0
            formato_pdf["fallos_consecutivos"] = 0
            logger.info(f"motor_plantillas: '{clave}' auto_generado → fallido (1 fallo)")
        elif estado == "validado":
            formato_pdf["fallos_consecutivos"] = formato_pdf.get("fallos_consecutivos", 0) + 1
            if formato_pdf["fallos_consecutivos"] >= 3:
                formato_pdf["estado"] = "fallido"
                formato_pdf["exitos_consecutivos"] = 0
                formato_pdf["fallos_consecutivos"] = 0
                logger.info(
                    f"motor_plantillas: '{clave}' validado → fallido (3 fallos acumulados)"
                )
            else:
                logger.info(
                    f"motor_plantillas: '{clave}' validado fallo "
                    f"{formato_pdf['fallos_consecutivos']}/3"
                )

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)
    except Exception as e:
        logger.warning(f"motor_plantillas: no se pudo escribir {config_path}: {e}")


def guardar_plantilla(config_path: Path, proveedor_cif: str,
                      plantilla_dict: dict) -> None:
    """Escribe o sobreescribe el bloque formato_pdf en config.yaml del proveedor.

    Construye el bloque completo con estado inicial auto_generado y los patrones
    extraídos del LLM.

    Args:
        config_path: Ruta al config.yaml del cliente.
        proveedor_cif: CIF del proveedor.
        plantilla_dict: Resultado de generar_plantilla_desde_llm (campo → {valor, patron}).
    """
    try:
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.load(f)
    except Exception as e:
        logger.warning(f"motor_plantillas: no se pudo leer {config_path}: {e}")
        return

    clave = _encontrar_proveedor_por_cif(config_data, proveedor_cif)
    if not clave:
        logger.warning(
            f"motor_plantillas: proveedor CIF {proveedor_cif} no encontrado en {config_path}"
        )
        return

    # Construir patrones a partir del resultado LLM
    patrones = {campo: datos["patron"] for campo, datos in plantilla_dict.items()
                if isinstance(datos, dict) and "patron" in datos}

    # Detectar campos ausentes (campos donde el LLM no encontró valor)
    campos_ausentes = {}
    for campo in _CAMPOS_OBLIGATORIOS:
        entrada = plantilla_dict.get(campo, {})
        if not isinstance(entrada, dict) or not entrada.get("valor"):
            campos_ausentes[campo] = None

    bloque = {
        "estado": "auto_generado",
        "version": 1,
        "exitos_consecutivos": 0,
        "fallos_consecutivos": 0,
        "campos_ausentes": campos_ausentes or None,
        "patrones": patrones,
    }

    config_data["proveedores"][clave]["formato_pdf"] = bloque

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)
        logger.info(
            f"motor_plantillas: plantilla guardada para '{clave}' "
            f"en {config_path.name}"
        )
    except Exception as e:
        logger.warning(f"motor_plantillas: no se pudo escribir {config_path}: {e}")
