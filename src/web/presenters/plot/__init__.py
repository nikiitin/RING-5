"""
Plot Presenters — Pure UI rendering for plot-related widgets.

Presenters are PASSIVE: they render Streamlit widgets and return user
selections as typed dicts. No state management, no API calls, no reruns.

Public API:
    PlotSelectorPresenter — plot selection radio
    PlotCreationPresenter — create plot form
    PlotControlsPresenter — rename/delete/duplicate/pipeline I/O buttons
    PipelinePresenter — shaper pipeline editor controls
    PipelineStepPresenter — individual pipeline step rendering
    ChartPresenter — chart display with refresh controls
    SaveDialogPresenter — save pipeline dialog
    LoadDialogPresenter — load pipeline dialog
    ConfigPresenter — plot configuration UI (wraps BasePlot methods)
"""

from src.web.presenters.plot.chart_presenter import ChartPresenter
from src.web.presenters.plot.config_presenter import ConfigPresenter
from src.web.presenters.plot.controls_presenter import PlotControlsPresenter
from src.web.presenters.plot.creation_presenter import PlotCreationPresenter
from src.web.presenters.plot.load_dialog_presenter import LoadDialogPresenter
from src.web.presenters.plot.pipeline_presenter import PipelinePresenter
from src.web.presenters.plot.pipeline_step_presenter import PipelineStepPresenter
from src.web.presenters.plot.save_dialog_presenter import SaveDialogPresenter
from src.web.presenters.plot.selector_presenter import PlotSelectorPresenter

__all__: list[str] = [
    "PlotSelectorPresenter",
    "PlotCreationPresenter",
    "PlotControlsPresenter",
    "PipelinePresenter",
    "PipelineStepPresenter",
    "ChartPresenter",
    "SaveDialogPresenter",
    "LoadDialogPresenter",
    "ConfigPresenter",
]
