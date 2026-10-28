"""Follow the bundled gallery and CSV tutorial through actual browser controls."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.helpers.html_assertions import assert_plotly_document
from tests.visual.pages.data_managers_page import DataManagersPage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage
from tests.visual.pages.portfolio_page import PortfolioPage

pytestmark = pytest.mark.requires_browser


_BENCHMARKS = ("blackscholes", "canneal", "ferret", "swaptions")
_FIRST_ANALYSIS_CSV = "benchmark,ipc\n" "mcf,1.08\n" "xalancbmk,1.31\n" "lbm,0.92\n"


def _assert_native_bar_values(page: Page, expected: dict[str, dict[str, float]]) -> None:
    """Compare native bar observations by series and category, independent of display order."""
    observed = page.wait_for_function(
        """expected => {
            const frame = document.querySelector('iframe[title$="interactive_plotly"]');
            const graph = frame?.contentDocument?.getElementById('myDiv');
            if (!graph?.calcdata || graph.calcdata.length !== Object.keys(expected).length) {
                return false;
            }
            const actual = {};
            for (let series = 0; series < graph.calcdata.length; series++) {
                const trace = graph._fullData[series];
                const wanted = expected[trace.name];
                const points = graph.calcdata[series];
                if (!wanted || points.length !== Object.keys(wanted).length ||
                    Object.hasOwn(actual, trace.name)) return false;
                const axisName = trace.xaxis === 'x' ? 'xaxis' :
                    'xaxis' + trace.xaxis.slice(1);
                const axis = graph._fullLayout[axisName];
                const values = {};
                for (let index = 0; index < points.length; index++) {
                    const point = points[index];
                    const nativeX = trace.x?.[index];
                    let category;
                    if (typeof nativeX === 'string') {
                        category = nativeX;
                    } else if (axis.type === 'category') {
                        category = axis.c2d(point.x);
                    } else if (axis.tickvals?.length &&
                               axis.tickvals.length === axis.ticktext?.length) {
                        let nearest = 0;
                        for (let tick = 1; tick < axis.tickvals.length; tick++) {
                            if (Math.abs(point.x - axis.tickvals[tick]) <
                                Math.abs(point.x - axis.tickvals[nearest])) nearest = tick;
                        }
                        category = axis.ticktext[nearest];
                    }
                    if (typeof category !== 'string' || !Object.hasOwn(wanted, category) ||
                        Object.hasOwn(values, category) || !Number.isFinite(point.y) ||
                        Math.abs(point.y - wanted[category]) >= 1e-8) return false;
                    values[category] = point.y;
                }
                actual[trace.name] = values;
            }
            return actual;
        }""",
        arg=expected,
        timeout=CHART_TIMEOUT,
    ).json_value()
    assert observed.keys() == expected.keys()
    for name, values in expected.items():
        assert observed[name].keys() == values.keys()
        assert observed[name] == pytest.approx(values)


def _download_source_rows(page: Page) -> list[dict[str, str]]:
    """Read the workspace table from its ordinary Data Managers CSV download."""
    managers = DataManagersPage(page)
    managers.navigate()
    download = managers.download_current_view()
    return list(csv.DictReader(StringIO(download.path().read_text(encoding="utf-8-sig"))))


def _assert_no_browser_errors(page: Page) -> None:
    """Reject visible application exceptions and failed-operation alerts."""
    expect(page.get_by_test_id("stException")).to_have_count(0)
    expect(page.get_by_test_id("stAlertContentError")).to_have_count(0)


@pytest.mark.xdist_group("e2e_documentation_showcase")
@pytest.mark.timeout(240)
class TestBundledExampleTour:
    """Load an untouched workspace and edit an existing example without replacing its source."""

    def test_gallery_loads_renders_and_preserves_shared_source(self, tier0_page: Page) -> None:
        # [test->req~ring5.portfolio.bundled-example~1]
        page = tier0_page
        source = DataSourcePage(page)
        source.navigate()
        offer = page.get_by_role("button", name="Load example portfolio", exact=True)
        expect(offer).to_be_visible(timeout=E2E_TIMEOUT)
        offer.click()
        source.wait_for_streamlit(timeout=CHART_TIMEOUT, expect_rerun=True)

        plots = ManagePlotsPage(page)
        plots.assert_page_header_visible()
        expect(plots.plot_selector_pills.get_by_role("radio")).to_have_count(17)
        expect(plots.get_plot_pill("01 · Normalized IPC")).to_be_checked()
        plots.assert_pipeline_step_count(4)
        plots.assert_chart_visible(timeout=CHART_TIMEOUT)
        _assert_native_bar_values(
            page,
            {
                "Baseline": dict.fromkeys(_BENCHMARKS, 1.0),
                "Large L2": dict.fromkeys(_BENCHMARKS, 1.12),
                "Prefetch": dict.fromkeys(_BENCHMARKS, 1.21),
            },
        )

        before = _download_source_rows(page)
        assert len(before) == 83
        assert {row["scenario"] for row in before} == {
            "summary",
            "cache_sweep",
            "repeated_runs",
            "traffic_series",
            "request_flow",
            "energy_waterfall",
        }
        baseline = next(
            row
            for row in before
            if row["scenario"] == "summary"
            and row["benchmark"] == "blackscholes"
            and row["configuration"] == "Baseline"
        )
        assert float(baseline["ipc"]) == pytest.approx(1.55)

        plots.navigate()
        plots.select_engine("matplotlib")
        image = plots.matplotlib_chart.locator("img").first
        expect(image).to_be_visible(timeout=CHART_TIMEOUT)
        expect(image).to_have_js_property("complete", True)
        assert image.evaluate("image => image.naturalWidth > 0 && image.naturalHeight > 0")

        normalization = plots.get_pipeline_step(2)
        baseline_widget = normalization.get_by_test_id("stSelectbox").filter(
            has_text="Baseline value"
        )
        if not baseline_widget.get_by_role("combobox").is_visible():
            normalization.locator("summary").click()
        plots._open_and_select(baseline_widget, "Large L2")
        expect(baseline_widget.get_by_role("combobox")).to_have_value("Large L2")
        plots.finalize_pipeline()
        plots.select_engine("plotly")
        plots.viz_y_label_input.fill("IPC / Large L2")
        plots.viz_y_label_input.press("Enter")
        plots.wait_for_streamlit(expect_rerun=True)
        plots.refresh_plot()
        _assert_native_bar_values(
            page,
            {
                "Baseline": dict.fromkeys(_BENCHMARKS, 1.0 / 1.12),
                "Large L2": dict.fromkeys(_BENCHMARKS, 1.0),
                "Prefetch": dict.fromkeys(_BENCHMARKS, 1.21 / 1.12),
            },
        )

        plots.select_plot("04 · Grouped IPC")
        _assert_native_bar_values(
            page,
            {
                "Baseline": dict(zip(_BENCHMARKS, [1.55, 1.10, 1.82, 2.20], strict=True)),
                "Large L2": dict(zip(_BENCHMARKS, [1.736, 1.232, 2.0384, 2.464], strict=True)),
                "Prefetch": dict(zip(_BENCHMARKS, [1.8755, 1.331, 2.2022, 2.662], strict=True)),
            },
        )
        assert _download_source_rows(page) == before
        source.navigate()
        expect(offer).to_have_count(0)
        _assert_no_browser_errors(page)


@pytest.mark.xdist_group("e2e_documentation_csv")
@pytest.mark.timeout(240)
class TestFirstAnalysisTutorial:
    """Review, plot, export, save and restore the guide's three-row CSV."""

    def test_csv_tutorial_exports_and_restores_exact_observations(
        self, tier0_page: Page, tmp_path: Path
    ) -> None:
        # [test->req~ring5.workspace.data-preview~1]
        page = tier0_page
        csv_path = tmp_path / "first-analysis.csv"
        csv_path.write_text(_FIRST_ANALYSIS_CSV, encoding="utf-8")
        source = DataSourcePage(page)
        source.navigate()
        source.select_csv_mode()
        expect(source.browser_upload_input).to_have_count(1)
        source.browser_upload_input.set_input_files(str(csv_path))
        expect(source.import_review_header).to_be_visible(timeout=E2E_TIMEOUT)
        expect(source.import_accepted_metric.get_by_test_id("stMetricValue")).to_have_text("3")
        rejected = page.get_by_test_id("stMetric").filter(has_text="Rejected rows")
        expect(rejected.get_by_test_id("stMetricValue")).to_have_text("0")
        source.load_accepted_import_button.click()
        expect(source.loaded_review_success).to_contain_text("3", timeout=E2E_TIMEOUT)
        expected_rows = list(csv.DictReader(StringIO(_FIRST_ANALYSIS_CSV)))
        assert _download_source_rows(page) == expected_rows

        plots = ManagePlotsPage(page)
        plots.navigate()
        plots.create_plot("First IPC comparison", "bar")
        plots.add_shaper("Column Selector")
        plots.select_all_columns()
        expect(plots.column_selector_multiselect.locator("[data-tag]")).to_have_count(2)
        plots.finalize_pipeline()
        plots.select_x_axis("benchmark")
        plots.select_y_axis("ipc")
        plots.viz_title_input.fill("IPC by benchmark")
        plots.viz_title_input.press("Enter")
        plots.wait_for_streamlit(expect_rerun=True)
        plots.viz_y_label_input.fill("Instructions per cycle")
        plots.viz_y_label_input.press("Enter")
        plots.wait_for_streamlit(expect_rerun=True)
        plots.refresh_plot()
        _assert_native_bar_values(page, {"ipc": {"mcf": 1.08, "xalancbmk": 1.31, "lbm": 0.92}})

        plots.open_download_expander("plotly", timeout=E2E_TIMEOUT)
        with page.expect_download(timeout=E2E_TIMEOUT) as transfer:
            plots.download_button.click()
        exported = transfer.value.path().read_bytes()
        assert transfer.value.suggested_filename == "First IPC comparison.html"
        assert_plotly_document(exported)
        assert b"Source data" in exported and b"Instructions per cycle" in exported
        plots.wait_for_streamlit(expect_rerun=True)

        portfolios = PortfolioPage(page)
        portfolios.navigate()
        portfolios.save_name_input.fill("First IPC analysis")
        portfolios.save_button.click()
        portfolios.wait_for_streamlit(expect_rerun=True)
        expect(portfolios.managed_portfolio("First IPC analysis")).to_be_visible()
        portfolios.reset_all()
        plots.navigate()
        plots.assert_no_plots_warning()
        portfolios.navigate()
        portfolios.select_portfolio("First IPC analysis")
        portfolios.assert_checksum_integrity_visible()
        portfolios.load_button.click()
        portfolios.wait_for_streamlit(expect_rerun=True)
        plots.navigate()
        expect(plots.plot_selector_pills.get_by_role("radio")).to_have_count(1)
        expect(plots.get_plot_pill("First IPC comparison")).to_be_checked()
        expect(plots.viz_title_input).to_have_value("IPC by benchmark")
        _assert_native_bar_values(page, {"ipc": {"mcf": 1.08, "xalancbmk": 1.31, "lbm": 0.92}})
        assert _download_source_rows(page) == expected_rows
        source.navigate()
        expect(page.get_by_role("button", name="Load example portfolio")).to_have_count(0)
        _assert_no_browser_errors(page)
