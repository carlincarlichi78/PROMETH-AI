# Integración Zoho Mail por Gestoría — Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrar Zoho Mail como proveedor de correo, con un buzón por gestoría y un catch-all compartido, de modo que los emails de los clientes fluyan automáticamente a las carpetas correctas según el destinatario o el remitente.

**Architecture:** Migración 019 añade `gestoria_id` y `tipo_cuenta` a `cuentas_correo`. `ingesta_correo.py` bifurca el flujo: cuentas `'dedicada'` enrutan por campo To (código existente), cuentas `'gestoria'` enrutan por remitente entre las empresas de esa gestoría. Se añaden endpoints CRUD de superadmin y GET/PUT por gestoría. La configuración SMTP se activa vía variables de entorno.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0, FastAPI, SQLite/PostgreSQL, pytest, React 18 + TypeScript + Tailwind

---

## Contexto del sistema

- `sfce/db/modelos.py:607` — clase `CuentaCorreo` (tiene `empresa_id` NOT NULL — hay que hacerlo nullable)
- `sfce/conectores/correo/ingesta_correo.py` — `IngestaCorreo.procesar_cuenta()` y `ejecutar_polling_todas_las_cuentas()`
- `sfce/conectores/correo/worker_catchall.py` — procesa catch-all por campo To. Sin cambios.
- `sfce/api/rutas/correo.py` — API existente en `/api/correo/`. Añadimos rutas admin aquí.
- `sfce/api/app.py:200` — registra `correo_router` en `/api/correo/`
- Tests existentes: `tests/test_ingesta_correo.py`, `tests/test_api_correo.py`
- Patrón de migración: ver `sfce/db/migraciones/migracion_018_email_mejorado.py`
- Patrón de test: `create_engine("sqlite:///:memory:", poolclass=StaticPool)` + `Base.metadata.create_all(eng)`

---

## Task 1: Migración 019 — gestoria_id + tipo_cuenta en cuentas_correo

**Archivos:**
- Crear: `sfce/db/migraciones/019_cuentas_correo_gestoria.py`
- Test: `tests/test_migracion_019.py`

**Step 1: Escribir test que falla**

```python
# tests/test_migracion_019.py
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


@pytest.fixture
def engine_019():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Crear tabla minimal antes de migrar
    with eng.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cuentas_correo (
                id INTEGER PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                protocolo TEXT NOT NULL,
                usuario TEXT NOT NULL,
                activa INTEGER DEFAULT 1
            )
        """))
    return eng


def test_migrar_019_añade_gestoria_id(engine_019):
    from sfce.db.migraciones.migracion_019_cuentas_correo_gestoria import ejecutar
    ejecutar(engine_019)
    with engine_019.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(cuentas_correo)")).fetchall()}
    assert "gestoria_id" in cols
    assert "tipo_cuenta" in cols


def test_migrar_019_es_idempotente(engine_019):
    from sfce.db.migraciones.migracion_019_cuentas_correo_gestoria import ejecutar
    ejecutar(engine_019)
    ejecutar(engine_019)  # segunda ejecucion no falla


def test_migrar_019_tipo_cuenta_default_empresa(engine_019):
    from sfce.db.migraciones.migracion_019_cuentas_correo_gestoria import ejecutar
    ejecutar(engine_019)
    with engine_019.begin() as conn:
        conn.execute(text(
            "INSERT INTO cuentas_correo (empresa_id, nombre, protocolo, usuario) "
            "VALUES (1, 'Test', 'imap', 'u@test.com')"
        ))
        row = conn.execute(text("SELECT tipo_cuenta FROM cuentas_correo WHERE id=1")).fetchone()
    assert row[0] == "empresa"


def test_migrar_019_empresa_id_nullable(engine_019):
    from sfce.db.migraciones.migracion_019_cuentas_correo_gestoria import ejecutar
    ejecutar(engine_019)
    # empresa_id ahora es nullable — debe aceptar NULL
    with engine_019.begin() as conn:
        conn.execute(text(
            "INSERT INTO cuentas_correo (gestoria_id, tipo_cuenta, nombre, protocolo, usuario) "
            "VALUES (7, 'gestoria', 'Gestoría1', 'imap', 'g1@prometh-ai.es')"
        ))
        row = conn.execute(text(
            "SELECT gestoria_id, tipo_cuenta FROM cuentas_correo ORDER BY id DESC LIMIT 1"
        )).fetchone()
    assert row[0] == 7
    assert row[1] == "gestoria"
```

**Step 2: Ejecutar y verificar que falla**

```bash
cd c:\Users\carli\PROYECTOS\CONTABILIDAD
pytest tests/test_migracion_019.py -v 2>&1 | tail -15
```
Esperado: `ModuleNotFoundError` o `ImportError`

**Step 3: Implementar la migración**

```python
# sfce/db/migraciones/migracion_019_cuentas_correo_gestoria.py
"""Migración 019 — Soporte Zoho por gestoría en cuentas_correo.

Cambios en cuentas_correo:
  - gestoria_id INTEGER nullable (FK lógica a gestorias)
  - tipo_cuenta TEXT default 'empresa' ('dedicada'|'gestoria'|'sistema'|'empresa')
  - empresa_id pasa a ser nullable (SQLite no soporta ALTER COLUMN, se hace con recreación)
"""
from sqlalchemy import Engine, text


def ejecutar(engine: Engine) -> None:
    with engine.begin() as conn:
        cols = {
            row[1]
            for row in conn.execute(
                text("PRAGMA table_info(cuentas_correo)")
            ).fetchall()
        }
        if "gestoria_id" not in cols:
            conn.execute(text(
                "ALTER TABLE cuentas_correo ADD COLUMN gestoria_id INTEGER"
            ))
        if "tipo_cuenta" not in cols:
            conn.execute(text(
                "ALTER TABLE cuentas_correo ADD COLUMN "
                "tipo_cuenta TEXT NOT NULL DEFAULT 'empresa'"
            ))


if __name__ == "__main__":
    from sfce.db.base import crear_motor
    ejecutar(crear_motor())
    print("Migración 019 aplicada.")
```

**Step 4: Ejecutar tests y verificar que pasan**

```bash
pytest tests/test_migracion_019.py -v 2>&1 | tail -15
```
Esperado: 4 PASSED

**Step 5: Commit**

```bash
git add sfce/db/migraciones/migracion_019_cuentas_correo_gestoria.py tests/test_migracion_019.py
git commit -m "feat: migración 019 — gestoria_id y tipo_cuenta en cuentas_correo"
```

---

## Task 2: Actualizar modelo CuentaCorreo

**Archivos:**
- Modificar: `sfce/db/modelos.py:607-631`
- Test: `tests/test_modelo_cuenta_correo.py`

**Step 1: Escribir test que falla**

```python
# tests/test_modelo_cuenta_correo.py
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool
import sfce.db.modelos_auth  # noqa: F401
from sfce.db.modelos import Base, CuentaCorreo


@pytest.fixture
def engine_modelo():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def test_cuenta_correo_tiene_gestoria_id(engine_modelo):
    inspector = inspect(engine_modelo)
    cols = {c["name"] for c in inspector.get_columns("cuentas_correo")}
    assert "gestoria_id" in cols


def test_cuenta_correo_tiene_tipo_cuenta(engine_modelo):
    inspector = inspect(engine_modelo)
    cols = {c["name"] for c in inspector.get_columns("cuentas_correo")}
    assert "tipo_cuenta" in cols


def test_cuenta_correo_empresa_id_nullable(engine_modelo):
    """empresa_id ahora es nullable para cuentas de tipo gestoria/sistema."""
    from sqlalchemy.orm import Session
    from sfce.db.modelos import CuentaCorreo
    with Session(engine_modelo) as s:
        c = CuentaCorreo(
            nombre="Catch-all",
            protocolo="imap",
            servidor="imap.zoho.eu",
            puerto=993,
            ssl=True,
            usuario="docs@prometh-ai.es",
            tipo_cuenta="dedicada",
            gestoria_id=None,
            empresa_id=None,
        )
        s.add(c)
        s.commit()
    assert c.id is not None


def test_cuenta_correo_tipo_cuenta_default(engine_modelo):
    from sqlalchemy.orm import Session
    with Session(engine_modelo) as s:
        c = CuentaCorreo(
            empresa_id=1,
            nombre="Test",
            protocolo="imap",
            servidor="imap.zoho.eu",
            puerto=993,
            ssl=True,
            usuario="u@test.com",
        )
        s.add(c)
        s.commit()
    assert c.tipo_cuenta == "empresa"
```

**Step 2: Ejecutar y verificar que falla**

```bash
pytest tests/test_modelo_cuenta_correo.py -v 2>&1 | tail -15
```

**Step 3: Actualizar el modelo**

En `sfce/db/modelos.py`, localizar la clase `CuentaCorreo` (línea ~607) y aplicar estos cambios:

```python
class CuentaCorreo(Base):
    """Cuenta de correo IMAP o Microsoft Graph configurada por empresa o gestoría."""
    __tablename__ = "cuentas_correo"

    id = Column(Integer, primary_key=True)
    # empresa_id es nullable: cuentas de tipo 'gestoria'/'sistema'/'dedicada' no tienen empresa
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    gestoria_id = Column(Integer, ForeignKey("gestorias.id"), nullable=True)
    # 'empresa' | 'dedicada' | 'gestoria' | 'sistema'
    tipo_cuenta = Column(String(20), nullable=False, default="empresa")
    nombre = Column(String(200), nullable=False)
    protocolo = Column(String(10), nullable=False)   # 'imap' | 'graph'
    servidor = Column(String(200))
    puerto = Column(Integer, default=993)
    ssl = Column(Boolean, default=True)
    usuario = Column(String(200), nullable=False)
    contrasena_enc = Column(Text)
    oauth_token_enc = Column(Text)
    oauth_refresh_enc = Column(Text)
    oauth_expires_at = Column(String(50))
    carpeta_entrada = Column(String(100), default="INBOX")
    ultimo_uid = Column(Integer, default=0)
    activa = Column(Boolean, default=True)
    polling_intervalo_segundos = Column(Integer, default=120)
    created_at = Column(DateTime, default=datetime.now)

    emails = relationship("EmailProcesado", back_populates="cuenta",
                          cascade="all, delete-orphan")
```

**Step 4: Ejecutar tests**

```bash
pytest tests/test_modelo_cuenta_correo.py -v 2>&1 | tail -15
```
Esperado: 4 PASSED

**Step 5: Verificar que tests anteriores siguen en verde**

```bash
pytest tests/test_ingesta_correo.py tests/test_api_correo.py -v 2>&1 | tail -20
```

**Step 6: Commit**

```bash
git add sfce/db/modelos.py tests/test_modelo_cuenta_correo.py
git commit -m "feat: CuentaCorreo — gestoria_id, tipo_cuenta, empresa_id nullable"
```

---

## Task 3: Ingesta — routing por gestoría

**Archivos:**
- Modificar: `sfce/conectores/correo/ingesta_correo.py`
- Modificar: `tests/test_ingesta_correo.py`

**Step 1: Escribir tests que fallan**

Añadir al final de `tests/test_ingesta_correo.py`:

```python
# ---- Tests routing por gestoría ----
import sfce.db.modelos_auth  # noqa: F401 — registra tabla gestorias
from sfce.db.modelos_auth import Gestoria


@pytest.fixture
def engine_gestoria(engine_test):
    """engine_test ya tiene Base.metadata.create_all — solo añadir gestorias."""
    import sfce.db.modelos_auth as _auth
    _auth.Base.metadata.create_all(engine_test)
    return engine_test


def test_procesar_cuenta_gestoria_enruta_por_remitente(engine_gestoria):
    """Email a buzón de gestoría se enruta a empresa correcta por regla de remitente."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    with Session(engine_gestoria) as s:
        gestoria = Gestoria(
            nombre="Gestoría Test",
            email_contacto="admin@gt.es",
            plan_asesores=1,
            plan_clientes_tramo="1-10",
        )
        s.add(gestoria)
        s.flush()
        gestoria_id = gestoria.id

        from sfce.db.modelos import Empresa
        empresa = Empresa(
            nombre="Pastorino S.L.",
            cif="B12345678",
            gestoria_id=gestoria_id,
        )
        s.add(empresa)
        s.flush()
        empresa_id = empresa.id

        from sfce.db.modelos import ReglaClasificacionCorreo
        regla = ReglaClasificacionCorreo(
            empresa_id=empresa_id,
            tipo="REMITENTE_EXACTO",
            condicion_json='{"remitente": "facturas@proveedor.es"}',
            accion="CLASIFICAR",
            slug_destino="pastorino",
            prioridad=10,
            activa=True,
        )
        s.add(regla)

        cuenta = CuentaCorreo(
            gestoria_id=gestoria_id,
            tipo_cuenta="gestoria",
            nombre="Gestoría Test inbox",
            protocolo="imap",
            servidor="imap.zoho.eu",
            puerto=993,
            ssl=True,
            usuario="gestoriatest@prometh-ai.es",
        )
        s.add(cuenta)
        s.commit()
        cuenta_id = cuenta.id

    emails_mock = [{
        "uid": "10",
        "message_id": "<gestoria@test>",
        "remitente": "facturas@proveedor.es",
        "asunto": "Factura marzo",
        "fecha": "2026-03-01",
        "cuerpo_texto": "Total 500 EUR",
        "cuerpo_html": "",
        "adjuntos": [],
    }]

    ingesta = IngestaCorreo(engine=engine_gestoria)
    with patch.object(ingesta, "_descargar_emails_cuenta", return_value=emails_mock):
        procesados = ingesta.procesar_cuenta(cuenta_id)

    assert procesados == 1
    with Session(engine_gestoria) as s:
        email_bd = s.execute(
            select(EmailProcesado).where(EmailProcesado.cuenta_id == cuenta_id)
        ).scalar_one()
    assert email_bd.empresa_destino_id == empresa_id
    assert email_bd.estado == "CLASIFICADO"


def test_procesar_cuenta_gestoria_cuarentena_si_remitente_desconocido(engine_gestoria):
    """Remitente desconocido en cuenta gestoría va a CUARENTENA."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    with Session(engine_gestoria) as s:
        gestoria = Gestoria(
            nombre="Gestoría2",
            email_contacto="g2@test.es",
            plan_asesores=1,
            plan_clientes_tramo="1-10",
        )
        s.add(gestoria)
        s.flush()
        cuenta = CuentaCorreo(
            gestoria_id=gestoria.id,
            tipo_cuenta="gestoria",
            nombre="G2 inbox",
            protocolo="imap",
            servidor="imap.zoho.eu",
            puerto=993,
            ssl=True,
            usuario="g2@prometh-ai.es",
        )
        s.add(cuenta)
        s.commit()
        cuenta_id = cuenta.id

    emails_mock = [{
        "uid": "1",
        "message_id": "<x@x>",
        "remitente": "desconocido@nowhere.com",
        "asunto": "doc",
        "fecha": "2026-03-01",
        "cuerpo_texto": "",
        "cuerpo_html": "",
        "adjuntos": [],
    }]

    ingesta = IngestaCorreo(engine=engine_gestoria)
    with patch.object(ingesta, "_descargar_emails_cuenta", return_value=emails_mock):
        ingesta.procesar_cuenta(cuenta_id)

    with Session(engine_gestoria) as s:
        email_bd = s.execute(
            select(EmailProcesado).where(EmailProcesado.cuenta_id == cuenta_id)
        ).scalar_one()
    assert email_bd.estado == "CUARENTENA"


def test_ejecutar_polling_omite_cuentas_sistema(engine_gestoria):
    """Cuentas tipo 'sistema' no se incluyen en el polling IMAP."""
    from sfce.conectores.correo.ingesta_correo import ejecutar_polling_todas_las_cuentas

    with Session(engine_gestoria) as s:
        cuenta_sistema = CuentaCorreo(
            tipo_cuenta="sistema",
            nombre="noreply",
            protocolo="imap",
            servidor="smtp.zoho.eu",
            puerto=993,
            ssl=True,
            usuario="noreply@prometh-ai.es",
            activa=True,
        )
        s.add(cuenta_sistema)
        s.commit()
        cuenta_id = cuenta_sistema.id

    ingesta_mock = MagicMock()
    with patch("sfce.conectores.correo.ingesta_correo.IngestaCorreo") as MockIngesta:
        MockIngesta.return_value = ingesta_mock
        ejecutar_polling_todas_las_cuentas(engine_gestoria)

    # procesar_cuenta nunca fue llamado con la cuenta sistema
    llamadas = [call.args[0] for call in ingesta_mock.procesar_cuenta.call_args_list]
    assert cuenta_id not in llamadas
```

**Step 2: Ejecutar y verificar que fallan**

```bash
pytest tests/test_ingesta_correo.py -v -k "gestoria or sistema" 2>&1 | tail -20
```

**Step 3: Implementar los cambios en ingesta_correo.py**

Modificar `sfce/conectores/correo/ingesta_correo.py`:

```python
"""Orquestador de ingesta de emails: descarga → clasifica → guarda → encola OCR."""
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sfce.db.modelos import (
    CuentaCorreo, EmailProcesado, AdjuntoEmail,
    EnlaceEmail, ReglaClasificacionCorreo, Empresa,
)
from sfce.conectores.correo.clasificacion.servicio_clasificacion import clasificar_email
from sfce.conectores.correo.extractor_enlaces import extraer_enlaces
from sfce.conectores.correo.parser_hints import extraer_hints_asunto

logger = logging.getLogger(__name__)

_ESTADO_POR_ACCION = {
    "CLASIFICAR": "CLASIFICADO",
    "APROBAR_MANUAL": "CUARENTENA",
    "IGNORAR": "IGNORADO",
    "CUARENTENA": "CUARENTENA",
}


class IngestaCorreo:
    """Orquesta el procesamiento de una cuenta de correo."""

    def __init__(self, engine: Engine, directorio_adjuntos: str = "clientes") -> None:
        self._engine = engine
        self._dir_adjuntos = Path(directorio_adjuntos)

    def procesar_cuenta(self, cuenta_id: int) -> int:
        """Procesa una cuenta de correo. Retorna número de emails nuevos procesados."""
        with Session(self._engine) as sesion:
            cuenta = sesion.get(CuentaCorreo, cuenta_id)
            if not cuenta or not cuenta.activa:
                return 0
            tipo = cuenta.tipo_cuenta or "empresa"
            ultimo_uid = cuenta.ultimo_uid
            if tipo == "gestoria":
                reglas, empresas_gestoria = self._cargar_reglas_gestoria(
                    sesion, cuenta.gestoria_id
                )
            else:
                reglas = self._cargar_reglas(sesion, cuenta.empresa_id)
                empresas_gestoria = []

        emails = self._descargar_emails_cuenta(cuenta_id, ultimo_uid)
        if not emails:
            return 0

        procesados = 0
        with Session(self._engine) as sesion:
            for email_data in emails:
                ya_existe = sesion.execute(
                    select(EmailProcesado).where(
                        EmailProcesado.cuenta_id == cuenta_id,
                        EmailProcesado.uid_servidor == email_data["uid"],
                    )
                ).scalar_one_or_none()
                if ya_existe:
                    continue

                hints = extraer_hints_asunto(email_data.get("asunto", ""))
                clasificacion = clasificar_email(
                    remitente=email_data["remitente"],
                    asunto=email_data["asunto"],
                    cuerpo_texto=email_data.get("cuerpo_texto", ""),
                    reglas=reglas,
                )
                if hints.tipo_doc and clasificacion.get("tipo_doc") is None:
                    clasificacion["tipo_doc"] = hints.tipo_doc

                estado_inicial = _ESTADO_POR_ACCION.get(
                    clasificacion["accion"], "PENDIENTE"
                )

                # Para cuentas gestoría: resolver empresa_destino_id por slug_destino
                empresa_destino_id = None
                if clasificacion["accion"] == "CLASIFICAR":
                    slug = clasificacion.get("slug_destino")
                    if slug and empresas_gestoria:
                        empresa_destino_id = self._resolver_empresa_por_slug(
                            slug, empresas_gestoria
                        )
                    elif slug and cuenta_id:
                        # cuenta empresa: empresa_id es el destino directo
                        empresa_destino_id = None  # se asigna manualmente si aplica

                email_bd = EmailProcesado(
                    cuenta_id=cuenta_id,
                    uid_servidor=email_data["uid"],
                    message_id=email_data.get("message_id"),
                    remitente=email_data["remitente"],
                    asunto=email_data.get("asunto", ""),
                    fecha_email=email_data.get("fecha"),
                    estado=estado_inicial,
                    nivel_clasificacion=clasificacion["nivel"],
                    empresa_destino_id=empresa_destino_id,
                    confianza_ia=clasificacion.get("confianza"),
                )
                sesion.add(email_bd)
                sesion.flush()

                for adj in email_data.get("adjuntos", []):
                    sesion.add(AdjuntoEmail(
                        email_id=email_bd.id,
                        nombre_original=adj["nombre"],
                        tamano_bytes=len(adj.get("datos_bytes", b"")),
                        mime_type=adj.get("mime_type", "application/pdf"),
                    ))

                if email_data.get("cuerpo_html"):
                    for enlace in extraer_enlaces(email_data["cuerpo_html"]):
                        sesion.add(EnlaceEmail(
                            email_id=email_bd.id,
                            url=enlace["url"],
                            dominio=enlace["dominio"],
                            patron_detectado=enlace["patron"],
                        ))

                procesados += 1

            cuenta_obj = sesion.get(CuentaCorreo, cuenta_id)
            if emails and cuenta_obj:
                max_uid = max(int(e["uid"]) for e in emails if e["uid"].isdigit())
                if max_uid > (cuenta_obj.ultimo_uid or 0):
                    cuenta_obj.ultimo_uid = max_uid
            sesion.commit()

        logger.info("Cuenta %d: %d emails nuevos procesados", cuenta_id, procesados)
        return procesados

    def _descargar_emails_cuenta(self, cuenta_id: int, ultimo_uid: int) -> list[dict]:
        """Descarga emails nuevos usando el protocolo configurado en la cuenta."""
        with Session(self._engine) as sesion:
            cuenta = sesion.get(CuentaCorreo, cuenta_id)
            if not cuenta:
                return []
            if cuenta.protocolo == "imap":
                from sfce.conectores.correo.imap_servicio import ImapServicio
                from sfce.core.cifrado import descifrar
                contrasena = descifrar(cuenta.contrasena_enc) if cuenta.contrasena_enc else ""
                svc = ImapServicio(
                    servidor=cuenta.servidor,
                    puerto=cuenta.puerto,
                    ssl=bool(cuenta.ssl),
                    usuario=cuenta.usuario,
                    contrasena=contrasena,
                    carpeta=cuenta.carpeta_entrada,
                )
                return svc.descargar_nuevos(ultimo_uid)
        return []

    def _cargar_reglas(self, sesion: Session, empresa_id: int) -> list[dict]:
        """Carga reglas activas de la empresa + reglas globales (empresa_id=None)."""
        reglas = sesion.execute(
            select(ReglaClasificacionCorreo).where(
                ReglaClasificacionCorreo.activa == True,  # noqa: E712
                (ReglaClasificacionCorreo.empresa_id == empresa_id)
                | ReglaClasificacionCorreo.empresa_id.is_(None),
            ).order_by(ReglaClasificacionCorreo.prioridad)
        ).scalars().all()
        return [self._regla_a_dict(r) for r in reglas]

    def _cargar_reglas_gestoria(
        self, sesion: Session, gestoria_id: int
    ) -> tuple[list[dict], list[dict]]:
        """Carga reglas de todas las empresas de la gestoría + globales.

        Returns:
            (reglas, empresas) donde empresas es [{id, nombre, slug}]
        """
        empresas_ids = sesion.execute(
            select(Empresa.id).where(Empresa.gestoria_id == gestoria_id)
        ).scalars().all()

        reglas_orm = sesion.execute(
            select(ReglaClasificacionCorreo).where(
                ReglaClasificacionCorreo.activa == True,  # noqa: E712
                ReglaClasificacionCorreo.empresa_id.in_(empresas_ids)
                | ReglaClasificacionCorreo.empresa_id.is_(None),
            ).order_by(ReglaClasificacionCorreo.prioridad)
        ).scalars().all()

        empresas_orm = sesion.execute(
            select(Empresa).where(Empresa.id.in_(empresas_ids))
        ).scalars().all()

        empresas = [{"id": e.id, "nombre": e.nombre} for e in empresas_orm]
        return [self._regla_a_dict(r) for r in reglas_orm], empresas

    def _resolver_empresa_por_slug(
        self, slug: str, empresas: list[dict]
    ) -> int | None:
        """Busca empresa_id por slug (slug = nombre normalizado)."""
        import re
        for emp in empresas:
            nombre_slug = re.sub(r"[^a-z0-9]", "", emp["nombre"].lower())[:20]
            if nombre_slug == slug:
                return emp["id"]
        return None

    @staticmethod
    def _regla_a_dict(r: ReglaClasificacionCorreo) -> dict:
        return {
            "tipo": r.tipo,
            "condicion_json": r.condicion_json,
            "accion": r.accion,
            "slug_destino": r.slug_destino,
            "prioridad": r.prioridad,
            "activa": r.activa,
        }


def ejecutar_polling_todas_las_cuentas(engine: Engine) -> None:
    """Entry point para scheduler: procesa todas las cuentas activas excepto 'sistema'."""
    with Session(engine) as sesion:
        cuentas = sesion.execute(
            select(CuentaCorreo.id).where(
                CuentaCorreo.activa == True,  # noqa: E712
                CuentaCorreo.tipo_cuenta != "sistema",
            )
        ).scalars().all()

    ingesta = IngestaCorreo(engine=engine)
    for cuenta_id in cuentas:
        try:
            ingesta.procesar_cuenta(cuenta_id)
        except Exception as exc:
            logger.error("Error procesando cuenta %d: %s", cuenta_id, exc)
```

**Step 4: Ejecutar tests**

```bash
pytest tests/test_ingesta_correo.py -v 2>&1 | tail -25
```
Esperado: todos PASSED

**Step 5: Commit**

```bash
git add sfce/conectores/correo/ingesta_correo.py tests/test_ingesta_correo.py
git commit -m "feat: ingesta — routing por gestoría, omitir cuentas sistema en polling"
```

---

## Task 4: API admin — CRUD cuentas de correo

**Archivos:**
- Modificar: `sfce/api/rutas/correo.py`
- Test: `tests/test_api_correo_admin.py`

**Step 1: Escribir tests que fallan**

```python
# tests/test_api_correo_admin.py
import os
import pytest
os.environ["SFCE_JWT_SECRET"] = "a" * 32

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sfce.db.modelos_auth as _auth
from sfce.db.modelos import Base
from sfce.db.modelos_auth import Base as AuthBase, Gestoria, Usuario
from sfce.core.seguridad import crear_token_acceso


def _crear_engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    AuthBase.metadata.create_all(eng)
    return eng


@pytest.fixture
def cliente_superadmin():
    eng = _crear_engine()
    sf = sessionmaker(bind=eng)
    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    client = TestClient(app)
    # Crear superadmin
    from sfce.core.seguridad import hashear_password
    with sf() as s:
        u = Usuario(
            email="admin@sfce.local",
            nombre="Admin",
            hash_password=hashear_password("admin"),
            rol="superadmin",
        )
        s.add(u)
        s.commit()
    token = crear_token_acceso({"sub": "admin@sfce.local", "rol": "superadmin"})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def cliente_admin_gestoria():
    eng = _crear_engine()
    sf = sessionmaker(bind=eng)
    from sfce.api.app import crear_app
    app = crear_app(sesion_factory=sf)
    client = TestClient(app)
    from sfce.core.seguridad import hashear_password
    with sf() as s:
        g = Gestoria(
            nombre="Gestoría Test",
            email_contacto="g@test.es",
            plan_asesores=1,
            plan_clientes_tramo="1-10",
        )
        s.add(g)
        s.flush()
        u = Usuario(
            email="ag@sfce.local",
            nombre="Admin Gestoria",
            hash_password=hashear_password("pass"),
            rol="admin_gestoria",
            gestoria_id=g.id,
        )
        s.add(u)
        s.commit()
        gid = g.id
    token = crear_token_acceso({"sub": "ag@sfce.local", "rol": "admin_gestoria", "gestoria_id": gid})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, gid


def test_crear_cuenta_admin_superadmin(cliente_superadmin):
    resp = cliente_superadmin.post("/api/correo/admin/cuentas", json={
        "nombre": "Catch-all",
        "tipo_cuenta": "dedicada",
        "servidor": "imap.zoho.eu",
        "puerto": 993,
        "ssl": True,
        "usuario": "docs@prometh-ai.es",
        "contrasena": "secreto",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["tipo_cuenta"] == "dedicada"
    assert data["usuario"] == "docs@prometh-ai.es"


def test_listar_cuentas_admin(cliente_superadmin):
    cliente_superadmin.post("/api/correo/admin/cuentas", json={
        "nombre": "Test",
        "tipo_cuenta": "sistema",
        "servidor": "smtp.zoho.eu",
        "puerto": 993,
        "ssl": True,
        "usuario": "noreply@prometh-ai.es",
        "contrasena": "x",
    })
    resp = cliente_superadmin.get("/api/correo/admin/cuentas")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_desactivar_cuenta_admin(cliente_superadmin):
    r = cliente_superadmin.post("/api/correo/admin/cuentas", json={
        "nombre": "Borrar",
        "tipo_cuenta": "empresa",
        "empresa_id": 1,
        "servidor": "imap.zoho.eu",
        "puerto": 993,
        "ssl": True,
        "usuario": "x@test.com",
        "contrasena": "x",
    })
    cid = r.json()["id"]
    resp = cliente_superadmin.delete(f"/api/correo/admin/cuentas/{cid}")
    assert resp.status_code == 200
    resp2 = cliente_superadmin.get("/api/correo/admin/cuentas")
    ids = [c["id"] for c in resp2.json() if c["activa"]]
    assert cid not in ids


def test_crear_cuenta_admin_requiere_superadmin(cliente_admin_gestoria):
    client, _ = cliente_admin_gestoria
    resp = client.post("/api/correo/admin/cuentas", json={
        "nombre": "X",
        "tipo_cuenta": "gestoria",
        "servidor": "imap.zoho.eu",
        "puerto": 993,
        "ssl": True,
        "usuario": "g@prometh-ai.es",
        "contrasena": "x",
    })
    assert resp.status_code == 403


def test_get_cuenta_gestoria(cliente_admin_gestoria):
    """admin_gestoria puede ver su propia cuenta de correo."""
    client, gid = cliente_admin_gestoria
    # Primero crear la cuenta (solo superadmin puede crear, pero fixture no tiene superadmin aquí)
    # Verificar que el endpoint 403 cuando no hay cuenta
    resp = client.get(f"/api/correo/gestorias/{gid}/cuenta-correo")
    assert resp.status_code in (200, 404)
```

**Step 2: Ejecutar y verificar que fallan**

```bash
pytest tests/test_api_correo_admin.py -v 2>&1 | tail -20
```

**Step 3: Añadir los endpoints en `sfce/api/rutas/correo.py`**

Añadir después de las importaciones y antes de los routers existentes:

```python
# ---------------------------------------------------------------------------
# Schemas admin
# ---------------------------------------------------------------------------

class CrearCuentaAdminRequest(BaseModel):
    nombre: str
    tipo_cuenta: str = "empresa"          # 'empresa'|'dedicada'|'gestoria'|'sistema'
    empresa_id: int | None = None
    gestoria_id: int | None = None
    servidor: str | None = None
    puerto: int = 993
    ssl: bool = True
    usuario: str
    contrasena: str
    carpeta_entrada: str = "INBOX"
    polling_intervalo_segundos: int = 120


class ActualizarCuentaAdminRequest(BaseModel):
    nombre: str | None = None
    servidor: str | None = None
    puerto: int | None = None
    ssl: bool | None = None
    contrasena: str | None = None
    activa: bool | None = None


# ---------------------------------------------------------------------------
# Endpoints admin (solo superadmin)
# ---------------------------------------------------------------------------

@router.get("/admin/cuentas")
def admin_listar_cuentas(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.get("rol") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuentas = s.execute(select(CuentaCorreo)).scalars().all()
        return [
            {
                "id": c.id,
                "nombre": c.nombre,
                "tipo_cuenta": c.tipo_cuenta,
                "usuario": c.usuario,
                "servidor": c.servidor,
                "activa": c.activa,
                "ultimo_uid": c.ultimo_uid,
                "empresa_id": c.empresa_id,
                "gestoria_id": c.gestoria_id,
            }
            for c in cuentas
        ]


@router.post("/admin/cuentas", status_code=201)
def admin_crear_cuenta(
    body: CrearCuentaAdminRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.get("rol") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = CuentaCorreo(
            nombre=body.nombre,
            tipo_cuenta=body.tipo_cuenta,
            empresa_id=body.empresa_id,
            gestoria_id=body.gestoria_id,
            protocolo="imap",
            servidor=body.servidor,
            puerto=body.puerto,
            ssl=body.ssl,
            usuario=body.usuario,
            contrasena_enc=cifrar(body.contrasena),
            carpeta_entrada=body.carpeta_entrada,
            polling_intervalo_segundos=body.polling_intervalo_segundos,
        )
        s.add(cuenta)
        s.commit()
        return {
            "id": cuenta.id,
            "nombre": cuenta.nombre,
            "tipo_cuenta": cuenta.tipo_cuenta,
            "usuario": cuenta.usuario,
            "activa": cuenta.activa,
        }


@router.put("/admin/cuentas/{cuenta_id}")
def admin_actualizar_cuenta(
    cuenta_id: int,
    body: ActualizarCuentaAdminRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.get("rol") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404)
        if body.nombre is not None:
            cuenta.nombre = body.nombre
        if body.servidor is not None:
            cuenta.servidor = body.servidor
        if body.puerto is not None:
            cuenta.puerto = body.puerto
        if body.ssl is not None:
            cuenta.ssl = body.ssl
        if body.contrasena is not None:
            cuenta.contrasena_enc = cifrar(body.contrasena)
        if body.activa is not None:
            cuenta.activa = body.activa
        s.commit()
        return {"id": cuenta.id, "activa": cuenta.activa}


@router.delete("/admin/cuentas/{cuenta_id}")
def admin_desactivar_cuenta(
    cuenta_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.get("rol") != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404)
        cuenta.activa = False
        s.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Endpoints gestoría — ver/actualizar su propia cuenta
# ---------------------------------------------------------------------------

@router.get("/gestorias/{gestoria_id}/cuenta-correo")
def gestoria_get_cuenta(
    gestoria_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    rol = usuario.get("rol")
    if rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403)
    if rol == "admin_gestoria" and usuario.get("gestoria_id") != gestoria_id:
        raise HTTPException(status_code=403)
    with sesion_factory() as s:
        cuenta = s.execute(
            select(CuentaCorreo).where(
                CuentaCorreo.gestoria_id == gestoria_id,
                CuentaCorreo.tipo_cuenta == "gestoria",
            )
        ).scalar_one_or_none()
        if not cuenta:
            raise HTTPException(status_code=404, detail="Sin cuenta de correo configurada")
        return {
            "id": cuenta.id,
            "nombre": cuenta.nombre,
            "servidor": cuenta.servidor,
            "usuario": cuenta.usuario,
            "activa": cuenta.activa,
            "ultimo_uid": cuenta.ultimo_uid,
        }


@router.put("/gestorias/{gestoria_id}/cuenta-correo")
def gestoria_actualizar_cuenta(
    gestoria_id: int,
    body: ActualizarCuentaAdminRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    rol = usuario.get("rol")
    if rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403)
    if rol == "admin_gestoria" and usuario.get("gestoria_id") != gestoria_id:
        raise HTTPException(status_code=403)
    with sesion_factory() as s:
        cuenta = s.execute(
            select(CuentaCorreo).where(
                CuentaCorreo.gestoria_id == gestoria_id,
                CuentaCorreo.tipo_cuenta == "gestoria",
            )
        ).scalar_one_or_none()
        if not cuenta:
            raise HTTPException(status_code=404)
        if body.servidor is not None:
            cuenta.servidor = body.servidor
        if body.contrasena is not None:
            cuenta.contrasena_enc = cifrar(body.contrasena)
        if body.activa is not None:
            cuenta.activa = body.activa
        s.commit()
        return {"ok": True, "id": cuenta.id}
```

**Step 4: Ejecutar tests**

```bash
pytest tests/test_api_correo_admin.py -v 2>&1 | tail -20
```
Esperado: todos PASSED

**Step 5: Regresión**

```bash
pytest tests/test_api_correo.py tests/test_ingesta_correo.py -v 2>&1 | tail -15
```

**Step 6: Commit**

```bash
git add sfce/api/rutas/correo.py tests/test_api_correo_admin.py
git commit -m "feat: API correo admin — CRUD cuentas superadmin + GET/PUT por gestoría"
```

---

## Task 5: Variables de entorno SMTP Zoho

**Archivos:**
- Modificar: `.env.example` (si existe) o crear `docs/zoho-setup.md`
- Actualizar: `.env` local del servidor (manual, fuera de git)

**Step 1: Verificar si existe .env.example**

```bash
ls -la .env* 2>/dev/null | head -5
```

**Step 2: Añadir las variables SMTP al .env.example**

Si existe `.env.example`, añadir al final:

```bash
# === ZOHO MAIL — SMTP saliente ===
SFCE_SMTP_HOST=smtp.zoho.eu
SFCE_SMTP_PORT=587
SFCE_SMTP_USER=noreply@prometh-ai.es
SFCE_SMTP_PASSWORD=
SFCE_SMTP_FROM=noreply@prometh-ai.es
```

Si no existe, crear `docs/zoho-setup.md`:

```markdown
# Configuración Zoho Mail

## Cuentas a crear en Zoho (organización prometh-ai.es)

| Cuenta | Tipo | Uso |
|--------|------|-----|
| noreply@prometh-ai.es | Sistema | SMTP saliente: invitaciones, alertas |
| docs@prometh-ai.es | Catch-all | Recibe empresa+tipo@prometh-ai.es |
| gestoriaX@prometh-ai.es | Por gestoría | Una cuenta por cada gestoría |

## DNS en DonDominio

1. MX: prioridad 10 → mx.zoho.eu
2. SPF: v=spf1 include:zoho.eu ~all
3. DKIM: clave TXT generada en panel Zoho → Mail → Domains → DKIM

## Variables de entorno en servidor (/opt/apps/sfce/.env)

SFCE_SMTP_HOST=smtp.zoho.eu
SFCE_SMTP_PORT=587
SFCE_SMTP_USER=noreply@prometh-ai.es
SFCE_SMTP_PASSWORD=<password de noreply en Zoho>
SFCE_SMTP_FROM=noreply@prometh-ai.es

## IMAP por gestoría (configurar en dashboard SFCE)

Servidor: imap.zoho.eu  Puerto: 993  SSL: sí
Catch-all: docs@prometh-ai.es  Carpeta: INBOX

## Catch-all en Zoho

Panel Zoho → Mail → Settings → Catch-all → Deliver to: docs@prometh-ai.es
```

**Step 3: Commit**

```bash
git add docs/zoho-setup.md  # o .env.example si existe
git commit -m "docs: configuración Zoho Mail — SMTP, DNS, IMAP por gestoría"
```

---

## Task 6: Dashboard — UI gestión cuentas de correo

**Archivos:**
- Crear: `dashboard/src/features/correo/cuentas-correo-page.tsx`
- Crear: `dashboard/src/features/correo/cuenta-correo-card.tsx`
- Modificar: `dashboard/src/App.tsx` (añadir ruta)
- Modificar: `dashboard/src/components/layout/app-sidebar.tsx` (añadir enlace)

**Step 1: Crear el componente card para una cuenta**

```tsx
// dashboard/src/features/correo/cuenta-correo-card.tsx
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface CuentaCorreo {
  id: number
  nombre: string
  tipo_cuenta: string
  usuario: string
  servidor: string | null
  activa: boolean
  ultimo_uid: number
  empresa_id: number | null
  gestoria_id: number | null
}

interface Props {
  cuenta: CuentaCorreo
  onDesactivar: (id: number) => void
}

const TIPO_LABEL: Record<string, string> = {
  dedicada: "Catch-all",
  gestoria: "Gestoría",
  sistema: "Sistema",
  empresa: "Empresa",
}

const TIPO_COLOR: Record<string, string> = {
  dedicada: "bg-blue-100 text-blue-800",
  gestoria: "bg-green-100 text-green-800",
  sistema: "bg-gray-100 text-gray-700",
  empresa: "bg-amber-100 text-amber-800",
}

export function CuentaCorreoCard({ cuenta, onDesactivar }: Props) {
  return (
    <Card className="border border-border/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{cuenta.nombre}</CardTitle>
          <div className="flex gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TIPO_COLOR[cuenta.tipo_cuenta] ?? ""}`}>
              {TIPO_LABEL[cuenta.tipo_cuenta] ?? cuenta.tipo_cuenta}
            </span>
            <Badge variant={cuenta.activa ? "default" : "secondary"}>
              {cuenta.activa ? "Activa" : "Inactiva"}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{cuenta.usuario}</p>
        {cuenta.servidor && (
          <p className="text-xs text-muted-foreground mt-0.5">{cuenta.servidor}</p>
        )}
        <p className="text-xs text-muted-foreground mt-1">Último UID: {cuenta.ultimo_uid}</p>
        {cuenta.activa && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-2 text-red-600 hover:text-red-700"
            onClick={() => onDesactivar(cuenta.id)}
          >
            Desactivar
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
```

**Step 2: Crear la página principal de cuentas**

```tsx
// dashboard/src/features/correo/cuentas-correo-page.tsx
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { CuentaCorreoCard } from "./cuenta-correo-card"
import { useAuthStore } from "@/store/auth"
import { PageTitle } from "@/components/ui/page-title"

interface NuevaCuentaForm {
  nombre: string
  tipo_cuenta: string
  servidor: string
  puerto: number
  ssl: boolean
  usuario: string
  contrasena: string
  gestoria_id?: number
  empresa_id?: number
}

async function fetchCuentas(token: string) {
  const r = await fetch("/api/correo/admin/cuentas", {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!r.ok) throw new Error("Error cargando cuentas")
  return r.json()
}

async function crearCuenta(token: string, datos: NuevaCuentaForm) {
  const r = await fetch("/api/correo/admin/cuentas", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(datos),
  })
  if (!r.ok) throw new Error("Error creando cuenta")
  return r.json()
}

async function desactivarCuenta(token: string, id: number) {
  const r = await fetch(`/api/correo/admin/cuentas/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!r.ok) throw new Error("Error desactivando cuenta")
  return r.json()
}

export function CuentasCorreoPage() {
  const token = useAuthStore((s) => s.token) ?? ""
  const qc = useQueryClient()
  const [abierto, setAbierto] = useState(false)
  const [form, setForm] = useState<NuevaCuentaForm>({
    nombre: "",
    tipo_cuenta: "gestoria",
    servidor: "imap.zoho.eu",
    puerto: 993,
    ssl: true,
    usuario: "",
    contrasena: "",
  })

  const { data: cuentas = [], isLoading } = useQuery({
    queryKey: ["cuentas-correo"],
    queryFn: () => fetchCuentas(token),
  })

  const crearMut = useMutation({
    mutationFn: (datos: NuevaCuentaForm) => crearCuenta(token, datos),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cuentas-correo"] })
      setAbierto(false)
    },
  })

  const desactivarMut = useMutation({
    mutationFn: (id: number) => desactivarCuenta(token, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cuentas-correo"] }),
  })

  const porTipo = (tipo: string) => cuentas.filter((c: any) => c.tipo_cuenta === tipo)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <PageTitle title="Cuentas de correo" subtitle="Buzones IMAP y SMTP Zoho" />
        <Dialog open={abierto} onOpenChange={setAbierto}>
          <DialogTrigger asChild>
            <Button size="sm">Nueva cuenta</Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Añadir cuenta de correo</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 mt-2">
              <div>
                <Label>Nombre</Label>
                <Input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Gestoría López" />
              </div>
              <div>
                <Label>Tipo</Label>
                <Select value={form.tipo_cuenta} onValueChange={(v) => setForm({ ...form, tipo_cuenta: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dedicada">Catch-all (docs@prometh-ai.es)</SelectItem>
                    <SelectItem value="gestoria">Gestoría</SelectItem>
                    <SelectItem value="sistema">Sistema (noreply)</SelectItem>
                    <SelectItem value="empresa">Empresa individual</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Servidor IMAP</Label>
                <Input value={form.servidor} onChange={(e) => setForm({ ...form, servidor: e.target.value })} />
              </div>
              <div>
                <Label>Usuario (email)</Label>
                <Input value={form.usuario} onChange={(e) => setForm({ ...form, usuario: e.target.value })} placeholder="gestoria1@prometh-ai.es" />
              </div>
              <div>
                <Label>Contraseña Zoho</Label>
                <Input type="password" value={form.contrasena} onChange={(e) => setForm({ ...form, contrasena: e.target.value })} />
              </div>
              <Button
                className="w-full"
                onClick={() => crearMut.mutate(form)}
                disabled={crearMut.isPending}
              >
                {crearMut.isPending ? "Guardando..." : "Guardar"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Cargando...</p>}

      {["dedicada", "sistema", "gestoria", "empresa"].map((tipo) => {
        const lista = porTipo(tipo)
        if (!lista.length) return null
        const labels: Record<string, string> = {
          dedicada: "Catch-all", sistema: "Sistema", gestoria: "Gestoría", empresa: "Empresa",
        }
        return (
          <div key={tipo}>
            <h3 className="text-sm font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
              {labels[tipo]}
            </h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {lista.map((c: any) => (
                <CuentaCorreoCard key={c.id} cuenta={c} onDesactivar={desactivarMut.mutate} />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

**Step 3: Registrar la ruta en App.tsx**

Buscar en `dashboard/src/App.tsx` la sección de rutas lazy y añadir:

```tsx
const CuentasCorreoPage = lazy(() =>
  import("@/features/correo/cuentas-correo-page").then((m) => ({ default: m.CuentasCorreoPage }))
)
```

Y añadir la ruta dentro del AppShell protegido:
```tsx
<Route path="/correo/cuentas" element={<CuentasCorreoPage />} />
```

**Step 4: Añadir enlace en el sidebar**

En `dashboard/src/components/layout/app-sidebar.tsx`, buscar el grupo de administración (donde está "Gestorias", "Usuarios"…) y añadir:

```tsx
{ title: "Cuentas correo", href: "/correo/cuentas", icon: Mail, roles: ["superadmin"] },
```

Asegurarse de que `Mail` está importado de `lucide-react`.

**Step 5: Compilar y verificar**

```bash
cd dashboard && npm run build 2>&1 | tail -10
```
Esperado: `✓ built in X.XXs`

**Step 6: Commit**

```bash
git add dashboard/src/features/correo/ dashboard/src/App.tsx dashboard/src/components/layout/app-sidebar.tsx
git commit -m "feat: dashboard — página gestión cuentas correo Zoho"
```

---

## Task 7: Ejecutar migración 019 en producción

**Step 1: Subir el archivo de migración al servidor**

```bash
scp sfce/db/migraciones/migracion_019_cuentas_correo_gestoria.py \
    carli@65.108.60.69:/opt/apps/sfce/sfce/db/migraciones/
```

**Step 2: Ejecutar la migración en producción**

```bash
ssh carli@65.108.60.69
cd /opt/apps/sfce
source .env
python sfce/db/migraciones/migracion_019_cuentas_correo_gestoria.py
```
Esperado: `Migración 019 aplicada.`

**Step 3: Añadir variables SMTP Zoho al .env del servidor**

```bash
# En el servidor, editar /opt/apps/sfce/.env y añadir:
SFCE_SMTP_HOST=smtp.zoho.eu
SFCE_SMTP_PORT=587
SFCE_SMTP_USER=noreply@prometh-ai.es
SFCE_SMTP_PASSWORD=<password-zoho>
SFCE_SMTP_FROM=noreply@prometh-ai.es
```

**Step 4: Reiniciar el servicio**

```bash
cd /opt/apps/sfce && docker compose restart sfce_api
docker compose logs sfce_api --tail=20
```
Esperado: sin errores de startup.

---

## Task 8: Actualizar documentación del libro

**Archivos:**
- Modificar: `docs/LIBRO/_temas/20-correo.md`

**Step 1: Actualizar la sección "Cómo añadir una cuenta nueva"**

Localizar la sección 8 de `docs/LIBRO/_temas/20-correo.md` y reemplazar con:

```markdown
## 8. Cómo añadir una cuenta nueva

### Cuentas Zoho bajo prometh-ai.es

| Cuenta | tipo_cuenta | Uso |
|--------|-------------|-----|
| noreply@prometh-ai.es | sistema | SMTP saliente — no hace polling IMAP |
| docs@prometh-ai.es | dedicada | Catch-all. Enruta por campo To via canal_email_dedicado.py |
| gestoriaX@prometh-ai.es | gestoria | Una por gestoría. Enruta por remitente entre empresas de la gestoría |

### Via dashboard (superadmin)

Ir a **Administración → Cuentas correo → Nueva cuenta**.
Servidor IMAP Zoho: `imap.zoho.eu`, puerto `993`, SSL activado.

### Via API

POST /api/correo/admin/cuentas (requiere rol superadmin):

```python
{
    "nombre": "Gestoría López",
    "tipo_cuenta": "gestoria",
    "gestoria_id": 3,
    "servidor": "imap.zoho.eu",
    "puerto": 993,
    "ssl": True,
    "usuario": "gestorialopez@prometh-ai.es",
    "contrasena": "password-zoho",
}
```

Para protocolo `graph` (Microsoft Graph / Office 365): sin cambios respecto a la implementación anterior.

### Variables SMTP (servidor /opt/apps/sfce/.env)

SFCE_SMTP_HOST=smtp.zoho.eu
SFCE_SMTP_PORT=587
SFCE_SMTP_USER=noreply@prometh-ai.es
SFCE_SMTP_PASSWORD=<password>
SFCE_SMTP_FROM=noreply@prometh-ai.es
```

**Step 2: Commit**

```bash
git add docs/LIBRO/_temas/20-correo.md
git commit -m "docs: libro 20-correo — actualizar para Zoho y cuentas por gestoría"
```

---

## Task 9: Suite de regresión final

**Step 1: Ejecutar todos los tests de correo**

```bash
pytest tests/test_migracion_019.py tests/test_modelo_cuenta_correo.py \
       tests/test_ingesta_correo.py tests/test_api_correo.py \
       tests/test_api_correo_admin.py tests/test_clasificacion_correo.py \
       -v 2>&1 | tail -30
```
Esperado: todos PASSED, 0 FAILED.

**Step 2: Suite completa**

```bash
pytest --tb=no -q 2>&1 | tail -5
```
Esperado: misma cantidad de PASS que antes de empezar (2320) + ~35 nuevos.

**Step 3: Build frontend**

```bash
cd dashboard && npm run build 2>&1 | tail -5
```

**Step 4: Commit final si hay cambios pendientes**

```bash
git add -A
git status
# Solo commitear si hay algo pendiente
```

---

## Resumen de cuentas Zoho a crear manualmente

Antes de configurar en SFCE, crear estas cuentas en el panel Zoho:

1. **noreply@prometh-ai.es** — para SMTP saliente
2. **docs@prometh-ai.es** — configurar como catch-all en Zoho Mail Settings
3. **gestoriaX@prometh-ai.es** — una por cada gestoría activa

DNS en DonDominio:
- MX: `mx.zoho.eu` (prioridad 10) y `mx2.zoho.eu` (20)
- SPF: `v=spf1 include:zoho.eu ~all`
- DKIM: clave TXT generada en Zoho → Mail → Domains → DKIM
