from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator


class CloudQuestionRequest(BaseModel):
    job_role: str = "Cloud Engineer"
    experience_years: int = 2          # <=5 → code mode, >5 → scenario mode
    difficulty: str = "Medium"
    aws_service: str = ""              # e.g. "s3", "ec2", "lambda", "iam"
    concepts: List[str] = []           # specific concepts e.g. ["bucket policy", "versioning"]
    count: int = 1
    time_limit: int = 30               # minutes
    mode: Optional[Literal["code", "scenario"]] = None  # auto-derived if None
    org_id: Optional[str] = None

    @field_validator("difficulty")
    @classmethod
    def normalize_difficulty(cls, v: str) -> str:
        return v.capitalize()

    @field_validator("aws_service")
    @classmethod
    def normalize_service(cls, v: str) -> str:
        return v.lower().strip()

    @property
    def resolved_mode(self) -> str:
        if self.mode:
            return self.mode
        return "code" if self.experience_years <= 5 else "scenario"
