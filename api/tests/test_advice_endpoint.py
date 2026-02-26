"""Integration tests for GET /advice endpoint.

The GuidelinesService is mocked on app.state to avoid real OpenAI calls.
Follows the same pattern as test_predict_endpoint.py: inject mock on app.state
before creating the TestClient (no context manager — avoids lifespan startup).
"""
import dataclasses
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.guidelines import AdviceRecord
from src.inference import CategoryPrediction, ClassificationResult
from src.main import app

# ---------------------------------------------------------------------------
# Shared mock advice records
# ---------------------------------------------------------------------------

MOCK_ADVICE = AdviceRecord(
    bin_colour="yellow",
    bin_name="Recycling",
    prep_instructions="Rinse and empty",
    disposal_method="kerbside",
    special_disposal_flag=False,
    notes="",
    is_fallback=False,
    council_slug="SydneyNSW",
    item_category="cardboard",
)

MOCK_FALLBACK = AdviceRecord(
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
    council_slug="SydneyNSW",
    item_category="cardboard",
)

MOCK_SPECIAL = AdviceRecord(
    bin_colour="special",
    bin_name="Special Disposal",
    prep_instructions="Tape terminals before disposal",
    disposal_method="special_disposal",
    special_disposal_flag=True,
    notes="Batteries must not go in kerbside bins — take to a battery drop-off point.",
    is_fallback=False,
    council_slug="SydneyNSW",
    item_category="batteries-electronics",
)


# ---------------------------------------------------------------------------
# Helper: a minimal mock model to satisfy app.state.model
# ---------------------------------------------------------------------------


def _make_mock_model() -> MagicMock:
    """Return a minimal mock ClassificationModel for app.state.model."""
    mock = MagicMock()
    mock.predict.return_value = ClassificationResult(
        top_prediction=CategoryPrediction(label="cardboard", confidence=0.9),
        alternatives=[
            CategoryPrediction(label="cardboard", confidence=0.9),
            CategoryPrediction(label="paper", confidence=0.05),
            CategoryPrediction(label="plastic-bags-soft-plastic", confidence=0.05),
        ],
    )
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_mock_guidelines() -> TestClient:
    """TestClient with a mock GuidelinesService injected into app.state.

    Does NOT use a context manager so the lifespan is not triggered
    (same pattern as test_predict_endpoint.py).
    """
    mock_service = AsyncMock()
    mock_service.lookup = AsyncMock(return_value=MOCK_ADVICE)
    app.state.model = _make_mock_model()
    app.state.guidelines_service = mock_service
    return TestClient(app)


@pytest.fixture
def client_with_special_disposal() -> TestClient:
    """TestClient whose mock returns a special-disposal AdviceRecord."""
    mock_service = AsyncMock()
    mock_service.lookup = AsyncMock(return_value=MOCK_SPECIAL)
    app.state.model = _make_mock_model()
    app.state.guidelines_service = mock_service
    return TestClient(app)


@pytest.fixture
def client_with_fallback() -> TestClient:
    """TestClient whose mock returns a fallback AdviceRecord."""
    mock_service = AsyncMock()
    mock_service.lookup = AsyncMock(return_value=MOCK_FALLBACK)
    app.state.model = _make_mock_model()
    app.state.guidelines_service = mock_service
    return TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: valid params → 200 with all required fields
# ---------------------------------------------------------------------------


def test_advice_returns_200_with_valid_params(client_with_mock_guidelines: TestClient) -> None:
    """GET /advice with valid query params must return 200 with all required fields."""
    response = client_with_mock_guidelines.get(
        "/advice?item_category=cardboard&council_slug=SydneyNSW"
    )
    assert response.status_code == 200

    body = response.json()
    required_fields = {
        "bin_colour",
        "bin_name",
        "prep_instructions",
        "disposal_method",
        "special_disposal_flag",
        "notes",
        "is_fallback",
        "council_slug",
        "item_category",
    }
    for field in required_fields:
        assert field in body, f"Response missing required field: {field!r}"


# ---------------------------------------------------------------------------
# Test 2: missing item_category → 422
# ---------------------------------------------------------------------------


def test_advice_missing_item_category_returns_422(client_with_mock_guidelines: TestClient) -> None:
    """GET /advice without item_category must return 422."""
    response = client_with_mock_guidelines.get("/advice?council_slug=SydneyNSW")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 3: missing council_slug → 422
# ---------------------------------------------------------------------------


def test_advice_missing_council_slug_returns_422(client_with_mock_guidelines: TestClient) -> None:
    """GET /advice without council_slug must return 422."""
    response = client_with_mock_guidelines.get("/advice?item_category=cardboard")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 4: special disposal item → correct flags in response
# ---------------------------------------------------------------------------


def test_advice_special_disposal_item_returns_correct_flag(
    client_with_special_disposal: TestClient,
) -> None:
    """Items requiring special disposal must have correct flag and disposal_method in response."""
    response = client_with_special_disposal.get(
        "/advice?item_category=batteries-electronics&council_slug=SydneyNSW"
    )
    assert response.status_code == 200

    body = response.json()
    assert body["special_disposal_flag"] is True
    assert body["disposal_method"] == "special_disposal"


# ---------------------------------------------------------------------------
# Test 5: fallback response includes disclaimer
# ---------------------------------------------------------------------------


def test_advice_fallback_includes_disclaimer(client_with_fallback: TestClient) -> None:
    """Fallback response must have is_fallback=True and notes containing disclaimer."""
    response = client_with_fallback.get(
        "/advice?item_category=cardboard&council_slug=SydneyNSW"
    )
    assert response.status_code == 200

    body = response.json()
    assert body["is_fallback"] is True
    assert "safe choice" in body["notes"]


# ---------------------------------------------------------------------------
# Test 6: response schema matches AdviceRecord fields exactly
# ---------------------------------------------------------------------------


def test_advice_response_schema_matches_advice_record_fields(
    client_with_mock_guidelines: TestClient,
) -> None:
    """All AdviceRecord field names must appear in the /advice response JSON."""
    response = client_with_mock_guidelines.get(
        "/advice?item_category=cardboard&council_slug=SydneyNSW"
    )
    assert response.status_code == 200

    body = response.json()
    advice_record_fields = {f.name for f in dataclasses.fields(AdviceRecord)}
    for field_name in advice_record_fields:
        assert field_name in body, f"AdviceRecord field {field_name!r} missing from /advice response"
