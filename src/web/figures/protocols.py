"""
Figure Engine Protocols — Contracts for Figure Creation & Styling.

These protocols define the interface between Controllers (Layer 2) and
the Figure Engine. They are deliberately Streamlit-free, enabling
pure-logic testing and eventual reuse outside of the web layer.

Components:
    FigureCreator: Protocol for type-specific figure creation (bar, line, etc.)
    FigureStyler: Protocol for applying visual styles to a figure
    FigureEngine: Facade that composes creation + styling into a single call

Design Principle:
    Controllers never import concrete plot types or the style applicator
    directly. They depend only on FigureEngine, which dispatches internally.
"""

from typing import Any, Dict, Protocol

import pandas as pd
import plotly.graph_objects as go


class FigureCreator(Protocol):
    """
    Protocol for type-specific figure creation.

    Each plot type (bar, line, scatter, ...) provides a creator that knows
    how to build a ``go.Figure`` from data and config, with ZERO Streamlit
    dependencies.

    This matches the existing ``BasePlot.create_figure`` signature, so
    current plot types can satisfy this protocol without modification.
    """

    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """
        Build a Plotly figure from data and configuration.

        Args:
            data: Processed DataFrame ready for plotting.
            config: Plot configuration dict (PlotDisplayConfig or legacy dict).

        Returns:
            A fully constructed Plotly figure (before style application).
        """
        ...


class FigureStyler(Protocol):
    """
    Protocol for applying visual styles to a Plotly figure.

    Matches the existing ``StyleApplicator.apply_styles`` signature.
    """

    def apply_styles(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """
        Apply layout, typography, colors, labels, etc. to a figure.

        Args:
            fig: Raw Plotly figure from a FigureCreator.
            config: Style configuration dict.

        Returns:
            Styled figure ready for display.
        """
        ...
