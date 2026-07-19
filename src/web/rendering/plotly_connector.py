"""
Plotly connector — translate resolved FigureConfig into go.Figure updates.

``StyleApplicator.apply_styles()`` delegates to ``ConfigSpecBuilder`` to
build a FigureConfig and then calls this connector to apply it.

Usage:
    from src.web.rendering import FigureSpecToPlotly

    resolved = resolve_config(spec)
    fig = FigureSpecToPlotly.apply(resolved, fig)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import plotly.graph_objects as go

from src.core.common.safe_format import plotly_numeric_template
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import LegendConfig
from src.web.rendering._heatmap_utils import compute_nice_range, compute_z_extent

if TYPE_CHECKING:
    from src.core.models.visualization.axis_config import AxisConfig


def _apply_grid_alpha(hex_color: str, alpha: float) -> str:
    """Convert a hex color + alpha to an ``rgba()`` string for Plotly.

    Plotly does not support a separate grid alpha property; transparency
    must be baked into the color value using CSS ``rgba()`` notation.

    When *alpha* is 1.0, the original hex color is returned unchanged.
    """
    if alpha >= 1.0:
        return hex_color
    hex_clean = hex_color.lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    try:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
    except (ValueError, IndexError):
        return hex_color
    return f"rgba({r},{g},{b},{alpha:.2f})"


def _fig_traces(fig: go.Figure) -> tuple[Any, ...]:
    """Return figure traces with correct typing.

    Plotly 6.x inline types do not properly annotate ``Figure.data``;
    iterating it makes Pyright infer each element as a string literal
    instead of a trace object.  This thin wrapper centralises the
    single ``type: ignore`` needed to work around the gap.
    """
    traces: tuple[Any, ...] = fig.data  # type: ignore[assignment]
    return traces


class FigureSpecToPlotly:
    """Stateless translator: FigureConfig → Plotly figure updates.

    All methods are static / class-level — no instance state needed.
    The FigureConfig must be **resolved** (no -1 sentinels) before calling.
    """

    @staticmethod
    def apply(spec: FigureConfig, fig: go.Figure) -> go.Figure:
        # [impl->req~ring5.render.plotly~1]
        # [impl->req~ring5.extension.render-connector~1]
        """Apply the full FigureConfig to a Plotly figure.

        Args:
            spec: A resolved FigureConfig (no sentinel values).
            fig: The Plotly figure to update in place.

        Returns:
            The same figure, updated.
        """
        # Pipeline order: see _connector_protocol.STYLING_PIPELINE_ORDER
        FigureSpecToPlotly._apply_dimensions(spec, fig)
        FigureSpecToPlotly._apply_backgrounds(spec, fig)
        FigureSpecToPlotly._apply_title(spec, fig)
        FigureSpecToPlotly._apply_xaxis(spec, fig)
        FigureSpecToPlotly._apply_yaxis(spec, fig)
        FigureSpecToPlotly._apply_y2axis(spec, fig)
        FigureSpecToPlotly._apply_legends(spec, fig)
        FigureSpecToPlotly._apply_heatmap_colorbars(spec, fig)
        FigureSpecToPlotly._apply_color_palette(spec, fig)
        FigureSpecToPlotly._apply_hovermode(spec, fig)
        FigureSpecToPlotly._apply_font_family(spec, fig)
        FigureSpecToPlotly._apply_reference_lines(spec, fig)
        FigureSpecToPlotly._apply_data_labels(spec, fig)
        FigureSpecToPlotly._apply_series_styling(spec, fig)
        FigureSpecToPlotly._apply_trace_overrides(spec, fig)
        FigureSpecToPlotly._apply_stripes(spec, fig)
        FigureSpecToPlotly._apply_axis_colors(spec, fig)
        return fig

    @staticmethod
    def _apply_dimensions(spec: FigureConfig, fig: go.Figure) -> None:
        """Set figure width, height, margins, and bar gaps."""
        dims = spec.dimensions
        # Plotly uses pixels; convert inches → px
        dpi = dims.dpi if dims.dpi > 0 else 96
        width_px = int(dims.width * dpi)
        height_px = int(dims.height * dpi)

        margins = dims.margins
        fig.update_layout(
            width=width_px,
            height=height_px,
            margin=dict(
                t=int(margins.top),
                b=int(margins.bottom),
                l=int(margins.left),
                r=int(margins.right),
                pad=int(margins.pad),
            ),
            bargap=dims.bargap,
            bargroupgap=dims.bargroupgap,
        )

    @staticmethod
    def _apply_backgrounds(spec: FigureConfig, fig: go.Figure) -> None:
        """Set paper and plot background colors."""
        # [impl->req~ring5.figure.colors~1]
        fig.update_layout(
            paper_bgcolor=spec.paper_bgcolor,
            plot_bgcolor=spec.plot_bgcolor,
        )

    @staticmethod
    def _apply_title(spec: FigureConfig, fig: go.Figure) -> None:
        """Set figure title with typography from spec."""
        if spec.title:
            typo = spec.typography
            if typo is None:
                raise ValueError("FigureConfig.typography must not be None")
            fig.update_layout(
                title=dict(
                    text=spec.title,
                    font=dict(
                        size=typo.font_size_title,
                    ),
                ),
            )

    @staticmethod
    def _apply_xaxis(spec: FigureConfig, fig: go.Figure) -> None:
        """Configure the primary X-axis."""
        # [impl->req~ring5.figure.axes~1]
        if spec.axes is None:
            raise ValueError("FigureConfig requires axes")
        if spec.typography is None:
            raise ValueError("FigureConfig requires typography")
        x_axis = spec.axes.x
        typo = spec.typography

        update: dict[str, Any] = {}

        if x_axis.label:
            update["title"] = dict(
                text=x_axis.label,
                font=dict(size=typo.font_size_xlabel),
            )
            if x_axis.label_standoff >= 0:
                update["title"]["standoff"] = int(x_axis.label_standoff)  # type: ignore[index]

        update["tickfont"] = dict(size=typo.font_size_ticks)
        update["tickangle"] = x_axis.tick_angle

        if x_axis.range is not None:
            update["range"] = x_axis.range
        if x_axis.scale != "linear":
            update["type"] = x_axis.scale
        if x_axis.dtick is not None:
            update["dtick"] = x_axis.dtick

        update["showgrid"] = x_axis.show_grid
        if x_axis.show_grid:
            update["gridcolor"] = _apply_grid_alpha(x_axis.grid_color, x_axis.grid_alpha)
            update["gridwidth"] = x_axis.grid_width
            update["griddash"] = x_axis.grid_dash

        update["showticklabels"] = x_axis.show_tick_labels
        update["ticks"] = "outside" if x_axis.show_ticks else ""
        update["automargin"] = x_axis.automargin

        if x_axis.tick_side and x_axis.tick_side != "bottom":
            update["side"] = x_axis.tick_side

        # Tick label standoff (distance from axis)
        if x_axis.tick_pad != 5.0:  # skip default to avoid noise
            update["ticklabelstandoff"] = int(x_axis.tick_pad)

        if x_axis.category_order is not None:
            update["categoryorder"] = "array"
            update["categoryarray"] = x_axis.category_order

        # Label aliases → tickvals / ticktext
        if x_axis.label_aliases:
            FigureSpecToPlotly._apply_label_aliases(
                x_axis,
                fig,
                update,
            )

        fig.update_xaxes(**update)

    @staticmethod
    def _apply_yaxis(spec: FigureConfig, fig: go.Figure) -> None:
        """Configure the primary Y-axis."""
        # [impl->req~ring5.figure.axes~1]
        if spec.axes is None:
            raise ValueError("FigureConfig requires axes")
        if spec.typography is None:
            raise ValueError("FigureConfig requires typography")
        y_axis = spec.axes.y
        typo = spec.typography

        update: dict[str, Any] = {}

        if y_axis.label:
            update["title"] = dict(
                text=y_axis.label,
                font=dict(size=typo.font_size_ylabel),
            )
            if y_axis.label_standoff >= 0:
                update["title"]["standoff"] = int(y_axis.label_standoff)  # type: ignore[index]
            # Note: vshift (title_vshift) is Matplotlib-only — Plotly's
            # yaxis.Title only supports text, font, standoff.  Vertical
            # repositioning is handled via Matplotlib's set_label_coords.

        update["tickfont"] = dict(size=typo.font_size_yticks)

        if y_axis.tick_angle != 0:
            update["tickangle"] = y_axis.tick_angle

        if y_axis.range is not None:
            update["range"] = y_axis.range
        if y_axis.scale != "linear":
            update["type"] = y_axis.scale
        if y_axis.dtick is not None:
            update["dtick"] = y_axis.dtick

        update["showgrid"] = y_axis.show_grid
        if y_axis.show_grid:
            update["gridcolor"] = _apply_grid_alpha(y_axis.grid_color, y_axis.grid_alpha)
            update["gridwidth"] = y_axis.grid_width
            update["griddash"] = y_axis.grid_dash

        update["showticklabels"] = y_axis.show_tick_labels
        update["ticks"] = "outside" if y_axis.show_ticks else ""
        update["automargin"] = y_axis.automargin

        if y_axis.tick_side and y_axis.tick_side != "left":
            update["side"] = y_axis.tick_side

        fig.update_yaxes(**update, selector=dict(overlaying=None))

    @staticmethod
    def _apply_y2axis(spec: FigureConfig, fig: go.Figure) -> None:
        """Configure the secondary Y-axis (if present)."""
        if spec.axes is None:
            raise ValueError("FigureConfig requires axes")
        if spec.typography is None:
            raise ValueError("FigureConfig requires typography")
        if spec.axes.y2 is None:
            return

        y2 = spec.axes.y2
        typo = spec.typography

        update: dict[str, Any] = {
            "overlaying": "y",
            "side": "right",
        }

        if y2.label:
            update["title"] = dict(
                text=y2.label,
                font=dict(size=typo.font_size_y2label),
            )
            if y2.label_standoff >= 0:
                update["title"]["standoff"] = int(y2.label_standoff)  # type: ignore[index]

        update["tickfont"] = dict(size=typo.font_size_y2ticks)

        if y2.range is not None:
            update["range"] = y2.range
        if y2.dtick is not None:
            update["dtick"] = y2.dtick

        update["showgrid"] = y2.show_grid
        if y2.show_grid:
            update["gridcolor"] = _apply_grid_alpha(y2.grid_color, y2.grid_alpha)
            update["gridwidth"] = y2.grid_width
            update["griddash"] = y2.grid_dash

        update["showticklabels"] = y2.show_tick_labels
        update["ticks"] = "outside" if y2.show_ticks else ""

        fig.update_layout(yaxis2=update)

    @staticmethod
    def _apply_legends(spec: FigureConfig, fig: go.Figure) -> None:
        """Apply legend configuration for all legends."""
        # [impl->req~ring5.figure.legends~1]
        if not spec.legends:
            return

        # Primary legend (legend1)
        primary = spec.legends[0]
        legend_update = FigureSpecToPlotly._build_legend_dict(primary)
        fig.update_layout(legend=legend_update)

        # Secondary legends (legend2, legend3) if multi-legend layout
        for i, legend in enumerate(spec.legends[1:], start=2):
            if not legend.visible:
                continue
            legend_key = f"legend{i}"
            legend_dict = FigureSpecToPlotly._build_legend_dict(legend)
            fig.update_layout(**{legend_key: legend_dict})  # type: ignore[arg-type]

    @staticmethod
    def _apply_heatmap_colorbars(spec: FigureConfig, fig: go.Figure) -> None:
        """Configure colorbar(s) on heatmap traces.

        Reads ``ColorbarConfig`` from the primary legend and applies:
        - title on top with ``<br>`` line breaks
        - shared vs individual colorbar mode
        - zmin/zmax (manual or auto with nice rounding)
        - tick count and tick formatting
        """
        if not spec.legends:
            return

        primary = spec.legends[0]
        cbar = primary.colorbar

        heatmap_traces = [t for t in _fig_traces(fig) if isinstance(t, go.Heatmap)]
        if not heatmap_traces:
            return

        # Determine z-range
        if cbar.range_mode == "manual" and cbar.zmin is not None and cbar.zmax is not None:
            zmin, zmax = float(cbar.zmin), float(cbar.zmax)
        else:
            # Auto mode: scan all heatmap z-values, apply nice rounding
            raw_min, raw_max = compute_z_extent(heatmap_traces)
            zmin, zmax, _ = compute_nice_range(raw_min, raw_max, cbar.nticks)

        # Build colorbar dict
        title_text = primary.title.replace("\n", "<br>") if primary.title else ""
        title_font: dict[str, Any] = {}
        if primary.title_font_size > 0:
            title_font["size"] = primary.title_font_size
        if primary.title_font_color:
            title_font["color"] = primary.title_font_color

        tick_format = f".{cbar.tick_decimals}f"

        colorbar_dict: dict[str, Any] = {
            "title": {
                "text": title_text,
                "side": cbar.title_side,
                "font": title_font,
            },
            "nticks": cbar.nticks,
            "tickformat": tick_format,
        }

        if cbar.tick_angle != 0.0:
            colorbar_dict["tickangle"] = cbar.tick_angle
        if cbar.tick_side != "right":
            colorbar_dict["ticklabelposition"] = f"outside {cbar.tick_side}"

        # Colorbar position and orientation from legend config
        if primary.custom_position and primary.position_x >= 0:
            colorbar_dict["x"] = primary.position_x
        if primary.custom_position and primary.position_y >= 0:
            colorbar_dict["y"] = primary.position_y
        if primary.orientation == "horizontal":
            colorbar_dict["orientation"] = "h"

        # Apply to traces
        if cbar.shared:
            # Shared mode: all traces get same zmin/zmax, only last shows colorbar
            for i, trace in enumerate(heatmap_traces):
                trace.update(zmin=zmin, zmax=zmax)
                if i < len(heatmap_traces) - 1:
                    trace.update(showscale=False)
                else:
                    trace.update(showscale=True, colorbar=colorbar_dict)
        else:
            # Individual mode: each trace gets its own nice range + colorbar
            for trace in heatmap_traces:
                t_min, t_max = compute_z_extent([trace])
                t_zmin, t_zmax, _ = compute_nice_range(t_min, t_max, cbar.nticks)
                trace.update(
                    zmin=t_zmin,
                    zmax=t_zmax,
                    showscale=True,
                    colorbar=colorbar_dict,
                )

    @staticmethod
    def _build_legend_dict(legend: LegendConfig) -> dict[str, Any]:
        """Build a Plotly legend configuration dictionary."""
        font_dict: dict[str, Any] = {
            "size": legend.font_size,
            "color": legend.font_color,
        }
        if legend.font_family:
            font_dict["family"] = legend.font_family

        result: dict[str, Any] = {
            "font": font_dict,
            "orientation": "h" if legend.orientation == "horizontal" else "v",
            "itemsizing": legend.itemsizing,
        }

        if legend.itemwidth > 0:
            # Plotly requires itemwidth >= 30
            result["itemwidth"] = max(30, legend.itemwidth)
        if legend.tracegroupgap > 0:
            result["tracegroupgap"] = legend.tracegroupgap

        # Multi-column layout via entrywidth.
        # When ncol > 1 and the user hasn't set a manual entrywidth,
        # auto-compute: divide the available space equally across columns.
        # When ncol == 1, force single-column so Plotly doesn't auto-wrap.
        effective_entrywidth = legend.entrywidth
        if legend.ncol > 1 and effective_entrywidth <= 0:
            # Use fraction mode: each entry gets 1/ncol of the plot width.
            result["entrywidth"] = round(1.0 / legend.ncol, 4)
            result["entrywidthmode"] = "fraction"
        elif legend.ncol == 1 and effective_entrywidth <= 0:
            # Force single column — each entry takes full width.
            result["entrywidth"] = 1.0
            result["entrywidthmode"] = "fraction"
        elif effective_entrywidth > 0:
            result["entrywidth"] = effective_entrywidth
            result["entrywidthmode"] = "pixels"

        # Indentation for grouped items
        if legend.indentation != 0:
            result["indentation"] = legend.indentation

        if legend.title:
            result["title"] = dict(
                text=legend.title,
                font=dict(
                    size=legend.title_font_size,
                    color=legend.title_font_color,
                ),
            )

        if legend.custom_position and legend.position_x >= 0:
            result["x"] = legend.position_x
        if legend.custom_position and legend.position_y >= 0:
            result["y"] = legend.position_y

        if legend.anchor_x != "auto":
            result["xanchor"] = legend.anchor_x
        if legend.anchor_y != "auto":
            result["yanchor"] = legend.anchor_y

        if legend.bgcolor:
            result["bgcolor"] = legend.bgcolor
        if legend.border_width > 0:
            result["borderwidth"] = legend.border_width
            result["bordercolor"] = legend.border_color

        if legend.valign != "middle":
            result["valign"] = legend.valign

        if legend.order == "reversed":
            result["traceorder"] = "reversed"

        return result

    # Palette and layout decoration helpers
    @staticmethod
    def _apply_color_palette(spec: FigureConfig, fig: go.Figure) -> None:
        """Set colorway and explicitly assign palette colors to traces.

        In addition to setting the layout ``colorway`` (for any future
        traces), this assigns palette colours to existing traces that
        don't already have an explicit ``marker.color`` set (e.g. by the
        plot factory or upstream styling when ``use_color=True``).
        """
        if not spec.color_palette:
            return

        fig.update_layout(colorway=spec.color_palette)

        for i, trace in enumerate(_fig_traces(fig)):
            trace_type = str(getattr(trace, "type", ""))

            # Heatmaps do not support marker-based coloring.
            # Their color is controlled by z-values and colorscale.
            if trace_type == "heatmap":
                continue

            # Skip traces that already have an explicit marker color
            # (set by the factory when use_color=True).
            existing_color = (
                getattr(trace.marker, "color", None) if hasattr(trace, "marker") else None
            )
            if existing_color is not None:
                continue

            col = spec.color_palette[i % len(spec.color_palette)]
            trace.update(marker=dict(color=col))
            if hasattr(trace, "line") and trace_type in (
                "scatter",
                "scattergl",
            ):
                trace.update(line=dict(color=col))

    @staticmethod
    def _apply_hovermode(spec: FigureConfig, fig: go.Figure) -> None:
        """Set hovermode from spec."""
        # [impl->req~ring5.figure.plotly-hovermode~1]
        fig.update_layout(hovermode=spec.hovermode)

    @staticmethod
    def _apply_font_family(spec: FigureConfig, fig: go.Figure) -> None:
        """Set global font family."""
        # [impl->req~ring5.figure.typography~1]
        if spec.font_family:
            fig.update_layout(font=dict(family=spec.font_family))

    @staticmethod
    def _apply_reference_lines(spec: FigureConfig, fig: go.Figure) -> None:
        """Add horizontal/vertical reference lines via fig.add_shape()."""
        # [impl->req~ring5.figure.reference-lines~1]
        for rl in spec.reference_lines:
            if not rl.enabled:
                continue
            if rl.axis == "y":
                fig.add_hline(
                    y=rl.value,
                    line_dash=rl.style,
                    line_color=rl.color,
                    line_width=rl.width,
                    annotation_text=rl.label if rl.label else None,
                )
            elif rl.axis == "x":
                fig.add_vline(
                    x=rl.value,
                    line_dash=rl.style,
                    line_color=rl.color,
                    line_width=rl.width,
                    annotation_text=rl.label if rl.label else None,
                )

    @staticmethod
    def _apply_data_labels(spec: FigureConfig, fig: go.Figure) -> None:
        """Apply data label annotations on bars/points."""
        # [impl->req~ring5.figure.data-labels~1]
        if spec.data_labels is None or not spec.data_labels.enabled:
            return

        dl = spec.data_labels

        # Clamp font size (6..100)
        font_size = max(6, min(100, dl.font_size))

        # Clamp rotation (-360..360)
        rotation = max(-360, min(360, dl.rotation))

        # Map position: valid Plotly textposition values
        valid_positions = {"auto", "inside", "outside", "none"}
        text_position = dl.position if dl.position in valid_positions else "auto"

        texttemplate = plotly_numeric_template(dl.format_string)

        for trace in _fig_traces(fig):
            # Heatmap traces don't support textposition/texttemplate —
            # their cell labels are handled separately via annotations.
            if isinstance(trace, go.Heatmap):
                continue

            update: dict[str, Any] = {
                "texttemplate": texttemplate,
                "textposition": text_position,
                "textangle": rotation,
                "textfont": dict(size=font_size),
            }

            # Custom color
            if dl.color_mode == "custom" and dl.custom_color:
                update["textfont"]["color"] = dl.custom_color

            # Constraint handling
            if dl.size_constraint == "inside":
                update["constraintext"] = "inside"
                update["textposition"] = "inside"
            else:
                update["constraintext"] = "none"

            # Inside text anchor (only for "inside" position)
            is_inside = text_position == "inside" or dl.size_constraint == "inside"
            if is_inside and dl.anchor in ("top", "middle", "bottom"):
                update["insidetextanchor"] = dl.anchor

            trace.update(**update)

        # Uniform text (layout-level) when constraint is active
        if dl.size_constraint == "inside":
            min_size = max(6, font_size - 4)
            fig.update_layout(
                uniformtext=dict(mode="hide", minsize=min_size),
            )

    @staticmethod
    def _apply_series_styling(spec: FigureConfig, fig: go.Figure) -> None:
        """Apply per-trace line_width, marker, opacity from series_styles."""
        # [impl->req~ring5.figure.series-styling~1]
        if not spec.series_styles:
            return

        for i, trace in enumerate(_fig_traces(fig)):
            # Use modular index to cycle through styles
            style = spec.series_styles[i % len(spec.series_styles)]

            update: dict[str, Any] = {}
            if style.opacity > 0:
                update["opacity"] = style.opacity
            if style.line_width > 0:
                if hasattr(trace, "line"):
                    update["line"] = dict(width=style.line_width)
            if style.marker_size > 0:
                # marker.size only applies to scatter-like traces
                if hasattr(trace, "marker") and not isinstance(trace, go.Bar):
                    marker_update = update.get("marker", {})
                    marker_update["size"] = style.marker_size
                    update["marker"] = marker_update
            if style.bar_border_width > 0:
                marker_update = update.get("marker", {})
                marker_update["line"] = dict(
                    width=style.bar_border_width,
                    color=style.bar_border_color or "#000",
                )
                update["marker"] = marker_update

            if update:
                trace.update(**update)

    @staticmethod
    def _apply_stripes(spec: FigureConfig, fig: go.Figure) -> None:
        """Alternating row background shapes."""
        if not spec.enable_stripes:
            return

        # Apply hatching pattern to bar-like traces only (scatter doesn't
        # support marker.pattern).
        if spec.hatching_sequence:
            for i, trace in enumerate(_fig_traces(fig)):
                if not isinstance(trace, (go.Bar, go.Histogram)):
                    continue
                pattern = spec.hatching_sequence[i % len(spec.hatching_sequence)]
                trace.update(
                    marker=dict(
                        pattern=dict(shape=pattern, fillmode="replace"),
                    )
                )

    @staticmethod
    def _apply_axis_colors(spec: FigureConfig, fig: go.Figure) -> None:
        """Apply tick/label/line colors and widths for all axis lines.

        Handles bottom (X), left (Y), top, and right axis lines.
        Width of 0 hides the line.
        """
        if spec.axes is None:
            raise ValueError("FigureConfig requires axes")

        x = spec.axes.x
        y = spec.axes.y

        # Bottom (X) axis line
        x_update: dict[str, Any] = {}
        if x.tick_font_color:
            x_update["tickfont"] = dict(color=x.tick_font_color)

        show_x_line = x.axis_line_width > 0
        x_update["showline"] = show_x_line
        if show_x_line:
            x_update["linewidth"] = x.axis_line_width
            x_update["linecolor"] = x.axis_line_color or x.axis_color

        # Top axis line via mirror
        top_w = spec.axes.top_axis_line_width
        if top_w > 0 and show_x_line:
            # Plotly mirror copies the bottom line to the top
            x_update["mirror"] = True
        elif top_w > 0 and not show_x_line:
            # Show only the top line: use mirror + showline, but this
            # also shows the bottom.  Plotly cannot show only the top
            # via native mirror, so we add a shape instead.
            FigureSpecToPlotly._add_axis_line_shape(
                fig,
                axis="top",
                color=spec.axes.top_axis_line_color,
                width=top_w,
            )

        if x_update:
            fig.update_xaxes(**x_update)

        # Left (Y) axis line
        y_update: dict[str, Any] = {}
        if y.tick_font_color:
            y_update["tickfont"] = dict(color=y.tick_font_color)

        show_y_line = y.axis_line_width > 0
        y_update["showline"] = show_y_line
        if show_y_line:
            y_update["linewidth"] = y.axis_line_width
            y_update["linecolor"] = y.axis_line_color or y.axis_color

        # Right axis line via mirror (when no Y2 axis)
        right_w = spec.axes.right_axis_line_width
        if spec.axes.y2 is None:
            if right_w > 0 and show_y_line:
                y_update["mirror"] = True
            elif right_w > 0 and not show_y_line:
                FigureSpecToPlotly._add_axis_line_shape(
                    fig,
                    axis="right",
                    color=spec.axes.right_axis_line_color,
                    width=right_w,
                )

        if y_update:
            fig.update_yaxes(**y_update, selector=dict(overlaying=None))

        # Y2 axis line (when dual axis)
        if spec.axes.y2 is not None:
            y2 = spec.axes.y2
            y2_update: dict[str, Any] = {}
            show_y2_line = y2.axis_line_width > 0
            y2_update["showline"] = show_y2_line
            if show_y2_line:
                y2_update["linewidth"] = y2.axis_line_width
                y2_update["linecolor"] = y2.axis_line_color or y2.axis_color
            if y2_update:
                fig.update_layout(yaxis2={**y2_update})

    @staticmethod
    def _add_axis_line_shape(
        fig: go.Figure,
        axis: str,
        color: str,
        width: float,
    ) -> None:
        """Add a shape acting as an axis line for top or right edges."""
        if axis == "top":
            fig.add_shape(
                type="line",
                x0=0,
                x1=1,
                y0=1,
                y1=1,
                xref="paper",
                yref="paper",
                line=dict(color=color, width=width),
            )
        elif axis == "right":
            fig.add_shape(
                type="line",
                x0=1,
                x1=1,
                y0=0,
                y1=1,
                xref="paper",
                yref="paper",
                line=dict(color=color, width=width),
            )

    # Per-trace overrides and axis aliases
    @staticmethod
    def _apply_trace_overrides(spec: FigureConfig, fig: go.Figure) -> None:
        """Apply per-trace styling overrides keyed by trace name.

        ``spec.trace_overrides`` maps original trace names to typed
        ``SeriesStyleConfig`` instances.  Each matching trace gets colour,
        symbol, size, width, pattern, and/or rename applied.
        """
        if not spec.trace_overrides:
            return

        for trace in _fig_traces(fig):
            trace_type = str(getattr(trace, "type", ""))
            t_name = str(getattr(trace, "name", ""))
            if t_name not in spec.trace_overrides:
                continue
            style = spec.trace_overrides[t_name]

            if style.display_name:
                trace.name = style.display_name

            if style.color and trace_type != "heatmap":
                trace.update(marker=dict(color=style.color))
                if hasattr(trace, "line") and trace_type in (
                    "scatter",
                    "scattergl",
                ):
                    trace.update(line=dict(color=style.color))

            if style.symbol and trace_type != "heatmap":
                trace.update(marker=dict(symbol=style.symbol))

            if style.marker_size > 0 and trace_type != "heatmap":
                trace.update(marker=dict(size=style.marker_size))

            if style.line_width > 0 and trace_type in ("scatter", "scattergl"):
                trace.update(line=dict(width=style.line_width))

            if style.hatching_pattern and trace_type != "heatmap":
                trace.update(
                    marker=dict(
                        pattern=dict(
                            shape=style.hatching_pattern,
                            fillmode="replace",
                        ),
                    )
                )

    @staticmethod
    def _apply_label_aliases(
        axis: AxisConfig,
        fig: go.Figure,
        update: dict[str, Any],
    ) -> None:
        """Translate axis label aliases to Plotly tickvals/ticktext.

        The alias mapping (e.g. ``{"a": "Alpha", "b": "Beta"}``) is stored
        in ``AxisConfig.label_aliases`` and resolved here into ``tickmode``,
        ``tickvals``, and ``ticktext``.

        When ``category_order`` is also set, the order is used for
        ``tickvals``; otherwise, values are sorted alphabetically.
        """

        if not axis.label_aliases:
            return

        mapping: dict[str, str] = axis.label_aliases

        # Determine order: explicit category_order if set, else sorted unique
        if axis.category_order is not None:
            ordered = list(axis.category_order)
        else:
            # Collect unique x-values from traces
            unique_vals: list[str] = []
            seen: set[str] = set()
            for trace in _fig_traces(fig):
                if hasattr(trace, "x") and trace.x is not None:
                    for x_val in trace.x:
                        key = str(x_val)
                        if key not in seen:
                            unique_vals.append(key)
                            seen.add(key)
            ordered = sorted(unique_vals)

        # Build tickvals/ticktext: map through aliases, preserving originals
        tickvals: list[str] = ordered
        ticktext: list[str] = [mapping.get(v, v) for v in ordered]

        update["tickmode"] = "array"
        update["tickvals"] = tickvals
        update["ticktext"] = ticktext
