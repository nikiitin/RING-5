# CI/CD Pipeline

## 1. Overview

RING-5 enforces code quality at two stages: **locally** through pre-commit
hooks that run on every `git commit`, and **remotely** through five GitHub
Actions workflows that gate every push and pull request. Together these form
a layered defense ensuring that formatting, linting, type safety, security,
architecture boundaries, and test coverage are validated before code reaches
the `main` branch.

| Layer            | Mechanism                  | When It Runs                       |
|------------------|----------------------------|------------------------------------|
| Local            | pre-commit hooks (12 + 5)  | Every `git commit`                 |
| CI -- on push/PR | `ci.yml`, `architecture-check.yml` | Push or PR to `main`/`develop` |
| CI -- scheduled  | `dependency-check.yml`, `codeql.yml` | Weekly (Monday)              |
| CD -- docs       | `pages.yml`                | Push to `main` when `docs/` changes |

---

## 2. Pre-commit Hooks

Install hooks once after cloning the repository:

```bash
make dev               # installs dev dependencies (includes pre-commit)
make pre-commit-install  # registers hooks in .git/hooks/
```

Run all hooks manually against the full codebase:

```bash
make pre-commit        # equivalent to: pre-commit run --all-files
```

### 2.1 Third-Party Hooks

Hooks execute in the order they appear in `.pre-commit-config.yaml`:

| Order | Hook             | Version  | Purpose                                |
|-------|------------------|----------|----------------------------------------|
| 1     | black            | 26.1.0   | Code formatting (line-length 100)      |
| 2     | flake8           | 7.3.0    | Linting (PEP 8 compliance)            |
| 3     | mypy             | v1.19.1  | Static type checking (`src/` only)     |
| 4     | isort            | 7.0.0    | Import sorting (Black-compatible)      |
| 5     | trailing-whitespace |        | Remove trailing whitespace             |
| 6     | end-of-file-fixer  |         | Ensure files end with newline          |
| 7     | check-yaml       |          | Validate YAML syntax                   |
| 8     | check-json       |          | Validate JSON syntax (excludes `.vscode/`) |
| 9     | check-toml       |          | Validate TOML syntax                   |
| 10    | check-merge-conflict |       | Detect unresolved merge markers        |
| 11    | check-added-large-files |    | Block files larger than 1000 KB        |
| 12    | debug-statements |          | Flag leftover `pdb`/`breakpoint()` calls |
| 13    | mixed-line-ending |         | Enforce consistent line endings        |
| 14    | check-ast        |          | Verify Python files parse correctly    |
| 15    | check-case-conflict |        | Detect filenames differing only in case |
| 16    | check-docstring-first |      | Ensure docstrings are the first statement |
| 17    | detect-private-key |         | Flag accidentally committed private keys |
| 18    | no-commit-to-branch |        | **Block direct commits to `main`**     |
| 19    | bandit           | 1.9.3    | Security scanning (excludes `tests/`)  |
| 20    | pyupgrade        | v3.19.1  | Modernize syntax to Python 3.12+      |

The `no-commit-to-branch` hook prevents accidental commits directly to the
`main` branch, enforcing the pull-request workflow.

### 2.2 Custom Architecture Hooks

Five local hooks enforce project-specific rules. All operate on `src/` and
fail the commit if a violation is found.

| Hook                      | Rule                                           |
|---------------------------|------------------------------------------------|
| `no-streamlit-in-core`    | No `import streamlit` or `from streamlit` in `src/core/` |
| `no-session-state-in-core`| No `session_state` references in `src/core/`   |
| `no-inplace-true`         | No `inplace=True` anywhere in `src/`           |
| `no-bare-except`          | No bare `except:` clauses (must name exception type) |
| `no-eval-exec`            | No `eval()` or `exec()` in production code     |

These hooks mirror the checks in the `architecture-check.yml` workflow,
providing identical enforcement both locally and in CI.

---

## 3. GitHub Actions Workflows

All workflow files live in `.github/workflows/`. The project defines five
workflows.

### 3.1 Main CI Pipeline (`ci.yml`)

**Triggers:** push or PR to `main`/`develop`; manual dispatch.

The pipeline runs three sequential jobs:

```
quality-checks  --->  tests  --->  e2e-tests (main only)
```

**Job 1 -- quality-checks** (runs on every push and PR):

1. `black --check --diff src/ tests/` -- formatting check
2. `flake8 src/ tests/ --count --statistics` -- linting
3. `mypy src/ --show-error-codes --pretty` -- type checking
4. `bandit -r src/ -c pyproject.toml -ll` -- security scan

**Job 2 -- tests** (depends on quality-checks passing):

1. Installs system dependency: `perl` (for gem5 Perl parser)
2. Checks out with Git LFS support (test data)
3. `pytest -v --cov=src --cov-report=xml --timeout=60`
4. Uploads coverage report to Codecov

**Job 3 -- e2e-tests** (depends on tests; runs only on push to `main`):

1. Installs Playwright with Chromium
2. `pytest tests/ui/ -v --timeout=120 -m "requires_browser"`

### 3.2 Architecture and Security Enforcement (`architecture-check.yml`)

**Triggers:** push or PR to `main`/`develop` when `src/**/*.py` or
`tests/**/*.py` files change.

Runs two parallel jobs:

**Job 1 -- Architecture Boundaries:** validates five rules via pattern
matching -- no Streamlit in core, no `session_state` in core, no
`inplace=True`, no bare `except:`, and no UI library imports in
`src/core/parsing/` or `src/core/models/`.

**Job 2 -- Security Analysis:** scans for dangerous patterns (`eval()`,
`exec()`, `pickle.load`, hardcoded secrets), runs Bandit with JSON report
output (uploaded as an artifact), and runs `pip-audit` for known
vulnerabilities.

### 3.3 Dependency Update Check (`dependency-check.yml`)

**Triggers:** weekly schedule (Monday 9:00 AM UTC); manual dispatch.

Steps:

1. Runs `pip list --outdated --format=json` and generates a markdown table
   in the GitHub step summary.
2. Runs `pip-audit` for security vulnerabilities.
3. If outdated packages are found and no open issue with labels
   `dependencies`, `automated`, `maintenance` already exists, creates a
   GitHub issue automatically.

### 3.4 CodeQL Advanced Security (`codeql.yml`)

**Triggers:** push or PR to `main`/`develop`; weekly schedule (Monday
midnight UTC); manual dispatch.

Runs GitHub CodeQL semantic analysis with the `security-and-quality` query
suite. Uses a custom configuration at `.github/codeql/codeql-config.yml`
that excludes test data, virtual environments, and build artifacts from
analysis. Results appear in the repository Security tab.

### 3.5 Documentation Deployment (`pages.yml`)

**Triggers:** push to `main` when files under `docs/` change.

A two-job workflow: builds the `docs/` directory with Jekyll, then deploys
to GitHub Pages. Concurrency control prevents partial deployments.

---

## 4. Quality Gate

The local quality gate replicates the CI checks in a single command:

```bash
make quality-gate
```

It runs five sequential gates and reports a pass/fail summary:

| Gate | Check             | Tool                     | What It Validates              |
|------|-------------------|--------------------------|--------------------------------|
| 1    | Architecture      | grep pattern matching    | Layer boundaries, immutability |
| 2    | Type Safety       | mypy                     | Static type errors in `src/`   |
| 3    | Formatting        | black `--check`          | Code style compliance          |
| 4    | Linting           | flake8                   | PEP 8 and error detection      |
| 5    | Security          | grep for `eval`/`exec`   | Dangerous function usage       |

Run the architecture check in isolation:

```bash
make arch-check
```

Run the full test suite with the 90% coverage gate used in CI:

```bash
make test-ci      # pytest --cov=src --cov-fail-under=90
```

---

## 5. Branch Protection Rules

The repository enforces a pull-request workflow through two mechanisms:

- **Pre-commit hook `no-commit-to-branch`:** prevents direct local commits
  to the `main` branch. Any `git commit` on `main` is rejected before it
  reaches the remote.

- **CI gating:** the `ci.yml` pipeline runs quality-checks and tests on
  every pull request targeting `main` or `develop`. E2E tests are gated to
  run only on pushes that reach `main`.

Configure GitHub branch protection rules (repository Settings > Branches)
to require the `quality-checks` and `tests` jobs to pass before merging.

---

## 6. Release Process

The project uses a tag-based release model:

1. **Feature work** happens on feature branches (e.g., `005/my-feature`).
2. **Pull requests** target `main` or `develop` and must pass all CI
   checks.
3. **Test data** is distributed via GitHub Releases (see the `test-data`
   Makefile target, which downloads from
   `github.com/nikiitin/RING-5/releases`).
4. **Documentation** is deployed to GitHub Pages automatically when changes
   to `docs/` are merged into `main`.

Dependency freshness is monitored weekly by the `dependency-check.yml`
workflow, which opens issues for outdated packages. CodeQL runs weekly to
detect newly disclosed vulnerabilities.

---

## 7. See Also

- [Architecture Overview](../architecture/overview.md) -- layer structure
  that the architecture hooks enforce
- [Layer Boundaries](../architecture/layer-boundaries.md) -- detailed rules
  for cross-layer imports
