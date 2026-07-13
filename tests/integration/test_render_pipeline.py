"""Integration tests for the figure rendering pipeline.

Covers Scenario #1 (Figure rendering E2E).

Tests:
    - PlotFactory + StyleApplicator with all 8 plot types using real data
    - StyleApplicator applied inline
    - Legend label overrides
    - Config variations (error bars, color grouping, etc.)
"""

from typing import Any, cast

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.core.application_api import ApplicationAPI
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

# Helper: build figure inline using PlotFactory + StyleApplicator


def _build_figure(
    plot_type: str,
    data: pd.DataFrame,
    config: dict[str, Any],
    legend_labels: dict[str, str] | None = None,
) -> go.Figure:
    """Build a figure using PlotFactory inline (replaces FigureEngine)."""
    plot = PlotFactory.create_plot(plot_type, plot_id=99, name=f"test_{plot_type}")
    styler = StyleApplicator(plot_type)
    fig: go.Figure = plot.create_figure(data, config)
    fig = styler.apply_styles(fig, config)
    if legend_labels:
        fig.for_each_trace(lambda t: t.update(name=legend_labels.get(t.name, t.name)))
    return fig


# Test Class 1: Render pipeline integration with all plot types


class TestFigureEngineIntegration:
    """Test PlotFactory + StyleApplicator produces valid figures for every plot type."""

    def test_build_bar_plot(
        self,
        rich_sample_data: pd.DataFrame,
        bar_config: dict[str, Any],
    ) -> None:
        """Bar plot: inline build returns a valid go.Figure with traces."""
        fig: go.Figure = _build_figure("bar", rich_sample_data, bar_config)

        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) > 0
        assert fig.layout.title is not None

    def test_build_line_plot(
        self,
        rich_sample_data: pd.DataFrame,
        line_config: dict[str, Any],
    ) -> None:
        """Line plot: inline build returns a valid go.Figure."""
        fig: go.Figure = _build_figure("line", rich_sample_data, line_config)

        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) > 0

    def test_build_scatter_plot(
        self,
        rich_sample_data: pd.DataFrame,
        scatter_config: dict[str, Any],
    ) -> None:
        """Scatter plot: inline build returns a valid go.Figure."""
        fig: go.Figure = _build_figure("scatter", rich_sample_data, scatter_config)

        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) > 0

    def test_build_grouped_bar_plot(
        self,
        rich_sample_data: pd.DataFrame,
        grouped_bar_config: dict[str, Any],
    ) -> None:
        """Grouped bar plot: inline build returns a valid go.Figure."""
        fig: go.Figure = _build_figure("grouped_bar", rich_sample_data, grouped_bar_config)

        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) > 0

    def test_build_stacked_bar_plot(
        self,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """Stacked bar plot: inline build with y_columns list."""
        config: dict[str, Any] = {
            "x": "benchmark_name",
            "y_columns": ["system.cpu.ipc", "system.cpu.numCycles"],
            "title": "Stacked Metrics",
            "xlabel": "Benchmark",
            "ylabel": "Value",
            "legend_title": "Metric",
        }
        fig: go.Figure = _build_figure("stacked_bar", rich_sample_data, config)

        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) >= 2  # At least one trace per y_column

    def test_build_histogram_plot(
        self,
    ) -> None:
        """Histogram plot: inline build with bucket columns."""
        # Histogram expects columns like "var..bucket_name" (gem5 format)
        histogram_data = pd.DataFrame(
            {
                "benchmark_name": ["mcf", "omnetpp", "xalancbmk"],
                "system.cpu.ipc..0-1": [10, 20, 15],
                "system.cpu.ipc..1-2": [30, 25, 35],
                "system.cpu.ipc..2-3": [20, 15, 10],
            }
        )
        config: dict[str, Any] = {
            "histogram_variable": "system.cpu.ipc",
            "title": "IPC Distribution",
            "xlabel": "IPC",
            "ylabel": "Count",
        }
        fig: go.Figure = _build_figure("histogram", histogram_data, config)

        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) > 0

    def test_build_dual_axis_bar_dot_plot(
        self,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """Dual-axis bar-dot plot: inline build with y_bar and y_dot."""
        config: dict[str, Any] = {
            "x": "benchmark_name",
            "y_bar": "system.cpu.numCycles",
            "y_dot": "system.cpu.ipc",
            "title": "Cycles (bar) vs IPC (dot)",
            "xlabel": "Benchmark",
            "ylabel_bar": "Cycles",
            "ylabel_dot": "IPC",
        }
        fig: go.Figure = _build_figure("dual_axis_bar_dot", rich_sample_data, config)

        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) >= 2  # Bar + dot traces

    def test_build_unregistered_type_raises_value_error(
        self, rich_sample_data: pd.DataFrame
    ) -> None:
        """PlotFactory raises ValueError for unregistered plot type."""
        with pytest.raises(ValueError):
            PlotFactory.create_plot("nonexistent", plot_id=1, name="Bad")

    def test_all_plot_types_available(self) -> None:
        """PlotFactory has all expected plot types registered."""
        factory_types: list[str] = PlotFactory.get_available_plot_types()
        assert len(factory_types) > 0
        assert "bar" in factory_types
        assert "line" in factory_types


# Test Class 2: FigureConfig styling integration


class TestFigureSpecStylingIntegration:
    """Test FigureConfig styling through the inline pipeline."""

    def test_styles_applied_to_bar_figure(
        self,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """FigureConfig pipeline modifies layout dimensions when config has them."""
        config: dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Styled Bar",
            "xlabel": "X",
            "ylabel": "Y",
            "width": 800,
            "height": 500,
        }
        fig: go.Figure = _build_figure("bar", rich_sample_data, config)

        assert fig.layout.width == 800
        assert fig.layout.height == 500

    def test_bar_gap_applied(
        self,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """FigureConfig pipeline applies bargap config to layout."""
        config: dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Bar Gap Test",
            "xlabel": "X",
            "ylabel": "Y",
            "bargap": 0.3,
        }
        fig: go.Figure = _build_figure("bar", rich_sample_data, config)

        assert fig.layout.bargap == 0.3

    def test_background_colors_applied(
        self,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """FigureConfig pipeline applies background color overrides."""
        config: dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Background Test",
            "xlabel": "X",
            "ylabel": "Y",
            "plot_bgcolor": "#f0f0f0",
            "paper_bgcolor": "#ffffff",
        }
        fig: go.Figure = _build_figure("bar", rich_sample_data, config)

        assert fig.layout.plot_bgcolor == "#f0f0f0"
        assert fig.layout.paper_bgcolor == "#ffffff"

    def test_legend_labels_override(
        self,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """Legend labels are renamed in final figure via inline application."""
        legend_labels: dict[str, str] = {
            "baseline": "Base",
            "optimized": "Opt",
            "aggressive": "Agg",
        }
        config: dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "color": "config_description",
            "title": "Legend Override",
            "xlabel": "X",
            "ylabel": "Y",
        }
        fig: go.Figure = _build_figure("bar", rich_sample_data, config, legend_labels=legend_labels)

        trace_names: list[str] = [
            cast(str, cast(go.Bar, t).name) for t in list(fig.data) if cast(go.Bar, t).name
        ]
        # Original names should be replaced
        assert "baseline" not in trace_names
        assert "optimized" not in trace_names
        # New names should be present
        for name in trace_names:
            assert name in {"Base", "Opt", "Agg"}, f"Unexpected trace name: {name}"


# Test Class 3: Full data flow — load → transform → render


class TestFullDataToRenderE2E:
    """Test E2E: load data → apply shapers → create figure."""

    def test_normalize_then_grouped_bar_render(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Normalize → grouped bar: a common scientific analysis pattern."""
        from src.core.services.shapers.factory import ShaperFactory

        api: ApplicationAPI = loaded_facade
        data_or_none = api.state_manager.get_data()
        assert data_or_none is not None
        data: pd.DataFrame = data_or_none

        # Column select
        col_shaper = ShaperFactory.create_shaper(
            "columnSelector",
            {  # type: ignore
                "columns": [
                    "benchmark_name",
                    "config_description",
                    "system.cpu.ipc",
                ]
            },
        )
        result_data: pd.DataFrame = col_shaper(data)

        # Normalize IPC against baseline
        norm_shaper = ShaperFactory.create_shaper(
            "normalize",
            {  # type: ignore
                "normalizeVars": ["system.cpu.ipc"],
                "normalizerColumn": "config_description",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark_name"],
            },
        )
        result_data = norm_shaper(result_data)

        # After normalization, baseline should be ~1.0
        baseline_rows = result_data[result_data["config_description"] == "baseline"]
        for val in baseline_rows["system.cpu.ipc"]:
            assert abs(val - 1.0) < 1e-6, f"Baseline not normalized: {val}"

        # Render grouped bar
        config: dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "group": "config_description",
            "title": "Normalized IPC Speedup",
            "xlabel": "Benchmark",
            "ylabel": "Normalized IPC",
        }
        plot = PlotFactory.create_plot("grouped_bar", plot_id=10, name="Norm Plot")
        fig: go.Figure = plot.create_figure(result_data, config)

        assert isinstance(fig, go.Figure)
        # Should have traces for each config_description
        assert len(list(fig.data)) >= 2

    def test_mean_aggregation_then_bar_render(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Mean aggregation → bar plot: geometric mean across benchmarks."""
        from src.core.services.shapers.factory import ShaperFactory

        api: ApplicationAPI = loaded_facade
        data_or_none = api.state_manager.get_data()
        assert data_or_none is not None
        data: pd.DataFrame = data_or_none

        # Column select
        col_shaper = ShaperFactory.create_shaper(
            "columnSelector",
            {  # type: ignore
                "columns": [
                    "benchmark_name",
                    "config_description",
                    "system.cpu.ipc",
                ]
            },
        )
        result_data: pd.DataFrame = col_shaper(data)

        # Compute mean per config
        mean_shaper = ShaperFactory.create_shaper(
            "mean",
            {  # type: ignore
                "meanVars": ["system.cpu.ipc"],
                "meanAlgorithm": "arithmean",
                "groupingColumns": ["config_description"],
                "replacingColumn": "benchmark_name",
            },
        )
        result_data = mean_shaper(result_data)

        # Mean should add rows with benchmark_name = "arithmean"
        mean_rows = result_data[result_data["benchmark_name"] == "arithmean"]
        assert len(mean_rows) > 0, "No mean rows added"

        # Render bar
        config: dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "color": "config_description",
            "title": "IPC with Mean",
            "xlabel": "Benchmark",
            "ylabel": "IPC",
        }
        plot = PlotFactory.create_plot("bar", plot_id=11, name="Mean Plot")
        fig: go.Figure = plot.create_figure(result_data, config)

        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) > 0
