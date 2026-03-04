"""Unit tests for WasteDataset.

Tests must FAIL before implementation is complete (TDD — constitution Principle II).
S3 interactions are fully mocked — no real AWS calls are made.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

from recbuddy.dataset import WasteDataset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image_dir(root: Path, labels: list[str], images_per_label: int = 5) -> None:
    """Populate root/<label>/<n>.jpg with tiny solid-colour images."""
    for label in labels:
        label_dir = root / label
        label_dir.mkdir(parents=True)
        for i in range(images_per_label):
            img = Image.new("RGB", (32, 32), color=(i * 10, 50, 100))
            img.save(label_dir / f"{i}.jpg")


# ---------------------------------------------------------------------------
# WasteDataset.get_splits
# ---------------------------------------------------------------------------


LABELS = ["paper-cardboard", "plastic-containers", "glass-containers"]
IMAGES_PER_LABEL = 10


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    _make_image_dir(tmp_path, LABELS, IMAGES_PER_LABEL)
    return tmp_path


@pytest.fixture
def dataset(data_dir: Path) -> WasteDataset:
    ds = WasteDataset(s3_bucket="test-bucket", data_dir=data_dir)
    return ds


def test_get_splits_returns_three_datasets(dataset: WasteDataset) -> None:
    train, val, test = dataset.get_splits(seed=0)
    assert train is not None
    assert val is not None
    assert test is not None


def test_get_splits_indices_sum_to_total(dataset: WasteDataset) -> None:
    total = len(LABELS) * IMAGES_PER_LABEL
    train, val, test = dataset.get_splits(val_frac=0.2, test_frac=0.2, seed=0)
    assert len(train) + len(val) + len(test) == total


def test_get_splits_no_index_overlap(dataset: WasteDataset) -> None:
    train, val, test = dataset.get_splits(seed=0)
    train_idx = set(train.indices)
    val_idx = set(val.indices)
    test_idx = set(test.indices)
    assert train_idx.isdisjoint(val_idx)
    assert train_idx.isdisjoint(test_idx)
    assert val_idx.isdisjoint(test_idx)


def test_get_splits_labels_are_valid_indices(dataset: WasteDataset) -> None:
    train, val, test = dataset.get_splits(seed=0)
    for ds in (train, val, test):
        for _, label_idx in ds:
            assert 0 <= label_idx < len(LABELS)


def test_get_splits_raises_when_data_dir_empty(tmp_path: Path) -> None:
    ds = WasteDataset(s3_bucket="test-bucket", data_dir=tmp_path / "empty")
    with pytest.raises(FileNotFoundError):
        ds.get_splits()


# ---------------------------------------------------------------------------
# WasteDataset.download (mocked S3)
# ---------------------------------------------------------------------------


def test_download_calls_s3_list_objects(tmp_path: Path) -> None:
    ds = WasteDataset(s3_bucket="test-bucket", data_dir=tmp_path)

    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [{"Contents": []}]
    ds._s3 = mock_s3

    ds.download()

    mock_s3.get_paginator.assert_called_once_with("list_objects_v2")


def test_download_skips_existing_files(tmp_path: Path) -> None:
    ds = WasteDataset(s3_bucket="test-bucket", data_dir=tmp_path)

    # Pre-create the local file
    key = "cardboard/image.jpg"
    local = tmp_path / key
    local.parent.mkdir(parents=True)
    local.write_bytes(b"fake")

    mock_s3 = MagicMock()
    mock_paginator = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [{"Contents": [{"Key": key}]}]
    ds._s3 = mock_s3

    ds.download()

    mock_s3.download_file.assert_not_called()
