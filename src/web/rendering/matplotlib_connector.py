"""
Matplotlib connector — translate a resolved FigureConfig into matplotlib calls.

It reads from the shared FigureConfig — the single styling source of truth.

Usage:
    from src.web.rendering import FigureSpecToMatplotlib

    resolved = resolve_config(spec)
    FigureSpecToMatplotlib.apply(resolved, ax)
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, cast

from src.core.common.safe_format import normalize_numeric_format
from src.core.models.visualization.data_label_config import DataLabelConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import ColorbarConfig
from src.core.models.visualization.trace_build_result import RuleLine, SeparatorLine, ShadedRegion
from src.web.rendering._render_result import MatplotlibRenderResult
from src.web.rendering.latex_security import escape_latex_text

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.typing import RcKeyType

logger = logging.getLogger(__name__)

_CSS_RGB_RE = re.compile(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", re.IGNORECASE)
_CSS_RGBA_RE = re.compile(
    r"^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9]*\.?[0-9]+)\s*\)$", re.IGNORECASE
)

# Plotly marker-symbol names → matplotlib marker codes (for per-trace overrides).
_PLOTLY_TO_MPL_MARKER: dict[str, str] = {
    "circle": "o",
    "circle-open": "o",
    "square": "s",
    "square-open": "s",
    "diamond": "D",
    "diamond-open": "D",
    "cross": "P",
    "x": "X",
    "triangle-up": "^",
    "triangle-down": "v",
    "triangle-left": "<",
    "triangle-right": ">",
    "star": "*",
    "pentagon": "p",
    "hexagon": "h",
}


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


def _css_color_to_mpl(color: str) -> Any:
    """Convert a CSS ``rgba(r,g,b,a)`` string to a matplotlib ``(r,g,b,a)`` tuple.

    Plotly accepts ``rgba(...)`` but matplotlib's color parser does not, so a legend/
    annotation background carrying alpha (e.g. a transparent number box) round-trips
    through the Plotly-built spec as ``rgba(...)`` and must be coerced here. Falls back
    to :func:`_css_rgb_to_hex` (rgb→hex, else unchanged).
    """
    m = _CSS_RGBA_RE.match(color.strip())
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return (r / 255.0, g / 255.0, b / 255.0, float(m.group(4)))
    return _css_rgb_to_hex(color)


class FigureSpecToMatplotlib:
    """Stateless translator: FigureConfig → matplotlib axes updates.

    The FigureConfig must be **resolved** (no -1 sentinels) before calling.

    Note: matplotlib is imported lazily inside methods to avoid import
    errors when matplotlib is not installed (e.g., in unit tests that
    only test the spec model).
    """

    @staticmethod
    def apply(
        spec: FigureConfig,
        ax: Axes,
        render_result: MatplotlibRenderResult | None = None,
        *,
        apply_margins: bool = True,
    ) -> None:
        """Apply the full FigureConfig to a matplotlib Axes.

        Args:
            spec: A resolved FigureConfig (no sentinel values).
            ax: A ``matplotlib.axes.Axes`` instance.
            render_result: Trace-rendering metadata, including an optional heatmap image.
            apply_margins: Apply figure-wide margins. Dashboard panels disable
                this because their parent grid owns the outer layout.
        """
        # [impl->req~ring5.extension.render-connector~1]
        import matplotlib as mpl

        # Scope the font family to this build: artists the steps below create
        # (title, labels, ticks, legend, annotations) inherit it from the
        # rc_context; pre-existing artists are fixed by _apply_font_family.
        # Global rcParams is never mutated.
        font_rc: dict[RcKeyType, Any] = (
            {"font.family": spec.font_family} if spec.font_family else {}
        )
        with mpl.rc_context(font_rc):
            # Pipeline order: see _connector_protocol.STYLING_PIPELINE_ORDER
            FigureSpecToMatplotlib._apply_backgrounds(spec, ax)
            FigureSpecToMatplotlib._apply_font_family(spec, ax)
            FigureSpecToMatplotlib._apply_color_palette(spec, ax)
            FigureSpecToMatplotlib._apply_title(spec, ax)
            FigureSpecToMatplotlib._apply_axis_labels(spec, ax)
            FigureSpecToMatplotlib._apply_axis_ticks(spec, ax, render_result)
            FigureSpecToMatplotlib._apply_axis_ranges(spec, ax)
            FigureSpecToMatplotlib._apply_axis_colors(spec, ax)
            FigureSpecToMatplotlib._apply_grids(spec, ax)
            # Per-trace styling must run before the legend is built so renames and
            # restyled handles are reflected (parity with the Plotly connector).
            FigureSpecToMatplotlib._apply_series_styling(spec, ax)
            FigureSpecToMatplotlib._apply_trace_overrides(spec, ax)
            FigureSpecToMatplotlib._apply_legends(spec, ax)
            FigureSpecToMatplotlib._apply_reference_lines(spec, ax)
            FigureSpecToMatplotlib._apply_data_labels(spec, ax)
            FigureSpecToMatplotlib._apply_annotations(spec, ax)
            FigureSpecToMatplotlib._apply_hatching(spec, ax)
            if apply_margins:
                FigureSpecToMatplotlib._apply_margins(spec, ax)

            if render_result and render_result.heatmap_image is not None:
                FigureSpecToMatplotlib._apply_colorbar(spec, ax, render_result.heatmap_image)

    # Per-trace styling (parity with the Plotly connector)

    @staticmethod
    def _styleable_handles(ax: Axes) -> list[tuple[Any, str]]:
        """Ordered (artist, label) pairs across the primary and twin axes.

        Each trace is drawn with ``label=spec.name``, so the legend handles
        give the trace order (for ``series_styles``) and the trace names (for
        ``trace_overrides``).
        """
        pairs: list[tuple[Any, str]] = list(zip(*ax.get_legend_handles_labels()))
        twin = getattr(ax, "_ring5_twin", None)
        if twin is not None:
            pairs += list(zip(*twin.get_legend_handles_labels()))
        return pairs

    @staticmethod
    def _style_handle(
        handle: Any,
        *,
        color: str | None = None,
        alpha: float | None = None,
        line_width: float | None = None,
        marker: str | None = None,
        marker_size: float | None = None,
        edge_color: str | None = None,
        edge_width: float | None = None,
        hatch: str | None = None,
    ) -> None:
        """Apply styling to a single matplotlib artist, dispatching by its type."""
        from matplotlib.collections import PathCollection, PolyCollection
        from matplotlib.container import BarContainer
        from matplotlib.lines import Line2D
        from matplotlib.patches import Patch

        fill = _css_rgb_to_hex(color) if color else None
        edge = _css_rgb_to_hex(edge_color) if edge_color else None

        if isinstance(handle, BarContainer):
            for patch in handle.patches:
                if fill:
                    patch.set_facecolor(fill)
                if alpha is not None:
                    patch.set_alpha(alpha)
                if hatch:
                    patch.set_hatch(hatch)
                if edge:
                    patch.set_edgecolor(edge)
                if edge_width is not None:
                    patch.set_linewidth(edge_width)
        elif isinstance(handle, Line2D):
            if fill:
                handle.set_color(fill)
            if alpha is not None:
                handle.set_alpha(alpha)
            if line_width is not None:
                handle.set_linewidth(line_width)
            if marker:
                handle.set_marker(marker)
            if marker_size is not None:
                handle.set_markersize(marker_size)
        elif isinstance(handle, PathCollection):
            if fill:
                handle.set_color(fill)
            if alpha is not None:
                handle.set_alpha(alpha)
            if marker_size is not None:
                handle.set_sizes([float(marker_size)])
        elif isinstance(handle, PolyCollection):
            if fill:
                handle.set_facecolor(fill)
                handle.set_edgecolor(fill)
            if alpha is not None:
                handle.set_alpha(alpha)
            if edge:
                handle.set_edgecolor(edge)
            if edge_width is not None:
                handle.set_linewidth(edge_width)
        elif isinstance(handle, Patch):
            if fill:
                handle.set_facecolor(fill)
            if alpha is not None:
                handle.set_alpha(alpha)
            if hatch:
                handle.set_hatch(hatch)
            if edge:
                handle.set_edgecolor(edge)
            if edge_width is not None:
                handle.set_linewidth(edge_width)

    @staticmethod
    def _apply_series_styling(spec: FigureConfig, ax: Axes) -> None:
        """Apply per-trace line_width / marker_size / opacity / bar border (by index)."""
        # [impl->req~ring5.figure.series-styling~1]
        if not spec.series_styles:
            return
        for i, (handle, _label) in enumerate(FigureSpecToMatplotlib._styleable_handles(ax)):
            style = spec.series_styles[i % len(spec.series_styles)]
            FigureSpecToMatplotlib._style_handle(
                handle,
                alpha=style.opacity if style.opacity > 0 else None,
                line_width=style.line_width if style.line_width > 0 else None,
                marker_size=style.marker_size if style.marker_size > 0 else None,
                edge_color=(
                    (style.bar_border_color or "#000") if style.bar_border_width > 0 else None
                ),
                edge_width=style.bar_border_width if style.bar_border_width > 0 else None,
            )

    @staticmethod
    def _apply_trace_overrides(spec: FigureConfig, ax: Axes) -> None:
        """Apply per-trace overrides (color/symbol/size/width/hatch/rename) by trace name."""
        # [impl->req~ring5.figure.series-styling~1]
        if not spec.trace_overrides:
            return
        for handle, label in FigureSpecToMatplotlib._styleable_handles(ax):
            style = spec.trace_overrides.get(label)
            if style is None:
                continue
            marker = _PLOTLY_TO_MPL_MARKER.get(style.symbol) if style.symbol else None
            FigureSpecToMatplotlib._style_handle(
                handle,
                color=style.color or None,
                marker=marker,
                marker_size=style.marker_size if style.marker_size > 0 else None,
                line_width=style.line_width if style.line_width > 0 else None,
                hatch=style.hatching_pattern or None,
            )
            if style.display_name:
                handle.set_label(style.display_name)

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
            spec.title,
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
                x_label,
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
                y_label,
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
                            y2_label,
                            fontsize=typo.font_size_y2label,
                            fontweight=weight,
                            labelpad=spec.axes.y2.label_pad,
                        )
                    break

    @staticmethod
    def _apply_axis_ticks(
        spec: FigureConfig, ax: Axes, render_result: MatplotlibRenderResult | None = None
    ) -> None:
        """Configure tick labels, rotation, padding."""
        # [impl->req~ring5.figure.axes~1]
        import matplotlib.transforms as transforms

        typo = spec.typography
        if typo is None:
            raise ValueError("FigureConfig requires typography")
        if spec.axes is None:
            raise ValueError("FigureConfig requires axes")
        x_axis = spec.axes.x
        y_axis = spec.axes.y

        # Apply log scale BEFORE any explicit ticks below: set_xscale reinstalls a
        # LogLocator that would wipe a FixedLocator, so fixed ticks must come after.
        if x_axis.scale == "log":
            ax.set_xscale("log")
        if y_axis.scale == "log":
            ax.set_yscale("log")

        # Heatmap tick population — labels from the render result.
        # pcolormesh cells span [i, i+1), so centres are at i + 0.5.
        # Always override any pre-set tick_values (e.g. from
        # enrich_from_plotly) because pcolormesh requires cell-centre
        # positions; Plotly-extracted string tickvals are not valid here.
        hm_cols: list[str] | None = render_result.heatmap_col_labels if render_result else None
        hm_rows: list[str] | None = render_result.heatmap_row_labels if render_result else None
        # x_axis/y_axis belong to the per-render resolved (deep-copied) spec we
        # own here, so we override the frozen tick fields via object.__setattr__.
        if hm_cols:
            object.__setattr__(x_axis, "tick_values", [i + 0.5 for i in range(len(hm_cols))])
            object.__setattr__(x_axis, "tick_text", list(hm_cols))
        if hm_rows:
            object.__setattr__(y_axis, "tick_values", [i + 0.5 for i in range(len(hm_rows))])
            object.__setattr__(y_axis, "tick_text", list(hm_rows))

        # X-ticks
        weight = "bold" if typo.bold_ticks else "normal"
        x_on_top = x_axis.tick_side == "top"
        ax.tick_params(
            axis="x",
            labelsize=typo.font_size_ticks,
            pad=x_axis.tick_pad,
            bottom=x_axis.show_ticks and not x_on_top,
            top=x_axis.show_ticks and x_on_top,
            labelbottom=x_axis.show_tick_labels and not x_on_top,
            labeltop=x_axis.show_tick_labels and x_on_top,
        )

        if x_axis.tick_values is not None and x_axis.tick_text is not None:
            # tick_values may be strings (e.g. heatmap col labels from Plotly tickvals).
            # set_xticks requires numeric positions; fall back to integer indices.
            try:
                x_tick_positions: list[float] = [float(v) for v in x_axis.tick_values]
            except (TypeError, ValueError):
                x_tick_positions = list(range(len(x_axis.tick_values)))
            ax.set_xticks(x_tick_positions)
            ax.set_xticklabels(
                [str(t) for t in x_axis.tick_text],
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
        y_on_right = y_axis.tick_side == "right"
        ax.tick_params(
            axis="y",
            labelsize=typo.font_size_yticks,
            pad=y_axis.tick_pad,
            left=y_axis.show_ticks and not y_on_right,
            right=y_axis.show_ticks and y_on_right,
            labelleft=y_axis.show_tick_labels and not y_on_right,
            labelright=y_axis.show_tick_labels and y_on_right,
        )

        if y_axis.tick_values is not None and y_axis.tick_text is not None:
            # Same guard as x-axis: Plotly may supply string tickvals for heatmaps.
            try:
                y_tick_positions: list[float] = [float(v) for v in y_axis.tick_values]
            except (TypeError, ValueError):
                y_tick_positions = list(range(len(y_axis.tick_values)))
            ax.set_yticks(y_tick_positions)
            ax.set_yticklabels(
                [str(t) for t in y_axis.tick_text],
                fontsize=typo.font_size_yticks,
                rotation=y_axis.tick_angle,
            )

        # Y-axis tick rotation for auto-ticks (no explicit tick_values)
        if y_axis.tick_angle != 0 and y_axis.tick_values is None:
            for label in ax.get_yticklabels():
                label.set_rotation(y_axis.tick_angle)

    @staticmethod
    def _apply_axis_ranges(spec: FigureConfig, ax: Axes) -> None:
        """Set axis range limits and scale."""
        if spec.axes is None:
            raise ValueError("FigureConfig requires axes")
        x_axis = spec.axes.x
        y_axis = spec.axes.y

        if x_axis.range is not None:
            ax.set_xlim(*x_axis.range)
        if y_axis.range is not None:
            ax.set_ylim(*y_axis.range)

        # NOTE: log scale is applied earlier, in _apply_axis_ticks, so explicit fixed ticks
        # survive (set_xscale resets locators). Keep it out of this later step.

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
                linestyle=FigureSpecToMatplotlib._map_dash_style(x_axis.grid_dash),
                alpha=x_axis.grid_alpha,
            )
        else:
            ax.xaxis.grid(False)

        # Y grid
        if y_axis.show_grid:
            ax.yaxis.grid(
                True,
                color=y_axis.grid_color,
                linewidth=y_axis.grid_width,
                linestyle=FigureSpecToMatplotlib._map_dash_style(y_axis.grid_dash),
                alpha=y_axis.grid_alpha,
            )
        else:
            ax.yaxis.grid(False)

    @staticmethod
    def _anchor_to_mpl_loc(anchor_x: str, anchor_y: str) -> str:
        """Map legend anchor values to a matplotlib ``loc`` string.

        Combines vertical (``anchor_y``) and horizontal (``anchor_x``)
        anchors into one of matplotlib's canonical legend location names.
        """
        v_map = {"top": "upper", "bottom": "lower", "middle": "center", "auto": "upper"}
        h_map = {"left": "left", "right": "right", "center": "center", "auto": "left"}
        v = v_map.get(anchor_y, "upper")
        h = h_map.get(anchor_x, "left")
        if v == "center" and h == "center":
            return "center"
        return f"{v} {h}"

    @staticmethod
    def _apply_legends(spec: FigureConfig, ax: Axes) -> None:
        """Render legends with full spacing control."""
        # [impl->req~ring5.figure.legends~1]
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

            # Horizontal orientation: force many columns so items wrap in a row
            if legend.orientation == "horizontal" and kwargs["ncol"] <= 1:
                kwargs["ncol"] = 999  # matplotlib clamps to actual item count

            if legend.custom_position and legend.position_x >= 0:
                kwargs["loc"] = FigureSpecToMatplotlib._anchor_to_mpl_loc(
                    legend.anchor_x,
                    legend.anchor_y,
                )
                kwargs["bbox_to_anchor"] = (
                    legend.position_x,
                    legend.position_y if legend.position_y >= 0 else 1.0,
                )

            if legend.bgcolor:
                kwargs["facecolor"] = legend.bgcolor
            if legend.bgalpha >= 0:
                kwargs["framealpha"] = legend.bgalpha
            if legend.border_width > 0:
                kwargs["edgecolor"] = legend.border_color

            if legend.title:
                kwargs["title"] = legend.title
                if legend.title_font_size > 0:
                    kwargs["title_fontsize"] = legend.title_font_size

            # Apply font color to all legend types
            if legend.font_color:
                kwargs["labelcolor"] = legend.font_color

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
                # Secondary legend on the twin axis. When RING-5 created the dual axis
                # (``_ring5_twin``), ``apply_dual_axis`` places + styles the twin legend
                # AFTER the styling pipeline, so building one here would just be clobbered —
                # skip it (one twin-legend mechanism, no wasted/conflicting work). The
                # ``_twinned_axes`` fallback remains for a non-RING-5 twin.
                if getattr(ax, "_ring5_twin", None) is not None:
                    continue
                twin_ax: Axes | None = None
                for child_ax in ax.figure.get_axes():
                    if child_ax is not ax and hasattr(child_ax, "_twinned_axes"):
                        twin_ax = child_ax
                        break
                if twin_ax is None:
                    continue
                handles, labels = twin_ax.get_legend_handles_labels()
                if not labels:
                    continue
                leg = twin_ax.legend(**kwargs)
                if leg and legend.bold:
                    for text in leg.get_texts():
                        text.set_fontweight("bold")
                if leg and legend.title_font_color:
                    title_text = leg.get_title()
                    if title_text:
                        title_text.set_color(legend.title_font_color)
            elif legend.role == "tertiary":
                # Boxed legend — rendered via _apply_annotations from
                # enriched FigureConfig annotations.  If the annotations
                # pipeline already placed the content, we skip creating
                # a duplicate matplotlib legend here.  If explicit
                # legend items exist on a third axis, render them.
                pass  # Content comes from annotations, not traces

    @staticmethod
    def _escape_latex(text: str) -> str:
        r"""Escape untrusted text for TeX-backed export."""
        return escape_latex_text(text)

    # Layout decoration helpers
    _DASH_MAP: dict[str, str] = {
        "solid": "-",
        "dash": "--",
        "dot": ":",
        "dashdot": "-.",
    }

    @staticmethod
    def draw_layout_shapes(
        ax: Axes,
        separator_lines: list[SeparatorLine],
        shaded_regions: list[ShadedRegion],
        rule_lines: list[RuleLine] | None = None,
    ) -> None:
        """Draw engine-agnostic bar-group separators, shading bands and span rules.

        Mirrors the ``layout.shapes`` the Plotly trace converter builds (same
        data-x coordinates as the bar positions), so separators/shading appear
        in matplotlib too. Separators/shades are drawn beneath the bars; span
        rules (data-x, paper-y) live below the axis, so clipping is off.
        """
        for band in shaded_regions:
            ax.axvspan(
                band.x0,
                band.x1,
                facecolor=band.color,
                alpha=band.opacity,
                linewidth=0,
                zorder=0,
            )
        for sep in separator_lines:
            ls = FigureSpecToMatplotlib._DASH_MAP.get(sep.dash, "--")
            ax.axvline(
                sep.x,
                color=sep.color,
                linestyle=ls,
                linewidth=sep.width,
                zorder=0.5,
            )
        if rule_lines:
            from matplotlib.lines import Line2D
            from matplotlib.transforms import blended_transform_factory

            trans = blended_transform_factory(ax.transData, ax.transAxes)
            for rule in rule_lines:
                ax.add_line(
                    Line2D(
                        [rule.x0, rule.x1],
                        [rule.y, rule.y],
                        transform=trans,
                        color=rule.color,
                        linewidth=rule.width,
                        clip_on=False,
                        zorder=5,
                    )
                )

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
        """Apply the font family to every text artist that already exists.

        Artists created before this step (at figure creation and by the
        trace renderer) captured the process default at creation time; the
        ``rc_context`` established by :meth:`apply` covers artists created
        by the later steps. Global ``mpl.rcParams`` is deliberately never
        mutated — a mid-render mutation leaked process-wide and made the
        first figure of every process render in the wrong font.
        """
        # [impl->req~ring5.figure.typography~1]
        import matplotlib.text

        if spec.font_family:
            for text in ax.figure.findobj(matplotlib.text.Text):
                text.set_fontfamily(spec.font_family)

    @staticmethod
    def _apply_color_palette(spec: FigureConfig, ax: Axes) -> None:
        """Set colour cycle on the axes from spec.color_palette.

        NOTE: in the live render order this runs *after* traces are drawn (which already
        carry explicit colours from ``MatplotlibTraceRenderer.palette_colors``), so it is
        effectively a belt-and-suspenders default cycle for any artist drawn later. Plotly
        qualitative palettes return CSS ``rgb(r,g,b)`` strings, normalised to hex first.
        """
        if spec.color_palette:
            hex_colors = [_css_rgb_to_hex(c) for c in spec.color_palette]
            ax.set_prop_cycle(color=hex_colors)

    @staticmethod
    def _apply_reference_lines(spec: FigureConfig, ax: Axes) -> None:
        """Draw horizontal / vertical reference lines.

        Uses the ReferenceLineConfig list on FigureConfig.
        """
        # [impl->req~ring5.figure.reference-lines~1]
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
            # Draw the label explicitly (mirrors Plotly's annotation_text). The legend is
            # built earlier in the pipeline, so the line's legend ``label`` alone is never
            # collected — without this the label silently vanishes on the matplotlib engine.
            if rl.label:
                if rl.axis == "y":
                    ax.annotate(
                        rl.label,
                        xy=(0.995, rl.value),
                        xycoords=ax.get_yaxis_transform(),
                        ha="right",
                        va="bottom",
                        color=rl.color,
                        fontsize=8,
                        clip_on=False,
                        zorder=6,
                    )
                else:
                    ax.annotate(
                        rl.label,
                        xy=(rl.value, 0.995),
                        xycoords=ax.get_xaxis_transform(),
                        ha="right",
                        va="top",
                        color=rl.color,
                        fontsize=8,
                        clip_on=False,
                        zorder=6,
                    )

    @staticmethod
    def _apply_data_labels(spec: FigureConfig, ax: Axes) -> None:
        """Annotate bar containers with value labels.

        Falls back to ``ax.bar_label()`` when available (mpl 3.4+),
        otherwise silently skips.
        """
        # [impl->req~ring5.figure.data-labels~1]
        if spec.data_labels is None or not spec.data_labels.enabled:
            return

        dl: DataLabelConfig = spec.data_labels
        # A Plotly-style template (e.g. "%{y:.2f}") is not a Python format spec — wrapping it
        # produces "{:%{y:.2f}}" which ax.bar_label rejects with KeyError. The plotly engine
        # handles these natively; on matplotlib skip the labels rather than abort the figure.
        if dl.format_string and "%{" in dl.format_string:
            return
        safe_format = normalize_numeric_format(dl.format_string)
        fmt = f"{{:{safe_format}}}"

        color = dl.custom_color if dl.color_mode == "custom" else "#000000"
        # Clamp rotation to Plotly's accepted [-360, 360] for dual-engine parity.
        rotation = max(-360.0, min(360.0, float(dl.rotation)))

        for container in ax.containers:
            from matplotlib.container import BarContainer  # local: needs runtime class

            if not isinstance(container, BarContainer):
                continue
            try:
                ax.bar_label(
                    container,
                    fmt=fmt,
                    fontsize=dl.font_size,
                    rotation=rotation,
                    color=color,
                    label_type="edge" if dl.position == "outside" else "center",
                )
            except (AttributeError, TypeError, KeyError, ValueError):
                # mpl < 3.4, non-bar container, or an unparseable format string — degrade
                # gracefully (skip labels) rather than abort the whole figure build.
                pass

    @staticmethod
    def _apply_annotations(spec: FigureConfig, ax: Axes) -> None:
        """Render text annotations from spec onto the matplotlib axes.

        Handles ``xref``/``yref`` coordinate systems: ``"data"`` maps to
        data coordinates, ``"paper"`` maps to axes-fraction coordinates.

        Annotations with string data-coordinates (categorical x/y values)
        are resolved via the axis unit converter.  If the axis is numeric
        and the coordinate is a category name that can't be converted, the
        annotation is silently skipped.
        """
        # [impl->req~ring5.figure.shapes-annotations~1]
        if not spec.annotations:
            return

        import matplotlib.transforms as transforms
        import matplotlib.units as munits

        for ann in spec.annotations:
            if not ann.text:
                continue

            # Resolve coordinates
            x_coord: float | str = ann.x
            y_coord: float | str = ann.y

            # String coordinates with data-ref need conversion to the
            # axis's numeric scale.  E.g. 'Highway' on a numeric axis
            # for grouped stacked bar plots cannot be placed.
            if isinstance(x_coord, str) and ann.xref == "data":
                try:
                    x_coord = ax.xaxis.convert_units(x_coord)
                    if x_coord is None:
                        continue
                except (munits.ConversionError, ValueError, TypeError):
                    continue

            if isinstance(y_coord, str) and ann.yref == "data":
                try:
                    y_coord = ax.yaxis.convert_units(y_coord)
                    if y_coord is None:
                        continue
                except (munits.ConversionError, ValueError, TypeError):
                    continue

            # Convert HTML line breaks to newlines for matplotlib
            raw_text = ann.text.replace("<br>", "\n").replace("<br/>", "\n")
            # Strip any remaining HTML tags
            raw_text = re.sub(r"<[^>]+>", "", raw_text)
            # Convert HTML entities to plain characters
            raw_text = raw_text.replace("&nbsp;", " ").replace("&amp;", "&")
            text = raw_text

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
                    "facecolor": _css_color_to_mpl(ann.bgcolor) if ann.bgcolor else "none",
                    "edgecolor": ann.border_color or "none",
                    "linewidth": ann.border_width,
                }

            # Arrow: only set when requested, so annotations without an arrow render
            # byte-identically (the text sits at the point). When an arrow is asked
            # for, offset the text upward a little so the arrowhead is visible at the
            # point, honouring arrow_color (and arrow_head as the matplotlib arrowstyle).
            arrow_kwargs: dict[str, Any] = {}
            if ann.show_arrow:
                arrow_kwargs = {
                    "xytext": (0.0, 20.0),
                    "textcoords": "offset points",
                    "arrowprops": {
                        "arrowstyle": "-|>" if ann.arrow_head else "->",
                        "color": ann.arrow_color,
                    },
                }

            # By this point any data-ref string coordinate has been resolved to
            # a numeric value (or skipped above); cast satisfies the stricter
            # matplotlib stubs without altering runtime behavior.
            ax.annotate(
                text,
                xy=cast("tuple[float, float]", (x_coord, y_coord)),
                xycoords=transform,
                fontsize=fontsize,
                fontweight=fontweight,
                color=ann.font_color,
                ha=ha,
                va=va,
                rotation=ann.text_angle,
                bbox=bbox_props,
                annotation_clip=False,
                **arrow_kwargs,
            )

    @staticmethod
    def _apply_hatching(spec: FigureConfig, ax: Axes) -> None:
        """Apply hatching patterns from hatching_sequence to bar patches."""
        # [impl->req~ring5.figure.accessible-themes~1]
        if not spec.enable_stripes or not spec.hatching_sequence:
            return

        from matplotlib.container import BarContainer

        containers = [
            container for container in ax.containers if isinstance(container, BarContainer)
        ]
        for i, container in enumerate(containers):
            pattern = spec.hatching_sequence[i % len(spec.hatching_sequence)]
            for patch in container.patches:
                patch.set_hatch(pattern)

    @staticmethod
    def _apply_axis_colors(spec: FigureConfig, ax: Axes) -> None:
        """Apply tick_font_color, axis_line_color, axis_line_width.

        Also handles top/right axis line visibility via spines.
        """
        if spec.axes is None:
            return

        # Bottom (X) axis line
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

        # Left (Y) axis line
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
    def _reposition_colorbar(cbar: Any, primary: Any, is_horizontal: bool) -> None:
        """Reposition a matplotlib colorbar using legend position_x/position_y.

        After ``fig.colorbar()`` creates the colorbar, its axes occupy an
        auto-computed rectangle.  This helper moves that rectangle so the
        colorbar's anchor point lands at (position_x, position_y) in
        figure-fraction coordinates — matching the Plotly behaviour.
        """
        if not (primary.custom_position and primary.position_x >= 0 and primary.position_y >= 0):
            return

        pos = cbar.ax.get_position()
        w, h = pos.width, pos.height

        # Use same anchor logic as Plotly: x,y is the anchor corner.
        # For vertical colorbar the default anchor is top-left at (x, y).
        # For horizontal colorbar the default anchor is bottom-left.
        left = primary.position_x - w / 2
        bottom = primary.position_y - h / 2

        cbar.ax.set_position([left, bottom, w, h])

    @staticmethod
    def _style_colorbar_ticks(
        cbar: Any, cbar_cfg: ColorbarConfig, horizontal: bool = False
    ) -> None:
        """Apply tick rotation and tick side to a matplotlib colorbar."""
        tick_axis = cbar.ax.xaxis if horizontal else cbar.ax.yaxis
        labels = cbar.ax.get_xticklabels() if horizontal else cbar.ax.get_yticklabels()
        if cbar_cfg.tick_angle != 0.0:
            for label in labels:
                label.set_rotation(cbar_cfg.tick_angle)
        if cbar_cfg.tick_side == "left":
            if horizontal:
                tick_axis.tick_bottom()
            else:
                tick_axis.tick_left()
                tick_axis.set_label_position("left")

    @staticmethod
    def _apply_colorbar(
        spec: FigureConfig,
        ax: Axes,
        mappable: Any,
        title_override: str | None = None,
    ) -> None:
        """Create a colorbar from a mappable and apply styling from spec.

        Places the title on top and applies tick count + tick formatting
        from ``ColorbarConfig``.
        """
        from matplotlib.ticker import FormatStrFormatter, MaxNLocator

        # Determine orientation from legend config
        is_horizontal = False
        if spec.legends and spec.legends[0].orientation == "horizontal":
            is_horizontal = True

        cbar = ax.figure.colorbar(
            mappable,
            ax=ax,
            orientation="horizontal" if is_horizontal else "vertical",
        )

        # Read colorbar config from primary legend
        nticks = 5
        tick_decimals = 2
        title_text = title_override or ""
        title_kwargs: dict[str, Any] = {}

        if spec.legends:
            primary = spec.legends[0]
            cbar_cfg = primary.colorbar
            nticks = cbar_cfg.nticks
            tick_decimals = cbar_cfg.tick_decimals
            if not title_text:
                title_text = primary.title or ""
            if primary.title_font_size > 0:
                title_kwargs["fontsize"] = primary.title_font_size
            if primary.title_font_color:
                title_kwargs["color"] = primary.title_font_color

        # Title on top (set_title instead of set_label)
        if title_text:
            cbar.ax.set_title(title_text, **title_kwargs)

        # Tick count
        cbar.locator = MaxNLocator(nbins=nticks)
        cbar.update_ticks()

        # Tick format — use xaxis for horizontal, yaxis for vertical
        fmt = FormatStrFormatter(f"%.{tick_decimals}f")
        if is_horizontal:
            cbar.ax.xaxis.set_major_formatter(fmt)
        else:
            cbar.ax.yaxis.set_major_formatter(fmt)

        # Colorbar tick rotation and side
        if spec.legends:
            FigureSpecToMatplotlib._style_colorbar_ticks(
                cbar,
                spec.legends[0].colorbar,
                horizontal=is_horizontal,
            )
            FigureSpecToMatplotlib._reposition_colorbar(
                cbar,
                spec.legends[0],
                is_horizontal,
            )

    @staticmethod
    def apply_multi_heatmap_colorbars(
        spec: FigureConfig,
        fig: Figure,
        axes_list: list[Axes],
        render_results: list[MatplotlibRenderResult],
    ) -> None:
        """Apply colorbars to a multi-heatmap figure.

        In **shared** mode, one colorbar is created for the entire figure
        using the last heatmap's mappable.  In **individual** mode, each
        axes gets its own colorbar.

        Args:
            spec: Resolved FigureConfig.
            fig: The matplotlib Figure.
            axes_list: List of Axes, one per heatmap subplot.
            render_results: Corresponding render results (one per axes).
        """
        import matplotlib as mpl
        import matplotlib.text

        # This runs AFTER the per-axes apply() calls, so the colorbar's new
        # Axes/Text artists would otherwise be created with the process
        # default font instead of spec.font_family (the single-heatmap
        # colorbar is built inside apply()'s rc_context and is unaffected).
        font_rc: dict[RcKeyType, Any] = (
            {"font.family": spec.font_family} if spec.font_family else {}
        )
        with mpl.rc_context(font_rc):
            FigureSpecToMatplotlib._build_multi_heatmap_colorbars(
                spec, fig, axes_list, render_results
            )
        if spec.font_family:
            for text in fig.findobj(matplotlib.text.Text):
                text.set_fontfamily(spec.font_family)

    @staticmethod
    def _build_multi_heatmap_colorbars(
        spec: FigureConfig,
        fig: Figure,
        axes_list: list[Axes],
        render_results: list[MatplotlibRenderResult],
    ) -> None:
        """Create the colorbars (see :meth:`apply_multi_heatmap_colorbars`)."""
        from matplotlib.ticker import FormatStrFormatter, MaxNLocator

        nticks = 5
        tick_decimals = 2
        shared = True
        title_text = ""
        title_kwargs: dict[str, Any] = {}
        is_horizontal = False

        if spec.legends:
            primary = spec.legends[0]
            cbar_cfg = primary.colorbar
            nticks = cbar_cfg.nticks
            tick_decimals = cbar_cfg.tick_decimals
            shared = cbar_cfg.shared
            title_text = primary.title or ""
            is_horizontal = primary.orientation == "horizontal"
            if primary.title_font_size > 0:
                title_kwargs["fontsize"] = primary.title_font_size
            if primary.title_font_color:
                title_kwargs["color"] = primary.title_font_color

        orient_str = "horizontal" if is_horizontal else "vertical"
        fmt = FormatStrFormatter(f"%.{tick_decimals}f")

        if shared:
            # Find the last valid heatmap image
            last_image = None
            for rr in reversed(render_results):
                if rr.heatmap_image is not None:
                    last_image = rr.heatmap_image
                    break
            if last_image is not None:
                cbar = fig.colorbar(
                    last_image,
                    ax=axes_list,
                    shrink=0.8,
                    orientation=orient_str,
                )
                if title_text:
                    cbar.ax.set_title(title_text, **title_kwargs)
                cbar.locator = MaxNLocator(nbins=nticks)
                cbar.update_ticks()
                if is_horizontal:
                    cbar.ax.xaxis.set_major_formatter(fmt)
                else:
                    cbar.ax.yaxis.set_major_formatter(fmt)
                if spec.legends:
                    FigureSpecToMatplotlib._style_colorbar_ticks(
                        cbar,
                        spec.legends[0].colorbar,
                        horizontal=is_horizontal,
                    )
                    FigureSpecToMatplotlib._reposition_colorbar(
                        cbar,
                        spec.legends[0],
                        is_horizontal,
                    )
        else:
            # Individual colorbars per subplot
            for ax_item, rr in zip(axes_list, render_results):
                if rr.heatmap_image is not None:
                    cbar = fig.colorbar(
                        rr.heatmap_image,
                        ax=ax_item,
                        orientation=orient_str,
                    )
                    if title_text:
                        cbar.ax.set_title(title_text, **title_kwargs)
                    cbar.locator = MaxNLocator(nbins=nticks)
                    cbar.update_ticks()
                    if is_horizontal:
                        cbar.ax.xaxis.set_major_formatter(fmt)
                    else:
                        cbar.ax.yaxis.set_major_formatter(fmt)
                    if spec.legends:
                        FigureSpecToMatplotlib._style_colorbar_ticks(
                            cbar,
                            spec.legends[0].colorbar,
                            horizontal=is_horizontal,
                        )
                        FigureSpecToMatplotlib._reposition_colorbar(
                            cbar,
                            spec.legends[0],
                            is_horizontal,
                        )

    @staticmethod
    def create_multi_figure(
        spec: FigureConfig,
        nrows: int,
    ) -> tuple[Figure, list[Axes]]:
        """Create a multi-row figure for heatmap subplots.

        Args:
            spec: Resolved FigureConfig.
            nrows: Number of subplot rows.

        Returns:
            Tuple of (Figure, list of Axes).
        """
        import matplotlib.pyplot as plt

        dims = spec.dimensions
        if dims.dpi <= 1:
            render_dpi = 96
            width_in = dims.width / render_dpi
            height_in = dims.height / render_dpi
        else:
            render_dpi = dims.dpi
            width_in = dims.width
            height_in = dims.height

        # Scale height by number of rows
        total_height = height_in * nrows

        import matplotlib as mpl

        font_rc: dict[RcKeyType, Any] = (
            {"font.family": spec.font_family} if spec.font_family else {}
        )
        with mpl.rc_context(font_rc):
            fig, axes = plt.subplots(
                nrows=nrows,
                ncols=1,
                figsize=(width_in, total_height),
                dpi=render_dpi,
            )
        # Ensure axes is always a list
        if nrows == 1:
            axes_list: list[Axes] = [axes]
        else:
            axes_list = list(axes)

        fig.subplots_adjust(hspace=0.4)
        return fig, axes_list

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

        import matplotlib as mpl

        font_rc: dict[RcKeyType, Any] = (
            {"font.family": spec.font_family} if spec.font_family else {}
        )
        with mpl.rc_context(font_rc):
            fig, ax = plt.subplots(
                figsize=(width_in, height_in),
                dpi=render_dpi,
            )
        return fig, ax
