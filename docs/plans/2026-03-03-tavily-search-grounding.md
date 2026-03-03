# Replace label_to_rny.json with Tavily Search Grounding — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the static `label_to_rny.json` mapping file with dynamic Tavily search to ground the LLM's recycling advice in real RNY page content.

**Architecture:** `GuidelinesService` drops its static mapping + HTML scraper and gains a `_search_rny()` method that calls Tavily's search API scoped to `recyclingnearyou.com.au`. A two-tier in-memory cache (advice: 1 week, search content: 24h) minimises external calls.

**Tech Stack:** `tavily-python` SDK, existing `openai` + `httpx` + `pydantic-settings` stack.

---

### Task 1: Add `tavily-python` dependency

**Files:**
- Modify: `api/pyproject.toml`

**Step 1: Add the dependency**

In `api/pyproject.toml`, add `"tavily-python>=0.5.0"` to the `dependencies` list (after the `openai` line):

```toml
dependencies = [
    "recbuddy",
    "boto3>=1.42.38",
    "fastapi>=0.128.0",
    "openai>=2.24.0",
    "pillow>=12.1.0",
    "pydantic-settings>=2.12.0",
    "python-multipart>=0.0.22",
    "safetensors>=0.4.0",
    "tavily-python>=0.5.0",
    "torch",
    "torchvision",
    "uvicorn>=0.40.0",
]
```

**Step 2: Lock the dependency**

Run from `api/`:
```bash
cd api && uv lock
```

Expected: `uv.lock` updates with `tavily-python` and its transitive deps. No errors.

**Step 3: Sync the venv**

```bash
cd api && uv sync
```

Expected: `tavily-python` installed into the venv.

**Step 4: Verify import**

```bash
cd api && uv run python -c "from tavily import TavilyClient; print('OK')"
```

Expected: `OK`

**Step 5: Commit**

```bash
git add api/pyproject.toml api/uv.lock
git commit -m "feat(api): add tavily-python dependency for search-based grounding"
```

---

### Task 2: Update config — add `tavily_api_key` and `search_cache_ttl_seconds`, remove `guidelines_data_path`

**Files:**
- Modify: `api/app/config.py`
- Modify: `api/config/.env.dev`

**Step 1: Update `config.py`**

Replace the current `Settings` class body in `api/app/config.py` so it looks like this:

```python
class Settings(BaseSettings):
    """Application settings."""

    s3_bucket: str = "recycling-buddy-training"
    s3_endpoint_url: str | None = None
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    cors_origins: str = "http://localhost:5173"
    model_artifact_path: str = "model/artifacts/model.safetensors"
    openai_api_key: str | None = None
    tavily_api_key: str | None = None
    guidelines_cache_ttl_seconds: int = 604800  # 1 week
    search_cache_ttl_seconds: int = 86400  # 24 hours

    model_config = {
        "env_file": f"config/.env.{os.getenv('ENVIRONMENT', 'DEV').lower()}",
    }
```

Changes:
- Remove `guidelines_data_path` line
- Add `tavily_api_key: str | None = None`
- Add `search_cache_ttl_seconds: int = 86400`
- Remove the `import pathlib` and `_PROJECT_ROOT` lines at module top (no longer needed)

Full file should be:

```python
"""Configuration settings for the API."""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    s3_bucket: str = "recycling-buddy-training"
    s3_endpoint_url: str | None = None
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    cors_origins: str = "http://localhost:5173"
    model_artifact_path: str = "model/artifacts/model.safetensors"
    openai_api_key: str | None = None
    tavily_api_key: str | None = None
    guidelines_cache_ttl_seconds: int = 604800  # 1 week
    search_cache_ttl_seconds: int = 86400  # 24 hours

    model_config = {
        "env_file": f"config/.env.{os.getenv('ENVIRONMENT', 'DEV').lower()}",
    }


settings = Settings()
```

**Step 2: Update `.env.dev`**

Replace `api/config/.env.dev` contents:

```
S3_BUCKET=recycling-buddy-training
S3_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
OPENAI_API_KEY=
TAVILY_API_KEY=
```

**Step 3: Commit**

```bash
git add api/app/config.py api/config/.env.dev
git commit -m "feat(api): add tavily_api_key and search_cache_ttl_seconds config, remove guidelines_data_path"
```

---

### Task 3: Rewrite `GuidelinesService` — replace mapping + scraper with Tavily search

**Files:**
- Modify: `api/app/guidelines.py`

**Step 1: Write the new implementation**

Replace the full contents of `api/app/guidelines.py` with the following. Key changes:
- Remove: `_load_mapping()`, `_rny_url()`, `_fetch_page()`, `_label_to_rny` dict, `RNY_MATERIAL_BASE`, `SCRAPE_HEADERS`, `FETCH_TIMEOUT`
- Add: `_search_rny()`, `_search_cache` dict
- Modify: `__init__()`, `lookup()`, `_call_llm()` (parameter renamed from `page_html` to `search_content`)

```python
"""LLM-backed guidelines lookup service for council recycling advice.

Uses Tavily search to find relevant recyclingnearyou.com.au pages as
grounding context, calls OpenAI to extract a structured bin decision,
and caches results in-memory (advice: 1 week TTL, search: 24h TTL).
"""

import json
import logging
import time
from dataclasses import dataclass, replace

from openai import AsyncOpenAI
from tavily import TavilyClient

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AdviceRecord:
    """Structured bin advice for a single (item_category, council_slug) pair."""

    bin_colour: str  # "red" | "yellow" | "green" | "blue" | "purple" | "special"
    bin_name: str  # e.g. "General Waste", "Recycling"
    prep_instructions: str  # e.g. "Rinse, remove lid, flatten" or ""
    disposal_method: str  # "kerbside" | "special_disposal" | "drop_off"
    special_disposal_flag: bool
    notes: str
    is_fallback: bool
    council_slug: str
    item_category: str


_FALLBACK = AdviceRecord(
    bin_colour="red",
    bin_name="General Waste",
    prep_instructions="",
    disposal_method="kerbside",
    special_disposal_flag=False,
    notes=(
        "We couldn't find specific advice for this item — "
        "general waste is the safe choice to prevent recycling contamination. "
        "Check your council's website for more information."
    ),
    is_fallback=True,
    council_slug="",
    item_category="",
)


SYSTEM_PROMPT = """\
You are a recycling advisor for Australian households. You will be given search \
results from recyclingnearyou.com.au and asked to extract the recycling advice for \
a specific item in a specific council area.

Respond ONLY with a JSON object matching this exact schema:
{
  "bin_colour": "<red|yellow|green|blue|purple|special>",
  "bin_name": "<bin display name, e.g. General Waste, Recycling, FOGO>",
  "prep_instructions": "<prep steps or empty string>",
  "disposal_method": "<kerbside|special_disposal|drop_off>",
  "special_disposal_flag": <true|false>,
  "notes": "<any extra context or empty string>",
  "is_fallback": <true|false>
}

Rules:
- bin_colour must be one of: red, yellow, green, blue, purple, special
- If the item requires special disposal (e.g. batteries, e-waste, chemicals), set \
  disposal_method to "special_disposal" and special_disposal_flag to true
- If you cannot find specific advice for the item in the provided search results, \
  set is_fallback to true and use red bin / General Waste as the safe default
- Never invent council-specific rules not present in the search results
- Respond with valid JSON only, no markdown fences
"""


class GuidelinesService:
    """Provides LLM-backed bin advice for (item_category, council_slug) pairs.

    On each lookup:
    1. Check in-memory advice cache (TTL = settings.guidelines_cache_ttl_seconds)
    2. Check in-memory search cache (TTL = settings.search_cache_ttl_seconds)
    3. On search miss: call Tavily to search recyclingnearyou.com.au
    4. Call OpenAI with the search content and extract a structured AdviceRecord
    5. If search or LLM fails, fall back to general waste + disclaimer
    6. Cache and return the result
    """

    def __init__(self) -> None:
        self._advice_cache: dict[tuple[str, str], tuple[AdviceRecord, float]] = {}
        self._search_cache: dict[tuple[str, str], tuple[str, float]] = {}
        self._advice_ttl = settings.guidelines_cache_ttl_seconds
        self._search_ttl = settings.search_cache_ttl_seconds
        self._openai = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if settings.openai_api_key
            else None
        )
        self._tavily = (
            TavilyClient(api_key=settings.tavily_api_key)
            if settings.tavily_api_key
            else None
        )

    def _search_rny(self, item_category: str, council_slug: str) -> str | None:
        """Search recyclingnearyou.com.au for item + council recycling advice.

        Args:
            item_category: Classifier label (e.g. 'cardboard').
            council_slug: RNY council slug (e.g. 'SydneyNSW').

        Returns:
            Extracted text content from search results, or None if no results.
        """
        if not self._tavily:
            return None

        # Check search cache
        cache_key = (item_category, council_slug)
        cached = self._search_cache.get(cache_key)
        if cached:
            content, inserted_at = cached
            if time.time() - inserted_at < self._search_ttl:
                logger.info("Search cache hit for %s/%s", item_category, council_slug)
                return content
            del self._search_cache[cache_key]

        # Human-readable query for Tavily
        query = f"{item_category.replace('-', ' ')} recycling {council_slug}"
        try:
            response = self._tavily.search(
                query=query,
                search_depth="basic",
                include_domains=["recyclingnearyou.com.au"],
                max_results=3,
            )
            results = response.get("results", [])
            if not results:
                logger.info(
                    "Tavily returned no results for %s/%s",
                    item_category,
                    council_slug,
                )
                return None

            # Concatenate extracted content from top results
            content = "\n\n---\n\n".join(
                f"Source: {r.get('url', 'unknown')}\n{r.get('content', '')}"
                for r in results
            )
            self._search_cache[cache_key] = (content, time.time())
            return content

        except Exception as exc:
            logger.warning(
                "Tavily search failed for %s/%s: %s",
                item_category,
                council_slug,
                exc,
            )
            return None

    async def _call_llm(
        self,
        item_category: str,
        council_slug: str,
        search_content: str | None,
    ) -> AdviceRecord:
        """Call OpenAI to extract advice, falling back to general waste if unavailable.

        Args:
            item_category: Classifier label (e.g. 'cardboard').
            council_slug: RNY council slug (e.g. 'SydneyNSW').
            search_content: Extracted text from Tavily search, or None.

        Returns:
            AdviceRecord from LLM extraction, or fallback record on failure.
        """
        if not self._openai:
            logger.warning(
                "No OPENAI_API_KEY configured — returning fallback for %s/%s",
                item_category,
                council_slug,
            )
            return replace(
                _FALLBACK, council_slug=council_slug, item_category=item_category
            )

        if search_content:
            context_block = search_content[:8000]
            user_message = (
                f"Council: {council_slug}\n"
                f"Item: {item_category}\n\n"
                f"Search results from recyclingnearyou.com.au:\n{context_block}\n\n"
                "Extract the recycling advice for this item in this council area."
            )
        else:
            user_message = (
                f"Council: {council_slug}\n"
                f"Item: {item_category}\n\n"
                "No search results were available from recyclingnearyou.com.au. "
                "Using your training knowledge, provide the most likely recycling advice "
                "for this item in an Australian council context. "
                "If uncertain, set is_fallback to true."
            )

        try:
            response = await self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return AdviceRecord(
                bin_colour=data.get("bin_colour", "red"),
                bin_name=data.get("bin_name", "General Waste"),
                prep_instructions=data.get("prep_instructions", ""),
                disposal_method=data.get("disposal_method", "kerbside"),
                special_disposal_flag=bool(data.get("special_disposal_flag", False)),
                notes=data.get("notes", ""),
                is_fallback=bool(data.get("is_fallback", False)),
                council_slug=council_slug,
                item_category=item_category,
            )
        except Exception as exc:
            logger.error(
                "OpenAI call failed for %s/%s: %s", item_category, council_slug, exc
            )
            return replace(
                _FALLBACK, council_slug=council_slug, item_category=item_category
            )

    async def lookup(self, item_category: str, council_slug: str) -> AdviceRecord:
        """Return bin advice for (item_category, council_slug).

        Checks advice cache first. On miss: searches RNY via Tavily for grounding
        context, calls OpenAI, caches and returns result. Falls back to general
        waste on any failure.

        Args:
            item_category: Classifier label (e.g. 'cardboard', 'glass-bottles-jars').
            council_slug: RNY council slug (e.g. 'SydneyNSW', 'MelbourneVIC').

        Returns:
            AdviceRecord with is_fallback=False on success, True on fallback.
        """
        cache_key = (item_category, council_slug)

        # Tier 1: advice cache
        cached = self._advice_cache.get(cache_key)
        if cached:
            record, inserted_at = cached
            if time.time() - inserted_at < self._advice_ttl:
                logger.info("Advice cache hit for %s/%s", item_category, council_slug)
                return record
            del self._advice_cache[cache_key]

        # Tier 2: search cache (or fresh Tavily call)
        search_content = self._search_rny(item_category, council_slug)

        record = await self._call_llm(item_category, council_slug, search_content)
        self._advice_cache[cache_key] = (record, time.time())
        logger.info(
            "Guidelines lookup: item=%s council=%s fallback=%s",
            item_category,
            council_slug,
            record.is_fallback,
        )
        return record
```

**Step 2: Commit**

```bash
git add api/app/guidelines.py
git commit -m "feat(api): replace label_to_rny mapping with Tavily search grounding"
```

---

### Task 4: Update tests for the new Tavily-based `GuidelinesService`

**Files:**
- Modify: `api/tests/test_guidelines.py`

**Step 1: Update the test file**

Replace the full contents of `api/tests/test_guidelines.py`. Changes:
- `_settings_with_no_key()` now returns `tavily_api_key` and `search_cache_ttl_seconds` instead of `guidelines_data_path`
- Add test for search cache hit (Tavily not called on second lookup)
- Add test for Tavily failure → fallback
- Existing tests remain largely the same but now mock `_search_rny` instead of relying on the mapping file

```python
"""Unit tests for GuidelinesService — fallback, cache, label coverage, search."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.guidelines import AdviceRecord, GuidelinesService
from recbuddy.labels import ALL_LABELS_LIST

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

VALID_BIN_COLOURS = {"red", "yellow", "green", "blue", "purple", "special"}
VALID_DISPOSAL_METHODS = {"kerbside", "special_disposal", "drop_off"}


def _make_advice_record(
    bin_colour: str = "yellow",
    bin_name: str = "Recycling",
    prep_instructions: str = "Rinse and empty",
    disposal_method: str = "kerbside",
    special_disposal_flag: bool = False,
    notes: str = "",
    is_fallback: bool = False,
    council_slug: str = "SydneyNSW",
    item_category: str = "cardboard",
) -> AdviceRecord:
    """Return a fully-populated AdviceRecord for use in tests."""
    return AdviceRecord(
        bin_colour=bin_colour,
        bin_name=bin_name,
        prep_instructions=prep_instructions,
        disposal_method=disposal_method,
        special_disposal_flag=special_disposal_flag,
        notes=notes,
        is_fallback=is_fallback,
        council_slug=council_slug,
        item_category=item_category,
    )


# ---------------------------------------------------------------------------
# Test 1: fallback when no OPENAI_API_KEY
# ---------------------------------------------------------------------------


async def test_fallback_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """GuidelinesService with no API key returns a fallback AdviceRecord."""
    monkeypatch.setattr("app.guidelines.settings", _settings_with_no_key())
    svc = GuidelinesService()

    result = await svc.lookup("cardboard", "SydneyNSW")

    assert isinstance(result, AdviceRecord)
    assert result.is_fallback is True
    assert result.bin_colour == "red"
    assert result.bin_name == "General Waste"
    assert "safe choice" in result.notes


# ---------------------------------------------------------------------------
# Test 2: advice cache prevents duplicate LLM calls
# ---------------------------------------------------------------------------


async def test_advice_cache_prevents_second_llm_call() -> None:
    """Second lookup with same args should hit advice cache, not call LLM again."""
    svc = GuidelinesService()
    mock_record = _make_advice_record()

    with (
        patch.object(
            svc, "_call_llm", new_callable=AsyncMock, return_value=mock_record
        ) as mock_llm,
        patch.object(svc, "_search_rny", return_value=None),
    ):
        await svc.lookup("cardboard", "SydneyNSW")
        await svc.lookup("cardboard", "SydneyNSW")  # should hit cache
        assert mock_llm.call_count == 1, (
            "LLM should only be called once (second call hits advice cache)"
        )


# ---------------------------------------------------------------------------
# Test 3: cache key includes both item and council
# ---------------------------------------------------------------------------


async def test_cache_key_is_item_and_council() -> None:
    """Different council slug = different cache key; LLM called twice."""
    svc = GuidelinesService()
    record_sydney = _make_advice_record(council_slug="SydneyNSW")
    record_melbourne = _make_advice_record(council_slug="MelbourneVIC")

    def _side_effect(item_category: str, council_slug: str, search_content):
        if council_slug == "SydneyNSW":
            return record_sydney
        return record_melbourne

    with (
        patch.object(
            svc, "_call_llm", new_callable=AsyncMock, side_effect=_side_effect
        ) as mock_llm,
        patch.object(svc, "_search_rny", return_value=None),
    ):
        await svc.lookup("cardboard", "SydneyNSW")
        await svc.lookup("cardboard", "MelbourneVIC")
        assert mock_llm.call_count == 2, (
            "Different council = different cache key; LLM must be called twice"
        )


# ---------------------------------------------------------------------------
# Test 4: all 67 labels resolve without exception
# ---------------------------------------------------------------------------


async def test_all_67_labels_do_not_raise() -> None:
    """Every label in ALL_LABELS_LIST must resolve to an AdviceRecord without raising."""
    assert len(ALL_LABELS_LIST) == 67, f"Expected 67 labels, got {len(ALL_LABELS_LIST)}"
    mock_record = _make_advice_record()

    for label in ALL_LABELS_LIST:
        svc = GuidelinesService()
        with (
            patch.object(
                svc, "_call_llm", new_callable=AsyncMock, return_value=mock_record
            ),
            patch.object(svc, "_search_rny", return_value=None),
        ):
            result = await svc.lookup(label, "SydneyNSW")
            assert isinstance(result, AdviceRecord), (
                f"lookup({label!r}) did not return AdviceRecord"
            )


# ---------------------------------------------------------------------------
# Test 5: LLM response fields passed through correctly
# ---------------------------------------------------------------------------


async def test_llm_response_parsed_correctly() -> None:
    """Fields returned by _call_llm must appear unchanged in lookup result."""
    svc = GuidelinesService()
    expected = _make_advice_record(
        bin_colour="green",
        bin_name="FOGO",
        prep_instructions="Remove packaging",
        disposal_method="kerbside",
        special_disposal_flag=False,
        notes="Place in green FOGO bin",
        is_fallback=False,
        council_slug="SydneyNSW",
        item_category="cardboard",
    )

    with (
        patch.object(svc, "_call_llm", new_callable=AsyncMock, return_value=expected),
        patch.object(svc, "_search_rny", return_value=None),
    ):
        result = await svc.lookup("cardboard", "SydneyNSW")

    assert result.bin_colour == expected.bin_colour
    assert result.bin_name == expected.bin_name
    assert result.prep_instructions == expected.prep_instructions
    assert result.disposal_method == expected.disposal_method
    assert result.special_disposal_flag == expected.special_disposal_flag
    assert result.notes == expected.notes
    assert result.is_fallback == expected.is_fallback
    assert result.council_slug == expected.council_slug
    assert result.item_category == expected.item_category


# ---------------------------------------------------------------------------
# Test 6: fallback record fields are complete and valid
# ---------------------------------------------------------------------------


async def test_fallback_record_fields_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallback AdviceRecord must have all fields non-None and valid enum values."""
    monkeypatch.setattr("app.guidelines.settings", _settings_with_no_key())
    svc = GuidelinesService()

    result = await svc.lookup("cardboard", "SydneyNSW")

    for field_name in (
        "bin_colour",
        "bin_name",
        "prep_instructions",
        "disposal_method",
        "notes",
        "council_slug",
        "item_category",
    ):
        value = getattr(result, field_name)
        assert value is not None, f"Field {field_name!r} must not be None"

    assert result.bin_colour in VALID_BIN_COLOURS, (
        f"bin_colour {result.bin_colour!r} not in valid set"
    )
    assert result.disposal_method in VALID_DISPOSAL_METHODS, (
        f"disposal_method {result.disposal_method!r} not in valid set"
    )
    assert isinstance(result.is_fallback, bool)
    assert isinstance(result.special_disposal_flag, bool)


# ---------------------------------------------------------------------------
# Test 7: search cache prevents duplicate Tavily calls
# ---------------------------------------------------------------------------


async def test_search_cache_prevents_second_tavily_call() -> None:
    """Second lookup with same args should hit search cache, not call Tavily again."""
    svc = GuidelinesService()
    svc._tavily = MagicMock()
    svc._tavily.search.return_value = {
        "results": [{"url": "https://recyclingnearyou.com.au/test", "content": "test content"}]
    }
    mock_record = _make_advice_record()

    with patch.object(
        svc, "_call_llm", new_callable=AsyncMock, return_value=mock_record
    ):
        await svc.lookup("cardboard", "SydneyNSW")
        # Clear advice cache to force search path
        svc._advice_cache.clear()
        await svc.lookup("cardboard", "SydneyNSW")

    assert svc._tavily.search.call_count == 1, (
        "Tavily should only be called once (second call hits search cache)"
    )


# ---------------------------------------------------------------------------
# Test 8: Tavily failure returns fallback via LLM
# ---------------------------------------------------------------------------


async def test_tavily_failure_falls_back_gracefully() -> None:
    """When Tavily raises an exception, lookup still returns an AdviceRecord."""
    svc = GuidelinesService()
    svc._tavily = MagicMock()
    svc._tavily.search.side_effect = Exception("API error")
    mock_record = _make_advice_record(is_fallback=True)

    with patch.object(
        svc, "_call_llm", new_callable=AsyncMock, return_value=mock_record
    ) as mock_llm:
        result = await svc.lookup("cardboard", "SydneyNSW")

    assert isinstance(result, AdviceRecord)
    # LLM should be called with search_content=None
    mock_llm.assert_called_once_with("cardboard", "SydneyNSW", None)


# ---------------------------------------------------------------------------
# Test 9: no TAVILY_API_KEY — LLM called with no search content
# ---------------------------------------------------------------------------


async def test_no_tavily_key_calls_llm_without_search() -> None:
    """With no Tavily key, LLM is called with search_content=None."""
    svc = GuidelinesService()
    svc._tavily = None  # simulate no key
    mock_record = _make_advice_record()

    with patch.object(
        svc, "_call_llm", new_callable=AsyncMock, return_value=mock_record
    ) as mock_llm:
        await svc.lookup("cardboard", "SydneyNSW")

    mock_llm.assert_called_once_with("cardboard", "SydneyNSW", None)


# ---------------------------------------------------------------------------
# Helper: fake settings without API keys
# ---------------------------------------------------------------------------


def _settings_with_no_key():
    """Return a settings-like object with no openai_api_key or tavily_api_key."""

    class _FakeSettings:
        openai_api_key: str | None = None
        tavily_api_key: str | None = None
        guidelines_cache_ttl_seconds: float = 604800.0
        search_cache_ttl_seconds: float = 86400.0

    return _FakeSettings()
```

**Step 2: Run tests**

```bash
cd api && uv run pytest tests/test_guidelines.py -v
```

Expected: All 9 tests pass.

**Step 3: Commit**

```bash
git add api/tests/test_guidelines.py
git commit -m "test(api): update guidelines tests for Tavily search grounding"
```

---

### Task 5: Remove `GUIDELINES_DATA_PATH` from Docker/infra files

**Files:**
- Modify: `api/Dockerfile`
- Modify: `docker-compose.yml`

**Step 1: Update `api/Dockerfile`**

Remove lines 8-9 (the comment and `ENV GUIDELINES_DATA_PATH` line). The file should become:

```dockerfile
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy recbuddy package (path dependency of the api)
# Only the package source is needed — not the full model directory
COPY model/pyproject.toml /model/pyproject.toml
COPY model/README.md /model/README.md
COPY model/recbuddy/ /model/recbuddy/

# Copy api project files and install dependencies
COPY api/pyproject.toml .
COPY api/uv.lock .
RUN uv sync --frozen

# Copy remaining api source
COPY api/ .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Update `docker-compose.yml`**

In the `api` service `environment` block, remove the `GUIDELINES_DATA_PATH` line. Also remove the `- ./data:/app/data` volume mount since it's no longer needed.

The `api` service should look like:

```yaml
  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./api/app:/app/app
      - ./model:/app/model
    environment:
      - PYTHONUNBUFFERED=1
      - MODEL_ARTIFACT_PATH=/app/model/artifacts/model.safetensors
      - ENVIRONMENT=DEV
      - S3_BUCKET=recycling-buddy-training
      - S3_ENDPOINT_URL=http://localstack:4566
      - AWS_ACCESS_KEY_ID=test
      - AWS_SECRET_ACCESS_KEY=test
      - AWS_REGION=us-east-1
    command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on:
      model:
        condition: service_started
      localstack:
        condition: service_healthy
```

**Step 3: Commit**

```bash
git add api/Dockerfile docker-compose.yml
git commit -m "chore: remove GUIDELINES_DATA_PATH from Docker config"
```

---

### Task 6: Delete `data/label_to_rny.json` and update CLAUDE.md

**Files:**
- Delete: `data/label_to_rny.json`
- Modify: `CLAUDE.md`

**Step 1: Delete the mapping file**

```bash
git rm data/label_to_rny.json
```

**Step 2: Update CLAUDE.md**

In `CLAUDE.md`, update the **Guidelines advice flow** section (around line 53-56). Replace:

```
1. Look up `label_to_rny.json` (`data/label_to_rny.json`) for the classifier label → RNY slug + URL
2. Fetch the council's RNY page HTML as grounding context
```

With:

```
1. Search recyclingnearyou.com.au via Tavily for the classifier label + council slug
2. Use the search results as grounding context
```

Also update the **Labels** section (around line 61). Replace:

```
`api/app/labels.py` is the single source of truth for the 67 waste category labels. Labels are lowercase with hyphens (e.g. `glass-bottles-jars`). The `data/label_to_rny.json` maps each label to its Recycling Near You slug and URL.
```

With:

```
`api/app/labels.py` is the single source of truth for the 67 waste category labels. Labels are lowercase with hyphens (e.g. `glass-bottles-jars`).
```

Also update the **Configuration** section (around line 49). In `Key settings:`, replace `guidelines_data_path` with `tavily_api_key, search_cache_ttl_seconds`.

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove label_to_rny.json, update CLAUDE.md for Tavily search"
```

---

### Task 7: Run full test suite and verify

**Step 1: Run API tests**

```bash
cd api && uv run pytest -v
```

Expected: All tests pass, no import errors, no references to `guidelines_data_path` or `label_to_rny`.

**Step 2: Verify no stale references**

```bash
grep -r "label_to_rny" . --include="*.py" --include="*.yml" --include="*.toml" --include="*.env*"
grep -r "guidelines_data_path" . --include="*.py" --include="*.yml" --include="*.toml" --include="*.env*"
```

Expected: No matches (only the design doc and CLAUDE.md history should mention it, if at all).

**Step 3: Lint**

```bash
cd api && uv run ruff check . && uv run ruff format --check .
```

Expected: No lint or format errors.
