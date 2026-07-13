"""Dual-axis bar + dot/line plot implementation.

A composite plot that overlays bars (primary Y-axis) with a dot/line series
(secondary Y-axis). The dots are always visible; lines connecting the dots
are optional. Dot color, symbol, size, and line width are all configurable.
"""

from typing import Any, override

import pandas as pd
import streamlit as st

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
    TraceConfig,
)
from src.web.components.plotting.config import dual_axis_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import (
    extract_error_bars,
    prepare_categorical_data,
)
from src.web.pages.ui.plotting.utils import order_with_overrides


class DualAxisBarDotPlot(BasePlot):
    """Dual Y-axis plot combining bars and dot/line traces.

    - Primary Y-axis (left): Bar chart for one statistic.
    - Secondary Y-axis (right): Dot (scatter) plot for another statistic,
      with optional lines connecting the dots.
    """

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "dual_axis_bar_dot")

    # Configuration UI

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render configuration UI for dual-axis bar+dot plot."""
        return dual_axis_config.render(data, saved_config, self.plot_id)

    # Figure creation

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        """Create dual-axis bar + dot/line trace configurations.

        Args:
            data: The data to plot.
            config: Configuration dictionary.

        Returns:
            TraceBuildResult with bars on primary Y and dots on secondary Y.
        """
        x_col: str = config["x"]
        y_bar: str = config["y_bar"]
        y_dot: str = config["y_dot"]
        color_col: str | None = config.get("color")
        show_lines: bool = config.get("show_lines", True)
        dot_size: int = config.get("dot_size", 10)
        dot_symbol: str = config.get("dot_symbol", "circle")
        dot_color: str | None = config.get("dot_color")
        line_width: int = config.get("line_width", 2)

        # Categorical x (+ optional color) axis; copies so input is never mutated.
        data = prepare_categorical_data(data, [x_col, color_col])

        bar_sd_col: str | None = extract_error_bars(data, y_bar, config)
        dot_sd_col: str | None = extract_error_bars(data, y_dot, config)

        # Isolation: when isolate_last_group is active and lines are shown, the
        # last x-category gets its own markers-only trace (no connecting line).
        isolate_last: bool = bool(config.get("isolate_last_group")) and show_lines
        if config.get("xaxis_order"):
            ordered_x: list[str] = [str(v) for v in config["xaxis_order"]]
        else:
            ordered_x = sorted(data[x_col].unique().tolist())
        last_x: str | None = ordered_x[-1] if ordered_x else None

        def bar_trace(df: pd.DataFrame, *, name: str, legendgroup: str = "") -> BarTraceConfig:
            """Bar trace on the primary (left) Y-axis."""
            return BarTraceConfig(
                name=name,
                x=df[x_col].tolist(),
                y=df[y_bar].tolist(),
                legendgroup=legendgroup,
                error_y=df[bar_sd_col].tolist() if bar_sd_col else None,
                yaxis="y",
            )

        def dot_traces(
            df: pd.DataFrame, *, name: str, legendgroup: str = "", color: str = ""
        ) -> list[TraceConfig]:
            """Dot/line trace(s) on the secondary (right) Y-axis.

            Honours the isolate-last-category split: the connecting line covers
            all but the last category, which gets a markers-only scatter.
            """

            def line(sub: pd.DataFrame) -> LineTraceConfig:
                return LineTraceConfig(
                    name=name,
                    x=sub[x_col].tolist(),
                    y=sub[y_dot].tolist(),
                    legendgroup=legendgroup,
                    color=color,
                    show_markers=True,
                    marker_symbol=dot_symbol,
                    marker_size=dot_size,
                    line_width=float(line_width),
                    error_y=sub[dot_sd_col].tolist() if dot_sd_col else None,
                    yaxis="y2",
                )

            def scatter(sub: pd.DataFrame, *, in_legend: bool) -> ScatterTraceConfig:
                return ScatterTraceConfig(
                    name=name,
                    x=sub[x_col].tolist(),
                    y=sub[y_dot].tolist(),
                    legendgroup=legendgroup,
                    color=color,
                    show_in_legend=in_legend,
                    marker_symbol=dot_symbol,
                    marker_size=dot_size,
                    error_y=sub[dot_sd_col].tolist() if dot_sd_col else None,
                    yaxis="y2",
                )

            out: list[TraceConfig] = []
            if isolate_last and last_x is not None:
                main_data = df[df[x_col] != last_x]
                iso_data = df[df[x_col] == last_x]
                if not main_data.empty:
                    out.append(line(main_data))
                if not iso_data.empty:
                    out.append(scatter(iso_data, in_legend=False))
            elif show_lines:
                out.append(line(df))
            else:
                out.append(scatter(df, in_legend=True))
            return out

        traces: list[TraceConfig] = []

        if color_col:
            groups = order_with_overrides(data[color_col].unique(), config.get("legend_order"))
            for grp in groups:
                grp_data: pd.DataFrame = data[data[color_col] == grp]
                traces.append(bar_trace(grp_data, name=f"{grp} ({y_bar})", legendgroup=grp))
                traces.extend(dot_traces(grp_data, name=f"{grp} ({y_dot})", legendgroup=grp))
        else:
            # No color grouping — single bar + single dot series.
            traces.append(bar_trace(data, name=y_bar))
            traces.extend(dot_traces(data, name=y_dot, color=dot_color or ""))

        return TraceBuildResult(
            traces=traces,
            barmode="group",
            secondary_y=True,
        )

    # Plot-specific advanced options

    @override
    def render_specific_advanced_options(
        self, saved_config: PlotConfig, data: pd.DataFrame | None = None
    ) -> PlotConfig:
        """Render advanced options specific to dual-axis bar+dot plot."""
        config: dict[str, Any] = {}

        st.markdown("#### Bar Settings")
        col_bar1, col_bar2 = st.columns(2)
        with col_bar1:
            config["bargap"] = st.slider(
                "Spacing between Bars (Gap)",
                min_value=0.0,
                max_value=1.0,
                value=saved_config.get("bargap", 0.2),
                step=0.05,
                key=f"bargap_{self.plot_id}",
            )

        st.markdown("#### Dot & Line Settings")
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            config["show_lines"] = st.checkbox(
                "Show lines",
                value=saved_config.get("show_lines", True),
                key=f"adv_show_lines_{self.plot_id}",
            )
        with dc2:
            symbols: list[str] = [
                "circle",
                "square",
                "diamond",
                "cross",
                "x",
                "triangle-up",
                "triangle-down",
            ]
            config["dot_symbol"] = st.selectbox(
                "Dot Symbol",
                options=symbols,
                index=(
                    symbols.index(saved_config.get("dot_symbol", "circle"))
                    if saved_config.get("dot_symbol") in symbols
                    else 0
                ),
                key=f"adv_dot_sym_{self.plot_id}",
            )
        with dc3:
            config["dot_size"] = st.number_input(
                "Dot Size",
                min_value=2,
                max_value=30,
                value=saved_config.get("dot_size", 10),
                key=f"adv_dot_size_{self.plot_id}",
            )

        dc4, dc5 = st.columns(2)
        with dc4:
            config["line_width"] = st.number_input(
                "Line Width",
                min_value=1,
                max_value=10,
                value=saved_config.get("line_width", 2),
                key=f"adv_line_width_{self.plot_id}",
                disabled=not config["show_lines"],
            )
        with dc5:
            if not saved_config.get("color"):
                config["dot_color"] = st.color_picker(
                    "Dot Color",
                    value=saved_config.get("dot_color", "#EF553B"),
                    key=f"adv_dot_color_{self.plot_id}",
                )

        # Isolation Section
        st.markdown("#### Summary Isolation (Last Category)")
        ic1, ic2 = st.columns(2)
        with ic1:
            config["isolate_last_group"] = st.checkbox(
                "Isolate Last Category",
                value=saved_config.get("isolate_last_group", False),
                key=f"iso_last_{self.plot_id}",
                help=(
                    "Removes the connecting line to the last X-axis category. "
                    "Useful when the last element is a mean/summary."
                ),
            )

        return config

    # Legend column

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Get the column used for legend grouping."""
        result: str | None = config.get("color")
        return str(result) if result is not None else None
