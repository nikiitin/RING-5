"""Unit tests for legend styling in StyleApplicator.

Verifies that legend positioning and styling properties are correctly
applied to Plotly figures following publication-quality standards.
"""

import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.styles.applicator import StyleApplicator


class TestLegendStyling:
    """Test suite for legend styling features."""

    @pytest.fixture
    def applicator(self):
        """Create a StyleApplicator instance for testing."""
        return StyleApplicator(plot_type="bar")

    def test_legend_position_applied(self, applicator):
        """
        Verify legend x/y positioning is correctly applied.
        """
        fig = go.Figure()
        fig.add_trace(go.Bar(y=[1, 2], name="Test"))

        config = {
            "legend_x": 0.5,
            "legend_y": 1.05,
        }

        fig = applicator.apply_styles(fig, config)

        assert fig.layout.legend.x == 0.5
        assert fig.layout.legend.y == 1.05

    def test_legend_orientation_horizontal(self, applicator):
        """
        Verify horizontal legend orientation is applied.
        """
        fig = go.Figure()
        fig.add_trace(go.Bar(y=[1, 2], name="Test"))

        config = {
            "legend_orientation": "h",
        }

        fig = applicator.apply_styles(fig, config)

        assert fig.layout.legend.orientation == "h"

    def test_legend_anchor_settings(self, applicator):
        """
        Verify legend anchor settings for proper alignment.
        """
        fig = go.Figure()
        fig.add_trace(go.Bar(y=[1, 2], name="Test"))

        config = {
            "legend_xanchor": "center",
            "legend_yanchor": "bottom",
        }

        fig = applicator.apply_styles(fig, config)

        assert fig.layout.legend.xanchor == "center"
        assert fig.layout.legend.yanchor == "bottom"

    def test_legend_no_columns_default_behavior(self, applicator):
        """
        Verify that ncols=0 does not set a fixed entrywidth.

        This allows Plotly's default behavior for single-column legends.
        """
        fig = go.Figure()
        fig.add_trace(go.Bar(y=[1, 2], name="Test"))

        config = {
            "legend_ncols": 0,
            "legend_x": 1.0,
            "legend_y": 1.0,
        }

        fig = applicator.apply_styles(fig, config)
        layout_json = fig.layout.to_plotly_json()

        # entrywidth should not be set when ncols=0
        assert layout_json["legend"].get("entrywidth") is None
