# Merge CI/CD Workflows Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix ty type errors, then merge `api-ci.yml` and `api-deploy.yml` into a single `api-build-deploy.yml` with the type check step reinstated.

**Architecture:** Two tasks: fix the two ty diagnostics so `ty check` exits 0, then create the merged workflow file and delete the old ones. No logic changes — purely CI/CD restructuring.

**Tech Stack:** GitHub Actions, ty, ruff

---

### Task 1: Fix ty errors so `ty check` exits 0

**Files:**
- Modify: `api/app/main.py`
- Modify: `api/tests/test_guidelines.py`

**Step 1: Add ty ignore comment to `api/app/main.py`**

Read the file. Find the `app.add_middleware(` block (around line 47). The `CORSMiddleware` argument line needs a `# ty: ignore[invalid-argument-type]` comment — ty flags this as a false positive due to Starlette's stub types.

Change from:
```python
app.add_middleware(
    CORSMiddleware,
```

To:
```python
app.add_middleware(
    CORSMiddleware,  # ty: ignore[invalid-argument-type]
```

**Step 2: Remove stale `type: ignore` from `api/tests/test_guidelines.py`**

Read the file. Find line ~92 with this content:
```python
    def _side_effect(item_category: str, council_slug: str, page_html):  # type: ignore[override]
```

Remove the comment so it becomes:
```python
    def _side_effect(item_category: str, council_slug: str, page_html):
```

**Step 3: Verify `ty check` exits 0**

```bash
cd /Users/tim/code/recycling-buddy/api && uv run ty check
```

Expected: `Found 0 diagnostics` and exit code 0. If any errors remain, fix them before continuing.

**Step 4: Run full test suite to confirm nothing broke**

```bash
cd /Users/tim/code/recycling-buddy/api && uv run pytest
```

Expected: 52 passed.

**Step 5: Commit**

```bash
git -C /Users/tim/code/recycling-buddy add api/app/main.py api/tests/test_guidelines.py
git -C /Users/tim/code/recycling-buddy commit -m "fix(api): suppress ty false positive and remove stale type-ignore comment"
```

---

### Task 2: Create `api-build-deploy.yml` and delete old workflow files

**Files:**
- Create: `.github/workflows/api-build-deploy.yml`
- Delete: `.github/workflows/api-ci.yml`
- Delete: `.github/workflows/api-deploy.yml`

**Step 1: Create `.github/workflows/api-build-deploy.yml`**

Create the file with this exact content:

```yaml
name: API Build & Deploy

on:
  workflow_dispatch:
  push:
    branches:
      - main
    paths:
      - 'api/**'
      - '.github/workflows/api-build-deploy.yml'
  pull_request:
    branches:
      - main
    paths:
      - 'api/**'
      - '.github/workflows/api-build-deploy.yml'

env:
  ECR_REPOSITORY: 646385694251.dkr.ecr.ap-southeast-2.amazonaws.com/recycling-buddy-api
  ECS_CLUSTER: recycling-buddy
  ECS_SERVICE: recycling-buddy-api
  ECS_TASK_DEFINITION: api/task-definition.json
  CONTAINER_NAME: api
  AWS_REGION: ap-southeast-2

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Setup uv
        uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        working-directory: api
        run: uv sync --frozen --all-groups

      - name: Format check
        working-directory: api
        run: uv run ruff format . --check

      - name: Lint check
        working-directory: api
        run: uv run ruff check .

      - name: Type check
        working-directory: api
        run: uv run ty check

      - name: Run tests
        working-directory: api
        run: uv run pytest

  build:
    name: Build and Push to ECR
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'
    permissions:
      id-token: write
      contents: read

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::646385694251:role/recycling-buddy-deployment
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push Docker image
        working-directory: api
        env:
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REPOSITORY:$IMAGE_TAG .
          docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_REPOSITORY:latest
          docker push $ECR_REPOSITORY:$IMAGE_TAG
          docker push $ECR_REPOSITORY:latest
          echo "✅ Image pushed to ECR: $ECR_REPOSITORY:$IMAGE_TAG"

  deploy:
    name: Deploy to ECS
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'
    permissions:
      id-token: write
      contents: read

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::646385694251:role/recycling-buddy-deployment
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Render Amazon ECS task definition
        id: render-task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: ${{ env.ECS_TASK_DEFINITION }}
          container-name: ${{ env.CONTAINER_NAME }}
          image: ${{ env.ECR_REPOSITORY }}:${{ github.sha }}

      - name: Deploy to Amazon ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.render-task-def.outputs.task-definition }}
          service: ${{ env.ECS_SERVICE }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true
```

**Step 2: Delete the old workflow files**

```bash
git -C /Users/tim/code/recycling-buddy rm .github/workflows/api-ci.yml .github/workflows/api-deploy.yml
```

**Step 3: Verify the new file is valid YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('/Users/tim/code/recycling-buddy/.github/workflows/api-build-deploy.yml'))" && echo "YAML valid"
```

Expected: `YAML valid`

**Step 4: Commit**

```bash
git -C /Users/tim/code/recycling-buddy add .github/workflows/api-build-deploy.yml
git -C /Users/tim/code/recycling-buddy commit -m "ci: merge api-ci and api-deploy into api-build-deploy.yml with ty check"
```
