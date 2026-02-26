# Project Research Summary

**Project:** Recycling Buddy — Australian council recycling advice app
**Domain:** Mobile web app (photo classification + council-local waste sorting advice)
**Researched:** 2026-02-26
**Confidence:** HIGH

## Executive Summary

Recycling Buddy is a mobile web application that combines an existing AI waste classifier (EfficientNet-B0, 67 categories, already built) with council-specific recycling rules to give Australians accurate bin advice from a photo. The standard architecture for this domain is: photo → ML classification → council resolution (GPS + reverse geocoding) → static guidelines lookup → advice card. The key insight from research is that the classifier already exists; the remaining work is entirely in the data layer (scraping recyclingnearyou.com.au) and the integration layer (connecting classification output to council rules). No new ML work is required.

The recommended approach is to build a static JSON guidelines dataset at scrape time (not at request time), resolve councils via browser GPS + Nominatim reverse geocoding + ABS postcode-to-LGA correspondence table, and serve advice from an in-memory dict loaded at API startup. The entire tech stack already exists in the repo (FastAPI, React 19, httpx); only `requests`, `beautifulsoup4`, `lxml`, and `tenacity` need to be added for the scraper. The differentiating UX opportunity — photo-first with automatic council resolution in a single uninterrupted flow — is not done well by any existing Australian app.

The primary risks are data quality (recyclingnearyou.com.au structure instability, classifier-label-to-RNY-category mismatches, incomplete council coverage) and UX trust (low-confidence predictions shown as definitive advice, geolocation denial breaking the core flow). Both risks have clear mitigations that must be designed in from the start, not bolted on later. The postcode fallback for geolocation denial and a confidence threshold (0.65) for classification uncertainty are non-negotiable for v1.

## Key Findings

### Recommended Stack

The existing stack handles everything except the scraper and council resolution. FastAPI 0.128, React 19, httpx 0.28, and uv are already in use. Add `requests` + `beautifulsoup4` + `lxml` + `tenacity` for the build-time scraper. Use the browser Geolocation API (no library) and Nominatim public instance (no API key) for council resolution. Commit the ABS ASGS postcode-to-LGA CSV as processed JSON — it is a one-time download updated annually.

**Core technologies:**
- `requests` + `beautifulsoup4` + `lxml`: build-time scraper for recyclingnearyou.com.au — server-rendered HTML, BS4 sufficient (no Playwright needed)
- `tenacity`: retry with exponential backoff for polite scraping (1 req/sec, 3 retries on 429/5xx)
- `httpx` (existing): async Nominatim calls from FastAPI `/council` endpoint
- Browser Geolocation API: GPS coords from device — built-in, HTTPS required (already enforced)
- ABS ASGS correspondence files: free postcode-to-LGA CSV, commit as JSON, ~2,800 entries in memory
- Nominatim public instance: free reverse geocoding, 1 req/sec limit, no key required

**Explicitly avoid:** Scrapy (overkill), Playwright (unnecessary for static HTML), Google Maps (paid, no map shown), Redux/Zustand (state is simple), service workers (not in scope).

### Expected Features

The classifier already exists. The gap is connecting it to a council-local advice layer. All major Australian recycling apps (RecycleRight, RecycleSmart, Recycle Mate) provide bin colour + prep instructions + special disposal notices. The differentiator is the single uninterrupted photo→council→advice flow with automatic geolocation — no existing Australian app does this without a manual council-selection step.

**Must have (table stakes):**
- Photo capture → classification → council-local bin advice in one mobile flow — core value proposition
- Bin colour display (red/yellow/green lid, council-specific) — users read lid colour, not bin names
- Council-local advice (rules vary significantly between LGAs) — without this, advice is unreliable
- Prep instructions in result card — "rinse, flatten, remove lid" — low complexity, high contamination reduction
- Special disposal notice as a distinct result state — batteries, e-waste cannot go in any kerbside bin
- Geolocation council resolution with manual postcode fallback — geolocation alone fails for ~20% of users
- Low-confidence/uncertain result handling — show top-3 alternatives below confidence threshold (0.65)
- Guidelines data layer from recyclingnearyou.com.au — data backbone; nothing else works without it

**Should have (competitive):**
- Confidence-aware classification display — no Australian app currently shows this; builds user trust
- Graceful out-of-taxonomy handling — clear "I don't recognise this, try searching by name" below threshold
- Text search / item name fallback — for failed or low-confidence photo captures
- Deep-link to recyclingnearyou.com.au for drop-off facility search

**Defer (v2+):**
- Bin night reminders (requires push notification infrastructure + council calendar data)
- Nearest drop-off map (requires separate facility database + maps API)
- User accounts and scan history (requires auth infrastructure)
- Barcode scanning (requires separate product-to-material database)
- Gamification (anti-feature for prototype; defer until core utility validated)

### Architecture Approach

Three FastAPI endpoints cover the new functionality: `/council` (lat/lng → council_slug via Nominatim + ABS postcode table), `/advice` (item_category + council_slug → bin decision from in-memory JSON), and the existing `/predict` (unchanged). The frontend orchestrates two sequential calls after photo capture: `/predict` then `/advice`. Council resolution happens once per session and is cached in React state. The guidelines store is a static JSON dataset scraped at build time, loaded into memory at API startup — zero runtime latency, no external dependency during inference.

**Major components:**
1. `scripts/scrape_guidelines.py` — one-time build tool; scrapes 560 councils from recyclingnearyou.com.au into `data/guidelines/rules/*.json`
2. `api/src/guidelines.py` (GuidelinesService) — loads JSON at startup; O(1) dict lookup by (council_slug, item_category)
3. `api/src/council.py` (CouncilService) — async Nominatim call + ABS postcode table lookup; resolves lat/lng to council_slug
4. `api/src/main.py` — adds `/council` and `/advice` routes to existing FastAPI app
5. `ui/src/hooks/useGeolocation.ts` + `useRecyclingAdvice.ts` — orchestrates GPS → council → photo → advice flow
6. `ui/src/components/ResultCard.tsx` — bin colour + item name + instructions + confidence state display
7. `label_to_rny.json` — explicit mapping table from 67 classifier labels to RNY material slugs (critical artifact)

### Critical Pitfalls

1. **recyclingnearyou.com.au structure instability** — treat the scrape as a one-time seed operation, not a live API. Write defensively: assert expected selectors exist, fail loudly on zero results. Validate against City of Melbourne as a known-good council. Build resumability (per-council output files) before the first scrape run.

2. **Classifier label to council rule category mismatch** — build an explicit `label_to_rny.json` mapping table; never rely on exact string match between 67 classifier labels and RNY material slugs. Write a unit test asserting all 67 labels resolve to at least one rule entry in a mock store. Return "check with your council" for unmapped labels, never a 500.

3. **Geolocation denial breaks core flow** — design the denied state first. Show a postcode entry field immediately on `PERMISSION_DENIED`. Never call `getCurrentPosition()` without an error callback. Cache resolved council name (not coordinates) in localStorage. Prompt for geolocation after photo capture, not on page load.

4. **Low-confidence predictions displayed as definitive advice** — define `CONFIDENCE_THRESHOLD = 0.65` as a named constant from day one. Below threshold, render "I'm not sure — here are the most likely options" with top-3 alternatives. The API already returns `alternatives`; the UI must use them.

5. **iOS HEIC images cause silent 500 errors** — the backend only accepts JPEG/PNG magic bytes. Add frontend Canvas-based normalisation (draw image to canvas, export as JPEG at 0.85 quality) before POSTing to `/predict`. Also resize to max 1024px longest dimension for mobile 4G performance. Test on a physical iPhone before any user testing.

## Implications for Roadmap

Based on the dependency chain in ARCHITECTURE.md and pitfall phase mappings in PITFALLS.md:

### Phase 1: Guidelines Data Layer
**Rationale:** Everything else depends on this data existing. The scraper must run before GuidelinesService can be built, before `/advice` can be tested, before the frontend flow can be integrated. This is the critical path item with the most unknowns (site structure stability, coverage gaps, label mapping).
**Delivers:** `data/guidelines/rules/*.json` (560 councils), `data/guidelines/councils.json` (index), `label_to_rny.json` (mapping table), `scraped_at` timestamp in schema.
**Addresses:** Guidelines data layer (table stakes), prep instructions data, special disposal data.
**Avoids:** Pitfall 1 (site instability — resumable scraper, defensive assertions), Pitfall 2 (label mismatch — build mapping table here), Pitfall 8 (staleness — `scraped_at` field in schema).
**Research flag:** Needs `/gsd:research-phase` — site structure must be validated live before scraper design is finalised. The Brisbane council page defers to an external URL; coverage gaps need a documented strategy.

### Phase 2: Council Resolution Service
**Rationale:** Can be built and tested independently of the frontend. Requires ABS postcode CSV (one-time download) and Nominatim integration. No dependency on Phase 1 data being complete, but the postcode-to-LGA table and council_slug format must be consistent with the slugs used in Phase 1 JSON files.
**Delivers:** `api/src/council.py` (CouncilService), `api/src/services/geocode.py` (Nominatim helper), `/council` FastAPI endpoint, ABS postcode→LGA JSON bundled in `data/`.
**Uses:** httpx (existing), Nominatim public instance, ABS ASGS correspondence files.
**Avoids:** Pitfall 5 (boundary accuracy — explicitly choose postcode-based approach, document as prototype decision), Pitfall 9 (geolocation timeout — `{ timeout: 8000, maximumAge: 300000 }` options object).
**Research flag:** Standard patterns — skip research-phase. ABS data is well-documented; Nominatim API is stable.

### Phase 3: Advice API Endpoint
**Rationale:** Bridges Phase 1 data and Phase 2 council resolution. Requires Phase 1 JSON files to exist (even a partial dataset for testing). GuidelinesService loaded at startup; `/advice` endpoint returns structured decision.
**Delivers:** `api/src/guidelines.py` (GuidelinesService), `/advice` FastAPI endpoint, response schema with bin colour enum, unmapped-label fallback ("check with your council"), integration tests.
**Implements:** GuidelinesService (Pattern 1 from ARCHITECTURE.md), Aggregated Advice Endpoint (Pattern 3).
**Avoids:** Pitfall 2 (label mismatch — unit test all 67 labels against mock store), Anti-pattern 1 (no runtime scraping), Anti-pattern 3 (no direct label-to-RNY assumption), Anti-pattern 4 (no silent fallback to wrong-council rules).
**Research flag:** Standard patterns — skip research-phase.

### Phase 4: Mobile UX Integration
**Rationale:** Final assembly layer. Depends on Phases 1-3 being functional. Frontend orchestrates GPS → council → photo → advice in one flow. This phase carries the most UX pitfall risk (iOS HEIC, geolocation denial, confidence display).
**Delivers:** `useGeolocation.ts` hook (with postcode fallback), `useRecyclingAdvice.ts` hook (predict → advice orchestration), `ResultCard.tsx` (bin colour + instructions + confidence states), `CouncilBanner.tsx`, mobile-optimised camera flow, Canvas-based image normalisation + resize.
**Addresses:** Photo-first single flow (differentiator), confidence-aware display (differentiator), all table-stakes UX features.
**Avoids:** Pitfall 3 (geolocation denial — postcode fallback, post-capture prompt), Pitfall 4 (low confidence — CONFIDENCE_THRESHOLD constant, top-3 alternatives), Pitfall 7 (iOS HEIC — Canvas normalisation before upload), Performance trap (image resize before upload).
**Research flag:** May need targeted research on Canvas-based HEIC normalisation browser support and iOS Safari-specific behaviour. Otherwise standard React patterns.

### Phase Ordering Rationale

- Data before services: GuidelinesService cannot be meaningfully tested without real council data; the label mapping must be built while examining the actual RNY taxonomy.
- Services before UI: the frontend hooks depend on both `/council` and `/advice` being functional; building UI first against mocks risks rework when real data reveals taxonomy gaps.
- Geolocation denial and confidence threshold are designed in Phase 4, not retrofitted — the PITFALLS research is clear that these are "looks done but isn't" failure modes when left to the end.
- Council resolution (Phase 2) and advice endpoint (Phase 3) can be developed in parallel once Phase 1 data extraction is underway, as they have no dependency on each other.

### Research Flags

Needs `/gsd:research-phase` during planning:
- **Phase 1 (Guidelines Data Layer):** recyclingnearyou.com.au HTML structure must be validated live before scraper design is locked. Coverage gap strategy (councils that defer to external URLs) needs a concrete decision.

Standard patterns — skip research-phase:
- **Phase 2 (Council Resolution):** ABS ASGS data and Nominatim API are well-documented with stable interfaces.
- **Phase 3 (Advice API):** FastAPI service patterns and in-memory dict loading are standard; GuidelinesService pattern is fully specified in ARCHITECTURE.md.
- **Phase 4 (Mobile UX):** React hooks and browser API integration are standard; Canvas-based HEIC workaround is an established pattern. Targeted iOS Safari testing is needed but not pre-research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified against existing codebase; only scraper libs are new additions; version compatibility confirmed |
| Features | HIGH | Competitive analysis covers all major Australian recycling apps; MVP scope well-bounded by PROJECT.md constraints |
| Architecture | HIGH | Data flow fully specified; component boundaries clear; build order implications derived from concrete dependencies |
| Pitfalls | HIGH | Most pitfalls verified against direct site inspection (recyclingnearyou.com.au robots.txt, URL structure), MDN docs (iOS HEIC, geolocation), and ABS data characteristics |

**Overall confidence:** HIGH

### Gaps to Address

- **Council coverage rate:** Unknown what percentage of 560 councils have complete item-to-bin data on recyclingnearyou.com.au vs. deferring to external council websites. Must be measured during Phase 1 scraping. Strategy: return `accepted: null` + "check your council's website" for gaps — do not use another council's rules as a fallback.
- **Label-to-RNY mapping completeness:** The 67 classifier labels were defined in phase 001; their correspondence to RNY material slugs has not been validated. This mapping table is a Phase 1 deliverable; gaps discovered here may require fallback labels or UI display name changes.
- **Nominatim accuracy for rural postcodes:** Reverse geocoding accuracy in rural/remote Australia (where council boundaries are large but postcodes may be sparse) is untested. Acceptable for prototype; document as a known limitation.
- **recyclingnearyou.com.au TOS compliance:** Planet Ark permits personal/educational use but not redistribution of scraped data. The scraped JSON must be treated as internal seed data only, not exposed as a public API or redistributed.

## Sources

### Primary (HIGH confidence)
- recyclingnearyou.com.au — direct inspection: server-rendered HTML, open robots.txt, predictable URL structure, ~560 councils
- ABS ASGS Edition 3 Correspondence Files (abs.gov.au) — postcode-to-LGA CSV, free, updated annually
- Nominatim Reverse Geocoding API (nominatim.org) — usage policy confirmed: User-Agent required, 1 req/sec on public instance
- MDN Web Docs — Geolocation API error codes, `<input capture>` behaviour, HEIC/canvas workaround
- `.planning/codebase/STACK.md` — existing stack inventory (FastAPI 0.128, React 19.2, Vite 7.2, httpx 0.28)

### Secondary (MEDIUM confidence)
- Recycle Mate app (Dreamwalk case study) — confirms photo→council→bin as standard Australian app architecture
- RecycleSmart / RecyclingNearYou (Planet Ark) — confirms 500+ council integration pattern; manual council selection as current norm
- RecycleRight WA — feature baseline for bin colour, prep instructions, special disposal
- Cleanaway Aussie Recycling Behaviours 2023 — geolocation denial rate (~20-30% on first request)
- ScienceDirect gamification study — evidence that utility > gamification for recycling app retention

### Tertiary (LOW confidence)
- Nominatim rural accuracy — inferred from general OSM coverage characteristics; needs empirical validation in Phase 1
- Confidence threshold 0.65 — suggested starting point based on transfer-learned classifier overconfidence patterns; must be calibrated from real usage data

---
*Research completed: 2026-02-26*
*Ready for roadmap: yes*
