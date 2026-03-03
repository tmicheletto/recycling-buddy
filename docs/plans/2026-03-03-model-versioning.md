# Model Versioning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace auto-incrementing model version numbers with semver from `model/pyproject.toml`, using versioned S3 prefixes (`artifacts/{version}/`) with per-version manifests for traceability and rollback.

**Architecture:** The model version is defined once in `model/pyproject.toml`. `train.py` outputs `model.safetensors` (no version in filename). `promote.py` reads the version from pyproject.toml, uploads to `artifacts/{version}/model.safetensors` with a manifest, and errors if that version already exists. The API pins to a specific version via `MODEL_ARTIFACT_PATH`.

**Tech Stack:** Python, boto3, safetensors, FastAPI, pytest, toml (stdlib `tomllib`)

---

### Task 1: Simplify train.py output naming

**Files:**
- Modify: `model/recbuddy/train.py:353-356` (artifact naming)
- Modify: `model/recbuddy/train.py:398-410` (remove `_next_version`)
- Test: `model/tests/test_train.py`

**Step 1: Update the artifact-saving test**

There's no existing test for artifact naming, so add one in `model/tests/test_train.py`:

```python
def test_train_saves_artifact_as_model_safetensors(tmp_path: Path) -> None:
    """Final artifact should be named model.safetensors (no version suffix)."""
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()
    # We test the naming by calling the save section directly — but since train()
    # requires S3, we just verify the naming convention via _next_version removal
    # and the artifact path construction.
    expected = output_dir / "model.safetensors"
    # After implementation, train() returns this path
    assert expected.name == "model.safetensors"
```

Actually, since `train()` requires a full S3 dataset, the best approach is to just modify the code and verify via the existing test infrastructure. Skip adding a unit test for naming — the promote tests will cover the end-to-end flow.

**Step 1: Modify train.py to output `model.safetensors`**

In `model/recbuddy/train.py`, replace lines 353-356:

```python
    version = _next_version(output_dir)
    artifact_path = output_dir / f"efficientnet_b0_recycling_v{version}.safetensors"
```

With:

```python
    artifact_path = output_dir / "model.safetensors"
```

**Step 2: Remove `_next_version` function**

Delete the `_next_version` function (lines 398-410) from `model/recbuddy/train.py`.

**Step 3: Run existing tests to verify nothing breaks**

Run: `cd model && uv run pytest tests/test_train.py -v`
Expected: All existing tests PASS (none depend on `_next_version` or the versioned filename)

**Step 4: Commit**

```bash
git add model/recbuddy/train.py
git commit -m "refactor(model): simplify artifact output to model.safetensors

Remove auto-incrementing version from artifact filename. Version now
lives in pyproject.toml and is applied during promotion, not training."
```

---

### Task 2: Rewrite promote.py for versioned S3 prefixes

**Files:**
- Modify: `model/recbuddy/promote.py` (full rewrite)
- Modify: `model/tests/test_promote.py` (full rewrite)

**Step 1: Write the new tests**

Replace `model/tests/test_promote.py` entirely:

```python
"""Tests for the promote module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

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
        "num_classes": 67,
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
```

**Step 2: Run tests to verify they fail**

Run: `cd model && uv run pytest tests/test_promote.py -v`
Expected: FAIL (old promote function has different signature)

**Step 3: Rewrite promote.py**

Replace `model/recbuddy/promote.py` entirely:

```python
"""Promote a trained model artifact to S3.

Uploads to a versioned prefix:
  artifacts/{version}/model.safetensors
  artifacts/{version}/manifest.json

The version is read from pyproject.toml (semver). Errors if the version
already exists in S3 — bump the version in pyproject.toml first.

Usage:
    uv run python -m recbuddy.promote \
        --artifact artifacts/model.safetensors \
        --s3-bucket recycling-buddy-data
"""

import argparse
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

_PYPROJECT_PATH = Path(__file__).parent.parent / "pyproject.toml"


def _read_version(pyproject_path: Path | None = None) -> str:
    """Read the version string from pyproject.toml."""
    import tomllib

    path = pyproject_path or _PYPROJECT_PATH
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def _find_training_metadata(artifact_dir: Path) -> dict | None:
    """Find the most recent training_run_*.json sidecar in artifact_dir."""
    candidates = sorted(artifact_dir.glob("training_run_*.json"), reverse=True)
    if not candidates:
        return None
    return json.loads(candidates[0].read_text())


def _git_sha() -> str | None:
    """Return short git SHA of HEAD, or None if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def promote(
    artifact: Path,
    s3_bucket: str,
    version: str | None = None,
    s3_endpoint_url: Optional[str] = None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    region_name: str = "us-east-1",
) -> str:
    """Upload a local artifact to a versioned S3 prefix with manifest.

    Args:
        artifact: Path to the local model.safetensors file.
        s3_bucket: S3 bucket to upload to.
        version: Semver string. If None, read from pyproject.toml.
        s3_endpoint_url: Optional S3 endpoint for LocalStack.
        aws_access_key_id: Optional AWS access key.
        aws_secret_access_key: Optional AWS secret key.
        region_name: AWS region.

    Returns:
        The full S3 URI of the uploaded artifact.

    Raises:
        FileNotFoundError: If artifact does not exist.
        ValueError: If the version already exists in S3.
    """
    artifact = Path(artifact)
    if not artifact.exists():
        raise FileNotFoundError(f"Artifact not found: {artifact}")

    if version is None:
        version = _read_version()

    client = boto3.client(
        "s3",
        endpoint_url=s3_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
    )

    prefix = f"artifacts/{version}/"
    existing = client.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)
    if existing.get("Contents"):
        raise ValueError(
            f"Version {version} already exists in s3://{s3_bucket}/{prefix}. "
            "Bump the version in pyproject.toml before promoting."
        )

    artifact_key = f"{prefix}model.safetensors"
    logger.info("Uploading to s3://%s/%s", s3_bucket, artifact_key)
    client.upload_file(str(artifact), s3_bucket, artifact_key)

    training_meta = _find_training_metadata(artifact.parent)
    manifest = {
        "version": version,
        "artifact_key": artifact_key,
        "training": {
            "epochs": training_meta.get("epochs") if training_meta else None,
            "val_accuracy": training_meta.get("val_accuracy") if training_meta else None,
            "seed": training_meta.get("seed") if training_meta else None,
            "num_classes": training_meta.get("num_classes") if training_meta else None,
        },
        "promotion": {
            "promoted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "promoted_by": os.environ.get("USER", "unknown"),
            "git_sha": _git_sha(),
        },
    }

    manifest_key = f"{prefix}manifest.json"
    client.put_object(
        Bucket=s3_bucket,
        Key=manifest_key,
        Body=json.dumps(manifest, indent=2).encode(),
        ContentType="application/json",
    )
    logger.info("Manifest written to s3://%s/%s", s3_bucket, manifest_key)

    uri = f"s3://{s3_bucket}/{artifact_key}"
    logger.info("Promoted: %s -> %s", artifact, uri)
    return uri


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote a trained model artifact to S3."
    )
    parser.add_argument(
        "--artifact",
        required=True,
        help="Local model.safetensors file",
    )
    parser.add_argument("--s3-bucket", required=True, help="Target S3 bucket")
    parser.add_argument(
        "--s3-endpoint-url", default=None, help="S3 endpoint URL (for LocalStack)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()
    uri = promote(
        artifact=Path(args.artifact),
        s3_bucket=args.s3_bucket,
        s3_endpoint_url=args.s3_endpoint_url,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    print(f"Promoted to {uri}")
```

**Step 4: Run tests to verify they pass**

Run: `cd model && uv run pytest tests/test_promote.py -v`
Expected: All PASS

**Step 5: Lint**

Run: `cd model && uv run ruff check --fix recbuddy/promote.py tests/test_promote.py && uv run ruff format recbuddy/promote.py tests/test_promote.py`

**Step 6: Commit**

```bash
git add model/recbuddy/promote.py model/tests/test_promote.py
git commit -m "feat(model): rewrite promote.py for versioned S3 prefixes

Upload artifacts to artifacts/{version}/ with per-version manifest.json.
Version comes from pyproject.toml. Errors if version already exists.
Removes _latest alias key and top-level latest.json manifest."
```

---

### Task 3: Update model/Makefile defaults

**Files:**
- Modify: `model/Makefile`

**Step 1: Update the ARTIFACT default and promote target**

Change `model/Makefile`:

```makefile
.PHONY: train evaluate promote test

ARTIFACT ?= artifacts/model.safetensors
S3_BUCKET ?= recycling-buddy-data

train:
	uv run python -m recbuddy.train \
		--s3-bucket $(S3_BUCKET) \
		--output-dir artifacts/ \
		--epochs 30 \
		--seed 42

evaluate:
	uv run python -m recbuddy.evaluate \
		--artifact $(ARTIFACT) \
		--s3-bucket $(S3_BUCKET) \
		--split test

promote:
	uv run python -m recbuddy.promote \
		--artifact $(ARTIFACT) \
		--s3-bucket $(S3_BUCKET)

test:
	uv run pytest
```

**Step 2: Commit**

```bash
git add model/Makefile
git commit -m "chore(model): update Makefile default artifact to model.safetensors"
```

---

### Task 4: Update API config and docker-compose

**Files:**
- Modify: `api/app/config.py:20-22`
- Modify: `docker-compose.yml:14`
- Modify: `api/task-definition.json:34`

**Step 1: Update config.py default**

In `api/app/config.py`, change the `model_artifact_path` default:

```python
    model_artifact_path: str = "model/artifacts/model.safetensors"
```

**Step 2: Update docker-compose.yml**

Change the `MODEL_ARTIFACT_PATH` env var:

```yaml
      - MODEL_ARTIFACT_PATH=/app/model/artifacts/model.safetensors
```

**Step 3: Update task-definition.json**

Change the `MODEL_ARTIFACT_PATH` value:

```json
        {
          "name": "MODEL_ARTIFACT_PATH",
          "value": "s3://recycling-buddy-data/artifacts/0.1.0/model.safetensors"
        }
```

**Step 4: Run API tests to verify nothing breaks**

Run: `cd api && uv run pytest tests/ -v`
Expected: All PASS. The test for S3 URI download (`test_predict_downloads_artifact_when_path_is_s3_uri`) uses `monkeypatch` to set a specific path, so it doesn't depend on the default.

**Step 5: Commit**

```bash
git add api/app/config.py docker-compose.yml api/task-definition.json
git commit -m "chore: update MODEL_ARTIFACT_PATH to versioned naming

Default local path: model/artifacts/model.safetensors
Production S3 URI: s3://recycling-buddy-data/artifacts/0.1.0/model.safetensors"
```

---

### Task 5: Add model version startup logging

**Files:**
- Modify: `api/app/main.py:182-191` (the lazy-load success path)

**Step 1: Write a test for version logging**

Add to `api/tests/test_predict_endpoint.py`:

```python
def test_predict_logs_model_version_on_load(
    monkeypatch, mock_model: MagicMock, valid_jpeg_bytes: bytes, caplog
) -> None:
    """Model version from artifact path is logged on first load."""
    monkeypatch.setattr(app.state, "model", None, raising=False)
    monkeypatch.setattr(app.state, "model_lock", asyncio.Lock(), raising=False)
    monkeypatch.setattr(
        settings,
        "model_artifact_path",
        "s3://recycling-buddy-data/artifacts/0.2.0/model.safetensors",
    )
    with (
        patch("app.main.s3_service.download_artifact"),
        patch("app.main.ClassificationModel.from_artifact", return_value=mock_model),
        caplog.at_level(logging.INFO),
    ):
        client = TestClient(app)
        client.post(
            "/predict",
            files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
    assert any("0.2.0" in record.message for record in caplog.records)
```

Note: add `import logging` to the test file imports.

**Step 2: Run the test to verify it fails**

Run: `cd api && uv run pytest tests/test_predict_endpoint.py::test_predict_logs_model_version_on_load -v`
Expected: FAIL

**Step 3: Add version logging to main.py**

In `api/app/main.py`, after the successful model load (line 191), add version extraction and logging:

```python
                    request.app.state.model = await run_in_threadpool(
                        ClassificationModel.from_artifact,
                        artifact_path,
                    )
                    _version = _extract_model_version(
                        settings.model_artifact_path
                    )
                    logger.info(
                        "Model loaded (version: %s)", _version
                    )
```

Add the helper function near `_resolve_artifact_path`:

```python
def _extract_model_version(path: str) -> str:
    """Extract model version from artifact path.

    Expects paths like ``artifacts/0.2.0/model.safetensors`` or
    ``s3://bucket/artifacts/0.2.0/model.safetensors``.
    Falls back to ``"unknown"`` if version cannot be parsed.
    """
    parts = path.replace("\\", "/").split("/")
    # Find "artifacts" and take the next segment as version
    for i, part in enumerate(parts):
        if part == "artifacts" and i + 1 < len(parts) - 1:
            return parts[i + 1]
    return "unknown"
```

**Step 4: Run the test to verify it passes**

Run: `cd api && uv run pytest tests/test_predict_endpoint.py::test_predict_logs_model_version_on_load -v`
Expected: PASS

**Step 5: Run all API tests**

Run: `cd api && uv run pytest tests/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add api/app/main.py api/tests/test_predict_endpoint.py
git commit -m "feat(api): log model version on lazy load

Extract version from MODEL_ARTIFACT_PATH (e.g. artifacts/0.2.0/model.safetensors)
and log it when the model is first loaded."
```

---

### Task 6: Run full test suite and lint

**Files:** None (verification only)

**Step 1: Run all model tests**

Run: `cd model && uv run pytest -v`
Expected: All PASS

**Step 2: Run all API tests**

Run: `cd api && uv run pytest -v`
Expected: All PASS

**Step 3: Lint and format both components**

Run: `cd model && uv run ruff check --fix . && uv run ruff format .`
Run: `cd api && uv run ruff check --fix . && uv run ruff format .`

**Step 4: Fix any issues and commit if needed**

```bash
git add -u
git commit -m "style: lint and format after model versioning changes"
```
