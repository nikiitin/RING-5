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
        # Note: Unicode characters in labels should be avoided or use LaTeX commands
        preamble = r"""
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath}
\usepackage{amssymb}
"""
        rc("text.latex", preamble=preamble)

        logger.info("LaTeX text rendering enabled with full font support")

        # Font configuration
        rc("font", family=self.preset["font_family"])
        rc("font", size=self.preset["font_size_base"])
        rc("axes", labelsize=self.preset["font_size_labels"])
        rc("axes", titlesize=self.preset["font_size_title"])
        rc("xtick", labelsize=self.preset["font_size_ticks"])
        rc("ytick", labelsize=self.preset["font_size_ticks"])
        rc("legend", fontsize=self.preset["font_size_labels"])

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

        for trace in plotly_fig.data:
            try:
                if trace.type == "bar":
                    self._convert_bar_trace(trace, ax, traces_converted)
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

    def _convert_bar_trace(self, trace: go.Bar, ax: Axes, offset: int) -> None:
        """
        Convert Plotly Bar trace to Matplotlib bar chart.

        Args:
            trace: Plotly Bar trace
            ax: Matplotlib axes
            offset: Position offset for grouped bars
        """
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
        # Must check length first to avoid empty list issues
        has_categorical_x = False
        try:
            if x and len(x) > 0:
                # Check first element type - handle both strings and bytes
                first_x = x[0]
                has_categorical_x = isinstance(first_x, (str, bytes)) or (
                    hasattr(first_x, "__class__")
                    and first_x.__class__.__name__ in ("str", "str_", "bytes_")
                )
        except (TypeError, IndexError):
            # If we can't check, assume numeric
            has_categorical_x = False

        if has_categorical_x:
            # For categorical x-axis, use numeric positions
            x_pos = list(range(len(x)))
            ax.bar(
                x=x_pos,
                height=y,
                label=trace.name or "",
                color=color,
                width=0.8,
            )
            ax.set_xticks(x_pos)
            ax.set_xticklabels(x, rotation=45, ha="right")
        else:
            # For numeric x-axis
            ax.bar(
                x=x,
                height=y,
                label=trace.name or "",
                color=color,
                width=0.8,
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
        layout = plotly_fig.layout
        applied = {}

        # Extract layout using LayoutMapper
        extracted_layout = self.layout_mapper.extract_layout(plotly_fig)

        # Apply to Matplotlib using LayoutMapper
        self.layout_mapper.apply_to_matplotlib(ax, extracted_layout)

        # Track what was applied
        applied.update(extracted_layout)

        # Additional layout elements
        if layout.title and layout.title.text:
            ax.set_title(layout.title.text)
            applied["title"] = layout.title.text

        # Grid (default styling)
        ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
        applied["grid"] = True

        # Tight layout for clean borders
        plt.tight_layout()

        return applied

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
