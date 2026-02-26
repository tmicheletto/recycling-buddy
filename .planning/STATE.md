# Recycling Buddy — State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** A user can photograph any household waste item and immediately know exactly which bin it belongs in, based on their council's actual rules.
**Current milestone:** v1.0 Recycling Advice System

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-02-26 — Milestone v1.0 started

## Key Decisions

(None yet for this milestone)

## Blockers / Concerns

(None)

## Accumulated Context

- Phase 001 (waste item classifier) complete — 63 tests passing
- EfficientNet-B0 model with 67 waste categories, deployed on AWS ECS Fargate (ap-southeast-2)
- Classifier uses recyclingnearyou.com.au category taxonomy
- React frontend exists as training data capture tool — needs conversion to recycling advice UI
- Main unknown: data layer mapping (item_category, council) → (bin, instructions)
