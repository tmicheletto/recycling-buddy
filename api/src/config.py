"""Configuration settings for the API."""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    s3_bucket: str = "recycling-buddy-training"
    s3_endpoint_url: str | None = None
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    model_config = {
        "env_file": f"config/{os.getenv('ENVIRONMENT', 'DEV').lower()}.env",
    }


settings = Settings()
