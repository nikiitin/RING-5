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
    - ``PresetSpecBuilder``          — Preset overlay on FigureConfig
    - ``FigureSpecToPlotly``         — FigureConfig → Plotly figure styling
    - ``FigureSpecToMatplotlib``     — FigureConfig → matplotlib figure styling
    - ``MatplotlibTraceRenderer``    — List[TraceConfig] → matplotlib artists
    - ``PlotlyTraceExtractor``       — go.Figure → List[TraceConfig]
    - ``FigureEngine``               — Orchestrator: creation + styling
    - ``EngineManager``              — Engine mode selection
    - ``PresetApplicator``           — Preset application to FigureConfig
"""

from src.web.rendering.config_builder import (
    ConfigSpecBuilder,
    PlotlyFigureSpecBuilder,
    PresetSpecBuilder,
)
from src.web.rendering.engine_manager import EngineManager
from src.web.rendering.figure_engine import FigureEngine
from src.web.rendering.matplotlib_connector import (
    FigureSpecToMatplotlib,
)
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer
from src.web.rendering.plotly_connector import FigureSpecToPlotly
from src.web.rendering.plotly_trace_extractor import PlotlyTraceExtractor
from src.web.rendering.preset_applicator import PresetApplicator

__all__ = [
    "ConfigSpecBuilder",
    "EngineManager",
    "FigureEngine",
    "FigureSpecToPlotly",
    "FigureSpecToMatplotlib",
    "PlotlyFigureSpecBuilder",
    "PresetApplicator",
    "PresetSpecBuilder",
    "MatplotlibTraceRenderer",
    "PlotlyTraceExtractor",
]
