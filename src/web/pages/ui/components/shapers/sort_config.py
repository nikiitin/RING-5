"""
Sort Config — UI Configuration for the Sort Shaper.

Provides Streamlit widgets for configuring the Sort shaper, which
sorts a DataFrame by categorical column ordering.

The Sort shaper requires an ``order_dict``: a mapping from column names
to the desired value order for each column.
"""

from typing import Any, Dict, List

import pandas as pd
import streamlit as st


class SortConfig:
    """UI Component for configuring the Sort shaper."""

    @staticmethod
    def render(
        data: pd.DataFrame,
        existing_config: Dict[str, Any],
        key_prefix: str,
        shaper_id: str,
    ) -> Dict[str, Any]:
        """
        Render the Sort shaper configuration UI.

        Allows the user to:
            1. Select one or more columns to sort by
            2. For each selected column, drag-reorder the unique values

        Args:
            data: Current DataFrame (for column/value discovery).
            existing_config: Previously saved config (for restoring state).
            key_prefix: Widget key prefix for uniqueness.
            shaper_id: Unique shaper instance ID.

        Returns:
            Dict with ``type`` and ``order_dict`` keys.
        """
        categorical_cols: List[str] = data.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()

        if not categorical_cols:
            st.warning("No categorical columns available for sorting.")
            return {"type": "sort", "order_dict": {}}

        # Restore previously selected columns
        existing_order: Dict[str, List[str]] = existing_config.get("order_dict", {})
        default_cols: List[str] = [c for c in existing_order.keys() if c in categorical_cols]

        sort_columns: List[str] = st.multiselect(
            "Sort by columns",
            options=categorical_cols,
            default=default_cols,
            key=f"{key_prefix}sort_cols_{shaper_id}",
            help="Select columns to define sort order",
        )

        order_dict: Dict[str, List[str]] = {}

        for col in sort_columns:
            unique_values: List[str] = sorted(data[col].dropna().unique().astype(str).tolist())

            # Restore previous order if available, filtering stale values
            previous_order: List[str] = existing_order.get(col, [])
            valid_previous: List[str] = [v for v in previous_order if v in unique_values]
            new_values: List[str] = [v for v in unique_values if v not in valid_previous]
            default_order: List[str] = valid_previous + new_values

            with st.expander(f"Order for '{col}' ({len(unique_values)} values)"):
                if len(unique_values) <= 20:
                    # For small cardinality, let user reorder via multiselect
                    ordered: List[str] = st.multiselect(
                        f"Drag to reorder '{col}' values",
                        options=unique_values,
                        default=default_order,
                        key=f"{key_prefix}sort_order_{col}_{shaper_id}",
                        help="Remove and re-add values to change order",
                    )
                    order_dict[col] = ordered if ordered else default_order
                else:
                    # For high cardinality, show text input
                    st.info(
                        f"Column '{col}' has {len(unique_values)} unique values. "
                        "Showing first 50."
                    )
                    st.dataframe(
                        pd.DataFrame({col: default_order[:50]}),
                        hide_index=True,
                        height=200,
                    )
                    order_dict[col] = default_order

        return {
            "type": "sort",
            "order_dict": order_dict,
        }
