"""Reporter HTML — Motor de Escenarios de Campo SFCE."""
import sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime
from scripts.motor_campo.bug_registry import BugRegistry

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Motor Campo SFCE — {sesion_id}</title>
<style>
  body {{ font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 2rem; }}
  h1 {{ color: #f0883e; }} h2 {{ color: #58a6ff; }}
  .ok {{ color: #3fb950; }} .bug_arreglado {{ color: #f0883e; }} .bug_pendiente {{ color: #f85149; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #30363d; padding: 0.5rem 1rem; text-align: left; }}
  th {{ background: #161b22; }}
  .stats {{ display: flex; gap: 2rem; margin: 1rem 0; }}
  .stat {{ background: #161b22; padding: 1rem 2rem; border-radius: 8px; text-align: center; }}
  .stat-num {{ font-size: 2rem; font-weight: bold; }}
</style>
</head>
<body>
<h1>Motor de Escenarios de Campo SFCE</h1>
<p>Sesion: <strong>{sesion_id}</strong> | Fecha: {fecha}</p>
<div class="stats">
  <div class="stat"><div class="stat-num ok">{ok}</div><div>OK</div></div>
  <div class="stat"><div class="stat-num bug_arreglado">{bugs_arreglados}</div><div>Arreglados</div></div>
  <div class="stat"><div class="stat-num bug_pendiente">{bugs_pendientes}</div><div>Pendientes</div></div>
</div>
<h2>Todas las ejecuciones</h2>
{tabla_ejecuciones}
<h2>Bugs detectados</h2>
{tabla_bugs}
</body></html>
"""


class Reporter:
    def __init__(self, registry: BugRegistry, output_dir: str = "reports"):
        self.registry = registry
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _listar_ejecuciones(self, sesion_id: str) -> list:
        """Consulta directa a la tabla ejecuciones (todos los resultados)."""
        with closing(sqlite3.connect(self.registry.ruta_db)) as con:
            rows = con.execute(
                "SELECT escenario_id, variante_id, resultado, duracion_ms, timestamp "
                "FROM ejecuciones WHERE sesion_id=? ORDER BY timestamp",
                (sesion_id,),
            ).fetchall()
        return [
            {"escenario_id": r[0], "variante_id": r[1], "resultado": r[2],
             "duracion_ms": r[3], "timestamp": r[4]}
            for r in rows
        ]

    def generar(self, sesion_id: str) -> str:
        stats = self.registry.stats_sesion(sesion_id)
        bugs = self.registry.listar_bugs(sesion_id)
        ejecuciones = self._listar_ejecuciones(sesion_id)

        # Tabla ejecuciones completa
        filas_ej = ""
        for e in ejecuciones:
            cls = e["resultado"]
            filas_ej += (
                f"<tr class='{cls}'>"
                f"<td>{e['escenario_id']}</td><td>{e['variante_id']}</td>"
                f"<td>{e['resultado']}</td><td>{e['duracion_ms']} ms</td></tr>"
            )
        tabla_ej = (
            f"<table><tr><th>Escenario</th><th>Variante</th>"
            f"<th>Resultado</th><th>Duracion</th></tr>{filas_ej}</table>"
            if filas_ej
            else "<p>Sin ejecuciones en esta sesion.</p>"
        )

        # Tabla bugs
        filas_bugs = ""
        for b in bugs:
            cls = "bug_arreglado" if b["fix_exitoso"] else "bug_pendiente"
            filas_bugs += (
                f"<tr class='{cls}'>"
                f"<td>{b['escenario_id']}</td><td>{b['variante_id']}</td>"
                f"<td>{b['fase']}</td><td>{b['descripcion']}</td>"
                f"<td>{b['fix_intentado'] or '—'}</td>"
                f"<td>{'✓' if b['fix_exitoso'] else '✗'}</td></tr>"
            )
        tabla_bugs = (
            f"<table><tr><th>Escenario</th><th>Variante</th><th>Fase</th>"
            f"<th>Error</th><th>Fix intentado</th><th>Arreglado</th></tr>{filas_bugs}</table>"
            if filas_bugs
            else "<p>Sin bugs en esta sesion.</p>"
        )

        html = PLANTILLA.format(
            sesion_id=sesion_id,
            fecha=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ok=stats["ok"],
            bugs_arreglados=stats["bugs_arreglados"],
            bugs_pendientes=stats["bugs_pendientes"],
            tabla_ejecuciones=tabla_ej,
            tabla_bugs=tabla_bugs,
        )
        ruta = self.output_dir / f"motor_campo_{sesion_id}.html"
        ruta.write_text(html, encoding="utf-8")
        return str(ruta)
