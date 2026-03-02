# Remove `api/app/labels.py` Shim Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Delete the zero-logic `api/app/labels.py` passthrough and import `recbuddy.labels` directly at every call site.

**Architecture:** `api/` already depends on `recbuddy` (path dependency in `api/pyproject.toml`). The shim only re-exports the same four symbols unchanged. Removing it makes the dependency explicit at each import site with no behaviour change.

**Tech Stack:** Python, uv, ty, pytest

---

### Task 1: Confirm baseline tests pass

**Files:**
- Read: `api/` (no edits)

**Step 1: Run tests to establish green baseline**

```bash
cd api && uv run pytest -q
```
Expected: all tests pass.

**Step 2: Run type checker to establish clean baseline**

```bash
cd api && uv run ty check
```
Expected: `All checks passed!`

---

### Task 2: Update runtime imports

**Files:**
- Modify: `api/app/inference.py:26`
- Modify: `api/app/main.py:21`

**Step 1: Update `inference.py`**

On line 26, change:
```python
from app.labels import ALL_LABELS_LIST
```
to:
```python
from recbuddy.labels import ALL_LABELS_LIST
```

**Step 2: Update `main.py`**

On line 21, change:
```python
from app.labels import ALL_LABELS, ALL_LABELS_LIST
```
to:
```python
from recbuddy.labels import ALL_LABELS, ALL_LABELS_LIST
```

---

### Task 3: Update test imports

**Files:**
- Modify: `api/tests/test_inference.py:17`
- Modify: `api/tests/test_guidelines.py:8`
- Modify: `api/tests/test_labels.py:5`
- Modify: `api/tests/test_labels_data.py:5`

**Step 1: Update `test_inference.py`**

On line 17, change:
```python
from app.labels import ALL_LABELS_LIST
```
to:
```python
from recbuddy.labels import ALL_LABELS_LIST
```

**Step 2: Update `test_guidelines.py`**

On line 8, change:
```python
from app.labels import ALL_LABELS_LIST
```
to:
```python
from recbuddy.labels import ALL_LABELS_LIST
```

**Step 3: Update `test_labels.py`**

On line 5, change:
```python
from app.labels import ALL_LABELS
```
to:
```python
from recbuddy.labels import ALL_LABELS
```

**Step 4: Update `test_labels_data.py`**

On line 5, change:
```python
from app.labels import ALL_LABELS, ALL_LABELS_LIST, is_s3_safe, is_valid_label
```
to:
```python
from recbuddy.labels import ALL_LABELS, ALL_LABELS_LIST, is_s3_safe, is_valid_label
```

---

### Task 4: Delete the shim

**Files:**
- Delete: `api/app/labels.py`

**Step 1: Delete the file**

```bash
rm api/app/labels.py
```

---

### Task 5: Verify and commit

**Step 1: Run type checker**

```bash
cd api && uv run ty check
```
Expected: `All checks passed!`

**Step 2: Run tests**

```bash
cd api && uv run pytest -q
```
Expected: all tests pass (same count as baseline).

**Step 3: Commit**

```bash
git add api/app/inference.py api/app/main.py \
        api/tests/test_inference.py api/tests/test_guidelines.py \
        api/tests/test_labels.py api/tests/test_labels_data.py
git rm api/app/labels.py
git commit -m "refactor(api): remove labels shim, import recbuddy.labels directly"
```
