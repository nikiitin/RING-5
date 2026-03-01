"""
Matplotlib connector — translate resolved FigureConfig into matplotlib calls.

This replaces ``LayoutApplier.apply_to_matplotlib()`` internals.
It reads from the shared FigureConfig instead of a raw layout dictionary
and scattered LaTeXPreset fields.

Usage:
    from src.web.rendering import FigureSpecToMatplotlib

    resolved = resolve_config(spec)
    FigureSpecToMatplotlib.apply(resolved, ax)
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from src.core.models.visualization.data_label_config import DataLabelConfig
from src.core.models.visualization.figure_config import FigureConfig

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

logger = logging.getLogger(__name__)

_CSS_RGB_RE = re.compile(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", re.IGNORECASE)


def _css_rgb_to_hex(color: str) -> str:
    """Convert a CSS ``rgb(r,g,b)`` string to ``#rrggbb`` hex.

    If *color* is already a hex string or any other format, return it
    unchanged so that Matplotlib's own validator handles it.
    """
    m = _CSS_RGB_RE.match(color.strip())
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"#{r:02x}{g:02x}{b:02x}"
    return color


class FigureSpecToMatplotlib:
    """Stateless translator: FigureConfig → matplotlib axes updates.

    The FigureConfig must be **resolved** (no -1 sentinels) before calling.

    Note: matplotlib is imported lazily inside methods to avoid import
    errors when matplotlib is not installed (e.g., in unit tests that
    only test the spec model).
    """

    @staticmethod
    def apply(spec: FigureConfig, ax: Axes) -> None:
        """Apply the full FigureConfig to a matplotlib Axes.

        Args:
            spec: A resolved FigureConfig (no sentinel values).
            ax: A ``matplotlib.axes.Axes`` instance.
        """
        FigureSpecToMatplotlib._apply_backgrounds(spec, ax)
        FigureSpecToMatplotlib._apply_font_family(spec, ax)
        FigureSpecToMatplotlib._apply_color_palette(spec, ax)
        FigureSpecToMatplotlib._apply_title(spec, ax)
        FigureSpecToMatplotlib._apply_axis_labels(spec, ax)
        FigureSpecToMatplotlib._apply_axis_ticks(spec, ax)
        FigureSpecToMatplotlib._apply_axis_ranges(spec, ax)
        FigureSpecToMatplotlib._apply_axis_colors(spec, ax)
        FigureSpecToMatplotlib._apply_grids(spec, ax)
        FigureSpecToMatplotlib._apply_legends(spec, ax)
        FigureSpecToMatplotlib._apply_reference_lines(spec, ax)
        FigureSpecToMatplotlib._apply_data_labels(spec, ax)
        FigureSpecToMatplotlib._apply_annotations(spec, ax)
        FigureSpecToMatplotlib._apply_separators(spec, ax)
        FigureSpecToMatplotlib._apply_hatching(spec, ax)
        FigureSpecToMatplotlib._apply_margins(spec, ax)

    @staticmethod
    def _apply_margins(spec: FigureConfig, ax: Axes) -> None:
        """Apply manual margins from FigureConfig to the current figure."""
        if spec.dimensions is None or spec.dimensions.margins is None:
            return

        dims = spec.dimensions
        margins = dims.margins

        # Plotly margins are in pixels. Convert to fractions of figure width/height.
        # Ensure we don't divide by zero.
        if dims.width > 0 and dims.height > 0:
            left = margins.left / dims.width
            right = 1.0 - (margins.right / dims.width)
            bottom = margins.bottom / dims.height
            top = 1.0 - (margins.top / dims.height)

            # Clamp values between 0 and 1 to prevent invalid margins
            left = max(0.0, min(0.99, left))
            right = max(left + 0.01, min(1.0, right))
            bottom = max(0.0, min(0.99, bottom))
            top = max(bottom + 0.01, min(1.0, top))

            try:
                ax.figure.subplots_adjust(left=left, right=right, top=top, bottom=bottom)
            except ValueError as e:
                logger.warning(f"Could not apply margins ({left}, {right}, {top}, {bottom}): {e}")

    @staticmethod
    def _apply_title(spec: FigureConfig, ax: Axes) -> None:
        """Set figure title with proper font properties."""
        if not spec.title:
            return

        typo = spec.typography
        if typo is None:
            raise ValueError("FigureConfig requires typography")
        weight = "bold" if typo.bold_title else "normal"
        ax.set_title(
            FigureSpecToMatplotlib._escape_latex(spec.title),
            fontsize=typo.font_size_title,
            fontweight=weight,
        )

    @staticmethod
    def _apply_axis_labels(spec: FigureConfig, ax: Axes) -> None:
        """Set X and Y axis labels with proper typography."""
        typo = spec.typography
        if typo is None:
            raise ValueError("FigureConfig requires typography")
        if spec.axes is None:
            raise ValueError("FigureConfig requires axes")

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
            # Use standoff as labelpad when explicitly set (>= 0)
            y_pad = (
                spec.axes.y.label_standoff
                if spec.axes.y.label_standoff >= 0
                else spec.axes.y.label_pad
            )
            ax.set_ylabel(
                FigureSpecToMatplotlib._escape_latex(y_label),
                fontsize=typo.font_size_ylabel,
                fontweight=weight,
                labelpad=y_pad,
            )
            # Custom y-label position (vshift overrides, then label_position)
            if spec.axes.y.title_vshift != 0.0:
                frac = spec.axes.y.title_vshift / 100.0
                ax.yaxis.set_label_coords(
                    -y_pad / 72.0,
                    0.5 + frac,
                )
            elif spec.axes.y.label_position != 0.5:
                ax.yaxis.set_label_coords(
                    -y_pad / 72.0,
                    spec.axes.y.label_position,
                )

        # Secondary Y-axis (twin axis)
        if spec.axes.y2 is not None:
            # Check if twin axis exists
            for child_ax in ax.figure.get_axes():
                if child_ax is not ax and hasattr(child_ax, "_twinned_axes"):
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
    def _apply_axis_ticks(spec: FigureConfig, ax: Axes) -> None:
        """Configure tick labels, rotation, padding."""
        import matplotlib.transforms as transforms

        typo = spec.typography
        if typo is None:
            raise ValueError("FigureConfig requires typography")
        if spec.axes is None:
            raise ValueError("FigureConfig requires axes")
        x_axis = spec.axes.x
        y_axis = spec.axes.y

        # X-ticks
        weight = "bold" if typo.bold_ticks else "normal"
        ax.tick_params(
            axis="x",
            labelsize=typo.font_size_ticks,
            pad=x_axis.tick_pad,
            bottom=x_axis.show_ticks,
            labelbottom=x_axis.show_tick_labels,
        )

        if x_axis.tick_values is not None and x_axis.tick_text is not None:
            ax.set_xticks(x_axis.tick_values)
            escaped = [FigureSpecToMatplotlib._escape_latex(str(t)) for t in x_axis.tick_text]
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
            left=y_axis.show_ticks,
            labelleft=y_axis.show_tick_labels,
        )

        if y_axis.tick_values is not None and y_axis.tick_text is not None:
            ax.set_yticks(y_axis.tick_values)
            escaped = [FigureSpecToMatplotlib._escape_latex(str(t)) for t in y_axis.tick_text]
            ax.set_yticklabels(
                escaped,
                fontsize=typo.font_size_yticks,
            )

    @staticmethod
    def _apply_axis_ranges(spec: FigureConfig, ax: Axes) -> None:
        """Set axis range limits and scale."""
        if spec.axes is None:
            raise ValueError("FigureConfig requires axes")
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
    def _map_dash_style(dash_str: str) -> str:
        """Map Plotly dash string to Matplotlib line style."""
        mapping = {
            "solid": "-",
            "dot": ":",
            "dash": "--",
            "longdash": "--",
            "dashdot": "-.",
            "longdashdot": "-.",
        }
        return mapping.get(dash_str.lower(), "-")

    @staticmethod
    def _apply_grids(spec: FigureConfig, ax: Axes) -> None:
        """Configure grid visibility and styling."""
        if spec.axes is None:
            raise ValueError("FigureConfig requires axes")
        x_axis = spec.axes.x
        y_axis = spec.axes.y

        # X grid — only pass line properties when enabling, otherwise
        # matplotlib overrides the False flag and shows the grid anyway.
        if x_axis.show_grid:
            ax.xaxis.grid(
                True,
                color=x_axis.grid_color,
                linewidth=x_axis.grid_width,
                linestyle=FigureSpecToMatplotlib._map_dash_style(x_axis.tick_dash),
            )
        else:
            ax.xaxis.grid(False)

        # Y grid
        if y_axis.show_grid:
            ax.yaxis.grid(
                True,
                color=y_axis.grid_color,
                linewidth=y_axis.grid_width,
                linestyle=FigureSpecToMatplotlib._map_dash_style(y_axis.tick_dash),
            )
        else:
            ax.yaxis.grid(False)

    @staticmethod
    def _apply_legends(spec: FigureConfig, ax: Axes) -> None:
        """Render legends with full spacing control."""
        if not spec.legends:
            return

        for legend in spec.legends:
            if not legend.visible:
                continue

            spacing = legend.spacing
            kwargs: dict[str, Any] = {
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

            # Font family — set via prop dict so each legend can
            # independently inherit or override the global family.
            if legend.font_family:
                from matplotlib.font_manager import FontProperties  # type: ignore[import-untyped]

                kwargs["prop"] = FontProperties(
                    family=legend.font_family,
                    size=legend.font_size,
                )

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

            if legend.title:
                kwargs["title"] = legend.title
                if legend.title_font_size > 0:
                    kwargs["title_fontsize"] = legend.title_font_size

            # Primary legend on the main axes
            if legend.role == "primary":
                handles, labels = ax.get_legend_handles_labels()
                if not labels:
                    continue
                leg = ax.legend(**kwargs)
                if leg and legend.bold:
                    for text in leg.get_texts():
                        text.set_fontweight("bold")
                if leg and legend.title_font_color:
                    title_text = leg.get_title()
                    if title_text:
                        title_text.set_color(legend.title_font_color)
            elif legend.role == "secondary":
                # Secondary legend on the twin axis
                for child_ax in ax.figure.get_axes():
                    if child_ax is not ax:
                        leg = child_ax.legend(**kwargs)
                        if leg and legend.bold:
                            for text in leg.get_texts():
                                text.set_fontweight("bold")
                        if leg and legend.title_font_color:
                            title_text = leg.get_title()
                            if title_text:
                                title_text.set_color(legend.title_font_color)
                        break
            elif legend.role == "tertiary":
                # Boxed legend — rendered via _apply_annotations from
                # enriched FigureConfig annotations.  If the annotations
                # pipeline already placed the content, we skip creating
                # a duplicate matplotlib legend here.  If explicit
                # legend items exist on a third axis, render them.
                pass  # Content comes from annotations, not traces

    @staticmethod
    def _escape_latex(text: str) -> str:
        r"""Escape special LaTeX characters in display text.

        Preserves existing LaTeX commands (\textbf, \texttt, etc.)
        and only escapes raw special characters.
        """
        if not text:
            return text

        # Don't escape if text already contains LaTeX commands
        if "\\" in text and any(
            cmd in text for cmd in ["\\textbf", "\\texttt", "\\textit", "\\mathrm"]
        ):
            return text

        # Escape special characters
        special_chars = ["&", "%", "$", "#", "_", "{", "}"]
        result = text
        for char in special_chars:
            result = result.replace(char, f"\\{char}")
        return result

    # ──────────────────────────────────────────────────────────────────
    #  Step 11 — new feature methods
    # ──────────────────────────────────────────────────────────────────

    _DASH_MAP: dict[str, str] = {
        "solid": "-",
        "dash": "--",
        "dot": ":",
        "dashdot": "-.",
    }

    @staticmethod
    def _apply_backgrounds(spec: FigureConfig, ax: Axes) -> None:
        """Set figure and axes background colours."""
        fig = ax.figure
        if spec.paper_bgcolor:
            fig.patch.set_facecolor(spec.paper_bgcolor)
        if spec.plot_bgcolor:
            ax.set_facecolor(spec.plot_bgcolor)

    @staticmethod
    def _apply_font_family(spec: FigureConfig, ax: Axes) -> None:
        """Set global font family via rcParams for this figure."""
        import matplotlib as mpl

        if spec.font_family:
            mpl.rcParams["font.family"] = spec.font_family

    @staticmethod
    def _apply_color_palette(spec: FigureConfig, ax: Axes) -> None:
        """Set colour cycle on the axes from spec.color_palette.

        Plotly qualitative palettes return CSS ``rgb(r,g,b)`` strings which
        Matplotlib cannot parse directly.  We normalise every entry to a hex
        colour before calling ``set_prop_cycle``.
        """
        if spec.color_palette:
            hex_colors = [_css_rgb_to_hex(c) for c in spec.color_palette]
            ax.set_prop_cycle(color=hex_colors)

    @staticmethod
    def _apply_reference_lines(spec: FigureConfig, ax: Axes) -> None:
        """Draw horizontal / vertical reference lines.

        Uses the ReferenceLineConfig list on FigureConfig.
        """
        for rl in spec.reference_lines:
            if not rl.enabled:
                continue
            ls = FigureSpecToMatplotlib._DASH_MAP.get(rl.style, "--")
            kwargs: dict[str, Any] = {
                "color": rl.color,
                "linewidth": rl.width,
                "linestyle": ls,
                "zorder": 5,
            }
            if rl.label:
                kwargs["label"] = rl.label
            if rl.axis == "y":
                ax.axhline(y=rl.value, **kwargs)
            else:
                ax.axvline(x=rl.value, **kwargs)

    @staticmethod
    def _apply_data_labels(spec: FigureConfig, ax: Axes) -> None:
        """Annotate bar containers with value labels.

        Falls back to ``ax.bar_label()`` when available (mpl 3.4+),
        otherwise silently skips.
        """
        if spec.data_labels is None or not spec.data_labels.enabled:
            return

        dl: DataLabelConfig = spec.data_labels
        fmt = f"{{:{dl.format_string}}}" if dl.format_string else "{:.2f}"

        color = dl.custom_color if dl.color_mode == "custom" else "#000000"

        for container in ax.containers:
            try:
                ax.bar_label(
                    container,
                    fmt=fmt,
                    fontsize=dl.font_size,
                    rotation=dl.rotation,
                    color=color,
                    label_type="edge" if dl.position == "outside" else "center",
                )
            except (AttributeError, TypeError):
                # mpl < 3.4 or non-bar container
                pass

    @staticmethod
    def _apply_annotations(spec: FigureConfig, ax: Axes) -> None:
        """Render text annotations from spec onto the matplotlib axes.

        Handles ``xref``/``yref`` coordinate systems: ``"data"`` maps to
        data coordinates, ``"paper"`` maps to axes-fraction coordinates.
        """
        if not spec.annotations:
            return

        import matplotlib.transforms as transforms

        for ann in spec.annotations:
            if not ann.text:
                continue

            # Convert HTML line breaks to newlines for matplotlib
            raw_text = ann.text.replace("<br>", "\n").replace("<br/>", "\n")
            # Strip any remaining HTML tags
            raw_text = re.sub(r"<[^>]+>", "", raw_text)
            text = FigureSpecToMatplotlib._escape_latex(raw_text)

            # Determine coordinate transform
            if ann.xref == "paper" and ann.yref == "paper":
                transform = ax.transAxes
            elif ann.xref == "paper":
                transform = transforms.blended_transform_factory(ax.transAxes, ax.transData)
            elif ann.yref == "paper":
                transform = transforms.blended_transform_factory(ax.transData, ax.transAxes)
            else:
                transform = ax.transData

            fontweight = "bold" if ann.font_bold else "normal"
            fontsize = ann.font_size if ann.font_size > 0 else 10

            ha_map = {"left": "left", "right": "right", "center": "center"}
            va_map = {"top": "top", "bottom": "bottom", "middle": "center"}
            ha = ha_map.get(ann.xanchor, "center")
            va = va_map.get(ann.yanchor, "center")

            bbox_props = None
            if ann.bgcolor or ann.border_width > 0:
                bbox_props = {
                    "boxstyle": f"round,pad={ann.border_pad / 72.0:.3f}",
                    "facecolor": ann.bgcolor or "none",
                    "edgecolor": ann.border_color or "none",
                    "linewidth": ann.border_width,
                }

            ax.annotate(
                text,
                xy=(ann.x, ann.y),
                xycoords=transform,
                fontsize=fontsize,
                fontweight=fontweight,
                color=ann.font_color,
                ha=ha,
                va=va,
                rotation=ann.text_angle,
                bbox=bbox_props,
                annotation_clip=False,
            )

    @staticmethod
    def _apply_separators(spec: FigureConfig, ax: Axes) -> None:
        """Draw vertical separator lines between bar groups."""
        import matplotlib.transforms as transforms

        if not spec.separator.enabled:
            return

        # Infer category boundaries from x-tick positions
        xticks = ax.get_xticks()
        if len(xticks) < 2:
            return

        ls = FigureSpecToMatplotlib._DASH_MAP.get(spec.separator.style, "--")
        blended = transforms.blended_transform_factory(ax.transData, ax.transAxes)

        for i in range(1, len(xticks)):
            mid = (xticks[i - 1] + xticks[i]) / 2.0
            ax.plot(
                [mid, mid],
                [0, 1],
                transform=blended,
                linestyle=ls,
                color=spec.separator.color,
                linewidth=0.8,
                alpha=0.6,
                clip_on=False,
            )

    @staticmethod
    def _apply_hatching(spec: FigureConfig, ax: Axes) -> None:
        """Apply hatching patterns from hatching_sequence to bar patches."""
        if not spec.enable_stripes or not spec.hatching_sequence:
            return

        for i, container in enumerate(ax.containers):
            pattern = spec.hatching_sequence[i % len(spec.hatching_sequence)]
            for patch in container:
                patch.set_hatch(pattern)

    @staticmethod
    def _apply_axis_colors(spec: FigureConfig, ax: Axes) -> None:
        """Apply tick_font_color, axis_line_color, axis_line_width.

        Also handles top/right axis line visibility via spines.
        """
        if spec.axes is None:
            return

        # ── Bottom (X) axis line ─────────────────────────────────
        x = spec.axes.x
        if x.tick_font_color:
            ax.tick_params(axis="x", colors=x.tick_font_color)

        # Bottom spine
        if x.axis_line_width > 0:
            color = x.axis_line_color or x.axis_color
            ax.spines["bottom"].set_color(color)
            ax.spines["bottom"].set_linewidth(x.axis_line_width)
            ax.spines["bottom"].set_visible(True)
        else:
            ax.spines["bottom"].set_visible(False)

        # Top spine
        top_w = spec.axes.top_axis_line_width
        if top_w > 0:
            ax.spines["top"].set_color(spec.axes.top_axis_line_color)
            ax.spines["top"].set_linewidth(top_w)
            ax.spines["top"].set_visible(True)
        else:
            ax.spines["top"].set_visible(False)

        # ── Left (Y) axis line ───────────────────────────────────
        y = spec.axes.y
        if y.tick_font_color:
            ax.tick_params(axis="y", colors=y.tick_font_color)

        # Left spine
        if y.axis_line_width > 0:
            color = y.axis_line_color or y.axis_color
            ax.spines["left"].set_color(color)
            ax.spines["left"].set_linewidth(y.axis_line_width)
            ax.spines["left"].set_visible(True)
        else:
            ax.spines["left"].set_visible(False)

        # Right spine (when no Y2)
        right_w = spec.axes.right_axis_line_width
        if spec.axes.y2 is None:
            if right_w > 0:
                ax.spines["right"].set_color(spec.axes.right_axis_line_color)
                ax.spines["right"].set_linewidth(right_w)
                ax.spines["right"].set_visible(True)
            else:
                ax.spines["right"].set_visible(False)

    @staticmethod
    def create_figure(
        spec: FigureConfig,
    ) -> tuple[Figure, Axes]:
        """Create a new matplotlib figure + axes from spec dimensions.

        When the spec uses ``dpi=1`` (the pixel-passthrough convention from
        :pymethod:`ConfigSpecBuilder.from_config`), *width* and *height*
        are raw pixel counts.  Matplotlib's ``figsize`` expects **inches**,
        and Streamlit's ``st.pyplot`` re-renders at 200 DPI, so passing
        raw pixel values as inches causes a >100 000 pixel image and an
        instant ``MemoryError``.

        We normalise to inches using 96 DPI (standard screen resolution)
        when the spec uses the passthrough convention.

        Returns:
            Tuple of (matplotlib.figure.Figure, matplotlib.axes.Axes).
        """
        import matplotlib.pyplot as plt

        dims = spec.dimensions

        # dpi=1 is the "pixel passthrough" sentinel from from_config();
        # convert pixel values to inches at 96 DPI for sane rendering.
        if dims.dpi <= 1:
            render_dpi = 96
            width_in = dims.width / render_dpi
            height_in = dims.height / render_dpi
        else:
            render_dpi = dims.dpi
            width_in = dims.width
            height_in = dims.height

        fig, ax = plt.subplots(
            figsize=(width_in, height_in),
            dpi=render_dpi,
        )
        return fig, ax
