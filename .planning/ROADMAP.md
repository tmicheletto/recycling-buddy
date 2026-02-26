# Roadmap: Recycling Buddy

## Overview

v1.0 delivers a working end-to-end recycling advisor across four phases. Phase 1 builds the guidelines data layer — the critical path item that everything else depends on. Phase 2 builds the council resolution service in parallel once the slug format is established. Phase 3 wires the data layer and council service into the advice API, connecting the existing classifier to structured bin decisions. Phase 4 assembles the mobile UX: photo capture, geolocation flow, confidence-aware display, and text search — the integration layer that delivers the core value to users.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Guidelines Data Layer** - Scrape recyclingnearyou.com.au into a versioned static dataset and build the lookup service
- [ ] **Phase 2: Council Resolution Service** - Resolve browser GPS coordinates and postcodes to Australian council slugs
- [ ] **Phase 3: Advice API** - Serve structured bin decisions by connecting classification output to the guidelines dataset
- [ ] **Phase 4: Mobile UX Integration** - Deliver the complete photo-to-advice flow on mobile with geolocation, confidence handling, and text search

## Phase Details

### Phase 1: Guidelines Data Layer
**Goal**: An LLM-backed guidelines lookup service exists and can be queried by (item_category, council_slug) to return a structured bin decision grounded in recyclingnearyou.com.au page content
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02
**Success Criteria** (what must be TRUE):
  1. All 67 classifier labels resolve through the `label_to_rny.json` mapping table to at least one RNY material slug (or an explicit "unmapped" entry)
  2. A lookup call for a known (item_category, council_slug) pair returns bin colour, bin name, prep instructions, disposal method, and special_disposal_flag
  3. A lookup call for an unmapped (item_category, council_slug) pair returns a documented fallback (is_fallback=True, general waste, disclaimer) rather than raising an error
  4. GET /advice?item_category=...&council_slug=... returns 200 with the AdviceResponse schema; missing params return 422
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Produce label_to_rny.json mapping all 67 classifier labels to RNY item slugs
- [ ] 01-02-PLAN.md — Implement GuidelinesService (LLM lookup + cache) and wire GET /advice endpoint
- [ ] 01-03-PLAN.md — Write unit and integration tests for GuidelinesService and /advice

### Phase 2: Council Resolution Service
**Goal**: The API can resolve a user's location — either GPS coordinates or a postcode — to a council slug that matches the guidelines dataset
**Depends on**: Phase 1 (slug format established in Phase 1 JSON files must match resolution output)
**Requirements**: CNCL-01, CNCL-02
**Success Criteria** (what must be TRUE):
  1. A `GET /council?lat=...&lng=...` call with valid Australian coordinates returns the correct council slug via Nominatim reverse geocoding
  2. A `GET /council?postcode=...` call with a valid Australian postcode returns the matching council slug via the ABS postcode-to-LGA table
  3. A `GET /council` call with denied or missing geolocation returns a clear error code (not a 500) that the frontend can use to prompt postcode entry
  4. The resolved council slug for a major city (e.g. Melbourne, Sydney) matches an entry in the guidelines dataset
**Plans**: TBD

### Phase 3: Advice API
**Goal**: Users can submit a classified item and a council slug and receive a structured, council-specific bin decision from a working API endpoint
**Depends on**: Phase 1 (guidelines dataset), Phase 2 (council slug format)
**Requirements**: CLSF-01, CLSF-02, ADVS-01, ADVS-02, ADVS-03
**Success Criteria** (what must be TRUE):
  1. A `POST /predict` call with a photo returns the top-predicted item category and confidence score (existing endpoint connected to the advice flow)
  2. A `GET /advice?item_category=...&council_slug=...` call returns bin colour, bin name, prep instructions, and disposal method for a known item+council combination
  3. When the `/advice` response indicates special disposal, the result includes a distinct disposal type (not a bin colour) indicating the item cannot go in any kerbside bin
  4. When the classified item falls below confidence threshold 0.65, the API response includes top alternative classifications with their confidence scores
  5. A `GET /advice` call for an unmapped item+council combination returns a graceful "check with your council" response rather than a 500
**Plans**: TBD

### Phase 4: Mobile UX Integration
**Goal**: A user on a mobile device can photograph a waste item and see council-specific bin advice in a single uninterrupted flow, with fallbacks for geolocation denial and low-confidence results
**Depends on**: Phase 1, Phase 2, Phase 3
**Requirements**: FEND-01, FEND-02
**Success Criteria** (what must be TRUE):
  1. A user who permits geolocation can go from opening the app to seeing council-specific bin advice after one photo capture, with no manual council-selection step
  2. A user who denies geolocation is immediately shown a postcode entry field and can complete the full advice flow after entering their postcode
  3. When the classifier confidence is below 0.65, the user sees the top alternative classifications and can tap to confirm or correct before advice is shown
  4. A user can type a waste item name and receive bin advice without using the camera
  5. The app functions correctly on iOS Safari including images captured via `<input capture>` (HEIC images are normalised to JPEG before upload)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Guidelines Data Layer | 2/3 | In Progress|  |
| 2. Council Resolution Service | 0/TBD | Not started | - |
| 3. Advice API | 0/TBD | Not started | - |
| 4. Mobile UX Integration | 0/TBD | Not started | - |
