"""
Phase 3 integration tests — FigureEngine ↔ FigureConfig pipeline.

Validates:
    1. End-to-end: FigureEngine.build() produces styled figures
    2. ConfigSpecBuilder round-trip: config → spec → Plotly layout
    3. last_spec survives the full pipeline
    4. Export path can consume last_spec for matplotlib rendering
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.resolvers import resolve_config
from src.web.figures.engine import FigureEngine
from src.web.pages.ui.plotting.styles.applicator import StyleApplicator
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.plotly_connector import FigureSpecToPlotly

# ─── Fixtures ────────────────────────────────────────────────────────────────

_BASE_CONFIG: Dict[str, Any] = {
    "x": "benchmark",
    "y": "ipc",
    "title": "IPC by Benchmark",
    "xlabel": "Benchmark",
    "ylabel": "Instructions Per Cycle",
    "width": 900,
    "height": 500,
    "margin_t": 80,
    "margin_b": 120,
    "margin_l": 100,
    "margin_r": 60,
    "margin_pad": 5,
    "title_font_size": 18,
    "xaxis_title_font_size": 14,
    "yaxis_title_font_size": 14,
    "xaxis_tickangle": -45,
    "xaxis_tickfont_size": 12,
    "yaxis_tickfont_size": 12,
    "legend_orientation": "v",
    "legend_x": 1.02,
    "legend_y": 1.0,
    "legend_font_size": 11,
    "legend_font_color": "#333",
    "legend_title": "Workload",
    "legend_title_font_size": 13,
    "legend_title_font_color": "#000",
    "plot_bgcolor": "#f9f9f9",
    "paper_bgcolor": "#ffffff",
    "bargap": 0.2,
    "bargroupgap": 0.05,
}


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Minimal gem5-like data."""
    return pd.DataFrame(
        {
            "benchmark": ["bzip2", "gcc", "mcf", "perlbench"],
            "ipc": [1.24, 1.58, 0.87, 1.41],
        }
    )


@pytest.fixture
def bar_config() -> Dict[str, Any]:
    return dict(_BASE_CONFIG)


# ─── 1. FigureEngine end-to-end ─────────────────────────────────────────────


class TestFigureEngineEndToEnd:
    """FigureEngine produces styled figures via the real pipeline."""

    def test_build_with_real_applicator(
        self, sample_data: pd.DataFrame, bar_config: Dict[str, Any]
    ) -> None:
        """Build using a real BarPlot-like creator and StyleApplicator."""

        class SimpleBarCreator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                return go.Figure(
                    data=[go.Bar(x=list(data["benchmark"]), y=list(data["ipc"]), name="series1")]
                )

        applicator = StyleApplicator("bar")
        engine = FigureEngine()
        engine.register("bar", SimpleBarCreator(), styler=applicator)

        fig = engine.build("bar", sample_data, bar_config)

        # Figure should have traces
        assert len(fig.data) == 1
        assert fig.data[0].type == "bar"
        # Title should be applied
        assert fig.layout.title.text == "IPC by Benchmark"
        # Dimensions should match config
        assert fig.layout.width == 900
        assert fig.layout.height == 500

    def test_applicator_stores_last_spec_after_build(
        self, sample_data: pd.DataFrame, bar_config: Dict[str, Any]
    ) -> None:
        """After engine.build(), the applicator's last_spec is populated."""

        class NullCreator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                return go.Figure(data=[go.Bar(x=["A"], y=[1])])

        applicator = StyleApplicator("bar")
        engine = FigureEngine()
        engine.register("bar", NullCreator(), styler=applicator)

        engine.build("bar", sample_data, bar_config)

        assert applicator.last_spec is not None
        assert applicator.last_spec.title == "IPC by Benchmark"
        assert applicator.last_spec.dimensions.width == 900.0

    def test_legend_labels_applied_by_engine(
        self, sample_data: pd.DataFrame, bar_config: Dict[str, Any]
    ) -> None:
        """FigureEngine applies legend_labels from config."""

        class TraceCreator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                return go.Figure(data=[go.Bar(x=["A"], y=[1], name="original")])

        bar_config["legend_labels"] = {"original": "Renamed"}
        applicator = StyleApplicator("bar")
        engine = FigureEngine()
        engine.register("bar", TraceCreator(), styler=applicator)

        fig = engine.build("bar", sample_data, bar_config)
        assert fig.data[0].name == "Renamed"


# ─── 2. ConfigSpecBuilder ↔ Plotly layout agreement ─────────────────────────


class TestConfigSpecRoundTrip:
    """Verify config → spec → Plotly matches direct StyleApplicator output."""

    def _build_spec_fig(self, config: Dict[str, Any]) -> go.Figure:
        """Build a figure using ConfigSpecBuilder + FigureSpecToPlotly."""
        spec = resolve_config(ConfigSpecBuilder.from_config(config, "bar"))
        fig = go.Figure()
        FigureSpecToPlotly.apply(spec, fig)
        return fig

    def _build_applicator_fig(self, config: Dict[str, Any]) -> go.Figure:
        """Build a figure using direct StyleApplicator."""
        applicator = StyleApplicator("bar")
        fig = go.Figure()
        applicator.apply_styles(fig, config)
        return fig

    def test_dimensions_match(self, bar_config: Dict[str, Any]) -> None:
        """Width and height agree between both paths."""
        spec_fig = self._build_spec_fig(bar_config)
        app_fig = self._build_applicator_fig(bar_config)

        assert spec_fig.layout.width == app_fig.layout.width
        assert spec_fig.layout.height == app_fig.layout.height

    def test_margins_match(self, bar_config: Dict[str, Any]) -> None:
        """Margins agree between both paths."""
        spec_fig = self._build_spec_fig(bar_config)
        app_fig = self._build_applicator_fig(bar_config)

        sm = spec_fig.layout.margin
        am = app_fig.layout.margin
        assert sm.t == am.t
        assert sm.b == am.b
        assert sm.l == am.l
        assert sm.r == am.r

    def test_backgrounds_match(self, bar_config: Dict[str, Any]) -> None:
        """Background colors agree."""
        spec_fig = self._build_spec_fig(bar_config)
        app_fig = self._build_applicator_fig(bar_config)

        assert spec_fig.layout.paper_bgcolor == app_fig.layout.paper_bgcolor
        assert spec_fig.layout.plot_bgcolor == app_fig.layout.plot_bgcolor

    def test_title_matches(self, bar_config: Dict[str, Any]) -> None:
        """Title text and font size agree."""
        spec_fig = self._build_spec_fig(bar_config)
        app_fig = self._build_applicator_fig(bar_config)

        assert spec_fig.layout.title.text == app_fig.layout.title.text
        assert spec_fig.layout.title.font.size == app_fig.layout.title.font.size

    def test_bargap_matches(self, bar_config: Dict[str, Any]) -> None:
        """Bar gap settings agree."""
        spec_fig = self._build_spec_fig(bar_config)
        app_fig = self._build_applicator_fig(bar_config)

        assert spec_fig.layout.bargap == app_fig.layout.bargap


# ─── 3. Spec survives serialization ─────────────────────────────────────────


class TestSpecSerialization:
    """FigureConfig from config round-trips through to_dict / from_dict."""

    def test_round_trip(self, bar_config: Dict[str, Any]) -> None:
        spec = resolve_config(ConfigSpecBuilder.from_config(bar_config, "bar"))
        data = spec.to_dict()
        restored = FigureConfig.from_dict(data)

        assert restored.title == spec.title
        assert restored.dimensions.width == spec.dimensions.width
        assert restored.dimensions.height == spec.dimensions.height
        assert restored.typography.font_size_title == spec.typography.font_size_title
        assert len(restored.legends) == len(spec.legends)

    def test_spec_contains_all_config_values(self, bar_config: Dict[str, Any]) -> None:
        """Key config values must be faithfully captured in the spec."""
        spec = resolve_config(ConfigSpecBuilder.from_config(bar_config, "bar"))

        assert spec.title == "IPC by Benchmark"
        assert spec.axes.x.label == "Benchmark"
        assert spec.axes.y.label == "Instructions Per Cycle"
        assert spec.typography.font_size_title == 18
        assert spec.typography.font_size_xlabel == 14
        assert spec.typography.font_size_ylabel == 14
        assert spec.typography.font_size_ticks == 12
        assert spec.legends[0].font_size == 11
        assert spec.legends[0].font_color == "#333"
        assert spec.legends[0].title == "Workload"
        assert spec.dimensions.bargap == 0.2


# ─── 4. Multi-type engine dispatch ──────────────────────────────────────────


class TestMultiTypeEngineIntegration:
    """Engine correctly dispatches different plot types."""

    def test_bar_and_line_produce_different_figures(self, sample_data: pd.DataFrame) -> None:
        class BarCreator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                return go.Figure(data=[go.Bar(x=["A"], y=[1])])

        class LineCreator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                return go.Figure(data=[go.Scatter(x=[1, 2], y=[3, 4], mode="lines")])

        engine = FigureEngine()
        engine.register("bar", BarCreator(), styler=StyleApplicator("bar"))
        engine.register("line", LineCreator(), styler=StyleApplicator("line"))

        config: Dict[str, Any] = dict(_BASE_CONFIG)

        bar_fig = engine.build("bar", sample_data, config)
        line_fig = engine.build("line", sample_data, config)

        assert bar_fig.data[0].type == "bar"
        assert line_fig.data[0].type == "scatter"
        # Both should have title applied by their respective StyleApplicators
        assert bar_fig.layout.title.text == "IPC by Benchmark"
        assert line_fig.layout.title.text == "IPC by Benchmark"
