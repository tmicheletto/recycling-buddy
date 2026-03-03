# Design: Replace label_to_rny.json with Tavily search grounding

**Date:** 2026-03-03
**Status:** Approved

## Problem

`data/label_to_rny.json` is a hand-maintained mapping from 67 classifier labels to Recycling Near You (RNY) URL slugs. It requires manual curation, 11 labels are unmapped, and it adds a maintenance burden without providing significant value — the LLM can determine the right context dynamically.

## Decision

Replace the static mapping file and direct HTML scraping with Tavily search API calls scoped to `recyclingnearyou.com.au`. Tavily returns extracted content directly, eliminating both the mapping file and the HTML scraper.

## Data flow

```
classify(image) → item_category (e.g. "cardboard")
                          ↓
    GuidelinesService.lookup(item_category, council_slug)
        ├── Check advice cache (TTL 1 week) → hit? return
        ├── Check search cache (TTL 24h) → hit? use cached content
        ├── Miss? → Tavily search: site:recyclingnearyou.com.au {item} {council}
        │           → cache extracted content
        ├── Pass content + item + council to GPT-4o-mini
        ├── Cache advice result (TTL 1 week)
        └── Return AdviceRecord
```

## Changes to GuidelinesService

### Remove
- `_load_mapping()` method
- `_rny_url()` method
- `_label_to_rny` dict (instance variable)
- `_fetch_page()` method (Tavily returns extracted content, no HTML scraping needed)

### Add
- `_search_rny(item_category, council_slug)` — calls Tavily with `search_depth="basic"`, `include_domains=["recyclingnearyou.com.au"]`, returns extracted content string
- `_search_cache` — dict mapping `(item_category, council_slug)` → `(content: str, timestamp: float)` with 24h TTL

### Modify
- `_call_llm()` — context is now Tavily's extracted text, not raw HTML; 8000-char truncation stays but applies to cleaner text
- `lookup()` — two-tier cache check: advice cache first, then search cache, then Tavily call

## Config changes

### Remove
- `guidelines_data_path` setting from `config.py`
- `GUIDELINES_DATA_PATH` from docker-compose.yml, api/Dockerfile, .env files

### Add
- `tavily_api_key` setting (from env var `TAVILY_API_KEY`)
- `search_cache_ttl_seconds` setting (default: 86400 = 24h)

## Files deleted

- `data/label_to_rny.json`

## Dependencies

- Add `tavily-python` to API dependencies

## Error handling

- **Tavily returns results:** extracted content → LLM → `is_fallback=false`
- **Tavily returns no results:** no context → LLM answers from training data → `is_fallback=true`
- **Tavily API error:** same as no results, plus logged warning
- **No `TAVILY_API_KEY`:** all lookups use LLM training data only (degraded mode, same pattern as missing OpenAI key)

## Testing

- Mock `tavily_client.search()` in unit tests (same pattern as current `httpx` mocking)
- Test both cache tiers independently
- No new integration test infrastructure needed
