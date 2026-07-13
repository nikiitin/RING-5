"""
Manage Plots Page — Thin composition using Controller/Component architecture.

Composes controllers that each handle a single concern:

    PlotCreationController — create, select, rename, delete, duplicate
    PipelineController — shaper pipeline editing
    PlotRenderController — config + figure generation + display

The page itself is pure wiring. All logic lives in controllers.
All rendering lives in components. All state access goes through
UIStateManager.

Dependency Injection:
    This page creates adapter instances that wrap old ``pages.ui.plotting.*``
    static methods into protocol-compatible objects. Controllers receive these
    adapters via constructor injection and never import concrete classes.
"""

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.controllers.plot.creation_controller import PlotCreationController
from src.web.controllers.plot.pipeline_controller import PipelineController
from src.web.controllers.plot.render_controller import PlotRenderController
from src.web.models.plot_protocols import PlotHandle, RenderablePlot
from src.web.pages.plot_adapters import (
    PipelineExecutorAdapter,
    PlotLifecycleAdapter,
    PlotTypeRegistryAdapter,
)
from src.web.state.ui_state_manager import UIStateManager


def _pipeline_fragment(pipeline: PipelineController, current_plot: PlotHandle) -> None:
    pipeline.render(current_plot)


def _render_fragment(render: PlotRenderController, current_plot: RenderablePlot) -> None:
    render.render(current_plot)


def show_manage_plots_page(api: ApplicationAPI) -> None:
    """
    Main interface for managing plots.

    Composes three controllers with injected dependencies:
        1. PlotCreationController — plot lifecycle
        2. PipelineController — data transformation pipeline
        3. PlotRenderController — visualization

    Args:
        api: Application API (dependency-injected).
    """
    st.markdown("## Manage Plots")
    st.markdown(
        "Create and configure multiple plots with independent " "data processing pipelines."
    )

    # ApplicationAPI initializes this session's repositories in its constructor.
    ui_state: UIStateManager = UIStateManager()

    # Apply pending widget updates from interactive plot events
    pending = ui_state.plot.consume_pending_updates()
    if pending:
        for key, value in pending.items():
            if key in st.session_state:
                st.session_state[key] = value

    # Create adapters (bridge old static/class methods to protocol contracts).
    # These are lightweight wrappers — no I/O in constructors.
    lifecycle: PlotLifecycleAdapter = PlotLifecycleAdapter()
    registry: PlotTypeRegistryAdapter = PlotTypeRegistryAdapter()
    pipeline_executor: PipelineExecutorAdapter = PipelineExecutorAdapter()

    # Controllers (dependency-injected, stateless)
    creation: PlotCreationController = PlotCreationController(api, ui_state, lifecycle, registry)
    pipeline: PipelineController = PipelineController(api, ui_state, pipeline_executor)
    render: PlotRenderController = PlotRenderController(api, ui_state, lifecycle, registry)

    # 1. Create Plot Section
    creation.render_create_section()

    # 2. Plot Selector
    current_plot = creation.render_selector()

    if current_plot:
        # 3. Controls (rename, delete, duplicate)
        creation.render_controls(current_plot)
        st.markdown("---")

        # 4. Pipeline Editor (fragmented)
        st.fragment(_pipeline_fragment)(pipeline, current_plot)

        # 5. Visualization (fragmented)
        st.fragment(_render_fragment)(render, current_plot)
