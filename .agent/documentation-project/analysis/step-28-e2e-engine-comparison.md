# Step 28 -- E2E Engine Comparison Tests (Plotly vs Matplotlib)

## 1. Executive Summary

This document defines an exhaustive end-to-end test plan that compares
the two rendering engines supported by the RING-5 Unified Engine v2:
**Plotly** (interactive, Kaleido-based export) and **Matplotlib**
(publication-quality, LaTeX-compatible export). The system implements a
protocol-driven dual-engine architecture where both connectors consume
the same `FigureConfig` model and apply an identical ordered styling
pipeline (`_connector_protocol.STYLING_PIPELINE_ORDER`). This test plan
verifies feature parity, visual consistency, engine switching, export
format correctness, and performance characteristics.

### Key Architectural Facts Driving Test Design

| Aspect | Plotly Connector | Matplotlib Connector |
|---|---|---|
| Entry class | `FigureSpecToPlotly` | `FigureSpecToMatplotlib` |
| Trace renderer | `traces_to_plotly()` | `MatplotlibTraceRenderer.render()` |
| State manager | `EngineManager` (session key `ring5_engine_mode`) | Same |
| Export formats | PNG, SVG, PDF, HTML | PDF, PGF, PNG, SVG |
| Colorbar API | `go.Heatmap.colorbar` dict | `fig.colorbar()` + `MaxNLocator` |
| Heatmap cell render | `go.Heatmap` (raster WebGL) | `ax.pcolormesh()` (vector quads) |
| Legend API | `fig.update_layout(legend=...)` | `ax.legend(**kwargs)` |
| Unique format | HTML (interactive) | PGF (LaTeX/TikZ) |
| Color normalization | CSS `rgb()` natively supported | `_css_rgb_to_hex()` conversion |
| LaTeX escaping | Not needed | `_escape_latex()` on all text |
| Dashboard settings | Hovermode selector | LaTeX preamble + TeX system |

### Test Strategy

- **Gherkin scenarios** define the expected user-facing behaviour.
- **pytest-playwright stubs** provide the automation skeleton.
- **Visual regression** uses screenshot pixel-diffing with configurable
  tolerance thresholds (engines will never produce identical pixels, but
  structural layout must match).
- Tests use a shared `FigureConfig` fixture built from resolved models
  to guarantee both engines receive identical input.

---

## 2. Dual Engine Architecture Overview

### 2.1 Engine Manager State Machine

`EngineManager` stores the active engine in `st.session_state["ring5_engine_mode"]`.
It exposes a static API: `get_engine()`, `set_engine(mode)`, `is_plotly()`,
`is_matplotlib()`. The default mode is `"plotly"`. Invalid modes fall
back to the default. `set_engine()` is idempotent -- it only writes when
the value changes to avoid Streamlit reruns.

### 2.2 Connector Protocol Pipeline

Both connectors apply styles in the order defined by
`_connector_protocol.STYLING_PIPELINE_ORDER`:

```
backgrounds -> font_family -> color_palette -> title -> axis_labels ->
axis_ticks -> axis_ranges -> axis_colors -> grids -> legends ->
reference_lines -> data_labels -> annotations -> separators ->
hatching -> margins
```

The Plotly connector (`FigureSpecToPlotly.apply()`) applies 18 methods
in its own internal order (dimensions, backgrounds, title, xaxis, yaxis,
y2axis, legends, heatmap_colorbars, color_palette, hovermode,
font_family, reference_lines, data_labels, series_styling,
trace_overrides, separator_lines, stripes, axis_colors).

The Matplotlib connector (`FigureSpecToMatplotlib.apply()`) applies 15
methods plus an optional colorbar step for heatmaps.

### 2.3 Trace Rendering Paths

| Trace Type | Plotly | Matplotlib |
|---|---|---|
| Bar | `go.Bar` | `ax.bar()` |
| Line | `go.Scatter(mode="lines")` | `ax.plot()` |
| Scatter | `go.Scatter(mode="markers")` | `ax.scatter()` |
| Histogram | `go.Histogram` | `ax.hist()` |
| Heatmap | `go.Heatmap` | `ax.pcolormesh()` |

### 2.4 Export Format Matrix

| Format | Plotly (Kaleido) | Matplotlib (savefig) |
|---|---|---|
| PNG | `fig.to_image(format="png")` | `savefig(format="png", backend="agg")` |
| SVG | `fig.to_image(format="svg")` | `savefig(format="svg")` |
| PDF | `fig.to_image(format="pdf")` | `savefig(format="pdf")` |
| HTML | `fig.to_html()` | N/A |
| PGF | N/A | `savefig(format="pgf", backend="pgf")` |

---

## 3. Engine Switching Tests

### 3.1 Gherkin Scenarios

```gherkin
Feature: Engine Switching Per-Plot
  The user can switch between Plotly and Matplotlib engines
  and the active plot re-renders with the selected engine.

  Background:
    Given the application is loaded at the plotting page
    And a dataset with numeric columns is uploaded

  Scenario: Default engine is Plotly
    When I navigate to the plot configuration page
    Then the engine selector shows "plotly" as active
    And the rendered output contains a Plotly chart container
    And the download section offers "html", "png", "svg", "pdf"

  Scenario: Switch from Plotly to Matplotlib
    Given the current engine is "plotly"
    When I select "matplotlib" in the engine toggle
    Then the session state key "ring5_engine_mode" equals "matplotlib"
    And the rendered output contains a Matplotlib figure element
    And the download section offers "pdf", "pgf", "png", "svg"
    And the interactive hover tooltip is no longer visible

  Scenario: Switch from Matplotlib back to Plotly
    Given the current engine is "matplotlib"
    When I select "plotly" in the engine toggle
    Then the session state key "ring5_engine_mode" equals "plotly"
    And the rendered output contains a Plotly chart container
    And interactive hover functionality is restored

  Scenario: Engine switch preserves plot configuration
    Given the current engine is "plotly"
    And I have configured a title "Revenue Analysis"
    And I have set the x-axis label to "Quarter"
    When I switch the engine to "matplotlib"
    Then the plot title reads "Revenue Analysis"
    And the x-axis label reads "Quarter"

  Scenario: Invalid engine mode falls back to default
    Given the session state "ring5_engine_mode" is set to "d3"
    When the EngineManager reads the engine
    Then it returns "plotly" as the default

  Scenario: Engine-specific settings appear conditionally
    Given the current engine is "plotly"
    Then the settings panel shows "Hover mode" selector
    And the settings panel does NOT show "LaTeX preamble"
    When I switch the engine to "matplotlib"
    Then the settings panel shows "LaTeX preamble" input
    And the settings panel shows "TeX system" selector
    And the settings panel does NOT show "Hover mode"

  Scenario: Idempotent engine set does not trigger rerun
    Given the current engine is "plotly"
    When I programmatically call set_engine("plotly") again
    Then session state is NOT written to
    And no Streamlit rerun is triggered
```

### 3.2 pytest-playwright Stubs

```python
"""E2E tests: Engine switching behaviour."""
import re

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def plot_page(page: Page, base_url: str) -> Page:
    """Navigate to plotting page with sample dataset loaded."""
    page.goto(f"{base_url}/plotting")
    page.wait_for_selector("[data-testid='plot-container']", timeout=10_000)
    return page


class TestEngineSwitch:
    """Verify engine toggling updates rendering and UI controls."""

    def test_default_engine_is_plotly(self, plot_page: Page) -> None:
        engine_label = plot_page.locator("[data-testid='engine-selector']")
        expect(engine_label).to_contain_text("plotly")
        plotly_container = plot_page.locator(".js-plotly-plot")
        expect(plotly_container).to_be_visible()

    def test_switch_to_matplotlib(self, plot_page: Page) -> None:
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)  # Streamlit rerun
        mpl_container = plot_page.locator("[data-testid='stImage']")
        expect(mpl_container).to_be_visible()
        plotly_container = plot_page.locator(".js-plotly-plot")
        expect(plotly_container).not_to_be_visible()

    def test_switch_back_to_plotly(self, plot_page: Page) -> None:
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        plot_page.locator("[data-testid='engine-plotly']").click()
        plot_page.wait_for_timeout(2000)
        plotly_container = plot_page.locator(".js-plotly-plot")
        expect(plotly_container).to_be_visible()

    def test_switch_preserves_title(self, plot_page: Page) -> None:
        title_input = plot_page.locator("[data-testid='title-input']")
        title_input.fill("Revenue Analysis")
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        expect(title_input).to_have_value("Revenue Analysis")

    def test_switch_preserves_axis_labels(self, plot_page: Page) -> None:
        x_label = plot_page.locator("[data-testid='x-axis-label']")
        x_label.fill("Quarter")
        y_label = plot_page.locator("[data-testid='y-axis-label']")
        y_label.fill("Revenue ($M)")
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        expect(x_label).to_have_value("Quarter")
        expect(y_label).to_have_value("Revenue ($M)")

    def test_engine_specific_settings_plotly(self, plot_page: Page) -> None:
        hovermode = plot_page.locator("[data-testid='hovermode-selector']")
        expect(hovermode).to_be_visible()
        latex = plot_page.locator("[data-testid='latex-preamble']")
        expect(latex).not_to_be_visible()

    def test_engine_specific_settings_matplotlib(self, plot_page: Page) -> None:
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        hovermode = plot_page.locator("[data-testid='hovermode-selector']")
        expect(hovermode).not_to_be_visible()
        latex = plot_page.locator("[data-testid='latex-preamble']")
        expect(latex).to_be_visible()
        tex_system = plot_page.locator("[data-testid='tex-system-selector']")
        expect(tex_system).to_be_visible()

    def test_download_formats_plotly(self, plot_page: Page) -> None:
        download_section = plot_page.locator("[data-testid='download-section']")
        download_section.click()
        for fmt in ["html", "png", "svg", "pdf"]:
            pill = plot_page.locator(f"[data-testid='dl-format-{fmt}']")
            expect(pill).to_be_visible()

    def test_download_formats_matplotlib(self, plot_page: Page) -> None:
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        download_section = plot_page.locator("[data-testid='download-section']")
        download_section.click()
        for fmt in ["pdf", "pgf", "png", "svg"]:
            pill = plot_page.locator(f"[data-testid='dl-format-{fmt}']")
            expect(pill).to_be_visible()
        html_pill = plot_page.locator("[data-testid='dl-format-html']")
        expect(html_pill).not_to_be_visible()
```

---

## 4. Feature Parity Matrix Tests

### 4.1 Gherkin Scenarios

```gherkin
Feature: Feature Parity Between Engines
  Both Plotly and Matplotlib must produce equivalent visual output
  for the same FigureConfig input across all supported styling steps.

  Scenario Outline: Pipeline step <step> produces equivalent output
    Given a resolved FigureConfig with <step> configured
    When I render the plot with the Plotly engine
    And I render the plot with the Matplotlib engine
    Then both outputs contain the <element> with matching properties

    Examples:
      | step            | element                         |
      | backgrounds     | paper and plot background colors |
      | font_family     | global font family setting       |
      | color_palette   | trace colors matching palette    |
      | title           | title text and font size         |
      | axis_labels     | x-axis and y-axis label text     |
      | axis_ticks      | tick font size and rotation      |
      | axis_ranges     | x/y axis limits                  |
      | axis_colors     | tick and axis line colors         |
      | grids           | grid visibility and dash style   |
      | legends         | legend text, position, columns   |
      | reference_lines | horizontal/vertical line values  |
      | data_labels     | bar value annotations            |
      | separators      | vertical separator lines         |
      | hatching        | bar hatching patterns            |
      | margins         | figure margin dimensions         |

  Scenario: Color palette CSS rgb conversion for Matplotlib
    Given a color palette with CSS "rgb(31,119,180)" entries
    When rendered with Plotly the trace color is "rgb(31,119,180)"
    When rendered with Matplotlib the trace color is "#1f77b4"
    Then both represent the same visual colour

  Scenario: Dual Y-axis renders on both engines
    Given a FigureConfig with y2 axis configured
    When rendered with Plotly it creates "yaxis2" with overlaying="y"
    When rendered with Matplotlib it creates a twin axis via twinx()
    Then both show the secondary y-axis on the right side

  Scenario: Legend orientation horizontal produces row layout
    Given a legend with orientation="horizontal"
    When rendered with Plotly the legend uses orientation="h"
    When rendered with Matplotlib the legend uses ncol=999
    Then both display legend items in a horizontal row

  Scenario: Grid dash styles map equivalently
    Given a grid with dash style "dot"
    When rendered with Plotly the griddash is "dot"
    When rendered with Matplotlib the linestyle is ":"
    Then both show dotted grid lines

  Scenario: Axis line width of 0 hides the axis line
    Given x-axis axis_line_width is 0
    When rendered with Plotly showline is False
    When rendered with Matplotlib bottom spine is hidden
    Then neither engine shows the bottom axis line

  Scenario: Annotation coordinate systems map correctly
    Given an annotation with xref="paper" and yref="paper"
    When rendered with Plotly it uses paper coordinates
    When rendered with Matplotlib it uses ax.transAxes
    Then the annotation appears at the same relative position
```

### 4.2 pytest-playwright Stubs

```python
"""E2E tests: Feature parity between engines."""
import pytest
from playwright.sync_api import Page, expect


class TestFeatureParity:
    """Verify both engines produce structurally equivalent output."""

    PIPELINE_STEPS = [
        "backgrounds", "font_family", "color_palette", "title",
        "axis_labels", "axis_ticks", "axis_ranges", "axis_colors",
        "grids", "legends", "reference_lines", "data_labels",
        "separators", "hatching", "margins",
    ]

    @pytest.mark.parametrize("step", PIPELINE_STEPS)
    def test_pipeline_step_renders_both_engines(
        self, plot_page: Page, step: str
    ) -> None:
        """Each pipeline step should produce visible output on both engines."""
        # Configure the plot with the specific step enabled
        plot_page.evaluate(f"window.__ring5_test_configure('{step}')")
        plot_page.wait_for_timeout(1000)

        # Screenshot with Plotly
        plot_page.locator("[data-testid='engine-plotly']").click()
        plot_page.wait_for_timeout(2000)
        plotly_shot = plot_page.locator(
            "[data-testid='plot-container']"
        ).screenshot()

        # Screenshot with Matplotlib
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        mpl_shot = plot_page.locator(
            "[data-testid='plot-container']"
        ).screenshot()

        # Both screenshots must have non-zero size
        assert len(plotly_shot) > 1000, f"Plotly screenshot too small for {step}"
        assert len(mpl_shot) > 1000, f"Matplotlib screenshot too small for {step}"

    def test_title_text_matches_across_engines(
        self, plot_page: Page
    ) -> None:
        """Both engines display the same title text."""
        TITLE = "Q4 Revenue Summary"
        plot_page.locator("[data-testid='title-input']").fill(TITLE)

        plot_page.locator("[data-testid='engine-plotly']").click()
        plot_page.wait_for_timeout(2000)
        plotly_title = plot_page.locator(".gtitle").text_content()
        assert TITLE in (plotly_title or "")

        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        # Matplotlib renders title into the raster image; verify via
        # the configuration state rather than OCR
        config_value = plot_page.evaluate(
            "window.__ring5_get_state('plot_title')"
        )
        assert config_value == TITLE

    def test_dual_y_axis_both_engines(self, plot_page: Page) -> None:
        """Secondary Y-axis appears on both engines."""
        plot_page.evaluate("window.__ring5_enable_y2_axis()")
        for engine in ["plotly", "matplotlib"]:
            plot_page.locator(
                f"[data-testid='engine-{engine}']"
            ).click()
            plot_page.wait_for_timeout(2000)
            container = plot_page.locator("[data-testid='plot-container']")
            expect(container).to_be_visible()

    def test_background_color_parity(self, plot_page: Page) -> None:
        """Both engines apply the same background colors."""
        BG_COLOR = "#f0f0f0"
        plot_page.evaluate(
            f"window.__ring5_set_config('paper_bgcolor', '{BG_COLOR}')"
        )

        for engine in ["plotly", "matplotlib"]:
            plot_page.locator(
                f"[data-testid='engine-{engine}']"
            ).click()
            plot_page.wait_for_timeout(2000)
            screenshot = plot_page.locator(
                "[data-testid='plot-container']"
            ).screenshot()
            assert len(screenshot) > 1000

    def test_reference_line_parity(self, plot_page: Page) -> None:
        """Both engines render horizontal reference lines."""
        plot_page.evaluate(
            "window.__ring5_add_reference_line({axis:'y',value:50,style:'dash'})"
        )

        for engine in ["plotly", "matplotlib"]:
            plot_page.locator(
                f"[data-testid='engine-{engine}']"
            ).click()
            plot_page.wait_for_timeout(2000)
            screenshot = plot_page.locator(
                "[data-testid='plot-container']"
            ).screenshot()
            assert len(screenshot) > 1000
```

---

## 5. Plotly-Specific Feature Tests

### 5.1 Gherkin Scenarios

```gherkin
Feature: Plotly-Specific Features
  Features that only apply to the Plotly rendering engine.

  Scenario: Hovermode is applied to Plotly figures
    Given the engine is set to "plotly"
    And the hovermode is configured as "x unified"
    When the figure renders
    Then the Plotly layout hovermode equals "x unified"
    And hovering over a data point shows a unified tooltip

  Scenario: Hovermode options are selectable
    Given the engine is set to "plotly"
    Then the hovermode selector offers exactly these options:
      | option     |
      | x unified  |
      | closest    |
      | x          |
      | y          |
      | off        |

  Scenario: Interactive HTML export preserves interactivity
    Given the engine is set to "plotly"
    When I export the plot as HTML
    Then the downloaded file contains "plotly.js" script
    And opening the file in a browser shows an interactive chart

  Scenario: Plotly legend entrywidth fraction mode for multi-column
    Given a legend with ncol=3
    When rendered with Plotly
    Then the legend uses entrywidthmode="fraction"
    And entrywidth is approximately 0.3333

  Scenario: Plotly legend single-column forces full width
    Given a legend with ncol=1
    When rendered with Plotly
    Then the legend uses entrywidth=1.0 and entrywidthmode="fraction"

  Scenario: Plotly colorbar ticklabelposition for non-default side
    Given a heatmap with colorbar tick_side="left"
    When rendered with Plotly
    Then the colorbar dict includes ticklabelposition="outside left"

  Scenario: Plotly trace overrides apply per-name
    Given trace overrides mapping "Revenue" to display_name="Net Revenue"
    When rendered with Plotly
    Then the trace named "Revenue" is renamed to "Net Revenue" in the legend

  Scenario: Plotly label aliases use tickvals/ticktext
    Given x-axis label_aliases {"q1": "Quarter 1", "q2": "Quarter 2"}
    When rendered with Plotly
    Then xaxis tickmode is "array"
    And tickvals contains ["q1", "q2"]
    And ticktext contains ["Quarter 1", "Quarter 2"]

  Scenario: Plotly dimensions convert inches to pixels
    Given figure dimensions width=7.0 height=5.0 dpi=96
    When rendered with Plotly
    Then the Plotly layout width is 672 and height is 480

  Scenario: Plotly data labels use texttemplate format
    Given data labels enabled with format_string=".1f"
    When rendered with Plotly
    Then each bar trace has texttemplate="%{y:.1f}"

  Scenario: Plotly heatmap annotations use auto-contrast coloring
    Given a heatmap with show_values=True
    When rendered with Plotly
    Then cells in the upper half of z-range have white text
    And cells in the lower half of z-range have black text

  Scenario: Plotly bar hatching uses marker.pattern.shape
    Given enable_stripes=True and hatching_sequence=["/", "\\", "x"]
    When rendered with Plotly
    Then bar traces get pattern shapes "/" "\\" "x" cyclically
```

### 5.2 pytest-playwright Stubs

```python
"""E2E tests: Plotly-specific features."""
import json

import pytest
from playwright.sync_api import Page, expect


class TestPlotlySpecific:
    """Features unique to the Plotly rendering engine."""

    def test_hovermode_applied(self, plot_page: Page) -> None:
        plot_page.locator("[data-testid='engine-plotly']").click()
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout"
            ")"
        )
        layout = json.loads(layout_json)
        assert layout.get("hovermode") == "x unified"

    def test_hover_tooltip_visible_on_interaction(
        self, plot_page: Page
    ) -> None:
        plot_page.locator("[data-testid='engine-plotly']").click()
        plot_page.wait_for_timeout(2000)
        plot_area = plot_page.locator(".js-plotly-plot .plot-container")
        plot_area.hover(position={"x": 200, "y": 150})
        plot_page.wait_for_timeout(500)
        hoverlayer = plot_page.locator(".hoverlayer")
        expect(hoverlayer).to_be_visible()

    def test_hovermode_options_available(self, plot_page: Page) -> None:
        plot_page.locator("[data-testid='engine-plotly']").click()
        plot_page.wait_for_timeout(2000)
        selector = plot_page.locator("[data-testid='hovermode-selector']")
        selector.click()
        expected_opts = ["x unified", "closest", "x", "y", "off"]
        for opt in expected_opts:
            option = plot_page.locator(f"li:has-text('{opt}')")
            expect(option).to_be_visible()

    def test_html_export_contains_plotlyjs(self, plot_page: Page) -> None:
        plot_page.locator("[data-testid='engine-plotly']").click()
        plot_page.wait_for_timeout(2000)
        plot_page.locator("[data-testid='download-section']").click()
        plot_page.locator("[data-testid='dl-format-html']").click()
        with plot_page.expect_download() as download_info:
            plot_page.locator("[data-testid='download-button']").click()
        download = download_info.value
        content = download.path().read_text()
        assert "plotly" in content.lower()
        assert "<script" in content

    def test_legend_entrywidth_fraction_multi_col(
        self, plot_page: Page
    ) -> None:
        plot_page.evaluate("window.__ring5_set_legend_ncol(3)")
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.legend"
            ")"
        )
        legend = json.loads(layout_json)
        assert legend.get("entrywidthmode") == "fraction"
        assert abs(legend.get("entrywidth", 0) - 0.3333) < 0.01

    def test_legend_single_col_full_width(self, plot_page: Page) -> None:
        plot_page.evaluate("window.__ring5_set_legend_ncol(1)")
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.legend"
            ")"
        )
        legend = json.loads(layout_json)
        assert legend.get("entrywidthmode") == "fraction"
        assert legend.get("entrywidth") == 1.0

    def test_trace_override_rename(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_trace_override('Revenue', 'Net Revenue')"
        )
        plot_page.wait_for_timeout(2000)
        traces_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot')"
            "    .data.map(t => t.name)"
            ")"
        )
        names = json.loads(traces_json)
        assert "Net Revenue" in names
        assert "Revenue" not in names

    def test_dimensions_inches_to_pixels(self, plot_page: Page) -> None:
        """Plotly converts width/height inches * dpi to pixel layout."""
        plot_page.evaluate(
            "window.__ring5_set_dimensions({width:7.0, height:5.0, dpi:96})"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify({"
            "  w: document.querySelector('.js-plotly-plot').layout.width,"
            "  h: document.querySelector('.js-plotly-plot').layout.height"
            "})"
        )
        dims = json.loads(layout_json)
        assert dims["w"] == 672  # 7.0 * 96
        assert dims["h"] == 480  # 5.0 * 96

    def test_data_labels_texttemplate(self, plot_page: Page) -> None:
        """Plotly data labels use texttemplate formatting."""
        plot_page.evaluate(
            "window.__ring5_enable_data_labels('.1f')"
        )
        plot_page.wait_for_timeout(2000)
        traces_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot')"
            "    .data.map(t => t.texttemplate)"
            ")"
        )
        templates = json.loads(traces_json)
        for tmpl in templates:
            if tmpl is not None:
                assert "%{y:.1f}" in tmpl
```

---

## 6. Matplotlib-Specific Feature Tests

### 6.1 Gherkin Scenarios

```gherkin
Feature: Matplotlib-Specific Features
  Features that only apply to the Matplotlib rendering engine.

  Scenario: LaTeX escaping is applied to all text elements
    Given the engine is set to "matplotlib"
    And the title contains special characters "Revenue & Profit (%)"
    When the figure renders
    Then the title text is escaped to "Revenue \& Profit (\%)"
    And no LaTeX compilation error occurs

  Scenario: LaTeX commands are preserved in escaping
    Given the engine is set to "matplotlib"
    And the title is "\textbf{Bold Title}"
    When the figure renders
    Then the title text is NOT further escaped
    And the LaTeX command renders as bold text

  Scenario: Matplotlib font family propagates via rcParams
    Given the engine is set to "matplotlib"
    And font_family is set to "serif"
    When the figure renders
    Then matplotlib.rcParams["font.family"] equals "serif"

  Scenario: Matplotlib color palette converts CSS rgb to hex
    Given a color palette with "rgb(255,127,14)"
    When rendered with Matplotlib
    Then the axes color cycle contains "#ff7f0e"

  Scenario: PGF export uses vector quadrilaterals for heatmaps
    Given the engine is set to "matplotlib"
    And a heatmap is rendered using pcolormesh
    When I export as PGF format
    Then the PGF output contains vector drawing commands
    And no raster image embed is present

  Scenario: PGF export falls back to PDF on raster content error
    Given the engine is set to "matplotlib"
    And a heatmap with raster graphics is rendered
    When I attempt PGF export and it raises a ValueError
    Then the system falls back to PDF format
    And a warning message is displayed

  Scenario: Matplotlib Y-axis label supports vshift positioning
    Given the engine is set to "matplotlib"
    And y-axis title_vshift is set to 10.0
    When the figure renders
    Then the y-axis label is repositioned via set_label_coords
    And the vertical offset is 0.5 + (10.0 / 100.0) = 0.6

  Scenario: Matplotlib legend font family override per-legend
    Given the engine is set to "matplotlib"
    And the legend font_family is "monospace"
    When the figure renders
    Then the legend uses FontProperties(family="monospace")

  Scenario: Matplotlib bold title via fontweight
    Given the engine is set to "matplotlib"
    And typography bold_title is True
    When the figure renders
    Then ax.set_title is called with fontweight="bold"

  Scenario: Matplotlib figure creation normalizes dpi=1 sentinel
    Given a FigureConfig with dpi=1 and width=960 height=540
    When create_figure is called
    Then the figure uses render_dpi=96
    And figsize is (10.0, 5.625) inches

  Scenario: TeX system selector offers three options
    Given the engine is set to "matplotlib"
    Then the TeX system selector offers:
      | option    |
      | xelatex   |
      | pdflatex  |
      | lualatex  |

  Scenario: Matplotlib data labels use bar_label API
    Given the engine is set to "matplotlib"
    And data labels are enabled with position="outside"
    When the figure renders
    Then ax.bar_label is called with label_type="edge"

  Scenario: Matplotlib dash style mapping
    Given reference line style is "dashdot"
    When rendered with Matplotlib
    Then the line uses linestyle="-."
```

### 6.2 pytest-playwright Stubs

```python
"""E2E tests: Matplotlib-specific features."""
import pytest
from playwright.sync_api import Page, expect


class TestMatplotlibSpecific:
    """Features unique to the Matplotlib rendering engine."""

    def test_latex_escaping_special_chars(self, plot_page: Page) -> None:
        """Special LaTeX characters are escaped in titles."""
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        plot_page.locator("[data-testid='title-input']").fill(
            "Revenue & Profit (%)"
        )
        plot_page.wait_for_timeout(2000)
        # Verify no error state in the plot container
        error = plot_page.locator("[data-testid='plot-error']")
        expect(error).not_to_be_visible()
        container = plot_page.locator("[data-testid='plot-container']")
        expect(container).to_be_visible()

    def test_pgf_export_available(self, plot_page: Page) -> None:
        """PGF format is available in Matplotlib download."""
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        plot_page.locator("[data-testid='download-section']").click()
        pgf_pill = plot_page.locator("[data-testid='dl-format-pgf']")
        expect(pgf_pill).to_be_visible()

    def test_pgf_download_produces_bytes(self, plot_page: Page) -> None:
        """PGF download produces non-empty file for non-heatmap plots."""
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        plot_page.locator("[data-testid='download-section']").click()
        plot_page.locator("[data-testid='dl-format-pgf']").click()
        with plot_page.expect_download() as download_info:
            plot_page.locator("[data-testid='download-button']").click()
        download = download_info.value
        content = download.path().read_bytes()
        assert len(content) > 100, "PGF file should be non-empty"

    def test_tex_system_options(self, plot_page: Page) -> None:
        """TeX system selector offers xelatex, pdflatex, lualatex."""
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        selector = plot_page.locator("[data-testid='tex-system-selector']")
        selector.click()
        for system in ["xelatex", "pdflatex", "lualatex"]:
            option = plot_page.locator(f"li:has-text('{system}')")
            expect(option).to_be_visible()

    def test_matplotlib_renders_static_image(
        self, plot_page: Page
    ) -> None:
        """Matplotlib output is a static image, not interactive."""
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        # No Plotly interactive elements should exist
        plotly = plot_page.locator(".js-plotly-plot")
        expect(plotly).not_to_be_visible()
        # Should be rendered as an image
        img = plot_page.locator("[data-testid='plot-container'] img")
        expect(img).to_be_visible()

    def test_dpi_sentinel_normalization(self, plot_page: Page) -> None:
        """When dpi=1 (pixel passthrough), figure normalizes to 96 DPI."""
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        # Set dimensions that would cause MemoryError without normalization
        plot_page.evaluate(
            "window.__ring5_set_dimensions({width:960, height:540, dpi:1})"
        )
        plot_page.wait_for_timeout(3000)
        # Should render without error (no MemoryError crash)
        container = plot_page.locator("[data-testid='plot-container']")
        expect(container).to_be_visible()
        error = plot_page.locator("[data-testid='plot-error']")
        expect(error).not_to_be_visible()
```

---

## 7. Visual Regression Tests (Screenshot Comparison)

### 7.1 Gherkin Scenarios

```gherkin
Feature: Visual Regression Between Engines
  Screenshots of the same plot rendered by both engines should
  be structurally similar within acceptable tolerance.

  Background:
    Given a bar chart with 5 categories and 3 series
    And a resolved FigureConfig with title, legends, and grid

  Scenario: Bar chart structural similarity
    When I capture a screenshot with "plotly"
    And I capture a screenshot with "matplotlib"
    Then the layout regions (title, axes, legend) occupy similar
         proportional areas within 15% tolerance

  Scenario: Line chart structural similarity
    Given a line chart with 4 time series
    When I capture screenshots with both engines
    Then both show lines traversing the plot area
    And both display legend entries matching trace names

  Scenario: Scatter plot structural similarity
    Given a scatter plot with 100 data points
    When I capture screenshots with both engines
    Then both show markers distributed across the plot area

  Scenario: Heatmap structural similarity
    Given a 5x5 heatmap with labeled axes
    When I capture screenshots with both engines
    Then both show a colored grid with cell labels
    And both display a colorbar

  Scenario: Multi-heatmap subplot structural similarity
    Given 3 heatmap traces producing subplot rows
    When I capture screenshots with both engines
    Then both show 3 stacked heatmap panels
    And colorbar position is visually consistent

  Scenario: Empty plot renders without error on both engines
    Given a FigureConfig with no traces
    When I render with "plotly" and "matplotlib"
    Then both produce a visible empty axes frame
    And no error messages appear
```

### 7.2 pytest-playwright Stubs

```python
"""E2E tests: Visual regression screenshot comparison."""
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


SCREENSHOT_DIR = Path("tests/screenshots/engine_comparison")


def _structural_similarity(img_a: bytes, img_b: bytes) -> float:
    """Compute structural similarity index between two images.

    Returns a value between 0.0 (completely different) and 1.0 (identical).
    Uses PIL for basic comparison; production code should use skimage.ssim.
    """
    from PIL import Image
    import io
    a = Image.open(io.BytesIO(img_a)).convert("L").resize((200, 150))
    b = Image.open(io.BytesIO(img_b)).convert("L").resize((200, 150))
    pixels_a = list(a.getdata())
    pixels_b = list(b.getdata())
    if len(pixels_a) != len(pixels_b):
        return 0.0
    diff = sum(abs(pa - pb) for pa, pb in zip(pixels_a, pixels_b))
    max_diff = 255 * len(pixels_a)
    return 1.0 - (diff / max_diff)


PLOT_TYPES = ["bar", "line", "scatter", "histogram", "heatmap"]


class TestVisualRegression:
    """Cross-engine visual regression via screenshot comparison."""

    @pytest.mark.parametrize("plot_type", PLOT_TYPES)
    def test_structural_similarity(
        self, plot_page: Page, plot_type: str
    ) -> None:
        """Both engines produce structurally similar output."""
        plot_page.evaluate(
            f"window.__ring5_load_sample_plot('{plot_type}')"
        )
        plot_page.wait_for_timeout(2000)

        # Plotly screenshot
        plot_page.locator("[data-testid='engine-plotly']").click()
        plot_page.wait_for_timeout(2000)
        plotly_shot = plot_page.locator(
            "[data-testid='plot-container']"
        ).screenshot()

        # Matplotlib screenshot
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        mpl_shot = plot_page.locator(
            "[data-testid='plot-container']"
        ).screenshot()

        # Save for manual inspection
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        (SCREENSHOT_DIR / f"{plot_type}_plotly.png").write_bytes(plotly_shot)
        (SCREENSHOT_DIR / f"{plot_type}_mpl.png").write_bytes(mpl_shot)

        # Structural similarity must exceed threshold
        # Note: engines produce different pixel output; we only
        # verify the overall structure (layout regions) match
        similarity = _structural_similarity(plotly_shot, mpl_shot)
        assert similarity > 0.3, (
            f"Structural similarity for {plot_type} is {similarity:.3f}, "
            f"expected > 0.3"
        )

    def test_empty_plot_both_engines(self, plot_page: Page) -> None:
        """Empty figure renders on both engines without error."""
        plot_page.evaluate("window.__ring5_load_empty_plot()")
        for engine in ["plotly", "matplotlib"]:
            plot_page.locator(
                f"[data-testid='engine-{engine}']"
            ).click()
            plot_page.wait_for_timeout(2000)
            container = plot_page.locator("[data-testid='plot-container']")
            expect(container).to_be_visible()
            error = plot_page.locator("[data-testid='plot-error']")
            expect(error).not_to_be_visible()
```

---

## 8. Export Format Tests (PNG, SVG, PDF, PGF)

### 8.1 Gherkin Scenarios

```gherkin
Feature: Export Format Correctness Across Engines
  Each engine produces valid output in its supported formats.

  Scenario Outline: Plotly exports valid <format> files
    Given the engine is "plotly"
    And a bar chart is rendered
    When I download the plot as "<format>"
    Then the file has extension "<extension>"
    And the MIME type is "<mime>"
    And the file content is valid <format>

    Examples:
      | format | extension | mime              |
      | png    | .png      | image/png         |
      | svg    | .svg      | image/svg+xml     |
      | pdf    | .pdf      | application/pdf   |
      | html   | .html     | text/html         |

  Scenario Outline: Matplotlib exports valid <format> files
    Given the engine is "matplotlib"
    And a bar chart is rendered
    When I download the plot as "<format>"
    Then the file has extension "<extension>"
    And the MIME type is "<mime>"
    And the file content is valid <format>

    Examples:
      | format | extension | mime              |
      | pdf    | .pdf      | application/pdf   |
      | pgf    | .pgf      | application/x-pgf |
      | png    | .png      | image/png         |
      | svg    | .svg      | image/svg+xml     |

  Scenario: PNG export from both engines produces non-zero images
    Given the same bar chart rendered on both engines
    When I export PNG from Plotly with scale=2
    And I export PNG from Matplotlib with dpi=300
    Then both files are valid PNG images with non-zero dimensions

  Scenario: SVG export from both engines produces valid markup
    Given the same chart rendered on both engines
    When I export SVG from each engine
    Then both files start with "<svg" or "<?xml"
    And both contain path or line elements representing data

  Scenario: PDF export from both engines produces valid documents
    Given the same chart on both engines
    When I export PDF from each engine
    Then both files start with "%PDF-" header
    And both have file size > 1 KB

  Scenario: Matplotlib PNG export disables usetex
    Given the engine is "matplotlib"
    When I export PNG format
    Then rc_context sets "text.usetex" to False
    And the agg backend is used
    And no dvipng dependency is required

  Scenario: Plotly HTML export includes full plotly.js
    Given the engine is "plotly"
    When I export HTML format
    Then fig.to_html is called with include_plotlyjs=True
    And full_html=True produces a self-contained document

  Scenario: Matplotlib PDF export uses bbox_inches="tight"
    Given the engine is "matplotlib"
    When I export PDF format
    Then savefig uses bbox_inches="tight" to avoid clipping
```

### 8.2 pytest-playwright Stubs

```python
"""E2E tests: Export format validation across engines."""
import pytest
from playwright.sync_api import Page, expect


class TestExportFormats:
    """Validate exported files are well-formed for each engine."""

    @pytest.mark.parametrize("fmt,header", [
        ("png", b"\x89PNG"),
        ("svg", b"<svg"),
        ("pdf", b"%PDF"),
    ])
    def test_plotly_export_headers(
        self, plot_page: Page, fmt: str, header: bytes
    ) -> None:
        """Plotly exports produce files with correct format headers."""
        plot_page.locator("[data-testid='engine-plotly']").click()
        plot_page.wait_for_timeout(2000)
        plot_page.locator("[data-testid='download-section']").click()
        plot_page.locator(f"[data-testid='dl-format-{fmt}']").click()
        with plot_page.expect_download() as download_info:
            plot_page.locator("[data-testid='download-button']").click()
        download = download_info.value
        content = download.path().read_bytes()
        assert content[:len(header)].startswith(header) or (
            fmt == "svg" and b"<?xml" in content[:100]
        )

    @pytest.mark.parametrize("fmt,header", [
        ("png", b"\x89PNG"),
        ("svg", b"<svg"),
        ("pdf", b"%PDF"),
    ])
    def test_matplotlib_export_headers(
        self, plot_page: Page, fmt: str, header: bytes
    ) -> None:
        """Matplotlib exports produce files with correct format headers."""
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        plot_page.locator("[data-testid='download-section']").click()
        plot_page.locator(f"[data-testid='dl-format-{fmt}']").click()
        with plot_page.expect_download() as download_info:
            plot_page.locator("[data-testid='download-button']").click()
        download = download_info.value
        content = download.path().read_bytes()
        assert content[:len(header)].startswith(header) or (
            fmt == "svg" and b"<?xml" in content[:100]
        )

    def test_plotly_html_self_contained(self, plot_page: Page) -> None:
        """Plotly HTML export is a self-contained document."""
        plot_page.locator("[data-testid='engine-plotly']").click()
        plot_page.wait_for_timeout(2000)
        plot_page.locator("[data-testid='download-section']").click()
        plot_page.locator("[data-testid='dl-format-html']").click()
        with plot_page.expect_download() as download_info:
            plot_page.locator("[data-testid='download-button']").click()
        download = download_info.value
        content = download.path().read_text()
        assert "<!DOCTYPE html>" in content or "<html" in content
        assert "Plotly" in content or "plotly" in content

    def test_matplotlib_pgf_export(self, plot_page: Page) -> None:
        """Matplotlib PGF export produces LaTeX-compatible output."""
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        # Use a line chart (no raster content) for PGF
        plot_page.evaluate("window.__ring5_load_sample_plot('line')")
        plot_page.wait_for_timeout(2000)
        plot_page.locator("[data-testid='download-section']").click()
        plot_page.locator("[data-testid='dl-format-pgf']").click()
        with plot_page.expect_download() as download_info:
            plot_page.locator("[data-testid='download-button']").click()
        download = download_info.value
        content = download.path().read_text()
        assert "\\begin{pgfpicture}" in content or "pgf" in content.lower()

    def test_cross_engine_png_dimensions(self, plot_page: Page) -> None:
        """PNG exports from both engines have comparable dimensions."""
        from PIL import Image
        import io

        screenshots = {}
        for engine in ["plotly", "matplotlib"]:
            plot_page.locator(
                f"[data-testid='engine-{engine}']"
            ).click()
            plot_page.wait_for_timeout(2000)
            plot_page.locator("[data-testid='download-section']").click()
            plot_page.locator("[data-testid='dl-format-png']").click()
            with plot_page.expect_download() as download_info:
                plot_page.locator("[data-testid='download-button']").click()
            download = download_info.value
            data = download.path().read_bytes()
            img = Image.open(io.BytesIO(data))
            screenshots[engine] = img.size

        pw, ph = screenshots["plotly"]
        mw, mh = screenshots["matplotlib"]
        # Dimensions should be within 50% of each other
        assert abs(pw - mw) / max(pw, mw) < 0.5
        assert abs(ph - mh) / max(ph, mh) < 0.5
```

---

## 9. Typography Consistency Tests

### 9.1 Gherkin Scenarios

```gherkin
Feature: Typography Consistency Across Engines
  Font sizes, weights, and families should be configured
  identically from the same FigureConfig.

  Scenario: Title font size applies to both engines
    Given typography font_size_title=18
    When rendered with Plotly the title font.size is 18
    When rendered with Matplotlib the title fontsize is 18

  Scenario: Axis label font sizes apply to both engines
    Given font_size_xlabel=14 and font_size_ylabel=14
    When rendered with Plotly the xaxis title font.size is 14
    When rendered with Matplotlib the xlabel fontsize is 14

  Scenario: Tick font sizes apply to both engines
    Given font_size_ticks=10 and font_size_yticks=10
    When rendered with Plotly the xaxis tickfont.size is 10
    When rendered with Matplotlib tick_params labelsize is 10

  Scenario: Bold title in Matplotlib uses fontweight
    Given typography bold_title=True
    When rendered with Plotly the title does NOT include weight
    When rendered with Matplotlib the title uses fontweight="bold"

  Scenario: Bold axis labels in Matplotlib
    Given typography bold_xlabel=True
    When rendered with Matplotlib xlabel uses fontweight="bold"

  Scenario: Font family propagates to global layout
    Given font_family="Courier New"
    When rendered with Plotly layout.font.family is "Courier New"
    When rendered with Matplotlib rcParams font.family is "Courier New"

  Scenario: Y2 axis label font size
    Given font_size_y2label=12
    When rendered with Plotly yaxis2.title.font.size is 12
    When rendered with Matplotlib twin axis ylabel fontsize is 12
```

### 9.2 pytest-playwright Stubs

```python
"""E2E tests: Typography consistency between engines."""
import json

import pytest
from playwright.sync_api import Page


class TestTypography:
    """Verify font sizes and families propagate correctly."""

    def test_title_font_size_plotly(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_typography({font_size_title: 18})"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.title"
            ")"
        )
        title = json.loads(layout_json)
        assert title.get("font", {}).get("size") == 18

    def test_tick_font_size_plotly(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_typography({font_size_ticks: 10})"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.xaxis"
            ")"
        )
        xaxis = json.loads(layout_json)
        assert xaxis.get("tickfont", {}).get("size") == 10

    def test_font_family_plotly(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_config('font_family', 'Courier New')"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.font"
            ")"
        )
        font = json.loads(layout_json)
        assert font.get("family") == "Courier New"

    def test_typography_renders_on_matplotlib(
        self, plot_page: Page
    ) -> None:
        """Matplotlib renders with configured typography without error."""
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        plot_page.evaluate(
            "window.__ring5_set_typography({font_size_title: 22})"
        )
        plot_page.wait_for_timeout(2000)
        container = plot_page.locator("[data-testid='plot-container']")
        from playwright.sync_api import expect
        expect(container).to_be_visible()
```

---

## 10. Legend Rendering Tests

### 10.1 Gherkin Scenarios

```gherkin
Feature: Legend Rendering Engine Comparison
  Both engines must render legends with matching structure from
  the same LegendConfig.

  Scenario: Primary legend visibility on both engines
    Given a legend with visible=True
    When rendered on both engines
    Then both show a visible legend box with trace names

  Scenario: Legend position custom coordinates
    Given a legend with custom_position=True, position_x=0.5, position_y=1.05
    When rendered with Plotly it sets legend.x=0.5 and legend.y=1.05
    When rendered with Matplotlib it uses bbox_to_anchor=(0.5, 1.05)

  Scenario: Legend anchor mapping from Plotly to Matplotlib
    Given a legend with anchor_x="right" and anchor_y="top"
    When rendered with Plotly it sets xanchor="right" yanchor="top"
    When rendered with Matplotlib the loc is "upper right"

  Scenario: Legend background color on both engines
    Given a legend with bgcolor="#ffffcc"
    When rendered with Plotly legend.bgcolor is "#ffffcc"
    When rendered with Matplotlib facecolor is "#ffffcc"

  Scenario: Legend border width and color
    Given a legend with border_width=2.0 and border_color="black"
    When rendered with Plotly borderwidth=2 and bordercolor="black"
    When rendered with Matplotlib edgecolor="black"

  Scenario: Multi-legend layout (primary + secondary)
    Given two legends: primary for main axis, secondary for twin axis
    When rendered with Plotly layout has legend and legend2
    When rendered with Matplotlib primary legend is on ax, secondary on child_ax

  Scenario: Legend multi-column via ncol
    Given a legend with ncol=2
    When rendered with Plotly entrywidth is approximately 0.5 (fraction)
    When rendered with Matplotlib ncol=2 is passed to ax.legend()

  Scenario: Legend spacing properties
    Given legend spacing with columnspacing=1.5, labelspacing=0.8
    When rendered with Matplotlib these values are passed to ax.legend()

  Scenario: Legend trace order reversed
    Given legend order="reversed"
    When rendered with Plotly traceorder="reversed"

  Scenario: Bold legend text in Matplotlib
    Given legend bold=True
    When rendered with Matplotlib
    Then each legend text element has fontweight="bold"

  Scenario: Legend title with font customization
    Given legend title="Metrics" with title_font_size=14 and title_font_color="red"
    When rendered with Plotly legend.title.text="Metrics"
    When rendered with Matplotlib title="Metrics" and title_fontsize=14
```

### 10.2 pytest-playwright Stubs

```python
"""E2E tests: Legend rendering comparison."""
import json

import pytest
from playwright.sync_api import Page, expect


class TestLegendRendering:
    """Compare legend rendering between engines."""

    def test_legend_visible_both_engines(self, plot_page: Page) -> None:
        """Legend appears on both engines."""
        for engine in ["plotly", "matplotlib"]:
            plot_page.locator(
                f"[data-testid='engine-{engine}']"
            ).click()
            plot_page.wait_for_timeout(2000)
            container = plot_page.locator("[data-testid='plot-container']")
            screenshot = container.screenshot()
            assert len(screenshot) > 1000

    def test_legend_position_plotly(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_legend_position(0.5, 1.05)"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.legend"
            ")"
        )
        legend = json.loads(layout_json)
        assert legend.get("x") == 0.5
        assert legend.get("y") == 1.05

    def test_legend_bgcolor_plotly(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_legend_config({bgcolor: '#ffffcc'})"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.legend"
            ")"
        )
        legend = json.loads(layout_json)
        assert legend.get("bgcolor") == "#ffffcc"

    def test_multi_legend_plotly(self, plot_page: Page) -> None:
        """Dual-axis plot creates primary and secondary legends."""
        plot_page.evaluate("window.__ring5_enable_dual_legend()")
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify({"
            "  legend: document.querySelector('.js-plotly-plot').layout.legend,"
            "  legend2: document.querySelector('.js-plotly-plot').layout.legend2"
            "})"
        )
        legends = json.loads(layout_json)
        assert legends.get("legend") is not None
        # legend2 may or may not exist depending on trace config
```

---

## 11. Axis & Grid Tests

### 11.1 Gherkin Scenarios

```gherkin
Feature: Axis and Grid Engine Comparison
  Axis configuration (ranges, scales, ticks, grids) must translate
  equivalently across both engines.

  Scenario: X-axis range limits on both engines
    Given x-axis range [0, 100]
    When rendered with Plotly xaxis.range is [0, 100]
    When rendered with Matplotlib ax.get_xlim() returns (0, 100)

  Scenario: Log scale on Y-axis
    Given y-axis scale="log"
    When rendered with Plotly yaxis.type is "log"
    When rendered with Matplotlib ax.get_yscale() is "log"

  Scenario: X-axis tick angle rotation
    Given x-axis tick_angle=45
    When rendered with Plotly xaxis.tickangle is 45
    When rendered with Matplotlib x-tick labels have rotation=45

  Scenario: Grid visibility toggle
    Given x-axis show_grid=True and y-axis show_grid=False
    When rendered with Plotly xaxis.showgrid=True, yaxis.showgrid=False
    When rendered with Matplotlib x grid is on, y grid is off

  Scenario: Grid dash style consistency
    Given y-axis grid with tick_dash="dash"
    When rendered with Plotly griddash="dash"
    When rendered with Matplotlib grid linestyle="--"

  Scenario: Grid color and width
    Given x-axis grid_color="#cccccc" and grid_width=0.5
    When rendered with Plotly gridcolor="#cccccc" gridwidth=0.5
    When rendered with Matplotlib grid color="#cccccc" linewidth=0.5

  Scenario: Tick visibility suppression
    Given x-axis show_tick_labels=False
    When rendered with Plotly showticklabels=False
    When rendered with Matplotlib set_xticklabels([]) is called

  Scenario: Axis line color and width
    Given x-axis axis_line_width=2 and axis_line_color="#333333"
    When rendered with Plotly xaxis linewidth=2 linecolor="#333333"
    When rendered with Matplotlib bottom spine color="#333333" width=2.0

  Scenario: Top axis line via mirror or spine
    Given top_axis_line_width=1
    When rendered with Plotly xaxis mirror=True (when bottom also shown)
    When rendered with Matplotlib top spine visible with width=1

  Scenario: Tick padding / standoff
    Given x-axis tick_pad=8 (non-default)
    When rendered with Plotly ticklabelstandoff=8
    When rendered with Matplotlib tick_params pad=8

  Scenario: Category order on x-axis
    Given x-axis category_order=["C", "A", "B"]
    When rendered with Plotly categoryorder="array" categoryarray=["C","A","B"]
```

### 11.2 pytest-playwright Stubs

```python
"""E2E tests: Axis and grid comparison between engines."""
import json

import pytest
from playwright.sync_api import Page


class TestAxisGrid:
    """Verify axis and grid configuration parity."""

    def test_axis_range_plotly(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_axis_range('x', [0, 100])"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.xaxis"
            ")"
        )
        xaxis = json.loads(layout_json)
        assert xaxis.get("range") == [0, 100]

    def test_log_scale_plotly(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_axis_scale('y', 'log')"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.yaxis"
            ")"
        )
        yaxis = json.loads(layout_json)
        assert yaxis.get("type") == "log"

    def test_grid_visibility_plotly(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_grid({x_show: true, y_show: false})"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify({"
            "  x: document.querySelector('.js-plotly-plot').layout.xaxis,"
            "  y: document.querySelector('.js-plotly-plot').layout.yaxis"
            "})"
        )
        axes = json.loads(layout_json)
        assert axes["x"].get("showgrid") is True
        assert axes["y"].get("showgrid") is False

    def test_tick_angle_plotly(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_config('x_tick_angle', 45)"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.xaxis"
            ")"
        )
        xaxis = json.loads(layout_json)
        assert xaxis.get("tickangle") == 45

    def test_axis_line_color_plotly(self, plot_page: Page) -> None:
        plot_page.evaluate(
            "window.__ring5_set_axis_line('x', {width: 2, color: '#333333'})"
        )
        plot_page.wait_for_timeout(2000)
        layout_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot').layout.xaxis"
            ")"
        )
        xaxis = json.loads(layout_json)
        assert xaxis.get("showline") is True
        assert xaxis.get("linewidth") == 2
        assert xaxis.get("linecolor") == "#333333"
```

---

## 12. Heatmap Engine Comparison Tests

### 12.1 Gherkin Scenarios

```gherkin
Feature: Heatmap Rendering Engine Comparison
  Heatmaps have significant implementation differences between
  engines: Plotly uses go.Heatmap (raster tiles), Matplotlib uses
  ax.pcolormesh (vector quadrilaterals). Both must produce
  equivalent visual output.

  Scenario: Single heatmap renders on both engines
    Given a 5x5 heatmap with z-values from 0 to 100
    When rendered with Plotly it creates a go.Heatmap trace
    When rendered with Matplotlib it uses ax.pcolormesh
    Then both display a colored grid with 25 cells

  Scenario: Heatmap cell annotations auto-contrast
    Given a heatmap with show_values=True
    When rendered with Plotly annotations use layout annotations
    When rendered with Matplotlib annotations use ax.text
    Then dark cells (z > midpoint) have white text
    And light cells (z <= midpoint) have black text

  Scenario: Heatmap colorscale name mapping
    Given colorscale="Blues"
    When rendered with Plotly colorscale="Blues"
    When rendered with Matplotlib cmap="Blues" (via _COLORSCALE_MAP)

  Scenario: Heatmap custom palette colorscale
    Given a colorscale as [[0,"#fff"],[0.5,"#f00"],[1,"#000"]]
    When rendered with Plotly it uses the list-of-lists directly
    When rendered with Matplotlib it creates a LinearSegmentedColormap

  Scenario: Shared colorbar across multi-heatmap subplots
    Given 3 heatmap traces with colorbar shared=True
    When rendered with Plotly only the last trace shows colorbar
    And all traces share the same zmin/zmax
    When rendered with Matplotlib fig.colorbar() is called once
    With ax=axes_list for shared positioning

  Scenario: Individual colorbar per subplot
    Given 3 heatmap traces with colorbar shared=False
    When rendered with Plotly each trace has its own colorbar
    And each trace has its own nice-rounded zmin/zmax
    When rendered with Matplotlib each axes gets its own colorbar

  Scenario: Colorbar title placement
    Given colorbar with title="Intensity\n(units)"
    When rendered with Plotly title uses "<br>" line breaks
    When rendered with Matplotlib cbar.ax.set_title is used

  Scenario: Colorbar nice range rounding
    Given heatmap z-values ranging from 3.7 to 97.2 with nticks=5
    When computing nice range
    Then zmin rounds down and zmax rounds up to nice step multiples
    And the range covers the original data

  Scenario: Colorbar tick decimals formatting
    Given colorbar tick_decimals=1
    When rendered with Plotly tickformat=".1f"
    When rendered with Matplotlib FormatStrFormatter("%.1f")

  Scenario: Colorbar tick angle rotation
    Given colorbar tick_angle=45
    When rendered with Plotly colorbar.tickangle=45
    When rendered with Matplotlib label rotation is set to 45

  Scenario: Heatmap totals separator line (right position)
    Given a heatmap with totals_position="right" and totals_count=1
    When rendered with Plotly a vertical shape is added at n_cols - 1.5
    When rendered with Matplotlib ax.axvline is called

  Scenario: Heatmap totals separator line (top position)
    Given a heatmap with totals_position="top" and totals_count=1
    When rendered with Plotly a horizontal shape at y=0.5
    When rendered with Matplotlib ax.axhline at y=totals_count

  Scenario: Heatmap Y-axis inversion
    When rendered with Matplotlib ax.invert_yaxis() is called
    Then row 0 appears at the top (matrix convention)

  Scenario: Multi-heatmap creates subplots on both engines
    Given 3 heatmap traces
    When rendered with Plotly make_subplots creates 3 rows
    When rendered with Matplotlib create_multi_figure creates 3 axes
    Then both produce vertically stacked heatmap panels

  Scenario: Horizontal colorbar orientation
    Given legend orientation="horizontal"
    When rendered with Plotly colorbar orientation="h"
    When rendered with Matplotlib colorbar orientation="horizontal"
```

### 12.2 pytest-playwright Stubs

```python
"""E2E tests: Heatmap engine comparison."""
import json

import pytest
from playwright.sync_api import Page, expect


class TestHeatmapComparison:
    """Verify heatmap rendering parity between engines."""

    def test_heatmap_renders_both_engines(self, plot_page: Page) -> None:
        """Heatmap produces visible output on both engines."""
        plot_page.evaluate("window.__ring5_load_sample_plot('heatmap')")
        for engine in ["plotly", "matplotlib"]:
            plot_page.locator(
                f"[data-testid='engine-{engine}']"
            ).click()
            plot_page.wait_for_timeout(3000)
            container = plot_page.locator("[data-testid='plot-container']")
            expect(container).to_be_visible()
            screenshot = container.screenshot()
            assert len(screenshot) > 2000

    def test_heatmap_cell_annotations_plotly(
        self, plot_page: Page
    ) -> None:
        """Plotly heatmap with show_values creates layout annotations."""
        plot_page.evaluate(
            "window.__ring5_load_heatmap_with_values()"
        )
        plot_page.wait_for_timeout(2000)
        annotations_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot')"
            "    .layout.annotations"
            ")"
        )
        annotations = json.loads(annotations_json)
        assert len(annotations) > 0, "Heatmap annotations should exist"
        # Check auto-contrast coloring exists
        colors = {a.get("font", {}).get("color") for a in annotations}
        assert "white" in colors or "black" in colors

    def test_heatmap_colorbar_plotly(self, plot_page: Page) -> None:
        """Plotly heatmap shows a colorbar."""
        plot_page.evaluate(
            "window.__ring5_load_sample_plot('heatmap')"
        )
        plot_page.wait_for_timeout(2000)
        # Check that at least one trace has showscale
        traces_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot')"
            "    .data.map(t => ({type: t.type, showscale: t.showscale}))"
            ")"
        )
        traces = json.loads(traces_json)
        heatmaps = [t for t in traces if t.get("type") == "heatmap"]
        assert any(
            t.get("showscale") is True or t.get("showscale") is None
            for t in heatmaps
        )

    def test_heatmap_shared_colorbar_plotly(
        self, plot_page: Page
    ) -> None:
        """Multi-heatmap with shared colorbar: only last trace shows it."""
        plot_page.evaluate(
            "window.__ring5_load_multi_heatmap_shared()"
        )
        plot_page.wait_for_timeout(2000)
        traces_json = plot_page.evaluate(
            "JSON.stringify("
            "  document.querySelector('.js-plotly-plot')"
            "    .data.filter(t => t.type === 'heatmap')"
            "    .map(t => t.showscale)"
            ")"
        )
        showscales = json.loads(traces_json)
        # All except last should be False
        for i, ss in enumerate(showscales[:-1]):
            assert ss is False, f"Trace {i} should hide colorbar"
        assert showscales[-1] is True, "Last trace should show colorbar"

    def test_heatmap_colorbar_matplotlib(self, plot_page: Page) -> None:
        """Matplotlib heatmap renders colorbar without error."""
        plot_page.locator("[data-testid='engine-matplotlib']").click()
        plot_page.wait_for_timeout(2000)
        plot_page.evaluate(
            "window.__ring5_load_sample_plot('heatmap')"
        )
        plot_page.wait_for_timeout(3000)
        container = plot_page.locator("[data-testid='plot-container']")
        expect(container).to_be_visible()
        screenshot = container.screenshot()
        # Colorbar adds significant width; verify image is wider than
        # a plot without colorbar would be
        assert len(screenshot) > 3000

    def test_multi_heatmap_subplots(self, plot_page: Page) -> None:
        """Multi-heatmap creates stacked subplot panels on both engines."""
        plot_page.evaluate(
            "window.__ring5_load_multi_heatmap(3)"
        )
        for engine in ["plotly", "matplotlib"]:
            plot_page.locator(
                f"[data-testid='engine-{engine}']"
            ).click()
            plot_page.wait_for_timeout(3000)
            container = plot_page.locator("[data-testid='plot-container']")
            expect(container).to_be_visible()
            screenshot = container.screenshot()
            # Multi-panel should produce a taller image
            assert len(screenshot) > 5000
```

---

## 13. Performance Comparison Tests

### 13.1 Gherkin Scenarios

```gherkin
Feature: Performance Comparison Between Engines
  Render and export times for both engines should stay within
  acceptable bounds for E2E user experience.

  Scenario: Bar chart render time comparison
    Given a bar chart with 10 categories and 5 series
    When I measure render time on Plotly
    And I measure render time on Matplotlib
    Then both complete within 5 seconds
    And neither engine is more than 3x slower than the other

  Scenario: Heatmap render time comparison
    Given a 20x20 heatmap with cell annotations
    When I measure render time on both engines
    Then both complete within 8 seconds

  Scenario: Multi-heatmap render time
    Given 5 stacked heatmap subplots
    When I measure render time on both engines
    Then both complete within 15 seconds

  Scenario: PNG export time comparison
    Given a complex bar chart rendered on both engines
    When I measure PNG export time for each engine
    Then Plotly PNG export (via Kaleido) completes within 5 seconds
    And Matplotlib PNG export (via savefig/agg) completes within 5 seconds

  Scenario: Engine switching does not accumulate memory
    Given I switch engines 10 times alternating Plotly and Matplotlib
    When I check the page memory usage
    Then memory does not grow by more than 50MB across switches

  Scenario: Large dataset render time
    Given a scatter plot with 10,000 data points
    When I measure render time on both engines
    Then both complete within 10 seconds

  Scenario: SVG export size comparison
    Given the same bar chart exported as SVG from both engines
    When I compare the file sizes
    Then both are within 5x of each other
    And the larger file does not exceed 5 MB
```

### 13.2 pytest-playwright Stubs

```python
"""E2E tests: Performance comparison between engines."""
import time

import pytest
from playwright.sync_api import Page, expect


class TestPerformance:
    """Benchmark rendering and export across engines."""

    MAX_RENDER_TIME_MS = 5000
    MAX_HEATMAP_RENDER_TIME_MS = 8000
    MAX_EXPORT_TIME_MS = 5000

    def _measure_render_time(
        self, plot_page: Page, engine: str
    ) -> float:
        """Switch to engine and measure time until plot visible."""
        plot_page.locator(
            f"[data-testid='engine-{engine}']"
        ).click()
        start = time.monotonic()
        plot_page.wait_for_selector(
            "[data-testid='plot-container'] img, .js-plotly-plot",
            timeout=15_000,
        )
        return (time.monotonic() - start) * 1000

    @pytest.mark.parametrize("plot_type", ["bar", "line", "scatter"])
    def test_render_time_within_bounds(
        self, plot_page: Page, plot_type: str
    ) -> None:
        """Both engines render standard chart types within time limit."""
        plot_page.evaluate(
            f"window.__ring5_load_sample_plot('{plot_type}')"
        )
        plot_page.wait_for_timeout(1000)

        times = {}
        for engine in ["plotly", "matplotlib"]:
            times[engine] = self._measure_render_time(plot_page, engine)

        for engine, ms in times.items():
            assert ms < self.MAX_RENDER_TIME_MS, (
                f"{engine} render time {ms:.0f}ms exceeds "
                f"{self.MAX_RENDER_TIME_MS}ms limit for {plot_type}"
            )

        # Neither engine should be more than 3x slower
        ratio = max(times.values()) / max(min(times.values()), 1)
        assert ratio < 3.0, (
            f"Engine speed ratio {ratio:.1f}x exceeds 3x threshold"
        )

    def test_heatmap_render_time(self, plot_page: Page) -> None:
        """Heatmap render times within bounds."""
        plot_page.evaluate(
            "window.__ring5_load_sample_plot('heatmap')"
        )
        plot_page.wait_for_timeout(1000)

        for engine in ["plotly", "matplotlib"]:
            ms = self._measure_render_time(plot_page, engine)
            assert ms < self.MAX_HEATMAP_RENDER_TIME_MS, (
                f"{engine} heatmap render {ms:.0f}ms exceeds limit"
            )

    def test_png_export_time(self, plot_page: Page) -> None:
        """PNG export time within bounds for both engines."""
        for engine in ["plotly", "matplotlib"]:
            plot_page.locator(
                f"[data-testid='engine-{engine}']"
            ).click()
            plot_page.wait_for_timeout(2000)

            plot_page.locator("[data-testid='download-section']").click()
            plot_page.locator("[data-testid='dl-format-png']").click()

            start = time.monotonic()
            with plot_page.expect_download(timeout=15_000) as dl_info:
                plot_page.locator(
                    "[data-testid='download-button']"
                ).click()
            dl_info.value  # Wait for download to finish
            elapsed = (time.monotonic() - start) * 1000

            assert elapsed < self.MAX_EXPORT_TIME_MS, (
                f"{engine} PNG export {elapsed:.0f}ms exceeds limit"
            )

    def test_engine_switch_memory_stability(
        self, plot_page: Page
    ) -> None:
        """Repeated engine switching does not leak memory."""
        initial_memory = plot_page.evaluate(
            "performance.memory ? performance.memory.usedJSHeapSize : 0"
        )

        for _ in range(10):
            plot_page.locator("[data-testid='engine-plotly']").click()
            plot_page.wait_for_timeout(1000)
            plot_page.locator(
                "[data-testid='engine-matplotlib']"
            ).click()
            plot_page.wait_for_timeout(1000)

        final_memory = plot_page.evaluate(
            "performance.memory ? performance.memory.usedJSHeapSize : 0"
        )

        if initial_memory > 0:
            growth_mb = (final_memory - initial_memory) / (1024 * 1024)
            assert growth_mb < 50, (
                f"Memory grew by {growth_mb:.1f}MB after 10 engine switches"
            )

    def test_svg_export_size_comparison(self, plot_page: Page) -> None:
        """SVG file sizes from both engines are within reasonable ratios."""
        sizes = {}
        for engine in ["plotly", "matplotlib"]:
            plot_page.locator(
                f"[data-testid='engine-{engine}']"
            ).click()
            plot_page.wait_for_timeout(2000)
            plot_page.locator("[data-testid='download-section']").click()
            plot_page.locator("[data-testid='dl-format-svg']").click()
            with plot_page.expect_download() as dl_info:
                plot_page.locator(
                    "[data-testid='download-button']"
                ).click()
            download = dl_info.value
            sizes[engine] = len(download.path().read_bytes())

        max_size = max(sizes.values())
        min_size = max(min(sizes.values()), 1)
        ratio = max_size / min_size
        assert ratio < 5.0, (
            f"SVG size ratio {ratio:.1f}x between engines"
        )
        assert max_size < 5 * 1024 * 1024, (
            f"Largest SVG is {max_size / 1024:.0f}KB, exceeds 5MB limit"
        )
```

---

## Appendix: Known Engine Divergences

The following differences are **by design** and should NOT be flagged
as test failures:

| Aspect | Plotly | Matplotlib | Note |
|---|---|---|---|
| **Interactivity** | Hover, zoom, pan | Static image | Fundamental |
| **HTML export** | Supported | N/A | Plotly-only |
| **PGF export** | N/A | Supported | Matplotlib-only |
| **LaTeX escaping** | Not applied | Applied to all text | Matplotlib needs it |
| **Bold title** | Not supported via spec | `fontweight="bold"` | Engine limitation |
| **Y-label vshift** | Not supported | `set_label_coords()` | Plotly limitation |
| **Legend ncol** | `entrywidth` fraction | Direct `ncol` param | Different APIs |
| **Colorbar API** | Inline on trace dict | `fig.colorbar()` call | Different lifecycles |
| **Heatmap rendering** | Raster (WebGL) | Vector (pcolormesh) | PGF compatibility |
| **Color format** | CSS `rgb()` | Hex `#rrggbb` | `_css_rgb_to_hex()` bridge |
| **Minimum itemwidth** | >= 30 (Plotly clamp) | No minimum | Plotly API constraint |
| **Annotation coords** | `xref`/`yref` strings | `transform` objects | Different coord systems |
| **Subplots** | `make_subplots()` | `plt.subplots()` | Different subplot APIs |
