"""
Configuration Components for Pivot Shapers.

Provides Streamlit UI implementations for configuring PivotLonger and PivotWider shapers.
"""

from typing import Any, cast

import pandas as pd
import streamlit as st

from src.core.models.data_models import ShaperStepConfig


class PivotLongerConfig:
    """Configuration UI for Pivot Longer (Melt) shaper."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        """Render configuration UI for PivotLonger."""
        columns = data.columns.tolist()
        cfg = cast(dict[str, Any], existing_config)

        st.markdown("##### Columns Configuration")
        col1, col2 = st.columns(2)
        with col1:
            default_id = []
            if "id_vars" in cfg:
                default_id = [str(c) for c in cfg["id_vars"] if c in columns]

            id_vars = st.multiselect(
                "Identifier Columns (keep as-is)",
                options=columns,
                default=default_id,
                key=f"{key_prefix}plonger_id_{shaper_id}",
                help="Columns to use as identifier variables (e.g., config, benchmark).",
            )

        with col2:
            default_vals = []
            if "value_vars" in cfg:
                default_vals = [str(c) for c in cfg["value_vars"] if c in columns]
            else:
                # Default to all columns not selected as id_vars if id_vars are selected
                if id_vars:
                    default_vals = [c for c in columns if c not in id_vars]

            value_vars = st.multiselect(
                "Value Columns (to unpivot)",
                options=columns,
                default=default_vals,
                key=f"{key_prefix}plonger_val_{shaper_id}",
                help=(
                    "Columns to unpivot. Selected column names will become "
                    "values in the new Name column."
                ),
            )

        st.markdown("##### Output Column Names")
        col3, col4 = st.columns(2)
        with col3:
            var_name = st.text_input(
                "New 'Name' Column",
                value=str(cfg.get("var_name", "variable")),
                key=f"{key_prefix}plonger_varname_{shaper_id}",
                help="Name for the new column that will store the old column names.",
            )
        with col4:
            val_name = st.text_input(
                "New 'Value' Column",
                value=str(cfg.get("value_name", "value")),
                key=f"{key_prefix}plonger_valname_{shaper_id}",
                help="Name for the new column that will store the cell values.",
            )

        st.markdown("##### Advanced Extraction (Regex)")
        extract_pattern = st.text_input(
            "Extract Pattern (Optional)",
            value=str(cfg.get("extract_pattern", "")),
            key=f"{key_prefix}plonger_pattern_{shaper_id}",
            help=(
                "Provide a regex pattern with a capture group "
                "(e.g., r'.+l(\\\\d+)_cntrl.*') to extract a variable part "
                "from the old column names. Leave empty to keep the whole string."
            ),
        )

        # Convert to strict types
        result: dict[str, Any] = {
            "type": "pivotLonger",
            "id_vars": [str(c) for c in id_vars],
            "value_vars": [str(c) for c in value_vars],
            "var_name": str(var_name),
            "value_name": str(val_name),
        }
        if extract_pattern.strip():
            result["extract_pattern"] = extract_pattern.strip()

        return cast(ShaperStepConfig, result)


class PivotWiderConfig:
    """Configuration UI for Pivot Wider shaper."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        """Render configuration UI for PivotWider."""
        columns = data.columns.tolist()
        cfg = cast(dict[str, Any], existing_config)

        col1, col2, col3 = st.columns(3)
        with col1:
            default_idx = []
            if "index" in cfg:
                default_idx = [str(c) for c in cfg["index"] if c in columns]

            index_cols = st.multiselect(
                "Index Columns",
                options=columns,
                default=default_idx,
                key=f"{key_prefix}pwider_idx_{shaper_id}",
                help="Columns to use as new frame's index (identifiers to keep row-level).",
            )

        with col2:
            default_col = ""
            if cfg.get("columns") in columns:
                default_col = str(cfg["columns"])

            columns_col = st.selectbox(
                "Columns from",
                options=[""] + columns,
                index=columns.index(default_col) + 1 if default_col in columns else 0,
                key=f"{key_prefix}pwider_col_{shaper_id}",
                help="Column containing values that will become the new column names.",
            )

        with col3:
            default_val = ""
            if cfg.get("values") in columns:
                default_val = str(cfg["values"])

            values_col = st.selectbox(
                "Values from",
                options=[""] + columns,
                index=columns.index(default_val) + 1 if default_val in columns else 0,
                key=f"{key_prefix}pwider_val_{shaper_id}",
                help="Column containing values that will populate the new columns.",
            )

        # Build type-strict dictionary without empty strings if not selected to avoid errors
        # Note: Validation will fail if required keys are missing, which is expected UI behavior.
        result: dict[str, Any] = {"type": "pivotWider"}

        if index_cols:
            result["index"] = [str(c) for c in index_cols]
        if columns_col:
            result["columns"] = str(columns_col)
        if values_col:
            result["values"] = str(values_col)

        return cast(ShaperStepConfig, result)
