"""
Connectors — translate FigureSpec to engine-specific API calls.

  - ``plotly_connector``     — FigureSpec → ``go.Figure`` updates
  - ``matplotlib_connector`` — FigureSpec → ``matplotlib.axes`` updates
  - ``builders``             — build FigureSpec from existing Plotly figures or presets
"""

from src.core.visualization.connectors.plotly_connector import FigureSpecToPlotly
from src.core.visualization.connectors.matplotlib_connector import (
    FigureSpecToMatplotlib,
)
from src.core.visualization.connectors.builders import (
    PlotlyFigureSpecBuilder,
    PresetSpecBuilder,
)

__all__ = [
    "FigureSpecToPlotly",
    "FigureSpecToMatplotlib",
    "PlotlyFigureSpecBuilder",
    "PresetSpecBuilder",
]
