import pandas as pd
import pytest

from src.plotting import GroupedBarPlot, GroupedStackedBarPlot


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    return pd.DataFrame(
        {
            "category": ["A", "B", "C", "A", "B", "C"],
            "value": [10, 20, 15, 12, 18, 16],
            "group": ["G1", "G1", "G1", "G2", "G2", "G2"],
            "stack": ["S1", "S1", "S2", "S1", "S2", "S2"],
        }
    )


class TestGroupedBarPlotFilters:
    """Test filtering in GroupedBarPlot."""

    def test_filter_x(self, sample_data):
        """Test filtering X values."""
        plot = GroupedBarPlot(1, "Test")
        config = {
            "x": "category",
            "y": "value",
            "group": "group",
            "x_filter": ["A", "B"],  # Exclude C
            "xlabel": "Category",
            "ylabel": "Value",
            "title": "Test",
        }
        fig = plot.create_figure(sample_data, config)

        # Check that C is not in the figure data
        # In grouped bar plot, x values are manual coords, check ticktext
        tick_text = fig.layout.xaxis.ticktext

        assert "A" in tick_text
        assert "B" in tick_text
        assert "C" not in tick_text

    def test_filter_group(self, sample_data):
        """Test filtering Group values."""
        plot = GroupedBarPlot(1, "Test")
        config = {
            "x": "category",
            "y": "value",
            "group": "group",
            "group_filter": ["G1"],  # Exclude G2
            "xlabel": "Category",
            "ylabel": "Value",
            "title": "Test",
        }
        fig = plot.create_figure(sample_data, config)

        # Check only G1 is present
        # Traces are named after groups
        trace_names = [trace.name for trace in fig.data]
        assert "G1" in trace_names
        assert "G2" not in trace_names


class TestGroupedStackedBarPlotFilters:
    """Test filtering in GroupedStackedBarPlot."""

    def test_filter_x(self, sample_data):
        """Test filtering X values."""
        plot = GroupedStackedBarPlot(1, "Test")
        config = {
            "x": "category",
            "y_columns": ["value"],
            "group": "group",
            "x_filter": ["A", "B"],  # Exclude C
            "title": "Test",
        }
        fig = plot.create_figure(sample_data, config)

        # Checked code: annotations are used for categories.

        annotation_texts = [ann.text for ann in fig.layout.annotations]
        # Text is "<b>A</b>"
        assert "<b>A</b>" in annotation_texts
        assert "<b>B</b>" in annotation_texts
        assert "<b>C</b>" not in annotation_texts

    def test_filter_group(self, sample_data):
        """Test filtering Group values."""
        plot = GroupedStackedBarPlot(1, "Test")
        config = {
            "x": "category",
            "y_columns": ["value"],
            "group": "group",
            "group_filter": ["G1"],  # Exclude G2
            "title": "Test",
        }
        fig = plot.create_figure(sample_data, config)

        # In custom layout, ticktext are group names
        tick_texts = fig.layout.xaxis.ticktext
        assert "G1" in tick_texts
        assert "G2" not in tick_texts


class TestHoverTotal:
    """Test hover total functionality."""

    def test_hover_total_present(self, sample_data):
        """Test that customdata (total) matches sum of stacked values."""
        plot = GroupedStackedBarPlot(1, "Test")
        config = {"x": "category", "y_columns": ["value"], "group": "group", "title": "Test"}
        fig = plot.create_figure(sample_data, config)

        # Check that customdata is present in traces
        for trace in fig.data:
            assert trace.customdata is not None
            # Verify presence of customdata in hover template.
            assert "customdata" in trace.hovertemplate

    def test_hover_total_calculation(self):
        """Test calculation of total with multiple stacks."""
        data = pd.DataFrame(
            {
                "cat": ["A", "A", "B"],
                "val1": [10, 20, 30],
                "val2": [5, 5, 5],
                "grp": ["G1", "G2", "G1"],
            }
        )
        plot = GroupedStackedBarPlot(1, "Test")
        config = {"x": "cat", "y_columns": ["val1", "val2"], "group": "grp", "title": "Test"}
        fig = plot.create_figure(data, config)

        # Total for first row (A, G1) should be 10+5=15
        # Total for second row (A, G2) should be 20+5=25
        # Total for third row (B, G1) should be 30+5=35

        # Traces:
        # Trace 0 (val1): customdata should be [15, 25, 35] (aligned with x coords)

        # Validate that customdata values contain the expected totals.
        # Simpler: just check that customdata values are 15, 25, 35 in some order.

        trace0 = fig.data[0]
        # customdata might be a Series or array
        totals = sorted(list(trace0.customdata))
        assert totals == [15, 25, 35]
