# ─── Etapa 1: builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# System dependencies for native packages (psycopg2, cryptography, pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements first → Docker layer cache (not reinstalled if unchanged)
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ─── Etapa 2: runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Runtime libraries only (libpq for psycopg2, libgomp for PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Application source code
COPY sfce/ ./sfce/
COPY reglas/ ./reglas/
COPY pyproject.toml .

# Install sfce package (so imports work)
RUN pip install --user --no-cache-dir -e . --no-deps

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Integrated health check — Docker marks container unhealthy if it fails
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
    || exit 1

# Start API (OCR + pipeline workers run as asyncio tasks in lifespan)
CMD ["uvicorn", "sfce.api.app:crear_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--log-level", "info"]
