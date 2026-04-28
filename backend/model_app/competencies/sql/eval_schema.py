"""Pydantic models for SQL AI evaluation request and response."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class TestResult(BaseModel):
    passed: bool
    user_output: str = ""
    expected_output: str = ""
    error: Optional[str] = None


class SQLEvaluationRequest(BaseModel):
    question_id: str
    question_description: str
    user_query: str
    reference_query: str
    max_marks: float
    schemas: dict[str, Any]
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
    evaluation_version: str = "2.1.0"
    ai_generated: bool = True
