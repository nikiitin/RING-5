"""
Seeds Reducer Manager
"""

import streamlit as st

from src.web.ui.data_managers.base_manager import DataManager


class SeedsReducerManager(DataManager):
    """Manager for aggregating data across random seeds."""

    @property
    def name(self) -> str:
        return "Seeds Reducer"

    def render(self):
        """Render the Seeds Reducer UI."""
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
        data = self.get_data()

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
                # Use DataProcessingService
                from src.web.services.data_processing_service import (
                    DataProcessingService,
                )

                result_df = DataProcessingService.reduce_seeds(
                    df=data,
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
            if st.button("Confirm and Apply Seeds Reducer", key="confirm_seeds", type="primary"):
                self.set_data(st.session_state["seeds_result"])
                del st.session_state["seeds_result"]
                st.success("✓ Seeds-reduced data is now active!")
                st.rerun()
