"""Data-manager UI for baseline and candidate comparison."""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.core.models.history_models import OperationRecord
from src.web.components.data_managers.data_manager import DataManager
from src.web.state.ui_state_manager import WidgetKeyBuilder

_PREVIEW_NAME = "regression_comparison"


class ComparisonManager(DataManager):
    """Configure and preview a baseline-to-candidate comparison."""

    @property
    def name(self) -> str:
        """Return the manager's display name."""
        return "Compare"

    def render(self) -> None:
        """Render comparison controls and the current result."""
        # [impl->req~ring5.analysis.regression-comparison~1]
        st.markdown("### Compare Baseline and Candidate")
        st.info(
            "Select two experiment groups, the columns that align their rows, and the "
            "numeric metrics to compare. Missing and non-comparable values remain visible."
        )

        data = self.get_data()
        if data is None or data.empty:
            st.warning("Load a non-empty dataset before creating a comparison.")
            return

        group_columns = [
            column for column in data.columns if 2 <= data[column].nunique(dropna=True) <= 100
        ]
        if not group_columns:
            st.warning("No column contains between 2 and 100 experiment groups.")
            return

        group_column = str(
            st.selectbox(
                "Experiment column",
                group_columns,
                key=WidgetKeyBuilder.manager_key("comparison", "group_column"),
            )
        )
        group_values = data[group_column].dropna().drop_duplicates().tolist()
        baseline_column, candidate_column = st.columns(2)
        with baseline_column:
            baseline_value = st.selectbox(
                "Baseline",
                group_values,
                index=0,
                key=WidgetKeyBuilder.manager_key("comparison", "baseline"),
            )
        with candidate_column:
            candidate_value = st.selectbox(
                "Candidate",
                group_values,
                index=1 if len(group_values) > 1 else 0,
                key=WidgetKeyBuilder.manager_key("comparison", "candidate"),
            )

        numeric_columns = [
            column
            for column in data.select_dtypes(include="number").columns
            if column != group_column
        ]
        if not numeric_columns:
            st.warning("No numeric metric columns are available.")
            return
        metric_columns = st.multiselect(
            "Metrics",
            numeric_columns,
            default=[],
            key=WidgetKeyBuilder.manager_key("comparison", "metrics"),
        )

        key_options = [
            column
            for column in data.columns
            if column != group_column and column not in metric_columns
        ]
        default_keys = [
            column
            for column in key_options
            if not pd.api.types.is_numeric_dtype(data[column].dtype)
        ]
        key_columns = st.multiselect(
            "Alignment keys",
            key_options,
            default=default_keys,
            help="The selected columns must identify at most one row in each group.",
            key=WidgetKeyBuilder.manager_key("comparison", "keys"),
        )

        direction_column, mode_column, threshold_column = st.columns(3)
        with direction_column:
            direction_label = st.selectbox(
                "Preferred direction",
                ["Higher is better", "Lower is better"],
                key=WidgetKeyBuilder.manager_key("comparison", "direction"),
            )
        with mode_column:
            mode_label = st.selectbox(
                "Threshold unit",
                ["Percentage", "Absolute"],
                key=WidgetKeyBuilder.manager_key("comparison", "threshold_mode"),
            )
        with threshold_column:
            threshold = float(
                st.number_input(
                    "Tolerance",
                    min_value=0.0,
                    value=0.0,
                    step=0.1,
                    key=WidgetKeyBuilder.manager_key("comparison", "threshold"),
                )
            )

        if baseline_value == candidate_value:
            st.warning("Baseline and candidate must be different groups.")
        elif st.button(
            "Compare",
            type="primary",
            key=WidgetKeyBuilder.manager_key("comparison", "apply"),
        ):
            if not key_columns or not metric_columns:
                st.error("Select at least one alignment key and one metric.")
            else:
                baseline = data.loc[data[group_column].eq(baseline_value)].copy()
                candidate = data.loc[data[group_column].eq(candidate_value)].copy()
                try:
                    result = self.api.managers.compare(
                        baseline,
                        candidate,
                        key_columns,
                        metric_columns,
                        directions="higher" if direction_label == "Higher is better" else "lower",
                        thresholds=threshold,
                        threshold_mode=("percentage" if mode_label == "Percentage" else "absolute"),
                        baseline_name=str(baseline_value),
                        candidate_name=str(candidate_value),
                    )
                except (TypeError, ValueError) as exc:
                    st.error(str(exc))
                else:
                    self.api.set_preview(_PREVIEW_NAME, result)

        preview = self.api.get_preview(_PREVIEW_NAME)
        if preview is None:
            return

        counts = preview["outcome"].value_counts()
        summary_columns = st.columns(4)
        for container, label in zip(
            summary_columns,
            ("regression", "improvement", "unchanged", "not_comparable"),
            strict=True,
        ):
            with container:
                st.metric(label.replace("_", " ").title(), int(counts.get(label, 0)))
        st.dataframe(preview, width="stretch")
        st.download_button(
            "Download comparison CSV",
            preview.to_csv(index=False),
            file_name="ring5-comparison.csv",
            mime="text/csv",
            key=WidgetKeyBuilder.manager_key("comparison", "download"),
        )
        if st.button(
            "Use Comparison Result",
            key=WidgetKeyBuilder.manager_key("comparison", "confirm"),
        ):
            self.set_data(preview)
            self.api.clear_preview(_PREVIEW_NAME)
            record: OperationRecord = {
                "source_columns": [group_column] + list(key_columns) + list(metric_columns),
                "dest_columns": list(preview.columns),
                "operation": f"Compare {baseline_value} with {candidate_value}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.api.add_manager_history_record(record)
            st.rerun(scope="app")
