"""
Plot Creation Controller — orchestrates plot lifecycle operations.

Handles create, delete, duplicate, and rename by:
    1. Calling presenters to render UI and get user actions
    2. Performing domain operations via injected PlotLifecycleService
    3. Updating UI state via UIStateManager
    4. Triggering reruns when state changes require it

Dependencies are injected via protocols (no concrete imports from pages.ui).
"""

import copy
import logging
from typing import Optional

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.models.plot_protocols import (
    PlotHandle,
    PlotLifecycleService,
    PlotTypeRegistry,
)
from src.web.presenters.plot.controls_presenter import PlotControlsPresenter
from src.web.presenters.plot.creation_presenter import PlotCreationPresenter
from src.web.presenters.plot.load_dialog_presenter import LoadDialogPresenter
from src.web.presenters.plot.save_dialog_presenter import SaveDialogPresenter
from src.web.presenters.plot.selector_presenter import PlotSelectorPresenter
from src.web.state.ui_state_manager import UIStateManager

logger = logging.getLogger(__name__)


class PlotCreationController:
    """
    Orchestrates plot lifecycle: create, select, rename, delete, duplicate.

    Single Responsibility: managing which plots exist and which is selected.
    Does NOT handle pipeline editing, config gathering, or rendering.

    Dependencies are injected via protocols — no concrete imports from
    ``pages.ui.plotting.*``.
    """

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

        Delegates rendering to PlotCreationPresenter, then handles
        the create action if the button was clicked.
        """
        counter: int = self._api.state_manager.get_plot_counter()
        available_types: list[str] = self._registry.get_available_types()

        result = PlotCreationPresenter.render(
            default_name=f"Plot {counter + 1}",
            available_types=available_types,
        )

        if result["create_clicked"] and result["plot_type"]:
            self._lifecycle.create_plot(
                result["name"], result["plot_type"], self._api.state_manager
            )
            st.rerun()

    def render_selector(self) -> Optional[PlotHandle]:
        """
        Render plot selector and return the currently selected plot.

        Returns:
            The selected plot, or None if no plots exist.
        """
        plots = self._api.state_manager.get_plots()
        if not plots:
            st.warning("No plots yet. Create a plot to get started!")
            return None

        plot_names: list[str] = [p.name for p in plots]
        current_id: Optional[int] = self._api.state_manager.get_current_plot_id()
        default_index: int = 0

        if current_id is not None:
            for i, p in enumerate(plots):
                if p.plot_id == current_id:
                    default_index = i
                    break

        selected_name: str = PlotSelectorPresenter.render(plot_names, default_index=default_index)

        selected_plot: PlotHandle = next((p for p in plots if p.name == selected_name), plots[0])
        if selected_plot.plot_id != current_id:
            self._api.state_manager.set_current_plot_id(selected_plot.plot_id)

        return selected_plot

    def render_controls(self, plot: PlotHandle) -> None:
        """
        Render plot controls and handle actions.

        Handles: rename, save/load pipeline, delete, duplicate.

        Save/Load dialog toggling uses ``on_click`` callbacks passed to the
        presenter so that the state change is atomic and no manual
        ``st.rerun()`` is needed for those buttons.

        Args:
            plot: The currently selected plot.
        """

        # Callbacks for dialog visibility (fire before the natural rerun)
        def _on_save() -> None:
            self._ui.plot.set_dialog_visible(plot.plot_id, "save", True)
            self._ui.plot.set_dialog_visible(plot.plot_id, "load", False)

        def _on_load() -> None:
            self._ui.plot.set_dialog_visible(plot.plot_id, "load", True)
            self._ui.plot.set_dialog_visible(plot.plot_id, "save", False)

        actions = PlotControlsPresenter.render(
            plot_id=plot.plot_id,
            current_name=plot.name,
            on_save=_on_save,
            on_load=_on_load,
        )

        # Rename
        if actions["new_name"] != plot.name:
            plot.name = actions["new_name"]

        # Delete
        if actions["delete_clicked"]:
            self._ui.plot.cleanup(plot.plot_id)
            self._lifecycle.delete_plot(plot.plot_id, self._api.state_manager)
            st.rerun()

        # Duplicate
        if actions["duplicate_clicked"]:
            self._lifecycle.duplicate_plot(plot, self._api.state_manager)
            st.rerun()

        # Dialogs — rendering delegated to presenters, logic stays here
        if self._ui.plot.is_dialog_visible(plot.plot_id, "save"):
            self._handle_save_dialog(plot)
        if self._ui.plot.is_dialog_visible(plot.plot_id, "load"):
            self._handle_load_dialog(plot)

    def _handle_save_dialog(self, plot: PlotHandle) -> None:
        """Handle save pipeline dialog: render via presenter, act on result."""
        result = SaveDialogPresenter.render(
            plot_id=plot.plot_id,
            plot_name=plot.name,
        )

        if result["save_clicked"]:
            try:
                self._api.shapers.save_pipeline(
                    result["pipeline_name"],
                    plot.pipeline,
                    description=f"Source: {plot.name}",
                )
                st.toast("Pipeline saved!", icon="✅")
                self._ui.plot.set_dialog_visible(plot.plot_id, "save", False)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        if result["cancel_clicked"]:
            self._ui.plot.set_dialog_visible(plot.plot_id, "save", False)
            st.rerun()

    def _handle_load_dialog(self, plot: PlotHandle) -> None:
        """Handle load pipeline dialog: render via presenter, act on result."""
        pipelines = self._api.shapers.list_pipelines()

        if not pipelines:
            empty_result = LoadDialogPresenter.render_empty(
                plot_id=plot.plot_id,
            )
            if empty_result["close_clicked"]:
                self._ui.plot.set_dialog_visible(plot.plot_id, "load", False)
                st.rerun()
            return

        result = LoadDialogPresenter.render(
            plot_id=plot.plot_id,
            available_pipelines=pipelines,
        )

        if result["load_clicked"]:
            try:
                data = self._api.shapers.load_pipeline(result["selected_pipeline"])
                plot.pipeline = copy.deepcopy(data.get("pipeline", []))
                plot.pipeline_counter = len(plot.pipeline)
                plot.processed_data = None
                st.toast("Pipeline loaded!", icon="✅")
                self._ui.plot.set_dialog_visible(plot.plot_id, "load", False)
                st.rerun()
            except Exception as e:
                st.error(f"Error loading: {e}")
                logger.error(
                    "PLOT: Failed to load pipeline for plot %r: %s",
                    str(plot.name).replace("\n", ""),
                    e,
                    exc_info=True,
                )

        if result["cancel_clicked"]:
            self._ui.plot.set_dialog_visible(plot.plot_id, "load", False)
            st.rerun()
