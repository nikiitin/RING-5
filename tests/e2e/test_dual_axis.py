"""E2E tests for the dual-axis bar+dot plot across both rendering engines.

``test_engine_comparison`` covers a bar plot; this suite covers the dual-axis
bar-and-dot path in both Plotly and Matplotlib.

Data precondition: ``tier1_page`` (18-row CSV). ``y_bar`` / ``y_dot`` auto-
default to the first two numeric columns (``system.cpu.ipc`` /
``system.cpu.numCycles``); ``test_02`` also sets them explicitly via the POM.
"""

from __future__ import annotations

import csv
from pathlib import Path
import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.helpers.browser_plot_data import read_native_plotly
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser


def _assert_native_grouped_dual_axis(page: Page, csv_path: Path) -> None:
    """Verify grouped bars and benchmark-local right-axis lines retain every CSV value."""
    with csv_path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    bar_values: dict[str, list[float]] = {}
    dot_values: dict[str, list[float]] = {}
    for row in rows:
        bar_values.setdefault(row["config_description"], []).append(float(row["system.cpu.ipc"]))
        dot_values.setdefault(row["benchmark_name"], []).append(float(row["system.cpu.numCycles"]))
    observed = read_native_plotly(
        page,
        "system.cpu.ipc vs system.cpu.numCycles",
        expected_trace_count=len(bar_values) + len(dot_values),
    )
    actual_bars: dict[str, list[float]] = {}
    actual_dots: list[list[float]] = []
    for trace, points in zip(observed["traces"], observed["calculated"], strict=True):
        values = sorted(float(point["y"]) for point in points)
        if trace["type"] == "bar":
            assert trace["yaxis"] == "y"
            group = trace["legendgroup"]
            assert group not in actual_bars
            assert trace["name"] == f"{group} (system.cpu.ipc)"
            actual_bars[group] = values
        else:
            assert trace["type"] == "scatter"
            assert trace["yaxis"] == "y2"
            assert trace["mode"] == "lines+markers"
            assert trace["legendgroup"] == "system.cpu.numCycles-within-group"
            actual_dots.append(values)
    assert actual_bars.keys() == bar_values.keys()
    for group, values in bar_values.items():
        assert actual_bars[group] == pytest.approx(sorted(values))
    expected_dots = sorted(sorted(values) for values in dot_values.values())
    assert len(actual_dots) == len(expected_dots)
    for values, wanted in zip(sorted(actual_dots), expected_dots, strict=True):
        assert values == pytest.approx(wanted)


@pytest.fixture(scope="class")
def dual_axis_page(tier1_page: Page) -> Page:
    """Tier 1 (CSV loaded) + a finalized ``dual_axis_bar_dot`` plot.

    Mirrors the ``_create_and_finalize_bar`` pattern: create the plot, add a
    Sort shaper (keeps every column so both numeric Y candidates survive),
    finalize, then navigate away and back to force a full rerun so the render
    fragment sees ``processed_data``. Creation leaves the new plot selected.
    """
    mp = ManagePlotsPage(tier1_page)
    mp.navigate()
    mp.create_plot("E2E Dual", "dual_axis_bar_dot")
    mp.assert_plot_pill_visible("E2E Dual")

    mp.add_shaper("Sort")
    mp.finalize_pipeline()

    mp.navigate_to("Data Source")
    mp.navigate()
    return tier1_page


@pytest.mark.xdist_group("e2e_dual_axis")
class TestDualAxisRendering:
    """Tier 2: render the dual-axis bar+dot plot in both engines (ordered).

    Shares ``dual_axis_page`` (class-scoped). "E2E Dual" is the most recently
    created plot, so it is auto-selected; tests rely on that and only switch
    the engine — never re-selecting the pill.
    """

    # [test->req~ring5.figure.dual-axis-controls~1]
    # [test->req~ring5.figure.dual-axis-dot-layout~1]

    @pytest.mark.order(1)
    def test_01_plotly_renders_with_auto_axes(self, dual_axis_page: Page) -> None:
        """Default (Plotly) engine renders the dual-axis chart from auto-picked axes."""
        mp = ManagePlotsPage(dual_axis_page)
        mp.navigate()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
        # Title auto-populates as "<y_bar> vs <y_dot>" once both Y columns resolve,
        # proving the dual-axis config picked a bar column and a dot column.
        expect(mp.viz_title_input).to_have_value(re.compile(r"\bvs\b"))

    @pytest.mark.order(2)
    def test_02_explicit_axis_config_renders(self, dual_axis_page: Page) -> None:
        """Explicitly mapping bars→ipc and dots→numCycles still renders (Plotly)."""
        mp = ManagePlotsPage(dual_axis_page)
        mp.navigate()
        expect(mp.viz_y_bar_selectbox).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_y_bar("system.cpu.ipc")
        mp.select_y_dot("system.cpu.numCycles")
        mp.refresh_plot()
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
        expect(mp.viz_title_input).to_have_value("system.cpu.ipc vs system.cpu.numCycles")
        expect(mp.viz_y_label_input).to_have_value("system.cpu.ipc")
        expect(dual_axis_page.get_by_role("textbox", name="Right Y-axis Label")).to_have_value(
            "system.cpu.numCycles"
        )

    @pytest.mark.order(3)
    def test_03_matplotlib_renders(self, dual_axis_page: Page) -> None:
        """Switching to matplotlib renders the dual-axis chart via twinx (st.pyplot)."""
        mp = ManagePlotsPage(dual_axis_page)
        mp.navigate()
        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_engine("matplotlib")
        mp.assert_matplotlib_chart_visible()

    @pytest.mark.order(4)
    def test_04_bar_aligned_within_group_mode_renders(self, dual_axis_page: Page) -> None:
        """Optional grouping survives unrelated controls and renders a decoded image."""
        mp = ManagePlotsPage(dual_axis_page)
        mp.navigate()
        mp.select_color_by("config_description")
        color = mp.viz_color_by_selectbox.get_by_role("combobox")
        expect(color).to_have_value("config_description")
        mp.select_dual_dot_placement("Aligned with each bar")
        expect(color).to_have_value("config_description")
        mp.select_dual_line_scope("Only within each benchmark group")
        expect(color).to_have_value("config_description")
        mp.refresh_plot()
        expect(color).to_have_value("config_description")
        mp.assert_matplotlib_chart_visible()
        image = mp.matplotlib_chart.locator("img").first
        expect(image).to_have_js_property("complete", True)
        assert image.evaluate("image => image.naturalWidth > 0 && image.naturalHeight > 0")

    @pytest.mark.order(5)
    def test_05_switch_back_to_plotly(self, dual_axis_page: Page, e2e_csv_path: Path) -> None:
        """Engine switching retains grouping and renders the exact bars and local lines."""
        mp = ManagePlotsPage(dual_axis_page)
        mp.navigate()
        expect(mp.viz_engine_pills).to_be_visible(timeout=E2E_TIMEOUT)
        mp.select_engine("plotly")
        mp.assert_chart_visible(timeout=CHART_TIMEOUT)
        expect(mp.viz_color_by_selectbox.get_by_role("combobox")).to_have_value(
            "config_description"
        )
        expect(mp.dual_dot_placement_selectbox.get_by_role("combobox")).to_have_value(
            "Aligned with each bar"
        )
        expect(mp.dual_line_scope_selectbox.get_by_role("combobox")).to_have_value(
            "Only within each benchmark group"
        )
        _assert_native_grouped_dual_axis(dual_axis_page, e2e_csv_path)
