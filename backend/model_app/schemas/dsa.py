from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class DSAQuestionRequest(BaseModel):
    difficulty: str = "Medium"
    topic: str
    concepts: List[str] = []
    languages: List[str] = []
    count: int = 1
    org_id: Optional[str] = None
