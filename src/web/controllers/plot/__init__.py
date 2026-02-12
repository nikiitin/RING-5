"""
Plot Controllers — orchestration for plot lifecycle, pipeline, and rendering.

Controllers are the ACTION layer: they read state, call presenters for UI,
perform domain operations via ApplicationAPI, and update state.

Public API:
    PlotCreationController — create, select, rename, delete, duplicate
    PipelineController — add/remove/reorder shapers, finalize pipeline
    PlotRenderController — config gathering, figure generation, chart display
"""

from src.web.controllers.plot.creation_controller import PlotCreationController
from src.web.controllers.plot.pipeline_controller import PipelineController
from src.web.controllers.plot.render_controller import PlotRenderController

__all__: list[str] = [
    "PlotCreationController",
    "PipelineController",
    "PlotRenderController",
]
