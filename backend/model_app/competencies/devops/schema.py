from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

_DIFFICULTY = Literal["Easy", "Medium", "Hard"]


class DevOpsQuestionRequest(BaseModel):
    job_role: str = "DevOps Engineer"
    experience_years: int = Field(default=2, ge=0, le=50)
    difficulty: _DIFFICULTY = "Medium"
    focus_area: str = Field(default="", max_length=200)
    topics: List[str] = []
    count: int = Field(default=1, ge=1, le=20)
    time_limit: int = Field(default=30, ge=5, le=180)
    mode: Optional[Literal["code", "scenario"]] = None
    org_id: Optional[str] = None

    @property
    def resolved_mode(self) -> str:
        if self.mode:
            return self.mode
        return "code" if self.experience_years <= 5 else "scenario"
