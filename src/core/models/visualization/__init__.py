"""
Core visualization models — engine-agnostic configuration dataclasses.

This package is the **single source of truth** for all visualization
configuration.  Both Plotly and Matplotlib connectors consume these
models; neither modifies them.

All models use the ``*Config`` naming convention.
"""

from src.core.models.visualization.annotation_config import (
    AnnotationConfig,
    ReferenceLineConfig,
)
from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
from src.core.models.visualization.data_label_config import DataLabelConfig
from src.core.models.visualization.dashboard_spec import DashboardSpec
from src.core.models.visualization.drill_down_result import DrillDownResult
from src.core.models.visualization.figure_config import (
    DimensionConfig,
    FigureConfig,
    MarginsConfig,
)
from src.core.models.visualization.legend_config import (
    LegendConfig,
    LegendSpacingConfig,
)
from src.core.models.visualization.linked_selection_spec import (
    LinkedSelectionSpec,
    SelectionAxis,
    SelectionMode,
)
from src.core.models.visualization.small_multiples_spec import (
    FacetPanel,
    SmallMultiplesSpec,
)
from src.core.models.visualization.plot_transfer_result import (
    PlotTransferMode,
    PlotTransferResult,
)
from src.core.models.visualization.plot_configuration_comparison import (
    ConfigurationChange,
    ConfigurationDifference,
    PlotConfigurationComparison,
)
from src.core.models.visualization.palettes import (
    PALETTE_REGISTRY,
)
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    BoxTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    RadarTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
    ViolinTraceConfig,
)
from src.core.models.visualization.typography_config import TypographyConfig

# NOTE: palette/config-resolution *logic* lives in src.core.services.visualization
# (palette_service, config_resolver) and must be imported from there. The models
# layer depends on nobody and intentionally does NOT re-export service functions.

__all__ = [
    # Annotations
    "AnnotationConfig",
    "ReferenceLineConfig",
    # Axes
    "AxisConfig",
    "AxesConfig",
    # Data labels
    "DataLabelConfig",
    # Dashboards
    "DashboardSpec",
    # Drill-down
    "DrillDownResult",
    # Figure + dimensions
    "FigureConfig",
    "DimensionConfig",
    "MarginsConfig",
    # Legend
    "LegendConfig",
    "LegendSpacingConfig",
    # Linked selection
    "LinkedSelectionSpec",
    "SelectionAxis",
    "SelectionMode",
    # Small multiples
    "FacetPanel",
    "SmallMultiplesSpec",
    # Plot transfers
    "PlotTransferMode",
    "PlotTransferResult",
    "ConfigurationChange",
    "ConfigurationDifference",
    "PlotConfigurationComparison",
    # Palettes
    "PALETTE_REGISTRY",
    # Series style
    "SeriesStyleConfig",
    # Traces
    "TraceConfig",
    "BarTraceConfig",
    "BoxTraceConfig",
    "LineTraceConfig",
    "RadarTraceConfig",
    "ScatterTraceConfig",
    "HistogramTraceConfig",
    "ViolinTraceConfig",
    "TraceBuildResult",
    # Typography
    "TypographyConfig",
]
