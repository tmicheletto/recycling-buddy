"""Tests for the promote module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from recbuddy.promote import _LATEST_KEY, _MANIFEST_KEY, promote

_BUCKET = "test-bucket"


def _make_artifact(tmp_path: Path, name: str = "efficientnet_b0_recycling_v1.safetensors") -> Path:
    artifact = tmp_path / name
    artifact.write_bytes(b"fake-weights")
    return artifact


def test_promote_raises_if_artifact_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        promote(artifact=tmp_path / "missing.safetensors", s3_bucket=_BUCKET)


def test_promote_uploads_to_latest_key(tmp_path: Path) -> None:
    artifact = _make_artifact(tmp_path)
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        promote(artifact=artifact, s3_bucket=_BUCKET)
    mock_client.upload_file.assert_any_call(str(artifact), _BUCKET, _LATEST_KEY)


def test_promote_uploads_versioned_key(tmp_path: Path) -> None:
    artifact = _make_artifact(tmp_path, "efficientnet_b0_recycling_v3.safetensors")
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        promote(artifact=artifact, s3_bucket=_BUCKET)
    versioned_key = "artifacts/efficientnet_b0_recycling_v3.safetensors"
    mock_client.upload_file.assert_any_call(str(artifact), _BUCKET, versioned_key)


def test_promote_writes_manifest(tmp_path: Path) -> None:
    artifact = _make_artifact(tmp_path, "efficientnet_b0_recycling_v2.safetensors")
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        promote(artifact=artifact, s3_bucket=_BUCKET)
    kw = mock_client.put_object.call_args.kwargs
    assert kw["Bucket"] == _BUCKET
    assert kw["Key"] == _MANIFEST_KEY
    manifest = json.loads(kw["Body"])
    assert manifest["version"] == "v2"
    assert "promoted_at" in manifest
    assert "artifact_key" in manifest
    assert manifest["latest_key"] == _LATEST_KEY


def test_promote_returns_latest_key(tmp_path: Path) -> None:
    artifact = _make_artifact(tmp_path)
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_boto.return_value = MagicMock()
        result = promote(artifact=artifact, s3_bucket=_BUCKET)
    assert result == _LATEST_KEY
