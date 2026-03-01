from dataclasses import dataclass, field


@dataclass
class ResultadoEsperado:
    http_status: int = 200
    debe_igual_haber: bool = True
    iva_correcto: bool = True
    asiento_no_invertido: bool = True
    sync_bd: bool = True
    campos_extra: dict = field(default_factory=dict)


@dataclass
class VarianteEjecucion:
    escenario_id: str
    variante_id: str
    datos_extraidos: dict
    resultado_esperado: ResultadoEsperado
    descripcion_variante: str = ""


@dataclass
class Escenario:
    id: str
    grupo: str
    descripcion: str
    datos_extraidos_base: dict
    resultado_esperado: ResultadoEsperado
    etiquetas: list = field(default_factory=list)

    def crear_variante(self, overrides: dict, variante_id: str, descripcion: str = "") -> VarianteEjecucion:
        datos = {**self.datos_extraidos_base, **overrides}
        return VarianteEjecucion(
            escenario_id=self.id,
            variante_id=variante_id,
            datos_extraidos=datos,
            resultado_esperado=self.resultado_esperado,
            descripcion_variante=descripcion,
        )
