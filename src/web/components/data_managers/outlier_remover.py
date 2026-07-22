"""Data-manager UI for IQR outlier removal."""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.core.models.history_models import OperationRecord
from src.web.components.common.history_components import HistoryComponents
from src.web.components.data_managers.data_manager import DataManager
from src.web.state.ui_state_manager import UIStateManager, WidgetKeyBuilder


class OutlierRemoverManager(DataManager):
    """Manager for removing outliers based on IQR."""

    @property
    def name(self) -> str:
        """Return the manager's display name."""
        return "Outlier Remover"

    def render(self) -> None:
        """Render the Outlier Remover UI."""
        # [impl->req~ring5.data.outlier-removal~1]
        # [impl->req~ring5.data.preview-confirm~1]
        st.markdown("### Outlier Remover")

        st.info("""
        **Outlier Remover** removes statistical outliers using the IQR
        (interquartile range) method.

        - Groups data by the selected categorical columns
        - Within each group, computes Q1, Q3, and IQR = Q3 − Q1 for the numeric column
        - Removes rows outside [Q1 − 1.5·IQR, Q3 + 1.5·IQR]
        - Helps drop extreme outliers from experiment results
        """)

        # Get current data
        data = self.get_data()

        if data is None:
            st.error("No data available. Please load data first.")
            return

        # Identify columns (shared classifier — includes category dtype)
        from src.web.components.common.data_components import detect_column_types

        numeric_cols, categorical_cols = detect_column_types(data)

        if not numeric_cols:
            st.warning("No numeric columns found for outlier detection.")
            return

        # Handle loaded operation from history
        loaded = UIStateManager().manager.consume_load_trigger("outlier_remover")
        if loaded is not None:
            src_cols = loaded["source_columns"]
            dest_cols = loaded["dest_columns"]
            outlier_col = dest_cols[0] if dest_cols else None
            group_by = [c for c in src_cols if c not in set(dest_cols)]
            all_missing = []
            if outlier_col and outlier_col in numeric_cols:
                self._restore_selection("outlier_remover", "col", outlier_col)
            elif outlier_col:
                all_missing.append(outlier_col)
            valid_groups = [c for c in group_by if c in categorical_cols]
            all_missing.extend([c for c in group_by if c not in categorical_cols])
            self._restore_selection("outlier_remover", "groupby", valid_groups)
            self._warn_removed_columns(all_missing)

        st.markdown("**Configuration:**")

        col1, col2 = st.columns(2)
        with col1:
            outlier_column_raw = st.selectbox(
                "Column to check for outliers",
                options=numeric_cols,
                key=WidgetKeyBuilder.manager_key("outlier_remover", "col"),
            )
            outlier_column: str = str(outlier_column_raw) if outlier_column_raw is not None else ""

        with col2:
            if categorical_cols:
                # Seed-like columns create one-row groups, for which IQR filtering is ineffective.
                seed_patterns = ("seed", "iteration", "run_id")
                default_cols = [
                    c for c in categorical_cols if not any(p in c.lower() for p in seed_patterns)
                ]
                if not default_cols:
                    default_cols = categorical_cols[:3]
                else:
                    default_cols = default_cols[:3]

                group_by_cols: list[str] = [
                    str(c)
                    for c in st.multiselect(
                        "Group by columns (optional)",
                        options=categorical_cols,
                        default=default_cols,
                        key=WidgetKeyBuilder.manager_key("outlier_remover", "groupby"),
                        help=(
                            "Columns to group data by before"
                            " computing IQR bounds. Avoid including"
                            " seed or iteration columns!"
                        ),
                    )
                ]
            else:
                group_by_cols = []
                st.info("No categorical columns for grouping. Will use global IQR bounds.")

        # Show current distribution
        st.markdown(f"**Current distribution of `{outlier_column}`:**")
        # Show Q1 and Q3 (not the mean) so the user can eyeball the IQR fences
        # [Q1 - 1.5·IQR, Q3 + 1.5·IQR] this manager applies (global distribution).
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Min", f"{data[outlier_column].min():.4f}")
        with col2:
            st.metric("Q1", f"{data[outlier_column].quantile(0.25):.4f}")
        with col3:
            st.metric("Q3", f"{data[outlier_column].quantile(0.75):.4f}")
        with col4:
            st.metric("Max", f"{data[outlier_column].max():.4f}")

        if st.button(
            "Apply Outlier Remover",
            key=WidgetKeyBuilder.manager_key("outlier_remover", "apply"),
        ):
            # Validate inputs first
            validation_errors = self.api.managers.validate_outlier_inputs(
                df=data,
                outlier_col=outlier_column,
                group_by_cols=group_by_cols,
            )

            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                return

            try:
                filtered_df = self.api.managers.remove_outliers(
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
                st.exception(e)

        # Separate confirmation button outside the first button's scope
        if self.api.has_preview("outlier_removal"):
            if st.button(
                "Confirm and Apply Outlier Remover",
                key=WidgetKeyBuilder.manager_key("outlier_remover", "confirm"),
                type="primary",
            ):
                confirmed_df: pd.DataFrame | None = self.api.get_preview("outlier_removal")
                if confirmed_df is not None:
                    self.set_data(
                        confirmed_df,
                        operation="Outlier Removal (IQR)",
                    )
                    self.api.clear_preview("outlier_removal")
                    record: OperationRecord = {
                        "source_columns": [outlier_column] + group_by_cols,
                        "dest_columns": [outlier_column],
                        "operation": "Outlier Removal (IQR)",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    self.api.add_manager_history_record(record)
                    st.toast("✓ Outlier-filtered data is now active!", icon="✅")
                    # ``set_data`` changes shared data; an app rerun updates sibling fragments.
                    # don't keep rendering the previously-captured dataframe.
                    st.rerun(scope="app")

        # Show manager-specific history with Load / Delete
        HistoryComponents.render_manager_history(
            self.api.get_manager_history(),
            "Outlier",
            WidgetKeyBuilder.manager_key("outlier_remover", "load_trigger"),
            self.api.remove_manager_history_record,
        )
