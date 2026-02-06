"""
Mean Config - UI Configuration for Mean Aggregation Shaper.

Provides Streamlit components for configuring the Mean shaper, which
aggregates values across specified columns or groups.
"""

from typing import Any, Dict

import pandas as pd
import streamlit as st


class MeanConfig:
    """UI Component for configuring the Mean shaper."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: Dict[str, Any], key_prefix: str, shaper_id: str
    ) -> Dict[str, Any]:
        """
        Render the mean configuration UI.
        """
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = data.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()

        col1, col2, col3 = st.columns(3)
        with col1:
            mean_algos = ["arithmean", "geomean", "hmean"]
            mean_algo_default = existing_config.get("meanAlgorithm", "arithmean")
            mean_algo_index = (
                mean_algos.index(mean_algo_default) if mean_algo_default in mean_algos else 0
            )
            mean_algorithm = st.selectbox(
                "Mean type",
                options=mean_algos,
                index=mean_algo_index,
                key=f"{key_prefix}mean_algo_{shaper_id}",
            )

        with col2:
            mean_vars = st.multiselect(
                "Variables",
                options=numeric_cols,
                default=[c for c in existing_config.get("meanVars", []) if c in numeric_cols],
                key=f"{key_prefix}mean_vars_{shaper_id}",
            )

        with col3:
            # Handle legacy config
            group_cols_default = existing_config.get("groupingColumns", [])
            if not group_cols_default and existing_config.get("groupingColumn"):
                group_cols_default = [existing_config.get("groupingColumn")]
            group_cols_default = [c for c in group_cols_default if c in categorical_cols]

            grouping_columns = st.multiselect(
                "Group by",
                options=categorical_cols,
                default=group_cols_default,
                key=f"{key_prefix}mean_group_{shaper_id}",
            )

        replace_col_default = existing_config.get("replacingColumn")
        replace_col_index = (
            categorical_cols.index(replace_col_default)
            if replace_col_default in categorical_cols
            else 0
        )
        replacing_column = st.selectbox(
            "Replacing column",
            options=categorical_cols,
            index=replace_col_index,
            key=f"{key_prefix}mean_replace_{shaper_id}",
        )

        return {
            "meanAlgorithm": mean_algorithm,
            "meanVars": mean_vars,
            "groupingColumns": grouping_columns,
            "replacingColumn": replacing_column,
        }
