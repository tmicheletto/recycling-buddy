# Architecture Research

**Domain:** Australian recycling advice app — council guidelines data layer
**Researched:** 2026-02-26
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser (React + TypeScript)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ CameraCapture│  │CouncilResolver│  │    ResultDisplay         │   │
│  │ (photo input)│  │(geolocation) │  │ (bin + instructions)     │   │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │
│         │                 │                        │                  │
│         │ multipart/form  │ lat/lng                │                  │
└─────────┼─────────────────┼────────────────────────┼──────────────────┘
          │                 │                        │
          ▼                 ▼                        │
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI (AWS ECS Fargate)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  /predict    │  │  /council    │  │     /advice              │   │
│  │(EfficientNet)│  │(lat/lng→LGA) │  │ (item+council→decision)  │   │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │
│         │                 │                        │                  │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌────────────┴─────────────┐   │
│  │ClassificationM│  │CouncilService│  │     GuidelinesService    │   │
│  │    odel      │  │(postcode map)│  │  (item+council→bin)      │   │
│  └──────────────┘  └──────────────┘  └────────────┬─────────────┘   │
└────────────────────────────────────────────────────┼──────────────────┘
                                                     │
                                          ┌──────────┴──────────┐
                                          │   Guidelines Store   │
                                          │  (JSON files in      │
                                          │   container or S3)   │
                                          └─────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| CameraCapture | Capture photo via browser camera or file input | React component using `<input type="file" capture="environment">` |
| CouncilResolver | Obtain device GPS coords, resolve to LGA slug | Browser Geolocation API + reverse-geocode call |
| ResultDisplay | Show bin colour, item name, instructions | React component consuming /advice response |
| /predict route | Classify image → item_category label | Existing EfficientNet-B0 FastAPI endpoint |
| /council route | lat/lng → council_slug | Postcode/suburb lookup against bundled mapping |
| /advice route | (item_category, council_slug) → recycling decision | Lookup in guidelines data; returns bin + instructions |
| CouncilService | Resolve coordinates to a council slug | Point-in-polygon or postcode→LGA correspondence table |
| GuidelinesService | Query guidelines store for a given item+council pair | In-memory dict loaded from JSON at startup |
| Guidelines Store | (council_slug, item_category) → {bin, instructions, accepted} | Static JSON files, scraped and curated from recyclingnearyou.com.au |

## Recommended Project Structure

```
api/
├── src/
│   ├── main.py                   # existing — add /council and /advice routes
│   ├── labels.py                 # existing — 67 item categories
│   ├── inference.py              # existing — EfficientNet-B0
│   ├── config.py                 # existing — extend with guidelines path
│   ├── council.py                # NEW — CouncilService (lat/lng → council_slug)
│   ├── guidelines.py             # NEW — GuidelinesService (item+council → decision)
│   └── services/
│       ├── s3.py                 # existing
│       └── geocode.py            # NEW (optional) — Nominatim reverse geocode helper
│
data/
├── guidelines/
│   ├── councils.json             # council_slug → display_name, state, postcode list
│   └── rules/
│       ├── SydneyNSW.json        # item_category → {bin, accepted, instructions}
│       ├── BrisbaneQLD.json
│       └── ...                   # one file per council (560 total)
│
scripts/
└── scrape_guidelines.py          # one-time scraper: recyclingnearyou.com.au → data/guidelines/
│
ui/
└── src/
    ├── components/
    │   ├── PhotoCapture.tsx       # existing — extend for /predict flow
    │   ├── ResultCard.tsx         # NEW — bin colour + instructions display
    │   └── CouncilBanner.tsx      # NEW — show resolved council name
    ├── hooks/
    │   ├── useGeolocation.ts      # NEW — browser GPS + /council call
    │   └── useRecyclingAdvice.ts  # NEW — orchestrates predict → advice flow
    └── services/
        └── api.ts                 # existing — add council() and advice() calls
```

### Structure Rationale

- **data/guidelines/:** Bundled static JSON means zero runtime latency for council lookup — no external dependency during inference. One file per council keeps updates surgical.
- **scripts/scrape_guidelines.py:** Scraper is a build-time tool, not a runtime dependency. Run once (or on a schedule) to refresh the dataset; commit output to repo or publish to S3.
- **api/src/council.py:** Council resolution is kept in the API, not the browser, so the postcode→LGA mapping table isn't downloaded by every client.
- **data/guidelines/councils.json:** A flat index of all 560+ councils (slug, state, postcodes, display name) enables both /council lookup and frontend display.

## Architectural Patterns

### Pattern 1: Static Dataset (Recommended for v1)

**What:** Scrape recyclingnearyou.com.au once at build time. Store output as JSON files checked into the repo (or uploaded to S3). Load into memory at API startup. No runtime dependency on external sites.

**When to use:** Prototype scope; data changes infrequently (council rules update yearly at most); reliability matters more than freshness.

**Trade-offs:** Data can become stale; a refresh script must be re-run to update. But eliminates scraping at request time, avoids rate-limit risk, and keeps p99 latency predictable.

**Example:**

```python
# guidelines.py — load at startup, query in O(1)
import json, pathlib

class GuidelinesService:
    def __init__(self, rules_dir: pathlib.Path):
        self._rules: dict[str, dict] = {}
        for path in rules_dir.glob("*.json"):
            council_slug = path.stem
            self._rules[council_slug] = json.loads(path.read_text())

    def lookup(self, council_slug: str, item_category: str) -> dict | None:
        council_rules = self._rules.get(council_slug)
        if not council_rules:
            return None
        return council_rules.get(item_category)
```

### Pattern 2: Postcode-to-Council Table (Council Resolution)

**What:** ABS correspondence files map every Australian postcode to its LGA. Store as a bundled dict `{postcode: council_slug}`. Browser sends GPS coords; API reverse-geocodes to postcode/suburb via Nominatim (free, no key), then looks up the table.

**When to use:** Always — it is the right primitive for this scale. 560 councils × average 5 postcodes = ~2,800 entries; trivially in-memory.

**Trade-offs:** Postcodes are not perfect LGA proxies (some postcodes span multiple councils), but ABS correspondence files handle this with population-weighted allocation. Sufficient for a prototype. If accuracy is critical, upgrade to point-in-polygon against ABS ASGS boundary files (GeoJSON shapefiles, ~10 MB download).

**Example:**

```python
# council.py — postcode → slug lookup
POSTCODE_TO_COUNCIL: dict[str, str] = json.loads(
    (DATA_DIR / "councils.json").read_text()
)["postcode_index"]

async def resolve_council(lat: float, lng: float) -> str | None:
    postcode = await reverse_geocode_to_postcode(lat, lng)  # Nominatim call
    return POSTCODE_TO_COUNCIL.get(postcode)
```

### Pattern 3: Aggregated Advice Endpoint

**What:** Expose a single `/advice` endpoint that accepts `{item_category, council_slug}` and returns a structured recycling decision. The frontend calls `/predict` then `/advice` in sequence (or the API chains them internally in a `/classify-and-advise` composite endpoint).

**When to use:** Prefer two sequential calls from the frontend for simplicity and independent cacheability. Composite endpoint is worthwhile only if latency from two round-trips becomes a UX problem.

**Trade-offs:** Two calls keep predict and advice independently testable and cacheable (advice responses can be cached by (item, council) pair indefinitely). Composite is marginally faster but couples concerns.

**Example response from /advice:**

```json
{
  "council_slug": "SydneyNSW",
  "council_name": "City of Sydney Council",
  "item_category": "plastic-bottles-containers",
  "accepted": true,
  "bin": "yellow",
  "bin_label": "Recycling bin (yellow lid)",
  "instructions": "Empty and rinse. Leave lids on.",
  "source_url": "https://recyclingnearyou.com.au/council/SydneyNSW"
}
```

## Data Flow

### Full Request Flow (Photo → Recycling Decision)

```
[User opens app]
    ↓
[Browser: navigator.geolocation.getCurrentPosition()]
    ↓
[Frontend → POST /council {lat, lng}]
    ↓
[CouncilService: Nominatim reverse geocode → postcode → council_slug]
    ↓
[Frontend stores council_slug + council_name in React state]
    ↓
[User captures/selects photo]
    ↓
[Frontend → POST /predict (multipart image)]
    ↓
[ClassificationModel: EfficientNet-B0 forward pass → item_category + confidence]
    ↓
[Frontend → GET /advice?item={item_category}&council={council_slug}]
    ↓
[GuidelinesService: rules[council_slug][item_category] → {bin, instructions}]
    ↓
[Frontend renders ResultCard: bin colour + item name + instructions]
```

### Data Flow from Guidelines Build

```
[recyclingnearyou.com.au/councils/ page]
    ↓ (scraper: 560 council slugs)
[recyclingnearyou.com.au/council/{CouncilSlug} pages]
    ↓ (scraper: per-council item→bin mapping)
[data/guidelines/rules/{CouncilSlug}.json]
    ↓ (API startup: GuidelinesService.__init__)
[in-memory dict: {council_slug: {item_category: {bin, instructions}}}]
    ↓ (per-request: O(1) lookup)
[/advice response]
```

### Key Data Flows

1. **Geolocation resolution:** Browser GPS → /council endpoint → Nominatim API → postcode → bundled postcode→LGA table → council_slug. Happens once per session; cached in frontend state.
2. **Classification:** Photo bytes → /predict → EfficientNet-B0 → item_category label (one of the 67 labels in labels.py). Happens per photo.
3. **Guidelines lookup:** (item_category, council_slug) → GuidelinesService dict → bin colour + instructions. Sub-millisecond; in-memory.
4. **Fallback:** If council cannot be resolved (GPS denied, unknown postcode), surface a suburb/postcode text input to the user. If item has no rule for the resolved council, return the most common default (general waste bin red) and flag as "rule not found".

## Data Source: recyclingnearyou.com.au

**Access approach:** Web scraping is viable. The site's robots.txt has no disallow rules (empty Disallow directive — all crawlers permitted). The URL structure is fully predictable:

- Council index: `https://recyclingnearyou.com.au/councils/` — lists all ~560 councils with slugs
- Council page: `https://recyclingnearyou.com.au/council/{CouncilSlug}` — per-council item/bin info
- Material page: `https://recyclingnearyou.com.au/material/home/{category-slug}` — per-material guidance

**Data characteristics observed:**
- Some council pages (e.g., Brisbane) link to the council's own website for bin item detail rather than listing items directly on the RNY page. This is the main data quality risk — not all councils have complete item→bin mapping on RNY.
- The RNY material taxonomy (60+ categories) is related to but not identical to the 67 classifier labels. A mapping table between classifier labels and RNY material slugs is needed (e.g., `"plastic-bottles-containers"` → `"/material/home/plastic-containers"`).
- Bin types across Australian councils: yellow lid (recycling), red/black lid (general waste), green lid (organics/FOGO). Some NSW councils use blue lid (paper). Victoria rolling out purple lid (glass). Rules store bin as a normalised enum: `yellow | red | green | blue | purple | special`.

**Coverage gap strategy:** Where a council page on RNY defers to the council's own website, store `accepted: null` and `source_url` pointing to the council's page. Frontend shows "Check your council's website" rather than an incorrect answer.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Static JSON in container memory — current recommendation. No database needed. |
| 1k-100k users | Externalize guidelines to S3; load at startup. Add Redis cache for /council responses (Nominatim has rate limits at scale). |
| 100k+ users | Replace Nominatim with hosted geocoding (Google Maps, Geoapify). Consider DynamoDB for guidelines if per-council updates become frequent. |

### Scaling Priorities

1. **First bottleneck:** Nominatim rate limits (1 req/sec on public instance). Fix: either self-host a Nominatim instance on ECS, or use a paid geocoding API with higher limits. The /council call can also be cached by lat/lng bounding box.
2. **Second bottleneck:** Guidelines data staleness — council rules change without notice. Fix: scheduled scrape job (weekly cron on Lambda or GitHub Actions) to refresh JSON files and trigger a container redeploy.

## Anti-Patterns

### Anti-Pattern 1: Scraping at Request Time

**What people do:** Call recyclingnearyou.com.au live during a user request to fetch the latest council rules.

**Why it's wrong:** Introduces 500ms–2s latency on every advice lookup, creates a hard runtime dependency on an external site, and risks rate limiting or being blocked. The data changes at most yearly.

**Do this instead:** Scrape at build time. Commit the JSON dataset. Refresh on a schedule. Serve from memory.

### Anti-Pattern 2: Sending GPS Coordinates to the Client

**What people do:** Return the raw Nominatim response (full address with street, suburb, postcode) to the browser, then do the council lookup in JavaScript.

**Why it's wrong:** Requires the full postcode→council table to be downloaded to every client (privacy implications of precise location staying on backend, and unnecessary client bundle weight).

**Do this instead:** GPS coords go to /council; only `council_slug` and `council_name` come back. The mapping table lives server-side.

### Anti-Pattern 3: Direct Label-to-RNY-Category Assumption

**What people do:** Assume the 67 classifier labels map 1:1 to RNY material slugs and skip building a mapping table.

**Why it's wrong:** The taxonomies differ. The classifier uses `"plastic-bottles-containers"` but RNY uses separate slugs for different plastic types. Without an explicit mapping, lookup failures silently return no result.

**Do this instead:** Build and maintain a `label_to_rny.json` mapping table. During scraping, normalise RNY categories against the 67 classifier labels. Flag unmapped labels for manual review.

### Anti-Pattern 4: Ignoring Council Coverage Gaps

**What people do:** Return a confident bin decision for every item/council combination, using fallback rules from another council when the target council has no data.

**Why it's wrong:** Australian councils have meaningfully different rules. Using Sydney's rules for a rural NSW council can give incorrect answers.

**Do this instead:** Return `accepted: null` with an explicit `"rule_not_found"` flag and link to the council's own website. An honest "we don't know" is better than a wrong answer.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| recyclingnearyou.com.au | Build-time scrape (Python requests + BeautifulSoup) | robots.txt permits scraping; scrape politely (1 req/s, User-Agent header). One-time + periodic refresh. |
| Nominatim (OpenStreetMap) | API call from /council route (reverse geocode lat/lng → address) | Free public instance: 1 req/sec limit. Self-host via Docker for production. Returns suburb, postcode, county fields sufficient for LGA lookup. |
| ABS ASGS Correspondence Files | Build-time download (CSV: postcode → LGA) | Free, open, updated annually. Provides the postcode→council_slug mapping table. More reliable than Nominatim's `county` field for LGA resolution. |
| Browser Geolocation API | Frontend: `navigator.geolocation.getCurrentPosition()` | No external dependency. Must handle denial gracefully (fallback to manual suburb/postcode entry). HTTPS required. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Frontend ↔ /predict | multipart/form-data POST, returns `{label, confidence, categories}` | Existing endpoint; no change required |
| Frontend ↔ /council | JSON POST `{lat, lng}`, returns `{council_slug, council_name, state}` | New endpoint; resolves once per session |
| Frontend ↔ /advice | JSON GET `?item=<label>&council=<slug>`, returns decision | New endpoint; cacheable indefinitely by (item, council) pair |
| GuidelinesService ↔ data/guidelines/ | File read at startup; in-memory dict thereafter | Zero latency at request time; restart required to pick up data changes |
| CouncilService ↔ Nominatim | Async HTTP GET; cached by (lat_rounded, lng_rounded) | Round to 3 decimal places (~100m) for cache hit rate |

## Build Order Implications

The components have the following dependency chain, which should inform phase sequencing:

1. **Guidelines dataset first** — scrape recyclingnearyou.com.au, build JSON files, establish the label→RNY mapping. Everything else depends on this data existing.
2. **GuidelinesService + /advice endpoint** — can be built and tested with hardcoded council slugs before geolocation works.
3. **CouncilService + /council endpoint** — requires the ABS postcode→LGA correspondence table and Nominatim integration. Independently testable.
4. **Frontend geolocation + ResultCard** — depends on both /council and /advice being functional. Build last.
5. **Mobile UI polish** — camera-first layout, bin colour styling, fallback flows. Final layer.

## Sources

- [RecyclingNearYou.com.au](https://recyclingnearyou.com.au/) — primary data source; council directory at `/councils/`, ~560 councils; robots.txt is open
- [RecyclingNearYou council URL structure](https://recyclingnearyou.com.au/council/BrisbaneQLD) — confirmed pattern `/{CouncilNamePascalCase}{StateAbbrev}`
- [RecycleSmart app architecture](https://wastemanagementreview.com.au/recyclesmart-caters-to-council/) — confirmed integration with Planet Ark RNY database; council data collected from 500+ Australian councils
- [Recycle Mate app](https://dreamwalk.com.au/project/recycle-mate) — confirms photo→council→bin decision is the standard architecture for Australian recycling apps; catalogued all LGAs
- [ABS ASGS Correspondence Files](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/correspondences) — free postcode→LGA mapping CSV files
- [ABS Digital Boundary Files](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files) — GeoJSON/shapefile for point-in-polygon LGA resolution if needed
- [Nominatim Reverse Geocoding API](https://nominatim.org/release-docs/latest/api/Reverse/) — free, open, no API key for prototype scale
- [Geoscape LGA Boundaries](https://data.gov.au/data/dataset/other-local-government-areas-geoscape-administrative-boundaries) — authoritative quarterly-updated LGA boundaries on data.gov.au
- [Recycling in Australia - Wikipedia](https://en.wikipedia.org/wiki/Recycling_in_Australia) — bin colour standards by state

---
*Architecture research for: Australian recycling advice app — council guidelines data layer*
*Researched: 2026-02-26*
