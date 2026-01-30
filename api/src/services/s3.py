"""S3 service for uploading training images."""

import uuid
from datetime import datetime, timezone

import boto3


class S3Service:
    """Service for uploading images to S3."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region_name: str = "us-east-1",
    ) -> None:
        """Initialize S3 service.

        Args:
            bucket: S3 bucket name
            endpoint_url: Optional endpoint URL for LocalStack
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            region_name: AWS region name
        """
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

    def upload_training_image(
        self,
        data: bytes,
        label: str,
    ) -> str:
        """Upload image bytes to S3 under label directory.

        Args:
            data: Image bytes
            label: Label for the image (e.g., 'recyclable', 'not_recyclable')

        Returns:
            S3 key where the image was uploaded
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_ext = self._detect_extension(data)
        key = f"{label}/{uuid.uuid4()}_{timestamp}.{file_ext}"

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=f"image/{file_ext}",
        )
        return key

    def _detect_extension(self, data: bytes) -> str:
        """Detect image format from magic bytes.

        Args:
            data: Image bytes

        Returns:
            File extension (jpeg, png, or bin)
        """
        if data[:3] == b"\xff\xd8\xff":
            return "jpeg"
        if data[:4] == b"\x89PNG":
            return "png"
        return "bin"  # fallback
