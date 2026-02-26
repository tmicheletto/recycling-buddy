# Pitfalls Research

**Domain:** Australian recycling advice app — council data scraping, geolocation, ML classifier, mobile camera UX
**Researched:** 2026-02-26
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Treating recyclingnearyou.com.au as a Stable API

**What goes wrong:**
The site is a public-facing content site, not an API. Its HTML structure, URL patterns, and content organisation change without notice. A scraper built in February against the current site structure will silently return empty or wrong data after the next redesign. Council pages may also be gated behind postcode search forms that require JavaScript or session cookies, making naive HTTP GET requests return nothing useful.

**Why it happens:**
Developers assume the site structure is stable because it "looks like a directory". Council directories are redesigned regularly and form-gated searches are common in government-adjacent sites.

**How to avoid:**
- Treat the scrape as a one-time data extraction to seed a local JSON/SQLite store, not an ongoing live API call.
- Store the scraped data as a versioned flat file (`council_rules.json`) committed to the repo.
- Write the scraper defensively: assert expected HTML selectors exist before trusting extracted content; fail loudly if a page yields zero items.
- Check TOS (recyclingnearyou.com.au is operated by Planet Ark — their terms permit personal/educational use but not redistribution; treat scraped data as internal seed data only).
- Set a `User-Agent` header identifying the prototype; add a 2–5 second delay between requests.

**Warning signs:**
- Scraper returns 0 councils or 0 rules for a council that previously returned data.
- Council rule content is HTML fragments (script tags, form elements) rather than text.
- HTTP 403 or redirect to a login/search page on direct URL access.

**Phase to address:**
Council data extraction phase (whichever phase builds the rules data store). Validate the extract against a known council (e.g., City of Melbourne) before committing data.

---

### Pitfall 2: Classifier Category Names Don't Match Council Rule Categories

**What goes wrong:**
The classifier outputs one of 67 labels derived from recyclingnearyou.com.au's taxonomy. Council rules pages on the same site use a different level of granularity or different terminology for the same items. The mapping between classifier output and council rule lookup key silently fails for a subset of categories, returning "no rule found" rather than an error.

**Why it happens:**
The 67 category labels were set during phase 001 based on one read of the taxonomy. Council rule pages may describe items at the material level ("glass jars") while the classifier is trained on object-level labels ("food jars"). Synonyms and plural/singular mismatches compound this.

**How to avoid:**
- Build an explicit mapping table (`label_to_rule_key.json`) from classifier label → council rule lookup key, rather than relying on exact string match.
- During data extraction, log every council label encountered and diff against ALL_LABELS_LIST; gaps must be resolved before launch.
- Write a test that, given a mock council rule store, asserts every one of the 67 classifier labels maps to at least one rule entry (even if it is "check with council").
- Provide a fallback "general waste" or "check with your council" result for any unmapped label rather than a 500 error.

**Warning signs:**
- More than ~5% of classifier labels return "no matching rule" when tested against a real council.
- Council rule store has entries that no classifier label ever maps to.

**Phase to address:**
Data model design phase (when the council rules schema is defined). Revisit before integration testing.

---

### Pitfall 3: Geolocation Permission Denial Breaks the Core Flow

**What goes wrong:**
The entire recycling advice flow depends on knowing the user's council, which depends on geolocation. On mobile browsers, permission is denied by roughly 20–30% of users on first request (especially on iOS Safari where the permission dialog is intrusive and often dismissed). If the app silently fails or shows a spinner after denial, users have no path to get advice.

**Why it happens:**
Developers test on their own devices where they have already granted permission. The denied-state is an afterthought.

**How to avoid:**
- Design the denied state first: show a postcode entry field as the fallback immediately after `GeolocationPositionError` with `code === PERMISSION_DENIED`.
- Never call `getCurrentPosition()` without a defined `error` callback that triggers the postcode fallback.
- Cache the resolved council (postcode → council name) in `localStorage` so repeat users skip geolocation entirely.
- On iOS, geolocation only works over HTTPS. Ensure the staging/production URL is HTTPS before any geolocation testing.
- Do not prompt for geolocation before the user has taken a photo — "why does this app need my location?" causes denials when context is missing.

**Warning signs:**
- UI shows an indefinite loading state after the user taps "Deny" in the browser dialog.
- No postcode input field exists in the codebase.
- Geolocation is called on page load rather than after photo capture.

**Phase to address:**
UI design phase, before any geolocation API integration is written. The postcode fallback must be in scope from day one.

---

### Pitfall 4: Low-Confidence Classifier Predictions Displayed as Definitive Advice

**What goes wrong:**
The EfficientNet-B0 model returns a confidence score, but if the UI displays "put this in the recycling bin" without surfacing the confidence, a user confidently places a non-recyclable item in recycling because the model mis-classified a dark-coloured glass bottle as a plastic bottle at 52% confidence. This causes recycling contamination — the literal harm the app is trying to prevent.

**Why it happens:**
Confidence thresholding is considered a model concern, not a UX concern. Developers assume the top-1 prediction is good enough because it works on test images.

**How to avoid:**
- Define a confidence threshold (suggested: 0.65 for prototype). Below threshold, show "I'm not sure — here are the most likely options" and present the top-3 alternatives from the existing API response.
- Never use the word "is" in advice text for low-confidence predictions ("This looks like..." vs. "This is...").
- Log all predictions with confidence scores; after a week of usage, analyse the confidence distribution to calibrate the threshold empirically.
- The API already returns `alternatives` — the UI must use them, not discard them.

**Warning signs:**
- UI only renders `top_prediction` and ignores the `alternatives` array from the API response.
- No confidence score is visible to the user in any form.
- No threshold constant exists anywhere in the frontend code.

**Phase to address:**
UI advice display phase. Define the threshold as a named constant (`CONFIDENCE_THRESHOLD = 0.65`) in the frontend config from day one.

---

### Pitfall 5: Council Boundary Polygons Don't Match Browser Geolocation Accuracy

**What goes wrong:**
Browser geolocation on mobile without GPS lock (i.e., using Wi-Fi/cell triangulation) has accuracy of 100–500 metres. Australian council boundaries in dense suburban areas can be as narrow as 200 metres (e.g., boundary streets between inner-city councils). A user in Fitzroy (City of Yarra) may be told they are in Collingwood (City of Melbourne) with different recycling rules.

**Why it happens:**
Developers test in their home suburb where there is no nearby boundary. The problem only manifests for users who live near a council border.

**How to avoid:**
- Use `position.coords.accuracy` from the Geolocation API. If accuracy radius exceeds a threshold (suggested: 500m), show a disambiguation message: "Your location may be near a council boundary — confirm your council below" with a dropdown pre-filtered to the 2–3 nearest councils.
- For prototype scope, rely on postcode-to-council mapping rather than full polygon boundary lookup; postcode boundaries are wider and less prone to edge-case mismatches.
- Source postcode-to-council mapping from the ABS or data.gov.au — it is a stable, licenced open dataset.
- Do not implement full GIS polygon intersection for prototype; defer to v2.

**Warning signs:**
- The council resolution logic uses raw lat/long coordinates against polygon data without checking `accuracy` radius.
- There is no user-visible "confirm your council" step in the flow.
- Testing only happens in a single suburb.

**Phase to address:**
Council resolution design phase. Choose postcode-based lookup explicitly as the prototype approach; document the boundary accuracy limitation.

---

### Pitfall 6: Scraping Rate Limits Causing IP Blocks Mid-Extraction

**What goes wrong:**
recyclingnearyou.com.au serves ~550 Australian councils. Scraping all council pages sequentially without delay triggers rate-limiting or an IP block partway through extraction, leaving a partial dataset. The developer restarts the scraper, gets a different partial set, and merges them inconsistently.

**Why it happens:**
Public content sites run Cloudflare or basic rate limiting without documenting it. Developers iterate quickly and don't add delays.

**How to avoid:**
- Add a 2–5 second random delay between requests (not a fixed delay, which looks more bot-like).
- Implement resumable scraping: save each council's data to a local file as it is fetched; skip already-fetched councils on restart.
- Run the full scrape once, commit the result, and never re-scrape in CI or automated flows.
- Set a `User-Agent` header (e.g., `recycling-buddy-prototype/0.1 (educational use)`).
- If blocked, use a residential IP or wait 24 hours before retrying (do not use multiple IPs to circumvent rate limiting — that violates TOS).

**Warning signs:**
- HTTP 429 or 503 responses mid-scrape.
- Council pages return identical HTML (cached error page) for the last N councils scraped.
- The scraper has no local file output between requests.

**Phase to address:**
Data extraction phase. Build resumability in before the first run, not after the first block.

---

### Pitfall 7: Mobile Camera Capture Silently Fails on iOS Safari

**What goes wrong:**
The existing `PhotoCapture.tsx` component uses `<input type="file" accept="image/*" capture="environment">`. On iOS Safari, this works for native camera capture. However: (1) `capture="environment"` is ignored on iOS — users always get a choice of camera or library. (2) HEIC/HEIF images taken on iPhone are not JPEG; the backend currently only handles JPEG and PNG magic bytes. A user snaps a photo and gets a silent 500 or an "invalid image" error.

**Why it happens:**
Development and testing happens on Android or desktop. iOS-specific image format behaviour is discovered late.

**How to avoid:**
- Add HEIC detection to the backend magic bytes check (`00 00 00 [various] 66 74 79 70`) — or, preferably, convert on the frontend using the Canvas API: draw the image to a canvas and export as JPEG via `canvas.toBlob('image/jpeg', 0.85)` before sending to the API.
- Test on a real iOS device (or BrowserStack iOS) before any user testing.
- The frontend Canvas-based JPEG conversion approach is the most robust: it normalises all input formats before hitting the API.

**Warning signs:**
- Backend `_is_valid_image()` only handles `FF D8 FF` (JPEG) and `89 50 4E 47` (PNG) magic bytes.
- No image format normalisation step exists in the frontend upload path.
- PhotoCapture component was only tested on desktop Chrome.

**Phase to address:**
UI camera integration phase. Add the Canvas-based normalisation at the same time as photo capture is wired to the classify flow.

---

### Pitfall 8: Council Rules Data Goes Stale Without a Refresh Mechanism

**What goes wrong:**
Australian councils update recycling rules periodically — new kerbside organics bins (FOGO), changes to accepted plastics, special collection events. A prototype using a scraped snapshot from February 2026 will be giving incorrect advice by late 2026 for councils that have since changed.

**Why it happens:**
The data layer is treated as a one-off seeding step. There is no mechanism to detect or signal data staleness.

**How to avoid:**
- Include a `scraped_at` timestamp in the council rules data file.
- Display "rules last updated [month/year]" in the UI advice card so users can calibrate trust.
- Add a README note (or planning comment) that the data file needs manual refresh every 6 months.
- For prototype scope, this is acceptable — just make staleness visible rather than invisible.

**Warning signs:**
- No `scraped_at` or `data_version` field in the rules data structure.
- No date attribution in the UI advice display.

**Phase to address:**
Data model design phase. Add the timestamp field to the schema before data extraction.

---

### Pitfall 9: Geolocation Timeout on Slow Mobile Networks Blocks UI

**What goes wrong:**
`navigator.geolocation.getCurrentPosition()` with default timeout (no timeout specified) can block for up to 30 seconds on a slow 3G connection or in a building with poor GPS. The user sees a spinner with no explanation and abandons the app.

**Why it happens:**
Default geolocation options have a very generous timeout. Developers on fast connections never see it.

**How to avoid:**
- Always specify `{ timeout: 8000, maximumAge: 300000 }` in the options object.
- Show a progress indicator with a label ("Finding your location...") and a "Skip — enter postcode" escape hatch visible after 3 seconds.
- Use `maximumAge: 300000` (5 minutes) to accept a cached position — a user's council doesn't change between photo captures.

**Warning signs:**
- `getCurrentPosition()` call has no options object.
- No timeout escape hatch exists in the UI.
- No `maximumAge` set (every call waits for a fresh fix).

**Phase to address:**
Geolocation integration phase.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode council rules as a JSON flat file | Avoids database setup | Cannot update rules without a deploy; no per-council partial updates | Prototype only — must be replaced before scaling |
| Postcode-to-council lookup via static table | Avoids GIS polygon logic | ~5% of postcodes span multiple councils; users in boundary postcodes get wrong council | Prototype only — acceptable with user confirmation step |
| Re-scrape on demand rather than caching | Always fresh data | Blocks request; risks rate limiting; cannot be unit tested | Never — always use a cached data store |
| Display top-1 classifier result unconditionally | Simpler UI | Wrong advice for low-confidence predictions causes recycling contamination | Never — confidence threshold is mandatory |
| Skip HTTPS for prototype staging | Faster setup | Geolocation API refuses to fire on HTTP origins in Chrome/Firefox; camera capture blocked in some browsers | Never — geolocation and camera require HTTPS |
| Call geolocation on page load | Simpler code | Browser shows permission dialog before user understands why; increases denial rate | Never — call after user initiates classification |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| recyclingnearyou.com.au | Scraping HTML of search results page (JavaScript-rendered) via direct GET | Inspect network traffic for XHR/fetch calls that return structured data; fall back to Playwright/Puppeteer for JS-rendered pages if needed |
| Browser Geolocation API | Not handling `PERMISSION_DENIED` (code 1), `POSITION_UNAVAILABLE` (code 2), `TIMEOUT` (code 3) separately | Implement distinct handlers for each error code; code 1 → postcode fallback, code 2 → postcode fallback, code 3 → retry with user message |
| Browser Geolocation API | Using `watchPosition()` instead of `getCurrentPosition()` | Use `getCurrentPosition()` with `maximumAge`; `watchPosition()` drains battery and is unnecessary |
| FastAPI `/predict` endpoint | Sending HEIC image bytes directly | Normalise to JPEG on the frontend via Canvas API before POSTing |
| ABS/data.gov.au postcode mapping | Using LGA codes instead of council names | The ABS ASGS (Australian Statistical Geography Standard) uses SA2/LGA codes; join against council name lookup table before using in UI |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading full council rules JSON on every API request | Sub-10ms latency at 1 req/s; multi-second at load | Load at FastAPI lifespan startup into `app.state`; same pattern as model loading | ~50 concurrent users |
| Re-running scraper in CI to build data | Works locally; CI hangs or gets blocked | Commit scraped data to repo; scraper is a one-off maintenance script | First CI run against rate-limited site |
| Full GIS polygon lookup per request | Fine on desktop; 2–4s on ECS Fargate (256 CPU units) | Use postcode lookup table for prototype | Every request on ECS Fargate |
| Sending full-resolution camera image to API | Fine on Wi-Fi; 5–15 second upload on 4G | Resize to max 1024px on the longest dimension before upload using Canvas API | Mobile 4G, any image from a 12MP+ phone camera |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing council names from geolocation response in URL params | Council name in URL leaks to referer headers and server logs alongside coordinates | Use `localStorage` or session state; never put location data in URLs |
| Proxying scraper requests through the production API | Production IP gets rate-limited or blocked by recyclingnearyou.com.au | Run scraper locally or in a one-off Lambda/ECS task; never in the serving path |
| Caching geolocation coordinates in localStorage | Coordinates persist beyond the session; if the site is compromised, coordinates are exfiltrated | Cache council name only (e.g., "City of Melbourne"), never raw lat/long |
| Exposing full classifier confidence scores in public API response | Exposes model internals; minor issue for prototype | Acceptable for prototype; round to 2 decimal places in production |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing bin colour (yellow lid, red lid) without a photo | Australian councils use different lid colour schemes; City of Sydney uses purple for recycling, most others use yellow | Always show bin label text ("Recycling bin") as primary; bin colour as secondary/optional |
| "Which bin?" as the only output | User doesn't know what to do with the item (rinse? remove lid? flatten?) | Always include brief prep instructions from the council rule, even if just "rinse before recycling" |
| Displaying "try again" on classifier low-confidence without alternatives | User has no information; abandons | Show top-3 alternatives with "Is it one of these?" so user can self-correct |
| Geolocation dialog appearing before any explanation | ~30% denial rate when context is absent | Show a brief "We need your location to find your council's rules" message before triggering the browser dialog |
| Treating all 67 categories as equally recognisable by non-experts | Users don't know what "soft plastics" means | Map classifier labels to plain-English display names in the UI (separate from the label key used for API calls) |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Geolocation integration:** Often missing the `error` callback — verify by testing with browser geolocation blocked in DevTools
- [ ] **Classifier confidence display:** Often missing the threshold check — verify the UI renders differently for a 0.45 confidence result vs. a 0.92 result
- [ ] **Council rules lookup:** Often missing the unmapped-label fallback — verify that a novel label not in the rules store returns a graceful "check with your council" response, not a 500
- [ ] **iOS camera capture:** Often missing HEIC handling — verify by testing on an actual iPhone (not iOS Simulator, which has no camera)
- [ ] **Mobile layout:** Often missing safe-area insets for iPhone notch/home indicator — verify on an iPhone with Face ID using the actual browser (not DevTools responsive mode)
- [ ] **Postcode fallback:** Often missing entirely — verify by revoking geolocation permission in browser settings and reloading the app
- [ ] **HTTPS enforcement:** Often missing on staging — verify that `navigator.geolocation` returns a result on the staging URL (it will refuse on HTTP)
- [ ] **Data staleness indicator:** Often missing — verify that the advice card shows when the council rules were last updated

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Scraper blocked mid-extraction | LOW | Wait 24h; add resumable state to scraper; re-run from last successful council |
| Classifier-to-rule mapping gaps discovered post-launch | MEDIUM | Add "check with your council" fallback for unmapped labels (1 day); schedule mapping table review |
| iOS HEIC images causing 500 errors | MEDIUM | Add frontend Canvas normalisation (1–2 days); hotfix deploy to ECS |
| Geolocation used without HTTPS (breaks in browser) | LOW | Enable HTTPS on staging via ACM/CloudFront; typically 1–2 hours |
| Council rules data significantly wrong for a council | MEDIUM | Correct the flat-file JSON; redeploy API (ECS task update); no user data is affected |
| Confidence threshold set too high (app refuses most photos) | LOW | Adjust threshold constant in frontend config; redeploy UI |
| Council boundary misresolution reported by users | LOW | Add user-visible "Is this your council?" confirmation step; postcode lookup as alternative |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| recyclingnearyou.com.au structure instability | Council data extraction phase | Assert extracted data covers >500 councils and >5 rules each; spot-check City of Melbourne |
| Classifier label ↔ council rule mismatch | Data model design phase | Unit test: all 67 labels resolve to at least one rule key in mock store |
| Geolocation permission denial | UI design phase (before coding) | Manual test: deny permission, verify postcode field appears immediately |
| Low-confidence predictions shown as definitive | UI advice display phase | Unit test: render with confidence=0.45 and assert "not sure" messaging shown |
| Council boundary accuracy vs. geolocation accuracy | Council resolution design phase | Document postcode-based approach as explicit prototype decision |
| Scraper rate limiting mid-extraction | Data extraction phase | Resumable scraper with per-council output files; tested by interrupting mid-run |
| iOS HEIC image failures | UI camera integration phase | Test on physical iPhone; Canvas normalisation in place before any user testing |
| Council rules data staleness | Data model design phase | `scraped_at` field in schema; visible in UI advice card |
| Geolocation timeout on slow networks | Geolocation integration phase | Test with Chrome DevTools network throttled to "Slow 3G" + geolocation emulation |

---

## Sources

- Browser Geolocation API behaviour on iOS: MDN Web Docs geolocation error codes; known iOS Safari HTTPS-only restriction (widely documented)
- HEIC/HEIF on iOS camera: WebKit tracking issue and MDN file input documentation; canvas-based workaround is established pattern
- recyclingnearyou.com.au: Direct inspection of site structure; Planet Ark TOS (public website)
- Australian council boundary data: ABS ASGS documentation; postcode-to-LGA correspondence file (data.gov.au)
- EfficientNet-B0 confidence calibration: general knowledge of softmax confidence overconfidence in transfer-learned classifiers
- Mobile performance: established patterns for image resizing before upload in PWA/mobile web apps

---
*Pitfalls research for: Australian recycling advice app (council data, geolocation, classifier, mobile UX)*
*Researched: 2026-02-26*
