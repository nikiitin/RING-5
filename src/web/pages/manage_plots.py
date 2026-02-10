"""
Manage Plots Page

Modern plot management interface using plot class hierarchy.
Provides functionality to create, configure, and manage multiple plots
with independent data processing pipelines.
"""

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.pages.ui.components.plot_manager_components import (  # noqa: E402
    PlotManagerComponents,
)


def show_manage_plots_page(api: ApplicationAPI) -> None:
    """Main interface for managing multiple plots with pipelines."""
    st.markdown("## Manage Plots")
    st.markdown("Create and configure multiple plots with independent data processing pipelines.")

    # Initialize State
    api.state_manager.initialize()

    # CRITICAL: Apply pending widget updates from previous run (e.g. interactive zoom/legend drag)
    # This must happen BEFORE any widgets are rendered to avoid "Instantiated" errors.
    if "pending_plot_updates" in st.session_state:
        updates = st.session_state["pending_plot_updates"]
        for key, value in updates.items():
            if key in st.session_state:
                st.session_state[key] = value
        del st.session_state["pending_plot_updates"]

    # 1. Create Plot Section
    PlotManagerComponents.render_create_plot_section(api)

    # 2. Plot Selector
    current_plot = PlotManagerComponents.render_plot_selector(api)

    if current_plot:
        # 3. Plot Controls (Rename, Delete, Duplicate, Pipe I/O)
        PlotManagerComponents.render_plot_controls(api, current_plot)

        st.markdown("---")

        # 4. Pipeline Editor
        PlotManagerComponents.render_pipeline_editor(api, current_plot)

        # 5. Plot Visualization & Config
        PlotManagerComponents.render_plot_display(api, current_plot)

    # 6. Workspace Management
    PlotManagerComponents.render_workspace_management(api)


if __name__ == "__main__":
    # For testing/running directly, we create a dummy API or fail
    # Ideally page should be run via main app.
    # But if run directly, we need to instantiate API.
    # This is likely for dev testing.
    # However, creating ApplicationAPI expects Streamlit context.
    try:
        api = ApplicationAPI()
        show_manage_plots_page(api)
    except Exception:
        st.error("Please run via main app.")
