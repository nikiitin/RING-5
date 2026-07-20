"""Line plot implementation."""

from typing import Any, override

import pandas as pd
import streamlit as st

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import (
    LINE_DASHES,
    LINE_MARKER_SYMBOLS,
    LINE_SHAPES,
    LineTraceConfig,
)
from src.web.components.plotting.config.base_plot_config import render_common_with_color
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import (
    build_color_grouped_traces,
    build_drill_down_payload,
)

_CONNECTOR_LABELS = {
    "Straight": "linear",
    "Smooth spline": "spline",
    "Step after": "hv",
    "Step before": "vh",
    "Centered step (H-V-H)": "hvh",
    "Centered step (V-H-V)": "vhv",
}
_DASH_LABELS = {
    "Solid": "solid",
    "Dashed": "dash",
    "Dotted": "dot",
    "Dash-dot": "dashdot",
    "Long dash": "longdash",
    "Long dash-dot": "longdashdot",
}


def _selected_label(options: dict[str, str], value: Any, default: str) -> str:
    """Return the human label for a stored value, falling back safely."""
    return next((label for label, stored in options.items() if stored == value), default)


def _bounded_saved_number(value: Any, minimum: float, maximum: float, default: float) -> float:
    """Return a finite saved widget value inside its supported range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    numeric = float(value)
    if not minimum <= numeric <= maximum:
        return default
    return numeric


class LinePlot(BasePlot):
    """Line plot."""

    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, "line")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render configuration UI for line plot."""
        return render_common_with_color(data, saved_config, self.plot_id)

    @override
    def render_specific_advanced_options(
        self, saved_config: PlotConfig, data: pd.DataFrame | None = None
    ) -> PlotConfig:
        """Specific options for Line Plot."""
        # [impl->req~ring5.figure.line-styles~1]
        config: PlotConfig = {}
        st.markdown("#### Line & marker style")
        connector_labels = list(_CONNECTOR_LABELS)
        saved_connector = _selected_label(
            _CONNECTOR_LABELS, saved_config.get("line_shape"), "Straight"
        )
        connector_label = st.selectbox(
            "Connector style",
            connector_labels,
            index=connector_labels.index(saved_connector),
            key=f"lshape_{self.plot_id}",
            help="Choose straight, smooth, or step-wise interpolation between observations.",
        )
        config["line_shape"] = _CONNECTOR_LABELS[str(connector_label)]

        dash_labels = list(_DASH_LABELS)
        saved_dash = _selected_label(_DASH_LABELS, saved_config.get("line_dash"), "Solid")
        dash_label = st.selectbox(
            "Line pattern",
            dash_labels,
            index=dash_labels.index(saved_dash),
            key=f"ldash_{self.plot_id}",
        )
        config["line_dash"] = _DASH_LABELS[str(dash_label)]
        config["line_width"] = float(
            st.number_input(
                "Line width",
                min_value=0.5,
                max_value=20.0,
                value=_bounded_saved_number(saved_config.get("line_width"), 0.5, 20.0, 2.0),
                step=0.5,
                key=f"lwidth_{self.plot_id}",
            )
        )

        config["show_markers"] = bool(
            st.checkbox(
                "Show point markers",
                value=bool(saved_config.get("show_markers", True)),
                key=f"lmarkers_{self.plot_id}",
            )
        )
        marker_symbols = list(LINE_MARKER_SYMBOLS)
        saved_symbol = str(saved_config.get("marker_symbol", "circle"))
        if saved_symbol not in LINE_MARKER_SYMBOLS:
            saved_symbol = "circle"
        config["marker_symbol"] = st.selectbox(
            "Marker symbol",
            marker_symbols,
            index=marker_symbols.index(saved_symbol),
            disabled=not config["show_markers"],
            key=f"lmarker_symbol_{self.plot_id}",
        )
        config["marker_size"] = int(
            st.number_input(
                "Marker size",
                min_value=1,
                max_value=50,
                value=int(_bounded_saved_number(saved_config.get("marker_size"), 1, 50, 6)),
                disabled=not config["show_markers"],
                key=f"lmarker_size_{self.plot_id}",
            )
        )
        config["connect_gaps"] = bool(
            st.checkbox(
                "Connect across missing values",
                value=bool(saved_config.get("connect_gaps", False)),
                key=f"lconnect_gaps_{self.plot_id}",
                help="Off leaves an honest visual break wherever the Y value is missing.",
            )
        )
        return config

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        """Produce line traces from data and config."""
        # [impl->req~ring5.plot.line~1]
        # [impl->req~ring5.figure.line-styles~1]
        x_col: str = config["x"]
        y_col: str = config["y"]

        # Sort by x-axis to ensure correct line drawing order
        if x_col in data.columns:
            data = data.sort_values(by=x_col)

        def _make_trace(
            grp_data: pd.DataFrame,
            group_name: str | None,
            sd_col: str | None,
        ) -> LineTraceConfig:
            line_shape = config.get("line_shape", "linear")
            line_dash = config.get("line_dash", "solid")
            marker_symbol = str(config.get("marker_symbol", "circle"))
            if line_shape not in LINE_SHAPES:
                raise ValueError(f"Unknown line connector style: {line_shape!r}.")
            if line_dash not in LINE_DASHES:
                raise ValueError(f"Unknown line pattern: {line_dash!r}.")
            if marker_symbol not in LINE_MARKER_SYMBOLS:
                raise ValueError(f"Unknown line marker symbol: {marker_symbol!r}.")
            return LineTraceConfig(
                name=str(group_name) if group_name is not None else y_col,
                x=grp_data[x_col].tolist(),
                y=grp_data[y_col].tolist(),
                line_width=float(config.get("line_width", 2.0)),
                line_dash=line_dash,
                show_markers=bool(config.get("show_markers", True)),
                line_shape=line_shape,
                marker_symbol=marker_symbol,
                marker_size=int(config.get("marker_size", 6)),
                connect_gaps=bool(config.get("connect_gaps", False)),
                error_y=grp_data[sd_col].tolist() if sd_col else None,
                custom_data={
                    "drilldown": build_drill_down_payload(
                        grp_data,
                        [x_col, *([str(config["color"])] if config.get("color") else [])],
                    )
                },
            )

        traces = build_color_grouped_traces(data, config, _make_trace)
        return TraceBuildResult(traces=traces)

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Get legend column for line plot."""
        result = config.get("color")
        return str(result) if result is not None else None
