from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TopicGenerationRequest(BaseModel):
    assessment_title: str
    job_designation: str
    skills: List[str]
    experience_min: int
    experience_max: int
    experience_mode: str = "corporate"
    num_topics: int = 10
    num_questions: int = 1
    use_cache: bool = True
    org_id: Optional[str] = None


class TopicGenerationResponse(BaseModel):
    topics: List[Dict[str, Any]]
    generation_time_seconds: float
    model: str = "Qwen2.5-7B-Instruct"
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1


class TopicBatchResponse(BaseModel):
    topics: List[Dict[str, Any]]
    generation_time_seconds: float
    model: str = "Qwen2.5-7B-Instruct"
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1


class MCQGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    target_audience: str
    num_questions: int = 1
    request_id: Optional[str] = None
    use_cache: bool = True
    org_id: Optional[str] = None


class MCQGenerationResponse(BaseModel):
    question: str
    options: List[Dict[str, Any]]
    explanation: str
    difficulty: str
    bloomLevel: str
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1


class MCQBatchResponse(BaseModel):
    questions: List[Dict[str, Any]]
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1


class SubjectiveGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    target_audience: str
    num_questions: int = 1
    use_cache: bool = True
    org_id: Optional[str] = None


class SubjectiveGenerationResponse(BaseModel):
    question: str
    expectedAnswer: str
    gradingCriteria: List[str]
    difficulty: str
    bloomLevel: str
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1


class SubjectiveBatchResponse(BaseModel):
    questions: List[Dict[str, Any]]
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1


class CodingGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    language: str = "Python"
    job_role: str = "Software Engineer"
    experience_years: str = "3-5"
    num_questions: int = 1
    use_cache: bool = True
    org_id: Optional[str] = None


class CodingGenerationResponse(BaseModel):
    problemStatement: str
    inputFormat: str
    outputFormat: str
    constraints: List[str]
    examples: List[Dict[str, Any]]
    testCases: List[Dict[str, Any]]
    starterCode: str
    difficulty: str
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1


class CodingBatchResponse(BaseModel):
    coding_problems: List[Dict[str, Any]]
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1


class SQLGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    database_type: str = "PostgreSQL"
    job_role: str = "Software Engineer"
    experience_years: str = "3-5"
    num_questions: int = 1
    use_cache: bool = True
    org_id: Optional[str] = None


class SQLGenerationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    problemStatement: str
    database_schema: Dict[str, Any] = Field(..., alias="schema")
    expectedQuery: str
    explanation: str
    difficulty: str
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1


class SQLBatchResponse(BaseModel):
    sql_problems: List[Dict[str, Any]]
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1
