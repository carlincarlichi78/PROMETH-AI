"""Motor generico de generacion de ficheros BOE posicionales."""
from sfce.modelos_fiscales.tipos import (
    CampoSpec, DisenoModelo, RegistroSpec, TipoCampo, ResultadoGeneracion
)


class MotorBOE:
    """Genera ficheros en formato BOE posicional desde un DisenoModelo."""

    def generar(
        self,
        diseno: DisenoModelo,
        ejercicio: str,
        periodo: str,
        casillas: dict,
        empresa: dict,
        declarados: list[dict] | None = None
    ) -> ResultadoGeneracion:
        """Genera fichero BOE posicional.

        Args:
            diseno: Especificacion del modelo
            ejercicio: Ano fiscal (ej: "2025")
            periodo: Periodo (ej: "1T", "0A")
            casillas: Dict de casillas {clave: valor}
            empresa: Datos empresa {nif, nombre, ...}
            declarados: Lista de declarados para registros repetibles (347, 190, etc.)
        """
        lineas = []
        for registro in diseno.registros:
            if registro.repetible and declarados:
                for declarado in declarados:
                    casillas_declarado = {**casillas, **declarado}
                    linea = self._generar_registro(
                        registro, diseno.longitud_registro,
                        ejercicio, periodo, casillas_declarado, empresa
                    )
                    lineas.append(linea)
            else:
                linea = self._generar_registro(
                    registro, diseno.longitud_registro,
                    ejercicio, periodo, casillas, empresa
                )
                lineas.append(linea)

        nif = empresa.get("nif", "")
        nombre_fichero = f"{nif}_{ejercicio}_{periodo}.{diseno.modelo}"
        contenido = "\r\n".join(lineas) if len(lineas) > 1 else lineas[0]

        return ResultadoGeneracion(
            modelo=diseno.modelo,
            ejercicio=ejercicio,
            periodo=periodo,
            contenido=contenido,
            formato=diseno.tipo_formato,
            nombre_fichero=nombre_fichero
        )

    def _generar_registro(
        self, registro: RegistroSpec, longitud: int,
        ejercicio: str, periodo: str, casillas: dict, empresa: dict
    ) -> str:
        linea = list(" " * longitud)
        for campo in registro.campos:
            valor = self._resolver_valor(campo, ejercicio, periodo, casillas, empresa)
            formateado = self._formatear_campo(campo, valor)
            inicio = campo.posicion[0] - 1  # 1-indexed -> 0-indexed
            for i, char in enumerate(formateado):
                if inicio + i < longitud:
                    linea[inicio + i] = char
        return "".join(linea)

    def _resolver_valor(
        self, campo: CampoSpec, ejercicio: str, periodo: str,
        casillas: dict, empresa: dict
    ):
        if campo.valor_fijo is not None:
            return campo.valor_fijo
        fuente = campo.fuente or ""
        if fuente == "ejercicio":
            return ejercicio
        if fuente == "periodo":
            return periodo
        if fuente == "nif_declarante":
            return empresa.get("nif", "")
        if fuente == "nombre_declarante":
            return empresa.get("nombre_fiscal", empresa.get("nombre", ""))
        if fuente.startswith("casillas."):
            clave = fuente.split(".", 1)[1]
            return casillas.get(clave, 0)
        if fuente.startswith("empresa."):
            clave = fuente.split(".", 1)[1]
            return empresa.get(clave, "")
        if fuente.startswith("declarado."):
            clave = fuente.split(".", 1)[1]
            return casillas.get(clave, "")
        return ""

    def _formatear_campo(self, campo: CampoSpec, valor) -> str:
        longitud = campo.longitud
        if campo.tipo == TipoCampo.ALFANUMERICO:
            texto = str(valor).upper()[:longitud]
            return texto.ljust(longitud)
        if campo.tipo == TipoCampo.NUMERICO:
            if isinstance(valor, float):
                texto = str(int(valor))
            else:
                texto = str(valor)
            texto = texto[:longitud]
            return texto.zfill(longitud)
        if campo.tipo == TipoCampo.NUMERICO_SIGNO:
            num = float(valor) if valor else 0.0
            signo = "N" if num < 0 else " "
            abs_val = abs(num)
            entero = int(round(abs_val * (10 ** campo.decimales)))
            parte_num = str(entero).zfill(longitud - 1)[:longitud - 1]
            return signo + parte_num
        if campo.tipo == TipoCampo.FECHA:
            texto = str(valor)[:longitud]
            return texto.zfill(longitud)
        if campo.tipo == TipoCampo.TELEFONO:
            texto = str(valor)[:longitud]
            return texto.zfill(longitud)
        return str(valor)[:longitud].ljust(longitud)
