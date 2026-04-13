from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings


class GatewaySettings(BaseSettings):
    mongodb_uri: str
    admin_api_key: str = ""
    billing_db_name: str = "aaptor_model"
    organization_db_name: str = "organization_db"
    model_service_url: str = "http://model-service:7001"
    redis_url: str = "redis://redis:6379"
    allowed_origins: list[str] = ["*"]
    require_verified_org_for_generation: bool = True
    rate_limit_per_org: int = 20
    model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    api_version: str = "2.0.0"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _parse_allowed_origins(cls, v):
        if v is None or v == "":
            return ["*"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s == "*":
                return ["*"]
            return [x.strip() for x in s.split(",") if x.strip()]
        return v

    class Config:
        env_file = ".env"


_settings: GatewaySettings | None = None


def get_settings() -> GatewaySettings:
    global _settings
    if _settings is None:
        _settings = GatewaySettings()
    return _settings
