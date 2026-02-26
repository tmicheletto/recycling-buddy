---
phase: 01-guidelines-data-layer
plan: 03
subsystem: testing
tags: [pytest, pytest-asyncio, fastapi, guidelines, openai, mock, asyncmock, testclient]

# Dependency graph
requires:
  - phase: 01-guidelines-data-layer plan 02
    provides: "GuidelinesService with LLM-backed lookup, in-memory cache, AdviceRecord dataclass, and GET /advice endpoint"
provides:
  - "api/tests/test_guidelines.py — 6 unit tests for GuidelinesService: fallback, cache, label coverage"
  - "api/tests/test_advice_endpoint.py — 6 integration tests for GET /advice endpoint"
affects:
  - 02-frontend (test patterns for /advice endpoint)
  - 03-mobile (test patterns for /advice endpoint)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AsyncMock + patch.object pattern for mocking async service methods in pytest-asyncio tests"
    - "app.state injection pattern: set app.state.guidelines_service (and app.state.model) before TestClient creation to bypass lifespan"
    - "_settings_with_no_key() helper: inline fake settings class to control GuidelinesService init in unit tests"

key-files:
  created:
    - api/tests/test_guidelines.py
    - api/tests/test_advice_endpoint.py
  modified: []

key-decisions:
  - "TestClient used without context manager to avoid triggering FastAPI lifespan — same pattern as test_predict_endpoint.py"
  - "Both app.state.model and app.state.guidelines_service must be set before TestClient creation — lifespan sets both"
  - "pytestmark = pytest.mark.asyncio at module level covers all async tests in STRICT asyncio mode"
  - "Fresh GuidelinesService instance per label in test_all_67_labels_do_not_raise avoids cache interference between labels"

patterns-established:
  - "GuidelinesService mock pattern: AsyncMock() with lookup = AsyncMock(return_value=record), injected on app.state"
  - "Inline _settings_with_no_key() class for controlling API key presence without environment manipulation"

requirements-completed: [DATA-02]

# Metrics
duration: 3min
completed: 2026-02-26
---

# Phase 1 Plan 3: GuidelinesService Test Suite Summary

**pytest test suite proving fallback safety, in-memory cache correctness, all-67-label coverage, and /advice HTTP contract — 12 new tests, all mocked, zero real OpenAI calls**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-26T04:02:24Z
- **Completed:** 2026-02-26T04:05:27Z
- **Tasks:** 2 of 2
- **Files modified:** 2

## Accomplishments
- Created test_guidelines.py with 6 async unit tests covering fallback path (no API key), in-memory cache deduplication, cache key per (item, council) pair, all 67 classifier labels resolving without exception, field passthrough correctness, and enum validation
- Created test_advice_endpoint.py with 6 synchronous integration tests covering 200 with valid params, 422 on missing params (two tests), special_disposal_flag propagation, fallback disclaimer in response, and AdviceRecord schema completeness
- Full API test suite grows from 38 to 50 tests, all passing, with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write GuidelinesService unit tests (RED then GREEN)** - `a93282d` (test)
2. **Task 2: Write /advice endpoint integration tests** - `749e218` (test)

**Plan metadata:** _(final metadata commit pending)_

## Files Created/Modified
- `/Users/tim/code/recycling-buddy/api/tests/test_guidelines.py` — 6 unit tests for GuidelinesService: fallback path, cache deduplication, cache key granularity, all-67-label coverage, field passthrough, fallback field validation
- `/Users/tim/code/recycling-buddy/api/tests/test_advice_endpoint.py` — 6 integration tests for GET /advice: valid params 200, missing params 422 (x2), special_disposal_flag, fallback disclaimer, schema completeness

## Decisions Made
- Used `TestClient(app)` without context manager (no `with`) to avoid triggering the FastAPI lifespan, which would attempt to load a real model artifact — same pattern established in test_predict_endpoint.py
- Also set `app.state.model` in each endpoint test fixture because the lifespan sets both model and guidelines_service; without a model mock, some error paths in other routes would fail
- Used `pytestmark = pytest.mark.asyncio` at module level in test_guidelines.py since pytest-asyncio is in STRICT mode — this applies the mark to all async tests in the file without per-function decoration
- Kept a fresh `GuidelinesService()` instance per label in `test_all_67_labels_do_not_raise` to prevent the first-call cache population from hiding failures on subsequent labels

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used non-context-manager TestClient to avoid lifespan artifact loading**
- **Found during:** Task 2 (test_advice_endpoint.py)
- **Issue:** `with TestClient(app) as c:` triggers the FastAPI lifespan which calls `ClassificationModel.from_artifact(...)` — this raises `FileNotFoundError` in CI because no trained model artifact exists in the test environment
- **Fix:** Used `TestClient(app)` without context manager (same pattern already used in test_predict_endpoint.py); also set `app.state.model` to a MagicMock to satisfy any code path that reads it
- **Files modified:** api/tests/test_advice_endpoint.py
- **Verification:** All 6 endpoint tests pass; no FileNotFoundError
- **Committed in:** 749e218 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - blocking behaviour of lifespan in test env)
**Impact on plan:** Essential fix — the plan showed `with TestClient(app) as c:` in the fixture snippet, but that pattern fails in this project because no model artifact exists in the test environment. The fix exactly mirrors the established pattern from test_predict_endpoint.py.

## Issues Encountered
- None beyond the lifespan issue documented above as a deviation.

## User Setup Required
None — test suite runs fully offline with all external dependencies mocked. No API keys or network access required.

## Next Phase Readiness
- DATA-02 verification gate satisfied: all 67 labels resolve through GuidelinesService without exception, fallback path returns valid AdviceRecord with is_fallback=True, cache prevents duplicate LLM calls, GET /advice HTTP contract verified
- Phase 1 (Guidelines Data Layer) is now fully implemented and tested — frontend (Phase 2) can integrate against GET /advice endpoint
- Test patterns for GuidelinesService mocking established and documented for future use

---
*Phase: 01-guidelines-data-layer*
*Completed: 2026-02-26*

## Self-Check: PASSED

- FOUND: api/tests/test_guidelines.py
- FOUND: api/tests/test_advice_endpoint.py
- FOUND: .planning/phases/01-guidelines-data-layer/01-03-SUMMARY.md
- FOUND: commit a93282d
- FOUND: commit 749e218
