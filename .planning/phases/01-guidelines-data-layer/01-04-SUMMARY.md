---
phase: 01-guidelines-data-layer
plan: "04"
subsystem: api
tags: [fastapi, lifespan, graceful-degradation, error-handling, python]

# Dependency graph
requires:
  - phase: 01-guidelines-data-layer
    provides: FastAPI app with ClassificationModel inference and GuidelinesService
provides:
  - FastAPI lifespan with graceful FileNotFoundError handling — sets app.state.model = None with WARNING log
  - /predict endpoint 503 guard when model artifact is absent
  - Server starts without model artifact present
affects: [all phases using the FastAPI API, integration tests, deployment]

# Tech tracking
tech-stack:
  added: []
  patterns: [graceful-degradation, model-availability-guard, 503-for-unavailable-resources]

key-files:
  created: []
  modified:
    - api/src/main.py

key-decisions:
  - "lifespan catches FileNotFoundError and sets app.state.model = None — server always starts"
  - "503 guard placed before content-type check in /predict — model unavailability is checked first"

patterns-established:
  - "Lifespan pattern: try/except FileNotFoundError sets app.state.model = None with WARNING log"
  - "503 guard pattern: check app.state.model is None at the top of /predict before any other validation"

requirements-completed: [DATA-01, DATA-02]

# Metrics
duration: 1min
completed: 2026-02-26
---

# Phase 1 Plan 04: Graceful Model-Load Failure Summary

**FastAPI lifespan catches FileNotFoundError and sets app.state.model = None; /predict returns HTTP 503 when model artifact is absent — server starts without crashing**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-02-26T08:37:06Z
- **Completed:** 2026-02-26T08:38:16Z
- **Tasks:** 1 completed
- **Files modified:** 1

## Accomplishments

- lifespan function wraps ClassificationModel.from_artifact() in try/except FileNotFoundError, sets app.state.model = None with WARNING log on failure
- /predict handler checks app.state.model is None as first guard and raises HTTP 503 with descriptive message
- All 50 existing pytest tests pass with no regressions
- Server starts successfully and reaches "Application startup complete" even when model artifact is absent

## Task Commits

Each task was committed atomically:

1. **Task 1: Graceful model load failure in lifespan and /predict 503 guard** - `eea164b` (fix)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `api/src/main.py` - lifespan try/except added; 503 guard added to /predict

## Decisions Made

- The 503 guard is placed before the content-type check in /predict — model availability is a prerequisite and should be checked first, before any file processing.
- GuidelinesService initialization remains outside the try/except block and is unaffected by model load failure — the two concerns are fully independent.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Both edits were straightforward. All 50 tests passed on first run after the changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Gap closure complete: server now starts without model artifact
- UAT test 2 scenario (server starts without artifact) is now unblocked
- The /advice endpoint remains fully functional regardless of model artifact presence
- /predict degrades gracefully to 503 rather than crashing at startup

---
*Phase: 01-guidelines-data-layer*
*Completed: 2026-02-26*
