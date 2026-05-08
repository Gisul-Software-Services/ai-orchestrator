"""Pydantic models for SQL AI evaluation request and response."""
from __future__ import annotations

from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class TestResult(BaseModel):
    passed: bool
    # Accept both string (JSON-encoded) and list (structured) for outputs
    user_output: Union[str, List[Any]] = ""
    expected_output: Union[str, List[Any]] = ""
    error: Optional[str] = None

    @field_validator("user_output", "expected_output", mode="before")
    @classmethod
    def normalize_output(cls, v):
        """Accept string, list, or None — normalize to string for backward compat."""
        if v is None:
            return ""
        if isinstance(v, (list, dict)):
            import json
            return json.dumps(v)
        return str(v)


class SQLEvaluationRequest(BaseModel):
    question_id: str
    question_description: str
    user_query: str
    reference_query: str = ""
    max_marks: float
    schemas: dict[str, Any] = Field(default_factory=dict)
    test_result: TestResult
    order_sensitive: bool = False
    difficulty: str = "medium"
    section: str = ""
    use_cache: bool = True


class CriterionScore(BaseModel):
    score: float
    weight: float
    feedback: str


class ImprovementSuggestion(BaseModel):
    suggestion: str = ""
    resources: list[str] = Field(default_factory=list)
    practice_exercises: list[str] = Field(default_factory=list)
    estimated_time: str = ""


class AreaOfImprovement(BaseModel):
    skill: str = ""
    current_level: str = ""
    gap_analysis: str = ""
    priority: str = ""
    improvement_suggestions: list[ImprovementSuggestion] = Field(default_factory=list)


class SQLAIFeedback(BaseModel):
    question_id: str
    section: str = ""
    question_type: Literal["SQL"] = "SQL"
    score: float
    max_marks: float
    percentage: float
    criteria_scores: dict[str, CriterionScore]
    feedback: dict[str, Any]
    answer_log: dict[str, Any]
    areas_of_improvement: list[dict[str, Any]] = Field(default_factory=list)
    benchmarking: dict[str, Any] = Field(default_factory=dict)
    insights: dict[str, Any] = Field(default_factory=dict)
    flags: dict[str, Any] = Field(default_factory=dict)
    evaluation_version: str = "2.2.0"
    ai_generated: bool = True
