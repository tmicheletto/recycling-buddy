"""Unit tests for labels module data integrity."""

import re

from src.labels import ALL_LABELS, ALL_LABELS_LIST, is_s3_safe, is_valid_label


def test_all_labels_s3_safe():
    """Test that every label matches S3-safe pattern."""
    pattern = re.compile(r"^[a-z][a-z0-9-]*$")
    for label in ALL_LABELS:
        assert pattern.match(label), f"Label '{label}' is not S3-safe"


def test_all_labels_frozenset_matches_list():
    """Test that ALL_LABELS contains exactly the labels from the list."""
    assert ALL_LABELS == set(ALL_LABELS_LIST)


def test_is_valid_label_accepts_known():
    """Test is_valid_label returns True for known labels."""
    assert is_valid_label("aluminum-can")
    assert is_valid_label("glass-bottle")
    assert is_valid_label("newspaper")


def test_is_valid_label_rejects_unknown():
    """Test is_valid_label returns False for unknown labels."""
    assert not is_valid_label("recyclable")
    assert not is_valid_label("not_recyclable")
    assert not is_valid_label("")
    assert not is_valid_label("unknown-item-xyz")


def test_is_s3_safe():
    """Test is_s3_safe helper."""
    assert is_s3_safe("aluminum-can")
    assert is_s3_safe("newspaper")
    assert not is_s3_safe("Not Valid")
    assert not is_s3_safe("has_underscore")
    assert not is_s3_safe("")
    assert not is_s3_safe("123-starts-with-digit")


def test_total_label_count():
    """Test the expected total number of labels."""
    assert len(ALL_LABELS) == 124


def test_list_is_sorted():
    """Test that ALL_LABELS_LIST is alphabetically sorted."""
    assert ALL_LABELS_LIST == sorted(ALL_LABELS_LIST)
