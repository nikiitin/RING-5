"""Data-manager UI for combining columns."""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.core.models.history_models import OperationRecord
from src.web.components.common.history_components import HistoryComponents
from src.web.components.data_managers.data_manager import DataManager
from src.web.state.ui_state_manager import UIStateManager, WidgetKeyBuilder


class MixerManager(DataManager):
    """Manager for merging multiple columns with standard deviation propagation."""

    @property
    def name(self) -> str:
        """Return the manager's display name."""
        return "Mixer (Merge Columns)"

    def render(self) -> None:
        """Render the Mixer UI."""
        st.markdown("### Mixer (Merge Columns)")

        st.info("""
        **Mixer** aggregates multiple columns into one by applying an operation (Sum or Mean).

        - **Automatic Error Propagation**: If columns have associated `.sd` or `_stdev` columns,
          the new standard deviation is calculated using standard error formulas:
          - Sum: sqrt(sd1^2 + sd2^2 + ...)
          - Mean: sqrt(sd1^2 + sd2^2 + ...) / N
        """)

        data = self.get_data()
        if data is None:
            st.error("No data loaded.")
            return

        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()

        # Handle loaded operation from history
        loaded = UIStateManager().manager.consume_load_trigger("mixer")
        if loaded is not None:
            op_raw = loaded["operation"].replace("Mixer: ", "")
            if op_raw == "Concatenate":
                self._restore_selection("mixer", "mode", "Configuration Merge")
                available = data.columns.tolist()
            else:
                self._restore_selection("mixer", "mode", "Numerical Operations")
                available = [c for c in numeric_cols if not c.endswith((".sd", "_stdev"))]
            src_cols = loaded["source_columns"]
            valid_src = [c for c in src_cols if c in available]
            self._warn_removed_columns([c for c in src_cols if c not in available])
            self._restore_selection("mixer", "select_cols", valid_src)
            if loaded["dest_columns"]:
                self._restore_selection("mixer", "new_name", loaded["dest_columns"][0])
            if op_raw in ["Sum", "Mean (Average)", "Concatenate"]:
                self._restore_selection("mixer", "op", op_raw)

        st.markdown("#### Configuration")

        mode = st.segmented_control(
            "Mixer Mode",
            ["Numerical Operations", "Configuration Merge"],
            default="Numerical Operations",
            key=WidgetKeyBuilder.manager_key("mixer", "mode"),
        )

        if mode is None:
            st.info("Select a mode to continue.")
            return

        if mode == "Numerical Operations":
            available_cols = [c for c in numeric_cols if not c.endswith((".sd", "_stdev"))]
            operations = ["Sum", "Mean (Average)"]
        else:
            # Configuration labels may combine numeric and text columns.
            available_cols = data.columns.tolist()
            operations = ["Concatenate"]

        col_select_1, col_select_2 = st.columns(2)

        with col_select_1:
            selected_cols = st.multiselect(
                "Select columns to merge",
                options=available_cols,
                key=WidgetKeyBuilder.manager_key("mixer", "select_cols"),
            )

        with col_select_2:
            operation = st.selectbox(
                "Operation", operations, key=WidgetKeyBuilder.manager_key("mixer", "op")
            )

        if operation is None:
            return

        separator = "_"
        if operation == "Concatenate":
            separator = st.text_input(
                "Separator", value="_", key=WidgetKeyBuilder.manager_key("mixer", "sep")
            )

        default_name_parts = selected_cols[:2] if selected_cols else ["merged"]
        if operation == "Concatenate":
            default_name = f"concat_{separator.join(default_name_parts)}"
        else:
            default_name = f"{operation.lower()}_{'_'.join(default_name_parts)}"

        new_col_name = st.text_input(
            "New Column Name",
            value=default_name,
            key=WidgetKeyBuilder.manager_key("mixer", "new_name"),
        )

        if st.button("Preview Merge", key=WidgetKeyBuilder.manager_key("mixer", "preview")):
            # Validate inputs first
            validation_errors = self.api.managers.validate_merge_inputs(
                df=data,
                columns=selected_cols,
                operation=operation,
                new_column_name=new_col_name,
            )

            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                return

            try:
                result_df = self.api.managers.apply_mixer(
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

                # Store in PreviewRepository via api
                self.api.set_preview("mixer", result_df)

            except Exception as e:
                st.exception(e)

        # Separate confirmation
        if self.api.has_preview("mixer"):
            if st.button(
                "Confirm and Merge",
                key=WidgetKeyBuilder.manager_key("mixer", "confirm"),
                type="primary",
            ):
                confirmed_df: pd.DataFrame | None = self.api.get_preview("mixer")
                if confirmed_df is not None:
                    self.set_data(confirmed_df)
                    self.api.clear_preview("mixer")
                    record: OperationRecord = {
                        "source_columns": selected_cols,
                        "dest_columns": [new_col_name],
                        "operation": f"Mixer: {operation}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    self.api.add_manager_history_record(record)
                    st.toast("✓ Merged data active!", icon="✅")
                    # ``set_data`` changes shared data; an app rerun updates sibling fragments.
                    # don't keep rendering the previously-captured dataframe.
                    st.rerun(scope="app")

        # Show manager-specific history with Load / Delete
        HistoryComponents.render_manager_history(
            self.api.get_manager_history(),
            "Mixer",
            WidgetKeyBuilder.manager_key("mixer", "load_trigger"),
            self.api.remove_manager_history_record,
        )
