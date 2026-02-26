---
phase: 01-guidelines-data-layer
plan: 05
subsystem: api
tags: [fastapi, pydantic-settings, docker-compose, pathlib, config]

requires:
  - phase: 01-guidelines-data-layer
    provides: label_to_rny.json mapping file at data/ in project root

provides:
  - "__file__-relative default for guidelines_data_path in config.py — resolves regardless of CWD"
  - "docker-compose api service with ./data:/app/data volume mount and GUIDELINES_DATA_PATH env var"
  - "api/Dockerfile ENV GUIDELINES_DATA_PATH for standalone container deployments"
affects:
  - GuidelinesService._rny_url() — now returns non-None URLs for mapped labels
  - DATA-01, DATA-02 requirements — RNY-grounded lookups now operational end-to-end

tech-stack:
  added: []
  patterns:
    - "Use pathlib.Path(__file__).parent chain to anchor config defaults to source file location, not CWD"
    - "Commented-out env var entry in dev.env documents override points without breaking defaults"

key-files:
  created: []
  modified:
    - api/src/config.py
    - api/config/dev.env
    - docker-compose.yml
    - api/Dockerfile

key-decisions:
  - "Empty string env vars in pydantic-settings str fields are NOT treated as missing — they override the default with empty string; use commented-out entries in env files to document override points without breaking defaults"
  - "guidelines_data_path uses _PROJECT_ROOT = Path(__file__).parent.parent.parent so the default is absolute and CWD-independent"
  - "data/ directory provided at runtime via volume mount only — cannot be COPY'd in Dockerfile because build context is ./api (project root is outside build context)"

patterns-established:
  - "Config anchor pattern: _PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent for project-root-relative defaults"
  - "Env override documentation: commented GUIDELINES_DATA_PATH= in dev.env signals override point to developers"

requirements-completed: [DATA-01, DATA-02]

duration: 8min
completed: 2026-02-26
---

# Phase 1 Plan 05: Wire label_to_rny.json to API Runtime Summary

**__file__-relative config default and docker-compose volume mount so label_to_rny.json resolves in all environments (local uvicorn, docker-compose, standalone Docker)**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-26T09:22:18Z
- **Completed:** 2026-02-26T09:30:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Fixed guidelines_data_path config default from CWD-relative string to absolute __file__-relative path via pathlib
- Added data volume mount (./data:/app/data) and GUIDELINES_DATA_PATH to docker-compose.yml api service
- Added ENV GUIDELINES_DATA_PATH to api/Dockerfile for standalone container deployments
- All 50 existing tests pass with no regressions; uvicorn startup no longer logs "label_to_rny.json not found"

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix config.py default path and add dev.env entry** - `596288d` (fix)
2. **Task 2: Add data volume mount to docker-compose.yml and ENV default to Dockerfile** - `470f98e` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `api/src/config.py` - Added `import pathlib`, `_PROJECT_ROOT = Path(__file__).parent.parent.parent`, changed `guidelines_data_path` default to `str(_PROJECT_ROOT / "data" / "label_to_rny.json")`
- `api/config/dev.env` - Added commented-out GUIDELINES_DATA_PATH entry to document override point
- `docker-compose.yml` - Added `./data:/app/data` volume and `GUIDELINES_DATA_PATH=/app/data/label_to_rny.json` to api service
- `api/Dockerfile` - Added `ENV GUIDELINES_DATA_PATH=/app/data/label_to_rny.json` after WORKDIR line

## Decisions Made

- Used a commented-out entry in dev.env rather than an empty `GUIDELINES_DATA_PATH=` — pydantic-settings treats empty string env vars as the value (not missing), which would override the __file__-relative default with an empty string and break path resolution
- data/ directory is provided via runtime volume mount, not COPY in Dockerfile — build context is ./api so the project root data/ directory is outside the build context

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's empty env var approach breaks config default in pydantic-settings**
- **Found during:** Task 1 (Fix config.py default path and add dev.env entry)
- **Issue:** Plan instructed adding `GUIDELINES_DATA_PATH=` (empty value) to dev.env, claiming "empty env var in pydantic-settings falls back to the field default." This is incorrect — pydantic-settings uses the empty string as the value for `str` fields, overriding the __file__-relative default and setting `guidelines_data_path` to `""`.
- **Fix:** Used a commented-out entry `# GUIDELINES_DATA_PATH=/path/to/label_to_rny.json` instead, which documents the override point without interfering with the config default.
- **Files modified:** `api/config/dev.env`
- **Verification:** `pathlib.Path(settings.guidelines_data_path).exists()` returns `True` from api/ CWD; no "label_to_rny.json not found" warning on uvicorn startup
- **Committed in:** `596288d` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in plan assumption about pydantic-settings empty string handling)
**Impact on plan:** Auto-fix necessary for correctness — the plan's prescribed approach would have silently broken the config default. The commented-out entry achieves the same documentation goal.

## Issues Encountered

None beyond the auto-fixed deviation above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- GuidelinesService._rny_url() now returns non-None URLs for mapped labels when API starts normally
- DATA-01 and DATA-02 requirements are fully satisfied — RNY-grounded lookups work end-to-end
- docker-compose up api container resolves label_to_rny.json from the mounted data/ volume
- GUIDELINES_DATA_PATH env var can override the resolved path in all environments

---
*Phase: 01-guidelines-data-layer*
*Completed: 2026-02-26*

## Self-Check: PASSED

- api/src/config.py: FOUND
- api/config/dev.env: FOUND
- docker-compose.yml: FOUND
- api/Dockerfile: FOUND
- 01-05-SUMMARY.md: FOUND
- Commit 596288d: FOUND
- Commit 470f98e: FOUND
