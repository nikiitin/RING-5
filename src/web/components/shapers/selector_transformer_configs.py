"""
Selector and Transformer Configs - UI Configuration for Selection Shapers.

Provides Streamlit components for configuring data selection and filtering shapers:
column selection, conditional filtering, and item-based selection.
"""

from typing import cast

import pandas as pd
import streamlit as st

from src.core.models.shaper_models import ShaperStepConfig


class ColumnSelectorConfig:
    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        st.markdown("Select which columns to keep")
        default_cols = [
            c for c in cast(list[str], existing_config.get("columns", [])) if c in data.columns
        ]
        if not default_cols and not data.columns.empty:
            default_cols = [data.columns[0]]

        selected_columns = st.multiselect(
            "Columns to keep",
            options=data.columns.tolist(),
            default=default_cols,
            key=f"{key_prefix}colsel_{shaper_id}",
        )
        return cast(ShaperStepConfig, {"columns": selected_columns if selected_columns else []})


class ConditionSelectorConfig:
    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        categorical_cols = data.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
        all_cols = categorical_cols + numeric_cols

        st.markdown("Filter rows based on column values")
        filter_col_default = cast(str, existing_config.get("column", ""))
        filter_col_index = (
            all_cols.index(filter_col_default) if filter_col_default in all_cols else 0
        )

        filter_column = st.selectbox(
            "Column to filter",
            options=all_cols,
            index=filter_col_index,
            key=f"{key_prefix}filter_col_{shaper_id}",
        )

        if not filter_column:
            return cast(ShaperStepConfig, {})

        is_numeric = filter_column in numeric_cols
        if is_numeric:
            filter_modes = ["range", "greater_than", "less_than", "equals"]
            filter_mode_default = cast(str, existing_config.get("mode", "range"))
            filter_mode_index = (
                filter_modes.index(filter_mode_default)
                if filter_mode_default in filter_modes
                else 0
            )
            filter_mode = st.selectbox(
                "Filter mode",
                options=filter_modes,
                index=filter_mode_index,
                key=f"{key_prefix}filter_mode_{shaper_id}",
            )

            min_val, max_val = float(data[filter_column].min()), float(data[filter_column].max())
            if filter_mode == "range":
                default_range = cast(list[float], existing_config.get("range", [min_val, max_val]))
                value_range = st.slider(
                    "Value range",
                    min_value=min_val,
                    max_value=max_val,
                    value=(float(default_range[0]), float(default_range[1])),
                    key=f"{key_prefix}filter_range_{shaper_id}",
                )
                return cast(
                    ShaperStepConfig,
                    {"column": filter_column, "mode": "range", "range": list(value_range)},
                )
            # ... (Simplified for brevity, similar for gt/lt/eq)
            elif filter_mode == "greater_than":
                threshold = st.number_input(
                    "Greater than",
                    value=cast(float, existing_config.get("threshold", min_val)),
                    key=f"{key_prefix}filter_gt_{shaper_id}",
                )
                return cast(
                    ShaperStepConfig,
                    {"column": filter_column, "mode": "greater_than", "threshold": threshold},
                )
            elif filter_mode == "less_than":
                threshold = st.number_input(
                    "Less than",
                    value=cast(float, existing_config.get("threshold", max_val)),
                    key=f"{key_prefix}filter_lt_{shaper_id}",
                )
                return cast(
                    ShaperStepConfig,
                    {"column": filter_column, "mode": "less_than", "threshold": threshold},
                )
            else:
                value = st.number_input(
                    "Equals",
                    value=cast(float, existing_config.get("value", min_val)),
                    key=f"{key_prefix}filter_eq_{shaper_id}",
                )
                return cast(
                    ShaperStepConfig, {"column": filter_column, "mode": "equals", "value": value}
                )
        else:
            unique_values = data[filter_column].unique().tolist()
            default_values = [
                v for v in cast(list[str], existing_config.get("values", [])) if v in unique_values
            ]
            selected_values = st.multiselect(
                "Keep rows where value is:",
                options=unique_values,
                default=default_values,
                key=f"{key_prefix}filter_values_{shaper_id}",
            )
            return cast(ShaperStepConfig, {"column": filter_column, "values": selected_values})


class ItemSelectorConfig:
    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        st.markdown("Keep rows whose column value matches the given items")
        all_cols = data.columns.tolist()
        col_default = cast(str, existing_config.get("column", ""))
        col_index = all_cols.index(col_default) if col_default in all_cols else 0
        column = st.selectbox(
            "Column to match",
            options=all_cols,
            index=col_index,
            key=f"{key_prefix}item_col_{shaper_id}",
        )
        if not column:
            return cast(ShaperStepConfig, {})

        modes = ["exact", "contains"]
        mode_default = cast(str, existing_config.get("mode", "exact"))
        mode = st.selectbox(
            "Match mode",
            options=modes,
            index=modes.index(mode_default) if mode_default in modes else 0,
            help="'exact' keeps rows equal to a selected value; 'contains' matches substrings.",
            key=f"{key_prefix}item_mode_{shaper_id}",
        )

        existing_strings = [str(s) for s in cast("list[str]", existing_config.get("strings", []))]
        if mode == "exact":
            unique_values = [str(v) for v in data[column].unique().tolist()]
            default_values = [v for v in existing_strings if v in unique_values]
            strings: list[str] = st.multiselect(
                "Values to keep",
                options=unique_values,
                default=default_values,
                key=f"{key_prefix}item_vals_{shaper_id}",
            )
        else:
            raw = st.text_input(
                "Substrings to match (comma-separated)",
                value=", ".join(existing_strings),
                key=f"{key_prefix}item_text_{shaper_id}",
            )
            strings = [s.strip() for s in raw.split(",") if s.strip()]

        return cast(
            ShaperStepConfig,
            {"column": str(column), "strings": list(strings), "mode": mode},
        )


class GroupCardinalitySelectorConfig:
    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        st.markdown(
            "Keep groups by their distinct-value count (e.g. benchmarks present "
            "under all policies)."
        )
        cols = data.columns.tolist()
        gb_default = [c for c in cast("list[str]", existing_config.get("groupBy", [])) if c in cols]
        group_by = st.multiselect(
            "Group by",
            options=cols,
            default=gb_default or cols[:1],
            key=f"{key_prefix}gcard_grp_{shaper_id}",
        )
        cc_default = cast(str, existing_config.get("countColumn", ""))
        count_column = st.selectbox(
            "Count distinct values of",
            options=cols,
            index=cols.index(cc_default) if cc_default in cols else 0,
            key=f"{key_prefix}gcard_col_{shaper_id}",
        )
        c1, c2 = st.columns(2)
        count = c1.number_input(
            "Count",
            min_value=0,
            step=1,
            value=int(cast(int, existing_config.get("count", 1))),
            key=f"{key_prefix}gcard_n_{shaper_id}",
        )
        modes = ["eq", "ge", "le"]
        mode = c2.selectbox(
            "Comparison",
            options=modes,
            index=(
                modes.index(cast(str, existing_config.get("mode", "eq")))
                if existing_config.get("mode") in modes
                else 0
            ),
            key=f"{key_prefix}gcard_mode_{shaper_id}",
        )
        return cast(
            ShaperStepConfig,
            {
                "groupBy": group_by,
                "countColumn": str(count_column or ""),
                "count": int(count),
                "mode": mode,
            },
        )


class GroupPredicateSelectorConfig:
    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        st.markdown(
            "Drop or keep whole groups based on a predicate on each group's " "baseline row."
        )
        cols = data.columns.tolist()
        gb_default = [c for c in cast("list[str]", existing_config.get("groupBy", [])) if c in cols]
        group_by = st.multiselect(
            "Group by",
            options=cols,
            default=gb_default or cols[:1],
            key=f"{key_prefix}gpred_grp_{shaper_id}",
        )
        c1, c2 = st.columns(2)
        bc_default = cast(str, existing_config.get("baselineColumn", ""))
        baseline_column = c1.selectbox(
            "Baseline column",
            options=cols,
            index=cols.index(bc_default) if bc_default in cols else 0,
            key=f"{key_prefix}gpred_bcol_{shaper_id}",
        )
        bvals = (
            [str(v) for v in data[baseline_column].unique()]
            if baseline_column in data.columns
            else []
        )
        bv_default = cast(str, existing_config.get("baselineValue", ""))
        if bvals:
            baseline_value = c2.selectbox(
                "Baseline value",
                options=bvals,
                index=bvals.index(bv_default) if bv_default in bvals else 0,
                key=f"{key_prefix}gpred_bval_{shaper_id}",
            )
        else:
            baseline_value = c2.text_input(
                "Baseline value", value=bv_default, key=f"{key_prefix}gpred_bval_{shaper_id}"
            )
        pc_default = cast(str, existing_config.get("predicateColumn", ""))
        predicate_column = st.selectbox(
            "Predicate column (tested on the baseline row)",
            options=cols,
            index=cols.index(pc_default) if pc_default in cols else 0,
            key=f"{key_prefix}gpred_pcol_{shaper_id}",
        )
        c3, c4 = st.columns(2)
        drop_when_opts = ["zero_or_nan", "zero", "nan"]
        drop_when = c3.selectbox(
            "Flag group when baseline value is",
            options=drop_when_opts,
            index=(
                drop_when_opts.index(cast(str, existing_config.get("drop_when", "zero_or_nan")))
                if existing_config.get("drop_when") in drop_when_opts
                else 0
            ),
            key=f"{key_prefix}gpred_when_{shaper_id}",
        )
        action_opts = ["drop", "keep"]
        action = c4.selectbox(
            "Action on flagged groups",
            options=action_opts,
            index=(
                action_opts.index(cast(str, existing_config.get("action", "drop")))
                if existing_config.get("action") in action_opts
                else 0
            ),
            key=f"{key_prefix}gpred_act_{shaper_id}",
        )
        return cast(
            ShaperStepConfig,
            {
                "groupBy": group_by,
                "baselineColumn": str(baseline_column or ""),
                "baselineValue": str(baseline_value or ""),
                "predicateColumn": str(predicate_column or ""),
                "drop_when": drop_when,
                "action": action,
            },
        )


class TransformerConfig:
    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        col1, col2 = st.columns(2)
        with col1:
            target_col = st.selectbox(
                "Select Variable to Transform",
                options=sorted(data.columns.tolist()),
                key=f"{key_prefix}trans_col_{shaper_id}",
            )
        with col2:
            type_options = ["Factor (String/Categorical)", "Scalar (Numeric)"]
            target_type_str = st.segmented_control(
                "Convert to:",
                options=type_options,
                default=(
                    type_options[0]
                    if existing_config.get("target_type") == "factor"
                    else type_options[1]
                ),
                key=f"{key_prefix}trans_type_{shaper_id}",
            )
            is_factor = target_type_str is not None and (
                "Factor" in target_type_str or "factor" in target_type_str.lower()
            )
            order_list = None
            if is_factor and target_col in data.columns:
                unique_vals = sorted([str(x) for x in data[target_col].unique()])
                default_order = [
                    v
                    for v in (cast("list[str] | None", existing_config.get("order")) or [])
                    if v in unique_vals
                ] or unique_vals
                order_list = st.multiselect(
                    "Define Factor Order",
                    options=unique_vals,
                    default=default_order,
                    key=f"{key_prefix}trans_order_{shaper_id}",
                )
        result: ShaperStepConfig = cast(
            ShaperStepConfig,
            {
                "column": str(target_col or ""),
                "target_type": "factor" if is_factor else "scalar",
                "order": list(order_list) if order_list else None,
            },
        )
        return result
