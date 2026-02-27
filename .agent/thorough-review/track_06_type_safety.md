# Track 06: Type Safety Improvements

> **Priority**: MEDIUM
> **Status**: PENDING
> **Estimated items**: 6
> **Scope**: Entire `src/` — type annotations, protocols, TypedDicts

---

## What to Look At

### 6.1 Replace `dict[str, Any]` proliferation (496 occurrences across 60+ files)

**Key offenders (highest impact)**:
- `src/core/models/plot_models.py`, line 297: `PlotConfig = dict[str, Any]`
- All plot type `render_config_ui() -> dict[str, Any]` return types
- All settings components returning `dict[str, Any]`
- `src/web/rendering/config_builder.py` — assembles dicts of dicts

**What**: `dict[str, Any]` defeats the type checker entirely. Any key/value passes, so type errors in config assembly go undetected until runtime.
**Fix approach**: Create specific `TypedDict` classes:
- `AxesConfig`, `LegendConfig`, `LayoutConfig`, `DataLabelsConfig`, etc.
- `PlotDisplayConfig` as the top-level plot config TypedDict

### 6.2 80+ `Any` type annotations

**Key offenders**:
- `src/web/rendering/matplotlib_connector.py` — heavily uses `Any` for matplotlib types
- `src/web/rendering/plotly_connector.py` — uses `Any` for figure types
- Various function parameters typed as `Any` when specific types exist

**What**: `Any` disables type checking at those boundaries. Need to replace with specific types or use `Protocol` for structural typing.

### 6.3 10 Protocol classes missing `@runtime_checkable`

**File**: `src/web/controllers/plot/plot_protocols.py` (and other protocol definitions)
**What**: Protocols without `@runtime_checkable` can't be used with `isinstance()` checks. Some code attempts `isinstance()` checks against these protocols, which will fail.

### 6.4 15+ missing `@override` decorators (Python 3.12+)

**Files**:
- `BasePlot` subclasses (8 plot types in `src/web/pages/ui/plotting/`)
- `Shaper` subclasses (10 shapers in `src/core/services/shapers/impl/`)
- `StatType` subclasses (5 types in `src/parsing/gem5/types/`)

**What**: Without `@override`, a method that was supposed to override a parent method but has a typo in its name will silently become a new method.

### 6.5 Incomplete return type annotations

**Files with `-> None` but actually returning values**:
- `src/web/components/data_source/data_source_components.py`, line 96 — returns `dict | None`
- Possibly others detected by mypy

**What**: Return type lies cause type checker to miss actual return value usage bugs.

### 6.6 Fix `PlotConfig` type alias

**File**: `src/core/models/plot_models.py`
**What**: Current: `PlotConfig = dict[str, Any]` — anything passes. Should be a specific TypedDict.

---

## How to Investigate

1. **For 6.1**: Categorize all settings components by what keys they return. Design TypedDicts for each category. Start with the most-used ones.
2. **For 6.2**: Read matplotlib_connector.py. Replace `Any` with `matplotlib.figure.Figure`, `matplotlib.axes.Axes`, etc. where possible.
3. **For 6.3**: Search for all `class ...Protocol)` definitions. Check each for `@runtime_checkable`. Search for `isinstance()` calls that use protocols.
4. **For 6.4**: Find all `def render(`, `def apply(`, `def reduce(` in subclasses. Add `@override` decorator to each.
5. **For 6.5**: Run `mypy src/ --strict` and examine all return type errors.
6. **For 6.6**: Design the `PlotDisplayConfig` TypedDict. Update all callers.

---

## What We Expect to Find

- **6.1**: 10-15 TypedDicts needed to cover 80% of `dict[str, Any]` usage. The remaining 20% are genuinely dynamic configs.
- **6.2**: Most `Any` annotations can be replaced with specific types. matplotlib_connector.py has the most.
- **6.3**: Several protocols ARE used with `isinstance()` — adding `@runtime_checkable` fixes runtime errors.
- **6.4**: All overrides are correctly named (no typos found), but adding `@override` prevents future regressions.
- **6.6**: `PlotConfig` TypedDict will have ~15-20 typed keys.

---

## Outcome

**Status**: PENDING

| Item | Result | Fix Applied | Notes |
| --- | --- | --- | --- |
| 6.1 dict[str,Any] → TypedDict | PENDING | | |
| 6.2 Any annotations | PENDING | | |
| 6.3 @runtime_checkable | PENDING | | |
| 6.4 @override decorators | PENDING | | |
| 6.5 Return type annotations | PENDING | | |
| 6.6 PlotConfig TypedDict | PENDING | | |
