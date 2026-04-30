"""Pydantic models for DevOps and Cloud AI evaluation request."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class EngineResponse(BaseModel):
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""


class ValidationSignals(BaseModel):
    passed: bool = False
    question_score: Optional[int] = None
    max_score: Optional[int] = None
    reasons: List[str] = Field(default_factory=list)


class TerminalHistoryEntry(BaseModel):
    command: str = ""
    output: str = ""


class DevOpsQuestion(BaseModel):
    id: str
    title: str
    description: str = ""
    kind: str = ""
    difficulty: str = ""
    instructions: str = ""
    constraints: List[str] = Field(default_factory=list)
    hints: List[str] = Field(default_factory=list)
    expected_submission_contains: List[str] = Field(default_factory=list)
    expected_exit_code: Optional[int] = None
    expected_stdout_contains: List[str] = Field(default_factory=list)
    forbidden_stderr_regex: Optional[str] = None


class DevOpsSubmission(BaseModel):
    answer: str = ""
    terminal_history: List[TerminalHistoryEntry] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    engine_response: Optional[EngineResponse] = None
    validation_signals: Optional[ValidationSignals] = None


class DevOpsEvalRequest(BaseModel):
    question: DevOpsQuestion
    submission: DevOpsSubmission
    use_cache: bool = True


class CloudEvalRequest(BaseModel):
    """Identical fields to DevOpsEvalRequest; kept as a separate model for
    schema clarity and future divergence."""
    question: DevOpsQuestion
    submission: DevOpsSubmission
    use_cache: bool = True
