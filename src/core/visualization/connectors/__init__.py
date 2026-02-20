"""
Connectors — translate FigureConfig to engine-specific API calls.

  - ``plotly_connector``     — FigureConfig → ``go.Figure`` updates
  - ``matplotlib_connector`` — FigureConfig → ``matplotlib.axes`` updates
  - ``builders``             — build FigureConfig from existing Plotly figures,
                               presets, or flat config dicts
"""

from src.core.visualization.connectors.builders import (
    ConfigSpecBuilder,
    PlotlyFigureSpecBuilder,
    PresetSpecBuilder,
)
from src.core.visualization.connectors.matplotlib_connector import (
    FigureSpecToMatplotlib,
)
from src.core.visualization.connectors.plotly_connector import FigureSpecToPlotly

__all__ = [
    "ConfigSpecBuilder",
    "FigureSpecToPlotly",
    "FigureSpecToMatplotlib",
    "PlotlyFigureSpecBuilder",
    "PresetSpecBuilder",
]
