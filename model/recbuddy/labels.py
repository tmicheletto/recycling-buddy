"""Household waste item labels — single source of truth for the recbuddy package.

Labels are S3-safe strings (lowercase letters, digits, hyphens)
used as directory prefixes when storing training images.
"""

import re

ALL_LABELS_LIST: list[str] = [
    "aerosol-cans",
    "aluminium-foil-trays",
    "animal-waste",
    "bagged-recyclables",
    "bagged-rubbish",
    "batteries-electronics",
    "building-materials",
    "bulky-items",
    "cardboard",
    "cd-dvd-cases",
    "ceramics",
    "citrus-aromatics",
    "clothing-textiles",
    "coat-hangers",
    "coffee-cups-pods",
    "compostable-liners",
    "compostable-packaging",
    "crockery",
    "dairy-eggshells",
    "dead-animals",
    "disposable-cutlery-plates",
    "food-leftovers",
    "food-packaging",
    "fruit-vegetable-scraps",
    "garden-waste",
    "gas-bottles-extinguishers",
    "general-rubbish",
    "glass-bottles-jars",
    "glass-mirrors",
    "grains-cereals",
    "hair",
    "hazardous-chemicals",
    "hessian-bags",
    "hot-ashes",
    "large-logs-stumps",
    "liquids",
    "meat-seafood-bones",
    "metal-cans-tins",
    "motor-oil-containers",
    "nappies",
    "non-approved-liners",
    "oil-paints",
    "paper",
    "plant-pots",
    "plastic-bags-soft-plastic",
    "plastic-bottles-containers",
    "plastic-coated-paper",
    "plastic-lids",
    "plastic-lined-cardboard",
    "plastic-strapping",
    "plastic-tubes",
    "polystyrene-foam",
    "reusable-containers",
    "rocks-soil",
    "scrap-metal",
    "seafood-shells",
    "shredded-laminated-paper",
    "steel-pots-pans",
    "syringes-sharps",
    "tea-coffee-grounds",
    "teabags",
    "tissues-paper-towel",
    "toothpaste-toothbrushes",
    "vacuum-dust",
    "waxed-cardboard",
    "wet-wipes",
    "wooden-utensils",
]

ALL_LABELS: frozenset[str] = frozenset(ALL_LABELS_LIST)

_S3_SAFE_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def is_valid_label(value: str) -> bool:
    """Check whether *value* is a recognized item label."""
    return value in ALL_LABELS


def is_s3_safe(value: str) -> bool:
    """Check whether *value* is safe for use as an S3 key prefix."""
    return bool(_S3_SAFE_RE.match(value))
