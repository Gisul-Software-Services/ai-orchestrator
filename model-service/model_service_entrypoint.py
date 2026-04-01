from __future__ import annotations

import os

from backend_app.main import app as core_app


def _assets_dir() -> str:
    return os.environ.get("ASSETS_DIR", "/app/assets")


@core_app.on_event("startup")
def _startup_preload_indexes() -> None:
    try:
        os.environ.setdefault("ASSETS_DIR", _assets_dir())
        from backend_app.engine import core as eng

        if hasattr(eng, "_load_faiss_index"):
            eng._load_faiss_index()
        if hasattr(eng, "_load_aiml_faiss"):
            eng._load_aiml_faiss()
    except Exception:
        pass


app = core_app
