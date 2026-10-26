"""Conservative native swatch equivalence for source-owned shared legends."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import math

if TYPE_CHECKING:
    from plotly.basedatatypes import BaseTraceType
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


def plotly_swatch(trace: BaseTraceType) -> tuple[Any, ...] | None:
    """Compare only known scalar native legend properties, never plotted values."""
    import plotly.graph_objects as go

    if isinstance(trace, (go.Bar, go.Histogram)):
        marker = trace.marker
        if any(
            color is not None and not isinstance(color, str)
            for color in (marker.color, marker.line.color)
        ):
            return None
        return _scalar_style(
            (
                trace.type,
                marker.color,
                marker.opacity,
                marker.line.color,
                marker.line.width,
                marker.pattern.shape,
                marker.pattern.path,
                marker.pattern.size,
                marker.pattern.solidity,
                trace.opacity,
            )
        )
    if isinstance(trace, (go.Scatter, go.Scattergl, go.Scatterpolar, go.Box, go.Violin)):
        marker, line = trace.marker, trace.line
        if any(
            color is not None and not isinstance(color, str)
            for color in (marker.color, marker.line.color, line.color)
        ):
            return None
        return _scalar_style(
            (
                trace.type,
                marker.color,
                marker.opacity,
                marker.size,
                marker.symbol,
                marker.line.color,
                marker.line.width,
                line.color,
                line.width,
                getattr(line, "dash", None),
                getattr(trace, "fillcolor", None),
                trace.opacity,
            )
        )
    if isinstance(trace, go.Waterfall):
        return _scalar_style(
            (
                trace.type,
                trace.increasing.marker.color,
                trace.decreasing.marker.color,
                trace.totals.marker.color,
                trace.connector.line.color,
                trace.connector.line.width,
                trace.connector.line.dash,
                trace.opacity,
            )
        )
    return None


def matplotlib_swatch(source: MatplotlibTraceBinding) -> tuple[Any, ...] | None:
    """Describe a scalar native representative, including a bounded marker glyph."""
    import numpy as np
    from matplotlib.collections import PathCollection
    from matplotlib.colors import to_rgba
    from matplotlib.container import BarContainer
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    handle = source.legend_handle
    if isinstance(handle, BarContainer):
        if not handle.patches:
            return None
        handle = handle.patches[0]
    if isinstance(handle, Patch):
        return (
            source.family,
            tuple(handle.get_facecolor()),
            tuple(handle.get_edgecolor()),
            handle.get_alpha(),
            handle.get_hatch(),
            handle.get_linewidth(),
            handle.get_linestyle(),
        )
    if isinstance(handle, Line2D):
        try:
            colors = (
                to_rgba(handle.get_color()),
                to_rgba(handle.get_markerfacecolor()),
                to_rgba(handle.get_markeredgecolor()),
            )
        except (TypeError, ValueError):
            return None
        marker = handle.get_marker()
        if not isinstance(marker, (str, int)):
            return None
        return (
            source.family,
            colors,
            handle.get_alpha(),
            handle.get_linestyle(),
            handle.get_linewidth(),
            marker,
            handle.get_markersize(),
            handle.get_markeredgewidth(),
        )
    if isinstance(handle, PathCollection):
        if handle.get_array() is not None:
            return None
        faces, edges, sizes, paths = (
            np.asarray(handle.get_facecolor()),
            np.asarray(handle.get_edgecolor()),
            np.asarray(handle.get_sizes()),
            handle.get_paths(),
        )
        if len(faces) != 1 or len(edges) > 1 or len(sizes) != 1 or len(paths) != 1:
            return None
        path = paths[0]
        vertices = np.asarray(path.vertices)
        if vertices.ndim != 2 or len(vertices) > 256:
            return None
        # These coordinates describe the marker glyph, not measured point offsets.
        glyph = tuple(tuple(float(coordinate) for coordinate in vertex) for vertex in vertices)
        codes = (
            tuple(int(code) for code in np.asarray(path.codes)) if path.codes is not None else None
        )
        return (
            source.family,
            tuple(faces[0]),
            tuple(edges[0]) if len(edges) else (),
            float(sizes[0]),
            glyph,
            codes,
            handle.get_alpha(),
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
