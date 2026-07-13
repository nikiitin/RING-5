"""Data structures and protocols shared by the web layer."""

from src.web.models.plot_models import (
    AnnotationShapeConfig,
    PlotDisplayConfig,
    RelayoutEventData,
    SeriesStyleConfig,
)
from src.web.models.plot_protocols import (
    ConfigRenderer,
    PipelineExecutor,
    PlotHandle,
    PlotLifecycleService,
    PlotTypeRegistry,
    RenderablePlot,
)

__all__ = [
    # TypedDicts
    "AnnotationShapeConfig",
    "PlotDisplayConfig",
    "RelayoutEventData",
    "SeriesStyleConfig",
    # Protocols
    "ConfigRenderer",
    "PipelineExecutor",
    "PlotHandle",
    "PlotLifecycleService",
    "PlotTypeRegistry",
    "RenderablePlot",
]
