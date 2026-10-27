"""Visual test: the dual-axis bar+dot plot rendered in both engines.

Loads the shared 18-row fixture CSV, builds a finalized ``dual_axis_bar_dot``
plot, and captures a screenshot of the chart in **both** the Plotly and the
matplotlib engine. This is the visual companion to ``tests/e2e/test_dual_axis``:
the e2e suite asserts the chart *renders*; this one checks painted Plotly bars
against the raw seed measurements and captures both engines for manual comparison.

Screenshots land in ``tests/visual/screenshots/<ClassName>/`` (gitignored).
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from typing import TypedDict

import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage

pytestmark = pytest.mark.requires_browser

# The same 18×8 fixture the e2e suite uses (has system.cpu.ipc + numCycles).
_E2E_CSV: Path = Path(__file__).parents[1] / "e2e" / "fixtures" / "sample_data.csv"
_CHART_TIMEOUT: int = 30_000
_E2E_TIMEOUT: int = 60_000


class PaintedBar(TypedDict):
    """Data coordinates recovered from actual browser SVG paint and axis ticks."""

    category: str
    bottom: float
    top: float


class PrimaryTick(TypedDict):
    """A visible primary-axis tick and its SVG coordinate."""

    value: float
    y: float


class PaintedGeometry(TypedDict):
    """Actual frontend version, visible-axis calibration and painted data marks."""

    plotly_version: str
    primary_y_ticks: list[PrimaryTick]
    bars: list[PaintedBar]


def _painted_group_bars(mp: ManagePlotsPage) -> PaintedGeometry:
    """Calibrate painted rectangle endpoints from the rendered primary-axis ticks."""
    expect(mp.plotly_chart).to_have_count(1)
    plot = mp.plotly_chart.content_frame.locator(".js-plotly-plot")
    expect(plot).to_be_visible(timeout=_CHART_TIMEOUT)
    expect(plot.locator(".barlayer .trace.bars")).to_have_count(1)
    payload: object = plot.evaluate(r"""plot => {
            const number = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
            const at = (element, x, y) => {
                const matrix = element.getCTM();
                if (matrix === null) throw new Error('Missing SVG coordinate matrix');
                return new DOMPoint(x, y).matrixTransform(matrix);
            };
            const ticks = [...plot.querySelectorAll('.yaxislayer-above .ytick text')].map(text => {
                const label = text.textContent.trim().replaceAll('−', '-');
                if (!number.test(label)) throw new Error(`Non-numeric primary tick: ${label}`);
                return {value: Number(label), y: at(text, 0, 0).y};
            }).sort((a, b) => a.value - b.value);
            if (ticks.length < 2 || ticks[0].value === ticks.at(-1).value) {
                throw new Error('Primary SVG ticks do not calibrate a linear axis');
            }
            const first = ticks[0], last = ticks.at(-1);
            const scale = (last.y - first.y) / (last.value - first.value);
            if (!Number.isFinite(scale) || scale >= 0) throw new Error('Invalid primary SVG scale');
            const zero = first.y - first.value * scale;
            for (const tick of ticks) {
                if (Math.abs(tick.y - (zero + scale * tick.value)) > 0.75) {
                    throw new Error('Primary SVG ticks are not affine');
                }
            }
            const labels = [...plot.querySelectorAll('.xaxislayer-above .xtick text')];
            const tickMarks = [...plot.querySelectorAll('.xaxislayer-above path.xtick.ticks')];
            if (tickMarks.length !== labels.length) {
                throw new Error('Category labels and tick marks do not pair');
            }
            // Painted tick marks retain category centers when label glyphs are rotated.
            const categories = labels.map((text, index) => {
                const tick = tickMarks[index], start = tick.getPointAtLength(0);
                const x = at(tick, start.x, start.y).x;
                const transforms = text.transform.baseVal;
                if (!transforms.numberOfItems || text.x.baseVal.numberOfItems !== 1) {
                    throw new Error('Missing category label translation or anchor');
                }
                const prefix = transforms.getItem(0).matrix;
                if (prefix.a !== 1 || prefix.b !== 0 || prefix.c !== 0 || prefix.d !== 1) {
                    throw new Error('Category label prefix is not a pure translation');
                }
                const anchorX = at(text.parentElement,
                    prefix.e + text.x.baseVal.getItem(0).value, prefix.f).x;
                if (!Number.isFinite(x) || !Number.isFinite(anchorX)
                    || Math.abs(anchorX - x) > 0.75) {
                    throw new Error('Category label and painted tick do not match');
                }
                return {label: text.textContent.trim(), x};
            });
            if (categories.length !== 3 || new Set(categories.map(t => t.label)).size !== 3
                || new Set(categories.map(t => t.x)).size !== 3) {
                throw new Error('Expected the three fixture benchmark ticks');
            }
            const paths = [...plot.querySelectorAll('.barlayer .trace.bars .point path')];
            if (paths.length !== 18) throw new Error(`Expected 18 raw bars, got ${paths.length}`);
            return {plotly_version: window.Plotly.version, primary_y_ticks: ticks,
                    bars: paths.map(path => {
                const match = /^M([\d.eE+-]+),([\d.eE+-]+)V([\d.eE+-]+)H([\d.eE+-]+)V([\d.eE+-]+)Z$/
                    .exec(path.getAttribute('d') || '');
                if (match === null) throw new Error('Unexpected painted bar path');
                const [left, bottom, top, right, close] = match.slice(1).map(Number);
                if (![left, bottom, top, right, close].every(Number.isFinite)
                    || right <= left || bottom !== close) {
                    throw new Error('Invalid painted rectangle');
                }
                const lower = at(path, (left + right) / 2, bottom);
                const upper = at(path, (left + right) / 2, top);
                const nearest = [...categories].sort(
                    (a, b) => Math.abs(a.x - lower.x) - Math.abs(b.x - lower.x)
                )[0];
                if (Math.abs(nearest.x - lower.x) > 0.75) {
                    throw new Error('Bar is not at its benchmark tick');
                }
                return {category: nearest.label, bottom: (lower.y - zero) / scale,
                        top: (upper.y - zero) / scale};
            })};
        }""")
    assert isinstance(payload, dict)
    version: object = payload.get("plotly_version")
    ticks_payload: object = payload.get("primary_y_ticks")
    bars_payload: object = payload.get("bars")
    assert isinstance(version, str) and version.strip()
    assert isinstance(ticks_payload, list) and len(ticks_payload) >= 2
    assert isinstance(bars_payload, list)
    ticks: list[PrimaryTick] = []
    for item in ticks_payload:
        assert isinstance(item, dict)
        value: object = item.get("value")
        position: object = item.get("y")
        assert type(value) in (int, float) and isinstance(value, (int, float))
        assert type(position) in (int, float) and isinstance(position, (int, float))
        ticks.append({"value": float(value), "y": float(position)})
    bars: list[PaintedBar] = []
    for item in bars_payload:
        assert isinstance(item, dict)
        category: object = item.get("category")
        bottom: object = item.get("bottom")
        top: object = item.get("top")
        assert isinstance(category, str)
        assert type(bottom) in (int, float) and isinstance(bottom, (int, float))
        assert type(top) in (int, float) and isinstance(top, (int, float))
        bars.append({"category": category, "bottom": float(bottom), "top": float(top)})
    return {"plotly_version": version, "primary_y_ticks": ticks, "bars": bars}


@pytest.mark.requires_browser
class TestDualAxisEngines:
    """Render the same dual-axis observations through both engines."""

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def _setup_dual_axis_plot(
        cls,
        shared_page: Page,
        live_server_url: str,
        _reset_app_state: None,
    ) -> None:
        """Load CSV → create + finalize a dual_axis_bar_dot plot once per class."""
        assert _E2E_CSV.exists(), f"Fixture CSV not found: {_E2E_CSV}"

        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.upload_csv(_E2E_CSV)
        ds.wait_for_streamlit()

        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.create_plot("Visual Dual", "dual_axis_bar_dot")
        mp.assert_plot_pill_visible("Visual Dual")
        mp.add_shaper("Sort")
        mp.finalize_pipeline()
        # Full rerun so the render fragment sees processed_data.
        mp.navigate_to("Data Source")
        mp.navigate()

    def test_01_plotly_screenshot(self, shared_page: Page, shared_screenshot_dir: Path) -> None:
        """Check the painted raw seed bars, then capture the Plotly chart."""
        # [test->req~ring5.plot.dual-axis-bar-dot~1]
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        mp.select_engine("plotly")
        mp.assert_chart_visible(timeout=_CHART_TIMEOUT)
        geometry = _painted_group_bars(mp)
        painted = geometry["bars"]
        with _E2E_CSV.open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        expected = {
            benchmark: sorted(
                float(row["seed"]) for row in rows if row["benchmark_name"] == benchmark
            )
            for benchmark in {row["benchmark_name"] for row in rows}
        }
        assert len(painted) == len(rows) == 18
        assert {bar["category"] for bar in painted} == set(expected)
        for benchmark, raw_seed in expected.items():
            bars = [bar for bar in painted if bar["category"] == benchmark]
            assert len(bars) == len(raw_seed) == 6
            assert [bar["bottom"] for bar in bars] == pytest.approx([0.0] * 6, abs=0.02)
            assert sorted(bar["top"] for bar in bars) == pytest.approx(raw_seed, abs=0.02)
        (shared_screenshot_dir / "dual_axis_plotly_geometry.json").write_text(
            json.dumps(
                {
                    **geometry,
                    "fixture_sha256": hashlib.sha256(_E2E_CSV.read_bytes()).hexdigest(),
                    "expected_seed_by_benchmark": expected,
                    "painted_geometry_matches_raw_seed": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        mp.plotly_chart.screenshot(
            path=str(shared_screenshot_dir / "dual_axis_plotly.png"),
        )

    def test_02_matplotlib_screenshot(self, shared_page: Page, shared_screenshot_dir: Path) -> None:
        """Switch to matplotlib (twinx) and capture the dual-axis chart."""
        mp = ManagePlotsPage(shared_page)
        mp.navigate()
        expect(mp.viz_engine_pills).to_be_visible(timeout=_E2E_TIMEOUT)
        mp.select_engine("matplotlib")
        mp.assert_matplotlib_chart_visible()
        mp.matplotlib_chart.screenshot(
            path=str(shared_screenshot_dir / "dual_axis_matplotlib.png"),
        )
