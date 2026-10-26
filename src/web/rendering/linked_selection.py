"""Pure Plotly transformations for linked selection and cross-filtering."""

from __future__ import annotations

import json
import math
import re
from hashlib import sha256
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any, cast

import plotly.graph_objects as go

from src.core.models.visualization.linked_selection_spec import LinkedSelectionSpec

_POINT_FIELDS = ("x", "y", "text", "hovertext", "customdata", "ids")
_MARKER_FIELDS = ("color", "size", "symbol", "opacity", "line")
_ERROR_FIELDS = ("array", "arrayminus")


def _value_key(value: Any) -> str:
    """Create a stable cross-trace comparison key for a Plotly scalar."""
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            # Keep the original extension scalar when conversion is unsupported.
            pass
    if isinstance(value, (datetime, date)):
        return f"date:{value.isoformat()}"
    if isinstance(value, float) and math.isnan(value):
        return "float:nan"
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return f"{type(value).__name__}:{value}"


def _as_points(value: Any) -> list[Any] | None:
    """Return a point-aligned list, excluding scalar strings and mappings."""
    if value is None or isinstance(value, (str, bytes, Mapping)):
        return None
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, Sequence):
        return list(value)
    return None


def _slice_if_aligned(value: Any, indices: list[int], point_count: int) -> Any:
    points = _as_points(value)
    if points is None or len(points) != point_count:
        return value
    return [points[index] for index in indices]


def _filter_point_trace(trace: Any, indices: list[int], point_count: int) -> None:
    """Slice every common point-aligned trace property without touching its source plot."""
    for field in _POINT_FIELDS:
        value = getattr(trace, field, None)
        sliced = _slice_if_aligned(value, indices, point_count)
        if sliced is not value:
            setattr(trace, field, sliced)

    marker = getattr(trace, "marker", None)
    if marker is not None:
        for field in _MARKER_FIELDS:
            value = getattr(marker, field, None)
            sliced = _slice_if_aligned(value, indices, point_count)
            if sliced is not value:
                setattr(marker, field, sliced)

    if marker is not None and marker.line is not None:
        for field in ("color", "width"):
            value = getattr(marker.line, field, None)
            sliced = _slice_if_aligned(value, indices, point_count)
            if sliced is not value:
                setattr(marker.line, field, sliced)

    if isinstance(trace.meta, Mapping):
        meta = dict(trace.meta)
        if "ring5_drilldown" in meta:
            meta["ring5_drilldown"] = _slice_if_aligned(
                meta["ring5_drilldown"], indices, point_count
            )
        trace.meta = meta

    for group_name in ("error_x", "error_y"):
        error = getattr(trace, group_name, None)
        if error is None:
            continue
        for field in _ERROR_FIELDS:
            value = getattr(error, field, None)
            sliced = _slice_if_aligned(value, indices, point_count)
            if sliced is not value:
                setattr(error, field, sliced)


def _filter_heatmap(figure: go.Figure, trace: Any, axis: str, indices: list[int]) -> None:
    """Filter cells and their metadata, labels, and totals separators together."""
    old_x = list(trace.x)
    old_y = list(trace.y)
    old_values = old_x if axis == "x" else old_y
    retained = {_value_key(old_values[index]) for index in indices}
    xref, yref = trace.xaxis or "x", trace.yaxis or "y"

    def slice_matrix(value: Any) -> Any:
        rows = _as_points(value)
        if rows is None or len(rows) != len(old_y):
            return value
        if axis == "y":
            return [rows[index] for index in indices]
        return [[row[index] for index in indices] for row in rows]

    for field in ("z", "text", "customdata"):
        value = getattr(trace, field, None)
        if value is not None:
            setattr(trace, field, slice_matrix(value))
    if isinstance(trace.meta, Mapping):
        meta = dict(trace.meta)
        if "ring5_drilldown" in meta:
            meta["ring5_drilldown"] = slice_matrix(meta["ring5_drilldown"])
        trace.meta = meta
    setattr(trace, axis, [old_values[index] for index in indices])

    annotations = []
    for annotation in figure.layout.annotations or ():
        owned = (
            re.fullmatch(r"ring5-(?:panel-\d+-)?source-label-\d+", str(annotation.name or ""))
            is not None
        )
        same_axes = annotation.xref == xref and annotation.yref == yref
        coordinate = annotation.x if axis == "x" else annotation.y
        if not (owned and same_axes and _value_key(coordinate) not in retained):
            annotations.append(annotation)
    figure.layout.annotations = annotations

    shapes = []
    for shape in figure.layout.shapes or ():
        owned = str(shape.name or "").startswith("ring5-heatmap-total-")
        if not (owned and shape.xref == xref and shape.yref == yref):
            shapes.append(shape)
            continue
        right = shape.name == "ring5-heatmap-total-right"
        if (axis == "x" and right) or (axis == "y" and not right):
            boundary = float(shape.x0 if right else shape.y0) + 0.5
            total_indices = [
                index for index in indices if (index >= boundary if right else index < boundary)
            ]
            if not total_indices or len(total_indices) == len(indices):
                continue
            position = (
                len(indices) - len(total_indices) - 0.5 if right else len(total_indices) - 0.5
            )
            if right:
                shape.x0 = shape.x1 = position
            else:
                shape.y0 = shape.y1 = position
        if right:
            shape.y0, shape.y1 = -0.5, len(trace.y) - 0.5
        else:
            shape.x0, shape.x1 = -0.5, len(trace.x) - 0.5
        shapes.append(shape)
    figure.layout.shapes = shapes


def apply_linked_selection(
    figure: go.Figure,
    spec: LinkedSelectionSpec,
    values: Sequence[Any],
) -> go.Figure:
    # [impl->req~ring5.plots.linked-selections~1]
    """Return a selected figure copy; never mutate the input figure or source data.

    ``highlight`` assigns Plotly ``selectedpoints`` and fades unselected
    markers. ``filter`` slices point-aligned trace arrays. Heatmaps are sliced
    in either mode because Plotly does not expose selected-point styling for
    heatmap cells.
    """
    if not isinstance(figure, go.Figure):
        raise TypeError("Linked selections require a Plotly figure.")
    selected_keys = {_value_key(value) for value in values}
    result = go.Figure(figure)
    if not selected_keys:
        return result

    for trace in result.data:
        axis_values = _as_points(getattr(trace, spec.axis, None))
        if axis_values is None:
            continue
        indices = [
            index for index, value in enumerate(axis_values) if _value_key(value) in selected_keys
        ]
        if getattr(trace, "type", "") == "heatmap":
            _filter_heatmap(result, trace, spec.axis, indices)
        elif spec.mode == "filter":
            _filter_point_trace(trace, indices, len(axis_values))
        else:
            valid_props = cast(set[str], trace._valid_props)
            if spec.mode != "highlight" or "selectedpoints" not in valid_props:
                continue
            trace.selectedpoints = indices
            if "selected" in valid_props:
                trace.selected = {"marker": {"opacity": 1.0}}
            if "unselected" in valid_props:
                trace.unselected = {"marker": {"opacity": 0.18}}

    selection_digest = sha256("\n".join(sorted(selected_keys)).encode()).hexdigest()[:12]
    result.update_layout(selectionrevision=f"{spec.axis}:{spec.mode}:{selection_digest}")
    return result


def selection_values_from_event(event: Mapping[str, Any], axis: str) -> tuple[Any, ...]:
    """Extract ordered unique X/Y values from a sanitized browser event."""
    if axis not in ("x", "y"):
        raise ValueError("Selection event axis must be 'x' or 'y'.")
    points = event.get("points", [])
    if not isinstance(points, list):
        return ()
    result: list[Any] = []
    seen: set[str] = set()
    for point in points:
        if not isinstance(point, Mapping) or axis not in point:
            continue
        value = point[axis]
        key = _value_key(value)
        if key not in seen:
            result.append(value)
            seen.add(key)
    return tuple(result)


__all__ = ["apply_linked_selection", "selection_values_from_event"]
