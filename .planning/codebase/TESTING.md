# Testing Patterns

**Analysis Date:** 2026-02-26

## Test Framework

**Runner:**
- pytest 9.0+ (specified in model and api pyproject.toml)
- Location: `model/pyproject.toml` and `api/pyproject.toml` in `[dependency-groups] dev`

**Assertion Library:**
- pytest's built-in assertions (no external library)
- Pattern: `assert condition` with optional message

**Additional Libraries:**
- `pytest-cov`: Code coverage reporting (model only)
- `pytest-asyncio`: Async test support (api only)
- `httpx`: HTTP client for testing FastAPI endpoints (api)
- `unittest.mock`: Mocking framework (built-in)

**Run Commands:**
```bash
# Model tests
cd model && pytest                          # Run all model tests
cd model && pytest tests/test_dataset.py   # Run specific test file
cd model && pytest -v                       # Verbose output

# API tests
cd api && uv run pytest                    # Run all API tests
cd api && uv run pytest tests/test_predict_endpoint.py -v  # Specific file

# All tests (from root)
make test                                   # Runs model, api, and ui tests
```

**Coverage:**
```bash
cd model && pytest --cov=src --cov-report=term-missing  # Model coverage
```

## Test File Organization

**Location:**
- Model tests: `model/tests/` (co-located with source in `model/src/`)
- API tests: `api/tests/` (co-located with source in `api/src/`)
- Pattern: Test files live alongside source, not in separate directory

**Naming:**
- Format: `test_<module>.py` (e.g., `test_dataset.py`, `test_train.py`, `test_inference.py`)
- Test functions: `test_<feature>` (e.g., `test_get_splits_returns_three_datasets`, `test_predict_returns_200_with_valid_jpeg`)
- Parametric tests: Use descriptive names (no pytest.mark.parametrize used in observed code)

**Structure:**
```
model/tests/
├── conftest.py          # Fixtures shared across all model tests
├── test_dataset.py      # Tests for WasteDataset
├── test_train.py        # Tests for training pipeline
├── test_evaluate.py     # Tests for evaluation
└── __init__.py          # Package marker

api/tests/
├── __init__.py
├── test_inference.py    # Tests for ClassificationModel
├── test_predict_endpoint.py  # Integration tests for /predict route
├── test_upload.py       # Tests for /upload route
├── test_labels.py       # Tests for /labels endpoint
└── test_labels_data.py  # Tests for labels data module
```

## Test Structure

**Suite Organization:**
Tests are organized with clear section headers and fixtures. Example from `model/tests/test_dataset.py`:

```python
"""Unit tests for WasteDataset.

Tests must FAIL before implementation is complete (TDD — constitution Principle II).
S3 interactions are fully mocked — no real AWS calls are made.
"""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from PIL import Image
from src.dataset import WasteDataset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image_dir(root: Path, labels: list[str], images_per_label: int = 5) -> None:
    """Populate root/<label>/<n>.jpg with tiny solid-colour images."""
    for label in labels:
        label_dir = root / label
        label_dir.mkdir(parents=True)
        for i in range(images_per_label):
            img = Image.new("RGB", (32, 32), color=(i * 10, 50, 100))
            img.save(label_dir / f"{i}.jpg")

# ---------------------------------------------------------------------------
# WasteDataset.get_splits
# ---------------------------------------------------------------------------

LABELS = ["cardboard", "plastic-bottles-containers", "glass-bottles-jars"]
IMAGES_PER_LABEL = 10

@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    _make_image_dir(tmp_path, LABELS, IMAGES_PER_LABEL)
    return tmp_path

@pytest.fixture
def dataset(data_dir: Path) -> WasteDataset:
    ds = WasteDataset(s3_bucket="test-bucket", data_dir=data_dir)
    return ds

def test_get_splits_returns_three_datasets(dataset: WasteDataset) -> None:
    train, val, test = dataset.get_splits(seed=0)
    assert train is not None
    assert val is not None
    assert test is not None
```

**Patterns:**
- **Setup**: Fixtures provide test data (see fixtures section below)
- **Execution**: Call the function/endpoint being tested
- **Assertion**: Assert conditions with clear, specific assertions
- **Teardown**: pytest fixtures handle cleanup automatically (tmp_path, monkeypatch)

## Mocking

**Framework:** Python standard library `unittest.mock`

**Patterns:**
- Use `MagicMock()` for mocked objects with configurable return values
- Use `patch()` context manager for patching module-level objects
- Use `monkeypatch` fixture for environment variable injection

**Example 1: Mock S3 in dataset test** (from `model/tests/test_dataset.py`):
```python
def test_download_calls_s3_list_objects(tmp_path: Path) -> None:
    ds = WasteDataset(s3_bucket="test-bucket", data_dir=tmp_path)

    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [{"Contents": []}]
    ds._s3 = mock_s3

    ds.download()

    mock_s3.get_paginator.assert_called_once_with("list_objects_v2")
```

**Example 2: Mock model in FastAPI test** (from `api/tests/test_predict_endpoint.py`):
```python
@pytest.fixture
def mock_model() -> MagicMock:
    """A mock ClassificationModel that returns a fixed result."""
    mock = MagicMock()
    mock.predict.return_value = ClassificationResult(
        top_prediction=CategoryPrediction(label="cardboard", confidence=0.923),
        alternatives=[
            CategoryPrediction(label="cardboard", confidence=0.923),
            CategoryPrediction(label="plastic-lined-cardboard", confidence=0.041),
            CategoryPrediction(label="paper", confidence=0.018),
        ],
    )
    return mock

@pytest.fixture
def client(mock_model: MagicMock) -> TestClient:
    """TestClient with mock model pre-loaded on app.state (no lifespan)."""
    app.state.model = mock_model
    return TestClient(app)
```

**Example 3: Patch at function level** (from `api/tests/test_upload.py`):
```python
with patch("src.main.s3_service.upload_training_image") as mock_upload:
    mock_upload.return_value = "metal-cans-tins/test-key.jpeg"
    response = client.post(
        "/upload",
        json={"image_base64": encoded, "label": "metal-cans-tins"},
    )
    assert response.status_code == 200
    mock_upload.assert_called_once()
```

**What to Mock:**
- External services (S3, AWS)
- HTTP calls
- Heavy computations (ML model)
- File I/O where test data can be used instead

**What NOT to Mock:**
- Core business logic being tested
- Pydantic models
- FastAPI routing
- Dataclasses

## Fixtures and Factories

**Test Data:**

Fixtures create synthetic test data. Examples:

1. **Image fixtures** (from `api/tests/test_predict_endpoint.py`):
```python
@pytest.fixture
def valid_jpeg_bytes() -> bytes:
    """Minimal valid 32×32 JPEG image bytes."""
    img = Image.new("RGB", (32, 32), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
```

2. **Model artifact fixture** (from `api/tests/test_inference.py`):
```python
@pytest.fixture
def model_artifact_path(tmp_path) -> str:
    """Create a tiny random EfficientNet-B0 safetensors artifact."""
    net = models.efficientnet_b0(weights=None)
    net.classifier[1] = torch.nn.Linear(1280, len(ALL_LABELS_LIST))
    path = tmp_path / "test_model.safetensors"
    save_file(net.state_dict(), str(path))
    return str(path)
```

3. **Directory fixture** (from `model/tests/test_dataset.py`):
```python
LABELS = ["cardboard", "plastic-bottles-containers", "glass-bottles-jars"]
IMAGES_PER_LABEL = 10

@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    _make_image_dir(tmp_path, LABELS, IMAGES_PER_LABEL)
    return tmp_path

@pytest.fixture
def dataset(data_dir: Path) -> WasteDataset:
    ds = WasteDataset(s3_bucket="test-bucket", data_dir=data_dir)
    return ds
```

**Location:**
- Shared fixtures: `tests/conftest.py` (e.g., `model/tests/conftest.py` contains `aws_credentials`)
- Test-specific fixtures: In the test file itself
- Helper functions: Start with `_` prefix (private) for small data builders (e.g., `_make_image_dir()`, `_make_tiny_dataset()`)

## Coverage

**Requirements:** No explicit coverage target enforced

**View Coverage:**
```bash
cd model && pytest --cov=src --cov-report=term-missing
```

**Observed Coverage:**
- All test files have descriptive docstrings stating "Tests must FAIL before implementation is complete (TDD — constitution Principle II)"
- Tests cover: happy path, error conditions, edge cases, validation

## Test Types

**Unit Tests:**
- Scope: Single function or method in isolation
- Approach: Fast, deterministic, mock external dependencies
- Examples:
  - `test_build_model_returns_nn_module()` in `model/tests/test_train.py`
  - `test_category_prediction_is_frozen()` in `api/tests/test_inference.py`
  - `test_freeze_backbone_freezes_all_but_classifier()` in `model/tests/test_train.py`

**Integration Tests:**
- Scope: Multiple components working together
- Approach: Use real(ish) objects but mocked external services
- Examples:
  - `test_predict_returns_200_with_valid_jpeg()` in `api/tests/test_predict_endpoint.py` (Route + Model)
  - `test_labels_response_structure()` in `api/tests/test_labels.py` (Route + Label data)
  - `test_upload_valid_jpeg()` in `api/tests/test_upload.py` (Route + S3 mock)

**E2E Tests:**
- Not used in current codebase
- Would require real services or LocalStack integration
- Manual testing pattern: Use `make run` to start all services

## Common Patterns

**Async Testing:**
Used in `api/tests/` for FastAPI async routes:

```python
# Pattern 1: TestClient handles async automatically
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.post("/predict", files={"file": (...)})
assert response.status_code == 200

# Pattern 2: Mock async functions if needed (not observed in current code)
# async def test_something():
#     result = await async_function()
#     assert result is not None
```

**Error Testing:**
- Pattern: Use `pytest.raises()` context manager
- Examples:

```python
# Test expected exception
def test_get_splits_raises_when_data_dir_empty(tmp_path: Path) -> None:
    ds = WasteDataset(s3_bucket="test-bucket", data_dir=tmp_path / "empty")
    with pytest.raises(FileNotFoundError):
        ds.get_splits()

# Test HTTP error response
def test_predict_returns_400_for_non_image_content_type(client: TestClient) -> None:
    response = client.post(
        "/predict",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400

# Test validation error
def test_upload_invalid_label():
    image_data = JPEG_HEADER + b"\x00" * 100
    encoded = base64.b64encode(image_data).decode()
    response = client.post(
        "/upload",
        json={"image_base64": encoded, "label": "invalid_label"},
    )
    assert response.status_code == 422  # Pydantic validation error
```

**Temporary Files and Directories:**
- Use `tmp_path` fixture from pytest (not `tempfile` module)
- Automatic cleanup handled by pytest
- Example:
  ```python
  def test_something(tmp_path: Path) -> None:
      data_dir = _make_image_dir(tmp_path, labels, 5)
      # Use data_dir
      # pytest cleans up tmp_path automatically after test
  ```

**Fixtures with Parameters (Monkeypatch):**
- Use `monkeypatch` fixture for:
  - Environment variables: `monkeypatch.setenv("VAR", "value")`
  - Working directory: `monkeypatch.chdir(tmp_path)`
  - Module patches: Use `patch()` context manager instead

**AWS Credentials Mocking:**
- Global `aws_credentials` autouse fixture in `model/tests/conftest.py`:
  ```python
  @pytest.fixture(autouse=True)
  def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
      """Set dummy AWS environment variables before every test."""
      monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
      monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
      monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
      monkeypatch.setenv("AWS_SECURITY_TOKEN", "test")
      monkeypatch.setenv("AWS_SESSION_TOKEN", "test")
  ```

## Privacy and Security Testing

**Pattern: Verify no sensitive data persists**

Example from `api/tests/test_predict_endpoint.py`:
```python
def test_predict_does_not_write_image_to_disk(
    client: TestClient, valid_jpeg_bytes: bytes, tmp_path, monkeypatch
) -> None:
    """Verify no image file is created during inference (FR-012)."""
    monkeypatch.chdir(tmp_path)
    client.post(
        "/predict",
        files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    image_files = list(tmp_path.rglob("*.jpg")) + list(tmp_path.rglob("*.png"))
    assert len(image_files) == 0
```

---

*Testing analysis: 2026-02-26*
