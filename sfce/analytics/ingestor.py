"""Ingestor — transforma eventos analíticos en filas del star schema."""
import json
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sfce.analytics.event_store import registrar
from sfce.analytics.modelos_analiticos import (
    EventoAnalitico, FactCaja, FactVenta, FactCompra, FactPersonal,
)


class Ingestor:
    def __init__(self, sesion: Session):
        self._sesion = sesion

    def registrar_evento(self, empresa_id: int, tipo: str,
                          fecha: date, payload: dict) -> int:
        return registrar(self._sesion, empresa_id, tipo, fecha, payload)

    def procesar_evento(self, evento_id: int) -> None:
        evento = self._sesion.get(EventoAnalitico, evento_id)
        if not evento or evento.procesado:
            return
        payload = json.loads(evento.payload) if isinstance(evento.payload, str) else evento.payload
        tipo = evento.tipo_evento

        if tipo == "TPV":
            self._procesar_tpv(evento, payload)
        elif tipo in ("BAN", "BAN_DETALLE"):
            self._procesar_ban(evento, payload)
        elif tipo == "NOM":
            self._procesar_nom(evento, payload)

        evento.procesado = True

    def procesar_pendientes(self, empresa_id: Optional[int] = None) -> int:
        from sqlalchemy import select
        q = select(EventoAnalitico).where(EventoAnalitico.procesado == False)
        if empresa_id:
            q = q.where(EventoAnalitico.empresa_id == empresa_id)
        eventos = self._sesion.execute(q).scalars().all()
        for ev in eventos:
            self._procesar_evento_obj(ev)
        return len(eventos)

    def _procesar_tpv(self, evento: EventoAnalitico, payload: dict) -> None:
        caja = FactCaja(
            empresa_id=evento.empresa_id,
            fecha=evento.fecha_evento,
            servicio=payload.get("servicio", "general"),
            covers=payload.get("covers", 0),
            ventas_totales=payload.get("ventas_totales", 0.0),
            ticket_medio=(
                payload["ventas_totales"] / payload["covers"]
                if payload.get("covers", 0) > 0 else 0.0
            ),
            num_mesas_ocupadas=payload.get("num_mesas_ocupadas", 0),
            metodo_pago_tarjeta=payload.get("metodo_pago_tarjeta", 0.0),
            metodo_pago_efectivo=payload.get("metodo_pago_efectivo", 0.0),
            metodo_pago_otros=payload.get("metodo_pago_otros", 0.0),
            evento_id=evento.id,
        )
        self._sesion.add(caja)

        for prod in payload.get("productos", []):
            venta = FactVenta(
                empresa_id=evento.empresa_id,
                fecha=evento.fecha_evento,
                servicio=payload.get("servicio", "general"),
                producto_nombre=prod.get("nombre", ""),
                familia=prod.get("familia", "otros"),
                qty=prod.get("qty", 0),
                pvp_unitario=prod.get("pvp_unitario", 0.0),
                total=prod.get("total", 0.0),
                evento_id=evento.id,
            )
            self._sesion.add(venta)

    def _procesar_ban(self, evento: EventoAnalitico, payload: dict) -> None:
        if payload.get("importe", 0) < 0:  # solo pagos (salidas)
            compra = FactCompra(
                empresa_id=evento.empresa_id,
                fecha=evento.fecha_evento,
                proveedor_nombre=payload.get("concepto", "Desconocido"),
                proveedor_cif=payload.get("cif_proveedor"),
                familia=payload.get("familia_gasto", "otros"),
                importe=abs(payload.get("importe", 0.0)),
                tipo_movimiento="compra",
                evento_id=evento.id,
            )
            self._sesion.add(compra)

    def _procesar_nom(self, evento: EventoAnalitico, payload: dict) -> None:
        periodo = evento.fecha_evento.strftime("%Y-%m")
        personal = FactPersonal(
            empresa_id=evento.empresa_id,
            periodo=periodo,
            empleado_nombre=payload.get("empleado_nombre"),
            coste_bruto=payload.get("salario_bruto", 0.0),
            coste_ss_empresa=payload.get("ss_empresa", 0.0),
            coste_total=payload.get("coste_total_empresa", 0.0),
            dias_baja=payload.get("dias_baja", 0),
            evento_id=evento.id,
        )
        self._sesion.add(personal)

    def _procesar_evento_obj(self, evento: EventoAnalitico) -> None:
        payload = json.loads(evento.payload) if isinstance(evento.payload, str) else evento.payload
        if evento.tipo_evento == "TPV":
            self._procesar_tpv(evento, payload)
        elif evento.tipo_evento in ("BAN", "BAN_DETALLE"):
            self._procesar_ban(evento, payload)
        elif evento.tipo_evento == "NOM":
            self._procesar_nom(evento, payload)
        evento.procesado = True
