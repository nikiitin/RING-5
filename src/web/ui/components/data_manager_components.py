import pandas as pd
import streamlit as st

from src.web.ui.components.data_components import DataComponents


class DataManagerComponents:
    """UI Components for the Data Managers Page."""

    @staticmethod
    def render_summary_tab(data: pd.DataFrame):
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

        DataComponents.show_column_details(data)

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

    @staticmethod
    def render_visualization_tab(data: pd.DataFrame):
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
                mask = filtered_data.astype(str).apply(
                    lambda row: row.str.contains(search_term, case=False, na=False).any(), axis=1
                )
                filtered_data = filtered_data[mask]
            else:
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
            total_rows = len(display_data)
            rows_per_page_int = int(rows_per_page)
            total_pages = (total_rows - 1) // rows_per_page_int + 1

            # Ensure page is within range
            if "page_num" not in st.session_state:
                st.session_state.page_num = 1

            page = st.number_input(
                "Page", min_value=1, max_value=max(1, total_pages), key="page_num"
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
