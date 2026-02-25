"""
Trace build result — aggregates all engine-agnostic output from a plot type.

``TraceBuildResult`` is the return type of ``BasePlot.create_traces()``.
It bundles the data traces with layout-level metadata (barmode, custom
tick positions, separator shapes, and annotations) that the downstream
connector needs to build the final figure.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from src.core.models.plot_config import ShapeConfig
from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.trace_config import TraceConfig


@dataclass
class TraceBuildResult:
    """Complete output from a plot type's ``create_traces()`` method.

    Attributes:
        traces: Engine-agnostic trace specifications.
        annotations: Text annotations (group labels, tertiary legends, etc.).
        layout_annotations: Raw annotation dicts passed straight to layout.
        shapes: Plotly-format shape dicts (separators, shading rectangles).
        barmode: Bar grouping mode (``"group"``, ``"stack"``, etc.).
        custom_x_ticks: Optional override for x-axis tick values/labels.
            Expected keys: ``"vals"`` (``List[float]``), ``"text"``
            (``List[str]``).
        secondary_y: Whether a secondary Y-axis is used.
    """

    traces: Sequence[TraceConfig] = field(default_factory=list)
    annotations: list[AnnotationConfig] = field(default_factory=list)
    layout_annotations: list[dict[str, Any]] = field(default_factory=list)
    shapes: list[ShapeConfig] = field(default_factory=list)
    barmode: str = "group"
    custom_x_ticks: dict[str, list[float] | list[str] | list[bool]] | None = None
    secondary_y: bool = False
