"""Tests for GET /labels endpoint."""

from fastapi.testclient import TestClient

from src.labels import ALL_LABELS, LABELS_BY_CATEGORY
from src.main import app

client = TestClient(app)


def test_labels_response_structure():
    """Test that /labels returns expected structure."""
    response = client.get("/labels")
    assert response.status_code == 200

    data = response.json()
    assert "categories" in data
    assert "total_count" in data
    assert isinstance(data["categories"], list)
    assert data["total_count"] == len(ALL_LABELS)


def test_labels_category_completeness():
    """Test that all categories from labels module are present."""
    response = client.get("/labels")
    data = response.json()

    returned_categories = {c["category"] for c in data["categories"]}
    expected_categories = set(LABELS_BY_CATEGORY.keys())
    assert returned_categories == expected_categories


def test_labels_item_structure():
    """Test that each item has value and display_name."""
    response = client.get("/labels")
    data = response.json()

    for category in data["categories"]:
        assert "category" in category
        assert "items" in category
        for item in category["items"]:
            assert "value" in item
            assert "display_name" in item


def test_labels_display_name_formatting():
    """Test that display names are title-cased human-readable."""
    response = client.get("/labels")
    data = response.json()

    # Find aluminum-can and check its display name
    for category in data["categories"]:
        for item in category["items"]:
            if item["value"] == "aluminum-can":
                assert item["display_name"] == "Aluminum Can"
                return

    raise AssertionError("aluminum-can not found in response")


def test_labels_values_are_s3_safe():
    """Test that all label values use only lowercase, digits, hyphens."""
    import re

    response = client.get("/labels")
    data = response.json()

    pattern = re.compile(r"^[a-z][a-z0-9-]*$")
    for category in data["categories"]:
        for item in category["items"]:
            assert pattern.match(item["value"]), (
                f"Label '{item['value']}' is not S3-safe"
            )


def test_labels_total_count_matches():
    """Test that total_count matches actual number of items."""
    response = client.get("/labels")
    data = response.json()

    actual_count = sum(len(cat["items"]) for cat in data["categories"])
    assert data["total_count"] == actual_count
