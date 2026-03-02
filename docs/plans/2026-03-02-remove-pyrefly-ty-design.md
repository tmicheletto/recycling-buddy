# Design: Replace pyrefly with ty

**Date:** 2026-03-02

## Summary

Swap pyrefly for ty (Astral's type checker) in both `api/` and `model/`. CI type-check step remains commented out — this is a tooling swap only.

## Changes

### `model/pyproject.toml`
- Remove `pyrefly>=0.19.0` from `[dependency-groups] dev`
- Add `ty` to `[dependency-groups] dev`
- Remove `[tool.pyrefly]` section

### `api/pyproject.toml`
- Remove `pyrefly>=0.19.0` from `[dependency-groups] dev`
- Add `ty` to `[dependency-groups] dev`
- Remove `[tool.pyrefly]` section
- Remove `[tool.pyright]` section (ty replaces pyright)

### `api/uv.lock` and `model/uv.lock`
- Regenerate via `uv lock` after dependency changes

### `.github/workflows/api-ci.yml`
- Update the TODO comment on the commented-out type-check step to reference ty instead of pyrefly

## Non-goals

- Enabling type checking in CI
- Fixing src-layout issues
- Adding `[tool.ty]` configuration (not needed unless issues arise)
