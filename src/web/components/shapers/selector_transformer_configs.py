"""Streamlit editors for selector and transformer shapers."""

import json
import math
from numbers import Integral, Real
from typing import Any, cast, get_args

import pandas as pd
import streamlit as st

from src.core.models.shaper_models import ConditionSelectorMode, ShaperStepConfig


class ColumnSelectorConfig:
    """Render a column-selector configuration."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        """Return the configured columns to retain."""
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
    """Edit one current predicate without inferring a different saved operation."""

    _FIELDS = {
        "greater_than": "threshold",
        "less_than": "threshold",
        "greater_or_equal": "threshold",
        "less_or_equal": "threshold",
        "equals": "value",
        "not_equals": "value",
        "contains": "value",
        "range": "range",
        "in": "values",
    }

    @staticmethod
    def _preserve(config: ShaperStepConfig, message: str) -> ShaperStepConfig:
        """Report an unrepresentable edit without replacing its saved predicate."""
        st.error(f"{message} The saved predicate is unchanged.")
        return cast(ShaperStepConfig, dict(config))

    @staticmethod
    def _number(value: Any) -> int | float:
        """Keep exact widget numbers within Streamlit's JSON integer precision."""
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError("Predicate bounds must be finite numbers.")
        if isinstance(value, Integral):
            result = int(value)
            if abs(result) > 2**53 - 1:
                raise ValueError("This integer cannot be represented exactly by the editor.")
            return result
        result_float = float(value)
        if not math.isfinite(result_float):
            raise ValueError("This numeric operand cannot be represented exactly by the editor.")
        return result_float

    @classmethod
    def _edit_number(cls, label: str, value: Any, key: str) -> int | float:
        """Allow fractional edits while retaining the type of an unchanged bound."""
        number = cls._number(value)
        edited = st.number_input(label, value=float(number), key=key)
        return number if edited == number else edited

    @staticmethod
    def _choice_token(value: Any) -> str:
        """Identify JSON scalar choices without merging integer and text labels."""
        if value is not None and type(value) not in (str, int, float, bool):
            raise ValueError("This column contains membership values the editor cannot represent.")
        try:
            return json.dumps([type(value).__name__, value], allow_nan=False)
        except ValueError as exc:
            raise ValueError("Non-finite membership values cannot be edited.") from exc

    @classmethod
    def _membership(cls, values: pd.Series, selected: Any, key: str) -> list[Any]:
        """Retain typed choices, including saved members absent from current rows."""
        if not isinstance(selected, list):
            raise ValueError("Membership requires a values list.")
        choices = {cls._choice_token(value): value for value in selected}
        for value in values.unique().tolist():
            try:
                token = cls._choice_token(value)
            except ValueError:
                # Missing/extension values cannot be serialized as current JSON
                # operands. Saved unsupported operands are rejected above.
                continue
            choices.setdefault(token, value)
        if not choices and not values.empty:
            raise ValueError("This column has no editable JSON scalar membership values.")
        tokens = st.multiselect(
            "Keep rows where value is:",
            options=list(choices),
            default=[cls._choice_token(value) for value in selected],
            format_func=lambda token: repr(choices[token]),
            key=key,
        )
        return [choices[token] for token in tokens]

    @classmethod
    def render(
        cls, data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        """Return the selected current mode and only its corresponding operand."""
        modes = get_args(ConditionSelectorMode)
        saved_mode = existing_config.get("mode")
        if saved_mode is None and set(existing_config) - {"type", "id", "column"}:
            return cls._preserve(existing_config, "The predicate requires an explicit mode.")
        if saved_mode is not None:
            if not isinstance(saved_mode, str) or saved_mode not in modes:
                return cls._preserve(existing_config, "This predicate mode is unsupported.")
            field = cls._FIELDS[saved_mode]
            operands = set(existing_config) & set(cls._FIELDS.values())
            unknown = set(existing_config) - {"type", "id", "column", "mode", field}
            if unknown or (operands and operands != {field}):
                return cls._preserve(existing_config, "The predicate has contradictory fields.")
        saved_column = existing_config.get("column")
        if saved_column is not None and saved_column not in data.columns:
            return cls._preserve(existing_config, "The predicate column is unavailable.")
        if data.columns.empty:
            return cls._preserve(existing_config, "No columns are available for filtering.")

        st.markdown("Filter rows based on column values")
        columns = data.columns.tolist()
        column = st.selectbox(
            "Column to filter",
            options=columns,
            index=columns.index(saved_column) if saved_column in columns else 0,
            key=f"{key_prefix}filter_col_{shaper_id}",
        )
        if column is None:
            return cast(ShaperStepConfig, dict(existing_config))
        values = data[column]
        numeric = pd.api.types.is_numeric_dtype(values.dtype)
        default_mode = saved_mode or (
            "range" if numeric and not pd.api.types.is_bool_dtype(values.dtype) else "in"
        )
        mode = st.selectbox(
            "Filter mode",
            options=modes,
            index=modes.index(default_mode),
            key=f"{key_prefix}filter_mode_{shaper_id}",
        )
        if mode is None:
            return cast(ShaperStepConfig, dict(existing_config))
        config: dict[str, Any] = {"column": column, "mode": mode}
        field = cls._FIELDS[mode]
        try:
            if field == "values":
                config[field] = cls._membership(
                    values,
                    existing_config.get("values", []),
                    f"{key_prefix}filter_values_{shaper_id}",
                )
            elif field in {"threshold", "range"}:
                if not numeric:
                    raise ValueError("Ordered predicates require a numeric column in this editor.")
                saved = existing_config.get(field)
                finite: list[Any] = []
                if saved is None:
                    measured = values.dropna()
                    finite = measured[~measured.isin([float("inf"), float("-inf")])].tolist()
                if saved is None and not finite:
                    raise ValueError("The column has no finite values to initialize bounds.")
                if field == "range":
                    bounds = saved if saved is not None else [min(finite), max(finite)]
                    if not isinstance(bounds, list) or len(bounds) != 2:
                        raise ValueError("Range requires two finite bounds.")
                    lower, upper = [cls._number(value) for value in bounds]
                    config[field] = [
                        cls._edit_number(
                            "Lower bound", value=lower, key=f"{key_prefix}filter_lower_{shaper_id}"
                        ),
                        cls._edit_number(
                            "Upper bound", value=upper, key=f"{key_prefix}filter_upper_{shaper_id}"
                        ),
                    ]
                    if config[field][0] > config[field][1]:
                        raise ValueError("The lower bound must not exceed the upper bound.")
                else:
                    bound = cls._number(saved if saved is not None else min(finite))
                    config[field] = cls._edit_number(
                        "Threshold",
                        value=bound,
                        key=f"{key_prefix}filter_threshold_{mode}_{shaper_id}",
                    )
            else:
                default = (
                    ""
                    if mode == "contains"
                    else next(
                        (
                            value
                            for value in values.dropna().tolist()
                            if type(value) in (str, int, float, bool)
                        ),
                        "",
                    )
                )
                operand = existing_config.get("value", default)
                key = f"{key_prefix}filter_value_{mode}_{shaper_id}"
                if mode != saved_mode and mode == "contains" and not isinstance(operand, str):
                    operand = ""
                if mode == "contains" and not isinstance(operand, str):
                    raise ValueError("Contains requires a literal text operand.")
                if isinstance(operand, str):
                    config[field] = st.text_input("Literal value", value=operand, key=key)
                elif isinstance(operand, bool):
                    config[field] = st.checkbox("Literal value", value=operand, key=key)
                else:
                    config[field] = cls._edit_number("Literal value", value=operand, key=key)
        except (TypeError, ValueError) as exc:
            return cls._preserve(existing_config, str(exc))
        return cast(ShaperStepConfig, config)


class ItemSelectorConfig:
    """Render an exact-value or substring selector configuration."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        """Return the configured item-selection rule."""
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
    """Render a distinct-value cardinality selector configuration."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        """Return the configured group-cardinality rule."""
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
    """Render a baseline predicate selector configuration."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        """Return the configured group predicate and action."""
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
    """Render a factor-or-scalar column transformation."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        """Return the configured target column and data type."""
        col1, col2 = st.columns(2)
        with col1:
            columns = sorted(data.columns.tolist())
            saved_column = cast(str | None, existing_config.get("column"))
            if saved_column and saved_column not in columns:
                st.warning(
                    f"Saved transformation column {saved_column!r} is absent. Choose a replacement."
                )
                columns = [saved_column, *columns]
            target_col = st.selectbox(
                "Select Variable to Transform",
                options=columns,
                index=columns.index(saved_column) if saved_column in columns else 0,
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
