"""Integration tests for error recovery and edge cases.

Covers Scenarios #7 (Pipeline error recovery) and #8 (Empty data edge cases).

Tests:
    - Invalid shaper params → proper ValueError propagation
    - Missing columns in data → early validation errors
    - Empty DataFrame through pipeline
    - Invalid plot type in PlotFactory
    - Malformed config in create_figure
    - FigureEngine with unregistered type
    - Export with invalid format
"""

from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.core.application_api import ApplicationAPI
from src.core.services.shapers.factory import ShaperFactory
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.figures.engine import FigureEngine
from src.web.pages.ui.plotting.export.converters.impl.matplotlib_converter import (
    MatplotlibConverter,
)
from src.web.pages.ui.plotting.export.presets.preset_schema import LaTeXPreset
from src.web.pages.ui.plotting.plot_factory import PlotFactory

# ===========================================================================
# Test Class 1: Shaper pipeline error recovery
# ===========================================================================


class TestShaperPipelineErrors:
    """Test that shaper errors propagate correctly and don't corrupt state."""

    def test_invalid_shaper_type_raises(self) -> None:
        """ShaperFactory raises ValueError for unknown shaper type."""
        with pytest.raises(ValueError, match="Unknown shaper type"):
            ShaperFactory.create_shaper("nonexistent", {})

    def test_column_selector_missing_params_raises(self) -> None:
        """ColumnSelector without 'columns' param raises ValueError."""
        with pytest.raises(ValueError, match="requires 'columns'"):
            ShaperFactory.create_shaper("columnSelector", {})

    def test_column_selector_missing_column_raises(self, rich_sample_data: pd.DataFrame) -> None:
        """ColumnSelector with non-existent column raises ValueError."""
        shaper = ShaperFactory.create_shaper(
            "columnSelector",
            {"columns": ["benchmark_name", "nonexistent_col"]},
        )
        with pytest.raises(ValueError, match="not found"):
            shaper(rich_sample_data)

    def test_normalize_missing_params_raises(self) -> None:
        """Normalize without required params raises ValueError."""
        with pytest.raises(ValueError, match="Missing required parameter"):
            ShaperFactory.create_shaper(
                "normalize",
                {"normalizeVars": ["x"]},  # Missing normalizerColumn, etc.
            )

    def test_mean_invalid_algorithm_raises(self) -> None:
        """Mean with invalid algorithm raises ValueError."""
        with pytest.raises(ValueError, match="meanAlgorithm"):
            ShaperFactory.create_shaper(
                "mean",
                {
                    "meanVars": ["x"],
                    "meanAlgorithm": "invalid_algo",
                    "groupingColumns": ["g"],
                    "replacingColumn": "r",
                },
            )

    def test_sort_missing_order_dict_raises(self) -> None:
        """Sort without order_dict raises ValueError."""
        with pytest.raises(ValueError, match="order_dict"):
            ShaperFactory.create_shaper("sort", {})

    def test_pipeline_error_does_not_corrupt_source_data(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """When pipeline fails mid-way, original data is unchanged."""
        data: pd.DataFrame = loaded_facade.state_manager.get_data()
        original_shape = data.shape
        original_columns = list(data.columns)

        # First shaper succeeds, second fails
        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": ["benchmark_name", "system.cpu.ipc"],
            },
            {
                "type": "sort",
                "order_dict": {"nonexistent_column": ["a", "b"]},
            },
        ]

        with pytest.raises(ValueError):
            loaded_facade.apply_shapers(data, pipeline)

        # Original data should be unchanged
        assert data.shape == original_shape
        assert list(data.columns) == original_columns


# ===========================================================================
# Test Class 2: Empty DataFrame edge cases
# ===========================================================================


class TestEmptyDataEdgeCases:
    """Test behavior with empty or minimal DataFrames."""

    def test_empty_dataframe_through_column_selector(self) -> None:
        """ColumnSelector with empty DataFrame raises ValueError."""
        empty_df = pd.DataFrame(columns=["a", "b", "c"])
        shaper = ShaperFactory.create_shaper("columnSelector", {"columns": ["a", "b"]})
        with pytest.raises(ValueError, match="empty dataframe"):
            shaper(empty_df)

    def test_single_row_dataframe_bar_plot(self) -> None:
        """Bar plot with single-row DataFrame generates valid figure."""
        single_row = pd.DataFrame(
            {
                "name": ["mcf"],
                "value": [2.1],
            }
        )
        config: Dict[str, Any] = {
            "x": "name",
            "y": "value",
            "title": "Single Row",
            "xlabel": "X",
            "ylabel": "Y",
        }

        plot = PlotFactory.create_plot("bar", plot_id=1, name="SingleRow")
        fig: go.Figure = plot.create_figure(single_row, config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_get_column_info_empty_dataframe(self, facade: ApplicationAPI) -> None:
        """get_column_info with empty DataFrame returns zero-count."""
        empty_df = pd.DataFrame()
        info: Dict[str, Any] = facade.get_column_info(empty_df)

        assert info["total_columns"] == 0
        assert info["total_rows"] == 0

    def test_large_column_count_data(self, facade: ApplicationAPI) -> None:
        """get_column_info handles DataFrame with many columns."""
        data: Dict[str, list[float]] = {f"col_{i}": [1.0, 2.0] for i in range(100)}
        df = pd.DataFrame(data)
        info: Dict[str, Any] = facade.get_column_info(df)

        assert info["total_columns"] == 100
        assert len(info["numeric_columns"]) == 100


# ===========================================================================
# Test Class 3: Plot creation error cases
# ===========================================================================


class TestPlotCreationErrors:
    """Test error handling in plot creation and figure generation."""

    def test_invalid_plot_type_raises(self) -> None:
        """PlotFactory raises ValueError for invalid plot type."""
        with pytest.raises(ValueError):
            PlotFactory.create_plot("invalid_type", plot_id=1, name="Bad")

    def test_bar_plot_missing_y_column(self, rich_sample_data: pd.DataFrame) -> None:
        """Bar plot with non-existent y column raises error."""
        plot = PlotFactory.create_plot("bar", plot_id=1, name="MissingY")
        config: Dict[str, Any] = {
            "x": "benchmark_name",
            "y": "nonexistent_column",
            "title": "Bad Y",
            "xlabel": "X",
            "ylabel": "Y",
        }
        with pytest.raises((ValueError, KeyError)):
            plot.create_figure(rich_sample_data, config)

    def test_figure_engine_unregistered_type(self) -> None:
        """FigureEngine.build() with unregistered type raises KeyError."""
        engine = FigureEngine()
        # Don't register anything
        with pytest.raises(KeyError, match="No figure creator registered"):
            engine.build("bar", pd.DataFrame(), {})

    def test_export_unsupported_format(self) -> None:
        """MatplotlibConverter.convert() with invalid format raises."""
        from tests.integration.test_render_pipeline import _make_minimal_preset

        preset: LaTeXPreset = _make_minimal_preset()
        converter = MatplotlibConverter(preset)

        fig = go.Figure(data=[go.Bar(x=["a"], y=[1])])
        with pytest.raises(ValueError):
            converter.convert(fig, "bmp")  # Unsupported format


# ===========================================================================
# Test Class 4: State consistency after errors
# ===========================================================================


class TestStateConsistencyAfterErrors:
    """Test that state remains consistent even after errors."""

    def test_failed_load_keeps_previous_data(self, loaded_facade: ApplicationAPI) -> None:
        """Loading a non-existent file does not clear existing data."""
        original_data: pd.DataFrame = loaded_facade.state_manager.get_data()
        assert original_data is not None

        with pytest.raises(Exception):
            loaded_facade.load_data("/nonexistent/path/to/file.csv")

        # Previous data should still be there
        current_data: pd.DataFrame = loaded_facade.state_manager.get_data()
        assert current_data is not None
        assert len(current_data) == len(original_data)

    def test_plot_creation_after_failed_creation(
        self,
        state_manager: RepositoryStateManager,
    ) -> None:
        """After a failed plot creation, subsequent creation succeeds."""
        from src.web.pages.ui.plotting.plot_service import PlotService

        # First: try invalid type (should fail)
        with pytest.raises(ValueError):
            PlotService.create_plot("Test", "invalid_type", state_manager)

        # Second: create valid plot (should succeed)
        plot = PlotService.create_plot("Valid", "bar", state_manager)
        assert plot is not None
        assert plot.plot_type == "bar"
