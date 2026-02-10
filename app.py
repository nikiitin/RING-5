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
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS
    st.markdown(
        """
    <style>
        .main-header {
            font-size: 3rem;
            font-weight: bold;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
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

    @st.cache_resource
    def get_api() -> ApplicationAPI:
        return ApplicationAPI()

    api = get_api()
    # Store for easy access in pages (optional, but consistent)
    st.session_state.api = api

    # Header
    st.markdown('<h1 class="main-header">RING-5 Interactive Analyzer</h1>', unsafe_allow_html=True)

    # Show current data preview if data is loaded
    # Access via API's state manager (exposed or via API method)
    # The API should expose a view model
    current_view = api.get_current_view()

    if current_view["raw_data"] is not None and not current_view["raw_data"].empty:
        st.markdown("#### Current Dataset")
        col1, col2, col3 = st.columns(3)
        data = current_view["raw_data"]
        config = current_view["config"]

        with col1:
            st.metric("Rows", len(data))
        with col2:
            st.metric("Columns", len(data.columns))
        with col3:
            csv_path = config.get("csv_path")
            if csv_path:
                st.metric("Source", Path(csv_path).name)
            else:
                st.metric("Source", "Uploaded")

        with st.expander("View Current Data", expanded=False):
            st.dataframe(data, width="stretch", height=300)

    # Sidebar - Navigation
    with st.sidebar:
        st.markdown("# RING-5")
        st.markdown("---")

        page = st.radio(
            "Navigation",
            [
                "Data Source",
                "Upload Data",
                "Data Managers",
                "Manage Plots",
                "Save/Load Portfolio",
                "⚡ Performance",
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")

        if st.button("Clear Data", width="stretch", help="Clear loaded CSV data and plots"):
            api.reset_session()
            st.rerun()

        if st.button(
            "Reset All",
            width="stretch",
            type="secondary",
            help="Reset entire application to defaults",
        ):
            api.reset_session()
            st.rerun()

    # Main content — lazy page imports: only the active page module is loaded
    if page == "Data Source":
        from src.web.pages.data_source import DataSourcePage

        DataSourcePage(api).render()
    elif page == "Upload Data":
        from src.web.pages.upload_data import UploadDataPage

        UploadDataPage(api).render()
    elif page == "Data Managers":
        from src.web.pages.data_managers import show_data_managers_page

        show_data_managers_page(api)
    elif page == "Manage Plots":
        from src.web.pages.manage_plots import show_manage_plots_page

        show_manage_plots_page(api)
    elif page == "Save/Load Portfolio":
        from src.web.pages.portfolio import show_portfolio_page

        show_portfolio_page(api)
    elif page == "⚡ Performance":
        from src.web.pages.performance import render_performance_page

        render_performance_page(api)


if __name__ == "__main__":
    # Note: Streamlit re-imports the main script.
    # By wrapping imports inside run_app(), we ensure they are NOT executed
    # when this script is imported as a module by multiprocessing workers.
    run_app()
