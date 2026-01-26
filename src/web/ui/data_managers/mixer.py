"""
Mixer Manager
"""

import streamlit as st

from src.web.services.data_processing_service import DataProcessingService
from src.web.ui.data_managers.base_manager import DataManager


class MixerManager(DataManager):
    """Manager for merging multiple columns with standard deviation propagation."""

    @property
    def name(self) -> str:
        return "Mixer (Merge Columns)"

    def render(self):
        """Render the Mixer UI."""
        st.markdown("### Mixer (Merge Columns)")

        st.info(
            """
        **Mixer** aggregates multiple columns into one by applying an operation (Sum or Mean).
        
        - **Automatic Error Propagation**: If columns have associated `.sd` or `_stdev` columns, 
          the new standard deviation is calculated using standard error formulas:
          - Sum: sqrt(sd1^2 + sd2^2 + ...)
          - Mean: sqrt(sd1^2 + sd2^2 + ...) / N
        """
        )

        data = self.get_data()
        if data is None:
            st.error("No data loaded.")
            return

        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()

        # Filter out likely SD columns to reduce clutter, but allow selecting them just in case
        [c for c in numeric_cols if not c.endswith((".sd", "_stdev"))]

        st.markdown("#### Configuration")

        mode = st.radio(
            "Mixer Mode",
            ["Numerical Operations", "Configuration Merge"],
            horizontal=True,
            key="mixer_mode",
        )

        if mode == "Numerical Operations":
            available_cols = [c for c in numeric_cols if not c.endswith((".sd", "_stdev"))]
            operations = ["Sum", "Mean (Average)"]
        else:
            # For configuration, allow all columns but prioritize string/object
            # Actually, usually config cols are object/string.
            # Include all columns to allow concatenating numbers to strings

            available_cols = data.columns.tolist()
            operations = ["Concatenate"]

        col_select_1, col_select_2 = st.columns(2)

        with col_select_1:
            selected_cols = st.multiselect(
                "Select columns to merge", options=available_cols, key="mixer_select_cols"
            )

        with col_select_2:
            operation = st.selectbox("Operation", operations, key="mixer_op")

        separator = "_"
        if operation == "Concatenate":
            separator = st.text_input("Separator", value="_", key="mixer_sep")

        default_name_parts = selected_cols[:2] if selected_cols else ["merged"]
        if operation == "Concatenate":
            default_name = f"concat_{separator.join(default_name_parts)}"
        else:
            default_name = f"{operation.lower()}_{'_'.join(default_name_parts)}"

        new_col_name = st.text_input("New Column Name", value=default_name, key="mixer_new_name")

        if st.button("Preview Merge", key="mixer_preview"):
            if len(selected_cols) < 2:
                st.warning("Please select at least 2 columns to merge.")
                return

            try:
                result_df = DataProcessingService.apply_mixer(
                    df=data,
                    dest_col=new_col_name,
                    source_cols=selected_cols,
                    operation=operation,
                    separator=separator,
                )

                st.success(f"Created merged column `{new_col_name}`")

                # Check if SD column created
                new_sd_col = f"{new_col_name}.sd"
                cols_to_show = [new_col_name]
                if new_sd_col in result_df.columns:
                    cols_to_show.append(new_sd_col)
                    st.success(f"✓ Propagated standard deviation to `{new_sd_col}`")

                st.dataframe(result_df[cols_to_show].head(), width="stretch")

                st.session_state["mixer_result"] = result_df

            except Exception as e:
                st.error(f"Error during merge: {e}")

        # Separate confirmation
        if "mixer_result" in st.session_state:
            if st.button("Confirm and Merge", key="confirm_mixer", type="primary"):
                self.set_data(st.session_state["mixer_result"])
                del st.session_state["mixer_result"]
                st.success("✓ Merged data active!")
                st.rerun()
