"""Generador de informe estructurado de cuarentena.

Combina dos fuentes:
- Tabla `cuarentena` de la BD SQLite (items con pregunta estructurada)
- Carpeta `cuarentena/` del cliente (PDFs sin entrada BD, caídos por error)

Genera:
- JSON estructurado con todos los items y sugerencias MCF
- Texto legible para terminal

Uso:
    from sfce.core.informe_cuarentena import generar_informe_cuarentena

    informe = generar_informe_cuarentena(
        ruta_cliente=Path("clientes/pastorino-costa-del-sol"),
        ejercicio="2025",
        config=config,
        ruta_bd=Path("sfce.db"),
    )
    print(informe["resumen_texto"])
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .cache_ocr import obtener_cache_ocr
from .clasificador_fiscal import ClasificadorFiscal
from .logger import crear_logger

logger = crear_logger("informe_cuarentena")

# Orden de prioridad visual de tipos de pregunta
_PRIORIDAD_TIPO = {
    "entidad": 1,
    "iva": 2,
    "importe": 3,
    "duplicado": 4,
    "subcuenta": 5,
    "otro": 6,
}

# Descripciones legibles de tipo_pregunta
_DESCRIPCION_TIPO = {
    "entidad": "Proveedor/cliente desconocido",
    "iva": "IVA incongruente",
    "importe": "Importe no cuadra",
    "duplicado": "Posible duplicado",
    "subcuenta": "Subcuenta indeterminada",
    "otro": "Error no catalogado",
    "sin_bd": "PDF en carpeta (sin entrada BD)",
}


@dataclass
class ItemCuarentena:
    """Un documento en cuarentena con toda la información disponible."""
    origen: str                     # "bd" | "carpeta"
    archivo: str                    # nombre del PDF
    tipo_pregunta: str              # subcuenta | iva | entidad | ...
    pregunta: str                   # texto de la pregunta generada
    opciones: list[dict]            # opciones sugeridas [{valor, descripcion, confianza}]
    respuesta: Optional[str]        # respuesta elegida (None si pendiente)
    resuelta: bool
    fecha_creacion: Optional[str]
    motivo_raw: str                 # motivo textual (de log o BD)

    # MCF — solo para proveedores (tipo "entidad")
    sugerencia_mcf: Optional[dict] = field(default=None)

    # IDs para cruce
    bd_id: Optional[int] = field(default=None)
    documento_id: Optional[int] = field(default=None)
    empresa_id: Optional[int] = field(default=None)

    @property
    def prioridad(self) -> int:
        return _PRIORIDAD_TIPO.get(self.tipo_pregunta, 99)

    @property
    def estado_label(self) -> str:
        if self.resuelta:
            return "RESUELTA"
        return "PENDIENTE"


def _items_desde_bd(ruta_bd: Path, empresa_id: Optional[int]) -> list[ItemCuarentena]:
    """Lee items de la tabla cuarentena en la BD SQLite."""
    items: list[ItemCuarentena] = []
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session
        from ..db.modelos import Cuarentena, Documento

        engine = create_engine(f"sqlite:///{ruta_bd}")
        with Session(engine) as sesion:
            stmt = select(Cuarentena)
            if empresa_id is not None:
                stmt = stmt.where(Cuarentena.empresa_id == empresa_id)
            stmt = stmt.order_by(Cuarentena.resuelta, Cuarentena.fecha_creacion.desc())

            for cua in sesion.scalars(stmt):
                doc = sesion.get(Documento, cua.documento_id)
                archivo = doc.nombre_archivo if doc else f"doc_{cua.documento_id}"

                items.append(ItemCuarentena(
                    origen="bd",
                    archivo=archivo,
                    tipo_pregunta=cua.tipo_pregunta,
                    pregunta=cua.pregunta,
                    opciones=cua.opciones or [],
                    respuesta=cua.respuesta,
                    resuelta=bool(cua.resuelta),
                    fecha_creacion=(cua.fecha_creacion.isoformat()
                                    if cua.fecha_creacion else None),
                    motivo_raw=cua.pregunta,
                    bd_id=cua.id,
                    documento_id=cua.documento_id,
                    empresa_id=cua.empresa_id,
                ))
    except Exception as exc:
        logger.warning("No se pudo leer cuarentena de BD: %s", exc)
    return items


def _items_desde_carpeta(
    ruta_cuarentena: Path, archivos_ya_en_bd: set[str]
) -> list[ItemCuarentena]:
    """Lee PDFs de la carpeta cuarentena/ que no tienen entrada en BD."""
    items: list[ItemCuarentena] = []
    if not ruta_cuarentena.exists():
        return items

    for pdf in sorted(ruta_cuarentena.glob("*.pdf")):
        if pdf.name in archivos_ya_en_bd:
            continue

        # Intentar leer datos OCR desde caché
        datos_ocr = obtener_cache_ocr(pdf) or {}
        motivo = datos_ocr.get("_motivo_cuarentena", "Motivo desconocido")

        items.append(ItemCuarentena(
            origen="carpeta",
            archivo=pdf.name,
            tipo_pregunta="sin_bd",
            pregunta=motivo,
            opciones=[],
            respuesta=None,
            resuelta=False,
            fecha_creacion=datetime.fromtimestamp(pdf.stat().st_mtime).isoformat(),
            motivo_raw=motivo,
        ))
    return items


def _enriquecer_con_mcf(
    items: list[ItemCuarentena], ruta_cuarentena: Path
) -> None:
    """Añade sugerencias MCF a items de tipo 'entidad' con caché OCR disponible."""
    clf = ClasificadorFiscal()

    for item in items:
        if item.tipo_pregunta not in ("entidad", "sin_bd"):
            continue

        # Buscar caché OCR del PDF
        ruta_pdf = ruta_cuarentena / item.archivo
        datos_ocr = obtener_cache_ocr(ruta_pdf) if ruta_pdf.exists() else {}
        if not datos_ocr:
            continue

        cif = datos_ocr.get("emisor_cif", "") or ""
        nombre = datos_ocr.get("emisor_nombre", "") or item.archivo

        try:
            clasificacion = clf.clasificar(cif, nombre, datos_ocr)
            item.sugerencia_mcf = {
                "categoria": clasificacion.categoria,
                "descripcion": clasificacion.descripcion,
                "iva_codimpuesto": clasificacion.iva_codimpuesto,
                "iva_deducible_pct": clasificacion.iva_deducible_pct,
                "irpf_pct": clasificacion.irpf_pct,
                "subcuenta": clasificacion.subcuenta,
                "confianza": clasificacion.confianza,
                "preguntas_pendientes": clasificacion.preguntas_pendientes,
                "razonamiento": clasificacion.razonamiento,
            }
        except Exception as exc:
            logger.debug("MCF error para %s: %s", item.archivo, exc)


def _texto_informe(
    items: list[ItemCuarentena],
    empresa_id: Optional[int],
    ejercicio: Optional[str],
) -> str:
    """Genera texto legible del informe para terminal o log."""
    lineas = [
        "=" * 70,
        "INFORME CUARENTENA SFCE",
        f"Fecha:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if ejercicio:
        lineas.append(f"Ejercicio: {ejercicio}")
    if empresa_id:
        lineas.append(f"Empresa:   {empresa_id}")
    lineas += ["=" * 70, ""]

    if not items:
        lineas.append("✓ No hay documentos en cuarentena.")
        return "\n".join(lineas)

    pendientes = [i for i in items if not i.resuelta]
    resueltas = [i for i in items if i.resuelta]

    lineas.append(f"Total: {len(items)} items  |  "
                  f"Pendientes: {len(pendientes)}  |  "
                  f"Resueltas: {len(resueltas)}")
    lineas.append("")

    # Agrupar por tipo
    por_tipo: dict[str, list[ItemCuarentena]] = {}
    for item in sorted(items, key=lambda x: (x.resuelta, x.prioridad)):
        por_tipo.setdefault(item.tipo_pregunta, []).append(item)

    for tipo, grupo in por_tipo.items():
        desc_tipo = _DESCRIPCION_TIPO.get(tipo, tipo)
        lineas.append(f"── {desc_tipo.upper()} ({len(grupo)}) ──────────────────────────")

        for item in grupo:
            estado = f"[{item.estado_label}]"
            fecha = item.fecha_creacion[:10] if item.fecha_creacion else "?"
            lineas.append(f"  {estado:10} {fecha}  {item.archivo}")
            lineas.append(f"             {item.pregunta[:80]}")

            if item.opciones:
                for opt in item.opciones[:3]:
                    conf = f"({opt.get('confianza', '?'):.0%})" if isinstance(
                        opt.get("confianza"), float) else ""
                    lineas.append(f"             → {opt.get('descripcion', opt.get('valor', ''))} {conf}")

            if item.sugerencia_mcf:
                mcf = item.sugerencia_mcf
                lineas.append(
                    f"             MCF: {mcf['descripcion']} | "
                    f"{mcf['iva_codimpuesto']} | "
                    f"confianza {mcf['confianza']:.0%}"
                )
                if mcf.get("preguntas_pendientes"):
                    lineas.append(
                        f"             MCF pendiente: {', '.join(mcf['preguntas_pendientes'])}"
                    )

            if item.respuesta:
                lineas.append(f"             Respuesta: {item.respuesta}")
            lineas.append("")

    lineas.append("=" * 70)
    return "\n".join(lineas)


def generar_informe_cuarentena(
    ruta_cliente: Path,
    ejercicio: Optional[str] = None,
    config=None,
    ruta_bd: Optional[Path] = None,
    empresa_id: Optional[int] = None,
    enriquecer_mcf: bool = True,
) -> dict:
    """Genera el informe estructurado de cuarentena.

    Args:
        ruta_cliente:  carpeta raíz del cliente (ej: clientes/pastorino-costa-del-sol)
        ejercicio:     año del ejercicio para filtrar (ej: "2025"). None = todos
        config:        ConfigCliente para obtener empresa_id si no se pasa directamente
        ruta_bd:       ruta a sfce.db. Si None, usa sfce.db en la raíz del proyecto
        empresa_id:    ID de empresa para filtrar en BD. Si None, se obtiene de config
        enriquecer_mcf: si True, añade sugerencias MCF a items de tipo entidad

    Returns:
        dict con claves:
            items:          list[dict] — todos los items serializados
            total:          int
            pendientes:     int
            resueltas:      int
            por_tipo:       dict[str, int] — conteo por tipo_pregunta
            resumen_texto:  str — texto legible
            ruta_guardado:  str | None — ruta del JSON guardado
    """
    # Resolver ruta BD
    if ruta_bd is None:
        ruta_bd = Path("sfce.db")

    # Resolver empresa_id desde config
    if empresa_id is None and config is not None:
        empresa_id = getattr(config, "idempresa", None)

    # Ruta cuarentena del cliente
    ruta_cuarentena = ruta_cliente / "cuarentena"

    # 1. Leer desde BD
    items_bd = _items_desde_bd(ruta_bd, empresa_id) if ruta_bd.exists() else []
    archivos_en_bd = {i.archivo for i in items_bd}

    # 2. Completar con PDFs de la carpeta que no están en BD
    items_carpeta = _items_desde_carpeta(ruta_cuarentena, archivos_en_bd)

    # Filtrar por ejercicio si se pide (solo items carpeta, BD ya filtra por empresa)
    if ejercicio and items_carpeta:
        items_carpeta = [
            i for i in items_carpeta
            if ejercicio in (i.fecha_creacion or "")
            or _pdf_es_del_ejercicio(ruta_cuarentena / i.archivo, ejercicio)
        ]

    todos = items_bd + items_carpeta

    # 3. Enriquecer con sugerencias MCF
    if enriquecer_mcf and todos:
        _enriquecer_con_mcf(todos, ruta_cuarentena)

    # 4. Estadísticas
    pendientes = [i for i in todos if not i.resuelta]
    resueltas = [i for i in todos if i.resuelta]
    por_tipo: dict[str, int] = {}
    for item in todos:
        por_tipo[item.tipo_pregunta] = por_tipo.get(item.tipo_pregunta, 0) + 1

    # 5. Texto legible
    texto = _texto_informe(todos, empresa_id, ejercicio)

    # 6. Guardar JSON en auditoria/
    ruta_guardado: Optional[str] = None
    try:
        ruta_auditoria = ruta_cliente / (ejercicio or "general") / "auditoria"
        ruta_auditoria.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_json = ruta_auditoria / f"cuarentena_{ts}.json"
        payload = {
            "generado": datetime.now().isoformat(),
            "empresa_id": empresa_id,
            "ejercicio": ejercicio,
            "total": len(todos),
            "pendientes": len(pendientes),
            "resueltas": len(resueltas),
            "por_tipo": por_tipo,
            "items": [asdict(i) for i in todos],
        }
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        ruta_guardado = str(ruta_json)
    except Exception as exc:
        logger.warning("No se pudo guardar JSON cuarentena: %s", exc)

    return {
        "items": [asdict(i) for i in todos],
        "total": len(todos),
        "pendientes": len(pendientes),
        "resueltas": len(resueltas),
        "por_tipo": por_tipo,
        "resumen_texto": texto,
        "ruta_guardado": ruta_guardado,
    }


def _pdf_es_del_ejercicio(ruta_pdf: Path, ejercicio: str) -> bool:
    """Heurística: mtime del PDF cae dentro del año del ejercicio."""
    if not ruta_pdf.exists():
        return False
    mtime = datetime.fromtimestamp(ruta_pdf.stat().st_mtime)
    return str(mtime.year) == ejercicio
