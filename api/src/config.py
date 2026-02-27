"""Configuration settings for the API."""

import os
import pathlib

from pydantic_settings import BaseSettings

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """Application settings."""

    s3_bucket: str = "recycling-buddy-training"
    s3_endpoint_url: str | None = None
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    cors_origins: str = "http://localhost:5173"
    model_artifact_path: str = (
        "model/artifacts/efficientnet_b0_recycling_v1.safetensors"
    )
    openai_api_key: str | None = None
    guidelines_data_path: str = str(_PROJECT_ROOT / "data" / "label_to_rny.json")
    guidelines_cache_ttl_seconds: int = 604800  # 1 week

    model_config = {
        "env_file": f"config/.env.{os.getenv('ENVIRONMENT', 'DEV').lower()}",
    }


settings = Settings()
