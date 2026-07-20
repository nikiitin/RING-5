"""Human-first controls for retaining and composing named datasets."""

from __future__ import annotations

from typing import Literal, cast

import pandas as pd
import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models.dataset_workspace_models import JoinCardinality
from src.web.state.ui_state_manager import WidgetKeyBuilder

_COMPARISON_PREVIEW = "workspace_dataset_comparison"


class DatasetWorkspaceManager:
    """Manage multiple named datasets without replacing unrelated data."""

    def __init__(self, api: ApplicationAPI) -> None:
        """Initialize with the application facade."""
        self.api = api

    def render(self) -> None:
        """Render retention, selection, comparison, join, append, and removal."""
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        st.markdown("### Named Dataset Workspace")
        st.info(
            "Keep independent tables in this session, switch the active table, or create a new "
            "table by comparing, joining, or appending retained datasets. Source tables remain "
            "unchanged."
        )

        infos = self.api.list_datasets()
        default_name = f"dataset_{len(infos) + 1}"
        retain_name = st.text_input(
            "Name for current data",
            value=default_name,
            key=WidgetKeyBuilder.manager_key("workspace", "retain_name"),
        )
        if st.button(
            "Retain Current Dataset",
            type="primary" if not infos else "secondary",
            key=WidgetKeyBuilder.manager_key("workspace", "retain"),
        ):
            try:
                self.api.add_current_dataset(retain_name)
            except (KeyError, TypeError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.rerun(scope="app")

        infos = self.api.list_datasets()
        if not infos:
            st.caption("No named datasets yet. Retain the current data to start the workspace.")
            return

        st.metric("Retained datasets", len(infos))
        st.dataframe(
            pd.DataFrame(
                {
                    "Name": [info.name for info in infos],
                    "Rows": [info.row_count for info in infos],
                    "Columns": [info.column_count for info in infos],
                    "Active": ["Yes" if info.selected else "" for info in infos],
                }
            ),
            width="stretch",
            hide_index=True,
        )

        names = [info.name for info in infos]
        selected_index = next((index for index, info in enumerate(infos) if info.selected), 0)
        chosen = str(
            st.selectbox(
                "Workspace dataset",
                names,
                index=selected_index,
                key=WidgetKeyBuilder.manager_key("workspace", "selected"),
            )
        )
        activate, remove = st.columns(2)
        with activate:
            if st.button(
                "Activate Dataset",
                key=WidgetKeyBuilder.manager_key("workspace", "activate"),
            ):
                self.api.select_dataset(chosen)
                st.rerun(scope="app")
        with remove:
            if st.button(
                "Remove Dataset",
                key=WidgetKeyBuilder.manager_key("workspace", "remove"),
            ):
                self.api.remove_dataset(chosen)
                st.rerun(scope="app")

        self._render_lineage(chosen)

        if len(names) < 2:
            st.caption("Retain a second dataset to compare, join, or append tables.")
            return

        operation = st.selectbox(
            "Workspace operation",
            ["Compare", "Join", "Append"],
            key=WidgetKeyBuilder.manager_key("workspace", "operation"),
        )
        if operation == "Compare":
            self._render_compare(names)
        elif operation == "Join":
            self._render_join(names)
        else:
            self._render_append(names)

    def _render_compare(self, names: list[str]) -> None:
        baseline, candidate = self._two_dataset_selectors(names, "compare")
        baseline_data = self.api.get_dataset(baseline)
        candidate_data = self.api.get_dataset(candidate)
        shared = [
            column
            for column in baseline_data
            if isinstance(column, str) and column in candidate_data.columns
        ]
        numeric = [
            column
            for column in shared
            if pd.api.types.is_numeric_dtype(baseline_data[column].dtype)
            and pd.api.types.is_numeric_dtype(candidate_data[column].dtype)
        ]
        keys = cast(
            list[str],
            st.multiselect(
                "Comparison keys",
                [column for column in shared if column not in numeric],
                key=WidgetKeyBuilder.manager_key("workspace", "compare_keys"),
            ),
        )
        metrics = cast(
            list[str],
            st.multiselect(
                "Comparison metrics",
                numeric,
                key=WidgetKeyBuilder.manager_key("workspace", "compare_metrics"),
            ),
        )
        direction = st.selectbox(
            "Preferred direction",
            ["Higher is better", "Lower is better"],
            key=WidgetKeyBuilder.manager_key("workspace", "compare_direction"),
        )
        threshold = float(
            st.number_input(
                "Regression tolerance (%)",
                min_value=0.0,
                value=0.0,
                key=WidgetKeyBuilder.manager_key("workspace", "compare_threshold"),
            )
        )
        if st.button(
            "Compare Retained Datasets",
            key=WidgetKeyBuilder.manager_key("workspace", "compare_apply"),
        ):
            if not keys or not metrics:
                st.error("Select at least one comparison key and metric.")
            else:
                try:
                    result = self.api.compare_datasets(
                        baseline,
                        candidate,
                        keys,
                        metrics,
                        directions="higher" if direction == "Higher is better" else "lower",
                        thresholds=threshold,
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    st.error(str(exc))
                else:
                    self.api.set_preview(_COMPARISON_PREVIEW, result)
        preview = self.api.get_preview(_COMPARISON_PREVIEW)
        if preview is not None:
            st.dataframe(preview, width="stretch")

    def _render_join(self, names: list[str]) -> None:
        # [impl->req~ring5.data.validated-joins~1]
        left_name, right_name = self._two_dataset_selectors(names, "join")
        left = self.api.get_dataset(left_name)
        right = self.api.get_dataset(right_name)
        shared = [column for column in left if isinstance(column, str) and column in right.columns]
        keys = cast(
            list[str],
            st.multiselect(
                "Join keys",
                shared,
                key=WidgetKeyBuilder.manager_key("workspace", "join_keys"),
            ),
        )
        how = cast(
            Literal["inner", "left", "right", "outer"],
            st.selectbox(
                "Join mode",
                ["inner", "left", "right", "outer"],
                key=WidgetKeyBuilder.manager_key("workspace", "join_mode"),
            ),
        )
        cardinality_labels: dict[str, JoinCardinality] = {
            "One left row to one right row": "one_to_one",
            "One left row to many right rows": "one_to_many",
            "Many left rows to one right row": "many_to_one",
            "Many rows on both sides": "many_to_many",
        }
        cardinality_label = str(
            st.selectbox(
                "Expected key relationship",
                list(cardinality_labels),
                key=WidgetKeyBuilder.manager_key("workspace", "join_cardinality"),
            )
        )
        cardinality = cardinality_labels[cardinality_label]
        output = st.text_input(
            "Joined dataset name",
            value=f"{left_name}_{right_name}_joined",
            key=WidgetKeyBuilder.manager_key("workspace", "join_output"),
        )

        diagnostics = None
        if keys:
            try:
                diagnostics = self.api.diagnose_join(
                    left_name,
                    right_name,
                    keys,
                    cardinality=cardinality,
                )
            except (KeyError, TypeError, ValueError) as exc:
                st.error(str(exc))
            else:
                status, duplicates, unmatched = st.columns(3)
                with status:
                    st.metric(
                        "Cardinality",
                        "Valid" if diagnostics.cardinality_valid else "Conflict",
                    )
                with duplicates:
                    st.metric(
                        "Duplicate-key rows",
                        diagnostics.left_duplicate_key_rows + diagnostics.right_duplicate_key_rows,
                        help=(
                            f"Left: {diagnostics.left_duplicate_key_rows}; "
                            f"right: {diagnostics.right_duplicate_key_rows}"
                        ),
                    )
                with unmatched:
                    st.metric(
                        "Unmatched rows",
                        diagnostics.left_unmatched_rows + diagnostics.right_unmatched_rows,
                        help=(
                            f"Left: {diagnostics.left_unmatched_rows}; "
                            f"right: {diagnostics.right_unmatched_rows}"
                        ),
                    )
                if diagnostics.cardinality_valid:
                    st.success(
                        f"Key relationship is valid; {diagnostics.matched_key_count} distinct "
                        "keys match on both sides."
                    )
                else:
                    st.warning(
                        "Duplicate keys conflict with the selected relationship. Choose the "
                        "intended relationship or correct the source keys before joining."
                    )
        if st.button(
            "Validate and Join Datasets",
            disabled=diagnostics is None or not diagnostics.cardinality_valid,
            key=WidgetKeyBuilder.manager_key("workspace", "join_apply"),
        ):
            try:
                self.api.join_datasets_validated(
                    left_name,
                    right_name,
                    output,
                    keys,
                    cardinality=cardinality,
                    how=how,
                )
            except (KeyError, TypeError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.rerun(scope="app")

    def _render_lineage(self, name: str) -> None:
        """Render inspectable provenance plus bounded undo and redo controls."""
        # [impl->req~ring5.data.lineage-undo-redo~1]
        lineage = self.api.get_dataset_lineage(name)
        revisions = list(lineage.revisions)
        with st.expander("Lineage & recovery", expanded=True):
            st.caption(
                "Every confirmed change creates an immutable in-session snapshot. "
                "Fingerprints identify exact table contents; sources and parent revisions "
                "show how derived data was produced."
            )
            st.dataframe(
                pd.DataFrame(
                    {
                        "Step": [revision.sequence for revision in revisions],
                        "Current": ["Yes" if revision.current else "" for revision in revisions],
                        "Operation": [revision.operation for revision in revisions],
                        "Sources": [", ".join(revision.source_datasets) for revision in revisions],
                        "Parents": [
                            ", ".join(revision.parent_revision_ids) for revision in revisions
                        ],
                        "Rows": [revision.row_count for revision in revisions],
                        "Columns": [revision.column_count for revision in revisions],
                        "Fingerprint": [revision.fingerprint for revision in revisions],
                    }
                ),
                width="stretch",
                hide_index=True,
            )

            undo, redo = st.columns(2)
            with undo:
                if st.button(
                    "Undo Last Change",
                    disabled=not lineage.can_undo,
                    key=WidgetKeyBuilder.manager_key("workspace", "lineage_undo"),
                ):
                    self.api.undo_dataset(name)
                    st.rerun(scope="app")
            with redo:
                if st.button(
                    "Redo Change",
                    disabled=not lineage.can_redo,
                    key=WidgetKeyBuilder.manager_key("workspace", "lineage_redo"),
                ):
                    self.api.redo_dataset(name)
                    st.rerun(scope="app")

            labels = {
                revision.revision_id: f"Step {revision.sequence}: {revision.operation}"
                for revision in revisions
            }
            selected_revision = str(
                st.selectbox(
                    "Inspect revision",
                    [revision.revision_id for revision in reversed(revisions)],
                    format_func=lambda revision_id: labels[revision_id],
                    key=WidgetKeyBuilder.manager_key("workspace", "lineage_revision"),
                )
            )
            selected_info = next(
                revision for revision in revisions if revision.revision_id == selected_revision
            )
            st.code(selected_info.fingerprint, language=None)
            snapshot = self.api.get_dataset_revision(selected_revision)
            st.dataframe(snapshot.head(100), width="stretch")
            if len(snapshot) > 100:
                st.caption(f"Showing the first 100 of {len(snapshot)} stored rows.")
            if st.button(
                "Restore This Revision",
                disabled=selected_revision == lineage.current_revision_id,
                key=WidgetKeyBuilder.manager_key("workspace", "lineage_restore"),
            ):
                self.api.restore_dataset_revision(selected_revision)
                st.rerun(scope="app")

    def _render_append(self, names: list[str]) -> None:
        selected = cast(
            list[str],
            st.multiselect(
                "Datasets to append",
                names,
                default=names[:2],
                key=WidgetKeyBuilder.manager_key("workspace", "append_inputs"),
            ),
        )
        join = cast(
            Literal["outer", "inner"],
            st.selectbox(
                "Append columns",
                ["outer", "inner"],
                format_func=lambda value: "Union" if value == "outer" else "Intersection",
                key=WidgetKeyBuilder.manager_key("workspace", "append_join"),
            ),
        )
        output = st.text_input(
            "Appended dataset name",
            value="appended_dataset",
            key=WidgetKeyBuilder.manager_key("workspace", "append_output"),
        )
        if st.button(
            "Append Retained Datasets",
            key=WidgetKeyBuilder.manager_key("workspace", "append_apply"),
        ):
            try:
                self.api.append_datasets(selected, output, join=join)
            except (KeyError, TypeError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.rerun(scope="app")

    def _two_dataset_selectors(self, names: list[str], operation: str) -> tuple[str, str]:
        left, right = st.columns(2)
        with left:
            first = str(
                st.selectbox(
                    "Baseline" if operation == "compare" else "Left dataset",
                    names,
                    index=0,
                    key=WidgetKeyBuilder.manager_key("workspace", f"{operation}_left"),
                )
            )
        with right:
            second = str(
                st.selectbox(
                    "Candidate" if operation == "compare" else "Right dataset",
                    names,
                    index=1,
                    key=WidgetKeyBuilder.manager_key("workspace", f"{operation}_right"),
                )
            )
        return first, second
