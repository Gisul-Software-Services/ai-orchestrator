"""Cloud (AWS) AI Evaluator.

Thin wrapper around the DevOps evaluator — identical logic, separate billing route.
Cloud evaluation uses the same terminal/scenario mode detection and derived-task
scoring as DevOps evaluation.
"""
from __future__ import annotations

from backend.model_app.evaluation.devops_evaluator import get_devops_feedback


def get_cloud_feedback(
    *,
    payload: dict,
    usage_meta: dict | None,
) -> dict:
    """
    Main entry point for Cloud (AWS) evaluation.
    Delegates entirely to get_devops_feedback with route="cloud_evaluation"
    so billing is tracked separately from DevOps evaluation.
    """
    return get_devops_feedback(
        payload=payload,
        usage_meta=usage_meta,
        route="cloud_evaluation",
    )
