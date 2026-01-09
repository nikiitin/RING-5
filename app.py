"""
RING-5 Interactive Web Application
Modern, interactive dashboard for gem5 data analysis and visualization.
"""

import sys
from pathlib import Path

import streamlit as st

# Add project root to path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.web.facade import BackendFacade  # noqa: E402
from src.web.pages.data_managers import show_data_managers_page  # noqa: E402
from src.web.pages.data_source import DataSourcePage  # noqa: E402
from src.web.pages.manage_plots import show_manage_plots_page  # noqa: E402
from src.web.pages.portfolio import show_portfolio_page  # noqa: E402
from src.web.pages.upload_data import UploadDataPage  # noqa: E402
from src.web.state_manager import StateManager  # noqa: E402

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
    .step-header {
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .step-header h2 {
        margin: 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


def main():
    """Main application entry point."""
    # Initialize Core Components
    StateManager.initialize()
    facade = BackendFacade()

    # Header
    st.markdown('<h1 class="main-header">RING-5 Interactive Analyzer</h1>', unsafe_allow_html=True)

    # Show current data preview if data is loaded
    if StateManager.has_data():
        st.markdown("#### Current Dataset")
        col1, col2, col3 = st.columns(3)
        data = StateManager.get_data()
        with col1:
            st.metric("Rows", len(data))
        with col2:
            st.metric("Columns", len(data.columns))
        with col3:
            if StateManager.get_csv_path():
                st.metric("Source", Path(StateManager.get_csv_path()).name)
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
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")

        if st.button("Clear All Data", width="stretch"):
            StateManager.clear_all()
            st.rerun()

    # Main content
    if page == "Data Source":
        DataSourcePage(facade).render()
    elif page == "Upload Data":
        UploadDataPage(facade).render()

    elif page == "Data Managers":
        show_data_managers_page()
    elif page == "Manage Plots":
        show_manage_plots_page()
    elif page == "Save/Load Portfolio":
        show_portfolio_page()


if __name__ == "__main__":
    main()
