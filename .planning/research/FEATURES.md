# Feature Research

**Domain:** Mobile recycling advice app (Australian councils, waste sorting)
**Researched:** 2026-02-26
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Bin result with colour | Every Australian recycling tool shows red/yellow/green lid. Users read bin colour not bin name. | LOW | Red = general waste, Yellow = recycling, Green = FOGO. Some councils use purple or lime for glass. Must be council-specific — bin colours are not fully standardised nationally. |
| Item lookup by photo | Recycle Mate and RecycleSmart both do this. Users arriving at a recycling-first app expect the camera to be the primary interaction. | MEDIUM | Already implemented (EfficientNet-B0 classifier). The gap is connecting classification output to bin advice. |
| Council-local advice | Rules vary significantly between council areas — what is recyclable in one LGA contaminates the stream in another. Users expect advice that reflects their situation, not a generic national rule. | MEDIUM | Core value proposition. Without council resolution, advice is unreliable and potentially harmful (causing contamination). |
| Text search / item name fallback | Camera fails on dark, small, or unusual items. All major Australian apps (RecycleRight, RecycleSmart, Recycle Mate) provide a text search fallback. Users who have poor camera lighting or low confidence in the scan result will type instead. | LOW | Fallback path for photo classification failures or low-confidence results. Searches the known item catalogue. |
| Prep instructions | "Rinse the container", "flatten the cardboard", "remove the lid" — councils include this in their A-Z lists. Users who get this right reduce contamination. Apps that omit it feel incomplete to engaged recyclers. | LOW | Data comes from the guidelines layer (recyclingnearyou.com.au). Needs to be surfaced in the result card alongside bin colour. |
| Special disposal / drop-off notice | Some items (batteries, e-waste, soft plastics, chemicals) cannot go in any kerbside bin. Apps that silently assign these to a bin cause real harm. Users expect to be told "take this to a drop-off". | LOW | Must be a distinct result state, not just a bin colour. The item may need a depot, a REDcycle point, or a council collection event. |
| Manual council selection / postcode entry | Geolocation fails or is denied by ~20% of mobile users. RecycleSmart uses a full council list (500+). Recycle Mate uses address entry. Without a fallback, the app is unusable for that cohort. | LOW | Postcode → council mapping is simpler to implement than full address lookup. Covers the denial and failure cases. |
| Low-confidence / uncertain result handling | AI classifiers produce wrong answers. Users lose trust quickly if the app confidently puts things in the wrong bin. Recycle Mate shows search alternatives when recognition is uncertain. | LOW | Show top alternatives from the classifier (already returned by `/predict` as `alternatives`). Let users confirm or correct the classification before showing advice. |
| Mobile-optimised camera UX | The primary entry point is a photo. On mobile, camera capture must be one tap, full-screen, and not require navigating a file picker. | LOW | Browser `<input type="file" capture="environment">` covers this. The existing `PhotoCapture.tsx` scaffold needs adapting for advice-first flow rather than training-data flow. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Photo-first with instant council advice in one flow | Recycle Mate requires selecting your council/bins as a separate onboarding step before scanning. RecycleSmart does not do camera-based classification. Combining photo → classify → council resolve → advice in a single uninterrupted flow is not currently done well by any Australian app. | MEDIUM | The EfficientNet-B0 classifier already exists. The differentiator is the seamless integration with council lookup in one UX flow, not a separate settings screen. |
| Automatic council resolution via geolocation | RecycleSmart asks users to select their council from a 500-item list. Recycle Mate requires address entry. Automatically resolving to a council from device GPS (with manual fallback) reduces onboarding friction significantly. | MEDIUM | Browser Geolocation API + reverse geocoding to LGA boundary. Australian LGA boundary data is available from ABS (ASGS). Council resolution accuracy is bounded by GPS accuracy (~10–50m), which is sufficient for LGA-level matching in most cases. |
| Confidence-aware result display | No Australian app currently shows the model's confidence in the identified item and adjusts the advice display accordingly. Showing "I'm 87% sure this is a glass bottle — here's what to do" versus "I'm not sure — did you mean X, Y, or Z?" is more trustworthy than a bare answer. | LOW | The classifier already returns confidence scores. This is a UI pattern, not a new backend capability. |
| Graceful handling of 67-category taxonomy gaps | The model knows 67 categories. Items outside those categories will get wrong or low-confidence results. Surfacing a clear "I don't recognise this — try searching by name" state, rather than a wrong answer with high confidence, is a meaningful trust differentiator. | LOW | Requires a confidence threshold below which the app switches to the manual search flow rather than showing a bin result. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Gamification (points, badges, leaderboards) | Makes recycling "fun"; seen in RecycleSmart v2 and global apps. | Adds complexity without core value for a prototype. Research shows engagement drops when gamification is the hook rather than utility. Risk of users gaming the system (scanning incorrect items for points). Reward fatigue is documented. One study found removing the rewards system and focusing on ease of use improved outcomes. | Focus on frictionless correct answers. Defer gamification to v2 after validating the core advice loop. |
| User accounts and scan history | Users want to remember what they learned; common feature request. | Requires auth infrastructure (registration, login, session management, password reset) which is out of scope for prototype and adds significant attack surface. | Defer to v2. The advice is stateless — users can re-scan any time. |
| Bin night reminders and collection schedules | RecycleRight and several council apps include this. Users value it. | Requires council-level calendar data (different format per council, not available from recyclingnearyou.com.au) and push notification infrastructure (requires app install or service workers). High maintenance, council data churn. | Explicitly out of scope per PROJECT.md for v1. Address when native app or PWA push is considered. |
| Nearest drop-off location finder with maps | Highly requested for items that can't go in kerbside bins. RecycleRight includes this. | Requires a facility database (separate from council guidelines), integration with a maps API, and ongoing data maintenance as facilities open and close. High cost relative to prototype scope. | Show a "find a drop-off for [item]" link to recyclingnearyou.com.au for the specific item. Defer the embedded map to v2. |
| Barcode scanning | Recycle Mate added this in mid-2024. Users find it intuitive for packaged goods. | Requires a product → packaging material database (separate from the waste classifier). The EfficientNet model classifies waste appearance, not product identity. Building or licensing a barcode-to-material database is a separate project. | Remain image-classification-first for prototype. Barcode scan is a v2 enhancement if item-based advice proves insufficient. |
| Global / non-Australian councils | Seems like natural expansion. | The entire data layer (recyclingnearyou.com.au, council taxonomy) is Australia-specific. International expansion requires rebuilding the guidelines data pipeline for each country, with different regulatory frameworks. | Explicitly Australia-only for v1. |
| Real-time contamination feedback (post-bin) | Some research apps explore using bin sensors or camera to detect contamination after the fact. | Far outside prototype scope; requires hardware or bin-mounted cameras. No existing infrastructure. | Not applicable. Core value is advice before disposal, not detection after. |

## Feature Dependencies

```
[Geolocation / Postcode Entry]
    └──requires──> [Council Resolution Service]
                       └──requires──> [Guidelines Data Layer (recyclingnearyou.com.au)]
                                          └──requires──> [Item Category → Council → Bin mapping]

[Photo Capture]
    └──requires──> [Image Classifier (EfficientNet-B0)] ← ALREADY BUILT
                       └──provides──> [Category + Confidence Score]
                                          └──feeds──> [Council-local Advice Display]
                                                          └──requires──> [Guidelines Data Layer]

[Text Search Fallback]
    └──enhances──> [Photo Capture] (fallback path when confidence low or camera fails)
    └──requires──> [Guidelines Data Layer]

[Confidence-Aware Result Display]
    └──enhances──> [Photo Capture]
    └──requires──> [Image Classifier confidence score] ← ALREADY BUILT (returned by /predict)

[Special Disposal Notice]
    └──requires──> [Guidelines Data Layer]
    └──enhances──> [Council-local Advice Display] (distinct result state)

[Manual Council Selection]
    └──conflicts──> [Geolocation] (must not run both simultaneously; manual overrides auto)
    └──serves as fallback for──> [Geolocation] when denied or failed
```

### Dependency Notes

- **Geolocation requires Council Resolution Service:** GPS coordinates alone are not enough; they must be reverse-geocoded to a council/LGA name to query the guidelines layer. ABS ASGS boundary data or a geocoding API is needed.
- **Council Resolution requires Guidelines Data Layer:** There is no value in knowing which council a user is in if there is no mapping from (council, item_category) → (bin, prep_instructions, disposal_method). This data layer is the primary unknown identified in PROJECT.md.
- **Photo Capture + Classifier already built:** The EfficientNet-B0 model and `/predict` endpoint are complete (phase 001). The missing piece is connecting classifier output to guidelines lookup.
- **Text Search Fallback enhances Photo Capture:** Text search is not a separate product — it is the fallback path for failed or low-confidence classifications. It shares the same guidelines data layer.
- **Manual Council Selection conflicts with Geolocation:** The UI must treat these as mutually exclusive modes with manual overriding automatic. Running both simultaneously creates ambiguous state.
- **Special Disposal requires distinct result state:** It must not be modelled as just another bin colour. It is a separate outcome type ("do not put in any bin") that requires different UI treatment and potentially a link to facility information.

## MVP Definition

### Launch With (v1)

Minimum viable product — what is needed to validate the concept.

- [ ] Photo capture → item classification → council-local bin advice in a single uninterrupted mobile flow — the core value proposition end-to-end
- [ ] Bin colour display (red / yellow / green lid) with bin name — the primary output users need
- [ ] Prep instructions surfaced in the result card — reduces contamination, low complexity, high value
- [ ] Special disposal / drop-off notice as a distinct result state — prevents harm from incorrect bin advice for hazardous or ineligible items
- [ ] Confidence-aware classification display — show top alternatives and let user confirm before showing advice; prevents wrong-bin advice from low-confidence predictions
- [ ] Geolocation-based council resolution with manual postcode/council fallback — both modes required; geolocation alone fails for ~20% of users
- [ ] Guidelines data layer from recyclingnearyou.com.au — the data backbone; without this the classification is unactionable

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Text search / item name lookup — add when user testing shows photo capture has meaningful failure rate for common household items
- [ ] Graceful out-of-taxonomy handling — add when model accuracy data shows frequent misclassifications outside 67 categories
- [ ] Deep-link to recyclingnearyou.com.au for drop-off facility search — add when special disposal rate in analytics is significant

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Bin night reminders — defer; requires push notification infrastructure and council calendar data not available from current data source
- [ ] Nearest drop-off location finder with embedded map — defer; requires separate facility database and maps API integration
- [ ] User accounts and classification history — defer; requires auth infrastructure out of scope for prototype
- [ ] Barcode scanning — defer; requires product → packaging material database separate from current classifier
- [ ] Gamification — defer; prototype must validate utility before layering engagement mechanics
- [ ] Native iOS/Android app — explicitly out of scope per PROJECT.md; web-first for prototype

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Photo capture → bin advice (end-to-end flow) | HIGH | MEDIUM | P1 |
| Bin colour display with council-specific result | HIGH | LOW | P1 |
| Guidelines data layer (recyclingnearyou.com.au) | HIGH | HIGH | P1 |
| Geolocation council resolution | HIGH | MEDIUM | P1 |
| Manual council / postcode fallback | HIGH | LOW | P1 |
| Prep instructions in result card | MEDIUM | LOW | P1 |
| Special disposal / drop-off notice | HIGH | LOW | P1 |
| Confidence-aware classification display | MEDIUM | LOW | P1 |
| Text search / item name lookup | MEDIUM | LOW | P2 |
| Out-of-taxonomy graceful degradation | MEDIUM | LOW | P2 |
| Deep-link to recyclingnearyou.com.au for facilities | LOW | LOW | P2 |
| Bin night reminders | MEDIUM | HIGH | P3 |
| Nearest drop-off map | MEDIUM | HIGH | P3 |
| Barcode scanning | LOW | HIGH | P3 |
| User accounts and history | LOW | HIGH | P3 |
| Gamification | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | RecycleRight (WA) | RecycleSmart / RecyclingNearYou | Recycle Mate | Our Approach |
|---------|-------------------|----------------------------------|--------------|--------------|
| Photo / camera classification | No (text search + A-Z only) | No (text search only) | Yes — AI photo recognition, barcode scan | Yes — EfficientNet-B0 already built |
| Council coverage | WA (Perth + Avon Valley) only | 500+ Australian councils | Nationwide, community-driven | All Australian councils via recyclingnearyou.com.au |
| Council resolution | Manual area selection | Manual council list (500 items) | Address entry + geolocation | Geolocation auto-detect with postcode fallback |
| Bin colour display | Yes | Yes | Yes | Yes — with council-specific accuracy |
| Prep instructions | Yes (A-Z list) | Yes (via database) | Yes | Yes — surfaced in result card |
| Special disposal / drop-off | Yes — "Find My Nearest" with map | Yes | Yes — 4000+ item database | Yes — as distinct result state; link to recyclingnearyou.com.au for facilities |
| Text search fallback | Yes (primary interaction) | Yes (primary interaction) | Yes (secondary to photo) | Yes — secondary to photo, fallback for low confidence |
| Bin night reminders | Yes | Yes (via council integration) | No | No (explicitly out of scope v1) |
| User accounts / history | No | No | No | No (explicitly out of scope v1) |
| Gamification | No | RecycleSmart recently added gamification | No | No (anti-feature for v1) |
| Confidence display | No | No | No | Yes — differentiator |
| End-to-end single flow (photo → council → advice) | No | No | Partial (requires onboarding step) | Yes — core differentiator |

## Sources

- [Recycle Right — WA Government app](https://recycleright.wa.gov.au/download-the-free-app/)
- [RecycleSmart app overview](https://www.recyclesmart.com/our-app)
- [Recycle Mate — AI recycling app case study (Dreamwalk)](https://dreamwalk.com.au/project/recycle-mate)
- [Recycle Mate — Australian Council of Recycling overview](https://acor.org.au/recycle-mate/)
- [RecyclingNearYou — Planet Ark](https://recyclingnearyou.com.au/)
- [The Pick of Australian Recycling Apps — Ecobin](https://www.ecobin.com.au/blogs/blog/pick-australian-recycling-apps)
- [Recycling Bin Colours in Australia — Sustainably Sorted](https://sustainablysorted.com/a-guide-to-bin-colours-recycling-and-more/)
- [Cleanaway Aussie Recycling Behaviours 2023 report](https://www.cleanaway.com.au/sustainable-future/aussie-recycling-behaviours-2023/)
- [Gamification of recycling — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0921344924006980)
- [Recycling app UX case studies — Medium/Bootcamp](https://medium.com/design-bootcamp/ux-case-study-biome-a-mobile-app-for-smarter-recycling-1ebdcb28a3b6)
- [Investigating residents' acceptance of mobile recycling apps — MDPI Sustainability](https://www.mdpi.com/2071-1050/14/17/10874)

---
*Feature research for: Australian mobile recycling advice app (council-local waste sorting)*
*Researched: 2026-02-26*
