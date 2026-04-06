from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    import backend.model_app.engine.core as eng

    if hasattr(eng, name):
        return getattr(eng, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
