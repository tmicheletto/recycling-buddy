# recbuddy Package Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move the model source from `model/src/` into a proper installable Python package called `recbuddy`, making the label list the shared source of truth consumed by both the model and the api.

**Architecture:** A new `model/recbuddy/` package replaces `model/src/`. `recbuddy.labels` is the only public surface — `train`, `evaluate`, `dataset`, and `transforms` are CLI-only scripts that live inside the package but are not re-exported. The api declares `recbuddy @ ../model` as a path dependency; `api/src/labels.py` becomes a thin re-export so no existing api import sites change.

**Tech Stack:** Python 3.11+, uv, hatchling (build backend), pytest

**Design doc:** `docs/plans/2026-03-02-recbuddy-package-design.md`

---

### Task 1: Create `recbuddy/` scaffold and move leaf modules

These two files have no internal model imports — move them first to establish the package.

**Files:**
- Create: `model/recbuddy/__init__.py`
- Create: `model/recbuddy/transforms.py`
- Create: `model/recbuddy/labels.py`

**Step 1: Create the package directory and empty `__init__.py`**

```bash
mkdir model/recbuddy
touch model/recbuddy/__init__.py
```

**Step 2: Copy `transforms.py` — no imports to update**

```bash
cp model/src/transforms.py model/recbuddy/transforms.py
```

Verify the copy: `model/recbuddy/transforms.py` should be identical to `model/src/transforms.py`.

**Step 3: Copy `labels.py` from the api**

```bash
cp api/src/labels.py model/recbuddy/labels.py
```

Update the module docstring in `model/recbuddy/labels.py` to reflect its new home:

```python
"""Household waste item labels — single source of truth for the recbuddy package.

Labels are S3-safe strings (lowercase letters, digits, hyphens)
used as directory prefixes when storing training images.
"""
```

The rest of the file is unchanged. All constants (`ALL_LABELS_LIST`, `ALL_LABELS`) and
functions (`is_valid_label`, `is_s3_safe`) stay exactly as they are.

**Step 4: Commit**

```bash
git add model/recbuddy/
git commit -m "feat(recbuddy): scaffold package, add transforms and labels"
```

---

### Task 2: Move `dataset.py`

**Files:**
- Create: `model/recbuddy/dataset.py`

**Step 1: Copy and update the one internal import**

```bash
cp model/src/dataset.py model/recbuddy/dataset.py
```

In `model/recbuddy/dataset.py`, change line 15:

```python
# Before
from src.transforms import inference_transform, training_transform

# After
from recbuddy.transforms import inference_transform, training_transform
```

Everything else in the file stays the same.

**Step 2: Commit**

```bash
git add model/recbuddy/dataset.py
git commit -m "feat(recbuddy): add dataset module"
```

---

### Task 3: Move `train.py`

**Files:**
- Create: `model/recbuddy/train.py`

**Step 1: Copy and update imports**

```bash
cp model/src/train.py model/recbuddy/train.py
```

In `model/recbuddy/train.py`, make these two changes:

1. Add the labels import near the top (after the existing stdlib/third-party imports, before `from src.dataset`):

```python
from recbuddy.dataset import WasteDataset
from recbuddy.labels import ALL_LABELS_LIST
```

2. Remove the old import:
```python
# Delete this line:
from src.dataset import WasteDataset
```

3. Update `build_model` default and `train` function default to derive from labels:

In `build_model` (around line 43):
```python
# Before
def build_model(num_classes: int = 67) -> nn.Module:

# After
def build_model(num_classes: int = len(ALL_LABELS_LIST)) -> nn.Module:
```

In `train` function signature (around line 196):
```python
# Before
    num_classes: int = 67,

# After
    num_classes: int = len(ALL_LABELS_LIST),
```

**Step 2: Commit**

```bash
git add model/recbuddy/train.py
git commit -m "feat(recbuddy): add train module, derive num_classes from labels"
```

---

### Task 4: Move `evaluate.py`

**Files:**
- Create: `model/recbuddy/evaluate.py`

**Step 1: Copy and update imports**

```bash
cp model/src/evaluate.py model/recbuddy/evaluate.py
```

In `model/recbuddy/evaluate.py`:

1. Add near the top (after third-party imports):
```python
from recbuddy.labels import ALL_LABELS_LIST
```

2. Replace the hardcoded constant:
```python
# Before
_NUM_CLASSES: int = 67

# After
_NUM_CLASSES: int = len(ALL_LABELS_LIST)
```

3. In the `if __name__ == "__main__":` block, update the dataset import:
```python
# Before
    from src.dataset import WasteDataset

# After
    from recbuddy.dataset import WasteDataset
```

**Step 2: Commit**

```bash
git add model/recbuddy/evaluate.py
git commit -m "feat(recbuddy): add evaluate module, derive _NUM_CLASSES from labels"
```

---

### Task 5: Update `model/pyproject.toml`

**Files:**
- Modify: `model/pyproject.toml`

**Step 1: Update project name and add build system**

Change the `[project]` name and add a `[build-system]` section. The full updated file:

```toml
[project]
name = "recbuddy"
version = "0.1.0"
description = "ML model training and evaluation for Recycling Buddy"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "torch",
    "torchvision",
    "safetensors>=0.4.0",
    "pillow>=12.0.0",
    "boto3>=1.42.0",
    "numpy>=1.24.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "pytest>=9.0.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.14.0",
    "pyrefly>=0.19.0",
]

# Use CPU-only PyTorch wheels on Linux (Docker); macOS uses PyPI wheels (includes MPS support)
[tool.uv.sources]
torch = [
    { index = "pytorch-cpu", marker = "sys_platform == 'linux'" },
]
torchvision = [
    { index = "pytorch-cpu", marker = "sys_platform == 'linux'" },
]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]

[tool.pyrefly]
search_path = ["."]
```

**Step 2: Commit**

```bash
git add model/pyproject.toml
git commit -m "chore(recbuddy): rename package to recbuddy, add build-system"
```

---

### Task 6: Update model tests and delete `src/`

The tests currently import from `src.*`. Update them all to `recbuddy.*`, run them, then
delete the now-redundant `src/` directory.

**Files:**
- Modify: `model/tests/test_train.py`
- Modify: `model/tests/test_evaluate.py`
- Modify: `model/tests/test_dataset.py`
- Delete: `model/src/`

**Step 1: Update `test_train.py`**

```python
# Before
from src.train import build_model, freeze_backbone, get_optimizer, train_one_epoch

# After
from recbuddy.train import build_model, freeze_backbone, get_optimizer, train_one_epoch
```

Also update the inline import inside `test_train_one_epoch_returns_float_loss`:
```python
# Before
    from src.transforms import training_transform

# After
    from recbuddy.transforms import training_transform
```

**Step 2: Update `test_evaluate.py`**

```python
# Before
from src.evaluate import compute_metrics, load_artifact
...
    from src.transforms import inference_transform

# After
from recbuddy.evaluate import compute_metrics, load_artifact
...
    from recbuddy.transforms import inference_transform
```

**Step 3: Update `test_dataset.py`**

```python
# Before
from src.dataset import WasteDataset

# After
from recbuddy.dataset import WasteDataset
```

**Step 4: Run all model tests — expect all to pass**

```bash
cd model && uv run pytest -v
```

Expected: all tests green. If any fail, the import paths in the moved files are wrong —
check `recbuddy/*.py` for any remaining `from src.` references:

```bash
grep -r "from src\." model/recbuddy/
```

This should return nothing. Fix any hits before proceeding.

**Step 5: Delete `src/`**

```bash
rm -rf model/src
```

**Step 6: Run tests again to confirm nothing was relying on `src/`**

```bash
cd model && uv run pytest -v
```

Expected: all tests still green.

**Step 7: Commit**

```bash
git add model/tests/ model/src/
git commit -m "refactor(recbuddy): update tests to recbuddy imports, delete src/"
```

---

### Task 7: Wire the api to `recbuddy`

**Files:**
- Modify: `api/pyproject.toml`
- Modify: `api/src/labels.py`

**Step 1: Add `recbuddy` as a dependency in `api/pyproject.toml`**

In the `dependencies` list, add:

```toml
dependencies = [
    "recbuddy @ ../model",
    "boto3>=1.42.38",
    # ... rest unchanged
]
```

**Step 2: Regenerate the api lockfile**

```bash
cd api && uv lock
```

This rewrites `api/uv.lock` to include `recbuddy`. The command should complete without
errors. If it fails, check that `model/pyproject.toml` has the `[build-system]` section
from Task 5.

**Step 3: Update `api/src/labels.py` to re-export from `recbuddy`**

Replace the entire file content with:

```python
"""Household waste item labels — re-exported from recbuddy.labels."""

from recbuddy.labels import ALL_LABELS, ALL_LABELS_LIST, is_s3_safe, is_valid_label

__all__ = ["ALL_LABELS", "ALL_LABELS_LIST", "is_valid_label", "is_s3_safe"]
```

**Step 4: Run all api tests — expect all to pass**

```bash
cd api && uv run pytest -v
```

Expected: all tests green. No api imports changed so no test logic changes — only the
`import` line at the top of each test still resolves via the re-export in `api/src/labels.py`.

If tests fail with `ModuleNotFoundError: No module named 'recbuddy'`, uv sync hasn't run:

```bash
cd api && uv sync
```

Then retry the tests.

**Step 5: Commit**

```bash
git add api/pyproject.toml api/uv.lock api/src/labels.py
git commit -m "feat(api): depend on recbuddy package, re-export labels from recbuddy"
```

---

### Task 8: Update Docker setup

The api Dockerfile build context changes from `./api` to repo root so uv can resolve the
`recbuddy @ ../model` path dependency during image build.

**Files:**
- Modify: `api/Dockerfile`
- Modify: `docker-compose.yml`

**Step 1: Update `api/Dockerfile`**

Replace the entire file:

```dockerfile
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Data directory expected at /app/data — mount a volume or set GUIDELINES_DATA_PATH env var
ENV GUIDELINES_DATA_PATH=/app/data/label_to_rny.json

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy recbuddy package (path dependency of the api)
# Only the package source is needed — not the full model directory
COPY model/pyproject.toml /model/pyproject.toml
COPY model/recbuddy/ /model/recbuddy/

# Copy api project files and install dependencies
COPY api/pyproject.toml .
COPY api/uv.lock .
RUN uv sync --frozen

# Copy remaining api source
COPY api/ .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Update `docker-compose.yml` api build context**

Change the `api` service `build` block from:

```yaml
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
```

to:

```yaml
  api:
    build:
      context: .
      dockerfile: api/Dockerfile
```

Everything else in `docker-compose.yml` stays the same.

**Step 3: Commit**

```bash
git add api/Dockerfile docker-compose.yml
git commit -m "chore(docker): update api build context to resolve recbuddy path dep"
```

---

### Task 9: Update `CLAUDE.md` CLI commands

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update the model commands in `CLAUDE.md`**

Find the Model section under `## Commands` and update:

```markdown
### Model (`cd model`)
```bash
uv run pytest
uv run python -m recbuddy.train --s3-bucket recycling-buddy-training --output-dir artifacts/ --epochs 30 --seed 42
uv run python -m recbuddy.evaluate --artifact artifacts/efficientnet_b0_recycling_v1.safetensors --s3-bucket recycling-buddy-training --split test
```
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(CLAUDE.md): update model CLI commands to recbuddy namespace"
```

---

### Task 10: Final verification

**Step 1: Run all tests across both packages**

```bash
cd model && uv run pytest -v && cd ../api && uv run pytest -v
```

Expected: all tests in both packages pass.

**Step 2: Confirm no remaining `src.` references in the model package**

```bash
grep -r "from src\." model/recbuddy/ model/tests/
```

Expected: no output.

**Step 3: Confirm api still imports labels correctly**

```bash
cd api && uv run python -c "from src.labels import ALL_LABELS_LIST; print(len(ALL_LABELS_LIST))"
```

Expected: `67`

**Step 4: Confirm recbuddy is directly importable in the api environment**

```bash
cd api && uv run python -c "from recbuddy.labels import ALL_LABELS_LIST; print(len(ALL_LABELS_LIST))"
```

Expected: `67`
