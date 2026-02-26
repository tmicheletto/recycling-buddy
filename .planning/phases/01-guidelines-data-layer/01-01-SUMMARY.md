---
phase: 01-guidelines-data-layer
plan: 01
subsystem: data
tags: [json, mapping, rny, classifier-labels, recyclingnearyou]

# Dependency graph
requires: []
provides:
  - "data/label_to_rny.json — 67-entry mapping table from classifier label to RNY material page slug"
  - "Verified canonical RNY slug inventory (49 slugs from multiple council pages)"
affects:
  - 01-guidelines-data-layer
  - GuidelinesService (Plan 02) — consumes label_to_rny.json to construct RNY URLs for LLM grounding

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RNY URL pattern: https://recyclingnearyou.com.au/material/home/{slug}"
    - "Council page URL pattern: https://recyclingnearyou.com.au/council/{CouncilNameState}"
    - "Mapping schema: {rny_slug: string|null, rny_url: string|null, notes: string}"

key-files:
  created:
    - data/label_to_rny.json
  modified: []

key-decisions:
  - "55/67 labels mapped to real RNY slugs; 12 unmapped entries have explanatory notes (no suitable RNY page exists)"
  - "RNY A-Z index page returned 404; council pages are the reliable source for slug discovery"
  - "Several broad classifier labels (food-packaging, disposable-cutlery-plates) mapped to best-fit RNY page with LLM clarification note — pages provide useful disposal context even if not a direct match"
  - "Compostable items mapped to garden-organics with caveats rather than left unmapped — RNY page gives correct FOGO bin guidance"
  - "Ceramics and glass-mirrors mapped to demolition as closest RNY hard-waste category"

patterns-established:
  - "Mapping pattern: exact label match → check slug variations → find closest RNY category → if none, set null with reason"
  - "Notes field documents edge cases and LLM guidance directives (e.g. 'LLM must clarify...')"

requirements-completed: [DATA-01]

# Metrics
duration: 5min
completed: 2026-02-26
---

# Phase 1 Plan 1: Label-to-RNY Mapping Table Summary

**67-entry JSON mapping table from EfficientNet classifier labels to recyclingnearyou.com.au material page slugs, with 55/67 labels mapped and 12 unmapped with explanatory notes**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-26T03:50:18Z
- **Completed:** 2026-02-26T03:55:16Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments
- Discovered canonical RNY slug inventory by fetching multiple council pages (49 unique slugs from SydneyNSW, MelbourneVIC, BrisbaneQLD, and others)
- Mapped 55 of 67 classifier labels to verified RNY material page slugs
- Documented all 12 unmapped labels with explanatory notes explaining why no suitable RNY page exists
- All 67 entries follow schema: rny_slug, rny_url, notes — ready for GuidelinesService consumption

## Task Commits

Each task was committed atomically:

1. **Task 1: Fetch RNY material index and build label_to_rny.json** - `430efd0` (feat)

**Plan metadata:** _(final metadata commit pending)_

## Files Created/Modified
- `/Users/tim/code/recycling-buddy/data/label_to_rny.json` — 67-entry mapping table, classifier label → RNY slug + URL + notes

## Decisions Made
- The RNY A-Z index page (`/recycling-a-to-z/`) returns 404; council pages (`/council/{Name}`) reliably expose all available material slugs via hyperlinks.
- 49 unique RNY slugs are available across all Australian councils (same set regardless of council).
- Several classifier categories are presentation-based (`bagged-recyclables`, `bagged-rubbish`) rather than material-based — these are correctly left unmapped as RNY does not address presentation in its taxonomy.
- Broad classifier labels like `food-packaging` and `disposable-cutlery-plates` were mapped to the most relevant RNY page with notes directing the LLM to refine advice by specific material sub-type.
- Compostable items (`compostable-liners`, `compostable-packaging`) mapped to `garden-organics` rather than left null — the FOGO guidance on that page is directly relevant even if compostable packaging is not explicitly mentioned.

## Deviations from Plan

None - plan executed exactly as written. The fallback URL strategy (try multiple pages when A-Z is unavailable) was pre-planned in the task action.

## Issues Encountered
- The RNY A-Z listing page (`/recycling-a-to-z/`) returns HTTP 404 — fell back to council pages as specified in the task action fallback strategy.
- The `/material/home/` index also returns 404; council pages at `/council/{CouncilNameState}` are the correct source for slug discovery.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `data/label_to_rny.json` is complete and validated — GuidelinesService (Plan 02) can consume it immediately
- RNY URL pattern confirmed: `https://recyclingnearyou.com.au/material/home/{slug}`
- 12 unmapped labels will fall through to LLM training-data-only mode (no grounding) — acceptable for v1

---
*Phase: 01-guidelines-data-layer*
*Completed: 2026-02-26*

## Self-Check: PASSED

- FOUND: data/label_to_rny.json
- FOUND: .planning/phases/01-guidelines-data-layer/01-01-SUMMARY.md
- FOUND: commit 430efd0
