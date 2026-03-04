# Labels from recyclingnearyou.com.au Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 67 classifier labels with the 48 Home material categories from recyclingnearyou.com.au.

**Architecture:** Single source of truth (`model/recbuddy/labels.py`) gets new label list. Tests and one comment that hardcode "67" get updated to "48". No migration needed.

**Tech Stack:** Python, pytest

---

### Task 1: Update test expectations for new labels

**Files:**
- Modify: `api/tests/test_labels_data.py:20-24` (valid label examples)
- Modify: `api/tests/test_labels_data.py:47` (count 67 → 48)
- Modify: `api/tests/test_guidelines.py:123` (count 67 → 48)

**Step 1: Update test_labels_data.py — fix valid label examples**

Change the `test_is_valid_label_accepts_known` test to use labels that exist in the new set:

```python
def test_is_valid_label_accepts_known():
    """Test is_valid_label returns True for known labels."""
    assert is_valid_label("steel-cans")
    assert is_valid_label("glass-containers")
    assert is_valid_label("paper-cardboard")
```

**Step 2: Update test_labels_data.py — fix label count**

```python
def test_total_label_count():
    """Test the expected total number of labels."""
    assert len(ALL_LABELS) == 48
```

**Step 3: Update test_guidelines.py — fix label count**

Change line 123 from:
```python
assert len(ALL_LABELS_LIST) == 67, f"Expected 67 labels, got {len(ALL_LABELS_LIST)}"
```
to:
```python
assert len(ALL_LABELS_LIST) == 48, f"Expected 48 labels, got {len(ALL_LABELS_LIST)}"
```

**Step 4: Run tests to verify they fail**

Run: `cd api && uv run pytest tests/test_labels_data.py tests/test_guidelines.py -v`
Expected: FAIL (labels still have old values)

---

### Task 2: Replace labels in labels.py

**Files:**
- Modify: `model/recbuddy/labels.py:9-77`

**Step 1: Replace ALL_LABELS_LIST contents**

Replace the entire list with:

```python
ALL_LABELS_LIST: list[str] = [
    "aerosols",
    "aluminium-cans",
    "asbestos",
    "batteries-single-use",
    "cars",
    "cartridges",
    "cartons",
    "cds-dvds",
    "chemical-drums",
    "chemicals",
    "clothing",
    "coffee-capsules",
    "coffee-cups",
    "computers",
    "cooking-oil",
    "corks",
    "demolition",
    "electrical",
    "electrical-battery-operated",
    "fluorescent-lights",
    "food",
    "furniture",
    "garden-organics",
    "gas-bottles",
    "glass-containers",
    "glasses",
    "incandescent-lights",
    "lead-acid-batteries",
    "led-lights",
    "mattresses",
    "medicines",
    "mobile-phones",
    "motor-oil",
    "office-paper",
    "paper-cardboard",
    "plastic-containers",
    "polystyrene",
    "pool-chemicals",
    "power-tools",
    "scrap-metals",
    "soft-plastics",
    "steel-cans",
    "tapes",
    "televisions",
    "tyres",
    "vapes",
    "whitegoods",
    "x-rays",
]
```

**Step 2: Update the comment in inference.py**

In `api/app/inference.py:34`, change:
```python
_NUM_CLASSES: int = len(ALL_LABELS_LIST)  # 67
```
to:
```python
_NUM_CLASSES: int = len(ALL_LABELS_LIST)  # 48
```

**Step 3: Reinstall recbuddy package in api venv**

Run: `cd api && uv sync`

This ensures the api venv picks up the updated labels from the local `recbuddy` package.

**Step 4: Run all tests**

Run: `cd api && uv run pytest tests/test_labels_data.py tests/test_guidelines.py -v`
Expected: ALL PASS

**Step 5: Run full test suite**

Run: `cd api && uv run pytest -v`
Expected: ALL PASS (inference tests mock the model so label count doesn't matter at runtime)

**Step 6: Commit**

```bash
git add model/recbuddy/labels.py api/app/inference.py api/tests/test_labels_data.py api/tests/test_guidelines.py
git commit -m "feat: replace labels with recyclingnearyou.com.au Home categories

Swap 67 custom labels for the 48 material categories used by
recyclingnearyou.com.au/materials (Home section). Labels now use
the site's URL slugs, giving a direct mapping for guidelines search."
```
