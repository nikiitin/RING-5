"""
Matplotlib trace renderer — draws ``TraceConfig`` instances on matplotlib axes.

This module is the **engine-agnostic** trace renderer for the matplotlib
connector.  It reads from ``TraceConfig`` sub-classes (``BarTraceConfig``,
``BoxTraceConfig``, ``LineTraceConfig``, ``ScatterTraceConfig``,
``HeatmapTraceConfig``, ``ViolinTraceConfig``) and draws the equivalent matplotlib artists.

**No Plotly dependency** — this module does not import or reference
``plotly.graph_objects`` or any Plotly types.

Design notes:
    * **Stateless** — all methods are ``@staticmethod``.
    * **No styling** — only draws data; layout/style is handled by
      ``FigureSpecToMatplotlib.apply()``.
    * **Shared coordinates** — categorical bars use one ordered category map;
      precomputed numeric positions and widths are preserved.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, cast

import numpy as np
from matplotlib.axes import Axes
from matplotlib.artist import Artist
from matplotlib.container import Container
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path

from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    BoxTraceConfig,
    HeatmapTraceConfig,
    LineTraceConfig,
    ParallelCoordinatesTraceConfig,
    RadarTraceConfig,
    SankeyTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
    ViolinTraceConfig,
    WaterfallTraceConfig,
)
from src.web.rendering._color_utils import css_color_to_matplotlib
from src.web.rendering._appearance import seed_matplotlib_appearance, validate_parallel_appearance
from src.web.rendering._matplotlib_lock import serialized_matplotlib
from src.web.rendering._heatmap_utils import (
    contrasting_text_color,
    heatmap_colormap,
    compute_z_extent,
)
from src.web.rendering._render_result import MatplotlibRenderResult, MatplotlibTraceBinding
from src.web.rendering._connector_protocol import validate_trace_types


@dataclass(frozen=True)
class _DrawnSource:
    """Actual native emissions, before the renderer associates their neutral source."""

    owned: tuple[Artist | Container, ...] = ()
    styled: tuple[Artist | Container, ...] = ()
    legend: Artist | Container | None = None
    series_channels: tuple[tuple[Artist, str], ...] = ()
    factors: tuple[tuple[Artist, float], ...] = ()


def _spline_coordinates(
    ax: Axes,
    x_values: list[Any],
    y_values: list[float],
) -> tuple[list[float], list[float], list[int], list[float]] | None:
    """Return a smooth curve containing every original marker coordinate."""
    if len(x_values) < 3 or not all(np.isfinite(y_values)):
        return None
    try:
        ax.xaxis.update_units(x_values)
        source_x = np.asarray(ax.convert_xunits(x_values), dtype=float)
    except (TypeError, ValueError):
        return None
    if source_x.ndim != 1 or not np.all(np.isfinite(source_x)) or np.any(np.diff(source_x) <= 0):
        return None

    from scipy.interpolate import make_interp_spline

    dense_x = np.linspace(source_x[0], source_x[-1], max(80, len(source_x) * 24))
    dense_x = np.unique(np.concatenate((dense_x, source_x)))
    spline = make_interp_spline(source_x, np.asarray(y_values), k=min(3, len(source_x) - 1))
    dense_y = spline(dense_x)
    marker_indices = [int(np.searchsorted(dense_x, value)) for value in source_x]
    return dense_x.tolist(), dense_y.tolist(), marker_indices, source_x.tolist()


class MatplotlibTraceRenderer:
    """Draw ``TraceConfig`` instances on a matplotlib ``Axes``.

    This replaces the previous implementation that read from Plotly
    ``go.Figure`` objects.  All trace data now comes from engine-agnostic
    ``TraceConfig`` dataclasses.
    """

    # public API
    @staticmethod
    @serialized_matplotlib
    def render(
        traces: Sequence[TraceConfig],
        ax: Axes,
        barmode: str = "group",
        palette_colors: Sequence[str] | None = None,
        bargap: float = 0.2,
        bargroupgap: float = 0.0,
        bar_border_width: float = 0.0,
        heatmap_vmin: float | None = None,
        heatmap_vmax: float | None = None,
        category_order: Sequence[str] | None = None,
    ) -> MatplotlibRenderResult:
        # [impl->req~ring5.render.matplotlib~1]
        # [impl->req~ring5.extension.render-connector~1]
        """Render all traces onto *ax*.

        Args:
            traces: Ordered list of ``TraceConfig`` instances to draw.
            ax: The matplotlib axes to draw on.
            barmode: Bar arrangement mode (``"group"`` or ``"stack"``).
            palette_colors: Resolved palette hex colours.  When supplied,
                each trace is coloured ``palette_colors[idx]`` instead of
                using the colour embedded in the ``TraceConfig``.  This
                ensures the user-selected palette is respected.
            bargap: Gap between bar groups (0.0–1.0).
            bargroupgap: Gap between bars within a group (0.0–1.0).
            bar_border_width: Border width around each bar (stacked).
            heatmap_vmin: Optional lower bound for heatmap color normalization.
            heatmap_vmax: Optional upper bound for heatmap color normalization.
            category_order: Explicit raw category order; unlisted categories
                retain their encounter order.

        Secondary-Y traces (``yaxis='y2'``) are rendered on a twin axis
        created via ``ax.twinx()``, stored as ``ax._ring5_twin``.

        Returns:
            A ``MatplotlibRenderResult`` with source bindings and heatmap metadata.

        Raises:
            TypeError: A trace has no supported concrete family.
            ValueError: A supported trace contains data that cannot be rendered.
        """
        validate_trace_types(traces)

        # Collect bar traces for stacking computation
        bar_specs: list[BarTraceConfig] = [
            t for t in traces if isinstance(t, BarTraceConfig) and t.visible
        ]

        # Secondary Y handling
        has_secondary = any(t.yaxis == "y2" for t in traces)
        ax2: Axes | None = None
        if has_secondary:
            ax2 = ax.twinx()
            cast(Any, ax)._ring5_twin = ax2

        result = MatplotlibRenderResult(ax, ax2)
        categorical_labels = list(
            dict.fromkeys(
                str(value) for trace in bar_specs if not trace.x_positions for value in trace.x
            )
        )
        if category_order:
            known_categories = set(categorical_labels)
            ordered = list(
                dict.fromkeys(
                    str(value) for value in category_order if str(value) in known_categories
                )
            )
            ordered_set = set(ordered)
            categorical_labels = ordered + [
                label for label in categorical_labels if label not in ordered_set
            ]
        category_positions = {label: float(index) for index, label in enumerate(categorical_labels)}
        result.x_category_positions = {
            value: category_positions[value]
            for trace in bar_specs
            if not trace.x_positions
            for value in trace.x
            if isinstance(value, str)
        }
        vertical_box_ticks: dict[int, str] = {}
        horizontal_box_ticks: dict[int, str] = {}

        spline_categories = sorted(
            {
                value
                for trace in traces
                if isinstance(trace, LineTraceConfig) and trace.line_shape == "spline"
                for value in trace.x
                if isinstance(value, str)
            }
        )
        if spline_categories:
            ax.xaxis.update_units(spline_categories)

        bindings: list[MatplotlibTraceBinding] = []
        for idx, trace in enumerate(traces):
            is_secondary = trace.yaxis == "y2"
            target = ax2 if (is_secondary and ax2 is not None) else ax
            drawn = _DrawnSource()

            # Palette colors fill only otherwise unspecified source channels.
            override_color: str | None = None
            if (
                palette_colors
                and not trace.color
                and trace.trace_type
                not in ("waterfall", "sankey", "parallel_coordinates", "heatmap")
            ):
                override_color = palette_colors[idx % len(palette_colors)]

            try:
                if not trace.visible:
                    pass
                elif isinstance(trace, BarTraceConfig):
                    axis_bars = [bar for bar in bar_specs if bar.yaxis == trace.yaxis]
                    bar_idx = next(i for i, bar in enumerate(axis_bars) if bar is trace)
                    drawn = MatplotlibTraceRenderer._draw_bar(
                        trace,
                        target,
                        bar_idx,
                        axis_bars,
                        barmode,
                        categorical_labels,
                        override_color=override_color,
                        bargap=bargap,
                        bargroupgap=bargroupgap,
                        bar_border_width=bar_border_width,
                    )
                elif isinstance(trace, BoxTraceConfig):
                    drawn = MatplotlibTraceRenderer._draw_box(
                        trace,
                        target,
                        vertical_box_ticks,
                        horizontal_box_ticks,
                        override_color=override_color,
                    )
                elif isinstance(trace, ViolinTraceConfig):
                    drawn = MatplotlibTraceRenderer._draw_violin(
                        trace,
                        target,
                        vertical_box_ticks,
                        horizontal_box_ticks,
                        override_color=override_color,
                    )
                elif isinstance(trace, LineTraceConfig):
                    drawn = MatplotlibTraceRenderer._draw_line(
                        trace,
                        target,
                        override_color=override_color,
                    )
                elif isinstance(trace, RadarTraceConfig):
                    drawn = MatplotlibTraceRenderer._draw_radar(
                        trace,
                        target,
                        override_color=override_color,
                    )
                elif isinstance(trace, WaterfallTraceConfig):
                    drawn = MatplotlibTraceRenderer._draw_waterfall(
                        trace,
                        target,
                        override_color=override_color,
                    )
                elif isinstance(trace, SankeyTraceConfig):
                    drawn = MatplotlibTraceRenderer._draw_sankey(trace, target)
                elif isinstance(trace, ParallelCoordinatesTraceConfig):
                    drawn = MatplotlibTraceRenderer._draw_parallel_coordinates(trace, target)
                elif isinstance(trace, ScatterTraceConfig):
                    drawn = MatplotlibTraceRenderer._draw_scatter(
                        trace,
                        target,
                        override_color=override_color,
                    )
                elif isinstance(trace, HeatmapTraceConfig):
                    drawn = MatplotlibTraceRenderer._draw_heatmap(
                        trace,
                        target,
                        result,
                        vmin=heatmap_vmin,
                        vmax=heatmap_vmax,
                    )
                else:
                    raise TypeError(f"Unsupported trace type: {type(trace).__name__}.")
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"Cannot render trace {trace.name!r}: {exc}") from exc
            bindings.append(
                MatplotlibTraceBinding(
                    idx,
                    trace.name,
                    target,
                    trace.legend_role,
                    trace.legendgroup,
                    trace.show_in_legend,
                    trace.trace_type,
                    drawn.owned,
                    drawn.styled,
                    drawn.legend,
                    appearance=seed_matplotlib_appearance(
                        drawn.owned,
                        opacity=trace.opacity,
                        series_channels=drawn.series_channels,
                        factors=drawn.factors,
                    ),
                )
            )

        if vertical_box_ticks:
            positions = sorted(vertical_box_ticks)
            ax.set_xticks(positions, [vertical_box_ticks[position] for position in positions])
        if horizontal_box_ticks:
            positions = sorted(horizontal_box_ticks)
            ax.set_yticks(positions, [horizontal_box_ticks[position] for position in positions])

        result.bindings = tuple(bindings)
        result.validate()
        return result

    # bar
    @staticmethod
    def _draw_bar(
        spec: BarTraceConfig,
        ax: Axes,
        bar_idx: int,
        bar_specs: list[BarTraceConfig],
        barmode: str,
        categorical_labels: list[str],
        override_color: str | None = None,
        bargap: float = 0.2,
        bargroupgap: float = 0.0,
        bar_border_width: float = 0.0,
    ) -> _DrawnSource:
        """Draw a single bar trace from its ``BarTraceConfig``."""
        # [impl->req~ring5.figure.accessible-themes~1]
        # 2) Compute standard x-positions and effective bar width
        if spec.x_positions:
            # Pre-filled numeric axis (e.g., histogram overlay)
            x_pos = spec.x_positions
            eff_bar_width = spec.bar_width
            is_categorical = False
        else:
            # Categorical string axis
            x_pos, eff_bar_width = _compute_categorical_positions(
                spec, bar_idx, bar_specs, barmode, bargap, bargroupgap, categorical_labels
            )
            is_categorical = not all(isinstance(value, (int, float)) for value in spec.x)

        props: dict[str, Any] = {}
        if eff_bar_width is not None:
            props["width"] = eff_bar_width

        # Bar border: controls visual separation between stacked items
        if bar_border_width > 0 or spec.border_width > 0:
            props["edgecolor"] = css_color_to_matplotlib(spec.border_color or "white")
            props["linewidth"] = bar_border_width or spec.border_width
        else:
            props["edgecolor"] = "none"
            props["linewidth"] = 0

        # 3) Sanitize y-values (None -> np.nan)
        y_clean = [float(v) if v is not None else np.nan for v in spec.y]

        # 4) Compute stacking bottom
        if barmode in {"stack", "relative"} and bar_idx > 0:
            if is_categorical:
                bottom = _stack_bottom(bar_idx, bar_specs, relative=barmode == "relative")
            else:
                bottom = _stack_bottom_numeric(
                    bar_idx, bar_specs, x_pos, relative=barmode == "relative"
                )
            props["bottom"] = bottom

        # 5) Render
        color = override_color or spec.color
        if color:
            props["color"] = css_color_to_matplotlib(color)
        if spec.pattern:
            props["hatch"] = spec.pattern

        if spec.error_y is not None:
            props["yerr"] = spec.error_y
        bars = ax.bar(x_pos, y_clean, label=spec.name, **props)

        if is_categorical:
            ax.set_xticks(range(len(categorical_labels)), categorical_labels)
        owned: tuple[Artist | Container, ...] = (bars,)
        if bars.errorbar is not None:
            owned += (bars.errorbar,)
        return _DrawnSource(owned, (bars,), bars, tuple((patch, "face") for patch in bars.patches))

    # line

    @staticmethod
    def _draw_box(
        spec: BoxTraceConfig,
        ax: Axes,
        vertical_ticks: dict[int, str],
        horizontal_ticks: dict[int, str],
        override_color: str | None = None,
    ) -> _DrawnSource:
        # [impl->req~ring5.plot.box~1]
        """Draw one precomputed distribution with deterministic point jitter."""
        color = css_color_to_matplotlib(spec.color or override_color or "#4472C4")
        stats: dict[str, Any] = {
            "label": spec.name,
            "med": spec.median,
            "q1": spec.q1,
            "q3": spec.q3,
            "whislo": spec.lower_whisker,
            "whishi": spec.upper_whisker,
            "fliers": [],
            "mean": spec.mean,
            "cilo": spec.notch_lower,
            "cihi": spec.notch_upper,
        }
        label = spec.name
        parts = ax.bxp(
            [stats],
            positions=[spec.position],
            widths=[spec.box_width],
            orientation=spec.orientation,
            patch_artist=True,
            shownotches=spec.notched,
            showmeans=spec.show_mean,
            showfliers=False,
            capwidths=[spec.box_width * spec.whisker_cap_width],
            label=label,
            boxprops={"facecolor": color, "edgecolor": color},
            medianprops={"color": "black"},
            whiskerprops={"color": color},
            capprops={"color": color},
            meanprops={"markerfacecolor": "white", "markeredgecolor": color},
        )
        point_artist = None
        points = spec.values if spec.point_mode == "all" else spec.outliers
        if spec.point_mode != "none" and points:
            center = spec.position + spec.point_position * spec.box_width
            spread = (
                np.linspace(-spec.jitter, spec.jitter, len(points)) * spec.box_width
                if len(points) > 1
                else np.array([0.0])
            )
            point_positions = center + spread
            if spec.orientation == "vertical":
                point_artist = ax.scatter(
                    point_positions,
                    points,
                    color=color,
                    s=16,
                )
            else:
                point_artist = ax.scatter(
                    points,
                    point_positions,
                    color=color,
                    s=16,
                )
        if spec.orientation == "vertical":
            vertical_ticks[spec.category_position] = spec.category
        else:
            horizontal_ticks[spec.category_position] = spec.category
        owned = [artist for values in parts.values() for artist in values]
        if point_artist is not None:
            owned.append(point_artist)
        body = parts["boxes"][0]
        channels: list[tuple[Artist, str]] = [(body, "face"), (body, "edge")]
        channels += [
            (artist, kind)
            for key in ("whiskers", "caps")
            for artist in parts[key]
            for kind in ("line", "marker_face", "marker_edge")
        ]
        channels += [(artist, "marker_edge") for artist in parts.get("means", ())]
        if point_artist is not None:
            channels.append((point_artist, "face"))
        return _DrawnSource(tuple(owned), (body,), body, tuple(channels))

    # line
    @staticmethod
    def _draw_line(
        spec: LineTraceConfig,
        ax: Axes,
        override_color: str | None = None,
    ) -> _DrawnSource:
        # [impl->req~ring5.plot.ecdf~1]
        # [impl->req~ring5.plot.area~1]
        # [impl->req~ring5.figure.line-styles~1]
        """Draw a single line trace from its ``LineTraceConfig``."""
        props: dict[str, Any] = {}
        color = override_color or spec.color
        if color:
            props["color"] = css_color_to_matplotlib(color)
        if spec.line_width:
            props["linewidth"] = spec.line_width
        if spec.line_dash:
            props["linestyle"] = _DASH_MAP.get(spec.line_dash, "-")
        drawstyle = {
            "hv": "steps-post",
            "vh": "steps-pre",
            "hvh": "steps-mid",
        }.get(spec.line_shape)
        if drawstyle:
            props["drawstyle"] = drawstyle
        # Markers: honour show_markers/marker_symbol/marker_size so the matplotlib
        # engine matches Plotly's "lines+markers" mode (dot-lines, dual-axis dots).
        if spec.show_markers:
            props["marker"] = _MARKER_MAP.get(spec.marker_symbol, "o")
            if spec.marker_size:
                props["markersize"] = float(spec.marker_size)

        y_clean: list[float] = []
        for value in spec.y:
            try:
                y_clean.append(float(value))
            except (TypeError, ValueError):
                y_clean.append(float("nan"))
        source_indices = list(range(len(y_clean)))
        x_values: list[Any] = list(spec.x)
        if spec.connect_gaps:
            source_indices = [index for index, value in enumerate(y_clean) if np.isfinite(value)]
            x_values = [x_values[index] for index in source_indices]
            y_clean = [y_clean[index] for index in source_indices]

        rendered_x: list[Any] = x_values
        rendered_y = y_clean
        source_x: list[float] | None = None
        if spec.line_shape == "spline":
            smoothed = _spline_coordinates(ax, x_values, y_clean)
            if smoothed is not None:
                rendered_x, rendered_y, marker_indices, source_x = smoothed
                if spec.show_markers:
                    props["markevery"] = marker_indices

        if spec.line_shape == "vhv" and x_values:
            ax.xaxis.update_units(x_values)
            source_x = np.asarray(ax.convert_xunits(x_values), dtype=float).tolist()
            rendered_x, rendered_y = [source_x[0]], [y_clean[0]]
            for index in range(1, len(source_x)):
                middle_y = (y_clean[index - 1] + y_clean[index]) / 2
                rendered_x.extend([source_x[index - 1], source_x[index], source_x[index]])
                rendered_y.extend([middle_y, middle_y, y_clean[index]])
            if spec.show_markers:
                props["markevery"] = [index * 3 for index in range(len(source_x))]

        artists = ax.plot(rendered_x, rendered_y, label=spec.name, **props)
        owned: list[Artist | Container] = list(artists)
        if spec.error_y is not None:
            errors = [spec.error_y[index] for index in source_indices]
            owned.append(
                ax.errorbar(
                    x_values, y_clean, yerr=errors, fmt="none", color=artists[0].get_color()
                )
            )
        if spec.fill != "none":
            raw_baseline = spec.fill_base or [0.0] * len(spec.y)
            baseline = [float(raw_baseline[index]) for index in source_indices]
            if source_x is not None:
                baseline = np.interp(rendered_x, source_x, baseline).tolist()
            step: Literal["pre", "post", "mid"] | None = None
            if spec.line_shape == "hv":
                step = "post"
            elif spec.line_shape == "vh":
                step = "pre"
            elif spec.line_shape in ("hvh", "vhv"):
                step = "mid"
            fill_artist = ax.fill_between(
                rendered_x,
                rendered_y,
                baseline,
                color=css_color_to_matplotlib(color or "#4472C4"),
                step=step,
                label="_nolegend_",
            )
            owned.append(fill_artist)
        channels: list[tuple[Artist, str]] = [
            (artists[0], kind) for kind in ("line", "marker_face", "marker_edge")
        ]
        if spec.fill != "none":
            channels += [(fill_artist, "face"), (fill_artist, "edge")]
        if spec.error_y is not None:
            channels += [
                (child, "edge")
                for child in owned[1].get_children()
                if hasattr(child, "get_edgecolor")
            ]
        return _DrawnSource(tuple(owned), (artists[0],), artists[0], tuple(channels))

    @staticmethod
    def _draw_violin(
        spec: ViolinTraceConfig,
        ax: Axes,
        vertical_ticks: dict[int, str],
        horizontal_ticks: dict[int, str],
        override_color: str | None = None,
    ) -> _DrawnSource:
        # [impl->req~ring5.plot.violin~1]
        """Draw one precomputed density, optional inner summary, and observations."""
        if not spec.density_coordinates or not spec.density:
            return _DrawnSource()
        color = css_color_to_matplotlib(spec.color or override_color or "#4472C4")
        coordinates = np.asarray(spec.density_coordinates, dtype=float)
        half_width = spec.violin_width * spec.width_scale / 2
        density_width = np.asarray(spec.density, dtype=float) * half_width
        if spec.side == "positive":
            lower = np.full_like(density_width, spec.position)
            upper = spec.position + density_width
        elif spec.side == "negative":
            lower = spec.position - density_width
            upper = np.full_like(density_width, spec.position)
        else:
            lower = spec.position - density_width
            upper = spec.position + density_width
        label = spec.name
        if spec.orientation == "vertical":
            density_artist = ax.fill_betweenx(
                coordinates,
                lower,
                upper,
                facecolor=color,
                edgecolor=color,
                label=label,
            )
        else:
            density_artist = ax.fill_between(
                coordinates,
                lower,
                upper,
                facecolor=color,
                edgecolor=color,
                label=label,
            )

        inner: dict[str, list[Artist]] = {}
        mean_artists: Sequence[Artist] = ()
        point_artist = None
        if spec.show_box:
            stats: dict[str, Any] = {
                "label": "_nolegend_",
                "med": spec.median,
                "q1": spec.q1,
                "q3": spec.q3,
                "whislo": min(spec.values),
                "whishi": max(spec.values),
                "fliers": [],
            }
            inner = ax.bxp(
                [stats],
                positions=[spec.position],
                widths=[max(half_width * 0.2, 0.01)],
                orientation=spec.orientation,
                patch_artist=True,
                showfliers=False,
                boxprops={"facecolor": "white", "edgecolor": color},
                medianprops={"color": "black"},
                whiskerprops={"color": color},
                capprops={"color": color},
            )
        if spec.show_mean:
            extent = max(half_width * 0.3, 0.01)
            if spec.orientation == "vertical":
                mean_artists = ax.plot(
                    [spec.position - extent, spec.position + extent],
                    [spec.mean, spec.mean],
                    color="black",
                    linewidth=1.5,
                )
            else:
                mean_artists = ax.plot(
                    [spec.mean, spec.mean],
                    [spec.position - extent, spec.position + extent],
                    color="black",
                    linewidth=1.5,
                )
        if spec.point_mode == "all" and spec.values:
            spread = (
                np.linspace(-spec.jitter, spec.jitter, len(spec.values)) * spec.violin_width
                if len(spec.values) > 1
                else np.array([0.0])
            )
            point_positions = spec.position + spread
            if spec.orientation == "vertical":
                point_artist = ax.scatter(
                    point_positions,
                    spec.values,
                    color=color,
                    s=12,
                )
            else:
                point_artist = ax.scatter(
                    spec.values,
                    point_positions,
                    color=color,
                    s=12,
                )
        if spec.orientation == "vertical":
            vertical_ticks[spec.category_position] = spec.category
        else:
            horizontal_ticks[spec.category_position] = spec.category
        owned = [
            density_artist,
            *mean_artists,
            *(artist for values in inner.values() for artist in values),
        ]
        if point_artist is not None:
            owned.append(point_artist)
        channels: list[tuple[Artist, str]] = [(density_artist, "face"), (density_artist, "edge")]
        channels += [
            (artist, kind)
            for key in ("whiskers", "caps")
            for artist in inner.get(key, ())
            for kind in ("line", "marker_face", "marker_edge")
        ]
        channels += [(artist, "edge") for artist in inner.get("boxes", ())]
        if point_artist is not None:
            channels.append((point_artist, "face"))
        factors = tuple((artist, 0.8) for artist in inner.get("boxes", ()))
        return _DrawnSource(
            tuple(owned), (density_artist,), density_artist, tuple(channels), factors
        )

    @staticmethod
    def _draw_radar(
        spec: RadarTraceConfig,
        ax: Axes,
        override_color: str | None = None,
    ) -> _DrawnSource:
        # [impl->req~ring5.plot.radar~1]
        """Draw a closed radar polygon on Cartesian axes with one shared radial scale."""
        if not spec.categories or not spec.values:
            return _DrawnSource()
        count = len(spec.categories)
        direction = -1.0 if spec.clockwise else 1.0
        start = np.deg2rad(spec.start_angle)
        angles = start + direction * np.arange(count) * (2 * np.pi / count)
        span = spec.radial_max - spec.radial_min
        radii = (np.asarray(spec.values, dtype=float) - spec.radial_min) / span
        closed_angles = np.append(angles, angles[0])
        closed_radii = np.append(radii, radii[0])
        x_values = closed_radii * np.cos(closed_angles)
        y_values = closed_radii * np.sin(closed_angles)
        color = css_color_to_matplotlib(override_color or spec.color or "#4472C4")

        if not getattr(ax, "_ring5_radar_frame", False):
            for angle, category in zip(angles, spec.categories):
                ax.plot(
                    [0.0, np.cos(angle)],
                    [0.0, np.sin(angle)],
                    color="#cccccc",
                    linewidth=0.8,
                )
                ax.text(
                    1.12 * np.cos(angle),
                    1.12 * np.sin(angle),
                    category,
                    ha="center",
                    va="center",
                )
            for fraction in (0.25, 0.5, 0.75, 1.0):
                circle_angles = np.linspace(0, 2 * np.pi, 181)
                ax.plot(
                    fraction * np.cos(circle_angles),
                    fraction * np.sin(circle_angles),
                    color="#dddddd",
                    linewidth=0.7,
                )
            cast(Any, ax)._ring5_radar_frame = True
            ax.set_aspect("equal")
            ax.set_xlim(-1.25, 1.25)
            ax.set_ylim(-1.25, 1.25)
            ax.axis("off")

        fill_artists: Sequence[Artist] = ()
        data_lines = ax.plot(
            x_values,
            y_values,
            color=color,
            linewidth=spec.line_width,
            marker="o" if spec.show_markers else None,
            markersize=spec.marker_size,
            label=spec.name,
        )
        if spec.fill_area:
            fill_artists = ax.fill(x_values, y_values, color=color)
        channels: list[tuple[Artist, str]] = [
            (artist, kind)
            for artist in data_lines
            for kind in ("line", "marker_face", "marker_edge")
        ]
        channels += [(artist, kind) for artist in fill_artists for kind in ("face", "edge")]
        return _DrawnSource(
            tuple([*data_lines, *fill_artists]),
            tuple(data_lines),
            data_lines[0],
            tuple(channels),
            tuple((artist, 0.45) for artist in fill_artists),
        )

    @staticmethod
    def _draw_waterfall(
        spec: WaterfallTraceConfig,
        ax: Axes,
        override_color: str | None = None,
    ) -> _DrawnSource:
        # [impl->req~ring5.plot.waterfall~1]
        """Draw explicit waterfall starts, ends, connectors, and value labels."""
        owned: list[Artist | Container] = []
        containers: list[Container] = []
        positions = np.arange(len(spec.categories), dtype=float)
        for index, (start, end, kind) in enumerate(zip(spec.starts, spec.ends, spec.kinds)):
            if kind in ("subtotal", "total", "absolute"):
                color = spec.total_color
            elif end >= start:
                color = spec.increasing_color
            else:
                color = spec.decreasing_color
            bottom = min(start, end)
            height = abs(end - start)
            bars = ax.bar(
                positions[index],
                height,
                bottom=bottom,
                width=spec.bar_width,
                color=css_color_to_matplotlib(color),
                label=spec.name if index == 0 else "_nolegend_",
            )
            owned.append(bars)
            containers.append(bars)
            if spec.show_values and index < len(spec.value_labels):
                owned.append(
                    ax.text(
                        positions[index],
                        max(start, end),
                        spec.value_labels[index],
                        ha="center",
                        va="bottom",
                    )
                )
            if spec.connector_visible and index < len(spec.categories) - 1:
                connectors = ax.plot(
                    [
                        positions[index] + spec.bar_width / 2,
                        positions[index + 1] - spec.bar_width / 2,
                    ],
                    [end, end],
                    color=css_color_to_matplotlib(spec.connector_color),
                    linewidth=spec.connector_width,
                )
                owned.extend(connectors)
        ax.set_xticks(positions, spec.categories)
        return _DrawnSource(tuple(owned), tuple(containers), containers[0] if containers else None)

    @staticmethod
    def _draw_sankey(spec: SankeyTraceConfig, ax: Axes) -> _DrawnSource:
        # [impl->req~ring5.plot.sankey~1]
        """Draw weighted Bézier links and positioned nodes from one shared layout."""
        if not spec.node_labels:
            return _DrawnSource()
        owned: list[Artist | Container] = []
        factors: list[tuple[Artist, float]] = []
        maximum = max(spec.values, default=1.0)
        node_width = max(0.02, min(0.09, spec.node_thickness / 300.0))
        layer_counts: dict[float, int] = {}
        for x_position in spec.node_x:
            layer_counts[x_position] = layer_counts.get(x_position, 0) + 1
        node_heights = [
            min(0.16, max(0.04, 0.7 / layer_counts.get(x_position, 1)))
            for x_position in spec.node_x
        ]

        for index, (source, target, value) in enumerate(
            zip(spec.source_indices, spec.target_indices, spec.values)
        ):
            source_x = spec.node_x[source] + node_width / 2
            target_x = spec.node_x[target] - node_width / 2
            source_y = spec.node_y[source]
            target_y = spec.node_y[target]
            distance = target_x - source_x
            vertices = [
                (source_x, source_y),
                (source_x + distance * 0.45, source_y),
                (target_x - distance * 0.45, target_y),
                (target_x, target_y),
            ]
            path = Path(vertices, [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
            color = spec.link_colors[index] if index < len(spec.link_colors) else "#7f7f7f"
            owned.append(
                ax.add_patch(
                    PathPatch(
                        path,
                        facecolor="none",
                        edgecolor=css_color_to_matplotlib(color),
                        linewidth=1.0 + 18.0 * value / maximum,
                        capstyle="butt",
                        zorder=1,
                    )
                )
            )
            factors.append((cast(Artist, owned[-1]), spec.link_opacity))
            if spec.show_link_labels and index < len(spec.link_labels) and spec.link_labels[index]:
                owned.append(
                    ax.text(
                        (source_x + target_x) / 2,
                        (source_y + target_y) / 2,
                        spec.link_labels[index],
                        ha="center",
                        va="center",
                        zorder=3,
                    )
                )

        for index, label in enumerate(spec.node_labels):
            x_position, y_position = spec.node_x[index], spec.node_y[index]
            height = node_heights[index]
            color = spec.node_colors[index] if index < len(spec.node_colors) else "#4c78a8"
            owned.append(
                ax.add_patch(
                    Rectangle(
                        (x_position - node_width / 2, y_position - height / 2),
                        node_width,
                        height,
                        facecolor=css_color_to_matplotlib(color),
                        edgecolor=css_color_to_matplotlib(spec.node_line_color),
                        linewidth=spec.node_line_width,
                        zorder=2,
                    )
                )
            )
            if spec.show_node_labels and label:
                on_right = x_position >= 0.85
                owned.append(
                    ax.text(
                        x_position + (-node_width if on_right else node_width),
                        y_position,
                        label,
                        ha="right" if on_right else "left",
                        va="center",
                        zorder=3,
                    )
                )
        ax.set_xlim(-0.12, 1.12)
        ax.set_ylim(-0.05, 1.05)
        ax.axis("off")
        return _DrawnSource(tuple(owned), factors=tuple(factors))

    @staticmethod
    def _draw_parallel_coordinates(spec: ParallelCoordinatesTraceConfig, ax: Axes) -> _DrawnSource:
        # [impl->req~ring5.plot.parallel-coordinates~1]
        """Draw normalized row paths, encoded axes, brushes, and a shared color scale."""
        validate_parallel_appearance(
            spec.opacity,
            spec.line_color if spec.line_color_values is None else spec.line_color_values,
            spec.colorscale,
        )
        if len(spec.dimensions) < 2:
            return _DrawnSource()
        owned: list[Artist | Container] = []
        row_count = len(spec.dimensions[0].values)
        x_positions = np.arange(len(spec.dimensions), dtype=float)
        normalized = np.zeros((row_count, len(spec.dimensions)), dtype=float)
        selected = np.ones(row_count, dtype=bool)
        for index, dimension in enumerate(spec.dimensions):
            lower, upper = dimension.range
            values = np.asarray(dimension.values, dtype=float)
            normalized[:, index] = (values - lower) / (upper - lower)
            if dimension.constraintrange is not None:
                brush_min, brush_max = dimension.constraintrange
                selected &= (values >= brush_min) & (values <= brush_max)

        cmap = heatmap_colormap(spec.colorscale)
        if spec.reverse_colorscale:
            cmap = cmap.reversed()
        normalization = Normalize(vmin=spec.color_min, vmax=spec.color_max)
        color_values = (
            np.asarray(spec.line_color_values, dtype=float)
            if spec.line_color_values is not None
            else None
        )
        factors: list[tuple[Artist, float]] = []
        for is_selected in (False, True):
            alpha = 1.0 if is_selected else spec.unselected_opacity
            for row in np.flatnonzero(selected == is_selected):
                color = (
                    cmap(normalization(color_values[row]))
                    if color_values is not None
                    else spec.line_color
                )
                data_lines = ax.plot(
                    x_positions,
                    normalized[row],
                    color=css_color_to_matplotlib(color),
                    zorder=2,
                )
                owned.extend(data_lines)
                factors.extend((line, alpha) for line in data_lines)

        for index, dimension in enumerate(spec.dimensions):
            ax.plot([index, index], [0, 1], color="#777777", linewidth=1.0, zorder=1)
            ax.text(index, 1.04, dimension.label, ha="center", va="bottom", fontweight="bold")
            lower, upper = dimension.range
            if dimension.tick_values:
                for tick, label in zip(dimension.tick_values, dimension.tick_labels):
                    y_position = (tick - lower) / (upper - lower)
                    ax.text(index - 0.03, y_position, label, ha="right", va="center")
            else:
                ax.text(index - 0.03, 0, f"{lower:.4g}", ha="right", va="center")
                ax.text(index - 0.03, 1, f"{upper:.4g}", ha="right", va="center")

        if color_values is not None and spec.show_colorbar:
            mappable = ScalarMappable(norm=normalization, cmap=cmap)
            colorbar = ax.figure.colorbar(mappable, ax=ax, pad=0.08)
            colorbar.set_label(spec.colorbar_title)
            if spec.color_tick_values:
                colorbar.set_ticks(spec.color_tick_values, labels=spec.color_tick_labels)
        ax.set_xlim(-0.25, len(spec.dimensions) - 0.75)
        ax.set_ylim(-0.08, 1.1)
        ax.axis("off")
        return _DrawnSource(tuple(owned), factors=tuple(factors))

    # scatter
    @staticmethod
    def _draw_scatter(
        spec: ScatterTraceConfig,
        ax: Axes,
        override_color: str | None = None,
    ) -> _DrawnSource:
        """Draw a single scatter trace from its ``ScatterTraceConfig``."""
        props: dict[str, Any] = {}
        color = override_color or spec.color
        if color:
            props["color"] = css_color_to_matplotlib(color)
        sizes = spec.size_values if spec.size_values is not None else spec.marker_size
        props["s"] = np.square(sizes)
        props["marker"] = _MARKER_MAP.get(spec.marker_symbol, "o")
        props["linewidths"] = spec.marker_line_width
        if spec.marker_line_color:
            props["edgecolors"] = css_color_to_matplotlib(spec.marker_line_color)

        y_clean = [float(v) if v is not None else np.nan for v in spec.y]
        points = ax.scatter(spec.x, y_clean, label=spec.name, **props)
        owned: list[Artist | Container] = [points]
        if spec.error_y is not None:
            error_color = color or cast(Any, points).get_facecolors()[0]
            error_artist = ax.errorbar(
                spec.x,
                y_clean,
                yerr=spec.error_y,
                fmt="none",
                color=css_color_to_matplotlib(error_color),
            )
            owned.append(error_artist)
        return _DrawnSource(tuple(owned), (points,), points, ((points, "face"),))

    # heatmap
    @staticmethod
    def _draw_heatmap(
        spec: HeatmapTraceConfig,
        ax: Axes,
        result: MatplotlibRenderResult,
        vmin: float | None = None,
        vmax: float | None = None,
    ) -> _DrawnSource:
        """Draw a heatmap from its ``HeatmapTraceConfig``.

        Uses ``ax.pcolormesh()`` so the output is pure vector graphics,
        enabling PGF/TikZ export without raster-image errors.
        """
        if not spec.z:
            return _DrawnSource()

        # Build z-matrix replacing None with NaN
        z_array = np.array(
            [[float(v) if v is not None else np.nan for v in row] for row in spec.z],
            dtype=float,
        )

        compute_z_extent([spec])
        cmap = heatmap_colormap(spec.colorscale)

        # pcolormesh draws vector quadrilaterals (PGF-safe) instead of a
        # raster bitmap (imshow).  Explicit edge arrays make each cell span
        # one unit so that cell centres sit at (col + 0.5, row + 0.5).
        n_rows, n_cols = z_array.shape
        mesh_kwargs: dict[str, Any] = {
            "cmap": cmap,
            "shading": "flat",
        }
        if vmin is not None:
            mesh_kwargs["vmin"] = vmin
        if vmax is not None:
            mesh_kwargs["vmax"] = vmax
        im = ax.pcolormesh(
            np.arange(n_cols + 1),
            np.arange(n_rows + 1),
            z_array,
            **mesh_kwargs,
        )
        ax.invert_yaxis()  # row 0 at top, matching matrix convention
        ax.set_aspect("auto")
        result.heatmap_image = im

        if spec.col_labels:
            result.heatmap_col_labels = spec.col_labels
        if spec.row_labels:
            result.heatmap_row_labels = spec.row_labels

        owned: list[Artist | Container] = [im]
        # Cell annotations — placed at cell centres (col+0.5, row+0.5)
        if spec.show_values and spec.text:
            font_size = spec.text_font_size or 8
            for i, text_row in enumerate(spec.text):
                for j, cell_text in enumerate(text_row):
                    if cell_text:
                        if spec.text_color_mode == "custom":
                            color = spec.text_color
                        else:
                            color = contrasting_text_color(
                                cast(Sequence[float], im.cmap(im.norm(z_array[i, j])))
                            )
                        owned.append(
                            ax.text(
                                j + 0.5,
                                i + 0.5,
                                cell_text,
                                ha="center",
                                va="center",
                                fontsize=font_size,
                                color=css_color_to_matplotlib(color),
                            )
                        )

        # Totals separator lines
        if spec.totals_position and spec.totals_count > 0:
            if spec.totals_position == "right" and n_cols > 1:
                # Vertical line before the totals column
                x_pos = n_cols - spec.totals_count
                ax.axvline(x=x_pos, color="black", linewidth=2, zorder=5)
            elif spec.totals_position == "top" and n_rows > 1:
                # Horizontal line below the totals row (first row)
                y_pos = spec.totals_count
                ax.axhline(y=y_pos, color="black", linewidth=2, zorder=5)
        return _DrawnSource(tuple(owned))


# module-level helpers
_DASH_MAP: dict[str, str | tuple[int, tuple[float, ...]]] = {
    "dash": "--",
    "dot": ":",
    "dashdot": "-.",
    "longdash": (0, (8, 4)),
    "longdashdot": (0, (8, 3, 1.5, 3)),
    "solid": "-",
}

# Plotly marker-symbol names -> matplotlib marker codes. Keeps the matplotlib
# engine's markers consistent with the Plotly path (which uses "lines+markers").
_MARKER_MAP: dict[str, str] = {
    "circle": "o",
    "square": "s",
    "diamond": "D",
    "cross": "+",
    "x": "x",
    "triangle-up": "^",
    "triangle-down": "v",
    "star": "*",
}


def _compute_categorical_positions(
    spec: BarTraceConfig,
    bar_idx: int,
    bar_specs: list[BarTraceConfig],
    barmode: str,
    bargap: float = 0.2,
    bargroupgap: float = 0.0,
    categories: list[str] | None = None,
) -> tuple[list[float], float]:
    """Map sparse categorical traces to one shared category coordinate system."""
    labels = categories or list(dict.fromkeys(str(x) for bar in bar_specs for x in bar.x))
    positions = {label: float(index) for index, label in enumerate(labels)}
    base = [
        float(value) if isinstance(value, (int, float)) else positions[str(value)]
        for value in spec.x
    ]
    group_width = max(0.05, 1.0 - bargap)
    if barmode != "group" or len(bar_specs) <= 1:
        return base, group_width
    step = group_width / len(bar_specs)
    width = max(0.01, step * (1.0 - bargroupgap))
    offset = (bar_idx - (len(bar_specs) - 1) / 2) * step
    return [value + offset for value in base], width


def _stack_bottom(
    bar_idx: int,
    bar_specs: list[BarTraceConfig],
    *,
    relative: bool = False,
) -> list[float]:
    """Stack matching categories only within the same axis and sign partition."""
    current = bar_specs[bar_idx]
    bottom = [0.0] * len(current.y)
    for previous in bar_specs[:bar_idx]:
        if previous.yaxis != current.yaxis:
            continue
        by_category = dict(zip(map(str, previous.x), previous.y))
        for index, category in enumerate(current.x):
            value = by_category.get(str(category))
            if value is not None and (not relative or (value >= 0) == (current.y[index] >= 0)):
                bottom[index] += float(value)
    return bottom


def _stack_bottom_numeric(
    bar_idx: int,
    bar_specs: list[BarTraceConfig],
    x_positions: list[float],
    *,
    relative: bool = False,
) -> list[float]:
    """Stack pre-positioned bars by coordinate without mixing primary/secondary units."""
    current = bar_specs[bar_idx]
    bottom = [0.0] * len(x_positions)
    for previous in bar_specs[:bar_idx]:
        if previous.yaxis != current.yaxis:
            continue
        positions = previous.x_positions or [float(value) for value in previous.x]
        for index, coordinate in enumerate(x_positions):
            for previous_index, other in enumerate(positions):
                if abs(coordinate - other) < 1e-6 and previous_index < len(previous.y):
                    value = previous.y[previous_index]
                    if value is not None and (
                        not relative or (value >= 0) == (current.y[index] >= 0)
                    ):
                        bottom[index] += float(value)
                    break
    return bottom
