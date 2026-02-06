"""
Preprocessor Manager
"""

from typing import Optional

import pandas as pd
import streamlit as st

from src.core.services.arithmetic_service import ArithmeticService
from src.web.pages.ui.data_managers.base_manager import DataManager


class PreprocessorManager(DataManager):
    """Manager for creating new columns via basic arithmetic."""

    @property
    def name(self) -> str:
        return "Preprocessor (Basic)"

    def render(self) -> None:
        """Render the Preprocessor UI."""
        st.markdown("### Preprocessor (Basic)")

        st.info("""
        **Preprocessor** creates new columns by combining existing ones with mathematical
        operations.

        - **Divide**: Create ratios (e.g., IPC = instructions / cycles)
        - **Sum**: Add columns together (e.g., total_time = user_time + system_time)
        - Results are added as new columns to your dataset
        """)

        # Get current data
        data = self.get_data()

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
            operation = st.selectbox(
                "Operation", options=ArithmeticService.list_operators(), key="preproc_op"
            )

        with col3:
            src_col2 = st.selectbox("Source Column 2", options=numeric_cols, key="preproc_src2")

        # Generate default name
        op_lower = operation.lower()
        if op_lower in ["division", "divide"]:
            default_name = f"{src_col1}_per_{src_col2}"
        elif op_lower in ["sum", "add"]:
            default_name = f"{src_col1}_plus_{src_col2}"
        elif op_lower in ["subtraction", "subtract"]:
            default_name = f"{src_col1}_minus_{src_col2}"
        elif op_lower in ["multiplication", "multiply"]:
            default_name = f"{src_col1}_prod_{src_col2}"
        else:
            default_name = "new_column"

        new_col_name = st.text_input("New column name", value=default_name, key="preproc_name")

        if st.button("Preview Result", key="preview_preproc"):
            try:
                preview_data = ArithmeticService.apply_operation(
                    df=data,
                    operation=operation,
                    src1=src_col1,
                    src2=src_col2,
                    dest=new_col_name,
                )

                st.success(f"Created column `{new_col_name}`!")

                st.markdown("**Preview with new column:**")
                preview_cols = [src_col1, src_col2, new_col_name]
                st.dataframe(preview_data[preview_cols].head(10), width="stretch")

                st.markdown("**Statistics:**")
                st.dataframe(preview_data[new_col_name].describe().to_frame(), width="stretch")

                # Store in PreviewRepository via api
                self.api.set_preview("preprocessor", preview_data)

            except Exception as e:
                st.error(f"Error creating column: {e}")

        # Separate confirmation button outside the first button's scope
        if self.api.has_preview("preprocessor"):
            if st.button(
                "Confirm and Add Column to Dataset", key="confirm_preproc", type="primary"
            ):
                confirmed_data: Optional[pd.DataFrame] = self.api.get_preview("preprocessor")
                if confirmed_data is not None:
                    self.set_data(confirmed_data)
                    self.api.clear_preview("preprocessor")
                    st.success("✓ Column added to dataset!")
                    st.rerun()
