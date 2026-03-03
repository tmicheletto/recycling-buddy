# Model Promotion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `recbuddy.promote` CLI and S3 URI support in `MODEL_ARTIFACT_PATH` so trained models can be promoted to S3 and loaded by the production API automatically.

**Architecture:** A `promote` CLI uploads a local `.safetensors` artifact to a stable S3 key (`artifacts/..._latest.safetensors`) plus a versioned copy. The API lazy-load path is extended to detect `s3://` URIs and download the artifact to `/tmp/model.safetensors` before loading.

**Tech Stack:** boto3 (already in model deps), FastAPI TestClient + `unittest.mock.patch` for API tests, pytest + monkeypatch for model tests.

---

### Task 1: `model/tests/test_promote.py` and `model/recbuddy/promote.py`

**Files:**
- Create: `model/tests/test_promote.py`
- Create: `model/recbuddy/promote.py`

The `conftest.py` already sets dummy AWS env vars for every test via `autouse=True` — no extra fixture needed.

**Step 1: Write the failing tests**

Create `model/tests/test_promote.py`:

```python
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


def test_promote_returns_latest_key(tmp_path: Path) -> None:
    artifact = _make_artifact(tmp_path)
    with patch("recbuddy.promote.boto3.client") as mock_boto:
        mock_boto.return_value = MagicMock()
        result = promote(artifact=artifact, s3_bucket=_BUCKET)
    assert result == _LATEST_KEY
```

**Step 2: Run tests to verify they fail**

```bash
cd model && uv run pytest tests/test_promote.py -v
```

Expected: `ImportError` — `recbuddy.promote` does not exist yet.

**Step 3: Implement `model/recbuddy/promote.py`**

```python
"""Promote a trained model artifact to S3.

Uploads under two S3 keys:
  - artifacts/efficientnet_b0_recycling_latest.safetensors  (stable, for API)
  - artifacts/efficientnet_b0_recycling_v{N}.safetensors    (versioned, for history)

Also writes artifacts/latest.json with promotion metadata.

Usage:
    uv run python -m recbuddy.promote \
        --artifact artifacts/efficientnet_b0_recycling_v1.safetensors \
        --s3-bucket recycling-buddy-data
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

_LATEST_KEY = "artifacts/efficientnet_b0_recycling_latest.safetensors"
_MANIFEST_KEY = "artifacts/latest.json"


def promote(
    artifact: Path,
    s3_bucket: str,
    s3_endpoint_url: Optional[str] = None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    region_name: str = "us-east-1",
) -> str:
    """Upload a local artifact to S3 under the stable latest key and a versioned key.

    Args:
        artifact: Path to the local .safetensors file.
        s3_bucket: S3 bucket to upload to.
        s3_endpoint_url: Optional S3 endpoint for LocalStack.
        aws_access_key_id: Optional AWS access key.
        aws_secret_access_key: Optional AWS secret key.
        region_name: AWS region.

    Returns:
        The stable latest S3 key.
    """
    artifact = Path(artifact)
    if not artifact.exists():
        raise FileNotFoundError(f"Artifact not found: {artifact}")

    client = boto3.client(
        "s3",
        endpoint_url=s3_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
    )

    versioned_key = f"artifacts/{artifact.name}"

    logger.info("Uploading to s3://%s/%s", s3_bucket, _LATEST_KEY)
    client.upload_file(str(artifact), s3_bucket, _LATEST_KEY)

    if versioned_key != _LATEST_KEY:
        logger.info("Uploading to s3://%s/%s", s3_bucket, versioned_key)
        client.upload_file(str(artifact), s3_bucket, versioned_key)

    # Derive version from filename, e.g. efficientnet_b0_recycling_v2 -> "v2"
    stem = artifact.stem
    version = stem.rsplit("_v", 1)[-1] if "_v" in stem else stem

    manifest = {
        "version": f"v{version}",
        "artifact_key": versioned_key,
        "latest_key": _LATEST_KEY,
        "promoted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    client.put_object(
        Bucket=s3_bucket,
        Key=_MANIFEST_KEY,
        Body=json.dumps(manifest, indent=2).encode(),
        ContentType="application/json",
    )
    logger.info("Manifest written to s3://%s/%s", s3_bucket, _MANIFEST_KEY)
    logger.info("Promoted: %s -> s3://%s/%s", artifact, s3_bucket, _LATEST_KEY)

    return _LATEST_KEY


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote a trained model artifact to S3."
    )
    parser.add_argument("--artifact", required=True, help="Local .safetensors file")
    parser.add_argument("--s3-bucket", required=True, help="Target S3 bucket")
    parser.add_argument(
        "--s3-endpoint-url", default=None, help="S3 endpoint URL (for LocalStack)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()
    key = promote(
        artifact=Path(args.artifact),
        s3_bucket=args.s3_bucket,
        s3_endpoint_url=args.s3_endpoint_url,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    print(f"Promoted to s3://{args.s3_bucket}/{key}")
```

**Step 4: Run tests to verify they pass**

```bash
cd model && uv run pytest tests/test_promote.py -v
```

Expected: all 5 tests PASS.

**Step 5: Run full model test suite**

```bash
cd model && uv run pytest -v
```

Expected: all tests PASS.

**Step 6: Commit**

```bash
git add model/recbuddy/promote.py model/tests/test_promote.py
git commit -m "feat(model): add recbuddy.promote CLI for S3 artifact promotion"
```

---

### Task 2: `model/Makefile`

**Files:**
- Create: `model/Makefile`

No tests for the Makefile itself. Just write and verify it's correct.

**Step 1: Create `model/Makefile`**

```makefile
.PHONY: train evaluate promote test

ARTIFACT ?= artifacts/efficientnet_b0_recycling_v1.safetensors
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

**Step 2: Verify `make test` works**

```bash
cd model && make test
```

Expected: pytest runs, all tests PASS.

**Step 3: Commit**

```bash
git add model/Makefile
git commit -m "feat(model): add Makefile with train, evaluate, promote, test targets"
```

---

### Task 3: `api/app/services/s3.py` — `download_artifact` method

**Files:**
- Modify: `api/app/services/s3.py`
- Create: `api/tests/test_s3_service.py`

**Step 1: Write the failing test**

Create `api/tests/test_s3_service.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

```bash
cd api && uv run pytest tests/test_s3_service.py -v
```

Expected: `AttributeError: 'S3Service' object has no attribute 'download_artifact'`.

**Step 3: Add `download_artifact` to `api/app/services/s3.py`**

Add this method to the `S3Service` class, after `upload_training_image`:

```python
def download_artifact(self, s3_key: str, local_path: str) -> None:
    """Download a model artifact from S3 to a local path.

    Args:
        s3_key: S3 object key to download.
        local_path: Local filesystem path to write to.
    """
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading s3://%s/%s to %s", self.bucket, s3_key, local_path)
    self.client.download_file(self.bucket, s3_key, local_path)
    logger.info("Download complete: %s", local_path)
```

Note: `Path` is not imported in `s3.py` yet — add `from pathlib import Path` at the top.

**Step 4: Run tests to verify they pass**

```bash
cd api && uv run pytest tests/test_s3_service.py -v
```

Expected: both tests PASS.

**Step 5: Run full API test suite**

```bash
cd api && uv run pytest -v
```

Expected: all tests PASS.

**Step 6: Commit**

```bash
git add api/app/services/s3.py api/tests/test_s3_service.py
git commit -m "feat(api): add S3Service.download_artifact for model artifact fetch"
```

---

### Task 4: `api/app/main.py` — s3:// URI resolution in lazy-load

**Files:**
- Modify: `api/app/main.py`
- Modify: `api/tests/test_predict_endpoint.py`

**Step 1: Write the failing tests**

Add these two tests to the bottom of `api/tests/test_predict_endpoint.py`:

```python
def test_predict_downloads_artifact_when_path_is_s3_uri(
    monkeypatch, mock_model: MagicMock, valid_jpeg_bytes: bytes
) -> None:
    """When MODEL_ARTIFACT_PATH is an s3:// URI, artifact is downloaded before load."""
    monkeypatch.setattr(app.state, "model", None, raising=False)
    monkeypatch.setattr(app.state, "model_lock", asyncio.Lock(), raising=False)
    monkeypatch.setattr(
        settings,
        "model_artifact_path",
        "s3://recycling-buddy-data/artifacts/efficientnet_b0_recycling_latest.safetensors",
    )
    with patch("app.main.s3_service.download_artifact") as mock_download, patch(
        "app.main.ClassificationModel.from_artifact", return_value=mock_model
    ):
        client = TestClient(app)
        response = client.post(
            "/predict",
            files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
    assert response.status_code == 200
    mock_download.assert_called_once_with(
        "artifacts/efficientnet_b0_recycling_latest.safetensors",
        "/tmp/model.safetensors",
    )


def test_predict_does_not_download_when_path_is_local(
    monkeypatch, mock_model: MagicMock, valid_jpeg_bytes: bytes
) -> None:
    """When MODEL_ARTIFACT_PATH is a local path, no S3 download is attempted."""
    monkeypatch.setattr(app.state, "model", None, raising=False)
    monkeypatch.setattr(app.state, "model_lock", asyncio.Lock(), raising=False)
    monkeypatch.setattr(settings, "model_artifact_path", "/some/local/model.safetensors")
    with patch("app.main.s3_service.download_artifact") as mock_download, patch(
        "app.main.ClassificationModel.from_artifact", return_value=mock_model
    ):
        client = TestClient(app)
        client.post(
            "/predict",
            files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
    mock_download.assert_not_called()
```

The existing imports at the top of `test_predict_endpoint.py` already include `patch`, `asyncio`, `MagicMock`, `monkeypatch` and `settings` — check whether `settings` is imported; if not, add:

```python
from app.config import settings
```

**Step 2: Run tests to verify they fail**

```bash
cd api && uv run pytest tests/test_predict_endpoint.py::test_predict_downloads_artifact_when_path_is_s3_uri tests/test_predict_endpoint.py::test_predict_does_not_download_when_path_is_local -v
```

Expected: both FAIL — `s3_service` has no `download_artifact` call in main.py yet (actually `download_artifact` was added in Task 3, but the URI resolution logic in `main.py` doesn't exist).

**Step 3: Add `_resolve_artifact_path` and update the lazy-load block in `api/app/main.py`**

Add this helper function just before the `predict` route (after the S3Service initialisation, around line 63):

```python
def _resolve_artifact_path(path: str) -> str:
    """Return a local path to the model artifact.

    If *path* is an ``s3://`` URI, downloads the artifact to
    ``/tmp/model.safetensors`` and returns that path.  Otherwise returns
    *path* unchanged.

    Args:
        path: ``MODEL_ARTIFACT_PATH`` setting value.

    Returns:
        Absolute local filesystem path to the artifact.
    """
    if not path.startswith("s3://"):
        return path
    without_scheme = path[len("s3://"):]
    _bucket, _, key = without_scheme.partition("/")
    local_path = "/tmp/model.safetensors"
    s3_service.download_artifact(key, local_path)
    return local_path
```

Then update the lazy-load block inside `predict` (around line 157–163). Replace:

```python
                    request.app.state.model = await run_in_threadpool(
                        ClassificationModel.from_artifact,
                        settings.model_artifact_path,
                    )
```

With:

```python
                    artifact_path = await run_in_threadpool(
                        _resolve_artifact_path,
                        settings.model_artifact_path,
                    )
                    request.app.state.model = await run_in_threadpool(
                        ClassificationModel.from_artifact,
                        artifact_path,
                    )
```

**Step 4: Run the new tests to verify they pass**

```bash
cd api && uv run pytest tests/test_predict_endpoint.py::test_predict_downloads_artifact_when_path_is_s3_uri tests/test_predict_endpoint.py::test_predict_does_not_download_when_path_is_local -v
```

Expected: both PASS.

**Step 5: Run full API test suite**

```bash
cd api && uv run pytest -v
```

Expected: all tests PASS.

**Step 6: Commit**

```bash
git add api/app/main.py api/tests/test_predict_endpoint.py
git commit -m "feat(api): resolve s3:// MODEL_ARTIFACT_PATH by downloading artifact at load time"
```

---

### Task 5: `api/task-definition.json` — set production `MODEL_ARTIFACT_PATH`

**Files:**
- Modify: `api/task-definition.json`

No tests — this is infrastructure config.

**Step 1: Update `api/task-definition.json`**

In the `environment` array, add:

```json
{
  "name": "MODEL_ARTIFACT_PATH",
  "value": "s3://recycling-buddy-data/artifacts/efficientnet_b0_recycling_latest.safetensors"
}
```

The full `environment` array becomes:

```json
"environment": [
  {
    "name": "ENVIRONMENT",
    "value": "TEST"
  },
  {
    "name": "S3_BUCKET",
    "value": "recycling-buddy-data"
  },
  {
    "name": "AWS_REGION",
    "value": "ap-southeast-2"
  },
  {
    "name": "MODEL_ARTIFACT_PATH",
    "value": "s3://recycling-buddy-data/artifacts/efficientnet_b0_recycling_latest.safetensors"
  }
]
```

**Step 2: Verify JSON is valid**

```bash
python3 -c "import json; json.load(open('api/task-definition.json'))" && echo "valid"
```

Expected: `valid`

**Step 3: Commit**

```bash
git add api/task-definition.json
git commit -m "feat(infra): set MODEL_ARTIFACT_PATH to s3:// URI in ECS task definition"
```

---

### Task 6: Lint and type-check

**Step 1: Lint and format the model package**

```bash
cd model && uv run ruff check recbuddy/promote.py && uv run ruff format recbuddy/promote.py --check
```

Fix any issues, then re-run.

**Step 2: Lint and format the API changes**

```bash
cd api && uv run ruff check app/ && uv run ruff format app/ --check
```

Fix any issues, then re-run.

**Step 3: Type-check the API**

```bash
cd api && uv run ty check
```

Expected: no errors. If `ty` flags the `s3://` string parse or the `Path` import, fix the types rather than suppressing.

**Step 4: Commit any lint/type fixes**

```bash
git add -p
git commit -m "fix: lint and type errors in promote and s3:// artifact resolution"
```

---

### Task 7: Update `model/README.md`

**Files:**
- Modify: `model/README.md`

**Step 1: Add Promotion section after Evaluation**

Add after the `## Evaluation` section:

```markdown
## Promotion

After evaluating a satisfactory artifact, promote it to S3:

```bash
cd model
make promote ARTIFACT=artifacts/efficientnet_b0_recycling_v1.safetensors
```

Or directly:

```bash
uv run python -m recbuddy.promote \
    --artifact artifacts/efficientnet_b0_recycling_v1.safetensors \
    --s3-bucket recycling-buddy-data
```

This uploads the artifact to two S3 keys:
- `artifacts/efficientnet_b0_recycling_latest.safetensors` — the stable key the API uses
- `artifacts/efficientnet_b0_recycling_v{N}.safetensors` — versioned copy for history

It also writes `artifacts/latest.json` with version and timestamp metadata.

The next ECS deploy will pick up the new artifact automatically on first `/predict` request.
```

**Step 2: Commit**

```bash
git add model/README.md
git commit -m "docs(model): add Promotion section to README"
```
