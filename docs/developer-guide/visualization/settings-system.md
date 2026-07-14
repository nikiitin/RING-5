---
title: "Settings Pills System"
parent: Visualization
grand_parent: Developer Guide
nav_order: 4
---

# Settings Pills System

The settings pills system is the primary user-facing configuration interface in
RING-5 Unified Engine v2. It presents plot styling options through a horizontal
row of selectable pill buttons, where each pill opens a dedicated settings panel.
The system follows a **progressive disclosure** pattern: only three basic pills
are visible by default, with four additional advanced pills revealed on demand.

This guide covers the full stack -- from the pill navigation layer, through the
widget definition and rendering abstractions, down to the individual settings
panels and their config key outputs.

---

## Architecture Overview

The settings system is a three-layer architecture:

| Layer | Responsibility | Key Module |
|-------|----------------|------------|
| **Pills Navigation** | Top-level section routing via `st.pills` | `settings_pills.py` |
| **Settings Components** | Per-section widget rendering; each returns a `PlotConfig` dict | `src/web/components/plotting/settings/*.py` |
| **Widget Factory** | Standardized wrappers around `st.*` widgets with config-based defaults | `widget_factory.py` |

A supplementary **declarative widget system** (`WidgetDef` / `WidgetRenderer`)
provides data-driven widget definitions with `spec_path` mappings to
`FigureConfig` fields. The hand-coded settings components remain the primary
rendering path for the pills UI.

The end-to-end flow from user interaction to rendered figure is:

```
RenderController
  -> st.toggle("Show advanced settings")
  -> render_settings_pills(show_advanced)        # returns section key
  -> plot.render_settings_section(section, ...)   # PlotConfigUIMixin dispatcher
     -> <SectionComponent>.render(saved_config)   # returns PlotConfig dict
        -> widget_factory.select_option / numeric_input / ...
           -> st.selectbox / st.number_input / ...
  -> current_config.update(extra_config)
```

### Progressive Disclosure

The settings UI implements a two-tier progressive disclosure pattern:

1. **Basic/Advanced toggle** -- An `st.toggle("Show advanced settings")` in the
   render controller controls which pills are visible. By default only three
   basic pills appear (Layout, Typography, Legends). Toggling the switch reveals
   four additional advanced pills (Axes, Data Labels, Colors, Advanced).

2. **Per-section disclosure** -- Individual sections use conditional rendering
   internally. For example, the Data Labels section hides all formatting widgets
   until "Show Values" is enabled. The Axes section only shows the grid dash
   style selector when tick marks are turned on.

---

## Settings Pills Navigation

### SettingsSection Data Structure

Each pill in the navigation row is described by a frozen dataclass defined in
`src/web/pages/ui/plotting/settings_pills.py`:

```python
@dataclass(frozen=True)
class SettingsSection:
    key: str         # Machine-readable identifier (e.g. "layout")
    label: str       # Human-readable display name (e.g. "Layout")
    icon: str        # Material icon name without prefix (e.g. "dashboard")
    advanced: bool   # Hidden unless advanced mode is enabled
```

### Section Registry

The `SETTINGS_SECTIONS` list defines all seven pills in display order:

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

### Rendering Logic

The `render_settings_pills(show_advanced)` function:

1. Filters the section list based on the `show_advanced` flag.
2. Builds an options list of section keys.
3. Builds a label map applying the `:material/<icon>: <label>` format.
4. Calls `st.pills("Settings", ...)` in `selection_mode="single"`.
5. Returns the selected section key as a string, or `None` if nothing is
   selected.

The session state key for the top-level pills is `"settings_nav"`.

### Nested Sub-Pills

Two settings components use nested `st.pills` for sub-navigation within their
panel:

| Component | Sub-Options | Session State Key |
|-----------|-------------|-------------------|
| `AxesSettingsComponent` | X-Axis, Y-Left, Y-Right, Group Labels | `axis_nav_{plot_id}` |
| `LegendSettingsComponent` | Primary, Secondary, Tertiary | `legend_nav_{plot_id}` |

The Y-Right sub-pill only appears for dual-axis plots. Group Labels only appears
for grouped stacked bar charts. Secondary and tertiary legend pills are
conditional on plot features.

### Section Dispatch

The `PlotConfigUIMixin.render_settings_section()` method in
`src/web/pages/ui/plotting/plot_config_ui.py` acts as a router. It receives
the selected section key and instantiates the appropriate component class:

```python
if section == "layout":      -> LayoutSettingsComponent(pid, pt).render(saved_config)
if section == "typography":  -> TypographySettingsComponent(pid, pt).render(...)
if section == "legends":     -> LegendSettingsComponent(pid, pt).render(...)
if section == "axes":        -> AxesSettingsComponent(pid, pt).render(...)
if section == "data_labels": -> DataLabelsSettingsComponent(pid, pt).render(...)
if section == "colors":      -> ColorsSettingsComponent(pid, pt).render(...)
if section == "advanced":    -> AdvancedSettingsComponent(pid, pt).render(...)
if section is None:          -> {}
```

Each component is instantiated fresh on every Streamlit render cycle. Components
are stateless; all persistence flows through the `saved_config` dictionary.

---

## Widget Definition System (WidgetDef)

The declarative widget system lives in `src/web/rendering/widgets/` and provides
a typed dataclass hierarchy for describing UI controls without directly calling
Streamlit.

### WidgetDef Base Class

```python
@dataclass(frozen=True)
class WidgetDef:
    key: str           # Config key and widget key suffix
    label: str         # Human-readable label
    default: Any       # Default value when config has no entry
    help_text: str     # Tooltip text (empty string = no tooltip)
    spec_path: str     # Mapping to FigureConfig field path
```

The `spec_path` field bridges flat config keys to the structured `FigureConfig`
model used downstream (e.g., `"dimensions.margins.left"`,
`"typography.font_size_title"`).

### Subclass Hierarchy

| Subclass | Streamlit Widget | Extra Fields |
|----------|-----------------|--------------|
| `NumberWidgetDef` | `st.number_input` | `min_value`, `max_value`, `step`, `format_str`, `as_int` |
| `SliderWidgetDef` | `st.slider` | `min_value`, `max_value`, `step` |
| `SelectWidgetDef` | `st.selectbox` | `options: tuple[str, ...]` |
| `CheckboxWidgetDef` | `st.checkbox` | `default: bool` |
| `ColorWidgetDef` | `st.color_picker` | `default: str` (hex color) |
| `TextWidgetDef` | `st.text_input` | `default: str`, `max_chars` |

All subclasses are frozen dataclasses, making widget definitions immutable and
safe to share across render cycles.

### WidgetSection

Related widgets are grouped under a `WidgetSection`:

```python
@dataclass(frozen=True)
class WidgetSection:
    id: str                              # Unique section identifier
    label: str                           # Display label
    widgets: tuple[WidgetDef, ...] = ()  # Ordered widgets in this section
    icon: str = ""                       # Optional icon
    collapsed: bool = True               # Start collapsed in expander
```

`WidgetSection` provides three utility methods:

- `keys()` -- returns all config keys defined in this section.
- `defaults()` -- returns a `{key: default_value}` dictionary.
- `find(key)` -- looks up a `WidgetDef` by config key.

### Predefined Sections (ALL_SECTIONS Catalog)

The `widget_def.py` module defines 15 predefined section constants:

| Constant | ID | Content |
|----------|----|---------|
| `LAYOUT_DIMENSIONS` | `dimensions` | Width, height sliders |
| `LAYOUT_MARGINS` | `margins` | Left, right, top, bottom, pad, automargin |
| `TYPOGRAPHY` | `typography` | 10 font size/color widgets |
| `BACKGROUNDS` | `backgrounds` | Transparent toggle, plot and paper backgrounds |
| `AXIS_COLORS` | `axis_colors` | Grid color, axis line/tick color |
| `LEGEND_POSITION` | `legend_position` | Orientation, columns, column width, vertical align |
| `LEGEND_APPEARANCE` | `legend_appearance` | 8 appearance widgets (colors, borders, fonts) |
| `LEGEND_SIZING` | `legend_sizing` | Marker scale, marker width, item spacing |
| `LEGEND` | `legend` | Union of position + appearance + sizing |
| `DATA_LABELS` | `data_labels` | 11 data label widgets |
| `AXIS_X` | `axis_x` | X-axis label rotation |
| `AXIS_Y` | `axis_y` | Y-axis step size |
| `AXIS_Y2` | `axis_y2` | Y2-axis step size |
| `COLORS_PALETTE` | `colors_palette` | Palette selector |
| `REFERENCE_LINES` | `reference_lines` | 5 reference line widgets |
| `ADVANCED_SECTION` | `advanced` | Error bars, editing, download format/scale |

The `ALL_SECTIONS` tuple collects every section and is available for iteration
or programmatic access to the complete widget catalog.

---

## Widget Renderer

The `WidgetRenderer` class in `src/web/rendering/widgets/widget_renderer.py`
turns `WidgetSection` definitions into live Streamlit widgets and collects their
return values into a flat config dictionary.

### Construction

```python
renderer = WidgetRenderer(key_prefix="p3_")
```

The `key_prefix` string is prepended to every widget key to prevent
`DuplicateWidgetID` errors when multiple plots share a page.

### Rendering Methods

```python
# Render a single section, returning {config_key: value, ...}
config = renderer.render_section(section, saved_config, use_expander=True)

# Render multiple sections and merge results
config = renderer.render_sections([TYPOGRAPHY, BACKGROUNDS], saved_config)
```

When `use_expander=True`, widgets are wrapped in an `st.expander()` using the
section label and icon. The `collapsed` flag on the section controls whether the
expander starts open or closed.

### Dispatch Logic

The internal `_render_widget()` method dispatches based on `isinstance` checks:

1. `NumberWidgetDef` -> `st.number_input(...)` with int/float coercion
2. `SliderWidgetDef` -> `st.slider(...)`
3. `SelectWidgetDef` -> `st.selectbox(...)` with safe index calculation
4. `CheckboxWidgetDef` -> `st.checkbox(...)`
5. `ColorWidgetDef` -> `st.color_picker(...)`
6. `TextWidgetDef` -> `st.text_input(...)`
7. Fallback -> `st.text_input(...)` for unknown types

Default values are read from `saved_config.get(widget_def.key, widget_def.default)`,
ensuring saved user preferences take precedence over widget defaults.

---

## Widget Factory (Imperative)

The widget factory in `src/web/components/plotting/settings/widget_factory.py`
provides five standalone functions that wrap Streamlit widgets with standardized
config-lookup behavior. This is the **primary** widget abstraction used by all
hand-coded settings components.

### Factory Functions

| Function | Streamlit Widget | Return Type |
|----------|-----------------|-------------|
| `select_option(label, options, config, config_key, plot_id, ...)` | `st.selectbox` | `str` |
| `numeric_input(label, config, config_key, plot_id, ...)` | `st.number_input` | `int \| float` |
| `color_picker(label, config, config_key, plot_id, ...)` | `st.color_picker` | `str` |
| `toggle(label, config, config_key, plot_id, ...)` | `st.checkbox` | `bool` |
| `slider(label, config, config_key, plot_id, ...)` | `st.slider` | `int \| float` |

### Key Behaviors

**Widget Key Generation**: Each function builds a unique key as
`widget_key or f"{config_key}_{plot_id}"`. Components can override the key
via the `widget_key` keyword argument for disambiguation.

**Default Value Lookup**: All functions read from `config.get(config_key, default)`,
so saved user values are always preferred over the coded default.

**Safe Index Calculation** (selectbox only): `select_option` uses
`options.index(current) if current in options else 0` to prevent `ValueError`
when a saved value no longer appears in the current options list.

**Type Coercion**: `numeric_input` and `slider` coerce values to `float` or
`int` based on the `default` parameter type, ensuring Streamlit receives
consistent numeric types.

### Usage Example

A typical settings component uses the factory like this:

```python
from src.web.components.plotting.settings.widget_factory import (
    color_picker, numeric_input,
)

class TypographySettingsComponent:
    def render(self, saved_config, key_prefix="theme_"):
        title_font_size = numeric_input(
            "Plot Title Font Size",
            saved_config,
            "title_font_size",
            self.plot_id,
            widget_key=f"{key_prefix}title_sz_{self.plot_id}",
            default=18,
            min_value=8,
            max_value=100,
        )
        # ... more widgets ...
        return {"title_font_size": title_font_size, ...}
```

---

## Settings Panel Catalog

Each panel is a standalone class in `src/web/components/plotting/settings/`.
Every class follows the same contract: it takes `(plot_id, plot_type)` at
construction and exposes a `render(saved_config, ...) -> PlotConfig` method.

### Layout

- **Class**: `LayoutSettingsComponent`
- **File**: `src/web/components/plotting/settings/layout_settings.py`
- **Pill key**: `"layout"` (basic, always visible)
- **Config keys**: `document_width_preset`, `width_inches`, `height_inches`,
  `width`, `height`, `margin_l`, `margin_r`, `margin_t`, `margin_b`,
  `margin_pad`, `automargin`

Offers a document size preset dropdown (Single Column 3.5in, Double Column
7.0in, Custom). Width is locked when a preset is selected. Height is always
editable. Pixel values are derived as `int(inches * 100)`. Margins are
hardcoded to zero (auto-margin mode).

### Typography

- **Class**: `TypographySettingsComponent`
- **File**: `src/web/components/plotting/settings/typography_settings.py`
- **Pill key**: `"typography"` (basic, always visible)
- **Config keys**: `title_font_size`, `xaxis_title_font_size`,
  `yaxis_title_font_size`, `xaxis_tickfont_size`, `xaxis_tickfont_color`,
  `yaxis_tickfont_size`, `yaxis_tickfont_color`

Two-column layout -- title font sizes on the left, tick label sizes and colors
on the right. Outputs exactly 7 keys with strict isolation verified by tests.

### Legends

- **Class**: `LegendSettingsComponent`
- **File**: `src/web/components/plotting/settings/legend_settings.py`
- **Pill key**: `"legends"` (basic, always visible)
- **Sub-pills**: Primary, Secondary (dual-axis), Tertiary (numbered X-axis)

Each legend level provides position controls (x, y, orientation), appearance
controls (background, border, font color/size, title), and sizing controls
(columns, spacing, stripe length). For heatmap plots, the appearance section
changes to colorbar-specific controls (shared colorbar toggle, range mode,
tick count, tick decimals). When switching between legend sub-pills, inactive
pills' config values are preserved from `saved_config`.

### Axes

- **Class**: `AxesSettingsComponent`
- **File**: `src/web/components/plotting/settings/axes_settings.py`
- **Pill key**: `"axes"` (advanced)
- **Sub-pills**: X-Axis, Y-Left, Y-Right (dual-axis only), Group Labels
  (grouped stacked bar only)

The X-Axis tab includes grid toggle, label rotation, tick marks, tick side,
grid dash style, axis line width/color, and numbered X-axis controls. The
Y-axis tabs mirror most of these options plus step size, title standoff, and
vertical shift. The axes section also injects plot-type-specific controls (bar
gap, group gap) and the ordering sub-section via Protocol callbacks.

### Data Labels

- **Class**: `DataLabelsSettingsComponent`
- **File**: `src/web/components/plotting/settings/data_labels_settings.py`
- **Pill key**: `"data_labels"` (advanced)

Implements per-section progressive disclosure: when `show_values` is false, no
formatting widgets are rendered. When enabled, exposes value color mode, font
size, rotation, position, anchor, number format, display logic with threshold,
and size constraint. Heatmap plots get additional controls for totals display.

### Colors

- **Class**: `ColorsSettingsComponent`
- **File**: `src/web/components/plotting/settings/colors_settings.py`
- **Pill key**: `"colors"` (advanced)

Contains four sub-sections: palette selector (with colorblind-safe indicators
and color swatch preview), heatmap colorscale reversal, per-series color
overrides with pattern/marker/line-width controls (via the StyleUIFactory), and
background/grid color pickers.

### Advanced

- **Class**: `AdvancedSettingsComponent`
- **File**: `src/web/components/plotting/settings/advanced_settings.py`
- **Pill key**: `"advanced"` (advanced)

Groups general options (error bars, download format, export scale, interactive
editing) with three injected sub-sections:

- **Reference Lines** (`ReferenceLineSettingsComponent`) -- Y position, color,
  width, and dash style for a horizontal reference line.
- **Shapes/Annotations** (`ShapesSettingsComponent`) -- Dynamic list builder for
  rectangles, lines, and circles with position, color, and width controls.
- **Engine Controls** (`EngineSettingsComponent`) -- Engine-specific options like
  Plotly hover mode and Matplotlib's TeX system. Custom PGF preambles are
  deliberately disabled because the web configuration is untrusted input.

### Ordering (Sub-Section)

- **Class**: `OrderingSettingsComponent`
- **File**: `src/web/components/plotting/settings/ordering_settings.py`

Not a top-level pill. Rendered as a sub-section within the Axes X-Axis tab.
Provides up to six expandable reorder/rename lists for X-axis labels, groups,
legend items, stacked series, heatmap metrics, and facets. Each uses the shared
`render_reorderable_list` component.

---

## How Settings Map to FigureConfig

Settings components produce a flat `PlotConfig` dictionary (a `dict[str, Any]`).
This dictionary flows through the rendering pipeline as follows:

```
Settings Component.render()
  -> returns PlotConfig dict (e.g. {"title_font_size": 18, ...})
  -> PlotConfigUIMixin.render_settings_section() returns it
  -> RenderController merges into current_config
  -> BasePlot.config = current_config
  -> BasePlot.generate_figure()
     -> create_traces(data, config)
     -> apply_common_layout(fig, config)
        -> StyleApplicator.apply_styles(fig, config)
           -> ConfigSpecBuilder.build(config) -> FigureConfig
              -> FigureSpecToPlotly / FigureSpecToMatplotlib
```

The `ConfigSpecBuilder` is responsible for mapping flat config keys to the
structured `FigureConfig` model. For example, `title_font_size` maps to
`FigureConfig.typography.font_size_title`. The declarative `spec_path` field on
`WidgetDef` instances documents this mapping (e.g.,
`spec_path="typography.font_size_title"`), though the actual mapping logic lives
in the config spec builder rather than being driven by `spec_path` at runtime.

### Session State Management

The settings system does not read from `st.session_state` directly (with the
exception of the shapes edit mode flag). All config values flow through the
`PlotConfig` dictionary:

1. `RenderController` builds `current_config` from settings components.
2. `current_config` is compared against `saved_config` for change detection.
3. On refresh, `plot.config = current_config` persists via session state.
4. On next render, `saved_config` is loaded and passed back to components.

### Widget Key Conventions

All Streamlit widget keys follow the pattern `{prefix}{descriptor}_{plot_id}`:

| Pattern | Used By | Example |
|---------|---------|---------|
| `settings_nav` | Top-level pills (global) | `settings_nav` |
| `axis_nav_{pid}` | Axes sub-pills | `axis_nav_1` |
| `legend_nav_{pid}` | Legend sub-pills | `legend_nav_1` |
| `col_preset_{pid}` | Layout preset selectbox | `col_preset_1` |
| `theme_{desc}_{pid}` | Typography, Data Labels | `theme_title_sz_1` |
| `{kp}leg_{desc}_{pid}` | Legend widgets | `theme_leg_x_1` |
| `{kp}color_{pid}_{hash}_{palette}` | Series color pickers | `theme_color_1_a3b2c1d4_wong` |

Series color picker keys include a content hash (`md5[:8]`) to avoid conflicts
across dynamic series items, and the palette name so that Streamlit resets the
widget value when the user changes palettes.

---

## See Also

- `src/web/pages/ui/plotting/settings_pills.py` -- Pill navigation and section
  registry.
- `src/web/rendering/widgets/widget_def.py` -- Declarative widget definitions
  and predefined sections.
- `src/web/rendering/widgets/widget_renderer.py` -- Declarative renderer that
  turns WidgetDef instances into Streamlit widgets.
- `src/web/components/plotting/settings/widget_factory.py` -- Imperative widget
  factory functions used by all settings components.
- `src/web/components/plotting/settings/` -- All settings component classes.
- `src/web/pages/ui/plotting/plot_config_ui.py` -- PlotConfigUIMixin dispatcher
  that routes pill selections to components.
- `src/web/controllers/plot/render_controller.py` -- Orchestrates the settings
  pills rendering within the overall plot rendering flow.
- `src/web/pages/ui/plotting/styles/factory.py` -- StyleUIFactory for
  plot-type-specific per-series visual controls.
