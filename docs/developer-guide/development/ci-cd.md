---
title: "CI/CD Pipeline"
parent: Development
grand_parent: Developer Guide
nav_order: 4
---

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
`src/parsing/` or `src/core/models/`.

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

It also uploads the outdated package list as a downloadable artifact. You
can trigger it manually from the GitHub UI: **Actions > "Dependency Update
Check" > Run workflow**, or with the CLI:

```bash
gh workflow run dependency-check.yml
```

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

## 6. Dependency Updates

RING-5 keeps its dependencies current through a mix of automation
(Dependabot plus the scheduled `dependency-check.yml` workflow described in
section 3.3) and a small set of manual Makefile commands for ad-hoc audits.

### 6.1 Dependabot

**Location:** `.github/dependabot.yml`

Dependabot is the recommended automation. It:

- Checks for updates on a weekly schedule (Monday).
- Opens individual PRs for security updates.
- Groups minor/patch updates together to reduce PR noise.
- Separates dev dependencies from production dependencies.
- Keeps GitHub Actions versions up to date.
- Triggers the CI pipeline on every PR, so each update is auto-validated.

**Grouping configuration:**

| Dependency class | Examples                         | PR strategy             |
|------------------|----------------------------------|-------------------------|
| Production       | pandas, numpy, streamlit, plotly | Grouped into one PR     |
| Dev tools        | black, mypy, pytest              | Grouped separately      |
| Major updates    | any                              | Individual PR (manual review) |

A cap on the number of simultaneously open PRs keeps the queue manageable.
Dependabot is free for public repos, fully automated, security-focused, and
emits email notifications. Its main trade-off is PR volume (mitigated by
grouping) and the fact that major version bumps still require manual review.

**Typical PR flow:**

1. Dependabot opens a PR, e.g. *"deps: Update pandas from 2.3.3 to 2.4.0"*.
2. GitHub Actions runs automatically (tests, type checking, linting).
3. Green CI -> review and merge.
4. Red CI -> review the breaking changes, fix the code, then merge.

To enable it, ensure Dependabot is turned on under **Settings > Code
security**, or simply push the `.github/dependabot.yml` file.

### 6.2 Manual Makefile Commands

For ad-hoc checks outside the automated cadence:

```bash
make check-outdated    # list packages with newer versions available
make update-deps       # update all dependencies (use with care)
make security-audit    # run pip-audit for known vulnerabilities
make show-deps         # print the dependency tree
```

### 6.3 Per-Dependency-Class Strategy

The version constraints in `pyproject.toml` reflect two different
risk tolerances.

**Production dependencies (pandas, numpy, streamlit, plotly) -- conservative.**
Pin to allow minor/patch updates but block major bumps:

```toml
# pyproject.toml
dependencies = [
  "pandas>=2.3.3,<3.0",      # allow minor updates, block major
  "numpy>=2.4.1,<3.0",
  "streamlit>=1.53.1,<2.0",
  "plotly>=6.5.2,<7.0",
]
```

Major versions of scientific-computing tools often introduce breaking
changes, and publication-quality plots must remain reproducible, so these
upgrades are deliberately gated behind manual review.

**Dev tools (black, mypy, flake8, pytest) -- aggressive.**
Track the latest releases, since linters and test runners rarely break
production code and newer versions improve type checking, linting, and
developer experience:

```toml
dev = [
  "pytest>=9.0.2",
  "black>=26.1.0",
  "mypy>=1.13.0",
  "flake8>=7.3.0",
]
```

### 6.4 Update Routines

**Weekly (automated via Dependabot):**

1. Dependabot opens grouped PRs on Monday.
2. CI runs automatically.
3. Triage by outcome:
   - Green CI + patch/minor update -> merge immediately.
   - Green CI + major update -> review the changelog, test locally, merge.
   - Red CI -> investigate breaking changes, fix the code, merge.

**Monthly (manual review):**

```bash
make check-outdated     # see what is behind
make security-audit     # pip-audit pass

# If a critical security issue is reported, update immediately:
./python_venv/bin/pip install --upgrade <package>

# Then re-validate:
make test
mypy src/ --strict
black --check src/ tests/
```

### 6.5 When to Update Immediately

- **Security vulnerabilities:** a CVE reported by `pip-audit` or a
  Dependabot security alert -> update ASAP.
- **Critical bugs:** a blocker bug in a dependency -> move to the patched
  version.
- **New Python version support:** when a new Python release lands, update
  dependencies for compatibility.

### 6.6 Caution: Major Version Updates

Before moving a production dependency across a major boundary (e.g.
pandas 2.x -> 3.x):

1. **Read the changelog** for breaking changes.
2. **Check deprecations** to see which APIs changed.
3. **Test locally:**
   ```bash
   ./python_venv/bin/pip install pandas==3.0.0
   make test
   mypy src/ --strict
   ./launch_webapp.sh   # manual smoke test
   ```
4. **Open a dedicated PR** -- do not mix the upgrade with other changes.
5. **Update documentation** if any APIs changed.

### 6.7 Monitoring

Track dependency health from several surfaces:

- **GitHub Security tab:** vulnerability alerts.
- **Actions tab > Dependency Check:** weekly outdated-package reports.
- **Dependabot PRs:** pending updates awaiting review.
- **Issues labelled `dependencies`:** update tracking opened by the
  scheduled workflow.

If Dependabot produces too many PRs, lower the open-PR limit or relax the
schedule (for example to `monthly`) in `.github/dependabot.yml`. Patch
updates can optionally be auto-merged with a small workflow that calls
`gh pr merge --auto --squash` when the PR is authored by `dependabot[bot]`.

---

## 7. Release Process

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

## 8. See Also

- [Architecture Overview](../architecture/overview.md) -- layer structure
  that the architecture hooks enforce
- [Layer Boundaries](../architecture/layer-boundaries.md) -- detailed rules
  for cross-layer imports
- [Dependabot docs](https://docs.github.com/en/code-security/dependabot)
- [pip-audit](https://github.com/pypa/pip-audit)
- [Semantic Versioning](https://semver.org/)
