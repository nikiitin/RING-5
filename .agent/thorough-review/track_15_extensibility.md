# Track 15: Extensibility Frameworks

> **Priority**: LOW
> **Status**: PENDING
> **Estimated items**: 3
> **Scope**: Plugin/factory patterns for future extensibility

---

## What to Look At

### 15.1 Create `@cached_shaper()` decorator

**Files**:
- `src/core/services/shapers/impl/mean.py`
- `src/core/services/shapers/impl/normalize.py`

**What**: Both shapers implement identical fingerprint-based caching:
```python
def _fingerprint(self, df: pd.DataFrame) -> str:
    return hashlib.md5(pd.util.hash_pandas_object(df).values.tobytes()).hexdigest()

def apply(self, df):
    key = self._fingerprint(df)
    if key in self._cache:
        return self._cache[key]
    result = self._compute(df)
    self._cache[key] = result
    return result
```
**Action**: Extract into `@cached_shaper(ttl=300)` decorator that any shaper can use.

### 15.2 Split LegendSettingsComponent into sub-components

**File**: `src/web/components/plotting/settings/legend_settings.py` (~180 lines)
**What**: Single class handles 3-level legend navigation (primary, secondary, tertiary). Hard to extend for new legend types.
**Action**: Split into:
- `PrimaryLegendSettings`
- `SecondaryLegendSettings`
- `LegendSettingsAggregator`

### 15.3 Evaluate plugin architecture for new plot types

**File**: `src/web/pages/ui/plotting/plot_factory.py`
**What**: Currently, adding a new plot type requires:
1. Creating the plot class in `src/web/pages/ui/plotting/`
2. Registering in `plot_factory.py`
3. Creating config in `src/web/components/plotting/config/`
4. Adding rendering logic in connectors

**Evaluate**: Whether a plugin/auto-discovery pattern (e.g., `__init_subclass__` hook or `importlib` scan) would reduce registration boilerplate.

---

## How to Investigate

1. **For 15.1**: Diff the caching patterns in mean.py and normalize.py. Verify they are truly identical. Design decorator with TTL and eviction.
2. **For 15.2**: Read legend_settings.py. Map the 3-level navigation. Design sub-component interfaces.
3. **For 15.3**: Read plot_factory.py registration code. Count the manual registration steps. Evaluate auto-discovery alternatives.

---

## What We Expect to Find

- **15.1**: Caching patterns are 95%+ identical. Decorator trivially extractable.
- **15.2**: Split is clean. Each level is ~60 lines. Aggregator is ~20 lines.
- **15.3**: Auto-discovery is feasible using `__init_subclass__` but adds complexity. Manual registration is fine for 8 plot types. Flag for when count exceeds 15.

---

## Outcome

**Status**: INVESTIGATION COMPLETE

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 15.1 cached_shaper decorator | **WARRANTED** — mean.py and normalize.py both implement identical `_compute_data_fingerprint()` static methods (~30 lines each, 95% identical). Both already use shared `@cached` decorator from `src/core/performance.py` but duplicate the fingerprint logic. Difference: cache sizes (16 vs 32). | MEDIUM | Create `@cached_shaper_fingerprint()` in `src/core/services/shapers/cached_shaper.py` that combines fingerprint computation with caching. ~60 lines of duplication removed. |
| 15.2 Legend split | **NOT WARRANTED** — legend_settings.py is 338 lines with well-decomposed private methods: `render()` (72 lines), `_render_legend_section()` (11 lines), `_render_legend_position()` (34 lines), `_render_legend_appearance()` (88 lines), `_render_legend_sizing()` (80 lines). Splitting would add boilerplate and reduce code locality. | LOW | No action needed. Current design is well-decomposed and manageable. |
| 15.3 Plugin architecture | **NOT WARRANTED** — 9 plot types registered via manual import + static dict in plot_factory.py:33-43. `register_plot_type()` class method already exists (line 80-98). Adding a new plot type requires 4 steps (create file, __init__.py, import, register). At 9 types, manual registration is optimal. `__init_subclass__` would add hidden magic with minimal benefit. | LOW | No action needed. Revisit only if plot count exceeds 15-20. |

### Key Finding
The codebase already has a shared caching utility (`@cached` in performance.py). The duplication is in fingerprint computation, not the caching mechanism itself. Extraction would consolidate the fingerprint logic while leveraging existing infrastructure.

### Critical Findings Summary (items for improvement)
1. **Fingerprint duplication in cached shapers** — MEDIUM: 60 lines of identical fingerprint logic across 2 files
