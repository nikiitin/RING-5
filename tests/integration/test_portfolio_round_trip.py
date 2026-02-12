"""Integration tests for portfolio, CSV pool, and configuration round-trip.

Covers Scenarios #9 (CSV pool full cycle), #10 (Multi-plot portfolio),
#11 (State consistency across operations), and #12 (Plot type switch).

Tests:
    - CSV pool: add → load → verify → delete cycle
    - Configuration: save → load → verify → delete cycle
    - Multi-plot portfolio: create plots → save → restore
    - Plot type switching with data preservation
    - State consistency across multiple operations
"""

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pandas as pd
import plotly.graph_objects as go

from src.core.application_api import ApplicationAPI
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_service import PlotService

# ===========================================================================
# Test Class 1: CSV Pool full cycle
# ===========================================================================


class TestCsvPoolCycle:
    """Test CSV pool add → list → load → delete round-trip."""

    def test_add_load_delete_csv(
        self,
        facade: ApplicationAPI,
        rich_sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Add CSV to pool → load it back → delete from pool."""
        # Write source CSV
        source_csv: Path = tmp_path / "source_data.csv"
        rich_sample_data.to_csv(source_csv, index=False)

        # Patch PathService to use tmp_path
        with patch(
            "src.core.services.data_services.csv_pool_service.PathService.get_data_dir",
            return_value=tmp_path / ".ring5",
        ):
            # 1. Add to pool
            pool_path: str = facade.add_to_csv_pool(str(source_csv))
            assert Path(pool_path).exists()

            # 2. Load from pool
            loaded_df: pd.DataFrame = facade.load_csv_file(pool_path)
            assert len(loaded_df) == len(rich_sample_data)
            assert set(loaded_df.columns) == set(rich_sample_data.columns)

            # 3. Delete from pool
            deleted: bool = facade.delete_from_csv_pool(pool_path)
            assert deleted is True
            assert not Path(pool_path).exists()

    def test_load_csv_pool_lists_files(
        self,
        facade: ApplicationAPI,
        rich_sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Adding CSV files populates pool listing."""
        csv_one: Path = tmp_path / "one.csv"
        rich_sample_data.to_csv(csv_one, index=False)

        with patch(
            "src.core.services.data_services.csv_pool_service.PathService.get_data_dir",
            return_value=tmp_path / ".ring5",
        ):
            facade.add_to_csv_pool(str(csv_one))

            pool: List[Dict[str, Any]] = facade.load_csv_pool()
            assert len(pool) >= 1
            # Verify metadata present
            assert "path" in pool[0]
            assert "name" in pool[0]
            assert "size" in pool[0]


# ===========================================================================
# Test Class 2: Configuration save/load round-trip
# ===========================================================================


class TestConfigurationRoundTrip:
    """Test configuration save → load → delete cycle."""

    def test_save_and_load_configuration(
        self,
        facade: ApplicationAPI,
        tmp_path: Path,
    ) -> None:
        """Saved configuration can be loaded back with same structure."""
        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": ["benchmark_name", "system.cpu.ipc"],
            },
            {
                "type": "sort",
                "order_dict": {"benchmark_name": ["mcf", "omnetpp"]},
            },
        ]

        with patch(
            "src.core.services.data_services.config_service.PathService.get_data_dir",
            return_value=tmp_path / ".ring5",
        ):
            # Save
            saved_path: str = facade.save_configuration(
                name="test_config",
                description="Integration test config",
                shapers_config=pipeline,
            )
            assert Path(saved_path).exists()

            # Load
            loaded: Dict[str, Any] = facade.load_configuration(saved_path)
            assert loaded["name"] == "test_config"
            assert loaded["description"] == "Integration test config"
            assert len(loaded["shapers"]) == 2
            assert loaded["shapers"][0]["type"] == "columnSelector"
            assert loaded["shapers"][1]["type"] == "sort"

    def test_delete_configuration(
        self,
        facade: ApplicationAPI,
        tmp_path: Path,
    ) -> None:
        """Deleted configuration file no longer exists."""
        pipeline: List[Dict[str, Any]] = [
            {"type": "columnSelector", "columns": ["x"]},
        ]

        with patch(
            "src.core.services.data_services.config_service.PathService.get_data_dir",
            return_value=tmp_path / ".ring5",
        ):
            saved_path: str = facade.save_configuration("deletable", "Desc", pipeline)
            assert Path(saved_path).exists()

            deleted: bool = facade.delete_configuration(saved_path)
            assert deleted is True
            assert not Path(saved_path).exists()


# ===========================================================================
# Test Class 3: Multi-plot state consistency
# ===========================================================================


class TestMultiPlotStateConsistency:
    """Test creating and managing multiple plots with data."""

    def test_create_three_plots_with_different_types(
        self,
        state_manager: RepositoryStateManager,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """Three plots of different types coexist in state."""
        bar_plot: BasePlot = PlotService.create_plot(
            "BarPlot", "bar", state_manager
        )  # type: ignore[assignment]
        line_plot: BasePlot = PlotService.create_plot(
            "LinePlot", "line", state_manager
        )  # type: ignore[assignment]
        scatter_plot: BasePlot = PlotService.create_plot(
            "ScatterPlot", "scatter", state_manager
        )  # type: ignore[assignment]

        # All exist in state
        plots: List[Any] = state_manager.get_plots()
        assert len(plots) == 3

        plot_types: set[str] = {p.plot_type for p in plots}
        assert plot_types == {"bar", "line", "scatter"}

        # Each can generate a figure
        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y": "system.cpu.ipc",
            "title": "Test",
            "xlabel": "X",
            "ylabel": "Y",
        }

        for plot in [bar_plot, line_plot, scatter_plot]:
            fig: go.Figure = plot.create_figure(rich_sample_data, config)
            assert isinstance(fig, go.Figure)
            assert len(fig.data) > 0

    def test_delete_middle_plot_preserves_others(
        self,
        state_manager: RepositoryStateManager,
    ) -> None:
        """Deleting one plot doesn't affect others."""
        p1: BasePlot = PlotService.create_plot(
            "First", "bar", state_manager
        )  # type: ignore[assignment]
        p2: BasePlot = PlotService.create_plot(
            "Second", "line", state_manager
        )  # type: ignore[assignment]
        p3: BasePlot = PlotService.create_plot(
            "Third", "scatter", state_manager
        )  # type: ignore[assignment]

        # Delete middle
        PlotService.delete_plot(p2.plot_id, state_manager)

        plots: List[Any] = state_manager.get_plots()
        assert len(plots) == 2
        remaining_ids: set[int] = {p.plot_id for p in plots}
        assert p1.plot_id in remaining_ids
        assert p3.plot_id in remaining_ids
        assert p2.plot_id not in remaining_ids


# ===========================================================================
# Test Class 4: Plot type switching with data
# ===========================================================================


class TestPlotTypeSwitchWithData:
    """Test plot type change preserves pipeline and processed_data."""

    def test_bar_to_line_preserves_processed_data(
        self,
        state_manager: RepositoryStateManager,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """Changing bar→line keeps processed_data intact."""
        plot: BasePlot = PlotService.create_plot(
            "Switch", "bar", state_manager
        )  # type: ignore[assignment]
        plot.processed_data = rich_sample_data
        plot.pipeline = [
            {"type": "columnSelector", "columns": ["benchmark_name", "system.cpu.ipc"]},
        ]

        new_plot: BasePlot = PlotService.change_plot_type(
            plot, "line", state_manager
        )  # type: ignore[assignment]

        assert new_plot.plot_type == "line"
        assert new_plot.processed_data is not None
        assert len(new_plot.processed_data) == len(rich_sample_data)
        # Pipeline should be preserved
        assert len(new_plot.pipeline) == 1

    def test_switch_type_then_render(
        self,
        state_manager: RepositoryStateManager,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """After type switch, new type can render a figure."""
        plot: BasePlot = PlotService.create_plot(
            "Render", "bar", state_manager
        )  # type: ignore[assignment]
        plot.processed_data = rich_sample_data

        new_plot: BasePlot = PlotService.change_plot_type(
            plot, "scatter", state_manager
        )  # type: ignore[assignment]
        assert new_plot.plot_type == "scatter"

        config: Dict[str, Any] = {
            "x": "system.cpu.numCycles",
            "y": "system.cpu.ipc",
            "title": "Switched Plot",
            "xlabel": "Cycles",
            "ylabel": "IPC",
        }
        fig: go.Figure = new_plot.create_figure(rich_sample_data, config)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_multiple_type_switches(
        self,
        state_manager: RepositoryStateManager,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """Plot can be switched through multiple types."""
        plot: BasePlot = PlotService.create_plot(
            "Multi", "bar", state_manager
        )  # type: ignore[assignment]
        plot.processed_data = rich_sample_data

        # bar → line → scatter → bar
        plot = PlotService.change_plot_type(plot, "line", state_manager)  # type: ignore[assignment]
        assert plot.plot_type == "line"

        plot = PlotService.change_plot_type(
            plot, "scatter", state_manager
        )  # type: ignore[assignment]
        assert plot.plot_type == "scatter"

        plot = PlotService.change_plot_type(plot, "bar", state_manager)  # type: ignore[assignment]
        assert plot.plot_type == "bar"

        # Data still there
        assert plot.processed_data is not None
