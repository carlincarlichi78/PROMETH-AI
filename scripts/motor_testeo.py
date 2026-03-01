"""Motor de Testeo Automático SFCE — Orquestador."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
import sys

DB_DEFAULT = Path("data/motor_testeo.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    rama_git TEXT,
    commit_hash TEXT,
    tests_total INTEGER DEFAULT 0,
    tests_pass INTEGER DEFAULT 0,
    tests_fail INTEGER DEFAULT 0,
    cobertura_pct REAL DEFAULT 0.0,
    duracion_seg REAL DEFAULT 0.0,
    estado TEXT DEFAULT 'en_progreso'
);

CREATE TABLE IF NOT EXISTS resultados_test (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    test_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    modulo TEXT,
    estado TEXT NOT NULL,
    error_msg TEXT,
    duracion_ms REAL DEFAULT 0.0,
    es_nuevo_fallo INTEGER DEFAULT 0,
    es_regresion INTEGER DEFAULT 0,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
);

CREATE TABLE IF NOT EXISTS fixes_aplicados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    test_id TEXT NOT NULL,
    archivo TEXT NOT NULL,
    descripcion_fix TEXT,
    intentos INTEGER DEFAULT 1,
    exitoso INTEGER DEFAULT 1,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
);

CREATE TABLE IF NOT EXISTS tests_generados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    archivo_test TEXT NOT NULL,
    modulo_cubierto TEXT,
    motivo TEXT,
    lineas_codigo INTEGER DEFAULT 0,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
);

CREATE TABLE IF NOT EXISTS cobertura_modulo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id INTEGER NOT NULL,
    modulo TEXT NOT NULL,
    pct_cobertura REAL DEFAULT 0.0,
    lineas_cubiertas INTEGER DEFAULT 0,
    lineas_totales INTEGER DEFAULT 0,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
);
"""


def _http_post(url: str, json: dict, headers: dict, timeout: int = 10):
    """Wrapper HTTP para facilitar testing con monkeypatch."""
    import json as _json
    import urllib.request
    data = _json.dumps(json).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={**headers, "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        class R:
            status_code = resp.status
            def json(self): return _json.loads(body)
        return R()


def _conectar(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _get_arg(argv: list, flag: str) -> str:
    idx = argv.index(flag)
    return argv[idx + 1]


def cmd_init_sesion(db_path: Path) -> int:
    """Crea las tablas si no existen y abre una nueva sesión. Retorna sesion_id."""
    import subprocess as sp
    conn = _conectar(db_path)
    conn.executescript(SCHEMA)

    try:
        rama = sp.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        commit = sp.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        rama, commit = "unknown", "unknown"

    cur = conn.execute(
        "INSERT INTO sesiones (fecha, rama_git, commit_hash) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), rama, commit),
    )
    conn.commit()
    sesion_id = cur.lastrowid
    conn.close()
    return sesion_id


def cmd_registrar_resultados(db_path: Path, sesion_id: int, reporte_json: Path) -> None:
    """Carga resultados de pytest JSON en SQLite y actualiza la sesión."""
    datos = json.loads(reporte_json.read_text())
    summary = datos.get("summary", {})
    duracion = datos.get("duration", 0.0)

    conn = _conectar(db_path)

    conn.execute(
        """UPDATE sesiones SET tests_total=?, tests_pass=?, tests_fail=?, duracion_seg=?
           WHERE id=?""",
        (
            summary.get("total", 0),
            summary.get("passed", 0),
            summary.get("failed", 0),
            duracion,
            sesion_id,
        ),
    )

    fallos_previos = {
        r["test_id"]
        for r in conn.execute(
            """SELECT DISTINCT test_id FROM resultados_test
               WHERE estado='failed' AND sesion_id < ?""",
            (sesion_id,),
        ).fetchall()
    }

    for test in datos.get("tests", []):
        node_id = test["nodeid"]
        modulo = node_id.split("::")[0].replace("/", ".").replace(".py", "")
        estado = test["outcome"]
        error_msg = None
        if estado == "failed":
            call = test.get("call", {})
            error_msg = call.get("longrepr", "")
        es_regresion = 1 if (estado == "failed" and node_id in fallos_previos) else 0

        conn.execute(
            """INSERT INTO resultados_test
               (sesion_id, test_id, nombre, modulo, estado, error_msg,
                duracion_ms, es_regresion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sesion_id, node_id, node_id, modulo, estado, error_msg,
                test.get("duration", 0.0) * 1000,
                es_regresion,
            ),
        )

    conn.commit()
    conn.close()


def cmd_registrar_cobertura(db_path: Path, sesion_id: int, cobertura_json: Path) -> None:
    datos = json.loads(cobertura_json.read_text())
    conn = _conectar(db_path)

    total_cubiertas = total_lineas = 0
    for archivo, info in datos.get("files", {}).items():
        s = info.get("summary", {})
        pct = s.get("percent_covered", 0.0)
        cubiertas = s.get("covered_lines", 0)
        total = s.get("num_statements", 0)
        conn.execute(
            """INSERT INTO cobertura_modulo
               (sesion_id, modulo, pct_cobertura, lineas_cubiertas, lineas_totales)
               VALUES (?, ?, ?, ?, ?)""",
            (sesion_id, archivo, pct, cubiertas, total),
        )
        total_cubiertas += cubiertas
        total_lineas += total

    pct_global = (total_cubiertas / total_lineas * 100) if total_lineas else 0.0
    conn.execute(
        "UPDATE sesiones SET cobertura_pct=? WHERE id=?",
        (round(pct_global, 2), sesion_id),
    )
    conn.commit()
    conn.close()


def cmd_finalizar_sesion(db_path: Path, sesion_id: int) -> None:
    conn = _conectar(db_path)
    conn.execute("UPDATE sesiones SET estado='completada' WHERE id=?", (sesion_id,))
    conn.commit()
    conn.close()


def cmd_generar_reporte(db_path: Path, sesion_id: int, reportes_dir: Path) -> Path:
    reportes_dir.mkdir(parents=True, exist_ok=True)
    conn = _conectar(db_path)

    sesion = conn.execute("SELECT * FROM sesiones WHERE id=?", (sesion_id,)).fetchone()
    fallos = conn.execute(
        "SELECT * FROM resultados_test WHERE sesion_id=? AND estado='failed'",
        (sesion_id,)
    ).fetchall()
    fixes = conn.execute("SELECT * FROM fixes_aplicados WHERE sesion_id=?", (sesion_id,)).fetchall()
    tests_gen = conn.execute("SELECT * FROM tests_generados WHERE sesion_id=?", (sesion_id,)).fetchall()
    cobertura = conn.execute(
        "SELECT modulo, pct_cobertura FROM cobertura_modulo WHERE sesion_id=? ORDER BY pct_cobertura",
        (sesion_id,)
    ).fetchall()
    conn.close()

    fecha_str = sesion["fecha"][:19].replace(":", "-").replace("T", "_")
    nombre = f"{fecha_str}_sesion_{sesion_id}.html"
    ruta = reportes_dir / nombre

    filas_fallos = "".join(
        f"<tr><td>{f['nombre']}</td><td><pre>{f['error_msg'] or ''}</pre></td>"
        f"<td>{'Si' if f['es_regresion'] else 'No'}</td></tr>"
        for f in fallos
    )
    filas_cob = "".join(
        f"<tr><td>{c[0]}</td><td class=\"{'ok' if c[1]>=80 else 'warn'}\">{c[1]:.1f}%</td></tr>"
        for c in cobertura
    )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Motor de Testeo SFCE - Sesion {sesion_id}</title>
<style>
  body{{font-family:monospace;margin:2rem;background:#0f172a;color:#e2e8f0}}
  h1{{color:#f59e0b}} h2{{color:#94a3b8;border-bottom:1px solid #334155;padding-bottom:.5rem}}
  .kpi{{display:flex;gap:2rem;margin:1rem 0}}
  .kpi div{{background:#1e293b;padding:1rem 2rem;border-radius:.5rem;text-align:center}}
  .kpi .val{{font-size:2rem;font-weight:bold;color:#f59e0b}}
  table{{width:100%;border-collapse:collapse;margin:1rem 0}}
  th{{background:#1e293b;padding:.5rem;text-align:left}}
  td{{padding:.5rem;border-bottom:1px solid #1e293b}}
  pre{{white-space:pre-wrap;font-size:.8rem;color:#f87171;max-height:100px;overflow:auto}}
  .ok{{color:#4ade80}} .warn{{color:#f87171}}
</style>
</head>
<body>
<h1>Motor de Testeo SFCE</h1>
<p>Sesion {sesion_id} - {sesion['fecha'][:19]} - Rama: {sesion['rama_git']} - Commit: {sesion['commit_hash']}</p>
<div class="kpi">
  <div><div class="val">{sesion['tests_total']}</div>Tests totales</div>
  <div><div class="val" style="color:#4ade80">{sesion['tests_pass']}</div>Pasados</div>
  <div><div class="val" style="color:#f87171">{sesion['tests_fail']}</div>Fallidos</div>
  <div><div class="val">{sesion['cobertura_pct']:.1f}%</div>Cobertura</div>
  <div><div class="val" style="color:#60a5fa">{len(fixes)}</div>Fixes aplicados</div>
  <div><div class="val" style="color:#a78bfa">{len(tests_gen)}</div>Tests generados</div>
</div>
<h2>Fallos</h2>
<table><tr><th>Test</th><th>Error</th><th>Regresion</th></tr>{filas_fallos or '<tr><td colspan="3">Sin fallos</td></tr>'}</table>
<h2>Cobertura por modulo</h2>
<table><tr><th>Modulo</th><th>Cobertura</th></tr>{filas_cob or '<tr><td colspan="2">Sin datos</td></tr>'}</table>
</body>
</html>"""

    ruta.write_text(html, encoding="utf-8")
    return ruta


def cmd_push_dashboard(db_path: Path, sesion_id: int, api_url: str, token: str) -> dict:
    """Envía los resultados de la sesión a la API del dashboard SFCE."""
    conn = _conectar(db_path)
    sesion = conn.execute("SELECT * FROM sesiones WHERE id=?", (sesion_id,)).fetchone()
    fallos = conn.execute(
        "SELECT test_id, nombre, modulo, error_msg FROM resultados_test WHERE sesion_id=? AND estado='failed'",
        (sesion_id,)
    ).fetchall()
    cobertura = conn.execute(
        "SELECT modulo, pct_cobertura, lineas_cubiertas, lineas_totales FROM cobertura_modulo WHERE sesion_id=?",
        (sesion_id,)
    ).fetchall()
    conn.close()

    payload = {
        "rama_git": sesion["rama_git"],
        "commit_hash": sesion["commit_hash"],
        "tests_total": sesion["tests_total"],
        "tests_pass": sesion["tests_pass"],
        "tests_fail": sesion["tests_fail"],
        "cobertura_pct": sesion["cobertura_pct"],
        "duracion_seg": sesion["duracion_seg"],
        "estado": sesion["estado"],
        "fallos": [
            {"test_id": f["test_id"], "nombre": f["nombre"],
             "modulo": f["modulo"], "error_msg": f["error_msg"]}
            for f in fallos
        ],
        "cobertura": [
            {"modulo": c["modulo"], "pct_cobertura": c["pct_cobertura"],
             "lineas_cubiertas": c["lineas_cubiertas"],
             "lineas_totales": c["lineas_totales"]}
            for c in cobertura
        ],
    }

    r = _http_post(
        f"{api_url}/api/salud/sesiones",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.json()


def main():
    argv = sys.argv[1:]

    db_path = DB_DEFAULT
    if "--db" in argv:
        db_path = Path(_get_arg(argv, "--db"))

    if "--init-sesion" in argv:
        sesion_id = cmd_init_sesion(db_path)
        print(sesion_id)
        return

    if "--registrar-resultados" in argv:
        sesion_id = int(_get_arg(argv, "--sesion-id"))
        reporte_json = Path(_get_arg(argv, "--reporte-json"))
        cmd_registrar_resultados(db_path, sesion_id, reporte_json)
        return

    if "--registrar-cobertura" in argv:
        sesion_id = int(_get_arg(argv, "--sesion-id"))
        cobertura_json = Path(_get_arg(argv, "--cobertura-json"))
        cmd_registrar_cobertura(db_path, sesion_id, cobertura_json)
        return

    if "--finalizar-sesion" in argv:
        sesion_id = int(_get_arg(argv, "--sesion-id"))
        cmd_finalizar_sesion(db_path, sesion_id)
        return

    if "--generar-reporte" in argv:
        sesion_id = int(_get_arg(argv, "--sesion-id"))
        reportes_dir = Path(_get_arg(argv, "--reportes-dir")) if "--reportes-dir" in argv else Path("data/reportes")
        ruta = cmd_generar_reporte(db_path, sesion_id, reportes_dir)
        print(str(ruta))
        return

    if "--push-dashboard" in argv:
        sesion_id = int(_get_arg(argv, "--sesion-id"))
        api_url = _get_arg(argv, "--api-url") if "--api-url" in argv else "http://localhost:8000"
        token = _get_arg(argv, "--token") if "--token" in argv else ""
        result = cmd_push_dashboard(db_path, sesion_id, api_url, token)
        print(result)
        return

    print("Uso: motor_testeo.py [--db PATH] --init-sesion")


if __name__ == "__main__":
    main()
