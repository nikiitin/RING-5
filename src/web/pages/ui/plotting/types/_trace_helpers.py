"""Shared helpers for building color-grouped traces.

Eliminates the duplicated grouping/error-bar pattern across
BarPlot, LinePlot, and ScatterPlot.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from src.core.models.visualization.trace_config import TraceConfig
from src.web.models.plot_models import PlotConfig


def extract_error_bars(
    data: pd.DataFrame,
    y_col: str,
    config: PlotConfig,
) -> str | None:
    """Return the SD column name if error bars are enabled and the column exists."""
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
        data = data.copy()
        data[color_col] = data[color_col].astype(str)

        if config.get("legend_order"):
            groups: list[str] = [str(g) for g in config["legend_order"]]
        else:
            groups = sorted(data[color_col].unique())

        for grp in groups:
            grp_data = data[data[color_col] == grp]
            traces.append(trace_factory(grp_data, grp, sd_col))
    else:
        traces.append(trace_factory(data, None, sd_col))

    return traces
