"""Shared helpers for building color-grouped traces.

Eliminates the duplicated grouping/error-bar pattern across
BarPlot, LinePlot, and ScatterPlot.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from typing import Any

import pandas as pd

from src.core.models.visualization.trace_config import TraceConfig
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.utils.ordering import order_with_overrides


def _browser_scalar(value: Any) -> Any:
    """Normalize a DataFrame scalar for Plotly metadata and browser messaging."""
    if value is None:
        return None
    missing = pd.isna(value)
    if not hasattr(missing, "__len__") and bool(missing):
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def build_drill_down_payload(
    data: pd.DataFrame,
    columns: Sequence[str] | Mapping[str, str],
) -> list[dict[str, Any]]:
    # [impl->req~ring5.plots.drill-down~1]
    """Build point-aligned source filters without exposing whole rows to the browser."""
    mapping = (
        dict(columns) if isinstance(columns, Mapping) else {column: column for column in columns}
    )
    if any(frame_column not in data.columns for frame_column in mapping.values()):
        return []
    return [
        {
            source_column: _browser_scalar(row[frame_column])
            for source_column, frame_column in mapping.items()
        }
        for row in data.to_dict(orient="records")
    ]


def prepare_categorical_data(
    data: pd.DataFrame,
    columns: Sequence[str | None],
    *,
    copy: bool = True,
) -> pd.DataFrame:
    """Cast the given columns to ``str`` for categorical (x / group / color) axes.

    Copies the frame by default so the caller's data is never mutated in place
    (the no-``inplace`` rule). ``None`` and absent columns are skipped, so a
    caller can pass an optional group/color column without guarding it itself.
    """
    if copy:
        data = data.copy()
    for col in columns:
        if col and col in data.columns:
            data[col] = data[col].astype(str)
    return data


def extract_error_bars(
    data: pd.DataFrame,
    y_col: str,
    config: PlotConfig,
) -> str | None:
    """Return the SD column name if error bars are enabled and the column exists."""
    # [impl->req~ring5.figure.error-bars~1]
    if config.get("show_error_bars"):
        candidate = f"{y_col}.sd"
        if candidate in data.columns:
            return candidate
    return None


def build_color_grouped_traces(
    data: pd.DataFrame,
    config: PlotConfig,
    trace_factory: Callable[[pd.DataFrame, str | None, str | None], TraceConfig],
) -> list[TraceConfig]:
    """Build traces split by the optional color column.

    Parameters
    ----------
    data:
        DataFrame to split.
    config:
        Plot configuration dict. Must include ``"x"``, ``"y"``, and
        optionally ``"color"`` and ``"legend_order"``.
    trace_factory:
        ``(group_data, group_name, sd_col) -> TraceConfig``.
        *group_name* is ``None`` when there is no color column.

    Returns
    -------
    list[TraceConfig]
        One trace per color group, or a single trace when no color column.
    """
    y_col: str = config["y"]
    color_col: str | None = config.get("color")
    sd_col = extract_error_bars(data, y_col, config)

    traces: list[TraceConfig] = []

    if color_col:
        data = prepare_categorical_data(data, [color_col])

        # Shared ordering rule: explicit legend_order first, then any remaining sorted.
        groups: list[str] = order_with_overrides(
            data[color_col].unique(), config.get("legend_order")
        )

        for grp in groups:
            grp_data = data[data[color_col] == grp]
            traces.append(trace_factory(grp_data, grp, sd_col))
    else:
        traces.append(trace_factory(data, None, sd_col))

    return traces
