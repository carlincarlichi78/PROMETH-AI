"""Perfil fiscal de un cliente — deriva modelos, libros y obligaciones automaticamente."""
from dataclasses import dataclass, field
from typing import Optional


# Mapeo territorio -> impuesto indirecto
_TERRITORIO_IMPUESTO = {
    "peninsula": "iva",
    "canarias": "igic",
    "ceuta_melilla": "ipsi",
    "navarra": "iva",
    "pais_vasco": "iva",
}

# Formas juridicas que son personas juridicas
_JURIDICAS = {"sl", "slu", "sa", "sll", "cb", "scp", "cooperativa",
              "asociacion", "comunidad_propietarios"}

# Formas juridicas que depositan cuentas en RM
_DEPOSITAN_CUENTAS = {"sl", "slu", "sa", "sll"}

# Formas juridicas que tributan IS (excluir comunidades propietarios y asociaciones exentas)
_TRIBUTAN_IS = {"sl", "slu", "sa", "sll", "cb", "scp", "cooperativa"}


@dataclass
class PerfilFiscal:
    """Perfil fiscal completo de un cliente.

    Deriva automaticamente impuesto_indirecto, modelos obligatorios,
    libros obligatorios y periodicidad segun los datos de entrada.
    """
    # --- Identidad ---
    tipo_persona: str = "juridica"  # "fisica" | "juridica"
    forma_juridica: str = "sl"

    # --- Territorio ---
    territorio: str = "peninsula"

    # --- Regimen IVA/IGIC ---
    regimen_iva: str = "general"
    prorrata: bool = False
    pct_prorrata: int = 100
    sectores_diferenciados: bool = False
    actividades: list = field(default_factory=list)

    # --- IRPF (solo fisicas) ---
    regimen_irpf: Optional[str] = None
    retencion_emitidas: bool = False
    pct_retencion_emitidas: Optional[int] = None

    # --- Modulos ---
    modulos: dict = field(default_factory=dict)

    # --- IS (solo juridicas) ---
    tipo_is: Optional[int] = None
    pagos_fraccionados_is: bool = False
    bases_negativas_pendientes: float = 0.0

    # --- Retenciones ---
    retiene_profesionales: bool = False
    retiene_alquileres: bool = False
    retiene_capital: bool = False
    paga_no_residentes: bool = False

    # --- Operaciones especiales ---
    operador_intracomunitario: bool = False
    importador: bool = False
    exportador: bool = False
    isp_construccion: bool = False
    isp_otros: bool = False
    operaciones_vinculadas: bool = False

    # --- Bienes de inversion ---
    tiene_bienes_inversion: bool = False
    amortizacion_metodo: str = "lineal"
    regularizacion_iva_bi: bool = False

    # --- Tamano ---
    sii_obligatorio: bool = False
    gran_empresa: bool = False
    deposita_cuentas: bool = False
    tipo_cuentas: Optional[str] = None

    # --- Plan contable ---
    plan_contable: str = "pgc_pymes"

    def __post_init__(self):
        # Derivar tipo_persona desde forma_juridica si no coincide
        if self.forma_juridica in _JURIDICAS:
            self.tipo_persona = "juridica"
        else:
            self.tipo_persona = "fisica"

        # Personas fisicas no tributan IS
        if self.tipo_persona == "fisica":
            self.tipo_is = None
            self.pagos_fraccionados_is = False
        elif self.tipo_is is None and self.forma_juridica in _TRIBUTAN_IS:
            self.tipo_is = 25

        # Personas juridicas no tienen IRPF
        if self.tipo_persona == "juridica":
            self.regimen_irpf = None

        # Deposito cuentas
        if self.forma_juridica in _DEPOSITAN_CUENTAS:
            self.deposita_cuentas = True

        # Comunidades de propietarios no tributan IS
        if self.forma_juridica == "comunidad_propietarios":
            self.tipo_is = None

    @property
    def impuesto_indirecto(self) -> str:
        return _TERRITORIO_IMPUESTO.get(self.territorio, "iva")

    @property
    def periodicidad(self) -> str:
        return "mensual" if self.gran_empresa else "trimestral"

    def modelos_obligatorios(self) -> dict[str, list[str]]:
        """Deriva modelos fiscales obligatorios segun el perfil."""
        trimestrales = []
        anuales = []

        # IVA / IGIC / IPSI
        if self.regimen_iva != "exento":
            if self.impuesto_indirecto == "iva":
                trimestrales.append("303")
                anuales.append("390")
            elif self.impuesto_indirecto == "igic":
                trimestrales.append("420")

        # IRPF (solo fisicas)
        if self.regimen_irpf == "objetiva":
            trimestrales.append("131")
            anuales.append("100")
        elif self.regimen_irpf in ("directa_simplificada", "directa_normal"):
            trimestrales.append("130")
            anuales.append("100")

        # IS (solo juridicas)
        if self.tipo_is is not None:
            anuales.append("200")
        if self.pagos_fraccionados_is:
            trimestrales.append("202")

        # Retenciones
        if self.retiene_profesionales:
            trimestrales.append("111")
            anuales.append("190")
        if self.retiene_alquileres:
            trimestrales.append("115")
            anuales.append("180")
        if self.retiene_capital:
            trimestrales.append("123")
            anuales.append("193")

        # Operaciones especiales
        if self.operador_intracomunitario:
            trimestrales.append("349")

        # 347 (operaciones con terceros > 3005.06)
        if self.tipo_is is not None or self.tipo_persona == "fisica":
            anuales.append("347")

        return {"trimestrales": trimestrales, "anuales": anuales}

    def libros_obligatorios(self) -> list[str]:
        """Deriva libros contables/registros obligatorios."""
        libros = []

        if self.tipo_persona == "juridica":
            libros.extend([
                "libro_diario",
                "libro_inventarios_cuentas_anuales",
            ])
        if self.tipo_persona == "fisica":
            libros.extend([
                "registro_facturas_emitidas",
                "registro_facturas_recibidas",
                "libro_bienes_inversion",
            ])
            if self.regimen_irpf in ("directa_simplificada", "directa_normal"):
                libros.append("libro_gastos")

        # Comun
        if self.regimen_iva != "exento":
            if "registro_facturas_emitidas" not in libros:
                libros.append("registro_facturas_emitidas")
            if "registro_facturas_recibidas" not in libros:
                libros.append("registro_facturas_recibidas")

        return libros

    @classmethod
    def desde_dict(cls, datos: dict) -> "PerfilFiscal":
        """Crea PerfilFiscal desde un diccionario (config.yaml)."""
        campos_validos = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in datos.items() if k in campos_validos}
        return cls(**kwargs)
