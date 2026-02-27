"""
Plot Presenters — Pure UI rendering for plot-related widgets.

Presenters are PASSIVE: they render Streamlit widgets and return user
selections as typed dicts. No state management, no API calls, no reruns.

Public API:
    PlotControlsPresenter — rename/delete/duplicate buttons
    PipelinePresenter — shaper pipeline editor controls
    PipelineStepPresenter — individual pipeline step rendering
    ConfigPresenter — plot configuration UI (wraps BasePlot methods)
"""

from src.web.presenters.plot.config_presenter import ConfigPresenter
from src.web.presenters.plot.controls_presenter import PlotControlsPresenter
from src.web.presenters.plot.pipeline_presenter import PipelinePresenter

__all__: list[str] = [
    "PlotControlsPresenter",
    "PipelinePresenter",
    "ConfigPresenter",
]
