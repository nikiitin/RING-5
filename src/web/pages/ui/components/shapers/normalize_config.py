from typing import Any, Dict

import pandas as pd
import streamlit as st


class NormalizeConfig:
    """UI Component for configuring the Normalize shaper."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: Dict[str, Any], key_prefix: str, shaper_id: str
    ) -> Dict[str, Any]:
        """
        Render the normalization configuration UI.

        Args:
            data: Input DataFrame to inspect for columns.
            existing_config: Previously saved configuration.
            key_prefix: Unique prefix for widget keys.
            shaper_id: Unique ID of the shaper.

        Returns:
            Shaper configuration dictionary.
        """
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = data.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()

        col1, col2 = st.columns(2)
        with col1:
            normalizer_vars = st.multiselect(
                "Normalizer variables (will be summed)",
                options=numeric_cols,
                default=[c for c in existing_config.get("normalizerVars", []) if c in numeric_cols],
                key=f"{key_prefix}normalizer_vars_{shaper_id}",
                help="These columns will be summed to create the baseline normalizer value",
            )

            normalize_vars = st.multiselect(
                "Variables to normalize",
                options=numeric_cols,
                default=[c for c in existing_config.get("normalizeVars", []) if c in numeric_cols],
                key=f"{key_prefix}norm_vars_{shaper_id}",
                help="These columns will be divided by the sum of normalizer variables",
            )

            norm_col_default = existing_config.get("normalizerColumn")
            norm_col_index = (
                categorical_cols.index(norm_col_default)
                if norm_col_default in categorical_cols
                else 0
            )
            normalizer_column = st.selectbox(
                "Normalizer column (baseline identifier)",
                options=categorical_cols,
                index=norm_col_index,
                key=f"{key_prefix}norm_col_{shaper_id}",
                help="The categorical column that identifies the baseline configuration",
            )

        with col2:
            normalizer_value = None
            if normalizer_column:
                unique_vals = data[normalizer_column].unique().tolist()
                norm_val_default = existing_config.get("normalizerValue")
                norm_val_index = (
                    unique_vals.index(norm_val_default) if norm_val_default in unique_vals else 0
                )
                normalizer_value = st.selectbox(
                    "Baseline value",
                    options=unique_vals,
                    index=norm_val_index,
                    key=f"{key_prefix}norm_val_{shaper_id}",
                )

            group_by = st.multiselect(
                "Group by",
                options=categorical_cols,
                default=[c for c in existing_config.get("groupBy", []) if c in categorical_cols],
                key=f"{key_prefix}norm_group_{shaper_id}",
            )

            normalize_sd = st.checkbox(
                "Automatically normalize standard deviation columns",
                value=existing_config.get("normalizeSd", True),
                key=f"{key_prefix}norm_sd_{shaper_id}",
                help="If enabled, .sd columns will be automatically normalized using the sum of their base normalizer columns",  # noqa: E501
            )

        return {
            "normalizerVars": normalizer_vars,
            "normalizeVars": normalize_vars,
            "normalizerColumn": normalizer_column,
            "normalizerValue": normalizer_value,
            "groupBy": group_by,
            "normalizeSd": normalize_sd,
        }
