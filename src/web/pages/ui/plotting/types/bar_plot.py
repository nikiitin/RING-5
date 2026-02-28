"""Bar plot implementation."""

from typing import Any, override

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.components.plotting.config import bar_config
from src.web.pages.ui.plotting.base_plot import BasePlot


class BarPlot(BasePlot):
    """Simple bar plot."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "bar")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: dict[str, Any]) -> dict[str, Any]:
        """Render configuration UI for bar plot."""
        return bar_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
        """Produce bar traces from data and config."""
        x_col: str = config["x"]
        y_col: str = config["y"]
        color_col: str | None = config.get("color")

        # Error bar column
        sd_col: str | None = None
        if config.get("show_error_bars"):
            candidate = f"{y_col}.sd"
            if candidate in data.columns:
                sd_col = candidate

        # Cast to string for categorical plotting
        data = data.copy()
        data[x_col] = data[x_col].astype(str)
        if color_col:
            data[color_col] = data[color_col].astype(str)

        # Determine ordering
        if config.get("xaxis_order"):
            x_order: list[str] = [str(x) for x in config["xaxis_order"]]
        else:
            x_order = sorted(data[x_col].unique())

        traces: list[BarTraceConfig] = []

        if color_col:
            if config.get("legend_order"):
                groups: list[str] = [str(g) for g in config["legend_order"]]
            else:
                groups = sorted(data[color_col].unique())

            for grp in groups:
                grp_data = data[data[color_col] == grp]
                # Sort to match x_order without reindex (avoids duplicate label errors)
                order_map = {v: i for i, v in enumerate(x_order)}
                grp_data = grp_data.copy()
                grp_data["__sort_key"] = pd.Series(grp_data[x_col]).map(order_map)
                grp_data = grp_data.sort_values(by="__sort_key").drop(columns=["__sort_key"])
                error_y = grp_data[sd_col].tolist() if sd_col else None
                traces.append(
                    BarTraceConfig(
                        name=str(grp),
                        x=grp_data[x_col].tolist(),
                        y=grp_data[y_col].tolist(),
                        error_y=error_y,
                    )
                )
        else:
            # Sort to match x_order without reindex
            order_map = {v: i for i, v in enumerate(x_order)}
            data = data.copy()
            data["__sort_key"] = pd.Series(data[x_col]).map(order_map)
            data = data.sort_values(by="__sort_key").drop(columns=["__sort_key"])
            error_y = data[sd_col].tolist() if sd_col else None
            traces.append(
                BarTraceConfig(
                    name=y_col,
                    x=data[x_col].tolist(),
                    y=data[y_col].tolist(),
                    error_y=error_y,
                )
            )

        return TraceBuildResult(traces=traces)

    @override
    def get_legend_column(self, config: dict[str, Any]) -> str | None:
        """Get legend column for bar plot."""
        result = config.get("color")
        return str(result) if result is not None else None
