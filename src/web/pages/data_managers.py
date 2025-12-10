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

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "Summary",
                "Data Visualization",
                "Seeds Reducer",
                "Outlier Remover",
                "Preprocessor (Mixer)",
            ]
        )

        with tab1:
            self._show_current_data(data)

        with tab2:
            self._show_data_visualization(data)

        with tab3:
            self._show_seeds_reducer()

        with tab4:
            self._show_outlier_remover()

        with tab5:
            self._show_preprocessor()

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

    def _show_seeds_reducer(self):
        """Seeds Reducer - Calculate mean and std dev across seeds."""
        st.markdown("### Seeds Reducer")

        st.info(
            """
        **Seeds Reducer** groups data by categorical columns and calculates statistics across
        different random seeds.

        - Removes the `random_seed` column
        - Groups by categorical columns
        - Calculates mean and standard deviation for numeric columns
        - Useful for averaging results across multiple simulation runs
        """
        )

        # Get current data
        data = StateManager.get_data()

        if data is None:
            st.error("No data available. Please load data first.")
            return

        # Check if random_seed column exists
        if "random_seed" not in data.columns:
            st.warning(
                "No `random_seed` column found in the dataset. "
                "Seeds Reducer requires this column."
            )
            st.info(
                "If your data has seeds in a different column, please rename it to `random_seed` "
                "first."
            )
            return

        # Identify categorical and numeric columns
        categorical_cols = data.select_dtypes(include=["object"]).columns.tolist()
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()

        # Remove random_seed from categorical if present
        if "random_seed" in categorical_cols:
            categorical_cols.remove("random_seed")
        if "random_seed" in numeric_cols:
            numeric_cols.remove("random_seed")

        if not categorical_cols:
            st.warning("No categorical columns found for grouping.")
            return

        if not numeric_cols:
            st.warning("No numeric columns found to calculate statistics.")
            return

        st.markdown("**Configuration:**")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Categorical columns (for grouping):**")
            selected_categorical = st.multiselect(
                "Group by columns",
                options=categorical_cols,
                default=categorical_cols,
                key="seeds_categorical",
            )

        with col2:
            st.markdown("**Numeric columns (for statistics):**")
            selected_numeric = st.multiselect(
                "Calculate stats for",
                options=numeric_cols,
                default=numeric_cols,
                key="seeds_numeric",
            )

        st.info(
            """
        **Note on Standard Deviation:**
        - Seeds Reducer will create `.sd` columns for standard deviations
        - When you later normalize data (in Configure Pipeline), the `.sd` columns will be
          automatically normalized by the same baseline value
        - This ensures error bars are correctly scaled in normalized plots
        """
        )

        if st.button("Apply Seeds Reducer", key="apply_seeds"):
            if not selected_categorical:
                st.error("Please select at least one categorical column for grouping.")
                return
            if not selected_numeric:
                st.error("Please select at least one numeric column for statistics.")
                return

            try:
                # Use the existing DataManager implementation via facade
                result_df = self.facade.apply_seeds_reducer(
                    data=data,
                    categorical_cols=selected_categorical,
                    statistic_cols=selected_numeric,
                )

                st.success(f"Reduced from {len(data)} to {len(result_df)} rows!")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Original Rows", len(data))
                with col2:
                    st.metric("Reduced Rows", len(result_df))

                st.markdown("**Result Preview:**")
                st.dataframe(result_df.head(20), width="stretch")

                # Store result in session state for confirmation
                st.session_state["seeds_result"] = result_df

            except Exception as e:
                st.error(f"Error applying Seeds Reducer: {e}")

        # Separate confirmation button outside the first button's scope
        if "seeds_result" in st.session_state:
            if st.button("✓ Confirm and Apply Seeds Reducer", key="confirm_seeds", type="primary"):
                StateManager.set_data(st.session_state["seeds_result"])
                del st.session_state["seeds_result"]
                st.success("✓ Seeds-reduced data is now active!")
                st.rerun()

    def _show_outlier_remover(self):
        """Outlier Remover - Remove values above Q3."""
        st.markdown("### Outlier Remover")

        st.info(
            """
        **Outlier Remover** filters out outlier values based on the 3rd quartile (Q3).

        - Groups data by categorical columns
        - Calculates Q3 for the selected numeric column within each group
        - Removes rows where the value exceeds Q3 for that group
        - Helps remove extreme outliers from experiments
        """
        )

        # Get current data
        data = StateManager.get_data()

        if data is None:
            st.error("No data available. Please load data first.")
            return

        # Identify columns
        categorical_cols = data.select_dtypes(include=["object"]).columns.tolist()
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()

        if not numeric_cols:
            st.warning("No numeric columns found for outlier detection.")
            return

        st.markdown("**Configuration:**")

        col1, col2 = st.columns(2)
        with col1:
            outlier_column = st.selectbox(
                "Column to check for outliers", options=numeric_cols, key="outlier_col"
            )

        with col2:
            if categorical_cols:
                group_by_cols = st.multiselect(
                    "Group by columns (optional)",
                    options=categorical_cols,
                    default=(
                        categorical_cols[:3] if len(categorical_cols) >= 3 else categorical_cols
                    ),
                    key="outlier_groupby",
                )
            else:
                group_by_cols = []
                st.info("No categorical columns for grouping. Will use global Q3.")

        # Show current distribution
        st.markdown(f"**Current distribution of `{outlier_column}`:**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Min", f"{data[outlier_column].min():.4f}")
        with col2:
            st.metric("Q3", f"{data[outlier_column].quantile(0.75):.4f}")
        with col3:
            st.metric("Max", f"{data[outlier_column].max():.4f}")
        with col4:
            st.metric("Mean", f"{data[outlier_column].mean():.4f}")

        if st.button("Apply Outlier Remover", key="apply_outlier"):
            try:
                # Use the existing DataManager implementation via facade
                if group_by_cols:
                    filtered_df = self.facade.apply_outlier_remover(
                        data=data, outlier_column=outlier_column, categorical_cols=group_by_cols
                    )
                else:
                    # For global Q3, use pandas directly (simpler than DataManager)
                    Q3 = data[outlier_column].quantile(0.75)
                    filtered_df = data[data[outlier_column] <= Q3]

                removed_count = len(data) - len(filtered_df)
                st.success(
                    f"Removed {removed_count} outlier rows ({(removed_count/len(data)*100):.1f}%)"
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Original Rows", len(data))
                with col2:
                    st.metric("Filtered Rows", len(filtered_df))
                with col3:
                    st.metric("Removed", removed_count)

                st.markdown("**Filtered Data Preview:**")
                st.dataframe(filtered_df.head(20), width="stretch")

                # Store result in session state for confirmation
                st.session_state["outlier_result"] = filtered_df

            except Exception as e:
                st.error(f"Error applying Outlier Remover: {e}")

        # Separate confirmation button outside the first button's scope
        if "outlier_result" in st.session_state:
            if st.button(
                "✓ Confirm and Apply Outlier Remover", key="confirm_outlier", type="primary"
            ):
                StateManager.set_data(st.session_state["outlier_result"])
                del st.session_state["outlier_result"]
                st.success("✓ Outlier-filtered data is now active!")
                st.rerun()

    def _show_preprocessor(self):
        """Preprocessor/Mixer - Create new columns from operations."""
        st.markdown("### Preprocessor (Mixer)")

        st.info(
            """
        **Preprocessor** creates new columns by combining existing ones with mathematical
        operations.

        - **Divide**: Create ratios (e.g., IPC = instructions / cycles)
        - **Sum**: Add columns together (e.g., total_time = user_time + system_time)
        - Results are added as new columns to your dataset
        """
        )

        # Get current data
        data = StateManager.get_data()

        if data is None:
            st.error("No data available. Please load data first.")
            return

        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()

        if not numeric_cols:
            st.warning("No numeric columns found for preprocessing.")
            return

        st.markdown("**Create New Column:**")

        col1, col2, col3 = st.columns(3)

        with col1:
            src_col1 = st.selectbox("Source Column 1", options=numeric_cols, key="preproc_src1")

        with col2:
            operation = st.selectbox("Operation", options=["divide", "sum"], key="preproc_op")

        with col3:
            src_col2 = st.selectbox("Source Column 2", options=numeric_cols, key="preproc_src2")

        # Generate default name
        if operation == "divide":
            default_name = f"{src_col1}_per_{src_col2}"
        else:
            default_name = f"{src_col1}_plus_{src_col2}"

        new_col_name = st.text_input("New column name", value=default_name, key="preproc_name")

        if st.button("Preview Result", key="preview_preproc"):
            try:
                # Use the existing DataManager implementation via facade
                preview_data = self.facade.apply_preprocessor(
                    data=data,
                    operation=operation,
                    src_col1=src_col1,
                    src_col2=src_col2,
                    dst_col=new_col_name,
                )

                st.success(f"Created column `{new_col_name}`!")

                st.markdown("**Preview with new column:**")
                preview_cols = [src_col1, src_col2, new_col_name]
                st.dataframe(preview_data[preview_cols].head(10), width="stretch")

                st.markdown("**Statistics:**")
                st.dataframe(preview_data[new_col_name].describe().to_frame(), width="stretch")

                # Store result in session state for confirmation
                st.session_state["preproc_result"] = preview_data

            except Exception as e:
                st.error(f"Error creating column: {e}")

        # Separate confirmation button outside the first button's scope
        if "preproc_result" in st.session_state:
            if st.button(
                "✓ Confirm and Add Column to Dataset", key="confirm_preproc", type="primary"
            ):
                StateManager.set_data(st.session_state["preproc_result"])
                del st.session_state["preproc_result"]
                st.success("✓ Column added to dataset!")
                st.rerun()

    def _show_filter_options(self, data: pd.DataFrame):
        """Show filtering options with live preview."""
        st.markdown("### Filter Data")

        st.markdown("Apply filters to subset your data:")

        # Column-based filtering
        filter_column = st.selectbox("Select column to filter", options=data.columns.tolist())

        if filter_column:
            col_data = data[filter_column]

            # Different filter types based on column type
            if pd.api.types.is_numeric_dtype(col_data):
                st.markdown(f"**Numeric filter for `{filter_column}`:**")

                min_val = float(col_data.min())
                max_val = float(col_data.max())

                col1, col2 = st.columns(2)
                with col1:
                    filter_min = st.number_input("Minimum value", value=min_val, key="filter_min")
                with col2:
                    filter_max = st.number_input("Maximum value", value=max_val, key="filter_max")

                if st.button("Apply Numeric Filter"):
                    filtered_data = data[
                        (data[filter_column] >= filter_min) & (data[filter_column] <= filter_max)
                    ]
                    self._show_filter_result(data, filtered_data)

            else:
                st.markdown(f"**Categorical filter for `{filter_column}`:**")

                unique_values = col_data.unique().tolist()
                selected_values = st.multiselect(
                    "Select values to keep",
                    options=unique_values,
                    default=unique_values[: min(5, len(unique_values))],
                )

                if st.button("Apply Categorical Filter"):
                    filtered_data = data[data[filter_column].isin(selected_values)]
                    self._show_filter_result(data, filtered_data)

    def _show_filter_result(self, original: pd.DataFrame, filtered: pd.DataFrame):
        """Show filtering results."""
        st.markdown("---")
        st.markdown("### Filter Results")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Original Rows", len(original))
        with col2:
            st.metric("Filtered Rows", len(filtered))
        with col3:
            percentage = (len(filtered) / len(original)) * 100
            st.metric("Retained", f"{percentage:.1f}%")

        st.markdown("**Filtered Data Preview:**")
        st.dataframe(filtered.head(20), width="stretch")

        if st.button("Use Filtered Data"):
            StateManager.set_data(filtered)
            st.success("Filtered data is now your active dataset!")
            st.rerun()

    def _show_transform_options(self, data: pd.DataFrame):
        """Show transformation options."""
        st.markdown("### Transform Data")

        transform_type = st.selectbox(
            "Select transformation",
            [
                "Add Column",
                "Rename Column",
                "Drop Columns",
                "Change Data Type",
                "Fill Missing Values",
            ],
        )

        if transform_type == "Add Column":
            self._add_column_transform(data)
        elif transform_type == "Rename Column":
            self._rename_column_transform(data)
        elif transform_type == "Drop Columns":
            self._drop_columns_transform(data)
        elif transform_type == "Change Data Type":
            self._change_dtype_transform(data)
        elif transform_type == "Fill Missing Values":
            self._fill_missing_transform(data)

    def _add_column_transform(self, data: pd.DataFrame):
        """Add a new column."""
        st.markdown("#### Add New Column")

        new_col_name = st.text_input("New column name")

        col1, col2 = st.columns(2)
        with col1:
            col_a = st.selectbox("Select column A", options=data.columns.tolist(), key="add_col_a")
        with col2:
            operation = st.selectbox("Operation", ["+", "-", "*", "/", "constant"])

        if operation != "constant":
            col_b = st.selectbox("Select column B", options=data.columns.tolist(), key="add_col_b")
            constant_val = None
        else:
            col_b = None
            constant_val = st.number_input("Constant value", value=1.0)

        if st.button("Add Column"):
            try:
                transformed_data = data.copy()

                if operation == "+":
                    if col_b:
                        transformed_data[new_col_name] = data[col_a] + data[col_b]
                elif operation == "-":
                    if col_b:
                        transformed_data[new_col_name] = data[col_a] - data[col_b]
                elif operation == "*":
                    if col_b:
                        transformed_data[new_col_name] = data[col_a] * data[col_b]
                elif operation == "/":
                    if col_b:
                        transformed_data[new_col_name] = data[col_a] / data[col_b]
                elif operation == "constant":
                    if constant_val is not None:
                        transformed_data[new_col_name] = constant_val

                st.success(f"Column `{new_col_name}` added!")
                st.dataframe(transformed_data.head(10), width="stretch")

                if st.button("Apply Transformation"):
                    StateManager.set_data(transformed_data)
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    def _rename_column_transform(self, data: pd.DataFrame):
        """Rename a column."""
        st.markdown("#### Rename Column")

        col1, col2 = st.columns(2)
        with col1:
            old_name = st.selectbox("Column to rename", options=data.columns.tolist())
        with col2:
            new_name = st.text_input("New name", value=old_name)

        if st.button("Rename Column"):
            transformed_data = data.rename(columns={old_name: new_name})
            st.success(f"Column `{old_name}` renamed to `{new_name}`!")
            st.dataframe(transformed_data.head(5), width="stretch")

            if st.button("Apply Transformation", key="apply_rename"):
                StateManager.set_data(transformed_data)
                st.rerun()

    def _drop_columns_transform(self, data: pd.DataFrame):
        """Drop columns."""
        st.markdown("#### Drop Columns")

        columns_to_drop = st.multiselect("Select columns to drop", options=data.columns.tolist())

        if columns_to_drop and st.button("Drop Columns"):
            transformed_data = data.drop(columns=columns_to_drop)
            st.success(f"Dropped {len(columns_to_drop)} column(s)!")
            st.dataframe(transformed_data.head(5), width="stretch")

            if st.button("Apply Transformation", key="apply_drop"):
                StateManager.set_data(transformed_data)
                st.rerun()

    def _change_dtype_transform(self, data: pd.DataFrame):
        """Change column data type."""
        st.markdown("#### Change Data Type")

        col1, col2 = st.columns(2)
        with col1:
            column = st.selectbox("Select column", options=data.columns.tolist(), key="dtype_col")
        with col2:
            new_dtype = st.selectbox("New data type", ["int", "float", "str", "category"])

        if st.button("Change Type"):
            try:
                transformed_data = data.copy()
                if new_dtype == "int":
                    transformed_data[column] = transformed_data[column].astype(int)
                elif new_dtype == "float":
                    transformed_data[column] = transformed_data[column].astype(float)
                elif new_dtype == "str":
                    transformed_data[column] = transformed_data[column].astype(str)
                elif new_dtype == "category":
                    transformed_data[column] = transformed_data[column].astype("category")

                st.success(f"Column `{column}` converted to {new_dtype}!")
                st.dataframe(transformed_data.head(5), width="stretch")

                if st.button("Apply Transformation", key="apply_dtype"):
                    StateManager.set_data(transformed_data)
                    st.rerun()
            except Exception as e:
                st.error(f"Error converting type: {e}")

    def _fill_missing_transform(self, data: pd.DataFrame):
        """Fill missing values."""
        st.markdown("#### Fill Missing Values")

        # Show columns with missing values
        null_counts = data.isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0]

        if cols_with_nulls.empty:
            st.info("No missing values in the dataset!")
            return

        st.markdown("**Columns with missing values:**")
        st.dataframe(cols_with_nulls.to_frame("Missing Count"), width="stretch")

        column = st.selectbox("Select column to fill", options=cols_with_nulls.index.tolist())

        fill_method = st.selectbox(
            "Fill method", ["Mean", "Median", "Mode", "Constant", "Forward Fill", "Backward Fill"]
        )

        fill_value = None
        if fill_method == "Constant":
            fill_value = st.text_input("Fill value")

        if st.button("Fill Missing Values"):
            try:
                transformed_data = data.copy()

                if fill_method == "Mean":
                    transformed_data[column].fillna(transformed_data[column].mean(), inplace=True)
                elif fill_method == "Median":
                    transformed_data[column].fillna(transformed_data[column].median(), inplace=True)
                elif fill_method == "Mode":
                    transformed_data[column].fillna(
                        transformed_data[column].mode()[0], inplace=True
                    )
                elif fill_method == "Constant":
                    if fill_value is not None:
                        transformed_data[column].fillna(fill_value, inplace=True)
                elif fill_method == "Forward Fill":
                    transformed_data[column] = transformed_data[column].ffill()
                elif fill_method == "Backward Fill":
                    transformed_data[column] = transformed_data[column].bfill()

                st.success(f"Missing values filled in `{column}`!")
                st.dataframe(transformed_data.head(10), width="stretch")

                if st.button("Apply Transformation", key="apply_fill"):
                    StateManager.set_data(transformed_data)
                    st.rerun()
            except Exception as e:
                st.error(f"Error filling values: {e}")


def show_data_managers_page():
    """Entry point for data managers page - creates facade and renders page."""
    facade = BackendFacade()
    page = DataManagersPage(facade)
    page.render()
