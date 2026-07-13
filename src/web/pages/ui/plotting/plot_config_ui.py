"""Mixin for plot configuration UI rendering.

Extracted from BasePlot to separate UI rendering concerns from
core plot lifecycle (figure generation, serialization, etc.).

All methods that render Streamlit widgets for plot configuration
live here. The mixin expects ``self.plot_id``, ``self.plot_type``,
``self.config``, ``self.processed_data``, and ``self._style_ui``
to be provided by the host class (BasePlot).
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from src.core.models.plot_config import ShapeConfig
from src.web.components.plotting.settings import (
    AdvancedSettingsComponent,
    AxesSettingsComponent,
    ColorsSettingsComponent,
    DataLabelsSettingsComponent,
    LayoutSettingsComponent,
    LegendSettingsComponent,
    TypographySettingsComponent,
)
from src.web.models.plot_models import PlotConfig

if TYPE_CHECKING:
    from src.web.pages.ui.plotting.styles import BaseStyleUI


class PlotConfigUIMixin:
    """Mixin providing all plot configuration UI rendering methods.

    Concrete plot types inherit this via ``BasePlot`` which provides
    the instance attributes referenced by these methods:

    - ``self.plot_id: int``
    - ``self.plot_type: str``
    - ``self.config: PlotConfig``
    - ``self.processed_data: pd.DataFrame | None``
    - ``self._style_ui: BaseStyleUI``
    """

    # Declare expected attributes for type checking
    plot_id: int
    plot_type: str
    config: PlotConfig
    processed_data: pd.DataFrame | None
    _style_ui: BaseStyleUI

    @abstractmethod
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render the configuration UI for this plot type.

        Args:
            data: The processed data to plot
            saved_config: Previously saved configuration

        Returns:
            Current configuration dictionary
        """

    def render_display_options(self, saved_config: PlotConfig) -> PlotConfig:
        """Render sizing and layout options via LayoutSettingsComponent."""
        component = LayoutSettingsComponent(self.plot_id, self.plot_type)
        return component.render(saved_config)

    def render_theme_options(
        self, saved_config: PlotConfig, items: list[str] | None = None
    ) -> PlotConfig:
        """Render theme/style options via the style UI strategy."""
        return self._style_ui.render_style_ui(
            saved_config, self.processed_data, items=items, key_prefix="theme_"
        )

    def _supports_secondary_legend(self) -> bool:
        """Whether this plot type supports a secondary legend pill.

        Override in subclasses that offer secondary legend features
        independently of dual-axis mode (e.g. numbered X-axis legend).
        """
        return False

    def _supports_tertiary_legend(self) -> bool:
        """Whether this plot type supports a tertiary legend pill.

        Override in subclasses that offer a third level of legend
        (e.g. numbered X-axis annotations when dual-axis is also active).
        Only show tertiary when the plot actually has three legend levels.
        """
        return False

    # ------------------------------------------------------------------
    # Pills-driven section dispatcher
    # ------------------------------------------------------------------

    def render_settings_section(
        self,
        section: str | None,
        saved_config: PlotConfig,
        data: pd.DataFrame | None = None,
    ) -> PlotConfig:
        """Render UI for a single settings section selected via pills.

        Args:
            section: The key returned by ``render_settings_pills``
                (``None`` when nothing is selected).
            saved_config: Current configuration dictionary.
            data: Processed data for data-dependent widgets.

        Returns:
            Configuration dictionary produced by the selected section.
        """
        if section is None:
            return {}

        if section == "layout":
            return LayoutSettingsComponent(self.plot_id, self.plot_type).render(saved_config)

        if section == "typography":
            return TypographySettingsComponent(self.plot_id, self.plot_type).render(
                saved_config, key_prefix="theme_"
            )

        if section == "legends":
            has_dual_axis: bool = self.plot_type == "dual_axis_bar_dot" or bool(
                saved_config.get("dual_axis")
            )
            has_secondary: bool = has_dual_axis or self._supports_secondary_legend()
            has_tertiary: bool = (
                self._supports_tertiary_legend()
                and has_dual_axis
                and bool(
                    saved_config.get("show_group_labels")
                    or "Number legend" in saved_config.get("numbered_xaxis_modes", [])
                    or saved_config.get("numbered_xaxis")
                )
            )
            return LegendSettingsComponent(self.plot_id, self.plot_type).render(
                saved_config,
                has_secondary=has_secondary,
                has_tertiary=has_tertiary,
            )

        if section == "axes":
            has_dual_axis = self.plot_type == "dual_axis_bar_dot" or bool(
                saved_config.get("dual_axis")
            )
            show_group_labels: bool = self.plot_type == "grouped_stacked_bar"
            return AxesSettingsComponent(self.plot_id, self.plot_type).render(
                saved_config,
                data=data,
                has_dual_axis=has_dual_axis,
                show_group_labels=show_group_labels,
                render_specific_fn=self.render_specific_advanced_options,
                render_ordering_fn=self._render_ordering_ui,
            )

        if section == "data_labels":
            return DataLabelsSettingsComponent(self.plot_id, self.plot_type).render(
                saved_config, key_prefix="theme_"
            )

        if section == "colors":
            return ColorsSettingsComponent(self.plot_id, self.plot_type).render(
                saved_config, data=data
            )

        if section == "advanced":
            return AdvancedSettingsComponent(self.plot_id, self.plot_type).render(
                saved_config,
                data=data,
                render_reference_line_fn=self._render_reference_line_ui,
                render_shapes_fn=self._render_shapes_ui,
                render_engine_fn=self._render_engine_specific_controls,
            )

        return {}

    def _render_engine_specific_controls(
        self,
        saved_config: PlotConfig,
        config: PlotConfig,
    ) -> None:
        """Render engine-specific controls. Delegates to engine_settings component."""
        from src.web.components.plotting.settings.engine_settings import (
            EngineSettingsComponent,
        )

        EngineSettingsComponent(self.plot_id, self.plot_type).render(saved_config, config)

    def render_advanced_options(
        self, saved_config: PlotConfig, data: pd.DataFrame | None = None
    ) -> PlotConfig:
        """Render advanced options (legend, error bars, download format, axis settings).

        Should be called within an expander.

        Args:
            saved_config: Previously saved configuration
            data: The data being plotted (optional, needed for ordering options)

        Returns:
            Configuration dictionary with advanced options
        """
        config: PlotConfig = {}

        # 1. General & Axis Settings
        self._render_general_settings(saved_config, config)

        # 2. Specific Settings (Plot Type Specific)
        specific_config = self.render_specific_advanced_options(saved_config, data)
        config.update(specific_config)

        # 3. Ordering Control (includes inline X-axis & legend rename)
        if data is not None:
            self._render_ordering_ui(saved_config, data, config)

        # 4. Legend & Interactivity
        st.markdown("#### Legend & Interactivity")
        config["enable_editable"] = st.checkbox(
            "Enable Interactive Editing",
            value=saved_config.get("enable_editable", False),
            key=f"editable_{self.plot_id}",
            help="Allows you to drag the legend/title and click to edit text directly on the plot.",
        )

        # Preserve existing series styles (renaming now inline in ordering)
        if "series_styles" not in config:
            config["series_styles"] = saved_config.get("series_styles", {})

        # 5. Reference Line
        self._render_reference_line_ui(saved_config, data, config)

        # 6. Annotations
        st.markdown("#### Annotations (Shapes)")
        config["shapes"] = self._render_shapes_ui(saved_config)

        return config

    def render_specific_advanced_options(
        self, saved_config: PlotConfig, data: pd.DataFrame | None = None
    ) -> PlotConfig:
        """Hook for subclasses to render plot-specific advanced options.

        Default implementation renders Bar settings if plot_type contains 'bar'.
        """
        config: PlotConfig = {}
        if "bar" in self.plot_type:
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

            with col_bar2:
                if "grouped" in self.plot_type:
                    config["bargroupgap"] = st.slider(
                        "Spacing between Groups",
                        min_value=0.0,
                        max_value=1.0,
                        value=saved_config.get("bargroupgap", 0.0),
                        step=0.05,
                        key=f"bargroupgap_{self.plot_id}",
                    )

                if "stacked" in self.plot_type:
                    config["bar_border_width"] = st.slider(
                        "Bar Border Width",
                        min_value=0.0,
                        max_value=5.0,
                        value=saved_config.get("bar_border_width", 0.0),
                        step=0.5,
                        key=f"bar_border_{self.plot_id}",
                        help=(
                            "Adds a white border around each bar segment"
                            " to separate stacked items."
                        ),
                    )
        return config

    def _render_general_settings(self, saved_config: PlotConfig, config: PlotConfig) -> None:
        """Helper to render general settings.

        Args:
            saved_config: Previously saved configuration
            config: Current configuration to update
        """
        st.markdown("#### General & Axis")
        col1, col2 = st.columns(2)
        with col1:
            config["show_error_bars"] = st.checkbox(
                "Show Error Bars (if .sd columns exist)",
                value=saved_config.get("show_error_bars", False),
                key=f"error_bars_{self.plot_id}",
            )

            # Y-axis Stepping
            dtick: float = st.number_input(
                "Y-axis Step Size (0 for auto)",
                min_value=0.0,
                value=float(saved_config.get("yaxis_dtick") or 0.0),
                key=f"ydtick_{self.plot_id}",
            )
            if dtick > 0:
                config["yaxis_dtick"] = dtick

        with col2:
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

            # Download Scale
            config["export_scale"] = st.selectbox(
                "Download Scale (Resolution)",
                options=[1, 2, 3],
                index=[1, 2, 3].index(saved_config.get("export_scale", 1)),
                key=f"exp_scale_{self.plot_id}",
                help="1x = Screen Resolution (WYSIWYG). 3x = High Res (Publication).",
            )

            # Dimension Preview
            w: int = saved_config.get("width", 800)
            h: int = saved_config.get("height", 500)
            s: int = config["export_scale"]
            st.caption(f"Download Size: {w * s} x {h * s} px")
            st.caption("Change base dimensions in 'Layout' settings.")

            config["xaxis_tickangle"] = st.slider(
                "X-axis Label Rotation",
                min_value=-90,
                max_value=90,
                value=saved_config.get("xaxis_tickangle", -45),
                step=15,
                key=f"xaxis_angle_{self.plot_id}",
                help="Rotate X-axis labels to prevent overlap",
            )

    def _render_ordering_ui(
        self, saved_config: PlotConfig, data: pd.DataFrame, config: PlotConfig
    ) -> None:
        """Render ordering UI. Delegates to ordering_settings component."""
        from src.web.components.plotting.settings.ordering_settings import (
            OrderingSettingsComponent,
        )

        OrderingSettingsComponent(self.plot_id, self.plot_type).render(saved_config, data, config)

    def _render_shapes_ui(self, saved_config: PlotConfig) -> list[ShapeConfig]:
        """Render shapes UI. Delegates to shapes_settings component."""
        from src.web.components.plotting.settings.shapes_settings import (
            ShapesSettingsComponent,
        )

        return ShapesSettingsComponent(self.plot_id, self.plot_type).render(saved_config)

    def render_reorderable_list(
        self,
        label: str,
        items: list[str],
        key_prefix: str,
        legend_labels: dict[str, str] | None = None,
        default_order: list[str] | None = None,
        enable_rename: bool = False,
        rename_map: dict[str, str] | None = None,
    ) -> list[str] | tuple[list[str], dict[str, str]]:
        """Render a list that can be reordered using up/down buttons.

        Delegates to the standalone ``render_reorderable_list`` component.
        Kept as a thin wrapper for backward compatibility with subclasses.
        """
        from src.web.components.common.reorderable_list import (
            render_reorderable_list,
        )

        return render_reorderable_list(
            label=label,
            items=items,
            key_prefix=key_prefix,
            plot_id=self.plot_id,
            legend_labels=legend_labels,
            default_order=default_order,
            enable_rename=enable_rename,
            rename_map=rename_map,
        )

    def _render_reference_line_ui(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None,
        config: PlotConfig,
    ) -> None:
        """Render reference line UI. Delegates to reference_line_settings component."""
        from src.web.components.plotting.settings.reference_line_settings import (
            ReferenceLineSettingsComponent,
        )

        ReferenceLineSettingsComponent(self.plot_id, self.plot_type).render(
            saved_config, data, config
        )
