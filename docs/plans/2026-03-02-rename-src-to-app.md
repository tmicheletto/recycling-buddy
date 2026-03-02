# Rename api/src/ to api/app/ Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename the `api/src/` directory to `api/app/` and update every reference across the codebase in a single atomic commit.

**Architecture:** Pure rename — no logic changes. `git mv` the directory, then update all import statements, patch strings, Dockerfile, docker-compose, and a CI comment. All changes land in one commit so git history never has a broken state.

**Tech Stack:** Python (FastAPI), Docker, GitHub Actions

---

### Task 1: Rename directory and update all references

**Files:**
- Rename: `api/src/` → `api/app/`
- Modify: `api/app/main.py` (was `api/src/main.py`)
- Modify: `api/app/guidelines.py` (was `api/src/guidelines.py`)
- Modify: `api/app/inference.py` (was `api/src/inference.py`)
- Modify: `api/tests/test_inference.py`
- Modify: `api/tests/test_guidelines.py`
- Modify: `api/tests/test_predict_endpoint.py`
- Modify: `api/tests/test_labels.py`
- Modify: `api/tests/test_upload.py`
- Modify: `api/tests/test_advice_endpoint.py`
- Modify: `api/tests/test_labels_data.py`
- Modify: `api/Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `.github/workflows/api-ci.yml`

> Note: TDD doesn't apply here — this is a pure rename. The verification step is running the existing test suite to confirm nothing broke.

**Step 1: Rename the directory**

```bash
git -C /Users/tim/code/recycling-buddy mv api/src api/app
```

Expected: `api/app/` now exists with all files inside (`main.py`, `config.py`, `guidelines.py`, `inference.py`, `labels.py`, `__init__.py`, `services/`).

**Step 2: Update imports in `api/app/main.py`**

Replace all `from src.` with `from app.`:

```python
# Lines 17-21 — change from:
from src.config import settings
from src.guidelines import AdviceRecord, GuidelinesService
from src.inference import ClassificationModel
from src.labels import ALL_LABELS, ALL_LABELS_LIST
from src.services.s3 import S3Service

# To:
from app.config import settings
from app.guidelines import AdviceRecord, GuidelinesService
from app.inference import ClassificationModel
from app.labels import ALL_LABELS, ALL_LABELS_LIST
from app.services.s3 import S3Service
```

**Step 3: Update import in `api/app/guidelines.py`**

```python
# Change from:
from src.config import settings

# To:
from app.config import settings
```

**Step 4: Update import in `api/app/inference.py`**

```python
# Change from:
from src.labels import ALL_LABELS_LIST

# To:
from app.labels import ALL_LABELS_LIST
```

**Step 5: Update `api/tests/test_inference.py`**

```python
# Change from:
from src.inference import CategoryPrediction, ClassificationModel, ClassificationResult
from src.labels import ALL_LABELS_LIST

# To:
from app.inference import CategoryPrediction, ClassificationModel, ClassificationResult
from app.labels import ALL_LABELS_LIST
```

**Step 6: Update `api/tests/test_guidelines.py`**

```python
# Change from:
from src.guidelines import AdviceRecord, GuidelinesService
from src.labels import ALL_LABELS_LIST

# To:
from app.guidelines import AdviceRecord, GuidelinesService
from app.labels import ALL_LABELS_LIST
```

Also update the two `monkeypatch.setattr` patch strings in that file:

```python
# Change from:
monkeypatch.setattr("src.guidelines.settings", ...)

# To:
monkeypatch.setattr("app.guidelines.settings", ...)
```

**Step 7: Update `api/tests/test_predict_endpoint.py`**

```python
# Change from:
from src.inference import CategoryPrediction, ClassificationResult
from src.main import app

# To:
from app.inference import CategoryPrediction, ClassificationResult
from app.main import app
```

**Step 8: Update `api/tests/test_labels.py`**

```python
# Change from:
from src.labels import ALL_LABELS
from src.main import app

# To:
from app.labels import ALL_LABELS
from app.main import app
```

**Step 9: Update `api/tests/test_upload.py`**

```python
# Change from:
from src.main import app

# To:
from app.main import app
```

Also update the three `patch()` strings in that file:

```python
# Change from:
patch("src.main.s3_service.upload_training_image")

# To:
patch("app.main.s3_service.upload_training_image")
```

**Step 10: Update `api/tests/test_advice_endpoint.py`**

```python
# Change from:
from src.guidelines import AdviceRecord
from src.inference import CategoryPrediction, ClassificationResult
from src.main import app

# To:
from app.guidelines import AdviceRecord
from app.inference import CategoryPrediction, ClassificationResult
from app.main import app
```

**Step 11: Update `api/tests/test_labels_data.py`**

```python
# Change from:
from src.labels import ALL_LABELS, ALL_LABELS_LIST, is_s3_safe, is_valid_label

# To:
from app.labels import ALL_LABELS, ALL_LABELS_LIST, is_s3_safe, is_valid_label
```

**Step 12: Update `api/Dockerfile`**

```dockerfile
# Change from:
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# To:
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 13: Update `docker-compose.yml`**

Two changes:

```yaml
# Volume mount — change from:
- ./api/src:/app/src

# To:
- ./api/app:/app/app
```

```yaml
# Uvicorn command — change from:
command: uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# To:
command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Step 14: Update `.github/workflows/api-ci.yml`**

```yaml
# Change from:
# TODO: Fix ty configuration for src-layout

# To:
# TODO: Fix ty configuration for app-layout
```

**Step 15: Run the test suite to verify**

```bash
cd /Users/tim/code/recycling-buddy/api && uv run pytest
```

Expected: 50 passed. If any tests fail, fix the import references before committing — do not proceed to step 16 with failures.

**Step 16: Commit atomically**

```bash
git -C /Users/tim/code/recycling-buddy add api/ docker-compose.yml .github/workflows/api-ci.yml
git -C /Users/tim/code/recycling-buddy commit -m "refactor(api): rename src/ to app/

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
