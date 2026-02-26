# Fase A — Gestoria AI-Powered: Plan de Implementacion

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convertir el sistema SFCE en un servicio de gestoria AI-powered con email intake automatico + portal web para clientes.

**Architecture:** FastAPI backend que wrappea los modulos SFCE existentes (`scripts/core/`, `scripts/phases/`), expone API REST para un frontend React. Email intake via IMAP polling deposita PDFs en `inbox/` y dispara el pipeline. PostgreSQL almacena usuarios, sesiones y estado de documentos. FacturaScripts (MariaDB) sigue siendo el motor contable.

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL | React 18 + Vite + Tailwind | Docker Compose | Mailgun/IMAP

**Diseno de referencia:** `docs/plans/2026-02-26-saas-gestoria-ia-design.md`

---

## Prerequisito: Resolver confianza SFCE

> **IMPORTANTE**: Antes de construir el portal, el pipeline SFCE debe funcionar end-to-end. El hallazgo del dry-run (28% confianza) debe resolverse primero. Ver seccion "Testing SFCE" en CLAUDE.md.

---

## Task 0: Setup del proyecto

**Files:**
- Create: `requirements.txt`
- Create: `backend/` (directorio)
- Create: `.env.example`
- Create: `docker-compose.dev.yml`

**Step 1: Crear requirements.txt**

```txt
# Core SFCE (ya en uso)
pdfplumber>=0.10.0
openai>=1.0.0
requests>=2.31.0
pyyaml>=6.0
openpyxl>=3.1.0
fpdf2>=2.7.0

# Backend web
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
alembic>=1.13.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.0
python-multipart>=0.0.6
python-dotenv>=1.0.0
httpx>=0.27.0

# Email intake
imapclient>=3.0.0

# Dev
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

**Step 2: Crear .env.example**

```env
# FacturaScripts
FS_API_TOKEN=tu_token_aqui
FS_API_URL=https://contabilidad.lemonfresh-tuc.com/api/3/

# OpenAI
OPENAI_API_KEY=tu_key_aqui

# PostgreSQL
DATABASE_URL=postgresql://contabilidad:password@localhost:5432/contabilidad

# JWT
JWT_SECRET=cambiar_en_produccion
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Email intake
IMAP_HOST=imap.mailgun.org
IMAP_USER=facturas@tudominio.com
IMAP_PASSWORD=tu_password
IMAP_POLL_INTERVAL=300

# Entorno
ENVIRONMENT=development
```

**Step 3: Crear docker-compose.dev.yml**

```yaml
version: "3.8"
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: contabilidad
      POSTGRES_USER: contabilidad
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

**Step 4: Crear estructura de directorios backend**

```bash
mkdir -p backend/app/{api,models,schemas,services,core}
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/services/__init__.py
touch backend/app/core/__init__.py
```

**Step 5: Commit**

```bash
git add requirements.txt .env.example docker-compose.dev.yml backend/
git commit -m "feat: setup proyecto SaaS (requirements, docker-compose, estructura backend)"
```

---

## Task 1: Base de datos — Modelos y migraciones

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/usuario.py`
- Create: `backend/app/models/cliente.py`
- Create: `backend/app/models/documento.py`
- Create: `alembic.ini`
- Create: `backend/alembic/env.py`
- Test: `tests/backend/test_models.py`

**Step 1: Escribir test de modelos**

```python
# tests/backend/test_models.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.app.core.database import Base
from backend.app.models.usuario import Usuario, Rol
from backend.app.models.cliente import ClienteDB
from backend.app.models.documento import Documento, EstadoDocumento


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def test_crear_usuario(db_session):
    usuario = Usuario(
        email="test@ejemplo.com",
        nombre="Test User",
        hashed_password="hash123",
        rol=Rol.GESTOR,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)

    assert usuario.id is not None
    assert usuario.email == "test@ejemplo.com"
    assert usuario.rol == Rol.GESTOR
    assert usuario.activo is True


def test_crear_cliente(db_session):
    gestor = Usuario(
        email="gestor@ejemplo.com",
        nombre="Gestor",
        hashed_password="hash",
        rol=Rol.GESTOR,
    )
    db_session.add(gestor)
    db_session.commit()

    cliente = ClienteDB(
        nombre="EMPRESA TEST S.L.",
        cif="B12345678",
        tipo="sl",
        carpeta="empresa-test",
        idempresa_fs=4,
        gestor_id=gestor.id,
    )
    db_session.add(cliente)
    db_session.commit()

    assert cliente.id is not None
    assert cliente.gestor_id == gestor.id


def test_crear_documento(db_session):
    gestor = Usuario(
        email="g@test.com", nombre="G", hashed_password="h", rol=Rol.GESTOR
    )
    db_session.add(gestor)
    db_session.commit()

    cliente = ClienteDB(
        nombre="E", cif="B00000000", tipo="sl",
        carpeta="e", idempresa_fs=1, gestor_id=gestor.id,
    )
    db_session.add(cliente)
    db_session.commit()

    doc = Documento(
        nombre_archivo="factura_001.pdf",
        hash_sha256="abc123",
        cliente_id=cliente.id,
        estado=EstadoDocumento.PENDIENTE,
        canal="email",
    )
    db_session.add(doc)
    db_session.commit()

    assert doc.id is not None
    assert doc.estado == EstadoDocumento.PENDIENTE
```

**Step 2: Ejecutar test — debe fallar**

```bash
pytest tests/backend/test_models.py -v
```
Expected: FAIL — modulos no existen

**Step 3: Implementar modelos**

`backend/app/core/database.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./contabilidad.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`backend/app/models/usuario.py`:
```python
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class Rol(str, enum.Enum):
    ADMIN = "admin"
    GESTOR = "gestor"
    CLIENTE = "cliente"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    rol: Mapped[Rol] = mapped_column(Enum(Rol), default=Rol.CLIENTE)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    clientes = relationship("ClienteDB", back_populates="gestor")
```

`backend/app/models/cliente.py`:
```python
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class ClienteDB(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255))
    cif: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    carpeta: Mapped[str] = mapped_column(String(255), unique=True)
    idempresa_fs: Mapped[int] = mapped_column(Integer)
    gestor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    gestor = relationship("Usuario", back_populates="clientes")
    documentos = relationship("Documento", back_populates="cliente")
```

`backend/app/models/documento.py`:
```python
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from backend.app.core.database import Base


class EstadoDocumento(str, enum.Enum):
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    REVISION = "revision"
    REGISTRADO = "registrado"
    ERROR = "error"


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre_archivo: Mapped[str] = mapped_column(String(500))
    hash_sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    estado: Mapped[EstadoDocumento] = mapped_column(
        Enum(EstadoDocumento), default=EstadoDocumento.PENDIENTE
    )
    canal: Mapped[str] = mapped_column(String(20))
    confianza: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    datos_extraidos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idfactura_fs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_detalle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    procesado: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    cliente = relationship("ClienteDB", back_populates="documentos")
```

**Step 4: Ejecutar test — debe pasar**

```bash
pytest tests/backend/test_models.py -v
```
Expected: 3 PASSED

**Step 5: Configurar Alembic para migraciones**

```bash
cd backend && alembic init alembic
```

Editar `backend/alembic/env.py` para importar Base y modelos.

**Step 6: Commit**

```bash
git add backend/app/core/database.py backend/app/models/ tests/backend/
git commit -m "feat: modelos BD (usuario, cliente, documento) con tests"
```

---

## Task 2: Autenticacion JWT

**Files:**
- Create: `backend/app/core/auth.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/schemas/auth.py`
- Test: `tests/backend/test_auth.py`

**Step 1: Escribir test de auth**

```python
# tests/backend/test_auth.py
import pytest
from backend.app.core.auth import crear_token, verificar_token, hash_password, verificar_password


def test_hash_y_verificar_password():
    password = "mi_password_seguro"
    hashed = hash_password(password)
    assert hashed != password
    assert verificar_password(password, hashed) is True
    assert verificar_password("password_malo", hashed) is False


def test_crear_y_verificar_token():
    datos = {"sub": "test@ejemplo.com", "rol": "gestor"}
    token = crear_token(datos)
    assert isinstance(token, str)

    payload = verificar_token(token)
    assert payload["sub"] == "test@ejemplo.com"
    assert payload["rol"] == "gestor"


def test_token_invalido():
    payload = verificar_token("token_invalido_xyz")
    assert payload is None
```

**Step 2: Ejecutar test — debe fallar**

```bash
pytest tests/backend/test_auth.py -v
```

**Step 3: Implementar auth**

`backend/app/core/auth.py`:
```python
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
import os

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_cambiar")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def crear_token(datos: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = datos.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verificar_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
```

`backend/app/schemas/auth.py`:
```python
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str


class UsuarioCreate(BaseModel):
    email: str
    nombre: str
    password: str
```

**Step 4: Ejecutar test — debe pasar**

```bash
pytest tests/backend/test_auth.py -v
```

**Step 5: Commit**

```bash
git add backend/app/core/auth.py backend/app/schemas/auth.py tests/backend/test_auth.py
git commit -m "feat: autenticacion JWT (hash, tokens, schemas)"
```

---

## Task 3: API endpoints — Auth + Documentos

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/documentos.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/schemas/documento.py`
- Test: `tests/backend/test_api_auth.py`
- Test: `tests/backend/test_api_documentos.py`

**Step 1: Escribir test de API auth**

```python
# tests/backend/test_api_auth.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.core.auth import hash_password
from backend.app.models.usuario import Usuario, Rol

engine = create_engine("sqlite:///:memory:")


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def override_get_db():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_login_exitoso():
    with Session(engine) as db:
        usuario = Usuario(
            email="gestor@test.com",
            nombre="Gestor Test",
            hashed_password=hash_password("password123"),
            rol=Rol.GESTOR,
        )
        db.add(usuario)
        db.commit()

    response = client.post("/api/auth/login", json={
        "email": "gestor@test.com",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["rol"] == "gestor"


def test_login_credenciales_invalidas():
    response = client.post("/api/auth/login", json={
        "email": "noexiste@test.com",
        "password": "wrong",
    })
    assert response.status_code == 401
```

**Step 2: Ejecutar test — debe fallar**

**Step 3: Implementar API**

`backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api import auth, documentos

app = FastAPI(title="Gestoria IA", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documentos.router, prefix="/api/documentos", tags=["documentos"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

`backend/app/api/deps.py`:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.auth import verificar_token
from backend.app.models.usuario import Usuario

security = HTTPBearer()


def get_usuario_actual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Usuario:
    payload = verificar_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")
    usuario = db.query(Usuario).filter(Usuario.email == payload["sub"]).first()
    if usuario is None or not usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return usuario
```

`backend/app/api/auth.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.auth import verificar_password, crear_token
from backend.app.models.usuario import Usuario
from backend.app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario or not verificar_password(datos.password, usuario.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")
    token = crear_token({"sub": usuario.email, "rol": usuario.rol.value})
    return TokenResponse(access_token=token, rol=usuario.rol.value, nombre=usuario.nombre)
```

`backend/app/api/documentos.py` y `backend/app/schemas/documento.py`: endpoints para listar, subir y ver estado de documentos del cliente autenticado. Incluyen:
- `POST /api/documentos/subir` — recibe archivo PDF, lo guarda en `inbox/`, crea registro en BD, dispara pipeline async
- `GET /api/documentos/` — lista documentos del cliente con estado, confianza, fecha
- `GET /api/documentos/{id}` — detalle de un documento

**Step 4: Ejecutar tests — deben pasar**

```bash
pytest tests/backend/test_api_auth.py tests/backend/test_api_documentos.py -v
```

**Step 5: Commit**

```bash
git add backend/app/ tests/backend/
git commit -m "feat: API REST (auth login, subir documentos, listar documentos)"
```

---

## Task 4: Servicio de procesamiento — Wrapper SFCE

**Files:**
- Create: `backend/app/services/procesador.py`
- Modify: `scripts/core/fs_api.py` (extraer token hardcodeado a env var)
- Test: `tests/backend/test_procesador.py`

**Objetivo:** Wrappear el pipeline SFCE existente como servicio invocable desde la API. El procesador:
1. Recibe path del PDF + cliente_id
2. Carga config.yaml del cliente (usando `scripts/core/config.py`)
3. Ejecuta intake (usando `scripts/phases/intake.py`)
4. Evalua confianza
5. Si >= 85%: ejecuta registration + asientos
6. Si < 85%: marca como "revision" en BD
7. Actualiza estado del Documento en PostgreSQL

**Importante:** No reescribir la logica SFCE. Importar y reutilizar los modulos existentes directamente.

```python
# backend/app/services/procesador.py
import sys
import os
from pathlib import Path

# Agregar raiz del proyecto al path para importar scripts/
RAIZ_PROYECTO = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(RAIZ_PROYECTO))

from scripts.core.config import ConfigCliente
from scripts.core.logger import crear_logger
from scripts.phases.intake import ejecutar as ejecutar_intake
from backend.app.models.documento import Documento, EstadoDocumento


def procesar_documento(documento: Documento, carpeta_cliente: str, db_session) -> dict:
    """Procesa un documento PDF usando el pipeline SFCE."""
    config = ConfigCliente(Path(RAIZ_PROYECTO) / "clientes" / carpeta_cliente / "config.yaml")
    logger = crear_logger(f"procesador_{documento.id}")

    documento.estado = EstadoDocumento.PROCESANDO
    db_session.commit()

    try:
        resultado_intake = ejecutar_intake(
            ruta_inbox=Path(RAIZ_PROYECTO) / "clientes" / carpeta_cliente / "inbox",
            config=config,
            logger=logger,
            archivos=[documento.nombre_archivo],
        )

        confianza = resultado_intake.get("confianza_global", 0)
        documento.confianza = confianza
        documento.datos_extraidos = str(resultado_intake.get("documentos", []))

        if confianza >= 85:
            documento.estado = EstadoDocumento.REGISTRADO
            # Ejecutar registration phase...
        else:
            documento.estado = EstadoDocumento.REVISION

        db_session.commit()
        return {"estado": documento.estado.value, "confianza": confianza}

    except Exception as e:
        documento.estado = EstadoDocumento.ERROR
        documento.error_detalle = str(e)
        db_session.commit()
        logger.error(f"Error procesando {documento.nombre_archivo}: {e}")
        return {"estado": "error", "error": str(e)}
```

**Step 1: Escribir test**
**Step 2: Verificar que falla**
**Step 3: Implementar**
**Step 4: Verificar que pasa**
**Step 5: Commit**

```bash
git commit -m "feat: servicio procesador (wrapper SFCE para API)"
```

---

## Task 5: Email intake — Script IMAP

**Files:**
- Create: `backend/app/services/email_intake.py`
- Test: `tests/backend/test_email_intake.py`

**Objetivo:** Script que:
1. Conecta a buzon IMAP (`facturas@dominio.com`)
2. Lee emails no leidos con adjuntos PDF
3. Identifica cliente por email remitente (mapeo en BD o config)
4. Guarda PDF en `clientes/{cliente}/inbox/`
5. Crea registro Documento en BD
6. Marca email como leido
7. Dispara procesamiento async

```python
# backend/app/services/email_intake.py
import os
import email
import hashlib
from pathlib import Path
from imapclient import IMAPClient
from datetime import datetime

IMAP_HOST = os.getenv("IMAP_HOST")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")


def conectar_imap():
    """Conecta al servidor IMAP."""
    server = IMAPClient(IMAP_HOST, ssl=True)
    server.login(IMAP_USER, IMAP_PASSWORD)
    server.select_folder("INBOX")
    return server


def procesar_emails_nuevos(db_session, raiz_clientes: Path):
    """Lee emails no leidos, extrae PDFs y los deposita en inbox del cliente."""
    server = conectar_imap()
    mensajes = server.search(["UNSEEN"])
    resultados = []

    for uid in mensajes:
        raw = server.fetch([uid], ["RFC822"])
        msg = email.message_from_bytes(raw[uid][b"RFC822"])
        remitente = email.utils.parseaddr(msg["From"])[1]

        for part in msg.walk():
            if part.get_content_type() == "application/pdf":
                nombre = part.get_filename() or f"adjunto_{uid}.pdf"
                contenido = part.get_payload(decode=True)
                hash_sha = hashlib.sha256(contenido).hexdigest()

                # Identificar cliente por email remitente
                cliente = _identificar_cliente(remitente, db_session)
                if not cliente:
                    resultados.append({"archivo": nombre, "error": f"remitente desconocido: {remitente}"})
                    continue

                # Guardar PDF
                destino = raiz_clientes / cliente.carpeta / "inbox" / nombre
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(contenido)

                resultados.append({"archivo": nombre, "cliente": cliente.nombre, "hash": hash_sha})

        server.set_flags([uid], [b"\\Seen"])

    server.logout()
    return resultados


def _identificar_cliente(email_remitente: str, db_session):
    """Busca cliente por email del remitente. Pendiente: tabla de mapeo email→cliente."""
    # TODO: implementar mapeo email→cliente en BD
    return None
```

**Step 1-5: TDD habitual**

**Step 6: Commit**

```bash
git commit -m "feat: email intake IMAP (extrae PDFs adjuntos, identifica cliente)"
```

---

## Task 6: Script de polling email (cron/daemon)

**Files:**
- Create: `backend/email_worker.py`

**Objetivo:** Proceso que se ejecuta cada N minutos (via cron o loop infinito), llama a `procesar_emails_nuevos()`, y loguea resultados.

```python
# backend/email_worker.py
import time
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from backend.app.core.database import SessionLocal
from backend.app.services.email_intake import procesar_emails_nuevos

INTERVALO = int(os.getenv("IMAP_POLL_INTERVAL", "300"))
RAIZ_CLIENTES = Path(__file__).parent.parent / "clientes"


def main():
    print(f"Email worker iniciado. Polling cada {INTERVALO}s")
    while True:
        try:
            db = SessionLocal()
            resultados = procesar_emails_nuevos(db, RAIZ_CLIENTES)
            if resultados:
                print(f"Procesados {len(resultados)} adjuntos")
                for r in resultados:
                    print(f"  - {r}")
            db.close()
        except Exception as e:
            print(f"Error en polling: {e}")
        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
```

**Commit:**
```bash
git commit -m "feat: email worker (polling IMAP periodico)"
```

---

## Task 7: Frontend — Setup React + Landing

**Files:**
- Create: `frontend/` (via Vite)
- Create: `frontend/src/pages/Landing.tsx`
- Create: `frontend/src/pages/Login.tsx`

**Step 1: Scaffold React con Vite**

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install tailwindcss @tailwindcss/vite react-router-dom axios
```

**Step 2: Configurar Tailwind**

Editar `frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

Editar `frontend/src/index.css`:
```css
@import "tailwindcss";
```

**Step 3: Implementar Landing page**

Pagina de aterrizaje con:
- Hero: propuesta de valor ("Sube tus facturas. La IA las procesa. Un gestor real supervisa.")
- 3 features destacadas (IA, multicanal, gestor humano)
- Pricing (3 planes)
- CTA: "Empieza gratis" → login

**Step 4: Implementar Login**

Formulario email + password → POST `/api/auth/login` → guardar token en localStorage → redirect a Dashboard

**Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: frontend React (landing page + login)"
```

---

## Task 8: Frontend — Dashboard cliente

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/components/FileUpload.tsx`
- Create: `frontend/src/components/DocumentList.tsx`
- Create: `frontend/src/components/DocumentStatus.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/auth.ts`

**Objetivo:** Dashboard donde el cliente:
1. Ve resumen: facturas procesadas, pendientes de revision, ultimo trimestre
2. Sube PDFs por drag&drop
3. Ve lista de documentos con estado (pendiente/procesando/revision/registrado/error)
4. Descarga modelos fiscales generados

**Componentes:**

`FileUpload.tsx` — zona drag&drop + boton seleccionar. POST multipart a `/api/documentos/subir`

`DocumentList.tsx` — tabla con columnas: archivo, fecha, estado, confianza, acciones. Polling cada 10s para actualizar estados.

`DocumentStatus.tsx` — badge de color segun estado:
- pendiente: gris
- procesando: azul animado
- revision: amarillo (requiere atencion gestor)
- registrado: verde
- error: rojo

`api.ts` — cliente axios con interceptor JWT. Base URL `/api/`.

`auth.ts` — funciones para guardar/leer/borrar token, verificar si esta logueado, logout.

**Step 1-5: Implementar componente a componente, verificar visualmente**

**Step 6: Commit**

```bash
git commit -m "feat: dashboard cliente (upload, lista documentos, estados)"
```

---

## Task 9: Frontend — Panel gestor (cola de revision)

**Files:**
- Create: `frontend/src/pages/GestorDashboard.tsx`
- Create: `frontend/src/components/ColaRevision.tsx`
- Create: `frontend/src/components/DocumentoDetalle.tsx`
- Create: `backend/app/api/gestor.py`

**Objetivo:** Vista exclusiva para rol=gestor donde:
1. Ve todos sus clientes y documentos pendientes de revision
2. Cola de revision: documentos con confianza < 85%, ordenados por fecha
3. Para cada documento dudoso: ver datos extraidos, corregir campos, aprobar/rechazar
4. Al aprobar: dispara registration en FS
5. Calendario fiscal: fechas de modelos trimestrales por cliente

**Backend:** `GET /api/gestor/cola` — devuelve documentos en estado "revision" de todos los clientes del gestor autenticado.

`POST /api/gestor/aprobar/{doc_id}` — recibe correcciones opcionales, ejecuta registration en FS, cambia estado a "registrado".

**Step 1-5: TDD backend + implementar frontend**

**Step 6: Commit**

```bash
git commit -m "feat: panel gestor (cola revision, aprobar/rechazar documentos)"
```

---

## Task 10: Integracion end-to-end + Docker

**Files:**
- Modify: `docker-compose.dev.yml` (agregar backend + frontend)
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `scripts/seed_db.py` (datos iniciales: usuario gestor + clientes existentes)

**Step 1: Crear Dockerfiles**

`backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Actualizar docker-compose.dev.yml**

```yaml
version: "3.8"
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: contabilidad
      POSTGRES_USER: contabilidad
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
    volumes:
      - ./clientes:/app/clientes
      - ./scripts:/app/scripts
      - ./reglas:/app/reglas

  email-worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    command: python backend/email_worker.py
    env_file: .env
    depends_on:
      - db
    volumes:
      - ./clientes:/app/clientes
      - ./scripts:/app/scripts

volumes:
  pgdata:
```

**Step 3: Crear script seed**

```python
# scripts/seed_db.py
"""Crea datos iniciales: usuario gestor + clientes existentes."""
from backend.app.core.database import engine, SessionLocal, Base
from backend.app.core.auth import hash_password
from backend.app.models.usuario import Usuario, Rol
from backend.app.models.cliente import ClienteDB

Base.metadata.create_all(engine)
db = SessionLocal()

# Gestor principal (tu)
gestor = Usuario(
    email="carli@gestoria.com",
    nombre="Carli",
    hashed_password=hash_password("cambiar_password"),
    rol=Rol.ADMIN,
)
db.add(gestor)
db.commit()

# Clientes existentes
clientes = [
    ("PASTORINO COSTA DEL SOL S.L.", "B13995519", "sl", "pastorino-costa-del-sol", 1),
    ("GERARDO GONZALEZ CALLEJON", "12345678A", "autonomo", "gerardo-gonzalez-callejon", 2),
]
for nombre, cif, tipo, carpeta, idempresa in clientes:
    db.add(ClienteDB(
        nombre=nombre, cif=cif, tipo=tipo,
        carpeta=carpeta, idempresa_fs=idempresa,
        gestor_id=gestor.id,
    ))
db.commit()
print("Seed completado")
```

**Step 4: Test E2E manual**

```bash
docker compose -f docker-compose.dev.yml up --build
python scripts/seed_db.py
# Abrir http://localhost:5173
# Login con carli@gestoria.com
# Subir un PDF de prueba
# Verificar que aparece en la lista
# Verificar que el pipeline lo procesa
```

**Step 5: Commit**

```bash
git commit -m "feat: docker-compose completo (backend + email-worker + postgres)"
```

---

## Task 11: Dominio y despliegue produccion

**Files:**
- Create: `deploy/nginx-gestoria.conf`
- Modify: servidor Hetzner (nuevo docker-compose)

**Pasos:**
1. Registrar dominio (ej: `contaflow.es`)
2. DNS: A record → 65.108.60.69
3. Nginx config con SSL (Let's Encrypt)
4. Docker compose produccion en servidor
5. Migrar BD produccion (Alembic)
6. Seed con datos reales

**Commit:**
```bash
git commit -m "feat: configuracion despliegue produccion (nginx + docker)"
```

---

## Resumen de Tasks

| Task | Descripcion | Duracion est. |
|------|-------------|---------------|
| 0 | Setup proyecto (requirements, docker, estructura) | 1 sesion |
| 1 | Modelos BD (usuario, cliente, documento) + tests | 1 sesion |
| 2 | Autenticacion JWT + tests | 1 sesion |
| 3 | API endpoints (auth, documentos) + tests | 1-2 sesiones |
| 4 | Servicio procesador (wrapper SFCE) + tests | 1-2 sesiones |
| 5 | Email intake IMAP + tests | 1 sesion |
| 6 | Email worker (polling daemon) | 1 sesion |
| 7 | Frontend: landing + login | 1-2 sesiones |
| 8 | Frontend: dashboard cliente | 2-3 sesiones |
| 9 | Frontend: panel gestor | 2-3 sesiones |
| 10 | Integracion Docker + seed | 1 sesion |
| 11 | Dominio + despliegue | 1 sesion |

**Total estimado: 13-18 sesiones de trabajo**

## Dependencias entre tasks

```
Task 0 (setup)
  ├── Task 1 (modelos BD)
  │     └── Task 2 (auth JWT)
  │           └── Task 3 (API endpoints)
  │                 ├── Task 4 (procesador SFCE)
  │                 │     └── Task 5 (email intake)
  │                 │           └── Task 6 (email worker)
  │                 └── Task 7 (frontend setup)
  │                       └── Task 8 (dashboard cliente)
  │                             └── Task 9 (panel gestor)
  └── Task 10 (docker integracion) ← depende de 3-9
        └── Task 11 (deploy produccion)
```

**Nota:** Tasks 4-6 (backend) y Tasks 7-9 (frontend) pueden avanzar en paralelo una vez completada Task 3.
