from typing import Any, Dict

import pandas as pd
import streamlit as st


class ColumnSelectorConfig:
    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: Dict[str, Any], key_prefix: str, shaper_id: str
    ) -> Dict[str, Any]:
        st.markdown("Select which columns to keep")
        default_cols = [c for c in existing_config.get("columns", []) if c in data.columns]
        if not default_cols and not data.columns.empty:
            default_cols = [data.columns[0]]

        selected_columns = st.multiselect(
            "Columns to keep",
            options=data.columns.tolist(),
            default=default_cols,
            key=f"{key_prefix}colsel_{shaper_id}",
        )
        return {"columns": selected_columns if selected_columns else []}


class ConditionSelectorConfig:
    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: Dict[str, Any], key_prefix: str, shaper_id: str
    ) -> Dict[str, Any]:
        categorical_cols = data.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
        all_cols = categorical_cols + numeric_cols

        st.markdown("Filter rows based on column values")
        filter_col_default = existing_config.get("column")
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
            return {}

        is_numeric = filter_column in numeric_cols
        if is_numeric:
            filter_modes = ["range", "greater_than", "less_than", "equals"]
            filter_mode_default = existing_config.get("mode", "range")
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
                default_range = existing_config.get("range", [min_val, max_val])
                value_range = st.slider(
                    "Value range",
                    min_value=min_val,
                    max_value=max_val,
                    value=(float(default_range[0]), float(default_range[1])),
                    key=f"{key_prefix}filter_range_{shaper_id}",
                )
                return {"column": filter_column, "mode": "range", "range": list(value_range)}
            # ... (Simplified for brevity, similar for gt/lt/eq)
            elif filter_mode == "greater_than":
                threshold = st.number_input(
                    "Greater than",
                    value=float(existing_config.get("threshold", min_val)),
                    key=f"{key_prefix}filter_gt_{shaper_id}",
                )
                return {"column": filter_column, "mode": "greater_than", "threshold": threshold}
            elif filter_mode == "less_than":
                threshold = st.number_input(
                    "Less than",
                    value=float(existing_config.get("threshold", max_val)),
                    key=f"{key_prefix}filter_lt_{shaper_id}",
                )
                return {"column": filter_column, "mode": "less_than", "threshold": threshold}
            else:
                value = st.number_input(
                    "Equals",
                    value=float(existing_config.get("value", min_val)),
                    key=f"{key_prefix}filter_eq_{shaper_id}",
                )
                return {"column": filter_column, "mode": "equals", "value": value}
        else:
            unique_values = data[filter_column].unique().tolist()
            default_values = [v for v in existing_config.get("values", []) if v in unique_values]
            selected_values = st.multiselect(
                "Keep rows where value is:",
                options=unique_values,
                default=default_values,
                key=f"{key_prefix}filter_values_{shaper_id}",
            )
            return {"column": filter_column, "values": selected_values}
        return {}


class TransformerConfig:
    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: Dict[str, Any], key_prefix: str, shaper_id: str
    ) -> Dict[str, Any]:
        col1, col2 = st.columns(2)
        with col1:
            target_col = st.selectbox(
                "Select Variable to Transform",
                options=sorted(data.columns.tolist()),
                key=f"{key_prefix}trans_col_{shaper_id}",
            )
        with col2:
            target_type_str = st.radio(
                "Convert to:",
                options=["Factor (String/Categorical)", "Scalar (Numeric)"],
                index=0 if existing_config.get("target_type") == "factor" else 1,
                key=f"{key_prefix}trans_type_{shaper_id}",
            )
            is_factor = "Factor" in target_type_str or "factor" in target_type_str.lower()
            order_list = None
            if is_factor and target_col in data.columns:
                unique_vals = sorted([str(x) for x in data[target_col].unique()])
                default_order = [
                    v for v in existing_config.get("order", []) if v in unique_vals
                ] or unique_vals
                order_list = st.multiselect(
                    "Define Factor Order",
                    options=unique_vals,
                    default=default_order,
                    key=f"{key_prefix}trans_order_{shaper_id}",
                )
        return {
            "column": target_col,
            "target_type": "factor" if is_factor else "scalar",
            "order": order_list,
        }
