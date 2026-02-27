"""Motor de aprendizaje evolutivo del sistema contable.

Nucleo fundamental del sistema: cuando algo falla, busca soluciones,
las aplica, y APRENDE para la proxima vez.

Componentes:
- BaseConocimiento: almacen persistente (YAML) de patrones error→solucion
- Resolutor: prueba estrategias conocidas ante errores, aprende de resultados

Cada estrategia es una funcion que recibe (error, doc, contexto) y devuelve
un dict con datos_corregidos si puede resolver, o None si no.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from .logger import crear_logger

logger = crear_logger("aprendizaje")

RUTA_CONOCIMIENTO = Path(__file__).parent.parent.parent / "reglas" / "aprendizaje.yaml"

# Maximo reintentos por documento
MAX_REINTENTOS = 3


class BaseConocimiento:
    """Almacen persistente de soluciones aprendidas.

    Guarda en YAML: patrones de error -> estrategias de resolucion,
    con contadores de exito/fallo para priorizar estrategias.
    """

    def __init__(self, ruta: Path = RUTA_CONOCIMIENTO):
        self.ruta = ruta
        self.datos = self._cargar()

    def _cargar(self) -> dict:
        if self.ruta.exists():
            with open(self.ruta, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {"version": 1, "patrones": []}
        return {"version": 1, "patrones": []}

    def guardar(self):
        """Persiste conocimiento a disco."""
        self.datos["ultima_actualizacion"] = datetime.now().isoformat()
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta, "w", encoding="utf-8") as f:
            yaml.dump(
                self.datos, f,
                allow_unicode=True, default_flow_style=False, sort_keys=False
            )

    def buscar_solucion(self, error_msg: str, contexto: dict) -> Optional[dict]:
        """Busca patron conocido que coincida con el error.

        Returns:
            dict del patron si hay match, None si no
        """
        tipo_doc = contexto.get("tipo", "")
        matches = []

        for patron in self.datos.get("patrones", []):
            try:
                if not re.search(patron["regex"], error_msg, re.IGNORECASE):
                    continue
            except re.error:
                continue

            # Filtrar por tipo_doc si el patron lo especifica
            tipos_validos = patron.get("tipo_doc", [])
            if tipos_validos and tipo_doc and tipo_doc not in tipos_validos:
                continue

            matches.append(patron)

        if not matches:
            return None

        # Priorizar por tasa de exito
        def _tasa_exito(p):
            exitos = p.get("exitos", 0)
            fallos = p.get("fallos", 0)
            total = exitos + fallos
            return exitos / max(total, 1)

        matches.sort(key=_tasa_exito, reverse=True)
        return matches[0]

    def registrar_exito(self, patron_id: str):
        """Incrementa exitos de un patron y persiste."""
        for p in self.datos.get("patrones", []):
            if p.get("id") == patron_id:
                p["exitos"] = p.get("exitos", 0) + 1
                p["ultimo_exito"] = datetime.now().isoformat()
                break
        self.guardar()

    def registrar_fallo(self, patron_id: str):
        """Incrementa fallos de un patron."""
        for p in self.datos.get("patrones", []):
            if p.get("id") == patron_id:
                p["fallos"] = p.get("fallos", 0) + 1
                break
        # No guardar en cada fallo para no ralentizar

    def aprender_nuevo(self, error_msg: str, estrategia: str, contexto: dict):
        """Registra un patron nuevo descubierto durante ejecucion."""
        patron_id = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Generalizar el error a regex reutilizable
        regex = self._generalizar_error(error_msg)

        nuevo = {
            "id": patron_id,
            "regex": regex,
            "estrategia": estrategia,
            "tipo_doc": [contexto.get("tipo", "")] if contexto.get("tipo") else [],
            "aprendido": datetime.now().isoformat(),
            "exitos": 1,
            "fallos": 0,
            "origen": "auto",
            "error_original": error_msg[:200],
        }
        self.datos.setdefault("patrones", []).append(nuevo)
        self.guardar()
        logger.info(f"APRENDIDO: {patron_id} -> {estrategia} ('{regex[:60]}')")

    def _generalizar_error(self, error_msg: str) -> str:
        """Convierte mensaje de error concreto en regex reutilizable."""
        regex = re.escape(error_msg[:120])
        # Generalizar numeros, CIFs, nombres
        regex = re.sub(r'\\\d+', r'\\d+', regex)
        regex = re.sub(r'[A-Z]\\d{7,8}[A-Z]', r'[A-Z]\\d+[A-Z]', regex)
        return regex

    def estadisticas(self) -> dict:
        """Resumen del estado del conocimiento."""
        patrones = self.datos.get("patrones", [])
        total_exitos = sum(p.get("exitos", 0) for p in patrones)
        total_fallos = sum(p.get("fallos", 0) for p in patrones)
        return {
            "patrones_conocidos": len(patrones),
            "total_resoluciones": total_exitos,
            "total_fallos": total_fallos,
            "tasa_exito": round(
                total_exitos / max(total_exitos + total_fallos, 1) * 100, 1
            ),
        }


class Resolutor:
    """Motor de resolucion automatica de problemas.

    Ante un error:
    1. Busca patron conocido en la base de conocimiento
    2. Aplica la estrategia asociada
    3. Si no hay patron, prueba TODAS las estrategias genericas
    4. Si algo funciona, lo aprende para la proxima vez
    """

    def __init__(self, config=None, ruta_conocimiento: Path = None):
        self.conocimiento = BaseConocimiento(ruta_conocimiento or RUTA_CONOCIMIENTO)
        self.config = config
        self.max_reintentos = MAX_REINTENTOS
        self._estrategias: dict[str, Callable] = {}
        self._intentados: dict[str, set] = {}  # archivo -> estrategias ya probadas
        self._stats = {"resueltos": 0, "no_resueltos": 0, "aprendidos": 0}
        self._registrar_estrategias()

    def _registrar_estrategias(self):
        """Registra todas las estrategias de resolucion disponibles."""
        self._estrategias = {
            "crear_entidad_desde_ocr": self._crear_entidad_desde_ocr,
            "buscar_entidad_fuzzy": self._buscar_entidad_fuzzy,
            "corregir_campo_null": self._corregir_campo_null,
            "adaptar_campos_ocr": self._adaptar_campos_ocr,
            "derivar_importes": self._derivar_importes,
            "crear_subcuenta_auto": self._crear_subcuenta_auto,
        }

    def intentar_resolver(
        self, error: Exception, doc: dict, contexto: dict
    ) -> Optional[dict]:
        """Intenta resolver un error usando conocimiento + estrategias.

        Args:
            error: la excepcion o error ocurrido
            doc: documento con datos_extraidos
            contexto: dict con config, tipo_doc, codejercicio, etc.

        Returns:
            {"estrategia": str, "datos_corregidos": dict} si resolvio, None si no
        """
        error_msg = str(error)
        archivo = doc.get("archivo", "?")
        logger.info(f"  Resolutor activado: {error_msg[:80]}...")

        # Tracking de estrategias ya probadas para este documento
        if archivo not in self._intentados:
            self._intentados[archivo] = set()

        # 1. Buscar patron conocido
        patron = self.conocimiento.buscar_solucion(error_msg, doc)
        if patron:
            nombre = patron["estrategia"]
            if nombre not in self._intentados[archivo]:
                self._intentados[archivo].add(nombre)
                resultado = self._ejecutar_estrategia(nombre, error, doc, contexto)
                if resultado:
                    self.conocimiento.registrar_exito(patron["id"])
                    self._stats["resueltos"] += 1
                    logger.info(f"  RESUELTO (patron {patron['id']}): {nombre}")
                    return resultado
                else:
                    self.conocimiento.registrar_fallo(patron["id"])

        # 2. Probar todas las estrategias genericas
        for nombre, fn in self._estrategias.items():
            if nombre in self._intentados[archivo]:
                continue
            self._intentados[archivo].add(nombre)

            resultado = self._ejecutar_estrategia(nombre, error, doc, contexto)
            if resultado:
                # APRENDER: nuevo patron descubierto
                self.conocimiento.aprender_nuevo(error_msg, nombre, doc)
                self._stats["resueltos"] += 1
                self._stats["aprendidos"] += 1
                logger.info(f"  RESUELTO (nuevo): {nombre}")
                return resultado

        self._stats["no_resueltos"] += 1
        logger.warning(f"  Sin solucion para: {error_msg[:80]}")
        return None

    def _ejecutar_estrategia(
        self, nombre: str, error: Exception, doc: dict, contexto: dict
    ) -> Optional[dict]:
        """Ejecuta una estrategia de forma segura."""
        fn = self._estrategias.get(nombre)
        if not fn:
            return None
        try:
            return fn(error, doc, contexto)
        except Exception as e:
            logger.debug(f"  Estrategia {nombre} fallo: {e}")
            return None

    @property
    def stats(self) -> dict:
        """Estadisticas de esta sesion de resolucion."""
        return {
            **self._stats,
            **self.conocimiento.estadisticas(),
        }

    def guardar_conocimiento(self):
        """Persiste el conocimiento acumulado."""
        self.conocimiento.guardar()

    # =========================================================================
    # ESTRATEGIAS DE RESOLUCION
    # Cada una recibe (error, doc, contexto) y devuelve Optional[dict]
    # con {"estrategia": nombre, "datos_corregidos": dict_doc_corregido}
    # =========================================================================

    def _crear_entidad_desde_ocr(self, error, doc, contexto):
        """Crea proveedor/cliente en FS a partir de datos OCR.

        Util cuando el proveedor no esta en config.yaml pero el OCR
        extrajo CIF y nombre correctamente.
        """
        error_msg = str(error).lower()
        if "entidad" not in error_msg and "proveedor" not in error_msg:
            return None

        from .config import _normalizar_cif
        from .fs_api import api_get, api_post, api_put

        datos = doc.get("datos_extraidos") or {}
        cif = (datos.get("emisor_cif") or datos.get("cif", "")).strip()
        nombre = (datos.get("emisor") or datos.get("nombre", "")).strip()

        if not cif or len(cif) < 5 or not nombre:
            return None

        # Verificar que no exista ya
        cif_norm = _normalizar_cif(cif)
        proveedores = api_get("proveedores", limit=500)
        for p in proveedores:
            if _normalizar_cif(p.get("cifnif", "")) == cif_norm:
                return None  # Ya existe, el problema es otro

        # Crear proveedor
        form = {
            "nombre": nombre,
            "razonsocial": nombre,
            "cifnif": cif,
            "regimeniva": "General",
            "personafisica": 0,
            "tipoidfiscal": "NIF",
        }

        try:
            resp = api_post("proveedores", form)
            codprov = resp.get("data", {}).get("codproveedor")
            idcontacto = resp.get("data", {}).get("idcontacto")

            if not codprov:
                return None

            # Codpais en contacto
            if idcontacto:
                api_put(f"contactos/{idcontacto}", data={"codpais": "ESP"})

            logger.info(f"  Proveedor creado desde OCR: {nombre} ({cif}) -> {codprov}")
            return {"estrategia": "crear_entidad_desde_ocr", "datos_corregidos": doc}
        except Exception:
            return None

    def _buscar_entidad_fuzzy(self, error, doc, contexto):
        """Busca entidad con CIF aproximado (error comun OCR: ultimo digito).

        Si el OCR extrae A28054600 pero el correcto es A28054609,
        esta estrategia lo encuentra por coincidencia parcial.
        """
        error_msg = str(error).lower()
        if "entidad" not in error_msg and "proveedor" not in error_msg:
            return None

        from .config import _normalizar_cif
        from .fs_api import api_get

        datos = doc.get("datos_extraidos") or {}
        cif = (datos.get("emisor_cif") or datos.get("cif", "")).strip()
        if not cif or len(cif) < 7:
            return None

        cif_norm = _normalizar_cif(cif)
        cif_parcial = cif_norm[:-1]  # Sin ultimo digito

        proveedores = api_get("proveedores", limit=500)
        for p in proveedores:
            cif_fs = _normalizar_cif(p.get("cifnif", ""))
            if cif_fs[:-1] == cif_parcial and cif_fs != cif_norm:
                # Match fuzzy encontrado
                logger.info(f"  CIF fuzzy: OCR={cif} -> FS={p['cifnif']} ({p.get('nombre')})")
                datos_corregidos = {**doc}
                datos_nuevos = {**(datos_corregidos.get("datos_extraidos") or {})}
                datos_nuevos["emisor_cif"] = p["cifnif"]
                datos_nuevos["_cif_corregido_por_aprendizaje"] = True
                datos_corregidos["datos_extraidos"] = datos_nuevos
                return {
                    "estrategia": "buscar_entidad_fuzzy",
                    "datos_corregidos": datos_corregidos,
                }

        return None

    def _corregir_campo_null(self, error, doc, contexto):
        """Reemplaza campos None por valores por defecto sensibles.

        Errores tipicos: 'NoneType has no len', 'NoneType is not subscriptable'
        """
        error_msg = str(error)
        if "NoneType" not in error_msg and "None" not in error_msg:
            return None

        datos = doc.get("datos_extraidos")
        if datos is None:
            datos_corregidos = {**doc, "datos_extraidos": {}}
            return {
                "estrategia": "corregir_campo_null",
                "datos_corregidos": datos_corregidos,
            }

        cambios = False
        datos_nuevos = {**datos}

        # Campos con defaults conocidos
        defaults = {
            "fecha": datetime.now().strftime("%Y-%m-01"),
            "divisa": "EUR",
            "lineas": [],
            "base_imponible": 0,
            "total": 0,
            "importe": 0,
        }

        for campo, default in defaults.items():
            if campo in datos_nuevos and datos_nuevos[campo] is None:
                datos_nuevos[campo] = default
                cambios = True

        if not cambios:
            return None

        datos_corregidos = {**doc, "datos_extraidos": datos_nuevos}
        return {
            "estrategia": "corregir_campo_null",
            "datos_corregidos": datos_corregidos,
        }

    def _adaptar_campos_ocr(self, error, doc, contexto):
        """Mapea campos OCR con nombres alternativos a los esperados.

        Diferentes motores OCR usan nombres distintos:
        salario_bruto → bruto, liquido → neto, etc.
        """
        datos = doc.get("datos_extraidos") or {}
        cambios = False
        datos_nuevos = {**datos}

        # Mapeos conocidos de campos OCR
        mapeos = {
            "total": "importe",
            "importe_total": "importe",
            "base": "base_imponible",
            "iva": "iva_importe",
            "cuota_iva": "iva_importe",
            "importe_iva": "iva_importe",
            "irpf": "retenciones_irpf",
            "retencion": "retenciones_irpf",
            "retencion_irpf": "retenciones_irpf",
            "salario_bruto": "bruto",
            "sueldo_bruto": "bruto",
            "salario_base": "bruto",
            "liquido": "neto",
            "salario_neto": "neto",
            "a_percibir": "neto",
            "ss_trabajador": "aportaciones_ss_trabajador",
            "seguridad_social": "aportaciones_ss_trabajador",
            "ss_empresa": "cuota_empresarial",
            "cuota_ss": "cuota_empresarial",
        }

        for campo_ocr, campo_esperado in mapeos.items():
            if campo_ocr in datos_nuevos and campo_esperado not in datos_nuevos:
                datos_nuevos[campo_esperado] = datos_nuevos[campo_ocr]
                cambios = True

        if not cambios:
            return None

        datos_corregidos = {**doc, "datos_extraidos": datos_nuevos}
        return {
            "estrategia": "adaptar_campos_ocr",
            "datos_corregidos": datos_corregidos,
        }

    def _derivar_importes(self, error, doc, contexto):
        """Calcula importes faltantes a partir de los disponibles.

        Si tiene base_imponible y total, puede derivar iva_importe.
        Si tiene bruto e irpf y ss, puede derivar neto.
        """
        datos = doc.get("datos_extraidos") or {}
        cambios = False
        datos_nuevos = {**datos}

        # Derivar IVA desde base y total
        base = datos_nuevos.get("base_imponible") or 0
        total = datos_nuevos.get("total") or datos_nuevos.get("importe") or 0
        if base > 0 and total > base and not datos_nuevos.get("iva_importe"):
            datos_nuevos["iva_importe"] = round(total - base, 2)
            cambios = True

        # Derivar neto de nomina
        bruto = datos_nuevos.get("bruto") or 0
        irpf = datos_nuevos.get("retenciones_irpf") or 0
        ss = datos_nuevos.get("aportaciones_ss_trabajador") or 0
        if bruto > 0 and (irpf > 0 or ss > 0) and not datos_nuevos.get("neto"):
            datos_nuevos["neto"] = round(bruto - irpf - ss, 2)
            cambios = True

        # Derivar importe desde base + IVA
        if not datos_nuevos.get("importe") and base > 0:
            iva = datos_nuevos.get("iva_importe") or 0
            datos_nuevos["importe"] = round(base + iva, 2)
            cambios = True

        if not cambios:
            return None

        datos_corregidos = {**doc, "datos_extraidos": datos_nuevos}
        return {
            "estrategia": "derivar_importes",
            "datos_corregidos": datos_corregidos,
        }

    def _crear_subcuenta_auto(self, error, doc, contexto):
        """Crea subcuenta en FS si no existe en el ejercicio."""
        error_msg = str(error).lower()
        if "subcuenta" not in error_msg and "codsubcuenta" not in error_msg:
            return None

        from .fs_api import api_get, api_post

        # Extraer codigo de subcuenta del error
        match = re.search(r'(\d{10})', str(error))
        if not match:
            return None

        codsubcuenta = match.group(1)
        codcuenta = codsubcuenta[:4]
        codejercicio = contexto.get("codejercicio", "")

        if not codejercicio:
            config = contexto.get("config")
            if config:
                codejercicio = getattr(config, "codejercicio", "")
        if not codejercicio:
            return None

        # Verificar si ya existe
        subcuentas = api_get("subcuentas", limit=1000)
        for s in subcuentas:
            if (s.get("codsubcuenta") == codsubcuenta
                    and s.get("codejercicio") == codejercicio):
                return None  # Ya existe, el error es otro

        try:
            api_post("subcuentas", {
                "codsubcuenta": codsubcuenta,
                "codcuenta": codcuenta,
                "codejercicio": codejercicio,
                "descripcion": f"Subcuenta {codsubcuenta} (auto)",
            })
            logger.info(f"  Subcuenta {codsubcuenta} creada automaticamente")
            return {"estrategia": "crear_subcuenta_auto", "datos_corregidos": doc}
        except Exception:
            return None
