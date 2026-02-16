"""
RING-5 Interactive Web Application
Modern, interactive dashboard for gem5 data analysis and visualization.
"""

import sys
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def run_app():
    """Main application entry point."""
    # LATE IMPORTS: Avoid loading UI/Plotting modules when this file is imported by workers.
    # This prevents the "missing ScriptRunContext" warnings.
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

    @st.cache_resource(show_spinner="Initializing RING-5...")
    def get_api() -> ApplicationAPI:
        return ApplicationAPI()

    api = get_api()
    st.session_state.api = api

    # Sidebar - Navigation
    with st.sidebar:
        st.markdown("# RING-5")
        st.caption("gem5 Analysis & Visualization")
        st.markdown("---")

        _NAV_OPTIONS = [
            "Data Source",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
            "Performance",
        ]

        if "_nav_page" not in st.session_state:
            st.session_state["_nav_page"] = _NAV_OPTIONS[0]

        for _nav_item in _NAV_OPTIONS:
            _is_active = st.session_state["_nav_page"] == _nav_item
            if st.button(
                _nav_item,
                key=f"nav_{_nav_item}",
                use_container_width=True,
                type="primary" if _is_active else "tertiary",
            ):
                st.session_state["_nav_page"] = _nav_item
                st.rerun()

        page = st.session_state["_nav_page"]

        st.markdown("---")

        if st.button(
            "Clear Data",
            use_container_width=True,
            type="tertiary",
            help="Clear loaded CSV data and plots",
        ):
            api.reset_session()
            st.rerun()

        if st.button(
            "Reset All",
            use_container_width=True,
            type="secondary",
            help="Reset entire application to defaults",
        ):
            api.reset_session()
            st.rerun()

    # Header
    st.markdown('<h1 class="main-header">RING-5 Interactive Analyzer</h1>', unsafe_allow_html=True)

    # Data preview (fragment-wrapped — only reruns when its own widgets change).
    @st.fragment
    def _data_preview_fragment() -> None:
        current_view = api.get_current_view()

        if current_view["raw_data"] is not None and not current_view["raw_data"].empty:
            st.markdown("#### Current Dataset")
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

            with st.expander("View Current Data", expanded=False):
                st.dataframe(data, width="stretch", height=300)

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
    elif page == "Performance":
        from src.web.pages.performance import render_performance_page

        render_performance_page(api)


if __name__ == "__main__":
    # Note: Streamlit re-imports the main script.
    # By wrapping imports inside run_app(), we ensure they are NOT executed
    # when this script is imported as a module by multiprocessing workers.
    run_app()
