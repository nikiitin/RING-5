"""Resolve the exact contributing rows behind real bar and heatmap pointer clicks."""

from __future__ import annotations

from collections import Counter

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import E2E_TIMEOUT
from tests.helpers.browser_plot_data import read_native_plotly
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.plot_interactions_page import PlotInteractionsPage

pytestmark = [pytest.mark.requires_browser, pytest.mark.xdist_group("e2e_plot_drill_down")]


def _assert_source_rows(
    actual: list[dict[str, str]], expected: list[dict[str, str]], *, identity_columns: set[str]
) -> None:
    """Compare complete original rows, ignoring only the grid's unnamed index."""
    assert actual and expected
    columns = set(actual[0]) - {""}
    assert identity_columns <= columns
    assert columns == set(expected[0])

    def normalized(row: dict[str, str]) -> tuple[tuple[str, float | str], ...]:
        values: list[tuple[str, float | str]] = []
        for name in sorted(columns):
            value = row[name]
            try:
                rendered: float | str = float(value)
            except ValueError:
                rendered = value
            values.append((name, rendered))
        return tuple(values)

    assert Counter(map(normalized, actual)) == Counter(map(normalized, expected))


def test_point_drill_down_returns_exact_clicked_category_and_color(tier2_page: Page) -> None:
    # [test->req~ring5.plots.drill-down~1]
    page = tier2_page
    manager = ManagePlotsPage(page)
    interactions = PlotInteractionsPage(page)
    source_rows = interactions.download_workspace_rows()
    manager.navigate()
    manager.select_plot("E2E Bar")
    manager.select_color_by("config_description")
    manager.enable_drill_down()
    title = manager.viz_title_input.input_value()
    native = read_native_plotly(page, title, expected_trace_count=3)
    first_trace = native["traces"][0]
    category = first_trace["x"][0]
    configuration = first_trace["name"]
    expected = [
        row
        for row in source_rows
        if row["benchmark_name"] == category and row["config_description"] == configuration
    ]
    assert len(expected) == 2
    point = max(index for index, value in enumerate(first_trace["x"]) if value == category)
    interactions.click_bar_point(trace=0, point=point)
    expect(manager.drill_down_panel).to_be_visible(timeout=E2E_TIMEOUT)
    metric = page.get_by_test_id("stMetric").filter(has_text="Matching rows")
    expect(metric.get_by_test_id("stMetricValue")).to_have_text(str(len(expected)))
    expect(
        page.get_by_text(
            f"Selected plot dimensions: benchmark_name = {category} · "
            f"config_description = {configuration}",
            exact=True,
        )
    ).to_be_visible()
    actual = interactions.download_drill_down_rows()
    _assert_source_rows(actual, expected, identity_columns={"benchmark_name", "config_description"})
    manager.drill_down_back_button.click()
    manager.wait_for_streamlit(expect_rerun=True)
    expect(manager.drill_down_panel).to_be_hidden(timeout=E2E_TIMEOUT)
    expect(manager.viz_x_axis_selectbox.get_by_role("combobox")).to_have_value("benchmark_name")
    expect(manager.viz_color_by_selectbox.get_by_role("combobox")).to_have_value(
        "config_description"
    )
    restored = read_native_plotly(page, title, expected_trace_count=3)
    assert [(trace["x"], trace["y"]) for trace in restored["traces"]] == [
        (trace["x"], trace["y"]) for trace in native["traces"]
    ]
    assert interactions.download_workspace_rows() == source_rows


@pytest.mark.parametrize("kind", ["histogram", "heatmap"])
def test_gallery_drill_down_excludes_rows_outside_its_pipeline(tier0_page: Page, kind: str) -> None:
    # [test->req~ring5.plots.drill-down~1]
    page = tier0_page
    source = DataSourcePage(page)
    source.navigate()
    page.get_by_role("button", name="Load example portfolio", exact=True).click()
    source.wait_for_streamlit(expect_rerun=True)
    manager = ManagePlotsPage(page)
    interactions = PlotInteractionsPage(page)
    source_rows = interactions.download_workspace_rows()
    assert len(source_rows) == 83
    manager.navigate()
    manager.select_plot(
        "07 · Latency Histogram" if kind == "histogram" else "08 · Cache Miss Rates"
    )
    manager.enable_drill_down()
    title = manager.viz_title_input.input_value()
    native = read_native_plotly(page, title)
    if kind == "histogram":
        trace = native["traces"][-1]
        configuration = trace["name"]
        assert configuration == "Prefetch"
        expected = [
            row
            for row in source_rows
            if row["scenario"] == "summary" and row["configuration"] == configuration
        ]
        assert len(expected) == 4
        # The value edge must sit above the other overlaid bars at this bucket.
        point = next(
            index
            for index, value in enumerate(trace["y"])
            if value > 0 and all(value > other["y"][index] for other in native["traces"][:-1])
        )
        interactions.click_bar_point(trace=len(native["traces"]) - 1, point=point)
        expect(
            page.get_by_text(
                f"Selected plot dimensions: configuration = {configuration}", exact=True
            )
        ).to_be_visible(timeout=E2E_TIMEOUT)
    else:
        trace = native["traces"][0]
        configuration = trace["x"][0]
        benchmark = trace["name"]
        expected = [
            row
            for row in source_rows
            if row["scenario"] == "summary"
            and row["configuration"] == configuration
            and row["benchmark"] == benchmark
        ]
        assert len(expected) == 1
        interactions.click_heatmap_cell(trace=0, row=0, column=0)
    expect(manager.drill_down_panel).to_be_visible(timeout=E2E_TIMEOUT)
    metric = page.get_by_test_id("stMetric").filter(has_text="Matching rows")
    expect(metric.get_by_test_id("stMetricValue")).to_have_text(str(len(expected)))
    _assert_source_rows(
        interactions.download_drill_down_rows(),
        expected,
        identity_columns={"benchmark", "configuration"},
    )
    manager.drill_down_back_button.click()
    manager.wait_for_streamlit(expect_rerun=True)
    expect(manager.drill_down_panel).to_be_hidden(timeout=E2E_TIMEOUT)
    restored = read_native_plotly(page, title)
    assert [(trace["x"], trace["y"]) for trace in restored["traces"]] == [
        (trace["x"], trace["y"]) for trace in native["traces"]
    ]
    assert interactions.download_workspace_rows() == source_rows
    expect(page.get_by_test_id("stException")).to_have_count(0)
