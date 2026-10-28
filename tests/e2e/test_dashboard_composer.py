"""Compose, export and interact with a real two-panel dashboard."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.helpers.browser_plot_data import read_native_plotly
from tests.helpers.html_assertions import assert_plotly_document
from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.plot_interactions_page import PlotInteractionsPage

pytestmark = [pytest.mark.requires_browser, pytest.mark.xdist_group("e2e_dashboard_composer")]


def test_build_export_and_link_dashboard_without_changing_source(
    tier2_page: Page, tmp_path: Path
) -> None:
    # [test->req~ring5.plots.multi-panel-dashboard~1]
    # [test->req~ring5.plots.linked-selections~1]
    # [test->req~ring5.figure.panel-composition~1]
    manager = ManagePlotsPage(tier2_page)
    interactions = PlotInteractionsPage(tier2_page)
    source_rows = interactions.download_workspace_rows()
    manager.navigate()
    manager.select_plot("E2E Bar")
    original_title = manager.viz_title_input.input_value()
    original = read_native_plotly(tier2_page, original_title, expected_trace_count=1)
    expected_x = original["traces"][0]["x"]
    expected_y = original["traces"][0]["y"]
    assert len(expected_y) == len(source_rows) == 18
    manager.duplicate_plot()
    expect(manager.plot_selector_pills.get_by_role("radio")).to_have_count(2, timeout=E2E_TIMEOUT)
    interactions.open_dashboard()
    composer = interactions.dashboard
    title = "Browser linked dashboard"
    title_input = composer.get_by_role("textbox", name="Common figure title", exact=True)
    title_input.fill(title)
    title_input.press("Enter")
    manager.wait_for_streamlit(expect_rerun=True)
    composer.get_by_text("Publication layout", exact=True).click()
    expect(composer.get_by_role("radiogroup", name="Panel labels")).to_be_visible(
        timeout=E2E_TIMEOUT
    )
    captions = composer.get_by_role("textbox", name="Panel captions (one per line)")
    captions.fill("Baseline\nComparison")
    captions.press("Tab")
    manager.wait_for_streamlit(expect_rerun=True)
    composer.get_by_text("Link panel selections", exact=True).click()
    expect(composer.get_by_role("radiogroup", name="Relate values on")).to_be_visible(
        timeout=E2E_TIMEOUT
    )
    composer.get_by_role("button", name="Build dashboard").click()
    manager.wait_for_streamlit(expect_rerun=True)
    download = composer.get_by_role("button", name="Download complete HTML", exact=True)
    expect(download).to_be_visible(timeout=CHART_TIMEOUT)
    native = read_native_plotly(tier2_page, title, expected_trace_count=2)
    for trace, points in zip(native["traces"], native["calculated"], strict=True):
        assert trace["type"] == "bar"
        assert trace["x"] == expected_x
        assert trace["y"] == expected_y
        assert len(points) == 18
    assert {trace["xaxis"] for trace in native["traces"]} == {"x", "x2"}
    left = native["layout"]["xaxis"]["domain"]
    right = native["layout"]["xaxis2"]["domain"]
    assert left[1] < right[0]
    annotations = [item["text"] for item in native["layout"]["annotations"]]
    assert any("Baseline" in item for item in annotations)
    assert any("Comparison" in item for item in annotations)

    with tier2_page.expect_download(timeout=CHART_TIMEOUT) as pending:
        download.click()
    html_path = tmp_path / "complete-dashboard.html"
    pending.value.save_as(html_path)
    assert_plotly_document(html_path.read_bytes())
    offline = tier2_page.context.new_page()
    attempted_network: list[str] = []
    offline.route("https://**", lambda route: route.abort())
    offline.route("http://**", lambda route: route.abort())
    offline.on(
        "request",
        lambda request: (
            attempted_network.append(request.url)
            if request.url.startswith(("https://", "http://"))
            else None
        ),
    )
    try:
        offline.goto(html_path.as_uri(), wait_until="domcontentloaded")
        exported = read_native_plotly(offline, title, expected_trace_count=2)
        assert [trace["x"] for trace in exported["traces"]] == [expected_x, expected_x]
        assert [trace["y"] for trace in exported["traces"]] == [expected_y, expected_y]
        assert {trace["xaxis"] for trace in exported["traces"]} == {"x", "x2"}
        assert not attempted_network
    finally:
        offline.close()

    category = "mcf"
    matching = [index for index, value in enumerate(expected_x) if value == category]
    assert len(matching) == 6
    for mode in ("highlight", "filter"):
        pill = composer.get_by_role("radiogroup", name="Linked behavior").get_by_role(
            "radio", name=mode.title(), exact=True
        )
        if not pill.is_checked():
            pill.click()
            manager.wait_for_streamlit(expect_rerun=True)
        interactions.select_dashboard_category(category)
        expect(composer.get_by_text(f"Linked X selection: {category}", exact=True)).to_be_visible(
            timeout=E2E_TIMEOUT
        )
        interactions.wait_for_dashboard_selection(
            category, mode=mode, selected=True, point_count=6 if mode == "filter" else 18
        )
        selected = read_native_plotly(tier2_page, title, expected_trace_count=2)
        for trace in selected["traces"]:
            if mode == "filter":
                assert trace["x"] == [category] * 6
                assert trace["y"] == [expected_y[index] for index in matching]
            else:
                assert trace["selectedpoints"] == matching
                assert trace["unselected"]["marker"]["opacity"] == pytest.approx(0.18)
                assert trace["y"] == expected_y
        composer.get_by_role("button", name="Clear selection", exact=True).click()
        manager.wait_for_streamlit(expect_rerun=True)
        expect(composer.get_by_role("button", name="Clear selection", exact=True)).to_have_count(0)
        interactions.wait_for_dashboard_selection(
            category, mode=mode, selected=False, point_count=18
        )
        restored = read_native_plotly(tier2_page, title, expected_trace_count=2)
        assert [trace["x"] for trace in restored["traces"]] == [expected_x, expected_x]
        assert [trace["y"] for trace in restored["traces"]] == [expected_y, expected_y]
    assert interactions.download_workspace_rows() == source_rows
