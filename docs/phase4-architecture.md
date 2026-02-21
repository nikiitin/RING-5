# Phase 4 — Declarative Widget System (UI Simplification)

> **Note (Phase B update):** Widget definitions and `WidgetRenderer` were moved
> from `src/core/visualization/widgets/` to `src/web/rendering/widgets/` and
> `ConfigBridge` was removed during Phase B5/B8. The declarative widget system
> remains functional at its new location.

## Overview

Phase 4 aligns the declarative widget definitions with production defaults
and wires the first section (`_render_legend_sizing`) through `WidgetRenderer`,
proving the migration path for replacing hand-coded Streamlit widgets.

## Architecture After Phase 4

```text
┌─────────────────────────────────────────────────────────────────┐
│  BaseStyleUI                                                     │
│    self._renderer = WidgetRenderer(key_prefix="p{id}_")          │
│                                                                  │
│  Declarative sections (via WidgetRenderer):                      │
│    ├─ _render_legend_sizing() → LEGEND_SIZING                    │
│    └─ (future) more sections as column-layout support is added   │
│                                                                  │
│  Hand-coded sections (kept for complex UX):                      │
│    ├─ render_layout_options()  — 2-column layout                 │
│    ├─ _render_backgrounds_section() — conditional rendering      │
│    ├─ _render_legend_position() — 2-column layout                │
│    ├─ _render_legend_appearance() — conditional + columns        │
│    ├─ _render_typography_section() — 2-column layout             │
│    ├─ render_data_labels_ui() — conditional rendering            │
│    └─ render_series_colors_ui() — dynamic per-series widgets     │
└─────────────────────────────────────────────────────────────────┘
```

## What Changed

### Step 29: Aligned standard section defaults

All standard sections now match `base_ui.py` production defaults:

- `LAYOUT_DIMENSIONS`: 800×500 (was 700×400), range 400-1600 (was 200-2000)
- `LAYOUT_MARGINS`: 100/100/80/120 (was 100/30/40/80), max 1000 (was 400)
- `TYPOGRAPHY`: 18/14/14/12/12 (was 14/12/12/8/8), added standoff/vshift/colors
- `BACKGROUNDS`: reordered transparent-first to match base_ui flow
- `AXIS_COLORS`: key `axis_color` (was `axis_line_color`) to match codebase
- Tick font colors moved from AXIS_COLORS to TYPOGRAPHY (grouped with other tick config)

### Step 30: New standard sections

Added 4 new sections, split LEGEND into 3 granular sub-sections:

| Section             | Widgets | Purpose                                               |
| ------------------- | ------- | ----------------------------------------------------- |
| `LEGEND_POSITION`   | 4       | Orientation, columns, width, valign                   |
| `LEGEND_APPEARANCE` | 8       | Transparent, bg, border, font, title font             |
| `LEGEND_SIZING`     | 3       | Item sizing, width, spacing                           |
| `DATA_LABELS`       | 11      | Show values, color mode, position, format, thresholds |
| `LAYOUT_MARGINS`    | 6       | +automargin checkbox (was 5)                          |

`LEGEND` remains as a convenience aggregate (`*POSITION + *APPEARANCE + *SIZING`).
`STANDARD_SECTIONS` uses granular sections to avoid duplicate `spec_path` entries.

### Step 31: Wire into base_ui.py

- Added `self._renderer = WidgetRenderer(...)` to `BaseStyleUI.__init__`
- Replaced `_render_legend_sizing()`: 37 → 12 lines, fully declarative
- Import: `from src.core.visualization.widgets import WidgetRenderer, LEGEND_SIZING`

### Step 32: Tests and code health

- Created `test_phase4_sections.py` with 21 tests:
  - Default alignment (9 tests): verify all sections match base_ui defaults
  - Section integrity (8 tests): no duplicates, valid options, ranges, coverage
  - Widget types (4 tests): correct DEF subclass for each use case
- mypy strict: 0 errors on all new/modified code
- No dead code, no regressions

## Migration Path for Remaining Sections

### Column Layout Support (Tier 2)

Add `columns: int = 1` to `WidgetSection` and teach `WidgetRenderer`
to distribute widgets across `st.columns()`. This enables:

- `_render_typography_section` → `TYPOGRAPHY` with `columns=2`
- `_render_legend_position` → `LEGEND_POSITION` with `columns=2`

### Conditional Visibility (Tier 2)

Add `visible_when: Optional[Callable[[Dict], bool]]` to `WidgetDef`.
`WidgetRenderer` skips rendering when predicate returns False. Enables:

- `_render_backgrounds_section` → transparent_bg hides color pickers
- `render_data_labels_ui` → color_mode/logic conditionals

### Dynamic/Repeater Sections (Tier 3)

Add `RepeaterWidgetSection` that stamps N copies based on data. Enables:

- `render_series_colors_ui` → per-series color pickers
- `render_series_renaming_ui` → per-series text inputs
- Subclass hooks (bar patterns, line markers)

## Test Summary

| Suite      | Tests  | Status   |
| ---------- | ------ | -------- |
| Full suite | 3326   | ✅ pass  |
| Skipped    | 2      | —        |
| Coverage   | 90.37% | ≥ 90% ✅ |
