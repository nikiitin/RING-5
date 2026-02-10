"""
History Components - UI for displaying operation history.

Provides reusable Streamlit components for rendering operation history
tables, filtered by manager type or showing the full portfolio history.
"""

from typing import Callable, List, Optional

import pandas as pd
import streamlit as st

from src.core.models.history_models import OperationRecord


class HistoryComponents:
    """UI Components for displaying operation history."""

    @staticmethod
    def render_history_table(
        records: List[OperationRecord],
        *,
        title: Optional[str] = None,
    ) -> None:
        """Render a list of OperationRecords as a Streamlit table.

        Args:
            records: The operation records to display.
            title: Optional section title.
        """
        if not records:
            return

        if title:
            st.markdown(f"#### {title}")

        rows = []
        for rec in reversed(records):
            rows.append(
                {
                    "Timestamp": rec["timestamp"][:19].replace("T", " "),
                    "Operation": rec["operation"],
                    "Source Columns": ", ".join(rec["source_columns"]),
                    "Dest Columns": ", ".join(rec["dest_columns"]),
                }
            )

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    @staticmethod
    def render_manager_history(
        all_records: List[OperationRecord],
        operation_prefix: str,
        load_session_key: str,
        delete_callback: Callable[[OperationRecord], None],
    ) -> None:
        """Render history for a specific manager with Load / Delete buttons.

        Each entry shows its details plus two action buttons:
        - **Load** (blue): stores the record in ``st.session_state[load_session_key]``
          so the manager can pre-fill its widgets on the next rerun.
        - **Delete** (red): removes the record via *delete_callback* and reruns.

        Args:
            all_records: Full manager history list.
            operation_prefix: Prefix to filter on (e.g. ``"Preprocessor"``).
            load_session_key: Session-state key used to pass loaded record to
                the manager.
            delete_callback: Called with the record to delete.
        """
        filtered = [r for r in all_records if r["operation"].startswith(operation_prefix)]
        if not filtered:
            return

        with st.expander(f"History ({len(filtered)} operations)", expanded=False):
            for i, record in enumerate(reversed(filtered)):
                cols = st.columns([2, 2, 2, 2, 1, 1])
                with cols[0]:
                    st.caption("Time")
                    st.text(record["timestamp"][:16].replace("T", " "))
                with cols[1]:
                    op_display = record["operation"]
                    if ": " in op_display:
                        op_display = op_display.split(": ", 1)[1]
                    st.caption("Operation")
                    st.text(op_display)
                with cols[2]:
                    st.caption("Source")
                    st.text(", ".join(record["source_columns"]))
                with cols[3]:
                    st.caption("Destination")
                    st.text(", ".join(record["dest_columns"]))
                with cols[4]:
                    if st.button(
                        "🔄",
                        key=f"hist_load_{operation_prefix}_{i}",
                        help="Load into manager",
                        type="primary",
                    ):
                        st.session_state[load_session_key] = record
                        st.rerun()
                with cols[5]:
                    if st.button(
                        "🗑️",
                        key=f"hist_del_{operation_prefix}_{i}",
                        help="Delete entry",
                    ):
                        delete_callback(record)
                        st.rerun()

    @staticmethod
    def render_portfolio_history(records: List[OperationRecord]) -> None:
        """Render the full portfolio history (all managers).

        Intended for the dedicated "Operations History" tab.

        Args:
            records: Complete portfolio history list.
        """
        st.markdown("### Operations History")
        st.info(
            "Complete log of every data transformation applied in this portfolio, "
            "across all managers."
        )

        if not records:
            st.warning("No operations have been performed yet.")
            return

        st.metric("Total Operations", len(records))
        HistoryComponents.render_history_table(records)
