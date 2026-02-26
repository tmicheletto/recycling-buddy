# Phase 1: Guidelines Data Layer - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the backend service that maps (item_category, council) → a bin decision. Instead of a static scraped dataset, this phase implements an LLM-backed lookup: fetch the relevant recyclingnearyou.com.au page at request time, pass it as context to OpenAI, and return a structured bin advice record. Includes in-memory caching to reduce latency and cost.

Council resolution (GPS/postcode → council slug) is a separate phase (Phase 2). The advice API endpoint that connects classification output to this lookup is Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Guidelines lookup approach
- **LLM at query time, not a static scraper** — Call OpenAI (GPT-4o-mini / GPT-4o) per (item_category, council) request instead of building a build-time scraper and static JSON dataset
- Grounding: fetch the recyclingnearyou.com.au item+council page as context, pass HTML to the LLM so it answers from actual current council data, not training data alone
- If the RNY page fetch fails (404, timeout, site down): fall back to the LLM answering from training data alone without grounding

### Response schema
The LLM must extract and return a full advice record:
- `bin_colour` — lid colour (red / yellow / green / purple / lime)
- `bin_name` — bin name (e.g. "General Waste", "Recycling")
- `prep_instructions` — prep steps if any (e.g. "rinse, remove lid, flatten")
- `disposal_method` — "kerbside" | "special_disposal" | "drop_off"
- `special_disposal_flag` — boolean
- `notes` — any extra context from the council page

### Uncertain/fallback results
- When the LLM is uncertain or cannot find specific advice for the item+council: default to **general waste (red bin)** — the safe choice to prevent recycling contamination
- Always include a disclaimer in the response when the result is a fallback: "We couldn't find specific advice — general waste is the safe choice"
- Frontend must surface this disclaimer to the user (Phase 4 concern, but the API flag must be present here)

### Response caching
- In-memory cache in the FastAPI process (no Redis or persistent storage)
- Cache key: `(item_category, council_slug)`
- TTL: 1 week — council rules rarely change
- Cache is lost on process restart (ECS task restart) and rebuilt on demand

### Label alignment — prerequisite task in Phase 1
- The 67 EfficientNet classifier labels were sourced from RNY's taxonomy, but label alignment with RNY item URL slugs must be verified before Phase 1 can proceed
- **Do a label audit first**: compare each of the 67 labels against the actual RNY item slug format
- If mismatches found: update the training labels to align with RNY slugs (may require re-fine-tuning the model with renamed classes, not a full retrain from scratch)
- Goal: classifier outputs `glass_bottle` → RNY URL slug is exactly `glass_bottle` (or whatever the canonical form is) — no translation layer needed

### Claude's Discretion
- Exact OpenAI prompt design (system prompt, user message structure, JSON mode vs tool use)
- HTTP client for RNY page fetch (httpx, already in the project)
- Cache implementation (Python dict with timestamp, functools.lru_cache + TTL decorator, or similar)
- Rate limiting / politeness for RNY fetches
- OpenAI model selection within gpt-4o-mini / gpt-4o (cost vs quality tradeoff)

</decisions>

<specifics>
## Specific Ideas

- Uncertain results should **always default to general waste (red bin)** — better safe than contaminate the recycling stream
- The grounding approach (fetch RNY page, pass as context) is preferred over training-data-only because it reflects actual current council rules, which change

</specifics>

<deferred>
## Deferred Ideas

- Persistent cache (Redis, file-based) — in-memory is sufficient for prototype; add if multi-instance ECS scaling is needed (future)
- Proactive cache warming (pre-fetch all 67 × N_councils at startup) — future optimisation if cold-start latency is a problem
- Label update → model retrain is a prerequisite for Phase 1, but if it requires significant ML work it may be worth inserting as a decimal phase (0.5) before Phase 1

</deferred>

---

*Phase: 01-guidelines-data-layer*
*Context gathered: 2026-02-26*
