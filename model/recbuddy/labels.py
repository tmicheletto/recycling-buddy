"""Household waste item labels — single source of truth for the recbuddy package.

Labels are S3-safe strings (lowercase letters, digits, hyphens)
used as directory prefixes when storing training images.
"""

import re

ALL_LABELS_LIST: list[str] = [
    "aerosols",
    "aluminium-cans",
    "asbestos",
    "batteries-single-use",
    "cars",
    "cartons",
    "cartridges",
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

ALL_LABELS: frozenset[str] = frozenset(ALL_LABELS_LIST)

_S3_SAFE_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def is_valid_label(value: str) -> bool:
    """Check whether *value* is a recognized item label."""
    return value in ALL_LABELS


def is_s3_safe(value: str) -> bool:
    """Check whether *value* is safe for use as an S3 key prefix."""
    return bool(_S3_SAFE_RE.match(value))
