"""
Plotly connector — translate resolved FigureConfig into go.Figure updates.

The neutral preparation owner delegates to ``ConfigSpecBuilder`` to
build a FigureConfig and then calls this connector to apply it.

Usage:
    from src.web.rendering.plotly_connector import FigureSpecToPlotly

    resolved = resolve_config(spec)
    # ``rendered`` is the explicit result of traces_to_plotly or build_plotly_figure.
    FigureSpecToPlotly.apply(resolved, rendered)
"""

from __future__ import annotations

from src.web.rendering._appearance import prepare_plotly_appearance, apply_plotly_appearance

from typing import TYPE_CHECKING, Any

import plotly.graph_objects as go

from src.core.common.safe_format import plotly_numeric_template
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.legend_config import LegendConfig
from src.web.rendering._color_utils import color_with_alpha
from src.web.rendering._hatch_utils import plotly_hatch
from src.web.rendering._render_result import PlotlyRenderResult
from src.web.rendering._legend_projection import project_plotly_shared

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
    def apply(spec: FigureConfig, rendered: PlotlyRenderResult) -> None:
        # [impl->req~ring5.render.plotly~1]
        # [impl->req~ring5.extension.render-connector~1]
        """Apply the full FigureConfig to a Plotly figure.

        Args:
            spec: A resolved FigureConfig (no sentinel values).
            rendered: Explicit native root and source-to-trace associations.

        Raises:
            ValueError: Any source, native membership or generated role is invalid.
        """
        # Pipeline order: see _connector_protocol.STYLING_PIPELINE_ORDER
        rendered.validate()
        appearance = prepare_plotly_appearance(spec, rendered)
        fig = rendered.figure
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
        FigureSpecToPlotly._apply_stripes(spec, rendered)
        apply_plotly_appearance(appearance)
        FigureSpecToPlotly._apply_series_styling(spec, rendered)
        FigureSpecToPlotly._apply_trace_overrides(spec, rendered)
        FigureSpecToPlotly._apply_axis_colors(spec, fig)
        FigureSpecToPlotly._project_labels(spec, rendered)
        project_plotly_shared(rendered)

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

        if y_axis.label and y_axis.title_angle is None:
            update["title"] = dict(
                text=y_axis.label,
                font=dict(size=typo.font_size_ylabel),
            )
            if y_axis.label_standoff >= 0:
                update["title"]["standoff"] = int(y_axis.label_standoff)  # type: ignore[index]
            # Note: vshift (title_vshift) is Matplotlib-only — Plotly's
            # yaxis.Title only supports text, font, standoff.  Vertical
            # repositioning is handled via Matplotlib's set_label_coords.
        elif y_axis.title_angle is not None:
            update["title"] = dict(text="")

        update["tickfont"] = dict(size=typo.font_size_yticks)

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

        if y2.label and y2.title_angle is None:
            update["title"] = dict(
                text=y2.label,
                font=dict(size=typo.font_size_y2label),
            )
            if y2.label_standoff >= 0:
                update["title"]["standoff"] = int(y2.label_standoff)  # type: ignore[index]
        elif y2.title_angle is not None:
            update["title"] = dict(text="")

        update["tickfont"] = dict(
            size=typo.font_size_y2ticks, color=y2.tick_font_color or y2.axis_color
        )
        update["tickangle"] = y2.tick_angle

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
        for legend in spec.legends[1:]:
            if not legend.visible:
                continue
            legend_key = "legend2" if legend.role == "secondary" else "legend3"
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

        from src.web.rendering._heatmap_utils import heatmap_ranges

        limits = heatmap_ranges(heatmap_traces, cbar)

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
            "x": None,
            "y": None,
            "orientation": "h" if primary.orientation == "horizontal" else "v",
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

        for index, (trace, (lower, upper)) in enumerate(zip(heatmap_traces, limits, strict=True)):
            trace.update(
                zmin=lower,
                zmax=upper,
                showscale=not cbar.shared or index == len(heatmap_traces) - 1,
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
            # None clears a prior explicit value when automatic placement returns.
            "x": None,
            "y": None,
            "xanchor": None,
            "yanchor": None,
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
            result["bgcolor"] = (
                color_with_alpha(legend.bgcolor, legend.bgalpha)
                if legend.bgalpha >= 0
                else legend.bgcolor
            )
        elif legend.bgalpha >= 0:
            result["bgcolor"] = color_with_alpha("#FFFFFF", legend.bgalpha)
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

            # Heatmaps do not support marker-based coloring. Waterfalls encode
            # meaning through their increasing/decreasing/totals markers.
            if trace_type in ("heatmap", "waterfall", "sankey", "parcoords"):
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
            if isinstance(trace, (go.Heatmap, go.Box, go.Violin, go.Sankey, go.Parcoords)):
                continue

            textfont: dict[str, Any] = {"size": font_size}
            if dl.color_mode == "custom" and dl.custom_color:
                textfont["color"] = dl.custom_color
            update: dict[str, Any] = {"texttemplate": texttemplate, "textfont": textfont}
            if isinstance(trace, (go.Bar, go.Waterfall)):
                update.update(
                    textposition=text_position,
                    textangle=rotation,
                    constraintext="inside" if dl.size_constraint == "inside" else "none",
                )
                if dl.size_constraint == "inside":
                    update["textposition"] = "inside"
                if update["textposition"] == "inside" and dl.anchor in ("top", "middle", "bottom"):
                    update["insidetextanchor"] = dl.anchor
            elif isinstance(trace, (go.Scatter, go.Scatterpolar)):
                update["textposition"] = (
                    "middle center" if text_position == "inside" else "top center"
                )
                mode = str(trace.mode or "lines")
                parts = [part for part in mode.split("+") if part not in ("text", "none")]
                parts.append("text")
                update["mode"] = "+".join(parts) or "none"
                if isinstance(trace, go.Scatterpolar):
                    update["texttemplate"] = texttemplate.replace("%{y", "%{r")
            else:
                continue

            trace.update(**update)

        # Uniform text (layout-level) when constraint is active
        if dl.size_constraint == "inside":
            min_size = max(6, font_size - 4)
            fig.update_layout(
                uniformtext=dict(mode="hide", minsize=min_size),
            )

    @staticmethod
    def _apply_series_styling(spec: FigureConfig, rendered: PlotlyRenderResult) -> None:
        """Apply per-trace dimensions and patterns after appearance projection."""
        # [impl->req~ring5.figure.series-styling~2]
        if not spec.series_styles:
            return

        for binding in (item for panel in rendered.panel_bindings for item in panel):
            trace = binding.native_trace
            # Use modular index to cycle through styles
            style = spec.series_styles[binding.source_ordinal % len(spec.series_styles)]
            trace_type = str(getattr(trace, "type", ""))

            update: dict[str, Any] = {}
            if style.line_width > 0 and not isinstance(trace, go.Parcoords):
                if hasattr(trace, "line"):
                    update["line"] = dict(width=style.line_width)
            if style.marker_size > 0:
                # marker.size only applies to scatter-like traces
                if trace_type in ("scatter", "scattergl", "scatterpolar", "box", "violin"):
                    marker_update = update.get("marker", {})
                    marker_update["size"] = style.marker_size
                    update["marker"] = marker_update
            if style.bar_border_width > 0 and hasattr(trace, "marker"):
                marker_update = update.get("marker", {})
                marker_update["line"] = dict(width=style.bar_border_width)
                update["marker"] = marker_update
            if style.hatching_pattern is not None and trace_type in ("bar", "histogram"):
                marker_update = update.get("marker", {})
                marker_update["pattern"] = {
                    **plotly_hatch(style.hatching_pattern),
                    "fillmode": "replace",
                }
                update["marker"] = marker_update

            if update:
                trace.update(**update)

    @staticmethod
    def _apply_stripes(spec: FigureConfig, rendered: PlotlyRenderResult) -> None:
        """Alternating row background shapes."""
        if not spec.enable_stripes:
            return

        # Apply hatching pattern to bar-like traces only (scatter doesn't
        # support marker.pattern).
        if spec.hatching_sequence:
            for binding in (item for panel in rendered.panel_bindings for item in panel):
                trace = binding.native_trace
                if not isinstance(trace, (go.Bar, go.Histogram)):
                    continue
                pattern = spec.hatching_sequence[
                    binding.source_ordinal % len(spec.hatching_sequence)
                ]
                trace.update(
                    marker=dict(
                        pattern={**plotly_hatch(pattern), "fillmode": "replace"},
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
    def _apply_trace_overrides(spec: FigureConfig, rendered: PlotlyRenderResult) -> None:
        """Apply per-trace styling overrides keyed by trace name.

        ``spec.trace_overrides`` maps original trace names to typed
        ``SeriesStyleConfig`` instances.  Each matching trace gets colour,
        symbol, size, width, pattern, and/or rename applied.
        """
        if not spec.trace_overrides:
            return

        for binding in (item for panel in rendered.panel_bindings for item in panel):
            trace = binding.native_trace
            trace_type = str(getattr(trace, "type", ""))
            t_name = binding.original_name
            if t_name not in spec.trace_overrides:
                continue
            style = spec.trace_overrides[t_name]

            if style.symbol and trace_type in (
                "scatter",
                "scattergl",
                "scatterpolar",
                "box",
                "violin",
            ):
                trace.update(marker=dict(symbol=style.symbol))

            if style.marker_size > 0 and trace_type in (
                "scatter",
                "scattergl",
                "scatterpolar",
                "box",
                "violin",
            ):
                trace.update(marker=dict(size=style.marker_size))

            if style.line_width > 0 and trace_type in (
                "scatter",
                "scattergl",
                "scatterpolar",
                "box",
                "violin",
            ):
                trace.update(line=dict(width=style.line_width))

            if style.hatching_pattern is not None and trace_type in ("bar", "histogram"):
                trace.update(
                    marker=dict(
                        pattern={**plotly_hatch(style.hatching_pattern), "fillmode": "replace"},
                    )
                )

    @staticmethod
    def _project_labels(spec: FigureConfig, rendered: PlotlyRenderResult) -> None:
        """Project text after styling without changing source or linked-group identity."""
        # [impl->req~ring5.figure.ordering-renaming~2]
        role_visibility = {legend.role: legend.visible for legend in spec.legends}
        for panel in rendered.panel_bindings:
            for binding in panel:
                trace = binding.native_trace
                trace.name = spec.legend_labels.get(binding.original_name, binding.original_name)
                if isinstance(
                    trace,
                    (
                        go.Bar,
                        go.Histogram,
                        go.Scatter,
                        go.Scattergl,
                        go.Scatterpolar,
                        go.Box,
                        go.Violin,
                        go.Waterfall,
                    ),
                ):
                    trace.showlegend = (
                        binding.show_in_legend
                        and trace.visible is not False
                        and role_visibility.get(binding.legend_role, True)
                    )
        annotations = {
            annotation.name: annotation
            for annotation in rendered.figure.layout.annotations or ()
            if annotation.name is not None
        }
        for role in rendered.layout_roles:
            if role.appearance is not None:
                continue
            source = role.source.original_name
            annotations[role.role_name].text = spec.legend_labels.get(source, source)

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

        Explicit category order comes first, followed by unlisted values in
        encounter order. Without an explicit order, values are alphabetical.
        """

        if not axis.label_aliases:
            return

        mapping: dict[str, str] = axis.label_aliases

        # Grouped geometry already owns numeric positions and their display labels.
        # Apply aliases to those labels without replacing positions with trace X values.
        if axis.tick_values is not None and axis.tick_text is not None:
            update["tickmode"] = "array"
            update["tickvals"] = list(axis.tick_values)
            update["ticktext"] = [mapping.get(text, text) for text in axis.tick_text]
            return

        unique_vals: list[str] = []
        seen: set[str] = set()
        for trace in _fig_traces(fig):
            if hasattr(trace, "x") and trace.x is not None:
                for x_val in trace.x:
                    key = str(x_val)
                    if key not in seen:
                        unique_vals.append(key)
                        seen.add(key)

        if axis.category_order is not None:
            ordered = list(dict.fromkeys(axis.category_order))
            ordered.extend(value for value in unique_vals if value not in ordered)
        else:
            ordered = sorted(unique_vals)

        # Build tickvals/ticktext: map through aliases, preserving originals
        tickvals: list[str] = ordered
        ticktext: list[str] = [mapping.get(v, v) for v in ordered]

        update["tickmode"] = "array"
        update["tickvals"] = tickvals
        update["ticktext"] = ticktext
