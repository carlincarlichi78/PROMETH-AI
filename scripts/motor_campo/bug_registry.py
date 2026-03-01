import sqlite3
import uuid
from pathlib import Path

class BugRegistry:
    def __init__(self, ruta_db: str = "data/motor_campo.db"):
        Path(ruta_db).parent.mkdir(parents=True, exist_ok=True)
        self.ruta_db = ruta_db
        self._crear_tablas()

    def _conn(self):
        return sqlite3.connect(self.ruta_db)

    def _crear_tablas(self):
        with self._conn() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS ejecuciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sesion_id TEXT NOT NULL,
                    escenario_id TEXT NOT NULL,
                    variante_id TEXT NOT NULL,
                    resultado TEXT NOT NULL,
                    duracion_ms INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS bugs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sesion_id TEXT NOT NULL,
                    escenario_id TEXT NOT NULL,
                    variante_id TEXT NOT NULL,
                    fase TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    stack_trace TEXT,
                    fix_intentado TEXT,
                    fix_exitoso BOOLEAN DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def iniciar_sesion(self) -> str:
        return uuid.uuid4().hex[:8]

    def registrar_ejecucion(self, sesion_id, escenario_id, variante_id, resultado, duracion_ms):
        with self._conn() as con:
            con.execute(
                "INSERT INTO ejecuciones (sesion_id,escenario_id,variante_id,resultado,duracion_ms) VALUES (?,?,?,?,?)",
                (sesion_id, escenario_id, variante_id, resultado, duracion_ms)
            )

    def registrar_bug(self, sesion_id, escenario_id, variante_id, fase, descripcion, stack_trace, fix_intentado, fix_exitoso):
        resultado = "bug_arreglado" if fix_exitoso else "bug_pendiente"
        with self._conn() as con:
            con.execute(
                "INSERT INTO bugs (sesion_id,escenario_id,variante_id,fase,descripcion,stack_trace,fix_intentado,fix_exitoso) VALUES (?,?,?,?,?,?,?,?)",
                (sesion_id, escenario_id, variante_id, fase, descripcion, stack_trace, fix_intentado, fix_exitoso)
            )
            con.execute(
                "INSERT INTO ejecuciones (sesion_id,escenario_id,variante_id,resultado,duracion_ms) VALUES (?,?,?,?,?)",
                (sesion_id, escenario_id, variante_id, resultado, 0)
            )

    def stats_sesion(self, sesion_id) -> dict:
        with self._conn() as con:
            rows = con.execute(
                "SELECT resultado, COUNT(*) FROM ejecuciones WHERE sesion_id=? GROUP BY resultado",
                (sesion_id,)
            ).fetchall()
        mapa = {"ok": "ok", "bug_arreglado": "bugs_arreglados", "bug_pendiente": "bugs_pendientes"}
        stats = {"ok": 0, "bugs_arreglados": 0, "bugs_pendientes": 0}
        for resultado, cnt in rows:
            clave = mapa.get(resultado)
            if clave:
                stats[clave] = cnt
        return stats

    def listar_bugs(self, sesion_id) -> list:
        with self._conn() as con:
            rows = con.execute(
                "SELECT escenario_id,variante_id,fase,descripcion,fix_intentado,fix_exitoso,timestamp FROM bugs WHERE sesion_id=? ORDER BY timestamp",
                (sesion_id,)
            ).fetchall()
        return [{"escenario_id": r[0], "variante_id": r[1], "fase": r[2],
                 "descripcion": r[3], "fix_intentado": r[4], "fix_exitoso": bool(r[5]),
                 "timestamp": r[6]} for r in rows]
