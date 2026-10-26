"""Conservative native swatch equivalence for source-owned shared legends."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, cast
import math

if TYPE_CHECKING:
    from matplotlib.markers import MarkerStyle
    from plotly.basedatatypes import BasePlotlyType, BaseTraceType
    from src.web.rendering._render_result import (
        MatplotlibTraceBinding,
        PlotlyRenderResult,
        PlotlyTraceBinding,
    )


def shared_legend_key(
    source: PlotlyTraceBinding | MatplotlibTraceBinding,
    display: str,
    swatch: tuple[Any, ...] | None,
) -> tuple[Any, ...] | None:
    """Identify a known equivalent entry; unknown swatches remain separate."""
    if swatch is None:
        return None
    return source.original_name, display, source.legend_role, source.legendgroup, swatch


def _scalar_style(values: tuple[Any, ...]) -> tuple[Any, ...] | None:
    # Array-valued colours/sizes are data-dependent. Do not compare or hash their rows.
    if all(
        value is None
        or isinstance(value, (str, bool, int))
        or isinstance(value, float)
        and math.isfinite(value)
        for value in values
    ):
        return values
    return None


class _ConfiguredStyle(Protocol):
    _props: Mapping[str, object] | None


class _LineMarkerOwner(Protocol):
    _marker: MarkerStyle


class _HandlerUpdateOwner(Protocol):
    _update_prop_func: object


def _configured_keys(style: BasePlotlyType) -> set[str]:
    properties = cast(_ConfiguredStyle, style)._props
    return set(properties) if properties is not None else set()


def _plotly_scalars(
    style: BasePlotlyType, fields: tuple[str, ...], children: tuple[str, ...] = ()
) -> tuple[Any, ...] | None:
    # The pinned native property map exposes configured keys without copying
    # arbitrary colour/size arrays. Never serialize or inspect their rows here.
    if _configured_keys(style) - set((*fields, *children)):
        return None
    return _scalar_style(tuple(style[field] for field in fields))


def _plotly_pattern(style: BasePlotlyType) -> tuple[Any, ...] | None:
    return _plotly_scalars(
        style, ("shape", "path", "size", "solidity", "fgcolor", "bgcolor", "fgopacity", "fillmode")
    )


def plotly_swatch(trace: BaseTraceType) -> tuple[Any, ...] | None:
    """Compare supported scalar native glyph state without traversing plotted values."""
    import plotly.graph_objects as go

    if isinstance(trace, (go.Bar, go.Histogram)):
        marker = trace.marker
        if any(
            color is not None and not isinstance(color, str)
            for color in (marker.color, marker.line.color)
        ):
            return None
        marker_fields: tuple[str, ...] = ("color", "opacity") + (
            ("cornerradius",) if isinstance(trace, go.Bar) else ()
        )
        parts: tuple[tuple[Any, ...] | None, ...] = (
            _scalar_style((trace.type, trace.orientation, trace.opacity)),
            _plotly_scalars(marker, marker_fields, ("line", "pattern")),
            _plotly_scalars(marker.line, ("color", "width")),
            _plotly_pattern(marker.pattern),
        )
    elif isinstance(trace, (go.Scatter, go.Scattergl, go.Scatterpolar, go.Box, go.Violin)):
        marker, line = trace.marker, trace.line
        if any(
            color is not None and not isinstance(color, str)
            for color in (marker.color, marker.line.color, line.color)
        ):
            return None
        marker_fields = ("color", "opacity", "size", "symbol", "angle")
        line_fields: tuple[str, ...] = ("color", "width")
        extra: tuple[Any, ...] = ()
        if isinstance(trace, (go.Scatter, go.Scattergl, go.Scatterpolar)):
            # An omitted mode is data-dependent; text glyph fonts are not covered.
            if trace.mode not in ("lines", "markers", "lines+markers"):
                return None
            marker_fields += ("sizemin", "sizemode", "sizeref")
            line_fields += ("dash", "shape")
            if isinstance(trace, (go.Scatter, go.Scatterpolar)):
                marker_fields += ("angleref", "standoff", "maxdisplayed")
                line_fields += ("backoff", "smoothing")
            if isinstance(trace, go.Scatter):
                line_fields += ("simplify",)
                if _configured_keys(cast("BasePlotlyType", trace.fillgradient)) or (
                    trace.stackgroup and trace.fill is None
                ):
                    return None
                pattern = _plotly_pattern(trace.fillpattern)
                if pattern is None:
                    return None
                extra = (pattern,)
            scalar = _scalar_style(
                (trace.type, trace.mode, trace.fill, trace.fillcolor, trace.opacity)
            )
        elif isinstance(trace, go.Box):
            scalar = _scalar_style(
                (
                    trace.type,
                    trace.orientation,
                    trace.fillcolor,
                    trace.opacity,
                    trace.boxmean,
                    trace.notched,
                    trace.whiskerwidth,
                    trace.boxpoints,
                    trace.pointpos,
                    trace.jitter,
                )
            )
        else:
            scalar = _scalar_style(
                (
                    trace.type,
                    trace.orientation,
                    trace.fillcolor,
                    trace.opacity,
                    trace.side,
                    trace.points,
                    trace.jitter,
                )
            )
            violin_parts = (
                _plotly_scalars(trace.box, ("visible", "width", "fillcolor"), ("line",)),
                _plotly_scalars(trace.box.line, ("color", "width")),
                _plotly_scalars(trace.meanline, ("visible", "color", "width")),
            )
            if any(part is None for part in violin_parts):
                return None
            extra = violin_parts
        parts = (
            scalar,
            _plotly_scalars(marker, marker_fields, ("line",)),
            _plotly_scalars(marker.line, ("color", "width")),
            _plotly_scalars(line, line_fields),
            *extra,
        )
    elif isinstance(trace, go.Waterfall):
        parts = (
            _scalar_style((trace.type, trace.orientation, trace.opacity)),
            _plotly_scalars(trace.connector, ("visible", "mode"), ("line",)),
            _plotly_scalars(trace.connector.line, ("color", "width", "dash")),
            *(
                part
                for section in (trace.increasing, trace.decreasing, trace.totals)
                for part in (
                    _plotly_scalars(section, (), ("marker",)),
                    _plotly_scalars(section.marker, ("color",), ("line",)),
                    _plotly_scalars(section.marker.line, ("color", "width")),
                )
            ),
        )
    else:
        return None
    return None if any(part is None for part in parts) else tuple(parts)


def _finite_native_style(values: tuple[Any, ...]) -> tuple[Any, ...] | None:
    """Keep only finite immutable scalar style leaves and bounded native glyph tuples."""
    for value in values:
        if isinstance(value, tuple):
            if _finite_native_style(value) is None:
                return None
        elif _scalar_style((value,)) is None:
            return None
    return values


def _stock_matplotlib_handler(handle: object) -> bool:
    """Recognize the current native glyph handlers without invoking custom updates."""
    from matplotlib.collections import PathCollection
    from matplotlib.container import BarContainer
    from matplotlib.legend import Legend
    from matplotlib.legend_handler import (
        HandlerLine2D,
        HandlerPatch,
        HandlerPathCollection,
        update_from_first_child,
    )
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, PathPatch, Rectangle

    expected_update: object = None
    if type(handle) is BarContainer:
        expected: type = HandlerPatch
        family: type = BarContainer
        expected_update = update_from_first_child
    elif type(handle) in (Patch, PathPatch, Rectangle):
        expected = HandlerPatch
        family = Patch
    elif type(handle) is Line2D:
        expected = HandlerLine2D
        family = Line2D
    elif type(handle) is PathCollection:
        expected = HandlerPathCollection
        family = PathCollection
    else:
        return False
    handlers = Legend.get_default_handler_map()
    handler = Legend.get_legend_handler(handlers, handle)
    # The pinned HandlerBase stores this function privately. Reading its identity
    # avoids certifying arbitrary user glyph updates; no callback is executed.
    return (
        handler is handlers.get(family)
        and type(handler) is expected
        and cast(_HandlerUpdateOwner, handler)._update_prop_func is expected_update
    )


def matplotlib_swatch(source: MatplotlibTraceBinding) -> tuple[Any, ...] | None:
    """Describe a scalar native representative, including a bounded marker glyph."""
    import numpy as np
    from matplotlib.artist import Artist
    from matplotlib.collections import PathCollection
    from matplotlib.colors import to_rgba
    from matplotlib.container import BarContainer
    from matplotlib.lines import Line2D
    from matplotlib.markers import MarkerStyle
    from matplotlib.patches import Patch, PathPatch, Rectangle

    handle = source.legend_handle
    if not _stock_matplotlib_handler(handle):
        return None
    if isinstance(handle, BarContainer):
        if type(handle) is not BarContainer or not handle.patches:
            return None
        handle = handle.patches[0]
    if not isinstance(handle, Artist):
        return None
    effects = handle.get_path_effects()
    if (
        (effects is not None and (type(effects) not in (list, tuple) or len(effects) != 0))
        or handle.get_agg_filter() is not None
        or handle.get_sketch_params() is not None
    ):
        return None
    if isinstance(handle, Patch):
        if type(handle) not in (Patch, PathPatch, Rectangle):
            return None
        # Public linestyle text does not identify stored custom dash geometry.
        if handle.get_linestyle() not in ("-", "solid", "None", "none", "", " "):
            return None
        return _finite_native_style(
            (
                source.family,
                tuple(handle.get_facecolor()),
                tuple(handle.get_edgecolor()),
                handle.get_alpha(),
                handle.get_hatch(),
                tuple(handle.get_hatchcolor()),
                handle.get_linewidth(),
                handle.get_linestyle(),
                handle.get_fill(),
            )
        )
    if isinstance(handle, Line2D):
        # get_marker() omits a MarkerStyle's explicit transform. The pinned
        # native owner is read only to recognize unsupported glyph state.
        marker_style = cast(_LineMarkerOwner, handle)._marker
        if (
            type(handle) is not Line2D
            or type(marker_style) is not MarkerStyle
            or marker_style.get_user_transform() is not None
            or handle.is_dashed()
        ):
            return None
        try:
            colors = (
                to_rgba(handle.get_color()),
                to_rgba(handle.get_markerfacecolor()),
                to_rgba(handle.get_markeredgecolor()),
                to_rgba(handle.get_markerfacecoloralt()),
            )
        except (TypeError, ValueError):
            return None
        marker = handle.get_marker()
        if not isinstance(marker, (str, int)):
            return None
        return _finite_native_style(
            (
                source.family,
                colors,
                handle.get_alpha(),
                handle.get_linestyle(),
                handle.get_linewidth(),
                marker,
                handle.get_markersize(),
                handle.get_markeredgewidth(),
                handle.get_fillstyle(),
                handle.get_drawstyle(),
                handle.get_solid_capstyle(),
                handle.get_solid_joinstyle(),
            )
        )
    if isinstance(handle, PathCollection):
        if type(handle) is not PathCollection or handle.get_array() is not None:
            return None
        faces, edges, sizes, paths = (
            np.asarray(handle.get_facecolor()),
            np.asarray(handle.get_edgecolor()),
            np.asarray(handle.get_sizes()),
            handle.get_paths(),
        )
        widths = np.asarray(handle.get_linewidth())
        # The Collection getter returns dash specifications; the external stub
        # gives this alias the Line2D string return type.
        strokes = cast("Sequence[tuple[float, Sequence[float] | None]]", handle.get_linestyle())
        hatch_colors = np.asarray(handle.get_hatchcolor())
        antialias = np.asarray(handle.get_antialiased())
        if (
            len(faces) != 1
            or len(edges) > 1
            or len(sizes) != 1
            or len(paths) != 1
            or len(widths) != 1
            or len(strokes) != 1
            or len(hatch_colors) > 1
            or len(antialias) != 1
        ):
            return None
        offset, dashes = strokes[0]
        if dashes is not None and len(dashes) > 256:
            return None
        stroke = (
            float(offset),
            None if dashes is None else tuple(float(value) for value in dashes),
        )
        path = paths[0]
        vertices = np.asarray(path.vertices)
        if vertices.ndim != 2 or len(vertices) > 256:
            return None
        # These coordinates describe the marker glyph, not measured point offsets.
        glyph = tuple(tuple(float(coordinate) for coordinate in vertex) for vertex in vertices)
        codes = (
            tuple(int(code) for code in np.asarray(path.codes)) if path.codes is not None else None
        )
        return _finite_native_style(
            (
                source.family,
                tuple(faces[0]),
                tuple(edges[0]) if len(edges) else (),
                float(sizes[0]),
                glyph,
                codes,
                handle.get_alpha(),
                float(widths[0]),
                stroke,
                handle.get_hatch(),
                tuple(hatch_colors[0]) if len(hatch_colors) else (),
                bool(antialias[0]),
            )
        )
    return None


def project_plotly_shared(rendered: PlotlyRenderResult) -> None:
    """Deduplicate final shared entries while retaining original visibility evidence."""
    if not rendered.shared_legend:
        return
    import plotly.graph_objects as go

    seen: set[tuple[Any, ...]] = set()
    for panel in rendered.panel_bindings:
        for binding in panel:
            trace = binding.native_trace
            if not isinstance(
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
                continue
            trace.legend = "legend"
            if trace.showlegend is False or trace.visible is False:
                continue
            display = trace.name
            if not isinstance(display, str):
                raise ValueError("Shared legend display text must be projected from its source.")
            key = shared_legend_key(binding, display, plotly_swatch(trace))
            if key is not None:
                trace.showlegend = key not in seen
                seen.add(key)
