# Track 16: Trunk Lint & Format Fixes

> **Priority**: MEDIUM (must be done LAST, after all refactors)
> **Status**: PENDING
> **Estimated items**: 8
> **Scope**: All files flagged by `trunk check --all`

---

## What to Look At

### 16.1 Source code: pyright "possibly unbound" errors (3 issues)

**File**: `src/web/components/shapers/pivot_config.py`
- Line 256:34 — `selection_filters` is possibly unbound
- Line 257:35 — `strategy` is possibly unbound
- Line 258:28 — `merge_label` is possibly unbound

**What**: Variables used without guaranteed initialization on all control flow paths. Real bug risk.
**Fix**: Add explicit initialization before the branching logic.

### 16.2 Source code: isort formatting (2 src files)

**Files**:
- `src/web/components/data_source/variable_editor.py`
- `src/web/rendering/matplotlib_connector.py`

**What**: Import order doesn't match isort configuration.
**Fix**: `isort --profile=black --line-length=100 <file>`

### 16.3 Test files: isort formatting (4 test files)

**Files**:
- `tests/unit/test_mixer.py`
- `tests/unit/test_state_management_new.py`
- `tests/unit/test_state_manager_logic.py`
- `tests/unit/test_web_modules.py`

**What**: Same isort formatting issues.
**Fix**: `isort --profile=black --line-length=100 <files>`

### 16.4 Markdown: table formatting in `.agent/` files (50+ issues)

**Files**: `.agent/DEEP_DIVE_PLAN.md`, `.agent/PROGRESS.md`, `.agent/research-scan/*.md`
**What**: Markdown tables don't have consistent column widths. `markdownlint/MD060` and `prettier` formatting issues.
**Fix**: `trunk fmt --all` for markdown files, or manual table reformatting.

### 16.5 Markdown: fenced code blocks without language (15+ issues)

**Files**: Various `.agent/` markdown files
**What**: Code blocks like ` ``` ` without language specifier. `markdownlint/MD040` requires language.
**Fix**: Add `python`, `bash`, `text`, etc. to all fenced code blocks.

### 16.6 Markdown: heading issues (5+ issues)

**Files**: Various `.agent/rules/`, `.agent/skills/`, `docs/` files
**What**: `MD041` (first line not heading), `MD025` (multiple top-level headings), `MD024` (duplicate headings), `MD036` (emphasis instead of heading).
**Fix**: Fix heading structure.

### 16.7 Run `trunk fmt --all` for auto-fixable issues

**What**: Many issues are auto-fixable. Run `trunk fmt --all` and review changes.
**Caveat**: Must be done AFTER all code refactors to avoid conflicts.

### 16.8 Verify zero trunk issues after all fixes

**What**: Final `trunk check --all` should show 0 issues.

---

## How to Investigate

1. **For 16.1**: Read pivot_config.py lines 240-260. Trace all control flow paths. Add initialization.
2. **For 16.2-16.3**: Run `isort --profile=black --line-length=100 --diff <file>` to see what changes.
3. **For 16.4-16.6**: These are markdown-only issues. Use `trunk fmt` for auto-fix.
4. **For 16.7**: Run `trunk fmt --all`. Review all changes. Commit.
5. **For 16.8**: Run `trunk check --all --no-fix`. Verify output shows 0 issues.

---

## What We Expect to Find

- **16.1**: Real bug — variables are used on a path where they weren't assigned. Fix: add defaults before branching.
- **16.2-16.3**: Trivial isort fixes. Auto-fixable.
- **16.4-16.6**: All markdown. Auto-fixable with `trunk fmt`.
- **16.8**: After all fixes, trunk check should be clean.

---

## Trunk Check Baseline (as of commit 362106e)

```text
Checked 733 files
- 20 unformatted files
- 119 lint issues
```

**Source code issues**: 3 pyright + 5 isort = 8 total
**Markdown/docs issues**: ~111 total (formatting, headings, code blocks)

---

## Outcome

**Status**: PENDING

| Item | Result | Fix Applied | Notes |
| --- | --- | --- | --- |
| 16.1 Pyright unbound | PENDING | | |
| 16.2 Source isort | PENDING | | |
| 16.3 Test isort | PENDING | | |
| 16.4 Markdown tables | PENDING | | |
| 16.5 Code block langs | PENDING | | |
| 16.6 Heading issues | PENDING | | |
| 16.7 trunk fmt --all | PENDING | | |
| 16.8 Zero issues verify | PENDING | | |
