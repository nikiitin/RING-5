"""
Style Manager - Plot Styling Orchestration Facade.

Coordinates application of visual styles to plots. Delegates to StyleUIFactory
for UI configuration and StyleApplicator → FigureConfig → FigureSpecToPlotly
for engine-agnostic styling.
"""

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from src.web.models.plot_models import PlotConfig

from .applicator import StyleApplicator
from .factory import StyleUIFactory


class StyleManager:
    """
    Facade for managing plot styling.

    Delegates to StyleUIFactory (UI widgets) and StyleApplicator
    (ConfigSpecBuilder → FigureConfig → engine connector).
    """

    def __init__(self, plot_id: int, plot_type: str):
        self.plot_id = plot_id
        self.plot_type = plot_type
        # Use Factory to get specific UI strategy
        self.ui_manager = StyleUIFactory.get_strategy(plot_id, plot_type)
        self.applicator = StyleApplicator(plot_type)

    def render_layout_options(self, saved_config: PlotConfig) -> PlotConfig:
        """Render layout options UI."""
        return self.ui_manager.render_layout_options(saved_config)

    def render_style_ui(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None = None,
        items: list[str] | None = None,
        key_prefix: str = "",
    ) -> PlotConfig:
        """Render generic style UI."""
        return self.ui_manager.render_style_ui(
            saved_config, data, items=items, key_prefix=key_prefix
        )

    def render_theme_options(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None = None,
        items: list[str] | None = None,
        key_prefix: str = "",
    ) -> PlotConfig:
        """Alias for render_style_ui to maintain compatibility with BasePlot."""
        return self.render_style_ui(saved_config, data, items=items, key_prefix=key_prefix)

    def render_series_colors_ui(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None = None,
        key_prefix: str = "",
    ) -> dict[str, Any]:
        """Render series color UI."""
        return self.ui_manager.render_series_colors_ui(saved_config, data, key_prefix=key_prefix)

    def render_series_renaming_ui(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None = None,
        items: list[str] | None = None,
    ) -> dict[str, Any]:
        """Render series renaming UI."""
        # Renaming doesn't usually conflict as it's not
        # reused in the same way, but could add prefix
        # if needed.
        return self.ui_manager.render_series_renaming_ui(saved_config, data, items=items)

    def render_xaxis_labels_ui(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None = None,
        key_prefix: str = "xlabel",
    ) -> dict[str, str]:
        """Render X-axis label UI."""
        return self.ui_manager.render_xaxis_labels_ui(saved_config, data, key_prefix)

    def render_data_labels_ui(
        self,
        saved_config: PlotConfig,
        key_prefix: str = "",
    ) -> PlotConfig:
        """Render data labels UI."""
        return self.ui_manager.render_data_labels_ui(saved_config, key_prefix)

    def apply_styles(self, fig: go.Figure, config: PlotConfig) -> go.Figure:
        """Apply styles to figure."""
        return self.applicator.apply_styles(fig, config)

    # Helper proxy if needed directly
    def _get_unique_values(
        self, saved_config: PlotConfig, data: pd.DataFrame | None, items: list[str] | None
    ) -> list[str]:
        return self.ui_manager._get_unique_values(saved_config, data, items)
