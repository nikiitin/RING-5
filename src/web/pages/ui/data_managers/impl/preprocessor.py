"""
Preprocessor Manager
"""

from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import streamlit as st

from src.core.models.history_models import OperationRecord
from src.web.pages.ui.components.history_components import HistoryComponents
from src.web.pages.ui.data_managers.data_manager import DataManager


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

        # Handle loaded operation from history
        loaded = st.session_state.pop("_preproc_load", None)
        if loaded is not None:
            op_str = loaded["operation"].replace("Preprocessor: ", "")
            operators = self.api.managers.list_operators()
            if op_str in operators:
                st.session_state["preproc_op"] = op_str
            src_cols = loaded["source_columns"]
            valid_src = [c for c in src_cols if c in numeric_cols]
            missing = [c for c in src_cols if c not in numeric_cols]
            if missing:
                st.warning(f"Columns removed (not in current data): {', '.join(missing)}")
            if len(valid_src) >= 1:
                st.session_state["preproc_src1"] = valid_src[0]
            if len(valid_src) >= 2:
                st.session_state["preproc_src2"] = valid_src[1]
            if loaded["dest_columns"]:
                st.session_state["preproc_name"] = loaded["dest_columns"][0]

        st.markdown("**Create New Column:**")

        col1, col2, col3 = st.columns(3)

        with col1:
            src_col1 = st.selectbox("Source Column 1", options=numeric_cols, key="preproc_src1")

        with col2:
            operation = st.selectbox(
                "Operation", options=self.api.managers.list_operators(), key="preproc_op"
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
                preview_data = self.api.managers.apply_operation(
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
                    record: OperationRecord = {
                        "source_columns": [src_col1, src_col2],
                        "dest_columns": [new_col_name],
                        "operation": f"Preprocessor: {operation}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    self.api.add_manager_history_record(record)
                    st.success("✓ Column added to dataset!")
                    st.rerun()

        # Show this manager's history
        HistoryComponents.render_manager_history(
            self.api.get_manager_history(),
            "Preprocessor",
            "_preproc_load",
            self.api.remove_manager_history_record,
        )
