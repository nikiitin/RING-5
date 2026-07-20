"""Framework-independent, serializable plot configuration models."""

from typing import Any, TypedDict

# Annotation Shapes


class AnnotationLineConfig(TypedDict, total=False):
    """Line styling for annotation shapes."""

    color: str
    width: int


class AnnotationShapeConfig(TypedDict, total=False):
    """Configuration for a line, circle, or rectangle annotation."""

    type: str  # "line", "circle", "rect"
    x0: float | str
    y0: float | str
    x1: float | str
    y1: float | str
    line: AnnotationLineConfig


# Series Styling


class SeriesStyleConfig(TypedDict, total=False):
    """Color, marker, pattern, and display name for a plotted series."""

    name: str  # Custom display name
    color: str  # Hex color code (e.g., "#FF5733")
    marker_symbol: str  # For scatter plots (circle, square, diamond, ...)
    pattern: str  # For bar charts (/, \\, x, -, |, +, .)


# Relayout Events


class RelayoutEventData(TypedDict, total=False):
    """Tracked Plotly zoom, pan, and legend relayout values."""

    # Axis ranges (zoom/pan)
    xaxis_range: list[float]
    yaxis_range: list[float]
    xaxis_autorange: bool
    yaxis_autorange: bool

    # Legend position (drag)
    legend_x: float
    legend_y: float
    legend_xanchor: str
    legend_yanchor: str
    legend_title_text: str


# Layout & Dimensions


class MarginsConfig(TypedDict, total=False):
    """Plot margin configuration in pixels."""

    top: int
    bottom: int
    left: int
    right: int


class TypographyConfig(TypedDict, total=False):
    """Font size and color configuration for plot text elements."""

    font_size: int
    title_font_size: int
    xaxis_title_font_size: int
    yaxis_title_font_size: int
    legend_font_size: int
    tick_font_size: int
    title_color: str
    xaxis_title_color: str
    yaxis_title_color: str


class PlotDisplayConfig(TypedDict, total=False):
    # [impl->req~ring5.figure.line-styles~1]
    """
    Complete display configuration for a plot.

    This is the **canonical schema** for everything that controls how a plot
    looks. It replaces the ad-hoc Dict[str, Any] that BasePlot.config currently
    uses. Fields are optional (total=False) because plots progressively
    accumulate configuration as the user interacts.

    Sections:
        - Identity: x, y, title, labels
        - Appearance: colors, dimensions, margins, typography
        - Interaction: zoom ranges, legend positions
        - Advanced: ordering, shapes, error bars, export
    """

    # Identity & Axes
    x: str  # X-axis column name
    y: str  # Y-axis column name
    title: str  # Plot title text
    xlabel: str  # X-axis label
    ylabel: str  # Y-axis label
    legend_title: str  # Legend title text

    # Grouping
    color: str | None  # Color-by column
    group: str | None  # Group-by column (grouped/stacked bars)

    # Column Metadata (computed, not user-set)
    numeric_cols: list[str]
    categorical_cols: list[str]

    # Dimensions & Layout
    width: int  # Plot width in pixels
    height: int  # Plot height in pixels
    margins: MarginsConfig
    template: str  # Plotly template name

    # Typography
    typography: TypographyConfig

    # Colors & Background
    paper_bgcolor: str
    plot_bgcolor: str
    show_grid: bool
    grid_color: str
    grid_width: int

    # Axis Configuration
    xaxis_tickangle: int  # Label rotation (-90 to 90)
    xaxis_dtick: float | None  # X-axis step (None = auto)
    yaxis_dtick: float | None  # Y-axis step (None = auto)
    xaxis_labels: dict[str, str]  # Renamed x-axis tick labels

    # Ordering
    xaxis_order: list[str] | None  # Custom x-axis category order
    group_order: list[str] | None  # Custom group order
    legend_order: list[str] | None  # Custom legend item order

    # Interactive State (from relayout events)
    range_x: list[float] | None  # Current zoom range for x-axis
    range_y: list[float] | None  # Current zoom range for y-axis
    legend_x: float | None  # Legend x position
    legend_y: float | None  # Legend y position
    legend_xanchor: str | None  # Legend x anchor
    legend_yanchor: str | None  # Legend y anchor

    # Legend Labels
    legend_labels: dict[str, str] | None  # Original → display label

    # Series Styling
    series_styles: dict[str, SeriesStyleConfig]

    # Annotations
    shapes: list[AnnotationShapeConfig]

    # Error Bars
    show_error_bars: bool

    # Bar-specific
    bargap: float  # Spacing between bars
    bargroupgap: float  # Spacing between groups
    bar_border_width: float  # Border width for stacked segments

    # Line-specific
    line_shape: str
    line_dash: str
    line_width: float
    show_markers: bool
    marker_symbol: str
    connect_gaps: bool

    # Box-specific
    orientation: str
    quartile_method: str
    whisker_mode: str
    whisker_multiplier: float
    whisker_percentiles: list[float]
    point_mode: str
    jitter: float
    point_position: float
    box_width: float
    whisker_cap_width: float
    notched: bool
    show_mean: bool

    # Violin-specific
    bandwidth_method: str
    bandwidth_scale: float
    density_span: str
    density_scale: str
    violin_side: str
    summary_mode: str
    violin_width: float

    # ECDF-specific
    ecdf_complementary: bool
    ecdf_y_mode: str
    ecdf_markers: bool
    marker_size: int

    # Area-specific
    area_mode: str
    area_interpolation: str
    area_missing: str
    area_opacity: float

    # Radar-specific
    radar_scale_mode: str
    radar_min: float
    radar_max: float
    radar_start_angle: float
    radar_clockwise: bool
    radar_fill: bool
    radar_markers: bool
    radar_opacity: float
    radar_line_width: float

    # Waterfall-specific
    waterfall_absolute: list[str]
    waterfall_subtotals: list[str]
    waterfall_final_total: bool
    waterfall_total_label: str
    waterfall_connectors: bool
    waterfall_connector_color: str
    waterfall_connector_width: float
    waterfall_increasing_color: str
    waterfall_decreasing_color: str
    waterfall_total_color: str
    waterfall_bar_width: float
    waterfall_opacity: float
    waterfall_show_values: bool
    waterfall_number_format: str

    # Sankey-specific
    sankey_source: str
    sankey_target: str
    sankey_value: str
    sankey_label: str | None
    sankey_node_labels: dict[str, str]
    sankey_label_mode: str
    sankey_show_link_labels: bool
    sankey_number_format: str
    sankey_arrangement: str
    sankey_node_positions: dict[str, list[float]]
    sankey_node_pad: int
    sankey_node_thickness: int
    sankey_color_mode: str
    sankey_link_color: str
    sankey_link_opacity: float
    sankey_node_line_color: str
    sankey_node_line_width: float

    # Parallel-coordinates-specific
    parallel_dimensions: list[str]
    parallel_color: str | None
    parallel_labels: dict[str, str]
    parallel_range_mode: str
    parallel_ranges: dict[str, list[float]]
    parallel_brush_dimension: str | None
    parallel_brush_range: list[float] | None
    parallel_brushes: dict[str, list[float]]
    parallel_colorscale: str
    parallel_reverse_colorscale: bool
    parallel_color_min: float
    parallel_color_max: float
    parallel_show_colorbar: bool
    parallel_colorbar_title: str
    parallel_line_color: str
    parallel_unselected_opacity: float

    # Export
    download_format: str  # "html", "png", "pdf", "svg"
    export_scale: int  # 1, 2, or 3

    # Interactivity
    enable_editable: bool  # Enable drag/edit on plot

    # Margins (flat keys consumed by ConfigSpecBuilder → FigureConfig)
    margin_t: int
    margin_b: int
    margin_l: int
    margin_r: int
    margin_pad: int
    automargin: bool

    # Axis colors
    axis_color: str
    xaxis_tickfont_size: int
    xaxis_tickfont_color: str
    yaxis_tickfont_size: int
    yaxis_tickfont_color: str
    xaxis_title_font_size: int
    yaxis_title_font_size: int
    yaxis_title_standoff: int
    yaxis_title_vshift: int

    # Title font
    title_font_size: int

    # Legend styling
    legend_orientation: str
    legend_font_color: str
    legend_font_size: int
    legend_title_font_color: str
    legend_title_font_size: int
    legend_bgcolor: str
    legend_border_color: str
    legend_border_width: int
    legend_itemsizing: str
    legend_ncols: int
    legend_col_width: int

    # Data labels
    show_values: bool
    text_format: str
    text_position: str
    text_color_mode: str
    text_color: str
    text_rotation: int
    text_anchor: str
    text_font_size: int
    text_constraint: bool
    text_display_logic: str
    text_threshold: float

    # Color palette
    color_palette: str
    accessibility_mode: bool
    enable_stripes: bool
    figure_theme_id: str
    figure_theme_name: str
    figure_theme_context: str

    # Reference line
    reference_line_enabled: bool
    reference_line_y: float
    reference_line_color: str
    reference_line_width: float
    reference_line_style: str

    # Filter columns
    x_filter: list[str] | None
    group_filter: list[str] | None


# Plot configuration accepts extension keys beyond PlotDisplayConfig.
PlotConfig = dict[str, Any]
