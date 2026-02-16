"""
Matplotlib connector — translate resolved FigureSpec into matplotlib calls.

This replaces ``LayoutApplier.apply_to_matplotlib()`` internals.
It reads from the shared FigureSpec instead of a raw layout dictionary
and scattered LaTeXPreset fields.

Usage:
    from src.core.visualization.connectors import FigureSpecToMatplotlib

    resolved = resolve_spec(spec)
    FigureSpecToMatplotlib.apply(resolved, ax)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.visualization.figure_spec import FigureSpec
from src.core.visualization.legend_spec import LegendSpec
from src.core.visualization.annotation_spec import AnnotationSpec
from src.core.visualization.axis_spec import AxisSpec

logger = logging.getLogger(__name__)


class FigureSpecToMatplotlib:
    """Stateless translator: FigureSpec → matplotlib axes updates.

    The FigureSpec must be **resolved** (no -1 sentinels) before calling.

    Note: matplotlib is imported lazily inside methods to avoid import
    errors when matplotlib is not installed (e.g., in unit tests that
    only test the spec model).
    """

    @staticmethod
    def apply(spec: FigureSpec, ax: Any) -> None:
        """Apply the full FigureSpec to a matplotlib Axes.

        Args:
            spec: A resolved FigureSpec (no sentinel values).
            ax: A ``matplotlib.axes.Axes`` instance.
        """
        FigureSpecToMatplotlib._apply_title(spec, ax)
        FigureSpecToMatplotlib._apply_axis_labels(spec, ax)
        FigureSpecToMatplotlib._apply_axis_ticks(spec, ax)
        FigureSpecToMatplotlib._apply_axis_ranges(spec, ax)
        FigureSpecToMatplotlib._apply_grids(spec, ax)
        FigureSpecToMatplotlib._apply_legends(spec, ax)

    @staticmethod
    def _apply_title(spec: FigureSpec, ax: Any) -> None:
        """Set figure title with proper font properties."""
        if not spec.title:
            return

        typo = spec.typography
        weight = "bold" if typo.bold_title else "normal"
        ax.set_title(
            FigureSpecToMatplotlib._escape_latex(spec.title),
            fontsize=typo.font_size_title,
            fontweight=weight,
        )

    @staticmethod
    def _apply_axis_labels(spec: FigureSpec, ax: Any) -> None:
        """Set X and Y axis labels with proper typography."""
        typo = spec.typography

        # X-axis label
        x_label = spec.axes.x.label
        if x_label:
            weight = "bold" if typo.bold_xlabel else "normal"
            ax.set_xlabel(
                FigureSpecToMatplotlib._escape_latex(x_label),
                fontsize=typo.font_size_xlabel,
                fontweight=weight,
                labelpad=spec.axes.x.label_pad,
            )

        # Y-axis label
        y_label = spec.axes.y.label
        if y_label:
            weight = "bold" if typo.bold_ylabel else "normal"
            ax.set_ylabel(
                FigureSpecToMatplotlib._escape_latex(y_label),
                fontsize=typo.font_size_ylabel,
                fontweight=weight,
                labelpad=spec.axes.y.label_pad,
            )
            # Custom y-label position
            if spec.axes.y.label_position != 0.5:
                ax.yaxis.set_label_coords(
                    -spec.axes.y.label_pad / 72.0,
                    spec.axes.y.label_position,
                )

        # Secondary Y-axis (twin axis)
        if spec.axes.y2 is not None:
            # Check if twin axis exists
            for child_ax in ax.figure.get_axes():
                if child_ax is not ax and hasattr(child_ax, '_twinned_axes'):
                    y2_label = spec.axes.y2.label
                    if y2_label:
                        weight = "bold" if typo.bold_y2label else "normal"
                        child_ax.set_ylabel(
                            FigureSpecToMatplotlib._escape_latex(y2_label),
                            fontsize=typo.font_size_y2label,
                            fontweight=weight,
                            labelpad=spec.axes.y2.label_pad,
                        )
                    break

    @staticmethod
    def _apply_axis_ticks(spec: FigureSpec, ax: Any) -> None:
        """Configure tick labels, rotation, padding."""
        import matplotlib.transforms as transforms

        typo = spec.typography
        x_axis = spec.axes.x
        y_axis = spec.axes.y

        # X-ticks
        weight = "bold" if typo.bold_ticks else "normal"
        ax.tick_params(
            axis="x",
            labelsize=typo.font_size_ticks,
            pad=x_axis.tick_pad,
        )

        if x_axis.tick_values is not None and x_axis.tick_text is not None:
            ax.set_xticks(x_axis.tick_values)
            escaped = [
                FigureSpecToMatplotlib._escape_latex(str(t))
                for t in x_axis.tick_text
            ]
            ax.set_xticklabels(
                escaped,
                rotation=x_axis.tick_angle,
                ha=x_axis.tick_ha,
                fontsize=typo.font_size_ticks,
                fontweight=weight,
            )

        # Apply horizontal offset to x-ticks if needed
        if x_axis.tick_offset != 0.0:
            offset = transforms.ScaledTranslation(
                x_axis.tick_offset / 72.0, 0, ax.figure.dpi_scale_trans
            )
            for label in ax.get_xticklabels():
                label.set_transform(label.get_transform() + offset)

        if not x_axis.show_tick_labels:
            ax.set_xticklabels([])

        # Y-ticks
        ax.tick_params(
            axis="y",
            labelsize=typo.font_size_yticks,
            pad=y_axis.tick_pad,
        )

        if y_axis.tick_values is not None and y_axis.tick_text is not None:
            ax.set_yticks(y_axis.tick_values)
            escaped = [
                FigureSpecToMatplotlib._escape_latex(str(t))
                for t in y_axis.tick_text
            ]
            ax.set_yticklabels(
                escaped,
                fontsize=typo.font_size_yticks,
            )

    @staticmethod
    def _apply_axis_ranges(spec: FigureSpec, ax: Any) -> None:
        """Set axis range limits and scale."""
        x_axis = spec.axes.x
        y_axis = spec.axes.y

        if x_axis.range is not None:
            ax.set_xlim(x_axis.range)
        if y_axis.range is not None:
            ax.set_ylim(y_axis.range)

        if x_axis.scale == "log":
            ax.set_xscale("log")
        if y_axis.scale == "log":
            ax.set_yscale("log")

        # X-axis margin
        if x_axis.margin > 0:
            ax.margins(x=x_axis.margin)

    @staticmethod
    def _apply_grids(spec: FigureSpec, ax: Any) -> None:
        """Configure grid visibility and styling."""
        x_axis = spec.axes.x
        y_axis = spec.axes.y

        # X grid
        ax.xaxis.grid(
            x_axis.show_grid,
            color=x_axis.grid_color,
            linewidth=x_axis.grid_width,
        )
        # Y grid
        ax.yaxis.grid(
            y_axis.show_grid,
            color=y_axis.grid_color,
            linewidth=y_axis.grid_width,
        )

    @staticmethod
    def _apply_legends(spec: FigureSpec, ax: Any) -> None:
        """Render legends with full spacing control."""
        if not spec.legends:
            return

        for legend in spec.legends:
            if not legend.visible:
                continue

            spacing = legend.spacing
            kwargs: Dict[str, Any] = {
                "fontsize": legend.font_size,
                "ncol": max(1, legend.ncol),
                "columnspacing": spacing.columnspacing,
                "handletextpad": spacing.handletextpad,
                "labelspacing": spacing.labelspacing,
                "handlelength": spacing.handlelength,
                "handleheight": spacing.handleheight,
                "borderpad": spacing.borderpad,
                "borderaxespad": spacing.borderaxespad,
            }

            if legend.custom_position and legend.position_x >= 0:
                kwargs["loc"] = "upper left"
                kwargs["bbox_to_anchor"] = (
                    legend.position_x,
                    legend.position_y if legend.position_y >= 0 else 1.0,
                )

            if legend.bgcolor:
                kwargs["facecolor"] = legend.bgcolor
            if legend.border_width > 0:
                kwargs["edgecolor"] = legend.border_color

            # Primary legend on the main axes
            if legend.role == "primary":
                leg = ax.legend(**kwargs)
                if leg and legend.bold:
                    for text in leg.get_texts():
                        text.set_fontweight("bold")
            elif legend.role == "secondary":
                # Secondary legend on the twin axis
                for child_ax in ax.figure.get_axes():
                    if child_ax is not ax:
                        leg = child_ax.legend(**kwargs)
                        if leg and legend.bold:
                            for text in leg.get_texts():
                                text.set_fontweight("bold")
                        break

    @staticmethod
    def _escape_latex(text: str) -> str:
        """Escape special LaTeX characters in display text.

        Preserves existing LaTeX commands (\\textbf, \\texttt, etc.)
        and only escapes raw special characters.
        """
        if not text:
            return text

        # Don't escape if text already contains LaTeX commands
        if "\\" in text and any(
            cmd in text
            for cmd in ["\\textbf", "\\texttt", "\\textit", "\\mathrm"]
        ):
            return text

        # Escape special characters
        special_chars = ["&", "%", "$", "#", "_", "{", "}"]
        result = text
        for char in special_chars:
            result = result.replace(char, f"\\{char}")
        return result

    @staticmethod
    def create_figure(
        spec: FigureSpec,
    ) -> Tuple[Any, Any]:
        """Create a new matplotlib figure + axes from spec dimensions.

        Returns:
            Tuple of (matplotlib.figure.Figure, matplotlib.axes.Axes).
        """
        import matplotlib.pyplot as plt

        dims = spec.dimensions
        fig, ax = plt.subplots(
            figsize=(dims.width, dims.height),
            dpi=dims.dpi,
        )
        return fig, ax
