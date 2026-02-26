---
phase: 01-guidelines-data-layer
plan: 02
subsystem: api
tags: [openai, fastapi, guidelines, recycling, llm, cache, httpx, pydantic]

# Dependency graph
requires:
  - phase: 01-guidelines-data-layer plan 01
    provides: "data/label_to_rny.json — mapping table consumed by GuidelinesService to construct RNY URLs"
provides:
  - "api/src/guidelines.py — GuidelinesService class with LLM-backed lookup and in-memory cache; AdviceRecord dataclass"
  - "GET /advice endpoint — returns council-specific bin advice for (item_category, council_slug)"
  - "openai SDK integrated into API project"
affects:
  - 02-frontend (consumes /advice endpoint for bin advice display)
  - 03-mobile (consumes /advice endpoint)

# Tech tracking
tech-stack:
  added:
    - "openai>=2.24.0 (AsyncOpenAI client, gpt-4o-mini)"
    - "httpx (async HTTP client for RNY page fetching — already in dev deps, now used in production code)"
  patterns:
    - "LLM grounding pattern: fetch relevant web page as context, truncate to 8000 chars, pass to LLM with structured JSON output"
    - "In-memory TTL cache pattern: dict[tuple[str,str], tuple[AdviceRecord, float]] with time.time() insertion tracking"
    - "Graceful fallback pattern: return meaningful default record (red bin + disclaimer) when LLM unavailable or fails"
    - "Frozen dataclass for immutable response records (AdviceRecord)"

key-files:
  created:
    - api/src/guidelines.py
  modified:
    - api/src/config.py
    - api/src/main.py
    - api/pyproject.toml
    - api/uv.lock
    - api/config/dev.env

key-decisions:
  - "gpt-4o-mini chosen as LLM model — lower cost, sufficient for structured extraction from HTML context"
  - "HTML truncated to 8000 chars before sending to LLM — stays within context budget while preserving most useful content"
  - "AsyncOpenAI client only instantiated when OPENAI_API_KEY is present — no crash on missing key"
  - "GuidelinesService initialised in FastAPI lifespan (not at import time) — ensures settings resolved at startup"
  - "Cache keyed by (item_category, council_slug) tuple — correct granularity for per-council differentiation"
  - "AdviceRecord is a frozen dataclass (not Pydantic) — immutable, hashable, suitable for cache values"

patterns-established:
  - "Fallback pattern: replace(_FALLBACK, council_slug=..., item_category=...) fills in contextual fields on the shared template"
  - "LLM error handling: all exceptions caught and logged, fallback returned — no unhandled exceptions bubble up"
  - "Settings extension: new fields added after existing ones, defaults allow zero-config startup"

requirements-completed: [DATA-01, DATA-02]

# Metrics
duration: 2min
completed: 2026-02-26
---

# Phase 1 Plan 2: GuidelinesService Summary

**LLM-backed recycling advice service using OpenAI gpt-4o-mini with RNY page grounding, in-memory TTL cache, and GET /advice FastAPI endpoint**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T03:57:18Z
- **Completed:** 2026-02-26T03:59:58Z
- **Tasks:** 2 of 2
- **Files modified:** 6

## Accomplishments
- Created GuidelinesService with full LLM-backed lookup: fetches recyclingnearyou.com.au page as grounding context, calls gpt-4o-mini with structured JSON output format, returns typed AdviceRecord
- Implemented in-memory TTL cache (1-week default) keyed by (item_category, council_slug) — second call for same pair never hits the LLM
- Graceful fallback path returns red bin / General Waste AdviceRecord with disclaimer when API key is absent or any failure occurs — no unhandled exceptions
- Wired GuidelinesService into FastAPI lifespan and added GET /advice endpoint with Pydantic AdviceResponse model
- Added openai SDK to api/pyproject.toml with uv, extended Settings with openai_api_key, guidelines_data_path, and guidelines_cache_ttl_seconds fields

## Task Commits

Each task was committed atomically:

1. **Task 1: Add openai dependency and extend Settings** - `f2b5447` (feat)
2. **Task 2: Implement GuidelinesService and wire /advice endpoint** - `d3f9e5b` (feat)

**Plan metadata:** _(final metadata commit pending)_

## Files Created/Modified
- `/Users/tim/code/recycling-buddy/api/src/guidelines.py` — GuidelinesService class, AdviceRecord dataclass, fallback template, system prompt, RNY fetch logic, in-memory cache
- `/Users/tim/code/recycling-buddy/api/src/main.py` — Added GuidelinesService import, lifespan init, AdviceResponse model, GET /advice route
- `/Users/tim/code/recycling-buddy/api/src/config.py` — Added openai_api_key, guidelines_data_path, guidelines_cache_ttl_seconds fields to Settings
- `/Users/tim/code/recycling-buddy/api/pyproject.toml` — Added openai>=2.24.0 dependency
- `/Users/tim/code/recycling-buddy/api/uv.lock` — Lock file updated with openai and transitive deps (distro, jiter, sniffio, tqdm)
- `/Users/tim/code/recycling-buddy/api/config/dev.env` — Added OPENAI_API_KEY= placeholder

## Decisions Made
- AsyncOpenAI client only created when OPENAI_API_KEY is present in settings — this allows the API to start and serve other endpoints without requiring an OpenAI key, returning fallback advice instead of crashing
- HTML truncated to 8000 chars before passing to LLM — gpt-4o-mini context window is large enough for full pages but this keeps costs predictable and response times fast
- AdviceRecord uses a frozen dataclass rather than Pydantic model — it is an internal immutable value type; AdviceResponse (Pydantic) handles serialisation at the API boundary
- SYSTEM_PROMPT instructs LLM to never invent council-specific rules — prevents hallucinated council policies not present in the grounding context

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Verification command used `python3` (system Python) instead of venv Python, causing `ModuleNotFoundError: No module named 'pydantic_settings'` — resolved by using `.venv/bin/python3` for verification. This is a local dev environment issue, not a code issue.

## User Setup Required

**External services require manual configuration.**

To enable LLM-backed advice (rather than fallback-only mode):

1. Obtain an OpenAI API key from https://platform.openai.com/api-keys
2. Set the key in `api/config/dev.env`:
   ```
   OPENAI_API_KEY=sk-...
   ```
3. Verify: `cd api && .venv/bin/python3 -c "from src.config import settings; print('Key set:', bool(settings.openai_api_key))"`

Without the key, the API starts normally and returns fallback advice (red bin + disclaimer) for all /advice requests.

## Next Phase Readiness
- GET /advice endpoint is fully implemented and returns correct AdviceRecord schema in all code paths
- Service works without OpenAI key (fallback mode) — safe for local dev without credentials
- label_to_rny.json (from Plan 01) is loaded at GuidelinesService init — 55/67 labels have RNY grounding URLs
- Cache is ready — second lookup for same (item, council) pair does not make additional OpenAI calls
- Frontend (Phase 2) can call GET /advice?item_category={label}&council_slug={slug} immediately

---
*Phase: 01-guidelines-data-layer*
*Completed: 2026-02-26*

## Self-Check: PASSED

- FOUND: api/src/guidelines.py
- FOUND: api/src/main.py
- FOUND: api/src/config.py
- FOUND: .planning/phases/01-guidelines-data-layer/01-02-SUMMARY.md
- FOUND: commit f2b5447
- FOUND: commit d3f9e5b
