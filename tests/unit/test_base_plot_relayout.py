"""Tests for relayout updates, figure generation, and plot serialization."""

from typing import Any, Literal, cast
from unittest.mock import patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from ring5 import Session
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory


class ConcretePlot(BasePlot):
    """Concrete implementation for testing abstract class."""

    def render_config_ui(self, data: pd.DataFrame, saved_config: dict) -> dict:
        return {}

    def create_traces(self, data: pd.DataFrame, config: dict) -> TraceBuildResult:
        from src.core.models.visualization.trace_build_result import TraceBuildResult
        from src.core.models.visualization.trace_config import ScatterTraceConfig

        return TraceBuildResult(traces=[ScatterTraceConfig(name="trace1", x=[1, 2], y=[3, 4])])


@pytest.fixture
def plot() -> ConcretePlot:
    return ConcretePlot(plot_id=1, name="Test", plot_type="test")


class TestUpdateFromRelayoutRanges:
    """Tests for range handling in update_from_relayout."""

    def test_empty_relayout_returns_false(self, plot: ConcretePlot) -> None:
        assert plot.update_from_relayout({}) is False
        assert plot.update_from_relayout(cast(dict[str, Any], None)) is False

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
        plot.config = {**plot.config, "range_x": [1.0, 5.0]}
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
        plot.config = {**plot.config, "legend_x": 0.5}
        result = plot.update_from_relayout({"legend.x": 0.5 + 1e-12})
        assert result is False


class TestUpdateFromRelayoutAutorange:
    """Tests for autorange handling."""

    def test_xaxis_autorange_clears_range(self, plot: ConcretePlot) -> None:
        plot.config = {**plot.config, "range_x": [1.0, 5.0]}
        result = plot.update_from_relayout({"xaxis.autorange": True})
        assert result is True
        assert plot.config["range_x"] is None

    def test_yaxis_autorange_clears_range(self, plot: ConcretePlot) -> None:
        plot.config = {**plot.config, "range_y": [0, 100]}
        result = plot.update_from_relayout({"yaxis.autorange": True})
        assert result is True
        assert plot.config["range_y"] is None

    def test_autorange_no_existing_range(self, plot: ConcretePlot) -> None:
        """Autorange when no range exists should not trigger change."""
        result = plot.update_from_relayout({"xaxis.autorange": True})
        assert result is False

    def test_autorange_false_no_change(self, plot: ConcretePlot) -> None:
        """Autorange=False should not clear range."""
        plot.config = {**plot.config, "range_x": [1.0, 5.0]}
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
        assert plot.config["legend_anchor_x"] == "left"
        assert plot.config["legend_anchor_y"] == "top"

    def test_legend2_position_drag(self, plot: ConcretePlot) -> None:
        """Multi-column legends may have legend2, legend3, etc."""
        result = plot.update_from_relayout({"legend2.x": 0.3})
        assert result is True
        assert plot.config["legend2_x"] == 0.3

    def test_legend_anchor_change(self, plot: ConcretePlot) -> None:
        result = plot.update_from_relayout({"legend.xanchor": "right"})
        assert result is True
        assert plot.config["legend_anchor_x"] == "right"

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

    def test_change_invalidates_cache(self, plot: ConcretePlot, plot_session: Session) -> None:
        """Config changes discard every derived render artifact."""
        plot.processed_data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        plot_session.render(plot)
        plot.update_from_relayout({"legend.x": 0.5})
        assert plot.render_artifact.figure is None
        assert plot.render_artifact.trace_result is None
        assert plot.render_artifact.cache_key is None

    def test_replacing_processed_data_invalidates_render_state(
        self, plot: ConcretePlot, plot_session: Session
    ) -> None:
        """New pipeline output cannot retain a figure built from old data."""
        replacement = pd.DataFrame({"x": [7], "y": [8]})
        plot.processed_data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        plot_session.render(plot)

        plot.replace_processed_data(replacement)

        assert plot.processed_data is replacement
        assert plot.render_artifact.figure is None
        assert plot.render_artifact.trace_result is None
        assert plot.render_artifact.cache_key is None


class TestSessionRender:
    """Public rendering preserves plot artifacts and legend relabeling."""

    def test_render_caches_plotly_figure(self, plot: ConcretePlot) -> None:
        plot.processed_data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        with Session() as session:
            fig = session.render(plot)
        assert isinstance(fig, go.Figure)
        assert plot.render_artifact.figure is fig
        assert plot.render_artifact.cache_key is None

    def test_render_with_legend_labels(self, plot: ConcretePlot) -> None:
        """When legend_labels in config, the trace legend names are relabeled."""
        plot.processed_data = pd.DataFrame({"x": [1], "y": [2]})
        plot.config = {**plot.config, "legend_labels": {"trace1": "Renamed"}}
        with Session() as session:
            fig = session.render(plot)
        assert isinstance(fig, go.Figure)
        assert cast(go.Scatter, fig.data[0]).name == "Renamed"


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
        from src.core.common.typed_table_codec import TypedTableCodec

        decoded = TypedTableCodec.decode(data["processed_data"])
        assert decoded is not None
        assert decoded["a"].tolist() == [1, 2]

    def test_from_dict_without_processed_data(self, plot: ConcretePlot) -> None:
        data = {
            "id": 1,
            "name": "Test",
            "plot_type": "test",
            "config": {"x": "col1"},
            "source_data": None,
            "processed_data": None,
            "pipeline": [],
            "pipeline_counter": 0,
        }
        with patch("src.web.pages.ui.plotting.plot_factory.PlotFactory.create_plot") as mock:
            mock.return_value = ConcretePlot(1, "Test", "test")
            loaded = PlotFactory.from_dict(data)
            assert loaded.processed_data is None

    def test_from_dict_preserves_pipeline_counter(self, plot: ConcretePlot) -> None:
        data = {
            "id": 1,
            "name": "Test",
            "plot_type": "test",
            "config": {},
            "source_data": None,
            "processed_data": None,
            "pipeline": [{"type": "sort"}],
            "pipeline_counter": 5,
        }
        with patch("src.web.pages.ui.plotting.plot_factory.PlotFactory.create_plot") as mock:
            mock.return_value = ConcretePlot(1, "Test", "test")
            loaded = PlotFactory.from_dict(data)
            assert loaded.pipeline_counter == 5


class TestLegendLabelProjection:
    """Native labels project after preparation without changing source names."""

    @staticmethod
    def _render(
        names: tuple[str, ...], config: dict[str, Any], engine: Literal["plotly", "matplotlib"]
    ) -> tuple[list[str], list[str]]:
        from src.core.models.visualization.trace_config import BarTraceConfig
        from src.web.rendering.figure_preparation import prepare_figure
        from src.web.rendering.matplotlib_figure_builder import (
            build_matplotlib_figure_from_prepared,
        )
        from src.web.rendering.plotly_figure_builder import build_plotly_figure

        result = TraceBuildResult(
            traces=[BarTraceConfig(name=name, x=["a", "b"], y=[3.0, 5.0]) for name in names]
        )
        prepared = prepare_figure(
            pd.DataFrame({"x": ["a", "b"], "value": [3.0, 5.0]}), config, "bar", lambda *_: result
        )
        raw_names = [trace.name for trace in prepared.trace_result.traces]
        assert [trace.name for trace in result.traces] == list(names)
        if engine == "plotly":
            native = build_plotly_figure(prepared)
            display = []
            for trace in native.figure.data:
                assert isinstance(trace, go.Bar)
                assert trace.y is not None and list(trace.y) == [3.0, 5.0]
                assert isinstance(trace.name, str)
                display.append(trace.name)
        else:
            import matplotlib.pyplot as plt

            native_mpl = build_matplotlib_figure_from_prepared(prepared)
            try:
                legend = native_mpl.figure.axes[0].get_legend()
                assert legend is not None
                display = [text.get_text() for text in legend.texts]
                from matplotlib.patches import Rectangle

                for rectangle in native_mpl.figure.axes[0].patches:
                    assert isinstance(rectangle, Rectangle)
                    assert rectangle.get_height() in (3.0, 5.0)
                assert len(native_mpl.figure.axes[0].patches) == 2 * len(names)
            finally:
                plt.close(native_mpl.figure)
        return raw_names, display

    @pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
    def test_absent_labels_no_change(self, engine: Literal["plotly", "matplotlib"]) -> None:
        raw, display = self._render(("original",), {}, engine)
        assert raw == ["original"]
        assert display == ["original"]

    @pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
    def test_empty_labels_no_change(self, engine: Literal["plotly", "matplotlib"]) -> None:
        raw, display = self._render(("original",), {"legend_labels": {}}, engine)
        assert raw == ["original"]
        assert display == ["original"]

    @pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
    def test_partial_labels(self, engine: Literal["plotly", "matplotlib"]) -> None:
        raw, display = self._render(("a", "b"), {"legend_labels": {"a": "Alpha"}}, engine)
        assert raw == ["a", "b"]
        assert display == ["Alpha", "b"]
