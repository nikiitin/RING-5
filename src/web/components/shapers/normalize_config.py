"""Streamlit controls for normalization against a baseline within each group."""

from typing import cast

import pandas as pd
import streamlit as st

from src.core.models.shaper_models import ShaperStepConfig, NormalizeShaperConfig


class NormalizeConfig:
    """UI Component for configuring the Normalize shaper."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
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

        baseline_cols = [*categorical_cols, *[c for c in data.columns if c not in categorical_cols]]
        col1, col2 = st.columns(2)
        with col1:
            normalizer_vars = st.multiselect(
                "Normalizer variables (will be summed)",
                options=numeric_cols,
                default=[
                    c
                    for c in cast(
                        list[str],
                        existing_config.get(
                            "normalizerVars", existing_config.get("normalizeVars", [])
                        ),
                    )
                    if c in numeric_cols
                ],
                key=f"{key_prefix}normalizer_vars_{shaper_id}",
                help="These columns will be summed to create the baseline normalizer value",
            )

            normalize_vars = st.multiselect(
                "Variables to normalize",
                options=numeric_cols,
                default=[
                    c
                    for c in cast(list[str], existing_config.get("normalizeVars", []))
                    if c in numeric_cols
                ],
                key=f"{key_prefix}norm_vars_{shaper_id}",
                help="These columns will be divided by the sum of normalizer variables",
            )

            norm_col_default = cast(str, existing_config.get("normalizerColumn", ""))
            norm_col_index = (
                baseline_cols.index(norm_col_default) if norm_col_default in baseline_cols else 0
            )
            normalizer_column = st.selectbox(
                "Normalizer column (baseline identifier)",
                options=baseline_cols,
                index=norm_col_index,
                key=f"{key_prefix}norm_col_{shaper_id}",
                help="The column that identifies the baseline configuration",
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
                options=data.columns.tolist(),
                default=[
                    c
                    for c in cast(list[str], existing_config.get("groupBy", []))
                    if c in data.columns
                ],
                key=f"{key_prefix}norm_group_{shaper_id}",
            )

            normalize_sd = st.checkbox(
                "Automatically normalize standard deviation columns",
                value=cast(bool, existing_config.get("normalizeSd", True)),
                key=f"{key_prefix}norm_sd_{shaper_id}",
                help=(
                    "If enabled, .sd columns will be automatically"
                    " normalized using the sum of their base"
                    " normalizer columns"
                ),
            )

        result = cast(
            NormalizeShaperConfig,
            {
                "normalizeVars": list(normalize_vars) if normalize_vars else [],
                "normalizerColumn": str(normalizer_column or ""),
                "normalizerValue": normalizer_value,
                "groupBy": list(group_by) if group_by else [],
                "normalizeSd": bool(normalize_sd),
            },
        )
        if "normalizerVars" in existing_config or normalizer_vars != normalize_vars:
            result["normalizerVars"] = list(normalizer_vars)
        return result
