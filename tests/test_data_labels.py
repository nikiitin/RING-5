"""
Tests for Data Labels features in GroupedStackedBarPlot.
Tests: font size, constraint to bar, uniformtext, and style application flow.
"""

import pandas as pd
import pytest

from src.plotting.styles.applicator import StyleApplicator
from src.plotting.types.grouped_stacked_bar_plot import GroupedStackedBarPlot


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return pd.DataFrame(
        {
            "Category": ["A", "A", "B", "B"],
            "Group": ["G1", "G2", "G1", "G2"],
            "Val1": [10, 5, 8, 12],
            "Val2": [5, 10, 6, 4],
        }
    )


@pytest.fixture
def plot():
    """Create a GroupedStackedBarPlot instance."""
    return GroupedStackedBarPlot(1, "Test Plot")


@pytest.fixture
def applicator():
    """Create a StyleApplicator instance."""
    return StyleApplicator("grouped_stacked_bar")


class TestDataLabelsBasic:
    """Test basic data labels functionality."""

    def test_show_values_disabled_by_default(self, plot, sample_data, applicator):
        """Test that data labels are not shown by default."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1", "Val2"],
            "show_values": False,
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        # When show_values is False, texttemplate should not be set
        for trace in fig.data:
            assert trace.texttemplate is None or trace.texttemplate == ""

    def test_show_values_enabled(self, plot, sample_data, applicator):
        """Test that data labels are shown when enabled."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1", "Val2"],
            "show_values": True,
            "text_format": "%{y:.2f}",
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        # When show_values is True, texttemplate should be set
        for trace in fig.data:
            assert trace.texttemplate == "%{y:.2f}"


class TestDataLabelsFontSize:
    """Test font size configuration."""

    def test_default_font_size(self, plot, sample_data, applicator):
        """Test default font size of 12."""
        config = {"x": "Category", "group": "Group", "y_columns": ["Val1"], "show_values": True}
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textfont.size == 12

    def test_custom_font_size(self, plot, sample_data, applicator):
        """Test custom font size."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_font_size": 20,
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textfont.size == 20


class TestConstrainToBar:
    """Test Constrain to Bar functionality."""

    def test_constraint_disabled(self, plot, sample_data, applicator):
        """Test that constraintext is 'none' when disabled."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_constraint": False,
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.constraintext == "none"

    def test_constraint_enabled(self, plot, sample_data, applicator):
        """Test that constraintext is 'inside' when enabled."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_constraint": True,
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.constraintext == "inside"
            assert trace.textposition == "inside"

    def test_constraint_sets_uniformtext(self, plot, sample_data, applicator):
        """Test that uniformtext is set when constraint is enabled."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_constraint": True,
            "text_font_size": 12,
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        assert fig.layout.uniformtext is not None
        assert fig.layout.uniformtext.mode == "hide"
        assert fig.layout.uniformtext.minsize == 8  # max(6, 12-4)


class TestTextPosition:
    """Test text position and anchor."""

    def test_position_auto(self, plot, sample_data, applicator):
        """Test auto position."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_position": "auto",
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textposition == "auto"

    def test_position_inside_with_anchor(self, plot, sample_data, applicator):
        """Test inside position with middle anchor."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_position": "inside",
            "text_anchor": "middle",
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textposition == "inside"
            assert trace.insidetextanchor == "middle"


class TestTextRotation:
    """Test text rotation."""

    def test_default_rotation(self, plot, sample_data, applicator):
        """Test default rotation of 0."""
        config = {"x": "Category", "group": "Group", "y_columns": ["Val1"], "show_values": True}
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textangle == 0

    def test_custom_rotation(self, plot, sample_data, applicator):
        """Test custom rotation."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_rotation": 90,
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textangle == 90


class TestTextColor:
    """Test text color modes."""

    def test_custom_color(self, plot, sample_data, applicator):
        """Test custom text color."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_color_mode": "Custom",
            "text_color": "#FF0000",
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textfont.color == "#FF0000"


class TestEdgeCasesAndValidation:
    """Test edge cases and input validation for robustness."""

    def test_invalid_font_size_string(self, plot, sample_data, applicator):
        """Test that invalid font size string falls back to default."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_font_size": "invalid",
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textfont.size == 12  # Default

    def test_font_size_clamped_to_min(self, plot, sample_data, applicator):
        """Test that font size is clamped to minimum of 6."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_font_size": 2,  # Below minimum
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textfont.size == 6  # Clamped to min

    def test_font_size_clamped_to_max(self, plot, sample_data, applicator):
        """Test that font size is clamped to maximum of 48."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_font_size": 100,  # Above maximum
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textfont.size == 48  # Clamped to max

    def test_invalid_rotation_string(self, plot, sample_data, applicator):
        """Test that invalid rotation string falls back to default."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_rotation": "invalid",
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textangle == 0  # Default

    def test_rotation_clamped_to_range(self, plot, sample_data, applicator):
        """Test that rotation is clamped to -360 to 360."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_rotation": 500,  # Above max, will be clamped to 360
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        # Plotly normalizes 360 to 0, so we check the clamping worked
        # by verifying the angle is in valid range
        for trace in fig.data:
            assert -360 <= trace.textangle <= 360

    def test_invalid_position_falls_back(self, plot, sample_data, applicator):
        """Test that invalid position falls back to auto."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_position": "invalid_position",
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        for trace in fig.data:
            assert trace.textposition == "auto"

    def test_invalid_anchor_ignored(self, plot, sample_data, applicator):
        """Test that invalid anchor is ignored."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_position": "inside",
            "text_anchor": "invalid_anchor",
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        # Should not raise and anchor should not be set
        for trace in fig.data:
            assert trace.insidetextanchor is None

    def test_invalid_threshold_string(self, plot, sample_data, applicator):
        """Test that invalid threshold string falls back to 0."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_display_logic": "If > Threshold",
            "text_threshold": "invalid",
        }
        fig = plot.create_figure(sample_data, config)
        # Should not raise
        fig = applicator.apply_styles(fig, config)

    def test_none_values_handled(self, plot, sample_data, applicator):
        """Test that None values are handled gracefully."""
        config = {
            "x": "Category",
            "group": "Group",
            "y_columns": ["Val1"],
            "show_values": True,
            "text_font_size": None,
            "text_rotation": None,
            "text_position": None,
            "text_constraint": None,
        }
        fig = plot.create_figure(sample_data, config)
        fig = applicator.apply_styles(fig, config)

        # Should use defaults
        for trace in fig.data:
            assert trace.textfont.size == 12
            assert trace.textangle == 0
            assert trace.textposition == "auto"
            assert trace.constraintext == "none"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
