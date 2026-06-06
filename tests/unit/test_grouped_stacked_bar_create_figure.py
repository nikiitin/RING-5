"""Tests for GroupedStackedBarPlot.create_figure — uncovered branches."""

from typing import cast

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

    def test_no_group_delegates_to_parent(self, plot: GroupedStackedBarPlot) -> None:
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
        fig = plot.create_figure(data, config)
        assert isinstance(fig, go.Figure)
        # Parent builds stacked traces
        assert len(list(fig.data)) > 0

    def test_no_x_returns_empty_traces(self, plot: GroupedStackedBarPlot) -> None:
        """When x_col is missing, returns empty TraceBuildResult."""
        config = {"x": None, "group": "Config", "y_columns": []}
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
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Standard grouped stacked bar creation."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks", "Energy"],
            "title": "Test",
            "xlabel": "Bench",
            "ylabel": "Value",
            "legend_title": "Stats",
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)
        # 2 y_columns → 2 bar traces
        assert len(list(fig.data)) == 2
        # Title/ylabel/legend_title are applied by the style chain,
        # not by create_figure().  Verify trace count only.
        assert len(list(fig.data)) > 0

    def test_with_group_filter(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Group filter limits displayed groups."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "group_filter": ["c1"],
            "title": "Filtered",
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)
        # Only c1 group → tick text should only contain "c1"
        tick_text = list(fig.layout.xaxis.ticktext)
        assert "c2" not in tick_text

    def test_with_xaxis_order(self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame) -> None:
        """Custom x-axis ordering is respected."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "xaxis_order": ["B", "A"],
            "title": "Ordered",
        }
        fig = plot.create_figure(sample_data, config)
        annotations = fig.layout.annotations
        # First annotation should be B, second A
        labels = [a.text for a in annotations]
        assert labels.index("<b>B</b>") < labels.index("<b>A</b>")

    def test_with_group_order(self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame) -> None:
        """Custom group ordering is respected."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "group_order": ["c2", "c1"],
            "title": "Group Ordered",
        }
        fig = plot.create_figure(sample_data, config)
        tick_text = list(fig.layout.xaxis.ticktext)
        # Within each benchmark, c2 should come before c1
        assert tick_text[0] == "c2"
        assert tick_text[1] == "c1"

    def test_with_renames(self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame) -> None:
        """X-axis and group renames are applied."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "xaxis_labels": {"A": "Alpha"},
            "group_renames": {"c1": "Config1"},
            "title": "Renamed",
        }
        fig = plot.create_figure(sample_data, config)
        annotations = fig.layout.annotations
        labels = [a.text for a in annotations]
        assert "<b>Alpha</b>" in labels
        tick_text = list(fig.layout.xaxis.ticktext)
        assert "Config1" in tick_text

    def test_with_show_totals(self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame) -> None:
        """Stack totals annotations are added when show_totals is True."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks", "Energy"],
            "show_totals": True,
            "title": "Totals",
        }
        fig = plot.create_figure(sample_data, config)
        annotations = fig.layout.annotations
        # Should have category labels + total annotations
        # 2 categories + 4 total annotations (2 groups × 2 categories)
        assert len(annotations) > 2

    def test_separators_rendered_when_enabled(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
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
        fig = plot.create_figure(sample_data, config)
        shapes = list(fig.layout.shapes)
        assert any(s.type == "line" for s in shapes)

    def test_user_shapes_config_ignored_by_create_figure(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """create_figure no longer reads config['shapes']; user-drawn shapes are
        applied separately by the StyleApplicator. A bad value is simply ignored."""
        config = {
            "x": "Benchmark",
            "group": "Config",
            "y_columns": ["Ticks"],
            "shapes": "invalid",
            "title": "Bad Shapes",
        }
        fig = plot.create_figure(sample_data, config)
        assert isinstance(fig, go.Figure)

    def test_get_legend_column_returns_none(self, plot: GroupedStackedBarPlot) -> None:
        """GroupedStacked legend column is always None."""
        assert plot.get_legend_column({"group": "Config"}) is None
        assert plot.get_legend_column({}) is None


class TestHelperMethods:
    """Test private helper methods for coverage."""

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
        plot = GroupedStackedBarPlot(1, "T")
        data = pd.DataFrame({"X": ["A", "B"], "G": ["g1", "g2"]})
        config = {"xaxis_labels": {"A": "Alpha"}, "group_renames": {"g1": "Group1"}}
        new_data, cats, groups = plot._apply_renames(
            data, "X", "G", ["A", "B"], ["g1", "g2"], config
        )
        assert cats == ["Alpha", "B"]
        assert groups == ["Group1", "g2"]
        assert "Alpha" in new_data["X"].values

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
        assert anns[0]["font"]["size"] == 16

    def test_apply_common_layout_enforces_hover(self) -> None:
        plot = GroupedStackedBarPlot(1, "T")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[1, 2], y=[3, 4], name="test"))
        result = plot.apply_common_layout(fig, {})
        hovertemplate = cast(str, cast(go.Bar, result.data[0]).hovertemplate)
        assert "customdata" in hovertemplate
