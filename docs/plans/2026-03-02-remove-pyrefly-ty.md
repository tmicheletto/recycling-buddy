# Replace pyrefly with ty Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Swap the pyrefly type checker for ty in both `model/` and `api/` packages.

**Architecture:** Remove pyrefly from dev dependencies and config in each package, add ty, regenerate lockfiles. No CI changes — the type-check step remains commented out.

**Tech Stack:** uv (package manager), ty (Astral type checker)

---

### Task 1: Swap pyrefly → ty in `model/`

**Files:**
- Modify: `model/pyproject.toml`

**Step 1: Edit `model/pyproject.toml`**

Remove `pyrefly>=0.19.0` from `[dependency-groups] dev` and add `ty`. Remove the `[tool.pyrefly]` section entirely.

The dev group should become:
```toml
[dependency-groups]
dev = [
    "pytest>=9.0.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.14.0",
    "ty",
]
```

Remove this section entirely:
```toml
[tool.pyrefly]
search_path = ["."]
```

**Step 2: Regenerate the lockfile**

```bash
cd model && uv lock
```

Expected: lockfile updated, pyrefly removed, ty added.

**Step 3: Verify ty is runnable**

```bash
cd model && uv run ty check
```

Expected: ty runs (errors/warnings are fine — we're not fixing them here, just confirming the tool works).

**Step 4: Commit**

```bash
git add model/pyproject.toml model/uv.lock
git commit -m "chore(model): replace pyrefly with ty"
```

---

### Task 2: Swap pyrefly → ty in `api/`

**Files:**
- Modify: `api/pyproject.toml`

**Step 1: Edit `api/pyproject.toml`**

Remove `pyrefly>=0.19.0` from `[dependency-groups] dev` and add `ty`. Remove the `[tool.pyrefly]` and `[tool.pyright]` sections entirely (ty replaces pyright).

The dev group should become:
```toml
[dependency-groups]
dev = [
    "anyio>=4.12.1",
    "httpx>=0.28.1",
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
    "ruff>=0.14.14",
    "ty",
]
```

Remove these sections entirely:
```toml
[tool.pyrefly]
search_path = ["."]

[tool.pyright]
# Override automatic src-layout detection
# Set import root to api directory (not api/src)
# This allows imports like 'from src.main import app' to work
include = ["src", "tests"]
stubPath = ""
venvPath = "."
venv = ".venv"
```

**Step 2: Regenerate the lockfile**

```bash
cd api && uv lock
```

Expected: lockfile updated, pyrefly removed, ty added.

**Step 3: Verify ty is runnable**

```bash
cd api && uv run ty check
```

Expected: ty runs (errors/warnings are fine — we're not fixing them here, just confirming the tool works).

**Step 4: Commit**

```bash
git add api/pyproject.toml api/uv.lock
git commit -m "chore(api): replace pyrefly with ty"
```

---

### Task 3: Update TODO comment in CI

**Files:**
- Modify: `.github/workflows/api-ci.yml`

**Step 1: Update the comment**

Find the commented-out type-check step (lines 48–51) and update the TODO to reference ty:

```yaml
      # TODO: Fix ty configuration for src-layout
      # - name: Type check
      #   working-directory: api
      #   run: uv run ty check
```

**Step 2: Commit**

```bash
git add .github/workflows/api-ci.yml
git commit -m "chore(ci): update type-check TODO to reference ty"
```
