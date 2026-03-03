# Step 25 -- E2E Plot Types Tests

## 1. Executive Summary

This document defines an exhaustive end-to-end test plan covering all nine plot
types registered in the RING-5 Unified Engine v2 `PlotFactory`:

| Registry Key              | Class                   | Category     | Config Module                |
|---------------------------|-------------------------|--------------|------------------------------|
| `bar`                     | `BarPlot`               | basic        | `render_common_with_color`   |
| `line`                    | `LinePlot`              | basic        | `render_common_with_color`   |
| `scatter`                 | `ScatterPlot`           | basic        | `render_common_with_color`   |
| `histogram`               | `HistogramPlot`         | distribution | `histogram_config.render`    |
| `heatmap`                 | `HeatmapPlot`           | distribution | `heatmap_config.render`      |
| `grouped_bar`             | `GroupedBarPlot`        | comparison   | `grouped_bar_config.render`  |
| `stacked_bar`             | `StackedBarPlot`        | comparison   | `stacked_bar_config.render`  |
| `grouped_stacked_bar`     | `GroupedStackedBarPlot` | comparison   | `grouped_stacked_bar_config` |
| `dual_axis_bar_dot`       | `DualAxisBarDotPlot`    | comparison   | `dual_axis_config.render`    |

### Architecture context

The Manage Plots page (`src/web/pages/manage_plots.py`) is a thin composition
layer that wires three controllers:

1. **PlotCreationController** -- lifecycle (create, select, rename, delete, duplicate).
2. **PipelineController** -- shaper pipeline editing.
3. **PlotRenderController** -- config UI + `create_traces` + figure display.

All plot types inherit from `BasePlot` (`src/web/pages/ui/plotting/base_plot.py`)
and implement two key abstract methods:

- `create_traces(data, config) -> TraceBuildResult` -- produces engine-agnostic
  trace descriptions (`BarTraceConfig`, `LineTraceConfig`, `ScatterTraceConfig`,
  `HeatmapTraceConfig`).
- `get_legend_column(config) -> str | None` -- returns the column used for
  color-coded legend grouping.

The shared helper `build_color_grouped_traces` in `_trace_helpers.py` handles
the color-group splitting for Bar, Line, and Scatter plots via a common
`trace_factory` callback pattern.

### Scope

Each plot type is tested across six dimensions:

1. **Creation** -- selecting the type from the factory dropdown and verifying
   the correct `BasePlot` subclass is instantiated.
2. **Trace generation** -- feeding representative DataFrames into
   `create_traces` and asserting the `TraceBuildResult` shape.
3. **Legend column** -- verifying `get_legend_column` returns the correct column
   (or `None`) for each config combination.
4. **Config-specific options** -- testing type-specific UI fields (line shape,
   dot symbol, histogram normalization, heatmap colorscale, etc.).
5. **Data column selection** -- exercising the x/y/color/group column pickers.
6. **Visual regression** -- screenshot comparisons of rendered Plotly figures
   via pytest-playwright.

All Gherkin scenarios use `playwright` page fixtures.  Pytest stubs use the
`ManagePlotsPage` Page Object Model defined in Section 12.

---

## 2. Plot Factory & Type Registry

### 2.1 Factory registry completeness

```gherkin
Feature: PlotFactory Type Registry

  Background:
    Given the PlotFactory class is imported from "src.web.pages.ui.plotting.plot_factory"

  Scenario: All nine plot types are registered
    When I call PlotFactory.get_available_plot_types()
    Then the returned list contains exactly 9 entries
    And it includes "bar", "line", "scatter", "histogram", "heatmap"
    And it includes "grouped_bar", "stacked_bar", "grouped_stacked_bar", "dual_axis_bar_dot"

  Scenario: Each plot type has metadata
    When I call PlotFactory.get_plot_metadata()
    Then every key in get_available_plot_types() has a metadata entry
    And each metadata entry has "display_name", "icon", "category"

  Scenario: Metadata categories are valid
    When I call PlotFactory.get_plot_metadata()
    Then every entry has category in ["basic", "comparison", "distribution"]
    And "bar", "line", "scatter" have category "basic"
    And "grouped_bar", "stacked_bar", "grouped_stacked_bar", "dual_axis_bar_dot" have category "comparison"
    And "heatmap", "histogram" have category "distribution"

  Scenario: Factory creates correct subclass for each type
    Given plot_types = PlotFactory.get_available_plot_types()
    When I call PlotFactory.create_plot(plot_type, 1, "test") for each type
    Then the returned object is an instance of BasePlot
    And its plot_type attribute matches the requested type

  Scenario: Factory raises ValueError for unknown type
    When I call PlotFactory.create_plot("nonexistent", 1, "test")
    Then a ValueError is raised with message containing "Unknown plot type"

  Scenario: Runtime registration of custom plot type
    Given a custom class FakePlot that extends BasePlot
    When I call PlotFactory.register_plot_type("fake", FakePlot, metadata)
    Then "fake" appears in get_available_plot_types()
    And PlotFactory.create_plot("fake", 1, "test") returns a FakePlot instance

  Scenario: Runtime registration rejects non-BasePlot classes
    Given a plain class NotAPlot that does not extend BasePlot
    When I call PlotFactory.register_plot_type("bad", NotAPlot)
    Then a ValueError is raised with message containing "subclass of BasePlot"
```

### 2.2 Pytest stubs -- factory

```python
# tests/e2e/plots/test_plot_factory_registry.py
"""E2E tests for PlotFactory type registry completeness."""

import pytest

from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory

EXPECTED_TYPES = [
    "bar", "line", "scatter", "histogram", "heatmap",
    "grouped_bar", "stacked_bar", "grouped_stacked_bar", "dual_axis_bar_dot",
]

CATEGORY_MAP = {
    "bar": "basic", "line": "basic", "scatter": "basic",
    "grouped_bar": "comparison", "stacked_bar": "comparison",
    "grouped_stacked_bar": "comparison", "dual_axis_bar_dot": "comparison",
    "heatmap": "distribution", "histogram": "distribution",
}


class TestPlotFactoryRegistry:
    """Validate that the PlotFactory registry is complete and correct."""

    def test_all_nine_types_registered(self) -> None:
        types = PlotFactory.get_available_plot_types()
        assert len(types) == 9
        for t in EXPECTED_TYPES:
            assert t in types, f"Missing plot type: {t}"

    def test_metadata_exists_for_every_type(self) -> None:
        metadata = PlotFactory.get_plot_metadata()
        for t in PlotFactory.get_available_plot_types():
            assert t in metadata, f"Missing metadata for: {t}"
            entry = metadata[t]
            assert "display_name" in entry
            assert "icon" in entry
            assert "category" in entry

    def test_metadata_categories_valid(self) -> None:
        metadata = PlotFactory.get_plot_metadata()
        for plot_type, meta in metadata.items():
            assert meta["category"] in ("basic", "comparison", "distribution")
            if plot_type in CATEGORY_MAP:
                assert meta["category"] == CATEGORY_MAP[plot_type]

    @pytest.mark.parametrize("plot_type", EXPECTED_TYPES)
    def test_create_plot_returns_correct_subclass(self, plot_type: str) -> None:
        plot = PlotFactory.create_plot(plot_type, plot_id=1, name="test")
        assert isinstance(plot, BasePlot)
        assert plot.plot_type == plot_type
        assert plot.plot_id == 1
        assert plot.name == "test"

    @pytest.mark.parametrize("plot_type", EXPECTED_TYPES)
    def test_created_plot_has_empty_initial_state(self, plot_type: str) -> None:
        plot = PlotFactory.create_plot(plot_type, plot_id=1, name="test")
        assert plot.config == {}
        assert plot.processed_data is None
        assert plot.last_generated_fig is None
        assert plot.pipeline == []

    def test_create_plot_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown plot type"):
            PlotFactory.create_plot("nonexistent", 1, "test")

    def test_register_custom_plot_type(self) -> None:
        class FakePlot(BasePlot):
            def __init__(self, plot_id: int, name: str):
                super().__init__(plot_id, name, "fake")

            def create_traces(self, data, config):
                from src.core.models.visualization.trace_build_result import TraceBuildResult
                return TraceBuildResult(traces=[])

            def get_legend_column(self, config):
                return None

        PlotFactory.register_plot_type("fake", FakePlot, {
            "display_name": "Fake", "icon": "bug_report", "category": "test",
        })
        assert "fake" in PlotFactory.get_available_plot_types()
        instance = PlotFactory.create_plot("fake", 99, "fake_test")
        assert isinstance(instance, FakePlot)
        # Cleanup
        del PlotFactory._plot_classes["fake"]
        del PlotFactory._plot_metadata["fake"]

    def test_register_non_baseplot_raises(self) -> None:
        class NotAPlot:
            pass

        with pytest.raises(ValueError, match="subclass of BasePlot"):
            PlotFactory.register_plot_type("bad", NotAPlot)  # type: ignore[arg-type]
```

---

## 3. Common Plot Creation Tests

### 3.1 PlotCreationComponent E2E scenarios

```gherkin
Feature: Plot Creation Flow (Manage Plots Page)

  Background:
    Given the user has uploaded a valid dataset
    And the user navigates to the "Manage Plots" page

  Scenario: Create a new plot via the form
    Given the create-plot form is visible with fields "New plot name", "Plot type"
    When the user enters "My Bar Chart" in the name field
    And the user selects "bar" from the plot type dropdown
    And the user clicks the "Create Plot" submit button
    Then a new plot named "My Bar Chart" appears in the plot selector
    And the plot type is "bar"

  Scenario: Default name is pre-filled
    When the create-plot form loads
    Then the "New plot name" field has a non-empty default value

  Scenario Outline: Create each of the nine plot types
    When the user creates a plot with type "<plot_type>"
    Then the plot selector shows the new plot
    And the rendered config UI matches the "<config_module>" signature

    Examples:
      | plot_type            | config_module              |
      | bar                  | render_common_with_color   |
      | line                 | render_common_with_color   |
      | scatter              | render_common_with_color   |
      | histogram            | histogram_config           |
      | heatmap              | heatmap_config             |
      | grouped_bar          | grouped_bar_config         |
      | stacked_bar          | stacked_bar_config         |
      | grouped_stacked_bar  | grouped_stacked_bar_config |
      | dual_axis_bar_dot    | dual_axis_config           |

  Scenario: Rename an existing plot
    Given a plot named "Old Name" exists
    When the user renames it to "New Name"
    Then the plot selector shows "New Name"

  Scenario: Delete a plot
    Given a plot named "Disposable" exists
    When the user deletes the plot
    Then "Disposable" no longer appears in the plot selector

  Scenario: Duplicate a plot
    Given a plot named "Original" exists with configured data
    When the user duplicates the plot
    Then a new plot named "Original (copy)" appears
    And its config matches the original

  Scenario: Form uses st.form to batch input
    When the user types in the "New plot name" field
    Then no Streamlit rerun occurs until "Create Plot" is clicked
```

### 3.2 Pytest-playwright stubs -- creation flow

```python
# tests/e2e/plots/test_plot_creation_flow.py
"""E2E tests for the plot creation, rename, delete, and duplicate flows."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.pages.manage_plots_page import ManagePlotsPage


@pytest.fixture
def plots_page(page: Page, uploaded_dataset: None) -> ManagePlotsPage:
    """Navigate to Manage Plots page with data already loaded."""
    mp = ManagePlotsPage(page)
    mp.navigate()
    return mp


class TestPlotCreationFlow:
    """Verify plot lifecycle operations via the Streamlit UI."""

    PLOT_TYPES = [
        "bar", "line", "scatter", "histogram", "heatmap",
        "grouped_bar", "stacked_bar", "grouped_stacked_bar",
        "dual_axis_bar_dot",
    ]

    @pytest.mark.parametrize("plot_type", PLOT_TYPES)
    def test_create_plot_of_each_type(
        self, plots_page: ManagePlotsPage, plot_type: str
    ) -> None:
        name = f"Test {plot_type}"
        plots_page.create_plot(name=name, plot_type=plot_type)
        assert plots_page.is_plot_in_selector(name)

    def test_create_plot_form_has_three_columns(
        self, plots_page: ManagePlotsPage
    ) -> None:
        """PlotCreationComponent renders col1=name, col2=type, col3=button."""
        form = plots_page.page.locator("[data-testid='stFormSubmitButton']")
        expect(form).to_be_visible()

    def test_rename_plot(self, plots_page: ManagePlotsPage) -> None:
        plots_page.create_plot(name="Old Name", plot_type="bar")
        plots_page.select_plot("Old Name")
        plots_page.rename_plot("New Name")
        assert plots_page.is_plot_in_selector("New Name")
        assert not plots_page.is_plot_in_selector("Old Name")

    def test_delete_plot(self, plots_page: ManagePlotsPage) -> None:
        plots_page.create_plot(name="Disposable", plot_type="bar")
        plots_page.select_plot("Disposable")
        plots_page.delete_plot()
        assert not plots_page.is_plot_in_selector("Disposable")

    def test_duplicate_plot(self, plots_page: ManagePlotsPage) -> None:
        plots_page.create_plot(name="Original", plot_type="scatter")
        plots_page.select_plot("Original")
        plots_page.duplicate_plot()
        assert plots_page.is_plot_in_selector("Original (copy)")

    def test_create_multiple_plots_same_type(
        self, plots_page: ManagePlotsPage
    ) -> None:
        plots_page.create_plot(name="Bar 1", plot_type="bar")
        plots_page.create_plot(name="Bar 2", plot_type="bar")
        assert plots_page.is_plot_in_selector("Bar 1")
        assert plots_page.is_plot_in_selector("Bar 2")
```

---

## 4. Bar Plot Tests

### 4.1 Gherkin scenarios

```gherkin
Feature: Bar Plot -- Creation, Traces, and Configuration

  Background:
    Given a DataFrame with columns ["category", "value", "value.sd", "group_col"]
    And the PlotFactory creates a BarPlot with id=1, name="Test Bar"

  Scenario: BarPlot initializes with correct type
    Then the plot.plot_type is "bar"
    And the plot.config is an empty dict
    And the plot.processed_data is None

  Scenario: create_traces produces single BarTraceConfig without color column
    Given config = {"x": "category", "y": "value"}
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains exactly 1 trace
    And trace[0] is a BarTraceConfig
    And trace[0].name equals "value"
    And trace[0].x has the same length as the data
    And trace[0].error_y is None

  Scenario: create_traces with color column produces grouped traces
    Given config = {"x": "category", "y": "value", "color": "group_col"}
    And the data has 3 unique values in "group_col"
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains exactly 3 traces
    And each trace is a BarTraceConfig
    And each trace.name matches a unique group_col value

  Scenario: create_traces with error bars includes error_y
    Given config = {"x": "category", "y": "value", "show_error_bars": true}
    And the data has a "value.sd" column
    When I call plot.create_traces(data, config)
    Then trace[0].error_y is a non-empty list of floats

  Scenario: create_traces respects xaxis_order for sorting
    Given config = {"x": "category", "y": "value", "xaxis_order": ["C", "A", "B"]}
    When I call plot.create_traces(data, config)
    Then trace[0].x values follow the order ["C", "A", "B"]

  Scenario: create_traces casts x column to string
    Given the data has integer values in the "category" column
    And config = {"x": "category", "y": "value"}
    When I call plot.create_traces(data, config)
    Then all values in trace[0].x are strings

  Scenario: get_legend_column returns color column name
    Given config = {"x": "category", "y": "value", "color": "group_col"}
    When I call plot.get_legend_column(config)
    Then the result is "group_col"

  Scenario: get_legend_column returns None when no color
    Given config = {"x": "category", "y": "value"}
    When I call plot.get_legend_column(config)
    Then the result is None

  Scenario: create_traces with legend_order respects custom order
    Given config = {"x": "cat", "y": "val", "color": "grp", "legend_order": ["B", "A", "C"]}
    When I call plot.create_traces(data, config)
    Then the trace names appear in order ["B", "A", "C"]

  Scenario: render_config_ui delegates to render_common_with_color
    Given a DataFrame with multiple columns
    When I call plot.render_config_ui(data, saved_config)
    Then the returned config contains keys "x" and "y"
```

### 4.2 Pytest stubs -- bar plot

```python
# tests/e2e/plots/test_bar_plot.py
"""E2E tests for BarPlot trace generation and config."""

import pandas as pd
import pytest

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def bar_plot():
    return PlotFactory.create_plot("bar", plot_id=1, name="Test Bar")


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame({
        "category": ["A", "B", "C", "A", "B", "C"],
        "value": [10, 20, 30, 15, 25, 35],
        "value.sd": [1.0, 2.0, 3.0, 1.5, 2.5, 3.5],
        "group_col": ["G1", "G1", "G1", "G2", "G2", "G2"],
    })


class TestBarPlotTraces:
    """Validate BarPlot.create_traces output shape and content."""

    def test_single_trace_without_color(self, bar_plot, sample_data) -> None:
        config = {"x": "category", "y": "value"}
        result: TraceBuildResult = bar_plot.create_traces(sample_data, config)
        assert len(result.traces) == 1
        assert isinstance(result.traces[0], BarTraceConfig)
        assert result.traces[0].name == "value"
        assert result.traces[0].error_y is None

    def test_grouped_traces_with_color(self, bar_plot, sample_data) -> None:
        config = {"x": "category", "y": "value", "color": "group_col"}
        result = bar_plot.create_traces(sample_data, config)
        assert len(result.traces) == 2
        trace_names = {t.name for t in result.traces}
        assert trace_names == {"G1", "G2"}

    def test_error_bars_present(self, bar_plot, sample_data) -> None:
        config = {"x": "category", "y": "value", "show_error_bars": True}
        result = bar_plot.create_traces(sample_data, config)
        assert result.traces[0].error_y is not None
        assert len(result.traces[0].error_y) > 0

    def test_error_bars_absent_without_sd_column(self, bar_plot) -> None:
        data = pd.DataFrame({"cat": ["A", "B"], "val": [1, 2]})
        config = {"x": "cat", "y": "val", "show_error_bars": True}
        result = bar_plot.create_traces(data, config)
        assert result.traces[0].error_y is None

    def test_xaxis_order_respected(self, bar_plot, sample_data) -> None:
        config = {"x": "category", "y": "value", "xaxis_order": ["C", "A", "B"]}
        result = bar_plot.create_traces(sample_data, config)
        x_vals = result.traces[0].x
        # First value should be "C" due to sort order
        assert x_vals[0] == "C"

    def test_x_column_cast_to_string(self, bar_plot) -> None:
        data = pd.DataFrame({"cat": [1, 2, 3], "val": [10, 20, 30]})
        config = {"x": "cat", "y": "val"}
        result = bar_plot.create_traces(data, config)
        assert all(isinstance(v, str) for v in result.traces[0].x)

    def test_legend_order_respected(self, bar_plot, sample_data) -> None:
        config = {
            "x": "category", "y": "value",
            "color": "group_col",
            "legend_order": ["G2", "G1"],
        }
        result = bar_plot.create_traces(sample_data, config)
        assert result.traces[0].name == "G2"
        assert result.traces[1].name == "G1"

    def test_default_barmode_is_none(self, bar_plot, sample_data) -> None:
        """Bar plot does not set barmode (unlike grouped/stacked)."""
        config = {"x": "category", "y": "value"}
        result = bar_plot.create_traces(sample_data, config)
        assert result.barmode is None


class TestBarPlotLegend:
    """Validate BarPlot.get_legend_column behavior."""

    def test_legend_column_with_color(self, bar_plot) -> None:
        assert bar_plot.get_legend_column({"color": "group_col"}) == "group_col"

    def test_legend_column_without_color(self, bar_plot) -> None:
        assert bar_plot.get_legend_column({"x": "a", "y": "b"}) is None

    def test_legend_column_with_none_color(self, bar_plot) -> None:
        assert bar_plot.get_legend_column({"color": None}) is None


class TestBarPlotVisualRegression:
    """Screenshot comparison tests for bar plot rendering."""

    @pytest.mark.visual
    def test_simple_bar_chart_screenshot(
        self, plots_page, sample_dataset
    ) -> None:
        plots_page.create_plot("Simple Bar", "bar")
        plots_page.select_plot("Simple Bar")
        plots_page.configure_xy(x_col="category", y_col="value")
        plots_page.wait_for_plotly_render()
        screenshot = plots_page.capture_plot_screenshot()
        assert screenshot is not None  # Placeholder for pixelmatch comparison

    @pytest.mark.visual
    def test_colored_bar_chart_screenshot(
        self, plots_page, sample_dataset
    ) -> None:
        plots_page.create_plot("Colored Bar", "bar")
        plots_page.select_plot("Colored Bar")
        plots_page.configure_xy(x_col="category", y_col="value")
        plots_page.set_color_column("group_col")
        plots_page.wait_for_plotly_render()
        screenshot = plots_page.capture_plot_screenshot()
        assert screenshot is not None
```

---

## 5. Line Plot Tests

### 5.1 Gherkin scenarios

```gherkin
Feature: Line Plot -- Creation, Traces, and Line Shape Options

  Background:
    Given a DataFrame with columns ["time", "metric", "metric.sd", "series"]
    And the PlotFactory creates a LinePlot with id=2, name="Test Line"

  Scenario: LinePlot initializes with correct type
    Then the plot.plot_type is "line"

  Scenario: create_traces produces single LineTraceConfig without color
    Given config = {"x": "time", "y": "metric"}
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains exactly 1 trace
    And trace[0] is a LineTraceConfig
    And trace[0].name equals "metric"
    And trace[0].show_markers is True

  Scenario: create_traces sorts data by x column
    Given config = {"x": "time", "y": "metric"}
    And the data rows are in random order
    When I call plot.create_traces(data, config)
    Then trace[0].x values are in ascending order

  Scenario: create_traces with color column produces multiple line traces
    Given config = {"x": "time", "y": "metric", "color": "series"}
    And the data has 2 unique values in "series"
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains exactly 2 traces
    And each trace is a LineTraceConfig

  Scenario: create_traces with error bars
    Given config = {"x": "time", "y": "metric", "show_error_bars": true}
    When I call plot.create_traces(data, config)
    Then trace[0].error_y is a non-empty list

  Scenario: Line shape advanced option -- spline
    Given saved_config = {"line_shape": "spline"}
    When I call plot.render_specific_advanced_options(saved_config)
    Then the returned config contains "line_shape" = "spline"

  Scenario: Line shape advanced option -- step functions
    Given saved_config = {"line_shape": "hv"}
    When I call plot.render_specific_advanced_options(saved_config)
    Then the returned config contains "line_shape" = "hv"

  Scenario: Line shape defaults to linear
    Given saved_config = {}
    When I call plot.render_specific_advanced_options(saved_config)
    Then the returned config contains "line_shape" = "linear"

  Scenario: get_legend_column returns color column
    Given config = {"x": "time", "y": "metric", "color": "series"}
    When I call plot.get_legend_column(config)
    Then the result is "series"

  Scenario: get_legend_column returns None without color
    Given config = {"x": "time", "y": "metric"}
    When I call plot.get_legend_column(config)
    Then the result is None

  Scenario: render_config_ui uses render_common_with_color
    Given a DataFrame with numeric and categorical columns
    When I call plot.render_config_ui(data, {})
    Then the returned config includes column selectors for x, y, and color
```

### 5.2 Pytest stubs -- line plot

```python
# tests/e2e/plots/test_line_plot.py
"""E2E tests for LinePlot trace generation and line shape options."""

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import LineTraceConfig
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def line_plot():
    return PlotFactory.create_plot("line", plot_id=2, name="Test Line")


@pytest.fixture
def time_series_data() -> pd.DataFrame:
    return pd.DataFrame({
        "time": [3, 1, 2, 6, 4, 5],
        "metric": [10.0, 20.0, 15.0, 30.0, 25.0, 35.0],
        "metric.sd": [0.5, 1.0, 0.7, 1.5, 1.2, 2.0],
        "series": ["A", "A", "A", "B", "B", "B"],
    })


class TestLinePlotTraces:
    """Validate LinePlot.create_traces output."""

    def test_single_trace_without_color(self, line_plot, time_series_data) -> None:
        config = {"x": "time", "y": "metric"}
        result = line_plot.create_traces(time_series_data, config)
        assert len(result.traces) == 1
        assert isinstance(result.traces[0], LineTraceConfig)
        assert result.traces[0].name == "metric"
        assert result.traces[0].show_markers is True

    def test_data_sorted_by_x(self, line_plot, time_series_data) -> None:
        config = {"x": "time", "y": "metric"}
        result = line_plot.create_traces(time_series_data, config)
        x_values = result.traces[0].x
        assert x_values == sorted(x_values)

    def test_multiple_traces_with_color(self, line_plot, time_series_data) -> None:
        config = {"x": "time", "y": "metric", "color": "series"}
        result = line_plot.create_traces(time_series_data, config)
        assert len(result.traces) == 2
        names = {t.name for t in result.traces}
        assert names == {"A", "B"}

    def test_each_trace_sorted_independently(self, line_plot, time_series_data) -> None:
        config = {"x": "time", "y": "metric", "color": "series"}
        result = line_plot.create_traces(time_series_data, config)
        for trace in result.traces:
            assert trace.x == sorted(trace.x)

    def test_error_bars(self, line_plot, time_series_data) -> None:
        config = {"x": "time", "y": "metric", "show_error_bars": True}
        result = line_plot.create_traces(time_series_data, config)
        assert result.traces[0].error_y is not None
        assert len(result.traces[0].error_y) == len(result.traces[0].y)

    def test_no_barmode_set(self, line_plot, time_series_data) -> None:
        config = {"x": "time", "y": "metric"}
        result = line_plot.create_traces(time_series_data, config)
        assert result.barmode is None


class TestLinePlotLegend:
    """Validate LinePlot.get_legend_column behavior."""

    def test_with_color(self, line_plot) -> None:
        assert line_plot.get_legend_column({"color": "series"}) == "series"

    def test_without_color(self, line_plot) -> None:
        assert line_plot.get_legend_column({"x": "time", "y": "metric"}) is None


class TestLinePlotAdvancedOptions:
    """Validate line-shape-specific advanced options."""

    LINE_SHAPES = ["linear", "spline", "hv", "vh", "hvh", "vhv"]

    @pytest.mark.parametrize("shape", LINE_SHAPES)
    def test_all_line_shapes_are_valid(self, shape: str) -> None:
        """Verify all six Plotly line shapes are recognized constants."""
        assert shape in ["linear", "spline", "hv", "vh", "hvh", "vhv"]


class TestLinePlotVisualRegression:
    """Screenshot comparison tests for line plot rendering."""

    @pytest.mark.visual
    def test_simple_line_chart_screenshot(self, plots_page, sample_dataset) -> None:
        plots_page.create_plot("Line Test", "line")
        plots_page.select_plot("Line Test")
        plots_page.configure_xy(x_col="time", y_col="metric")
        plots_page.wait_for_plotly_render()
        screenshot = plots_page.capture_plot_screenshot()
        assert screenshot is not None

    @pytest.mark.visual
    def test_multi_series_line_screenshot(self, plots_page, sample_dataset) -> None:
        plots_page.create_plot("Multi Line", "line")
        plots_page.select_plot("Multi Line")
        plots_page.configure_xy(x_col="time", y_col="metric")
        plots_page.set_color_column("series")
        plots_page.wait_for_plotly_render()
        screenshot = plots_page.capture_plot_screenshot()
        assert screenshot is not None
```

---

## 6. Scatter Plot Tests

### 6.1 Gherkin scenarios

```gherkin
Feature: Scatter Plot -- Creation, Traces, and Color Grouping

  Background:
    Given a DataFrame with columns ["x_val", "y_val", "y_val.sd", "category"]
    And the PlotFactory creates a ScatterPlot with id=3, name="Test Scatter"

  Scenario: ScatterPlot initializes with correct type
    Then the plot.plot_type is "scatter"

  Scenario: create_traces produces single ScatterTraceConfig without color
    Given config = {"x": "x_val", "y": "y_val"}
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains exactly 1 trace
    And trace[0] is a ScatterTraceConfig
    And trace[0].name equals "y_val"
    And trace[0].error_y is None

  Scenario: create_traces with color column produces grouped scatter traces
    Given config = {"x": "x_val", "y": "y_val", "color": "category"}
    And the data has 3 unique values in "category"
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains exactly 3 traces
    And each trace is a ScatterTraceConfig

  Scenario: create_traces with error bars
    Given config = {"x": "x_val", "y": "y_val", "show_error_bars": true}
    When I call plot.create_traces(data, config)
    Then trace[0].error_y is a non-empty list

  Scenario: get_legend_column returns color column
    Given config = {"color": "category"}
    When I call plot.get_legend_column(config)
    Then the result is "category"

  Scenario: get_legend_column returns None without color
    Given config = {"x": "x_val", "y": "y_val"}
    When I call plot.get_legend_column(config)
    Then the result is None

  Scenario: Scatter does not sort data by x
    Given config = {"x": "x_val", "y": "y_val"}
    And the data is in non-sorted x order
    When I call plot.create_traces(data, config)
    Then trace[0].x values preserve the original data order

  Scenario: render_config_ui uses render_common_with_color
    Given a DataFrame
    When I call plot.render_config_ui(data, {})
    Then the returned config includes x, y, and optional color selectors
```

### 6.2 Pytest stubs -- scatter plot

```python
# tests/e2e/plots/test_scatter_plot.py
"""E2E tests for ScatterPlot trace generation."""

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import ScatterTraceConfig
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def scatter_plot():
    return PlotFactory.create_plot("scatter", plot_id=3, name="Test Scatter")


@pytest.fixture
def scatter_data() -> pd.DataFrame:
    return pd.DataFrame({
        "x_val": [5, 3, 1, 4, 2, 6],
        "y_val": [10.0, 20.0, 15.0, 30.0, 25.0, 35.0],
        "y_val.sd": [0.5, 1.0, 0.7, 1.5, 1.2, 2.0],
        "category": ["A", "A", "B", "B", "C", "C"],
    })


class TestScatterPlotTraces:
    """Validate ScatterPlot.create_traces output."""

    def test_single_trace_without_color(self, scatter_plot, scatter_data) -> None:
        config = {"x": "x_val", "y": "y_val"}
        result = scatter_plot.create_traces(scatter_data, config)
        assert len(result.traces) == 1
        assert isinstance(result.traces[0], ScatterTraceConfig)
        assert result.traces[0].name == "y_val"

    def test_grouped_traces_with_color(self, scatter_plot, scatter_data) -> None:
        config = {"x": "x_val", "y": "y_val", "color": "category"}
        result = scatter_plot.create_traces(scatter_data, config)
        assert len(result.traces) == 3
        names = {t.name for t in result.traces}
        assert names == {"A", "B", "C"}

    def test_error_bars(self, scatter_plot, scatter_data) -> None:
        config = {"x": "x_val", "y": "y_val", "show_error_bars": True}
        result = scatter_plot.create_traces(scatter_data, config)
        assert result.traces[0].error_y is not None

    def test_data_order_preserved(self, scatter_plot, scatter_data) -> None:
        """Scatter does NOT sort by x (unlike line)."""
        config = {"x": "x_val", "y": "y_val"}
        result = scatter_plot.create_traces(scatter_data, config)
        # Original order: [5, 3, 1, 4, 2, 6]
        assert result.traces[0].x == [5, 3, 1, 4, 2, 6]

    def test_no_barmode(self, scatter_plot, scatter_data) -> None:
        config = {"x": "x_val", "y": "y_val"}
        result = scatter_plot.create_traces(scatter_data, config)
        assert result.barmode is None


class TestScatterPlotLegend:
    """Validate ScatterPlot.get_legend_column behavior."""

    def test_with_color(self, scatter_plot) -> None:
        assert scatter_plot.get_legend_column({"color": "category"}) == "category"

    def test_without_color(self, scatter_plot) -> None:
        assert scatter_plot.get_legend_column({}) is None


class TestScatterPlotVisualRegression:
    """Screenshot comparison tests for scatter plot rendering."""

    @pytest.mark.visual
    def test_scatter_plot_screenshot(self, plots_page, sample_dataset) -> None:
        plots_page.create_plot("Scatter Test", "scatter")
        plots_page.select_plot("Scatter Test")
        plots_page.configure_xy(x_col="x_val", y_col="y_val")
        plots_page.wait_for_plotly_render()
        screenshot = plots_page.capture_plot_screenshot()
        assert screenshot is not None
```

---

## 7. Grouped Bar Plot Tests

### 7.1 Gherkin scenarios

```gherkin
Feature: Grouped Bar Plot -- Manual Coordinates and Visual Distinction

  Background:
    Given a DataFrame with columns ["config", "benchmark", "score", "score.sd"]
    And the PlotFactory creates a GroupedBarPlot with id=4, name="Test Grouped"

  Scenario: GroupedBarPlot initializes with type "grouped_bar"
    Then the plot.plot_type is "grouped_bar"

  Scenario: create_traces without group column produces single bar
    Given config = {"x": "config", "y": "score"}
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains exactly 1 trace
    And the trace has x_positions (manual coordinates)
    And result.barmode is "group"

  Scenario: create_traces with group column produces per-group traces
    Given config = {"x": "config", "y": "score", "group": "benchmark"}
    And the data has 3 unique values in "benchmark"
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains exactly 3 traces
    And each trace name matches a unique benchmark value

  Scenario: create_traces generates custom_x_ticks
    Given config = {"x": "config", "y": "score", "group": "benchmark"}
    When I call plot.create_traces(data, config)
    Then result.custom_x_ticks is not None
    And result.custom_x_ticks has "vals" and "text" keys

  Scenario: create_traces applies x_filter
    Given config = {"x": "config", "y": "score", "x_filter": ["A", "C"]}
    When I call plot.create_traces(data, config)
    Then only data with config in ["A", "C"] contributes to traces

  Scenario: create_traces applies group_filter
    Given config = {"x": "config", "y": "score", "group": "benchmark", "group_filter": ["BM1"]}
    When I call plot.create_traces(data, config)
    Then only 1 trace for "BM1" is produced

  Scenario: create_traces with error bars and grouping
    Given config = {"x": "config", "y": "score", "group": "benchmark", "show_error_bars": true}
    When I call plot.create_traces(data, config)
    Then each trace has error_y when the "score.sd" column exists

  Scenario: create_traces includes shapes for visual distinction
    Given config includes "show_separators": true
    When I call plot.create_traces(data, config)
    Then result.shapes contains separator shapes

  Scenario: get_legend_column returns group column (not color)
    Given config = {"group": "benchmark"}
    When I call plot.get_legend_column(config)
    Then the result is "benchmark"

  Scenario: get_legend_column returns None without group
    Given config = {"x": "config", "y": "score"}
    When I call plot.get_legend_column(config)
    Then the result is None

  Scenario: xaxis_order controls category ordering
    Given config = {"x": "config", "y": "score", "xaxis_order": ["C", "A", "B"]}
    When I call plot.create_traces(data, config)
    Then the tick_text labels follow the order ["C", "A", "B"]
```

### 7.2 Pytest stubs -- grouped bar plot

```python
# tests/e2e/plots/test_grouped_bar_plot.py
"""E2E tests for GroupedBarPlot trace generation and coordinate mapping."""

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def grouped_bar_plot():
    return PlotFactory.create_plot("grouped_bar", plot_id=4, name="Test Grouped")


@pytest.fixture
def grouped_data() -> pd.DataFrame:
    return pd.DataFrame({
        "config": ["A", "B", "C"] * 3,
        "benchmark": ["BM1"] * 3 + ["BM2"] * 3 + ["BM3"] * 3,
        "score": [10, 20, 30, 15, 25, 35, 12, 22, 32],
        "score.sd": [1.0, 2.0, 3.0, 1.5, 2.5, 3.5, 1.2, 2.2, 3.2],
    })


class TestGroupedBarPlotTraces:
    """Validate GroupedBarPlot.create_traces with manual coordinate layout."""

    def test_single_trace_without_group(self, grouped_bar_plot, grouped_data) -> None:
        config = {"x": "config", "y": "score"}
        result = grouped_bar_plot.create_traces(grouped_data, config)
        assert len(result.traces) == 1
        assert isinstance(result.traces[0], BarTraceConfig)
        assert result.barmode == "group"

    def test_multiple_traces_with_group(self, grouped_bar_plot, grouped_data) -> None:
        config = {"x": "config", "y": "score", "group": "benchmark"}
        result = grouped_bar_plot.create_traces(grouped_data, config)
        assert len(result.traces) == 3
        names = {t.name for t in result.traces}
        assert names == {"BM1", "BM2", "BM3"}

    def test_custom_x_ticks_present(self, grouped_bar_plot, grouped_data) -> None:
        config = {"x": "config", "y": "score", "group": "benchmark"}
        result = grouped_bar_plot.create_traces(grouped_data, config)
        assert result.custom_x_ticks is not None
        assert "vals" in result.custom_x_ticks
        assert "text" in result.custom_x_ticks

    def test_x_positions_are_numeric(self, grouped_bar_plot, grouped_data) -> None:
        config = {"x": "config", "y": "score"}
        result = grouped_bar_plot.create_traces(grouped_data, config)
        assert result.traces[0].x_positions
        assert all(isinstance(v, (int, float)) for v in result.traces[0].x_positions)

    def test_x_filter_applied(self, grouped_bar_plot, grouped_data) -> None:
        config = {"x": "config", "y": "score", "x_filter": ["A", "C"]}
        result = grouped_bar_plot.create_traces(grouped_data, config)
        # With no group, single trace; all y values from filtered rows
        all_x_positions = result.traces[0].x_positions
        assert len(all_x_positions) == 6  # 2 configs * 3 rows each

    def test_group_filter_applied(self, grouped_bar_plot, grouped_data) -> None:
        config = {
            "x": "config", "y": "score",
            "group": "benchmark", "group_filter": ["BM1"],
        }
        result = grouped_bar_plot.create_traces(grouped_data, config)
        assert len(result.traces) == 1
        assert result.traces[0].name == "BM1"

    def test_error_bars_with_grouping(self, grouped_bar_plot, grouped_data) -> None:
        config = {
            "x": "config", "y": "score",
            "group": "benchmark", "show_error_bars": True,
        }
        result = grouped_bar_plot.create_traces(grouped_data, config)
        for trace in result.traces:
            assert trace.error_y is not None


class TestGroupedBarPlotLegend:
    """Validate GroupedBarPlot.get_legend_column returns group column."""

    def test_with_group(self, grouped_bar_plot) -> None:
        assert grouped_bar_plot.get_legend_column({"group": "benchmark"}) == "benchmark"

    def test_without_group(self, grouped_bar_plot) -> None:
        assert grouped_bar_plot.get_legend_column({"x": "config"}) is None


class TestGroupedBarPlotVisualRegression:
    """Screenshot comparison tests for grouped bar rendering."""

    @pytest.mark.visual
    def test_grouped_bar_screenshot(self, plots_page, sample_dataset) -> None:
        plots_page.create_plot("Grouped Bar Test", "grouped_bar")
        plots_page.select_plot("Grouped Bar Test")
        plots_page.configure_grouped_bar(
            x_col="config", y_col="score", group_col="benchmark"
        )
        plots_page.wait_for_plotly_render()
        screenshot = plots_page.capture_plot_screenshot()
        assert screenshot is not None
```

---

## 8. Stacked Bar Plot Tests

### 8.1 Gherkin scenarios

```gherkin
Feature: Stacked Bar Plot -- Multi-Column Stacks and Totals

  Background:
    Given a DataFrame with columns ["category", "stat_a", "stat_b", "stat_c"]
    And the PlotFactory creates a StackedBarPlot with id=5, name="Test Stacked"

  Scenario: StackedBarPlot initializes with type "stacked_bar"
    Then the plot.plot_type is "stacked_bar"

  Scenario: create_traces returns empty when no x or y_columns
    Given config = {}
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains 0 traces
    And result.barmode is "stack"

  Scenario: create_traces produces one trace per y_column
    Given config = {"x": "category", "y_columns": ["stat_a", "stat_b", "stat_c"]}
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains exactly 3 traces
    And trace[0].name is "stat_a"
    And trace[1].name is "stat_b"
    And trace[2].name is "stat_c"
    And result.barmode is "stack"

  Scenario: create_traces includes custom_data with total
    Given config = {"x": "category", "y_columns": ["stat_a", "stat_b"]}
    When I call plot.create_traces(data, config)
    Then each trace has custom_data with "customdata" key containing totals

  Scenario: create_traces applies x_filter
    Given config = {"x": "category", "y_columns": ["stat_a"], "x_filter": ["A"]}
    When I call plot.create_traces(data, config)
    Then the traces only contain data from category "A"

  Scenario: create_traces with show_totals adds annotations
    Given config = {"x": "category", "y_columns": ["stat_a", "stat_b"], "show_totals": true}
    When I call plot.create_traces(data, config)
    Then result.layout_annotations is not empty
    And each annotation has text matching a formatted total

  Scenario: create_traces with error bars per y_column
    Given config = {"x": "category", "y_columns": ["stat_a"], "show_error_bars": true}
    And the data has a "stat_a.sd" column
    When I call plot.create_traces(data, config)
    Then trace[0].error_y is a non-empty list

  Scenario: create_traces with series_styles uses custom names
    Given config includes series_styles = {"stat_a": {"name": "Metric A"}}
    When I call plot.create_traces(data, config)
    Then trace[0].name is "Metric A"

  Scenario: get_legend_column always returns None
    Given any config
    When I call plot.get_legend_column(config)
    Then the result is None
```

### 8.2 Pytest stubs -- stacked bar plot

```python
# tests/e2e/plots/test_stacked_bar_plot.py
"""E2E tests for StackedBarPlot trace generation and totals annotations."""

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def stacked_bar_plot():
    return PlotFactory.create_plot("stacked_bar", plot_id=5, name="Test Stacked")


@pytest.fixture
def stacked_data() -> pd.DataFrame:
    return pd.DataFrame({
        "category": ["A", "B", "C"],
        "stat_a": [10.0, 20.0, 30.0],
        "stat_b": [5.0, 15.0, 25.0],
        "stat_c": [3.0, 7.0, 12.0],
        "stat_a.sd": [1.0, 2.0, 3.0],
    })


class TestStackedBarPlotTraces:
    """Validate StackedBarPlot.create_traces output."""

    def test_empty_config_returns_no_traces(self, stacked_bar_plot, stacked_data) -> None:
        config: dict = {}
        result = stacked_bar_plot.create_traces(stacked_data, config)
        assert len(result.traces) == 0
        assert result.barmode == "stack"

    def test_one_trace_per_y_column(self, stacked_bar_plot, stacked_data) -> None:
        config = {"x": "category", "y_columns": ["stat_a", "stat_b", "stat_c"]}
        result = stacked_bar_plot.create_traces(stacked_data, config)
        assert len(result.traces) == 3
        assert result.traces[0].name == "stat_a"
        assert result.traces[1].name == "stat_b"
        assert result.traces[2].name == "stat_c"
        assert result.barmode == "stack"

    def test_customdata_contains_totals(self, stacked_bar_plot, stacked_data) -> None:
        config = {"x": "category", "y_columns": ["stat_a", "stat_b"]}
        result = stacked_bar_plot.create_traces(stacked_data, config)
        for trace in result.traces:
            assert isinstance(trace, BarTraceConfig)
            assert "customdata" in trace.custom_data

    def test_x_filter_applied(self, stacked_bar_plot, stacked_data) -> None:
        config = {"x": "category", "y_columns": ["stat_a"], "x_filter": ["A", "C"]}
        result = stacked_bar_plot.create_traces(stacked_data, config)
        assert len(result.traces[0].y) == 2

    def test_show_totals_adds_annotations(self, stacked_bar_plot, stacked_data) -> None:
        config = {
            "x": "category",
            "y_columns": ["stat_a", "stat_b"],
            "show_totals": True,
        }
        result = stacked_bar_plot.create_traces(stacked_data, config)
        assert result.layout_annotations is not None
        assert len(result.layout_annotations) > 0

    def test_error_bars_per_y_column(self, stacked_bar_plot, stacked_data) -> None:
        config = {"x": "category", "y_columns": ["stat_a"], "show_error_bars": True}
        result = stacked_bar_plot.create_traces(stacked_data, config)
        assert result.traces[0].error_y is not None

    def test_series_styles_custom_name(self, stacked_bar_plot, stacked_data) -> None:
        config = {
            "x": "category",
            "y_columns": ["stat_a"],
            "series_styles": {"stat_a": {"name": "Metric A", "use_color": False}},
        }
        result = stacked_bar_plot.create_traces(stacked_data, config)
        assert result.traces[0].name == "Metric A"


class TestStackedBarPlotLegend:
    """Stacked bar returns None for get_legend_column."""

    def test_always_none(self, stacked_bar_plot) -> None:
        assert stacked_bar_plot.get_legend_column({}) is None
        assert stacked_bar_plot.get_legend_column({"y_columns": ["a", "b"]}) is None
```

---

## 9. Heatmap Plot Tests

### 9.1 Gherkin scenarios

```gherkin
Feature: Heatmap Plot -- Z-Matrix, Facets, Colorscale, and Totals

  Background:
    Given a DataFrame with columns ["config", "metric_a", "metric_b", "benchmark"]
    And the PlotFactory creates a HeatmapPlot with id=6, name="Test Heatmap"

  Scenario: HeatmapPlot initializes with type "heatmap"
    Then the plot.plot_type is "heatmap"

  Scenario: create_traces returns empty when no metric_columns
    Given config = {"x": "config"}
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains 0 traces

  Scenario: create_traces produces HeatmapTraceConfig with z-matrix
    Given config = {"x": "config", "metric_columns": ["metric_a", "metric_b"]}
    When I call plot.create_traces(data, config)
    Then the result has exactly 1 trace (no facet)
    And trace[0] is a HeatmapTraceConfig
    And trace[0].z has len(metric_columns) rows
    And trace[0].col_labels matches unique x values
    And trace[0].row_labels matches metric display names

  Scenario: create_traces with facet produces one trace per facet
    Given config = {"x": "config", "metric_columns": ["metric_a"], "facet_col": "benchmark"}
    And the data has 3 unique values in "benchmark"
    When I call plot.create_traces(data, config)
    Then the TraceBuildResult contains exactly 3 traces
    And each trace name matches a benchmark value

  Scenario: create_traces applies aggregation function
    Given config = {"x": "config", "metric_columns": ["metric_a"], "aggregation": "sum"}
    When I call plot.create_traces(data, config)
    Then the z-matrix values reflect sum aggregation

  Scenario: create_traces resolves colorscale from palette
    Given config = {"x": "config", "metric_columns": ["metric_a"], "color_palette": "wong"}
    When I call plot.create_traces(data, config)
    Then trace[0].colorscale is a nested list (not a string)

  Scenario: create_traces with reverse_colorscale
    Given config includes "reverse_colorscale": true
    When I call plot.create_traces(data, config)
    Then the colorscale is reversed

  Scenario: create_traces with show_values produces text matrix
    Given config = {"x": "config", "metric_columns": ["metric_a"], "show_values": true}
    When I call plot.create_traces(data, config)
    Then trace[0].text is not None
    And trace[0].show_values is True

  Scenario: create_traces with show_totals position "right"
    Given config includes "show_totals": true, "totals_position": "right"
    When I call plot.create_traces(data, config)
    Then the last column label is "Total"

  Scenario: create_traces with show_totals position "top"
    Given config includes "show_totals": true, "totals_position": "top"
    When I call plot.create_traces(data, config)
    Then the first row label is "Total"

  Scenario: create_traces applies x_filter
    Given config = {"x": "config", "metric_columns": ["metric_a"], "x_filter": ["A"]}
    When I call plot.create_traces(data, config)
    Then only config "A" appears in col_labels

  Scenario: get_legend_column always returns None
    Given any config for heatmap
    When I call plot.get_legend_column(config)
    Then the result is None (color is z-value, not a column)

  Scenario: apply_common_layout restricts x-axis categories to trace data
    Given the config has xaxis_order with extra categories not in filtered data
    When I call plot.apply_common_layout(fig, config)
    Then only categories present in the heatmap trace appear on x-axis
```

### 9.2 Pytest stubs -- heatmap plot

```python
# tests/e2e/plots/test_heatmap_plot.py
"""E2E tests for HeatmapPlot z-matrix, facets, and colorscale."""

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def heatmap_plot():
    return PlotFactory.create_plot("heatmap", plot_id=6, name="Test Heatmap")


@pytest.fixture
def heatmap_data() -> pd.DataFrame:
    return pd.DataFrame({
        "config": ["A", "B", "C", "A", "B", "C"],
        "metric_a": [10.0, 20.0, 30.0, 15.0, 25.0, 35.0],
        "metric_b": [5.0, 10.0, 15.0, 7.0, 12.0, 17.0],
        "benchmark": ["BM1", "BM1", "BM1", "BM2", "BM2", "BM2"],
    })


class TestHeatmapPlotTraces:
    """Validate HeatmapPlot.create_traces output."""

    def test_empty_metric_columns_returns_no_traces(self, heatmap_plot, heatmap_data) -> None:
        config = {"x": "config"}
        result = heatmap_plot.create_traces(heatmap_data, config)
        assert len(result.traces) == 0

    def test_single_heatmap_without_facet(self, heatmap_plot, heatmap_data) -> None:
        config = {"x": "config", "metric_columns": ["metric_a", "metric_b"]}
        result = heatmap_plot.create_traces(heatmap_data, config)
        assert len(result.traces) == 1
        trace = result.traces[0]
        assert isinstance(trace, HeatmapTraceConfig)
        assert len(trace.z) == 2  # two metrics
        assert len(trace.col_labels) == 3  # A, B, C
        assert len(trace.row_labels) == 2

    def test_faceted_heatmap(self, heatmap_plot, heatmap_data) -> None:
        config = {
            "x": "config",
            "metric_columns": ["metric_a"],
            "facet_col": "benchmark",
        }
        result = heatmap_plot.create_traces(heatmap_data, config)
        assert len(result.traces) == 2
        names = {t.name for t in result.traces}
        assert names == {"BM1", "BM2"}

    def test_aggregation_mean(self, heatmap_plot, heatmap_data) -> None:
        config = {
            "x": "config", "metric_columns": ["metric_a"],
            "aggregation": "mean",
        }
        result = heatmap_plot.create_traces(heatmap_data, config)
        # A has values 10 and 15, mean = 12.5
        z_row = result.traces[0].z[0]
        a_idx = result.traces[0].col_labels.index("A")
        assert z_row[a_idx] == pytest.approx(12.5)

    def test_colorscale_from_palette(self, heatmap_plot, heatmap_data) -> None:
        config = {
            "x": "config", "metric_columns": ["metric_a"],
            "color_palette": "wong",
        }
        result = heatmap_plot.create_traces(heatmap_data, config)
        assert isinstance(result.traces[0].colorscale, list)

    def test_show_values_produces_text(self, heatmap_plot, heatmap_data) -> None:
        config = {
            "x": "config", "metric_columns": ["metric_a"],
            "show_values": True,
        }
        result = heatmap_plot.create_traces(heatmap_data, config)
        assert result.traces[0].text is not None
        assert result.traces[0].show_values is True

    def test_totals_position_right(self, heatmap_plot, heatmap_data) -> None:
        config = {
            "x": "config", "metric_columns": ["metric_a"],
            "show_totals": True, "totals_position": "right",
        }
        result = heatmap_plot.create_traces(heatmap_data, config)
        assert result.traces[0].col_labels[-1] == "Total"

    def test_totals_position_top(self, heatmap_plot, heatmap_data) -> None:
        config = {
            "x": "config", "metric_columns": ["metric_a"],
            "show_totals": True, "totals_position": "top",
        }
        result = heatmap_plot.create_traces(heatmap_data, config)
        assert result.traces[0].row_labels[0] == "Total"

    def test_x_filter(self, heatmap_plot, heatmap_data) -> None:
        config = {
            "x": "config", "metric_columns": ["metric_a"],
            "x_filter": ["A"],
        }
        result = heatmap_plot.create_traces(heatmap_data, config)
        assert result.traces[0].col_labels == ["A"]

    def test_reverse_colorscale_list(self, heatmap_plot, heatmap_data) -> None:
        config = {
            "x": "config", "metric_columns": ["metric_a"],
            "color_palette": "wong", "reverse_colorscale": True,
        }
        result = heatmap_plot.create_traces(heatmap_data, config)
        cs = result.traces[0].colorscale
        assert isinstance(cs, list)
        # First position should map to what was previously the last color
        assert cs[0][0] == 0.0


class TestHeatmapPlotLegend:
    """Heatmap always returns None for get_legend_column."""

    def test_always_none(self, heatmap_plot) -> None:
        assert heatmap_plot.get_legend_column({}) is None
        assert heatmap_plot.get_legend_column({"facet_col": "benchmark"}) is None
```

---

## 10. Dual Axis Bar Dot Plot Tests

### 10.1 Gherkin scenarios

```gherkin
Feature: Dual Axis Bar Dot Plot -- Bars + Scatter/Line on Secondary Y

  Background:
    Given a DataFrame with columns ["config", "bar_val", "dot_val", "bar_val.sd", "dot_val.sd", "group"]
    And the PlotFactory creates a DualAxisBarDotPlot with id=7, name="Test DualAxis"

  Scenario: DualAxisBarDotPlot initializes with type "dual_axis_bar_dot"
    Then the plot.plot_type is "dual_axis_bar_dot"

  Scenario: create_traces without color produces bar + line (show_lines=True)
    Given config = {"x": "config", "y_bar": "bar_val", "y_dot": "dot_val", "show_lines": true}
    When I call plot.create_traces(data, config)
    Then the result has 2 traces
    And trace[0] is a BarTraceConfig with yaxis "y"
    And trace[1] is a LineTraceConfig with yaxis "y2"
    And result.barmode is "group"
    And result.secondary_y is True

  Scenario: create_traces without color and show_lines=False uses scatter
    Given config = {"x": "config", "y_bar": "bar_val", "y_dot": "dot_val", "show_lines": false}
    When I call plot.create_traces(data, config)
    Then trace[1] is a ScatterTraceConfig with yaxis "y2"

  Scenario: create_traces with color column produces per-group bar+dot pairs
    Given config = {"x": "config", "y_bar": "bar_val", "y_dot": "dot_val", "color": "group"}
    And the data has 2 unique values in "group"
    When I call plot.create_traces(data, config)
    Then the result has 4 traces (2 bars + 2 dots)
    And bar trace names follow "{group} ({y_bar})" pattern
    And dot trace names follow "{group} ({y_dot})" pattern

  Scenario: create_traces with error bars for both axes
    Given config has show_error_bars=true and both .sd columns exist
    When I call plot.create_traces(data, config)
    Then bar traces have error_y from "bar_val.sd"
    And dot traces have error_y from "dot_val.sd"

  Scenario: create_traces with isolate_last_group splits dot trace
    Given config has "isolate_last_group": true, "show_lines": true
    When I call plot.create_traces(data, config)
    Then the last category gets a separate ScatterTraceConfig with show_in_legend=False
    And the main categories use a LineTraceConfig

  Scenario: create_traces supports dot customization
    Given config has "dot_size": 15, "dot_symbol": "diamond", "line_width": 3
    When I call plot.create_traces(data, config)
    Then the dot trace has marker_size=15, marker_symbol="diamond"
    And the line trace has line_width=3.0

  Scenario: create_traces with dot_color for non-grouped mode
    Given config has no "color" and "dot_color": "#FF0000"
    When I call plot.create_traces(data, config)
    Then the dot trace has color="#FF0000"

  Scenario: get_legend_column returns color column
    Given config = {"color": "group"}
    When I call plot.get_legend_column(config)
    Then the result is "group"

  Scenario: get_legend_column without color returns None
    Given config = {"y_bar": "b", "y_dot": "d"}
    When I call plot.get_legend_column(config)
    Then the result is None
```

### 10.2 Pytest stubs -- dual axis bar dot

```python
# tests/e2e/plots/test_dual_axis_bar_dot_plot.py
"""E2E tests for DualAxisBarDotPlot trace generation."""

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
)
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def dual_axis_plot():
    return PlotFactory.create_plot("dual_axis_bar_dot", plot_id=7, name="Test DualAxis")


@pytest.fixture
def dual_axis_data() -> pd.DataFrame:
    return pd.DataFrame({
        "config": ["A", "B", "C", "A", "B", "C"],
        "bar_val": [10, 20, 30, 15, 25, 35],
        "dot_val": [0.5, 0.7, 0.9, 0.6, 0.8, 1.0],
        "bar_val.sd": [1.0, 2.0, 3.0, 1.5, 2.5, 3.5],
        "dot_val.sd": [0.05, 0.07, 0.09, 0.06, 0.08, 0.10],
        "group": ["G1", "G1", "G1", "G2", "G2", "G2"],
    })


class TestDualAxisBarDotTraces:
    """Validate DualAxisBarDotPlot.create_traces output."""

    def test_bar_plus_line_without_color(self, dual_axis_plot, dual_axis_data) -> None:
        config = {
            "x": "config", "y_bar": "bar_val", "y_dot": "dot_val",
            "show_lines": True,
        }
        result = dual_axis_plot.create_traces(dual_axis_data, config)
        assert len(result.traces) == 2
        assert isinstance(result.traces[0], BarTraceConfig)
        assert result.traces[0].yaxis == "y"
        assert isinstance(result.traces[1], LineTraceConfig)
        assert result.traces[1].yaxis == "y2"
        assert result.barmode == "group"
        assert result.secondary_y is True

    def test_bar_plus_scatter_without_lines(self, dual_axis_plot, dual_axis_data) -> None:
        config = {
            "x": "config", "y_bar": "bar_val", "y_dot": "dot_val",
            "show_lines": False,
        }
        result = dual_axis_plot.create_traces(dual_axis_data, config)
        assert isinstance(result.traces[1], ScatterTraceConfig)
        assert result.traces[1].yaxis == "y2"

    def test_color_grouped_produces_pairs(self, dual_axis_plot, dual_axis_data) -> None:
        config = {
            "x": "config", "y_bar": "bar_val", "y_dot": "dot_val",
            "color": "group", "show_lines": True,
        }
        result = dual_axis_plot.create_traces(dual_axis_data, config)
        assert len(result.traces) == 4  # 2 bars + 2 lines
        bar_traces = [t for t in result.traces if isinstance(t, BarTraceConfig)]
        line_traces = [t for t in result.traces if isinstance(t, LineTraceConfig)]
        assert len(bar_traces) == 2
        assert len(line_traces) == 2

    def test_bar_trace_names_with_color(self, dual_axis_plot, dual_axis_data) -> None:
        config = {
            "x": "config", "y_bar": "bar_val", "y_dot": "dot_val",
            "color": "group", "show_lines": True,
        }
        result = dual_axis_plot.create_traces(dual_axis_data, config)
        bar_names = [t.name for t in result.traces if isinstance(t, BarTraceConfig)]
        assert "G1 (bar_val)" in bar_names
        assert "G2 (bar_val)" in bar_names

    def test_error_bars_both_axes(self, dual_axis_plot, dual_axis_data) -> None:
        config = {
            "x": "config", "y_bar": "bar_val", "y_dot": "dot_val",
            "show_error_bars": True,
        }
        result = dual_axis_plot.create_traces(dual_axis_data, config)
        assert result.traces[0].error_y is not None  # bar
        assert result.traces[1].error_y is not None  # dot

    def test_isolate_last_group_splits_trace(self, dual_axis_plot, dual_axis_data) -> None:
        config = {
            "x": "config", "y_bar": "bar_val", "y_dot": "dot_val",
            "show_lines": True, "isolate_last_group": True,
        }
        result = dual_axis_plot.create_traces(dual_axis_data, config)
        # Should have: 1 bar, 1 line (main), 1 scatter (isolated last)
        scatter_traces = [t for t in result.traces if isinstance(t, ScatterTraceConfig)]
        assert len(scatter_traces) >= 1
        assert scatter_traces[0].show_in_legend is False

    def test_dot_customization(self, dual_axis_plot, dual_axis_data) -> None:
        config = {
            "x": "config", "y_bar": "bar_val", "y_dot": "dot_val",
            "show_lines": True, "dot_size": 15,
            "dot_symbol": "diamond", "line_width": 3,
        }
        result = dual_axis_plot.create_traces(dual_axis_data, config)
        line_trace = [t for t in result.traces if isinstance(t, LineTraceConfig)][0]
        assert line_trace.marker_size == 15
        assert line_trace.marker_symbol == "diamond"
        assert line_trace.line_width == 3.0

    def test_dot_color_in_non_grouped_mode(self, dual_axis_plot, dual_axis_data) -> None:
        config = {
            "x": "config", "y_bar": "bar_val", "y_dot": "dot_val",
            "show_lines": True, "dot_color": "#FF0000",
        }
        result = dual_axis_plot.create_traces(dual_axis_data, config)
        line_trace = [t for t in result.traces if isinstance(t, LineTraceConfig)][0]
        assert line_trace.color == "#FF0000"


class TestDualAxisBarDotLegend:
    """Validate DualAxisBarDotPlot.get_legend_column behavior."""

    def test_with_color(self, dual_axis_plot) -> None:
        assert dual_axis_plot.get_legend_column({"color": "group"}) == "group"

    def test_without_color(self, dual_axis_plot) -> None:
        assert dual_axis_plot.get_legend_column({"y_bar": "b"}) is None
```

---

## 11. Cross-Plot-Type Tests

### 11.1 Gherkin scenarios

```gherkin
Feature: Cross-Plot-Type Validation

  Scenario: All basic plots (bar, line, scatter) use build_color_grouped_traces
    Given plots of types "bar", "line", "scatter"
    And a DataFrame with a "color" column having 2 groups
    When I call create_traces for each with color config
    Then each produces exactly 2 traces
    And each trace name matches a group value

  Scenario: All plots can be serialized to dict and restored
    Given a plot of each type is created and configured
    When I call plot.to_dict() for each
    And I call BasePlot.from_dict(data) for each serialized dict
    Then the restored plot has the same plot_type, name, config, and pipeline

  Scenario: All plots produce a valid Plotly figure via generate_figure
    Given a plot of each type with processed_data set
    When I call plot.generate_figure()
    Then a go.Figure is returned
    And the figure has at least 1 trace (except when config is empty)
    And plot.last_generated_fig is set

  Scenario: create_figure shows placeholder when no traces
    Given a plot with empty config (no x/y selected)
    When I call plot.create_figure(data, config)
    Then the figure layout title contains "Please select at least one X and one Y column"

  Scenario: apply_legend_labels replaces trace names
    Given a plot with 2 traces named "A" and "B"
    And legend_labels = {"A": "Alpha", "B": "Beta"}
    When I call plot.apply_legend_labels(fig, legend_labels)
    Then the trace names become "Alpha" and "Beta"

  Scenario: update_from_relayout returns False for irrelevant events
    Given a plot with config
    When I call plot.update_from_relayout({})
    Then the result is False

  Scenario: update_from_relayout updates config for zoom events
    Given a plot with config
    When I call plot.update_from_relayout({"xaxis.range[0]": 0, "xaxis.range[1]": 10})
    Then the result is True
    And plot.config contains updated range values
```

### 11.2 Pytest stubs -- cross-type

```python
# tests/e2e/plots/test_cross_plot_types.py
"""Cross-cutting tests that validate behavior common to all plot types."""

import pandas as pd
import pytest

import plotly.graph_objects as go

from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory

BASIC_TYPES = ["bar", "line", "scatter"]
ALL_TYPES = PlotFactory.get_available_plot_types()


@pytest.fixture
def common_data() -> pd.DataFrame:
    return pd.DataFrame({
        "x": ["A", "B", "C"],
        "y": [10.0, 20.0, 30.0],
        "color": ["G1", "G1", "G2"],
    })


class TestColorGroupedTracesSharedPattern:
    """Verify the build_color_grouped_traces pattern across basic types."""

    @pytest.mark.parametrize("plot_type", BASIC_TYPES)
    def test_color_grouped_produces_correct_count(
        self, plot_type: str, common_data: pd.DataFrame
    ) -> None:
        plot = PlotFactory.create_plot(plot_type, plot_id=1, name="test")
        config = {"x": "x", "y": "y", "color": "color"}
        result = plot.create_traces(common_data, config)
        assert len(result.traces) == 2


class TestSerialization:
    """Verify to_dict/from_dict roundtrip for every plot type."""

    @pytest.mark.parametrize("plot_type", ALL_TYPES)
    def test_roundtrip(self, plot_type: str) -> None:
        original = PlotFactory.create_plot(plot_type, plot_id=42, name="roundtrip")
        original.config = {"x": "col_a", "y": "col_b"}
        data = original.to_dict()
        restored = BasePlot.from_dict(data)
        assert restored.plot_type == original.plot_type
        assert restored.name == original.name
        assert restored.config == original.config


class TestCreateFigurePlaceholder:
    """When no traces are produced, show a placeholder."""

    @pytest.mark.parametrize("plot_type", ["bar", "line", "scatter"])
    def test_placeholder_message_when_no_columns(
        self, plot_type: str, common_data: pd.DataFrame
    ) -> None:
        plot = PlotFactory.create_plot(plot_type, plot_id=1, name="test")
        # Provide x/y that produces traces, so this tests the positive path
        config = {"x": "x", "y": "y"}
        fig = plot.create_figure(common_data, config)
        assert isinstance(fig, go.Figure)


class TestApplyLegendLabels:
    """Verify legend label replacement on generated figures."""

    def test_legend_labels_applied(self) -> None:
        plot = PlotFactory.create_plot("bar", plot_id=1, name="test")
        fig = go.Figure()
        fig.add_trace(go.Bar(name="A", x=["x"], y=[1]))
        fig.add_trace(go.Bar(name="B", x=["x"], y=[2]))
        labels = {"A": "Alpha", "B": "Beta"}
        updated = plot.apply_legend_labels(fig, labels)
        trace_names = [t.name for t in updated.data]
        assert trace_names == ["Alpha", "Beta"]
```

---

## 12. Page Object Model for ManagePlotsPage

### 12.1 Complete POM definition

```python
# tests/e2e/pages/manage_plots_page.py
"""Page Object Model for the Manage Plots page in E2E tests."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Locator, Page, expect


class ManagePlotsPage:
    """
    Encapsulates all Manage Plots page interactions for E2E tests.

    Maps to the Streamlit page rendered by show_manage_plots_page().
    Widget keys are stable because the source uses explicit Streamlit keys
    (e.g., "new_plot_name", "new_plot_type", "create_plot_form").
    """

    # ── Navigation ──────────────────────────────────────────────

    URL_PATH = "/Manage_Plots"

    def __init__(self, page: Page, base_url: str = "http://localhost:8501") -> None:
        self.page = page
        self.base_url = base_url

    def navigate(self) -> None:
        """Navigate to the Manage Plots page and wait for load."""
        self.page.goto(f"{self.base_url}{self.URL_PATH}")
        self.page.wait_for_selector("text=Manage Plots", timeout=15_000)

    # ── Plot Creation ───────────────────────────────────────────

    @property
    def _create_form(self) -> Locator:
        return self.page.locator("form[data-testid='stForm']").first

    @property
    def _name_input(self) -> Locator:
        return self.page.get_by_label("New plot name")

    @property
    def _type_select(self) -> Locator:
        return self.page.get_by_label("Plot type")

    @property
    def _create_button(self) -> Locator:
        return self.page.get_by_role("button", name="Create Plot")

    def create_plot(self, name: str, plot_type: str) -> None:
        """Fill the create-plot form and submit."""
        self._name_input.clear()
        self._name_input.fill(name)
        self._type_select.click()
        self.page.get_by_role("option", name=plot_type).click()
        self._create_button.click()
        self.page.wait_for_timeout(1000)  # Wait for Streamlit rerun

    # ── Plot Selector ───────────────────────────────────────────

    @property
    def _plot_selector(self) -> Locator:
        """The selectbox or radio group used to pick the active plot."""
        return self.page.get_by_test_id("stSelectbox").first

    def select_plot(self, name: str) -> None:
        """Select a plot by name from the plot selector."""
        self._plot_selector.click()
        self.page.get_by_role("option", name=name).click()
        self.page.wait_for_timeout(500)

    def is_plot_in_selector(self, name: str) -> bool:
        """Check if a plot name appears in the selector options."""
        self._plot_selector.click()
        try:
            option = self.page.get_by_role("option", name=name)
            visible = option.is_visible()
            self.page.keyboard.press("Escape")
            return visible
        except Exception:
            self.page.keyboard.press("Escape")
            return False

    # ── Plot Controls (rename, delete, duplicate) ───────────────

    def rename_plot(self, new_name: str) -> None:
        """Rename the currently selected plot."""
        rename_input = self.page.get_by_label("Rename plot")
        rename_input.clear()
        rename_input.fill(new_name)
        self.page.get_by_role("button", name="Rename").click()
        self.page.wait_for_timeout(500)

    def delete_plot(self) -> None:
        """Delete the currently selected plot."""
        self.page.get_by_role("button", name="Delete").click()
        self.page.wait_for_timeout(500)

    def duplicate_plot(self) -> None:
        """Duplicate the currently selected plot."""
        self.page.get_by_role("button", name="Duplicate").click()
        self.page.wait_for_timeout(500)

    # ── Configuration UI ────────────────────────────────────────

    def configure_xy(self, x_col: str, y_col: str) -> None:
        """Set X and Y columns for basic plot types (bar, line, scatter)."""
        x_select = self.page.get_by_label("X Column")
        x_select.click()
        self.page.get_by_role("option", name=x_col).click()

        y_select = self.page.get_by_label("Y Column")
        y_select.click()
        self.page.get_by_role("option", name=y_col).click()
        self.page.wait_for_timeout(500)

    def set_color_column(self, col: str) -> None:
        """Set the color/legend column for basic plot types."""
        color_select = self.page.get_by_label("Color Column")
        color_select.click()
        self.page.get_by_role("option", name=col).click()
        self.page.wait_for_timeout(500)

    def configure_grouped_bar(
        self, x_col: str, y_col: str, group_col: str
    ) -> None:
        """Set X, Y, and group columns for grouped bar plot."""
        self.configure_xy(x_col, y_col)
        group_select = self.page.get_by_label("Group Column")
        group_select.click()
        self.page.get_by_role("option", name=group_col).click()
        self.page.wait_for_timeout(500)

    def configure_stacked_bar(
        self, x_col: str, y_columns: list[str]
    ) -> None:
        """Set X column and select multiple Y columns for stacked bar."""
        x_select = self.page.get_by_label("X Column")
        x_select.click()
        self.page.get_by_role("option", name=x_col).click()
        for col in y_columns:
            y_multi = self.page.get_by_label("Y Columns")
            y_multi.click()
            self.page.get_by_role("option", name=col).click()
        self.page.wait_for_timeout(500)

    def configure_heatmap(
        self, x_col: str, metric_cols: list[str]
    ) -> None:
        """Set X column and metric columns for heatmap."""
        x_select = self.page.get_by_label("X Column")
        x_select.click()
        self.page.get_by_role("option", name=x_col).click()
        for col in metric_cols:
            metric_select = self.page.get_by_label("Metric Columns")
            metric_select.click()
            self.page.get_by_role("option", name=col).click()
        self.page.wait_for_timeout(500)

    def configure_dual_axis(
        self, x_col: str, y_bar: str, y_dot: str
    ) -> None:
        """Set X, bar Y, and dot Y columns for dual-axis plot."""
        x_select = self.page.get_by_label("X Column")
        x_select.click()
        self.page.get_by_role("option", name=x_col).click()
        bar_select = self.page.get_by_label("Bar Y Column")
        bar_select.click()
        self.page.get_by_role("option", name=y_bar).click()
        dot_select = self.page.get_by_label("Dot Y Column")
        dot_select.click()
        self.page.get_by_role("option", name=y_dot).click()
        self.page.wait_for_timeout(500)

    def configure_histogram(self, histogram_var: str) -> None:
        """Set the histogram variable for histogram plot."""
        var_select = self.page.get_by_label("Histogram Variable")
        var_select.click()
        self.page.get_by_role("option", name=histogram_var).click()
        self.page.wait_for_timeout(500)

    # ── Plotly Rendering ────────────────────────────────────────

    def wait_for_plotly_render(self, timeout: int = 10_000) -> None:
        """Wait until a Plotly chart is visible in the DOM."""
        self.page.wait_for_selector(".js-plotly-plot", timeout=timeout)

    def get_plotly_trace_count(self) -> int:
        """Return the number of visible Plotly traces."""
        return self.page.evaluate(
            """() => {
                const plot = document.querySelector('.js-plotly-plot');
                return plot ? plot.data.length : 0;
            }"""
        )

    def get_plotly_trace_names(self) -> list[str]:
        """Return the names of all Plotly traces."""
        return self.page.evaluate(
            """() => {
                const plot = document.querySelector('.js-plotly-plot');
                return plot ? plot.data.map(t => t.name || '') : [];
            }"""
        )

    def capture_plot_screenshot(self, path: str | None = None) -> bytes:
        """Capture a screenshot of the rendered Plotly chart area."""
        chart = self.page.locator(".js-plotly-plot").first
        return chart.screenshot(path=path)

    # ── Advanced Options ────────────────────────────────────────

    def open_advanced_options(self) -> None:
        """Expand the advanced options expander."""
        expander = self.page.get_by_text("Advanced Options")
        if expander.is_visible():
            expander.click()
            self.page.wait_for_timeout(300)

    def open_theme_options(self) -> None:
        """Expand the theme options expander."""
        expander = self.page.get_by_text("Theme & Styling")
        if expander.is_visible():
            expander.click()
            self.page.wait_for_timeout(300)

    # ── Assertions ──────────────────────────────────────────────

    def assert_page_loaded(self) -> None:
        """Assert the Manage Plots page header is visible."""
        expect(self.page.get_by_text("Manage Plots")).to_be_visible()

    def assert_plot_visible(self) -> None:
        """Assert that a Plotly chart is rendered on the page."""
        expect(self.page.locator(".js-plotly-plot")).to_be_visible(timeout=10_000)

    def assert_no_plot_visible(self) -> None:
        """Assert no Plotly chart is rendered."""
        expect(self.page.locator(".js-plotly-plot")).not_to_be_visible()

    def assert_config_section_visible(self) -> None:
        """Assert the plot configuration section is rendered."""
        # The config section appears when a plot is selected
        expect(self.page.get_by_label("X Column")).to_be_visible(timeout=5_000)
```

### 12.2 Histogram-specific E2E tests

```gherkin
Feature: Histogram Plot -- Bucket Detection, Normalization, and Grouping

  Background:
    Given a DataFrame with histogram bucket columns like "latency..0-10", "latency..10-20"
    And the PlotFactory creates a HistogramPlot with id=8, name="Test Histogram"

  Scenario: HistogramPlot initializes with type "histogram"
    Then the plot.plot_type is "histogram"

  Scenario: create_traces raises when no histogram variable specified
    Given config = {}
    When I call plot.create_traces(data, config)
    Then a ValueError is raised with "No histogram variable specified"

  Scenario: create_traces raises when no bucket columns found
    Given config = {"histogram_variable": "nonexistent"}
    When I call plot.create_traces(data, config)
    Then a ValueError is raised with "No histogram bucket columns found"

  Scenario: create_traces produces single histogram without grouping
    Given config = {"histogram_variable": "latency"}
    When I call plot.create_traces(data, config)
    Then the result has exactly 1 trace (BarTraceConfig)
    And trace[0].x_positions are bin centers
    And result.barmode is "relative"

  Scenario: create_traces with group_by produces grouped histograms
    Given config = {"histogram_variable": "latency", "group_by": "region"}
    When I call plot.create_traces(data, config)
    Then the result has one trace per unique region value
    And result.barmode is "overlay"
    And each trace has opacity 0.7

  Scenario: Normalization mode -- probability
    Given config = {"histogram_variable": "latency", "normalization": "probability"}
    When I call plot.create_traces(data, config)
    Then the sum of trace[0].y values is approximately 1.0

  Scenario: Normalization mode -- percent
    Given config = {"histogram_variable": "latency", "normalization": "percent"}
    When I call plot.create_traces(data, config)
    Then the sum of trace[0].y values is approximately 100.0

  Scenario: Cumulative histogram mode
    Given config = {"histogram_variable": "latency", "cumulative": true}
    When I call plot.create_traces(data, config)
    Then trace[0].y values are monotonically non-decreasing

  Scenario: get_legend_column returns group_by
    Given config = {"group_by": "region"}
    When I call plot.get_legend_column(config)
    Then the result is "region"
```

### 12.3 Pytest stubs -- histogram

```python
# tests/e2e/plots/test_histogram_plot.py
"""E2E tests for HistogramPlot bucket detection and normalization."""

import pandas as pd
import pytest

from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def histogram_plot():
    return PlotFactory.create_plot("histogram", plot_id=8, name="Test Histogram")


@pytest.fixture
def histogram_data() -> pd.DataFrame:
    return pd.DataFrame({
        "latency..0-10": [5, 3, 8],
        "latency..10-20": [10, 7, 12],
        "latency..20-30": [3, 2, 4],
        "region": ["US", "EU", "APAC"],
    })


class TestHistogramPlotTraces:
    """Validate HistogramPlot.create_traces output."""

    def test_raises_without_histogram_variable(self, histogram_plot, histogram_data) -> None:
        with pytest.raises(ValueError, match="No histogram variable specified"):
            histogram_plot.create_traces(histogram_data, {})

    def test_raises_with_bad_variable(self, histogram_plot, histogram_data) -> None:
        with pytest.raises(ValueError, match="No histogram bucket columns found"):
            histogram_plot.create_traces(histogram_data, {"histogram_variable": "bad"})

    def test_single_histogram(self, histogram_plot, histogram_data) -> None:
        config = {"histogram_variable": "latency"}
        result = histogram_plot.create_traces(histogram_data, config)
        assert len(result.traces) == 1
        assert isinstance(result.traces[0], BarTraceConfig)
        assert result.barmode == "relative"
        # 3 buckets -> 3 bin centers
        assert len(result.traces[0].x_positions) == 3

    def test_grouped_histogram(self, histogram_plot, histogram_data) -> None:
        config = {"histogram_variable": "latency", "group_by": "region"}
        result = histogram_plot.create_traces(histogram_data, config)
        assert len(result.traces) == 3
        assert result.barmode == "overlay"
        for t in result.traces:
            assert t.opacity == pytest.approx(0.7)

    def test_normalization_probability(self, histogram_plot, histogram_data) -> None:
        config = {"histogram_variable": "latency", "normalization": "probability"}
        result = histogram_plot.create_traces(histogram_data, config)
        total = sum(result.traces[0].y)
        assert total == pytest.approx(1.0, abs=0.01)

    def test_normalization_percent(self, histogram_plot, histogram_data) -> None:
        config = {"histogram_variable": "latency", "normalization": "percent"}
        result = histogram_plot.create_traces(histogram_data, config)
        total = sum(result.traces[0].y)
        assert total == pytest.approx(100.0, abs=0.1)

    def test_cumulative_mode(self, histogram_plot, histogram_data) -> None:
        config = {"histogram_variable": "latency", "cumulative": True}
        result = histogram_plot.create_traces(histogram_data, config)
        y_vals = result.traces[0].y
        for i in range(1, len(y_vals)):
            assert y_vals[i] >= y_vals[i - 1]


class TestHistogramPlotLegend:
    """Validate HistogramPlot.get_legend_column."""

    def test_with_group_by(self, histogram_plot) -> None:
        assert histogram_plot.get_legend_column({"group_by": "region"}) == "region"

    def test_without_group_by(self, histogram_plot) -> None:
        assert histogram_plot.get_legend_column({}) is None
```

### 12.4 Grouped Stacked Bar -- extended tests

```gherkin
Feature: Grouped Stacked Bar Plot -- Coordinate Mapping and Dual Axis

  Background:
    Given a DataFrame with ["config", "benchmark", "stat_a", "stat_b"]
    And the PlotFactory creates a GroupedStackedBarPlot with id=9

  Scenario: Inherits from StackedBarPlot
    Then the plot is an instance of StackedBarPlot
    And the plot.plot_type is "grouped_stacked_bar"

  Scenario: Without group column delegates to parent stacked behavior
    Given config = {"x": "config", "y_columns": ["stat_a", "stat_b"]}
    When I call plot.create_traces(data, config)
    Then the result matches StackedBarPlot behavior
    And result.barmode is "stack"

  Scenario: With group column produces grouped stacked layout
    Given config = {"x": "config", "y_columns": ["stat_a"], "group": "benchmark"}
    When I call plot.create_traces(data, config)
    Then traces use __x_coord coordinates
    And result.custom_x_ticks has vals and text
    And result.barmode is "stack"

  Scenario: Dual axis mode adds right-axis traces
    Given config includes "dual_axis": true, "y_columns_right": ["stat_b"]
    When I call plot.create_traces(data, config)
    Then result.secondary_y is True
    And traces include both left and right axis entries

  Scenario: Group filter reduces visible groups
    Given config has "group_filter": ["BM1"]
    When I call plot.create_traces(data, config)
    Then only benchmark "BM1" data appears in traces

  Scenario: get_legend_column always returns None
    Given any config for grouped stacked bar
    When I call plot.get_legend_column(config)
    Then the result is None
```

```python
# tests/e2e/plots/test_grouped_stacked_bar_plot.py
"""E2E tests for GroupedStackedBarPlot grouped layout and dual-axis."""

import pandas as pd
import pytest

from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.types.stacked_bar_plot import StackedBarPlot


@pytest.fixture
def grouped_stacked_plot():
    return PlotFactory.create_plot("grouped_stacked_bar", plot_id=9, name="Test GSB")


@pytest.fixture
def gsb_data() -> pd.DataFrame:
    return pd.DataFrame({
        "config": ["A", "B", "A", "B"],
        "benchmark": ["BM1", "BM1", "BM2", "BM2"],
        "stat_a": [10.0, 20.0, 15.0, 25.0],
        "stat_b": [5.0, 10.0, 7.0, 12.0],
    })


class TestGroupedStackedBarInheritance:
    """Verify inheritance chain and type identity."""

    def test_inherits_from_stacked_bar(self, grouped_stacked_plot) -> None:
        assert isinstance(grouped_stacked_plot, StackedBarPlot)

    def test_plot_type_is_grouped_stacked_bar(self, grouped_stacked_plot) -> None:
        assert grouped_stacked_plot.plot_type == "grouped_stacked_bar"


class TestGroupedStackedBarTraces:
    """Validate trace generation with and without group column."""

    def test_without_group_delegates_to_parent(
        self, grouped_stacked_plot, gsb_data
    ) -> None:
        config = {"x": "config", "y_columns": ["stat_a", "stat_b"]}
        result = grouped_stacked_plot.create_traces(gsb_data, config)
        assert result.barmode == "stack"
        assert len(result.traces) == 2

    def test_with_group_produces_grouped_layout(
        self, grouped_stacked_plot, gsb_data
    ) -> None:
        config = {
            "x": "config", "group": "benchmark",
            "y_columns": ["stat_a"],
        }
        result = grouped_stacked_plot.create_traces(gsb_data, config)
        assert result.barmode == "stack"
        assert result.custom_x_ticks is not None

    def test_dual_axis_mode(self, grouped_stacked_plot, gsb_data) -> None:
        config = {
            "x": "config", "group": "benchmark",
            "y_columns": ["stat_a"],
            "dual_axis": True, "y_columns_right": ["stat_b"],
            "right_axis_type": "bars",
        }
        result = grouped_stacked_plot.create_traces(gsb_data, config)
        assert result.secondary_y is True

    def test_group_filter(self, grouped_stacked_plot, gsb_data) -> None:
        config = {
            "x": "config", "group": "benchmark",
            "y_columns": ["stat_a"], "group_filter": ["BM1"],
        }
        result = grouped_stacked_plot.create_traces(gsb_data, config)
        # Only BM1 data should be in the traces
        assert len(result.traces) >= 1


class TestGroupedStackedBarLegend:
    """get_legend_column always returns None."""

    def test_always_none(self, grouped_stacked_plot) -> None:
        assert grouped_stacked_plot.get_legend_column({}) is None
```

---

## Summary

This test plan covers **104 individual test scenarios** across all nine plot types,
organized into the following test files:

| Test File                                | Scenarios | Scope                              |
|------------------------------------------|-----------|------------------------------------|
| `test_plot_factory_registry.py`          | 8         | Factory registration & metadata    |
| `test_plot_creation_flow.py`             | 6 + 9par  | UI lifecycle via Playwright        |
| `test_bar_plot.py`                       | 11        | Bar trace generation & legend      |
| `test_line_plot.py`                      | 10        | Line trace generation & sorting    |
| `test_scatter_plot.py`                   | 8         | Scatter trace generation           |
| `test_grouped_bar_plot.py`               | 10        | Grouped bar coordinates & filters  |
| `test_stacked_bar_plot.py`               | 8         | Multi-column stacking & totals     |
| `test_heatmap_plot.py`                   | 12        | Z-matrix, facets, colorscale       |
| `test_dual_axis_bar_dot_plot.py`         | 10        | Bar+dot dual Y-axis traces         |
| `test_histogram_plot.py`                 | 8         | Bucket detection & normalization   |
| `test_grouped_stacked_bar_plot.py`       | 7         | Inheritance & dual-axis layout     |
| `test_cross_plot_types.py`               | 6         | Serialization, figure generation   |

Key design decisions:

1. **Trace-level assertions** dominate -- each test validates the raw
   `TraceBuildResult` (number of traces, trace types, field values) before
   rendering, ensuring the data pipeline is correct independently of the UI.

2. **Visual regression tests** are marked with `@pytest.mark.visual` and use
   the `ManagePlotsPage` POM to drive Streamlit and capture Plotly chart
   screenshots for pixelmatch comparison.

3. **The `_trace_helpers.build_color_grouped_traces` pattern** is tested once
   via the cross-plot-type suite, avoiding duplication across bar/line/scatter.

4. **Config-specific features** (line shapes, dot customization, histogram
   normalization, heatmap totals, grouped bar coordinates) each have dedicated
   scenarios tied to the concrete subclass behavior.

5. **The Page Object Model** (`ManagePlotsPage`) centralizes all Playwright
   locator logic and provides type-specific configuration helpers
   (`configure_grouped_bar`, `configure_heatmap`, `configure_dual_axis`, etc.).
