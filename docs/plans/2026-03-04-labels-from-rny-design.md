# Design: Replace labels with recyclingnearyou.com.au Home categories

**Date:** 2026-03-04
**Status:** Approved

## Context

Our classifier labels should align with the material categories used by
recyclingnearyou.com.au so that predictions map directly to the site's
recycling advice pages. The site's Home section has 48 broader material
categories, each with a URL slug (e.g. `/material/home/aluminium-cans`).

## Decision

Replace the current 67 labels in `model/recbuddy/labels.py` with the 48
Home category URL slugs from recyclingnearyou.com.au. Clean swap — no
migration of existing training data or model artifacts.

## New labels (48)

```
aerosols, aluminium-cans, asbestos, batteries-single-use, cars,
cartridges, cartons, cds-dvds, chemical-drums, chemicals, clothing,
coffee-capsules, coffee-cups, computers, cooking-oil, corks, demolition,
electrical, electrical-battery-operated, fluorescent-lights, food,
furniture, garden-organics, gas-bottles, glass-containers, glasses,
incandescent-lights, lead-acid-batteries, led-lights, mattresses,
medicines, mobile-phones, motor-oil, office-paper, paper-cardboard,
plastic-containers, polystyrene, pool-chemicals, power-tools,
scrap-metals, soft-plastics, steel-cans, tapes, televisions, tyres,
vapes, whitegoods, x-rays
```

## What changes

- `model/recbuddy/labels.py` — replace `ALL_LABELS_LIST` contents
- Labels without training data can be pruned later

## What doesn't change

- Module API (`ALL_LABELS_LIST`, `ALL_LABELS`, `is_valid_label`, `is_s3_safe`)
- All consumers of labels work unchanged

## Impact

- Existing model artifact won't match new labels (retrain needed)
- Existing S3 training images under old prefixes become orphaned (acceptable)
- Guidelines search improves since labels map directly to site URL slugs
