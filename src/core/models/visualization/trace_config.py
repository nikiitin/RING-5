"""
Trace configurations — engine-agnostic descriptions of data traces.

Each trace describes *what* data is plotted and *how* it should look,
without referencing any specific charting library.  The connectors
translate these into ``go.Bar``, ``go.Scatter``, or ``ax.bar()`` calls.

``TraceConfig`` carries positioning data so that the matplotlib connector
does **not** need to reimplement bar grouping math — it gets the exact
x-positions, widths, and offsets pre-computed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class TraceConfig:
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
        legendgroup: Group identifier for linked legend entries.
        custom_data: Arbitrary per-trace metadata.
    """

    name: str = ""
    trace_type: Literal["bar", "line", "scatter", "histogram", "heatmap"] = "bar"
    x: list[str | int | float] = field(default_factory=list)
    y: list[int | float] = field(default_factory=list)
    yaxis: Literal["y", "y2"] = "y"
    color: str = ""
    opacity: float = 1.0
    visible: bool = True
    show_in_legend: bool = True
    legendgroup: str = ""
    custom_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class BarTraceConfig(TraceConfig):
    """Bar-specific trace parameters.

    Carries pre-computed positioning so matplotlib connector can
    place bars directly without reimplementing grouping logic.
    """

    trace_type: Literal["bar", "line", "scatter", "histogram", "heatmap"] = "bar"

    # Bar positioning (pre-computed)
    x_positions: list[float] = field(default_factory=list)  # center of each bar
    bar_width: float = 0.8  # width of each bar
    offset: float = 0.0  # horizontal offset for grouped bars

    # Bar styling
    pattern: str = ""  # hatch pattern: "", "/", "\\", "x", etc.
    border_width: float = 0.0
    border_color: str = ""
    text_values: list[str] | None = None  # data label text
    text_position: Literal["inside", "outside", "auto", "none"] = "none"
    text_angle: float = 0.0
    text_font_size: int = 6

    # Error bars
    error_y: list[float] | None = None


@dataclass
class LineTraceConfig(TraceConfig):
    """Line-specific trace parameters."""

    trace_type: Literal["bar", "line", "scatter", "histogram", "heatmap"] = "line"

    line_width: float = 2.0
    line_dash: Literal["solid", "dash", "dot", "dashdot", "longdash"] = "solid"
    marker_symbol: str = "circle"
    marker_size: int = 6
    show_markers: bool = True
    fill: Literal["none", "tozeroy", "tonexty"] = "none"

    # Error bars
    error_y: list[float] | None = None


@dataclass
class ScatterTraceConfig(TraceConfig):
    """Scatter-specific trace parameters."""

    trace_type: Literal["bar", "line", "scatter", "histogram", "heatmap"] = "scatter"

    marker_symbol: str = "circle"
    marker_size: int = 8
    marker_line_width: float = 0.0
    marker_line_color: str = ""
    colorscale: str | None = None  # for continuous color mapping
    size_values: list[float] | None = None  # bubble chart sizes

    # Error bars
    error_y: list[float] | None = None


@dataclass
class HistogramTraceConfig(TraceConfig):
    """Histogram-specific trace parameters.

    Note: in RING-5, histograms are typically pre-binned and rendered
    as ``BarTraceConfig`` with bin centres as ``x``.  This subclass
    exists for the rare case where raw data is passed directly and
    the binning should be done by the rendering engine.
    """

    trace_type: Literal["bar", "line", "scatter", "histogram", "heatmap"] = "histogram"

    nbins: int = 20
    normalization: Literal["", "percent", "probability", "density"] = ""
    cumulative: bool = False


@dataclass
class HeatmapTraceConfig(TraceConfig):
    """Heatmap-specific trace parameters.

    The ``z`` matrix holds cell values; ``x`` and ``y`` hold
    column and row labels respectively.
    """

    trace_type: Literal["bar", "line", "scatter", "histogram", "heatmap"] = "heatmap"

    # Heatmap-specific label fields (base x/y are unused)
    col_labels: list[str] = field(default_factory=list)  # column (x-axis) labels
    row_labels: list[str] = field(default_factory=list)  # row (y-axis) labels
    z: list[list[float | None]] = field(default_factory=list)
    colorscale: str | list[list[str | float]] = "Viridis"
    show_values: bool = True
    text: list[list[str]] | None = None
    text_font_size: int = 10
    text_color_mode: str = "contrast"  # "auto", "contrast", "custom"
    text_color: str = "#000000"
    totals_position: str = ""  # "", "right", or "top"
    totals_count: int = 0  # number of totals rows/columns (0 or 1)
