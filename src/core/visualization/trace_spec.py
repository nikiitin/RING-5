"""
Trace specifications — engine-agnostic descriptions of data traces.

Each trace describes *what* data is plotted and *how* it should look,
without referencing any specific charting library.  The connectors
translate these into ``go.Bar``, ``go.Scatter``, or ``ax.bar()`` calls.

``TraceSpec`` carries positioning data so that the matplotlib connector
does **not** need to reimplement bar grouping math — it gets the exact
x-positions, widths, and offsets pre-computed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union


@dataclass
class TraceSpec:
    """Base trace specification shared by all trace types.

    Attributes:
        name: Legend label for this trace.
        trace_type: Discriminator for sub-type dispatch.
        x: X-axis data values (categories or numeric).
        y: Y-axis data values (always numeric).
        yaxis: Which Y-axis this trace belongs to ("y" or "y2").
        color: Trace color (hex, rgb, or named).
        opacity: Fill/marker opacity (0–1).
        visible: Whether the trace is visible.
        show_in_legend: Whether to include in legend.
        custom_data: Arbitrary per-trace metadata.
    """

    name: str = ""
    trace_type: Literal["bar", "line", "scatter", "histogram"] = "bar"
    x: List[Any] = field(default_factory=list)
    y: List[Union[int, float]] = field(default_factory=list)
    yaxis: Literal["y", "y2"] = "y"
    color: str = ""
    opacity: float = 1.0
    visible: bool = True
    show_in_legend: bool = True
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BarTraceSpec(TraceSpec):
    """Bar-specific trace parameters.

    Carries pre-computed positioning so matplotlib connector can
    place bars directly without reimplementing grouping logic.
    """

    trace_type: Literal["bar", "line", "scatter", "histogram"] = "bar"

    # ── Bar positioning (pre-computed) ───────────────────────────
    x_positions: List[float] = field(default_factory=list)  # center of each bar
    bar_width: float = 0.8  # width of each bar
    offset: float = 0.0  # horizontal offset for grouped bars

    # ── Bar styling ──────────────────────────────────────────────
    pattern: str = ""  # hatch pattern: "", "/", "\\", "x", etc.
    border_width: float = 0.0
    border_color: str = ""
    text_values: Optional[List[str]] = None  # data label text
    text_position: Literal[
        "inside", "outside", "auto", "none"
    ] = "none"
    text_angle: float = 0.0
    text_font_size: int = 6

    # ── Error bars ───────────────────────────────────────────────
    error_y: Optional[List[float]] = None


@dataclass
class LineTraceSpec(TraceSpec):
    """Line-specific trace parameters."""

    trace_type: Literal["bar", "line", "scatter", "histogram"] = "line"

    line_width: float = 2.0
    line_dash: Literal["solid", "dash", "dot", "dashdot", "longdash"] = "solid"
    marker_symbol: str = "circle"
    marker_size: int = 6
    show_markers: bool = True
    fill: Literal["none", "tozeroy", "tonexty"] = "none"


@dataclass
class ScatterTraceSpec(TraceSpec):
    """Scatter-specific trace parameters."""

    trace_type: Literal["bar", "line", "scatter", "histogram"] = "scatter"

    marker_symbol: str = "circle"
    marker_size: int = 8
    marker_line_width: float = 0.0
    marker_line_color: str = ""
    colorscale: Optional[str] = None  # for continuous color mapping
    size_values: Optional[List[float]] = None  # bubble chart sizes
