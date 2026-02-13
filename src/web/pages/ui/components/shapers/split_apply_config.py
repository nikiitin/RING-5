"""
Split-Apply Config — UI for the SplitApply composite shaper.

Lets the user define:
  1. Join columns (categorical columns shared across all groups).
  2. Two column groups, each with its own numeric columns and
     a mini sub-pipeline of shapers applied independently.

This is the UI counterpart of
:class:`src.core.services.shapers.impl.split_apply.SplitApply`.
"""

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


class SplitApplyConfig:
    """UI component for configuring the SplitApply shaper."""

    # Shaper types available inside sub-pipelines.
    # We only expose those that make sense for per-axis transforms.
    _SUB_SHAPER_TYPES: Dict[str, str] = {
        "Mean Calculator": "mean",
        "Normalize": "normalize",
        "Sort": "sort",
        "Filter": "conditionSelector",
    }

    @staticmethod
    def render(
        data: pd.DataFrame,
        existing_config: Dict[str, Any],
        key_prefix: str,
        shaper_id: str,
    ) -> Dict[str, Any]:
        """Render the SplitApply configuration UI.

        Args:
            data: Current DataFrame for column introspection.
            existing_config: Previously saved configuration.
            key_prefix: Unique prefix for Streamlit widget keys.
            shaper_id: Unique shaper instance ID.

        Returns:
            Configuration dictionary consumable by ``SplitApply``.
        """
        numeric_cols: List[str] = data.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols: List[str] = data.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()

        st.markdown(
            "Split the data into independent column groups, apply "
            "separate transformations to each, then merge the results. "
            "Ideal for dual-axis plots where each axis needs its own "
            "Mean / Normalize step."
        )

        # ── Join Columns ──────────────────────────────────────────
        join_default: List[str] = [
            c for c in existing_config.get("joinColumns", categorical_cols) if c in categorical_cols
        ]
        join_columns: List[str] = st.multiselect(
            "Join columns (shared categorical columns)",
            options=categorical_cols,
            default=join_default or categorical_cols,
            key=f"{key_prefix}sa_join_{shaper_id}",
            help=(
                "Categorical columns used to merge the groups back "
                "together. Typically all categorical columns."
            ),
        )

        # ── Groups ────────────────────────────────────────────────
        existing_groups: List[Dict[str, Any]] = existing_config.get("groups", [{}, {}])
        # Always show exactly 2 groups (matching dual-axis paradigm).
        while len(existing_groups) < 2:
            existing_groups.append({})

        groups: List[Dict[str, Any]] = []
        group_labels: List[str] = [
            "Group A (e.g. left axis / bars)",
            "Group B (e.g. right axis / dots)",
        ]
        col_a, col_b = st.columns(2)

        for g_idx, (container, label) in enumerate(zip([col_a, col_b], group_labels)):
            with container:
                st.markdown(f"**{label}**")
                grp = SplitApplyConfig._render_group(
                    data=data,
                    numeric_cols=numeric_cols,
                    categorical_cols=categorical_cols,
                    join_columns=join_columns,
                    existing_group=existing_groups[g_idx],
                    key_prefix=key_prefix,
                    shaper_id=shaper_id,
                    group_index=g_idx,
                )
                groups.append(grp)

        return {
            "joinColumns": join_columns,
            "groups": groups,
        }

    # ── Private helpers ───────────────────────────────────────────

    @staticmethod
    def _render_group(
        data: pd.DataFrame,
        numeric_cols: List[str],
        categorical_cols: List[str],
        join_columns: List[str],
        existing_group: Dict[str, Any],
        key_prefix: str,
        shaper_id: str,
        group_index: int,
    ) -> Dict[str, Any]:
        """Render config UI for a single column group.

        Args:
            data: Full DataFrame (for sub-shaper config introspection).
            numeric_cols: All numeric column names.
            categorical_cols: All categorical column names.
            join_columns: Currently selected join columns.
            existing_group: Saved config for this group.
            key_prefix: Widget key prefix.
            shaper_id: Shaper instance ID.
            group_index: 0-based group index.

        Returns:
            Group config dict with ``columns`` and ``pipeline`` keys.
        """
        gk: str = f"{key_prefix}sa_g{group_index}_{shaper_id}"

        # ── Column selection ──────────────────────────────────────
        col_default: List[str] = [c for c in existing_group.get("columns", []) if c in numeric_cols]
        columns: List[str] = st.multiselect(
            "Numeric columns",
            options=numeric_cols,
            default=col_default,
            key=f"{gk}_cols",
            help="Numeric columns processed by this group's pipeline.",
        )

        # ── Sub-pipeline ──────────────────────────────────────────
        existing_pipeline: List[Dict[str, Any]] = existing_group.get("pipeline", [])
        pipeline: List[Dict[str, Any]] = SplitApplyConfig._render_sub_pipeline(
            data=data,
            columns=columns,
            join_columns=join_columns,
            categorical_cols=categorical_cols,
            existing_pipeline=existing_pipeline,
            key_base=gk,
        )

        return {"columns": columns, "pipeline": pipeline}

    @staticmethod
    def _render_sub_pipeline(
        data: pd.DataFrame,
        columns: List[str],
        join_columns: List[str],
        categorical_cols: List[str],
        existing_pipeline: List[Dict[str, Any]],
        key_base: str,
    ) -> List[Dict[str, Any]]:
        """Render the sub-pipeline editor for one group.

        Shows a selectbox to choose a shaper type and automatically
        generates pre-filled config for the most common operations
        (Mean and Normalize) so the user doesn't have to repeat
        column selections manually.

        Args:
            data: Full DataFrame.
            columns: Numeric columns belonging to this group.
            join_columns: Categorical join columns.
            categorical_cols: All categorical columns.
            existing_pipeline: Previously saved sub-pipeline.
            key_base: Widget key base string.

        Returns:
            List of shaper config dicts for this group.
        """
        pipeline: List[Dict[str, Any]] = []

        # How many steps does this group have?
        existing_count: int = len(existing_pipeline)
        step_count_key: str = f"{key_base}_step_count"

        # Use session_state to track add/remove
        if step_count_key not in st.session_state:
            st.session_state[step_count_key] = max(existing_count, 0)

        num_steps: int = st.session_state[step_count_key]

        for s_idx in range(num_steps):
            existing_step: Dict[str, Any] = (
                existing_pipeline[s_idx] if s_idx < existing_count else {}
            )
            step_cfg: Optional[Dict[str, Any]] = SplitApplyConfig._render_sub_step(
                data=data,
                columns=columns,
                join_columns=join_columns,
                categorical_cols=categorical_cols,
                existing_step=existing_step,
                key_base=f"{key_base}_s{s_idx}",
                step_index=s_idx,
            )
            if step_cfg:
                pipeline.append(step_cfg)

        # Add / Remove buttons
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("+ Add step", key=f"{key_base}_add"):
                st.session_state[step_count_key] = num_steps + 1
                st.rerun()
        with bc2:
            if num_steps > 0 and st.button("− Remove last", key=f"{key_base}_rem"):
                st.session_state[step_count_key] = num_steps - 1
                st.rerun()

        return pipeline

    @staticmethod
    def _render_sub_step(
        data: pd.DataFrame,
        columns: List[str],
        join_columns: List[str],
        categorical_cols: List[str],
        existing_step: Dict[str, Any],
        key_base: str,
        step_index: int,
    ) -> Optional[Dict[str, Any]]:
        """Render config for a single sub-pipeline step.

        For Mean and Normalize, pre-fills ``meanVars`` / ``normalizeVars``
        with the group's columns so the user only needs to choose the
        algorithm and grouping.

        Args:
            data: Full DataFrame.
            columns: This group's numeric columns.
            join_columns: Categorical join columns.
            categorical_cols: All categorical columns.
            existing_step: Previously saved step config.
            key_base: Widget key base string.
            step_index: 0-based step index.

        Returns:
            Shaper config dict, or None if no type selected.
        """
        st.markdown(f"Step {step_index + 1}")

        # Shaper type selector
        display_names: List[str] = list(SplitApplyConfig._SUB_SHAPER_TYPES.keys())
        existing_type: str = existing_step.get("type", "")
        # Reverse-lookup display name from internal type
        reverse: Dict[str, str] = {v: k for k, v in SplitApplyConfig._SUB_SHAPER_TYPES.items()}
        default_display: str = reverse.get(existing_type, display_names[0])
        default_idx: int = (
            display_names.index(default_display) if default_display in display_names else 0
        )

        selected_display: str = st.selectbox(
            "Transformation",
            options=display_names,
            index=default_idx,
            key=f"{key_base}_type",
        )
        shaper_type: str = SplitApplyConfig._SUB_SHAPER_TYPES[selected_display]

        # Render type-specific config
        if shaper_type == "mean":
            return SplitApplyConfig._render_mean_step(
                data,
                columns,
                categorical_cols,
                existing_step,
                key_base,
            )
        elif shaper_type == "normalize":
            return SplitApplyConfig._render_normalize_step(
                data,
                columns,
                categorical_cols,
                existing_step,
                key_base,
            )
        elif shaper_type == "sort":
            # Delegate to the standard SortConfig
            from src.web.pages.ui.components.shapers.sort_config import (
                SortConfig,
            )

            cfg = SortConfig.render(
                data,
                existing_step,
                f"{key_base}_",
                f"sub{step_index}",
            )
            cfg["type"] = "sort"
            return cfg
        elif shaper_type == "conditionSelector":
            from src.web.pages.ui.components.shapers.selector_transformer_configs import (
                ConditionSelectorConfig,
            )

            cfg = ConditionSelectorConfig.render(
                data,
                existing_step,
                f"{key_base}_",
                f"sub{step_index}",
            )
            cfg["type"] = "conditionSelector"
            return cfg

        return None

    # ── Pre-filled sub-step renderers ─────────────────────────────

    @staticmethod
    def _render_mean_step(
        data: pd.DataFrame,
        columns: List[str],
        categorical_cols: List[str],
        existing_step: Dict[str, Any],
        key_base: str,
    ) -> Dict[str, Any]:
        """Render Mean config pre-filled with this group's columns.

        Args:
            data: Full DataFrame.
            columns: This group's numeric columns (pre-selected as meanVars).
            categorical_cols: All categorical columns.
            existing_step: Previously saved step config.
            key_base: Widget key base string.

        Returns:
            Mean shaper config dict.
        """
        mean_algos: List[str] = ["arithmean", "geomean", "hmean"]
        algo_default: str = existing_step.get("meanAlgorithm", "arithmean")
        algo_idx: int = mean_algos.index(algo_default) if algo_default in mean_algos else 0
        mean_algorithm: str = st.selectbox(
            "Mean type",
            options=mean_algos,
            index=algo_idx,
            key=f"{key_base}_algo",
        )

        # Grouping columns
        group_default: List[str] = [
            c for c in existing_step.get("groupingColumns", []) if c in categorical_cols
        ]
        grouping_columns: List[str] = st.multiselect(
            "Group by",
            options=categorical_cols,
            default=group_default,
            key=f"{key_base}_grp",
        )

        # Replacing column
        replace_default: str = existing_step.get("replacingColumn", "")
        replace_idx: int = (
            categorical_cols.index(replace_default) if replace_default in categorical_cols else 0
        )
        replacing_column: str = st.selectbox(
            "Replacing column",
            options=categorical_cols,
            index=replace_idx,
            key=f"{key_base}_repl",
        )

        return {
            "type": "mean",
            "meanAlgorithm": mean_algorithm,
            "meanVars": list(columns),
            "groupingColumns": grouping_columns,
            "replacingColumn": replacing_column,
        }

    @staticmethod
    def _render_normalize_step(
        data: pd.DataFrame,
        columns: List[str],
        categorical_cols: List[str],
        existing_step: Dict[str, Any],
        key_base: str,
    ) -> Dict[str, Any]:
        """Render Normalize config pre-filled with this group's columns.

        Args:
            data: Full DataFrame.
            columns: This group's numeric columns (pre-selected as
                normalizeVars and normalizerVars).
            categorical_cols: All categorical columns.
            existing_step: Previously saved step config.
            key_base: Widget key base string.

        Returns:
            Normalize shaper config dict.
        """
        # Normalizer column
        norm_col_default: str = existing_step.get("normalizerColumn", "")
        norm_col_idx: int = (
            categorical_cols.index(norm_col_default) if norm_col_default in categorical_cols else 0
        )
        normalizer_column: str = st.selectbox(
            "Normalizer column",
            options=categorical_cols,
            index=norm_col_idx,
            key=f"{key_base}_ncol",
        )

        # Normalizer value
        normalizer_value: Optional[str] = None
        if normalizer_column and normalizer_column in data.columns:
            unique_vals: List[str] = data[normalizer_column].unique().tolist()
            val_default: str = existing_step.get("normalizerValue", "")
            val_idx: int = unique_vals.index(val_default) if val_default in unique_vals else 0
            normalizer_value = st.selectbox(
                "Baseline value",
                options=unique_vals,
                index=val_idx,
                key=f"{key_base}_nval",
            )

        # Group by
        gb_default: List[str] = [
            c for c in existing_step.get("groupBy", []) if c in categorical_cols
        ]
        group_by: List[str] = st.multiselect(
            "Group by",
            options=categorical_cols,
            default=gb_default,
            key=f"{key_base}_ngb",
        )

        return {
            "type": "normalize",
            "normalizeVars": list(columns),
            "normalizerVars": list(columns),
            "normalizerColumn": normalizer_column,
            "normalizerValue": normalizer_value,
            "groupBy": group_by,
        }
