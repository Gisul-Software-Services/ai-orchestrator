"""Application settings from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import json

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_assets_dir() -> Path:
    """
    Prefer repo-root ``assets/``, then ``backend/assets/``.
    """
    core_dir = Path(__file__).resolve().parent
    gisul_dir = core_dir.parent
    backend_dir = gisul_dir.parent
    repo_root = backend_dir.parent
    for candidate in (repo_root / "assets", backend_dir / "assets"):
        if candidate.is_dir():
            return candidate
    return repo_root / "assets"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    model_name: str = Field(
        default="Qwen/Qwen2.5-7B-Instruct",
        description="Hugging Face model id",
    )

    assets_dir: Path = Field(
        default_factory=_default_assets_dir,
        description="Root directory for dsa-coding/ and aiml-data/",
        validation_alias=AliasChoices("ASSETS_DIR", "assets_dir"),
    )

    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI",
        validation_alias=AliasChoices("MONGODB_URI", "mongodb_uri"),
    )
    billing_db_name: str = Field(
        default="gisul_billing",
        description="MongoDB database for usage_logs and api_keys",
        validation_alias=AliasChoices("BILLING_DB_NAME", "billing_db_name"),
    )
    organization_db_name: str = Field(
        default="organization_db",
        description="Read-only Aaptor database containing organizations collection",
        validation_alias=AliasChoices("ORGANIZATION_DB_NAME", "organization_db_name"),
    )

    batch_size_max: int = Field(default=2, ge=1)
    batch_timeout: float = Field(default=0.5, gt=0)

    require_verified_org_for_generation: bool = Field(
        default=False,
        description="Set True in production: POST generate/enrich-dsa require X-Org-Id in organization_db",
        validation_alias=AliasChoices(
            "REQUIRE_VERIFIED_ORG_FOR_GENERATION",
            "require_verified_org_for_generation",
        ),
    )

    api_version: str = Field(
        default="2.0.0",
        description="Stored on usage_logs for auditing",
        validation_alias=AliasChoices("API_VERSION", "api_version"),
    )

    aiml_library_data_preview: bool = Field(
        default=True,
        description="Server-side OpenML row preview for AIML catalog",
        validation_alias=AliasChoices(
            "AIML_LIBRARY_DATA_PREVIEW",
            "aiml_library_data_preview",
        ),
    )
    aiml_library_preview_max_rows: int = Field(
        default=20,
        ge=1,
        le=500,
        validation_alias=AliasChoices(
            "AIML_LIBRARY_PREVIEW_MAX_ROWS",
            "aiml_library_preview_max_rows",
        ),
    )
    aiml_library_preview_max_catalog_rows: int = Field(
        default=30_000,
        ge=1,
        description="Skip preview when catalog declares row count above this threshold",
        validation_alias=AliasChoices(
            "AIML_LIBRARY_PREVIEW_MAX_CATALOG_ROWS",
            "aiml_library_preview_max_catalog_rows",
        ),
    )

    environment: str = Field(
        default="development",
        description="Use production for startup security warnings (does not change API behavior alone)",
        validation_alias=AliasChoices("ENVIRONMENT", "GISUL_ENV", "environment"),
    )

    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("environment", mode="after")
    @classmethod
    def _normalize_environment(cls, v: str) -> str:
        return (v or "development").strip().lower()

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _parse_allowed_origins(cls, v: Any) -> Any:
        if v is None or v == "":
            return ["*"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                try:
                    return json.loads(s)
                except json.JSONDecodeError:
                    pass
            return [x.strip() for x in s.split(",") if x.strip()]
        return v

    @field_validator("assets_dir", mode="before")
    @classmethod
    def _coerce_assets_dir(cls, v: Any) -> Any:
        if v is None or v == "":
            return _default_assets_dir()
        return Path(v).expanduser() if not isinstance(v, Path) else v

    @property
    def dsa_enriched_path(self) -> Path:
        return self.assets_dir / "dsa-coding" / "dsa_enriched.json"

    @property
    def dsa_faiss_path(self) -> Path:
        return self.assets_dir / "dsa-coding" / "dsa_faiss.index"

    @property
    def dsa_metadata_path(self) -> Path:
        return self.assets_dir / "dsa-coding" / "dsa_metadata.json"

    @property
    def aiml_catalog_path(self) -> Path:
        return self.assets_dir / "aiml-data" / "aiml_dataset_catalog.json"

    @property
    def aiml_faiss_path(self) -> Path:
        return self.assets_dir / "aiml-data" / "aiml_faiss.index"

    @property
    def aiml_metadata_path(self) -> Path:
        return self.assets_dir / "aiml-data" / "aiml_catalog_metadata.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
