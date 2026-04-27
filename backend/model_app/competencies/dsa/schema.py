from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

_DIFFICULTY = Literal["Easy", "Medium", "Hard"]


class DSAQuestionRequest(BaseModel):
    difficulty: _DIFFICULTY = "Medium"
    topic: str = Field(..., min_length=1, max_length=500)
    concepts: List[str] = []
    languages: List[str] = []
    count: int = Field(default=1, ge=1, le=20)
    org_id: Optional[str] = None
