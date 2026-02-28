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
