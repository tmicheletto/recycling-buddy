# Lazy Model Loading Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move model loading out of the FastAPI lifespan and into the first `/predict` request so the API always starts successfully.

**Architecture:** Add `asyncio.Lock` to `app.state` at startup. In `/predict`, use double-checked locking to load the model once on first call — any load failure returns 503 and retries on the next request. Only `api/app/main.py` and `api/tests/test_predict_endpoint.py` change.

**Tech Stack:** FastAPI, asyncio, unittest.mock

---

### Task 1: Write failing tests for lazy loading behaviour

**Files:**
- Modify: `api/tests/test_predict_endpoint.py`

The existing `client` fixture pre-sets `app.state.model = mock_model`, so the lazy-load path is never exercised. Add two new tests: one verifying 503 when the artifact can't load, one verifying the model is loaded and cached on first call.

**Step 1: Add the two new tests at the bottom of `api/tests/test_predict_endpoint.py`**

Add this import at the top of the file (after the existing imports):

```python
from unittest.mock import patch
import asyncio
```

Then add these two tests at the bottom of the file:

```python
# ---------------------------------------------------------------------------
# Lazy loading
# ---------------------------------------------------------------------------


def test_predict_returns_503_when_model_fails_to_load(valid_jpeg_bytes: bytes) -> None:
    """503 is returned when the artifact can't be loaded on first /predict."""
    app.state.model = None
    app.state.model_lock = asyncio.Lock()
    with patch(
        "app.main.ClassificationModel.from_artifact",
        side_effect=FileNotFoundError("no artifact"),
    ):
        client = TestClient(app)
        response = client.post(
            "/predict",
            files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
    assert response.status_code == 503


def test_predict_loads_model_lazily_on_first_request(
    mock_model: MagicMock, valid_jpeg_bytes: bytes
) -> None:
    """Model is loaded from artifact and cached in app.state on first /predict."""
    app.state.model = None
    app.state.model_lock = asyncio.Lock()
    with patch(
        "app.main.ClassificationModel.from_artifact",
        return_value=mock_model,
    ):
        client = TestClient(app)
        response = client.post(
            "/predict",
            files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
    assert response.status_code == 200
    assert app.state.model is mock_model
```

**Step 2: Run the new tests to verify they fail**

```bash
cd /Users/tim/code/recycling-buddy/api && uv run pytest tests/test_predict_endpoint.py::test_predict_returns_503_when_model_fails_to_load tests/test_predict_endpoint.py::test_predict_loads_model_lazily_on_first_request -v
```

Expected: both FAIL — `app.state` has no `model_lock` attribute yet and the lazy-load logic doesn't exist.

---

### Task 2: Implement lazy loading in `api/app/main.py`

**Files:**
- Modify: `api/app/main.py`

**Step 1: Add `import asyncio` to the stdlib imports block**

The file currently starts:
```python
import base64
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator
```

Add `import asyncio` so it becomes:
```python
import asyncio
import base64
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator
```

**Step 2: Replace the lifespan function**

Current lifespan (lines 28–38):
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load the classifier model at startup; release on shutdown."""
    try:
        app.state.model = ClassificationModel.from_artifact(settings.model_artifact_path)
        logger.info("Model loaded and ready for inference")
    except FileNotFoundError as exc:
        logger.warning("Model artifact not found — /predict will return 503: %s", exc)
        app.state.model = None
    app.state.guidelines_service = GuidelinesService()
    yield
```

Replace with:
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise app state; model is loaded lazily on first /predict request."""
    app.state.model = None
    app.state.model_lock = asyncio.Lock()
    app.state.guidelines_service = GuidelinesService()
    yield
```

**Step 3: Replace the model-unavailable guard in `/predict`**

Current guard in `/predict` (lines 158–162):
```python
    if request.app.state.model is None:
        raise HTTPException(
            status_code=503,
            detail="Model artifact not available. Run the training pipeline first.",
        )
```

Replace with:
```python
    if request.app.state.model is None:
        async with request.app.state.model_lock:
            if request.app.state.model is None:
                try:
                    request.app.state.model = await run_in_threadpool(
                        ClassificationModel.from_artifact,
                        settings.model_artifact_path,
                    )
                    logger.info("Model loaded lazily on first /predict request")
                except Exception as exc:
                    logger.warning("Model failed to load: %s", exc)
                    raise HTTPException(
                        status_code=503,
                        detail="Model artifact not available. Run the training pipeline first.",
                    )
```

**Step 4: Run the new tests to verify they pass**

```bash
cd /Users/tim/code/recycling-buddy/api && uv run pytest tests/test_predict_endpoint.py::test_predict_returns_503_when_model_fails_to_load tests/test_predict_endpoint.py::test_predict_loads_model_lazily_on_first_request -v
```

Expected: both PASS.

**Step 5: Run the full test suite to verify nothing regressed**

```bash
cd /Users/tim/code/recycling-buddy/api && uv run pytest
```

Expected: 52 passed (50 existing + 2 new).

**Step 6: Commit**

```bash
git -C /Users/tim/code/recycling-buddy add api/app/main.py api/tests/test_predict_endpoint.py
git -C /Users/tim/code/recycling-buddy commit -m "feat(api): lazy-load model on first /predict request"
```
