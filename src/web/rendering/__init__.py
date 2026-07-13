"""
Web Rendering Layer — engine-specific translation of visualization configs.

Connectors translate ``FigureConfig`` (core model) into engine-specific
API calls (Plotly ``go.Figure`` updates, matplotlib ``Axes`` updates, etc.).
Builders construct ``FigureConfig`` from user inputs or existing figures.

Sub-packages:
    - ``widgets/`` — declarative widget system for style configuration

Public API:
    - ``ConfigSpecBuilder``          — Dict[str, Any] → FigureConfig
    - ``PlotlyFigureSpecBuilder``    — go.Figure → FigureConfig
    - ``FigureSpecToPlotly``         — FigureConfig → Plotly figure styling
    - ``FigureSpecToMatplotlib``     — FigureConfig → matplotlib figure styling
    - ``MatplotlibTraceRenderer``    — List[TraceConfig] → matplotlib artists
    - ``EngineManager``              — Engine mode selection
"""

from src.web.rendering.config_builder import (
    ConfigSpecBuilder,
    PlotlyFigureSpecBuilder,
)
from src.web.rendering.engine_manager import EngineManager
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer
from src.web.rendering.plotly_connector import FigureSpecToPlotly

__all__ = [
    "ConfigSpecBuilder",
    "EngineManager",
    "FigureSpecToPlotly",
    "FigureSpecToMatplotlib",
    "PlotlyFigureSpecBuilder",
    "MatplotlibTraceRenderer",
]
