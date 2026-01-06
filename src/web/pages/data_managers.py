"""
RING-5 Data Managers Page
Visualize and configure data managers with live effects preview.
"""

import pandas as pd
import streamlit as st

from ..components import UIComponents
from ..facade import BackendFacade
from ..state_manager import StateManager
from ..styles import AppStyles


class DataManagersPage:
    """Handles data manager configuration and visualization."""

    def __init__(self, facade: BackendFacade):
        """Initialize the managers page."""
        self.facade = facade

    def render(self):
        """Render the data managers page."""
        st.markdown(
            AppStyles.step_header("Data Managers & Transformations"), unsafe_allow_html=True
        )

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
            st.warning(
                "No data loaded. Please load data from **Data Source** or **Upload Data** page."
            )
            return

        # Show current data
        data = StateManager.get_data()

        # Safety check (should never be None due to has_data check above, but for type safety)
        if data is None:
            st.error("Data is None despite has_data check. This is unexpected.")
            return

        # Instantiate Managers
        from src.web.ui.data_managers.seeds_reducer import SeedsReducerManager
        from src.web.ui.data_managers.outlier_remover import OutlierRemoverManager
        from src.web.ui.data_managers.preprocessor import PreprocessorManager
        from src.web.ui.data_managers.mixer import MixerManager
        seeds_mgr = SeedsReducerManager(self.facade)
        outlier_mgr = OutlierRemoverManager(self.facade)
        preproc_mgr = PreprocessorManager(self.facade)
        mixer_mgr = MixerManager(self.facade) # [NEW] Mixer Manager!

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            [
                "Summary",
                "Data Visualization",
                seeds_mgr.name,
                outlier_mgr.name,
                preproc_mgr.name,
                mixer_mgr.name
            ]
        )

        with tab1:
            self._show_current_data(data)

        with tab2:
            self._show_data_visualization(data)

        with tab3:
            seeds_mgr.render()

        with tab4:
            outlier_mgr.render()

        with tab5:
            preproc_mgr.render()
            
        with tab6:
            mixer_mgr.render()

    def _show_current_data(self, data: pd.DataFrame):
        """Display current data with statistics."""
        st.markdown("### Dataset Summary")

        # Quick overview
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Rows", len(data))
        with col2:
            st.metric("Columns", len(data.columns))
        with col3:
            st.metric("Memory", f"{data.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        with col4:
            st.metric("Missing Values", data.isnull().sum().sum())

        st.markdown("### Quick Preview (first 20 rows)")
        st.dataframe(data.head(20), width="stretch")

        UIComponents.show_column_details(data)

        # Additional statistics
        st.markdown("### Data Statistics")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Numeric Columns Summary:**")
            numeric_data = data.select_dtypes(include=["number"])
            if not numeric_data.empty:
                st.dataframe(numeric_data.describe(), width="stretch")
            else:
                st.info("No numeric columns")

        with col2:
            st.markdown("**Categorical Columns Summary:**")
            categorical_data = data.select_dtypes(include=["object"])
            if not categorical_data.empty:
                for col in categorical_data.columns:
                    unique_count = data[col].nunique()
                    st.text(f"{col}: {unique_count} unique values")
                    if unique_count <= 10:
                        st.text(f"  Values: {', '.join(map(str, data[col].unique()[:10]))}")
            else:
                st.info("No categorical columns")

    def _show_data_visualization(self, data: pd.DataFrame):
        """Full data visualization with search and filtering."""
        st.markdown("### Full Data Visualization")

        # Search functionality
        st.markdown("#### Search & Filter")

        col1, col2 = st.columns([2, 1])

        with col1:
            search_column = st.selectbox(
                "Search in column",
                options=["All Columns"] + data.columns.tolist(),
                key="search_col",
            )

        with col2:
            search_term = st.text_input(
                "Search term", placeholder="Enter search term...", key="search_term"
            )

        # Apply search filter
        filtered_data = data.copy()

        if search_term:
            if search_column == "All Columns":
                # Search across all columns
                mask = filtered_data.astype(str).apply(
                    lambda row: row.str.contains(search_term, case=False, na=False).any(), axis=1
                )
                filtered_data = filtered_data[mask]
            else:
                # Search in specific column
                mask = (
                    filtered_data[search_column]
                    .astype(str)
                    .str.contains(search_term, case=False, na=False)
                )
                filtered_data = filtered_data[mask]

            st.info(f"Found {len(filtered_data)} matching rows (out of {len(data)} total)")

        # Column selection
        st.markdown("#### Display Options")

        col1, col2 = st.columns(2)

        with col1:
            display_columns = st.multiselect(
                "Select columns to display (leave empty for all)",
                options=data.columns.tolist(),
                default=[],
                key="display_cols",
            )

        with col2:
            rows_per_page = st.selectbox(
                "Rows per page", options=[20, 50, 100, 500, "All"], index=2, key="rows_per_page"
            )

        # Prepare display data
        display_data = filtered_data[display_columns] if display_columns else filtered_data

        # Pagination
        st.markdown("---")
        st.markdown(
            f"### Data Table ({len(display_data)} rows × {len(display_data.columns)} columns)"
        )

        if rows_per_page == "All":
            st.dataframe(display_data, width="stretch", height=600)
        else:
            # Paginated view
            total_rows = len(display_data)
            rows_per_page_int = int(rows_per_page)
            total_pages = (total_rows - 1) // rows_per_page_int + 1

            page = st.number_input(
                "Page", min_value=1, max_value=max(1, total_pages), value=1, key="page_num"
            )

            start_idx = (page - 1) * rows_per_page_int
            end_idx = min(start_idx + rows_per_page_int, total_rows)

            st.info(
                f"Showing rows {start_idx + 1} to {end_idx} of {total_rows} "
                f"(Page {page}/{total_pages})"
            )
            st.dataframe(display_data.iloc[start_idx:end_idx], width="stretch")

        # Download filtered data
        if st.button("Download Current View as CSV", key="download_view"):
            csv = display_data.to_csv(index=False)
            st.download_button(
                label="Click to Download",
                data=csv,
                file_name="filtered_data.csv",
                mime="text/csv",
                key="download_csv_btn",
            )



def show_data_managers_page():
    """Entry point for data managers page - creates facade and renders page."""
    facade = BackendFacade()
    page = DataManagersPage(facade)
    page.render()
