"""Unit tests for S3Service."""

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_download_artifact_calls_download_file(tmp_path: Path) -> None:
    from app.services.s3 import S3Service

    with patch("app.services.s3.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client

        service = S3Service(bucket="my-bucket")
        local_path = str(tmp_path / "model.safetensors")
        service.download_artifact("artifacts/model.safetensors", local_path)

    mock_client.download_file.assert_called_once_with(
        "my-bucket", "artifacts/model.safetensors", local_path
    )


def test_download_artifact_creates_parent_directory(tmp_path: Path) -> None:
    from app.services.s3 import S3Service

    with patch("app.services.s3.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client

        service = S3Service(bucket="my-bucket")
        local_path = str(tmp_path / "nested" / "dir" / "model.safetensors")
        service.download_artifact("artifacts/model.safetensors", local_path)

    assert (tmp_path / "nested" / "dir").exists()
