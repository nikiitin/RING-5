"""Native legend styling through public rendering.

Verifies that legend positioning and styling properties are correctly
applied to Plotly figures following publication-quality standards.
"""

from typing import cast

import pandas as pd
from ring5 import Session
from src.web.pages.ui.plotting.types.bar_plot import BarPlot

import plotly.graph_objects as go
import pytest


class TestLegendStyling:
    """Test suite for legend styling features."""

    @pytest.fixture
    def plot(self) -> BarPlot:
        """Provide actual bars for legend styling."""
        plot = BarPlot(1, "Legend")
        plot.processed_data = pd.DataFrame({"x": ["a", "b"], "y": [1, 2]})
        return plot

    def test_legend_position_applied(self, plot: BarPlot, plot_session: Session) -> None:
        """
        Verify legend x/y positioning is correctly applied.
        """

        config = {
            "legend_x": 0.5,
            "legend_y": 1.05,
        }

        plot.config = {"x": "x", "y": "y", **config}
        fig = cast(go.Figure, plot_session.render(plot))

        assert fig.layout.legend.x == 0.5
        assert fig.layout.legend.y == 1.05

    def test_legend_orientation_applied_from_config(
        self, plot: BarPlot, plot_session: Session
    ) -> None:
        """Apply the canonical orientation emitted by the active legend controls."""

        config = {
            "legend_orientation": "horizontal",
        }

        plot.config = {"x": "x", "y": "y", **config}
        fig = cast(go.Figure, plot_session.render(plot))

        assert fig.layout.legend.orientation == "h"

    def test_retired_legend_anchor_keys_are_rejected(
        self, plot: BarPlot, plot_session: Session
    ) -> None:
        """The current editable contract never silently ignores retired anchor keys."""
        with pytest.raises(ValueError, match="Unsupported legend configuration keys"):
            plot.config = {
                "x": "x",
                "y": "y",
                "legend_xanchor": "center",
                "legend_yanchor": "bottom",
            }

    def test_legend_no_columns_default_behavior(self, plot: BarPlot, plot_session: Session) -> None:
        """
        Verify that ncols=0 does not set a fixed entrywidth.

        This allows Plotly's default behavior for single-column legends.
        """

        config = {
            "legend_ncols": 0,
            "legend_x": 1.0,
            "legend_y": 1.0,
        }

        plot.config = {"x": "x", "y": "y", **config}
        fig = cast(go.Figure, plot_session.render(plot))
        layout_json = fig.layout.to_plotly_json()

        # entrywidth should not be set when ncols=0
        assert layout_json["legend"].get("entrywidth") is None
