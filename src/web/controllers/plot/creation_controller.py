"""
Plot Creation Controller — orchestrates plot lifecycle operations.

Handles create, delete, duplicate, and rename by:
    1. Calling components to render UI and get user actions
    2. Performing domain operations via injected PlotLifecycleService
    3. Updating UI state via UIStateManager
    4. Triggering reruns when state changes require it

Dependencies are injected via protocols (no concrete imports from pages.ui).

Architecture Note — Streamlit usage:
    This controller uses ``st.rerun()`` for flow control after state mutations
    (create/delete/duplicate), ``st.toast()`` for transient success
    notifications, and ``st.exception()`` for error handling. These are
    intentional: ``st.rerun()`` is Streamlit's flow control mechanism,
    ``st.toast()`` is non-blocking feedback, and ``st.exception()`` renders
    full tracebacks. Presentation-only calls (warnings) are delegated to
    the component layer.
"""

import logging
from typing import cast

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.components.common.plot_controls import PlotControlsComponent
from src.web.components.common.plot_creation import PlotCreationComponent
from src.web.components.common.plot_selector import PlotSelectorComponent
from src.web.models.plot_protocols import (
    PlotHandle,
    PlotLifecycleService,
    PlotTypeRegistry,
    RenderablePlot,
)
from src.web.state.ui_state_manager import UIStateManager

logger = logging.getLogger(__name__)


class PlotCreationController:
    """Create, select, rename, delete, and duplicate plots."""

    def __init__(
        self,
        api: ApplicationAPI,
        ui_state: UIStateManager,
        lifecycle: PlotLifecycleService,
        registry: PlotTypeRegistry,
    ) -> None:
        """
        Initialize with dependency injection.

        Args:
            api: Application API for domain operations.
            ui_state: UI state manager for transient state.
            lifecycle: Plot lifecycle service (create/delete/duplicate).
            registry: Plot type registry (available types).
        """
        self._api: ApplicationAPI = api
        self._ui: UIStateManager = ui_state
        self._lifecycle: PlotLifecycleService = lifecycle
        self._registry: PlotTypeRegistry = registry

    def render_create_section(self) -> None:
        """
        Render the "Create New Plot" section.

        Delegates rendering to PlotCreationComponent, then handles
        the create action if the button was clicked.
        """
        # [impl->req~ring5.plots.create-multiple~1]
        counter: int = self._api.state_manager.get_plot_counter()
        available_types: list[str] = self._registry.get_available_types()

        result = PlotCreationComponent.render(
            default_name=f"Plot {counter + 1}",
            available_types=available_types,
        )

        if result["create_clicked"] and result["plot_type"]:
            self._lifecycle.create_plot(
                result["name"], result["plot_type"], self._api.state_manager
            )
            st.session_state.pop("plot_selector", None)
            st.rerun()

    def render_selector(self) -> RenderablePlot | None:
        """
        Render plot selector and return the currently selected plot.

        Returns:
            The selected plot, or None if no plots exist.
        """
        # [impl->req~ring5.plots.create-multiple~1]
        plots = self._api.state_manager.get_plots()
        if not plots:
            PlotSelectorComponent.render_no_plots_warning()
            return None

        # Disambiguate duplicate names (for example, ``X`` becomes ``X (2)``) so plots with the
        # same name can't collapse in the pills widget or resolve to the wrong plot.
        seen: dict[str, int] = {}
        labels: list[str] = []
        for p in plots:
            seen[p.name] = seen.get(p.name, 0) + 1
            labels.append(p.name if seen[p.name] == 1 else f"{p.name} ({seen[p.name]})")
        label_to_plot = {labels[i]: plots[i] for i in range(len(plots))}

        current_id: int | None = self._api.state_manager.get_current_plot_id()
        default_index: int = 0

        if current_id is not None:
            for i, p in enumerate(plots):
                if p.plot_id == current_id:
                    default_index = i
                    break

        selected_name: str = PlotSelectorComponent.render(labels, default_index=default_index)

        # BasePlot satisfies RenderablePlot
        selected_plot: RenderablePlot = cast(
            RenderablePlot, label_to_plot.get(selected_name, plots[0])
        )
        if selected_plot.plot_id != current_id:
            self._api.state_manager.set_current_plot_id(selected_plot.plot_id)

        return selected_plot

    def render_controls(self, plot: PlotHandle) -> None:
        """
        Render plot controls and handle actions.

        Handles: rename, delete, duplicate.

        Args:
            plot: The currently selected plot.
        """
        # [impl->req~ring5.plots.delete~1]
        # [impl->req~ring5.plots.duplicate~1]
        # [impl->req~ring5.plots.rename~1]
        actions = PlotControlsComponent.render(
            plot_id=plot.plot_id,
            current_name=plot.name,
        )

        # Rename
        if actions["new_name"] != plot.name:
            plot.name = actions["new_name"]
            st.session_state.pop("plot_selector", None)
            st.rerun()
            return

        # Delete
        if actions["delete_clicked"]:
            self._ui.plot.cleanup(plot.plot_id)
            self._lifecycle.delete_plot(plot.plot_id, self._api.state_manager)
            st.session_state.pop("plot_selector", None)
            st.rerun()

        # Duplicate
        if actions["duplicate_clicked"]:
            duplicate = self._lifecycle.duplicate_plot(plot, self._api.state_manager)
            self._api.state_manager.set_current_plot_id(duplicate.plot_id)
            st.session_state.pop("plot_selector", None)
            st.rerun()
