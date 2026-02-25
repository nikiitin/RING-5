"""Scatter plot implementation."""

from typing import Any

import pandas as pd

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import ScatterTraceConfig
from src.web.components.plotting.config import scatter_config
from src.web.pages.ui.plotting.base_plot import BasePlot


class ScatterPlot(BasePlot):
    """Scatter plot."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "scatter")

    def render_config_ui(self, data: pd.DataFrame, saved_config: dict[str, Any]) -> dict[str, Any]:
        """Render configuration UI for scatter plot."""
        return scatter_config.render(data, saved_config, self.plot_id)

    def create_traces(self, data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
        """Produce scatter traces from data and config."""
        x_col: str = config["x"]
        y_col: str = config["y"]
        color_col: str | None = config.get("color")

        # Error bar column
        sd_col: str | None = None
        if config.get("show_error_bars"):
            candidate = f"{y_col}.sd"
            if candidate in data.columns:
                sd_col = candidate

        traces: list[ScatterTraceConfig] = []

        if color_col:
            groups: list[str] = sorted(data[color_col].unique().astype(str))
            data = data.copy()
            data[color_col] = data[color_col].astype(str)
            for grp in groups:
                grp_data = data[data[color_col] == grp]
                error_y = grp_data[sd_col].tolist() if sd_col else None
                traces.append(
                    ScatterTraceConfig(
                        name=str(grp),
                        x=grp_data[x_col].tolist(),
                        y=grp_data[y_col].tolist(),
                        error_y=error_y,
                    )
                )
        else:
            error_y = data[sd_col].tolist() if sd_col else None
            traces.append(
                ScatterTraceConfig(
                    name=y_col,
                    x=data[x_col].tolist(),
                    y=data[y_col].tolist(),
                    error_y=error_y,
                )
            )

        return TraceBuildResult(traces=traces)

    def get_legend_column(self, config: dict[str, Any]) -> str | None:
        """Get legend column for scatter plot."""
        result = config.get("color")
        return str(result) if result is not None else None
