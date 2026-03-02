# Design: Lazy Model Loading

**Date:** 2026-03-02

## Problem

The API currently attempts to load the model artifact during the FastAPI lifespan (startup). Only `FileNotFoundError` is caught — any other loading failure crashes the app. The app should start and serve non-model endpoints regardless of artifact availability.

## Solution

Move model loading out of the lifespan and into the first `/predict` request using an `asyncio.Lock` for thread safety (double-checked locking pattern).

## Changes

Only `api/app/main.py` changes.

### Lifespan

Remove model loading. Initialise `app.state.model = None` and `app.state.model_lock = asyncio.Lock()`.

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.model = None
    app.state.model_lock = asyncio.Lock()
    app.state.guidelines_service = GuidelinesService()
    yield
```

### `/predict` endpoint

Replace the simple `model is None → 503` check with double-checked lazy loading:

```python
if request.app.state.model is None:
    async with request.app.state.model_lock:
        if request.app.state.model is None:
            try:
                request.app.state.model = await run_in_threadpool(
                    ClassificationModel.from_artifact,
                    settings.model_artifact_path,
                )
            except Exception as exc:
                logger.warning("Model failed to load: %s", exc)
                raise HTTPException(
                    status_code=503,
                    detail="Model artifact not available. Run the training pipeline first.",
                )
```

### Imports

Add `import asyncio` to `main.py`.

## Behaviour

| Scenario | Outcome |
|---|---|
| Artifact missing at startup | App starts normally |
| `/predict` called, artifact missing | 503; next request retries |
| `/predict` called, artifact present | Model loads once, cached in `app.state.model` |
| `/predict` called concurrently before load | One coroutine loads; others wait on lock |
| Artifact appears after startup | Picked up automatically on next `/predict` |

## Non-goals

- No changes to `inference.py`, tests (beyond fixture adjustment), or any other file
- No caching of load failures (retry on each request is desirable)
