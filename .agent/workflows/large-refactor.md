# Large-Scale Refactoring Workflow

> **Invoke with**: `/large-refactor`
> **Purpose**: Structured approach to multi-phase architectural refactoring with persistent plan tracking
> **Applies to**: Any refactoring spanning more than 3 files or 2 phases
> **Complexity**: Variable (hours to days)
> **Prerequisites**: Quality gate passing before starting

---

## Overview

This workflow captures the methodology for executing large-scale refactoring safely. The core philosophy:

1. **Plan first, execute second** — Every refactor starts with a written plan
2. **One phase at a time** — Complete and verify each phase before moving on
3. **Tests never break** — Full suite must pass after every phase
4. **Log everything** — Update the plan file after every phase to capture decisions

---

## Phase 0: Create the Plan File

Before writing any code, create a plan file at `.agent/plans/<refactor-name>.md`:

```markdown
# Refactor Plan: [Name]

## Objective

[What we're trying to achieve and why]

## Success Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] All tests pass
- [ ] Quality gate clean

## Phase Inventory

| Phase | Description            | Status | Test Count |
| ----- | ---------------------- | ------ | ---------- |
| 0     | Setup & prerequisites  | ⬜     | —          |
| 1     | [First transformation] | ⬜     | —          |
| ...   |                        |        |            |

## Decisions Log

[Record every non-trivial decision, especially skips]

## Lessons Learned

[Capture patterns and gotchas as they arise]
```

**The plan file is the single source of truth.** Update it after every phase.

---

## Phase 1: Pre-Refactor Assessment

### 1.1 Measure the Codebase

Before refactoring, quantify what you have:

```bash
# File sizes of targets
wc -l src/web/pages/ui/plotting/base_plot.py
wc -l src/web/pages/ui/plotting/types/*.py

# Test count baseline
./python_venv/bin/pytest tests/ --co -q 2>&1 | tail -1

# Quality gate baseline
# Run the full quality gate workflow
```

### 1.2 Identify Dependencies

For each file you plan to modify:

```bash
# Who imports this module?
grep -rn "from src.web.pages.ui.plotting.base_plot import" src/ tests/ --include="*.py"

# Who patches methods on this class?
grep -rn "patch.*BasePlot\|patch.object.*BasePlot" tests/ --include="*.py"
```

### 1.3 Record Baseline

Update the plan file with:

- Starting line counts for target files
- Starting test count
- List of all files that will need import updates

---

## Phase 2: Execute One Phase at a Time

### 2.1 Phase Execution Protocol

For each phase:

1. **Mark phase as in-progress** in plan file
2. **Create the new file(s)** — write the standalone component/module
3. **Add thin delegates** on the original class (if backward compat needed)
4. **Update ALL test patches** — this is where most bugs hide (see Rule 009)
5. **Run affected tests**: `pytest tests/path/to/affected/ -v`
6. **Run full suite**: `pytest tests/ -x -q`
7. **Run quality gate**: architecture boundaries + flake8 + black
8. **Update plan file** with:
   - Status: ✅
   - Test count: N passed
   - Notable decisions or patterns discovered

### 2.2 Phase Ordering Strategy

Execute phases in dependency order:

1. **Leaf extractions first** — Settings tabs, config panels (no external deps)
2. **Shared utilities next** — Common functions used by multiple components
3. **Core class decomposition** — God class reduction
4. **Directory reorganization** — Move files to final locations (ALL imports change)
5. **Cleanup** — Remove dead code, thin delegates, old directories

### 2.3 Import Update Strategy for Large Moves

When moving many files at once:

```bash
# Bulk update with sed (grouped by source directory)
find src/ tests/ -name "*.py" -exec sed -i \
  's/from src\.old\.path\./from src.new.path./g' {} +

# Verify zero old references
grep -rn "old\.path" src/ tests/ --include="*.py" | grep -v __pycache__

# Run full test suite
./python_venv/bin/pytest tests/ -x -q
```

---

## Phase 3: Skip Assessment

### 3.1 When to Skip a Phase

Not every planned phase needs execution. Run this assessment:

**Quantitative check:**

- Lines of code that would be shared/reduced: < 30 → likely skip
- Test patches that would break: > 100 with marginal benefit → skip
- Existing code already clean and readable → skip
- Pattern adds indirection without reducing complexity → skip

**Assessment format** (record in plan file):

```markdown
### Phase N: [Name] — SKIPPED

**Assessment**: [1-2 sentences explaining what was evaluated]
**Data**: [Lines analyzed, shared code found, test impact]
**Verdict**: Skip — [concrete reason]
```

### 3.2 Examples of Good Skips

- Template Method for 4 managers with only 15 shared lines each
- Builder for a config class with sensible defaults on all fields
- Further decomposition of a class already reduced from 1077 → 504 lines

---

## Phase 4: Final Validation

### 4.1 Quality Gate Checklist

Run the full quality gate (`.agent/workflows/code-quality-gate.md`):

```bash
# Architecture boundaries
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "session_state" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "inplace=True" src/ --include="*.py" | grep -v __pycache__

# Full test suite
./python_venv/bin/pytest tests/ --tb=short -q

# Formatting & linting
./python_venv/bin/black --check src/
./python_venv/bin/flake8 src/

# Type safety
./python_venv/bin/mypy src/ --show-error-codes

# Unused imports
./python_venv/bin/autoflake --check --remove-all-unused-imports -r src/
```

### 4.2 Coverage Check

```bash
./python_venv/bin/pytest tests/ --cov=src --cov-report=term-missing -q 2>&1 | tail -5
```

### 4.3 Final Plan Update

Update the plan file with:

- All phases marked with final status (✅, ⏭️ SKIPPED)
- Final test count and coverage
- Summary of total lines reduced
- Lessons learned section

---

## Anti-Patterns

| Don't                                                | Do Instead                                    |
| ---------------------------------------------------- | --------------------------------------------- |
| Refactor multiple groups simultaneously              | Complete one group, test, then start next     |
| Skip test verification "because it's just a move"    | ALWAYS run tests after every file operation   |
| Delete files before verifying all references updated | `grep` first, delete second                   |
| Assume a function is dead code                       | Verify with `grep -rn` across src/ AND tests/ |
| Mix refactoring with feature development             | One concern per phase                         |
| Start phase N+1 before N is green                    | Fix all test failures first                   |

---

## Plan File as Persistent Context

The plan file serves multiple critical purposes:

1. **Session continuity**: When the AI agent is re-invoked in a new session, the plan file provides complete context of what was done, what remains, and what decisions were made
2. **Knowledge accumulation**: Lessons learned during execution are captured for future refactors
3. **Progress tracking**: Test counts at each phase detect regressions immediately
4. **Decision audit trail**: Why phases were executed or skipped is documented
5. **Communication**: The user can read the plan file to understand exactly what happened

**Format**: `.agent/plans/<name>.md`
**Update frequency**: After every phase completion or skip
**Reference**: Load the plan file as context before starting any refactoring work

---

## End of Workflow
