---
title: "Code Quality Tools"
parent: Development
grand_parent: Developer Guide
nav_order: 3
---

# Code Quality Tools

## Overview

RING-5 enforces code quality through six automated tools integrated into both
pre-commit hooks and CI pipelines. Every commit is checked by the full toolchain
before it reaches the repository.

| Tool       | Role                        | Version |
|------------|-----------------------------|---------|
| Black      | Code formatter              | 26.1.0  |
| isort      | Import sorter               | 7.0.0   |
| Flake8     | Linter (PEP 8 + errors)     | 7.3.0   |
| mypy       | Static type checker         | 1.19.1  |
| Bandit     | Security scanner            | 1.9.3   |
| pyupgrade  | Python syntax modernizer    | 3.19.1  |

All tool configurations live in `pyproject.toml` (or `.pre-commit-config.yaml`
for hook-specific arguments), keeping a single source of truth.

---

## Black

Black is the project's opinionated code formatter. It produces deterministic
output, eliminating style debates during code review.

**Configuration** (`pyproject.toml`):

```toml
[tool.black]
line-length = 100
target-version = ['py312']
```

- **Line length 100** -- wider than the default 88 to accommodate the long
  method chains common in pandas data-processing code.
- **Target Python 3.12** -- enables modern formatting choices such as
  parenthesized context managers.

**Usage**:

```bash
black src/ tests/              # Format all source files
black --check --diff src/      # Dry-run: show what would change
```

---

## isort

isort sorts and groups import statements so that every file follows the same
ordering convention.

**Configuration** (via pre-commit hook arguments):

```yaml
args: [--profile=black, --line-length=100]
```

- `--profile=black` ensures import formatting does not conflict with Black.
- `--line-length=100` matches the project-wide line length.

**Usage**:

```bash
isort src/ tests/              # Sort imports in-place
isort --check-only src/        # Dry-run: report unsorted files
```

---

## Flake8

Flake8 is the project's linter, checking for PEP 8 violations and common
programming errors.

**Configuration** (`pyproject.toml`):

```toml
[tool.flake8]
max-line-length = 100
extend-ignore = ["E203", "W503"]
exclude = [".git", "__pycache__", "python_venv", ".pytest_cache", "*.egg-info", "build", "dist"]
```

- **E203 ignored** -- "Whitespace before `:`". Conflicts with how Black formats
  slice expressions (e.g., `x[1 : 2]`).
- **W503 ignored** -- "Line break before binary operator". Black always places
  breaks before operators; ignoring W503 prevents conflicts.
- The `flake8-pyproject` plugin is required so that flake8 reads its settings
  from `pyproject.toml`.

**Usage**:

```bash
flake8 src/ tests/ --count --statistics
```

---

## mypy

mypy performs static type checking. The project runs it in a near-strict mode
that requires type annotations on every function definition.

**Configuration** (`pyproject.toml`):

```toml
[tool.mypy]
python_version = "3.12"
disallow_untyped_defs = true
no_implicit_optional = true
check_untyped_defs = true
strict_equality = true
warn_return_any = true
warn_no_return = true
warn_redundant_casts = true
```

Key rules enforced:

| Setting                  | Effect                                                  |
|--------------------------|---------------------------------------------------------|
| `disallow_untyped_defs`  | All functions must have type annotations.               |
| `no_implicit_optional`   | `x: str = None` is an error; must write `str \| None`.  |
| `strict_equality`        | Prevents comparing incompatible types.                  |
| `check_untyped_defs`     | Bodies of untyped functions are still type-checked.      |

Type stubs for third-party libraries are provided by `pandas-stubs`,
`plotly-stubs`, `types-jsonschema`, and `scipy-stubs` (all in dev dependencies).

**Usage**:

```bash
mypy src/ --show-error-codes --pretty
```

---

## Bandit

Bandit scans Python code for common security issues such as hardcoded passwords,
use of `exec()`/`eval()`, and insecure module usage.

**Configuration** (`pyproject.toml`):

```toml
[tool.bandit]
skips = ["B603", "B404"]
```

- **B603** (subprocess without shell) -- skipped because the project explicitly
  uses `shell=False` with validated paths for the Perl parser.
- **B404** (import subprocess) -- skipped because subprocess is required for
  invoking the external Perl parser.

**Usage**:

```bash
bandit -r src/ -c pyproject.toml -ll
```

The `-ll` flag limits output to medium- and high-severity findings.

---

## pyupgrade

pyupgrade automatically rewrites source files to use modern Python 3.12+ syntax.

**Configuration** (`.pre-commit-config.yaml`):

```yaml
args: [--py312-plus]
```

Examples of transformations applied:

- `Optional[X]` becomes `X | None`
- `Union[X, Y]` becomes `X | Y`
- `Dict[K, V]` becomes `dict[K, V]` (lowercase built-in generics)

pyupgrade runs as a pre-commit hook only; there is no separate CI step.

---

## Custom Architecture Hooks

Five local pre-commit hooks enforce project-specific rules that go beyond
generic linting. Each hook scans `src/` with `grep` and fails the commit if a
violation is found.

| Hook ID                    | Rule                                                   |
|----------------------------|--------------------------------------------------------|
| `no-streamlit-in-core`     | No `import streamlit` or `from streamlit` in `src/core/`. Keeps the core layer framework-independent. |
| `no-session-state-in-core` | No `session_state` references in `src/core/`. Confines Streamlit state to the web layer. |
| `no-inplace-true`          | No `inplace=True` anywhere in `src/`. Enforces immutable DataFrame operations. |
| `no-bare-except`           | No bare `except:` clauses in `src/`. Requires specifying an exception type. |
| `no-eval-exec`             | No `eval()` or `exec()` in `src/`. Blocks arbitrary code execution as a security measure. |

These hooks only trigger on `.py` files under their respective scopes.

---

## Running Quality Checks

**Run all checks at once** (recommended before pushing):

```bash
make quality-gate          # 5-gate check: architecture, types, formatting, lint, security
```

**Run all pre-commit hooks on the entire codebase**:

```bash
pre-commit run --all-files
```

**Run individual tools**:

```bash
black --check src/ tests/                       # Formatting
isort --check-only src/ tests/                  # Import order
flake8 src/ tests/ --count --statistics         # Linting
mypy src/ --show-error-codes --pretty           # Type checking
bandit -r src/ -c pyproject.toml -ll            # Security
```

**Install pre-commit hooks** (first-time setup):

```bash
pip install -e ".[dev]"
pre-commit install
```

---

## See Also

- [Testing](testing.md) -- pytest configuration and test execution
- [CI/CD Pipelines](ci-cd.md) -- GitHub Actions workflow details
- [Architecture](../architecture/overview.md) -- layer boundaries enforced by custom hooks
