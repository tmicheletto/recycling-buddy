# Recycling Buddy

## What This Is

Recycling Buddy is a mobile-friendly web app that helps Australian households correctly sort their waste. Users snap a photo, the app classifies the item and resolves their local council, then tells them which bin it goes in — turning council recycling rules into instant, personalised guidance.

## Core Value

A user can photograph any household waste item and immediately know exactly which bin it belongs in, based on their council's actual rules.

## Current Milestone: v1.0 Recycling Advice System

**Goal:** Deliver a working end-to-end recycling advisor — classify a photographed item, resolve the user's council, and tell them which bin it goes in.

**Target features:**
- Photo capture → item classification (using existing classifier)
- Browser geolocation → Australian council resolution
- Council rules data layer (recyclingnearyou.com.au)
- Bin advice UI: which bin + prep instructions
- Mobile-optimised camera-first interface

## Requirements

### Validated

<!-- Capabilities already implemented in the codebase -->

- ✓ Image-based waste item classification using EfficientNet-B0 model (67 categories) — phase 001
- ✓ FastAPI inference endpoint (`/predict`) returning top prediction + alternatives with confidence scores — phase 001
- ✓ FastAPI labels endpoint (`/labels`) returning all 67 recyclable waste categories — phase 001
- ✓ S3-backed training image upload for model improvement — phase 001
- ✓ Transfer learning training pipeline (two-phase EfficientNet-B0 fine-tuning) — phase 001
- ✓ React UI scaffold with photo capture and item picker components — phase 001

### Active

<!-- What we're building now -->

- [ ] User can photograph a waste item and receive a classification (item category)
- [ ] System determines user's local council from device geolocation
- [ ] System looks up recycling rules for classified item + resolved council
- [ ] User sees which bin the item belongs in (recycling / general waste / compost / special disposal) with any prep instructions
- [ ] UI is mobile-optimised with camera capture as the primary interaction
- [ ] Australian council coverage via recyclingnearyou.com.au data

### Out of Scope

- Native iOS/Android app — web-first for prototype; app store adds friction
- Pickup schedules and bin night reminders — v2 feature
- Nearest drop-off location finder — v2 feature
- User accounts and classification history — v2 feature
- Global coverage beyond Australia — v2+

## Context

The classifier (phase 001) is complete and passing 63 tests. Item categories are sourced from recyclingnearyou.com.au's taxonomy. The FastAPI service runs on AWS ECS Fargate (ap-southeast-2). The React frontend exists but is currently a training data capture tool, not a recycling advice UI.

The main unknowns are the guidelines data layer: how to map (item_category, council) → recycling_decision + bin + instructions. RecyclingNearYou.com.au is the target data source for Australian council rules.

## Constraints

- **Geography**: Australia only for v1 — council data from recyclingnearyou.com.au
- **Platform**: Mobile web (PWA patterns, camera + geolocation via browser APIs)
- **Stack**: Python 3.11 + FastAPI backend; React + TypeScript frontend — extend existing stack, don't introduce new languages
- **Deployment**: AWS ECS Fargate (ap-southeast-2) — infrastructure already configured
- **Prototype scope**: Working end-to-end demo, not production-hardened

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LLM-backed advice lookup (not static scraper) | Fetch RNY page at request time, pass as context to OpenAI — avoids build-time scraper, always uses current council data, in-memory cache for cost/latency | — Pending |
| recyclingnearyou.com.au as grounding source | Fetch council item page as LLM context — same data quality as scraper approach without ETL pipeline | — Pending |
| Browser geolocation for council resolution | No app install required; sufficient for prototype | — Pending |
| Extend existing React UI | Already has photo capture scaffold; avoid rewrite | — Pending |
| General waste (red bin) as uncertain-result default | Safe fallback to prevent recycling contamination when LLM confidence is low | — Pending |

---
*Last updated: 2026-02-26 after milestone v1.0 start*
