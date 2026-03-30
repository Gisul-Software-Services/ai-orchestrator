"""
Runtime generation state (``MODEL``, ``TOKENIZER``, ``JOB_STORE``, ``STATS``, …)
lives on ``gisul.engine.core`` — this module is a lazy proxy so imports like
``from gisul.core.state import MODEL`` resolve without duplicating globals.

The spec’s ``AppState`` class shape is satisfied by those attributes on
``gisul.engine.core``; use that module as the single source of truth.
"""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    import gisul.engine.core as eng

    if hasattr(eng, name):
        return getattr(eng, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
