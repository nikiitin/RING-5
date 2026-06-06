"""Bar plot implementation."""

from typing import override

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.components.plotting.config.base_plot_config import render_common_with_color
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import (
    build_color_grouped_traces,
    prepare_categorical_data,
)


class BarPlot(BasePlot):
    """Simple bar plot."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "bar")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render configuration UI for bar plot."""
        return render_common_with_color(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        """Produce bar traces from data and config."""
        x_col: str = config["x"]
        y_col: str = config["y"]

        # Cast x to string for categorical plotting
        data = prepare_categorical_data(data, [x_col])

        # Determine ordering
        if config.get("xaxis_order"):
            x_order: list[str] = [str(x) for x in config["xaxis_order"]]
        else:
            x_order = sorted(data[x_col].unique())

        def _sort_by_x(df: pd.DataFrame) -> pd.DataFrame:
            order_map = {v: i for i, v in enumerate(x_order)}
            df = df.copy()
            df["__sort_key"] = pd.Series(df[x_col]).map(order_map)
            return df.sort_values(by="__sort_key").drop(columns=["__sort_key"])

        def _make_trace(
            grp_data: pd.DataFrame,
            group_name: str | None,
            sd_col: str | None,
        ) -> BarTraceConfig:
            grp_data = _sort_by_x(grp_data)
            return BarTraceConfig(
                name=str(group_name) if group_name is not None else y_col,
                x=grp_data[x_col].tolist(),
                y=grp_data[y_col].tolist(),
                error_y=grp_data[sd_col].tolist() if sd_col else None,
            )

        traces = build_color_grouped_traces(data, config, _make_trace)
        return TraceBuildResult(traces=traces)

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Get legend column for bar plot."""
        result = config.get("color")
        return str(result) if result is not None else None
