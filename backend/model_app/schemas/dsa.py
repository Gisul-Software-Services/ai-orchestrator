from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class DSAQuestionRequest(BaseModel):
    difficulty: str
    topic: str
    concepts: List[str] = []
    languages: List[str] = []
    org_id: Optional[str] = None
