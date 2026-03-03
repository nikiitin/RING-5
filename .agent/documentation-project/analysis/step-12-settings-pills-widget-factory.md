# Step 12 -- Settings, Pills & Widget Factory Analysis

> **Objective**: Document the settings UI system, pill-based navigation,
> and how user interactions map to `PlotConfig` modifications through
> the widget factory, settings components, and style UI layers.

---

## 1. Executive Summary

The RING-5 Unified Engine v2 settings system is a **three-layer architecture** that
translates user interactions into configuration dictionaries consumed by the rendering
pipeline:

| Layer | Role | Key Module |
|-------|------|------------|
| **Pills Navigation** | Top-level section routing via `st.pills` (horizontal pill buttons) | `settings_pills.py` |
| **Settings Components** | Per-section widget rendering; each returns a `PlotConfig` dict | `src/web/components/plotting/settings/*.py` |
| **Widget Factory** | Standardised wrappers around `st.*` widgets with config-based defaults | `widget_factory.py` |

A supplementary **declarative widget system** (`WidgetDef` / `WidgetRenderer`) provides
data-driven widget definitions with `spec_path` mappings to `FigureConfig` fields,
though the hand-coded settings components remain the primary rendering path.

The flow is:

```
RenderController
  -> st.toggle("Show advanced settings")
  -> render_settings_pills(show_advanced)       # returns section key
  -> plot.render_settings_section(section, ...)  # PlotConfigUIMixin dispatcher
     -> <SectionComponent>.render(saved_config)  # returns PlotConfig dict
        -> widget_factory.select_option / numeric_input / ...
           -> st.selectbox / st.number_input / ...
  -> current_config.update(extra_config)
```

The system provides **7 settings sections** (3 basic, 4 advanced), **11 settings
component classes**, **5 widget factory functions**, and approximately **120+ distinct
config keys** that flow downstream into the rendering pipeline.

---

## 2. Settings Architecture Overview

### 2.1 Progressive Disclosure

The settings UI implements a two-tier progressive disclosure pattern:

1. **Basic/Advanced toggle** -- An `st.toggle("Show advanced settings")` in the
   render controller controls which pills are visible. By default only 3 basic
   pills appear; toggling reveals 4 additional advanced pills.

2. **Per-section disclosure** -- Individual sections use conditional rendering
   (e.g., Data Labels hides formatting widgets until "Show Values" is enabled;
   Y-axis grid dash only appears when tick marks are enabled).

### 2.2 Component-Only Architecture

All settings panels follow the **component-only architecture** (principles P1, P9):

- Each panel is a standalone class in `src/web/components/plotting/settings/`.
- Each class takes `(plot_id, plot_type)` at construction time.
- Each class has a `render(saved_config, ...) -> PlotConfig` method.
- Components are decoupled from `BasePlot` via the `PlotConfigUIMixin` dispatcher.
- Plot-type-specific logic is injected via `Protocol`-typed callables (e.g.,
  `SpecificOptionsRenderer`, `OrderingRenderer`).

### 2.3 Dual Widget Systems

The codebase contains two co-existing widget abstraction layers:

| System | Files | Status |
|--------|-------|--------|
| **Widget Factory** (imperative) | `widget_factory.py` | Primary -- used by all settings components |
| **WidgetDef/WidgetRenderer** (declarative) | `widget_def.py`, `widget_renderer.py` | Supplementary -- used by `BaseStyleUI._renderer` for some legacy paths |

The Widget Factory provides 5 thin wrappers (`select_option`, `numeric_input`,
`color_picker`, `toggle`, `slider`) around Streamlit widgets. The declarative system
provides typed dataclass definitions (`NumberWidgetDef`, `SliderWidgetDef`, etc.) with
a `WidgetRenderer` that dispatches to `st.*` calls based on type.

---

## 3. File Inventory

### 3.1 Settings Pills Navigation

| File | Lines | Purpose |
|------|-------|---------|
| `src/web/pages/ui/plotting/settings_pills.py` | 125 | `SettingsSection` dataclass, `SETTINGS_SECTIONS` list, `render_settings_pills()`, `render_preset_pills()` |

### 3.2 Widget Factory

| File | Lines | Purpose |
|------|-------|---------|
| `src/web/components/plotting/settings/widget_factory.py` | 157 | 5 factory functions: `select_option`, `numeric_input`, `color_picker`, `toggle`, `slider` |

### 3.3 Settings Component Classes

| File | Class | Pill Label | Lines |
|------|-------|------------|-------|
| `src/web/components/plotting/settings/__init__.py` | (re-exports) | -- | 44 |
| `src/web/components/plotting/settings/layout_settings.py` | `LayoutSettingsComponent` | Layout | 117 |
| `src/web/components/plotting/settings/typography_settings.py` | `TypographySettingsComponent` | Typography | 147 |
| `src/web/components/plotting/settings/legend_settings.py` | `LegendSettingsComponent` | Legends | 582 |
| `src/web/components/plotting/settings/axes_settings.py` | `AxesSettingsComponent` | Axes | 524 |
| `src/web/components/plotting/settings/data_labels_settings.py` | `DataLabelsSettingsComponent` | Data Labels | 262 |
| `src/web/components/plotting/settings/colors_settings.py` | `ColorsSettingsComponent` | Colors | 425 |
| `src/web/components/plotting/settings/advanced_settings.py` | `AdvancedSettingsComponent` | Advanced | 170 |
| `src/web/components/plotting/settings/engine_settings.py` | `EngineSettingsComponent` | (sub-section of Advanced) | 82 |
| `src/web/components/plotting/settings/ordering_settings.py` | `OrderingSettingsComponent` | (sub-section of Axes) | 186 |
| `src/web/components/plotting/settings/reference_line_settings.py` | `ReferenceLineSettingsComponent` | (sub-section of Advanced) | 126 |
| `src/web/components/plotting/settings/shapes_settings.py` | `ShapesSettingsComponent` | (sub-section of Advanced) | 144 |

### 3.4 Style UI Layer (Legacy + Bridge)

| File | Class | Purpose |
|------|-------|---------|
| `src/web/pages/ui/plotting/styles/factory.py` | `StyleUIFactory` | Dispatches to plot-type-specific `BaseStyleUI` subclass |
| `src/web/pages/ui/plotting/styles/base_ui.py` | `BaseStyleUI` | Base style manager; delegates to components; provides series color rendering |
| `src/web/pages/ui/plotting/styles/bar_ui.py` | `BarStyleUI` | Adds bar pattern selector per series |
| `src/web/pages/ui/plotting/styles/line_ui.py` | `LineStyleUI`, `ScatterStyleUI` | Adds marker symbol, marker size, line width per series |

### 3.5 Declarative Widget System

| File | Purpose |
|------|---------|
| `src/web/rendering/widgets/__init__.py` | Re-exports all `WidgetDef` types, sections, and `WidgetRenderer` |
| `src/web/rendering/widgets/widget_def.py` | `WidgetDef` base + 6 subclasses + 15 pre-defined `WidgetSection` constants |
| `src/web/rendering/widgets/widget_renderer.py` | `WidgetRenderer` class -- section-to-Streamlit generator |

### 3.6 Supporting Files

| File | Purpose |
|------|---------|
| `src/web/pages/ui/plotting/plot_config_ui.py` | `PlotConfigUIMixin` -- pills dispatcher (`render_settings_section`) |
| `src/web/pages/ui/plotting/base_plot.py` | `BasePlot` -- inherits `PlotConfigUIMixin`; owns `_style_ui` |
| `src/web/models/plot_models.py` | `PlotConfig = dict[str, Any]`; `PlotDisplayConfig` TypedDict (canonical schema) |
| `src/web/controllers/plot/render_controller.py` | Calls `render_settings_pills` + `render_settings_section` in rendering flow |
| `src/web/components/plotting/config/dual_axis_settings.py` | Dual-axis grid, typography, legend, dot settings |
| `src/web/pages/ui/plotting/styles/colors.py` | `to_hex()` color conversion utility |

### 3.7 Tests

| File | Test Classes | Coverage |
|------|-------------|----------|
| `tests/ui_logic/test_settings_pills.py` | `TestRenderSettingsPills`, `TestSectionDispatch`, `TestLegendSubPills`, `TestAxesSubPills`, `TestPresetPills` | Steps 24-26, 29, 31 |
| `tests/ui_logic/test_settings_pills_e2e.py` | 9 test classes, ~50 test methods | Issues #1-11: typography isolation, axis lines, numbered X-axis, group labels, legend sizing, data labels disclosure, ordering |
| `tests/ui_logic/test_engine_specific_controls.py` | `TestEngineSpecificControls` | Step 30: engine-specific widget visibility |

---

## 4. Settings Section Catalog

### 4.1 Layout (`LayoutSettingsComponent`)

- **File**: `src/web/components/plotting/settings/layout_settings.py:17`
- **Pill Label**: `:material/dashboard: Layout`
- **Pill Key**: `"layout"`
- **Advanced**: No (always visible)
- **Function**: `LayoutSettingsComponent(plot_id, plot_type).render(saved_config) -> PlotConfig`

**Widgets:**

| Widget | Streamlit Type | Widget Key | Default | Config Key | Description |
|--------|---------------|------------|---------|------------|-------------|
| Document Size Preset | `st.selectbox` | `col_preset_{pid}` | `"Double Column (~7.0in)"` | `document_width_preset` | Preset: Single Column (3.5in), Double Column (7.0in), Custom |
| Width (inches) | `st.number_input` | `wi_{pid}` | 7.0 | `width_inches` | Only editable when preset is "Custom"; otherwise disabled |
| Height (inches) | `st.number_input` | `hi_{pid}` | 3.5 | `height_inches` | Always editable, range 1.0-30.0 |

**Derived Config Keys** (computed, no widget):

| Config Key | Derivation |
|------------|------------|
| `width` | `int(width_inches * 100)` -- px for Plotly preview |
| `height` | `int(height_inches * 100)` |
| `margin_l` | Hard-coded `0` (auto-margin mode) |
| `margin_r` | Hard-coded `0` |
| `margin_t` | Hard-coded `0` |
| `margin_b` | Hard-coded `0` |
| `margin_pad` | Hard-coded `0` |
| `automargin` | Hard-coded `True` |

**Conditional Widgets**: Width input disabled when preset is not "Custom".

**Engine-Specific**: None.

---

### 4.2 Typography (`TypographySettingsComponent`)

- **File**: `src/web/components/plotting/settings/typography_settings.py:25`
- **Pill Label**: `:material/text_fields: Typography`
- **Pill Key**: `"typography"`
- **Advanced**: No (always visible)
- **Function**: `TypographySettingsComponent(plot_id, plot_type).render(saved_config, key_prefix="theme_") -> PlotConfig`

**Widgets:**

| Widget | Streamlit Type | Widget Key | Default | Config Key | Description |
|--------|---------------|------------|---------|------------|-------------|
| Plot Title Font Size | `numeric_input` (factory) | `{prefix}title_sz_{pid}` | 18 | `title_font_size` | Range 8-100 |
| X-Axis Title Font Size | `numeric_input` | `{prefix}xaxis_title_sz_{pid}` | 14 | `xaxis_title_font_size` | Range 8-100 |
| Y-Axis Title Font Size | `numeric_input` | `{prefix}yaxis_title_sz_{pid}` | 14 | `yaxis_title_font_size` | Range 8-100 |
| X-Axis Label (Tick) Size | `numeric_input` | `{prefix}xaxis_tick_sz_{pid}` | 12 | `xaxis_tickfont_size` | Range 8-100 |
| X-Axis Label Color | `color_picker` (factory) | `{prefix}xaxis_tick_col_{pid}` | `#444444` | `xaxis_tickfont_color` | Hex color |
| Y-Axis Label (Tick) Size | `numeric_input` | `{prefix}yaxis_tick_sz_{pid}` | 12 | `yaxis_tickfont_size` | Range 8-100 |
| Y-Axis Label Color | `color_picker` | `{prefix}yaxis_tick_col_{pid}` | `#444444` | `yaxis_tickfont_color` | Hex color |

**Layout**: Two columns -- left column has title font sizes, right column has tick label sizes and colors.

**Strict Key Isolation**: This section outputs exactly 7 keys. Tests in `TestTypographyNoAxisLeak` verify that no axis/grid keys leak into the typography output.

**Conditional Widgets**: None.

**Engine-Specific**: None.

---

### 4.3 Legends (`LegendSettingsComponent`)

- **File**: `src/web/components/plotting/settings/legend_settings.py:46`
- **Pill Label**: `:material/legend_toggle: Legends`
- **Pill Key**: `"legends"`
- **Advanced**: No (always visible)
- **Function**: `LegendSettingsComponent(plot_id, plot_type).render(saved_config, has_secondary, has_tertiary) -> PlotConfig`

**Sub-Navigation**: Nested `st.pills` with primary/secondary/tertiary tabs.

| Sub-Pill | Visible When | Widget Key Prefix | Config Key Prefix |
|----------|-------------|-------------------|-------------------|
| Primary | Always | `theme_` | `legend_` |
| Secondary | `has_secondary=True` (dual-axis or supports secondary) | `legend2_` | `legend2_` |
| Tertiary | `has_tertiary=True` (dual-axis + numbered X-axis) | `legend3_` | `legend3_` |

**Per-Legend Widgets** (each prefixed per level):

| Sub-Section | Widget | Type | Key Pattern | Default | Config Key Pattern |
|------------|--------|------|-------------|---------|-------------------|
| **Position** | X Position | `numeric_input` | `{kp}leg_x_{pid}` | 1.02 (primary), 1.0 (others) | `{cp}x` |
| | Y Position | `numeric_input` | `{kp}leg_y_{pid}` | 1.0 | `{cp}y` |
| | Orientation | `select_option` | `{kp}leg_orient_{pid}` | `"vertical"` | `{cp}orientation` |
| **Appearance** | Transparent Background | `toggle` | `{kp}trans_leg_{pid}` | `False` | `{cp}transparent` |
| | Background Color | `st.color_picker` | `{kp}leg_bg_col_{pid}` | `#ffffff` | `{cp}bgcolor` |
| | Border Color | `color_picker` | `{kp}leg_bord_col_{pid}` | `#000000` | `{cp}border_color` |
| | Border Width | `numeric_input` | `{kp}leg_bord_wd_{pid}` | 0 | `{cp}border_width` |
| | Text Color | `color_picker` | `{kp}leg_font_col_{pid}` | `#000000` | `{cp}font_color` |
| | Font Size | `numeric_input` | `{kp}leg_font_sz_{pid}` | 12 | `{cp}font_size` |
| | Legend Title | `st.text_input` | `{kp}leg_title_txt_{pid}` | `""` | `{cp}title` |
| | Title Color | `color_picker` | `{kp}leg_title_col_{pid}` | `#000000` | `{cp}title_font_color` |
| | Title Size | `numeric_input` | `{kp}leg_title_sz_{pid}` | 14 | `{cp}title_font_size` |
| **Sizing** | Columns | `numeric_input` | `{kp}leg_ncols_{pid}` | 0 | `{cp}ncols` |
| | Item Spacing (px) | `numeric_input` | `{kp}leg_tracegap_{pid}` | 10 | `{cp}tracegroupgap` |
| | Column Spacing | `numeric_input` | `{kp}leg_colspace_{pid}` | 0.5 | `{cp}column_spacing` |
| | Stripe Length (px) | `numeric_input` | `{kp}leg_itemwidth_{pid}` | 30 | `{cp}itemwidth` |
| | Stripe-Text Gap | `numeric_input` | `{kp}leg_htpad_{pid}` | 0.3 | `{cp}handletextpad` |

Where `{kp}` = key prefix (`theme_`, `legend2_`, `legend3_`) and `{cp}` = config prefix (`legend_`, `legend2_`, `legend3_`).

**Heatmap Variant**: When `plot_type == "heatmap"`, the appearance section changes to show only colorbar title controls (title text via `st.text_area`, title font color, title font size). Additional colorbar-specific controls are rendered via `_render_colorbar_settings()`:

| Widget | Type | Config Key Pattern | Default |
|--------|------|-------------------|---------|
| Shared Colorbar | `toggle` | `{cp}colorbar_shared` | `True` |
| Range Mode | `st.radio` | `{cp}colorbar_range_mode` | `"auto"` |
| Min | `numeric_input` | `{cp}colorbar_zmin` | 0.0 (only when manual) |
| Max | `numeric_input` | `{cp}colorbar_zmax` | 100.0 (only when manual) |
| Tick Count | `numeric_input` | `{cp}colorbar_nticks` | 5 |
| Tick Decimals | `numeric_input` | `{cp}colorbar_tick_decimals` | 2 |
| Tick Rotation | `numeric_input` | `{cp}colorbar_tick_angle` | 0.0 |
| Tick Side | `select_option` | `{cp}colorbar_tick_side` | `"right"` |

**Config Preservation**: When switching between legend pills, inactive pills' config values are preserved from `saved_config` to prevent data loss.

---

### 4.4 Axes (`AxesSettingsComponent`)

- **File**: `src/web/components/plotting/settings/axes_settings.py:72`
- **Pill Label**: `:material/straighten: Axes`
- **Pill Key**: `"axes"`
- **Advanced**: Yes (hidden by default)
- **Function**: `AxesSettingsComponent(plot_id, plot_type).render(saved_config, data, has_dual_axis, show_group_labels, render_specific_fn, render_ordering_fn) -> PlotConfig`

**Sub-Navigation**: Nested `st.pills` with X / Y-Left / Y-Right / Group Labels tabs.

| Sub-Pill | Visible When | Key | Icon |
|----------|-------------|-----|------|
| X-Axis | Always | `"x"` | `:material/straighten:` |
| Y-Left | Always | `"y_left"` | `:material/straighten:` |
| Y-Right | `has_dual_axis=True` | `"y_right"` | `:material/straighten:` |
| Group Labels | `show_group_labels=True` (grouped stacked bar) | `"group"` | `:material/label:` |

#### 4.4.1 X-Axis Sub-Pill

| Widget | Type | Widget Key | Default | Config Key |
|--------|------|------------|---------|------------|
| Show Grid | `toggle` | `show_x_grid_{pid}` | `False` | `show_x_grid` |
| X-axis Label Rotation | `slider` | `xaxis_angle_{pid}` | -45 | `xaxis_tickangle` |
| Show X-Axis Tick Marks | `toggle` | `x_show_ticks_{pid}` | `False` | `show_xtick_marks` |
| X-Axis Tick Side | `select_option` | `x_tick_side_{pid}` | `"bottom"` | `xaxis_tick_side` |
| X-Axis Grid Dash Style | `select_option` | `x_tickdash_{pid}` | `"solid"` | `xtick_dash` |
| X-Axis Tick Label Distance (px) | `numeric_input` | `xtick_pad_{pid}` | 5.0 | `xtick_pad` |
| Bottom Axis Line Width (px) | `numeric_input` | `x_axis_line_width_{pid}` | 1.0 | `x_axis_line_width` |
| Bottom Axis Line Color | `color_picker` | `x_axis_line_color_{pid}` | `#444444` | `x_axis_line_color` |
| Top Axis Line Width (px) | `numeric_input` | `top_axis_line_width_{pid}` | 0.0 | `top_axis_line_width` |
| Top Axis Line Color | `color_picker` | `top_axis_line_color_{pid}` | `#444444` | `top_axis_line_color` |
| Use Numbered X-Axis | `toggle` | `numbered_xaxis_{pid}` | `False` | `numbered_xaxis` |
| Numbered X-Axis Modes | `st.pills` (multi) | `numbered_modes_{pid}` | `[]` | `numbered_xaxis_modes` |

**Derived Config Keys** (from numbered modes):
- `show_numbered_ticks` -- `True` if `"Numbers"` in modes
- `show_numbered_legend` -- `True` if `"Number legend"` in modes

**Conditional Widgets**:
- Grid Dash Style only appears when tick marks are enabled.
- Numbered X-axis modes multiselect pills always render but `numbered_xaxis` boolean is derived from mode count.

**Injected Callbacks**:
- `render_specific_fn(saved_config, data) -> PlotConfig` -- bar gap, bar group gap, bar border width
- `render_ordering_fn(saved_config, data, config) -> None` -- reorder/rename X-axis labels, groups, legend items

#### 4.4.2 Y-Left / Y-Right Sub-Pills

Rendered by `_render_y_axis_settings(saved_config, config, prefix)` where `prefix=""` for Y-Left and `prefix="y2"` for Y-Right.

| Widget | Type | Widget Key | Default | Config Key |
|--------|------|------------|---------|------------|
| Show Grid | `toggle` | `{pfx}show_y_grid_{pid}` | `True`(L)/`False`(R) | `{pfx}show_y_grid` |
| Y-axis Label Rotation | `slider` | `{pfx}yaxis_angle_{pid}` | 0 | `yaxis_tickangle` |
| Y Step Size (0=auto) | `st.number_input` | `{pfx}ydtick_{pid}` | 0.0 | `{pfx}yaxis_dtick` |
| Show Y-Axis Tick Marks | `toggle` | `{pfx}y_show_ticks_{pid}` | `False` | `show_ytick_marks` |
| Y-Axis Tick Side | `select_option` | `{pfx}y_tick_side_{pid}` | `"left"` | `yaxis_tick_side` |
| Y-Axis Grid Dash Style | `select_option` | `{pfx}y_tickdash_{pid}` | `"solid"` | `ytick_dash` |
| Y-Axis Title Standoff | `slider` | `{pfx}yaxis_title_standoff_{pid}` | -1 | `yaxis_title_standoff` |
| Y-Axis Title Vertical Shift | `slider` | `{pfx}yaxis_title_vshift_{pid}` | 0 | `yaxis_title_vshift` |
| Y-Axis Line Width (px) | `numeric_input` | `{pfx}y_axis_line_width_{pid}` | 1.0 | `{pfx}y_axis_line_width` |
| Y-Axis Line Color | `color_picker` | `{pfx}y_axis_line_color_{pid}` | `#444444` | `{pfx}y_axis_line_color` |
| Right Axis Line Width (px) | `numeric_input` | `right_axis_line_width_{pid}` | 0.0 | `right_axis_line_width` |
| Right Axis Line Color | `color_picker` | `right_axis_line_color_{pid}` | `#444444` | `right_axis_line_color` |

Note: Right Axis Line Width/Color only rendered for the primary Y-axis (`prefix=""`).

**Engine-Specific**: Y-Axis Title Vertical Shift help text notes "Matplotlib only -- Plotly uses standoff."

#### 4.4.3 Group Labels Sub-Pill

Only visible for `grouped_stacked_bar` plot type.

| Widget | Type | Widget Key | Default | Config Key |
|--------|------|------------|---------|------------|
| Label-to-Axis Distance | `numeric_input` | `grp_lbl_dist_{pid}` | -0.15 | `major_label_offset` + `group_label_offset` |
| Alternate Group Labels | `toggle` | `grp_alt_{pid}` | `True` | `group_label_alternate` |
| Alt. Label Row Spacing | `numeric_input` | `grp_alt_sp_{pid}` | 0.05 | `group_label_alt_spacing` |

---

### 4.5 Data Labels (`DataLabelsSettingsComponent`)

- **File**: `src/web/components/plotting/settings/data_labels_settings.py:24`
- **Pill Label**: `:material/label: Data Labels`
- **Pill Key**: `"data_labels"`
- **Advanced**: Yes (hidden by default)
- **Function**: `DataLabelsSettingsComponent(plot_id, plot_type).render(saved_config, key_prefix="theme_") -> PlotConfig`

**Progressive Disclosure**: When `show_values=False`, the component returns default/saved values
for all keys without rendering any formatting widgets (no `selectbox`/`slider`/`number_input`
calls). Verified by `TestDataLabelsProgressiveDisclosure`.

| Widget | Type | Widget Key | Default | Config Key | Condition |
|--------|------|------------|---------|------------|-----------|
| Show Values | `toggle` | `{kp}show_val_{pid}` | `False` (bar), `True` (heatmap) | `show_values` | Always |
| Value Color Mode | `select_option` | `{kp}tx_col_mode_{pid}` | `"auto"` (bar), `"contrast"` (heatmap) | `text_color_mode` | `show_values=True` |
| Value Color | `color_picker` | `{kp}tx_col_{pid}` | `#000000` | `text_color` | `text_color_mode=="custom"` |
| Value Font Size | `numeric_input` | `{kp}tx_font_sz_{pid}` | 10 | `text_font_size` | `show_values=True` |
| Value Rotation | `slider` | `{kp}tx_rot_{pid}` | 0 | `text_rotation` | `show_values=True` and not heatmap |
| Value Position | `select_option` | `{kp}tx_pos_{pid}` | `"auto"` | `text_position` | `show_values=True` and not heatmap |
| Value Anchor | `select_option` | `{kp}tx_anc_{pid}` | `"auto"` | `text_anchor` | `show_values=True` and not heatmap |
| Value Number Format | `st.text_input` | `{kp}tx_fmt_{pid}` | `".2f"` (bar), `".4g"` (heatmap) | `text_format` | `show_values=True` |
| Display Logic | `select_option` | `{kp}tx_logic_{pid}` | `"all"` | `text_display_logic` | `show_values=True` |
| Threshold Value | `numeric_input` | `{kp}tx_thresh_{pid}` | 0.0 | `text_threshold` | `text_display_logic != "all"` |
| Size Constraint | `select_option` | `{kp}tx_const_{pid}` | `"none"` | `text_constraint` | `show_values=True` and not heatmap |

**Heatmap-Specific Totals** (only when `plot_type == "heatmap"` and `show_values=True`):

| Widget | Type | Widget Key | Default | Config Key |
|--------|------|------------|---------|------------|
| Show Totals | `toggle` | `{kp}hm_show_totals_{pid}` | `False` | `show_totals` |
| Position | `select_option` | `{kp}hm_totals_pos_{pid}` | `"right"` | `totals_position` |
| Totals Aggregation | `select_option` | `{kp}hm_totals_agg_{pid}` | `"mean"` | `totals_aggregation` |

---

### 4.6 Colors (`ColorsSettingsComponent`)

- **File**: `src/web/components/plotting/settings/colors_settings.py:34`
- **Pill Label**: `:material/palette: Colors`
- **Pill Key**: `"colors"`
- **Advanced**: Yes (hidden by default)
- **Function**: `ColorsSettingsComponent(plot_id, plot_type).render(saved_config, data, items) -> PlotConfig`

**Sub-Sections:**

#### 4.6.1 Palette Selector

| Widget | Type | Widget Key | Default | Config Key |
|--------|------|------------|---------|------------|
| Palette | `select_option` (factory) | `palette_select_{pid}` | `"wong"` | `color_palette` |

Palette names come from `get_palette_names()` via the core `PALETTE_REGISTRY`. Names marked
as colorblind-safe get a checkmark prefix in the `format_func`. A color swatch preview is
rendered as inline HTML (`unsafe_allow_html=True`).

#### 4.6.2 Heatmap Colorscale (conditional)

| Widget | Type | Widget Key | Default | Config Key | Condition |
|--------|------|------------|---------|------------|-----------|
| Reverse Color Scale | `st.checkbox` | `hm_rev_cs_{pid}` | `False` | `reverse_colorscale` | `plot_type == "heatmap"` |

#### 4.6.3 Series Color Overrides

For each unique series value (discovered from data or explicit `items` list):

| Widget | Type | Widget Key | Config Key |
|--------|------|------------|------------|
| Original Color (disabled) | `st.color_picker` | `{kp}orig_col_{pid}_{hash}_{palette}` | (display only) |
| Custom Color | `st.color_picker` | `{kp}color_{pid}_{hash}_{palette}` | `series_styles[val].color` |
| Override | `st.checkbox` | `{kp}use_col_{pid}_{hash}` | `series_styles[val].use_color` |
| Rewind (reset) | `st.button` | `{kp}rst_{pid}_{hash}` | Resets color and override |

Widget keys include a content hash (`md5[:8]`) to avoid conflicts across dynamic series items.
The palette name is included in the picker key so Streamlit resets the widget value when the
user changes the palette.

**Per-Series Visuals** (via `StyleUIFactory` subclasses):

| Plot Type | Extra Widget | Type | Key Pattern | Config Key |
|-----------|-------------|------|-------------|------------|
| Bar | Pattern | `st.selectbox` | `{kp}pat_{pid}_{hash}` | `series_styles[val].pattern` |
| Line | Marker Symbol | `st.selectbox` | `{kp}sym_{pid}_{hash}` | `series_styles[val].symbol` |
| Line | Marker Size | `st.number_input` | `{kp}msize_{pid}_{hash}` | `series_styles[val].marker_size` |
| Line | Line Width | `st.number_input` | `{kp}lwidth_{pid}_{hash}` | `series_styles[val].line_width` |

#### 4.6.4 Backgrounds & Grid

| Widget | Type | Widget Key | Default | Config Key |
|--------|------|------------|---------|------------|
| Transparent Background | `toggle` | `{kp}trans_bg_{pid}` | `False` | `transparent_bg` |
| Plot Background | `st.color_picker` | `{kp}bg_plot_{pid}` | `#ffffff` | `plot_bgcolor` |
| Paper (Outer) Background | `st.color_picker` | `{kp}bg_paper_{pid}` | `#ffffff` | `paper_bgcolor` |
| Grid Color | `color_picker` | `{kp}grid_col_{pid}` | `#e5e5e5` | `grid_color` |
| Axis Line/Tick Color | `color_picker` | `{kp}axis_col_{pid}` | `#444444` | `axis_color` |
| Axis Line Width (px) | `numeric_input` | `{kp}axis_lw_{pid}` | 1.0 | `axis_line_width` |
| Enable Bar Stripes | `toggle` | `{kp}stripes_{pid}` | `False` | `enable_stripes` |

**Conditional Widgets**:
- Background color pickers hidden when `transparent_bg=True`.
- Bar Stripes only shown for bar types (excluding `grouped_stacked`).

---

### 4.7 Advanced (`AdvancedSettingsComponent`)

- **File**: `src/web/components/plotting/settings/advanced_settings.py:63`
- **Pill Label**: `:material/settings: Advanced`
- **Pill Key**: `"advanced"`
- **Advanced**: Yes (hidden by default)
- **Function**: `AdvancedSettingsComponent(plot_id, plot_type).render(saved_config, data, render_reference_line_fn, render_shapes_fn, render_engine_fn) -> PlotConfig`

**Widgets:**

| Widget | Type | Widget Key | Default | Config Key |
|--------|------|------------|---------|------------|
| Show Error Bars | `st.checkbox` | `error_bars_{pid}` | `False` | `show_error_bars` |
| Default Download Format | `st.selectbox` | `download_fmt_{pid}` | `"html"` | `download_format` |
| Download Scale | `st.selectbox` | `exp_scale_{pid}` | 1 | `export_scale` |
| Enable Interactive Editing | `st.checkbox` | `editable_{pid}` | `False` | `enable_editable` |

**Injected Sub-Sections** (via Protocol callbacks):

1. **Reference Line** (`ReferenceLineSettingsComponent`):

| Widget | Type | Widget Key | Default | Config Key |
|--------|------|------------|---------|------------|
| Show reference line | `toggle` | `ref_line_enabled_{pid}` | `False` | `reference_line_enabled` |
| Y position | `numeric_input` | `ref_line_y_{pid}` | 1.0 | `reference_line_y` |
| Line color | `color_picker` | `ref_line_color_{pid}` | `#FF0000` | `reference_line_color` |
| Line width | `slider` | `ref_line_width_{pid}` | 1.5 | `reference_line_width` |
| Line style | `select_option` | `ref_line_style_{pid}` | `"dash"` | `reference_line_style` |

Reference line detail widgets only appear when `reference_line_enabled=True` and `data is not None`.

2. **Shapes/Annotations** (`ShapesSettingsComponent`):

| Widget | Type | Widget Key | Config Key |
|--------|------|------------|------------|
| Shape Type | `st.selectbox` | `new_shape_type_{pid}` | `shapes[].type` |
| x0, y0, x1, y1 | `st.text_input` | `s_x0_{pid}`, etc. | `shapes[].x0`, etc. |
| Color | `st.color_picker` | `s_color_{pid}` | `shapes[].line.color` |
| Width | `st.number_input` | `s_width_{pid}` | `shapes[].line.width` |
| Add Shape | `st.button` | `add_shape_{pid}` | Appends to list |
| Delete | `st.button` | `del_shape_{i}_{pid}` | Removes from list |

3. **Engine Controls** (`EngineSettingsComponent`):

| Engine | Widget | Type | Widget Key | Default | Config Key |
|--------|--------|------|------------|---------|------------|
| Plotly | Hover mode | `select_option` | `hovermode_{pid}` | `"x unified"` | `hovermode` |
| Matplotlib | Extra LaTeX preamble | `st.text_area` | `latex_preamble_{pid}` | `""` | `latex_extra_preamble` |
| Matplotlib | TeX system | `select_option` | `tex_system_{pid}` | `"xelatex"` | `tex_system` |

---

### 4.8 Ordering (`OrderingSettingsComponent`)

- **File**: `src/web/components/plotting/settings/ordering_settings.py:17`
- **Not a top-level pill** -- rendered as a sub-section within the Axes X-Axis tab.
- **Function**: `OrderingSettingsComponent(plot_id, plot_type).render(saved_config, data, config) -> None`

Renders up to 6 expandable reorder/rename lists depending on data and config:

| Expander | Condition | Config Keys |
|----------|-----------|-------------|
| Reorder and Rename X-axis Labels | `saved_config["x"]` exists in data | `xaxis_order`, `xaxis_labels` |
| Reorder and Rename Groups | `saved_config["group"]` exists in data | `group_order`, `legend_labels` |
| Reorder and Rename Legend Items | `saved_config["color"]` exists in data | `legend_order`, `legend_labels` |
| Reorder and Rename Stacked Series | `saved_config["y_columns"]` is non-empty | `y_columns`, `series_styles[].name` |
| Reorder and Rename Y-axis Metrics | `saved_config["metric_columns"]` is non-empty (heatmap) | `metric_columns`, `metric_labels` |
| Reorder and Rename Facets | `saved_config["facet_col"]` exists in data | `facet_order`, `facet_labels` |

Each uses the shared `render_reorderable_list` component from `src/web/components/common/reorderable_list.py`.

---

### 4.9 Preset Pills (`render_preset_pills`)

- **File**: `src/web/pages/ui/plotting/settings_pills.py:67`
- **Not a settings section** -- separate pills row above the settings navigation.

Renders preset selector as `st.pills` with options `["none"] + PresetManager.list_presets()`.
Returns the selected preset name or `None`. Presets are loaded from `latex_presets.json`
via `PresetManager`.

---

## 5. Widget Factory Pattern

### 5.1 Imperative Widget Factory (`widget_factory.py`)

**Location**: `src/web/components/plotting/settings/widget_factory.py`

Five standalone functions, each wrapping a single Streamlit widget type:

```python
def select_option(label, options, config, config_key, plot_id, *, widget_key, default, help, format_func) -> str
def numeric_input(label, config, config_key, plot_id, *, widget_key, default, min_value, max_value, step, help, format) -> int | float
def color_picker(label, config, config_key, plot_id, *, widget_key, default) -> str
def toggle(label, config, config_key, plot_id, *, widget_key, default, help) -> bool
def slider(label, config, config_key, plot_id, *, widget_key, default, min_value, max_value, step, help) -> int | float
```

**Key Generation**: `widget_key or f"{config_key}_{plot_id}"` -- ensures uniqueness per plot.

**Default Value Lookup**: `config.get(config_key, default)` -- reads from saved config, falls back to provided default.

**Safe Index Calculation** (selectbox only): `options.index(current) if current in options else 0` -- prevents `ValueError` when saved value is not in current options.

**Type Coercion**: `numeric_input` and `slider` coerce values to `float` or `int` based on the `default` parameter type.

### 5.2 Declarative Widget System (`WidgetDef` / `WidgetRenderer`)

**Location**: `src/web/rendering/widgets/`

**Data Layer** -- Frozen dataclass hierarchy:

```
WidgetDef (base)
  +-- NumberWidgetDef    -> st.number_input
  +-- SliderWidgetDef    -> st.slider
  +-- SelectWidgetDef    -> st.selectbox
  +-- CheckboxWidgetDef  -> st.checkbox
  +-- ColorWidgetDef     -> st.color_picker
  +-- TextWidgetDef      -> st.text_input
```

**Grouping** -- `WidgetSection` groups widgets under a collapsible header:

```python
@dataclass(frozen=True)
class WidgetSection:
    id: str
    label: str
    widgets: tuple[WidgetDef, ...] = ()
    icon: str = ""
    collapsed: bool = True
```

**Pre-Defined Sections** (15 total in `widget_def.py`):

| Constant | ID | Widgets |
|----------|----|---------|
| `LAYOUT_DIMENSIONS` | `dimensions` | `width`, `height` |
| `LAYOUT_MARGINS` | `margins` | `margin_l`, `margin_r`, `margin_t`, `margin_b`, `margin_pad`, `automargin` |
| `TYPOGRAPHY` | `typography` | 10 font size/color widgets |
| `BACKGROUNDS` | `backgrounds` | `transparent_bg`, `plot_bgcolor`, `paper_bgcolor` |
| `AXIS_COLORS` | `axis_colors` | `grid_color`, `axis_color` |
| `LEGEND_POSITION` | `legend_position` | `legend_orientation`, `legend_ncols`, `legend_col_width`, `legend_valign` |
| `LEGEND_APPEARANCE` | `legend_appearance` | 8 appearance widgets |
| `LEGEND_SIZING` | `legend_sizing` | `legend_itemsizing`, `legend_itemwidth`, `legend_tracegroupgap` |
| `LEGEND` | `legend` | Union of position + appearance + sizing |
| `DATA_LABELS` | `data_labels` | 11 data label widgets |
| `AXIS_X` | `axis_x` | `xaxis_tickangle` |
| `AXIS_Y` | `axis_y` | `yaxis_dtick` |
| `AXIS_Y2` | `axis_y2` | `y2axis_dtick` |
| `COLORS_PALETTE` | `colors_palette` | `color_palette` |
| `REFERENCE_LINES` | `reference_lines` | 5 reference line widgets |
| `ADVANCED_SECTION` | `advanced` | 4 advanced widgets |

**Rendering Layer** -- `WidgetRenderer`:

```python
class WidgetRenderer:
    def __init__(self, key_prefix: str = "")
    def render_section(self, section, saved_config, use_expander=True) -> dict[str, Any]
    def render_sections(self, sections, saved_config) -> dict[str, Any]
    def _render_widget(self, widget_def, saved_config) -> Any
```

Each `_render_widget` call dispatches based on `isinstance` checks to the appropriate
`st.*` widget. The key is built as `f"{self._prefix}{config_key}"`.

**spec_path Field**: Widget definitions include an optional `spec_path` mapping
(e.g., `"dimensions.margins.left"`, `"typography.font_size_title"`) bridging flat
config keys to the structured `FigureConfig` model used downstream.

**Current Usage**: `BaseStyleUI.__init__` creates a `WidgetRenderer` instance, but
the hand-coded settings components are the primary rendering path for the pills UI.
The declarative system serves as a reference catalog and is used in some legacy
code paths.

---

## 6. Pill Navigation Pattern

### 6.1 Top-Level Settings Pills

**Data Structure**:

```python
@dataclass(frozen=True)
class SettingsSection:
    key: str         # Machine-readable identifier
    label: str       # Human-readable display name
    icon: str        # Material icon name
    advanced: bool   # Hidden unless advanced mode enabled
```

**Registry**:

```python
SETTINGS_SECTIONS: list[SettingsSection] = [
    # Basic sections -- always visible
    SettingsSection("layout",      "Layout",      "dashboard"),
    SettingsSection("typography",  "Typography",  "text_fields"),
    SettingsSection("legends",     "Legends",     "legend_toggle"),
    # Advanced sections -- hidden by default
    SettingsSection("axes",        "Axes",        "straighten",    advanced=True),
    SettingsSection("data_labels", "Data Labels", "label",         advanced=True),
    SettingsSection("colors",      "Colors",      "palette",       advanced=True),
    SettingsSection("advanced",    "Advanced",    "settings",      advanced=True),
]
```

**Rendering** (`render_settings_pills`):

1. Filter sections: `[s for s in SETTINGS_SECTIONS if not s.advanced or show_advanced]`
2. Build options list: `[s.key for s in visible]`
3. Build label map: `{s.key: f":material/{s.icon}: {s.label}" for s in visible}`
4. Call `st.pills("Settings", options=options, format_func=..., selection_mode="single", key="settings_nav")`
5. Return selected key (string) or `None`.

**Session State Key**: `"settings_nav"` -- single global key for the top-level pills.

### 6.2 Section Dispatch (`render_settings_section` in `PlotConfigUIMixin`)

The `PlotConfigUIMixin.render_settings_section(section, saved_config, data)` method
acts as a router:

```python
if section == "layout":     -> LayoutSettingsComponent(pid, pt).render(saved_config)
if section == "typography": -> TypographySettingsComponent(pid, pt).render(saved_config, key_prefix="theme_")
if section == "legends":    -> LegendSettingsComponent(pid, pt).render(saved_config, has_secondary, has_tertiary)
if section == "axes":       -> AxesSettingsComponent(pid, pt).render(saved_config, data, has_dual_axis, ...)
if section == "data_labels":-> DataLabelsSettingsComponent(pid, pt).render(saved_config, key_prefix="theme_")
if section == "colors":     -> ColorsSettingsComponent(pid, pt).render(saved_config, data=data)
if section == "advanced":   -> AdvancedSettingsComponent(pid, pt).render(saved_config, data, ...)
if section is None:         -> {}
```

Each component is instantiated fresh on every render cycle (no caching).

### 6.3 Nested Pills (Sub-Navigation)

Two settings components use nested `st.pills` for sub-navigation:

| Component | Pills Label | Sub-Options | Key |
|-----------|------------|-------------|-----|
| `AxesSettingsComponent` | `"Axis"` | `x`, `y_left`, `y_right`, `group` | `axis_nav_{pid}` |
| `LegendSettingsComponent` | `"Legend"` | `primary`, `secondary`, `tertiary` | `legend_nav_{pid}` |

These nested pills use `selection_mode="single"` and `default` values to ensure one
sub-section is always active.

### 6.4 Preset Pills

The preset pills are a separate `st.pills` call rendered before the settings pills:

```python
st.pills("Preset", options=["none"] + preset_names,
         format_func=..., selection_mode="single",
         key=f"preset_selector_{plot_id}", default="none")
```

---

## 7. Config Field -> Widget Mapping

### 7.1 Complete Config Key Reference

The following table maps every config key produced by the settings system to its
source component, Streamlit widget type, and default value.

#### Layout Keys

| Config Key | Component | Widget | Default |
|------------|-----------|--------|---------|
| `document_width_preset` | Layout | `st.selectbox` | `"Double Column (~7.0in)"` |
| `width_inches` | Layout | `st.number_input` | 7.0 |
| `height_inches` | Layout | `st.number_input` | 3.5 |
| `width` | Layout | (computed) | 700 |
| `height` | Layout | (computed) | 350 |
| `margin_l` | Layout | (hardcoded) | 0 |
| `margin_r` | Layout | (hardcoded) | 0 |
| `margin_t` | Layout | (hardcoded) | 0 |
| `margin_b` | Layout | (hardcoded) | 0 |
| `margin_pad` | Layout | (hardcoded) | 0 |
| `automargin` | Layout | (hardcoded) | `True` |

#### Typography Keys

| Config Key | Component | Widget | Default |
|------------|-----------|--------|---------|
| `title_font_size` | Typography | `numeric_input` | 18 |
| `xaxis_title_font_size` | Typography | `numeric_input` | 14 |
| `yaxis_title_font_size` | Typography | `numeric_input` | 14 |
| `xaxis_tickfont_size` | Typography | `numeric_input` | 12 |
| `xaxis_tickfont_color` | Typography | `color_picker` | `#444444` |
| `yaxis_tickfont_size` | Typography | `numeric_input` | 12 |
| `yaxis_tickfont_color` | Typography | `color_picker` | `#444444` |

#### Legend Keys (per-level prefix: `legend_`, `legend2_`, `legend3_`)

| Config Key Pattern | Component | Widget | Default |
|-------------------|-----------|--------|---------|
| `{cp}x` | Legend | `numeric_input` | 1.02 / 1.0 |
| `{cp}y` | Legend | `numeric_input` | 1.0 |
| `{cp}orientation` | Legend | `select_option` | `"vertical"` |
| `{cp}transparent` | Legend | `toggle` | `False` |
| `{cp}bgcolor` | Legend | `st.color_picker` | `#ffffff` |
| `{cp}border_color` | Legend | `color_picker` | `#000000` |
| `{cp}border_width` | Legend | `numeric_input` | 0 |
| `{cp}font_color` | Legend | `color_picker` | `#000000` |
| `{cp}font_size` | Legend | `numeric_input` | 12 |
| `{cp}title` | Legend | `st.text_input` | `""` |
| `{cp}title_font_color` | Legend | `color_picker` | `#000000` |
| `{cp}title_font_size` | Legend | `numeric_input` | 14 |
| `{cp}ncols` | Legend | `numeric_input` | 0 |
| `{cp}tracegroupgap` | Legend | `numeric_input` | 10 |
| `{cp}column_spacing` | Legend | `numeric_input` | 0.5 |
| `{cp}itemwidth` | Legend | `numeric_input` | 30 |
| `{cp}handletextpad` | Legend | `numeric_input` | 0.3 |

#### Axes Keys

| Config Key | Component | Widget | Default |
|------------|-----------|--------|---------|
| `show_x_grid` | Axes (X) | `toggle` | `False` |
| `xaxis_tickangle` | Axes (X) | `slider` | -45 |
| `show_xtick_marks` | Axes (X) | `toggle` | `False` |
| `xaxis_tick_side` | Axes (X) | `select_option` | `"bottom"` |
| `xtick_dash` | Axes (X) | `select_option` | `"solid"` |
| `xtick_pad` | Axes (X) | `numeric_input` | 5.0 |
| `x_axis_line_width` | Axes (X) | `numeric_input` | 1.0 |
| `x_axis_line_color` | Axes (X) | `color_picker` | `#444444` |
| `top_axis_line_width` | Axes (X) | `numeric_input` | 0.0 |
| `top_axis_line_color` | Axes (X) | `color_picker` | `#444444` |
| `numbered_xaxis` | Axes (X) | `toggle` / derived | `False` |
| `numbered_xaxis_modes` | Axes (X) | `st.pills` (multi) | `[]` |
| `show_numbered_ticks` | Axes (X) | (derived) | `False` |
| `show_numbered_legend` | Axes (X) | (derived) | `False` |
| `show_y_grid` | Axes (Y-Left) | `toggle` | `True` |
| `y2show_y_grid` | Axes (Y-Right) | `toggle` | `False` |
| `yaxis_tickangle` | Axes (Y) | `slider` | 0 |
| `yaxis_dtick` | Axes (Y) | `st.number_input` | 0.0 |
| `show_ytick_marks` | Axes (Y) | `toggle` | `False` |
| `yaxis_tick_side` | Axes (Y) | `select_option` | `"left"` |
| `ytick_dash` | Axes (Y) | `select_option` | `"solid"` |
| `yaxis_title_standoff` | Axes (Y) | `slider` | -1 |
| `yaxis_title_vshift` | Axes (Y) | `slider` | 0 |
| `y_axis_line_width` | Axes (Y-Left) | `numeric_input` | 1.0 |
| `y_axis_line_color` | Axes (Y-Left) | `color_picker` | `#444444` |
| `right_axis_line_width` | Axes (Y-Left) | `numeric_input` | 0.0 |
| `right_axis_line_color` | Axes (Y-Left) | `color_picker` | `#444444` |
| `major_label_offset` | Axes (Group) | `numeric_input` | -0.15 |
| `group_label_offset` | Axes (Group) | (derived) | -0.15 |
| `group_label_alternate` | Axes (Group) | `toggle` | `True` |
| `group_label_alt_spacing` | Axes (Group) | `numeric_input` | 0.05 |

#### Data Labels Keys

| Config Key | Component | Widget | Default |
|------------|-----------|--------|---------|
| `show_values` | Data Labels | `toggle` | `False` |
| `text_color_mode` | Data Labels | `select_option` | `"auto"` |
| `text_color` | Data Labels | `color_picker` | `#000000` |
| `text_font_size` | Data Labels | `numeric_input` | 10 |
| `text_rotation` | Data Labels | `slider` | 0 |
| `text_position` | Data Labels | `select_option` | `"auto"` |
| `text_anchor` | Data Labels | `select_option` | `"auto"` |
| `text_format` | Data Labels | `st.text_input` | `".2f"` |
| `text_display_logic` | Data Labels | `select_option` | `"all"` |
| `text_threshold` | Data Labels | `numeric_input` | 0.0 |
| `text_constraint` | Data Labels | `select_option` | `"none"` |
| `show_totals` | Data Labels | `toggle` | `False` |
| `totals_position` | Data Labels | `select_option` | `"right"` |
| `totals_aggregation` | Data Labels | `select_option` | `"mean"` |

#### Colors Keys

| Config Key | Component | Widget | Default |
|------------|-----------|--------|---------|
| `color_palette` | Colors | `select_option` | `"wong"` |
| `reverse_colorscale` | Colors | `st.checkbox` | `False` |
| `series_styles` | Colors | (dynamic per-series) | `{}` |
| `transparent_bg` | Colors | `toggle` | `False` |
| `plot_bgcolor` | Colors | `st.color_picker` | `#ffffff` |
| `paper_bgcolor` | Colors | `st.color_picker` | `#ffffff` |
| `grid_color` | Colors | `color_picker` | `#e5e5e5` |
| `axis_color` | Colors | `color_picker` | `#444444` |
| `axis_line_width` | Colors | `numeric_input` | 1.0 |
| `enable_stripes` | Colors | `toggle` | `False` |

#### Advanced Keys

| Config Key | Component | Widget | Default |
|------------|-----------|--------|---------|
| `show_error_bars` | Advanced | `st.checkbox` | `False` |
| `download_format` | Advanced | `st.selectbox` | `"html"` |
| `export_scale` | Advanced | `st.selectbox` | 1 |
| `enable_editable` | Advanced | `st.checkbox` | `False` |
| `reference_line_enabled` | Advanced/Ref | `toggle` | `False` |
| `reference_line_y` | Advanced/Ref | `numeric_input` | 1.0 |
| `reference_line_color` | Advanced/Ref | `color_picker` | `#FF0000` |
| `reference_line_width` | Advanced/Ref | `slider` | 1.5 |
| `reference_line_style` | Advanced/Ref | `select_option` | `"dash"` |
| `shapes` | Advanced/Shapes | (list builder) | `[]` |
| `hovermode` | Advanced/Engine | `select_option` | `"x unified"` |
| `latex_extra_preamble` | Advanced/Engine | `st.text_area` | `""` |
| `tex_system` | Advanced/Engine | `select_option` | `"xelatex"` |

#### Ordering Keys (mutates config in-place, no return)

| Config Key | Component | Condition |
|------------|-----------|-----------|
| `xaxis_order` | Ordering | X column in data |
| `xaxis_labels` | Ordering | Renames provided |
| `group_order` | Ordering | Group column in data |
| `legend_labels` | Ordering | Color column rename map |
| `legend_order` | Ordering | Color column in data |
| `y_columns` | Ordering | Stacked series reordered |
| `metric_columns` | Ordering | Heatmap metric reordered |
| `metric_labels` | Ordering | Heatmap metric renamed |
| `facet_order` | Ordering | Facet column in data |
| `facet_labels` | Ordering | Facet renames provided |

---

## 8. Downstream Dependencies

### 8.1 Config Flow

```
User Interaction
  -> Streamlit widget (st.slider, st.selectbox, ...)
  -> Widget Factory function (select_option, numeric_input, ...)
  -> Settings Component.render() returns PlotConfig dict
  -> PlotConfigUIMixin.render_settings_section() returns PlotConfig dict
  -> RenderController merges into current_config
  -> BasePlot.config = current_config
  -> BasePlot.generate_figure()
     -> create_traces(data, config)  [plot-type-specific]
     -> apply_common_layout(fig, config)
        -> StyleApplicator.apply_styles(fig, config)
           -> ConfigSpecBuilder.build(config) -> FigureConfig
              -> FigureSpecToPlotly / FigureSpecToMatplotlib
```

### 8.2 Who Reads Session State Values

The settings system does **not** read from `st.session_state` directly (except for
the shapes edit mode check: `st.session_state.get(f"edit_shapes_{pid}", False)`).
Instead, all config values flow through the `PlotConfig` dictionary:

1. `RenderController` builds `current_config` from `render_config_ui()` + `render_settings_section()`.
2. `current_config` is compared to `saved_config` for change detection.
3. When the user clicks Refresh (or auto-refresh is on), `plot.config = current_config`
   is persisted via the session state management layer.
4. On next render, `saved_config` is loaded from session state and passed to components.

### 8.3 Cross-Step Dependencies

| Upstream | This Step | Downstream |
|----------|-----------|------------|
| Step 07 (FigureConfig) | Settings widgets produce flat config keys | ConfigSpecBuilder maps flat keys to FigureConfig fields |
| Step 11 (Rendering) | PlotConfig dict is the input to ConfigSpecBuilder | FigureConfig drives Plotly/Matplotlib rendering |
| Step 18 (Data Flow) | Settings are part of the configuration step | Config is serialized/deserialized with plot state |
| Step 08 (Palettes) | `color_palette` key selects the palette | `resolve_palette()` resolves to hex color list |
| Step 01 (Architecture) | Component-only architecture (P1, P9) | Settings components follow extraction pattern |

### 8.4 Style UI Factory Pattern

The `StyleUIFactory` provides plot-type-specific style UI managers:

```python
class StyleUIFactory:
    @staticmethod
    def get_strategy(plot_id: int, plot_type: str) -> BaseStyleUI:
        if plot_type == "dual_axis_bar_dot": return BaseStyleUI(...)
        elif "line" in plot_type:            return LineStyleUI(...)
        elif "scatter" in plot_type:         return ScatterStyleUI(...)
        elif "bar" in plot_type:             return BarStyleUI(...)
        else:                                return BaseStyleUI(...)
```

The subclasses override `_render_specific_series_visuals()` to add plot-type-specific
per-series controls:

| Subclass | Extra Per-Series Widget | Options |
|----------|----------------------|---------|
| `BarStyleUI` | Pattern selectbox | `""`, `/`, `\`, `x`, `-`, `|`, `+`, `.` |
| `LineStyleUI` | Marker Symbol selectbox | `circle`, `square`, `diamond`, `cross`, `x`, `triangle-up`, `triangle-down` |
| `LineStyleUI` | Marker Size number_input | 0-50, default 8 |
| `LineStyleUI` | Line Width number_input | 1-20, default 2 |
| `ScatterStyleUI` | (inherits from LineStyleUI) | Same as LineStyleUI |

### 8.5 Dual-Axis Settings

The `dual_axis_settings.py` module provides supplementary settings for dual-axis plots
(`grouped_stacked_bar` with `dual_axis=True`). These are rendered outside the pills
navigation, directly in the plot type's `render_config_ui`:

| Function | Config Keys |
|----------|-------------|
| `render_dual_axis_display_settings` | `show_y_grid`, `y2show_y_grid`, `yaxis2_title_font_size`, `yaxis2_title_standoff`, `yaxis2_tickfont_size`, `yaxis2_tickfont_color`, `unified_legend` |
| `render_secondary_legend_controls` | `legend2_orientation`, `legend2_x`, `legend2_y`, `legend2_xanchor`, `legend2_yanchor`, `legend2_bgcolor`, `legend2_border_color`, `legend2_border_width`, `legend2_font_color`, `legend2_font_size`, `legend2_title` |
| `render_right_axis_dot_settings` | `right_show_lines`, `right_dot_symbol`, `right_dot_size`, `right_line_width` |

---

## 9. Session State Key Map (Settings-Related)

All Streamlit widget keys follow the pattern `{prefix}{descriptor}_{plot_id}`:

| Prefix Pattern | Used By | Example |
|----------------|---------|---------|
| `settings_nav` | Top-level pills (global) | `settings_nav` |
| `preset_selector_{pid}` | Preset pills | `preset_selector_1` |
| `show_advanced_{pid}` | Advanced toggle | `show_advanced_1` |
| `axis_nav_{pid}` | Axes sub-pills | `axis_nav_1` |
| `legend_nav_{pid}` | Legend sub-pills | `legend_nav_1` |
| `numbered_modes_{pid}` | Numbered X-axis pills | `numbered_modes_1` |
| `col_preset_{pid}` | Layout preset selectbox | `col_preset_1` |
| `wi_{pid}` / `hi_{pid}` | Layout dimensions | `wi_1`, `hi_1` |
| `theme_{desc}_{pid}` | Typography, Data Labels | `theme_title_sz_1` |
| `{kp}leg_{desc}_{pid}` | Legend widgets | `theme_leg_x_1`, `legend2_leg_x_1` |
| `{desc}_{pid}` | Axes, Advanced, Engine | `xaxis_angle_1`, `error_bars_1` |
| `{kp}color_{pid}_{hash}_{palette}` | Series color overrides | `theme_color_1_a3b2c1d4_wong` |
| `{kp}use_col_{pid}_{hash}` | Series override toggle | `theme_use_col_1_a3b2c1d4` |
| `{kp}pat_{pid}_{hash}` | Bar pattern | `theme_pat_1_a3b2c1d4` |
| `{kp}sym_{pid}_{hash}` | Line marker symbol | `theme_sym_1_a3b2c1d4` |
| `edit_shapes_{pid}` | Shapes edit mode flag | `edit_shapes_1` |
