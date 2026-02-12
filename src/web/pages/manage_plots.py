"""
Manage Plots Page — Thin composition using Controller/Presenter architecture.

Composes controllers that each handle a single concern:

    PlotCreationController — create, select, rename, delete, duplicate
    PipelineController — shaper pipeline editing
    PlotRenderController — config + figure generation + display

The page itself is pure wiring. All logic lives in controllers.
All rendering lives in presenters. All state access goes through UIStateManager.

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
from src.web.pages.plot_adapters import (
    ChartDisplayAdapter,
    PipelineExecutorAdapter,
    PlotLifecycleAdapter,
    PlotTypeRegistryAdapter,
)
from src.web.pages.ui.components.plot_manager_components import (
    PlotManagerComponents,
)
from src.web.state.ui_state_manager import UIStateManager


def show_manage_plots_page(api: ApplicationAPI) -> None:
    """
    Main interface for managing plots.

    Composes three controllers with injected dependencies:
        1. PlotCreationController — plot lifecycle
        2. PipelineController — data transformation pipeline
        3. PlotRenderController — visualization

    Plus workspace management from PlotManagerComponents.

    Args:
        api: Application API (dependency-injected).
    """
    st.markdown("## Manage Plots")
    st.markdown(
        "Create and configure multiple plots with independent " "data processing pipelines."
    )

    # Initialize
    api.state_manager.initialize()
    ui_state: UIStateManager = UIStateManager()

    # Apply pending widget updates from interactive plot events
    pending = ui_state.plot.consume_pending_updates()
    if pending:
        for key, value in pending.items():
            if key in st.session_state:
                st.session_state[key] = value

    # Create adapters (bridge old static/class methods to protocol contracts)
    lifecycle: PlotLifecycleAdapter = PlotLifecycleAdapter()
    registry: PlotTypeRegistryAdapter = PlotTypeRegistryAdapter()
    chart_display: ChartDisplayAdapter = ChartDisplayAdapter()
    pipeline_executor: PipelineExecutorAdapter = PipelineExecutorAdapter()

    # Controllers (dependency-injected, stateless)
    creation: PlotCreationController = PlotCreationController(api, ui_state, lifecycle, registry)
    pipeline: PipelineController = PipelineController(api, ui_state, pipeline_executor)
    render: PlotRenderController = PlotRenderController(
        api, ui_state, lifecycle, registry, chart_display
    )

    # 1. Create Plot Section
    creation.render_create_section()

    # 2. Plot Selector
    current_plot = creation.render_selector()

    if current_plot:
        # 3. Controls (rename, delete, duplicate, pipeline I/O)
        creation.render_controls(current_plot)
        st.markdown("---")

        # 4. Pipeline Editor (fragmented — widget interactions only rerun this section)
        @st.fragment
        def _pipeline_fragment() -> None:
            pipeline.render(current_plot)

        _pipeline_fragment()

        # 5. Visualization (fragmented — config widgets only rerun this section)
        @st.fragment
        def _render_fragment() -> None:
            render.render(current_plot)  # type: ignore[arg-type]

        _render_fragment()

    # 6. Workspace Management (export all, etc.)
    PlotManagerComponents.render_workspace_management(api)
