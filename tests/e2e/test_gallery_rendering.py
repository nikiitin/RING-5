"""Render every shipped example through both connectors and inspect native observations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CHART_TIMEOUT, E2E_TIMEOUT
from tests.helpers.browser_plot_data import read_native_plotly
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = [pytest.mark.requires_browser, pytest.mark.xdist_group("e2e_gallery_rendering")]


@dataclass(frozen=True)
class GalleryCase:
    """One public gallery selection and its independent native assertion family."""

    plot_type: str
    name: str
    title: str
    native_type: str


_CASES = (
    GalleryCase("bar", "01 · Normalized IPC", "Normalized IPC by Configuration", "bar"),
    GalleryCase(
        "line", "02 · Cache Capacity Sweep", "IPC Across an Ordered Cache-Capacity Sweep", "scatter"
    ),
    GalleryCase("scatter", "03 · IPC vs Energy", "Performance–Energy Trade-off", "scatter"),
    GalleryCase(
        "grouped_bar", "04 · Grouped IPC", "IPC with Illustrative Summary Uncertainty", "bar"
    ),
    GalleryCase("stacked_bar", "05 · Cycle Composition", "Baseline Cycle Composition", "bar"),
    GalleryCase(
        "grouped_stacked_bar",
        "06 · Grouped Cycle Composition",
        "Cycle Composition by Configuration",
        "bar",
    ),
    GalleryCase(
        "histogram", "07 · Latency Histogram", "Synthetic Memory-Latency Bucket Counts", "bar"
    ),
    GalleryCase(
        "heatmap", "08 · Cache Miss Rates", "L1 and L2 Miss Rates by Configuration", "heatmap"
    ),
    GalleryCase("dual_axis_bar_dot", "09 · IPC and Cache Misses", "IPC and L2 Miss Rate", "bar"),
    GalleryCase(
        "area",
        "10 · Memory Traffic Over Time",
        "Additive Memory Traffic in Equal-Length Intervals",
        "scatter",
    ),
    GalleryCase(
        "box", "11 · Repeated-Run IPC", "Twelve Synthetic IPC Observations per Configuration", "box"
    ),
    GalleryCase(
        "ecdf", "12 · Repeated-Run Latency ECDF", "Synthetic Repeated-Run Memory Latency", "scatter"
    ),
    GalleryCase(
        "parallel_coordinates", "13 · Design Space", "Configuration Design Space", "parcoords"
    ),
    GalleryCase("radar", "14 · Workload Profile", "IPC Profile by Workload", "scatterpolar"),
    GalleryCase("sankey", "15 · Request Flow", "Conserved Synthetic Memory Requests", "sankey"),
    GalleryCase(
        "violin",
        "16 · Repeated-Run Latency",
        "Twelve Synthetic Latency Observations per Configuration",
        "violin",
    ),
    GalleryCase("waterfall", "17 · Energy Savings", "Illustrative Energy Savings", "waterfall"),
)
_BENCHMARKS = ["blackscholes", "canneal", "ferret", "swaptions"]
_CONFIGURATIONS = ["Baseline", "Large L2", "Prefetch"]
_IPC = {
    "Baseline": [1.55, 1.10, 1.82, 2.20],
    "Large L2": [1.736, 1.232, 2.0384, 2.464],
    "Prefetch": [1.8755, 1.331, 2.2022, 2.662],
}
_ENERGY = {
    "Baseline": [8.4, 12.8, 10.1, 7.3],
    "Large L2": [7.896, 12.032, 9.494, 6.862],
    "Prefetch": [8.736, 13.312, 10.504, 7.592],
}
_MISSES = {
    "blackscholes": [[0.0435, 0.03306, 0.02784], [0.075, 0.057, 0.048]],
    "canneal": [[0.08236, 0.06259, 0.05271], [0.142, 0.10792, 0.09088]],
    "ferret": [[0.05684, 0.0432, 0.03638], [0.098, 0.07448, 0.06272]],
    "swaptions": [[0.03016, 0.02292, 0.0193], [0.052, 0.03952, 0.03328]],
}
_CYCLES = {
    "Front end": [
        135483871,
        200000000,
        126373626,
        109090909,
        120967742,
        178571429,
        112833595,
        97402597,
        111970141,
        165289256,
        104441013,
        90157776,
    ],
    "Memory": [
        203225806,
        347272727,
        185714286,
        132727273,
        181451613,
        310064935,
        165816327,
        118506494,
        167955212,
        287002254,
        153482881,
        109691961,
    ],
    "Execution": [
        306451613,
        361818182,
        237362637,
        212727273,
        273617511,
        323051948,
        211930926,
        189935065,
        253265796,
        299023291,
        196167469,
        175807663,
    ],
}
_VARIATION = [0.90, 0.92, 0.94, 0.96, 0.98, 1.0, 1.0, 1.02, 1.04, 1.06, 1.08, 1.10]


@pytest.fixture(scope="class")
def gallery_page(tier0_page: Page) -> Page:
    """Load the ordinary offline portfolio once within this independent class."""
    source = DataSourcePage(tier0_page)
    source.navigate()
    tier0_page.get_by_role("button", name="Load example portfolio", exact=True).click()
    source.wait_for_streamlit(timeout=CHART_TIMEOUT, expect_rerun=True)
    plots = ManagePlotsPage(tier0_page)
    expect(plots.plot_selector_pills.get_by_role("radio")).to_have_count(17)
    return tier0_page


def _by_name(traces: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    names = {trace["name"]: trace for trace in traces}
    assert len(names) == len(traces), "Unexpected duplicate native series identity"
    return names


def _assert_values(actual: Any, expected: Sequence[float]) -> None:
    assert len(actual) == len(expected)
    assert actual == pytest.approx(expected, rel=1e-8, abs=1e-8)


def _assert_native_observations(case: GalleryCase, native: dict[str, Any]) -> None:
    """Check the gallery's declared synthetic science in the calculated frontend."""
    traces = native["traces"]
    assert traces and any(trace["type"] == case.native_type for trace in traces)
    kind = case.plot_type
    if kind in {"bar", "grouped_bar", "scatter", "radar"}:
        groups = _by_name(traces)
        assert set(groups) == set(_CONFIGURATIONS)
        for index, name in enumerate(_CONFIGURATIONS):
            trace = groups[name]
            if kind == "scatter":
                _assert_values(trace["x"], _IPC[name])
                _assert_values(trace["y"], _ENERGY[name])
            elif kind == "radar":
                assert trace["theta"] == [*_BENCHMARKS, _BENCHMARKS[0]]
                _assert_values(trace["r"], [*_IPC[name], _IPC[name][0]])
            else:
                values = [1.0, 1.12, 1.21][index] if kind == "bar" else None
                _assert_values(trace["y"], [values] * 4 if values is not None else _IPC[name])
                if kind == "grouped_bar":
                    _assert_values(
                        trace["error_y"]["array"], [round(value * 0.035, 4) for value in _IPC[name]]
                    )
    elif kind == "line":
        groups = _by_name(traces)
        assert set(groups) == set(_BENCHMARKS)
        for benchmark, expected in zip(
            _BENCHMARKS,
            (
                [1.55, 1.674, 1.798],
                [1.1, 1.188, 1.276],
                [1.82, 1.9656, 2.1112],
                [2.2, 2.376, 2.552],
            ),
            strict=True,
        ):
            _assert_values(groups[benchmark]["x"], [64, 128, 256])
            _assert_values(groups[benchmark]["y"], expected)
    elif kind in {"stacked_bar", "grouped_stacked_bar"}:
        groups = _by_name(traces)
        assert set(groups) == set(_CYCLES)
        count = 4 if kind == "stacked_bar" else 12
        for name, values in _CYCLES.items():
            _assert_values(sorted(groups[name]["y"]), sorted(values[:count]))
        assert native["layout"]["barmode"] == "stack"
    elif kind == "histogram":
        groups = _by_name(traces)
        assert set(groups) == set(_CONFIGURATIONS)
        for name, values in zip(
            _CONFIGURATIONS,
            ([18, 30, 27, 17, 8], [25, 34, 24, 12, 5], [32, 36, 20, 9, 3]),
            strict=True,
        ):
            _assert_values(groups[name]["y"], values)
            assert sum(groups[name]["y"]) == pytest.approx(100)
            assert len(groups[name]["x"]) == 5
    elif kind == "heatmap":
        groups = _by_name(traces)
        assert set(groups) == set(_BENCHMARKS)
        for benchmark, expected in _MISSES.items():
            assert groups[benchmark]["x"] == _CONFIGURATIONS
            assert groups[benchmark]["y"] == ["L1 miss rate", "L2 miss rate"]
            for actual_row, expected_row in zip(groups[benchmark]["z"], expected, strict=True):
                _assert_values(actual_row, expected_row)
    elif kind == "dual_axis_bar_dot":
        assert len(traces) == 6
        for name in _CONFIGURATIONS:
            bars = [
                trace for trace in traces if trace["legendgroup"] == name and trace["type"] == "bar"
            ]
            dots = [
                trace
                for trace in traces
                if trace["legendgroup"] == name and trace["type"] == "scatter"
            ]
            assert len(bars) == len(dots) == 1
            _assert_values(bars[0]["y"], _IPC[name])
            _assert_values(
                dots[0]["y"],
                [_MISSES[benchmark][1][_CONFIGURATIONS.index(name)] for benchmark in _BENCHMARKS],
            )
            assert bars[0]["yaxis"] == "y" and dots[0]["yaxis"] == "y2"
            assert dots[0]["mode"] == "markers"
    elif kind == "area":
        groups = _by_name(traces)
        assert set(groups) == {"Demand reads", "Writebacks", "Prefetches"}
        for name, values in {
            "Demand reads": [10, 14, 18, 16, 12],
            "Writebacks": [12, 17, 22, 19, 14],
            "Prefetches": [15, 20, 26, 23, 18],
        }.items():
            _assert_values(groups[name]["x"], [0, 1, 2, 3, 4])
            _assert_values(groups[name]["y"], values)
    elif kind in {"box", "violin", "ecdf"}:
        groups = _by_name(traces)
        assert set(groups) == set(_CONFIGURATIONS)
        for index, name in enumerate(_CONFIGURATIONS):
            center = _IPC[name][0] if kind == "box" else [24, 19.68, 17.04][index]
            expected = [round(center * value, 5) for value in _VARIATION]
            trace = groups[name]
            if kind == "ecdf":
                _assert_values(trace["x"], sorted(set(expected)))
                _assert_values(
                    trace["y"],
                    [
                        1 / 12,
                        2 / 12,
                        3 / 12,
                        4 / 12,
                        5 / 12,
                        7 / 12,
                        8 / 12,
                        9 / 12,
                        10 / 12,
                        11 / 12,
                        1,
                    ],
                )
                assert trace["line"]["shape"] == "hv"
            elif kind == "box":
                _assert_values(trace["y"][0], expected)
                _assert_values(trace["median"], [center])
                assert native["calculated"][_CONFIGURATIONS.index(name)][0]["med"] == pytest.approx(
                    center
                )
            else:
                _assert_values(trace["y"], expected)
    elif kind == "parallel_coordinates":
        assert len(traces) == 1
        dimensions = traces[0]["dimensions"]
        assert [item["label"] for item in dimensions] == [
            "benchmark",
            "configuration",
            "ipc",
            "energy_j",
            "l2_miss_rate",
        ]
        assert all(len(item["values"]) == 12 for item in dimensions)
        _assert_values(
            sorted(dimensions[2]["values"]),
            sorted(value for values in _IPC.values() for value in values),
        )
        _assert_values(
            sorted(dimensions[3]["values"]),
            sorted(value for values in _ENERGY.values() for value in values),
        )
    elif kind == "sankey":
        assert len(traces) == 1
        trace = traces[0]
        labels, links = trace["node"]["label"], trace["link"]
        observed = {
            (labels[source], labels[target]): value
            for source, target, value in zip(
                links["source"], links["target"], links["value"], strict=True
            )
        }
        assert observed == {
            ("CPU 0", "L1"): 100,
            ("CPU 1", "L1"): 80,
            ("L1", "L2"): 60,
            ("L1", "Memory"): 120,
            ("L2", "Memory"): 60,
        }
    elif kind == "waterfall":
        assert len(traces) == 1
        assert traces[0]["x"] == ["Baseline", "Large L2 saving", "Prefetch saving", "Optimized"]
        _assert_values(traces[0]["y"], [10, -1.6, -1.2, 0])
        assert traces[0]["measure"] == ["absolute", "relative", "relative", "total"]
        assert traces[0]["text"][-1] == "7.2"
    else:
        pytest.fail(f"No native science assertion for {kind}")


class TestGalleryRendering:
    """Select every actual example and replace its native chart through both engines."""

    @pytest.mark.parametrize("case", _CASES, ids=lambda case: case.plot_type)
    def test_each_example_has_expected_native_data_and_fresh_matplotlib_image(
        self, gallery_page: Page, case: GalleryCase
    ) -> None:
        page = gallery_page
        plots = ManagePlotsPage(page)
        previous_image = plots.matplotlib_chart.locator("img")
        previous_source = (
            previous_image.first.get_attribute("src") if previous_image.count() else None
        )
        plots.select_plot(case.name)
        plots.select_engine("plotly")
        expect(plots.get_plot_pill(case.name)).to_be_checked(timeout=E2E_TIMEOUT)
        expect(plots.viz_title_input).to_have_value(case.title, timeout=E2E_TIMEOUT)
        native = read_native_plotly(page, case.title)
        _assert_native_observations(case, native)

        # A zero image count before switching prevents an earlier plot's bitmap
        # from satisfying the Matplotlib assertion after a Streamlit rerun.
        expect(plots.matplotlib_chart).to_have_count(0)
        plots.select_engine("matplotlib")
        expect(plots.plotly_chart).to_have_count(0)
        expect(plots.get_plot_pill(case.name)).to_be_checked()
        expect(plots.viz_title_input).to_have_value(case.title)
        image = plots.matplotlib_chart.locator("img").first
        expect(image).to_be_visible(timeout=CHART_TIMEOUT)
        expect(image).to_have_js_property("complete", True, timeout=CHART_TIMEOUT)
        if previous_source is not None:
            assert (
                image.get_attribute("src") != previous_source
            ), "Another example's native image survived the plot switch"
        decoded = image.evaluate("""image => {
            if (image.naturalWidth <= 0 || image.naturalHeight <= 0) return null;
            const canvas = document.createElement('canvas');
            canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
            const context = canvas.getContext('2d');
            context.drawImage(image, 0, 0);
            const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
            const colors = new Set();
            for (let offset = 0; offset < pixels.length; offset += 4) {
                colors.add(Array.from(pixels.slice(offset, offset + 4)).join(','));
                if (colors.size > 16) break;
            }
            return {width: canvas.width, height: canvas.height, colors: colors.size};
        }""")
        assert decoded and decoded["width"] > 100 and decoded["height"] > 100
        assert decoded["colors"] > 4, "Decoded native image contains no meaningful painted chart"
        expect(page.get_by_test_id("stException")).to_have_count(0)
        expect(page.get_by_test_id("stAlertContentError")).to_have_count(0)
