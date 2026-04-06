"""
Optional tabular preview rows for AIML *library* responses.

Library datasets normally ship metadata + load_code only. When enabled, we fetch a
small head() via sklearn's fetch_openml (same contract as catalog load_code) so the
frontend can render a table. Skips large catalogs to avoid heavy downloads.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


def load_catalog_entry(catalog_id: str) -> dict[str, Any] | None:
    """Return one AIML catalog row by ``id`` (e.g. ``openml-telco-churn``)."""
    try:
        from backend.model_app.core.settings import get_settings
    except ImportError:
        return None
    path = get_settings().assets_dir / "aiml-data" / "aiml_dataset_catalog.json"
    if not path.is_file():
        logger.warning("AIML catalog file missing: %s", path)
        return None
    with open(path, encoding="utf-8") as f:
        catalog = json.load(f)
    if not isinstance(catalog, list):
        return None
    for row in catalog:
        if isinstance(row, dict) and row.get("id") == catalog_id:
            return row
    return None


def preview_catalog_by_id(catalog_id: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    """
    Load catalog entry and return preview rows (same rules as ``try_library_preview_rows``).

    Returns ``(rows, None)`` on success, or ``(None, reason_code)`` on failure.
    """
    entry = load_catalog_entry(catalog_id)
    if not entry:
        return None, "not_found"
    if not _preview_enabled():
        return None, "preview_disabled"
    rows = try_library_preview_rows(entry)
    if rows:
        return rows, None
    load_code = str(entry.get("load_code") or "")
    if "fetch_openml" not in load_code:
        return None, "openml_only"
    return None, "fetch_failed_or_too_large"


def _preview_enabled() -> bool:
    try:
        from backend.model_app.core.settings import get_settings

        return bool(get_settings().aiml_library_data_preview)
    except Exception:
        v = os.environ.get("AIML_LIBRARY_DATA_PREVIEW", "true").strip().lower()
        return v not in ("0", "false", "no", "off")


def _max_rows() -> int:
    try:
        from backend.model_app.core.settings import get_settings

        return max(1, min(500, int(get_settings().aiml_library_preview_max_rows)))
    except Exception:
        try:
            return max(1, min(100, int(os.environ.get("AIML_LIBRARY_PREVIEW_MAX_ROWS", "15"))))
        except ValueError:
            return 15


def _max_catalog_rows() -> int:
    """Skip preview if catalog ``size`` reports more rows than this (avoids huge OpenML pulls)."""
    try:
        from backend.model_app.core.settings import get_settings

        return max(1, int(get_settings().aiml_library_preview_max_catalog_rows))
    except Exception:
        try:
            return max(5_000, int(os.environ.get("AIML_LIBRARY_PREVIEW_MAX_CATALOG_ROWS", "30000")))
        except ValueError:
            return 30_000


def _estimated_row_count(matched: dict[str, Any]) -> int | None:
    s = str(matched.get("size") or "").replace(",", "")
    m = re.search(r"(\d+)\s*rows", s, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{1,9})", s)
    return int(m.group(1)) if m else None


def _df_to_records(df: Any, max_rows: int) -> list[dict[str, Any]]:
    sub = df.head(max_rows)
    try:
        return json.loads(sub.to_json(orient="records", date_format="iso"))
    except Exception:
        out: list[dict[str, Any]] = []
        for _, row in sub.iterrows():
            rec: dict[str, Any] = {}
            for k, v in row.items():
                rec[str(k)] = _jsonify_cell(v)
            out.append(rec)
        return out


def _jsonify_cell(v: Any) -> Any:
    try:
        import numpy as np
    except ImportError:
        np = None  # type: ignore

    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if np is not None:
        if isinstance(v, getattr(np, "integer", ())):
            return int(v)
        if isinstance(v, getattr(np, "floating", ())):
            x = float(v)
            return None if math.isnan(x) or math.isinf(x) else x
        if isinstance(v, np.ndarray):
            return v.tolist()
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    return v


def try_library_preview_rows(matched: dict[str, Any]) -> list[dict[str, Any]] | None:
    """
    Return JSON-serializable row dicts for UI, or None if disabled / unsafe / failed.
    """
    if not _preview_enabled():
        return None
    est = _estimated_row_count(matched)
    cap = _max_catalog_rows()
    if est is not None and est > cap:
        logger.info(
            "AIML library preview skipped: catalog ~%s rows > limit %s (%s)",
            est,
            cap,
            matched.get("id"),
        )
        return None

    load_code = matched.get("load_code") or ""
    if not isinstance(load_code, str) or not load_code.strip():
        return None

    try:
        from sklearn.datasets import fetch_openml
    except ImportError as e:
        logger.warning("AIML library preview skipped: sklearn not available (%s)", e)
        return None

    mr = _max_rows()

    m = re.search(r"data_id\s*=\s*(\d+)", load_code)
    if m:
        try:
            did = int(m.group(1))
            data = fetch_openml(data_id=did, as_frame=True, parser="auto")
            return _df_to_records(data.frame, mr)
        except Exception as e:
            logger.warning(
                "AIML library OpenML data_id preview failed (%s): %s",
                matched.get("id"),
                e,
            )
            return None

    m = re.search(r"fetch_openml\s*\(\s*['\"]([^'\"]+)['\"]", load_code)
    if m:
        name = m.group(1)
        vm = re.search(r"version\s*=\s*(\d+)", load_code)
        ver: int | str = int(vm.group(1)) if vm else "active"
        try:
            data = fetch_openml(name=name, version=ver, as_frame=True, parser="auto")
            return _df_to_records(data.frame, mr)
        except Exception as e:
            logger.warning(
                "AIML library OpenML name=%s preview failed (%s): %s",
                name,
                matched.get("id"),
                e,
            )
            return None

    return None
