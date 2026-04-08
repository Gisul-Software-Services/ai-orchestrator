"""
DEPRECATED SHIM — use ``uvicorn backend.model_app.main:app`` instead.

Kept for backward compatibility only. Remove after confirming no external callers.
"""

from __future__ import annotations

import warnings

from backend.model_app.main import app  # noqa: F401


def __getattr__(name: str):
    warnings.warn(
        f"Accessing '{name}' via qwen_model_server_script_multiple is deprecated. "
        "Import from backend.model_app.core.app, backend.model_app.core.state, "
        "or backend.model_app.services.* directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    from backend.model_app.core import app as _appmod
    from backend.model_app.core import state as _state
    from backend.model_app.prompts import aiml as _prompt_aiml
    from backend.model_app.prompts import dsa as _prompt_dsa
    from backend.model_app.prompts import generation as _prompt_generation
    from backend.model_app.prompts import mcq as _prompt_mcq
    from backend.model_app.schemas import aiml as _schema_aiml
    from backend.model_app.schemas import dsa as _schema_dsa
    from backend.model_app.schemas import generation as _schema_generation
    from backend.model_app.services import aiml as _aiml
    from backend.model_app.services import batching as _batching
    from backend.model_app.services import cache as _cache
    from backend.model_app.services import dsa as _dsa
    from backend.model_app.services import generation as _generation
    from backend.model_app.services import jobs as _jobs
    from backend.model_app.services import mcq as _mcq
    from backend.model_app.services import model as _model
    from backend.model_app.services import system as _system

    modules = (
        _appmod,
        _state,
        _aiml,
        _batching,
        _cache,
        _dsa,
        _generation,
        _jobs,
        _mcq,
        _model,
        _system,
        _prompt_aiml,
        _prompt_dsa,
        _prompt_generation,
        _prompt_mcq,
        _schema_aiml,
        _schema_dsa,
        _schema_generation,
    )
    for module in modules:
        if hasattr(module, name):
            return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
