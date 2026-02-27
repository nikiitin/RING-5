# Track 07: Code Duplication Consolidation

> **Priority**: HIGH
> **Status**: PENDING
> **Estimated items**: 8
> **Scope**: Duplicated files, functions, and patterns across `src/`

---

## What to Look At

### 7.1 ChartDisplayComponent vs ChartPresenter (~520 lines of duplication)

**Files**:
- `src/web/components/common/chart_display.py` (~260 lines)
- `src/web/presenters/plot/chart_presenter.py` (~260 lines)

**What**: Nearly identical implementations of chart rendering logic. The presenter layer was removed during architectural refactor v2, but `chart_presenter.py` was not deleted.
**Action**: Keep `ChartDisplayComponent`, delete `ChartPresenter`, update all imports.

### 7.2 Duplicate shaper config: split_apply_config.py

**Files**:
- `src/web/components/shapers/split_apply_config.py`
- `src/web/pages/ui/components/shapers/split_apply_config.py`

**What**: Same file in two locations. One is the canonical import, the other is a leftover.

### 7.3 Duplicate data managers: seeds_reducer.py, outlier_remover.py

**Files**:
- `src/web/components/data_managers/seeds_reducer.py` vs `src/web/pages/ui/components/data_managers/seeds_reducer.py`
- `src/web/components/data_managers/outlier_remover.py` vs `src/web/pages/ui/components/data_managers/outlier_remover.py`

**What**: Same duplication pattern as 7.2. One copy in components/, one in pages/ui/.

### 7.4 Centralize session state access through UIStateManager

**Files with direct `st.session_state[]` access** (bypassing UIStateManager):
- `seeds_reducer.py:110-112`
- `mixer.py:50-65`
- `preprocessor.py:54-65`
- `outlier_remover.py:59-66`
- `colors_settings.py:242-244`
- `base_ui.py:358-360`

**What**: UIStateManager exists but is bypassed in 6+ files with 13+ direct accesses.
**Action**: Add data manager state methods to UIStateManager. Migrate direct accesses.

### 7.5 Create SettingsComponentBase class

**What**: Every settings component (axes, legend, layout, typography, data_labels, colors, advanced, engine, ordering, reference_line, shapes) reimplements:
- Widget key building: `key=f"{key_prefix}show_val_{self.plot_id}"`
- Config dict assembly: `config = {}; config["x_title"] = ...; return config`
- Render signature: `render() -> dict[str, Any]`

**Action**: Create `SettingsComponentBase` with `widget_key(suffix)` method and standardized `render() -> SettingsConfig` signature.

### 7.6 Extract shaper UI utilities from pivot_config.py

**File**: `src/web/components/shapers/pivot_config.py`
**Functions**:
- `extract_with_pattern()` (line ~30)
- `detect_common_pattern()` (line ~17)

**What**: These utility functions are in a specific config file but could be reused by other shaper configs.
**Action**: Move to `src/web/components/shapers/utils.py`.

### 7.7 Shaper caching duplication (mean.py and normalize.py)

**Files**:
- `src/core/services/shapers/impl/mean.py`
- `src/core/services/shapers/impl/normalize.py`

**What**: Both implement identical fingerprint-based caching patterns:
- `_fingerprint(df)` method computing hash of input DataFrame
- Cache lookup before computation
- Cache store after computation

**Action**: Extract `@cached_shaper()` decorator or `CachedShaper` mixin.

### 7.8 Legend and data label logic duplication between connectors

**Files**:
- `src/web/rendering/plotly_connector.py`
- `src/web/rendering/matplotlib_connector.py`

**What**: 85-90% duplication in legend configuration and data label formatting logic. Both connectors implement the same business logic (which labels to show, where to position them).
**Action**: Extract shared logic into `src/web/rendering/common/label_config.py` or similar.

---

## How to Investigate

1. **For 7.1**: Diff the two files. Identify all imports of `ChartPresenter`. Redirect to `ChartDisplayComponent`. Delete.
2. **For 7.2-7.3**: Diff each pair. Grep for import paths. Delete the unused copy.
3. **For 7.4**: List all UIStateManager methods. Compare with direct access keys. Add missing methods.
4. **For 7.5**: Audit all settings components. List shared patterns. Design base class.
5. **For 7.6**: Check if functions are already called from outside pivot_config.py (they may not be yet). Add shared location.
6. **For 7.7**: Diff caching patterns in mean.py and normalize.py. Extract decorator.
7. **For 7.8**: Identify the shared logic in both connectors. Design extraction.

---

## What We Expect to Find

- **7.1**: ChartPresenter is fully replaceable by ChartDisplayComponent. ~260 lines removed.
- **7.2-7.3**: One copy is imported, the other is dead. ~600 lines removed.
- **7.4**: UIStateManager needs ~5-6 new methods for data manager state.
- **7.5**: Base class reduces ~200 lines across 11 settings components.
- **7.7**: Decorator reduces ~80 lines across mean.py and normalize.py.
- **7.8**: This is the largest win — ~300+ lines of shared logic extracted.

---

## Outcome

**Status**: INVESTIGATION COMPLETE

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 7.1 Chart duplication | **CONFIRMED** — ~240 lines of identical code. ChartDisplayComponent is canonical (imported by render_controller.py:30). ChartPresenter is unused (exported from presenters/__init__.py but never imported). Identical methods: render_refresh_controls, render_engine_selector, render_plotly_chart, render_matplotlib_chart, render_error. | HIGH | Delete ChartPresenter. ~240 lines removed. |
| 7.2 split_apply_config dup | **CONFIRMED** — Byte-for-byte identical (361 lines). pages/ui version imported by shaper_config.py:1. components version is canonical location. | HIGH | Delete pages/ui copy. Update shaper_config.py import to use components version. ~361 lines removed. |
| 7.3 data_manager dups | **NOT A BUG** — Files in `pages/ui/data_managers/impl/` are different classes (SeedsReducerManager, OutlierRemoverManager extending DataManager). Different from component versions in responsibility and structure. No duplication. | N/A | No action needed. |
| 7.4 UIStateManager | **CONFIRMED** — 10 direct `st.session_state[` bypasses in: render_controller.py:270, split_apply_config.py:262/264, seeds_reducer.py:118/120, outlier_remover.py:59/66, base_ui.py:242/244, manage_plots.py. UIStateManager internally handles 50+ accesses properly. | LOW | Create _WidgetUIState namespace for widget-level transient state. |
| 7.5 SettingsComponentBase | **NOT NEEDED** — All settings components follow identical pattern (constructor, render, widget keys, config assembly) but this is intentional clean architecture. Pattern is consistent, not repetitive. No base class needed. | N/A | No action needed. |
| 7.6 Shaper UI utils | **CONFIRMED** — `extract_with_pattern()` defined in BOTH pivot.py (core) and pivot_config.py (UI). ~30 lines of near-identical code. UI version should import from core. `detect_common_pattern()` is UI-only, stays in pivot_config.py. | MEDIUM | Import `extract_with_pattern` from core in pivot_config.py. Remove duplicate. ~30 lines removed. |
| 7.7 Caching duplication | **NOT A BUG** — Both mean.py and normalize.py use `@cached` decorator (properly factored in performance.py). Fingerprint logic similar but intentionally different (different cache sizes: 16 vs 32, different params). Acceptable pattern reuse. | N/A | No action needed. Pattern reuse is acceptable. |
| 7.8 Connector duplication | **NOT A BUG** — Plotly and Matplotlib connectors implement same config spec (LegendConfig, DataLabelConfig) but with engine-specific APIs (fig.update_layout vs ax.set_*). Proper separation of concerns, not duplication. | N/A | No action needed. Correct architecture. |

### Corrections from Initial Hypotheses
- **7.3 was NOT duplication** — Files in different directories have different classes/responsibilities
- **7.5 was consistent architecture** — Settings components follow clean pattern, no base class needed
- **7.7 was intentional pattern reuse** — Caching decorator properly factored
- **7.8 was proper architecture** — Engine-specific rendering is not duplication

### Critical Findings Summary (items requiring fix)
1. **ChartPresenter is dead duplicate** — HIGH: ~240 lines of unused identical code
2. **split_apply_config.py duplicate** — HIGH: ~361 lines byte-for-byte identical
3. **extract_with_pattern in two places** — MEDIUM: Core/UI duplication of utility function

### Estimated Implementation Impact
- **~631 lines removable** from confirmed duplications (7.1 + 7.2 + 7.6)
- **0 production behavior change** — all removed items are unused duplicates
