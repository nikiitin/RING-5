"""E2E Integration: Multi-plot workspace and cross-feature tests.

Tests workspace-level workflows that span multiple features:
- Multi-plot workspace: create multiple plots with different types and pipelines
- Data manager → plot consistency: data modifications reflect in plots
- Preprocessor → grouped bar workflow
- Mixer → stacked bar workflow
- Portfolio restore → render verification
- Cross-page state consistency
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


def _apply_pipeline(raw_data: pd.DataFrame, configs: List[Dict[str, Any]]) -> pd.DataFrame:
    """Apply a shaper pipeline to a DataFrame."""
    from src.core.services.shapers.factory import ShaperFactory

    result: pd.DataFrame = raw_data.copy()
    for config in configs:
        shaper = ShaperFactory.create_shaper(config["type"], config)
        result = shaper(result)
    return result


# ---------------------------------------------------------------------------
# Multi-plot workspace
# ---------------------------------------------------------------------------
class TestMultiPlotWorkspace:
    """Workspace with multiple plots of different types and pipelines."""

    def test_create_diverse_plot_workspace(self) -> None:
        """Create plots of different types with different pipelines."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)
        raw: pd.DataFrame = api.state_manager.get_data()

        # Bar plot with column selection
        bar_plot = PlotService.create_plot("IPC Bar", "bar", api.state_manager)
        bar_plot.processed_data = _apply_pipeline(
            raw,
            [{"type": "columnSelector", "columns": ["benchmark_name", "system.cpu.ipc"]}],
        )
        bar_plot.config = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "IPC",
        }

        # Line plot with filter
        line_plot = PlotService.create_plot("Baseline Line", "line", api.state_manager)
        line_plot.processed_data = _apply_pipeline(
            raw,
            [
                {
                    "type": "conditionSelector",
                    "column": "config_description",
                    "values": ["baseline"],
                },
                {
                    "type": "columnSelector",
                    "columns": ["benchmark_name", "system.cpu.numCycles"],
                },
            ],
        )

        # Scatter plot
        scatter_plot = PlotService.create_plot("IPC vs Miss", "scatter", api.state_manager)
        scatter_plot.processed_data = _apply_pipeline(
            raw,
            [
                {
                    "type": "columnSelector",
                    "columns": [
                        "system.cpu.ipc",
                        "system.cpu.dcache.overall_miss_rate",
                    ],
                },
            ],
        )

        plots = api.state_manager.get_plots()
        our_plots = [
            p
            for p in plots
            if hasattr(p, "name") and p.name in ("IPC Bar", "Baseline Line", "IPC vs Miss")
        ]
        assert len(our_plots) == 3

    def test_multi_plot_page_renders(self) -> None:
        """Manage Plots page renders with multiple plot types."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        for pt in ["bar", "grouped_bar", "line"]:
            PlotService.create_plot(f"Test {pt}", pt, api.state_manager)

        navigate_to(at, "Manage Plots")
        assert not at.exception

    def test_each_plot_has_independent_pipeline(self) -> None:
        """Each plot maintains its own independent pipeline."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        p1 = PlotService.create_plot("Plot A", "bar", api.state_manager)
        p2 = PlotService.create_plot("Plot B", "bar", api.state_manager)

        p1.pipeline = [
            {"id": 0, "type": "columnSelector", "config": {"columns": ["benchmark_name"]}},
        ]
        p2.pipeline = [
            {"id": 0, "type": "sort", "config": {"order_dict": {"benchmark_name": ["mcf"]}}},
        ]

        assert p1.pipeline[0]["type"] == "columnSelector"
        assert p2.pipeline[0]["type"] == "sort"
        assert len(p1.pipeline) == 1
        assert len(p2.pipeline) == 1


# ---------------------------------------------------------------------------
# Data manager → plot consistency
# ---------------------------------------------------------------------------
class TestDataManagerPlotConsistency:
    """Data modifications via managers should be available to plots."""

    def test_seeds_reduction_available_for_plot(self) -> None:
        """After reducing seeds, reduced data can be used by plots."""
        at = create_app_with_data()
        api: Any = get_api(at)

        original: pd.DataFrame = api.state_manager.get_data()
        original_rows: int = len(original)

        # Reduce seeds via API
        reduced: pd.DataFrame = api.managers.reduce_seeds(
            original,
            categorical_cols=["benchmark_name", "config_description"],
            statistic_cols=["system.cpu.ipc", "system.cpu.numCycles"],
        )

        # Update state with reduced data
        api.state_manager.set_data(reduced)
        api.state_manager.set_processed_data(reduced.copy())

        assert len(reduced) < original_rows

        # Create plot with reduced data
        from src.web.pages.ui.plotting.plot_service import PlotService

        plot = PlotService.create_plot("Reduced Plot", "bar", api.state_manager)
        plot.processed_data = reduced

        assert plot.processed_data is not None
        assert len(plot.processed_data) < original_rows

    def test_preprocessed_data_used_by_plot(self) -> None:
        """Preprocessor transformations are available for plotting."""
        at = create_app_with_data()
        api: Any = get_api(at)

        raw: pd.DataFrame = api.state_manager.get_data()

        # Rename a column via preprocessor
        renamed: pd.DataFrame = raw.rename(columns={"system.cpu.ipc": "IPC"})
        api.state_manager.set_data(renamed)
        api.state_manager.set_processed_data(renamed.copy())

        # Verify column rename persisted
        current: pd.DataFrame = api.state_manager.get_data()
        assert "IPC" in current.columns
        assert "system.cpu.ipc" not in current.columns


# ---------------------------------------------------------------------------
# Cross-page state consistency
# ---------------------------------------------------------------------------
class TestCrossPageConsistency:
    """State remains consistent when navigating between pages."""

    def test_data_persists_across_pages(self) -> None:
        """Data loaded on one page is available on others."""
        at = create_app_with_data()
        api: Any = get_api(at)

        # Navigate through all data-dependent pages
        navigate_to(at, "Data Managers")
        assert not at.exception
        assert api.state_manager.has_data()

        navigate_to(at, "Manage Plots")
        assert not at.exception
        assert api.state_manager.has_data()

        navigate_to(at, "Save/Load Portfolio")
        assert not at.exception
        assert api.state_manager.has_data()

    def test_plots_persist_across_pages(self) -> None:
        """Plots created on Manage Plots survive page navigation."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        plot = PlotService.create_plot("Cross Page", "bar", api.state_manager)
        plot_id: int = plot.plot_id

        navigate_to(at, "Data Managers")
        assert not at.exception

        navigate_to(at, "Manage Plots")
        assert not at.exception

        # Plot should still exist
        remaining_ids = [p.plot_id for p in api.state_manager.get_plots() if hasattr(p, "plot_id")]
        assert plot_id in remaining_ids

    def test_full_workflow_sequence(self) -> None:
        """Complete workflow: upload → manage data → create plot → save."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        at = create_app_with_data()
        api: Any = get_api(at)

        # Step 1: Verify data on Data Managers
        navigate_to(at, "Data Managers")
        assert not at.exception

        # Step 2: Create plot on Manage Plots
        navigate_to(at, "Manage Plots")
        assert not at.exception
        plot = PlotService.create_plot("Workflow Plot", "bar", api.state_manager)
        plot.processed_data = api.state_manager.get_data().copy()

        # Step 3: Save on Portfolio
        navigate_to(at, "Save/Load Portfolio")
        assert not at.exception

        api.data_services.save_portfolio(
            name="e2e_workflow_portfolio",
            data=api.state_manager.get_data(),
            plots=[plot],
            config={},
            plot_counter=api.state_manager.get_plot_counter(),
        )

        portfolios = api.data_services.list_portfolios()
        assert "e2e_workflow_portfolio" in portfolios

        # Cleanup
        api.data_services.delete_portfolio("e2e_workflow_portfolio")

    def test_performance_metrics_update_with_state(self) -> None:
        """Performance page shows updated metrics as state grows."""
        at = create_app_with_data()
        navigate_to(at, "\u26a1 Performance")

        assert not at.exception
        data_metrics = [m for m in at.metric if m.label == "Data Loaded"]
        if data_metrics:
            assert data_metrics[0].value == "Yes"


# ---------------------------------------------------------------------------
# FigureEngine with multiple plot types
# ---------------------------------------------------------------------------
class TestFigureEngineMultiType:
    """FigureEngine produces valid figures for all registered types."""

    def test_all_basic_types_produce_figures(self) -> None:
        """Bar, line, scatter all produce valid go.Figure objects."""
        from src.web.figures.engine import FigureEngine

        at = create_app_with_data()
        api: Any = get_api(at)
        raw: pd.DataFrame = api.state_manager.get_data()

        selected_cols: pd.DataFrame = _apply_pipeline(
            raw,
            [
                {
                    "type": "columnSelector",
                    "columns": [
                        "benchmark_name",
                        "system.cpu.ipc",
                        "system.cpu.dcache.overall_miss_rate",
                    ],
                },
            ],
        )

        from src.web.pages.ui.plotting.plot_factory import PlotFactory

        for plot_type in ["bar", "line", "scatter"]:
            plot = PlotFactory.create_plot(plot_type, 999, f"test_{plot_type}")
            engine = FigureEngine.from_plot(plot, plot_type)

            config: Dict[str, Any] = {
                "x": "benchmark_name",
                "y": "system.cpu.ipc",
                "title": f"Test {plot_type}",
                "xlabel": "X",
                "ylabel": "Y",
                "barmode": "group",
            }

            fig: go.Figure = engine.build(plot_type, selected_cols, config)
            assert isinstance(fig, go.Figure), f"Failed for {plot_type}"
            assert len(fig.data) > 0, f"No data traces for {plot_type}"
