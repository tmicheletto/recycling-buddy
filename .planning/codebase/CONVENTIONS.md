# Coding Conventions

**Analysis Date:** 2026-02-26

## Naming Patterns

**Files:**
- Module files: `lowercase_with_underscores.py` (e.g., `dataset.py`, `train.py`, `inference.py`)
- Test files: `test_<module>.py` (e.g., `test_dataset.py`, `test_predict_endpoint.py`)
- Configuration files: `config.py` in component root
- Service files: Component-specific structure under `src/services/` (e.g., `src/services/s3.py`)

**Functions:**
- All functions use `snake_case` (e.g., `build_model()`, `freeze_backbone()`, `train_one_epoch()`)
- Private/internal functions prefixed with underscore: `_decode()`, `_make_image_dir()`, `_is_valid_image()`
- Async functions follow same naming: `async def predict()`, `async def get_labels()`

**Variables:**
- Local variables: `snake_case` (e.g., `image_bytes`, `logits`, `train_ds`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `_NUM_CLASSES`, `_IMAGENET_MEAN`, `DEFAULT_DATA_DIR`)
- Class attributes: `snake_case` (e.g., `self.s3_bucket`, `self.data_dir`)
- Protected attributes (internal to class): underscore prefix (e.g., `self._s3`, `self._net`)

**Types:**
- Type hints: Use PEP 604 syntax (`str | None`, `list[str]`, `dict[str, int]`) for Python 3.11+
- BaseModel subclasses: PascalCase (e.g., `HealthResponse`, `PredictionResponse`, `UploadRequest`)
- Dataclass names: PascalCase, use `@dataclass(frozen=True)` for immutable value objects (e.g., `CategoryPrediction`, `ClassificationResult`)

## Code Style

**Formatting:**
- Line length: 88 characters (enforced by Ruff)
- Indentation: 4 spaces
- No trailing whitespace

**Linting:**
- Tool: Ruff
- Config location: `model/pyproject.toml` and `api/pyproject.toml`
- Selected rules: `["E", "F", "I"]` (errors, pyflakes, isort)
  - E: PEP 8 style errors
  - F: PyFlakes (undefined names, duplicate imports)
  - I: isort (import sorting)

**Type Checking:**
- Type hints used extensively throughout codebase
- Return type hints always present on functions: `def func() -> ReturnType:`
- Function arguments with type hints
- API: Pyright configuration in `api/pyrightconfig.json` and `api/pyproject.toml`

## Import Organization

**Order:**
1. Standard library imports (`import os`, `from pathlib import Path`)
2. Third-party imports (`import torch`, `from fastapi import FastAPI`)
3. Local/relative imports (`from src.dataset import WasteDataset`, `from src.labels import ALL_LABELS`)

**Path Aliases:**
- Model: Uses absolute imports from `src` (e.g., `from src.dataset import WasteDataset`)
- API: Uses absolute imports from `src` (e.g., `from src.main import app`, `from src.config import settings`)
- No relative imports used (no `from ..module import`)

**Example from `api/src/main.py`:**
```python
import base64
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from starlette.concurrency import run_in_threadpool

from src.config import settings
from src.inference import ClassificationModel
from src.labels import ALL_LABELS, ALL_LABELS_LIST
from src.services.s3 import S3Service
```

## Error Handling

**Patterns:**
- Use specific exception types in `except` clauses, not bare `except:`
- Chain exceptions with `from exc` to preserve stack traces
- Examples:
  - `except ClientError as exc: raise RuntimeError(...) from exc` (in `model/src/dataset.py`)
  - `except ValueError as exc: raise HTTPException(...) from exc` (in `api/src/main.py`)
  - `except (UnidentifiedImageError, Exception) as exc: raise ValueError(...) from exc` (in `api/src/inference.py`)

**HTTP Errors in FastAPI:**
- Use `HTTPException(status_code=code, detail="message")` for API errors
- Common status codes:
  - 400: Bad request (invalid input, missing file)
  - 422: Validation error (Pydantic model validation failure)
  - 500: Internal server error
- Errors logged before raising: `logger.error(...)`

**Validation:**
- Use Pydantic `@field_validator` decorators for model-level validation
- Example from `api/src/main.py`:
  ```python
  @field_validator("label")
  @classmethod
  def label_must_be_valid(cls, v: str) -> str:
      if v not in ALL_LABELS:
          raise ValueError(f"Invalid label '{v}'. Use GET /labels for valid options.")
      return v
  ```

## Logging

**Framework:** Python standard library `logging`

**Patterns:**
- Logger defined at module level: `logger = logging.getLogger(__name__)`
- Configuration in main modules:
  - `api/src/main.py`: `logging.basicConfig(level=logging.INFO)`
- Structured logging for events: JSON format with contextual metadata
  - Example from `api/src/main.py`:
    ```python
    logger.info(
        json.dumps({
            "event": "prediction",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "predicted_label": result.top_prediction.label,
            "confidence": result.top_prediction.confidence,
        })
    )
    ```
- Use `%s` string formatting in logs (not f-strings): `logger.info("Model loaded: %s", artifact_path)`
- Error logging: `logger.error("Prediction error: %s", exc)`

## Comments

**When to Comment:**
- Module-level docstrings: Every module has a docstring explaining purpose
- Complex algorithms: Explain non-obvious logic (e.g., transform pipelines in `inference.py`)
- Design constraints: Document why a pattern is used, especially for concurrency/safety
- TODOs/FIXMEs: Included in code with actionable context

**Docstring Format (Google/numpy-style):**
- Module docstring at top with overview
- Class docstrings with Args and purpose
- Function docstrings with description, Args, Returns, Raises sections
- Example from `model/src/dataset.py`:
  ```python
  def get_splits(
      self,
      val_frac: float = 0.15,
      test_frac: float = 0.15,
      seed: int = 42,
  ) -> tuple[Dataset, Dataset, Dataset]:
      """Return (train, val, test) datasets derived from the downloaded images.

      Args:
          val_frac: Fraction of images reserved for validation.
          test_frac: Fraction of images reserved for testing.
          seed: Random seed for reproducible splits.

      Returns:
          Tuple of (train_dataset, val_dataset, test_dataset).

      Raises:
          FileNotFoundError: If ``data_dir`` is empty or does not exist.
      """
  ```

**Comment Style:**
- Markdown-formatted section headers in code: `# ---------------------------------------------------------------------------`
- Marks logical sections in files (tests organized into sections)
- Example from test files: Separates test groups for fixtures, success paths, error paths

## Function Design

**Size:** Functions are kept focused and small
- Typical range: 10-30 lines for implementation functions
- Test functions: 5-15 lines (often single assertion or small setup)
- Helpers start with underscore and do single responsibility

**Parameters:**
- Type hints on every parameter
- Use keyword-only arguments for clarity when needed
- Example: `def __init__(self, s3_bucket: str, data_dir: Path = DEFAULT_DATA_DIR, endpoint_url: Optional[str] = None, ...) -> None:`

**Return Values:**
- Explicit return type hints on all functions
- Return tuples for multiple values: `tuple[Dataset, Dataset, Dataset]`
- Return dataclasses for complex results: `ClassificationResult` with `top_prediction` and `alternatives`
- Return None explicitly for functions that don't return: `-> None`

**Async Functions:**
- Used in FastAPI routes: `async def predict(...) -> PredictionResponse:`
- Thread-pool offloading for CPU-bound work: `await run_in_threadpool(request.app.state.model.predict, image_bytes)`
- Return type annotated: `async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:`

## Module Design

**Exports:**
- Main API endpoints exported from `api/src/main.py` (FastAPI app instance)
- Configuration exported as singleton: `settings = Settings()` in `api/src/config.py`
- Dataclasses exported from module level for type hints in other modules

**Barrel Files:**
- Not used; imports are explicit module-to-module
- Example: `from src.dataset import WasteDataset` not `from src import WasteDataset`

**Class Design:**
- Value objects are frozen dataclasses: `@dataclass(frozen=True)` (e.g., `CategoryPrediction`, `ClassificationResult`)
- Service classes (e.g., `ClassificationModel`) are not frozen; they manage state (the model instance)
- Pydantic BaseModel used for request/response serialization (e.g., `HealthResponse`, `PredictionResponse`)
- Use `@classmethod` for factory constructors: `ClassificationModel.from_artifact(path)`

---

*Convention analysis: 2026-02-26*
