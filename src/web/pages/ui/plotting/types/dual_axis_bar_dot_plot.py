"""Dual-axis bar + dot/line plot implementation.

A composite plot that overlays bars (primary Y-axis) with a dot/line series
(secondary Y-axis). The dots are always visible; lines connecting the dots
are optional. Dot color, symbol, size, and line width are all configurable.
"""

from typing import Any

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
from src.web.pages.ui.plotting.base_plot import BasePlot


class DualAxisBarDotPlot(BasePlot):
    """Dual Y-axis plot combining bars and dot/line traces.

    - Primary Y-axis (left): Bar chart for one statistic.
    - Secondary Y-axis (right): Dot (scatter) plot for another statistic,
      with optional lines connecting the dots.
    """

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "dual_axis_bar_dot")

    # ------------------------------------------------------------------
    # Configuration UI
    # ------------------------------------------------------------------

    def render_config_ui(self, data: pd.DataFrame, saved_config: dict[str, Any]) -> dict[str, Any]:
        """Render configuration UI for dual-axis bar+dot plot."""
        return dual_axis_config.render(data, saved_config, self.plot_id)

    # ------------------------------------------------------------------
    # Figure creation
    # ------------------------------------------------------------------

    def create_traces(self, data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
        """Create dual-axis bar + dot/line trace configurations.

        Args:
            data: The data to plot.
            config: Configuration dictionary.

        Returns:
            TraceBuildResult with bars on primary Y and dots on secondary Y.
        """
        data = data.copy()
        x_col: str = config["x"]
        y_bar: str = config["y_bar"]
        y_dot: str = config["y_dot"]
        color_col: str | None = config.get("color")
        show_lines: bool = config.get("show_lines", True)
        dot_size: int = config.get("dot_size", 10)
        dot_symbol: str = config.get("dot_symbol", "circle")
        dot_color: str | None = config.get("dot_color")
        line_width: int = config.get("line_width", 2)

        # Ensure categorical x-axis
        data[x_col] = data[x_col].astype(str)
        if color_col:
            data[color_col] = data[color_col].astype(str)

        # Error bar helpers
        bar_sd_col: str | None = None
        dot_sd_col: str | None = None
        if config.get("show_error_bars"):
            bar_sd_candidate = f"{y_bar}.sd"
            if bar_sd_candidate in data.columns:
                bar_sd_col = bar_sd_candidate
            dot_sd_candidate = f"{y_dot}.sd"
            if dot_sd_candidate in data.columns:
                dot_sd_col = dot_sd_candidate

        # Isolation: when isolate_last_group is active and lines are shown,
        # the last x-category gets its own markers-only trace
        isolate_last: bool = bool(config.get("isolate_last_group")) and show_lines

        # Resolve ordered x-categories for isolation split
        ordered_x: list[str]
        if config.get("xaxis_order"):
            ordered_x = [str(v) for v in config["xaxis_order"]]
        else:
            ordered_x = sorted(data[x_col].unique().tolist())
        last_x: str | None = ordered_x[-1] if ordered_x else None

        traces: list[TraceConfig] = []

        if color_col:
            groups: list[str] = sorted(data[color_col].unique().tolist())
            if config.get("legend_order"):
                ordered: list[str] = [
                    str(g) for g in config["legend_order"] if str(g) in data[color_col].unique()
                ]
                missing: list[str] = [g for g in groups if g not in ordered]
                groups = ordered + missing

            for grp in groups:
                grp_data: pd.DataFrame = pd.DataFrame(data[data[color_col] == grp])

                # Bar trace (primary Y)
                bar_error: list[float] | None = None
                if bar_sd_col:
                    bar_error = grp_data[bar_sd_col].tolist()

                traces.append(
                    BarTraceConfig(
                        name=f"{grp} ({y_bar})",
                        x=grp_data[x_col].tolist(),
                        y=grp_data[y_bar].tolist(),
                        legendgroup=grp,
                        error_y=bar_error,
                        yaxis="y",
                    )
                )

                # Scatter traces — split if isolating last category
                if isolate_last and last_x is not None:
                    main_data = grp_data[grp_data[x_col] != last_x]
                    iso_data = grp_data[grp_data[x_col] == last_x]

                    if not main_data.empty:
                        main_dot_error: list[float] | None = None
                        if dot_sd_col:
                            main_dot_error = main_data[dot_sd_col].tolist()
                        traces.append(
                            LineTraceConfig(
                                name=f"{grp} ({y_dot})",
                                x=main_data[x_col].tolist(),
                                y=main_data[y_dot].tolist(),
                                legendgroup=grp,
                                show_markers=True,
                                marker_symbol=dot_symbol,
                                marker_size=dot_size,
                                line_width=float(line_width),
                                error_y=main_dot_error,
                                yaxis="y2",
                            )
                        )

                    if not iso_data.empty:
                        iso_dot_error: list[float] | None = None
                        if dot_sd_col:
                            iso_dot_error = iso_data[dot_sd_col].tolist()
                        traces.append(
                            ScatterTraceConfig(
                                name=f"{grp} ({y_dot})",
                                x=iso_data[x_col].tolist(),
                                y=iso_data[y_dot].tolist(),
                                legendgroup=grp,
                                show_in_legend=False,
                                marker_symbol=dot_symbol,
                                marker_size=dot_size,
                                error_y=iso_dot_error,
                                yaxis="y2",
                            )
                        )
                else:
                    dot_error: list[float] | None = None
                    if dot_sd_col:
                        dot_error = grp_data[dot_sd_col].tolist()

                    if show_lines:
                        traces.append(
                            LineTraceConfig(
                                name=f"{grp} ({y_dot})",
                                x=grp_data[x_col].tolist(),
                                y=grp_data[y_dot].tolist(),
                                legendgroup=grp,
                                show_markers=True,
                                marker_symbol=dot_symbol,
                                marker_size=dot_size,
                                line_width=float(line_width),
                                error_y=dot_error,
                                yaxis="y2",
                            )
                        )
                    else:
                        traces.append(
                            ScatterTraceConfig(
                                name=f"{grp} ({y_dot})",
                                x=grp_data[x_col].tolist(),
                                y=grp_data[y_dot].tolist(),
                                legendgroup=grp,
                                marker_symbol=dot_symbol,
                                marker_size=dot_size,
                                error_y=dot_error,
                                yaxis="y2",
                            )
                        )
        else:
            # No color grouping — single bar + single dot trace
            bar_error_vals: list[float] | None = None
            if bar_sd_col:
                bar_error_vals = data[bar_sd_col].tolist()

            traces.append(
                BarTraceConfig(
                    name=y_bar,
                    x=data[x_col].tolist(),
                    y=data[y_bar].tolist(),
                    error_y=bar_error_vals,
                    yaxis="y",
                )
            )

            if isolate_last and last_x is not None:
                main_data = data[data[x_col] != last_x]
                iso_data = data[data[x_col] == last_x]

                if not main_data.empty:
                    main_dot_error_vals: list[float] | None = None
                    if dot_sd_col:
                        main_dot_error_vals = main_data[dot_sd_col].tolist()
                    traces.append(
                        LineTraceConfig(
                            name=y_dot,
                            x=main_data[x_col].tolist(),
                            y=main_data[y_dot].tolist(),
                            color=dot_color or "",
                            show_markers=True,
                            marker_symbol=dot_symbol,
                            marker_size=dot_size,
                            line_width=float(line_width),
                            error_y=main_dot_error_vals,
                            yaxis="y2",
                        )
                    )

                if not iso_data.empty:
                    iso_dot_error_vals: list[float] | None = None
                    if dot_sd_col:
                        iso_dot_error_vals = iso_data[dot_sd_col].tolist()
                    traces.append(
                        ScatterTraceConfig(
                            name=y_dot,
                            x=iso_data[x_col].tolist(),
                            y=iso_data[y_dot].tolist(),
                            show_in_legend=False,
                            color=dot_color or "",
                            marker_symbol=dot_symbol,
                            marker_size=dot_size,
                            error_y=iso_dot_error_vals,
                            yaxis="y2",
                        )
                    )
            else:
                dot_error_vals: list[float] | None = None
                if dot_sd_col:
                    dot_error_vals = data[dot_sd_col].tolist()

                if show_lines:
                    traces.append(
                        LineTraceConfig(
                            name=y_dot,
                            x=data[x_col].tolist(),
                            y=data[y_dot].tolist(),
                            color=dot_color or "",
                            show_markers=True,
                            marker_symbol=dot_symbol,
                            marker_size=dot_size,
                            line_width=float(line_width),
                            error_y=dot_error_vals,
                            yaxis="y2",
                        )
                    )
                else:
                    traces.append(
                        ScatterTraceConfig(
                            name=y_dot,
                            x=data[x_col].tolist(),
                            y=data[y_dot].tolist(),
                            color=dot_color or "",
                            marker_symbol=dot_symbol,
                            marker_size=dot_size,
                            error_y=dot_error_vals,
                            yaxis="y2",
                        )
                    )

        return TraceBuildResult(
            traces=traces,
            barmode="group",
            secondary_y=True,
        )

    # ------------------------------------------------------------------
    # Plot-specific advanced options
    # ------------------------------------------------------------------

    def render_specific_advanced_options(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None = None
    ) -> dict[str, Any]:
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

    # ------------------------------------------------------------------
    # Legend column
    # ------------------------------------------------------------------

    def get_legend_column(self, config: dict[str, Any]) -> str | None:
        """Get the column used for legend grouping."""
        result: str | None = config.get("color")
        return str(result) if result is not None else None
