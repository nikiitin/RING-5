"""
Seeds Reducer Manager
"""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.core.models.history_models import OperationRecord
from src.web.components.common.history_components import HistoryComponents
from src.web.components.data_managers.data_manager import DataManager
from src.web.state.ui_state_manager import UIStateManager, WidgetKeyBuilder


class SeedsReducerManager(DataManager):
    """Manager for aggregating data across random seeds."""

    @property
    def name(self) -> str:
        return "Seeds Reducer"

    def render(self) -> None:
        """Render the Seeds Reducer UI."""
        st.markdown("### Seeds Reducer")

        st.info(
            "**Seeds Reducer** groups data by a selected column and "
            "calculates statistics (mean + standard deviation) across "
            "its values.\n\n"
            "- Choose which column to reduce over "
            "(e.g. `random_seed`, `iteration`, `run_id`)\n"
            "- Groups by remaining categorical columns\n"
            "- Calculates mean and standard deviation for numeric columns\n"
            "- Useful for averaging results across multiple simulation runs"
        )

        # Get current data
        data = self.get_data()

        if data is None:
            st.error("No data available. Please load data first.")
            return

        # Build list of candidate columns to reduce over.
        # Candidates: any column with <=50 unique values OR object/string dtype.
        all_columns: list[str] = list(data.columns)
        candidate_cols: list[str] = [
            c for c in all_columns if data[c].nunique() <= 50 or data[c].dtype == "object"
        ]

        if not candidate_cols:
            st.warning(
                "No suitable columns found for reduction. "
                "Reduction works best with categorical columns or "
                "columns with few unique values."
            )
            return

        # Auto-select random_seed when present for backward compatibility
        default_idx: int = 0
        if "random_seed" in candidate_cols:
            default_idx = candidate_cols.index("random_seed")

        reduce_col: str = str(
            st.selectbox(
                "Column to reduce over",
                options=candidate_cols,
                index=default_idx,
                help=(
                    "Select the column whose values will be aggregated "
                    "(e.g. random_seed, iteration, run_id)"
                ),
                key=WidgetKeyBuilder.manager_key("seeds_reducer", "target_column"),
            )
        )

        # Identify categorical and numeric columns (shared classifier — includes category
        # dtype), excluding the reduction target column.
        from src.web.components.common.data_components import detect_column_types

        all_numeric, all_categorical = detect_column_types(data)
        categorical_cols = [c for c in all_categorical if c != reduce_col]
        numeric_cols = [c for c in all_numeric if c != reduce_col]

        if not categorical_cols:
            st.warning("No categorical columns found for grouping.")
            return

        if not numeric_cols:
            st.warning("No numeric columns found to calculate statistics.")
            return

        # Handle loaded operation from history
        loaded = UIStateManager().manager.consume_load_trigger("seeds_reducer")
        if loaded is not None:
            loaded_numeric = loaded["dest_columns"]
            loaded_categorical = [
                c for c in loaded["source_columns"] if c not in set(loaded_numeric)
            ]
            valid_cat = [c for c in loaded_categorical if c in categorical_cols]
            valid_num = [c for c in loaded_numeric if c in numeric_cols]
            missing = [c for c in loaded_categorical if c not in categorical_cols]
            missing += [c for c in loaded_numeric if c not in numeric_cols]
            self._warn_removed_columns(missing)
            self._restore_selection("seeds_reducer", "categorical", valid_cat)
            self._restore_selection("seeds_reducer", "numeric", valid_num)

        st.markdown("**Configuration:**")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Categorical columns (for grouping):**")
            selected_categorical = st.multiselect(
                "Group by columns",
                options=categorical_cols,
                default=categorical_cols,
                key=WidgetKeyBuilder.manager_key("seeds_reducer", "categorical"),
            )

        with col2:
            st.markdown("**Numeric columns (for statistics):**")
            selected_numeric = st.multiselect(
                "Calculate stats for",
                options=numeric_cols,
                default=numeric_cols,
                key=WidgetKeyBuilder.manager_key("seeds_reducer", "numeric"),
            )

        st.info("""
        **Note on Standard Deviation:**
        - Seeds Reducer will create `.sd` columns for standard deviations
        - When you later normalize data (in Configure Pipeline), the `.sd` columns will be
          automatically normalized by the same baseline value
        - This ensures error bars are correctly scaled in normalized plots
        """)

        if st.button(
            "Apply Seeds Reducer",
            key=WidgetKeyBuilder.manager_key("seeds_reducer", "apply"),
        ):
            # Validate inputs first
            validation_errors = self.api.managers.validate_seeds_reducer_inputs(
                df=data,
                categorical_cols=selected_categorical,
                statistic_cols=selected_numeric,
            )

            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                return

            try:
                result_df = self.api.managers.reduce_seeds(
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

                # Store in PreviewRepository via api
                self.api.set_preview("seeds_reduction", result_df)

            except Exception as e:
                st.exception(e)

        # Separate confirmation button outside the first button's scope
        if self.api.has_preview("seeds_reduction"):
            if st.button(
                "Confirm and Apply Seeds Reducer",
                key=WidgetKeyBuilder.manager_key("seeds_reducer", "confirm"),
                type="primary",
            ):
                confirmed_df: pd.DataFrame | None = self.api.get_preview("seeds_reduction")
                if confirmed_df is not None:
                    self.set_data(confirmed_df)
                    self.api.clear_preview("seeds_reduction")
                    record: OperationRecord = {
                        "source_columns": selected_categorical + selected_numeric,
                        "dest_columns": selected_numeric,
                        "operation": "Seeds Reduction (mean + stdev)",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    self.api.add_manager_history_record(record)
                    st.toast("✓ Seeds-reduced data is now active!", icon="✅")
                    # set_data mutates GLOBAL data → rerun the whole app, not just this
                    # fragment, so sibling tabs (Summary/Viz/other managers) refresh too.
                    st.rerun(scope="app")

        # Show manager-specific history with Load / Delete
        HistoryComponents.render_manager_history(
            self.api.get_manager_history(),
            "Seeds",
            WidgetKeyBuilder.manager_key("seeds_reducer", "load_trigger"),
            self.api.remove_manager_history_record,
        )
