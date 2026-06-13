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
from typing import Any, Literal

from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.trace_config import TraceConfig


@dataclass
class SeparatorLine:
    """A full-height vertical separator line at a data-space x position.

    Engine-agnostic: the Plotly connector renders it as a ``layout.shapes``
    line, the matplotlib connector as a blended-transform vertical line — so
    bar-group separators appear in both engines.
    """

    x: float
    color: str = "#E0E0E0"
    dash: Literal["solid", "dash", "dot", "dashdot"] = "dash"
    width: float = 1.0


@dataclass
class RuleLine:
    """A horizontal rule spanning ``[x0, x1]`` in data space at a paper-fraction y.

    Used for category super-group span rules (the LaTeX ``\\cmidrule`` look,
    drawn under each run of same-group categories, below the axis). Rendered
    by Plotly as a ``layout.shapes`` line with ``yref="paper"`` and by
    matplotlib as a blended-transform horizontal line with clipping off.
    """

    x0: float
    x1: float
    y: float
    color: str = "#444444"
    width: float = 1.0


@dataclass
class ShadedRegion:
    """A full-height background band spanning ``[x0, x1]`` in data space.

    Used for alternating-category shading; rendered by Plotly as a
    ``layout.shapes`` rect and by matplotlib as ``axvspan``.
    """

    x0: float
    x1: float
    color: str = "#F5F5F5"
    opacity: float = 0.5


@dataclass
class TraceBuildResult:
    """Complete output from a plot type's ``create_traces()`` method.

    Attributes:
        traces: Engine-agnostic trace specifications.
        annotations: Text annotations (group labels, tertiary legends, etc.).
        layout_annotations: Raw annotation dicts passed straight to layout.
        separator_lines: Engine-agnostic vertical separators between bar groups.
        rule_lines: Engine-agnostic horizontal span rules (category super-groups).
        shaded_regions: Engine-agnostic alternating-category background bands.
        barmode: Bar grouping mode (``"group"``, ``"stack"``, etc.).
        custom_x_ticks: Optional override for x-axis tick values/labels.
            Expected keys: ``"vals"`` (``List[float]``), ``"text"``
            (``List[str]``).
        secondary_y: Whether a secondary Y-axis is used.
    """

    traces: Sequence[TraceConfig] = field(default_factory=list)
    annotations: list[AnnotationConfig] = field(default_factory=list)
    layout_annotations: list[dict[str, Any]] = field(default_factory=list)
    separator_lines: list[SeparatorLine] = field(default_factory=list)
    rule_lines: list[RuleLine] = field(default_factory=list)
    shaded_regions: list[ShadedRegion] = field(default_factory=list)
    barmode: str = "group"
    custom_x_ticks: dict[str, list[float] | list[str] | list[bool]] | None = None
    secondary_y: bool = False
