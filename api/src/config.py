"""Configuration settings for the API."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    s3_bucket: str = "recycling-buddy-training"
    s3_endpoint_url: str | None = None  # Set for LocalStack
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None  # For LocalStack
    aws_secret_access_key: str | None = None  # For LocalStack

    model_config = {"env_file": ".env.dev"}


settings = Settings()
