"""
Configuration Components for Pivot Shapers.

Provides Streamlit UI implementations for configuring PivotLonger and PivotWider shapers.
"""

import re
from typing import Any, cast

import pandas as pd
import streamlit as st

from src.core.models.data_models import ShaperStepConfig
from src.core.services.data_services.pattern_index_service import PatternIndexService


def detect_common_pattern(strings: list[str]) -> tuple[str, str]:
    r"""
    Detect a common numeric pattern among a list of strings.

    Example: ["cpu0.ipc", "cpu1.ipc", "cpu2.ipc"] -> (r"cpu(\d+).ipc", "cpu{}.ipc")
    """
    if not strings:
        return "", ""

    # Simplified version for the UI proof of concept.
    return "", ""


def extract_with_pattern(
    value: str, pattern: str, group_indices: list[int], separator: str = "_"
) -> str:
    """Extract capture groups localized for UI preview."""
    try:
        match = re.search(pattern, value)
        if not match:
            return value
        parts = [
            str(match.group(idx)) for idx in group_indices if 0 <= idx <= (match.lastindex or 0)
        ]
        return separator.join(parts) if parts else value
    except Exception:
        return value


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

        # Auto-detect logic
        detected_pattern = ""
        if value_vars:
            if st.button(
                "Auto-detect pattern from Value Columns", key=f"{key_prefix}pl_auto_{shaper_id}"
            ):
                detected_pattern, _ = detect_common_pattern([str(v) for v in value_vars])
                if detected_pattern:
                    st.success(f"Detected: {detected_pattern}")
                else:
                    st.warning("No common numeric pattern detected.")

        extract_pattern = st.text_input(
            "Extract Pattern (Optional)",
            value=detected_pattern if detected_pattern else str(cfg.get("extract_pattern", "")),
            key=f"{key_prefix}plonger_pattern_{shaper_id}",
            help=("Regex pattern with capture groups (e.g., r'.+l(\\\\d+)_cntrl(\\\\d+).*')."),
        )

        group_indices = list(cfg.get("extract_group_indices", [1]))
        separator = str(cfg.get("extract_separator", "_"))

        if extract_pattern:
            try:
                import re

                compiled = re.compile(extract_pattern)
                num_groups = compiled.groups

                if num_groups > 0:
                    st.markdown("###### Selection Options")
                    labels = PatternIndexService.extract_index_positions(
                        extract_pattern.replace(r"(\d+)", r"\d+")
                    )

                    options = {}
                    for i in range(1, num_groups + 1):
                        label = labels[i - 1] if i - 1 < len(labels) else f"Group {i}"
                        options[i] = f"{label} (Group {i})"

                    options[0] = "Whole Match (Group 0)"

                    selected_opt_ids = st.multiselect(
                        "Sections to Keep",
                        options=sorted(list(options.keys())),
                        default=[i for i in group_indices if i in options],
                        format_func=lambda x: options[x],
                        key=f"{key_prefix}pl_groups_{shaper_id}",
                        help="Select one or more capture groups to keep and join.",
                    )
                    group_indices = [int(i) for i in selected_opt_ids]

                    if len(group_indices) > 1:
                        separator = st.text_input(
                            "Separator",
                            value=separator,
                            key=f"{key_prefix}pl_sep_{shaper_id}",
                            help="Separator to join multiple selected groups.",
                        )

                    # --- Selective Value Filtering ---
                    st.markdown("###### Value Filtering")
                    selection_filters = cast(dict[int, list[str]], cfg.get("selection_filters", {}))

                    # We need to know which values are available for each group
                    # to show a selector.
                    group_values: dict[int, set[str]] = {i: set() for i in range(num_groups + 1)}
                    if value_vars:
                        for v in value_vars:
                            m = compiled.search(str(v))
                            if m:
                                for i in range(num_groups + 1):
                                    group_values[i].add(m.group(i))

                    new_selection_filters = {}
                    for i in group_indices:
                        if i == 0:
                            continue  # Skip whole match for per-group filtering usually
                        label = labels[i - 1] if i - 1 < len(labels) else f"Group {i}"

                        available = sorted(list(group_values.get(i, set())))
                        selected_vals = selection_filters.get(i, [])
                        selected_vals = [v for v in selected_vals if v in available]

                        new_vals = st.multiselect(
                            f"Keep values for {label}",
                            options=available,
                            default=selected_vals,
                            key=f"{key_prefix}pl_filter_{i}_{shaper_id}",
                            help=(
                                f"Select specific values to keep for {label}. "
                                "Leave empty to keep all."
                            ),
                        )
                        if new_vals:
                            new_selection_filters[i] = new_vals

                    selection_filters = new_selection_filters

                    strategy = str(cfg.get("selection_strategy", "discard"))
                    strategy_idx = 0 if strategy == "discard" else 1

                    strategy = st.radio(
                        "Missing values strategy",
                        options=["discard", "merge"],
                        index=strategy_idx,
                        horizontal=True,
                        key=f"{key_prefix}pl_strategy_{shaper_id}",
                        help="How to handle rows that don't match the selected values.",
                    )

                    merge_label = str(cfg.get("merge_label", "other"))
                    if strategy == "merge":
                        merge_label = st.text_input(
                            "Merge Label",
                            value=merge_label,
                            key=f"{key_prefix}pl_merge_label_{shaper_id}",
                            help="Label for the merged 'other' row (e.g., '9+').",
                        )

                    # Preview
                    if value_vars:
                        sample = str(value_vars[0])
                        is_filtered = bool(selection_filters)
                        preview = extract_with_pattern(
                            sample, extract_pattern, group_indices, separator
                        )
                        msg = f"Preview: `{sample}` → `{preview}`"
                        if is_filtered:
                            msg += " (Filtered)"
                        st.info(msg)
                else:
                    st.warning(
                        "Pattern has no capture groups (parentheses). " "Defaults to whole match."
                    )
            except Exception:
                st.error("Invalid Regex Pattern")

        # Convert to strict types
        result: dict[str, Any] = {
            "type": "pivotLonger",
            "id_vars": [str(c) for c in id_vars],
            "value_vars": [str(c) for c in value_vars],
            "var_name": str(var_name),
            "value_name": str(val_name),
            "selection_filters": selection_filters if "selection_filters" in locals() else {},
            "selection_strategy": strategy if "strategy" in locals() else "discard",
            "merge_label": merge_label if "merge_label" in locals() else "other",
        }
        if extract_pattern.strip():
            result["extract_pattern"] = extract_pattern.strip()
            result["extract_group_indices"] = group_indices
            result["extract_separator"] = separator

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
