"""
Web Rendering Layer — engine-specific translation of visualization configs.

Connectors translate ``FigureConfig`` (core model) into engine-specific
API calls (Plotly ``go.Figure`` updates, matplotlib ``Axes`` updates, etc.).
Builders construct ``FigureConfig`` from user inputs or existing figures.

Public API:
    - ``ConfigSpecBuilder``          — Dict[str, Any] → FigureConfig
    - ``PlotlyFigureSpecBuilder``    — go.Figure → FigureConfig
    - ``PresetSpecBuilder``          — Preset overlay on FigureConfig
    - ``FigureSpecToPlotly``         — FigureConfig → Plotly figure styling
    - ``FigureSpecToMatplotlib``     — FigureConfig → matplotlib figure styling
    - ``MatplotlibTraceRenderer``    — List[TraceConfig] → matplotlib artists
    - ``PlotlyTraceExtractor``       — go.Figure → List[TraceConfig]
"""

from src.web.rendering.config_builder import (
    ConfigSpecBuilder,
    PlotlyFigureSpecBuilder,
    PresetSpecBuilder,
)
from src.web.rendering.matplotlib_connector import (
    FigureSpecToMatplotlib,
)
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer
from src.web.rendering.plotly_connector import FigureSpecToPlotly
from src.web.rendering.plotly_trace_extractor import PlotlyTraceExtractor

__all__ = [
    "ConfigSpecBuilder",
    "FigureSpecToPlotly",
    "FigureSpecToMatplotlib",
    "PlotlyFigureSpecBuilder",
    "PresetSpecBuilder",
    "MatplotlibTraceRenderer",
    "PlotlyTraceExtractor",
]
