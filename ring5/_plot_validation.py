"""Validation for the mapping-based public plot configuration surface."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any

import pandas as pd

from ring5.errors import ColumnNotFoundError, DataValidationError
from src.core.models.visualization.trace_config import (
    LINE_DASHES,
    LINE_MARKER_SYMBOLS,
    LINE_SHAPES,
)

_REQUIRED_SINGLE: dict[str, tuple[str, ...]] = {
    "area": ("x", "y"),
    "bar": ("x", "y"),
    "box": ("x", "y"),
    "dual_axis_bar_dot": ("x", "y_bar", "y_dot"),
    "ecdf": ("x",),
    "grouped_bar": ("x", "y"),
    "grouped_stacked_bar": ("x",),
    "heatmap": ("x",),
    "histogram": ("histogram_variable",),
    "line": ("x", "y"),
    "parallel_coordinates": (),
    "radar": ("x", "y"),
    "sankey": ("sankey_source", "sankey_target", "sankey_value"),
    "scatter": ("x", "y"),
    "stacked_bar": ("x",),
    "violin": ("x", "y"),
    "waterfall": ("x", "y"),
}

_REQUIRED_LIST: dict[str, tuple[str, ...]] = {
    "grouped_stacked_bar": ("y_columns",),
    "heatmap": ("metric_columns",),
    "parallel_coordinates": ("parallel_dimensions",),
    "stacked_bar": ("y_columns",),
}

_OPTIONAL_SINGLE: dict[str, tuple[str, ...]] = {
    "area": ("color",),
    "bar": ("color",),
    "box": ("color",),
    "dual_axis_bar_dot": ("color",),
    "ecdf": ("color",),
    "grouped_bar": ("group",),
    "grouped_stacked_bar": ("group",),
    "heatmap": ("facet_col",),
    "histogram": ("group_by",),
    "line": ("color",),
    "parallel_coordinates": ("parallel_color",),
    "radar": ("color",),
    "sankey": ("sankey_label",),
    "scatter": ("color",),
    "violin": ("color",),
}

_OPTIONAL_LIST: dict[str, tuple[str, ...]] = {
    "grouped_stacked_bar": ("y_columns_right",),
}


def _column(data: pd.DataFrame, config: Mapping[str, Any], field: str, *, required: bool) -> None:
    value = config.get(field)
    if value is None and not required:
        return
    if not isinstance(value, str) or not value:
        qualifier = "required" if required else "optional"
        raise DataValidationError(
            f"Plot config field {field!r} is {qualifier} and must be a non-empty string."
        )
    if value not in data.columns:
        raise ColumnNotFoundError(value, list(data.columns))


def _columns(data: pd.DataFrame, config: Mapping[str, Any], field: str, *, required: bool) -> None:
    value = config.get(field)
    if value is None and not required:
        return
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(column, str) or not column for column in value)
    ):
        qualifier = "a non-empty" if required else "an optional non-empty"
        raise DataValidationError(
            f"Plot config field {field!r} must be {qualifier} list of column names."
        )
    for column in value:
        if column not in data.columns:
            raise ColumnNotFoundError(column, list(data.columns))


def _validate_line_style(config: Mapping[str, Any]) -> None:
    # [impl->req~ring5.figure.line-styles~1]
    """Reject line styles that cannot be rendered consistently."""
    choices = {
        "line_shape": LINE_SHAPES,
        "line_dash": LINE_DASHES,
        "marker_symbol": LINE_MARKER_SYMBOLS,
    }
    for field, allowed in choices.items():
        if field in config and config[field] not in allowed:
            raise DataValidationError(
                f"Plot config field {field!r} must be one of {list(allowed)}."
            )

    if "line_width" in config:
        width = config["line_width"]
        if isinstance(width, bool) or not isinstance(width, Real) or not 0.5 <= float(width) <= 20:
            raise DataValidationError("Plot config field 'line_width' must be from 0.5 through 20.")
    if "marker_size" in config:
        size = config["marker_size"]
        if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 50:
            raise DataValidationError("Plot config field 'marker_size' must be from 1 through 50.")
    for field in ("show_markers", "connect_gaps"):
        if field in config and not isinstance(config[field], bool):
            raise DataValidationError(f"Plot config field {field!r} must be a boolean.")


def validate_plot_config(plot_type: str, data: pd.DataFrame, config: Mapping[str, Any]) -> None:
    # [impl->req~ring5.api.plot-validation~1]
    """Validate required fields, their types, and every referenced column.

    Args:
        plot_type: Registered snake-case plot identifier.
        data: Data available to the plot.
        config: Flat renderer configuration mapping.

    Raises:
        ColumnNotFoundError: A referenced column is absent.
        DataValidationError: A required field or value type is invalid.
    """
    for field in _REQUIRED_SINGLE[plot_type]:
        if plot_type == "histogram" and field == "histogram_variable":
            value = config.get(field)
            if not isinstance(value, str) or not value:
                raise DataValidationError(
                    "Plot config field 'histogram_variable' is required and must be a "
                    "non-empty string."
                )
            bucket_prefix = f"{value}.."
            if not any(
                isinstance(column, str)
                and column.startswith(bucket_prefix)
                and not column.endswith(".sd")
                for column in data.columns
            ):
                raise DataValidationError(
                    f"No histogram bucket columns found for variable {value!r}."
                )
            continue
        _column(data, config, field, required=True)

    for field in _REQUIRED_LIST.get(plot_type, ()):
        _columns(data, config, field, required=True)
    for field in _OPTIONAL_SINGLE.get(plot_type, ()):
        _column(data, config, field, required=False)
    for field in _OPTIONAL_LIST.get(plot_type, ()):
        _columns(data, config, field, required=False)
    if plot_type == "line":
        _validate_line_style(config)
