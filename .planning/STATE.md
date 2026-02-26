---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-02-26T09:28:57.902Z"
progress:
  total_phases: 1
  completed_phases: 1
  total_plans: 5
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** A user can photograph any household waste item and immediately know exactly which bin it belongs in, based on their council's actual rules.
**Current focus:** Phase 1 — Guidelines Data Layer

## Current Position

Phase: 1 of 4 (Guidelines Data Layer)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-02-26 — Phase 1 plan 04 complete (gap closure — graceful model-load failure)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: -

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01-guidelines-data-layer P01 | 5 | 1 tasks | 1 files |
| Phase 01-guidelines-data-layer P02 | 2 | 2 tasks | 6 files |
| Phase 01-guidelines-data-layer P03 | 3 | 2 tasks | 2 files |
| Phase 01-guidelines-data-layer P04 | 1 | 1 tasks | 1 files |
| Phase 01-guidelines-data-layer P05 | 8 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: recyclingnearyou.com.au as guidelines data source — covers all Australian councils, uses same category taxonomy as classifier
- [Roadmap]: Phase 1 needs `/gsd:research-phase` before planning — site structure must be validated live before scraper design is finalised
- [Roadmap]: Phases 2 and 3 can be developed in parallel once Phase 1 slug format is established
- [Phase 01-guidelines-data-layer]: 55/67 classifier labels mapped to RNY slugs; 12 unmapped with explanatory notes; RNY council pages (not A-Z index) are the canonical slug source
- [Phase 01-guidelines-data-layer]: RNY URL pattern confirmed: https://recyclingnearyou.com.au/material/home/{slug}; 49 unique slugs available across all Australian councils
- [Phase 01-guidelines-data-layer]: gpt-4o-mini chosen for GuidelinesService — lower cost with sufficient structured extraction capability
- [Phase 01-guidelines-data-layer]: AsyncOpenAI client only instantiated when OPENAI_API_KEY present — API starts in fallback-only mode without credentials
- [Phase 01-guidelines-data-layer]: AdviceRecord is frozen dataclass (not Pydantic) — immutable value type; AdviceResponse Pydantic model handles API serialisation boundary
- [Phase 01-guidelines-data-layer]: TestClient used without context manager to avoid triggering FastAPI lifespan — same pattern as test_predict_endpoint.py
- [Phase 01-guidelines-data-layer]: pytestmark = pytest.mark.asyncio at module level covers all async tests in STRICT asyncio mode
- [Phase 01-guidelines-data-layer]: Fresh GuidelinesService instance per label in test_all_67_labels_do_not_raise avoids cache interference between label iterations
- [Phase 01-guidelines-data-layer]: lifespan catches FileNotFoundError and sets app.state.model = None — server always starts
- [Phase 01-guidelines-data-layer]: 503 guard placed before content-type check in /predict — model unavailability is checked first
- [Phase 01-guidelines-data-layer]: pydantic-settings empty string env vars override str field defaults — use commented-out entries in env files to document override points without breaking defaults
- [Phase 01-guidelines-data-layer]: guidelines_data_path default uses _PROJECT_ROOT = Path(__file__).parent.parent.parent for CWD-independent absolute path resolution
- [Phase 01-guidelines-data-layer]: data/ directory provided at runtime via volume mount only — cannot COPY from Dockerfile because build context ./api excludes project root

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: recyclingnearyou.com.au HTML structure must be validated live before scraper design is finalised — research flag active
- [Phase 1]: classifier label-to-RNY category mapping completeness is unknown; `label_to_rny.json` is a Phase 1 deliverable
- [Phase 4]: iOS HEIC image handling must be tested on a physical device before any user testing

## Session Continuity

Last session: 2026-02-26
Stopped at: Completed 01-guidelines-data-layer Plan 04 (gap closure — graceful model-load failure)
Resume file: None
