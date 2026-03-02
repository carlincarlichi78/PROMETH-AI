"""Script temporal para analizar cobertura de módulos cambiados."""
import json
import subprocess
from pathlib import Path

changed = subprocess.check_output(
    ["git", "diff", "main", "--name-only"], text=True
).splitlines()
changed_sfce = {f for f in changed if f.startswith("sfce/") and f.endswith(".py")}

cov_path = Path("coverage.json")
if not cov_path.exists():
    print("coverage.json no encontrado")
    raise SystemExit(1)

cov = json.loads(cov_path.read_text())
baja = []
for filepath, info in cov["files"].items():
    pct = info["summary"]["percent_covered"]
    if pct < 80:
        norm = filepath.replace("\\", "/")
        for c in changed_sfce:
            if norm.endswith(c) or c in norm:
                baja.append((pct, filepath, info["summary"]["missing_lines"]))
                break

baja.sort()
for pct, f, missing in baja[:15]:
    print(f"{pct:.1f}% (faltan {missing} líneas) {f}")
print(f"\nTotal módulos cambiados con <80%: {len(baja)}")
