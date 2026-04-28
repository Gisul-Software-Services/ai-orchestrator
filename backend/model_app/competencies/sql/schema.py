from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

_DIFFICULTY = Literal["Easy", "Medium", "Hard"]


class SQLQuestionRequest(BaseModel):
    difficulty: _DIFFICULTY = "Medium"
    topic: str = Field(..., min_length=1, max_length=500)
    sql_category: Optional[str] = None  # join, aggregation, window, subquery, select
    count: int = Field(default=1, ge=1, le=20)
    org_id: Optional[str] = None
