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

TraceType = Literal[
    "bar",
    "line",
    "scatter",
    "histogram",
    "heatmap",
    "box",
    "violin",
    "radar",
    "waterfall",
    "sankey",
]


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
    trace_type: TraceType = "bar"
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

    trace_type: TraceType = "bar"

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

    trace_type: TraceType = "line"

    line_width: float = 2.0
    line_dash: Literal["solid", "dash", "dot", "dashdot", "longdash"] = "solid"
    line_shape: Literal["linear", "spline", "hv", "vh", "hvh", "vhv"] = "linear"
    marker_symbol: str = "circle"
    marker_size: int = 6
    show_markers: bool = True
    fill: Literal["none", "tozeroy", "tonexty"] = "none"
    fill_base: list[float] | None = None

    # Error bars
    error_y: list[float] | None = None


@dataclass
class ScatterTraceConfig(TraceConfig):
    """Scatter-specific trace parameters."""

    trace_type: TraceType = "scatter"

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

    trace_type: TraceType = "histogram"

    nbins: int = 20
    normalization: Literal["", "percent", "probability", "density"] = ""
    cumulative: bool = False


@dataclass
class HeatmapTraceConfig(TraceConfig):
    """Heatmap-specific trace parameters.

    The ``z`` matrix holds cell values; ``x`` and ``y`` hold
    column and row labels respectively.
    """

    trace_type: TraceType = "heatmap"

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


@dataclass
class BoxTraceConfig(TraceConfig):
    # [impl->req~ring5.plot.box~1]
    """Precomputed distribution summary shared by both rendering engines."""

    trace_type: TraceType = "box"
    values: list[float] = field(default_factory=list)
    category: str = ""
    orientation: Literal["vertical", "horizontal"] = "vertical"
    quartile_method: Literal["linear", "inclusive", "exclusive"] = "linear"
    q1: float = 0.0
    median: float = 0.0
    q3: float = 0.0
    notch_lower: float = 0.0
    notch_upper: float = 0.0
    lower_whisker: float = 0.0
    upper_whisker: float = 0.0
    mean: float = 0.0
    outliers: list[float] = field(default_factory=list)
    point_mode: Literal["outliers", "all", "none"] = "outliers"
    jitter: float = 0.25
    point_position: float = 0.0
    position: float = 0.0
    category_position: int = 0
    box_width: float = 0.6
    whisker_cap_width: float = 0.5
    notched: bool = False
    show_mean: bool = False


@dataclass
class ViolinTraceConfig(TraceConfig):
    # [impl->req~ring5.plot.violin~1]
    """Precomputed kernel density and summary shared by both renderers."""

    trace_type: TraceType = "violin"
    values: list[float] = field(default_factory=list)
    category: str = ""
    orientation: Literal["vertical", "horizontal"] = "vertical"
    density_coordinates: list[float] = field(default_factory=list)
    density: list[float] = field(default_factory=list)
    bandwidth: float = 1.0
    bandwidth_method: Literal["scott", "silverman"] = "scott"
    density_span: Literal["soft", "hard"] = "soft"
    density_scale: Literal["width", "count"] = "width"
    side: Literal["both", "positive", "negative"] = "both"
    point_mode: Literal["all", "none"] = "none"
    jitter: float = 0.15
    position: float = 0.0
    category_position: int = 0
    violin_width: float = 0.8
    width_scale: float = 1.0
    q1: float = 0.0
    median: float = 0.0
    q3: float = 0.0
    mean: float = 0.0
    show_box: bool = True
    show_mean: bool = False


@dataclass
class RadarTraceConfig(TraceConfig):
    # [impl->req~ring5.plot.radar~1]
    """Closed radial series with a scale shared by every radar trace."""

    trace_type: TraceType = "radar"
    categories: list[str] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    radial_min: float = 0.0
    radial_max: float = 1.0
    start_angle: float = 90.0
    clockwise: bool = True
    fill_area: bool = True
    show_markers: bool = True
    marker_size: int = 6
    line_width: float = 2.0


@dataclass
class WaterfallTraceConfig(TraceConfig):
    # [impl->req~ring5.plot.waterfall~1]
    """Precomputed running-total bars and connectors for a waterfall chart."""

    trace_type: TraceType = "waterfall"
    categories: list[str] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    measures: list[Literal["relative", "absolute", "total"]] = field(default_factory=list)
    kinds: list[Literal["relative", "absolute", "subtotal", "total"]] = field(default_factory=list)
    starts: list[float] = field(default_factory=list)
    ends: list[float] = field(default_factory=list)
    connector_visible: bool = True
    connector_color: str = "#666666"
    connector_width: float = 1.0
    increasing_color: str = "#2ca02c"
    decreasing_color: str = "#d62728"
    total_color: str = "#4c78a8"
    bar_width: float = 0.7
    show_values: bool = True
    value_labels: list[str] = field(default_factory=list)


@dataclass
class SankeyTraceConfig(TraceConfig):
    # [impl->req~ring5.plot.sankey~1]
    """Validated nodes, links, labels, colors, and positions for a Sankey diagram."""

    trace_type: TraceType = "sankey"
    node_labels: list[str] = field(default_factory=list)
    source_indices: list[int] = field(default_factory=list)
    target_indices: list[int] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    link_labels: list[str] = field(default_factory=list)
    node_colors: list[str] = field(default_factory=list)
    link_colors: list[str] = field(default_factory=list)
    node_x: list[float] = field(default_factory=list)
    node_y: list[float] = field(default_factory=list)
    arrangement: Literal["snap", "perpendicular", "freeform", "fixed"] = "snap"
    node_pad: int = 15
    node_thickness: int = 20
    node_line_color: str = "#333333"
    node_line_width: float = 0.5
    link_opacity: float = 0.35
    show_node_labels: bool = True
    show_link_labels: bool = False
