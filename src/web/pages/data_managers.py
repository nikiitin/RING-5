"""
RING-5 Data Managers Page

Visualize and configure data managers with live effects preview.
Handles loading, filtering, and transforming data from various sources.
"""

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.pages.ui.components.data_manager_components import DataManagerComponents
from src.web.pages.ui.components.history_components import HistoryComponents
from src.web.pages.ui.data_managers.impl.mixer import MixerManager
from src.web.pages.ui.data_managers.impl.outlier_remover import OutlierRemoverManager
from src.web.pages.ui.data_managers.impl.preprocessor import PreprocessorManager

# Import Sub-Managers
from src.web.pages.ui.data_managers.impl.seeds_reducer import SeedsReducerManager


def show_data_managers_page(api: ApplicationAPI) -> None:
    """Render the data managers page with transformation capabilities."""

    st.markdown("## Data Managers & Transformations")

    st.info("""
    **Data Managers** handle loading, filtering, and transforming data from various sources.

    - View your current data
    - Apply filters and transformations
    - See effects in real-time
    - Manage multiple data sources
    """)

    if not api.state_manager.has_data():
        st.warning("No data loaded. Please load data from **Data Source** or **Upload Data** page.")
        return

    data_or_none = api.state_manager.get_data()
    if data_or_none is None:
        st.error("Failed to retrieve data.")
        return
    data = data_or_none

    # Initialize Managers
    seeds_mgr = SeedsReducerManager(api)
    outlier_mgr = OutlierRemoverManager(api)
    preproc_mgr = PreprocessorManager(api)
    mixer_mgr = MixerManager(api)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "Summary",
            "Data Visualization",
            seeds_mgr.name,
            outlier_mgr.name,
            preproc_mgr.name,
            mixer_mgr.name,
            "Operations History",
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

    with tab7:
        HistoryComponents.render_portfolio_history(api.get_portfolio_history())
