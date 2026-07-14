"""Stacked bar plot implementation."""

from typing import Any, override

import pandas as pd

from src.core.common.safe_format import safe_format_number
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.web.components.plotting.config import stacked_bar_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.types._trace_helpers import (
    extract_error_bars,
    prepare_categorical_data,
)


class StackedBarPlot(BasePlot):
    """Stacked bar plot with support for multiple stacked statistics."""

    def __init__(self, plot_id: int, name: str):
        """Initialize stacked bar plot."""
        super().__init__(plot_id, name, "stacked_bar")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render configuration UI for stacked bar plot."""
        return stacked_bar_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        """Create stacked bar trace configurations."""
        x_col = config.get("x")
        y_cols = config.get("y_columns", [])

        if not x_col or not y_cols:
            return TraceBuildResult(traces=[], barmode="stack")

        # Prepare data
        data = self._prepare_data(data, x_col, y_cols, config)

        # Define hover template
        hover_template = self._get_hover_template()

        # Build traces
        traces = self._create_stacked_traces(data, x_col, y_cols, config, hover_template)

        # Build annotations
        layout_annotations: list[dict[str, Any]] = []
        if config.get("show_totals"):
            layout_annotations = self._build_totals_annotations(data, x_col, config)

        return TraceBuildResult(
            traces=traces,
            barmode="stack",
            layout_annotations=layout_annotations,
        )

    def _prepare_data(
        self, data: pd.DataFrame, x_col: str, y_cols: list[str], config: PlotConfig
    ) -> pd.DataFrame:
        """Prepare data: apply filters, calculate totals, convert types."""
        data = prepare_categorical_data(data, [x_col])

        # Apply X Filter
        if config.get("x_filter") is not None:
            data = data[data[x_col].isin(config["x_filter"])]

        # Calculate Total for each row
        data["__total"] = data[y_cols].sum(axis=1)

        return data

    def _get_hover_template(self) -> str:
        """Get standard hover template."""
        return (
            "<b>%{x}</b><br>"
            "Value: %{y:.4f}<br>"
            "<b>Total: %{customdata:.4f}</b>"
            "<extra></extra>"
        )

    def _create_stacked_traces(
        self,
        data: pd.DataFrame,
        x_col: str,
        y_cols: list[str],
        config: PlotConfig,
        hover_template: str,
    ) -> list[BarTraceConfig]:
        """Build list of bar traces for stacked bars."""
        traces: list[BarTraceConfig] = []
        for y_col in y_cols:
            trace = self._build_bar_trace(data, y_col, x_col, None, hover_template, config)
            traces.append(trace)
        return traces

    def _build_bar_trace(
        self,
        data: pd.DataFrame,
        y_col: str,
        x_col: str,
        bar_width: float | None,
        hover_template: str,
        config: PlotConfig,
    ) -> BarTraceConfig:
        """Build a single BarTraceConfig for a stacked series."""
        sd_col = extract_error_bars(data, y_col, config)
        error_y_vals: list[float] | None = data[sd_col].tolist() if sd_col else None

        # Get series styling configuration
        series_styles = config.get("series_styles", {})
        style = series_styles.get(y_col, {})

        # Use custom name if defined, otherwise use y_col
        trace_name = style.get("name", y_col)

        # Only use per-series color when explicitly enabled via use_color;
        # otherwise let the palette mechanism assign colors.
        color = style.get("color", "") if style.get("use_color") else ""
        pattern = style.get("pattern", "")

        # Detect pre-computed numeric coordinates (e.g. __x_coord from
        # GroupedBarUtils) — store them as x_positions so the matplotlib
        # renderer uses the actual coordinates instead of integer indices.
        x_values = data[x_col].tolist()
        is_numeric_coords = bool(x_values) and isinstance(x_values[0], (int, float))
        x_positions: list[float] = [float(v) for v in x_values] if is_numeric_coords else []

        return BarTraceConfig(
            name=trace_name,
            x=x_values,
            x_positions=x_positions,
            y=data[y_col].tolist(),
            bar_width=bar_width if bar_width is not None else 0.8,
            color=color,
            pattern=pattern,
            error_y=error_y_vals,
            custom_data={
                "customdata": data["__total"].tolist(),
                "hovertemplate": hover_template,
            },
        )

    def _build_totals_annotations(
        self, data: pd.DataFrame, x_col: str, config: PlotConfig
    ) -> list[dict[str, Any]]:
        """Build annotations for stack totals."""
        total_fmt = config.get("net_total_format", ".2f")
        font_size = config.get("total_font_size", 12)
        font_color = config.get("total_font_color", "#000000")
        position_option = config.get("total_position", "Outside")
        anchor_option = config.get("total_anchor", "End")
        offset = config.get("total_offset", 0)
        rotation = config.get("total_rotation", 0)
        threshold = config.get("total_threshold", 0.0)

        def fmt_val(val: float) -> str:
            return safe_format_number(val, total_fmt)

        annotations = []
        for total_val, x_pos in zip(data["__total"], data[x_col], strict=False):
            val = float(total_val)

            if val <= threshold:
                continue
            y_pos, yanchor = self._get_total_position(val, position_option, anchor_option)

            annotations.append(
                dict(
                    x=x_pos,
                    y=y_pos,
                    xref="x",
                    yref="y",
                    text=fmt_val(val),
                    showarrow=False,
                    font=dict(size=font_size, color=font_color),
                    yanchor=yanchor,
                    yshift=offset,
                    textangle=rotation,
                )
            )

        return annotations

    def _get_total_position(
        self, val: float, position_option: str, anchor_option: str
    ) -> tuple[float, str]:
        """Calculate Y position and anchor for total annotation."""
        if position_option == "Outside":
            return val, "bottom"
        elif position_option == "Inside":
            if anchor_option == "End":
                return val, "top"
            elif anchor_option == "Middle":
                return val / 2, "middle"
            elif anchor_option == "Start":
                return 0, "bottom"
        return val, "bottom"

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Get legend column for stacked bar plot."""
        return None
