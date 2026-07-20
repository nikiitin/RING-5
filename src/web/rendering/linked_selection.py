"""Pure Plotly transformations for linked selection and cross-filtering."""

from __future__ import annotations

import json
import math
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

    for group_name in ("error_x", "error_y"):
        error = getattr(trace, group_name, None)
        if error is None:
            continue
        for field in _ERROR_FIELDS:
            value = getattr(error, field, None)
            sliced = _slice_if_aligned(value, indices, point_count)
            if sliced is not value:
                setattr(error, field, sliced)


def _filter_heatmap(trace: Any, axis: str, indices: list[int]) -> None:
    """Filter heatmap rows or columns while retaining aligned labels and text."""
    z_rows = _as_points(getattr(trace, "z", None)) or []
    if axis == "x":
        x_values = _as_points(getattr(trace, "x", None)) or []
        trace.x = [x_values[index] for index in indices]
        trace.z = [[row[index] for index in indices] for row in z_rows if isinstance(row, Sequence)]
        text_rows = _as_points(getattr(trace, "text", None))
        if text_rows:
            trace.text = [
                [row[index] for index in indices] for row in text_rows if isinstance(row, Sequence)
            ]
        return

    y_values = _as_points(getattr(trace, "y", None)) or []
    trace.y = [y_values[index] for index in indices]
    trace.z = [z_rows[index] for index in indices]
    text_rows = _as_points(getattr(trace, "text", None))
    if text_rows:
        trace.text = [text_rows[index] for index in indices]


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
    result = go.Figure(figure.to_dict())
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
            _filter_heatmap(trace, spec.axis, indices)
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
