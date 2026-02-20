"""
Engine-agnostic visualization specification module (Layer B — Domain).

This module provides a shared figure specification model (`FigureConfig`) that
both Plotly and matplotlib rendering engines consume. It has **zero** UI or
engine-specific dependencies — only standard library and dataclasses.

Architecture:
    FigureConfig (top-level container)
    ├── DimensionConfig      — width, height, DPI, margins
    ├── TypographyConfig      — font family + per-element sizes/bold
    ├── AxesConfig            — primary X/Y + optional secondary Y
    │   ├── AxisConfig (x)
    │   ├── AxisConfig (y)
    │   └── AxisConfig (y2, optional)
    ├── List[LegendConfig]    — uniform model for legend1/2/3
    ├── List[TraceConfig]     — bar, line, scatter trace descriptions
    ├── List[AnnotationConfig]— text annotations + boxed annotations
    ├── SeparatorConfig       — group separator lines
    └── metadata: Dict      — arbitrary key-value (benchmark, seed, etc.)

Sentinel pattern:
    The value ``-1`` (or ``-1.0`` for floats) means "inherit from parent".
    Call ``resolvers.resolve_config()`` to walk the tree and fill in inherited
    values before passing to any engine connector.
"""

from src.core.models.visualization.annotation_config import AnnotationConfig, ReferenceLineConfig
from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
from src.core.models.visualization.data_label_config import DataLabelConfig
from src.core.models.visualization.figure_config import (
    DimensionConfig,
    FigureConfig,
    MarginsConfig,
    SeparatorConfig,
)
from src.core.models.visualization.legend_config import LegendConfig, LegendSpacingConfig
from src.core.models.visualization.resolvers import resolve_config
from src.core.models.visualization.series_style_config import SeriesStyleConfig
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    HistogramTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)
from src.core.models.visualization.typography_config import TypographyConfig

__all__ = [
    # Top-level
    "FigureConfig",
    # Sub-specs
    "DimensionConfig",
    "MarginsConfig",
    "TypographyConfig",
    "AxesConfig",
    "AxisConfig",
    "LegendConfig",
    "LegendSpacingConfig",
    "TraceConfig",
    "BarTraceConfig",
    "HistogramTraceConfig",
    "LineTraceConfig",
    "ScatterTraceConfig",
    "AnnotationConfig",
    "ReferenceLineConfig",
    "DataLabelConfig",
    "SeriesStyleConfig",
    "SeparatorConfig",
    # Resolution
    "resolve_config",
]
