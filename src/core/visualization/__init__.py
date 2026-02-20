"""
Engine-agnostic visualization specification module (Layer B — Domain).

This module provides a shared figure specification model (`FigureSpec`) that
both Plotly and matplotlib rendering engines consume. It has **zero** UI or
engine-specific dependencies — only standard library and dataclasses.

Architecture:
    FigureSpec (top-level container)
    ├── DimensionsSpec      — width, height, DPI, margins
    ├── TypographySpec      — font family + per-element sizes/bold
    ├── AxesSpec            — primary X/Y + optional secondary Y
    │   ├── AxisSpec (x)
    │   ├── AxisSpec (y)
    │   └── AxisSpec (y2, optional)
    ├── List[LegendSpec]    — uniform model for legend1/2/3
    ├── List[TraceSpec]     — bar, line, scatter trace descriptions
    ├── List[AnnotationSpec]— text annotations + boxed annotations
    ├── SeparatorSpec       — group separator lines
    └── metadata: Dict      — arbitrary key-value (benchmark, seed, etc.)

Sentinel pattern:
    The value ``-1`` (or ``-1.0`` for floats) means "inherit from parent".
    Call ``resolvers.resolve_spec()`` to walk the tree and fill in inherited
    values before passing to any engine connector.
"""

from src.core.visualization.annotation_spec import AnnotationSpec, ReferenceLineSpec
from src.core.visualization.axis_spec import AxesSpec, AxisSpec
from src.core.visualization.data_label_spec import DataLabelSpec
from src.core.visualization.figure_spec import (
    DimensionsSpec,
    FigureSpec,
    MarginsSpec,
    SeparatorSpec,
)
from src.core.visualization.legend_spec import LegendSpacingSpec, LegendSpec
from src.core.visualization.resolvers import resolve_spec
from src.core.visualization.series_style_spec import SeriesStyleSpec
from src.core.visualization.trace_spec import (
    BarTraceSpec,
    HistogramTraceSpec,
    LineTraceSpec,
    ScatterTraceSpec,
    TraceSpec,
)
from src.core.visualization.typography_spec import TypographySpec

__all__ = [
    # Top-level
    "FigureSpec",
    # Sub-specs
    "DimensionsSpec",
    "MarginsSpec",
    "TypographySpec",
    "AxesSpec",
    "AxisSpec",
    "LegendSpec",
    "LegendSpacingSpec",
    "TraceSpec",
    "BarTraceSpec",
    "HistogramTraceSpec",
    "LineTraceSpec",
    "ScatterTraceSpec",
    "AnnotationSpec",
    "ReferenceLineSpec",
    "DataLabelSpec",
    "SeriesStyleSpec",
    "SeparatorSpec",
    # Resolution
    "resolve_spec",
]
