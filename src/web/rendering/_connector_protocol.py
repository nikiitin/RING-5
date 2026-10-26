"""Shared trace and styling contracts for native rendering connectors.

``STYLING_PIPELINE_ORDER`` is the set of named styling steps every connector
(``FigureSpecToPlotly``, ``FigureSpecToMatplotlib``) must implement so the two
engines produce equivalent figures. The Matplotlib connector — verified by
``test_matplotlib_implements_every_pipeline_step`` — applies them in exactly
this order via ``_apply_<step>`` methods.

Two styling operations run as a sub-phase that is not a named step here:
``_apply_series_styling`` (global per-index) and ``_apply_trace_overrides``
(per trace name). Both connectors apply them after ``color_palette`` and default
``hatching`` so explicit overrides win. Matplotlib builds legends after these
sub-phases so native swatches reflect the final styles.
"""

from collections.abc import Sequence

from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    BoxTraceConfig,
    HeatmapTraceConfig,
    LineTraceConfig,
    ParallelCoordinatesTraceConfig,
    RadarTraceConfig,
    SankeyTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
    ViolinTraceConfig,
    WaterfallTraceConfig,
)

_SUPPORTED_TRACE_TYPES = (
    BarTraceConfig,
    BoxTraceConfig,
    HeatmapTraceConfig,
    LineTraceConfig,
    ParallelCoordinatesTraceConfig,
    RadarTraceConfig,
    SankeyTraceConfig,
    ScatterTraceConfig,
    ViolinTraceConfig,
    WaterfallTraceConfig,
)


def uses_heatmap_panels(result: TraceBuildResult) -> bool:
    """Whether every trace belongs to a separate heatmap panel."""
    return (
        len(result.traces) > 1
        and not result.secondary_y
        and all(isinstance(trace, HeatmapTraceConfig) for trace in result.traces)
    )


def validate_trace_types(traces: Sequence[TraceConfig]) -> None:
    """Reject unsupported families before an engine creates or draws a figure.

    Args:
        traces: Neutral traces, including any intentionally hidden traces.

    Raises:
        TypeError: A trace has no supported concrete family.
    """
    # [impl->req~ring5.render.engine-independent-traces~1]
    for trace in traces:
        if not isinstance(trace, _SUPPORTED_TRACE_TYPES):
            raise TypeError(f"Unsupported trace type: {type(trace).__name__}.")


def validate_annotation_types(annotations: Sequence[AnnotationConfig]) -> None:
    """Reject unsupported annotation objects before copying or drawing them.

    Args:
        annotations: Typed annotations, including entries with empty text.

    Raises:
        TypeError: An entry is not an AnnotationConfig or its subclass.
    """
    # [impl->req~ring5.render.engine-independent-traces~1]
    for annotation in annotations:
        if not isinstance(annotation, AnnotationConfig):
            raise TypeError(f"Unsupported annotation type: {type(annotation).__name__}.")


STYLING_PIPELINE_ORDER: tuple[str, ...] = (
    "backgrounds",
    "font_family",
    "color_palette",
    "title",
    "axis_labels",
    "axis_ticks",
    "axis_ranges",
    "axis_colors",
    "grids",
    "hatching",
    "legends",
    "reference_lines",
    "data_labels",
    "annotations",
    "margins",
)
