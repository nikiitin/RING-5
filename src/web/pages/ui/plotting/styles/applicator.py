"""
Style Applicator - Plotly Figure Styling Implementation.

Bridges the flat ``config`` dict that the UI layer produces to the
engine-agnostic ``FigureSpec`` model.  ``apply_styles`` builds a spec
via ``ConfigSpecBuilder``, resolves sentinel values, stores the result,
and delegates all Plotly-specific layout mutations to
``FigureSpecToPlotly.apply``.
"""

from typing import Any, Dict, Optional

import plotly.graph_objects as go

from src.core.visualization.connectors.builders import ConfigSpecBuilder
from src.core.visualization.connectors.plotly_connector import FigureSpecToPlotly
from src.core.visualization.figure_spec import FigureSpec
from src.core.visualization.resolvers import resolve_spec


class StyleApplicator:
    """
    Handles application of styles, themes, and layouts to Plotly figures.
    Decoupled from UI rendering.

    Attributes:
        last_spec:  The resolved ``FigureSpec`` built from the most recent
                    ``apply_styles`` call.  ``None`` until the first call.
    """

    def __init__(self, plot_type: str):
        self.plot_type: str = plot_type
        self.last_spec: Optional[FigureSpec] = None

    def apply_styles(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """
        Apply common layout, theme, and styling settings to the figure.

        Builds a ``FigureSpec`` from the flat config dict, resolves sentinel
        values, then delegates all Plotly-specific application to the
        ``FigureSpecToPlotly`` connector.

        Side-effect: stores the resolved ``FigureSpec`` in ``self.last_spec``
        for downstream consumers (e.g., the LaTeX export pipeline).
        """
        # Build & resolve the engine-agnostic FigureSpec
        self.last_spec = resolve_spec(ConfigSpecBuilder.from_config(config, self.plot_type))

        # Delegate all Plotly layout mutations to the connector
        FigureSpecToPlotly.apply(self.last_spec, fig)

        # Pass-through: raw Plotly shapes are not part of the FigureSpec
        # model (they are renderer-specific).  Apply them directly.
        if config.get("shapes"):
            fig.update_layout(shapes=config["shapes"])

        return fig
