from __future__ import annotations

from backend.model_app.core.settings import ModelSettings, get_settings
from backend.model_app.engine import core as eng


def get_model():
    return eng.llm


def get_model_settings() -> ModelSettings:
    return get_settings()
