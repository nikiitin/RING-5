# Test-Driven Development Workflow

> **Invoke with**: `/test-driven-development`
> **Purpose**: Guide all code changes through the TDD process
> **Applies to**: All new features, bug fixes, and refactoring

## Overview

RING-5 follows strict TDD principles: **NO code is committed until it passes unit AND integration tests.**

## The Golden Rule

```
Write Test → See it Fail → Write Code → See it Pass → Refactor → Repeat
```

## Step-by-Step Process

### 1. Architectural Alignment (Rule 001)

Before writing tests, identify the **Layer**:
*   **Layer A (Data)**: Repository/Parser. Test with `fake_filesystem`.
*   **Layer B (Domain)**: Pure Logic (Entities/Shapers). Test with **Property-Based Testing** (Hypothesis).
*   **Layer C (Presentation)**: UI. Test with `BackendFacade` mocks.

### 2. Strategy: Fixtures as Architecture (Rule 004)

**DO NOT** create ad-hoc setup in your test file.
1.  Check `tests/conftest.py` (Root) for shared fixtures (`session`).
2.  Check `tests/<component>/conftest.py` for component specifics.
3.  **Mandatory:** Use `conftest` fixtures for Dependency Injection.

### 3. Write the Test First (Public API Only)

**Constraint:** Do **NOT** test private methods (`_internal`). Test the public interface.

```python
# tests/unit/domain/test_shaper.py
def test_transform_maintains_invariants(sample_dataframe):  # Use shared fixture
    shaper = ValidationShaper()
    result = shaper.transform(sample_dataframe)
    assert result.shape == sample_dataframe.shape
```

### 4. Property-Based Testing (Hypothesis)

For Domain Logic (Math, Transformations), generate edge cases.

```python
from hypothesis import given, strategies as st

@given(st.lists(st.floats(allow_nan=True)))
def test_normalization_never_crashes(values):
    result = normalize(values)
    assert len(result) == len(values)
```

### 5. Verified Implementation

Write code that satisfies the test AND Rule 003 (Strong Typing).
*   **Vectorization (Rule 002):** No loops over DataFrames.
*   **Typing:** Full `mypy` compliance.

### 6. Refactor

*   **Rule of Three:** Extract duplicates.
*   **Naming:** Ensure "Ubiquitous Language".

## Checklist before Commit

- [ ] **Tests:** Unit (Red/Green) passed.
- [ ] **Properties:** Hypothesis tests passed (for Domain).
- [ ] **Typing:** `mypy src/` passed (Strict).
- [ ] **Architecture:** No "London School" mocking of private methods.
