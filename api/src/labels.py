"""Household waste item labels — single source of truth.

Labels are S3-safe strings (lowercase letters, digits, hyphens)
used as directory prefixes when storing training images.
"""

import re

LABELS_BY_CATEGORY: dict[str, list[str]] = {
    "Paper and Cardboard": [
        "newspaper",
        "cardboard-box",
        "cereal-box",
        "paper-bag",
        "office-paper",
        "magazine",
        "junk-mail",
        "phone-book",
        "wrapping-paper",
        "paper-towel-roll",
        "egg-carton-paper",
        "paper-plate",
        "notebook",
        "envelope",
        "shredded-paper",
    ],
    "Plastic Containers": [
        "plastic-bottle",
        "plastic-jug",
        "plastic-tub",
        "plastic-cup",
        "plastic-food-container",
        "yogurt-container",
        "plastic-lid",
        "detergent-bottle",
        "shampoo-bottle",
        "plastic-bucket",
    ],
    "Plastic Film and Bags": [
        "plastic-bag",
        "plastic-wrap",
        "bubble-wrap",
        "shrink-wrap",
        "zip-lock-bag",
    ],
    "Glass": [
        "glass-bottle",
        "glass-jar",
        "glass-container",
        "wine-bottle",
        "beer-bottle",
        "glass-cup",
        "broken-glass",
    ],
    "Metal": [
        "aluminum-can",
        "tin-can",
        "steel-can",
        "aluminum-foil",
        "aluminum-tray",
        "aerosol-can",
        "metal-lid",
        "paint-can",
        "wire-hanger",
        "metal-utensil",
    ],
    "Food and Yard Waste": [
        "fruit-scraps",
        "vegetable-scraps",
        "coffee-grounds",
        "coffee-filter",
        "tea-bag",
        "eggshell",
        "bread",
        "pasta",
        "rice",
        "nutshell",
        "yard-trimmings",
        "leaves",
        "grass-clippings",
        "flower",
        "houseplant",
    ],
    "Electronics": [
        "cell-phone",
        "laptop",
        "tablet",
        "computer-monitor",
        "keyboard",
        "mouse",
        "power-cord",
        "charger",
        "headphones",
        "battery",
        "light-bulb-led",
        "light-bulb-fluorescent",
        "light-bulb-incandescent",
    ],
    "Textiles": [
        "clothing",
        "shoes",
        "towel",
        "bedsheet",
        "curtain",
        "rug",
        "stuffed-animal",
        "backpack",
        "purse",
    ],
    "Hazardous Waste": [
        "motor-oil",
        "paint",
        "pesticide",
        "cleaning-chemical",
        "prescription-medication",
        "thermometer",
        "smoke-detector",
        "propane-tank",
        "fire-extinguisher",
    ],
    "Non-Recyclable Household": [
        "styrofoam-container",
        "styrofoam-packing",
        "disposable-diaper",
        "sanitary-product",
        "cotton-swab",
        "dental-floss",
        "rubber-band",
        "pen",
        "marker",
        "crayon",
        "ceramic-mug",
        "ceramic-plate",
        "mirror",
        "window-glass",
        "tissue",
        "paper-napkin",
        "wax-paper",
        "parchment-paper",
        "chip-bag",
        "candy-wrapper",
        "straw",
    ],
}

ALL_LABELS: frozenset[str] = frozenset(
    label for items in LABELS_BY_CATEGORY.values() for label in items
)

_S3_SAFE_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def is_valid_label(value: str) -> bool:
    """Check whether *value* is a recognized item label."""
    return value in ALL_LABELS


def is_s3_safe(value: str) -> bool:
    """Check whether *value* is safe for use as an S3 key prefix."""
    return bool(_S3_SAFE_RE.match(value))
