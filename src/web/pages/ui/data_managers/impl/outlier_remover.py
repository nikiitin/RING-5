"""
Outlier Remover Manager
"""

from typing import Optional

import pandas as pd
import streamlit as st

from src.web.pages.ui.data_managers.data_manager import DataManager


class OutlierRemoverManager(DataManager):
    """Manager for removing outliers based on IQR."""

    @property
    def name(self) -> str:
        return "Outlier Remover"

    def render(self) -> None:
        """Render the Outlier Remover UI."""
        st.markdown("### Outlier Remover")

        st.info("""
        **Outlier Remover** filters out outlier values based on the 3rd quartile (Q3).

        - Groups data by categorical columns
        - Calculates Q3 for the selected numeric column within each group
        - Removes rows where the value exceeds Q3 for that group
        - Helps remove extreme outliers from experiments
        """)

        # Get current data
        data = self.get_data()

        if data is None:
            st.error("No data available. Please load data first.")
            return

        # Identify columns
        categorical_cols = data.select_dtypes(include=["object", "string"]).columns.tolist()
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
                # Intelligent default: Exclude "random_seed" from grouping as it defeats outlier detection  # noqa: E501
                # (grouping by seed means 1 item per group -> no outliers)
                default_cols = [
                    c for c in categorical_cols if c != "random_seed" and "seed" not in c.lower()
                ]
                # Fallback if everything was filtered out (unlikely) or take top 3
                if not default_cols:
                    default_cols = categorical_cols[:3]
                else:
                    default_cols = default_cols[:3]

                group_by_cols = st.multiselect(
                    "Group by columns (optional)",
                    options=categorical_cols,
                    default=default_cols,
                    key="outlier_groupby",
                    help="Columns to group data by before calculating Q3. Do NOT include 'random_seed' here!",  # noqa: E501
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
            # Validate inputs first
            validation_errors = self.api.compute.validate_outlier_inputs(
                df=data,
                outlier_col=outlier_column,
                group_by_cols=group_by_cols,
            )

            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                return

            try:
                filtered_df = self.api.compute.remove_outliers(
                    df=data, outlier_col=outlier_column, group_by_cols=group_by_cols
                )

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

                # Store in PreviewRepository via api
                self.api.set_preview("outlier_removal", filtered_df)

            except Exception as e:
                st.error(f"Error applying Outlier Remover: {e}")

        # Separate confirmation button outside the first button's scope
        if self.api.has_preview("outlier_removal"):
            if st.button(
                "Confirm and Apply Outlier Remover", key="confirm_outlier", type="primary"
            ):
                confirmed_df: Optional[pd.DataFrame] = self.api.get_preview("outlier_removal")
                if confirmed_df is not None:
                    self.set_data(confirmed_df)
                    self.api.clear_preview("outlier_removal")
                    st.success("✓ Outlier-filtered data is now active!")
                    st.rerun()
