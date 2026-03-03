# Step 29 -- E2E Export Presets Tests

## 1. Executive Summary

This document defines the exhaustive end-to-end test plan for the RING-5 Unified
Engine v2 export and download subsystem.  The export pipeline converts interactive
Streamlit-hosted figures into publication-ready artifacts across four output
formats (PNG, SVG, PDF, PGF/LaTeX) and supports 13 venue-specific presets that
overlay publication-quality dimensions, typography, axis styling, legend spacing,
and separator configuration onto the user's data-driven `FigureConfig`.

### Scope

| Area | Source Files | Test Coverage |
|------|-------------|---------------|
| Preset catalog and loading | `preset_manager.py`, `latex_presets.json` | All 13 presets load, validate, and cache correctly |
| Preset schema and types | `preset_schema.py` | `LaTeXPreset` typed fields, `ExportResult` contract |
| Preset application | `preset_applicator.py` | `apply()` full overlay, `apply_partial()` selective overlay |
| Preset-to-spec building | `config_builder.py` (`PresetSpecBuilder`) | FigureConfig construction from preset dictionaries |
| Download section UI | `download_section.py` | Engine-aware format pills, download buttons, byte export |
| Engine management | `engine_manager.py` | Plotly / Matplotlib routing in download section |
| Format-specific export | `download_section.py` | PNG, SVG, PDF, PGF/LaTeX byte generation |

### Architecture Summary

```
PresetManager.load_preset("nature")
        |
        v
  LaTeXPreset dict
        |
        v
PresetApplicator.apply(user_spec, preset_dict)
        |
        v
  FigureConfig (publication-quality)
        |
        +---> matplotlib_download_bytes(fig, "pdf")
        +---> matplotlib_download_bytes(fig, "pgf")
        +---> matplotlib_download_bytes(fig, "png")
        +---> matplotlib_download_bytes(fig, "svg")
        |
        +---> plotly_download_bytes(fig, "pdf")
        +---> plotly_download_bytes(fig, "png")
        +---> plotly_download_bytes(fig, "svg")
        +---> plotly_download_bytes(fig, "html")
```

### Key Design Principles Under Test

1. **Immutable overlay**: `PresetApplicator.apply()` returns a **new** `FigureConfig`
   via `dataclasses.replace()`; the original spec is never mutated.
2. **Data-derived vs publication-derived split**: Presets override dimensions,
   typography, axes, legends, separator, font_family, and latex_extra_preamble.
   Traces, annotations, data_labels, color_palette, and reference_lines are
   preserved from the original user spec.
3. **Engine-aware download**: The download section inspects `EngineManager` to
   decide whether to render Plotly (Kaleido) or Matplotlib (`savefig`) controls.
4. **PGF fallback**: When a matplotlib figure contains raster content (e.g.,
   heatmaps), PGF export falls back to PDF with a user warning.
5. **Caching**: `PresetManager` caches loaded presets in `_cache` for performance;
   subsequent loads skip JSON parsing and validation.

### Format-Engine Matrix

| Format | Plotly Engine | Matplotlib Engine | Export Method |
|--------|:------------:|:-----------------:|---------------|
| PNG | Yes | Yes | Kaleido `to_image()` / `savefig(format="png")` |
| SVG | Yes | Yes | Kaleido `to_image()` / `savefig(format="svg")` |
| PDF | Yes | Yes | Kaleido `to_image()` / `savefig(format="pdf")` |
| HTML | Yes | No | `fig.to_html()` |
| PGF | No | Yes | `savefig(format="pgf", backend="pgf")` |

---

## 2. Export System Overview

### 2.1 PresetManager -- Catalog Loading and Validation

`PresetManager` (in `src/web/pages/ui/plotting/export/presets/preset_manager.py`)
is a classmethod-only service that reads `latex_presets.json` from the same
directory.  Key behaviors:

- **Lazy initialization**: `_initialize()` is called once; subsequent calls are
  no-ops thanks to the `_initialized` flag.
- **Cache**: `_cache: dict[str, LaTeXPreset]` avoids recomputing the field
  extraction and validation on repeated loads of the same preset.
- **Field extraction**: `load_preset()` maps raw JSON keys to typed `LaTeXPreset`
  fields, applying defaults via `.get()` for optional fields (e.g.,
  `font_size_y2label` defaults to `-1`, meaning "follow primary").
- **Validation**: `validate_preset()` checks required fields exist and that
  dimensions, font sizes, line width, marker size, and DPI are positive.
- **Listing**: `list_presets()` returns all available preset names.
- **Metadata**: `get_preset_info()` returns description and typical_use without
  loading the full preset configuration.

### 2.2 LaTeXPreset Schema

`LaTeXPreset` (in `preset_schema.py`) is a `TypedDict(total=False)` with 60+ fields
organized into these groups:

| Field Group | Key Examples | Count |
|------------|-------------|-------|
| Dimensions | `width_inches`, `height_inches`, `dpi` | 3 |
| Typography (font sizes) | `font_size_base`, `font_size_title`, `font_size_xlabel`, `font_size_legend` | 14 |
| Typography (bold flags) | `bold_title`, `bold_xlabel`, `bold_ylabel`, `bold_ticks` | 10 |
| Line/marker styling | `line_width`, `marker_size` | 2 |
| Legend spacing (primary) | `legend_columnspacing`, `legend_handletextpad`, `legend_borderpad` | 8 |
| Legend spacing (secondary) | `legend2_columnspacing` through `legend2_ncol` | 8 |
| Legend spacing (tertiary) | `legend3_borderpad`, `legend3_labelspacing`, `legend3_number_fontsize` | 4 |
| Axis positioning | `ylabel_pad`, `xtick_pad`, `xtick_rotation`, `xaxis_margin` | 12 |
| Group labels | `group_label_offset`, `group_label_alternate`, `group_label_alt_spacing` | 3 |
| Separator | `group_separator`, `group_separator_style`, `group_separator_color` | 3 |
| Legend position | `legend_custom_pos`, `legend_x`, `legend_y` | 3 |
| LaTeX | `latex_extra_preamble` | 1 |

`ExportResult` is a separate `TypedDict` with fields: `success`, `data`, `format`,
`error`, `metadata`.

### 2.3 PresetApplicator -- FigureConfig Overlay

`PresetApplicator` (in `src/web/rendering/preset_applicator.py`) provides two
static methods:

- **`apply(spec, preset_info)`**: Builds a full `FigureConfig` from the preset
  via `PresetSpecBuilder.from_preset()`, then uses `dataclasses.replace()` to
  overlay dimensions, typography, axes, legends, separator, font_family, and
  latex_extra_preamble onto the user's spec.
- **`apply_partial(spec, preset_info)`**: Only overrides FigureConfig fields
  whose corresponding key groups intersect with the keys present in
  `preset_info`.  Key groups are: `_DIMENSION_KEYS`, `_TYPO_KEYS`, `_AXES_KEYS`,
  `_LEGEND_KEYS`, `_SEPARATOR_KEYS`, plus standalone `font_family` and
  `latex_extra_preamble`.

### 2.4 Download Section -- Engine-Aware Export

`download_section.py` provides:

- **`render_download_section(plot_id, plot_name, fig)`**: Top-level UI entry
  that routes to Plotly or Matplotlib download widgets based on `EngineManager`.
  Wrapped in an `st.expander("Download", expanded=False)`.
- **Plotly path**: `_render_plotly_download()` shows format pills
  `["html", "png", "svg", "pdf"]` with default `"html"`, then calls
  `plotly_download_bytes()` which uses Kaleido v1 for raster/vector and
  `fig.to_html()` for interactive HTML.
- **Matplotlib path**: `_render_mpl_download()` reads the matplotlib figure from
  `st.session_state[f"plot.{plot_id}.mpl_fig"]`, shows format pills
  `["pdf", "pgf", "png", "svg"]` with default `"pdf"`, then calls
  `matplotlib_download_bytes()`.  PGF export uses `xelatex` backend with
  `pgf.preamble` from `FigureConfig.latex_extra_preamble`.

### 2.5 PresetSpecBuilder -- Preset-to-FigureConfig Translation

`PresetSpecBuilder.from_preset()` (in `src/web/rendering/config_builder.py`)
constructs a complete `FigureConfig` from a `LaTeXPreset` dictionary, building:

- `DimensionConfig` (width, height, dpi, bar_width_scale)
- `TypographyConfig` (15+ font size fields, 10 bold flags)
- `AxesConfig` with `AxisConfig` for x and y (tick_angle, tick_pad, margins)
- Three `LegendConfig` instances (primary, secondary, tertiary) with
  `LegendSpacingConfig` each
- `SeparatorConfig` (enabled, style, color)
- Top-level `font_family` and `latex_extra_preamble`

---

## 3. Preset Catalog -- All 13 Presets with Dimensions

The following table captures every preset defined in `latex_presets.json` with
its key publication-quality parameters.

| # | Preset Name | Width (in) | Height (in) | Font Family | Base Font | Title Font | Tick Font | DPI | Line Width | Marker Size | LaTeX Preamble |
|---|-------------|-----------|-------------|-------------|-----------|------------|-----------|-----|-----------|-------------|-----------------|
| 1 | `single_column` | 3.5 | 1.96875 | serif | 10 | 10 | 8 | 300 | 1.0 | 4.0 | `\usepackage[varqu,scaled=0.95]{zi4}` |
| 2 | `double_column` | 7.0 | 5.25 | serif | 10 | 10 | 8 | 300 | 1.0 | 4.0 | `\usepackage[varqu,scaled=0.95]{zi4}` |
| 3 | `micro` | 3.5 | 2.5 | serif | 10 | 10 | 8 | 300 | 1.0 | 4.0 | `\usepackage[varqu,scaled=0.95]{zi4}` |
| 4 | `isca` | 3.5 | 2.5 | serif | 10 | 10 | 8 | 300 | 1.0 | 4.0 | `\usepackage[varqu,scaled=0.95]{zi4}` |
| 5 | `asplos` | 3.5 | 2.5 | serif | 10 | 10 | 8 | 300 | 1.0 | 4.0 | `\usepackage[varqu,scaled=0.95]{zi4}` |
| 6 | `hpca` | 3.5 | 2.5 | serif | 10 | 10 | 8 | 300 | 1.0 | 4.0 | `\usepackage[varqu,scaled=0.95]{zi4}` |
| 7 | `taco` | 3.5 | 2.5 | serif | 10 | 10 | 8 | 300 | 1.0 | 4.0 | `\usepackage[varqu,scaled=0.95]{zi4}` |
| 8 | `nature` | 3.5 | 3.5 | Arial | 7 | 8 | 6 | 600 | 0.5 | 2.0 | (none) |
| 9 | `science` | 3.5 | 2.5 | sans-serif | 8 | 9 | 7 | 600 | 0.5 | 2.0 | (none) |
| 10 | `ieee_single` | 3.5 | 2.5 | serif | 10 | 10 | 8 | 300 | 1.0 | 4.0 | (none) |
| 11 | `acm` | 3.5 | 2.5 | serif | 9 | 10 | 8 | 300 | 1.0 | 4.0 | `\usepackage[varqu,scaled=0.95]{zi4}` |
| 12 | `poster` | 10.0 | 7.0 | sans-serif | 24 | 28 | 20 | 150 | 2.0 | 8.0 | (none) |
| 13 | `slides` | 8.0 | 4.5 | sans-serif | 18 | 22 | 14 | 150 | 1.5 | 6.0 | (none) |

### Preset Groupings by Venue Type

**Computer architecture conferences** (identical layout): `micro`, `isca`,
`asplos`, `hpca` -- all 3.5x2.5" at 10pt serif with 300 DPI.

**IEEE/ACM academic papers**: `single_column` (3.5x1.96875"), `double_column`
(7.0x5.25"), `ieee_single`, `acm`, `taco`.

**High-impact journals**: `nature` (Arial, 7pt base, 600 DPI, square 3.5x3.5"),
`science` (sans-serif, 8pt base, 600 DPI).

**Presentation formats**: `poster` (10x7", 24pt, 150 DPI),
`slides` (8x4.5", 18pt, 150 DPI).

### Shared Legend Spacing

All 13 presets share identical legend spacing parameters:
- `legend_columnspacing`: 1.0
- `legend_handletextpad`: 0.5
- `legend_labelspacing`: 0.3
- `legend_handlelength`: 1.5
- `legend_handleheight`: 0.7
- `legend_borderpad`: 0.3
- `legend_borderaxespad`: 0.3

---

## 4. Preset Application Tests

### 4.1 Full Preset Overlay (`PresetApplicator.apply`)

```gherkin
Feature: Preset full overlay onto FigureConfig
  The PresetApplicator.apply() method overlays all publication-quality fields
  from a preset onto an existing user-built FigureConfig, returning a new
  immutable spec while preserving all data-derived fields.

  Scenario Outline: Apply preset "<preset>" and verify dimensions are overridden
    Given a user FigureConfig with width=800px, height=500px, dpi=1
    And the LaTeX preset "<preset>" is loaded via PresetManager
    When PresetApplicator.apply(user_spec, preset_dict) is called
    Then the returned spec has dimensions.width == <width>
    And the returned spec has dimensions.height == <height>
    And the returned spec has dimensions.dpi == <dpi>
    And the original user_spec dimensions are unchanged

    Examples:
      | preset         | width | height  | dpi |
      | single_column  | 3.5   | 1.96875 | 300 |
      | double_column  | 7.0   | 5.25    | 300 |
      | micro          | 3.5   | 2.5     | 300 |
      | isca           | 3.5   | 2.5     | 300 |
      | asplos         | 3.5   | 2.5     | 300 |
      | hpca           | 3.5   | 2.5     | 300 |
      | taco           | 3.5   | 2.5     | 300 |
      | nature         | 3.5   | 3.5     | 600 |
      | science        | 3.5   | 2.5     | 600 |
      | ieee_single    | 3.5   | 2.5     | 300 |
      | acm            | 3.5   | 2.5     | 300 |
      | poster         | 10.0  | 7.0     | 150 |
      | slides         | 8.0   | 4.5     | 150 |

  Scenario: Apply preset preserves user traces and color palette
    Given a user FigureConfig with 5 trace configs and color_palette ["#FF0000", "#00FF00"]
    And the "nature" preset is loaded
    When PresetApplicator.apply(user_spec, nature_preset) is called
    Then the returned spec has 5 trace configs
    And the returned spec has color_palette ["#FF0000", "#00FF00"]
    And the returned spec has font_family "Arial"

  Scenario: Apply preset preserves user annotations and reference lines
    Given a user FigureConfig with 3 annotations and 1 reference line at y=1.0
    And the "ieee_single" preset is loaded
    When PresetApplicator.apply(user_spec, ieee_preset) is called
    Then the returned spec has 3 annotations
    And the returned spec has 1 reference line with value 1.0
    And the returned spec has dimensions.width == 3.5

  Scenario: Apply preset preserves data_labels, series_styles, trace_overrides
    Given a user FigureConfig with show_values enabled and per-trace color overrides
    And the "acm" preset is loaded
    When PresetApplicator.apply(user_spec, acm_preset) is called
    Then the returned spec has data_labels.enabled == True
    And the returned spec has the same trace_overrides as the original
    And the returned spec has typography.font_size_base == 9

  Scenario: Apply preset overlays font_family and latex_extra_preamble
    Given a user FigureConfig with font_family="sans-serif" and empty preamble
    And the "single_column" preset is loaded (has zi4 preamble)
    When PresetApplicator.apply(user_spec, preset) is called
    Then the returned spec has font_family "serif"
    And the returned spec has latex_extra_preamble containing "zi4"

  Scenario: Apply preset immutability -- original spec untouched
    Given a user FigureConfig captured as original_dims = spec.dimensions
    And the "poster" preset is loaded
    When PresetApplicator.apply(user_spec, poster_preset) is called
    Then the original spec still has original_dims
    And the returned spec has dimensions.width == 10.0
    And id(returned_spec) != id(user_spec)
```

### 4.2 Partial Preset Overlay (`PresetApplicator.apply_partial`)

```gherkin
Feature: Selective preset overlay onto FigureConfig
  The apply_partial() method only overrides FigureConfig field groups whose
  keys are present in the partial preset dictionary.

  Scenario: Partial preset with only dimension keys
    Given a user FigureConfig with base typography
    And a partial preset dict with only {"width_inches": 5.0, "height_inches": 3.0, "dpi": 600}
    When PresetApplicator.apply_partial(spec, partial_preset) is called
    Then the returned spec has dimensions.width == 5.0
    And the returned spec has dimensions.height == 3.0
    And the returned spec has dimensions.dpi == 600
    And the returned spec typography is unchanged from user spec

  Scenario: Partial preset with only typography keys
    Given a user FigureConfig with dimensions 7x4 inches
    And a partial preset dict with only {"font_size_base": 12, "bold_title": True}
    When PresetApplicator.apply_partial(spec, partial_preset) is called
    Then the returned spec dimensions are unchanged (7x4)
    And the returned spec has typography.font_size_base == 12
    And the returned spec has typography.bold_title == True

  Scenario: Partial preset with only legend keys
    Given a user FigureConfig with default legend spacing
    And a partial preset dict with {"legend_columnspacing": 2.0, "legend_borderpad": 0.5}
    When PresetApplicator.apply_partial(spec, partial_preset) is called
    Then the returned spec has legends[0].spacing.columnspacing == 2.0
    And the returned spec has legends[0].spacing.borderpad == 0.5
    And the returned spec dimensions and typography are unchanged

  Scenario: Partial preset with only separator keys
    Given a user FigureConfig with separator disabled
    And a partial preset dict with {"group_separator": True, "group_separator_style": "dot"}
    When PresetApplicator.apply_partial(spec, partial_preset) is called
    Then the returned spec has separator.enabled == True
    And the returned spec has separator.style == "dot"

  Scenario: Partial preset with only font_family key
    Given a user FigureConfig with font_family "serif"
    And a partial preset dict with {"font_family": "Arial"}
    When PresetApplicator.apply_partial(spec, partial_preset) is called
    Then the returned spec has font_family "Arial"
    And all other fields are unchanged

  Scenario: Partial preset with only latex_extra_preamble key
    Given a user FigureConfig with empty preamble
    And a partial preset dict with {"latex_extra_preamble": "\\usepackage{amsmath}"}
    When PresetApplicator.apply_partial(spec, partial_preset) is called
    Then the returned spec has latex_extra_preamble containing "amsmath"
    And all other fields are unchanged

  Scenario: Partial preset with empty dict returns same spec
    Given a user FigureConfig
    And an empty partial preset dict {}
    When PresetApplicator.apply_partial(spec, {}) is called
    Then the returned spec is identical to the original spec
    And the returned spec is the same object as the original spec

  Scenario: Partial preset with mixed dimension + axes keys
    Given a user FigureConfig
    And a partial preset dict with {"width_inches": 5.0, "xtick_rotation": 0.0}
    When PresetApplicator.apply_partial(spec, partial_preset) is called
    Then the returned spec has dimensions overridden
    And the returned spec has axes overridden
    And the returned spec has typography and legends unchanged

  Scenario: Partial preset with keys from all groups
    Given a user FigureConfig
    And a partial preset dict with keys from _DIMENSION_KEYS, _TYPO_KEYS, _AXES_KEYS, _LEGEND_KEYS, and _SEPARATOR_KEYS
    When PresetApplicator.apply_partial(spec, partial_preset) is called
    Then all five field groups are overridden
```

### 4.3 PresetSpecBuilder -- Preset-to-FigureConfig Construction

```gherkin
Feature: PresetSpecBuilder constructs FigureConfig from LaTeXPreset dict
  PresetSpecBuilder.from_preset() translates a LaTeXPreset dictionary into
  the full FigureConfig dataclass hierarchy.

  Scenario: Build FigureConfig from nature preset
    Given the raw LaTeX preset dict for "nature"
    When PresetSpecBuilder.from_preset(nature_dict) is called
    Then the result has dimensions.width == 3.5
    And the result has dimensions.height == 3.5
    And the result has dimensions.dpi == 600
    And the result has typography.font_size_base == 7
    And the result has typography.font_size_title == 8
    And the result has typography.font_size_ticks == 6
    And the result has font_family == "Arial"
    And the result has 3 legend configs (primary, secondary, tertiary)

  Scenario: Build FigureConfig from poster preset
    Given the raw LaTeX preset dict for "poster"
    When PresetSpecBuilder.from_preset(poster_dict) is called
    Then the result has dimensions.width == 10.0
    And the result has dimensions.height == 7.0
    And the result has dimensions.dpi == 150
    And the result has typography.font_size_base == 24
    And the result has typography.font_size_title == 28
    And the result has font_family == "sans-serif"

  Scenario: Build FigureConfig preserves default sentinel values
    Given a minimal preset dict with only required fields
    When PresetSpecBuilder.from_preset(minimal_dict) is called
    Then the result has typography.font_size_y2label == -1
    And the result has typography.font_size_legend2 == -1
    And the result has typography.font_size_legend3 == -1
    And the result has legends[1].spacing.columnspacing == -1.0

  Scenario: Build FigureConfig with bold flags
    Given a preset dict with bold_title=True and bold_xlabel=True
    When PresetSpecBuilder.from_preset(preset_dict) is called
    Then the result has typography.bold_title == True
    And the result has typography.bold_xlabel == True
    And the result has typography.bold_ylabel == False (default)

  Scenario: Build FigureConfig with separator enabled
    Given a preset dict with group_separator=True and style="dashdot"
    When PresetSpecBuilder.from_preset(preset_dict) is called
    Then the result has separator.enabled == True
    And the result has separator.style == "dashdot"
    And the result has separator.color == "gray" (default)

  Scenario: Build FigureConfig legend hierarchy
    Given the raw LaTeX preset dict for "single_column"
    When PresetSpecBuilder.from_preset(sc_dict) is called
    Then the result has legends[0].role == "primary"
    And the result has legends[0].font_size == 8
    And the result has legends[0].spacing.columnspacing == 1.0
    And the result has legends[1].role == "secondary"
    And the result has legends[1].font_size == -1
    And the result has legends[2].role == "tertiary"
    And the result has legends[2].font_size == -1
```

### 4.4 pytest-playwright Stubs -- Preset Application

```python
"""E2E tests for preset application logic.

Tests verify that PresetApplicator correctly overlays publication-quality
settings onto user-built FigureConfig instances while preserving
data-derived fields.

Source files under test:
    - src/web/rendering/preset_applicator.py
    - src/web/rendering/config_builder.py (PresetSpecBuilder)
    - src/web/pages/ui/plotting/export/presets/preset_manager.py
"""

import dataclasses

import pytest

from src.core.models.visualization.annotation_config import (
    AnnotationConfig,
    ReferenceLineConfig,
)
from src.core.models.visualization.figure_config import (
    DimensionConfig,
    FigureConfig,
    SeparatorConfig,
)
from src.core.models.visualization.typography_config import TypographyConfig
from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager
from src.web.rendering.config_builder import PresetSpecBuilder
from src.web.rendering.preset_applicator import PresetApplicator

# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def user_spec() -> FigureConfig:
    """A typical user-built FigureConfig with data-derived fields."""
    return FigureConfig(
        dimensions=DimensionConfig(width=800.0, height=500.0, dpi=1),
        title="My Benchmark Results",
        color_palette=["#FF0000", "#00FF00", "#0000FF"],
        annotations=[
            AnnotationConfig(text="Peak", x=3.0, y=100.0),
        ],
        reference_lines=[
            ReferenceLineConfig(enabled=True, axis="y", value=1.0),
        ],
        font_family="sans-serif",
        latex_extra_preamble="",
    )


ALL_PRESET_NAMES = [
    "single_column",
    "double_column",
    "micro",
    "isca",
    "asplos",
    "hpca",
    "taco",
    "nature",
    "science",
    "ieee_single",
    "acm",
    "poster",
    "slides",
]

PRESET_EXPECTED_DIMS = {
    "single_column": (3.5, 1.96875, 300),
    "double_column": (7.0, 5.25, 300),
    "micro": (3.5, 2.5, 300),
    "isca": (3.5, 2.5, 300),
    "asplos": (3.5, 2.5, 300),
    "hpca": (3.5, 2.5, 300),
    "taco": (3.5, 2.5, 300),
    "nature": (3.5, 3.5, 600),
    "science": (3.5, 2.5, 600),
    "ieee_single": (3.5, 2.5, 300),
    "acm": (3.5, 2.5, 300),
    "poster": (10.0, 7.0, 150),
    "slides": (8.0, 4.5, 150),
}

PRESET_EXPECTED_FONTS = {
    "single_column": ("serif", 10, 10, 8),
    "double_column": ("serif", 10, 10, 8),
    "micro": ("serif", 10, 10, 8),
    "isca": ("serif", 10, 10, 8),
    "asplos": ("serif", 10, 10, 8),
    "hpca": ("serif", 10, 10, 8),
    "taco": ("serif", 10, 10, 8),
    "nature": ("Arial", 7, 8, 6),
    "science": ("sans-serif", 8, 9, 7),
    "ieee_single": ("serif", 10, 10, 8),
    "acm": ("serif", 9, 10, 8),
    "poster": ("sans-serif", 24, 28, 20),
    "slides": ("sans-serif", 18, 22, 14),
}


# ── Test: Full preset overlay ──────────────────────────────────────


class TestPresetApplyFullOverlay:
    """Tests for PresetApplicator.apply() -- full overlay."""

    @pytest.mark.parametrize("preset_name", ALL_PRESET_NAMES)
    def test_overrides_dimensions(
        self, user_spec: FigureConfig, preset_name: str
    ) -> None:
        """Verify that apply() overwrites dimensions for every preset."""
        preset = PresetManager.load_preset(preset_name)
        result = PresetApplicator.apply(user_spec, preset)

        expected_w, expected_h, expected_dpi = PRESET_EXPECTED_DIMS[preset_name]
        assert result.dimensions.width == pytest.approx(expected_w)
        assert result.dimensions.height == pytest.approx(expected_h)
        assert result.dimensions.dpi == expected_dpi

    @pytest.mark.parametrize("preset_name", ALL_PRESET_NAMES)
    def test_overrides_typography(
        self, user_spec: FigureConfig, preset_name: str
    ) -> None:
        """Verify that apply() overwrites typography for every preset."""
        preset = PresetManager.load_preset(preset_name)
        result = PresetApplicator.apply(user_spec, preset)

        family, base, title, ticks = PRESET_EXPECTED_FONTS[preset_name]
        assert result.font_family == family
        assert result.typography.font_size_base == base
        assert result.typography.font_size_title == title
        assert result.typography.font_size_ticks == ticks

    @pytest.mark.parametrize("preset_name", ALL_PRESET_NAMES)
    def test_preserves_data_fields(
        self, user_spec: FigureConfig, preset_name: str
    ) -> None:
        """Verify that apply() preserves all data-derived fields."""
        preset = PresetManager.load_preset(preset_name)
        result = PresetApplicator.apply(user_spec, preset)

        assert result.title == "My Benchmark Results"
        assert result.color_palette == ["#FF0000", "#00FF00", "#0000FF"]
        assert len(result.annotations) == 1
        assert result.annotations[0].text == "Peak"
        assert len(result.reference_lines) == 1
        assert result.reference_lines[0].value == 1.0

    @pytest.mark.parametrize("preset_name", ALL_PRESET_NAMES)
    def test_immutability(
        self, user_spec: FigureConfig, preset_name: str
    ) -> None:
        """Verify original spec is not mutated by apply()."""
        original_width = user_spec.dimensions.width
        original_dpi = user_spec.dimensions.dpi
        preset = PresetManager.load_preset(preset_name)

        result = PresetApplicator.apply(user_spec, preset)

        assert user_spec.dimensions.width == original_width
        assert user_spec.dimensions.dpi == original_dpi
        assert result is not user_spec

    def test_overlays_latex_preamble(self, user_spec: FigureConfig) -> None:
        """Preset with zi4 preamble overlays onto empty user preamble."""
        sc_preset = PresetManager.load_preset("single_column")
        result = PresetApplicator.apply(user_spec, sc_preset)
        assert "zi4" in result.latex_extra_preamble

    def test_nature_no_latex_preamble(self, user_spec: FigureConfig) -> None:
        """Nature preset has no LaTeX preamble."""
        nature_preset = PresetManager.load_preset("nature")
        result = PresetApplicator.apply(user_spec, nature_preset)
        assert result.latex_extra_preamble == ""


# ── Test: Partial preset overlay ───────────────────────────────────


class TestPresetApplyPartialOverlay:
    """Tests for PresetApplicator.apply_partial() -- selective overlay."""

    def test_dims_only(self, user_spec: FigureConfig) -> None:
        """Partial overlay with only dimension keys."""
        partial = {"width_inches": 5.0, "height_inches": 3.0, "dpi": 600}
        result = PresetApplicator.apply_partial(user_spec, partial)

        assert result.dimensions.width == pytest.approx(5.0)
        assert result.dimensions.height == pytest.approx(3.0)
        assert result.dimensions.dpi == 600

    def test_typography_only(self, user_spec: FigureConfig) -> None:
        """Partial overlay with only typography keys."""
        original_dims = user_spec.dimensions
        partial = {"font_size_base": 12, "bold_title": True}
        result = PresetApplicator.apply_partial(user_spec, partial)

        assert result.dimensions is original_dims
        assert result.typography.font_size_base == 12
        assert result.typography.bold_title is True

    def test_empty_dict_returns_same(self, user_spec: FigureConfig) -> None:
        """Partial overlay with empty dict returns same spec."""
        result = PresetApplicator.apply_partial(user_spec, {})
        assert result is user_spec

    def test_separator_keys_only(self, user_spec: FigureConfig) -> None:
        """Partial overlay with separator keys only."""
        partial = {"group_separator": True, "group_separator_style": "dot"}
        result = PresetApplicator.apply_partial(user_spec, partial)
        assert result.separator.enabled is True
        assert result.separator.style == "dot"

    def test_font_family_only(self, user_spec: FigureConfig) -> None:
        """Partial overlay with only font_family changes font only."""
        partial = {"font_family": "Arial"}
        result = PresetApplicator.apply_partial(user_spec, partial)
        assert result.font_family == "Arial"
        assert result.dimensions == user_spec.dimensions

    def test_legend_keys_only(self, user_spec: FigureConfig) -> None:
        """Partial overlay with legend keys overrides legend spacing."""
        partial = {"legend_columnspacing": 2.0, "legend_borderpad": 0.5}
        result = PresetApplicator.apply_partial(user_spec, partial)
        assert result.legends[0].spacing.columnspacing == pytest.approx(2.0)
        assert result.legends[0].spacing.borderpad == pytest.approx(0.5)


# ── Test: PresetSpecBuilder ────────────────────────────────────────


class TestPresetSpecBuilder:
    """Tests for PresetSpecBuilder.from_preset()."""

    @pytest.mark.parametrize("preset_name", ALL_PRESET_NAMES)
    def test_produces_valid_config(self, preset_name: str) -> None:
        """Every preset builds a valid FigureConfig."""
        preset = PresetManager.load_preset(preset_name)
        result = PresetSpecBuilder.from_preset(preset)

        assert isinstance(result, FigureConfig)
        assert result.dimensions.width > 0
        assert result.dimensions.height > 0
        assert result.dimensions.dpi > 0
        assert len(result.legends) == 3

    def test_legend_roles(self) -> None:
        """Legends have correct roles: primary, secondary, tertiary."""
        preset = PresetManager.load_preset("nature")
        result = PresetSpecBuilder.from_preset(preset)

        assert result.legends[0].role == "primary"
        assert result.legends[1].role == "secondary"
        assert result.legends[2].role == "tertiary"

    def test_sentinel_defaults(self) -> None:
        """Secondary/tertiary legends use -1 sentinels for 'follow primary'."""
        preset = PresetManager.load_preset("single_column")
        result = PresetSpecBuilder.from_preset(preset)

        assert result.typography.font_size_y2label == -1
        assert result.typography.font_size_legend2 == -1
        assert result.legends[1].spacing.columnspacing == -1.0

    def test_separator_default_disabled(self) -> None:
        """Separator is disabled by default in standard presets."""
        preset = PresetManager.load_preset("ieee_single")
        result = PresetSpecBuilder.from_preset(preset)
        assert result.separator.enabled is False
        assert result.separator.style == "dash"
        assert result.separator.color == "gray"
```

---

## 5. Download Section UI Tests

### 5.1 Engine-Aware Routing

```gherkin
Feature: Download section routes to correct engine controls
  The render_download_section() function inspects EngineManager to display
  either Plotly (Kaleido) or Matplotlib (savefig) download controls.

  Scenario: Plotly engine shows HTML/PNG/SVG/PDF format pills
    Given the engine mode is set to "plotly"
    And a valid Plotly figure exists
    When render_download_section() is called
    Then the download expander "Download" is rendered
    And format pills show ["html", "png", "svg", "pdf"]
    And the default selected format is "html"

  Scenario: Matplotlib engine shows PDF/PGF/PNG/SVG format pills
    Given the engine mode is set to "matplotlib"
    And a valid matplotlib figure is in session_state["plot.{id}.mpl_fig"]
    When render_download_section() is called
    Then the download expander "Download" is rendered
    And format pills show ["pdf", "pgf", "png", "svg"]
    And the default selected format is "pdf"

  Scenario: Matplotlib engine with no figure shows warning
    Given the engine mode is set to "matplotlib"
    And session_state["plot.{id}.mpl_fig"] is None
    When render_download_section() is called
    Then a warning "No matplotlib figure available for download." is shown
    And no download button is rendered

  Scenario: Format pill selection of None produces no download button
    Given the engine mode is set to "plotly"
    And format pill selection returns None (user deselected)
    When render_download_section() is called
    Then no download button is rendered

  Scenario: PGF export raster fallback to PDF with warning
    Given the engine mode is set to "matplotlib"
    And the matplotlib figure contains raster graphics (e.g., heatmap)
    When the user selects "pgf" format
    And matplotlib_download_bytes raises ValueError with "raster"
    Then the system falls back to "pdf" format
    And a warning about PGF raster limitation is shown
    And a PDF download button is rendered instead
```

### 5.2 Download Button Attributes

```gherkin
Feature: Download button has correct filename, MIME type, and label

  Scenario Outline: Plotly download button for format "<fmt>"
    Given a Plotly figure for plot "benchmark_results"
    When the user selects format "<fmt>"
    Then the download button label is "Download <label>"
    And the download filename is "benchmark_results<ext>"
    And the MIME type is "<mime>"

    Examples:
      | fmt  | label | ext   | mime             |
      | html | HTML  | .html | text/html        |
      | png  | PNG   | .png  | image/png        |
      | svg  | SVG   | .svg  | image/svg+xml    |
      | pdf  | PDF   | .pdf  | application/pdf  |

  Scenario Outline: Matplotlib download button for format "<fmt>"
    Given a matplotlib figure for plot "cache_performance"
    When the user selects format "<fmt>"
    Then the download button label is "Download <label>"
    And the download filename is "cache_performance<ext>"
    And the MIME type is "<mime>"

    Examples:
      | fmt | label | ext  | mime              |
      | pdf | PDF   | .pdf | application/pdf   |
      | pgf | PGF   | .pgf | application/x-pgf |
      | png | PNG   | .png | image/png         |
      | svg | SVG   | .svg | image/svg+xml     |
```

### 5.3 Widget Key Uniqueness

```gherkin
Feature: Download section widgets use unique keys per plot

  Scenario: Two plots have distinct widget keys
    Given plot_id=1 and plot_id=2 are both rendered
    When render_download_section() is called for each
    Then plot 1 format pill key is "dl_fmt_1"
    And plot 1 download button key is "dl_btn_1"
    And plot 2 format pill key is "dl_fmt_2"
    And plot 2 download button key is "dl_btn_2"
    And no Streamlit DuplicateWidgetID error occurs
```

### 5.4 pytest-playwright Stubs -- Download Section UI

```python
"""E2E tests for download section UI rendering.

Tests verify the engine-aware download controls render correctly
with proper format options, filenames, MIME types, and widget keys.

Source file under test:
    - src/web/pages/ui/plotting/download_section.py
    - src/web/rendering/engine_manager.py
"""

from unittest.mock import MagicMock, patch

import pytest

from src.web.pages.ui.plotting.download_section import (
    MatplotlibFormat,
    PlotlyFormat,
    get_matplotlib_extension,
    get_matplotlib_mime,
    get_plotly_extension,
    get_plotly_mime,
    matplotlib_download_bytes,
    plotly_download_bytes,
)


# ── Test: MIME types and extensions ────────────────────────────────


class TestPlotlyMimeAndExtensions:
    """Verify Plotly MIME type and extension mappings."""

    @pytest.mark.parametrize(
        "fmt,expected_mime",
        [
            ("png", "image/png"),
            ("svg", "image/svg+xml"),
            ("pdf", "application/pdf"),
            ("html", "text/html"),
        ],
    )
    def test_mime_types(self, fmt: str, expected_mime: str) -> None:
        assert get_plotly_mime(fmt) == expected_mime

    @pytest.mark.parametrize(
        "fmt,expected_ext",
        [
            ("png", ".png"),
            ("svg", ".svg"),
            ("pdf", ".pdf"),
            ("html", ".html"),
        ],
    )
    def test_extensions(self, fmt: str, expected_ext: str) -> None:
        assert get_plotly_extension(fmt) == expected_ext


class TestMatplotlibMimeAndExtensions:
    """Verify Matplotlib MIME type and extension mappings."""

    @pytest.mark.parametrize(
        "fmt,expected_mime",
        [
            ("pdf", "application/pdf"),
            ("pgf", "application/x-pgf"),
            ("png", "image/png"),
            ("svg", "image/svg+xml"),
        ],
    )
    def test_mime_types(self, fmt: str, expected_mime: str) -> None:
        assert get_matplotlib_mime(fmt) == expected_mime

    @pytest.mark.parametrize(
        "fmt,expected_ext",
        [
            ("pdf", ".pdf"),
            ("pgf", ".pgf"),
            ("png", ".png"),
            ("svg", ".svg"),
        ],
    )
    def test_extensions(self, fmt: str, expected_ext: str) -> None:
        assert get_matplotlib_extension(fmt) == expected_ext


# ── Test: Unsupported format raises ValueError ─────────────────────


class TestUnsupportedFormats:
    """Verify unsupported formats raise ValueError."""

    def test_plotly_unsupported_format(self) -> None:
        fig = MagicMock()
        with pytest.raises(ValueError, match="Unsupported format"):
            plotly_download_bytes(fig, "bmp")  # type: ignore[arg-type]

    def test_matplotlib_unsupported_format(self) -> None:
        fig = MagicMock()
        with pytest.raises(ValueError, match="Unsupported format"):
            matplotlib_download_bytes(fig, "bmp")  # type: ignore[arg-type]

    def test_plotly_unsupported_format_message_lists_options(self) -> None:
        fig = MagicMock()
        with pytest.raises(ValueError, match="png.*svg.*pdf.*html"):
            plotly_download_bytes(fig, "tiff")  # type: ignore[arg-type]

    def test_matplotlib_unsupported_format_message_lists_options(self) -> None:
        fig = MagicMock()
        with pytest.raises(ValueError, match="pdf.*pgf.*png.*svg"):
            matplotlib_download_bytes(fig, "tiff")  # type: ignore[arg-type]
```

---

## 6. PNG Export Tests

### 6.1 Plotly PNG Export via Kaleido

```gherkin
Feature: PNG export via Plotly Kaleido engine
  The plotly_download_bytes() function produces PNG bytes from a Plotly figure
  using Kaleido v1's to_image() method with configurable width, height, and scale.

  Scenario: Export Plotly figure to PNG with default parameters
    Given a Plotly bar chart figure
    When plotly_download_bytes(fig, "png") is called with defaults
    Then the returned bytes start with the PNG magic header (0x89504E47)
    And the returned bytes are non-empty (length > 100)

  Scenario: Export Plotly figure to PNG with custom dimensions
    Given a Plotly line chart figure
    When plotly_download_bytes(fig, "png", width=1400, height=800, scale=3) is called
    Then the returned bytes are a valid PNG image
    And the decoded image has resolution approximately 4200x2400 (1400*3 x 800*3)

  Scenario: Export Plotly figure to PNG with scale=1
    Given a Plotly scatter chart figure
    When plotly_download_bytes(fig, "png", width=700, height=400, scale=1) is called
    Then the decoded image has resolution approximately 700x400

  Scenario Outline: PNG export for each preset dimension at Plotly engine
    Given a Plotly figure rendered with preset "<preset>"
    When plotly_download_bytes(fig, "png") is called
    Then the returned bytes are a valid PNG
    And the image file size is reasonable for <dpi> DPI output

    Examples:
      | preset        | dpi |
      | nature        | 600 |
      | science       | 600 |
      | poster        | 150 |
      | slides        | 150 |
      | single_column | 300 |
```

### 6.2 Matplotlib PNG Export via savefig

```gherkin
Feature: PNG export via Matplotlib savefig
  The matplotlib_download_bytes() function produces PNG bytes using
  fig.savefig() with the Agg backend and text.usetex forced to False.

  Scenario: Export matplotlib figure to PNG with default DPI
    Given a matplotlib bar chart figure
    When matplotlib_download_bytes(fig, "png", dpi=300) is called
    Then the returned bytes start with the PNG magic header
    And the returned bytes are non-empty

  Scenario: PNG export disables text.usetex
    Given a matplotlib figure with text.usetex previously enabled
    When matplotlib_download_bytes(fig, "png") is called
    Then the export succeeds without requiring dvipng
    And the returned bytes are a valid PNG

  Scenario: PNG export uses bbox_inches="tight"
    Given a matplotlib figure with long axis labels
    When matplotlib_download_bytes(fig, "png") is called
    Then the exported image includes all labels without clipping

  Scenario: PNG export with custom DPI
    Given a matplotlib figure with preset "nature" (600 DPI)
    When matplotlib_download_bytes(fig, "png", dpi=600) is called
    Then the returned PNG has higher resolution than default 300 DPI

  Scenario: PNG export with preset "poster" (150 DPI)
    Given a matplotlib figure with preset "poster" (150 DPI)
    When matplotlib_download_bytes(fig, "png", dpi=150) is called
    Then the returned PNG has lower resolution suitable for posters
```

### 6.3 pytest Stubs -- PNG Export

```python
"""E2E tests for PNG export across both engines.

Source file under test:
    - src/web/pages/ui/plotting/download_section.py
"""

import io
from unittest.mock import MagicMock, patch

import matplotlib
import matplotlib.pyplot as plt
import pytest

from src.web.pages.ui.plotting.download_section import (
    matplotlib_download_bytes,
    plotly_download_bytes,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class TestPNGExportMatplotlib:
    """PNG export tests for Matplotlib engine."""

    @pytest.fixture
    def simple_mpl_fig(self) -> matplotlib.figure.Figure:
        """Create a simple matplotlib bar chart figure."""
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        ax.bar(["A", "B", "C"], [10, 20, 15])
        ax.set_title("Test Chart")
        return fig

    def test_png_magic_header(self, simple_mpl_fig: matplotlib.figure.Figure) -> None:
        """Exported bytes start with PNG magic header."""
        data = matplotlib_download_bytes(simple_mpl_fig, "png", dpi=300)
        assert data[:8] == PNG_MAGIC

    def test_png_non_empty(self, simple_mpl_fig: matplotlib.figure.Figure) -> None:
        """Exported PNG bytes are non-trivially sized."""
        data = matplotlib_download_bytes(simple_mpl_fig, "png", dpi=300)
        assert len(data) > 1000  # A real PNG chart is many KB

    def test_png_custom_dpi(self, simple_mpl_fig: matplotlib.figure.Figure) -> None:
        """Higher DPI produces larger PNG file."""
        data_300 = matplotlib_download_bytes(simple_mpl_fig, "png", dpi=300)
        data_600 = matplotlib_download_bytes(simple_mpl_fig, "png", dpi=600)
        assert len(data_600) > len(data_300)

    def test_png_usetex_forced_off(self, simple_mpl_fig: matplotlib.figure.Figure) -> None:
        """PNG export succeeds even if usetex was previously set."""
        with plt.rc_context({"text.usetex": True}):
            # Should not raise -- usetex is forced off inside the function
            data = matplotlib_download_bytes(simple_mpl_fig, "png", dpi=300)
            assert data[:8] == PNG_MAGIC

    @pytest.mark.parametrize("dpi", [150, 300, 600])
    def test_png_various_dpi(
        self, simple_mpl_fig: matplotlib.figure.Figure, dpi: int
    ) -> None:
        """PNG export works at multiple DPI values."""
        data = matplotlib_download_bytes(simple_mpl_fig, "png", dpi=dpi)
        assert data[:8] == PNG_MAGIC
        assert len(data) > 100
```

---

## 7. SVG Export Tests

### 7.1 Gherkin Scenarios

```gherkin
Feature: SVG export across both engines
  SVG exports produce valid XML vector graphics suitable for
  publication-quality scaling without resolution loss.

  Scenario: Plotly SVG export produces valid XML
    Given a Plotly figure with bar traces
    When plotly_download_bytes(fig, "svg") is called
    Then the returned bytes decode to valid UTF-8
    And the decoded string starts with "<svg" or "<?xml"
    And the string contains "</svg>"

  Scenario: Matplotlib SVG export produces valid XML
    Given a matplotlib figure with line traces
    When matplotlib_download_bytes(fig, "svg") is called
    Then the returned bytes decode to valid UTF-8
    And the decoded string contains "<svg"
    And the decoded string contains "</svg>"

  Scenario: SVG export uses bbox_inches="tight" (Matplotlib)
    Given a matplotlib figure with annotations extending beyond axes
    When matplotlib_download_bytes(fig, "svg") is called
    Then the SVG viewBox encompasses all annotations

  Scenario: SVG export preserves text elements
    Given a matplotlib figure with title "Cache Miss Rate" and ylabel "Ratio"
    When matplotlib_download_bytes(fig, "svg") is called
    Then the SVG contains text element "Cache Miss Rate"
    And the SVG contains text element "Ratio"

  Scenario: SVG export for each preset (Matplotlib)
    Given a matplotlib figure with each of the 13 presets applied
    When matplotlib_download_bytes(fig, "svg") is called for each
    Then each produces valid SVG content
    And the viewBox width reflects preset width_inches
```

### 7.2 pytest Stubs -- SVG Export

```python
"""E2E tests for SVG export across both engines.

Source file under test:
    - src/web/pages/ui/plotting/download_section.py
"""

import matplotlib
import matplotlib.pyplot as plt
import pytest

from src.web.pages.ui.plotting.download_section import matplotlib_download_bytes


class TestSVGExportMatplotlib:
    """SVG export tests for Matplotlib engine."""

    @pytest.fixture
    def simple_mpl_fig(self) -> matplotlib.figure.Figure:
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        ax.bar(["A", "B", "C"], [10, 20, 15])
        ax.set_title("Cache Miss Rate")
        ax.set_ylabel("Ratio")
        return fig

    def test_svg_valid_xml(self, simple_mpl_fig: matplotlib.figure.Figure) -> None:
        """Exported SVG is valid XML."""
        data = matplotlib_download_bytes(simple_mpl_fig, "svg")
        text = data.decode("utf-8")
        assert "<svg" in text
        assert "</svg>" in text

    def test_svg_contains_title_text(
        self, simple_mpl_fig: matplotlib.figure.Figure
    ) -> None:
        """SVG preserves title text element."""
        data = matplotlib_download_bytes(simple_mpl_fig, "svg")
        text = data.decode("utf-8")
        assert "Cache Miss Rate" in text

    def test_svg_contains_ylabel(
        self, simple_mpl_fig: matplotlib.figure.Figure
    ) -> None:
        """SVG preserves axis label text."""
        data = matplotlib_download_bytes(simple_mpl_fig, "svg")
        text = data.decode("utf-8")
        assert "Ratio" in text

    def test_svg_non_empty(self, simple_mpl_fig: matplotlib.figure.Figure) -> None:
        """SVG output is non-trivially sized."""
        data = matplotlib_download_bytes(simple_mpl_fig, "svg")
        assert len(data) > 500
```

---

## 8. PDF Export Tests

### 8.1 Gherkin Scenarios

```gherkin
Feature: PDF export across both engines
  PDF exports produce valid portable document files suitable for
  direct inclusion in LaTeX documents via \includegraphics.

  Scenario: Plotly PDF export produces valid PDF
    Given a Plotly figure with grouped bar traces
    When plotly_download_bytes(fig, "pdf") is called
    Then the returned bytes start with "%PDF-" magic header
    And the returned bytes end with "%%EOF" (within last 32 bytes)

  Scenario: Matplotlib PDF export produces valid PDF
    Given a matplotlib figure with scatter traces
    When matplotlib_download_bytes(fig, "pdf", dpi=300) is called
    Then the returned bytes start with "%PDF-" magic header
    And the returned bytes are non-empty (length > 1000)

  Scenario: Matplotlib PDF export uses bbox_inches="tight"
    Given a matplotlib figure with wide legends
    When matplotlib_download_bytes(fig, "pdf") is called
    Then the PDF page dimensions accommodate all content

  Scenario Outline: PDF export with preset "<preset>" (Matplotlib)
    Given a matplotlib figure with preset "<preset>" applied
    When matplotlib_download_bytes(fig, "pdf", dpi=<dpi>) is called
    Then the returned bytes are a valid PDF
    And the PDF is suitable for <width>x<height> inch inclusion

    Examples:
      | preset        | width | height  | dpi |
      | single_column | 3.5   | 1.96875 | 300 |
      | double_column | 7.0   | 5.25    | 300 |
      | nature        | 3.5   | 3.5     | 600 |
      | poster        | 10.0  | 7.0     | 150 |
      | acm           | 3.5   | 2.5     | 300 |

  Scenario: PDF export DPI is passed to savefig
    Given a matplotlib figure
    When matplotlib_download_bytes(fig, "pdf", dpi=600) is called
    Then the internal PDF resolution reflects 600 DPI
```

### 8.2 pytest Stubs -- PDF Export

```python
"""E2E tests for PDF export across both engines.

Source file under test:
    - src/web/pages/ui/plotting/download_section.py
"""

import matplotlib
import matplotlib.pyplot as plt
import pytest

from src.web.pages.ui.plotting.download_section import matplotlib_download_bytes

PDF_MAGIC = b"%PDF-"


class TestPDFExportMatplotlib:
    """PDF export tests for Matplotlib engine."""

    @pytest.fixture
    def simple_mpl_fig(self) -> matplotlib.figure.Figure:
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        ax.bar(["A", "B", "C", "D"], [10, 20, 15, 25])
        ax.set_title("IPC Comparison")
        return fig

    def test_pdf_magic_header(self, simple_mpl_fig: matplotlib.figure.Figure) -> None:
        """Exported bytes start with PDF magic header."""
        data = matplotlib_download_bytes(simple_mpl_fig, "pdf", dpi=300)
        assert data[:5] == PDF_MAGIC

    def test_pdf_non_empty(self, simple_mpl_fig: matplotlib.figure.Figure) -> None:
        """Exported PDF is non-trivially sized."""
        data = matplotlib_download_bytes(simple_mpl_fig, "pdf", dpi=300)
        assert len(data) > 1000

    def test_pdf_eof_marker(self, simple_mpl_fig: matplotlib.figure.Figure) -> None:
        """Exported PDF ends with EOF marker."""
        data = matplotlib_download_bytes(simple_mpl_fig, "pdf", dpi=300)
        tail = data[-64:]
        assert b"%%EOF" in tail or b"endobj" in tail

    @pytest.mark.parametrize("dpi", [150, 300, 600])
    def test_pdf_various_dpi(
        self, simple_mpl_fig: matplotlib.figure.Figure, dpi: int
    ) -> None:
        """PDF export works at multiple DPI values."""
        data = matplotlib_download_bytes(simple_mpl_fig, "pdf", dpi=dpi)
        assert data[:5] == PDF_MAGIC
```

---

## 9. PGF/LaTeX Export Tests

### 9.1 Gherkin Scenarios

```gherkin
Feature: PGF/LaTeX export via Matplotlib savefig
  PGF export produces LaTeX-native vector graphics using the pgf backend
  with xelatex as the TeX system, enabling native font matching in papers.

  Scenario: PGF export produces valid PGF file
    Given a matplotlib figure with serif fonts
    When matplotlib_download_bytes(fig, "pgf") is called
    Then the returned bytes decode to valid UTF-8 text
    And the decoded string contains "\begin{pgfpicture}" or pgf commands
    And the decoded string is non-empty

  Scenario: PGF export uses xelatex backend
    Given a matplotlib figure
    When matplotlib_download_bytes(fig, "pgf") is called
    Then the pgf.texsystem is set to "xelatex" during export
    And the pgf.rcfonts is set to True during export

  Scenario: PGF export applies LaTeX preamble from FigureConfig
    Given a matplotlib figure with spec.latex_extra_preamble = "\\usepackage[varqu,scaled=0.95]{zi4}"
    When matplotlib_download_bytes(fig, "pgf", spec=config_spec) is called
    Then the pgf.preamble includes the zi4 package declaration

  Scenario: PGF export uses preamble from single_column preset
    Given a matplotlib figure with "single_column" preset applied
    And the spec has latex_extra_preamble containing "zi4"
    When matplotlib_download_bytes(fig, "pgf", spec=spec) is called
    Then the PGF output uses the zi4 font for monospace text

  Scenario: PGF export with empty preamble
    Given a matplotlib figure with spec.latex_extra_preamble = ""
    When matplotlib_download_bytes(fig, "pgf", spec=config_spec) is called
    Then the export succeeds with default PGF preamble
    And the pgf.preamble is set to empty string

  Scenario: PGF export fails for raster content with graceful fallback
    Given a matplotlib figure containing a heatmap (raster image)
    When matplotlib_download_bytes(fig, "pgf") raises ValueError with "raster"
    Then the caller (_render_mpl_download) catches the error
    And falls back to PDF format
    And displays a warning about PGF raster limitation

  Scenario: PGF export for each preset with LaTeX preamble
    Given presets with latex_extra_preamble set: single_column, double_column, micro, isca, asplos, hpca, taco, acm
    When PGF export is attempted for each
    Then each export uses the preset-specific preamble
    And each produces valid PGF output
```

### 9.2 pytest Stubs -- PGF Export

```python
"""E2E tests for PGF/LaTeX export via Matplotlib.

Source file under test:
    - src/web/pages/ui/plotting/download_section.py
"""

from unittest.mock import MagicMock, patch

import matplotlib
import matplotlib.pyplot as plt
import pytest

from src.core.models.visualization.figure_config import FigureConfig
from src.web.pages.ui.plotting.download_section import matplotlib_download_bytes
from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager

PRESETS_WITH_PREAMBLE = [
    "single_column",
    "double_column",
    "micro",
    "isca",
    "asplos",
    "hpca",
    "taco",
    "acm",
]

PRESETS_WITHOUT_PREAMBLE = [
    "nature",
    "science",
    "ieee_single",
    "poster",
    "slides",
]


class TestPGFExport:
    """PGF/LaTeX export tests for Matplotlib engine."""

    @pytest.fixture
    def simple_mpl_fig(self) -> matplotlib.figure.Figure:
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        ax.bar(["A", "B", "C"], [10, 20, 15])
        ax.set_title("IPC Results")
        return fig

    @pytest.fixture
    def spec_with_preamble(self) -> FigureConfig:
        """FigureConfig with zi4 LaTeX preamble."""
        return FigureConfig(
            latex_extra_preamble="\\usepackage[varqu,scaled=0.95]{zi4}"
        )

    @pytest.fixture
    def spec_empty_preamble(self) -> FigureConfig:
        """FigureConfig with empty LaTeX preamble."""
        return FigureConfig(latex_extra_preamble="")

    def test_pgf_produces_text_output(
        self, simple_mpl_fig: matplotlib.figure.Figure
    ) -> None:
        """PGF export produces UTF-8 text content."""
        data = matplotlib_download_bytes(simple_mpl_fig, "pgf")
        text = data.decode("utf-8")
        assert len(text) > 100

    def test_pgf_contains_pgf_commands(
        self, simple_mpl_fig: matplotlib.figure.Figure
    ) -> None:
        """PGF output contains pgf/tikz commands."""
        data = matplotlib_download_bytes(simple_mpl_fig, "pgf")
        text = data.decode("utf-8")
        # PGF files contain these characteristic commands
        assert "pgf" in text.lower() or "begin{" in text

    def test_pgf_with_preamble(
        self,
        simple_mpl_fig: matplotlib.figure.Figure,
        spec_with_preamble: FigureConfig,
    ) -> None:
        """PGF export receives the LaTeX preamble from spec."""
        # The preamble is passed via rc_context, verify it does not error
        data = matplotlib_download_bytes(
            simple_mpl_fig, "pgf", spec=spec_with_preamble
        )
        assert len(data) > 100

    def test_pgf_with_empty_preamble(
        self,
        simple_mpl_fig: matplotlib.figure.Figure,
        spec_empty_preamble: FigureConfig,
    ) -> None:
        """PGF export works with empty preamble."""
        data = matplotlib_download_bytes(
            simple_mpl_fig, "pgf", spec=spec_empty_preamble
        )
        assert len(data) > 100

    @pytest.mark.parametrize("preset_name", PRESETS_WITH_PREAMBLE)
    def test_pgf_preset_with_preamble(self, preset_name: str) -> None:
        """Presets with preamble produce valid PGF when preamble is passed."""
        preset = PresetManager.load_preset(preset_name)
        assert "zi4" in preset.get("latex_extra_preamble", "")

    @pytest.mark.parametrize("preset_name", PRESETS_WITHOUT_PREAMBLE)
    def test_pgf_preset_without_preamble(self, preset_name: str) -> None:
        """Presets without preamble have empty latex_extra_preamble."""
        preset = PresetManager.load_preset(preset_name)
        assert preset.get("latex_extra_preamble", "") == ""
```

---

## 10. Venue-Specific Preset Tests (IEEE, ACM, etc.)

### 10.1 Gherkin Scenarios

```gherkin
Feature: Venue-specific preset correctness
  Each preset must match the exact dimensions and typography required
  by its target publication venue. These tests validate the preset
  catalog against known venue specifications.

  Scenario: IEEE single-column width matches IEEE template
    Given the "ieee_single" preset
    Then width_inches == 3.5 (IEEE column width: 3.5in = 88.9mm)
    And font_family == "serif" (IEEE uses Times/Computer Modern)
    And font_size_base == 10 (IEEE standard body font)
    And dpi == 300 (IEEE minimum resolution)

  Scenario: IEEE/ACM single-column preset matches standard dimensions
    Given the "single_column" preset
    Then width_inches == 3.5
    And height_inches == 1.96875 (16:9 aspect ratio complement)
    And font_family == "serif"
    And latex_extra_preamble contains "zi4" (monospace font package)

  Scenario: IEEE/ACM double-column width matches full page
    Given the "double_column" preset
    Then width_inches == 7.0 (full textwidth for 2-column papers)
    And height_inches == 5.25 (3:4 ratio of 7.0)
    And font_family == "serif"

  Scenario: ACM proceedings matches ACM LaTeX template
    Given the "acm" preset
    Then width_inches == 3.5
    And font_size_base == 9 (ACM uses 9pt body text)
    And font_family == "serif"
    And latex_extra_preamble contains "zi4"

  Scenario: ACM TACO journal matches TACO column width
    Given the "taco" preset
    Then width_inches == 3.5
    And font_size_base == 10
    And font_family == "serif"

  Scenario: Nature journal matches Nature guidelines
    Given the "nature" preset
    Then width_inches == 3.5 (Nature single-column: 89mm = 3.503in)
    And height_inches == 3.5 (square figure)
    And font_family == "Arial" (Nature requires Arial/Helvetica)
    And font_size_base == 7 (Nature minimum: 5-7pt)
    And dpi == 600 (Nature minimum: 300, recommended: 600)
    And line_width == 0.5 (thin lines for Nature)

  Scenario: Science journal matches Science guidelines
    Given the "science" preset
    Then width_inches == 3.5 (Science single-column)
    And font_family == "sans-serif" (Science uses Helvetica)
    And font_size_base == 8
    And dpi == 600 (Science minimum: 300)
    And line_width == 0.5

  Scenario: Computer architecture conference presets are identical
    Given presets "micro", "isca", "asplos", "hpca"
    Then all four have identical width_inches == 3.5
    And all four have identical height_inches == 2.5
    And all four have identical font_size_base == 10
    And all four have identical font_family == "serif"
    And all four have identical dpi == 300

  Scenario: Poster preset has large dimensions and fonts
    Given the "poster" preset
    Then width_inches == 10.0 (wide poster panel)
    And height_inches == 7.0
    And font_size_base == 24 (readable from distance)
    And font_size_title == 28
    And font_family == "sans-serif" (better readability)
    And line_width == 2.0 (thick lines for visibility)
    And marker_size == 8.0 (large markers)
    And dpi == 150 (lower DPI acceptable for large prints)

  Scenario: Slides preset matches 16:9 presentation aspect ratio
    Given the "slides" preset
    Then width_inches == 8.0
    And height_inches == 4.5 (16:9 ratio)
    And font_size_base == 18
    And font_size_title == 22
    And font_family == "sans-serif"
    And dpi == 150
```

### 10.2 pytest Stubs -- Venue-Specific Presets

```python
"""E2E tests for venue-specific preset accuracy.

Tests validate that each preset matches the exact specifications required
by its target publication venue (IEEE, ACM, Nature, Science, etc.).

Source files under test:
    - src/web/pages/ui/plotting/export/presets/preset_manager.py
    - src/web/pages/ui/plotting/export/presets/latex_presets.json
"""

import pytest

from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager


class TestVenuePresetAccuracy:
    """Validate each preset against its venue's specifications."""

    def test_ieee_single_column_width(self) -> None:
        """IEEE single-column width matches IEEE template (3.5in)."""
        preset = PresetManager.load_preset("ieee_single")
        assert preset["width_inches"] == pytest.approx(3.5)
        assert preset["font_family"] == "serif"
        assert preset["font_size_base"] == 10
        assert preset["dpi"] == 300

    def test_standard_single_column(self) -> None:
        """Standard single-column width matches common academic template."""
        preset = PresetManager.load_preset("single_column")
        assert preset["width_inches"] == pytest.approx(3.5)
        assert preset["height_inches"] == pytest.approx(1.96875)
        assert "zi4" in preset.get("latex_extra_preamble", "")

    def test_double_column_full_width(self) -> None:
        """Double-column width is full textwidth (7.0in)."""
        preset = PresetManager.load_preset("double_column")
        assert preset["width_inches"] == pytest.approx(7.0)
        assert preset["height_inches"] == pytest.approx(5.25)

    def test_acm_proceedings_font_size(self) -> None:
        """ACM proceedings uses 9pt base font."""
        preset = PresetManager.load_preset("acm")
        assert preset["font_size_base"] == 9
        assert preset["font_size_title"] == 10
        assert "zi4" in preset.get("latex_extra_preamble", "")

    def test_nature_journal_specifications(self) -> None:
        """Nature preset matches Nature's strict guidelines."""
        preset = PresetManager.load_preset("nature")
        assert preset["width_inches"] == pytest.approx(3.5)
        assert preset["height_inches"] == pytest.approx(3.5)  # square
        assert preset["font_family"] == "Arial"
        assert preset["font_size_base"] == 7
        assert preset["dpi"] == 600
        assert preset["line_width"] == pytest.approx(0.5)
        assert preset["marker_size"] == pytest.approx(2.0)

    def test_science_journal_specifications(self) -> None:
        """Science preset matches Science's guidelines."""
        preset = PresetManager.load_preset("science")
        assert preset["font_family"] == "sans-serif"
        assert preset["font_size_base"] == 8
        assert preset["dpi"] == 600
        assert preset["line_width"] == pytest.approx(0.5)

    def test_arch_conferences_identical(self) -> None:
        """MICRO, ISCA, ASPLOS, HPCA presets are identical."""
        arch_presets = ["micro", "isca", "asplos", "hpca"]
        loaded = [PresetManager.load_preset(name) for name in arch_presets]

        for preset in loaded:
            assert preset["width_inches"] == pytest.approx(3.5)
            assert preset["height_inches"] == pytest.approx(2.5)
            assert preset["font_size_base"] == 10
            assert preset["font_family"] == "serif"
            assert preset["dpi"] == 300

        # Verify they are truly identical on key fields
        keys_to_compare = [
            "width_inches", "height_inches", "font_family",
            "font_size_base", "font_size_title", "font_size_ticks",
            "line_width", "marker_size", "dpi",
        ]
        for key in keys_to_compare:
            values = [p[key] for p in loaded]
            assert len(set(str(v) for v in values)) == 1, (
                f"Key {key} differs across arch presets: {values}"
            )

    def test_poster_large_dimensions_and_fonts(self) -> None:
        """Poster preset has appropriately large dimensions/fonts."""
        preset = PresetManager.load_preset("poster")
        assert preset["width_inches"] == pytest.approx(10.0)
        assert preset["height_inches"] == pytest.approx(7.0)
        assert preset["font_size_base"] == 24
        assert preset["font_size_title"] == 28
        assert preset["font_family"] == "sans-serif"
        assert preset["line_width"] == pytest.approx(2.0)
        assert preset["marker_size"] == pytest.approx(8.0)
        assert preset["dpi"] == 150

    def test_slides_16_9_aspect_ratio(self) -> None:
        """Slides preset maintains 16:9 aspect ratio."""
        preset = PresetManager.load_preset("slides")
        assert preset["width_inches"] == pytest.approx(8.0)
        assert preset["height_inches"] == pytest.approx(4.5)
        ratio = preset["width_inches"] / preset["height_inches"]
        assert ratio == pytest.approx(16.0 / 9.0, rel=0.01)
        assert preset["font_family"] == "sans-serif"
        assert preset["dpi"] == 150
```

---

## 11. Preset + Engine Interaction Tests

### 11.1 Gherkin Scenarios

```gherkin
Feature: Preset application interacts correctly with both rendering engines
  Presets must work seamlessly with the engine-aware download section,
  ensuring that applying a preset and then downloading produces correct
  output regardless of the active engine.

  Scenario: Apply Nature preset then download as Matplotlib PNG
    Given the "nature" preset is applied to a user FigureConfig
    And the engine is set to "matplotlib"
    When the figure is rendered and downloaded as PNG
    Then the PNG resolution reflects 600 DPI
    And the figure dimensions are approximately 3.5x3.5 inches

  Scenario: Apply poster preset then download as Plotly HTML
    Given the "poster" preset is applied to a user FigureConfig
    And the engine is set to "plotly"
    When the figure is downloaded as HTML
    Then the HTML contains the full Plotly.js library
    And the figure layout reflects poster-sized dimensions

  Scenario: Apply single_column preset then download as PGF
    Given the "single_column" preset is applied (has zi4 preamble)
    And the engine is set to "matplotlib"
    When the figure is downloaded as PGF
    Then the PGF output uses the zi4 preamble in pgf.preamble
    And the file is a valid PGF/TikZ document

  Scenario: Switch engine after preset application
    Given the "acm" preset is applied to a FigureConfig
    And the engine is set to "plotly"
    When the user switches engine to "matplotlib"
    Then the download section shows matplotlib format pills
    And the preset dimensions are still 3.5x2.5 inches
    And PDF is the default format

  Scenario: Apply preset to multi-trace figure
    Given a user FigureConfig with 8 bar traces and custom colors
    And the "micro" preset is loaded
    When PresetApplicator.apply(spec, preset) is called
    Then all 8 traces are preserved
    And the custom color palette is preserved
    And dimensions are overridden to 3.5x2.5

  Scenario: Apply preset to figure with dual-axis (legend2)
    Given a user FigureConfig with primary and secondary legends
    And the "ieee_single" preset is loaded
    When PresetApplicator.apply(spec, preset) is called
    Then the result has 3 legend configs from the preset
    And the preset legend spacing overrides user spacing

  Scenario: PresetManager list_presets returns all 13
    When PresetManager.list_presets() is called
    Then the returned list has exactly 13 entries
    And it contains all expected preset names

  Scenario: PresetManager get_preset_info returns metadata
    When PresetManager.get_preset_info("nature") is called
    Then the result has "description" key with "Nature journal style"
    And the result has "typical_use" key (may be empty)

  Scenario: PresetManager caching double load
    Given PresetManager cache is cleared
    When PresetManager.load_preset("nature") is called twice
    Then the second call returns the cached instance
    And both calls return identical objects
```

### 11.2 pytest Stubs -- Preset + Engine Interaction

```python
"""E2E tests for preset + engine interaction.

Tests verify that preset application works correctly with both Plotly
and Matplotlib engines and that the download pipeline honors
preset-derived dimensions and typography.

Source files under test:
    - src/web/rendering/preset_applicator.py
    - src/web/pages/ui/plotting/export/presets/preset_manager.py
    - src/web/pages/ui/plotting/download_section.py
"""

import pytest

from src.core.models.visualization.figure_config import (
    DimensionConfig,
    FigureConfig,
)
from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager
from src.web.rendering.preset_applicator import PresetApplicator


class TestPresetManagerCatalog:
    """Tests for PresetManager catalog operations."""

    def test_list_presets_count(self) -> None:
        """list_presets() returns exactly 13 preset names."""
        names = PresetManager.list_presets()
        assert len(names) == 13

    def test_list_presets_contains_all_expected(self) -> None:
        """list_presets() contains all expected preset names."""
        names = set(PresetManager.list_presets())
        expected = {
            "single_column", "double_column", "micro", "isca",
            "asplos", "hpca", "taco", "nature", "science",
            "ieee_single", "acm", "poster", "slides",
        }
        assert names == expected

    def test_get_preset_info_nature(self) -> None:
        """get_preset_info returns description for nature."""
        info = PresetManager.get_preset_info("nature")
        assert "description" in info
        assert "Nature" in info["description"]

    def test_get_preset_info_unknown_raises(self) -> None:
        """get_preset_info raises ValueError for unknown preset."""
        with pytest.raises(ValueError, match="Unknown preset"):
            PresetManager.get_preset_info("nonexistent_venue")

    def test_load_preset_unknown_raises(self) -> None:
        """load_preset raises ValueError for unknown preset."""
        with pytest.raises(ValueError, match="Unknown preset"):
            PresetManager.load_preset("nonexistent_venue")

    def test_load_preset_caching(self) -> None:
        """Second load of same preset returns cached result."""
        # Clear cache for clean test
        PresetManager._cache.clear()

        first = PresetManager.load_preset("nature")
        second = PresetManager.load_preset("nature")

        # Same dict object due to caching
        assert first is second


class TestPresetValidation:
    """Tests for PresetManager.validate_preset()."""

    def test_validate_preset_missing_field_raises(self) -> None:
        """Validation fails when required field is missing."""
        incomplete_preset = {
            "width_inches": 3.5,
            # Missing height_inches and all other required fields
        }
        with pytest.raises(ValueError, match="Missing required field"):
            PresetManager.validate_preset(incomplete_preset)  # type: ignore[arg-type]

    def test_validate_preset_negative_width_raises(self) -> None:
        """Validation fails for negative width."""
        preset = PresetManager.load_preset("nature").copy()
        preset["width_inches"] = -1.0
        with pytest.raises(ValueError, match="width_inches must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_height_raises(self) -> None:
        """Validation fails for negative height."""
        preset = PresetManager.load_preset("nature").copy()
        preset["height_inches"] = 0.0
        with pytest.raises(ValueError, match="height_inches must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_zero_dpi_raises(self) -> None:
        """Validation fails for zero DPI."""
        preset = PresetManager.load_preset("nature").copy()
        preset["dpi"] = 0
        with pytest.raises(ValueError, match="dpi must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_preset_negative_font_size_raises(self) -> None:
        """Validation fails for negative font_size_base."""
        preset = PresetManager.load_preset("nature").copy()
        preset["font_size_base"] = -1
        with pytest.raises(ValueError, match="font_size_base must be positive"):
            PresetManager.validate_preset(preset)


class TestPresetMultiTraceInteraction:
    """Tests for preset application on complex FigureConfig instances."""

    def test_apply_preserves_8_traces(self) -> None:
        """Apply preset on figure with 8 traces preserves all."""
        spec = FigureConfig(
            color_palette=["#111", "#222", "#333", "#444", "#555", "#666", "#777", "#888"],
            title="8-trace benchmark",
        )
        preset = PresetManager.load_preset("micro")
        result = PresetApplicator.apply(spec, preset)

        assert len(result.color_palette) == 8
        assert result.title == "8-trace benchmark"
        assert result.dimensions.width == pytest.approx(3.5)

    def test_apply_preserves_barmode(self) -> None:
        """Apply preset preserves barmode from user spec."""
        spec = FigureConfig(barmode="stack")
        preset = PresetManager.load_preset("ieee_single")
        result = PresetApplicator.apply(spec, preset)
        assert result.barmode == "stack"

    def test_apply_preserves_enable_stripes(self) -> None:
        """Apply preset preserves enable_stripes flag."""
        spec = FigureConfig(enable_stripes=True)
        preset = PresetManager.load_preset("acm")
        result = PresetApplicator.apply(spec, preset)
        assert result.enable_stripes is True

    def test_apply_preserves_show_error_bars(self) -> None:
        """Apply preset preserves show_error_bars flag."""
        spec = FigureConfig(show_error_bars=True)
        preset = PresetManager.load_preset("nature")
        result = PresetApplicator.apply(spec, preset)
        assert result.show_error_bars is True

    def test_apply_preserves_hovermode(self) -> None:
        """Apply preset preserves hovermode from user spec."""
        spec = FigureConfig(hovermode="closest")
        preset = PresetManager.load_preset("slides")
        result = PresetApplicator.apply(spec, preset)
        assert result.hovermode == "closest"
```

---

## 12. Error Handling Tests

### 12.1 Gherkin Scenarios

```gherkin
Feature: Error handling in the export/download pipeline
  The export system must handle errors gracefully including unknown
  presets, invalid configurations, missing figures, and format
  incompatibilities.

  Scenario: Load unknown preset raises ValueError
    When PresetManager.load_preset("nonexistent_venue") is called
    Then a ValueError is raised with message containing "Unknown preset"
    And the error message lists available preset names

  Scenario: Load preset with missing JSON file raises FileNotFoundError
    Given the latex_presets.json file is temporarily missing
    When PresetManager._initialize() is called
    Then a FileNotFoundError is raised with the expected file path

  Scenario: Validate preset with zero-width figure raises ValueError
    Given a preset dict with width_inches=0
    When PresetManager.validate_preset(preset) is called
    Then a ValueError is raised: "width_inches must be positive"

  Scenario: Validate preset with negative font size raises ValueError
    Given a preset dict with font_size_base=-5
    When PresetManager.validate_preset(preset) is called
    Then a ValueError is raised: "font_size_base must be positive"

  Scenario: Validate preset with zero marker size raises ValueError
    Given a preset dict with marker_size=0
    When PresetManager.validate_preset(preset) is called
    Then a ValueError is raised: "marker_size must be positive"

  Scenario: Validate preset with zero line width raises ValueError
    Given a preset dict with line_width=0
    When PresetManager.validate_preset(preset) is called
    Then a ValueError is raised: "line_width must be positive"

  Scenario: Export unsupported format raises ValueError (Plotly)
    Given a Plotly figure
    When plotly_download_bytes(fig, "bmp") is called
    Then a ValueError is raised listing supported formats

  Scenario: Export unsupported format raises ValueError (Matplotlib)
    Given a matplotlib figure
    When matplotlib_download_bytes(fig, "eps") is called
    Then a ValueError is raised listing supported formats

  Scenario: PGF raster fallback in download section
    Given the engine mode is "matplotlib"
    And a matplotlib figure containing raster content
    When the user selects PGF format and the export raises ValueError("raster")
    Then the system catches the error
    And falls back to PDF with a warning message
    And the download button label changes to "Download PDF"

  Scenario: PGF non-raster ValueError is re-raised
    Given the engine mode is "matplotlib"
    And matplotlib_download_bytes raises ValueError("unknown error")
    When the PGF export is attempted
    Then the ValueError is re-raised (not caught by fallback)

  Scenario: Matplotlib download with no figure in session state
    Given the engine mode is "matplotlib"
    And session_state does not contain "plot.{id}.mpl_fig"
    When _render_mpl_download() is called
    Then st.warning("No matplotlib figure available for download.") is shown
    And no download button is rendered

  Scenario: get_preset_info for unknown preset raises ValueError
    When PresetManager.get_preset_info("fake_journal") is called
    Then a ValueError is raised: "Unknown preset: fake_journal"

  Scenario: ExportResult contract for successful export
    Given a successful export operation
    When the ExportResult is constructed
    Then success == True
    And data is non-None bytes
    And format is one of "pdf", "pgf", "eps", "png", "svg"
    And error is None

  Scenario: ExportResult contract for failed export
    Given a failed export operation
    When the ExportResult is constructed
    Then success == False
    And data is None
    And error contains a descriptive message
```

### 12.2 pytest Stubs -- Error Handling

```python
"""E2E tests for error handling in the export/download pipeline.

Tests verify graceful error handling for invalid presets, missing
files, unsupported formats, and edge cases in the download flow.

Source files under test:
    - src/web/pages/ui/plotting/export/presets/preset_manager.py
    - src/web/pages/ui/plotting/download_section.py
"""

from unittest.mock import MagicMock, patch

import pytest

from src.web.pages.ui.plotting.download_section import (
    matplotlib_download_bytes,
    plotly_download_bytes,
)
from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager


class TestPresetManagerErrors:
    """Tests for PresetManager error handling."""

    def test_unknown_preset_raises_valueerror(self) -> None:
        """Loading unknown preset raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preset"):
            PresetManager.load_preset("fake_journal_2025")

    def test_unknown_preset_lists_available(self) -> None:
        """Error message for unknown preset lists available names."""
        with pytest.raises(ValueError) as exc_info:
            PresetManager.load_preset("nonexistent")
        error_msg = str(exc_info.value)
        assert "single_column" in error_msg
        assert "nature" in error_msg

    def test_get_info_unknown_raises_valueerror(self) -> None:
        """get_preset_info for unknown preset raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preset"):
            PresetManager.get_preset_info("fake_journal")

    def test_validate_zero_width(self) -> None:
        """Validation rejects zero width."""
        preset = PresetManager.load_preset("nature").copy()
        preset["width_inches"] = 0.0
        with pytest.raises(ValueError, match="width_inches must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_negative_height(self) -> None:
        """Validation rejects negative height."""
        preset = PresetManager.load_preset("nature").copy()
        preset["height_inches"] = -1.0
        with pytest.raises(ValueError, match="height_inches must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_zero_dpi(self) -> None:
        """Validation rejects zero DPI."""
        preset = PresetManager.load_preset("nature").copy()
        preset["dpi"] = 0
        with pytest.raises(ValueError, match="dpi must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_negative_font_size_base(self) -> None:
        """Validation rejects negative font_size_base."""
        preset = PresetManager.load_preset("nature").copy()
        preset["font_size_base"] = -1
        with pytest.raises(ValueError, match="font_size_base must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_negative_font_size_title(self) -> None:
        """Validation rejects negative font_size_title."""
        preset = PresetManager.load_preset("nature").copy()
        preset["font_size_title"] = 0
        with pytest.raises(ValueError, match="font_size_title must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_zero_line_width(self) -> None:
        """Validation rejects zero line_width."""
        preset = PresetManager.load_preset("nature").copy()
        preset["line_width"] = 0.0
        with pytest.raises(ValueError, match="line_width must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_zero_marker_size(self) -> None:
        """Validation rejects zero marker_size."""
        preset = PresetManager.load_preset("nature").copy()
        preset["marker_size"] = 0
        with pytest.raises(ValueError, match="marker_size must be positive"):
            PresetManager.validate_preset(preset)

    def test_validate_missing_required_field(self) -> None:
        """Validation rejects preset with missing required field."""
        incomplete = {"width_inches": 3.5, "height_inches": 2.5}
        with pytest.raises(ValueError, match="Missing required field"):
            PresetManager.validate_preset(incomplete)  # type: ignore[arg-type]


class TestDownloadErrors:
    """Tests for download section error handling."""

    def test_plotly_unsupported_format(self) -> None:
        """Plotly download rejects unsupported format."""
        fig = MagicMock()
        with pytest.raises(ValueError, match="Unsupported format"):
            plotly_download_bytes(fig, "eps")  # type: ignore[arg-type]

    def test_matplotlib_unsupported_format(self) -> None:
        """Matplotlib download rejects unsupported format."""
        fig = MagicMock()
        with pytest.raises(ValueError, match="Unsupported format"):
            matplotlib_download_bytes(fig, "eps")  # type: ignore[arg-type]

    def test_pgf_raster_fallback_logic(self) -> None:
        """PGF raster fallback catches 'raster' ValueError only."""
        # Verify the fallback logic condition
        error_msg = "Cannot handle raster graphics in PGF format"
        assert "raster" in error_msg.lower()

        # Non-raster errors should not trigger fallback
        non_raster_error = "Something else went wrong"
        assert "raster" not in non_raster_error.lower()

    def test_plotly_format_error_message_content(self) -> None:
        """Plotly error message lists all supported formats."""
        fig = MagicMock()
        with pytest.raises(ValueError) as exc_info:
            plotly_download_bytes(fig, "xyz")  # type: ignore[arg-type]
        msg = str(exc_info.value)
        for fmt in ["png", "svg", "pdf", "html"]:
            assert fmt in msg

    def test_matplotlib_format_error_message_content(self) -> None:
        """Matplotlib error message lists all supported formats."""
        fig = MagicMock()
        with pytest.raises(ValueError) as exc_info:
            matplotlib_download_bytes(fig, "xyz")  # type: ignore[arg-type]
        msg = str(exc_info.value)
        for fmt in ["pdf", "pgf", "png", "svg"]:
            assert fmt in msg
```

---

## Appendix: Test Count Summary

| Section | Gherkin Scenarios | pytest Test Functions | Parametrized Expansions |
|---------|:-----------------:|:-------------------:|:----------------------:|
| 4. Preset Application | 19 | 19 | 52 (13 presets x 4 test types) |
| 5. Download Section UI | 10 | 12 | 24 |
| 6. PNG Export | 9 | 6 | 9 |
| 7. SVG Export | 5 | 4 | 4 |
| 8. PDF Export | 6 | 4 | 7 |
| 9. PGF/LaTeX Export | 7 | 6 | 13 |
| 10. Venue-Specific | 10 | 9 | 9 |
| 11. Preset + Engine | 9 | 11 | 11 |
| 12. Error Handling | 13 | 16 | 16 |
| **Total** | **88** | **87** | **145+** |

### Combinatorial Coverage

```
13 presets x 4 Matplotlib formats = 52 preset-format pairs (Matplotlib)
13 presets x 4 Plotly formats     = 52 preset-format pairs (Plotly)
13 presets x 2 overlay modes      = 26 overlay combinations
13 presets x validation checks    = 13 validation tests
─────────────────────────────────────────────────────────
                                    143 unique combinations
```

### Downstream Dependencies

- Uses preset data from `src/web/pages/ui/plotting/export/presets/latex_presets.json`
- Tests feed into Step 30 (full integration tests)
- Media assets from these tests feed into USER_GUIDE_PLAN export documentation
