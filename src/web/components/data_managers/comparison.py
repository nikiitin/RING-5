"""Data-manager UI for baseline and candidate comparison."""

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.core.models.history_models import OperationRecord
from src.web.components.data_managers.data_manager import DataManager
from src.web.components.plotting.interactive_plot import interactive_plotly_chart
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
        # [impl->req~ring5.analysis.statistical-comparison~1]
        # [impl->req~ring5.analysis.regression-annotations~1]
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

        method_label = st.selectbox(
            "Comparison method",
            ["Threshold", "Statistics"],
            help=(
                "Threshold compares one aligned value per key. Statistics treats repeated rows "
                "within each key as samples."
            ),
            key=WidgetKeyBuilder.manager_key("comparison", "method"),
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
            help=(
                "Threshold comparison requires one row per key and experiment. Statistical "
                "comparison groups repeated samples by these columns; leave empty for one "
                "overall comparison."
            ),
            key=WidgetKeyBuilder.manager_key("comparison", "keys"),
        )

        if method_label == "Threshold":
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
        else:
            confidence_column, alpha_column, samples_column = st.columns(3)
            with confidence_column:
                confidence_level = float(
                    st.number_input(
                        "Confidence level",
                        min_value=0.5,
                        max_value=0.999,
                        value=0.95,
                        step=0.01,
                        key=WidgetKeyBuilder.manager_key("comparison", "confidence"),
                    )
                )
            with alpha_column:
                alpha = float(
                    st.number_input(
                        "Significance level",
                        min_value=0.001,
                        max_value=0.5,
                        value=0.05,
                        step=0.01,
                        key=WidgetKeyBuilder.manager_key("comparison", "alpha"),
                    )
                )
            with samples_column:
                bootstrap_samples = int(
                    st.number_input(
                        "Bootstrap samples",
                        min_value=100,
                        max_value=50_000,
                        value=2_000,
                        step=100,
                        key=WidgetKeyBuilder.manager_key("comparison", "bootstrap_samples"),
                    )
                )
            minimum_sample_size = int(
                st.number_input(
                    "Small-sample warning below",
                    min_value=2,
                    value=5,
                    step=1,
                    key=WidgetKeyBuilder.manager_key("comparison", "minimum_sample_size"),
                )
            )

        if baseline_value == candidate_value:
            st.warning("Baseline and candidate must be different groups.")
        elif st.button(
            "Compare",
            type="primary",
            key=WidgetKeyBuilder.manager_key("comparison", "apply"),
        ):
            if not metric_columns or (method_label == "Threshold" and not key_columns):
                st.error(
                    "Select at least one metric and, for threshold comparison, one alignment key."
                )
            else:
                baseline = data.loc[data[group_column].eq(baseline_value)].copy()
                candidate = data.loc[data[group_column].eq(candidate_value)].copy()
                try:
                    if method_label == "Threshold":
                        result = self.api.managers.compare(
                            baseline,
                            candidate,
                            key_columns,
                            metric_columns,
                            directions=(
                                "higher" if direction_label == "Higher is better" else "lower"
                            ),
                            thresholds=threshold,
                            threshold_mode=(
                                "percentage" if mode_label == "Percentage" else "absolute"
                            ),
                            baseline_name=str(baseline_value),
                            candidate_name=str(candidate_value),
                        )
                    else:
                        result = self.api.managers.compare_statistics(
                            baseline,
                            candidate,
                            key_columns,
                            metric_columns,
                            confidence_level=confidence_level,
                            alpha=alpha,
                            bootstrap_samples=bootstrap_samples,
                            minimum_sample_size=minimum_sample_size,
                        )
                except (TypeError, ValueError) as exc:
                    st.error(str(exc))
                else:
                    self.api.set_preview(_PREVIEW_NAME, result)

        preview = self.api.get_preview(_PREVIEW_NAME)
        if preview is None:
            return

        summary_columns = st.columns(4)
        if "outcome" in preview:
            counts = preview["outcome"].value_counts()
            labels_and_values = [
                (label.replace("_", " ").title(), int(counts.get(label, 0)))
                for label in ("regression", "improvement", "unchanged", "not_comparable")
            ]
        else:
            significant = int(preview["significant"].fillna(False).sum())
            warnings = int(preview["warning"].ne("").sum())
            labels_and_values = [
                ("Comparisons", len(preview)),
                ("Significant", significant),
                ("Warnings", warnings),
                ("Bootstrap samples", int(preview["bootstrap_samples"].max())),
            ]
        for container, (label, value) in zip(summary_columns, labels_and_values, strict=True):
            with container:
                st.metric(label, value)
        if "outcome" in preview:
            annotated = self.api.managers.annotate_comparison(
                preview,
                label_columns=key_columns,
            )
            self._render_regression_plot(annotated)
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
            self.set_data(
                preview,
                operation=(f"{method_label} comparison: {baseline_value} with {candidate_value}"),
            )
            self.api.clear_preview(_PREVIEW_NAME)
            record: OperationRecord = {
                "source_columns": [group_column] + list(key_columns) + list(metric_columns),
                "dest_columns": list(preview.columns),
                "operation": (
                    f"{method_label} comparison: {baseline_value} with {candidate_value}"
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.api.add_manager_history_record(record)
            st.rerun(scope="app")

    @staticmethod
    def _render_regression_plot(annotated: pd.DataFrame) -> None:
        """Render outcome labels with redundant color, shape, text, and legend cues."""
        # [impl->req~ring5.analysis.regression-annotations~1]
        finite = pd.to_numeric(annotated["annotation_change"], errors="coerce").replace(
            [float("inf"), float("-inf")], pd.NA
        )
        visible = annotated.loc[finite.notna()].copy()
        if visible.empty:
            st.caption("No comparable changes are available for the regression plot.")
            return

        st.markdown("#### Regression Map")
        st.caption(
            "Outcome is encoded redundantly: ▲ blue is improvement, ▼ vermillion is "
            "regression, and ● gray is within tolerance. Hover a point for its exact result."
        )
        figure = go.Figure()
        for outcome in ("regression", "improvement", "unchanged"):
            rows = visible.loc[visible["outcome"].eq(outcome)]
            if rows.empty:
                continue
            figure.add_trace(
                go.Scatter(
                    x=rows["annotation_label"],
                    y=rows["annotation_change"],
                    customdata=rows["annotation_text"].tolist(),
                    mode="markers+text",
                    name=outcome.title(),
                    marker={
                        "color": rows["annotation_color"].iloc[0],
                        "size": 12,
                        "symbol": rows["annotation_marker"].iloc[0],
                    },
                    text=rows["annotation_symbol"].astype(str).tolist(),
                    textposition="top center",
                    hovertemplate="%{x}<br>%{customdata}<extra></extra>",
                )
            )
        figure.add_hline(y=0.0, line_color="#4B5563", line_width=1)
        figure.update_layout(
            title="Candidate change by comparison",
            xaxis_title="Alignment key and metric",
            yaxis_title=(
                "Percentage change (%)"
                if annotated["threshold_mode"].eq("percentage").all()
                else "Absolute change"
            ),
            legend_title="Outcome",
            height=480,
            margin={"l": 60, "r": 20, "t": 60, "b": 120},
        )
        interactive_plotly_chart(
            figure,
            config={"responsive": True, "displaylogo": False},
            key=WidgetKeyBuilder.manager_key("comparison", "regression_plot"),
        )
