# Design: Rename api/src/ to api/app/

**Date:** 2026-03-02

## Summary

Rename the `api/src/` directory to `api/app/` and update all references atomically in a single commit.

## Files affected

| File | Change |
|------|--------|
| `api/src/` (directory) | Rename to `api/app/` |
| `api/src/main.py` | `from src.X` → `from app.X` (5 imports) |
| `api/src/guidelines.py` | `from src.config` → `from app.config` |
| `api/src/inference.py` | `from src.labels` → `from app.labels` |
| `api/tests/test_inference.py` | `from src.X` → `from app.X` |
| `api/tests/test_guidelines.py` | imports + `monkeypatch.setattr("src.guidelines.X")` → `app.guidelines.X` |
| `api/tests/test_predict_endpoint.py` | `from src.X` → `from app.X` |
| `api/tests/test_labels.py` | `from src.X` → `from app.X` |
| `api/tests/test_upload.py` | import + `patch("src.main.X")` → `app.main.X` |
| `api/tests/test_advice_endpoint.py` | `from src.X` → `from app.X` |
| `api/tests/test_labels_data.py` | `from src.X` → `from app.X` |
| `api/Dockerfile` | CMD `src.main:app` → `app.main:app` |
| `docker-compose.yml` | volume `./api/src:/app/src` → `./api/app:/app/app`; uvicorn command |
| `.github/workflows/api-ci.yml` | comment `src-layout` → `app-layout` |

## Commit strategy

Single atomic commit — all changes together so no intermediate broken state exists in git history.

## Non-goals

- No changes to `model/` or `ui/`
- No changes to import style or module structure
- No changes to `__init__.py` contents
