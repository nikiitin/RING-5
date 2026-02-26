# Code Quality Gate Workflow

> **Invoke with**: `/quality-gate`
> **Purpose**: Comprehensive checklist an agent MUST complete before declaring any task "done"
> **Applies to**: ALL code changes — features, bug fixes, refactoring
> **Complexity**: Quick (3-5 minutes)
> **MANDATORY**: No task is complete until this workflow passes

---

## Overview

This is the **Definition of Done** for AI agents. Every code change must pass through this quality gate before reporting completion to the user. This is not optional — it is the contract between the agent and the codebase.

**Philosophy**: "Done means tested, typed, linted, secure, and architecturally sound."

---

## Gate 1: Architecture Boundaries (BLOCKING)

Run the architecture validation workflow checks:

```bash
# Layer boundary check (ALL must return empty)
echo "=== GATE 1: Architecture ===" && \
VIOLATIONS=0 && \
RESULT=$(grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" 2>/dev/null | grep -v __pycache__) && \
[ -n "$RESULT" ] && echo "❌ Streamlit in core: $RESULT" && VIOLATIONS=$((VIOLATIONS+1)) || true && \
RESULT=$(grep -rn "session_state" src/core/ --include="*.py" 2>/dev/null | grep -v __pycache__) && \
[ -n "$RESULT" ] && echo "❌ session_state in core: $RESULT" && VIOLATIONS=$((VIOLATIONS+1)) || true && \
RESULT=$(grep -rn "inplace=True" src/ --include="*.py" 2>/dev/null | grep -v __pycache__) && \
[ -n "$RESULT" ] && echo "❌ inplace=True found: $RESULT" && VIOLATIONS=$((VIOLATIONS+1)) || true && \
RESULT=$(grep -rn "^[[:space:]]*except:" src/ --include="*.py" 2>/dev/null | grep -v __pycache__) && \
[ -n "$RESULT" ] && echo "❌ Bare except found: $RESULT" && VIOLATIONS=$((VIOLATIONS+1)) || true && \
echo "Violations: $VIOLATIONS" && \
[ $VIOLATIONS -eq 0 ] && echo "✅ GATE 1 PASSED" || echo "❌ GATE 1 FAILED — fix violations before proceeding"
```

**Verdict**: Any violation → **STOP and fix**.

---

## Gate 2: Type Safety (BLOCKING)

```bash
echo "=== GATE 2: Type Safety ===" && \
./python_venv/bin/mypy src/ --show-error-codes --pretty 2>&1 | tail -3
```

**Criteria**:

- Zero new mypy errors
- No `# type: ignore` added without justification comment
- All new functions have complete type annotations (parameters + return type)

**Quick check for untyped new code**:

```bash
# Functions without return types (review manually)
grep -rn "def " src/ --include="*.py" | grep -v " -> " | grep -v __pycache__ | grep -v "__init__\|__repr__\|__str__" | wc -l
```

---

## Gate 3: Code Formatting (BLOCKING)

```bash
echo "=== GATE 3: Formatting ===" && \
./python_venv/bin/black --check src/ 2>&1 | tail -3 && \
echo "✅ Formatting OK" || echo "❌ Run: ./python_venv/bin/black src/"
```

---

## Gate 4: Linting (BLOCKING)

```bash
echo "=== GATE 4: Linting ===" && \
./python_venv/bin/flake8 src/ --count --statistics 2>&1 | tail -5
```

**Criteria**: Zero flake8 errors.

---

## Gate 5: Security Scan (BLOCKING)

```bash
echo "=== GATE 5: Security ===" && \
ISSUES=0 && \
RESULT=$(grep -rn "eval(\|exec(" src/ --include="*.py" 2>/dev/null | grep -v __pycache__ | grep -v test) && \
[ -n "$RESULT" ] && echo "❌ eval/exec: $RESULT" && ISSUES=$((ISSUES+1)) || true && \
RESULT=$(grep -rn "pickle\.load" src/ --include="*.py" 2>/dev/null | grep -v __pycache__) && \
[ -n "$RESULT" ] && echo "⚠️ pickle.load: $RESULT" && ISSUES=$((ISSUES+1)) || true && \
RESULT=$(grep -rn "shell=True" src/ --include="*.py" 2>/dev/null | grep -v __pycache__) && \
[ -n "$RESULT" ] && echo "⚠️ shell=True: $RESULT (verify necessity)" || true && \
[ $ISSUES -eq 0 ] && echo "✅ GATE 5 PASSED" || echo "⚠️ GATE 5: Review findings above"
```

Optional deeper scan:

```bash
./python_venv/bin/bandit -r src/ -ll --quiet 2>&1 | tail -10
```

---

## Gate 6: Test Existence (WARNING)

For every new/modified source file, verify a corresponding test exists:

```bash
echo "=== GATE 6: Test Coverage ===" && \
for f in $(find src/ -name "*.py" -newer src/__init__.py -not -path "*__pycache__*" 2>/dev/null | head -10); do
    base=$(basename "$f" .py)
    if [ "$base" = "__init__" ]; then continue; fi
    found=$(find tests/ -name "*${base}*" -not -path "*__pycache__*" 2>/dev/null | head -1)
    if [ -z "$found" ]; then
        echo "⚠️ No test found for: $f"
    fi
done && \
echo "✅ GATE 6 CHECK COMPLETE"
```

**Criteria**: Every new public module should have corresponding tests.

---

## Gate 7: Documentation (WARNING)

```bash
echo "=== GATE 7: Documentation ===" && \
# Check for public functions without docstrings in modified files
for f in $(find src/ -name "*.py" -newer src/__init__.py -not -path "*__pycache__*" 2>/dev/null | head -10); do
    missing=$(grep -n "def [a-z]" "$f" 2>/dev/null | while read line; do
        linenum=$(echo "$line" | cut -d: -f1)
        nextline=$((linenum + 1))
        if ! sed -n "${nextline}p" "$f" 2>/dev/null | grep -q '"""'; then
            echo "  $f:$linenum"
        fi
    done)
    [ -n "$missing" ] && echo "⚠️ Missing docstrings:$missing"
done && \
echo "✅ GATE 7 CHECK COMPLETE"
```

---

## Quick All-Gates Script

Copy-paste this to run all blocking gates at once:

```bash
echo "╔══════════════════════════════════╗" && \
echo "║     RING-5 QUALITY GATE          ║" && \
echo "╚══════════════════════════════════╝" && \
echo "" && \
PASS=0 && FAIL=0 && \
echo "▸ Gate 1: Architecture..." && \
V=$(grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" 2>/dev/null | grep -v __pycache__ | wc -l) && \
V=$((V + $(grep -rn "inplace=True" src/ --include="*.py" 2>/dev/null | grep -v __pycache__ | wc -l))) && \
V=$((V + $(grep -rn "^[[:space:]]*except:" src/ --include="*.py" 2>/dev/null | grep -v __pycache__ | wc -l))) && \
[ $V -eq 0 ] && echo "  ✅ Architecture OK" && PASS=$((PASS+1)) || (echo "  ❌ $V violations" && FAIL=$((FAIL+1))) && \
echo "▸ Gate 2: Type Safety..." && \
MYPY_ERRORS=$(./python_venv/bin/mypy src/ --no-error-summary 2>&1 | grep ": error:" | wc -l) && \
[ "$MYPY_ERRORS" -eq 0 ] && echo "  ✅ Types OK" && PASS=$((PASS+1)) || (echo "  ❌ $MYPY_ERRORS mypy errors" && FAIL=$((FAIL+1))) && \
echo "▸ Gate 3: Formatting..." && \
./python_venv/bin/black --check --quiet src/ 2>&1 && echo "  ✅ Formatting OK" && PASS=$((PASS+1)) || (echo "  ❌ Needs formatting" && FAIL=$((FAIL+1))) && \
echo "▸ Gate 4: Linting..." && \
LINT_ERRORS=$(./python_venv/bin/flake8 src/ --count 2>&1 | tail -1) && \
[ "$LINT_ERRORS" = "0" ] && echo "  ✅ Linting OK" && PASS=$((PASS+1)) || (echo "  ❌ $LINT_ERRORS lint issues" && FAIL=$((FAIL+1))) && \
echo "▸ Gate 5: Security..." && \
SEC=$(grep -rn "eval(\|exec(" src/ --include="*.py" 2>/dev/null | grep -v __pycache__ | grep -v test | wc -l) && \
[ $SEC -eq 0 ] && echo "  ✅ Security OK" && PASS=$((PASS+1)) || (echo "  ⚠️ $SEC security findings" && FAIL=$((FAIL+1))) && \
echo "" && \
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" && \
echo "Results: $PASS passed, $FAIL failed" && \
[ $FAIL -eq 0 ] && echo "🟢 ALL GATES PASSED — Ready for review" || echo "🔴 QUALITY GATE FAILED — Fix issues above"
```

---

## When to Run This Workflow

| Situation                        | Required?            |
| :------------------------------- | :------------------- |
| After implementing a new feature | **YES**              |
| After fixing a bug               | **YES**              |
| After refactoring                | **YES**              |
| After editing any `.py` file     | **YES**              |
| After editing only docs/configs  | No (but recommended) |

---

## Gate 8: UI Widget Audit (WARNING — for UI changes)

When modifying UI code in `src/web/pages/`, verify:

```bash
echo "=== GATE 8: UI Widget Audit ===" && \
echo "Check 1: Conditional widgets — dual-axis/boxed guards" && \
grep -rn "has_dual_axis\|has_boxed" src/web/pages/ --include="*.py" | grep -v __pycache__ | head -10 && \
echo "" && \
echo "Check 2: No duplicate rename/reorder widgets" && \
grep -rn "render_xaxis_labels_ui\|render_series_renaming_ui" src/web/pages/ --include="*.py" | grep -v __pycache__ | head -10 && \
echo "" && \
echo "Check 3: Settings pills — no dead sections" && \
grep -rn "SettingsSection" src/web/pages/ --include="*.py" | grep -v __pycache__ && \
echo "✅ GATE 8 CHECK COMPLETE"
```

**Criteria**:

- Conditional widgets (Y-Right axis, secondary/boxed legend) must check
  `has_dual_axis` or `has_boxed` before rendering
- No standalone `render_xaxis_labels_ui()` or `render_series_renaming_ui()`
  calls — inline via `render_reorderable_list(enable_rename=True)` instead
- Every `SettingsSection` must have a matching handler in the dispatcher

---

## Escalation

If a gate cannot be resolved:

1. **Type errors in third-party libs**: Add targeted `# type: ignore[error-code]` with comment explaining why
2. **Flake8 false positives**: Add inline `# noqa: EXXX` with justification
3. **Architecture violations inherited from existing code**: Flag to user, do not add new violations

---

## End of Workflow
