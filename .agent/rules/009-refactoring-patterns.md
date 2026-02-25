---
description: Refactoring patterns, extraction techniques, and mock path management learned from the Architectural Refactor v2.
globs: src/**/*.py, tests/**/*.py
---

# 009-refactoring-patterns.md

## 1. The Refactoring Engineer

You know how to decompose large classes, extract methods to standalone components, and reorganize directories — all while keeping 3000+ tests green at every step.

## 2. Method Extraction to Standalone Component

### 2.1 The Pattern

When extracting a method from a class into a standalone module-level function:

```python
# BEFORE: Method on a large class (God Class)
class BasePlot:
    def _render_axes_settings(self, config: dict) -> dict:
        col1, col2 = st.columns(2)
        with col1:
            config["x_label"] = st.text_input("X Label", config.get("x_label", ""))
        ...
        return config

# AFTER, Step 1: Standalone component function in its own module
# src/web/components/plotting/settings/axes_settings.py
def render_axes_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Render axes configuration widgets. Returns updated config."""
    col1, col2 = st.columns(2)
    with col1:
        config["x_label"] = st.text_input("X Label", config.get("x_label", ""))
    ...
    return config

# AFTER, Step 2: Thin delegate on the original class (backward compat during migration)
class BasePlot:
    def _render_axes_settings(self, config: dict) -> dict:
        from src.web.components.plotting.settings.axes_settings import render_axes_settings
        return render_axes_settings(config)
```

### 2.2 Thin Delegate Pattern

The thin delegate is a 3-line method that:
1. Lazy-imports the standalone function
2. Calls it with the same parameters
3. Returns the result

```python
def _render_some_settings(self, config: dict[str, Any]) -> dict[str, Any]:
    from src.web.components.plotting.settings.some_settings import render_some_settings
    return render_some_settings(config)
```

**Why lazy import?** Avoids circular imports during migration. The lazy import can be converted to a top-level import once the migration is complete and there are no circular dependency risks.

### 2.3 When to Remove Thin Delegates

Remove delegates when:
- All callers have been updated to call the standalone function directly
- No test patches target the class method anymore
- The class itself is being removed or simplified

## 3. Mock Path Management (CRITICAL)

### 3.1 The Core Rule

**When you extract a method to a standalone function, ALL test `@patch` decorators MUST be updated to target the NEW module where `st` is actually imported.**

```python
# BEFORE: Method on class, test mocks st in the class module
@patch("src.web.pages.ui.plotting.base_plot.st")
def test_axes_settings(mock_st):
    plot = BasePlot()
    plot._render_axes_settings(config)
    mock_st.columns.assert_called()

# AFTER: Standalone function, test must mock st in the COMPONENT module
@patch("src.web.components.plotting.settings.axes_settings.st")
def test_axes_settings(mock_st):
    from src.web.components.plotting.settings.axes_settings import render_axes_settings
    render_axes_settings(config)
    mock_st.columns.assert_called()
```

### 3.2 @patch.object vs @patch for Extracted Functions

When a component function calls another component function directly (not via `self.method()`), `@patch.object(Class, "method")` **will NOT intercept** the direct function call.

```python
# Component module
def render_grouped_theme_extras(config):
    # Calls render_stack_total_options directly — NOT via self
    totals = render_stack_total_options(config)
    ...

# ❌ WRONG — patch.object won't intercept the direct call
@patch.object(GroupedStackedBarPlot, "_render_stack_total_options")
def test_theme_extras(mock_totals):
    ...  # mock_totals is never called!

# ✅ CORRECT — patch at the module level where the function is defined
@patch("src.web.components.plotting.config.grouped_stacked_bar_theme.render_stack_total_options")
def test_theme_extras(mock_totals):
    ...  # mock_totals IS called
```

### 3.3 Mock Path Update Checklist

When extracting method `Class._method()` → `module.function()`:

1. **Find all patches**: `grep -rn "_method\|method_name" tests/ --include="*.py"`
2. **Identify patch style**: Is it `@patch("old.module.st")` or `@patch.object(Class, "_method")`?
3. **Update `@patch("old.module.st")`** → `@patch("new.component.module.st")`
4. **Update `@patch.object(Class, "_method")`** → `@patch("new.component.module.function_name")`
5. **Update imports in test**: change `from old.module import Class` to `from new.module import function`
6. **Run tests immediately**: `pytest tests/path/to/test_file.py -v`

## 4. Bulk File Reorganization

### 4.1 The 3-Group Strategy

When reorganizing many files, group them by domain and migrate one group at a time:

1. **Group by domain**: shapers, data managers, general components
2. **For each group**:
   - Copy files to new location with proper `__init__.py`
   - Bulk-update ALL import paths using `sed` or manual edits
   - Verify zero old references remain: `grep -rn "old.path" src/ tests/`
   - Run full test suite
   - Delete old files
3. **Never mix groups** — complete one before starting the next

### 4.2 Bulk Import Update with sed

```bash
# Example: Update all imports from old path to new path
find src/ tests/ -name "*.py" -exec sed -i \
  's/from src\.web\.pages\.ui\.components\.shapers\./from src.web.components.shapers./g' {} +

# Verify no old references remain
grep -rn "pages\.ui\.components\.shapers" src/ tests/ --include="*.py" | grep -v __pycache__
```

### 4.3 `__init__.py` for Reorganized Directories

Always write a proper `__init__.py` that re-exports all public names:

```python
"""Shaper configuration components."""
from src.web.components.shapers.mean_config import render_mean_config
from src.web.components.shapers.normalize_config import render_normalize_config
# ... all public exports

__all__ = [
    "render_mean_config",
    "render_normalize_config",
    # ...
]
```

## 5. Phase Skip Assessment

### 5.1 When to Skip a Refactoring Phase

Before executing a phase, run a quantitative ROI assessment:

| Factor | Skip If |
|--------|---------|
| Lines saved per class | < 30 lines |
| Shared code across targets | < 20 lines |
| Test mock paths to update | > 100 and benefit is marginal |
| Existing structure | Already clean and readable |
| Pattern adds indirection | Without reducing complexity |

### 5.2 Assessment Template

```markdown
## Phase N Assessment: [Name]

**Target**: [What to refactor]
**Current state**: [Lines, structure, pain points]
**Proposed action**: [What the refactoring would do]

**ROI Analysis**:
- Lines of shared code: X
- Lines that would be extracted: Y
- Test patches to update: Z
- New files/classes to create: N

**Verdict**: [EXECUTE / SKIP]
**Reason**: [Concrete justification]
```

### 5.3 Examples of Justified Skips

- **Template Method for Data Managers**: Each manager ~170 lines, only ~15 lines shared (confirm flow + history). Template would fragment readable code and break 100+ test mock paths.
- **Builder for FigureConfig**: Config has sensible defaults on all 24 fields. `FigureConfig()` with zero args is valid. 3 existing factory builders already work. Builder would add indirection without reducing complexity.
- **BaseStyleUI decomposition**: Already at 504 lines (down from 1077). Legend, typography, layout, colors extraction was done previously. Further splits would create too many tiny files.

## 6. Dead Code Identification

### 6.1 Verification Before Deletion

**NEVER delete code assumed to be dead without verifying**:

```bash
# Check ALL usages including tests
grep -rn "FunctionOrClassName" src/ tests/ --include="*.py" | grep -v __pycache__

# Check for dynamic imports or string references
grep -rn "function_name\|ClassName" src/ tests/ --include="*.py" | grep -v __pycache__
```

### 6.2 Autoflake for Unused Imports

```bash
# Dry-run check (report only)
./python_venv/bin/autoflake --check --remove-all-unused-imports -r src/

# Fix automatically
./python_venv/bin/autoflake --in-place --remove-all-unused-imports -r src/
```

### 6.3 What We Learned is NOT Dead Code

During Phase 10, several planned deletions turned out to still be active:
- `ShaperStepConfig` — used in 20+ files (it's the runtime config, not the model discriminated union)
- `render_advanced_options()` — actively called by multiple plot types
- `src/web/pages/ui/plotting/` — still the active location for plot type classes

**Rule**: Always verify with grep before deleting.

## 7. Continuous Test Verification

### 7.1 Run Tests After Every Change

After each extraction or reorganization step, run the affected tests immediately:

```bash
# Run specific test file
./python_venv/bin/pytest tests/unit/test_specific_file.py -v

# Run broader suite after multiple changes
./python_venv/bin/pytest tests/ -x -q

# Full suite before declaring phase complete
./python_venv/bin/pytest tests/ --tb=short -q
```

### 7.2 Track Test Count

Record the test count at each milestone to catch regressions:

```
Phase 1 start: 3184 passed
Phase 4 complete: 3184 passed
Phase 5 complete: 3229 passed (new component tests added)
Phase 11 final: 3229 passed, 2 skipped
```

If tests drop, investigate before proceeding.

---

**Status:** ✅ Active
**Priority:** HIGH
**Acknowledgement:** ✅ **Acknowledged Rule 009**
