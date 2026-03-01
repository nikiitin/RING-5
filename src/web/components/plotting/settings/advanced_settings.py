"""Advanced settings component — export, interactivity, annotations.

Extracted from ``BasePlot._section_advanced()`` and related methods as a
standalone component following the component-only architecture (P1, P9).

Plot-specific rendering (reference lines, shapes, engine controls) is
injected via optional callables so the component stays decoupled from
the ``BasePlot`` class hierarchy.

Usage::

    component = AdvancedSettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(
        saved_config,
        data=df,
        render_reference_line_fn=plot._render_reference_line_ui,
        render_shapes_fn=plot._render_shapes_ui,
        render_engine_fn=plot._render_engine_specific_controls,
    )
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd
import streamlit as st

from src.core.models.plot_config import ShapeConfig
from src.web.models.plot_models import PlotConfig


class ReferenceLineRenderer(Protocol):
    """Protocol for reference line UI renderers."""

    def __call__(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None,
        config: PlotConfig,
    ) -> None: ...


class ShapesRenderer(Protocol):
    """Protocol for shapes UI renderers."""

    def __call__(
        self,
        saved_config: PlotConfig,
    ) -> list[ShapeConfig]: ...


class EngineControlsRenderer(Protocol):
    """Protocol for engine-specific control renderers."""

    def __call__(
        self,
        saved_config: PlotConfig,
        config: PlotConfig,
    ) -> None: ...


class AdvancedSettingsComponent:
    """Render advanced settings (export, interactivity, annotations).

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
        render_reference_line_fn: ReferenceLineRenderer | None = None,
        render_shapes_fn: ShapesRenderer | None = None,
        render_engine_fn: EngineControlsRenderer | None = None,
    ) -> PlotConfig:
        """Render all advanced settings sections.

        Parameters
        ----------
        saved_config : PlotConfig
            Current saved configuration.
        data : pd.DataFrame | None
            Processed DataFrame (needed for reference line).
        render_reference_line_fn : callable | None
            Optional callback to render reference line UI.
        render_shapes_fn : callable | None
            Optional callback to render shapes/annotations UI.
        render_engine_fn : callable | None
            Optional callback for engine-specific controls.

        Returns
        -------
        PlotConfig
            Advanced configuration keys.
        """
        config: PlotConfig = {}

        # ── Export & Download ────────────────────────────────────
        st.markdown("#### Export & Download")
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            config["show_error_bars"] = st.checkbox(
                "Show Error Bars (if .sd columns exist)",
                value=saved_config.get("show_error_bars", False),
                key=f"error_bars_{self.plot_id}",
            )
        with col_exp2:
            download_formats: list[str] = ["html", "png", "pdf", "svg"]
            default_fmt_idx: int = 0
            if saved_config.get("download_format") in download_formats:
                default_fmt_idx = download_formats.index(saved_config["download_format"])
            config["download_format"] = st.selectbox(
                "Default Download Format",
                options=download_formats,
                index=default_fmt_idx,
                key=f"download_fmt_{self.plot_id}",
            )
            config["export_scale"] = st.selectbox(
                "Download Scale (Resolution)",
                options=[1, 2, 3],
                index=[1, 2, 3].index(saved_config.get("export_scale", 1)),
                key=f"exp_scale_{self.plot_id}",
                help="1x = Screen. 3x = High Res (Publication).",
            )
            w: int = saved_config.get("width", 800)
            h: int = saved_config.get("height", 500)
            s: int = config["export_scale"]
            st.caption(f"Download Size: {w * s} x {h * s} px")

        # ── Legend & Interactivity ───────────────────────────────
        st.markdown("#### Legend & Interactivity")
        config["enable_editable"] = st.checkbox(
            "Enable Interactive Editing",
            value=saved_config.get("enable_editable", False),
            key=f"editable_{self.plot_id}",
            help=(
                "Allows you to drag the legend/title and click"
                " to edit text directly on the plot."
            ),
        )

        # Preserve existing series styles
        if "series_styles" not in config:
            config["series_styles"] = saved_config.get("series_styles", {})

        # ── Reference Line ──────────────────────────────────────
        if render_reference_line_fn is not None:
            render_reference_line_fn(saved_config, data, config)

        # ── Annotations (Shapes) ────────────────────────────────
        if render_shapes_fn is not None:
            st.markdown("#### Annotations (Shapes)")
            config["shapes"] = render_shapes_fn(saved_config)

        # ── Engine-specific controls ────────────────────────────
        if render_engine_fn is not None:
            render_engine_fn(saved_config, config)

        return config
