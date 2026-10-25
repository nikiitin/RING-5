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

from src.core.common.numbered_axis import numbered_axis_modes
from src.core.models.plot_config import ShapeConfig
from src.web.components.plotting.settings import (
    AdvancedSettingsComponent,
    AxesSettingsComponent,
    ColorsSettingsComponent,
    DataLabelsSettingsComponent,
    LayoutSettingsComponent,
    LegendSettingsComponent,
    ThemePresetsSettingsComponent,
    TypographySettingsComponent,
)
from src.core.models.plot_config import PlotConfig

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

    # Pills-driven section dispatcher

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
        # [impl->req~ring5.figure.theme-presets~1]
        if section is None:
            return {}

        if section == "layout":
            return LayoutSettingsComponent(self.plot_id, self.plot_type).render(saved_config, data)

        if section == "themes":
            return ThemePresetsSettingsComponent(self.plot_id, self.plot_type).render(saved_config)

        if section == "typography":
            return TypographySettingsComponent(self.plot_id, self.plot_type).render(
                saved_config, key_prefix="theme_"
            )

        if section == "legends":
            numbered_legend = "Number legend" in (numbered_axis_modes(saved_config) or [])
            has_separate_axis_legend = bool(
                saved_config.get("dual_axis")
                and not saved_config.get("unified_legend", True)
                and saved_config.get("y_columns_right")
            )
            has_secondary = has_separate_axis_legend or (
                self._supports_secondary_legend() and numbered_legend
            )
            has_tertiary: bool = (
                self._supports_tertiary_legend() and has_separate_axis_legend and numbered_legend
            )
            return LegendSettingsComponent(self.plot_id, self.plot_type).render(
                saved_config,
                data=data,
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
            return ColorsSettingsComponent(
                self.plot_id,
                self.plot_type,
                series_renderer=self._style_ui.render_series_visuals,
            ).render(saved_config, data=data)

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
