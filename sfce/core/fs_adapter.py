"""Capa defensiva para la API de FacturaScripts.

Único punto de contacto con FS. Encapsula TODAS las peculiaridades:
- form-encoded (nunca JSON)
- json.dumps(lineas) obligatorio
- filtrado de campos _*
- idempresa + codejercicio siempre presentes
- recargo=0 forzado en líneas
- nick truncado a 10 chars
- personafisica como int (0/1)
- post-filtrado en Python (filtros FS no funcionan)
- retry con backoff en timeouts
- rollback automático en creación 2-pasos
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import requests
import requests.exceptions

from .logger import crear_logger

logger = crear_logger("fs_adapter")


# ---------------------------------------------------------------------------
# Tipos de datos
# ---------------------------------------------------------------------------

@dataclass
class FSResult:
    """Respuesta normalizada de cualquier operación FS."""
    ok: bool
    data: dict = field(default_factory=dict)
    id_creado: Any = None       # idfactura, idasiento, codproveedor...
    error: str | None = None
    http_status: int = 0
    raw_response: dict = field(default_factory=dict)

    def raise_if_error(self) -> None:
        """Lanza FSError si la operación falló."""
        if not self.ok:
            raise FSError(self.error or "Error desconocido en FS",
                          self.http_status, self.raw_response)


class FSError(Exception):
    """Error de FacturaScripts con contexto completo para debug."""

    def __init__(self, message: str, http_status: int = 0, raw: dict = None):
        super().__init__(message)
        self.http_status = http_status
        self.raw = raw or {}


# ---------------------------------------------------------------------------
# Adaptador principal
# ---------------------------------------------------------------------------

class FSAdapter:
    """Único punto de contacto con FacturaScripts.

    Constructor obligatorio con los 4 parámetros que siempre se olvidan:
    base_url, token, idempresa, codejercicio.

    No usar instancias globales — crear una por ejecución/empresa.
    """

    def __init__(self, base_url: str, token: str, idempresa: int, codejercicio: str):
        """Los 4 parámetros son OBLIGATORIOS. Sin defaults.

        Args:
            base_url: URL de la instancia FS (ej: 'https://contabilidad.prometh-ai.es/api/3')
            token: Token API de FS
            idempresa: ID de la empresa en FS (ej: 7)
            codejercicio: Código del ejercicio (ej: '0007', 'GG26')
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.idempresa = idempresa
        self.codejercicio = codejercicio

        self._session = requests.Session()
        self._session.headers["Token"] = token

    # -----------------------------------------------------------------------
    # Métodos HTTP internos
    # -----------------------------------------------------------------------

    def _post(self, endpoint: str, form_data: dict) -> FSResult:
        """POST form-encoded con todas las defensas de FS."""

        # 1. Filtrar campos internos _*
        clean = {k: v for k, v in form_data.items() if not k.startswith("_")}

        # 2. Inyectar idempresa + codejercicio SIEMPRE
        clean.setdefault("idempresa", self.idempresa)
        clean.setdefault("codejercicio", self.codejercicio)

        # 3. Convertir personafisica bool/str → int
        if "personafisica" in clean:
            val = clean["personafisica"]
            if isinstance(val, bool):
                clean["personafisica"] = 1 if val else 0
            elif isinstance(val, str):
                clean["personafisica"] = 1 if val.lower() in ("true", "1", "si") else 0

        # 4. Serializar lineas si son lista + forzar recargo=0 en cada una
        if "lineas" in clean and isinstance(clean["lineas"], list):
            for linea in clean["lineas"]:
                if isinstance(linea, dict):
                    linea.setdefault("recargo", 0)
            clean["lineas"] = json.dumps(clean["lineas"])

        # 5. Truncar nicks a 10 chars (límite FS)
        for campo in ("codproveedor", "codcliente"):
            if campo in clean and clean[campo]:
                clean[campo] = str(clean[campo])[:10]

        # 6. POST con retry (3 intentos, backoff exponencial)
        url = f"{self.base_url}/{endpoint}"
        last_error: str = "Sin intentos"

        for intento in range(3):
            try:
                resp = self._session.post(url, data=clean, timeout=30)
                return self._normalizar_response(resp)
            except requests.exceptions.Timeout:
                last_error = f"Timeout intento {intento + 1}/3"
                logger.warning("FS timeout POST %s — intento %d/3", endpoint, intento + 1)
                if intento < 2:
                    time.sleep(2 ** intento)
            except requests.exceptions.RequestException as exc:
                return FSResult(ok=False, error=str(exc), http_status=0)

        return FSResult(ok=False, error=last_error, http_status=0)

    def _get(self, endpoint: str, params: dict = None) -> list | dict | None:
        """GET con paginación automática.

        IMPORTANTE: los filtros de FS no funcionan — post-filtrar siempre en Python.
        """
        url = f"{self.base_url}/{endpoint}"
        todos = []
        p = dict(params or {})
        p.setdefault("limit", 200)
        p["offset"] = 0

        while True:
            try:
                resp = self._session.get(url, params=p, timeout=30)
            except requests.exceptions.RequestException as exc:
                logger.error("FS GET %s falló: %s", endpoint, exc)
                return []

            if resp.status_code == 404:
                return None
            resp.raise_for_status()

            lote = resp.json()
            if not lote:
                break

            if isinstance(lote, list):
                todos.extend(lote)
                if len(lote) < p["limit"]:
                    break
                p["offset"] += p["limit"]
            else:
                # Respuesta singular (no lista)
                return lote

        return todos

    def _get_one(self, endpoint: str) -> dict | None:
        """GET recurso individual por ruta completa (ej: 'asientos/123')."""
        url = f"{self.base_url}/{endpoint}"
        try:
            resp = self._session.get(url, timeout=30)
        except requests.exceptions.RequestException as exc:
            logger.error("FS GET_ONE %s falló: %s", endpoint, exc)
            return None

        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data[0] if data else None
        return data

    def _put(self, endpoint: str, data: dict) -> FSResult:
        """PUT form-encoded."""
        url = f"{self.base_url}/{endpoint}"
        try:
            resp = self._session.put(url, data=data, timeout=30)
        except requests.exceptions.RequestException as exc:
            return FSResult(ok=False, error=str(exc))

        try:
            body = resp.json()
        except Exception:
            body = {}

        return FSResult(
            ok=resp.status_code < 400,
            data=body,
            http_status=resp.status_code,
            raw_response=body,
        )

    def _delete(self, endpoint: str) -> bool:
        """DELETE recurso."""
        url = f"{self.base_url}/{endpoint}"
        try:
            resp = self._session.delete(url, timeout=30)
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def _normalizar_response(self, resp: requests.Response) -> FSResult:
        """Normaliza la respuesta de FS a FSResult.

        FS devuelve respuestas en formatos inconsistentes:
        - {"ok": "...", "data": {"idfactura": "X"}}
        - {"idfactura": "X"}
        - [{"idfactura": "X"}]
        """
        try:
            body = resp.json()
        except Exception:
            body = {"raw_text": resp.text[:500]}

        if resp.status_code >= 400:
            if isinstance(body, dict):
                error_msg = body.get("error", body.get("message", f"HTTP {resp.status_code}"))
            else:
                error_msg = f"HTTP {resp.status_code}"
            return FSResult(
                ok=False,
                error=error_msg,
                http_status=resp.status_code,
                raw_response=body if isinstance(body, dict) else {"raw": body},
            )

        # Normalizar estructura
        data = body
        if isinstance(body, list):
            data = body[0] if body else {}

        inner_data = data.get("data", data) if isinstance(data, dict) else {}

        # Extraer ID creado (puede ser idfactura, idasiento, idpartida, etc.)
        id_creado = None
        for campo_id in ("idfactura", "idasiento", "idpartida", "idlinea",
                         "codproveedor", "codcliente"):
            val = inner_data.get(campo_id) if isinstance(inner_data, dict) else None
            if val is not None:
                try:
                    id_creado = int(val)
                except (ValueError, TypeError):
                    id_creado = val  # codproveedor/codcliente son strings
                break

        return FSResult(
            ok=True,
            data=inner_data if isinstance(inner_data, dict) else {},
            id_creado=id_creado,
            http_status=resp.status_code,
            raw_response=body if isinstance(body, dict) else {"raw": body},
        )

    # -----------------------------------------------------------------------
    # API pública — Proveedores / Clientes
    # -----------------------------------------------------------------------

    def crear_proveedor(self, cifnif: str, nombre: str, **kwargs) -> FSResult:
        """Crea proveedor. NO pasa codsubcuenta (FS auto-asigna 400x)."""
        data = {"cifnif": cifnif, "nombre": nombre, **kwargs}
        data.pop("codsubcuenta", None)  # NUNCA pasar codsubcuenta
        return self._post("proveedores", data)

    def crear_cliente(self, cifnif: str, nombre: str, **kwargs) -> FSResult:
        """Crea cliente."""
        data = {"cifnif": cifnif, "nombre": nombre, **kwargs}
        return self._post("clientes", data)

    def buscar_proveedor(self, cifnif: str) -> dict | None:
        """Busca proveedor por CIF. Post-filtra (filtros FS no funcionan).

        Maneja prefijos intracomunitarios: "ES76638663H".endswith("76638663H") → True.
        """
        todos = self._get("proveedores") or []
        cifnif_norm = _normalizar_cif(cifnif)
        for p in todos:
            cif_fs = _normalizar_cif(p.get("cifnif") or "")
            if cif_fs == cifnif_norm or cif_fs.endswith(cifnif_norm) or cifnif_norm.endswith(cif_fs):
                return p
        return None

    def buscar_cliente(self, cifnif: str) -> dict | None:
        """Busca cliente por CIF. Post-filtra."""
        todos = self._get("clientes") or []
        cifnif_norm = _normalizar_cif(cifnif)
        for c in todos:
            cif_fs = _normalizar_cif(c.get("cifnif") or "")
            if cif_fs == cifnif_norm or cif_fs.endswith(cifnif_norm) or cifnif_norm.endswith(cif_fs):
                return c
        return None

    # -----------------------------------------------------------------------
    # API pública — Facturas (2 pasos)
    # -----------------------------------------------------------------------

    def crear_factura_proveedor(self, cabecera: dict, lineas: list[dict]) -> FSResult:
        """Crea factura proveedor en 2 pasos (cabecera + líneas).

        Maneja internamente:
        - Enriquecimiento cifnif/nombre desde codproveedor si faltan
        - pvpsindto = pvpunitario * cantidad en cada línea
        - recargo=0 forzado en cada línea
        - PUT totales cabecera tras insertar líneas
        - Rollback (eliminar cabecera) si falla alguna línea
        """
        return self._crear_factura_2pasos(es_proveedor=True, cabecera=cabecera, lineas=lineas)

    def crear_factura_cliente(self, cabecera: dict, lineas: list[dict]) -> FSResult:
        """Crea factura cliente en 2 pasos.

        FS genera el asiento automáticamente (no necesita POST manual).
        """
        return self._crear_factura_2pasos(es_proveedor=False, cabecera=cabecera, lineas=lineas)

    def crear_lote_facturas_cliente(self, facturas: list[dict]) -> list[FSResult]:
        """Crea lote de facturas cliente PRE-ORDENADAS por fecha ASC.

        FS valida orden cronológico estricto. Este método ordena internamente.
        Cada dict debe tener 'cabecera' y 'lineas'.
        """
        ordenadas = sorted(facturas, key=lambda f: f["cabecera"].get("fecha", ""))
        resultados = []
        for f in ordenadas:
            r = self.crear_factura_cliente(f["cabecera"], f["lineas"])
            resultados.append(r)
        return resultados

    def _crear_factura_2pasos(
        self, es_proveedor: bool, cabecera: dict, lineas: list[dict]
    ) -> FSResult:
        """Implementación interna del flujo 2-pasos."""
        endpoint_cab = "facturaproveedores" if es_proveedor else "facturaclientes"
        endpoint_lin = "lineasfacturaproveedores" if es_proveedor else "lineasfacturaclientes"

        # Enriquecer cabecera con cifnif/nombre si falta
        form_cab = self._enriquecer_cabecera(cabecera, es_proveedor)

        # Paso 1: POST cabecera
        result_cab = self._post(endpoint_cab, form_cab)
        if not result_cab.ok:
            return result_cab

        idfactura = result_cab.id_creado
        if not idfactura:
            return FSResult(
                ok=False, error="Respuesta sin idfactura",
                raw_response=result_cab.raw_response
            )

        # Paso 2: POST cada línea
        neto_acum = 0.0

        for linea in lineas:
            pvpunitario = float(linea.get("pvpunitario", 0))
            cantidad = float(linea.get("cantidad", 1))
            pvpsindto = round(pvpunitario * cantidad, 2)

            datos_linea = {
                **linea,
                "idfactura": idfactura,
                "pvpsindto": pvpsindto,
                "pvptotal": pvpsindto,
                "recargo": 0,
            }

            result_lin = self._post(endpoint_lin, datos_linea)
            if not result_lin.ok:
                # Rollback: eliminar factura parcial
                self._delete(f"{endpoint_cab}/{idfactura}")
                logger.warning(
                    "Error en línea de factura %s — rollback idfactura=%s: %s",
                    endpoint_lin, idfactura, result_lin.error
                )
                return FSResult(
                    ok=False,
                    error=f"Error en línea: {result_lin.error}",
                    raw_response=result_lin.raw_response,
                )

            neto_acum += pvpsindto

        # Paso 3: PUT totales en cabecera
        self._put(f"{endpoint_cab}/{idfactura}", {
            "neto": round(neto_acum, 2),
            "total": round(neto_acum, 2),
        })

        return FSResult(
            ok=True,
            id_creado=idfactura,
            data={"idfactura": idfactura},
        )

    def _enriquecer_cabecera(self, cabecera: dict, es_proveedor: bool) -> dict:
        """Añade cifnif y nombre desde FS si faltan en la cabecera."""
        result = {**cabecera}

        if es_proveedor and "cifnif" not in result:
            cod = result.get("codproveedor")
            if cod:
                prov = self._get_one(f"proveedores/{cod}")
                if prov:
                    result.setdefault("cifnif", prov.get("cifnif", ""))
                    result.setdefault("nombre", prov.get("nombre", ""))
        elif not es_proveedor and "cifnif" not in result:
            cod = result.get("codcliente")
            if cod:
                cli = self._get_one(f"clientes/{cod}")
                if cli:
                    result.setdefault("cifnif", cli.get("cifnif", ""))
                    result.setdefault("nombre", cli.get("nombre", ""))

        return result

    # -----------------------------------------------------------------------
    # API pública — Asientos
    # -----------------------------------------------------------------------

    def crear_asiento(self, concepto: str, fecha: str, lineas: list[dict]) -> FSResult:
        """Crea asiento con partidas inline.

        idempresa y codejercicio se inyectan automáticamente.
        lineas se serializa con json.dumps y se fuerza recargo=0.
        """
        return self._post("asientos", {
            "concepto": concepto,
            "fecha": fecha,
            "lineas": lineas,
        })

    def crear_asiento_con_partidas(
        self, concepto: str, fecha: str, partidas: list[dict]
    ) -> FSResult:
        """Crea asiento cabecera + partidas individuales (sin lineas en cabecera).

        Necesario cuando FS no acepta lineas en el POST de asientos.
        """
        result = self._post("asientos", {"concepto": concepto, "fecha": fecha})
        if not result.ok:
            return result

        idasiento = result.id_creado
        if not idasiento:
            return FSResult(ok=False, error="Sin idasiento en respuesta")

        for partida in partidas:
            datos_partida = {
                "idasiento": idasiento,
                "idempresa": self.idempresa,
                "codsubcuenta": partida["codsubcuenta"],
                "debe": partida.get("debe", 0),
                "haber": partida.get("haber", 0),
                "concepto": partida.get("concepto", concepto),
            }
            r = self._post("partidas", datos_partida)
            if not r.ok:
                logger.error(
                    "Error creando partida %s en asiento %s: %s",
                    partida.get("codsubcuenta"), idasiento, r.error
                )
                return FSResult(
                    ok=False,
                    error=f"Error en partida {partida.get('codsubcuenta')}: {r.error}",
                    data={"idasiento": idasiento},
                )

        return FSResult(
            ok=True,
            id_creado=idasiento,
            data={"idasiento": idasiento, "num_partidas": len(partidas)},
        )

    def obtener_asiento(self, idasiento: int) -> dict | None:
        """Obtiene asiento por ID."""
        return self._get_one(f"asientos/{idasiento}")

    def obtener_partidas(self, idasiento: int) -> list[dict]:
        """Obtiene partidas de un asiento. POST-FILTRA (filtros FS no funcionan)."""
        todas = self._get("partidas", params={"idasiento": idasiento}) or []
        return [p for p in todas if int(p.get("idasiento", 0)) == idasiento]

    def crear_partida(self, datos: dict) -> FSResult:
        """Crea una partida individual en un asiento existente.

        Args:
            datos: debe incluir 'idasiento', 'codsubcuenta', 'debe', 'haber'.
                   'concepto' es opcional.
                   idempresa se inyecta automáticamente por _post().
        """
        return self._post("partidas", datos)

    # -----------------------------------------------------------------------
    # API pública — Facturas consulta/eliminación
    # -----------------------------------------------------------------------

    def verificar_factura(self, idfactura: int, tipo: str = "proveedor") -> dict | None:
        """Obtiene datos de una factura existente."""
        endpoint = "facturaproveedores" if tipo == "proveedor" else "facturaclientes"
        return self._get_one(f"{endpoint}/{idfactura}")

    def eliminar_factura(self, idfactura: int, tipo: str = "proveedor") -> bool:
        """Elimina una factura. Devuelve True si tuvo éxito."""
        endpoint = "facturaproveedores" if tipo == "proveedor" else "facturaclientes"
        return self._delete(f"{endpoint}/{idfactura}")

    # -----------------------------------------------------------------------
    # API pública — Correcciones
    # -----------------------------------------------------------------------

    def corregir_partida(self, idpartida: int, cambios: dict) -> FSResult:
        """PUT partida. ADVERTENCIA: si es línea de factura, FS regenera asiento."""
        return self._put(f"partidas/{idpartida}", cambios)

    def corregir_linea_factura(
        self, idlinea: int, cambios: dict, es_proveedor: bool = True
    ) -> FSResult:
        """PUT línea de factura. FS REGENERA el asiento al hacer esto."""
        endpoint = "lineasfacturaproveedores" if es_proveedor else "lineasfacturaclientes"
        return self._put(f"{endpoint}/{idlinea}", cambios)

    # -----------------------------------------------------------------------
    # Factories
    # -----------------------------------------------------------------------

    @classmethod
    def desde_config(cls, config) -> "FSAdapter":
        """Crea FSAdapter desde un ConfigCliente.

        Usa el token global y la URL global de fs_api.py.
        Apropiado para el pipeline (un cliente a la vez).
        """
        from .fs_api import obtener_token, API_BASE
        return cls(
            base_url=API_BASE,
            token=obtener_token(),
            idempresa=config.idempresa,
            codejercicio=config.codejercicio,
        )

    @classmethod
    def desde_empresa_bd(cls, empresa, gestoria) -> "FSAdapter":
        """Crea FSAdapter desde objetos Empresa + Gestoria de BD.

        Usa credenciales específicas de la gestoría (cifradas en BD).
        Apropiado para la API web (múltiples gestorías).
        """
        from .fs_api import obtener_credenciales_gestoria
        fs_url, token = obtener_credenciales_gestoria(gestoria)
        return cls(
            base_url=fs_url,
            token=token,
            idempresa=empresa.idempresa_fs,
            codejercicio=empresa.codejercicio_fs,
        )


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _normalizar_cif(cif: str) -> str:
    """Normaliza CIF: mayúsculas, sin espacios/guiones."""
    return (cif or "").upper().replace(" ", "").replace("-", "")
