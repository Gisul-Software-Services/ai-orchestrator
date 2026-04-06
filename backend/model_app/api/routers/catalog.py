"""
Dataset catalog CRUD + FAISS rebuild endpoints (mounted at ``/api/v1``).

Catalog source of truth: ``settings.aiml_catalog_path`` (JSON array).
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from backend.model_app.core.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["catalog"])

REQUIRED_FIELDS = [
    "id",
    "name",
    "source",
    "category",
    "pip_install",
    "import_code",
    "load_code",
    "description",
    "use_case",
    "features_info",
    "target",
    "target_type",
    "size",
    "tags",
    "domain",
    "difficulty",
    "direct_load",
]

ALLOWED_CATEGORIES = {"tabular", "nlp", "cv", "audio", "time-series", "graph"}
ALLOWED_DIFFICULTY = {"Easy", "Medium", "Hard"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def _load_catalog() -> List[Dict[str, Any]]:
    p = get_settings().aiml_catalog_path
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise HTTPException(status_code=500, detail={"error": "catalog_corrupt"})
    return data  # type: ignore[return-value]


def _save_catalog(catalog: List[Dict[str, Any]]) -> None:
    _atomic_write_json(get_settings().aiml_catalog_path, catalog)
    # Invalidate monolith cache if present (best effort).
    try:
        from backend.model_app.engine import core as eng

        if hasattr(eng, "_aiml_catalog_cache"):
            eng._aiml_catalog_cache = None  # type: ignore[attr-defined]
    except Exception:
        pass


def _validate_entry(entry: Dict[str, Any], *, mode: str, existing_ids: set[str]) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    for f in REQUIRED_FIELDS:
        if f not in entry:
            errors[f] = "required"

    if "category" in entry and entry.get("category") not in ALLOWED_CATEGORIES:
        errors["category"] = f"must be one of: {sorted(ALLOWED_CATEGORIES)}"

    if "difficulty" in entry:
        d = entry.get("difficulty")
        if not isinstance(d, list):
            errors["difficulty"] = "must be a list"
        else:
            bad = [x for x in d if x not in ALLOWED_DIFFICULTY]
            if bad:
                errors["difficulty"] = f"invalid values: {bad} (allowed: {sorted(ALLOWED_DIFFICULTY)})"

    if "direct_load" in entry and not isinstance(entry.get("direct_load"), bool):
        errors["direct_load"] = "must be boolean"

    if "tags" in entry and not isinstance(entry.get("tags"), list):
        errors["tags"] = "must be a list"

    if mode == "post":
        cid = entry.get("id")
        if isinstance(cid, str) and cid in existing_ids:
            errors["id"] = "must be unique"

    return errors


@router.get("/catalog")
async def catalog_list():
    return _load_catalog()


@router.get("/catalog/{catalog_id}")
async def catalog_get(catalog_id: str):
    catalog = _load_catalog()
    for e in catalog:
        if str(e.get("id")) == catalog_id:
            return e
    raise HTTPException(status_code=404, detail={"error": "not_found", "id": catalog_id})


@router.post("/catalog")
async def catalog_add(entry: Dict[str, Any]):
    catalog = _load_catalog()
    existing_ids = {str(e.get("id")) for e in catalog if e.get("id") is not None}
    errors = _validate_entry(entry, mode="post", existing_ids=existing_ids)
    if errors:
        raise HTTPException(status_code=422, detail={"error": "validation_error", "fields": errors})
    catalog.append(entry)
    _save_catalog(catalog)
    return {"ok": True, "id": entry.get("id")}


@router.put("/catalog/{catalog_id}")
async def catalog_update(catalog_id: str, entry: Dict[str, Any]):
    catalog = _load_catalog()
    existing_ids = {str(e.get("id")) for e in catalog if e.get("id") is not None}
    errors = _validate_entry(entry, mode="put", existing_ids=existing_ids)
    if errors:
        raise HTTPException(status_code=422, detail={"error": "validation_error", "fields": errors})
    for i, e in enumerate(catalog):
        if str(e.get("id")) == catalog_id:
            # id is immutable in edit mode
            entry = {**entry, "id": catalog_id}
            catalog[i] = entry
            _save_catalog(catalog)
            return {"ok": True, "id": catalog_id}
    raise HTTPException(status_code=404, detail={"error": "not_found", "id": catalog_id})


@router.delete("/catalog/{catalog_id}")
async def catalog_delete(catalog_id: str):
    catalog = _load_catalog()
    new_catalog = [e for e in catalog if str(e.get("id")) != catalog_id]
    if len(new_catalog) == len(catalog):
        raise HTTPException(status_code=404, detail={"error": "not_found", "id": catalog_id})
    _save_catalog(new_catalog)
    return {"ok": True, "id": catalog_id}


def _build_search_text(dataset: dict) -> str:
    parts: list[str] = []
    for k, max_len in [
        ("name", None),
        ("domain", None),
        ("category", None),
        ("use_case", 200),
        ("description", 300),
        ("features_info", 150),
        ("target_type", None),
    ]:
        v = dataset.get(k, "")
        if not v:
            continue
        s = str(v)
        parts.append(s if max_len is None else s[:max_len])
    tags = dataset.get("tags", [])
    if isinstance(tags, list) and tags:
        parts.append(" ".join([str(x) for x in tags]))
    return " ".join(parts)


def _atomic_replace_file(target: Path, write_fn) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
    os.close(fd)
    try:
        write_fn(Path(tmp))
        os.replace(tmp, target)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def _vector_count_from_metadata(meta_path: Path) -> int:
    if not meta_path.exists():
        return 0
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        return len(meta) if isinstance(meta, list) else 0
    except Exception:
        return 0


@router.post("/catalog/faiss/rebuild-aiml")
async def catalog_faiss_rebuild_aiml():
    s = get_settings()
    catalog = _load_catalog()
    try:
        import numpy as np
        import faiss  # type: ignore
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "faiss_unavailable", "detail": str(e)})

    search_texts = [_build_search_text(d) for d in catalog]
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(
        search_texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    dim = int(embeddings.shape[1])
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))

    metadata = [
        {
            "index": i,
            "id": d.get("id", ""),
            "name": d.get("name", ""),
            "source": d.get("source", ""),
            "domain": d.get("domain", ""),
            "tags": d.get("tags", []),
            "difficulty": d.get("difficulty", []),
            "target_type": d.get("target_type", ""),
            "size": d.get("size", ""),
            "direct_load": d.get("direct_load", True),
        }
        for i, d in enumerate(catalog)
    ]

    _atomic_replace_file(s.aiml_faiss_path, lambda p: faiss.write_index(index, str(p)))
    _atomic_write_json(s.aiml_metadata_path, metadata)

    return {"ok": True, "vectors_indexed": int(index.ntotal), "last_rebuilt": _now_iso()}


@router.get("/catalog/faiss/status")
async def catalog_faiss_status():
    s = get_settings()

    def mtime_iso(p: Path) -> str | None:
        if not p.exists():
            return None
        try:
            return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
        except Exception:
            return None

    def count_vectors(index_path: Path, meta_path: Path) -> int:
        if index_path.exists():
            try:
                import faiss  # type: ignore

                idx = faiss.read_index(str(index_path))
                return int(idx.ntotal)
            except Exception:
                return _vector_count_from_metadata(meta_path)
        return _vector_count_from_metadata(meta_path)

    return {
        "aiml": {
            "last_rebuilt": mtime_iso(s.aiml_faiss_path),
            "vector_count": count_vectors(s.aiml_faiss_path, s.aiml_metadata_path),
        },
        "dsa": {
            "last_rebuilt": mtime_iso(s.dsa_faiss_path),
            "vector_count": count_vectors(s.dsa_faiss_path, s.dsa_metadata_path),
        },
    }

