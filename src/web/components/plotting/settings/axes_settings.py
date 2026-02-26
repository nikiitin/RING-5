"""Axes settings component — X-axis, Y-left, Y-right, Group Labels.

Extracted from ``BasePlot._section_axes()`` and related methods as a
standalone component following the component-only architecture (P1, P9).

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

from typing import Any, Protocol

import pandas as pd
import streamlit as st


class SpecificOptionsRenderer(Protocol):
    """Protocol for plot-type-specific advanced option renderers."""

    def __call__(
        self,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None,
    ) -> dict[str, Any]: ...


class OrderingRenderer(Protocol):
    """Protocol for ordering-UI renderers."""

    def __call__(
        self,
        saved_config: dict[str, Any],
        data: pd.DataFrame,
        config: dict[str, Any],
    ) -> None: ...


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
        saved_config: dict[str, Any],
        data: pd.DataFrame | None = None,
        has_dual_axis: bool = False,
        show_group_labels: bool = False,
        render_specific_fn: SpecificOptionsRenderer | None = None,
        render_ordering_fn: OrderingRenderer | None = None,
    ) -> dict[str, Any]:
        """Render axis pills navigation and settings.

        Parameters
        ----------
        saved_config : dict[str, Any]
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
            ``(saved_config, data) -> dict[str, Any]``.
        render_ordering_fn : callable | None
            Optional callback for ordering/rename controls.
            Signature: ``(saved_config, data, config) -> None``.

        Returns
        -------
        dict[str, Any]
            Axis configuration keys.
        """
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

        config: dict[str, Any] = {}

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
        elif axis_tab == "group":
            self._render_group_labels_settings(saved_config, config)

        return config

    # ------------------------------------------------------------------
    # X-axis settings
    # ------------------------------------------------------------------

    def _render_x_axis_settings(self, saved_config: dict[str, Any], config: dict[str, Any]) -> None:
        """Render X-axis specific settings (tick angle, grid, tick marks)."""
        st.markdown("#### X-Axis Settings")
        config["show_x_grid"] = st.checkbox(
            "Show Grid",
            value=saved_config.get("show_x_grid", True),
            key=f"show_x_grid_{self.plot_id}",
        )
        config["xaxis_tickangle"] = st.slider(
            "X-axis Label Rotation",
            min_value=-90,
            max_value=90,
            value=saved_config.get("xaxis_tickangle", -45),
            step=15,
            key=f"xaxis_angle_{self.plot_id}",
            help="Rotate X-axis labels to prevent overlap",
        )

        # ── Tick marks ──────────────────────────────────────────
        st.markdown("**Tick Marks & Grid**")
        show_xtick_marks = st.checkbox(
            "Show X-Axis Tick Marks",
            value=saved_config.get("show_xtick_marks", True),
            key=f"x_show_ticks_{self.plot_id}",
        )
        config["show_xtick_marks"] = show_xtick_marks

        dash_options = [
            "solid",
            "dot",
            "dash",
            "longdash",
            "dashdot",
            "longdashdot",
        ]
        xtick_dash_idx = 0
        if saved_config.get("xtick_dash", "solid") in dash_options:
            xtick_dash_idx = dash_options.index(saved_config.get("xtick_dash", "solid"))

        xtick_dash: str = "solid"
        if show_xtick_marks:
            xtick_dash = (
                st.selectbox(
                    "X-Axis Grid Dash Style",
                    options=dash_options,
                    index=xtick_dash_idx,
                    key=f"x_tickdash_{self.plot_id}",
                )
                or "solid"
            )
        config["xtick_dash"] = xtick_dash

        config["xtick_pad"] = st.number_input(
            "X-Axis Tick Label Distance (px)",
            min_value=0.0,
            max_value=100.0,
            value=float(saved_config.get("xtick_pad", 5.0)),
            step=1.0,
            key=f"xtick_pad_{self.plot_id}",
            help="Distance between X-axis tick marks and their labels.",
        )

    # ------------------------------------------------------------------
    # Y-axis settings
    # ------------------------------------------------------------------

    def _render_y_axis_settings(
        self,
        saved_config: dict[str, Any],
        config: dict[str, Any],
        prefix: str,
    ) -> None:
        """Render Y-axis settings for left or right axis.

        Parameters
        ----------
        saved_config : dict[str, Any]
            Previously saved configuration.
        config : dict[str, Any]
            Current configuration to update.
        prefix : str
            Empty string for left axis, ``"y2"`` for right axis.
        """
        label = "Y-Left Axis" if not prefix else "Y-Right Axis"
        st.markdown(f"#### {label} Settings")

        grid_key = f"{prefix}show_y_grid" if prefix else "show_y_grid"
        config[grid_key] = st.checkbox(
            "Show Grid",
            value=saved_config.get(grid_key, True if not prefix else False),
            key=f"{prefix}show_y_grid_{self.plot_id}",
        )

        dtick_key = f"{prefix}yaxis_dtick" if prefix else "yaxis_dtick"
        dtick: float = st.number_input(
            f"{label} Step Size (0 for auto)",
            min_value=0.0,
            value=float(saved_config.get(dtick_key) or 0.0),
            key=f"{prefix}ydtick_{self.plot_id}",
        )
        if dtick > 0:
            config[dtick_key] = dtick

        # ── Tick marks ──────────────────────────────────────────
        st.markdown("**Tick Marks & Grid**")
        show_ytick_marks = st.checkbox(
            "Show Y-Axis Tick Marks",
            value=saved_config.get("show_ytick_marks", True),
            key=f"{prefix}y_show_ticks_{self.plot_id}",
        )
        config["show_ytick_marks"] = show_ytick_marks

        dash_options = [
            "solid",
            "dot",
            "dash",
            "longdash",
            "dashdot",
            "longdashdot",
        ]
        ytick_dash_idx = 0
        if saved_config.get("ytick_dash", "solid") in dash_options:
            ytick_dash_idx = dash_options.index(saved_config.get("ytick_dash", "solid"))

        ytick_dash: str = "solid"
        if show_ytick_marks:
            ytick_dash = (
                st.selectbox(
                    "Y-Axis Grid Dash Style",
                    options=dash_options,
                    index=ytick_dash_idx,
                    key=f"{prefix}y_tickdash_{self.plot_id}",
                )
                or "solid"
            )
        config["ytick_dash"] = ytick_dash

        # ── Y-axis title position ───────────────────────────────
        st.markdown("**Title Position**")
        config["yaxis_title_standoff"] = st.slider(
            "Y-Axis Title Standoff (Spacing)",
            min_value=-1,
            max_value=200,
            value=saved_config.get("yaxis_title_standoff", -1),
            key=f"{prefix}yaxis_title_standoff_{self.plot_id}",
            help=("Distance between Y-axis ticks and the title. " "-1 = auto (engine default)."),
        )

        config["yaxis_title_vshift"] = st.slider(
            "Y-Axis Title Vertical Shift",
            min_value=-500,
            max_value=500,
            value=saved_config.get("yaxis_title_vshift", 0),
            key=f"{prefix}yaxis_title_vshift_{self.plot_id}",
            help=(
                "Move title up (+) or down (-) along"
                " the axis. Matplotlib only — Plotly uses"
                " standoff. Note: Disables native"
                " auto-margins for title."
            ),
        )

    # ------------------------------------------------------------------
    # Group labels settings (separate pill for grouped stacked bar)
    # ------------------------------------------------------------------

    def _render_group_labels_settings(
        self, saved_config: dict[str, Any], config: dict[str, Any]
    ) -> None:
        """Render group label controls (for grouped stacked bar)."""
        st.markdown("#### Group Labels")
        config["major_label_offset"] = st.number_input(
            "Label-to-Axis Distance",
            min_value=-1.0,
            max_value=0.0,
            value=float(saved_config.get("major_label_offset", -0.15)),
            step=0.01,
            format="%.2f",
            key=f"grp_lbl_dist_{self.plot_id}",
            help=(
                "Vertical distance between major group labels "
                "and the X-axis. More negative = farther below."
            ),
        )
        config["group_label_alternate"] = st.checkbox(
            "Alternate Group Labels (up/down)",
            value=saved_config.get("group_label_alternate", True),
            key=f"grp_alt_{self.plot_id}",
            help="Stagger group labels to avoid overlap.",
        )
        config["group_label_alt_spacing"] = st.number_input(
            "Alt. Label Row Spacing",
            min_value=0.0,
            max_value=0.5,
            value=float(saved_config.get("group_label_alt_spacing", 0.05)),
            step=0.01,
            key=f"grp_alt_sp_{self.plot_id}",
            help="Vertical distance between alternating label rows.",
        )
