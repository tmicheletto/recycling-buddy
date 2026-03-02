# Design: `recbuddy` shared Python package

**Date:** 2026-03-02
**Status:** Approved

## Problem

`api/src/labels.py` is the single source of truth for the 67 waste category labels, but the
model hardcodes the count (`num_classes=67`, `_NUM_CLASSES=67`) independently. There is no
enforcement that the two stay in sync. As the canonical consumer of these labels, the model
is a better home for them — the api already depends on the model's artifact, and will now
depend on its Python package too.

## Decision

Rename the model package from `recycling-model` to `recbuddy` and move all model source
files from `model/src/` into `model/recbuddy/`. The `recbuddy` package is designed for
future publication to PyPI or a private registry. The api declares it as a path dependency
for now, swappable to a version specifier later.

`recbuddy.labels` is the only public surface. All other modules (`train`, `evaluate`,
`dataset`, `transforms`) are CLI-only scripts and are not re-exported from `__init__.py`.

## Package structure

```
model/
  recbuddy/
    __init__.py       # empty — no public re-exports beyond labels
    labels.py         # single source of truth for all 67 waste labels
    train.py          # CLI: python -m recbuddy.train
    evaluate.py       # CLI: python -m recbuddy.evaluate
    dataset.py
    transforms.py
  tests/              # unchanged location
  pyproject.toml      # name = "recbuddy"
```

## What moves

| From | To |
|---|---|
| `api/src/labels.py` (content) | `model/recbuddy/labels.py` |
| `model/src/train.py` | `model/recbuddy/train.py` |
| `model/src/evaluate.py` | `model/recbuddy/evaluate.py` |
| `model/src/dataset.py` | `model/recbuddy/dataset.py` |
| `model/src/transforms.py` | `model/recbuddy/transforms.py` |
| `model/src/` | deleted |

## API impact

`api/src/labels.py` becomes a thin re-export so no existing api import sites change:

```python
from recbuddy.labels import ALL_LABELS, ALL_LABELS_LIST, is_valid_label, is_s3_safe
__all__ = ["ALL_LABELS", "ALL_LABELS_LIST", "is_valid_label", "is_s3_safe"]
```

## Model internal changes

- All `from src.xxx import` → `from recbuddy.xxx import` within the moved files
- `train.py`: `num_classes` default uses `len(ALL_LABELS_LIST)` instead of hardcoded `67`
- `evaluate.py`: `_NUM_CLASSES` derived from `len(ALL_LABELS_LIST)` instead of hardcoded `67`

## Packaging

`model/pyproject.toml` changes:
- `name = "recbuddy"` (was `recycling-model`)
- Add `[build-system]` with hatchling so the package is installable
- `pythonpath = ["."]` stays (for pytest)

`api/pyproject.toml` adds:
```toml
"recbuddy @ ../model"   # path dep now; replace with "recbuddy>=0.1.0" when published
```

## Docker

The api Dockerfile build context changes from `./api` to repo root (`.`) so uv can resolve
the path dependency during image build. When `recbuddy` is published to a registry, the
context reverts to `./api` since the dep resolves from the registry.

`docker-compose.yml` api service: `context: .`, `dockerfile: api/Dockerfile`.

## Full changeset

| File | Change |
|---|---|
| `model/recbuddy/__init__.py` | Create (empty) |
| `model/recbuddy/labels.py` | Create (from `api/src/labels.py`) |
| `model/recbuddy/train.py` | Move + update imports |
| `model/recbuddy/evaluate.py` | Move + update imports + derive `_NUM_CLASSES` |
| `model/recbuddy/dataset.py` | Move + update imports |
| `model/recbuddy/transforms.py` | Move |
| `model/src/` | Delete |
| `model/pyproject.toml` | `name = "recbuddy"`, `[build-system]`, updated pythonpath |
| `model/tests/*.py` | `from src.xxx` → `from recbuddy.xxx` |
| `api/pyproject.toml` | Add `recbuddy` dep, regenerate `uv.lock` |
| `api/src/labels.py` | Re-export from `recbuddy.labels` |
| `api/Dockerfile` | Build from repo root, COPY model source |
| `docker-compose.yml` | `context: .` for api build |
| `CLAUDE.md` | Update CLI commands to `python -m recbuddy.train` etc. |
