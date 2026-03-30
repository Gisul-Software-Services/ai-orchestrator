"""
DEPRECATED SHIM — use ``uvicorn gisul.main:app`` instead.

Kept for backward compatibility only. Remove after confirming no external callers.
"""

from __future__ import annotations

import warnings

from gisul.main import app  # noqa: F401


def __getattr__(name: str):
    warnings.warn(
        f"Accessing '{name}' via qwen_model_server_script_multiple is deprecated. "
        "Import from gisul.engine.core directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    import gisul.engine.core as _core

    return getattr(_core, name)
