from __future__ import annotations

from backend.model_app.core.settings import ModelSettings, get_settings
from backend.model_app.core import state as app_state


def get_model():
    return app_state.llm


def get_model_settings() -> ModelSettings:
    return get_settings()
