---
status: complete
phase: 01-guidelines-data-layer
source: 01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md
started: 2026-02-26T04:20:00Z
updated: 2026-02-26T04:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. label_to_rny.json — 67 entries, all classifier labels present
expected: |
  Run: python3 -c "import json; d=json.load(open('data/label_to_rny.json')); print(len(d), 'entries')"
  Expected: prints "67 entries" with no error.
  Bonus: open data/label_to_rny.json and spot-check a few entries have rny_slug + notes fields.
result: pass

### 2. GET /advice — 200 with valid params
expected: |
  Start the API (cd api && .venv/bin/uvicorn src.main:app --reload) then:
  curl "http://localhost:8000/advice?item_category=cardboard&council_slug=SydneyNSW"
  Expected: HTTP 200 with JSON containing bin_colour, bin_name, disposal_method, is_fallback, notes.
  (Without OPENAI_API_KEY set, is_fallback will be true and bin_colour will be "red" — that's correct.)
result: issue
reported: "FileNotFoundError: Model artifact not found: model/artifacts/efficientnet_b0_recycling_v1.safetensors. Run the training pipeline to produce an artifact first."
severity: major

### 3. GET /advice — 422 on missing params
expected: |
  curl "http://localhost:8000/advice?item_category=cardboard"   (no council_slug)
  Expected: HTTP 422 Unprocessable Entity — FastAPI validation rejects the incomplete request.
result: skipped
reason: server won't start without model artifact

### 4. Fallback mode — no API key returns safe default
expected: |
  With no OPENAI_API_KEY in api/config/dev.env (leave it blank), hit /advice:
  curl "http://localhost:8000/advice?item_category=glass-bottles-jars&council_slug=MelbourneVIC"
  Expected: 200 response with is_fallback=true, bin_colour="red", bin_name="General Waste",
  and notes containing "safe choice" or similar disclaimer text.
result: skipped
reason: server won't start without model artifact

### 5. pytest suite — all 50 tests pass
expected: |
  Run: cd api && .venv/bin/python -m pytest tests/ -v 2>&1 | tail -5
  Expected: "50 passed" (or similar) with 0 failures, 0 errors.
result: pass

### 6. Unmapped label — graceful handling
expected: |
  curl "http://localhost:8000/advice?item_category=syringes-sharps&council_slug=SydneyNSW"
  (syringes-sharps is one of the 12 unmapped labels — no RNY slug, no grounding URL)
  Expected: 200 response with some bin advice — either LLM training-data answer or fallback.
  Should NOT return a 500 error or crash.
result: skipped
reason: server won't start without model artifact

## Summary

total: 6
passed: 2
issues: 1
pending: 0
skipped: 3

## Gaps

- truth: "API server starts and GET /advice returns 200 with valid params"
  status: failed
  reason: "User reported: FileNotFoundError: Model artifact not found: model/artifacts/efficientnet_b0_recycling_v1.safetensors. Run the training pipeline to produce an artifact first."
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
