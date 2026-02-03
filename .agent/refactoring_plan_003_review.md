# Refactoring Plan: Export Feature Production Readiness

**Branch**: `003/review`
**Goal**: Reduce complexity, increase reusability, add comprehensive tests
**Status**: Phase 2 - Architecture Review

## Executive Summary

This document outlines the comprehensive refactoring plan for the LaTeX export features to achieve production-ready code quality. The implementation currently has 5 functions with excessive complexity (>10) and 25 missing test cases.

**Current State**:
- ✅ All features working correctly (93 tests passing)
- ⚠️ High complexity in 5 key functions
- ⚠️ Missing 25 test cases for new features
- ⚠️ Some functions violate Single Responsibility Principle

**Target State**:
- ✅ All functions <100 lines, complexity <10
- ✅ 100% test coverage for new features (118+ tests)
- ✅ Extracted reusable components following SOLID principles
- ✅ Comprehensive documentation

## Complexity Audit Results

### Critical Functions Requiring Refactoring

| Function | File | Lines | Complexity | Priority |
|----------|------|-------|------------|----------|
| `apply_to_matplotlib()` | layout_mapper.py | 325 | 39 | **CRITICAL** |
| `extract_layout()` | layout_mapper.py | 154 | 39 | **CRITICAL** |
| `_convert_bar_trace()` | matplotlib_converter.py | 181 | 31 | HIGH |
| `_render_download_button()` | plot_renderer.py | 521 | 13 | HIGH |
| `render_plot()` | plot_renderer.py | 124 | 18 | MEDIUM |

### Test Coverage Gaps

| Feature | Missing Tests | Files Affected |
|---------|---------------|----------------|
| ylabel_y_position | 5 | schema, preset_manager, layout_mapper, UI, portfolio |
| Separate font sizes | 9 | schema (3), presets (1), appliers (3), UI, portfolio |
| Bold styling | 11 | schema (6), presets, appliers (6), UI, default, portfolio |
| **TOTAL** | **25** | **5 modules** |

---

## Phase 2: Detailed Refactoring Design

### 2.1 Layout Mapper Refactoring

#### File: `src/plotting/export/converters/layout_mapper.py`

**Current Issues**:
1. `extract_layout()`: 154 lines, complexity 39
   - Extracts 10+ different layout properties in one function
   - Complex annotation filtering logic
   - Y-axis label detection from annotations

2. `apply_to_matplotlib()`: 325 lines, complexity 39
   - Applies 7+ different categories of layout properties
   - Complex annotation handling with coordinate transformations
   - Group separator drawing logic embedded

**Refactoring Strategy**:

#### A. Extract `extract_layout()` into 4 functions

```python
# New structure (target: each <50 lines, complexity <10)

@dataclass
class LayoutExtractor:
    """Coordinates layout extraction from Plotly figures."""

    def extract_layout(self, figure: go.Figure) -> Dict[str, Any]:
        """Main extraction orchestrator (target: 20 lines)."""
        layout_dict = {}
        layout_dict.update(self._extract_axis_properties(figure.layout))
        layout_dict.update(self._extract_legend_settings(figure.layout))
        layout_dict.update(self._extract_annotations(figure.layout))
        return layout_dict

    def _extract_axis_properties(self, layout) -> Dict[str, Any]:
        """Extract axis ranges, labels, scales, grids, ticks (40 lines)."""
        # Handles: x_range, y_range, x_label, y_label, title
        # x_grid, y_grid, x_type, y_type
        # x_tickvals, y_tickvals, x_ticktext, y_ticktext

    def _extract_legend_settings(self, layout) -> Dict[str, Any]:
        """Extract legend position and anchor (20 lines)."""
        # Handles: legend dict with x, y, xanchor, yanchor

    def _extract_annotations(self, layout) -> Dict[str, Any]:
        """Extract and filter annotations (60 lines)."""
        # Handles: annotations list
        # Filters out Y-axis label annotations
        # Calls _detect_ylabel_from_annotation()

    def _detect_ylabel_from_annotation(self, annotations) -> str | None:
        """Detect if Y-axis label is stored as annotation (30 lines)."""
        # Looks for textangle=-90, xref='paper', x<0.1
```

**Benefits**:
- Each function has single responsibility
- `_detect_ylabel_from_annotation()` is testable in isolation
- Easy to add new extraction types without modifying existing code

**Testing**:
- Unit tests for each extraction function (4 tests)
- Integration test for full extraction (1 test)
- Edge case tests (annotations with Y-label, without) (2 tests)

---

#### B. Extract `apply_to_matplotlib()` into 7 functions + 2 config classes

```python
# New structure (target: each <80 lines, complexity <10)

@dataclass
class FontStyleConfig:
    """Configuration for font sizes and bold styling."""
    font_size_title: int = 10
    font_size_xlabel: int = 9
    font_size_ylabel: int = 9
    font_size_ticks: int = 7
    font_size_annotations: int = 6
    bold_title: bool = False
    bold_xlabel: bool = False
    bold_ylabel: bool = False
    bold_ticks: bool = False
    bold_annotations: bool = True

@dataclass
class PositioningConfig:
    """Configuration for element positioning and spacing."""
    ylabel_pad: float = 10.0
    ylabel_y_position: float = 0.5
    xtick_pad: float = 5.0
    ytick_pad: float = 5.0
    xaxis_margin: float = 0.02
    xtick_rotation: float = 45.0
    xtick_ha: str = "right"
    xtick_offset: float = 0.0
    group_label_offset: float = -0.12
    group_label_alternate: bool = True

@dataclass
class SeparatorConfig:
    """Configuration for group separators."""
    enabled: bool = False
    style: str = "dashed"
    color: str = "gray"

class LayoutApplier:
    """Applies extracted layout to Matplotlib axes."""

    def __init__(self, preset: LaTeXPreset | None = None):
        self.font_config = self._build_font_config(preset)
        self.pos_config = self._build_positioning_config(preset)
        self.sep_config = self._build_separator_config(preset)

    def apply_to_matplotlib(
        self,
        ax: Axes,
        layout: Dict[str, Any]
    ) -> None:
        """Main application orchestrator (target: 30 lines)."""
        self._apply_axis_ranges(ax, layout)
        self._apply_axis_labels(ax, layout)
        self._apply_title(ax, layout)
        self._apply_axis_scales_and_grids(ax, layout)
        self._apply_ticks(ax, layout)
        self._apply_legend(ax, layout)
        self._apply_annotations(ax, layout)

    def _build_font_config(self, preset) -> FontStyleConfig:
        """Extract font configuration from preset (20 lines)."""

    def _build_positioning_config(self, preset) -> PositioningConfig:
        """Extract positioning configuration from preset (25 lines)."""

    def _build_separator_config(self, preset) -> SeparatorConfig:
        """Extract separator configuration from preset (10 lines)."""

    def _apply_axis_ranges(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """Apply X/Y axis ranges with margins (25 lines)."""
        # Handles: x_range, y_range, xaxis_margin

    def _apply_axis_labels(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """Apply X/Y axis labels with font styling (30 lines)."""
        # Handles: x_label, y_label
        # Uses: font_config (sizes, bold), pos_config (ylabel_pad, ylabel_y_position)
        # Calls: _escape_latex()

    def _apply_title(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """Apply figure title with font styling (15 lines)."""
        # Handles: title
        # Uses: font_config

    def _apply_axis_scales_and_grids(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """Apply axis scales (log/linear) and grid visibility (20 lines)."""
        # Handles: x_type, y_type, x_grid, y_grid

    def _apply_ticks(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """Apply tick positions, labels, and styling (70 lines)."""
        # Handles: x_tickvals, x_ticktext, y_tickvals, y_ticktext
        # Uses: font_config (size, bold), pos_config (padding, rotation, offset)
        # Calls: _escape_latex()
        # Applies: tick_params, set_xticklabels with rotation/alignment
        # Handles: xtick_offset with ScaledTranslation

    def _apply_legend(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """Apply legend position (15 lines)."""
        # Handles: legend dict with x, y, xanchor, yanchor

    def _apply_annotations(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """Apply all annotations with coordinate transformations (80 lines)."""
        # Handles: annotations list
        # Uses: font_config, pos_config (group_label_offset, group_label_alternate)
        # Calls: _clean_html_tags(), _escape_latex()
        # Calls: _determine_annotation_font(), _calculate_annotation_position()
        # Calls: _build_matplotlib_annotation()
        # Calls: _draw_group_separators()

    def _clean_html_tags(self, text: str) -> str:
        """Remove HTML tags from annotation text (10 lines)."""
        # Removes: <b>, <i> tags using regex

    def _determine_annotation_font(
        self,
        annotation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine font properties based on annotation type (30 lines)."""
        # Detects: bar_total, grouping_label, default
        # Returns: fontsize, weight, color

    def _calculate_annotation_position(
        self,
        annotation: Dict[str, Any],
        grouping_label_index: int
    ) -> tuple[float, float, str | tuple[str, str]]:
        """Calculate position and coordinate system (40 lines)."""
        # Returns: (x, y, xycoords)
        # Handles: alternation for grouping labels
        # Maps: Plotly refs to Matplotlib xycoords

    def _build_matplotlib_annotation(
        self,
        annotation: Dict[str, Any],
        font_props: Dict[str, Any],
        position: tuple[float, float, str | tuple[str, str]]
    ) -> Dict[str, Any]:
        """Build matplotlib annotation kwargs (30 lines)."""
        # Determines: ha, va based on xanchor, yanchor
        # Handles: rotation from textangle
        # Returns: complete annotation kwargs dict

    def _draw_group_separators(
        self,
        ax: Axes,
        layout: Dict[str, Any]
    ) -> None:
        """Draw vertical separators between groups (50 lines)."""
        # Only if sep_config.enabled
        # Extracts: grouping label positions
        # Draws: vertical line using blended transform
```

**Benefits**:
- Configuration classes (FontStyleConfig, PositioningConfig, SeparatorConfig) are reusable
- Each application function has single responsibility
- Annotation handling is broken into testable sub-functions
- Easy to add new layout properties without modifying existing code
- Config classes make it easy to add new parameters

**Testing**:
- Unit tests for each config builder (3 tests)
- Unit tests for each application function (9 tests)
- Unit tests for annotation helpers (4 tests)
- Integration test for full application (1 test)
- Edge case tests (legends, separators, tick offsets) (5 tests)

---

### 2.2 Matplotlib Converter Refactoring

#### File: `src/plotting/export/converters/matplotlib_converter.py`

**Current Issues**:
1. `_convert_bar_trace()`: 181 lines, complexity 31
   - Bar positioning calculation
   - Stacking logic
   - Annotation creation
   - All in one function

**Refactoring Strategy**:

```python
# New structure (target: each <80 lines, complexity <10)

@dataclass
class BarLayoutConfig:
    """Configuration for bar chart layout."""
    trace_index: int
    total_traces: int
    bar_width: float
    group_gap: float
    is_stacked: bool

class BarTraceConverter:
    """Handles conversion of bar traces from Plotly to Matplotlib."""

    def convert_bar_trace(
        self,
        trace: go.Bar,
        ax: Axes,
        layout_config: BarLayoutConfig,
        preset: LaTeXPreset
    ) -> None:
        """Main conversion orchestrator (target: 30 lines)."""
        positions = self._calculate_bar_positions(trace, layout_config)
        bars = self._draw_bars(ax, trace, positions, layout_config)
        if preset.get("show_bar_values", False):
            self._add_bar_annotations(ax, bars, trace, positions, preset)

    def _calculate_bar_positions(
        self,
        trace: go.Bar,
        layout_config: BarLayoutConfig
    ) -> List[float]:
        """Calculate X positions for bars (60 lines)."""
        # Handles: grouped vs stacked positioning
        # Applies: bar_width, group_gap, trace_index
        # Returns: list of x positions

    def _draw_bars(
        self,
        ax: Axes,
        trace: go.Bar,
        positions: List[float],
        layout_config: BarLayoutConfig
    ) -> BarContainer:
        """Draw bars with proper styling (40 lines)."""
        # Handles: stacking with bottom parameter
        # Applies: color, edgecolor, linewidth, alpha
        # Returns: BarContainer for annotation positioning

    def _add_bar_annotations(
        self,
        ax: Axes,
        bars: BarContainer,
        trace: go.Bar,
        positions: List[float],
        preset: LaTeXPreset
    ) -> None:
        """Add value annotations above bars (50 lines)."""
        # Handles: text formatting, positioning
        # Uses: preset for font size and styling
        # Applies: proper y-offset for stacked bars
```

**Benefits**:
- Separation of concerns: positioning, drawing, annotating
- BarLayoutConfig makes layout parameters explicit
- Each function is testable with mock data
- Easy to extend with new bar chart features

**Testing**:
- Unit tests for position calculation (grouped, stacked) (4 tests)
- Unit tests for bar drawing (colors, styles) (3 tests)
- Unit tests for annotations (formats, positions) (3 tests)
- Integration test for full conversion (2 tests)

---

### 2.3 Plot Renderer Refactoring

#### File: `src/plotting/plot_renderer.py`

**Current Issues**:
1. `_render_download_button()`: 521 lines, complexity 13
   - Renders 4+ separate UI sections
   - Preset selection
   - Export format selection
   - Font controls (3 columns with 6 sliders + 6 checkboxes)
   - Positioning controls
   - Separator controls
   - Legend controls
   - Download button

2. `render_plot()`: 124 lines, complexity 18
   - Validation
   - Data preparation
   - Plot creation
   - Export handling
   - Error handling

**Refactoring Strategy**:

```python
# New structure (target: each <150 lines for UI components, <40 for logic)

class ExportControlsRenderer:
    """Renders export configuration UI components."""

    def render_export_controls(
        self,
        plot_config: Dict[str, Any],
        portfolio_manager: Any
    ) -> tuple[str, str, LaTeXPreset]:
        """Main UI orchestrator (target: 50 lines)."""
        preset_name = self._render_preset_selection(plot_config)
        export_format = self._render_format_selection(plot_config)
        preset = self._load_preset(preset_name)

        self._render_font_controls(preset)
        self._render_positioning_controls(preset)
        self._render_separator_controls(preset)
        self._render_legend_controls(preset)

        return preset_name, export_format, preset

    def _render_preset_selection(
        self,
        plot_config: Dict[str, Any]
    ) -> str:
        """Render preset selector with portfolio persistence (40 lines)."""
        # Renders: selectbox with all presets
        # Handles: loading saved preset from plot.config
        # Returns: selected preset name

    def _render_format_selection(
        self,
        plot_config: Dict[str, Any]
    ) -> str:
        """Render format selector (PDF/PNG) (20 lines)."""
        # Renders: radio buttons
        # Handles: loading saved format from plot.config
        # Returns: selected format

    def _load_preset(self, preset_name: str) -> LaTeXPreset:
        """Load preset and apply session overrides (30 lines)."""
        # Loads: preset from YAML
        # Applies: session state overrides
        # Returns: merged preset dict

    def _render_font_controls(self, preset: LaTeXPreset) -> None:
        """Render 3-column font controls (120 lines)."""
        # Column 1: title, xlabel, ylabel sliders
        # Column 2: legend, ticks, annotations sliders
        # Column 3: 6 bold checkboxes
        # Stores: all values in st.session_state

    def _render_positioning_controls(self, preset: LaTeXPreset) -> None:
        """Render positioning sliders (80 lines)."""
        # Sliders: ylabel_pad, ylabel_y_position, xtick_pad, ytick_pad
        # xtick_rotation, xtick_offset, group_label_offset
        # Checkbox: group_label_alternate
        # Stores: all values in st.session_state

    def _render_separator_controls(self, preset: LaTeXPreset) -> None:
        """Render group separator controls (60 lines)."""
        # Checkbox: group_separator
        # Selectbox: style
        # Color picker: color
        # Stores: all values in st.session_state

    def _render_legend_controls(self, preset: LaTeXPreset) -> None:
        """Render legend controls (40 lines)."""
        # Checkboxes: show_legend, legend_frameon
        # Sliders: legend_x, legend_y, legend_fontsize
        # Stores: all values in st.session_state


class PlotRenderer:
    """Renders plots with export functionality."""

    def __init__(self):
        self.export_controls = ExportControlsRenderer()

    def render_plot(
        self,
        plot_config: Dict[str, Any],
        data: pd.DataFrame,
        portfolio_manager: Any
    ) -> None:
        """Main plot rendering orchestrator (target: 40 lines)."""
        # Validate config
        validated_config = self._validate_plot_config(plot_config)

        # Prepare data
        prepared_data = self._prepare_data(data, validated_config)

        # Create plot
        figure = self._create_plot(prepared_data, validated_config)

        # Render plot
        st.plotly_chart(figure, use_container_width=True)

        # Render export controls and handle download
        self._handle_export(figure, validated_config, portfolio_manager)

    def _validate_plot_config(
        self,
        plot_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate plot configuration (25 lines)."""
        # Checks: required fields present
        # Validates: types and ranges
        # Returns: validated config
        # Raises: ValueError with clear message if invalid

    def _prepare_data(
        self,
        data: pd.DataFrame,
        config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Prepare data for plotting (30 lines)."""
        # Applies: filters from config
        # Handles: missing values
        # Returns: prepared DataFrame

    def _create_plot(
        self,
        data: pd.DataFrame,
        config: Dict[str, Any]
    ) -> go.Figure:
        """Create Plotly figure from config (30 lines)."""
        # Uses: PlotFactory to create plot
        # Applies: config to plot
        # Returns: Plotly figure

    def _handle_export(
        self,
        figure: go.Figure,
        config: Dict[str, Any],
        portfolio_manager: Any
    ) -> None:
        """Render export controls and handle download (40 lines)."""
        # Renders: export controls
        # Handles: download button click
        # Saves: export settings to portfolio
        # Exports: figure to file
```

**Benefits**:
- UI components are now separate classes (easy to test with mocks)
- Each rendering function has single responsibility
- Export controls are reusable across different plot types
- Plot rendering logic is separated from UI rendering
- Easy to add new controls without modifying existing code

**Testing**:
- Unit tests for each control renderer (6 tests)
- Unit tests for plot rendering steps (4 tests)
- Integration tests for full rendering (2 tests)
- UI tests with mock Streamlit state (4 tests)

---

## Phase 3: Test Plan

### 3.1 ylabel_y_position Tests (5 tests)

**File**: `tests/unit/export/test_ylabel_position.py`

```python
def test_schema_validates_ylabel_y_position():
    """Ensure preset schema accepts ylabel_y_position 0.0-1.0."""

def test_preset_manager_loads_ylabel_y_position():
    """Ensure preset manager loads ylabel_y_position from YAML."""

def test_layout_mapper_applies_ylabel_y_position():
    """Ensure layout mapper applies y parameter to set_ylabel()."""

def test_ui_renders_ylabel_y_position_slider():
    """Ensure UI renders slider with range 0.0-1.0, default 0.5."""

def test_portfolio_persists_ylabel_y_position():
    """Ensure plot.config saves and restores ylabel_y_position."""
```

---

### 3.2 Separate Font Sizes Tests (9 tests)

**File**: `tests/unit/export/test_separate_font_sizes.py`

```python
def test_schema_validates_font_size_xlabel():
    """Ensure schema accepts font_size_xlabel."""

def test_schema_validates_font_size_ylabel():
    """Ensure schema accepts font_size_ylabel."""

def test_schema_validates_font_size_legend():
    """Ensure schema accepts font_size_legend."""

def test_presets_updated_with_separate_fonts():
    """Ensure all 13 presets have xlabel/ylabel/legend fonts."""

def test_layout_mapper_applies_font_size_xlabel():
    """Ensure xlabel uses font_size_xlabel."""

def test_layout_mapper_applies_font_size_ylabel():
    """Ensure ylabel uses font_size_ylabel."""

def test_matplotlib_converter_applies_font_size_legend():
    """Ensure legend uses font_size_legend."""

def test_ui_renders_separate_font_sliders():
    """Ensure UI renders 3 sliders for xlabel/ylabel/legend."""

def test_portfolio_persists_separate_fonts():
    """Ensure plot.config saves all 3 font sizes."""
```

---

### 3.3 Bold Styling Tests (11 tests)

**File**: `tests/unit/export/test_bold_styling.py`

```python
def test_schema_validates_bold_title():
    """Ensure schema accepts bold_title boolean."""

def test_schema_validates_bold_xlabel():
    """Ensure schema accepts bold_xlabel boolean."""

def test_schema_validates_bold_ylabel():
    """Ensure schema accepts bold_ylabel boolean."""

def test_schema_validates_bold_legend():
    """Ensure schema accepts bold_legend boolean."""

def test_schema_validates_bold_ticks():
    """Ensure schema accepts bold_ticks boolean."""

def test_schema_validates_bold_annotations():
    """Ensure schema accepts bold_annotations boolean."""

def test_presets_updated_with_bold_flags():
    """Ensure all 13 presets have all 6 bold flags."""

def test_layout_mapper_applies_bold_styling():
    """Ensure fontweight='bold' applied when bold flags are True."""

def test_ui_renders_bold_checkboxes():
    """Ensure UI renders 6 checkboxes for bold styling."""

def test_bold_annotations_defaults_to_true():
    """Ensure bold_annotations defaults to True in schema."""

def test_portfolio_persists_bold_flags():
    """Ensure plot.config saves all 6 bold flags."""
```

---

### 3.4 Refactored Code Tests (22+ tests)

Each extracted function needs unit tests. Based on the refactoring plan:

**LayoutExtractor**: 7 tests
**LayoutApplier**: 16 tests
**BarTraceConverter**: 10 tests
**ExportControlsRenderer**: 6 tests
**PlotRenderer**: 4 tests

**Total new tests**: ~25 (features) + 43 (refactored code) = **68 new tests**

---

## Phase 4: Implementation Schedule

### Week 1: Layout Mapper Refactoring
- Day 1-2: Extract `extract_layout()` (4 functions + tests)
- Day 3-5: Extract `apply_to_matplotlib()` (7 functions + 2 config classes + tests)

### Week 2: Converter & Renderer Refactoring
- Day 1-2: Extract `_convert_bar_trace()` (3 functions + config class + tests)
- Day 3-5: Extract `_render_download_button()` (6 functions + tests)

### Week 3: Testing & Documentation
- Day 1-2: Implement 25 feature tests
- Day 3: Integration tests for refactored code
- Day 4: Documentation update
- Day 5: Final validation and metrics

---

## Phase 5: Success Metrics

### Code Quality Metrics

**Before Refactoring**:
- Functions >100 lines: 5
- Max complexity: 39
- Max function lines: 521
- Test coverage for new features: 0%

**Target After Refactoring**:
- Functions >100 lines: 0
- Max complexity: <10
- Max function lines: <150 (UI), <80 (logic)
- Test coverage for new features: 100%

### Validation Checklist

- [ ] All functions <100 lines (except UI components <150)
- [ ] All functions complexity <10
- [ ] 118+ tests passing (93 existing + 25 new)
- [ ] mypy --strict passes on all files
- [ ] flake8 passes with no violations
- [ ] black formatting applied
- [ ] All 13 pre-commit hooks passing
- [ ] Documentation updated
- [ ] No regression in existing functionality

---

## Phase 6: Risk Mitigation

### Risks & Mitigation Strategies

1. **Risk**: Refactoring breaks existing functionality
   - **Mitigation**: Write tests BEFORE refactoring, run after each extraction

2. **Risk**: New abstractions are too complex
   - **Mitigation**: Follow SOLID principles, keep config classes simple dataclasses

3. **Risk**: Time overrun on refactoring
   - **Mitigation**: Prioritize by complexity (layout_mapper first, others can wait)

4. **Risk**: Tests become flaky
   - **Mitigation**: Use fixtures, avoid time-dependent tests, mock external dependencies

---

## Appendix A: SOLID Principles Applied

### Single Responsibility Principle (SRP)
- Each extracted function has ONE reason to change
- FontStyleConfig only manages font configuration
- LayoutExtractor only extracts layout
- LayoutApplier only applies layout

### Open/Closed Principle (OCP)
- Config classes are open for extension (add new fields) but closed for modification
- Adding new layout properties doesn't require modifying existing extraction functions

### Liskov Substitution Principle (LSP)
- Config classes are concrete (not inheritance-based), so LSP doesn't apply
- All functions work with base types (Axes, Dict, etc.)

### Interface Segregation Principle (ISP)
- Functions take only the parameters they need
- Config classes are focused (Font, Positioning, Separator)

### Dependency Inversion Principle (DIP)
- Functions depend on abstract types (Dict, Axes) not concrete implementations
- Preset is passed as Dict[str, Any] allowing flexibility

---

## Appendix B: Example Refactoring (Before/After)

### Before: apply_to_matplotlib() - 325 lines, complexity 39

```python
@staticmethod
def apply_to_matplotlib(
    ax: Axes, layout: Dict[str, Any], preset: LaTeXPreset | None = None
) -> None:
    # 40 lines: Extract all font sizes and bold flags from preset
    font_size_title = preset.get("font_size_title", 10) if preset else 10
    font_size_xlabel = preset.get("font_size_xlabel", 9) if preset else 9
    # ... 35 more lines of parameter extraction

    # 20 lines: Apply axis ranges
    if "x_range" in layout:
        x_min, x_max = layout["x_range"]
        # ... range application logic

    # 30 lines: Apply axis labels
    if "x_label" in layout and layout["x_label"]:
        ax.set_xlabel(...)
    # ... label application logic

    # ... 200+ more lines of various applications
```

### After: apply_to_matplotlib() - 30 lines, complexity 7

```python
class LayoutApplier:
    def __init__(self, preset: LaTeXPreset | None = None):
        self.font_config = self._build_font_config(preset)
        self.pos_config = self._build_positioning_config(preset)
        self.sep_config = self._build_separator_config(preset)

    def apply_to_matplotlib(
        self,
        ax: Axes,
        layout: Dict[str, Any]
    ) -> None:
        """Apply extracted layout to Matplotlib axes."""
        self._apply_axis_ranges(ax, layout)
        self._apply_axis_labels(ax, layout)
        self._apply_title(ax, layout)
        self._apply_axis_scales_and_grids(ax, layout)
        self._apply_ticks(ax, layout)
        self._apply_legend(ax, layout)
        self._apply_annotations(ax, layout)
```

**Benefits**:
- Main function is now a clean orchestrator
- Each sub-function is independently testable
- Config classes make dependencies explicit
- Easy to add new application types

---

## Next Steps

1. ✅ Phase 1: Comprehensive Code Audit (COMPLETE)
2. ✅ Phase 2: Architecture Review & Refactoring Plan (COMPLETE)
3. 🔄 Phase 3: Begin Implementation - Layout Mapper Extraction
4. ⏳ Phase 4: Continue with Converter & Renderer
5. ⏳ Phase 5: Comprehensive Testing
6. ⏳ Phase 6: Documentation & Final Validation
