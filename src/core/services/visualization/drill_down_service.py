"""Non-mutating source-row resolution for plot drill-down interactions."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

import pandas as pd

from src.core.models.visualization.drill_down_result import DrillDownResult


def _is_scalar_filter(value: Any) -> bool:
    """Return whether a browser-provided filter is safe to compare as a scalar."""
    return value is None or bool(pd.api.types.is_scalar(value))


def _matching_rows(series: pd.Series[Any], value: Any) -> pd.Series[bool]:
    """Match native values, including the string form used by categorical plots."""
    if value is None:
        return series.isna()
    try:
        exact = series.eq(value).fillna(False).astype(bool)
    except (TypeError, ValueError):
        exact = pd.Series(False, index=series.index, dtype=bool)
    if isinstance(value, str):

        def render(item: Any) -> str:
            if item is None:
                return ""
            missing = pd.isna(item)
            if not hasattr(missing, "__len__") and bool(missing):
                return ""
            if hasattr(item, "item"):
                try:
                    item = item.item()
                except (TypeError, ValueError):
                    # Keep the original extension scalar when conversion is unsupported.
                    pass
            if isinstance(item, (date, datetime)):
                return item.isoformat()
            return str(item)

        rendered = series.map(render)
        return exact | rendered.eq(value)
    return exact


def drill_down_rows(
    plot_id: int,
    source_data: pd.DataFrame,
    filters: Mapping[str, Any],
) -> DrillDownResult:
    # [impl->req~ring5.plots.drill-down~1]
    """Return source rows matching the exact dimensions attached to a plot point."""
    if isinstance(plot_id, bool) or not isinstance(plot_id, int):
        raise ValueError("Drill-down plot ID must be an integer.")
    if not isinstance(source_data, pd.DataFrame):
        raise ValueError("Drill-down source data must be a pandas DataFrame.")
    if not isinstance(filters, Mapping):
        raise ValueError("Drill-down filters must be a column-to-value mapping.")

    normalized: list[tuple[str, Any]] = []
    for column, value in filters.items():
        if not isinstance(column, str) or not column:
            raise ValueError("Drill-down filter columns must be non-empty strings.")
        if column not in source_data.columns:
            raise ValueError(f"Drill-down source data has no column {column!r}.")
        if not _is_scalar_filter(value):
            raise ValueError(f"Drill-down filter for {column!r} must be a scalar value.")
        normalized.append((column, value))

    mask = pd.Series(True, index=source_data.index, dtype=bool)
    for column, value in normalized:
        mask &= _matching_rows(source_data[column], value)
    return DrillDownResult(
        plot_id=plot_id,
        filters=tuple(normalized),
        _rows=source_data.loc[mask],
    )


__all__ = ["drill_down_rows"]
