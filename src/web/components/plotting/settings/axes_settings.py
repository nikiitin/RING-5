"""Axes settings component — X, Y-left, Y-right and group-label placement.

The component renders a nested pills navigation for X / Y-Left / Y-Right
axes, plus a conditional Group Labels pill for grouped stacked bar plots.
Plot-type-specific widgets (e.g. bar gap) and ordering controls are
injected via optional callables so the component stays decoupled from the
``BasePlot`` class hierarchy.

Usage::

    component = AxesSettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(
        saved_config,
        data=df,
        has_dual_axis=False,
        show_group_labels=False,
        render_specific_fn=plot.render_specific_advanced_options,
        render_ordering_fn=plot._render_ordering_ui,
    )
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd
import streamlit as st

from src.core.common.numbered_axis import NUMBERED_AXIS_MODES, numbered_axis_modes
from src.web.components.plotting.settings.widget_factory import (
    color_picker,
    numeric_input,
    select_option,
    slider,
    toggle,
)
from src.web.models.plot_models import PlotConfig

_DASH_OPTIONS: list[str] = [
    "solid",
    "dot",
    "dash",
    "longdash",
    "dashdot",
    "longdashdot",
]


_RIGHT_AXIS_KEYS = {
    "show_y_grid": "y2show_y_grid",
    "y_grid_color": "y2_grid_color",
    "y_grid_width": "y2_grid_width",
    "y_grid_dash": "y2_grid_dash",
    "y_grid_alpha": "y2_grid_alpha",
    "yaxis_tickangle": "yaxis2_tickangle",
    "yaxis_dtick": "yaxis2_dtick",
    "show_ytick_marks": "show_y2tick_marks",
    "yaxis_tick_side": "yaxis2_tick_side",
    "ytick_dash": "y2tick_dash",
    "yaxis_title_standoff": "yaxis2_title_standoff",
    "yaxis_title_vshift": "yaxis2_title_vshift",
    "y_axis_line_width": "y2_axis_line_width",
    "y_axis_line_color": "y2_axis_line_color",
}


class SpecificOptionsRenderer(Protocol):
    """Protocol for plot-type-specific advanced option renderers."""

    def __call__(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None,
    ) -> PlotConfig:
        """Render plot-specific options and return the updated configuration."""
        raise NotImplementedError


class OrderingRenderer(Protocol):
    """Protocol for ordering-UI renderers."""

    def __call__(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame,
        config: PlotConfig,
    ) -> None:
        """Render ordering controls into ``config``."""
        raise NotImplementedError


class AxesSettingsComponent:
    """Render axis configuration with pills navigation.

    Parameters
    ----------
    plot_id : int
        Unique plot identifier for Streamlit widget keys.
    plot_type : str
        Plot type identifier.
    """

    def __init__(self, plot_id: int, plot_type: str) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None = None,
        has_dual_axis: bool = False,
        show_group_labels: bool = False,
        render_specific_fn: SpecificOptionsRenderer | None = None,
        render_ordering_fn: OrderingRenderer | None = None,
    ) -> PlotConfig:
        """Render axis pills navigation and settings.

        Parameters
        ----------
        saved_config : PlotConfig
            Current saved configuration.
        data : pd.DataFrame | None
            Processed DataFrame (needed for ordering controls).
        has_dual_axis : bool
            Whether to show a Y-Right pill.
        show_group_labels : bool
            Whether to show a Group Labels pill (grouped stacked bar).
        render_specific_fn : callable | None
            Optional callback for plot-type-specific widgets
            (e.g. bar gap, bar group gap). Signature:
            ``(saved_config, data) -> PlotConfig``.
        render_ordering_fn : callable | None
            Optional callback for ordering/rename controls.
            Signature: ``(saved_config, data, config) -> None``.

        Returns
        -------
        PlotConfig
            Axis configuration keys.
        """
        # [impl->req~ring5.figure.axes~1]
        _axis_labels: dict[str, str] = {
            "x": ":material/straighten: X-Axis",
            "y_left": ":material/straighten: Y-Left",
        }
        if has_dual_axis:
            _axis_labels["y_right"] = ":material/straighten: Y-Right"
        if show_group_labels:
            _axis_labels["group"] = ":material/label: Group Labels"

        axis_tab: str | None = st.pills(
            "Axis",
            options=list(_axis_labels.keys()),
            format_func=lambda x: _axis_labels.get(x, str(x)),
            selection_mode="single",
            key=f"axis_nav_{self.plot_id}",
            default="x",
        )

        config: PlotConfig = {}

        if axis_tab == "x" or axis_tab is None:
            self._render_x_axis_settings(saved_config, config)
            # Plot-type-specific options (e.g. bar gap)
            if render_specific_fn is not None:
                specific = render_specific_fn(saved_config, data)
                config.update(specific)
            # Ordering controls (reorder + rename)
            if render_ordering_fn is not None and data is not None:
                render_ordering_fn(saved_config, data, config)
        elif axis_tab == "y_left":
            self._render_y_axis_settings(saved_config, config, prefix="")
        elif axis_tab == "y_right":
            self._render_y_axis_settings(saved_config, config, prefix="y2")
            if (
                self.plot_type == "grouped_stacked_bar"
                and saved_config.get("right_axis_type") == "dots"
            ):
                from src.web.components.plotting.config.dual_axis_settings import (
                    render_right_axis_dot_settings,
                )

                render_right_axis_dot_settings(saved_config, config, self.plot_id)
        elif axis_tab == "group":
            self._render_group_labels_settings(saved_config, config)

        return config

    # X-axis settings

    def _render_x_axis_settings(self, saved_config: PlotConfig, config: PlotConfig) -> None:
        """Render X-axis specific settings (tick angle, grid, tick marks)."""
        st.markdown("#### X-Axis Settings")
        config["show_x_grid"] = toggle(
            "Show Grid",
            saved_config,
            "show_x_grid",
            self.plot_id,
        )
        if config["show_x_grid"]:
            st.markdown("**Grid Styling**")
            _xgc1, _xgc2 = st.columns(2)
            with _xgc1:
                config["x_grid_color"] = color_picker(
                    "X Grid Color",
                    saved_config,
                    "x_grid_color",
                    self.plot_id,
                    widget_key=f"x_grid_color_{self.plot_id}",
                    default="#e5e5e5",
                )
            with _xgc2:
                config["x_grid_width"] = numeric_input(
                    "X Grid Width (px)",
                    saved_config,
                    "x_grid_width",
                    self.plot_id,
                    widget_key=f"x_grid_width_{self.plot_id}",
                    default=1.0,
                    min_value=0.1,
                    max_value=10.0,
                    step=0.5,
                )
            _xgc3, _xgc4 = st.columns(2)
            with _xgc3:
                config["x_grid_dash"] = select_option(
                    "X Grid Dash Style",
                    _DASH_OPTIONS,
                    saved_config,
                    "x_grid_dash",
                    self.plot_id,
                    widget_key=f"x_grid_dash_{self.plot_id}",
                    default="solid",
                )
            with _xgc4:
                config["x_grid_alpha"] = slider(
                    "X Grid Opacity",
                    saved_config,
                    "x_grid_alpha",
                    self.plot_id,
                    widget_key=f"x_grid_alpha_{self.plot_id}",
                    default=1.0,
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                    help="0 = fully transparent, 1 = fully opaque",
                )
        config["xaxis_tickangle"] = slider(
            "X-axis Label Rotation",
            saved_config,
            "xaxis_tickangle",
            self.plot_id,
            widget_key=f"xaxis_angle_{self.plot_id}",
            default=-45,
            min_value=-90,
            max_value=90,
            step=15,
            help="Rotate X-axis labels to prevent overlap",
        )

        # Tick marks
        st.markdown("**Tick Marks & Grid**")
        show_xtick_marks = toggle(
            "Show X-Axis Tick Marks",
            saved_config,
            "show_xtick_marks",
            self.plot_id,
            widget_key=f"x_show_ticks_{self.plot_id}",
        )
        config["show_xtick_marks"] = show_xtick_marks

        config["xaxis_tick_side"] = select_option(
            "X-Axis Tick Side",
            ["bottom", "top"],
            saved_config,
            "xaxis_tick_side",
            self.plot_id,
            widget_key=f"x_tick_side_{self.plot_id}",
            default="bottom",
        )

        xtick_dash: str = "solid"
        if show_xtick_marks:
            xtick_dash = select_option(
                "X-Axis Tick Dash Style",
                _DASH_OPTIONS,
                saved_config,
                "xtick_dash",
                self.plot_id,
                widget_key=f"x_tickdash_{self.plot_id}",
                default="solid",
            )
        config["xtick_dash"] = xtick_dash

        config["xtick_pad"] = numeric_input(
            "X-Axis Tick Label Distance (px)",
            saved_config,
            "xtick_pad",
            self.plot_id,
            default=5.0,
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            help="Distance between X-axis tick marks and their labels.",
        )

        # Axis Lines
        st.markdown("**Axis Lines**")
        al_col1, al_col2 = st.columns(2)
        with al_col1:
            config["x_axis_line_width"] = numeric_input(
                "Bottom Axis Line Width (px)",
                saved_config,
                "x_axis_line_width",
                self.plot_id,
                default=1.0,
                min_value=0.0,
                max_value=10.0,
                step=0.5,
                help="Width of the bottom X-axis border line. 0 = hidden.",
            )
        with al_col2:
            config["x_axis_line_color"] = color_picker(
                "Bottom Axis Line Color",
                saved_config,
                "x_axis_line_color",
                self.plot_id,
                default="#444444",
            )

        al_col3, al_col4 = st.columns(2)
        with al_col3:
            config["top_axis_line_width"] = numeric_input(
                "Top Axis Line Width (px)",
                saved_config,
                "top_axis_line_width",
                self.plot_id,
                default=0.0,
                min_value=0.0,
                max_value=10.0,
                step=0.5,
                help="Width of the top axis border line. 0 = hidden.",
            )
        with al_col4:
            config["top_axis_line_color"] = color_picker(
                "Top Axis Line Color",
                saved_config,
                "top_axis_line_color",
                self.plot_id,
                default="#444444",
            )

        if self.plot_type == "grouped_stacked_bar":
            modes = st.pills(
                "Numbered X-Axis",
                options=list(NUMBERED_AXIS_MODES),
                default=numbered_axis_modes(saved_config) or [],
                selection_mode="multi",
                key=f"numbered_modes_{self.plot_id}",
            )
            config["numbered_xaxis_modes"] = numbered_axis_modes(
                {"numbered_xaxis_modes": [] if modes is None else modes}
            )

    # Y-axis settings

    def _render_y_axis_settings(
        self,
        saved_config: PlotConfig,
        config: PlotConfig,
        prefix: str,
    ) -> None:
        """Render Y-axis settings for left or right axis.

        Parameters
        ----------
        saved_config : PlotConfig
            Previously saved configuration.
        config : PlotConfig
            Current configuration to update.
        prefix : str
            Empty string for left axis, ``"y2"`` for right axis.
        """

        def axis_key(primary: str) -> str:
            return _RIGHT_AXIS_KEYS[primary] if prefix else primary

        label = "Y-Left Axis" if not prefix else "Y-Right Axis"
        st.markdown(f"#### {label} Settings")

        grid_key = axis_key("show_y_grid")
        config[grid_key] = toggle(
            "Show Grid",
            saved_config,
            grid_key,
            self.plot_id,
            widget_key=f"{prefix}show_y_grid_{self.plot_id}",
            default=True if not prefix else False,
        )
        if config[grid_key]:
            st.markdown("**Grid Styling**")
            _ygrid_color_key = axis_key("y_grid_color")
            _ygrid_width_key = axis_key("y_grid_width")
            _ygrid_dash_key = axis_key("y_grid_dash")
            _ygrid_alpha_key = axis_key("y_grid_alpha")
            _ygc1, _ygc2 = st.columns(2)
            with _ygc1:
                config[_ygrid_color_key] = color_picker(
                    f"{label} Grid Color",
                    saved_config,
                    _ygrid_color_key,
                    self.plot_id,
                    widget_key=f"{prefix}y_grid_color_{self.plot_id}",
                    default="#e5e5e5",
                )
            with _ygc2:
                config[_ygrid_width_key] = numeric_input(
                    f"{label} Grid Width (px)",
                    saved_config,
                    _ygrid_width_key,
                    self.plot_id,
                    widget_key=f"{prefix}y_grid_width_{self.plot_id}",
                    default=1.0,
                    min_value=0.1,
                    max_value=10.0,
                    step=0.5,
                )
            _ygc3, _ygc4 = st.columns(2)
            with _ygc3:
                config[_ygrid_dash_key] = select_option(
                    f"{label} Grid Dash Style",
                    _DASH_OPTIONS,
                    saved_config,
                    _ygrid_dash_key,
                    self.plot_id,
                    widget_key=f"{prefix}y_grid_dash_{self.plot_id}",
                    default="solid",
                )
            with _ygc4:
                config[_ygrid_alpha_key] = slider(
                    f"{label} Grid Opacity",
                    saved_config,
                    _ygrid_alpha_key,
                    self.plot_id,
                    widget_key=f"{prefix}y_grid_alpha_{self.plot_id}",
                    default=1.0,
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                    help="0 = fully transparent, 1 = fully opaque",
                )

        config[axis_key("yaxis_tickangle")] = slider(
            "Y-axis Label Rotation",
            saved_config,
            axis_key("yaxis_tickangle"),
            self.plot_id,
            widget_key=f"{prefix}yaxis_angle_{self.plot_id}",
            default=0,
            min_value=-90,
            max_value=90,
            step=15,
            help="Rotate Y-axis labels",
        )

        dtick_key = axis_key("yaxis_dtick")
        dtick: float = st.number_input(
            f"{label} Step Size (0 for auto)",
            min_value=0.0,
            value=float(saved_config.get(dtick_key) or 0.0),
            key=f"{prefix}ydtick_{self.plot_id}",
        )
        config[dtick_key] = dtick if dtick > 0 else None

        # Tick marks
        st.markdown("**Tick Marks & Grid**")
        show_ytick_marks = toggle(
            "Show Y-Axis Tick Marks",
            saved_config,
            axis_key("show_ytick_marks"),
            self.plot_id,
            widget_key=f"{prefix}y_show_ticks_{self.plot_id}",
            default=True,
        )
        config[axis_key("show_ytick_marks")] = show_ytick_marks

        config[axis_key("yaxis_tick_side")] = select_option(
            "Y-Axis Tick Side",
            ["left", "right"],
            saved_config,
            axis_key("yaxis_tick_side"),
            self.plot_id,
            widget_key=f"{prefix}y_tick_side_{self.plot_id}",
            default="right" if prefix else "left",
        )

        ytick_dash: str = "solid"
        if show_ytick_marks:
            ytick_dash = select_option(
                "Y-Axis Tick Dash Style",
                _DASH_OPTIONS,
                saved_config,
                axis_key("ytick_dash"),
                self.plot_id,
                widget_key=f"{prefix}y_tickdash_{self.plot_id}",
                default="solid",
            )
        config[axis_key("ytick_dash")] = ytick_dash

        # Y-axis title position
        st.markdown("**Title Position**")
        config[axis_key("yaxis_title_standoff")] = slider(
            "Y-Axis Title Standoff (Spacing)",
            saved_config,
            axis_key("yaxis_title_standoff"),
            self.plot_id,
            widget_key=f"{prefix}yaxis_title_standoff_{self.plot_id}",
            default=-1,
            min_value=-1,
            max_value=200,
            help="Distance between Y-axis ticks and the title. -1 = auto (engine default).",
        )

        config[axis_key("yaxis_title_vshift")] = slider(
            "Y-Axis Title Vertical Shift",
            saved_config,
            axis_key("yaxis_title_vshift"),
            self.plot_id,
            widget_key=f"{prefix}yaxis_title_vshift_{self.plot_id}",
            default=0,
            min_value=-500,
            max_value=500,
            help=(
                "Move title up (+) or down (-) along"
                " the axis. Matplotlib only — Plotly uses"
                " standoff. Note: Disables native"
                " auto-margins for title."
            ),
        )

        # Axis Lines
        st.markdown("**Axis Lines**")
        width_key = axis_key("y_axis_line_width")
        color_key = axis_key("y_axis_line_color")

        al_col1, al_col2 = st.columns(2)
        with al_col1:
            config[width_key] = numeric_input(
                f"{label} Line Width (px)",
                saved_config,
                width_key,
                self.plot_id,
                widget_key=f"{prefix}y_axis_line_width_{self.plot_id}",
                default=1.0,
                min_value=0.0,
                max_value=10.0,
                step=0.5,
                help=f"Width of the {label.lower()} border line. 0 = hidden.",
            )
        with al_col2:
            config[color_key] = color_picker(
                f"{label} Line Color",
                saved_config,
                color_key,
                self.plot_id,
                widget_key=f"{prefix}y_axis_line_color_{self.plot_id}",
                default="#444444",
            )

        # Opposite (right) axis line — only for primary Y-axis
        if not prefix:
            al_col3, al_col4 = st.columns(2)
            with al_col3:
                config["right_axis_line_width"] = numeric_input(
                    "Right Axis Line Width (px)",
                    saved_config,
                    "right_axis_line_width",
                    self.plot_id,
                    default=0.0,
                    min_value=0.0,
                    max_value=10.0,
                    step=0.5,
                    help="Width of the right axis border line. 0 = hidden.",
                )
            with al_col4:
                config["right_axis_line_color"] = color_picker(
                    "Right Axis Line Color",
                    saved_config,
                    "right_axis_line_color",
                    self.plot_id,
                    default="#444444",
                )

    # Group labels settings (separate pill for grouped stacked bar)

    def _render_group_labels_settings(self, saved_config: PlotConfig, config: PlotConfig) -> None:
        """Render group label controls (for grouped stacked bar)."""
        st.markdown("#### Group Labels")
        config["major_label_offset"] = numeric_input(
            "Label-to-Axis Distance",
            saved_config,
            "major_label_offset",
            self.plot_id,
            widget_key=f"grp_lbl_dist_{self.plot_id}",
            default=-0.15,
            min_value=-1.0,
            max_value=0.0,
            step=0.01,
            format="%.2f",
            help=(
                "Vertical distance between major group labels "
                "and the X-axis. More negative = farther below."
            ),
        )
        config["group_label_offset"] = config["major_label_offset"]
        config["group_label_alternate"] = toggle(
            "Alternate Group Labels (up/down)",
            saved_config,
            "group_label_alternate",
            self.plot_id,
            widget_key=f"grp_alt_{self.plot_id}",
            default=True,
            help="Stagger group labels to avoid overlap.",
        )
        config["group_label_alt_spacing"] = numeric_input(
            "Alt. Label Row Spacing",
            saved_config,
            "group_label_alt_spacing",
            self.plot_id,
            widget_key=f"grp_alt_sp_{self.plot_id}",
            default=0.05,
            min_value=0.0,
            max_value=0.5,
            step=0.01,
            help="Vertical distance between alternating label rows.",
        )
