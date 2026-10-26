"""
Matplotlib connector — translate a resolved FigureConfig into matplotlib calls.

It reads from the shared FigureConfig — the single styling source of truth.

Usage:
    from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

    resolved = resolve_config(spec)
    # ``rendered`` is the explicit result of build_matplotlib_figure_from_prepared.
    FigureSpecToMatplotlib.apply(resolved, rendered)
"""

from __future__ import annotations

import logging
import re
from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

from src.core.common.safe_format import normalize_numeric_format
from src.core.models.visualization.data_label_config import DataLabelConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import LegendConfig
from src.core.models.visualization.trace_build_result import RuleLine, SeparatorLine, ShadedRegion
from src.web.rendering._matplotlib_lock import serialized_matplotlib
from src.web.rendering._render_result import MatplotlibFigureResult, MatplotlibRenderResult
from src.web.rendering._legend_projection import matplotlib_swatch, shared_legend_key
from src.web.rendering.matplotlib_colorbar import (
    prepare_colorbars,
    retire_colorbars,
    apply_colorbars,
)
from src.web.rendering._color_utils import css_color_to_matplotlib
from src.web.rendering._connector_protocol import validate_annotation_types
from src.web.rendering.latex_security import escape_latex_text

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.typing import RcKeyType

logger = logging.getLogger(__name__)

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


class FigureSpecToMatplotlib:
    """Stateless translator: FigureConfig → matplotlib axes updates.

    The FigureConfig must be **resolved** (no -1 sentinels) before calling.

    Note: matplotlib is imported lazily inside methods to avoid import
    errors when matplotlib is not installed (e.g., in unit tests that
    only test the spec model).
    """

    @staticmethod
    @serialized_matplotlib
    def apply(
        spec: FigureConfig,
        rendered: MatplotlibFigureResult,
        *,
        apply_margins: bool = True,
    ) -> None:
        """Style one native root after preflighting every supplied panel and output.

        Args:
            spec: Resolved styling with original-key overrides and canonical labels.
            rendered: The actual native figure and its explicit source associations.
            apply_margins: Apply common figure margins once after panel styling.

        Raises:
            ValueError: Any bound root, source, native member or generated role is invalid.
            TypeError: An annotation has no supported typed family.
        """
        rendered.validate()
        validate_annotation_types(spec.annotations)
        colorbars = prepare_colorbars(
            rendered,
            tuple(spec for _ in rendered.panels),
            layout_change=bool(
                apply_margins
                and rendered.panels
                and FigureSpecToMatplotlib._margins_changed(spec, rendered.panels[0].primary_axes)
            ),
        )
        retire_colorbars(colorbars)
        for panel in rendered.panels:
            FigureSpecToMatplotlib._apply_panel(
                spec,
                panel,
                apply_margins=False,
                apply_legends=not rendered.shared_legend,
            )
        if apply_margins and rendered.panels:
            FigureSpecToMatplotlib._apply_margins(spec, rendered.panels[0].primary_axes)
        apply_colorbars(colorbars)
        if rendered.shared_legend:
            FigureSpecToMatplotlib._project_shared_legends(
                rendered,
                tuple(spec for _ in rendered.panels),
            )

    @staticmethod
    @serialized_matplotlib
    def _apply_panel(
        spec: FigureConfig,
        render_result: MatplotlibRenderResult,
        *,
        apply_margins: bool = True,
        apply_legends: bool = True,
    ) -> None:
        """Apply the full FigureConfig to a matplotlib Axes.

        Args:
            spec: A resolved FigureConfig (no sentinel values).
            render_result: Explicit owned panel and source-to-native associations.
            apply_margins: Apply figure-wide margins. Dashboard panels disable
                this because their parent grid owns the outer layout.

        Raises:
            TypeError: An annotation has no supported typed family.
        """
        # [impl->req~ring5.extension.render-connector~1]
        render_result.validate()
        validate_annotation_types(spec.annotations)
        ax = render_result.primary_axes
        import matplotlib as mpl

        # Scope the font family to this build: artists the steps below create
        # (title, labels, ticks, legend, annotations) inherit it from the
        # rc_context; pre-existing artists are fixed by _apply_font_family.
        # The shared native-operation lock protects temporary rcParams changes.
        font_rc: dict[RcKeyType, Any] = (
            {"font.family": spec.font_family} if spec.font_family else {}
        )
        with mpl.rc_context(font_rc):
            # Pipeline order: see _connector_protocol.STYLING_PIPELINE_ORDER
            FigureSpecToMatplotlib._apply_backgrounds(spec, ax)
            FigureSpecToMatplotlib._apply_font_family(spec, ax)
            FigureSpecToMatplotlib._apply_color_palette(spec, ax)
            FigureSpecToMatplotlib._apply_title(spec, ax)
            FigureSpecToMatplotlib._apply_axis_labels(spec, render_result)
            FigureSpecToMatplotlib._apply_axis_ticks(spec, ax, render_result)
            FigureSpecToMatplotlib._apply_axis_ranges(spec, ax)
            FigureSpecToMatplotlib._apply_axis_colors(spec, ax)
            FigureSpecToMatplotlib._apply_grids(spec, ax)
            FigureSpecToMatplotlib._apply_secondary_axis(spec, render_result)
            FigureSpecToMatplotlib._apply_hatching(spec, render_result)
            # Per-trace styling must run before the legend is built so renames and
            # restyled handles are reflected (parity with the Plotly connector).
            FigureSpecToMatplotlib._apply_series_styling(spec, render_result)
            FigureSpecToMatplotlib._apply_trace_overrides(spec, render_result)
            if render_result.title_source is not None:
                source_name = render_result.title_source.original_name
                ax.set_title(spec.legend_labels.get(source_name, source_name))
            if apply_legends:
                FigureSpecToMatplotlib._apply_legends(spec, render_result)
            FigureSpecToMatplotlib._apply_reference_lines(spec, ax)
            FigureSpecToMatplotlib._apply_data_labels(spec, render_result)
            FigureSpecToMatplotlib._apply_annotations(spec, ax, render_result)
            if apply_margins:
                FigureSpecToMatplotlib._apply_margins(spec, ax)

    # Per-trace styling (parity with the Plotly connector)

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
        from matplotlib.markers import MarkerStyle
        from matplotlib.patches import Patch

        fill = css_color_to_matplotlib(color) if color else None
        edge = css_color_to_matplotlib(edge_color) if edge_color else None

        if isinstance(handle, BarContainer):
            for patch in handle.patches:
                if fill:
                    patch.set_facecolor(fill)
                if alpha is not None:
                    patch.set_alpha(alpha)
                if hatch is not None:
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
                handle.set_facecolor(fill)
            if alpha is not None:
                handle.set_alpha(alpha)
            if marker:
                marker_style = MarkerStyle(marker)
                handle.set_paths(
                    [marker_style.get_path().transformed(marker_style.get_transform())]
                )
            if marker_size is not None:
                # Scatter collections use area; configuration specifies diameter.
                handle.set_sizes([float(marker_size) ** 2])
            if edge:
                handle.set_edgecolor(edge)
            if edge_width is not None:
                handle.set_linewidth(edge_width)
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
            if hatch is not None:
                handle.set_hatch(hatch)
            if edge:
                handle.set_edgecolor(edge)
            if edge_width is not None:
                handle.set_linewidth(edge_width)

    @staticmethod
    def _apply_series_styling(spec: FigureConfig, rendered: MatplotlibRenderResult) -> None:
        """Cycle positional styles by original source ordinal, including hidden slots."""
        # [impl->req~ring5.figure.series-styling~1]
        if not spec.series_styles:
            return
        for binding in rendered.bindings:
            style = spec.series_styles[binding.source_ordinal % len(spec.series_styles)]
            for handle in binding.style_targets:
                FigureSpecToMatplotlib._style_handle(
                    handle,
                    alpha=style.opacity if style.opacity > 0 else None,
                    line_width=style.line_width if style.line_width > 0 else None,
                    marker_size=style.marker_size if style.marker_size > 0 else None,
                    edge_color=(
                        (style.bar_border_color or "#000") if style.bar_border_width > 0 else None
                    ),
                    edge_width=style.bar_border_width if style.bar_border_width > 0 else None,
                    hatch=style.hatching_pattern if binding.family == "bar" else None,
                )

    @staticmethod
    def _apply_trace_overrides(spec: FigureConfig, rendered: MatplotlibRenderResult) -> None:
        """Apply visual overrides by immutable original source name."""
        # [impl->req~ring5.figure.series-styling~1]
        for binding in rendered.bindings:
            style = spec.trace_overrides.get(binding.original_name)
            if style is None:
                continue
            semantic = binding.family in ("waterfall", "sankey", "parallel_coordinates", "heatmap")
            marker = _PLOTLY_TO_MPL_MARKER.get(style.symbol) if style.symbol else None
            for handle in binding.style_targets:
                FigureSpecToMatplotlib._style_handle(
                    handle,
                    color=style.color if style.color and not semantic else None,
                    marker=marker,
                    marker_size=style.marker_size if style.marker_size > 0 else None,
                    line_width=style.line_width if style.line_width > 0 else None,
                    hatch=style.hatching_pattern if binding.family == "bar" else None,
                )

    @staticmethod
    def _margin_values(spec: FigureConfig) -> dict[str, float] | None:
        """Compute the current figure-margin projection without mutating native layout."""
        if spec.dimensions is None or spec.dimensions.margins is None:
            return None
        dims, margins = spec.dimensions, spec.dimensions.margins
        if dims.width <= 0 or dims.height <= 0:
            return None
        left = max(0.0, min(0.99, margins.left / (dims.width * dims.dpi)))
        right = max(left + 0.01, min(1.0, 1.0 - margins.right / (dims.width * dims.dpi)))
        bottom = max(0.0, min(0.99, margins.bottom / (dims.height * dims.dpi)))
        top = max(bottom + 0.01, min(1.0, 1.0 - margins.top / (dims.height * dims.dpi)))
        return dict(left=left, right=right, bottom=bottom, top=top)

    @staticmethod
    def _margins_changed(spec: FigureConfig, ax: Axes) -> bool:
        values = FigureSpecToMatplotlib._margin_values(spec)
        engine = ax.figure.get_layout_engine()
        if values is None or (engine is not None and not engine.adjust_compatible):
            return False
        params = ax.figure.subplotpars
        return any(getattr(params, name) != value for name, value in values.items())

    @staticmethod
    def _apply_margins(spec: FigureConfig, ax: Axes) -> None:
        """Apply changed figure margins once, preserving an existing colorbar allocation."""
        if not FigureSpecToMatplotlib._margins_changed(spec, ax):
            return
        values = FigureSpecToMatplotlib._margin_values(spec)
        if values is None:
            return
        try:
            ax.figure.subplots_adjust(**values)
        except ValueError as error:
            logger.warning("Could not apply margins %s: %s", values, error)

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
    def _apply_axis_labels(spec: FigureConfig, rendered: MatplotlibRenderResult) -> None:
        """Set X and Y axis labels with proper typography."""
        ax = rendered.primary_axes
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
            if spec.axes.y.title_angle is not None:
                ax.yaxis.label.set_rotation(-spec.axes.y.title_angle)
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

        child_ax = rendered.secondary_axes
        if spec.axes.y2 is not None and child_ax is not None and spec.axes.y2.label:
            child_ax.set_ylabel(
                spec.axes.y2.label,
                fontsize=typo.font_size_y2label,
                fontweight="bold" if typo.bold_y2label else "normal",
                labelpad=spec.axes.y2.label_pad,
            )

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
        # neutral preparation) because pcolormesh requires cell-centre
        # positions; Plotly-extracted string tickvals are not valid here.
        hm_cols: list[str] | None = render_result.heatmap_col_labels if render_result else None
        hm_rows: list[str] | None = render_result.heatmap_row_labels if render_result else None
        if hm_cols:
            x_axis = replace(
                x_axis, tick_values=[i + 0.5 for i in range(len(hm_cols))], tick_text=list(hm_cols)
            )
        if hm_rows:
            y_axis = replace(
                y_axis, tick_values=[i + 0.5 for i in range(len(hm_rows))], tick_text=list(hm_rows)
            )

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

        if x_axis.label_aliases:
            positions = ax.get_xticks()
            labels = [
                x_axis.label_aliases.get(label.get_text(), label.get_text())
                for label in ax.get_xticklabels()
            ]
            ax.set_xticks(positions, labels)

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
                color=css_color_to_matplotlib(x_axis.grid_color),
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
                color=css_color_to_matplotlib(y_axis.grid_color),
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
    def _apply_secondary_axis(spec: FigureConfig, rendered: MatplotlibRenderResult) -> None:
        """Style only this panel's owned right axis from the resolved specification."""
        twin = rendered.secondary_axes
        y2 = spec.axes.y2
        if twin is None or y2 is None:
            return
        twin.set_yscale(y2.scale)
        if y2.range is not None:
            twin.set_ylim(*y2.range)
        if y2.tick_values is not None:
            twin.set_yticks([float(value) for value in y2.tick_values], y2.tick_text)
        elif y2.dtick is not None and y2.dtick > 0 and y2.scale == "linear":
            from matplotlib.ticker import MultipleLocator

            twin.yaxis.set_major_locator(MultipleLocator(y2.dtick))
        on_left = y2.tick_side == "left"
        twin.tick_params(
            axis="y",
            left=on_left and y2.show_ticks,
            right=not on_left and y2.show_ticks,
            labelleft=on_left and y2.show_tick_labels,
            labelright=not on_left and y2.show_tick_labels,
            pad=y2.tick_pad,
            labelrotation=y2.tick_angle,
            labelsize=spec.typography.font_size_y2ticks,
            colors=y2.tick_font_color or y2.axis_color,
        )
        if y2.show_grid:
            twin.yaxis.grid(
                True,
                color=css_color_to_matplotlib(y2.grid_color),
                linewidth=y2.grid_width,
                linestyle=FigureSpecToMatplotlib._map_dash_style(y2.grid_dash),
                alpha=y2.grid_alpha,
            )
        else:
            twin.yaxis.grid(False)
        twin.yaxis.label.set_color(y2.axis_color)
        twin.yaxis.labelpad = y2.label_standoff if y2.label_standoff >= 0 else y2.label_pad
        twin.yaxis.label.set_y(y2.label_position + y2.title_vshift / 100.0)
        if y2.title_angle is not None:
            twin.yaxis.label.set_rotation(-y2.title_angle)
        twin.spines["right"].set_color(y2.axis_line_color or y2.axis_color)
        twin.spines["right"].set_linewidth(y2.axis_line_width)
        if spec.font_family:
            twin.yaxis.label.set_fontfamily(spec.font_family)
            for label in twin.get_yticklabels():
                label.set_fontfamily(spec.font_family)

    @staticmethod
    def _legend_kwargs(legend: LegendConfig) -> dict[str, Any]:
        """Translate one resolved legend style for either axes or figure composition."""
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
            kwargs["facecolor"] = css_color_to_matplotlib(legend.bgcolor)
            if isinstance(kwargs["facecolor"], tuple) and len(kwargs["facecolor"]) == 4:
                kwargs["framealpha"] = kwargs["facecolor"][3]
        if legend.bgalpha >= 0:
            kwargs["framealpha"] = legend.bgalpha
        if legend.border_width > 0:
            kwargs["edgecolor"] = css_color_to_matplotlib(legend.border_color)

        if legend.title:
            kwargs["title"] = legend.title
            if legend.title_font_size > 0:
                kwargs["title_fontsize"] = legend.title_font_size

        # Apply font color to all legend types
        if legend.font_color:
            kwargs["labelcolor"] = css_color_to_matplotlib(legend.font_color)

        return kwargs

    @staticmethod
    def _style_legend(legend: LegendConfig, native: Any) -> None:
        """Apply text and border properties shared by native legend containers."""
        if legend.bold:
            for text in native.get_texts():
                text.set_fontweight("bold")
        if legend.title_font_color:
            native.get_title().set_color(css_color_to_matplotlib(legend.title_font_color))
        if legend.border_width > 0:
            native.get_frame().set_linewidth(legend.border_width)

    @staticmethod
    def _clear_owned_legends(ax: Axes) -> None:
        """Remove only role artists recorded by this renderer on these axes."""
        owned = getattr(ax, "_ring5_legend_artists", {})
        for artist in owned.values():
            attached = any(candidate is artist for candidate in ax.artists)
            if attached or ax.get_legend() is artist:
                artist.remove()
        cast(Any, ax)._ring5_legend_artists = {}

    @staticmethod
    def _apply_legends(spec: FigureConfig, rendered: MatplotlibRenderResult) -> None:
        """Project display labels from owned sources after native styling."""
        # [impl->req~ring5.figure.legends~1]
        ax, twin = rendered.primary_axes, rendered.secondary_axes
        for target in (ax,) if twin is None else (ax, twin):
            FigureSpecToMatplotlib._clear_owned_legends(target)
        for legend in spec.legends:
            if not legend.visible or legend.role not in ("primary", "secondary"):
                continue
            target = ax if legend.role == "primary" or twin is None else twin
            entries = [
                binding
                for binding in rendered.bindings
                if binding.legend_role == legend.role
                and binding.show_in_legend
                and binding.legend_handle is not None
            ]
            if not entries:
                continue
            handles = [
                handle for binding in entries if (handle := binding.legend_handle) is not None
            ]
            labels = [
                spec.legend_labels.get(binding.original_name, binding.original_name)
                for binding in entries
            ]
            previous = target.get_legend()
            if previous is not None and not any(artist is previous for artist in target.artists):
                target.add_artist(previous)
            native = target.legend(handles, labels, **FigureSpecToMatplotlib._legend_kwargs(legend))
            if native is not None:
                FigureSpecToMatplotlib._style_legend(legend, native)
                cast(Any, target)._ring5_legend_artists[legend.role] = native

    @staticmethod
    def _project_shared_legends(
        rendered: MatplotlibFigureResult,
        specs: tuple[FigureConfig, ...],
    ) -> None:
        """Replace only this root's shared legend using final source-owned swatches."""
        rendered.validate()
        if len(specs) != len(rendered.panels):
            raise ValueError("Shared legend projection requires every actual panel specification.")
        entries: list[tuple[Any, str]] = []
        seen: set[tuple[Any, ...]] = set()
        for panel, spec in zip(rendered.panels, specs, strict=True):
            visibility = {legend.role: legend.visible for legend in spec.legends}
            for binding in panel.bindings:
                if (
                    not binding.show_in_legend
                    or binding.legend_handle is None
                    or not visibility.get(binding.legend_role, True)
                ):
                    continue
                display = spec.legend_labels.get(binding.original_name, binding.original_name)
                key = shared_legend_key(binding, display, matplotlib_swatch(binding))
                if key is not None:
                    if key in seen:
                        continue
                    seen.add(key)
                entries.append((binding.legend_handle, display))
        previous = rendered.native_outputs.legend
        if previous is not None:
            previous.remove()
            rendered.native_outputs.legend = None
        for panel in rendered.panels:
            for axes in (panel.primary_axes, panel.secondary_axes):
                if axes is not None:
                    FigureSpecToMatplotlib._clear_owned_legends(axes)
        if not entries or not specs or not specs[0].legends:
            return
        primary = specs[0].legends[0]
        options = FigureSpecToMatplotlib._legend_kwargs(primary)
        options.update(loc="lower center", ncol=min(4, len(entries)), bbox_to_anchor=(0.5, 0.01))
        native = rendered.figure.legend(
            [entry[0] for entry in entries], [entry[1] for entry in entries], **options
        )
        rendered.native_outputs.legend = native
        FigureSpecToMatplotlib._style_legend(primary, native)

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
            fig.patch.set_facecolor(css_color_to_matplotlib(spec.paper_bgcolor))
        if spec.plot_bgcolor:
            ax.set_facecolor(css_color_to_matplotlib(spec.plot_bgcolor))

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
        qualitative palettes retain their CSS colors through native RGB projection.
        """
        if spec.color_palette:
            colors = [css_color_to_matplotlib(c) for c in spec.color_palette]
            ax.set_prop_cycle(color=colors)

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
    def _apply_data_labels(spec: FigureConfig, rendered: MatplotlibRenderResult) -> None:
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

        for binding in rendered.bindings:
            for container in binding.owned_data:
                from matplotlib.container import BarContainer  # local: needs runtime class

                if not isinstance(container, BarContainer):
                    continue
                try:
                    binding.axes.bar_label(
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
    def _apply_annotations(
        spec: FigureConfig,
        ax: Axes,
        render_result: MatplotlibRenderResult | None = None,
    ) -> None:
        """Render text annotations from spec onto the matplotlib axes.

        Handles ``xref``/``yref`` coordinate systems: ``"data"`` maps to
        data coordinates, ``"paper"`` maps to axes-fraction coordinates.

        Categorical bar annotations use the renderer's raw category positions,
        independently of displayed tick renames. Other string coordinates use
        the axis unit converter; unknown categories are skipped.
        """
        # [impl->req~ring5.figure.shapes-annotations~1]
        validate_annotation_types(spec.annotations)
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

            if isinstance(x_coord, str) and ann.xref == "data":
                if render_result is not None and x_coord in render_result.x_category_positions:
                    x_coord = render_result.x_category_positions[x_coord]
                else:
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

            if ann.x_shift_pixels or ann.y_shift_pixels:
                # Capture the native render scale; dpi_scale_trans then preserves
                # logical-pixel offsets when savefig or Streamlit changes DPI.
                render_dpi = ax.figure.dpi
                transform = transform + transforms.ScaledTranslation(
                    ann.x_shift_pixels / render_dpi,
                    ann.y_shift_pixels / render_dpi,
                    ax.figure.dpi_scale_trans,
                )

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
                    "facecolor": css_color_to_matplotlib(ann.bgcolor) if ann.bgcolor else "none",
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
                fontfamily=ann.font_family or spec.font_family or None,
                color=ann.font_color,
                multialignment=ann.align,
                ha=ha,
                va=va,
                rotation=ann.text_angle,
                bbox=bbox_props,
                annotation_clip=False,
                **arrow_kwargs,
            )

    @staticmethod
    def _apply_hatching(spec: FigureConfig, rendered: MatplotlibRenderResult) -> None:
        """Apply default bar hatches by original source slot before explicit overrides."""
        # [impl->req~ring5.figure.accessible-themes~1]
        if not spec.enable_stripes or not spec.hatching_sequence:
            return
        for binding in rendered.bindings:
            if binding.family != "bar":
                continue
            pattern = spec.hatching_sequence[binding.source_ordinal % len(spec.hatching_sequence)]
            for handle in binding.style_targets:
                FigureSpecToMatplotlib._style_handle(handle, hatch=pattern)

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
    @serialized_matplotlib
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

        total_height = height_in

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
    @serialized_matplotlib
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
