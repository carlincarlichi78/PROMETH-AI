"""PerfilEmpresa — modelo de datos y lógica de acumulación y validación."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


# CP prefijos por territorio
_CP_PAIS_VASCO = {"01", "20", "48"}
_CP_NAVARRA    = {"31"}
_CP_CANARIAS   = {"35", "38"}
_CP_CEUTA      = {"51"}
_CP_MELILLA    = {"52"}


def _detectar_territorio(cp: str) -> str:
    prefijo = str(cp)[:2]
    if prefijo in _CP_PAIS_VASCO:
        return "pais_vasco"
    if prefijo in _CP_NAVARRA:
        return "navarra"
    if prefijo in _CP_CANARIAS:
        return "canarias"
    if prefijo in _CP_CEUTA:
        return "ceuta"
    if prefijo in _CP_MELILLA:
        return "melilla"
    return "peninsula"


def _normalizar_forma_juridica(raw: str) -> str:
    mapa = {
        "sl": "sl", "s.l.": "sl", "s.l": "sl",
        "sa": "sa", "s.a.": "sa",
        "slp": "slp", "slu": "slu",
        "autonomo": "autonomo", "autónomo": "autonomo",
        "cb": "cb", "comunidad de bienes": "cb",
        "sc": "sc", "sociedad civil": "sc",
        "coop": "coop", "cooperativa": "coop",
        "asociacion": "asociacion", "asociación": "asociacion",
        "fundacion": "fundacion", "fundación": "fundacion",
        "comunidad": "comunidad",
        "arrendador": "arrendador",
    }
    return mapa.get(raw.lower().strip(), "sl")


def _validar_nif(nif: str) -> bool:
    """Validación básica de formato NIF/CIF/NIE español."""
    nif = nif.strip().upper()
    # CIF: letra + 7 dígitos + letra/dígito
    if re.match(r"^[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]$", nif):
        return True
    # DNI: 8 dígitos + letra
    letras = "TRWAGMYFPDXBNJZSQVHLCKE"
    if re.match(r"^\d{8}[A-Z]$", nif):
        return nif[-1] == letras[int(nif[:-1]) % 23]
    # NIE: X/Y/Z + 7 dígitos + letra
    if re.match(r"^[XYZ]\d{7}[A-Z]$", nif):
        return True
    return False


@dataclass
class PerfilEmpresa:
    nif: str = ""
    nombre: str = ""
    nombre_comercial: Optional[str] = None
    forma_juridica: str = "sl"
    territorio: str = "peninsula"
    domicilio_fiscal: dict = field(default_factory=dict)
    fecha_alta_censal: Optional[str] = None
    fecha_inicio_actividad: Optional[str] = None

    regimen_iva: str = "general"
    regimen_iva_confirmado: bool = False
    recc: bool = False
    prorrata_historico: dict = field(default_factory=dict)
    sectores_diferenciados: list = field(default_factory=list)
    isp_aplicable: bool = False

    tipo_is: Optional[float] = None
    es_erd: bool = False
    bins_por_anyo: dict = field(default_factory=dict)
    bins_total: Optional[float] = None
    retencion_facturas_pct: Optional[float] = None
    pagos_fraccionados: dict = field(default_factory=dict)

    tiene_trabajadores: bool = False
    tiene_arrendamientos: bool = False
    socios: list = field(default_factory=list)
    operaciones_vinculadas: bool = False
    obligaciones_adicionales: list = field(default_factory=list)

    proveedores_habituales: list = field(default_factory=list)
    clientes_habituales: list = field(default_factory=list)
    sumas_saldos: Optional[dict] = None
    bienes_inversion_iva: list = field(default_factory=list)

    documentos_procesados: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)
    config_extra: dict = field(default_factory=dict)


@dataclass
class ResultadoValidacion:
    score: float = 0.0
    apto_creacion_automatica: bool = False
    requiere_revision: bool = False
    bloqueado: bool = False
    bloqueos: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)


class Acumulador:
    """Acumula datos de múltiples documentos en un PerfilEmpresa."""

    def __init__(self):
        self._perfil = PerfilEmpresa()

    def incorporar(self, tipo_doc: str, datos: dict) -> None:
        if tipo_doc == "censo_036_037":
            self._incorporar_036(datos)
        elif tipo_doc == "is_anual_200":
            self._incorporar_200(datos)
        elif tipo_doc == "iva_trimestral_303":
            self._incorporar_303(datos)
        elif tipo_doc == "iva_anual_390":
            self._incorporar_390(datos)
        elif tipo_doc == "irpf_fraccionado_130":
            self._incorporar_130(datos)
        elif tipo_doc == "irpf_anual_100":
            self._incorporar_100(datos)
        elif tipo_doc == "retenciones_111":
            self._incorporar_111(datos)
        elif tipo_doc == "retenciones_115":
            self._incorporar_115(datos)
        elif tipo_doc == "arrendamiento_180":
            self._incorporar_180(datos)
        elif tipo_doc == "libro_facturas_emitidas":
            self._perfil.clientes_habituales = datos.get("clientes", [])
        elif tipo_doc == "libro_facturas_recibidas":
            self._perfil.proveedores_habituales = datos.get("proveedores", [])
        elif tipo_doc == "sumas_y_saldos":
            self._perfil.sumas_saldos = datos.get("saldos")
            self._verificar_cuentas_alerta(datos.get("cuentas_alertas", []))
        elif tipo_doc == "libro_bienes_inversion":
            self._perfil.bienes_inversion_iva = datos.get("bienes", [])

        if tipo_doc not in self._perfil.documentos_procesados:
            self._perfil.documentos_procesados.append(tipo_doc)

    def _incorporar_036(self, datos: dict) -> None:
        self._perfil.nif = datos.get("nif", self._perfil.nif)
        self._perfil.nombre = datos.get("nombre", self._perfil.nombre)
        self._perfil.nombre_comercial = datos.get("nombre_comercial")
        self._perfil.fecha_alta_censal = datos.get("fecha_alta")
        self._perfil.regimen_iva = datos.get("regimen_iva", "general")
        dom = datos.get("domicilio", {})
        self._perfil.domicilio_fiscal = dom
        cp = str(dom.get("cp", "28000"))
        self._perfil.territorio = _detectar_territorio(cp)
        fj_raw = datos.get("forma_juridica", "sl")
        self._perfil.forma_juridica = _normalizar_forma_juridica(fj_raw)

    def _incorporar_200(self, datos: dict) -> None:
        if "tipo_is" in datos:
            self._perfil.tipo_is = datos["tipo_is"]
        if "es_erd" in datos:
            self._perfil.es_erd = datos["es_erd"]
        if "bins_total" in datos:
            self._perfil.bins_total = datos["bins_total"]

    def _incorporar_303(self, datos: dict) -> None:
        if datos.get("recc"):
            self._perfil.recc = True
        if "prorrata_pct" in datos:
            trim = datos.get("trimestre", "?")
            self._perfil.prorrata_historico[trim] = datos["prorrata_pct"]
        self._perfil.regimen_iva_confirmado = True

    def _incorporar_390(self, datos: dict) -> None:
        if "prorrata_definitiva" in datos and "ejercicio" in datos:
            self._perfil.prorrata_historico[int(datos["ejercicio"])] = \
                datos["prorrata_definitiva"]

    def _incorporar_130(self, datos: dict) -> None:
        if "pago_fraccionado" in datos and "trimestre" in datos:
            self._perfil.pagos_fraccionados[datos["trimestre"]] = \
                datos["pago_fraccionado"]

    def _incorporar_100(self, datos: dict) -> None:
        if "retencion_pct" in datos:
            self._perfil.retencion_facturas_pct = datos["retencion_pct"]

    def _incorporar_111(self, datos: dict) -> None:
        if datos.get("tiene_trabajadores"):
            self._perfil.tiene_trabajadores = True

    def _incorporar_115(self, datos: dict) -> None:
        if datos.get("tiene_arrendamientos"):
            self._perfil.tiene_arrendamientos = True

    def _incorporar_180(self, datos: dict) -> None:
        if datos.get("tiene_arrendamientos"):
            self._perfil.tiene_arrendamientos = True

    def _verificar_cuentas_alerta(self, cuentas: list) -> None:
        for cuenta in cuentas:
            if cuenta.startswith("55"):
                self._perfil.advertencias.append(
                    f"Cuenta {cuenta} con saldo — posible préstamo socio/operación vinculada")
            if cuenta.startswith("4750"):
                self._perfil.advertencias.append(
                    f"Cuenta {cuenta} con saldo — deuda AEAT preexistente")

    def obtener_perfil(self) -> PerfilEmpresa:
        return self._perfil


class Validador:
    """Valida un PerfilEmpresa y calcula su score de confianza."""

    def validar(self, perfil: PerfilEmpresa) -> ResultadoValidacion:
        resultado = ResultadoValidacion()
        self._checks_duros(perfil, resultado)
        self._checks_blandos(perfil, resultado)
        resultado.score = self._calcular_score(perfil, resultado)

        if resultado.bloqueos:
            resultado.bloqueado = True
            resultado.apto_creacion_automatica = False
        elif resultado.score >= 85:
            resultado.apto_creacion_automatica = True
        elif resultado.score >= 60:
            resultado.requiere_revision = True
        else:
            resultado.requiere_revision = True

        return resultado

    def _checks_duros(self, perfil: PerfilEmpresa,
                      resultado: ResultadoValidacion) -> None:
        if not _validar_nif(perfil.nif):
            resultado.bloqueos.append(f"NIF inválido: {perfil.nif}")

        if perfil.territorio in ("pais_vasco", "navarra"):
            resultado.bloqueos.append(
                f"Territorio {perfil.territorio}: requiere gestor foral, "
                "sistema fiscal diferente (Concierto Económico)")

        if "censo_036_037" not in perfil.documentos_procesados:
            resultado.bloqueos.append(
                "Falta documento base: 036/037 obligatorio")

        if (perfil.sumas_saldos is not None and
                not perfil.sumas_saldos.get("_cuadra", True)):
            resultado.bloqueos.append(
                "Sumas y saldos no cuadran (activo ≠ pasivo+PN)")

    def _checks_blandos(self, perfil: PerfilEmpresa,
                        resultado: ResultadoValidacion) -> None:
        if perfil.bienes_inversion_iva and not perfil.prorrata_historico:
            resultado.advertencias.append(
                "Bienes de inversión sin historial prorrata — "
                "regularización IVA futura puede ser incorrecta")

        if perfil.territorio == "canarias":
            resultado.advertencias.append(
                "Canarias: verificar régimen IGIC vs IVA")

        if perfil.bins_total and not perfil.bins_por_anyo:
            resultado.advertencias.append(
                "BINs pendientes sin detalle por año — "
                "cada año tiene reglas de caducidad distintas")

    def _calcular_score(self, perfil: PerfilEmpresa,
                        resultado: ResultadoValidacion) -> float:
        score = 0.0

        if "censo_036_037" in perfil.documentos_procesados:
            score += 40
        if ("libro_facturas_emitidas" in perfil.documentos_procesados and
                "libro_facturas_recibidas" in perfil.documentos_procesados):
            score += 20
        if "sumas_y_saldos" in perfil.documentos_procesados:
            score += 15
        if perfil.forma_juridica not in ("", "sl"):
            score += 10
        if perfil.regimen_iva_confirmado:
            score += 10
        if not resultado.advertencias:
            score += 5

        # Penalizaciones
        if not _validar_nif(perfil.nif):
            score -= 30
        if perfil.territorio in ("pais_vasco", "navarra"):
            score -= 15
        if perfil.bienes_inversion_iva and not perfil.prorrata_historico:
            score -= 10

        return max(0.0, score)
