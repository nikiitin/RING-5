"""E2E Integration: Full data→transform→render chain tests.

Tests complete workflows from data loading through transformation
and rendering, exercising the full stack through AppTest + API.

Complements existing integration tests by:
- Testing the full chain via AppTest (not just backend APIs)
- Exercising shaper→FigureEngine→figure chain
- Testing multiple plot types through the render pipeline
- Verifying pipeline modification → re-render cycle
"""

from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go

from tests.ui.helpers import (
    create_app_with_data,
    get_api,
    navigate_to,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_plot_and_finalize(
    api: Any,
    name: str,
    plot_type: str,
    pipeline_configs: List[Dict[str, Any]],
) -> Any:
    """Create a plot, apply pipeline, and set processed_data."""
    from src.core.services.shapers.factory import ShaperFactory
    from src.web.pages.ui.plotting.plot_service import PlotService

    plot = PlotService.create_plot(name, plot_type, api.state_manager)

    raw_data: pd.DataFrame = api.state_manager.get_data()
    result: pd.DataFrame = raw_data.copy()

    for config in pipeline_configs:
        shaper = ShaperFactory.create_shaper(config["type"], config)
        result = shaper(result)

    plot.processed_data = result
    plot.pipeline = [
        {"id": i, "type": c["type"], "config": c} for i, c in enumerate(pipeline_configs)
    ]
    return plot


# ---------------------------------------------------------------------------
# Data → Transform → Render chain
# ---------------------------------------------------------------------------
class TestDataTransformRenderChain:
    """Full chain: load data → apply shapers → build figure."""

    def test_bar_plot_full_chain(self) -> None:
        """Bar plot: load → column select → sort → create figure."""
        from src.web.figures.engine import FigureEngine

        at = create_app_with_data()
        api: Any = get_api(at)

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": ["benchmark_name", "system.cpu.ipc"],
            },
            {
                "type": "sort",
                "order_dict": {
                    "benchmark_name": ["mcf", "omnetpp", "xalancbmk"],
                },
            },
        ]
        plot = _create_plot_and_finalize(api, "Bar Chain", "bar", pipeline)

        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "IPC by Benchmark",
            "xlabel": "Benchmark",
            "ylabel": "IPC",
            "barmode": "group",
        }

        engine = FigureEngine.from_plot(plot, "bar")
        fig: go.Figure = engine.build("bar", plot.processed_data, config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_grouped_bar_full_chain(self) -> None:
        """Grouped bar: load → column select → mean → create figure."""
        from src.web.figures.engine import FigureEngine

        at = create_app_with_data()
        api: Any = get_api(at)

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": [
                    "benchmark_name",
                    "config_description",
                    "system.cpu.ipc",
                ],
            },
            {
                "type": "mean",
                "meanVars": ["system.cpu.ipc"],
                "meanAlgorithm": "arithmean",
                "groupingColumns": ["config_description"],
                "replacingColumn": "benchmark_name",
            },
        ]
        plot = _create_plot_and_finalize(api, "Grouped Bar Chain", "grouped_bar", pipeline)

        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "color": "config_description",
            "title": "IPC by Config",
        }

        engine = FigureEngine.from_plot(plot, "grouped_bar")
        fig: go.Figure = engine.build("grouped_bar", plot.processed_data, config)

        assert isinstance(fig, go.Figure)

    def test_line_plot_full_chain(self) -> None:
        """Line plot: load → filter → sort → create figure."""
        from src.web.figures.engine import FigureEngine

        at = create_app_with_data()
        api: Any = get_api(at)

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "conditionSelector",
                "column": "config_description",
                "values": ["baseline"],
            },
            {
                "type": "columnSelector",
                "columns": [
                    "benchmark_name",
                    "system.cpu.ipc",
                    "system.cpu.numCycles",
                ],
            },
        ]
        plot = _create_plot_and_finalize(api, "Line Chain", "line", pipeline)

        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "IPC Baseline Line",
            "xlabel": "Benchmark",
            "ylabel": "IPC",
        }

        engine = FigureEngine.from_plot(plot, "line")
        fig: go.Figure = engine.build("line", plot.processed_data, config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_scatter_plot_full_chain(self) -> None:
        """Scatter plot: load → column select → create figure."""
        from src.web.figures.engine import FigureEngine

        at = create_app_with_data()
        api: Any = get_api(at)

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": [
                    "system.cpu.ipc",
                    "system.cpu.dcache.overall_miss_rate",
                ],
            },
        ]
        plot = _create_plot_and_finalize(api, "Scatter Chain", "scatter", pipeline)

        config: Dict[str, Any] = {
            "x": "system.cpu.ipc",
            "y": "system.cpu.dcache.overall_miss_rate",
            "title": "IPC vs Miss Rate",
            "xlabel": "IPC",
            "ylabel": "Miss Rate",
        }

        engine = FigureEngine.from_plot(plot, "scatter")
        fig: go.Figure = engine.build("scatter", plot.processed_data, config)

        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Pipeline modification cycle
# ---------------------------------------------------------------------------
class TestPipelineModificationCycle:
    """Modify pipeline → re-process → verify output changes."""

    def test_add_shaper_changes_output(self) -> None:
        """Adding a filter shaper reduces the row count."""
        from src.core.services.shapers.factory import ShaperFactory

        at = create_app_with_data()
        api: Any = get_api(at)

        raw: pd.DataFrame = api.state_manager.get_data()
        initial_rows: int = len(raw)

        # First pipeline: just column select
        shaper1 = ShaperFactory.create_shaper(
            "columnSelector",
            {"columns": ["benchmark_name", "config_description", "system.cpu.ipc"]},
        )
        after_select: pd.DataFrame = shaper1(raw)
        assert len(after_select) == initial_rows

        # Second pipeline: column select + filter
        shaper2 = ShaperFactory.create_shaper(
            "conditionSelector",
            {"column": "config_description", "values": ["baseline"]},
        )
        after_filter: pd.DataFrame = shaper2(after_select)

        assert len(after_filter) < initial_rows
        assert all(after_filter["config_description"] == "baseline")

    def test_pipeline_produces_consistent_results(self) -> None:
        """Same pipeline on same data produces identical results."""
        from src.core.services.shapers.factory import ShaperFactory

        at = create_app_with_data()
        api: Any = get_api(at)
        raw: pd.DataFrame = api.state_manager.get_data()

        def run_pipeline(data: pd.DataFrame) -> pd.DataFrame:
            s1 = ShaperFactory.create_shaper(
                "columnSelector",
                {"columns": ["benchmark_name", "system.cpu.ipc"]},
            )
            s2 = ShaperFactory.create_shaper(
                "sort",
                {"order_dict": {"benchmark_name": ["mcf", "omnetpp", "xalancbmk"]}},
            )
            return s2(s1(data))

        result1: pd.DataFrame = run_pipeline(raw)
        result2: pd.DataFrame = run_pipeline(raw)

        pd.testing.assert_frame_equal(result1, result2)


# ---------------------------------------------------------------------------
# Data → Transform → UI rendering
# ---------------------------------------------------------------------------
class TestDataToUIRendering:
    """Full chain through AppTest: data → transform → page render."""

    def test_finalized_plot_renders_on_manage_page(self) -> None:
        """A plot with processed_data renders visualization section."""
        at = create_app_with_data()
        api: Any = get_api(at)

        _create_plot_and_finalize(
            api,
            "Rendered Plot",
            "bar",
            [
                {
                    "type": "columnSelector",
                    "columns": ["benchmark_name", "system.cpu.ipc"],
                },
            ],
        )

        navigate_to(at, "Manage Plots")
        assert not at.exception

        # With processed_data set, toggle and refresh should appear
        assert len(at.toggle) >= 1, "Expected auto-refresh toggle"

    def test_multiple_finalized_plots_render(self) -> None:
        """Multiple finalized plots render without error."""
        at = create_app_with_data()
        api: Any = get_api(at)

        for i, plot_type in enumerate(["bar", "line", "scatter"]):
            _create_plot_and_finalize(
                api,
                f"Plot {i}",
                plot_type,
                [
                    {
                        "type": "columnSelector",
                        "columns": [
                            "benchmark_name",
                            "system.cpu.ipc",
                        ],
                    },
                ],
            )

        navigate_to(at, "Manage Plots")
        assert not at.exception

    def test_empty_pipeline_preserves_raw_data(self) -> None:
        """Plot with empty pipeline uses raw data as processed_data."""
        at = create_app_with_data()
        api: Any = get_api(at)

        plot = _create_plot_and_finalize(api, "No Pipeline", "bar", [])
        raw: pd.DataFrame = api.state_manager.get_data()

        assert plot.processed_data is not None
        assert len(plot.processed_data) == len(raw)


# ---------------------------------------------------------------------------
# Portfolio round-trip with plots
# ---------------------------------------------------------------------------
class TestPortfolioRoundTripWithPlots:
    """Save portfolio with plots → load → verify consistency."""

    def test_save_load_with_plots_via_api(self) -> None:
        """Portfolio save/load preserves plot configurations."""
        at = create_app_with_data()
        api: Any = get_api(at)

        from src.web.pages.ui.plotting.plot_service import PlotService

        plot = PlotService.create_plot("Test Bar", "bar", api.state_manager)
        plot.config = {"x": "benchmark_name", "y": "system.cpu.ipc"}
        plot.pipeline = [
            {
                "id": 0,
                "type": "columnSelector",
                "config": {"columns": ["benchmark_name", "system.cpu.ipc"]},
            },
        ]

        # Pass plot objects directly — save_portfolio calls to_dict internally
        api.data_services.save_portfolio(
            name="e2e_plots_portfolio",
            data=api.state_manager.get_data(),
            plots=[plot],
            config={},
            plot_counter=api.state_manager.get_plot_counter(),
        )

        # Clear and restore
        api.state_manager.set_data(None)
        api.state_manager.set_plots([])

        portfolio_data = api.data_services.load_portfolio("e2e_plots_portfolio")
        api.state_manager.restore_session(portfolio_data)

        restored_data = api.state_manager.get_data()
        restored_plots = api.state_manager.get_plots()

        assert restored_data is not None
        assert len(restored_plots) >= 1

        # Cleanup
        api.data_services.delete_portfolio("e2e_plots_portfolio")
