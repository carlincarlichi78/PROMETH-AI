"""Alias importable para migración 021 (el módulo real empieza con dígito)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "mig_021",
    Path(__file__).parent / "021_empresa_slug_backfill.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

ejecutar = _mod.ejecutar
