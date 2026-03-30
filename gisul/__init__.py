"""
Production-ready import package.

This project’s source code lives under `backend/gisul/`, but runtime and CI
prefer imports like `from gisul...` without relying on `PYTHONPATH`.

This file extends the `gisul` package search path so `gisul.*` resolves to
the existing implementation under `backend/gisul/`.
"""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

_backend_pkg = Path(__file__).resolve().parents[1] / "backend" / "gisul"
if _backend_pkg.exists():
    # Allow `import gisul.main` to resolve to `backend/gisul/main.py`.
    __path__.append(str(_backend_pkg))

