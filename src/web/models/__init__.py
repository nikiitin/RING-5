"""
Web Layer Models — Pure Data Definitions (Layer 5).

This module contains TypedDicts and dataclasses used throughout the web layer.
These models have ZERO Streamlit imports and ZERO side effects.
They serve as the shared vocabulary between Controllers, Components, and State.

Architecture:
    Page → Controller → Component
                ↕
          UIStateManager
                ↕
             Models  ← YOU ARE HERE
"""

from src.web.models.plot_models import (
    AnnotationShapeConfig,
    PlotDisplayConfig,
    RelayoutEventData,
    SeriesStyleConfig,
    ShaperStep,
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
    "ShaperStep",
    # Protocols
    "ConfigRenderer",
    "PipelineExecutor",
    "PlotHandle",
    "PlotLifecycleService",
    "PlotTypeRegistry",
    "RenderablePlot",
]
