# Skill: Refactoring Large Codebases

> **Activates when**: Decomposing God classes, extracting methods to components, reorganizing directories, or performing multi-phase refactoring
> **Domain**: Software Architecture × Test Engineering

---

## Overview

This skill encodes the complete methodology for performing large-scale refactoring on the RING-5 codebase, distilled from the Architectural Refactor v2 which:
- Reduced `GroupedStackedBarPlot` from 1335 → 506 lines
- Reduced `BasePlot` from 992 → 685 lines
- Reduced `BaseStyleUI` from 1077 → 504 lines
- Extracted 20+ standalone component functions
- Reorganized 3 groups of files into `src/web/components/`
- Maintained 3229 tests passing throughout

---

## Step 1: Identify Extraction Candidates

Look for methods that:
- Are > 50 lines and primarily render UI widgets
- Accept a config dict and return a modified config dict
- Don't rely on `self` beyond forwarding to other methods
- Are called from only one or two locations

```bash
# Find long methods in a class
grep -n "def " src/web/pages/ui/plotting/base_plot.py | head -20

# Count lines per method (approximate)
awk '/def /{name=$0; count=0} {count++} /^    def |^class /{if(count>50)print count, name}' \
  src/web/pages/ui/plotting/base_plot.py
```

---

## Step 2: Extract to Standalone Function

### 2.1 Create the Component Module

```python
# src/web/components/plotting/settings/axes_settings.py
"""Axes configuration component for plot settings."""

from typing import Any
import streamlit as st


def render_axes_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Render axes configuration widgets.

    Args:
        config: Current figure configuration dict.

    Returns:
        Updated configuration dict with axes settings.
    """
    col1, col2 = st.columns(2)
    # ... extracted logic here (NO self references)
    return config
```

### 2.2 Add Thin Delegate on Original Class

```python
# In the original class (e.g., BasePlot)
def _render_axes_settings(self, config: dict[str, Any]) -> dict[str, Any]:
    from src.web.components.plotting.settings.axes_settings import render_axes_settings
    return render_axes_settings(config)
```

### 2.3 Handle `self` Dependencies

If the method uses `self.some_property`:
1. **Pass as parameter**: Add `some_property` as a function argument
2. **Extract from config**: If it's in the config dict, access it there
3. **Lazy import**: Use `from module import constant` for class-level constants

---

## Step 3: Update Test Mock Paths

This is the **most critical step** — where most bugs occur.

### 3.1 Find All Affected Tests

```bash
# Find patches targeting the old module
grep -rn "patch.*base_plot\|patch.*BasePlot" tests/ --include="*.py" | head -20

# Find patches targeting the specific method
grep -rn "_render_axes_settings" tests/ --include="*.py"
```

### 3.2 Update Patches

| Old Pattern | New Pattern |
|-------------|-------------|
| `@patch("src.web.pages.ui.plotting.base_plot.st")` | `@patch("src.web.components.plotting.settings.axes_settings.st")` |
| `@patch.object(BasePlot, "_render_axes_settings")` | `@patch("src.web.components.plotting.settings.axes_settings.render_axes_settings")` |

### 3.3 Verify Immediately

```bash
./python_venv/bin/pytest tests/ui_unit/test_axes_settings.py -v
```

---

## Step 4: Bulk Directory Reorganization

When moving many files to new locations:

### 4.1 Plan the Mapping

```markdown
| Source | Destination |
|--------|-------------|
| src/web/pages/ui/components/shapers/ | src/web/components/shapers/ |
| src/web/pages/ui/data_managers/ | src/web/components/data_managers/ |
```

### 4.2 Execute Per Group

```bash
# 1. Copy files to new location
cp src/old/path/*.py src/new/path/

# 2. Write __init__.py with re-exports
cat > src/new/path/__init__.py << 'EOF'
"""Module description."""
from src.new.path.module_a import function_a
from src.new.path.module_b import function_b
__all__ = ["function_a", "function_b"]
EOF

# 3. Bulk update ALL imports
find src/ tests/ -name "*.py" -exec sed -i \
  's/from src\.old\.path\./from src.new.path./g' {} +

# 4. Verify zero old references
grep -rn "old\.path" src/ tests/ --include="*.py" | grep -v __pycache__

# 5. Run full test suite
./python_venv/bin/pytest tests/ -x -q

# 6. Delete old directory (only after tests pass)
rm -rf src/old/path/
```

---

## Step 5: Dead Code Cleanup

### 5.1 Verify Before Deleting

```bash
# Check ALL usages
grep -rn "TargetName" src/ tests/ --include="*.py" | grep -v __pycache__

# Check for string references (dynamic imports, configs)
grep -rn "\"TargetName\"\|'TargetName'" src/ tests/ --include="*.py"
```

### 5.2 Clean Caches

```bash
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
```

### 5.3 Unused Imports

```bash
./python_venv/bin/autoflake --check --remove-all-unused-imports -r src/
```

---

## Common Pitfalls

1. **Mock path mismatch**: `@patch("old.module.st")` still mocks `st` in the old module, but the logic now runs in the new module where `st` is NOT mocked → tests pass but assertions fail silently
2. **`@patch.object` on extracted functions**: When function A calls function B directly (not via `self`), `@patch.object(Class, "B")` won't intercept it — must use `@patch("module.B")` 
3. **Circular imports**: Use lazy imports in thin delegates to break cycles
4. **Forgetting `__init__.py`**: New directories need proper `__init__.py` with re-exports
5. **Deleting "dead" code prematurely**: Always `grep` first — tests may use it

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Test count | Same or higher than baseline |
| Quality gate | All gates pass |
| God class lines | Reduced by ≥ 40% |
| New component files | Each < 200 lines |
| Old import references | Zero remaining |

---

## References

- **Rule**: `.agent/rules/009-refactoring-patterns.md` — Mock paths, extraction patterns
- **Workflow**: `.agent/workflows/large-refactor.md` — Phase execution methodology
- **Plan**: `.agent/plans/architectural-refactor-v2.md` — Canonical refactor log
- **Quality Gate**: `.agent/workflows/code-quality-gate.md` — Run after every phase
