# Stack Research

**Domain:** Australian recycling advice app — council data layer + mobile web frontend
**Researched:** 2026-02-26
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python `requests` | 2.32.x | Build-time scraper for recyclingnearyou.com.au | Standard HTTP client; no async needed for a one-shot scrape; simpler than httpx for sequential polite crawling |
| BeautifulSoup4 | 4.12.x | HTML parsing for recyclingnearyou.com.au pages | Handles real-world malformed HTML; well-documented; the go-to for Python scraping of static HTML pages. lxml parser backend recommended for speed. |
| httpx | 0.28.x | Async HTTP client for Nominatim calls from FastAPI | Already in the dev dependencies (used for API testing). Supports async/await natively, essential for non-blocking geocode calls from an ASGI handler. |
| React 19 (existing) | 19.2.0 | Mobile UI | Already in use. `navigator.geolocation` and `<input type="file" capture="environment">` are standard browser APIs; no new framework needed. |
| Browser Geolocation API | Web standard | GPS coordinates from device | Built into every modern mobile browser. No library required. Must be served over HTTPS (already the case for ECS Fargate + ALB). |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lxml` | 5.3.x | Fast HTML/XML parser backend for BeautifulSoup4 | Always pair with BS4 — 3–5x faster than the default `html.parser`; more lenient with malformed markup |
| `tenacity` | 9.0.x | Retry logic with exponential backoff for scraper | Use to handle transient HTTP errors and rate-limit responses (429) during the recyclingnearyou.com.au scrape |
| `aiohttp` | — | Alternative async HTTP | Do NOT use — prefer httpx which is already a dev dependency and has a cleaner API for FastAPI integration |
| `shapely` | 2.0.x | Point-in-polygon LGA boundary matching | Use only if postcode→LGA correspondence table proves too inaccurate (e.g. postcodes straddling multiple LGAs). Not needed for prototype. |
| `react-query` / TanStack Query | 5.x | Server state management for API calls in React | Use if the two-step (predict → advice) call sequence needs loading/error/cache state management. Lightweight alternative: plain `fetch` + `useState`. For prototype, plain fetch is sufficient. |
| Tailwind CSS | 3.4.x | Mobile-first utility CSS | Fastest path to a polished mobile layout without a design system. If the existing UI already has a CSS approach, match it rather than adding Tailwind. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` (existing) | Python dependency management | Already in use for `api/` and `model/`. Add `requests`, `beautifulsoup4`, `lxml`, `tenacity` as dependencies of a new `scripts/` or `data/` package, or directly in `api/` if the scraper runs in the same container. |
| Nominatim public instance | Reverse geocoding lat/lng → suburb/postcode | `https://nominatim.openstreetmap.org/reverse` — free, no API key. **Rate limit: 1 request/second.** Add `User-Agent` header identifying the app (required by Nominatim usage policy). |
| ABS ASGS Correspondence Files | Postcode → LGA mapping table | Download once from abs.gov.au (CSV, ~200 KB). Commit the processed JSON to the repo. Updated annually — check for new release around July each year. URL: `https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/correspondences` |

## Installation

```bash
# Backend — scraper and geocoding dependencies
# Add to api/pyproject.toml or a new scripts/pyproject.toml
uv add requests beautifulsoup4 lxml tenacity

# httpx is already present as a dev dependency in api/
# No additional install needed for Nominatim integration

# Frontend — no new packages required for Geolocation API or camera capture
# These are standard browser APIs available in React components

# Optional: if point-in-polygon LGA resolution is needed later
uv add shapely

# Optional: if TanStack Query is adopted for API state management
npm install @tanstack/react-query
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| BeautifulSoup4 + requests (build-time scrape) | Playwright / Selenium (headless browser) | Only if recyclingnearyou.com.au pages require JavaScript execution to render content. Current observation: pages are server-rendered HTML — BS4 is sufficient. |
| Nominatim (free, no key) | Google Maps Geocoding API | When request volume exceeds ~500 geocode calls/day or when Nominatim accuracy proves insufficient for rural councils. Google costs ~$5 per 1,000 requests. Not warranted for prototype. |
| Nominatim (free, no key) | Geoapify | Good middle ground — free tier 3,000 req/day, no credit card required. Upgrade path if Nominatim public instance rate limit is hit before self-hosting is justified. |
| ABS postcode → LGA correspondence table | Point-in-polygon against ABS ASGS boundary GeoJSON | Use PIP if postcode-level accuracy is insufficient (postcodes straddling two councils). PIP requires shapely + ~10 MB GeoJSON download. Defer to post-prototype. |
| Static JSON files in container (build-time scrape) | Live scraping at request time | Never scrape at request time — adds 500ms–2s latency, creates runtime dependency on external site, risks rate-limit blocking. Static dataset is always correct for this use case. |
| Static JSON files in container | SQLite database | Use SQLite if the guidelines dataset exceeds ~50 MB or if partial council updates become frequent. At 560 councils × ~67 items × ~200 bytes, total size is ~7.5 MB — well within in-memory JSON range. |
| Browser Geolocation API | IP-based geolocation | IP geolocation is city-level at best — useless for LGA resolution within a metro area. Browser GPS is the only viable approach for council-level accuracy. |
| `<input type="file" capture="environment">` | WebRTC `getUserMedia()` live camera stream | Use WebRTC only if a live viewfinder with overlay is required (not needed for v1). The file input approach works on all mobile browsers, requires no permissions dialog beyond the camera access prompt, and integrates with the existing `PhotoCapture.tsx` component. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Scrapy | Overkill for a one-shot scrape of 560 predictably structured pages. Adds framework complexity, a separate process model, and a steeper learning curve for a task that `requests` + BS4 handles in ~100 lines. | `requests` + `beautifulsoup4` + `tenacity` |
| Selenium / Playwright for scraping | Requires a headless browser binary, much slower, and unnecessary if recyclingnearyou.com.au pages are server-rendered (confirmed: they are). | `requests` + `beautifulsoup4` |
| Google Maps / Mapbox for council resolution | Paid APIs with per-request billing; overkill when the only output needed is a council slug. No map is displayed to the user. | Nominatim (free) + ABS postcode→LGA CSV |
| IP geolocation libraries (e.g. `geoip2`) | City-level accuracy only — cannot resolve to an LGA. A user in Parramatta and a user in Blacktown have the same suburb-level IP but different councils and different recycling rules. | Browser `navigator.geolocation` |
| `react-leaflet` / Google Maps embed for v1 | No map is shown to the user in the advice flow. Drop-off location finders are explicitly v2. Adding a mapping library now wastes bundle size. | Plain text council name in the result card |
| Redux / Zustand for state management | The app state is simple: `{council, photo, classificationResult, advice}`. A single top-level `useState` or `useReducer` in `App.tsx` is sufficient. Global state management libraries add complexity without benefit at this scale. | `useState` + `useContext` if needed |
| Service workers / PWA manifest for v1 | Offline support is not in scope. Adding a service worker now creates cache invalidation risk and debugging overhead with no user benefit until push notifications (v2) are considered. | Standard React SPA without service worker |
| Next.js / Remix | The existing stack is React + Vite. Migrating to a meta-framework would require restructuring the entire frontend for no benefit — server-side rendering is not needed for a client-side advice tool backed by an existing API. | Vite (existing) |

## Stack Patterns by Variant

**If recyclingnearyou.com.au pages require JavaScript rendering (discovered during scraping):**
- Switch the scraper to Playwright (`playwright-python`, `asyncio`-native)
- Run as a one-shot script, not a server process
- Still commit output as static JSON — do not use Playwright at request time

**If Nominatim public instance rate limits become a problem (>1 req/sec sustained):**
- Self-host Nominatim via Docker (`mediagis/nominatim` image) on a t3.small EC2 in ap-southeast-2
- Or switch to Geoapify free tier (3,000 req/day, no billing required)
- Cache geocode results in a Redis ElastiCache instance keyed by `(round(lat,3), round(lng,3))`

**If postcode→LGA accuracy is insufficient for a specific region:**
- Download ABS ASGS Edition 3 LGA boundary GeoJSON (~10 MB)
- Use `shapely.geometry.shape` + `Point.within(polygon)` for precise point-in-polygon
- Only needed if user complaints show council mismatches — defer to data evidence

**If the React UI needs to handle the two-step API call (predict → advice) with loading states:**
- Use `useReducer` with states: `idle | locating | located | capturing | classifying | advising | done | error`
- No external state library needed; the state machine is simple enough for a reducer

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| FastAPI 0.128.0 | httpx 0.28.x | httpx is the recommended async client for FastAPI test and runtime use. No compatibility issues. |
| BeautifulSoup4 4.12.x | lxml 5.3.x | BS4's `lxml` parser requires lxml installed separately. No version conflicts with current Python 3.11 target. |
| React 19.2.0 | Browser Geolocation API | Standard Web API, no library dependency. Works in all mobile browsers on HTTPS. |
| tenacity 9.0.x | Python 3.11 | Fully compatible. Uses `@retry` decorator pattern. |
| requests 2.32.x | Python 3.11 | Fully compatible. No async support (intentional — scraper is synchronous). |

## Scraping Approach: recyclingnearyou.com.au

### Rate-limiting strategy

```python
# Recommended scraper pattern — polite, resumable
import time
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "RecyclingBuddy/1.0 (research scraper; contact: your@email.com)"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch(url: str) -> BeautifulSoup:
    resp = SESSION.get(url, timeout=10)
    resp.raise_for_status()
    time.sleep(1.0)  # 1 req/sec — polite baseline
    return BeautifulSoup(resp.text, "lxml")
```

- Target rate: **1 request/second** — same as Nominatim; sufficient for scraping 560 pages in ~10 minutes
- Retry on 429 / 5xx with exponential backoff via `tenacity`
- Use a `requests.Session` for connection reuse and consistent headers
- Set a descriptive `User-Agent` (robots.txt is open but politeness is standard practice)
- Output: one JSON file per council in `data/guidelines/rules/`; run once, commit, refresh on a schedule

### Council resolution: GPS → postcode → LGA

```
navigator.geolocation.getCurrentPosition()
    → {lat, lng}
    → POST /council {lat, lng}
    → Nominatim reverse geocode → {postcode, suburb}
    → ABS postcode→LGA CSV lookup → council_slug
    → return {council_slug, council_name, state}
```

The ABS ASGS "Postcode to Local Government Area" correspondence file (CSV) maps every Australian postcode to its primary LGA with a population-weighted allocation ratio. Process this CSV once into a dict at API startup. No database needed.

### Mobile camera capture (React)

```tsx
// Existing PhotoCapture.tsx pattern — adapt for advice flow
<input
  type="file"
  accept="image/*"
  capture="environment"   // opens rear camera directly on mobile
  onChange={handleCapture}
  ref={fileInputRef}
/>
```

- `capture="environment"` opens the rear camera on Android and iOS without a file picker
- Falls back to file picker on desktop — acceptable for prototype
- No WebRTC, no getUserMedia, no camera permissions dialog beyond the standard browser prompt
- HTTPS is required for camera access (already enforced by ECS Fargate + ALB setup)

## Sources

- recyclingnearyou.com.au — confirmed server-rendered HTML, open robots.txt, URL structure `/{CouncilNamePascalCase}{StateAbbrev}`, ~560 councils
- ABS ASGS Edition 3 Correspondence Files — `abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3` — postcode→LGA CSV, free, updated annually
- Nominatim reverse geocoding docs — `nominatim.org/release-docs/latest/api/Reverse/` — confirmed usage policy (User-Agent required, 1 req/sec on public instance)
- BeautifulSoup4 docs — `crummy.com/software/BeautifulSoup/bs4/doc/` — lxml parser recommended
- tenacity docs — `tenacity.readthedocs.io` — retry decorator for Python
- MDN: HTMLInputElement capture — confirmed `capture="environment"` behaviour on mobile browsers
- MDN: Geolocation API — confirmed HTTPS requirement, `getCurrentPosition()` API shape
- `.planning/codebase/STACK.md` — existing stack inventory (FastAPI 0.128, React 19.2, Vite 7.2, httpx 0.28 already present)
- `.planning/research/ARCHITECTURE.md` — architecture decisions already ratified (static JSON, Nominatim, ABS postcode table)
- `.planning/research/FEATURES.md` — confirmed `<input capture="environment">` as the camera pattern; Geolocation API for council resolution

---
*Stack research for: Australian recycling advice app — council data layer + mobile web frontend*
*Researched: 2026-02-26*
