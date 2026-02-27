"""MotorReglas — nucleo del sistema de reglas contables SFCE.

Orquesta clasificador, normativa y perfil fiscal para producir
DecisionContable con trazabilidad completa.

Jerarquia de decision:
1. Regla cliente (config.yaml) — confianza 95%
2. Aprendizaje previo — confianza 85%
3. Tipo documento — confianza 80%
4. Palabras clave OCR — confianza 60%
5. Cuarentena — confianza 0%
"""
from datetime import date
from typing import Optional

from .clasificador import Clasificador
from .config import ConfigCliente
from .decision import DecisionContable
from ..normativa.vigente import Normativa


class MotorReglas:
    """Nucleo del sistema de reglas contables.

    Combina clasificador (que subcuenta), normativa (que IVA/IRPF)
    y perfil fiscal (que obligaciones) para producir DecisionContable.
    """

    def __init__(self, config: ConfigCliente,
                 normativa: Normativa | None = None,
                 aprendizaje: dict | None = None):
        self.config = config
        self.normativa = normativa or Normativa()
        self._aprendizaje = aprendizaje or {}
        self.clasificador = Clasificador(
            config, aprendizaje=self._aprendizaje)

    def decidir_asiento(self, documento: dict,
                        fecha: date | None = None) -> DecisionContable:
        """Decide subcuenta, IVA, retencion y genera DecisionContable.

        Args:
            documento: dict con emisor_cif, tipo_doc, concepto, base_imponible.
            fecha: fecha para consultar normativa (default: hoy).

        Returns:
            DecisionContable con todos los parametros y log_razonamiento.
        """
        fecha = fecha or date.today()
        log = []
        perfil = self.config.perfil_fiscal
        territorio = perfil.territorio if perfil else "peninsula"

        # 1. Clasificar subcuenta via cascada
        resultado = self.clasificador.clasificar(documento)
        log.extend(resultado.log)

        subcuenta_gasto = resultado.subcuenta
        confianza = resultado.confianza
        origen = resultado.origen

        # 2. Determinar parametros fiscales
        cif = documento.get("emisor_cif", "")
        prov = self.config.buscar_proveedor_por_cif(cif) if cif else None

        # Parametros base desde proveedor o defaults
        codimpuesto = "IVA21"
        tipo_iva = 21.0
        retencion_pct = None
        recargo_equiv = None
        regimen = "general"
        isp = False
        isp_tipo_iva = None

        if prov:
            codimpuesto = prov.get("codimpuesto", "IVA21")
            regimen = prov.get("regimen", "general")
            retencion_pct = prov.get("retencion")
            if retencion_pct:
                retencion_pct = float(retencion_pct)
            recargo_equiv = prov.get("recargo_equiv")
            if recargo_equiv:
                recargo_equiv = float(recargo_equiv)
            log.append(f"Proveedor {cif}: codimpuesto={codimpuesto}, regimen={regimen}")
        elif resultado.codimpuesto:
            codimpuesto = resultado.codimpuesto
            log.append(f"Codimpuesto desde clasificador: {codimpuesto}")
        elif resultado.regimen:
            regimen = resultado.regimen
            log.append(f"Regimen desde clasificador: {regimen}")

        # Resolver tipo IVA numerico desde codimpuesto
        tipo_iva = self._resolver_tipo_iva(codimpuesto, fecha, territorio)
        log.append(f"Tipo IVA resuelto: {tipo_iva}% (codimpuesto={codimpuesto})")

        # Documentos sin IVA (nominas, bancarios, RLC)
        tipo_doc = documento.get("tipo_doc", "FC")
        if tipo_doc in ("NOM", "BAN", "RLC"):
            codimpuesto = "IVA0"
            tipo_iva = 0.0
            log.append(f"Tipo doc {tipo_doc}: sin IVA")

        # ISP para intracomunitario
        if regimen == "intracomunitario":
            isp = True
            isp_tipo_iva = self._resolver_tipo_iva("IVA21", fecha, territorio)
            codimpuesto = "IVA0"
            tipo_iva = 0.0
            log.append(f"ISP intracomunitario: autorepercusion {isp_tipo_iva}%")

        # Recargo equivalencia desde perfil fiscal
        if perfil and perfil.regimen_iva == "recargo_equivalencia" and not recargo_equiv:
            # Si el perfil tiene RE pero el proveedor no especifica, no forzar
            pass

        # Contrapartida
        subcuenta_contra = self._resolver_contrapartida(documento, prov)
        log.append(f"Contrapartida: {subcuenta_contra}")

        # Construir DecisionContable
        decision = DecisionContable(
            subcuenta_gasto=subcuenta_gasto,
            subcuenta_contrapartida=subcuenta_contra,
            codimpuesto=codimpuesto,
            tipo_iva=tipo_iva,
            confianza=confianza,
            origen_decision=origen,
            retencion_pct=retencion_pct,
            recargo_equiv=recargo_equiv,
            isp=isp,
            isp_tipo_iva=isp_tipo_iva,
            regimen=regimen,
            cuarentena=resultado.cuarentena,
            motivo_cuarentena=resultado.motivo_cuarentena,
            log_razonamiento=log,
        )

        return decision

    def validar_asiento(self, decision: DecisionContable) -> list[str]:
        """Valida un asiento generado. Devuelve lista de errores (vacia = OK).

        Checks:
        1. Cuadre debe = haber
        2. Subcuentas validas (10 digitos)
        3. Importes positivos
        """
        errores = []

        if not decision.partidas:
            errores.append("Sin partidas generadas")
            return errores

        total_debe = sum(p.debe for p in decision.partidas)
        total_haber = sum(p.haber for p in decision.partidas)
        if abs(total_debe - total_haber) > 0.01:
            errores.append(
                f"Descuadre: debe={total_debe:.2f} != haber={total_haber:.2f}")

        for p in decision.partidas:
            if len(p.subcuenta) != 10:
                errores.append(f"Subcuenta invalida: {p.subcuenta} ({len(p.subcuenta)} digitos)")
            if p.debe < 0 or p.haber < 0:
                errores.append(f"Importe negativo en {p.subcuenta}")

        return errores

    def aprender(self, documento: dict, subcuenta: str,
                 codimpuesto: str = "IVA21") -> None:
        """Registra una decision humana para uso futuro.

        Args:
            documento: dict con emisor_cif.
            subcuenta: subcuenta correcta segun el humano.
            codimpuesto: codimpuesto correcto.
        """
        cif = documento.get("emisor_cif", "")
        if not cif:
            return
        self._aprendizaje[cif] = {
            "subcuenta": subcuenta,
            "codimpuesto": codimpuesto,
            "veces_aplicado": self._aprendizaje.get(cif, {}).get("veces_aplicado", 0) + 1,
        }
        # Actualizar clasificador con el nuevo aprendizaje
        self.clasificador.aprendizaje = self._aprendizaje

    def _resolver_tipo_iva(self, codimpuesto: str, fecha: date,
                           territorio: str) -> float:
        """Resuelve tipo IVA numerico desde codimpuesto."""
        # Mapeo directo para casos conocidos
        mapeo = {
            "IVA0": 0.0, "IVA4": 4.0, "IVA10": 10.0, "IVA21": 21.0,
            "IGIC0": 0.0, "IGIC3": 3.0, "IGIC7": 7.0, "IGIC9.5": 9.5,
            "IGIC15": 15.0, "IGIC20": 20.0,
            "IPSI0": 0.0, "IPSI0.5": 0.5, "IPSI1": 1.0, "IPSI2": 2.0,
            "IPSI4": 4.0, "IPSI8": 8.0, "IPSI10": 10.0,
        }
        if codimpuesto in mapeo:
            return mapeo[codimpuesto]
        # Intentar extraer numero del codimpuesto
        try:
            return float(codimpuesto.replace("IVA", "").replace("IGIC", "").replace("IPSI", ""))
        except (ValueError, AttributeError):
            return 21.0

    def _resolver_contrapartida(self, documento: dict,
                                proveedor: dict | None) -> str:
        """Determina subcuenta contrapartida (proveedor/acreedor)."""
        tipo_doc = documento.get("tipo_doc", "FC")

        # Facturas de venta -> cliente
        if tipo_doc == "FV":
            return "4300000000"

        # Nominas -> remuneraciones pendientes
        if tipo_doc == "NOM":
            return "4650000000"

        # SS a cargo empresa -> organismos SS
        if tipo_doc == "RLC":
            return "4760000000"

        # Impuestos/tasas -> HP acreedora
        if tipo_doc == "IMP":
            return "4751000000"

        # Bancarios -> banco
        if tipo_doc == "BAN":
            return "5720000000"

        # Default: proveedor generico
        if proveedor and proveedor.get("codproveedor"):
            return f"400{proveedor['codproveedor']:0>7}"
        return "4000000000"
