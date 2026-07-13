"""
Style Applicator - Plotly Figure Styling Implementation.

Bridges the flat ``config`` dict that the UI layer produces to the
engine-agnostic ``FigureConfig`` model.  ``apply_styles`` builds a spec
via ``ConfigSpecBuilder``, resolves sentinel values, stores the result,
and delegates all Plotly-specific layout mutations to
``FigureSpecToPlotly.apply``.
"""

import plotly.graph_objects as go

from src.core.models.visualization.figure_config import FigureConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.web.models.plot_models import PlotConfig
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.plotly_connector import FigureSpecToPlotly


class StyleApplicator:
    """
    Handles application of styles, themes, and layouts to Plotly figures.
    Decoupled from UI rendering.

    Attributes:
        last_spec:  The resolved ``FigureConfig`` built from the most recent
                    ``apply_styles`` call.  ``None`` until the first call.
    """

    def __init__(self, plot_type: str):
        self.plot_type: str = plot_type
        self.last_spec: FigureConfig | None = None

    def apply_styles(self, fig: go.Figure, config: PlotConfig) -> go.Figure:
        """
        Apply common layout, theme, and styling settings to the figure.

        Builds a ``FigureConfig`` from the flat config dict, resolves sentinel
        values, then delegates all Plotly-specific application to the
        ``FigureSpecToPlotly`` connector.

        Side-effect: stores the resolved ``FigureConfig`` in ``self.last_spec``
        for downstream consumers (e.g., the LaTeX export pipeline).
        """
        # Build & resolve the engine-agnostic FigureConfig
        self.last_spec = resolve_config(ConfigSpecBuilder.from_config(config, self.plot_type))

        # Delegate all Plotly layout mutations to the connector
        FigureSpecToPlotly.apply(self.last_spec, fig)

        # Pass-through: user-drawn Plotly shapes are not part of the
        # FigureConfig model.  APPEND them to any shapes the connector already
        # set (e.g. auto bar-group separators/shading) rather than replacing —
        # otherwise drawing a custom shape would wipe the separators.
        user_shapes = config.get("shapes")
        if user_shapes:
            existing = list(fig.layout.shapes or ())
            fig.update_layout(shapes=existing + list(user_shapes))

        return fig
