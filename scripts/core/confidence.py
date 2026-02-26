"""Sistema de puntuacion de confianza para datos extraidos."""
from dataclasses import dataclass, field
from typing import Optional


UMBRALES = {
    "cif": 90,
    "importe": 85,
    "fecha": 85,
    "numero_factura": 80,
    "tipo_iva": 90,
    "divisa": 95,
}

PESOS_FUENTE = {
    "pdfplumber": 40,    # Extraccion deterministica de texto
    "gpt": 30,           # Parsing LLM del texto
    "config": 10,        # Coincide con config.yaml esperado
    "fs_api": 20,        # Coincide con dato en FS (si existe)
}


@dataclass
class DatoConConfianza:
    """Un dato con su puntuacion de confianza."""
    campo: str
    valor: any
    confianza: int = 0
    fuentes: dict = field(default_factory=dict)  # fuente -> valor extraido

    def agregar_fuente(self, fuente: str, valor):
        """Agrega una fuente de extraccion."""
        self.fuentes[fuente] = valor
        self._recalcular()

    def _recalcular(self):
        """Recalcula confianza basada en coincidencia de fuentes."""
        if not self.fuentes:
            self.confianza = 0
            return

        # Si solo hay una fuente
        if len(self.fuentes) == 1:
            fuente = list(self.fuentes.keys())[0]
            self.confianza = PESOS_FUENTE.get(fuente, 25)
            self.valor = list(self.fuentes.values())[0]
            return

        # Multiples fuentes: valor de referencia = el de mayor peso
        valor_ref = None
        max_peso = 0

        for fuente, val in self.fuentes.items():
            peso = PESOS_FUENTE.get(fuente, 10)
            if peso > max_peso:
                max_peso = peso
                valor_ref = val

        self.valor = valor_ref

        # Sumar pesos de fuentes que coinciden, restar mitad de discrepantes
        self.confianza = 0
        for fuente, val in self.fuentes.items():
            peso = PESOS_FUENTE.get(fuente, 10)
            if self._valores_coinciden(val, valor_ref):
                self.confianza += peso
            else:
                self.confianza -= peso // 2

        self.confianza = max(0, min(100, self.confianza))

    @staticmethod
    def _valores_coinciden(v1, v2) -> bool:
        """Compara valores con tolerancia para numeros."""
        if v1 is None or v2 is None:
            return v1 == v2
        try:
            f1, f2 = float(v1), float(v2)
            return abs(f1 - f2) < 0.02
        except (ValueError, TypeError):
            return str(v1).strip().upper() == str(v2).strip().upper()

    def pasa_umbral(self) -> bool:
        """Verifica si supera el umbral minimo para este campo."""
        umbral = UMBRALES.get(self.campo, 85)
        return self.confianza >= umbral


@dataclass
class DocumentoConfianza:
    """Resultado de extraccion de un documento con confianzas."""
    archivo: str
    hash_sha256: str
    tipo: str = ""  # FC, FV, NC, ANT, etc.
    datos: dict = field(default_factory=dict)  # campo -> DatoConConfianza

    def agregar_dato(self, campo: str, fuente: str, valor):
        """Agrega un dato de una fuente."""
        if campo not in self.datos:
            self.datos[campo] = DatoConConfianza(campo=campo, valor=valor)
        self.datos[campo].agregar_fuente(fuente, valor)

    def confianza_global(self) -> int:
        """Calcula confianza promedio ponderada del documento."""
        if not self.datos:
            return 0

        campos_criticos = {"cif", "importe", "fecha", "numero_factura"}
        total_peso = 0
        total_confianza = 0

        for campo, dato in self.datos.items():
            peso = 3 if campo in campos_criticos else 1
            total_peso += peso
            total_confianza += dato.confianza * peso

        return round(total_confianza / total_peso) if total_peso > 0 else 0

    def campos_bajo_umbral(self) -> list[str]:
        """Devuelve campos que no pasan su umbral."""
        return [c for c, d in self.datos.items() if not d.pasa_umbral()]

    def es_fiable(self) -> bool:
        """True si todos los campos criticos pasan umbral."""
        criticos = {"cif", "importe", "fecha"}
        for campo in criticos:
            if campo in self.datos and not self.datos[campo].pasa_umbral():
                return False
        return self.confianza_global() >= 85


def calcular_nivel(score: int) -> str:
    """Devuelve nivel de fiabilidad."""
    if score >= 95:
        return "FIABLE"
    elif score >= 85:
        return "ACEPTABLE"
    return "NO_FIABLE"
