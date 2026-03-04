"""
Motor de conciliación bancaria.

Empareja MovimientoBancario (extracto C43/XLS) con Asiento (contabilidad).
Niveles de matching:
  1. Exacto   — mismo importe + fecha dentro de ventana (VENTANA_DIAS)
  2. Aproximado — diferencia < TOLERANCIA_PCT (1 %) y fecha compatible
  3. Sin match → estado "pendiente" sin cambios
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from sfce.db.modelos import Asiento, MovimientoBancario


@dataclass
class ResultadoMatch:
    """Resultado de un emparejamiento movimiento ↔ asiento."""
    movimiento_id: int
    asiento_id: int
    tipo: str       # 'exacto' | 'aproximado' | 'manual'
    diferencia: Decimal
    confianza: float    # 0.0 – 1.0


class MotorConciliacion:
    VENTANA_DIAS: int = 2             # tolerancia de fecha (días)
    TOLERANCIA_PCT: float = 0.01      # 1 % de diferencia para match aproximado

    def __init__(self, session: Session, empresa_id: int):
        self.session = session
        self.empresa_id = empresa_id

    def conciliar(self) -> List[ResultadoMatch]:
        """Ejecuta conciliación completa. Devuelve lista de matches."""
        movimientos = (
            self.session.query(MovimientoBancario)
            .filter_by(empresa_id=self.empresa_id, estado_conciliacion="pendiente")
            .all()
        )
        asientos = (
            self.session.query(Asiento)
            .filter_by(empresa_id=self.empresa_id)
            .all()
        )

        matches: List[ResultadoMatch] = []
        asientos_usados: set = set()

        # Pasada 1 — match exacto (prioridad máxima)
        for mov in movimientos:
            match = self._buscar_exacto(mov, asientos, asientos_usados)
            if match:
                matches.append(match)
                asientos_usados.add(match.asiento_id)

        # Pasada 2 — match aproximado para los que quedan sin conciliar
        conciliados = {m.movimiento_id for m in matches}
        for mov in movimientos:
            if mov.id in conciliados:
                continue
            match = self._buscar_aproximado(mov, asientos, asientos_usados)
            if match:
                matches.append(match)
                asientos_usados.add(match.asiento_id)

        # Aplicar a BD
        for m in matches:
            mov_obj = self.session.get(MovimientoBancario, m.movimiento_id)
            if mov_obj:
                mov_obj.asiento_id = m.asiento_id
                mov_obj.estado_conciliacion = (
                    "conciliado" if m.tipo == "exacto" else "revision"
                )

        self.session.flush()
        return matches

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _buscar_exacto(
        self,
        mov: MovimientoBancario,
        asientos: list,
        usados: set,
    ) -> Optional[ResultadoMatch]:
        for asiento in asientos:
            if asiento.id in usados:
                continue
            if not self._fechas_compatibles(mov.fecha, asiento.fecha):
                continue
            importe = self._importe_asiento(asiento)
            if importe is not None and importe == mov.importe:
                return ResultadoMatch(
                    movimiento_id=mov.id,
                    asiento_id=asiento.id,
                    tipo="exacto",
                    diferencia=Decimal("0"),
                    confianza=1.0,
                )
        return None

    def _buscar_aproximado(
        self,
        mov: MovimientoBancario,
        asientos: list,
        usados: set,
    ) -> Optional[ResultadoMatch]:
        mejor: Optional[ResultadoMatch] = None
        for asiento in asientos:
            if asiento.id in usados:
                continue
            if not self._fechas_compatibles(mov.fecha, asiento.fecha):
                continue
            importe = self._importe_asiento(asiento)
            if not importe or importe == Decimal("0"):
                continue
            diferencia = abs(mov.importe - importe)
            pct = diferencia / mov.importe if mov.importe else Decimal("1")
            if pct <= Decimal(str(self.TOLERANCIA_PCT)):
                confianza = float(1 - pct)
                if mejor is None or confianza > mejor.confianza:
                    mejor = ResultadoMatch(
                        movimiento_id=mov.id,
                        asiento_id=asiento.id,
                        tipo="aproximado",
                        diferencia=diferencia,
                        confianza=confianza,
                    )
        return mejor

    def _fechas_compatibles(self, fecha_mov: date, fecha_asiento: date) -> bool:
        return abs((fecha_mov - fecha_asiento).days) <= self.VENTANA_DIAS

    def _importe_asiento(self, asiento: Asiento) -> Optional[Decimal]:
        """Suma el debe de las partidas del asiento."""
        if not asiento.partidas:
            return None
        total = sum(p.debe or Decimal("0") for p in asiento.partidas)
        return total if total > Decimal("0") else None

    # ----------------------------------------------------------------
    # Motor Inteligente — 5 Capas
    # ----------------------------------------------------------------

    VENTANA_NIF    = 5   # días para capas 2-3
    VENTANA_PATRON = 7   # días para capa 4
    UMBRAL_REDONDEO = Decimal("0.05")

    def conciliar_inteligente(self) -> dict:
        """
        Ejecuta conciliación de 5 capas sobre documentos del pipeline.
        Devuelve stats: {conciliados_auto, sugeridos, revision, pendientes}.
        """
        from sfce.db.modelos import Documento, SugerenciaMatch
        from sfce.core.normalizar_bancario import limpiar_nif, normalizar_concepto, rango_importe

        pendientes = (
            self.session.query(MovimientoBancario)
            .filter(
                MovimientoBancario.empresa_id == self.empresa_id,
                MovimientoBancario.estado_conciliacion == "pendiente",
            )
            .all()
        )

        docs_usados: set = set()

        # CAPA 1 — Exacta y unívoca
        for mov in pendientes:
            candidatos = self._docs_por_importe(mov.importe, pct=0, ventana=self.VENTANA_DIAS, usados=docs_usados)
            if len(candidatos) == 1:
                doc = candidatos[0]
                self._conciliar_automatico(mov, doc, capa=1, score=1.0)
                docs_usados.add(doc.id)
            elif len(candidatos) > 1:
                for doc in candidatos:
                    diff_dias = abs((mov.fecha - doc.fecha_documento).days) if doc.fecha_documento else 99
                    score = 1.0 - diff_dias * 0.05
                    self._insertar_sugerencia(mov, doc, capa=1, score=max(score, 0.70))
                mov.estado_conciliacion = "sugerido"

        self.session.flush()
        return self._estadisticas_conciliacion(pendientes)

    def _docs_por_importe(self, importe, pct, ventana, usados) -> list:
        """Consulta SQL: documentos por rango de importe + sin usar."""
        from sfce.db.modelos import Documento
        margen = importe * Decimal(str(pct))
        return (
            self.session.query(Documento)
            .filter(
                Documento.empresa_id == self.empresa_id,
                Documento.asiento_id.isnot(None),
                Documento.importe_total.between(importe - margen, importe + margen),
                Documento.id.notin_(list(usados)) if usados else True,
            )
            .all()
        )

    def _conciliar_automatico(self, mov, doc, capa, score):
        """Marca el movimiento como conciliado y vincula el documento."""
        import json
        mov.documento_id = doc.id
        mov.asiento_id = doc.asiento_id
        mov.estado_conciliacion = "conciliado"
        mov.score_confianza = score
        mov.capa_match = capa
        mov.metadata_match = json.dumps({"capa": capa, "documento_id": doc.id})

    def _insertar_sugerencia(self, mov, doc, capa, score):
        """Inserta una SugerenciaMatch si no existe."""
        from sfce.db.modelos import SugerenciaMatch
        existente = (
            self.session.query(SugerenciaMatch)
            .filter_by(movimiento_id=mov.id, documento_id=doc.id)
            .first()
        )
        if not existente:
            self.session.add(SugerenciaMatch(
                movimiento_id=mov.id,
                documento_id=doc.id,
                score=score,
                capa_origen=capa,
                activa=True,
            ))

    def _estadisticas_conciliacion(self, pendientes_originales) -> dict:
        conciliados_auto = sum(
            1 for m in pendientes_originales
            if self.session.get(MovimientoBancario, m.id).estado_conciliacion == "conciliado"
            and self.session.get(MovimientoBancario, m.id).capa_match is not None
        )
        sugeridos = sum(
            1 for m in pendientes_originales
            if self.session.get(MovimientoBancario, m.id).estado_conciliacion == "sugerido"
        )
        revision = sum(
            1 for m in pendientes_originales
            if self.session.get(MovimientoBancario, m.id).estado_conciliacion == "revision"
        )
        return {
            "conciliados_auto": conciliados_auto,
            "sugeridos": sugeridos,
            "revision": revision,
            "pendientes": len(pendientes_originales) - conciliados_auto - sugeridos - revision,
        }
