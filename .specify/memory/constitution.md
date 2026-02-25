<!--
SYNC IMPACT REPORT — Constitution v(unset/template) → v1.0.0
=============================================================
Version change: (unset — all placeholders) → 1.0.0
Bump rationale: MINOR (initial ratification; all content newly authored)

Modified principles: none (initial authoring)

Added sections:
  - I. Type Safety & Contract Integrity
  - II. Test-Driven Development
  - III. Simplicity & YAGNI
  - IV. Docker-First Reproducibility
  - V. Observability & Security
  - Technology Standards (replaces [SECTION_2_NAME])
  - Development Workflow (replaces [SECTION_3_NAME])
  - Governance

Removed sections: none

Templates reviewed for consistency:
  ✅ .specify/templates/plan-template.md
       Constitution Check section is dynamically filled per feature; no update needed.
  ✅ .specify/templates/spec-template.md
       No direct principle references; compatible with all five principles.
  ✅ .specify/templates/tasks-template.md
       Test discipline, user-story independence, and parallel-task markers align
       with Principles II and III; no update needed.
  ✅ .specify/templates/agent-file-template.md
       Generic runtime guidance template; no constitution references to update.

Deferred TODOs:
  - TODO(ML_FRAMEWORK): ML framework (PyTorch/TensorFlow/scikit-learn) not yet
    selected; accuracy/latency targets are aspirational until framework is chosen.
  - TODO(CLOUD_TARGET): Cloud deployment beyond Docker Compose is TBD; IaC
    section will need expansion once provider is finalised.
-->

# Recycling Buddy Constitution

## Core Principles

### I. Type Safety & Contract Integrity

All data crossing component boundaries MUST be strictly typed. The API MUST
define Pydantic v2 models for every request and response shape. The UI MUST
define equivalent TypeScript interfaces in `ui/src/types/` and keep them in
sync with API changes. Python code throughout the codebase MUST carry type
hints on all functions and public APIs; `any` in TypeScript is forbidden.

**Rationale**: This is a portfolio project with three distinct runtimes (Python
model, Python API, TypeScript UI). Type contracts are the primary safeguard
against integration regressions when working across those boundaries.

### II. Test-Driven Development

New features MUST be accompanied by tests written before or alongside
implementation — never deferred. Bug fixes MUST include a regression test that
fails without the fix. Python tests MUST run via `uv run pytest`; async tests
MUST use `anyio`. UI tests MUST use vitest. Edge cases and error paths MUST be
covered, not just happy paths.

**Rationale**: Test coverage is a direct demonstration of engineering discipline
for portfolio reviewers. Deferring tests produces unmaintainable code and hides
regressions.

### III. Simplicity & YAGNI

Code MUST solve the current, explicitly stated requirement and no more.
Abstractions, helper utilities, and features MUST NOT be introduced for
hypothetical future use. Each component (`model/`, `api/`, `ui/`) MUST remain
independently understandable and runnable. When complexity is unavoidable, it
MUST be documented with a justification in the relevant plan's Complexity
Tracking table.

**Rationale**: A portfolio project is judged on clarity as much as capability.
Over-engineering obscures intent and inflates maintenance cost.

### IV. Docker-First Reproducibility

The full stack MUST start cleanly via `docker-compose up --build` from the
project root without additional manual steps. Component Dockerfiles MUST use
multi-stage builds for production images. Secrets and credentials MUST never
be committed to the repository; `.env` files are used locally and
cloud-native secret managers in CI/CD. All infrastructure MUST be
version-controlled as code (Terraform or equivalent).

**Rationale**: One-command startup is a core onboarding requirement for
portfolio reviewers. Infrastructure drift between environments is eliminated
by treating all config as code.

### V. Observability & Security

Every service MUST emit structured logs (JSON-compatible format) using
consistent log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL. API endpoints
MUST validate all inputs at the boundary (content type, file size, schema).
Secrets MUST use environment variables — hardcoded credentials are forbidden.
HTTPS and restrictive CORS MUST be enforced in any non-local deployment.
Rate limiting MUST be added before any public-facing deployment.

**Rationale**: Observability and secure-by-default practices reflect
production-readiness. These attributes distinguish a strong portfolio project
from a prototype.

## Technology Standards

### Python (model/, api/)

- **Package manager**: `uv` only. Never use `pip` directly.
  - Install: `uv add <package>`
  - Run tools: `uv run <tool>`
  - Forbidden: `uv pip install`, `@latest` syntax
- **Formatter / linter**: `ruff` — `uv run ruff format . && uv run ruff check . --fix`
- **Type checker**: `pyrefly` — run `pyrefly check` after every change and fix all errors
- **Line length**: 88 characters maximum
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes,
  `UPPER_SNAKE_CASE` for constants
- **Testing**: `uv run pytest`; async tests MUST use `anyio`, not `asyncio`

### TypeScript / UI (ui/)

- **Framework**: React 18, Vite, TypeScript strict mode
- **No `any` types** — use proper interfaces and generics
- **Components**: functional components with hooks only; no class components
- **HTTP**: Fetch API or axios; types imported from `ui/src/types/`
- **Build check**: `npm run build` MUST pass before committing

### ML Model (model/)

- Framework: TBD — PyTorch, TensorFlow/Keras, or scikit-learn
  (TODO(ML_FRAMEWORK): update this section once chosen)
- Pin all dependency versions in `requirements.txt`
- Target accuracy: >85% on validation set
- Target inference latency: <500ms per image
- Target model checkpoint size: <100MB
- Track experiments with reproducible random seeds

### Infrastructure (infra/)

- AWS region: `ap-southeast-2`
- Local orchestration: Docker Compose
- CI/CD: GitHub Actions
- IaC: Terraform (TODO(CLOUD_TARGET): expand once cloud target finalised)
- Before every infrastructure commit: `make fmt && make validate && make plan`

## Development Workflow

1. Write or update tests **before or alongside** implementation (Principle II).
2. Run `uv run ruff format . && uv run ruff check . --fix` then `pyrefly check`
   before committing any Python changes.
3. Run `npm run build` (TypeScript type-check) before committing UI changes.
4. Verify the Docker stack starts cleanly: `docker-compose up --build`.
5. Commit messages MUST follow Conventional Commits format (e.g. `feat:`,
   `fix:`, `docs:`, `chore:`).
6. The working tree MUST be clean before creating a commit — no uncommitted
   changes left behind.
7. All pull requests MUST pass CI checks (lint, type-check, tests) before merge.
8. Infrastructure changes MUST be validated in staging before production.
9. Complexity violations MUST be documented in the plan's Complexity Tracking
   table (Principle III).

## Governance

This Constitution supersedes all other development guidelines within this
repository. Component `CLAUDE.md` files provide runtime operational detail and
MUST NOT contradict the principles above; they may add component-specific
elaboration.

**Amendment procedure**:
1. Document the rationale for the change.
2. Increment `CONSTITUTION_VERSION` following semantic versioning:
   - **MAJOR**: removal or redefinition of an existing principle (backward incompatible).
   - **MINOR**: new principle or new section added.
   - **PATCH**: clarification, wording improvement, or typo fix.
3. Update `LAST_AMENDED_DATE` to the ISO date of the amendment.
4. Propagate any impacted changes to templates in `.specify/templates/`.
5. Add a Sync Impact Report comment at the top of this file.

All pull requests MUST verify compliance with these principles. Refer to
component `CLAUDE.md` files for runtime development guidance specific to each
component.

**Version**: 1.0.0 | **Ratified**: 2026-02-25 | **Last Amended**: 2026-02-25
