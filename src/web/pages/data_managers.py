"""
RING-5 Data Managers Page

Visualize and configure data managers with live effects preview.
Handles loading, filtering, and transforming data from various sources.
"""

import streamlit as st

from src.web.state_manager import StateManager
from src.web.styles import AppStyles
from src.web.ui.components.data_manager_components import DataManagerComponents
from src.web.ui.data_managers.mixer import MixerManager
from src.web.ui.data_managers.outlier_remover import OutlierRemoverManager
from src.web.ui.data_managers.preprocessor import PreprocessorManager

# Import Sub-Managers
from src.web.ui.data_managers.seeds_reducer import SeedsReducerManager


def show_data_managers_page() -> None:
    """Render the data managers page with transformation capabilities."""

    st.markdown(AppStyles.step_header("Data Managers & Transformations"), unsafe_allow_html=True)

    st.info(
        """
    **Data Managers** handle loading, filtering, and transforming data from various sources.

    - View your current data
    - Apply filters and transformations
    - See effects in real-time
    - Manage multiple data sources
    """
    )

    if not StateManager.has_data():
        st.warning("No data loaded. Please load data from **Data Source** or **Upload Data** page.")
        return

    data_or_none = StateManager.get_data()
    if data_or_none is None:
        st.error("Failed to retrieve data.")
        return
    data = data_or_none

    # Initialize Managers
    seeds_mgr = SeedsReducerManager()
    outlier_mgr = OutlierRemoverManager()
    preproc_mgr = PreprocessorManager()
    mixer_mgr = MixerManager()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "Summary",
            "Data Visualization",
            seeds_mgr.name,
            outlier_mgr.name,
            preproc_mgr.name,
            mixer_mgr.name,
        ]
    )

    with tab1:
        DataManagerComponents.render_summary_tab(data)

    with tab2:
        DataManagerComponents.render_visualization_tab(data)

    with tab3:
        seeds_mgr.render()

    with tab4:
        outlier_mgr.render()

    with tab5:
        preproc_mgr.render()

    with tab6:
        mixer_mgr.render()
