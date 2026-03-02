# Design: Merge CI/CD Workflows into api-build-deploy.yml

**Date:** 2026-03-02

## Problem

The API has two separate workflow files:
- `api-ci.yml` — test + build (ECR push)
- `api-deploy.yml` — deploy to ECS, triggered via `workflow_run` on CI success

This split requires `workflow_run` cross-workflow triggering and a SHA-resolution step to determine which image to deploy. The type check step is also disabled.

## Solution

Merge into a single `api-build-deploy.yml` with three dependent jobs. Fix the two ty errors so type checking can be reinstated as a hard gate.

## Ty fixes

Before touching CI:

1. **`api/app/main.py:48`** — add `# ty: ignore[invalid-argument-type]` to the `CORSMiddleware` line (ty false positive — Starlette stubs don't match actual usage pattern)
2. **`api/tests/test_guidelines.py:92`** — remove stale `# type: ignore[override]` comment (was needed for pyrefly, not ty)

## New workflow: `.github/workflows/api-build-deploy.yml`

### Triggers

```yaml
on:
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - 'api/**'
      - '.github/workflows/api-build-deploy.yml'
  pull_request:
    branches: [main]
    paths:
      - 'api/**'
      - '.github/workflows/api-build-deploy.yml'
```

### Jobs

**`test`** — runs on all triggers:
- Checkout, Python 3.11, uv
- `uv sync --frozen --all-groups`
- `ruff format . --check`
- `ruff check .`
- `uv run ty check` ← reinstated
- `uv run pytest`

**`build`** — `needs: test`, only on main (not PRs):
```yaml
if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'
```
- AWS OIDC, ECR login
- `docker build`, tag `${{ github.sha }}` + `latest`, push both

**`deploy`** — `needs: build`, same condition:
- AWS OIDC, ECR login
- Render ECS task definition with image `ECR_REPOSITORY:${{ github.sha }}`
- Deploy to ECS with `wait-for-service-stability: true`

### Simplifications vs. current

- No `workflow_run` cross-workflow trigger
- No "Determine image tag" step — both build and deploy use `github.sha` directly
- Single `workflow_dispatch` covers the full pipeline

## Files changed

| Action | File |
|--------|------|
| Create | `.github/workflows/api-build-deploy.yml` |
| Delete | `.github/workflows/api-ci.yml` |
| Delete | `.github/workflows/api-deploy.yml` |
| Fix | `api/app/main.py` (ty ignore comment) |
| Fix | `api/tests/test_guidelines.py` (remove stale type: ignore) |
