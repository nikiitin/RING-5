"""
RING-5 Interactive Web Application
Modern, interactive dashboard for gem5 data analysis and visualization.
"""

import sys
from pathlib import Path

root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.core.services.workspace_command_catalog import DOCUMENTATION_URL  # noqa: E402


def run_app() -> None:
    """Main application entry point."""
    # [impl->req~ring5.workspace.web-app~1]
    # [impl->req~ring5.workspace.guided-analysis~1]
    # Lazy imports keep Streamlit out of multiprocessing workers that import app.py.
    import streamlit as st

    # Page configuration
    st.set_page_config(
        page_title="RING-5 Interactive Analyzer",
        page_icon="R5",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for dark Alphabet-inspired theme + sidebar nav menu
    st.markdown(
        """
    <style>
        .main-header {
            font-size: 3rem;
            font-weight: bold;
            background: linear-gradient(90deg, #8b5cf6 0%, #a78bfa 50%, #c4b5fd 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            padding: 1rem 0;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Initialize Core Components
    from src.core.application_api import ApplicationAPI
    from src.web.pages.ui.plotting.plot_factory import PlotFactory

    # The API owns mutable workspace state and transient parse metadata. Keep
    # one resource per browser session and release it when that session ends.
    # Only explicitly thread-safe parser worker pools remain process-wide.
    # [impl->req~ring5.workspace.session-isolation~1]
    @st.cache_resource(
        show_spinner="Initializing RING-5...",
        scope="session",
        on_release=lambda session_api: session_api.close(),
    )
    def get_api() -> ApplicationAPI:
        """Return the mutable application facade owned by this browser session."""
        return ApplicationAPI(plot_deserializer=PlotFactory.from_dict)

    api = get_api()
    st.session_state.api = api

    from src.web.components.data_source.parse_job_status import (
        render_sidebar_parse_job,
        show_parse_job_flash,
    )

    show_parse_job_flash()

    # Sidebar - Navigation
    with st.sidebar:
        st.markdown("# RING-5")
        st.caption("gem5 Analysis & Visualization")
        st.markdown("---")

        # [impl->req~ring5.workspace.navigation~2]
        _NAV_OPTIONS = [
            "Data Source",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
        ]

        if st.session_state.get("_nav_page") not in _NAV_OPTIONS:
            st.session_state["_nav_page"] = _NAV_OPTIONS[0]

        from src.web.components.command_palette import CommandPaletteComponent
        from src.web.components.analysis_review import AnalysisReviewComponent
        from src.web.components.autosave_recovery import AutosaveRecoveryComponent
        from src.web.components.guided_analysis import GuidedAnalysisComponent
        from src.web.components.workspace_organizer import WorkspaceOrganizerComponent
        from src.web.components.workspace_search import WorkspaceSearchComponent

        CommandPaletteComponent.render(api)
        GuidedAnalysisComponent.render_fragmented(api)
        WorkspaceSearchComponent.render(api)
        WorkspaceOrganizerComponent.render(api)
        AnalysisReviewComponent.render(api)
        AutosaveRecoveryComponent.render(api)
        st.markdown("---")

        for _nav_item in _NAV_OPTIONS:
            _is_active = st.session_state["_nav_page"] == _nav_item
            _nav_clicked = st.button(
                _nav_item,
                key=f"nav_{_nav_item}",
                width="stretch",
                type="primary" if _is_active else "tertiary",
            )
            if _nav_clicked and not _is_active:
                st.session_state["_nav_page"] = _nav_item
                st.rerun()

        # [impl->req~ring5.workspace.documentation-hub~2]
        st.link_button(
            "Documentation",
            DOCUMENTATION_URL,
            width="stretch",
            help="Open the published RING-5 documentation",
        )

        page = st.session_state["_nav_page"]

        st.markdown("---")

        from src.web.components.background_job_center import BackgroundJobCenter

        render_sidebar_parse_job(api)
        BackgroundJobCenter.render(api)

        st.markdown("---")

        # [impl->req~ring5.workspace.reset~1]
        if st.button(
            "Clear Data",
            width="stretch",
            type="tertiary",
            help="Clear loaded CSV data and plots",
        ):
            api.reset_session()
            st.session_state.pop(GuidedAnalysisComponent.EXPORT_STATE_KEY, None)
            st.rerun()

        if st.button(
            "Reset All",
            width="stretch",
            type="secondary",
            help="Reset entire application to defaults",
        ):
            api.reset_session()
            st.session_state.pop(GuidedAnalysisComponent.EXPORT_STATE_KEY, None)
            st.rerun()

    # Header
    st.markdown('<h1 class="main-header">RING-5 Interactive Analyzer</h1>', unsafe_allow_html=True)

    # Data preview (fragment-wrapped — only reruns when its own widgets change).
    @st.fragment
    def _data_preview_fragment() -> None:
        """Render the current dataset summary in an isolated fragment."""
        # [impl->req~ring5.workspace.data-preview~1]
        current_view = api.get_current_view()

        if current_view["raw_data"] is not None and not current_view["raw_data"].empty:
            col1, col2, col3 = st.columns(3)
            data = current_view["raw_data"]
            config = current_view["config"]

            with col1:
                st.metric("Rows", len(data), border=True)
            with col2:
                st.metric("Columns", len(data.columns), border=True)
            with col3:
                csv_path = config.get("csv_path")
                if csv_path:
                    st.metric("Source", Path(csv_path).name, border=True)
                else:
                    st.metric("Source", "Uploaded", border=True)

    _data_preview_fragment()

    # Main content — lazy page imports: only the active page module is loaded
    if page == "Data Source":
        from src.web.pages.data_source import DataSourcePage

        DataSourcePage(api).render()
    elif page == "Data Managers":
        from src.web.pages.data_managers import show_data_managers_page

        show_data_managers_page(api)
    elif page == "Manage Plots":
        from src.web.pages.manage_plots import show_manage_plots_page

        show_manage_plots_page(api)
    elif page == "Save/Load Portfolio":
        from src.web.pages.portfolio import show_portfolio_page

        show_portfolio_page(api)


if __name__ == "__main__":
    # Keep page imports out of multiprocessing workers that import this module.
    run_app()
