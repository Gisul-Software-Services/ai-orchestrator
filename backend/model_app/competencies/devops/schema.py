from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator


class DevOpsQuestionRequest(BaseModel):
    job_role: str = "DevOps Engineer"
    experience_years: int = 2          # 0-5 → code mode, 5+ → scenario mode
    difficulty: str = "Medium"
    focus_area: str = ""               # e.g. "Docker", "Kubernetes", "Terraform"
    topics: List[str] = []             # specific topics within focus area
    count: int = 1
    time_limit: int = 30               # minutes
    mode: Optional[Literal["code", "scenario"]] = None  # auto-derived if None
    org_id: Optional[str] = None

    @field_validator("difficulty")
    @classmethod
    def normalize_difficulty(cls, v: str) -> str:
        return v.capitalize()

    @property
    def resolved_mode(self) -> str:
        if self.mode:
            return self.mode
        return "code" if self.experience_years <= 5 else "scenario"
