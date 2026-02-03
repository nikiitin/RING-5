"""
Matplotlib Converter - Converts Plotly figures to Matplotlib for LaTeX export.

Provides high-quality PDF/PGF/EPS export with proper LaTeX font rendering,
dimension control, and layout preservation.
"""

import io
import logging
from typing import Any, Dict, List, Literal, Tuple

import matplotlib
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from matplotlib import rc
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from src.plotting.export.converters.base_converter import BaseConverter
from src.plotting.export.converters.layout_mapper import LayoutMapper
from src.plotting.export.presets.preset_schema import ExportResult, LaTeXPreset

logger = logging.getLogger(__name__)

# Use non-interactive backend to avoid display issues
matplotlib.use("Agg")


class MatplotlibConverter(BaseConverter):
    """
    Converts Plotly figures to Matplotlib for LaTeX-optimized export.

    Features:
    - LaTeX font rendering with Computer Modern or journal-specific fonts
    - Precise dimension control (single/double column sizes)
    - Layout preservation (legend position, zoom, colors from Plotly)
    - Multiple export formats: PDF (embedded fonts), PGF (LaTeX), EPS (legacy)
    """

    def __init__(self, preset: LaTeXPreset) -> None:
        """
        Initialize converter with LaTeX preset.

        Args:
            preset: LaTeX export configuration
        """
        super().__init__(preset)
        self.layout_mapper = LayoutMapper()
        self._barmode: str = "group"  # Track bar layout mode
        self._bar_traces: List[Any] = []  # Track bar traces for positioning
        self._categorical_labels: List[str] = []  # Track x-axis labels

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported export formats.

        Returns:
            List of format strings
        """
        return ["pdf", "pgf", "eps"]

    def convert(self, fig: go.Figure, format: str) -> ExportResult:
        """
        Convert Plotly figure to Matplotlib and export to specified format.

        Args:
            fig: Plotly Figure with user's interactive configuration
            format: Export format (pdf, pgf, eps)

        Returns:
            ExportResult with data or error

        Raises:
            ValueError: If format is unsupported
        """
        if format not in self.get_supported_formats():
            raise ValueError(
                f"Unsupported format: {format}. "
                f"Supported formats: {', '.join(self.get_supported_formats())}"
            )

        try:
            # Validate figure has data
            if not self.validate_figure(fig):
                raise ValueError(
                    "Cannot export empty figure. "
                    "Figure must contain at least one trace with data."
                )

            # Step 1: Create Matplotlib figure with LaTeX dimensions
            mpl_fig, mpl_ax = self._create_matplotlib_figure()

            # Step 2: Configure LaTeX rendering
            self._configure_latex_rendering()

            # Step 2.5: Extract barmode from layout
            if hasattr(fig, "layout") and hasattr(fig.layout, "barmode"):
                self._barmode = str(fig.layout.barmode) if fig.layout.barmode else "group"
            else:
                self._barmode = "group"
            self._bar_traces = []
            self._categorical_labels = []

            # Step 3: Convert Plotly traces to Matplotlib
            traces_converted = self._convert_traces(fig, mpl_ax)

            # Step 4: Apply layout from Plotly (preserve user decisions)
            layout_preserved = self._apply_layout(fig, mpl_ax)

            # Step 5: Export to specified format
            # Validate format is supported
            if format not in ["pdf", "pgf", "eps"]:
                raise ValueError(f"Unsupported format: {format}")

            data = self._export_figure(mpl_fig, format)  # type: ignore[arg-type]

            # Prepare metadata
            metadata: Dict[str, Any] = {
                "width_inches": self.preset["width_inches"],
                "height_inches": self.preset["height_inches"],
                "dpi": self.preset["dpi"],
                "font_family": self.preset["font_family"],
                "line_width": self.preset["line_width"],
                "marker_size": self.preset["marker_size"],
                "traces_converted": traces_converted,
                "layout_preserved": layout_preserved,
                "barmode": self._barmode,
                "bar_traces_count": len(self._bar_traces),
            }

            return ExportResult(
                success=True,
                data=data,
                format=format,
                error=None,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Matplotlib conversion failed: {e}", exc_info=True)
            return ExportResult(
                success=False,
                data=None,
                format=format,
                error=str(e),
                metadata={},
            )
        finally:
            # CRITICAL: Clean up matplotlib state
            plt.close("all")

    def _create_matplotlib_figure(self) -> Tuple[Figure, Axes]:
        """
        Create Matplotlib figure with LaTeX-specified dimensions.

        Returns:
            Tuple of (Figure, Axes)
        """
        width = self.preset["width_inches"]
        height = self.preset["height_inches"]
        dpi = self.preset["dpi"]

        fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)

        return fig, ax

    def _configure_latex_rendering(self) -> None:
        """
        Configure Matplotlib for LaTeX text rendering.

        Enables LaTeX rendering for publication-quality output.
        Requires full LaTeX installation with necessary font packages.

        Required system packages:
        - texlive-latex-base
        - texlive-fonts-recommended
        - texlive-fonts-extra
        - cm-super

        Install with:
            sudo apt-get install texlive-fonts-recommended texlive-fonts-extra cm-super
        """
        # Enable LaTeX text rendering
        rc("text", usetex=True)

        # Proper LaTeX preamble for font encoding and math support
        # This ensures \mathdefault and other font commands work correctly
        # Note: Unicode characters in labels should be avoided
        preamble = (
            r"\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}"
            r"\usepackage{amsmath}\usepackage{amssymb}"
        )
        rc("text.latex", preamble=preamble)

        logger.info("LaTeX text rendering enabled with full font support")

        # Font configuration
        rc("font", family=self.preset["font_family"])
        rc("font", size=self.preset["font_size_base"])
        rc("axes", labelsize=self.preset.get("font_size_xlabel", 9))  # X label default
        rc("axes", titlesize=self.preset["font_size_title"])
        rc("xtick", labelsize=self.preset["font_size_ticks"])
        rc("ytick", labelsize=self.preset["font_size_ticks"])
        rc("legend", fontsize=self.preset.get("font_size_legend", 8))

        # Line and marker defaults
        rc("lines", linewidth=self.preset["line_width"])
        rc("lines", markersize=self.preset["marker_size"])

    def _convert_traces(self, plotly_fig: go.Figure, ax: Axes) -> int:
        """
        Convert all Plotly traces to Matplotlib.

        Args:
            plotly_fig: Source Plotly figure
            ax: Target Matplotlib axes

        Returns:
            Number of traces converted
        """
        traces_converted = 0

        # First pass: collect bar traces
        for trace in plotly_fig.data:
            if trace.type == "bar":
                self._bar_traces.append(trace)

        # Second pass: convert traces with proper positioning
        for idx, trace in enumerate(plotly_fig.data):
            try:
                if trace.type == "bar":
                    self._convert_bar_trace(trace, ax, idx)
                    traces_converted += 1
                elif trace.type == "scatter":
                    if trace.mode and "markers" in trace.mode:
                        self._convert_scatter_trace(trace, ax)
                        traces_converted += 1
                    elif trace.mode and "lines" in trace.mode:
                        self._convert_line_trace(trace, ax)
                        traces_converted += 1
                    else:
                        # Default to line plot
                        self._convert_line_trace(trace, ax)
                        traces_converted += 1
                else:
                    logger.warning(f"Unsupported trace type: {trace.type}")
            except Exception as e:
                logger.error(f"Failed to convert trace {trace.name}: {e}")

        return traces_converted

    def _convert_bar_trace(self, trace: go.Bar, ax: Axes, trace_idx: int) -> None:
        """
        Convert Plotly Bar trace to Matplotlib bar chart with proper grouped/stacked positioning.

        Handles three cases:
        1. Categorical x-axis (strings): Use integer positions with labels
        2. Numeric x-axis with gaps (grouped-stacked): Use actual numeric positions
        3. Simple numeric x-axis: Use values as-is

        Args:
            trace: Plotly Bar trace
            ax: Matplotlib axes
            trace_idx: Index of this trace in the figure

        Uses bar_width_scale from preset to adjust bar widths.
        """
        # Get bar width scale from preset
        bar_width_scale = self.preset.get("bar_width_scale", 1.0)

        x = trace.x if trace.x is not None else []
        y = trace.y if trace.y is not None else []

        # Convert to list if needed (handles numpy arrays, pandas Series, etc.)
        if hasattr(x, "tolist"):
            x = x.tolist()
        if hasattr(y, "tolist"):
            y = y.tolist()

        # Ensure we have lists
        if not isinstance(x, list):
            x = list(x) if x is not None else []
        if not isinstance(y, list):
            y = list(y) if y is not None else []

        # Handle color
        color = None
        if trace.marker and trace.marker.color:
            color = trace.marker.color

        # Check if x contains strings (categorical data)
        has_categorical_x = False
        has_numeric_x = False
        try:
            if x and len(x) > 0:
                first_x = x[0]
                has_categorical_x = isinstance(first_x, (str, bytes)) or (
                    hasattr(first_x, "__class__")
                    and first_x.__class__.__name__ in ("str", "str_", "bytes_")
                )
                # Check if numeric
                if not has_categorical_x:
                    try:
                        float(first_x)
                        has_numeric_x = True
                    except (ValueError, TypeError):
                        pass
        except (TypeError, IndexError):
            has_categorical_x = False

        if has_categorical_x:
            # Case 1: Categorical x-axis (strings) - convert to integer positions
            # Store labels from first trace
            if trace_idx == 0 or not self._categorical_labels:
                self._categorical_labels = [str(label) for label in x]

            # Calculate positioning based on barmode
            n_bars = len(self._bar_traces)
            n_positions = len(x)
            x_positions = list(range(n_positions))

            if self._barmode == "stack":
                # Stacked bars: all at same position
                # Need to calculate bottom positions
                bottom = [0.0] * n_positions
                if trace_idx > 0:
                    # Calculate cumulative sum from previous traces
                    for prev_trace in self._bar_traces[:trace_idx]:
                        prev_y = prev_trace.y if prev_trace.y is not None else []
                        if hasattr(prev_y, "tolist"):
                            prev_y = prev_y.tolist()
                        for i, val in enumerate(prev_y):
                            if i < len(bottom):
                                bottom[i] += float(val) if val is not None else 0.0

                ax.bar(
                    x=x_positions,
                    height=y,
                    bottom=bottom,
                    label=trace.name or "",
                    color=color,
                    width=0.8 * bar_width_scale,
                    edgecolor="white",
                    linewidth=0.5,
                )
            else:
                # Grouped bars: offset each bar
                if n_bars > 1:
                    bar_width = (0.8 * bar_width_scale) / n_bars  # Divide space among bars
                    offset = (-0.4 * bar_width_scale) + (trace_idx + 0.5) * bar_width
                    x_positions_grouped: List[float] = [pos + offset for pos in x_positions]
                else:
                    bar_width = 0.8 * bar_width_scale
                    x_positions_grouped = [float(pos) for pos in x_positions]

                ax.bar(
                    x=x_positions_grouped,
                    height=y,
                    label=trace.name or "",
                    color=color,
                    width=bar_width,
                    edgecolor="white",
                    linewidth=0.5,
                )

            # Set x-axis labels only once (from first trace)
            if trace_idx == 0:
                ax.set_xticks(list(range(n_positions)))
                # Smart rotation: only rotate if labels are long
                max_label_len = max(len(str(label)) for label in self._categorical_labels)
                if max_label_len > 8 or n_positions > 10:
                    ax.set_xticklabels(self._categorical_labels, rotation=45, ha="right")
                else:
                    ax.set_xticklabels(self._categorical_labels, rotation=0, ha="center")
        elif has_numeric_x and self._barmode == "stack":
            # Case 2: Numeric x-axis with stacked bars (grouped-stacked pattern)
            # Use the actual numeric x positions from Plotly figure
            x_numeric_positions = [float(xi) for xi in x]
            n_positions = len(x_numeric_positions)

            # Calculate bottom positions for stacking
            bottom = [0.0] * n_positions
            if trace_idx > 0:
                # Calculate cumulative sum from previous traces
                for prev_trace in self._bar_traces[:trace_idx]:
                    prev_x = prev_trace.x if prev_trace.x is not None else []
                    prev_y = prev_trace.y if prev_trace.y is not None else []
                    if hasattr(prev_x, "tolist"):
                        prev_x = prev_x.tolist()
                    if hasattr(prev_y, "tolist"):
                        prev_y = prev_y.tolist()

                    # Match x positions to accumulate bottom values
                    for i, xi in enumerate(x_numeric_positions):
                        for j, prev_xi in enumerate(prev_x):
                            if abs(float(xi) - float(prev_xi)) < 1e-6:  # Same position
                                bottom[i] += float(prev_y[j]) if prev_y[j] is not None else 0.0
                                break

            # Determine bar width from Plotly trace or x-axis spacing
            # First, try to get width from trace
            if hasattr(trace, "width") and trace.width is not None:
                bar_width = float(trace.width) * bar_width_scale
            elif len(x_numeric_positions) > 1:
                # Fallback: calculate from minimum spacing
                spacings = [
                    x_numeric_positions[i + 1] - x_numeric_positions[i]
                    for i in range(len(x_numeric_positions) - 1)
                ]
                min_spacing = min(s for s in spacings if s > 0.1)  # Ignore tiny gaps
                bar_width = min_spacing * 0.8 * bar_width_scale  # 80% of min spacing
            else:
                bar_width = 0.8 * bar_width_scale

            ax.bar(
                x=x_numeric_positions,
                height=y,
                bottom=bottom,
                label=trace.name or "",
                color=color,
                width=bar_width,
                edgecolor="white",
                linewidth=0.5,
            )
        else:
            # Case 3: Simple numeric x-axis (no stacking, or regular grouped bars)
            ax.bar(
                x=x,
                height=y,
                label=trace.name or "",
                color=color,
                width=0.8 * bar_width_scale,
            )

    def _convert_line_trace(self, trace: go.Scatter, ax: Axes) -> None:
        """
        Convert Plotly Scatter (line mode) trace to Matplotlib line plot.

        Args:
            trace: Plotly Scatter trace with line mode
            ax: Matplotlib axes
        """
        x = trace.x if trace.x is not None else []
        y = trace.y if trace.y is not None else []

        # Handle line properties
        line_props: Dict[str, Any] = {}
        if trace.line:
            if trace.line.color:
                line_props["color"] = trace.line.color
            if trace.line.width:
                line_props["linewidth"] = trace.line.width
            if trace.line.dash:
                if trace.line.dash == "dash":
                    line_props["linestyle"] = "--"
                elif trace.line.dash == "dot":
                    line_props["linestyle"] = ":"
                elif trace.line.dash == "dashdot":
                    line_props["linestyle"] = "-."

        ax.plot(x, y, label=trace.name or "", **line_props)

    def _convert_scatter_trace(self, trace: go.Scatter, ax: Axes) -> None:
        """
        Convert Plotly Scatter (marker mode) trace to Matplotlib scatter plot.

        Args:
            trace: Plotly Scatter trace with marker mode
            ax: Matplotlib axes
        """
        x = trace.x if trace.x is not None else []
        y = trace.y if trace.y is not None else []

        # Handle marker properties
        marker_props: Dict[str, Any] = {}
        if trace.marker:
            if trace.marker.color:
                marker_props["color"] = trace.marker.color
            if trace.marker.size:
                marker_props["s"] = trace.marker.size

        ax.scatter(x, y, label=trace.name or "", **marker_props)

    def _apply_layout(self, plotly_fig: go.Figure, ax: Axes) -> Dict[str, Any]:
        """
        Apply Plotly layout to Matplotlib axes.

        Preserves user's interactive decisions (legend position, zoom, etc.)

        Args:
            plotly_fig: Source Plotly figure
            ax: Target Matplotlib axes

        Returns:
            Dictionary of applied layout properties
        """
        applied = {}

        # Extract layout using LayoutMapper
        extracted_layout = self.layout_mapper.extract_layout(plotly_fig)

        # Apply to Matplotlib using LayoutMapper, passing preset for font sizes
        self.layout_mapper.apply_to_matplotlib(ax, extracted_layout, preset=self.preset)

        # Track what was applied
        applied.update(extracted_layout)

        # Grid (default styling)
        ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
        applied["grid"] = True

        # Configure legend with multi-column support
        # Use 2 columns if there are many traces (> 4), otherwise 1 column
        handles, labels = ax.get_legend_handles_labels()
        if handles:  # Only add legend if there are traces with labels
            ncol = 2 if len(handles) > 4 else 1

            # Get font size and bold from preset
            legend_fontsize = self.preset.get("font_size_legend", 8)
            legend_bold = self.preset.get("bold_legend", False)

            # Get legend spacing from preset (with defaults matching matplotlib)
            legend = ax.legend(
                handles=handles,
                labels=labels,
                ncol=ncol,
                frameon=True,
                fancybox=False,
                shadow=False,
                framealpha=1.0,
                edgecolor="black",
                loc="best",
                fontsize=legend_fontsize,
                # Spacing from preset - user configurable
                columnspacing=self.preset.get("legend_columnspacing", 0.5),
                handletextpad=self.preset.get("legend_handletextpad", 0.3),
                labelspacing=self.preset.get("legend_labelspacing", 0.2),
                handlelength=self.preset.get("legend_handlelength", 1.0),
                handleheight=self.preset.get("legend_handleheight", 0.7),
                borderpad=self.preset.get("legend_borderpad", 0.2),
                borderaxespad=self.preset.get("legend_borderaxespad", 0.5),
            )

            # Apply bold to legend text if requested
            if legend_bold:
                for text in legend.get_texts():
                    text.set_fontweight("bold")
            applied["legend_ncols"] = ncol
            applied["legend_items"] = len(handles)
            applied["legend_fontsize"] = legend_fontsize

        # Skip tight_layout() - let bbox_inches='tight' in savefig handle it
        # This avoids UserWarning about margins not accommodating decorations

        return applied

    def generate_preview(self, fig: go.Figure, preview_dpi: int = 150) -> bytes:
        """
        Generate a PNG preview of the matplotlib figure at lower DPI.

        Useful for showing users what the exported figure will look like
        before generating the full-resolution export.

        Args:
            fig: Plotly figure to convert
            preview_dpi: DPI for preview (default 150, lower than export DPI)

        Returns:
            PNG image data as bytes

        Example:
            >>> converter = MatplotlibConverter(preset)
            >>> preview_png = converter.generate_preview(fig, preview_dpi=150)
            >>> st.image(preview_png, caption="Export Preview")
        """
        # Temporarily override DPI for preview
        original_dpi = self.preset["dpi"]
        self.preset["dpi"] = preview_dpi

        # Save LaTeX settings and disable for preview (PNG doesn't need LaTeX)
        original_usetex = plt.rcParams["text.usetex"]
        plt.rcParams["text.usetex"] = False

        try:
            # Convert to matplotlib
            mpl_fig, ax = self._create_matplotlib_figure()

            # Skip LaTeX rendering for preview - use matplotlib's native rendering
            # This avoids requiring dvipng and makes preview generation much faster

            # Extract barmode
            if hasattr(fig, "layout") and hasattr(fig.layout, "barmode"):
                self._barmode = str(fig.layout.barmode) if fig.layout.barmode else "group"
            else:
                self._barmode = "group"
            self._bar_traces = []
            self._categorical_labels = []

            # Convert traces and apply layout
            self._convert_traces(fig, ax)
            self._apply_layout(fig, ax)

            # Export as PNG
            buf = io.BytesIO()
            mpl_fig.savefig(
                buf,
                format="png",
                bbox_inches="tight",
                pad_inches=0.05,
                dpi=preview_dpi,
            )
            buf.seek(0)
            png_data = buf.read()

            plt.close(mpl_fig)
            return png_data

        finally:
            # Restore original settings
            self.preset["dpi"] = original_dpi
            plt.rcParams["text.usetex"] = original_usetex

    def _export_figure(self, fig: Figure, format: Literal["pdf", "pgf", "eps"]) -> bytes:
        """
        Export Matplotlib figure to specified format.

        Args:
            fig: Matplotlib Figure to export
            format: Export format

        Returns:
            Binary data of exported figure

        Raises:
            ValueError: If format is unsupported
        """
        buf = io.BytesIO()

        export_kwargs = {
            "bbox_inches": "tight",
            "pad_inches": 0.05,
        }

        if format == "pdf":
            fig.savefig(
                buf,
                format="pdf",
                metadata={"Creator": "RING-5 LaTeX Export", "Author": "RING-5"},
                bbox_inches=export_kwargs["bbox_inches"],
                pad_inches=export_kwargs["pad_inches"],
            )
        elif format == "pgf":
            # PGF: Best for LaTeX (vector + TeX fonts)
            fig.savefig(
                buf,
                format="pgf",
                bbox_inches=export_kwargs["bbox_inches"],
                pad_inches=export_kwargs["pad_inches"],
            )
        elif format == "eps":
            # EPS: Legacy format for older journals
            fig.savefig(
                buf,
                format="eps",
                bbox_inches=export_kwargs["bbox_inches"],
                pad_inches=export_kwargs["pad_inches"],
            )
        else:
            raise ValueError(f"Unsupported format: {format}")

        buf.seek(0)
        return buf.read()
