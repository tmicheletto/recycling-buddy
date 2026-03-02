# Design: Remove `api/app/labels.py` Shim

**Date:** 2026-03-02
**Status:** Approved

## Problem

`api/app/labels.py` is a zero-logic passthrough that re-exports symbols from
`recbuddy.labels`. It exists as an indirection layer that adds no value — the
`api` package already declares `recbuddy` as a direct path dependency in
`pyproject.toml`.

## Decision

Delete `api/app/labels.py` and update all six import sites to import from
`recbuddy.labels` directly.

## Change Set

| File | Change |
|------|--------|
| `api/app/labels.py` | Delete |
| `api/app/inference.py` | `from app.labels` → `from recbuddy.labels` |
| `api/app/main.py` | `from app.labels` → `from recbuddy.labels` |
| `api/tests/test_labels.py` | `from app.labels` → `from recbuddy.labels` |
| `api/tests/test_labels_data.py` | `from app.labels` → `from recbuddy.labels` |
| `api/tests/test_inference.py` | `from app.labels` → `from recbuddy.labels` |
| `api/tests/test_guidelines.py` | `from app.labels` → `from recbuddy.labels` |

## Verification

- `uv run ty check` passes in `api/`
- `uv run pytest` passes in `api/`

## Non-Goals

- No changes to `recbuddy/labels.py`
- No changes to exported symbols or behaviour
