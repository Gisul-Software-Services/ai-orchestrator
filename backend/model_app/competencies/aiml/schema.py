from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AIMLGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    use_cache: bool = True
    org_id: Optional[str] = None


class AIMLGenerationResponse(BaseModel):
    problemStatement: str
    dataset: Dict[str, Any]
    expectedApproach: str
    evaluationCriteria: List[str]
    difficulty: str
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1


class AIMLBatchResponse(BaseModel):
    aiml_problems: List[Dict[str, Any]]
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1


class AIMLLibraryRequest(BaseModel):
    topic: str
    difficulty: str
    concepts: List[str] = []
    use_cache: bool = True
    org_id: Optional[str] = None
