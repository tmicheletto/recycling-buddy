# Requirements: Recycling Buddy

**Defined:** 2026-02-26
**Milestone:** v1.0 — Recycling Advice System
**Core Value:** A user can photograph any household waste item and immediately know exactly which bin it belongs in, based on their council's actual rules.

## v1.0 Requirements

### Data Layer

- [x] **DATA-01**: System can scrape item-category recycling rules from recyclingnearyou.com.au for all available Australian councils and persist as a versioned static JSON dataset in the repo
- [x] **DATA-02**: System can look up (item_category, council) and return bin type, bin colour (lid colour), prep instructions, and disposal method from the static dataset

### Council Resolution

- [ ] **CNCL-01**: App can resolve a user's local council from browser geolocation (GPS coordinates → reverse geocode via Nominatim → LGA/council name)
- [ ] **CNCL-02**: User can manually enter a postcode to select their council when geolocation is unavailable, fails, or is denied

### Classification Flow

- [ ] **CLSF-01**: User can photograph a waste item and receive the top-predicted category with a confidence score (connecting existing /predict endpoint to the advice flow)
- [ ] **CLSF-02**: User sees the top alternative classifications with confidence scores when the top prediction falls below the uncertainty threshold, and can confirm or correct the classification before advice is shown

### Advice Display

- [ ] **ADVS-01**: User sees which bin to use — bin colour (lid colour) and bin name — for their classified item, specific to their resolved council
- [ ] **ADVS-02**: User sees prep instructions (e.g. rinse, flatten, remove lid) for their classified item in the result card when instructions are available in the guidelines data
- [ ] **ADVS-03**: User is shown a distinct special-disposal result (not a bin colour) for items that cannot go in any kerbside bin, indicating the item requires drop-off or special collection

### Frontend / UX

- [ ] **FEND-01**: User can go from photographing a waste item to seeing council-specific bin advice in a single uninterrupted mobile-first flow without a manual council-selection step (when geolocation is permitted)
- [ ] **FEND-02**: User can search for a waste item by name and receive bin advice as an alternative to photo capture (fallback for failed captures or low-confidence results)

## v2 Requirements

### Drop-off & Facilities

- **DROP-01**: User can follow a deep-link to recyclingnearyou.com.au to find a drop-off facility for their item
- **DROP-02**: User can view a map of nearby drop-off locations for special disposal items

### Engagement

- **ENGD-01**: User can view their past scan history
- **ENGD-02**: User receives bin night reminders for their council

## Out of Scope

| Feature | Reason |
|---------|--------|
| Native iOS/Android app | Web-first for prototype; app store adds friction and development overhead |
| User accounts and authentication | Auth infrastructure out of scope for prototype; advice is stateless |
| Bin night reminders | Requires council calendar data not available from recyclingnearyou.com.au + push notification infra |
| Nearest drop-off map (embedded) | Requires separate facility database and maps API; link to recyclingnearyou.com.au is sufficient for v1 |
| Barcode scanning | Requires product → packaging material database separate from current classifier |
| Global coverage (non-Australian councils) | Entire data layer is Australia-specific; international requires rebuilding data pipeline |
| Gamification | Anti-feature for prototype; risks engagement gaming over utility |
| Confidence threshold below 0.65 | Research-established threshold; lower values produce unreliable advice |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| CNCL-01 | Phase 2 | Pending |
| CNCL-02 | Phase 2 | Pending |
| CLSF-01 | Phase 3 | Pending |
| CLSF-02 | Phase 3 | Pending |
| ADVS-01 | Phase 3 | Pending |
| ADVS-02 | Phase 3 | Pending |
| ADVS-03 | Phase 3 | Pending |
| FEND-01 | Phase 4 | Pending |
| FEND-02 | Phase 4 | Pending |

**Coverage:**
- v1.0 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after roadmap creation*
