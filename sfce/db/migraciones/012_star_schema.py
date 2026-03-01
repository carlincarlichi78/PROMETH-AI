"""Migración 012: star schema analítico para módulo Advisor Intelligence."""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")

TABLAS = [
    """CREATE TABLE IF NOT EXISTS eventos_analiticos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        tipo_evento TEXT NOT NULL,
        fecha_evento DATE NOT NULL,
        payload TEXT NOT NULL,
        procesado INTEGER DEFAULT 0,
        creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS ix_evento_empresa_fecha ON eventos_analiticos(empresa_id, fecha_evento)",
    """CREATE TABLE IF NOT EXISTS fact_caja (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        fecha DATE NOT NULL,
        servicio TEXT NOT NULL DEFAULT 'general',
        covers INTEGER DEFAULT 0,
        ventas_totales REAL DEFAULT 0.0,
        ticket_medio REAL DEFAULT 0.0,
        num_mesas_ocupadas INTEGER DEFAULT 0,
        metodo_pago_tarjeta REAL DEFAULT 0.0,
        metodo_pago_efectivo REAL DEFAULT 0.0,
        metodo_pago_otros REAL DEFAULT 0.0,
        evento_id INTEGER REFERENCES eventos_analiticos(id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_fact_caja_empresa_fecha ON fact_caja(empresa_id, fecha)",
    """CREATE TABLE IF NOT EXISTS fact_venta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        fecha DATE NOT NULL,
        servicio TEXT NOT NULL DEFAULT 'general',
        producto_nombre TEXT NOT NULL,
        familia TEXT NOT NULL DEFAULT 'otros',
        qty INTEGER DEFAULT 0,
        pvp_unitario REAL DEFAULT 0.0,
        total REAL DEFAULT 0.0,
        evento_id INTEGER REFERENCES eventos_analiticos(id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_fact_venta_empresa_fecha ON fact_venta(empresa_id, fecha)",
    """CREATE TABLE IF NOT EXISTS fact_compra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        fecha DATE NOT NULL,
        proveedor_nombre TEXT NOT NULL,
        proveedor_cif TEXT,
        familia TEXT NOT NULL DEFAULT 'otros',
        importe REAL DEFAULT 0.0,
        tipo_movimiento TEXT DEFAULT 'compra',
        evento_id INTEGER REFERENCES eventos_analiticos(id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_fact_compra_empresa_fecha ON fact_compra(empresa_id, fecha)",
    "CREATE INDEX IF NOT EXISTS ix_fact_compra_proveedor ON fact_compra(empresa_id, proveedor_nombre)",
    """CREATE TABLE IF NOT EXISTS fact_personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        periodo TEXT NOT NULL,
        empleado_nombre TEXT,
        coste_bruto REAL DEFAULT 0.0,
        coste_ss_empresa REAL DEFAULT 0.0,
        coste_total REAL DEFAULT 0.0,
        dias_baja INTEGER DEFAULT 0,
        evento_id INTEGER REFERENCES eventos_analiticos(id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_fact_personal_empresa_periodo ON fact_personal(empresa_id, periodo)",
    """CREATE TABLE IF NOT EXISTS alertas_analiticas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        alerta_id TEXT NOT NULL,
        severidad TEXT NOT NULL,
        mensaje TEXT NOT NULL,
        valor_actual REAL,
        benchmark_referencia REAL,
        activa INTEGER DEFAULT 1,
        creada_en DATETIME DEFAULT CURRENT_TIMESTAMP,
        resuelta_en DATETIME
    )""",
    "CREATE INDEX IF NOT EXISTS ix_alerta_empresa_activa ON alertas_analiticas(empresa_id, activa)",
]


def ejecutar():
    db_path = os.environ.get("SFCE_DB_PATH", DB_PATH)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for sql in TABLAS:
        cur.execute(sql)
    conn.commit()
    conn.close()
    print("Migracion 012 completada: star schema analitico creado.")


if __name__ == "__main__":
    ejecutar()
