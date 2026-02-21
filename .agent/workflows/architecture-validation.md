# Architecture Validation Workflow

> **Invoke with**: `/architecture-validate`
> **Purpose**: Automated verification of layered architecture boundaries, import rules, and design patterns
> **Applies to**: All code changes in `src/`
> **Complexity**: Quick (2-5 minutes)
> **Frequency**: Run after EVERY code change before declaring work done

---

## Overview

This workflow enforces the strict 3-layer architecture of RING-5. It provides executable commands that detect boundary violations, anti-patterns, and architectural drift. **Every command should produce empty output for a healthy codebase.**

---

## Phase 1: Layer Boundary Validation (CRITICAL)

### 1.1 Core Layer Must Not Import UI Frameworks

The `src/core/` directory is the domain + data layer. It MUST NOT depend on any UI framework.

```bash
# Streamlit imports in core (MUST be empty)
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" | grep -v __pycache__

# Plotly imports in core parsing/models (MUST be empty)
grep -rn "import plotly\|from plotly" src/core/parsing/ src/core/models/ --include="*.py" | grep -v __pycache__

# Matplotlib imports in core parsing/models (MUST be empty)
grep -rn "import matplotlib\|from matplotlib" src/core/parsing/ src/core/models/ --include="*.py" | grep -v __pycache__
```

**Verdict**: If any results appear → **BLOCKING VIOLATION**. Refactor imports before proceeding.

### 1.2 Session State Isolation

`st.session_state` access MUST be confined to the web layer only.

```bash
# session_state outside web layer (MUST be empty)
grep -rn "session_state" src/core/ --include="*.py" | grep -v __pycache__

# Direct st.* calls in core (MUST be empty)
grep -rn "\bst\.\(error\|warning\|info\|success\|write\|sidebar\|columns\|expander\)" src/core/ --include="*.py" | grep -v __pycache__
```

### 1.3 Web Layer → Core Dependency Direction

The web layer should access core through defined interfaces (Facade, services), not reach deep into internals.

```bash
# Check for deep reaching into core internals from UI pages
grep -rn "from src\.core\.parsing\.gem5\.impl\." src/web/pages/ --include="*.py" | grep -v __pycache__
```

---

## Phase 2: Design Pattern Compliance

### 2.1 Factory Pattern for Plots

All plot instantiation MUST go through the factory, never direct construction in UI code.

```bash
# Direct plot class instantiation outside factories/tests (should be minimal)
grep -rn "= [A-Z][a-zA-Z]*Plot(" src/web/pages/ --include="*.py" | grep -v "Factory\|test\|__pycache__"
```

### 2.2 Facade Pattern for Backend Access

UI pages should interact with the backend primarily through the Facade or controllers.

```bash
# Count direct service imports in UI pages (prefer going through controllers/presenters)
grep -rn "from src\.core\.services\." src/web/pages/ui/ --include="*.py" | grep -v __pycache__ | wc -l
```

### 2.3 Immutability Enforcement

DataFrames must never be modified in-place.

```bash
# inplace=True usage (MUST be empty in src/)
grep -rn "inplace=True" src/ --include="*.py" | grep -v __pycache__
```

---

## Phase 3: Type Safety Verification

### 3.1 Untyped Functions

```bash
# Functions missing return type annotations
grep -rn "def " src/ --include="*.py" | grep -v " -> " | grep -v __pycache__ | grep -v "def __" | grep -v "# type:" | head -20
```

### 3.2 Dangerous Type Patterns

```bash
# Any usage (should be minimized and documented)
grep -rn ": Any\b\|-> Any\b" src/ --include="*.py" | grep -v __pycache__ | grep -v "typing" | wc -l

# type: ignore without justification
grep -rn "# type: ignore" src/ --include="*.py" | grep -v __pycache__ | head -10
```

### 3.3 Run mypy

```bash
# Type check the full source tree
./python_venv/bin/mypy src/ --show-error-codes --pretty 2>&1 | tail -5
```

---

## Phase 4: Security Patterns

### 4.1 Dangerous Code Patterns

```bash
# eval/exec (FORBIDDEN in production code)
grep -rn "eval(\|exec(" src/ --include="*.py" | grep -v __pycache__ | grep -v test

# Bare except (FORBIDDEN)
grep -rn "^[[:space:]]*except:" src/ --include="*.py" | grep -v __pycache__

# pickle on untrusted data
grep -rn "pickle\.load\|pickle\.loads" src/ --include="*.py" | grep -v __pycache__

# subprocess with shell=True
grep -rn "shell=True" src/ --include="*.py" | grep -v __pycache__

# Hardcoded secrets
grep -rn "password\s*=\s*['\"]" src/ --include="*.py" | grep -v __pycache__ | grep -v test
```

---

## Phase 5: Code Quality Checks

### 5.1 Formatting & Linting

```bash
# Check formatting (should report no changes)
./python_venv/bin/black --check --diff src/ 2>&1 | tail -5

# Lint
./python_venv/bin/flake8 src/ --count --statistics 2>&1 | tail -5
```

### 5.2 Import Organization

```bash
# Check import sorting
./python_venv/bin/isort --check-only --diff src/ 2>&1 | tail -10
```

---

## Quick Validation Script

Run this one-liner to perform a fast boundary check:

```bash
echo "=== Architecture Boundary Check ===" && \
echo "--- Streamlit in core ---" && \
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" 2>/dev/null | grep -v __pycache__ | head -5 && \
echo "--- session_state in core ---" && \
grep -rn "session_state" src/core/ --include="*.py" 2>/dev/null | grep -v __pycache__ | head -5 && \
echo "--- inplace=True ---" && \
grep -rn "inplace=True" src/ --include="*.py" 2>/dev/null | grep -v __pycache__ | head -5 && \
echo "--- bare except ---" && \
grep -rn "^[[:space:]]*except:" src/ --include="*.py" 2>/dev/null | grep -v __pycache__ | head -5 && \
echo "--- eval/exec ---" && \
grep -rn "eval(\|exec(" src/ --include="*.py" 2>/dev/null | grep -v __pycache__ | grep -v test | head -5 && \
echo "=== Check Complete ==="
```

---

## Verdict Criteria

| Check                          | Result     | Action                                 |
| :----------------------------- | :--------- | :------------------------------------- |
| Streamlit in `src/core/`       | Any match  | **BLOCK** — move import to web layer   |
| `session_state` in `src/core/` | Any match  | **BLOCK** — pass as parameter instead  |
| `inplace=True`                 | Any match  | **BLOCK** — return new DataFrame       |
| Bare `except:`                 | Any match  | **BLOCK** — catch specific exceptions  |
| `eval()`/`exec()`              | Any match  | **BLOCK** — find safe alternative      |
| Untyped functions              | >5 new     | **WARN** — add type hints before merge |
| `Any` type usage               | Increasing | **WARN** — use specific types          |
| mypy errors                    | Any new    | **BLOCK** — fix type errors            |

---

## End of Workflow
