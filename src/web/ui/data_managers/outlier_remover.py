"""
Outlier Remover Manager
"""

import streamlit as st
from src.web.ui.data_managers.base_manager import DataManager


class OutlierRemoverManager(DataManager):
    """Manager for removing outliers based on IQR."""

    @property
    def name(self) -> str:
        return "Outlier Remover"

    def render(self):
        """Render the Outlier Remover UI."""
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
        data = self.get_data()

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
                "Confirm and Apply Outlier Remover", key="confirm_outlier", type="primary"
            ):
                self.set_data(st.session_state["outlier_result"])
                del st.session_state["outlier_result"]
                st.success("✓ Outlier-filtered data is now active!")
                st.rerun()
