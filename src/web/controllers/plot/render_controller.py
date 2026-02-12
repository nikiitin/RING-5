"""
Plot Render Controller — orchestrates config gathering, figure generation, display.

Handles:
    - Gathering config from ConfigPresenter (which wraps BasePlot methods)
    - Detecting config changes
    - Display via ChartDisplay (wraps PlotRenderer caching + relayout)
    - Plot type changes via PlotLifecycleService

Dependencies are injected via protocols (no concrete imports from pages.ui).
"""

import logging
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.models.plot_protocols import (
    ChartDisplay,
    PlotLifecycleService,
    PlotTypeRegistry,
    RenderablePlot,
)
from src.web.presenters.plot.chart_presenter import ChartPresenter
from src.web.presenters.plot.config_presenter import ConfigPresenter
from src.web.state.ui_state_manager import UIStateManager

logger = logging.getLogger(__name__)


class PlotRenderController:
    """
    Orchestrates the visualization section: config → display.

    Single Responsibility: turning plot config + data into a rendered chart.
    Does NOT handle pipeline editing or plot lifecycle.

    Architecture:
        - ConfigPresenter gathers all config (type-specific + advanced + theme)
        - ChartDisplay renders the figure (caching + relayout handling)
        - PlotLifecycleService handles plot type changes

    Dependencies are injected via protocols — no concrete imports from
    ``pages.ui.plotting.*``.
    """

    def __init__(
        self,
        api: ApplicationAPI,
        ui_state: UIStateManager,
        lifecycle: PlotLifecycleService,
        registry: PlotTypeRegistry,
        chart_display: ChartDisplay,
    ) -> None:
        """
        Initialize with dependency injection.

        Args:
            api: Application API for domain operations.
            ui_state: UI state manager for transient state.
            lifecycle: Plot lifecycle service (for type changes).
            registry: Plot type registry (available types).
            chart_display: Chart display service (caching + rendering).
        """
        self._api: ApplicationAPI = api
        self._ui: UIStateManager = ui_state
        self._lifecycle: PlotLifecycleService = lifecycle
        self._registry: PlotTypeRegistry = registry
        self._chart: ChartDisplay = chart_display

    def render(self, plot: RenderablePlot) -> None:
        """
        Render the full visualization section for a plot.

        Steps:
            1. Guard: check processed data exists
            2. Plot type selector (via ConfigPresenter)
            3. Type-specific config (via ConfigPresenter)
            4. Advanced + theme config (via ConfigPresenter)
            5. Detect config changes
            6. Refresh controls (via ChartPresenter)
            7. Display chart (via ChartDisplay)

        Args:
            plot: The plot to render (must satisfy both PlotHandle
                  and ConfigRenderer protocols).
        """
        if plot.processed_data is None:
            ConfigPresenter.render_no_data_warning()
            return

        ConfigPresenter.render_section_headers()
        saved_config: Dict[str, Any] = plot.config
        current_config: Dict[str, Any] = saved_config.copy()
        config_error: bool = False

        # 1. Plot type selector (via ConfigPresenter)
        available_types: List[str] = self._registry.get_available_types()
        type_result = ConfigPresenter.render_plot_type_selector(
            plot_type=plot.plot_type,
            available_types=available_types,
            plot_id=plot.plot_id,
        )

        if type_result["type_changed"]:
            self._lifecycle.change_plot_type(plot, type_result["new_type"], self._api.state_manager)
            st.rerun()

        # 2. Type-specific config (via ConfigPresenter → delegates to plot)
        data: pd.DataFrame = plot.processed_data
        # plot satisfies RenderablePlot (PlotHandle + ConfigRenderer)
        try:
            ui_config: Dict[str, Any] = ConfigPresenter.render_type_config(
                renderer=plot,
                data=data,
                saved_config=saved_config,
            )
            current_config.update(ui_config)
        except Exception as e:
            st.error(f"Configuration error: {e}")
            logger.error(
                "RENDER: Type config failed for plot %r: %s",
                str(plot.name).replace("\n", ""),
                e,
                exc_info=True,
            )
            config_error = True

        # 3. Advanced & Theme (via ConfigPresenter)
        try:
            extra_config: Dict[str, Any] = ConfigPresenter.render_advanced_and_theme(
                renderer=plot,
                current_config=current_config,
                data=data,
            )
            current_config.update(extra_config)
        except Exception as e:
            st.error(f"Advanced options error: {e}")
            logger.error(
                "RENDER: Advanced config failed for plot %r: %s",
                str(plot.name).replace("\n", ""),
                e,
                exc_info=True,
            )
            config_error = True

        # 4. Refresh logic (via ChartPresenter)
        config_changed: bool = current_config != saved_config
        auto_refresh: bool = self._ui.plot.get_auto_refresh(plot.plot_id)

        controls = ChartPresenter.render_refresh_controls(
            plot_id=plot.plot_id,
            auto_refresh=auto_refresh,
            config_changed=config_changed,
        )

        # Update auto-refresh in UI state
        self._ui.plot.set_auto_refresh(plot.plot_id, controls["auto_refresh"])

        should_gen: bool = controls["should_generate"] and not config_error
        plot.config = current_config

        # 5. Render chart via ChartDisplay (handles caching + relayout)
        self._chart.render_chart(plot, should_gen)
