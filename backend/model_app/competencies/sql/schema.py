from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

_DIFFICULTY = Literal["Easy", "Medium", "Hard"]


class SQLQuestionRequest(BaseModel):
    difficulty: _DIFFICULTY = "Medium"
    topic: Optional[str] = Field(default=None, min_length=1, max_length=500)
    sql_category: Optional[str] = None  # join, aggregation, window, subquery, select
    count: int = Field(default=1, ge=1, le=20)
    org_id: Optional[str] = None

    @field_validator("difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, v: str) -> str:
        """Accept any case: easy/EASY/Easy → Easy"""
        if isinstance(v, str):
            return v.strip().capitalize()
        return v

    @field_validator("sql_category", mode="before")
    @classmethod
    def normalize_sql_category(cls, v: str) -> str:
        """Normalize sql_category to lowercase."""
        if isinstance(v, str):
            return v.strip().lower()
        return v
