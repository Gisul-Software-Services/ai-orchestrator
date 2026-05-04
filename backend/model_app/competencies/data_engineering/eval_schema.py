"""Pydantic models for Data Engineering evaluation request and response."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    input_data: dict = Field(default_factory=dict)
    expected_output: List[dict] = Field(default_factory=list)  # list of row dicts


class ExecutionResult(BaseModel):
    test_case_index: int = 0
    status: Literal["success", "failed", "timeout", "cancelled", "pending", "running"]
    output_df: Optional[List[dict]] = None
    error_message: Optional[str] = None


class DataEngineeringQuestion(BaseModel):
    id: str
    title: str
    description: str = ""
    question_type: Literal["coding", "subjective"]
    difficulty: str = "medium"
    rubric_items: List[str] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)


class DataEngineeringSubmission(BaseModel):
    code: str = ""           # for coding questions
    answer: str = ""         # for subjective questions
    execution_results: List[ExecutionResult] = Field(default_factory=list)


class DataEngineeringEvalRequest(BaseModel):
    question: DataEngineeringQuestion
    submission: DataEngineeringSubmission
    use_cache: bool = True


class DataEngineeringEvalResponse(BaseModel):
    overall_score: float
    deterministic_score: float
    static_partial_score: float
    ai_score: Optional[float] = None
    final_score: float
    score_reason: str
    per_test_case_results: List[dict] = Field(default_factory=list)
    ai_feedback: dict = Field(default_factory=dict)
    is_correct: bool
