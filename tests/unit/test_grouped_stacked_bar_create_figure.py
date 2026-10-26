"""Tests for grouped-stacked-bar figure creation."""

from ring5 import Session
from ring5.errors import RenderError

from typing import Any, cast

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.types.grouped_stacked_bar_plot import (
    GroupedStackedBarPlot,
)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Benchmark": ["A", "A", "B", "B"],
            "Config": ["c1", "c2", "c1", "c2"],
            "Ticks": [100, 200, 150, 250],
            "Energy": [10, 20, 15, 25],
        }
    )


@pytest.fixture
def plot() -> GroupedStackedBarPlot:
    return GroupedStackedBarPlot(1, "Test")


class TestCreateFigure:
    """Test GroupedStackedBarPlot.create_figure logic branches."""

    def test_no_group_delegates_to_parent(
        self, plot: GroupedStackedBarPlot, plot_session: Session
    ) -> None:
        """When group column is None/empty, delegates to StackedBarPlot."""
        data = pd.DataFrame(
            {
                "Category": ["A", "B", "C"],
                "Val1": [10, 20, 30],
                "Val2": [5, 10, 15],
            }
        )
        config = {
            "x": "Category",
            "group": None,
            "y_columns": ["Val1", "Val2"],
            "y": "Val1",
            "title": "No Group",
            "xlabel": "Cat",
            "ylabel": "V",
        }
        plot.processed_data = data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)
        # Parent builds stacked traces
        assert len(list(fig.data)) > 0

    def test_no_x_returns_empty_traces(self, plot: GroupedStackedBarPlot) -> None:
        """When x_col is missing, returns empty TraceBuildResult."""
        config: dict[str, Any] = {"x": None, "group": "Config", "y_columns": []}
        result = plot.create_traces(pd.DataFrame(), config)
        assert result.traces == []

    def test_no_y_columns_returns_empty_traces(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """When y_columns is empty, returns empty TraceBuildResult."""
        config = {"x": "Benchmark", "group": "Config", "y_columns": []}
        result = plot.create_traces(sample_data, config)
        assert result.traces == []

    def test_basic_grouped_stacked(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Standard grouped stacked bar creation."""
        # [test->req~ring5.plot.grouped-stacked-bar~1]
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks", "Energy"],
            "title": "Test",
            "xlabel": "Bench",
            "ylabel": "Value",
            "legend_title": "Stats",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)
        # 2 y_columns → 2 bar traces
        assert len(list(fig.data)) == 2
        # Title/ylabel/legend_title are applied by the style chain,
        # not by create_figure().  Verify trace count only.
        assert len(list(fig.data)) > 0

    def test_with_group_filter(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Group filter limits displayed groups."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "group_filter": ["c1"],
            "title": "Filtered",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        assert isinstance(fig, go.Figure)
        # Only c1 group → tick text should only contain "c1"
        tick_text = list(fig.layout.xaxis.ticktext)
        assert "c2" not in tick_text

    def test_with_xaxis_order(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Custom x-axis ordering is respected."""
        # [test->req~ring5.figure.ordering-renaming~2]
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "xaxis_order": ["B", "A"],
            "title": "Ordered",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        annotations = fig.layout.annotations
        # First annotation should be B, second A
        labels = [a.text for a in annotations]
        assert labels.index("<b>B</b>") < labels.index("<b>A</b>")

    def test_with_group_order(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Custom group ordering is respected."""
        # [test->req~ring5.figure.ordering-renaming~2]
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "group_order": ["c2", "c1"],
            "title": "Group Ordered",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        tick_text = list(fig.layout.xaxis.ticktext)
        # Within each benchmark, c2 should come before c1
        assert tick_text[0] == "c2"
        assert tick_text[1] == "c1"

    def test_with_renames(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """X-axis and group renames are applied."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "xaxis_labels": {"A": "Alpha"},
            "group_renames": {"c1": "Config1"},
            "title": "Renamed",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        annotations = fig.layout.annotations
        labels = [a.text for a in annotations]
        assert "<b>Alpha</b>" in labels
        tick_text = list(fig.layout.xaxis.ticktext)
        assert "Config1" in tick_text

    def test_with_show_totals(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Stack totals annotations are added when show_totals is True."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks", "Energy"],
            "show_totals": True,
            "title": "Totals",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        annotations = fig.layout.annotations
        # Should have category labels + total annotations
        # 2 categories + 4 total annotations (2 groups × 2 categories)
        assert len(annotations) > 2

    def test_separators_rendered_when_enabled(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """Auto bar-group separators flow through the engine-agnostic path and
        become Plotly line shapes (and would be axvlines in matplotlib)."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "show_separators": True,
            "title": "Separators",
        }
        plot.processed_data = sample_data
        plot.config = config
        fig = cast(go.Figure, plot_session.render(plot))
        shapes = list(fig.layout.shapes)
        assert any(s.type == "line" for s in shapes)

    def test_malformed_shapes_fail_public_render(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame, plot_session: Session
    ) -> None:
        """The final native owner rejects malformed shapes visibly."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "shapes": "invalid",
            "title": "Bad Shapes",
        }
        plot.processed_data = sample_data
        plot.config = config
        with pytest.raises(RenderError, match="shapes"):
            plot_session.render(plot)


class TestHelperMethods:
    """Test helper behavior used by grouped-stacked figure creation."""

    def test_get_ordered_categories_default(self) -> None:
        plot = GroupedStackedBarPlot(1, "T")
        data = pd.DataFrame({"X": ["B", "A", "C"], "G": ["g1", "g2", "g1"]})
        cats, groups = plot._get_ordered_categories_and_groups(data, "X", "G", {})
        assert cats == ["A", "B", "C"]
        assert groups == ["g1", "g2"]

    def test_get_ordered_categories_custom_order(self) -> None:
        plot = GroupedStackedBarPlot(1, "T")
        data = pd.DataFrame({"X": ["B", "A"], "G": ["g1", "g2"]})
        config = {"xaxis_order": ["A", "B"], "group_order": ["g2", "g1"]}
        cats, groups = plot._get_ordered_categories_and_groups(data, "X", "G", config)
        assert cats == ["A", "B"]
        assert groups == ["g2", "g1"]

    def test_get_ordered_with_missing_values(self) -> None:
        """Order list includes values not in data — they are skipped."""
        plot = GroupedStackedBarPlot(1, "T")
        data = pd.DataFrame({"X": ["A", "B"], "G": ["g1", "g2"]})
        config = {"xaxis_order": ["C", "A", "B"], "group_order": ["g3", "g2"]}
        cats, groups = plot._get_ordered_categories_and_groups(data, "X", "G", config)
        # C and g3 not in data → skipped. g1 missing from order → appended
        assert cats == ["A", "B"]
        assert groups == ["g2", "g1"]

    def test_apply_renames_basic(self) -> None:
        """Apply display labels without changing the source DataFrame."""
        plot = GroupedStackedBarPlot(1, "T")
        data = pd.DataFrame({"X": ["A", "B"], "G": ["g1", "g2"]})
        original = data.copy()
        config = {"xaxis_labels": {"A": "Alpha"}, "group_renames": {"g1": "Group1"}}
        new_data, cats, groups = plot._apply_renames(
            data, "X", "G", ["A", "B"], ["g1", "g2"], config
        )
        assert cats == ["Alpha", "B"]
        assert groups == ["Group1", "g2"]
        assert "Alpha" in new_data["X"].values
        pd.testing.assert_frame_equal(data, original)

    def test_apply_renames_empty(self) -> None:
        plot = GroupedStackedBarPlot(1, "T")
        data = pd.DataFrame({"X": ["A"], "G": ["g1"]})
        new_data, cats, groups = plot._apply_renames(data, "X", "G", ["A"], ["g1"], {})
        assert cats == ["A"]
        assert groups == ["g1"]

    def test_build_category_annotations(self) -> None:
        plot = GroupedStackedBarPlot(1, "T")
        centers = [(0.5, "A"), (2.5, "B")]
        config = {"major_label_size": 16, "major_label_color": "#333"}
        anns = plot._build_category_annotations(centers, config)
        assert len(anns) == 2
        assert anns[0].font_size == 16

    def test_neutral_hover_carries_actual_measured_totals(self, sample_data: pd.DataFrame) -> None:
        from src.web.rendering.trace_to_plotly import traces_to_plotly

        plot = GroupedStackedBarPlot(1, "T")
        result = plot.create_traces(
            sample_data, {"x": "Benchmark", "group": "Config", "y_columns": ["Ticks", "Energy"]}
        )
        figure = traces_to_plotly(result).figure
        for trace in figure.data:
            bar = cast(go.Bar, trace)
            assert "customdata" in cast(str, bar.hovertemplate)
            assert bar.customdata is not None
            assert bar.y is not None
            assert list(bar.customdata) == [110, 220, 165, 275]
            assert list(bar.y) in ([100, 200, 150, 250], [10, 20, 15, 25])
