---
title: "Development Setup"
parent: Development
grand_parent: Developer Guide
nav_order: 1
---

# Development Setup

> How to clone, install, configure, and run RING-5 Unified Engine v2 for local
> development.

---

## 1. Prerequisites

RING-5 requires **Python 3.12 or later**. The project uses modern syntax (union
types `X | Y`, `match` statements, lowercase generics) unavailable in earlier
versions.

```bash
python3 --version   # must report 3.12+
```

| Dependency | Required | Purpose |
|------------|----------|---------|
| Python 3.12+ | Yes | Runtime and development |
| Perl | Yes | Legacy gem5 statistics parser |
| Git | Yes | Version control, pre-commit hooks |
| curl or wget | Recommended | Downloading test data from GitHub Releases |

On Debian/Ubuntu, install Perl with `sudo apt-get install -y perl`.

**Optional -- LaTeX** is needed only for PDF/PGF publication exports. Run
`make install-latex` to install the required TeX Live packages and
`make check-latex` to verify.

---

## 2. Installation

```bash
git clone <repo-url>
cd RING-5-unified-engine-v2

python3 -m venv python_venv        # project convention: python_venv
source python_venv/bin/activate
pip install -e ".[dev]"            # editable install with dev tools
make pre-commit-install            # register git hooks
```

The virtual environment name `python_venv` is referenced by the Makefile,
`.gitignore`, and flake8 exclude rules. Editable mode (`-e`) means source
changes take effect without reinstalling.

The Makefile provides equivalent targets:

```bash
make venv       # Create python_venv and upgrade pip
make dev        # pip install -e ".[dev]" inside the venv
```

---

## 3. Project Configuration (pyproject.toml)

All metadata, dependencies, and tool settings live in a single `pyproject.toml`.
There are no `setup.py`, `setup.cfg`, or `requirements.txt` files.

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*", "components_library*"]

[tool.setuptools]
py-modules = ["argumentParser", "ring5"]
```

The flat `src/` layout relies on `pythonpath = ["."]` in both pytest and mypy so
that imports like `from src.core.services.foo import Bar` resolve at development
time and when installed as a package.

---

## 4. Dependencies

### Runtime

| Package | Min version | Role |
|---------|------------|------|
| pandas | 2.3.3 | Core DataFrame throughout the pipeline |
| numpy | 2.4.1 | Numerical operations |
| scipy | 1.17.0 | Geometric mean, outlier detection |
| matplotlib | 3.10.8 | Static rendering, LaTeX/PDF/PGF export |
| plotly | 6.5.2 | Interactive web UI plots |
| streamlit | 1.53.1 | Web application framework |
| jsonschema | 4.26.0 | Draft-07 validation for pipeline configs |
| openpyxl | 3.1.5 | Excel I/O via pandas |
| kaleido | 1.0.0 | Static image export for Plotly |

All use `>=` without upper bounds to allow future-compatible installs.

### Development (`.[dev]`)

| Package | Purpose |
|---------|---------|
| pytest, pytest-cov, pytest-xdist, pytest-randomly | Testing, coverage, parallel workers, random order |
| black | Formatting (line length 100, py312 target) |
| flake8, flake8-pyproject | Linting with pyproject.toml support |
| mypy | Static type checking (`disallow_untyped_defs`) |
| pre-commit | Git hook framework |
| pandas-stubs, plotly-stubs, types-jsonschema, scipy-stubs | Type stubs |

### CI-only (`.[dev,ci]`)

bandit, pytest-timeout, pip-audit -- security scanning and CI hang prevention.
Not needed for local development.

### E2E (`.[dev,e2e]`)

pytest-playwright and pytest-base-url for browser automation against Streamlit.

---

## 5. Running the Application

```bash
make run
# or directly:
./python_venv/bin/streamlit run app.py
```

The application starts at `http://localhost:8501` by default.

---

## 6. Running Tests

### Fetch test data

Integration tests need gem5 sample data from GitHub Releases. The Makefile
downloads it automatically:

```bash
make test-data
```

### Test commands

| Command | What it runs |
|---------|-------------|
| `make test` | Full suite, no coverage gate, 3 parallel workers |
| `make test-unit` | `tests/unit/` only -- fast feedback |
| `make test-ci` | Non-browser suite with the 84% branch-coverage gate |
| `make test-visual` | Playwright browser tests (starts Streamlit first) |

### Pytest configuration

Key settings from `[tool.pytest.ini_options]` in `pyproject.toml`:

- **`addopts = "-v --tb=short --strict-markers -n 3 --dist loadgroup"`** --
  parallel execution across 3 workers with grouped distribution.
- **`norecursedirs`** -- excludes `tests/tests_principle_compliance`,
  `tests/manual`, `tests/data`, and `tests/visual` from default collection.
- **`xfail_strict = true`** -- unexpectedly passing xfail tests are errors.

Custom markers: `requires_latex`, `requires_browser`, `benchmark`, `smoke`,
`slow` (deselect with `-m "not slow"`).

---

## 7. Development Workflow

A typical edit-test-lint-commit cycle:

**1. Edit** -- Source files live under `src/` and `components_library/`. Imports
use the flat style from the repository root:

```python
from src.core.application_api import ApplicationAPI
```

**2. Test** -- Run unit tests for fast feedback:

```bash
make test-unit
```

**3. Quality gate** -- Run all checks before pushing:

```bash
make quality-gate
```

This runs the architecture, comment, documentation, dependency, formatting,
lint, type, Bandit, and vulnerability checks used by CI.

**4. Commit** -- Pre-commit hooks run automatically on `git commit`, enforcing
formatting, linting, type checking, import sorting, and architecture rules. If
a hook modifies files (e.g., black reformats), stage and commit again. Direct
commits to `main` are blocked by the `no-commit-to-branch` hook.

### Makefile quick reference

| Target | Description |
|--------|-------------|
| `make run` | Start the Streamlit application |
| `make test` | Run tests (no coverage gate) |
| `make test-unit` | Unit tests only (fast) |
| `make test-ci` | Tests with the 84% branch-coverage gate |
| `make quality-gate` | All quality and security checks |
| `make arch-check` | Architecture boundary violations |
| `make comments-check` | Code comment audit |
| `make pre-commit` | Pre-commit hooks on entire codebase |
| `make check-outdated` | List outdated packages |
| `make security-audit` | Known vulnerability check |
| `make clean` | Remove build artifacts and caches |

---

## 8. See Also

- [Testing Guide](testing.md) -- pytest fixtures, mock patterns, test organization
- [CI/CD](ci-cd.md) -- GitHub Actions workflows, pre-commit hook details
- [Code Quality](code-quality.md) -- Black, Flake8, mypy, and repository checks
- [Architecture Overview](../architecture/overview.md) -- 3-layer architecture and import rules
