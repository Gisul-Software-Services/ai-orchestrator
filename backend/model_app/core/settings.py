from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class ModelSettings(BaseSettings):
    model_name: str = "Qwen/Qwen2.5-7B-Instruct-AWQ"
    assets_dir: Path = Path("/app/assets")
    mongodb_uri: str
    redis_url: str = "redis://redis:6379"
    billing_db_name: str = "aaptor_model"
    batch_size_max: int = 2
    batch_timeout: float = 0.5
    aiml_library_data_preview: bool = True
    aiml_library_preview_max_rows: int = 20
    api_version: str = "2.0.0"
    # 8GB-class GPUs (e.g. RTX 4060 on WSL) need tighter defaults.
    # Keep utilization high enough to fit weights, and keep KV budget bounded.
    vllm_gpu_memory_utilization: float = 0.86
    vllm_max_model_len: int = 1024
    vllm_max_num_seqs: int = 1

    @property
    def aiml_catalog_path(self) -> Path:
        return self.assets_dir / "aiml-data" / "aiml_dataset_catalog.json"

    @property
    def aiml_faiss_path(self) -> Path:
        return self.assets_dir / "aiml-data" / "aiml_faiss.index"

    @property
    def aiml_metadata_path(self) -> Path:
        return self.assets_dir / "aiml-data" / "aiml_catalog_metadata.json"

    @property
    def dsa_enriched_path(self) -> Path:
        return self.assets_dir / "dsa-coding" / "dsa_enriched.json"

    @property
    def dsa_faiss_path(self) -> Path:
        return self.assets_dir / "dsa-coding" / "dsa_faiss.index"

    @property
    def dsa_metadata_path(self) -> Path:
        return self.assets_dir / "dsa-coding" / "dsa_metadata.json"

    class Config:
        env_file = ".env"


_settings: ModelSettings | None = None


def get_settings() -> ModelSettings:
    global _settings
    if _settings is None:
        _settings = ModelSettings()
    return _settings
