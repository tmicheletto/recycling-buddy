"""Tests for the promote module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from recbuddy.promote import promote

_BUCKET = "test-bucket"


def _make_artifact(tmp_path: Path) -> Path:
    artifact = tmp_path / "model.safetensors"
    artifact.write_bytes(b"fake-weights")
    return artifact


def _make_training_metadata(tmp_path: Path) -> Path:
    meta = {
        "epochs": 30,
        "val_accuracy": 0.9142,
        "seed": 42,
        "num_classes": 48,
        "timestamp": "20260303T120000Z",
    }
    meta_path = tmp_path / "training_run_20260303T120000Z.json"
    meta_path.write_text(json.dumps(meta))
    return meta_path


@pytest.fixture()
def artifact_dir(tmp_path: Path) -> Path:
    """Directory with a model artifact and training metadata sidecar."""
    _make_artifact(tmp_path)
    _make_training_metadata(tmp_path)
    return tmp_path


def test_promote_raises_if_artifact_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        promote(artifact=tmp_path / "missing.safetensors", s3_bucket=_BUCKET)


def test_promote_uploads_artifact_to_versioned_prefix(artifact_dir: Path) -> None:
    artifact = artifact_dir / "model.safetensors"
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {}
        mock_boto.return_value = mock_client
        promote(artifact=artifact, s3_bucket=_BUCKET, version="0.1.0")
    mock_client.upload_file.assert_any_call(
        str(artifact), _BUCKET, "artifacts/0.1.0/model.safetensors"
    )


def test_promote_uploads_manifest_to_versioned_prefix(artifact_dir: Path) -> None:
    artifact = artifact_dir / "model.safetensors"
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {}
        mock_boto.return_value = mock_client
        promote(artifact=artifact, s3_bucket=_BUCKET, version="0.1.0")
    put_call = mock_client.put_object.call_args
    assert put_call.kwargs["Key"] == "artifacts/0.1.0/manifest.json"
    manifest = json.loads(put_call.kwargs["Body"])
    assert manifest["version"] == "0.1.0"
    assert manifest["artifact_key"] == "artifacts/0.1.0/model.safetensors"
    assert "promoted_at" in manifest["promotion"]


def test_promote_manifest_includes_training_metadata(artifact_dir: Path) -> None:
    artifact = artifact_dir / "model.safetensors"
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {}
        mock_boto.return_value = mock_client
        promote(artifact=artifact, s3_bucket=_BUCKET, version="0.1.0")
    manifest = json.loads(mock_client.put_object.call_args.kwargs["Body"])
    assert manifest["training"]["epochs"] == 30
    assert manifest["training"]["val_accuracy"] == 0.9142
    assert manifest["training"]["seed"] == 42


def test_promote_errors_if_version_already_exists(artifact_dir: Path) -> None:
    artifact = artifact_dir / "model.safetensors"
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "artifacts/0.1.0/model.safetensors"}]
        }
        mock_boto.return_value = mock_client
        with pytest.raises(ValueError, match="already exists"):
            promote(artifact=artifact, s3_bucket=_BUCKET, version="0.1.0")


def test_promote_returns_versioned_s3_uri(artifact_dir: Path) -> None:
    artifact = artifact_dir / "model.safetensors"
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {}
        mock_boto.return_value = mock_client
        result = promote(artifact=artifact, s3_bucket=_BUCKET, version="0.1.0")
    assert result == "s3://test-bucket/artifacts/0.1.0/model.safetensors"


def test_promote_does_not_upload_latest_alias(artifact_dir: Path) -> None:
    artifact = artifact_dir / "model.safetensors"
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {}
        mock_boto.return_value = mock_client
        promote(artifact=artifact, s3_bucket=_BUCKET, version="0.1.0")
    for c in mock_client.upload_file.call_args_list:
        assert "latest" not in c.args[2]
