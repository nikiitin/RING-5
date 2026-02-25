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
from src.core.models.visualization.figure_config import (
    DimensionConfig,
    FigureConfig,
    MarginsConfig,
    SeparatorConfig,
)
from src.core.models.visualization.legend_config import (
    LegendConfig,
    LegendSpacingConfig,
)
from src.core.models.visualization.palettes import (
    PALETTE_REGISTRY,
)
from src.core.services.visualization.config_resolver import resolve_config
from src.core.services.visualization.palette_service import (
    get_palette_names,
    is_colorblind_safe,
    resolve_palette,
)
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)
from src.core.models.visualization.typography_config import TypographyConfig

__all__ = [
    # Annotations
    "AnnotationConfig",
    "ReferenceLineConfig",
    # Axes
    "AxisConfig",
    "AxesConfig",
    # Data labels
    "DataLabelConfig",
    # Figure + dimensions
    "FigureConfig",
    "DimensionConfig",
    "MarginsConfig",
    "SeparatorConfig",
    # Legend
    "LegendConfig",
    "LegendSpacingConfig",
    # Palettes
    "PALETTE_REGISTRY",
    "resolve_palette",
    "get_palette_names",
    "is_colorblind_safe",
    # Resolvers
    "resolve_config",
    # Series style
    "SeriesStyleConfig",
    # Traces
    "TraceConfig",
    "BarTraceConfig",
    "LineTraceConfig",
    "ScatterTraceConfig",
    "HistogramTraceConfig",
    "TraceBuildResult",
    # Typography
    "TypographyConfig",
]
