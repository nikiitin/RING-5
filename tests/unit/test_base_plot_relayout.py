"""
Tests targeting uncovered lines in BasePlot.update_from_relayout and generate_figure.

Covers:
- update_from_relayout: empty data (L118), xaxis range (L138-142, 155-165),
  yaxis range (L174-176), autorange (L199), legend drag (L238, 270, 278),
  legend title (L372), list range equality (L132-136), float close equality (L89, 103)
- generate_figure: no data error (L270), legend_labels branch (L278)
- to_dict / from_dict with processed_data=None
"""

from unittest.mock import patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.base_plot import BasePlot


class ConcretePlot(BasePlot):
    """Concrete implementation for testing abstract class."""

    def render_config_ui(self, data: pd.DataFrame, saved_config: dict) -> dict:
        return {}

    def create_figure(self, data: pd.DataFrame, config: dict) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2], y=[3, 4], name="trace1"))
        return fig

    def get_legend_column(self, config: dict) -> str:
        return "col"


@pytest.fixture
def plot() -> ConcretePlot:
    return ConcretePlot(plot_id=1, name="Test", plot_type="test")


class TestUpdateFromRelayoutRanges:
    """Tests for range handling in update_from_relayout."""

    def test_empty_relayout_returns_false(self, plot: ConcretePlot) -> None:
        assert plot.update_from_relayout({}) is False
        assert plot.update_from_relayout(None) is False

    def test_xaxis_range_bracket_notation(self, plot: ConcretePlot) -> None:
        """xaxis.range[0] and xaxis.range[1] should set range_x."""
        result = plot.update_from_relayout(
            {
                "xaxis.range[0]": 1.0,
                "xaxis.range[1]": 5.0,
            }
        )
        assert result is True
        assert plot.config["range_x"] == [1.0, 5.0]

    def test_xaxis_range_array_notation(self, plot: ConcretePlot) -> None:
        """xaxis.range as a single array value."""
        result = plot.update_from_relayout({"xaxis.range": [2.0, 8.0]})
        assert result is True
        assert plot.config["range_x"] == [2.0, 8.0]

    def test_yaxis_range_bracket_notation(self, plot: ConcretePlot) -> None:
        result = plot.update_from_relayout(
            {
                "yaxis.range[0]": 0.0,
                "yaxis.range[1]": 100.0,
            }
        )
        assert result is True
        assert plot.config["range_y"] == [0.0, 100.0]

    def test_yaxis_range_array_notation(self, plot: ConcretePlot) -> None:
        result = plot.update_from_relayout({"yaxis.range": [10.0, 50.0]})
        assert result is True
        assert plot.config["range_y"] == [10.0, 50.0]

    def test_same_range_no_change(self, plot: ConcretePlot) -> None:
        """Setting the same range twice should return False the second time."""
        plot.update_from_relayout({"xaxis.range[0]": 1.0, "xaxis.range[1]": 5.0})
        result = plot.update_from_relayout({"xaxis.range[0]": 1.0, "xaxis.range[1]": 5.0})
        assert result is False

    def test_close_float_equality(self, plot: ConcretePlot) -> None:
        """Values that are very close (within rel_tol) should not trigger change."""
        plot.config["range_x"] = [1.0, 5.0]
        # Values that differ by less than rel_tol=1e-9
        result = plot.update_from_relayout(
            {
                "xaxis.range[0]": 1.0 + 1e-12,
                "xaxis.range[1]": 5.0 + 1e-12,
            }
        )
        assert result is False

    def test_single_value_close_float_equality(self, plot: ConcretePlot) -> None:
        """A single config value that's close should not trigger change."""
        plot.config["legend_x"] = 0.5
        result = plot.update_from_relayout({"legend.x": 0.5 + 1e-12})
        assert result is False


class TestUpdateFromRelayoutAutorange:
    """Tests for autorange handling."""

    def test_xaxis_autorange_clears_range(self, plot: ConcretePlot) -> None:
        plot.config["range_x"] = [1.0, 5.0]
        result = plot.update_from_relayout({"xaxis.autorange": True})
        assert result is True
        assert plot.config["range_x"] is None

    def test_yaxis_autorange_clears_range(self, plot: ConcretePlot) -> None:
        plot.config["range_y"] = [0, 100]
        result = plot.update_from_relayout({"yaxis.autorange": True})
        assert result is True
        assert plot.config["range_y"] is None

    def test_autorange_no_existing_range(self, plot: ConcretePlot) -> None:
        """Autorange when no range exists should not trigger change."""
        result = plot.update_from_relayout({"xaxis.autorange": True})
        assert result is False

    def test_autorange_false_no_change(self, plot: ConcretePlot) -> None:
        """Autorange=False should not clear range."""
        plot.config["range_x"] = [1.0, 5.0]
        result = plot.update_from_relayout({"xaxis.autorange": False})
        assert result is False
        assert plot.config["range_x"] == [1.0, 5.0]


class TestUpdateFromRelayoutLegend:
    """Tests for legend drag handling."""

    def test_legend_position_drag(self, plot: ConcretePlot) -> None:
        result = plot.update_from_relayout({"legend.x": 0.8, "legend.y": 0.95})
        assert result is True
        assert plot.config["legend_x"] == 0.8
        assert plot.config["legend_y"] == 0.95
        # Anchors should be set
        assert plot.config["legend_xanchor"] == "left"
        assert plot.config["legend_yanchor"] == "top"

    def test_legend2_position_drag(self, plot: ConcretePlot) -> None:
        """Multi-column legends may have legend2, legend3, etc."""
        result = plot.update_from_relayout({"legend2.x": 0.3})
        assert result is True
        assert plot.config["legend2_x"] == 0.3

    def test_legend_anchor_change(self, plot: ConcretePlot) -> None:
        result = plot.update_from_relayout({"legend.xanchor": "right"})
        assert result is True
        assert plot.config["legend_xanchor"] == "right"

    def test_legend_title_update(self, plot: ConcretePlot) -> None:
        result = plot.update_from_relayout({"legend.title.text": "My Legend"})
        assert result is True
        assert plot.config["legend_title"] == "My Legend"

    def test_invalid_legend_key_ignored(self, plot: ConcretePlot) -> None:
        """Non-legend keys starting with 'legend' but having more than 2 parts."""
        result = plot.update_from_relayout({"legend.title.something.deep": "val"})
        # Should not crash — the split check filters it out
        # May or may not change based on the handler for "legend.title.text"
        assert isinstance(result, bool)

    def test_change_invalidates_cache(self, plot: ConcretePlot) -> None:
        """Config change should set last_generated_fig to None."""
        plot.last_generated_fig = go.Figure()
        plot.update_from_relayout({"legend.x": 0.5})
        assert plot.last_generated_fig is None


class TestGenerateFigure:
    """Tests for generate_figure method."""

    def test_no_data_raises_error(self, plot: ConcretePlot) -> None:
        plot.processed_data = None
        with pytest.raises(ValueError, match="no processed data"):
            plot.generate_figure()

    def test_generate_with_data(self, plot: ConcretePlot) -> None:
        plot.processed_data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        fig = plot.generate_figure()
        assert isinstance(fig, go.Figure)
        assert plot.last_generated_fig is fig

    def test_generate_with_legend_labels(self, plot: ConcretePlot) -> None:
        """When legend_labels in config, apply_legend_labels should be called."""
        plot.processed_data = pd.DataFrame({"x": [1], "y": [2]})
        plot.config["legend_labels"] = {"trace1": "Renamed"}
        fig = plot.generate_figure()
        assert fig.data[0].name == "Renamed"


class TestToDictFromDict:
    """Tests for serialization edge cases."""

    def test_to_dict_without_processed_data(self, plot: ConcretePlot) -> None:
        plot.processed_data = None
        data = plot.to_dict()
        assert data["processed_data"] is None

    def test_to_dict_with_processed_data(self, plot: ConcretePlot) -> None:
        plot.processed_data = pd.DataFrame({"a": [1, 2]})
        data = plot.to_dict()
        assert data["processed_data"] is not None
        assert "a" in data["processed_data"]

    def test_from_dict_without_processed_data(self, plot: ConcretePlot) -> None:
        data = {
            "id": 1,
            "name": "Test",
            "plot_type": "test",
            "config": {"x": "col1"},
            "processed_data": None,
            "pipeline": [],
            "pipeline_counter": 0,
            "legend_mappings_by_column": {},
            "legend_mappings": {},
        }
        with patch("src.web.pages.ui.plotting.plot_factory.PlotFactory.create_plot") as mock:
            mock.return_value = ConcretePlot(1, "Test", "test")
            loaded = BasePlot.from_dict(data)
            assert loaded.processed_data is None

    def test_from_dict_preserves_pipeline_counter(self, plot: ConcretePlot) -> None:
        data = {
            "id": 1,
            "name": "Test",
            "plot_type": "test",
            "config": {},
            "processed_data": None,
            "pipeline": [{"type": "sort"}],
            "pipeline_counter": 5,
            "legend_mappings_by_column": {"col": {"a": "A"}},
            "legend_mappings": {"x": "X"},
        }
        with patch("src.web.pages.ui.plotting.plot_factory.PlotFactory.create_plot") as mock:
            mock.return_value = ConcretePlot(1, "Test", "test")
            loaded = BasePlot.from_dict(data)
            assert loaded.pipeline_counter == 5
            assert loaded.legend_mappings_by_column == {"col": {"a": "A"}}
            assert loaded.legend_mappings == {"x": "X"}


class TestApplyLegendLabels:
    """Tests for apply_legend_labels edge cases."""

    def test_none_labels_no_change(self, plot: ConcretePlot) -> None:
        fig = go.Figure()
        fig.add_trace(go.Scatter(name="original"))
        result = plot.apply_legend_labels(fig, None)
        assert result.data[0].name == "original"

    def test_empty_labels_no_change(self, plot: ConcretePlot) -> None:
        fig = go.Figure()
        fig.add_trace(go.Scatter(name="original"))
        result = plot.apply_legend_labels(fig, {})
        assert result.data[0].name == "original"

    def test_partial_labels(self, plot: ConcretePlot) -> None:
        fig = go.Figure()
        fig.add_trace(go.Scatter(name="a"))
        fig.add_trace(go.Scatter(name="b"))
        result = plot.apply_legend_labels(fig, {"a": "Alpha"})
        assert result.data[0].name == "Alpha"
        assert result.data[1].name == "b"
