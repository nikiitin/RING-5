"""Axes settings component — X-axis, Y-left, Y-right configuration.

Extracted from ``BasePlot._section_axes()`` and related methods as a
standalone component following the component-only architecture (P1, P9).

The component renders a nested pills navigation for X / Y-Left / Y-Right
axes. Plot-type-specific widgets (e.g. bar gap) and ordering controls are
injected via optional callables so the component stays decoupled from the
``BasePlot`` class hierarchy.

Usage::

    component = AxesSettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(
        saved_config,
        data=df,
        has_dual_axis=False,
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

        return config

    # ------------------------------------------------------------------
    # X-axis settings
    # ------------------------------------------------------------------

    def _render_x_axis_settings(self, saved_config: dict[str, Any], config: dict[str, Any]) -> None:
        """Render X-axis specific settings (tick angle, grid)."""
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
