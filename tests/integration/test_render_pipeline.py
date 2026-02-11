"""Integration tests for the figure rendering pipeline.

Covers Scenarios #1 (FigureEngine E2E) and #14 (Full Parse→Render→Export chain).

Tests:
    - FigureEngine.build() with all 8 plot types using real data
    - StyleApplicator applied through the engine
    - Plot → Figure → Export chain (MatplotlibConverter)
    - Legend label overrides
    - Config variations (error bars, color grouping, etc.)
"""

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.core.application_api import ApplicationAPI
from src.web.figures.engine import FigureEngine
from src.web.pages.ui.plotting.export.converters.impl.matplotlib_converter import (
    MatplotlibConverter,
)
from src.web.pages.ui.plotting.export.presets.preset_schema import (
    ExportResult,
    LaTeXPreset,
)
from src.web.pages.ui.plotting.plot_factory import PlotFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_preset() -> LaTeXPreset:
    """Create a minimal LaTeXPreset for testing export."""
    return LaTeXPreset(
        width_inches=3.5,
        height_inches=2.625,
        font_family="sans-serif",
        font_size_base=9,
        font_size_title=10,
        font_size_xlabel=8,
        font_size_ylabel=8,
        font_size_legend=7,
        font_size_ticks=7,
        font_size_annotations=7,
        bold_title=False,
        bold_xlabel=False,
        bold_ylabel=False,
        bold_legend=False,
        bold_ticks=False,
        bold_annotations=True,
        line_width=1.0,
        marker_size=4,
        dpi=150,
        legend_columnspacing=2.0,
        legend_handletextpad=0.8,
        legend_labelspacing=0.5,
        legend_handlelength=2.0,
        legend_handleheight=0.7,
        legend_borderpad=0.4,
        legend_borderaxespad=0.5,
        ylabel_pad=10.0,
        ylabel_y_position=0.5,
        xtick_pad=5.0,
        ytick_pad=5.0,
        group_label_offset=-0.12,
        group_label_alternate=True,
        xaxis_margin=0.02,
        bar_width_scale=1.0,
        xtick_rotation=45.0,
        xtick_ha="right",
        xtick_offset=0.0,
        group_separator=False,
        group_separator_style="dashed",
        group_separator_color="gray",
    )


# ===========================================================================
# Test Class 1: FigureEngine integration with all plot types
# ===========================================================================


class TestFigureEngineIntegration:
    """Test FigureEngine.build() produces valid figures for every plot type."""

    def test_build_bar_plot(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
        bar_config: Dict[str, Any],
    ) -> None:
        """Bar plot: engine.build() returns a valid go.Figure with traces."""
        fig: go.Figure = figure_engine.build("bar", rich_sample_data, bar_config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.layout.title is not None

    def test_build_line_plot(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
        line_config: Dict[str, Any],
    ) -> None:
        """Line plot: engine.build() returns a valid go.Figure."""
        fig: go.Figure = figure_engine.build("line", rich_sample_data, line_config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_build_scatter_plot(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
        scatter_config: Dict[str, Any],
    ) -> None:
        """Scatter plot: engine.build() returns a valid go.Figure."""
        fig: go.Figure = figure_engine.build("scatter", rich_sample_data, scatter_config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_build_grouped_bar_plot(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
        grouped_bar_config: Dict[str, Any],
    ) -> None:
        """Grouped bar plot: engine.build() returns a valid go.Figure."""
        fig: go.Figure = figure_engine.build("grouped_bar", rich_sample_data, grouped_bar_config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_build_stacked_bar_plot(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """Stacked bar plot: engine.build() with y_columns list."""
        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y_columns": ["system.cpu.ipc", "system.cpu.numCycles"],
            "title": "Stacked Metrics",
            "xlabel": "Benchmark",
            "ylabel": "Value",
            "legend_title": "Metric",
        }
        fig: go.Figure = figure_engine.build("stacked_bar", rich_sample_data, config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2  # At least one trace per y_column

    def test_build_histogram_plot(
        self,
        figure_engine: FigureEngine,
    ) -> None:
        """Histogram plot: engine.build() with bucket columns."""
        # Histogram expects columns like "var..bucket_name" (gem5 format)
        histogram_data = pd.DataFrame(
            {
                "benchmark_name": ["mcf", "omnetpp", "xalancbmk"],
                "system.cpu.ipc..0-1": [10, 20, 15],
                "system.cpu.ipc..1-2": [30, 25, 35],
                "system.cpu.ipc..2-3": [20, 15, 10],
            }
        )
        config: Dict[str, Any] = {
            "histogram_variable": "system.cpu.ipc",
            "title": "IPC Distribution",
            "xlabel": "IPC",
            "ylabel": "Count",
        }
        fig: go.Figure = figure_engine.build("histogram", histogram_data, config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_build_dual_axis_bar_dot_plot(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """Dual-axis bar-dot plot: engine.build() with y_bar and y_dot."""
        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y_bar": "system.cpu.numCycles",
            "y_dot": "system.cpu.ipc",
            "title": "Cycles (bar) vs IPC (dot)",
            "xlabel": "Benchmark",
            "ylabel_bar": "Cycles",
            "ylabel_dot": "IPC",
        }
        fig: go.Figure = figure_engine.build("dual_axis_bar_dot", rich_sample_data, config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2  # Bar + dot traces

    def test_build_unregistered_type_raises_key_error(
        self, figure_engine: FigureEngine, rich_sample_data: pd.DataFrame
    ) -> None:
        """Engine raises KeyError for unregistered plot type."""
        with pytest.raises(KeyError, match="No figure creator registered"):
            figure_engine.build("nonexistent", rich_sample_data, {})

    def test_all_plot_types_registered(self, figure_engine: FigureEngine) -> None:
        """Fixture registers all PlotFactory types in the engine."""
        factory_types: list[str] = PlotFactory.get_available_plot_types()
        engine_types: list[str] = figure_engine.registered_types

        for pt in factory_types:
            assert pt in engine_types, f"Plot type '{pt}' not in engine"


# ===========================================================================
# Test Class 2: StyleApplicator integration
# ===========================================================================


class TestStyleApplicatorIntegration:
    """Test StyleApplicator through the FigureEngine pipeline."""

    def test_styles_applied_to_bar_figure(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """StyleApplicator modifies layout dimensions when config has them."""
        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Styled Bar",
            "xlabel": "X",
            "ylabel": "Y",
            "width": 800,
            "height": 500,
        }
        fig: go.Figure = figure_engine.build("bar", rich_sample_data, config)

        assert fig.layout.width == 800
        assert fig.layout.height == 500

    def test_bar_gap_applied(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """StyleApplicator applies bargap config to layout."""
        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Bar Gap Test",
            "xlabel": "X",
            "ylabel": "Y",
            "bargap": 0.3,
        }
        fig: go.Figure = figure_engine.build("bar", rich_sample_data, config)

        assert fig.layout.bargap == 0.3

    def test_background_colors_applied(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """StyleApplicator applies background color overrides."""
        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Background Test",
            "xlabel": "X",
            "ylabel": "Y",
            "plot_bgcolor": "#f0f0f0",
            "paper_bgcolor": "#ffffff",
        }
        fig: go.Figure = figure_engine.build("bar", rich_sample_data, config)

        assert fig.layout.plot_bgcolor == "#f0f0f0"
        assert fig.layout.paper_bgcolor == "#ffffff"

    def test_legend_labels_override(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """FigureEngine._apply_legend_labels renames traces in final figure."""
        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "color": "config_description",
            "title": "Legend Override",
            "xlabel": "X",
            "ylabel": "Y",
            "legend_labels": {
                "baseline": "Base",
                "optimized": "Opt",
                "aggressive": "Agg",
            },
        }
        fig: go.Figure = figure_engine.build("bar", rich_sample_data, config)

        trace_names: list[str] = [t.name for t in fig.data if t.name]
        # Original names should be replaced
        assert "baseline" not in trace_names
        assert "optimized" not in trace_names
        # New names should be present
        for name in trace_names:
            assert name in {"Base", "Opt", "Agg"}, f"Unexpected trace name: {name}"


# ===========================================================================
# Test Class 3: Plot → Figure → Export chain
# ===========================================================================


class TestPlotToExportChain:
    """Test the full chain: PlotFactory → create_figure → convert to PDF."""

    def test_bar_plot_to_pdf_export(
        self, rich_sample_data: pd.DataFrame, bar_config: Dict[str, Any]
    ) -> None:
        """Create a bar plot, generate figure, export to PDF — end to end."""
        # 1. Create plot via factory
        plot = PlotFactory.create_plot("bar", plot_id=1, name="Export Test")

        # 2. Generate figure
        fig: go.Figure = plot.create_figure(rich_sample_data, bar_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

        # 3. Export to PDF
        preset: LaTeXPreset = _make_minimal_preset()
        converter = MatplotlibConverter(preset)
        result: ExportResult = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["data"] is not None
        assert isinstance(result["data"], bytes)
        assert len(result["data"]) > 0
        assert result["format"] == "pdf"
        assert result["error"] is None

    def test_line_plot_to_pdf_export(
        self, rich_sample_data: pd.DataFrame, line_config: Dict[str, Any]
    ) -> None:
        """Line plot → figure → PDF export."""
        plot = PlotFactory.create_plot("line", plot_id=2, name="Line Export")
        fig: go.Figure = plot.create_figure(rich_sample_data, line_config)
        assert isinstance(fig, go.Figure)

        preset: LaTeXPreset = _make_minimal_preset()
        converter = MatplotlibConverter(preset)
        result: ExportResult = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["data"] is not None
        assert len(result["data"]) > 0

    def test_grouped_bar_to_pdf_export(
        self,
        rich_sample_data: pd.DataFrame,
        grouped_bar_config: Dict[str, Any],
    ) -> None:
        """Grouped bar → figure → PDF export."""
        plot = PlotFactory.create_plot("grouped_bar", plot_id=3, name="Grouped Export")
        fig: go.Figure = plot.create_figure(rich_sample_data, grouped_bar_config)
        assert isinstance(fig, go.Figure)

        preset: LaTeXPreset = _make_minimal_preset()
        converter = MatplotlibConverter(preset)
        result: ExportResult = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["data"] is not None

    def test_scatter_to_pdf_export(
        self,
        rich_sample_data: pd.DataFrame,
        scatter_config: Dict[str, Any],
    ) -> None:
        """Scatter → figure → PDF export."""
        plot = PlotFactory.create_plot("scatter", plot_id=4, name="Scatter Export")
        fig: go.Figure = plot.create_figure(rich_sample_data, scatter_config)
        assert isinstance(fig, go.Figure)

        preset: LaTeXPreset = _make_minimal_preset()
        converter = MatplotlibConverter(preset)
        result: ExportResult = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["data"] is not None

    def test_styled_figure_to_pdf_export(
        self,
        figure_engine: FigureEngine,
        rich_sample_data: pd.DataFrame,
        bar_config: Dict[str, Any],
    ) -> None:
        """Full engine (create + style) → PDF export."""
        styled_config: Dict[str, Any] = {
            **bar_config,
            "width": 700,
            "height": 400,
            "plot_bgcolor": "white",
            "paper_bgcolor": "white",
        }
        fig: go.Figure = figure_engine.build("bar", rich_sample_data, styled_config)

        preset: LaTeXPreset = _make_minimal_preset()
        converter = MatplotlibConverter(preset)
        result: ExportResult = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["data"] is not None
        assert len(result["data"]) > 100  # Non-trivial PDF


# ===========================================================================
# Test Class 4: Full data flow — load → transform → render → export
# ===========================================================================


class TestFullDataToRenderE2E:
    """Test E2E: load data → apply shapers → create figure → export."""

    def test_load_transform_render_export(
        self,
        loaded_facade: ApplicationAPI,
        bar_config: Dict[str, Any],
    ) -> None:
        """Full E2E: API data → shaper pipeline → figure → PDF."""
        api: ApplicationAPI = loaded_facade

        # 1. Verify data is loaded
        data: pd.DataFrame = api.state_manager.get_data()
        assert data is not None
        assert len(data) > 0

        # 2. Apply shapers (column select + sort)
        from src.core.services.shapers.factory import ShaperFactory

        col_shaper = ShaperFactory.create_shaper(
            "columnSelector",
            {"columns": ["benchmark_name", "config_description", "system.cpu.ipc"]},
        )
        shaped_data: pd.DataFrame = col_shaper(data)

        sort_shaper = ShaperFactory.create_shaper(
            "sort",
            {
                "order_dict": {
                    "benchmark_name": ["mcf", "omnetpp", "xalancbmk"],
                },
            },
        )
        shaped_data = sort_shaper(shaped_data)

        assert list(shaped_data.columns) == [
            "benchmark_name",
            "config_description",
            "system.cpu.ipc",
        ]
        # Sort orders categorically: mcf, omnetpp, xalancbmk
        benchmarks = shaped_data["benchmark_name"].unique().tolist()
        assert benchmarks == ["mcf", "omnetpp", "xalancbmk"]

        # 3. Create figure
        plot = PlotFactory.create_plot("bar", plot_id=1, name="E2E Plot")
        fig: go.Figure = plot.create_figure(shaped_data, bar_config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

        # 4. Export
        preset: LaTeXPreset = _make_minimal_preset()
        converter = MatplotlibConverter(preset)
        result: ExportResult = converter.convert(fig, "pdf")

        assert result["success"] is True
        assert result["data"] is not None
        assert len(result["data"]) > 100

    def test_normalize_then_grouped_bar_render(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Normalize → grouped bar: a common scientific analysis pattern."""
        from src.core.services.shapers.factory import ShaperFactory

        api: ApplicationAPI = loaded_facade
        data: pd.DataFrame = api.state_manager.get_data()
        assert data is not None

        # 1. Column select
        col_shaper = ShaperFactory.create_shaper(
            "columnSelector",
            {
                "columns": [
                    "benchmark_name",
                    "config_description",
                    "system.cpu.ipc",
                ]
            },
        )
        result_data: pd.DataFrame = col_shaper(data)

        # 2. Normalize IPC against baseline
        norm_shaper = ShaperFactory.create_shaper(
            "normalize",
            {
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

        # 3. Render grouped bar
        config: Dict[str, Any] = {
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
        assert len(fig.data) >= 2

    def test_mean_aggregation_then_bar_render(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Mean aggregation → bar plot: geometric mean across benchmarks."""
        from src.core.services.shapers.factory import ShaperFactory

        api: ApplicationAPI = loaded_facade
        data: pd.DataFrame = api.state_manager.get_data()
        assert data is not None

        # 1. Column select
        col_shaper = ShaperFactory.create_shaper(
            "columnSelector",
            {
                "columns": [
                    "benchmark_name",
                    "config_description",
                    "system.cpu.ipc",
                ]
            },
        )
        result_data: pd.DataFrame = col_shaper(data)

        # 2. Compute mean per config
        mean_shaper = ShaperFactory.create_shaper(
            "mean",
            {
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

        # 3. Render bar
        config: Dict[str, Any] = {
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
        assert len(fig.data) > 0
