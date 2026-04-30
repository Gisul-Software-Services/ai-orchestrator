"""Pydantic models for Design AI evaluation request and response."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


_DIFFICULTY = Literal["beginner", "intermediate", "advanced"]


class DesignMetrics(BaseModel):
    """Quantitative metrics extracted from the Penpot design file."""
    total_elements: int = 0
    pages: int = 1
    colors_used: int = 0
    typography_scales: int = 0
    components: int = 0
    has_grid: bool = False
    has_tokens: bool = False
    deliverables_found: List[str] = Field(default_factory=list)
    deliverables_missing: List[str] = Field(default_factory=list)
    # Optional extras Aaptor may send
    reusable_components: int = 0
    color_palette_size: int = 0


class DesignQuestion(BaseModel):
    id: str
    title: str
    description: str = ""
    role: str = "UI/UX Designer"
    difficulty: _DIFFICULTY = "intermediate"
    task_type: str = "design"
    deliverables: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class DesignSubmission(BaseModel):
    design_metrics: DesignMetrics = Field(default_factory=DesignMetrics)
    screenshot_available: bool = False
    # Optional: raw Penpot data or additional context
    extra_context: Optional[str] = None


class DesignEvalRequest(BaseModel):
    question: DesignQuestion
    submission: DesignSubmission
    use_cache: bool = True
