"""
RING-5 Data Managers Page

Visualize and configure data managers with live effects preview.
Handles loading, filtering, and transforming data from various sources.
"""

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.components.common.history_components import HistoryComponents
from src.web.components.data_managers.data_manager_components import (
    DataManagerComponents,
)
from src.web.components.data_managers.comparison import ComparisonManager
from src.web.components.data_managers.dataset_workspace import DatasetWorkspaceManager
from src.web.components.data_managers.mixer import MixerManager
from src.web.components.data_managers.outlier_remover import OutlierRemoverManager
from src.web.components.data_managers.preprocessor import PreprocessorManager
from src.web.components.data_managers.quality_profile import QualityProfileManager
from src.web.components.data_managers.schema_contract import SchemaContractManager

# Import Sub-Managers
from src.web.components.data_managers.seeds_reducer import SeedsReducerManager


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

    has_data: bool = api.state_manager.has_data()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs(
        [
            "Summary",
            "Data Visualization",
            "Workspace",
            "Seeds Reducer",
            "Outlier Remover",
            "Preprocessor",
            "Mixer",
            "Compare",
            "Data Quality",
            "Schema Contract",
            "Operations History",
        ]
    )

    if not has_data:
        with tab1:
            st.warning("No data loaded. Please load data from the **Data Source** page.")
        return

    data_or_none = api.state_manager.get_data()
    if data_or_none is None:
        with tab1:
            st.error("Failed to retrieve data.")
        return
    data = data_or_none

    with tab1:

        @st.fragment
        def _summary_fragment() -> None:
            DataManagerComponents.render_summary_tab(data)

        _summary_fragment()

    with tab2:

        @st.fragment
        def _visualization_fragment() -> None:
            DataManagerComponents.render_visualization_tab(data)

        _visualization_fragment()

    with tab3:

        @st.fragment
        def _workspace_fragment() -> None:
            DatasetWorkspaceManager(api).render()

        _workspace_fragment()

    with tab4:

        @st.fragment
        def _seeds_fragment() -> None:
            SeedsReducerManager(api).render()

        _seeds_fragment()

    with tab5:

        @st.fragment
        def _outlier_fragment() -> None:
            OutlierRemoverManager(api).render()

        _outlier_fragment()

    with tab6:

        @st.fragment
        def _preproc_fragment() -> None:
            PreprocessorManager(api).render()

        _preproc_fragment()

    with tab7:

        @st.fragment
        def _mixer_fragment() -> None:
            MixerManager(api).render()

        _mixer_fragment()

    with tab8:

        @st.fragment
        def _comparison_fragment() -> None:
            ComparisonManager(api).render()

        _comparison_fragment()

    with tab9:

        @st.fragment
        def _quality_fragment() -> None:
            QualityProfileManager(api).render()

        _quality_fragment()

    with tab10:

        @st.fragment
        def _schema_contract_fragment() -> None:
            SchemaContractManager(api).render()

        _schema_contract_fragment()

    with tab11:
        HistoryComponents.render_portfolio_history(api.get_portfolio_history())
