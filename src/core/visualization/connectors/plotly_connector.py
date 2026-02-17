"""
Plotly connector — translate resolved FigureSpec into go.Figure updates.

``StyleApplicator.apply_styles()`` delegates to ``ConfigSpecBuilder`` to
build a FigureSpec and then calls this connector to apply it.

Usage:
    from src.core.visualization.connectors import FigureSpecToPlotly

    resolved = resolve_spec(spec)
    fig = FigureSpecToPlotly.apply(resolved, fig)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import plotly.graph_objects as go

from src.core.visualization.figure_spec import FigureSpec
from src.core.visualization.legend_spec import LegendSpec

if TYPE_CHECKING:
    from src.core.visualization.axis_spec import AxisSpec


class FigureSpecToPlotly:
    """Stateless translator: FigureSpec → Plotly figure updates.

    All methods are static / class-level — no instance state needed.
    The FigureSpec must be **resolved** (no -1 sentinels) before calling.
    """

    @staticmethod
    def apply(spec: FigureSpec, fig: go.Figure) -> go.Figure:
        """Apply the full FigureSpec to a Plotly figure.

        Args:
            spec: A resolved FigureSpec (no sentinel values).
            fig: The Plotly figure to update in place.

        Returns:
            The same figure, updated.
        """
        FigureSpecToPlotly._apply_dimensions(spec, fig)
        FigureSpecToPlotly._apply_backgrounds(spec, fig)
        FigureSpecToPlotly._apply_title(spec, fig)
        FigureSpecToPlotly._apply_xaxis(spec, fig)
        FigureSpecToPlotly._apply_yaxis(spec, fig)
        FigureSpecToPlotly._apply_y2axis(spec, fig)
        FigureSpecToPlotly._apply_legends(spec, fig)
        FigureSpecToPlotly._apply_color_palette(spec, fig)
        FigureSpecToPlotly._apply_hovermode(spec, fig)
        FigureSpecToPlotly._apply_font_family(spec, fig)
        FigureSpecToPlotly._apply_reference_lines(spec, fig)
        FigureSpecToPlotly._apply_data_labels(spec, fig)
        FigureSpecToPlotly._apply_series_styling(spec, fig)
        FigureSpecToPlotly._apply_trace_overrides(spec, fig)
        FigureSpecToPlotly._apply_separator_lines(spec, fig)
        FigureSpecToPlotly._apply_stripes(spec, fig)
        FigureSpecToPlotly._apply_axis_colors(spec, fig)
        return fig

    @staticmethod
    def _apply_dimensions(spec: FigureSpec, fig: go.Figure) -> None:
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
    def _apply_backgrounds(spec: FigureSpec, fig: go.Figure) -> None:
        """Set paper and plot background colors."""
        fig.update_layout(
            paper_bgcolor=spec.paper_bgcolor,
            plot_bgcolor=spec.plot_bgcolor,
        )

    @staticmethod
    def _apply_title(spec: FigureSpec, fig: go.Figure) -> None:
        """Set figure title with typography from spec."""
        if spec.title:
            typo = spec.typography
            assert typo is not None  # guaranteed by __post_init__  # nosec B101
            fig.update_layout(
                title=dict(
                    text=spec.title,
                    font=dict(
                        size=typo.font_size_title,
                    ),
                ),
            )

    @staticmethod
    def _apply_xaxis(spec: FigureSpec, fig: go.Figure) -> None:
        """Configure the primary X-axis."""
        assert spec.axes is not None  # guaranteed by __post_init__  # nosec B101
        assert spec.typography is not None  # guaranteed by __post_init__  # nosec B101
        x_axis = spec.axes.x
        typo = spec.typography

        update: Dict[str, Any] = {}

        if x_axis.label:
            update["title"] = dict(
                text=x_axis.label,
                font=dict(size=typo.font_size_xlabel),
            )

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
            update["gridcolor"] = x_axis.grid_color
            update["gridwidth"] = x_axis.grid_width

        update["showticklabels"] = x_axis.show_tick_labels
        update["automargin"] = x_axis.automargin

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
    def _apply_yaxis(spec: FigureSpec, fig: go.Figure) -> None:
        """Configure the primary Y-axis."""
        assert spec.axes is not None  # guaranteed by __post_init__  # nosec B101
        assert spec.typography is not None  # guaranteed by __post_init__  # nosec B101
        y_axis = spec.axes.y
        typo = spec.typography

        update: Dict[str, Any] = {}

        if y_axis.label:
            update["title"] = dict(
                text=y_axis.label,
                font=dict(size=typo.font_size_ylabel),
            )

        update["tickfont"] = dict(size=typo.font_size_yticks)

        if y_axis.range is not None:
            update["range"] = y_axis.range
        if y_axis.scale != "linear":
            update["type"] = y_axis.scale
        if y_axis.dtick is not None:
            update["dtick"] = y_axis.dtick

        update["showgrid"] = y_axis.show_grid
        if y_axis.show_grid:
            update["gridcolor"] = y_axis.grid_color
            update["gridwidth"] = y_axis.grid_width

        update["automargin"] = y_axis.automargin

        fig.update_yaxes(**update, selector=dict(overlaying=None))

    @staticmethod
    def _apply_y2axis(spec: FigureSpec, fig: go.Figure) -> None:
        """Configure the secondary Y-axis (if present)."""
        assert spec.axes is not None  # guaranteed by __post_init__  # nosec B101
        assert spec.typography is not None  # guaranteed by __post_init__  # nosec B101
        if spec.axes.y2 is None:
            return

        y2 = spec.axes.y2
        typo = spec.typography

        update: Dict[str, Any] = {
            "overlaying": "y",
            "side": "right",
        }

        if y2.label:
            update["title"] = dict(
                text=y2.label,
                font=dict(size=typo.font_size_y2label),
            )

        update["tickfont"] = dict(size=typo.font_size_y2ticks)

        if y2.range is not None:
            update["range"] = y2.range
        if y2.dtick is not None:
            update["dtick"] = y2.dtick

        update["showgrid"] = y2.show_grid

        fig.update_layout(yaxis2=update)

    @staticmethod
    def _apply_legends(spec: FigureSpec, fig: go.Figure) -> None:
        """Apply legend configuration for all legends."""
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
            fig.update_layout(**{legend_key: legend_dict})

    @staticmethod
    def _build_legend_dict(legend: LegendSpec) -> Dict[str, Any]:
        """Build a Plotly legend configuration dictionary."""
        result: Dict[str, Any] = {
            "font": dict(
                size=legend.font_size,
                color=legend.font_color,
            ),
            "orientation": "h" if legend.orientation == "horizontal" else "v",
            "itemsizing": legend.itemsizing,
        }

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

        if legend.order == "reversed":
            result["traceorder"] = "reversed"

        return result

    # ────────────────────────────────────────────────────────────
    # Step 10 — New feature methods
    # ────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_color_palette(spec: FigureSpec, fig: go.Figure) -> None:
        """Set colorway and explicitly assign palette colors to traces.

        In addition to setting the layout ``colorway`` (for any future
        traces), this assigns palette colours to existing traces that
        don't already have an explicit ``marker.color`` set (e.g. by the
        plot factory or upstream styling).
        """
        if not spec.color_palette:
            return

        fig.update_layout(colorway=spec.color_palette)

        for i, trace in enumerate(fig.data):
            # Skip traces that already have an explicit marker color
            existing_color = (
                getattr(trace.marker, "color", None) if hasattr(trace, "marker") else None
            )
            if existing_color is not None:
                continue

            col = spec.color_palette[i % len(spec.color_palette)]
            trace.update(marker=dict(color=col))
            if hasattr(trace, "line") and getattr(trace, "type", "") in (
                "scatter",
                "scattergl",
            ):
                trace.update(line=dict(color=col))

    @staticmethod
    def _apply_hovermode(spec: FigureSpec, fig: go.Figure) -> None:
        """Set hovermode from spec."""
        fig.update_layout(hovermode=spec.hovermode)

    @staticmethod
    def _apply_font_family(spec: FigureSpec, fig: go.Figure) -> None:
        """Set global font family."""
        if spec.font_family:
            fig.update_layout(font=dict(family=spec.font_family))

    @staticmethod
    def _apply_reference_lines(spec: FigureSpec, fig: go.Figure) -> None:
        """Add horizontal/vertical reference lines via fig.add_shape()."""
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
    def _apply_data_labels(spec: FigureSpec, fig: go.Figure) -> None:
        """Apply data label annotations on bars/points."""
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

        # Build texttemplate: if format_string already contains "%{",
        # use it verbatim (full Plotly template); otherwise wrap it.
        fmt = dl.format_string
        if "%{" in fmt:
            texttemplate = fmt
        else:
            texttemplate = f"%{{y:{fmt}}}"

        for trace in fig.data:
            update: Dict[str, Any] = {
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
            if (text_position == "inside" or dl.size_constraint == "inside") and dl.anchor in (
                "top",
                "middle",
                "bottom",
            ):
                update["insidetextanchor"] = dl.anchor

            trace.update(**update)

        # Uniform text (layout-level) when constraint is active
        if dl.size_constraint == "inside":
            min_size = max(6, font_size - 4)
            fig.update_layout(
                uniformtext=dict(mode="hide", minsize=min_size),
            )

    @staticmethod
    def _apply_series_styling(spec: FigureSpec, fig: go.Figure) -> None:
        """Apply per-trace line_width, marker, opacity from series_styles."""
        if not spec.series_styles:
            return

        for i, trace in enumerate(fig.data):
            # Use modular index to cycle through styles
            style = spec.series_styles[i % len(spec.series_styles)]

            update: Dict[str, Any] = {}
            if style.opacity > 0:
                update["opacity"] = style.opacity
            if style.line_width > 0:
                if hasattr(trace, "line"):
                    update["line"] = dict(width=style.line_width)
            if style.marker_size > 0:
                # marker.size only applies to scatter-like traces, not Bar
                if not isinstance(trace, go.Bar):
                    update["marker"] = dict(size=style.marker_size)
            if style.bar_border_width > 0:
                marker_update: Dict[str, Any] = update.get("marker", {})
                marker_update["line"] = dict(
                    width=style.bar_border_width,
                    color=style.bar_border_color or "#000",
                )
                update["marker"] = marker_update

            if update:
                trace.update(**update)

    @staticmethod
    def _apply_separator_lines(spec: FigureSpec, fig: go.Figure) -> None:
        """Add group separator vertical lines between bar clusters."""
        if not spec.separator.enabled:
            return

        # Separators require X-axis category data; infer boundaries
        x_data: Optional[List[Any]] = None
        for trace in fig.data:
            if hasattr(trace, "x") and trace.x is not None:
                x_data = list(trace.x)
                break

        if not x_data:
            return

        # Draw vertical lines at half-integer positions between categories
        for i in range(1, len(x_data)):
            fig.add_shape(
                type="line",
                x0=i - 0.5,
                x1=i - 0.5,
                y0=0,
                y1=1,
                yref="paper",
                line=dict(
                    dash=spec.separator.style,
                    color=spec.separator.color,
                    width=1.0,
                ),
            )

    @staticmethod
    def _apply_stripes(spec: FigureSpec, fig: go.Figure) -> None:
        """Alternating row background shapes."""
        if not spec.enable_stripes:
            return

        # Apply hatching pattern to bar-like traces only (scatter doesn't
        # support marker.pattern).
        if spec.hatching_sequence:
            for i, trace in enumerate(fig.data):
                if not isinstance(trace, (go.Bar, go.Histogram)):
                    continue
                pattern = spec.hatching_sequence[i % len(spec.hatching_sequence)]
                trace.update(
                    marker=dict(
                        pattern=dict(shape=pattern, fillmode="replace"),
                    )
                )

    @staticmethod
    def _apply_axis_colors(spec: FigureSpec, fig: go.Figure) -> None:
        """Apply tick/label/line colors per axis from new AxisSpec fields."""
        assert spec.axes is not None  # guaranteed by __post_init__  # nosec B101

        x = spec.axes.x
        y = spec.axes.y

        x_update: Dict[str, Any] = {}
        if x.tick_font_color:
            x_update["tickfont"] = dict(color=x.tick_font_color)
        if x.axis_line_color:
            x_update["linecolor"] = x.axis_line_color
            x_update["showline"] = True
        if x.axis_line_width != 1.0:
            x_update["linewidth"] = x.axis_line_width
        if x_update:
            fig.update_xaxes(**x_update)

        y_update: Dict[str, Any] = {}
        if y.tick_font_color:
            y_update["tickfont"] = dict(color=y.tick_font_color)
        if y.axis_line_color:
            y_update["linecolor"] = y.axis_line_color
            y_update["showline"] = True
        if y.axis_line_width != 1.0:
            y_update["linewidth"] = y.axis_line_width
        if y_update:
            fig.update_yaxes(**y_update)

    # ────────────────────────────────────────────────────────────
    # Step 13 — Per-trace overrides + axis label aliases
    # ────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_trace_overrides(spec: FigureSpec, fig: go.Figure) -> None:
        """Apply per-trace styling overrides keyed by trace name.

        ``spec.trace_overrides`` maps original trace names to typed
        ``SeriesStyleSpec`` instances.  Each matching trace gets colour,
        symbol, size, width, pattern, and/or rename applied.
        """
        if not spec.trace_overrides:
            return

        for trace in fig.data:
            t_name = str(getattr(trace, "name", ""))
            if t_name not in spec.trace_overrides:
                continue
            style = spec.trace_overrides[t_name]

            if style.display_name:
                trace.name = style.display_name

            if style.color:
                trace.update(marker=dict(color=style.color))
                if hasattr(trace, "line") and getattr(trace, "type", "") in (
                    "scatter",
                    "scattergl",
                ):
                    trace.update(line=dict(color=style.color))

            if style.symbol:
                trace.update(marker=dict(symbol=style.symbol))

            if style.marker_size > 0:
                trace.update(marker=dict(size=style.marker_size))

            if style.line_width > 0:
                trace.update(line=dict(width=style.line_width))

            if style.hatching_pattern:
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
        axis: AxisSpec,
        fig: go.Figure,
        update: Dict[str, Any],
    ) -> None:
        """Translate axis label aliases to Plotly tickvals/ticktext.

        The alias mapping (e.g. ``{"a": "Alpha", "b": "Beta"}``) is stored
        in ``AxisSpec.label_aliases`` and resolved here into ``tickmode``,
        ``tickvals``, and ``ticktext``.

        When ``category_order`` is also set, the order is used for
        ``tickvals``; otherwise, values are sorted alphabetically.
        """

        if not axis.label_aliases:
            return

        mapping: Dict[str, str] = axis.label_aliases

        # Determine order: explicit category_order if set, else sorted unique
        if axis.category_order is not None:
            ordered = list(axis.category_order)
        else:
            # Collect unique x-values from traces
            unique_vals: List[str] = []
            seen: set[str] = set()
            for trace in fig.data:
                if hasattr(trace, "x") and trace.x is not None:
                    for x_val in trace.x:
                        key = str(x_val)
                        if key not in seen:
                            unique_vals.append(key)
                            seen.add(key)
            ordered = sorted(unique_vals)

        # Build tickvals/ticktext: map through aliases, preserving originals
        tickvals: List[str] = ordered
        ticktext: List[str] = [mapping.get(v, v) for v in ordered]

        update["tickmode"] = "array"
        update["tickvals"] = tickvals
        update["ticktext"] = ticktext
