"""Motor de generacion de ficheros XML para modelos que usan formato XSD (ej: 200)."""
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from sfce.modelos_fiscales.tipos import (
    DisenoModelo, RegistroSpec, CampoSpec, ResultadoGeneracion
)


class MotorXML:
    """Genera ficheros XML desde un DisenoModelo con tipo_formato='xml'.

    Para modelos como el 200 (Impuesto Sociedades) que usan formato XML/XSD
    en vez de registros posicionales.
    """

    def generar(
        self,
        diseno: DisenoModelo,
        ejercicio: str,
        periodo: str,
        casillas: dict,
        empresa: dict
    ) -> ResultadoGeneracion:
        """Genera fichero XML para el modelo.

        Los registros del diseno se interpretan como nodos XML:
        - tipo="raiz" → elemento raiz
        - tipo="grupo_*" → elemento contenedor
        - tipo="casillas_*" → elementos con valores de casillas

        Cada campo del registro se convierte en un sub-elemento o atributo.
        """
        raiz = Element("declaracion")
        raiz.set("modelo", diseno.modelo)
        raiz.set("ejercicio", ejercicio)

        for registro in diseno.registros:
            nodo = SubElement(raiz, registro.tipo.replace(" ", "_"))
            for campo in registro.campos:
                valor = self._resolver_valor(
                    campo, ejercicio, periodo, casillas, empresa
                )
                sub = SubElement(nodo, campo.nombre)
                sub.text = str(valor) if valor is not None else ""

        xml_bytes = tostring(raiz, encoding="unicode")
        xml_formateado = parseString(xml_bytes).toprettyxml(
            indent="  ", encoding=None
        )
        # Quitar declaracion XML duplicada si minidom la agrega
        lineas = xml_formateado.split("\n")
        if lineas[0].startswith("<?xml"):
            contenido = '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(lineas[1:])
        else:
            contenido = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_formateado

        nif = empresa.get("nif", "")
        nombre_fichero = f"{nif}_{ejercicio}_{periodo}.{diseno.modelo}.xml"

        return ResultadoGeneracion(
            modelo=diseno.modelo,
            ejercicio=ejercicio,
            periodo=periodo,
            contenido=contenido,
            formato="xml",
            nombre_fichero=nombre_fichero
        )

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
        if fuente.startswith("casillas."):
            clave = fuente.split(".", 1)[1]
            return casillas.get(clave, 0)
        if fuente.startswith("empresa."):
            clave = fuente.split(".", 1)[1]
            return empresa.get(clave, "")
        return ""
