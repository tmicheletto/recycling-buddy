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
        "results": [
            {"url": "https://recyclingnearyou.com.au/test", "content": "test content"}
        ]
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
