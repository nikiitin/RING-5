"""Registered strategies prepare styling once for native figures and serialization."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.core.models.visualization.figure_config import FigureConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.rendering.plot_renderer import build_render_artifact
from src.web.rendering.figure_preparation import PreparedFigure
from src.web.models.render_artifact import RenderArtifact
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.plotly_connector import FigureSpecToPlotly

# Fixtures
_BASE_CONFIG: dict[str, Any] = {
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
    "legend_orientation": "vertical",
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
def bar_config() -> dict[str, Any]:
    return dict(_BASE_CONFIG)


def _artifact(data: pd.DataFrame, config: dict[str, Any], plot_type: str = "bar") -> RenderArtifact:
    plot = PlotFactory.create_plot(plot_type, plot_id=1, name="Measured")
    plot.processed_data = data
    return build_render_artifact(plot, config, "plotly")


class TestFigureEngineEndToEnd:
    """Real registered strategies produce measured native figures and owned styling."""

    def test_build_with_real_artifact(
        self, sample_data: pd.DataFrame, bar_config: dict[str, Any]
    ) -> None:
        artifact = _artifact(sample_data, bar_config)
        assert isinstance(artifact.figure, go.Figure)
        fig = artifact.figure
        assert len(fig.data) == 1
        assert cast(go.Bar, fig.data[0]).type == "bar"
        assert list(cast(go.Bar, fig.data[0]).y) == [1.24, 1.58, 0.87, 1.41]
        assert fig.layout.title.text == "IPC by Benchmark"
        assert fig.layout.width == 900
        assert fig.layout.height == 500

    def test_artifact_retains_exact_spec_after_build(
        self, sample_data: pd.DataFrame, bar_config: dict[str, Any]
    ) -> None:
        artifact = _artifact(sample_data, bar_config)
        assert isinstance(artifact.figure_spec, FigureConfig)
        assert artifact.figure_spec.title == "IPC by Benchmark"
        assert artifact.figure_spec.dimensions.width == 900.0
        assert isinstance(artifact.preparation, PreparedFigure)
        assert artifact.figure_spec is artifact.preparation.spec

    def test_legend_labels_applied_during_preparation(
        self, sample_data: pd.DataFrame, bar_config: dict[str, Any]
    ) -> None:
        bar_config["legend_labels"] = {"ipc": "Renamed"}
        artifact = _artifact(sample_data, bar_config)
        assert isinstance(artifact.figure, go.Figure)
        assert cast(go.Bar, artifact.figure.data[0]).name == "Renamed"
        assert artifact.trace_result is not None
        assert artifact.trace_result.traces[0].name == "Renamed"


# 2. ConfigSpecBuilder ↔ Plotly layout agreement


class TestConfigSpecRoundTrip:
    """Direct typed styling agrees with a measured prepared native artifact."""

    def _build_spec_fig(self, config: dict[str, Any]) -> go.Figure:
        """Build a figure using ConfigSpecBuilder + FigureSpecToPlotly."""
        spec = resolve_config(ConfigSpecBuilder.from_config(config, "bar"))
        fig = go.Figure()
        FigureSpecToPlotly.apply(spec, fig)
        return fig

    def _build_artifact_fig(self, config: dict[str, Any]) -> go.Figure:
        data = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 2.0]})
        artifact = _artifact(data, config)
        assert isinstance(artifact.figure, go.Figure)
        return artifact.figure

    def test_dimensions_match(self, bar_config: dict[str, Any]) -> None:
        """Width and height agree between both paths."""
        spec_fig = self._build_spec_fig(bar_config)
        app_fig = self._build_artifact_fig(bar_config)

        assert spec_fig.layout.width == app_fig.layout.width
        assert spec_fig.layout.height == app_fig.layout.height

    def test_margins_match(self, bar_config: dict[str, Any]) -> None:
        """Margins agree between both paths."""
        spec_fig = self._build_spec_fig(bar_config)
        app_fig = self._build_artifact_fig(bar_config)

        sm = spec_fig.layout.margin
        am = app_fig.layout.margin
        assert sm.t == am.t
        assert sm.b == am.b
        assert sm.l == am.l
        assert sm.r == am.r

    def test_backgrounds_match(self, bar_config: dict[str, Any]) -> None:
        """Background colors agree."""
        spec_fig = self._build_spec_fig(bar_config)
        app_fig = self._build_artifact_fig(bar_config)

        assert spec_fig.layout.paper_bgcolor == app_fig.layout.paper_bgcolor
        assert spec_fig.layout.plot_bgcolor == app_fig.layout.plot_bgcolor

    def test_title_matches(self, bar_config: dict[str, Any]) -> None:
        """Title text and font size agree."""
        spec_fig = self._build_spec_fig(bar_config)
        app_fig = self._build_artifact_fig(bar_config)

        assert spec_fig.layout.title.text == app_fig.layout.title.text
        assert spec_fig.layout.title.font.size == app_fig.layout.title.font.size

    def test_bargap_matches(self, bar_config: dict[str, Any]) -> None:
        """Bar gap settings agree."""
        spec_fig = self._build_spec_fig(bar_config)
        app_fig = self._build_artifact_fig(bar_config)

        assert spec_fig.layout.bargap == app_fig.layout.bargap


# 3. Spec survives serialization


class TestSpecSerialization:
    """FigureConfig from config round-trips through to_dict / from_dict."""

    def test_round_trip(self, bar_config: dict[str, Any]) -> None:
        spec = resolve_config(ConfigSpecBuilder.from_config(bar_config, "bar"))
        data = spec.to_dict()
        restored = FigureConfig.from_dict(data)

        assert restored.title == spec.title
        assert restored.dimensions.width == spec.dimensions.width
        assert restored.dimensions.height == spec.dimensions.height
        assert restored.typography.font_size_title == spec.typography.font_size_title
        assert len(restored.legends) == len(spec.legends)

    def test_spec_contains_all_config_values(self, bar_config: dict[str, Any]) -> None:
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


class TestMultiTypeEngineIntegration:
    """Native trace families come from real registered neutral strategies."""

    def test_bar_and_line_produce_different_figures(self, sample_data: pd.DataFrame) -> None:
        config: dict[str, Any] = dict(_BASE_CONFIG)
        bar = _artifact(sample_data, config, "bar")
        line = _artifact(sample_data, config, "line")
        assert isinstance(bar.figure, go.Figure) and isinstance(line.figure, go.Figure)
        bar_fig, line_fig = bar.figure, line.figure
        assert cast(go.Bar, bar_fig.data[0]).type == "bar"
        assert cast(go.Scatter, line_fig.data[0]).type == "scatter"
        assert list(cast(go.Bar, bar_fig.data[0]).y) == list(cast(go.Scatter, line_fig.data[0]).y)
        assert list(cast(go.Bar, bar_fig.data[0]).y) == [1.24, 1.58, 0.87, 1.41]
        assert bar_fig.layout.title.text == "IPC by Benchmark"
        assert line_fig.layout.title.text == "IPC by Benchmark"
