# Release Branch Review Workflow

> **Invoke with**: `/release-branch-review`
> **Purpose**: Comprehensive, publication-grade review of branches before merging to main/develop
> **Applies to**: All release-candidate branches, feature branches merging to protected branches
> **Complexity**: Advanced
> **Estimated Time**: 30-60 minutes depending on branch scope

---

## Overview

This is the **ultimate pre-merge review workflow** - designed for branches destined for `main` or `develop`. It leaves no stone unturned. A release merge is irreversible in impact: bugs here affect all downstream development and potentially production.

**Philosophy**: "A release is not a commit, it's a contract."

---

## Pre-Review Checklist

Before beginning, ensure:

- [ ] Branch is rebased on target (main/develop)
- [ ] All CI pipelines are green
- [ ] No merge conflicts exist
- [ ] Working tree is clean (`git status`)

---

## Phase 1: Scope Assessment (5 min)

### 1.1 Quantify the Change

```bash
# Get commit count and stats
git log --oneline origin/main..HEAD | wc -l
git diff --stat origin/main..HEAD | tail -1

# List affected areas
git diff --name-only origin/main..HEAD | cut -d'/' -f1-2 | sort | uniq -c | sort -rn
```

**Record:**

- Total commits: \_\_\_
- Files changed: \_\_\_
- Lines added/deleted: \_\_\_
- Primary areas affected: \_\_\_

### 1.2 Classify the Change Type

| Type                | Risk Level | Review Depth |
| :------------------ | :--------- | :----------- |
| Bug fix             | Medium     | Standard     |
| New feature         | High       | Deep         |
| Refactoring         | Very High  | Exhaustive   |
| Dependency update   | Medium     | Security     |
| Configuration only  | Low        | Quick        |
| Architecture change | Critical   | Full Audit   |

**This branch is**: **\_ (Type)
**Risk level**: \_** (Low/Medium/High/Very High/Critical)

---

## Phase 2: Commit History Audit (10 min)

### 2.1 Commit Quality Check

```bash
# Review all commits
git log --oneline origin/main..HEAD

# Check for problematic patterns
git log --oneline origin/main..HEAD | grep -iE "(fix|wip|temp|todo|hack|xxx|oops)"
```

**Commit Hygiene Verification:**

- [ ] Each commit has a clear, descriptive message
- [ ] Commits follow conventional format (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`)
- [ ] No "WIP" or "temp" commits present
- [ ] Logical grouping (one logical change per commit)
- [ ] No "fix typo in previous commit" - should be squashed

### 2.2 Commit Sequence Logic

```bash
# View detailed commit log
git log --stat origin/main..HEAD
```

**Verify:**

- [ ] Commits build on each other logically
- [ ] Tests appear alongside or before implementation
- [ ] No broken intermediate states (each commit should be buildable)

---

## Phase 3: Architectural Integrity (15 min)

### 3.1 Layer Boundary Violations

**Critical Rule**: Dependencies must point inward only.

```bash
# Check for UI imports in domain layer
grep -rn "import streamlit\|from streamlit\|import st" src/core/ src/domain/ 2>/dev/null

# Check for infrastructure imports in models
grep -rn "import sqlalchemy\|import requests" src/core/models/ 2>/dev/null

# Check for direct file operations in models (should use Repository)
grep -rn "open(\|Path(" src/core/models/ 2>/dev/null | grep -v "typing\|pathlib"
```

**Violations Found**: \_\_\_ (List any)

### 3.2 Dependency Direction Audit

For each modified file in `src/core/`:

```bash
# List all imports per file
for f in $(git diff --name-only origin/main..HEAD | grep "^src/core/"); do
    echo "=== $f ==="
    grep -E "^from |^import " "$f" 2>/dev/null | head -20
done
```

**Verify:**

- [ ] Domain layer imports only from: `typing`, `dataclasses`, `abc`, `datetime`, `pathlib`, standard library
- [ ] Domain layer does NOT import from: `streamlit`, `plotly`, `pandas` (controversial - check project policy)
- [ ] Service layer can import from domain, not from UI
- [ ] UI layer can import from anywhere

### 3.3 Pattern Compliance

**Repository Pattern:**

```bash
# Ensure no direct file I/O outside adapters
grep -rn "\.read_csv\|\.to_csv\|json\.load\|yaml\.load" src/core/models/ 2>/dev/null
```

**Factory Pattern:**

```bash
# Check plot/shaper creation goes through factories
grep -rn "= [A-Z][a-z]*Plot(" src/web/ | grep -v "Factory\|test"
```

**Facade Pattern:**

```bash
# UI should primarily interact via Facade, not deep internals
grep -rn "from src\.core\." src/web/pages/ | grep -v facades | head -20
```

---

## Phase 4: Type Safety Audit (10 min)

### 4.1 Type Coverage Check

```bash
# Run mypy on changed files
git diff --name-only origin/main..HEAD | grep "\.py$" | xargs mypy --strict 2>&1 | head -50
```

**Type Issues Found**: \_\_\_ (Count)

### 4.2 Type Annotation Completeness

```bash
# Find functions without return type annotations
for f in $(git diff --name-only origin/main..HEAD | grep "\.py$"); do
    echo "=== $f ==="
    grep -n "def " "$f" | grep -v " -> " | head -10
done
```

**Verify:**

- [ ] All public functions have complete type hints
- [ ] No use of `Any` without documented justification
- [ ] TypedDict used for structured dictionaries
- [ ] Protocol used for structural typing where appropriate

### 4.3 Dangerous Type Patterns

```bash
# Find dangerous patterns
git diff origin/main..HEAD | grep -E "^\\+.*: Any\b|^\\+.*# type: ignore|^\\+.*cast\\("
```

**Each `Any`/`type: ignore`/`cast` must be justified in PR description.**

---

## Phase 5: Test Coverage Analysis (10 min)

### 5.1 Test Existence Verification

For each new/modified source file, verify corresponding test exists:

```bash
# List source files changed
git diff --name-only origin/main..HEAD | grep "^src/" | grep -v "__pycache__"

# Cross-reference with tests
for f in $(git diff --name-only origin/main..HEAD | grep "^src/" | grep "\.py$"); do
    base=$(basename "$f" .py)
    if ! find tests/ -name "*$base*" -o -name "*test_$base*" 2>/dev/null | head -1 | grep -q .; then
        echo "MISSING TEST: $f"
    fi
done
```

### 5.2 Test Quality Check

```bash
# Run all tests with coverage on changed files
pytest tests/ --cov=src --cov-report=term-missing -v 2>&1 | tail -50
```

**Coverage Metrics:**

- Overall coverage: \_\_\_%
- New code coverage: \_\_\_%

**Verify:**

- [ ] All new functions have unit tests
- [ ] Edge cases are tested (empty input, null, boundaries)
- [ ] Error conditions are tested
- [ ] Integration tests exist for new features
- [ ] No tests disabled/skipped without justification

### 5.3 Test Independence

```bash
# Check for test order dependencies
pytest tests/ --randomly-seed=12345 -x 2>&1 | tail -20
pytest tests/ --randomly-seed=67890 -x 2>&1 | tail -20
```

**Verify:**

- [ ] Tests pass regardless of execution order
- [ ] No shared mutable state between tests

---

## Phase 6: Security & Vulnerability Scan (5 min)

### 6.1 Static Security Analysis

```bash
# Run bandit
bandit -r src/ -ll 2>&1 | head -50

# Check for secrets/credentials
grep -rn "password\|secret\|api_key\|token\|credential" src/ --include="*.py" | grep -v "test\|\.pyc"
```

### 6.2 Dependency Vulnerabilities

```bash
# Check for known vulnerabilities
pip-audit 2>&1 | head -30
```

### 6.3 Dangerous Patterns

```bash
# Unsafe operations
git diff origin/main..HEAD | grep -E "^\\+.*(eval\\(|exec\\(|pickle\\.load|subprocess\\.call.*shell=True)"

# SQL injection vectors
git diff origin/main..HEAD | grep -E "^\\+.*execute\\(.*\\%|^\\+.*execute\\(.*format\\("

# Path traversal
git diff origin/main..HEAD | grep -E "^\\+.*\\.\\./"
```

**Security Issues Found**: \_\_\_ (List any)

---

## Phase 7: Performance Review (5 min)

### 7.1 Algorithmic Complexity

Review new/modified code for:

```bash
# Potential O(n²) patterns
git diff origin/main..HEAD | grep -E "^\\+.*for.*for|^\\+.*\\[.*for.*for"

# Repeated operations in loops
git diff origin/main..HEAD | grep -A5 "^\\+.*for " | grep -E "open\\(|read_csv|query\\("
```

### 7.2 Pandas Anti-patterns

```bash
# Check for slow Pandas operations
git diff origin/main..HEAD | grep -E "^\\+.*(iterrows|itertuples|apply\\(.*axis=1|inplace=True)"
```

**Verify:**

- [ ] No DataFrame iteration where vectorization is possible
- [ ] No `inplace=True` (violates immutability principle)
- [ ] Large data operations use appropriate data types

### 7.3 Memory Considerations

- [ ] No unbounded data structures that could grow infinitely
- [ ] Large file processing uses streaming/chunking where appropriate
- [ ] Temporary large objects are explicitly deleted or scoped

---

## Phase 8: Documentation & API Review (5 min)

### 8.1 Docstring Presence

```bash
# Functions missing docstrings
for f in $(git diff --name-only origin/main..HEAD | grep "\.py$"); do
    echo "=== $f ==="
    grep -n "def " "$f" | while read line; do
        linenum=$(echo "$line" | cut -d: -f1)
        nextline=$((linenum + 1))
        if ! sed -n "${nextline}p" "$f" | grep -q '"""'; then
            echo "  Line $linenum: Missing docstring"
        fi
    done 2>/dev/null | head -10
done
```

### 8.2 API Compatibility

For public API changes:

- [ ] Breaking changes are documented in CHANGELOG
- [ ] Deprecation warnings added for removed/changed APIs
- [ ] Migration guide provided for breaking changes

### 8.3 README & Docs Updates

- [ ] README updated if user-facing behavior changed
- [ ] Architecture docs updated if structure changed
- [ ] API docs reflect new endpoints/methods

---

## Phase 9: Code Quality Deep Dive (10 min)

### 9.1 Code Smells Detection

**Long Methods (>50 lines):**

```bash
for f in $(git diff --name-only origin/main..HEAD | grep "\.py$"); do
    awk '/^[[:space:]]*def /{name=$0; count=0} /^[[:space:]]*def /,/^[[:space:]]*def /{count++} count>50{print FILENAME":"name" ("count" lines)"; count=0}' "$f" 2>/dev/null
done
```

**Deep Nesting (>4 levels):**

```bash
git diff origin/main..HEAD | grep -E "^\\+[[:space:]]{16,}(if|for|while|try)"
```

**Magic Numbers/Strings:**

```bash
git diff origin/main..HEAD | grep -E "^\\+.*[^a-zA-Z_][0-9]{2,}[^a-zA-Z_0-9]" | grep -v "test\|#"
```

### 9.2 Naming Conventions

**Verify:**

- [ ] Classes are PascalCase
- [ ] Functions/methods are snake_case
- [ ] Constants are UPPER_SNAKE_CASE
- [ ] Private methods prefixed with `_`
- [ ] Names are descriptive (no `x`, `data`, `temp` for non-trivial variables)

### 9.3 Error Handling

```bash
# Bare except clauses
git diff origin/main..HEAD | grep -E "^\\+.*except:|^\\+.*except Exception:"

# Silent exception swallowing
git diff origin/main..HEAD | grep -A3 "^\\+.*except" | grep "pass$"
```

**Verify:**

- [ ] No bare `except:` clauses
- [ ] Exceptions are logged before being swallowed
- [ ] Custom domain exceptions used where appropriate
- [ ] Error messages are actionable

---

## Phase 10: Integration & Regression Testing (5 min)

### 10.1 Full Test Suite

```bash
# Run complete test suite
make test
# or
pytest tests/ -v --tb=short 2>&1 | tail -100
```

**Test Results:**

- Total tests: \_\_\_
- Passed: \_\_\_
- Failed: \_\_\_
- Skipped: \_\_\_

### 10.2 Manual Smoke Test (if UI changes)

- [ ] Application starts without errors
- [ ] Key workflows complete successfully
- [ ] No console errors in browser (if web UI)
- [ ] Data displays correctly

---

## Final Verification Checklist

### Must Pass (Blocking)

- [ ] **All tests pass** (100%)
- [ ] **Type checking passes** (mypy --strict)
- [ ] **No security vulnerabilities** (Critical/High)
- [ ] **Architectural boundaries respected**
- [ ] **No regression in existing functionality**

### Should Pass (Strongly Recommended)

- [ ] Test coverage ≥ 80% for new code
- [ ] All public APIs documented
- [ ] No code smells detected
- [ ] Performance considerations addressed

### Nice to Have (Recommended)

- [ ] Commit history is clean and logical
- [ ] Documentation updated
- [ ] CHANGELOG entry added

---

## Review Sign-Off

### Reviewer Notes

**Strengths of this branch:**

1. ***
2. ***
3. ***

**Concerns/Issues found:**

1. \_\_\_ (Severity: Critical/High/Medium/Low)
2. \_\_\_ (Severity: Critical/High/Medium/Low)
3. \_\_\_ (Severity: Critical/High/Medium/Low)

**Required changes before merge:**

1. ***
2. ***

**Recommended improvements (non-blocking):**

1. ***
2. ***

### Final Decision

- [ ] **APPROVED** - Ready to merge
- [ ] **APPROVED WITH CONDITIONS** - Merge after addressing specific items
- [ ] **CHANGES REQUESTED** - Cannot merge until issues resolved
- [ ] **REJECTED** - Fundamental issues require rework

---

**Reviewer**: **\_
**Date**: \_**
**Branch**: **\_
**Target**: \_**

---

## Appendix A: Quick Commands Reference

```bash
# Full review command sequence
git fetch origin
git log --oneline origin/main..HEAD
git diff --stat origin/main..HEAD

# Quality checks
make test
mypy src/ --strict
bandit -r src/ -ll
flake8 src/ tests/
black --check src/ tests/

# Coverage
pytest --cov=src --cov-report=html tests/
```

## Appendix B: Common Issues & Solutions

| Issue                   | Solution                                   |
| ----------------------- | ------------------------------------------ |
| Failing tests           | Fix tests before review proceeds           |
| Type errors             | Add proper type annotations                |
| Security warning        | Assess severity, fix or document exception |
| Missing tests           | Add tests for new code paths               |
| Architectural violation | Refactor to respect layer boundaries       |
| Performance issue       | Optimize or document as known limitation   |

## Appendix C: Escalation Path

If review uncovers issues that cannot be easily resolved:

1. **Minor issues**: Document in PR, fix in follow-up
2. **Significant issues**: Block merge, request changes
3. **Critical issues**: Escalate to tech lead, consider reverting related changes
4. **Architectural issues**: Schedule architecture review meeting

---

**End of Workflow**
