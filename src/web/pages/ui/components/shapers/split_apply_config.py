"""
Split-Apply Config — UI for the SplitApply composite shaper.

Lets the user define:
  1. Join columns (categorical columns shared across all groups).
  2. N column groups (2–4), each with its own numeric columns and
     a mini sub-pipeline of shapers applied independently.

Each sub-pipeline step delegates to the **exact same** UI component
used by the main pipeline (MeanConfig, NormalizeConfig, SortConfig,
ConditionSelectorConfig), ensuring a consistent user experience.

This is the UI counterpart of
:class:`src.core.services.shapers.impl.split_apply.SplitApply`.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# ── Sub-step config dispatch ──────────────────────────────────────
# Lazily populated to avoid circular imports.
# Maps display name → (internal_type, render_fn).

_SUB_SHAPER_DISPATCH: Dict[str, Tuple[str, Callable[..., Dict[str, Any]]]] = {}
_DISPATCH_INITIALIZED: bool = False

_GROUP_LABELS: List[str] = [
    "Group A",
    "Group B",
    "Group C",
    "Group D",
]

_MIN_GROUPS: int = 2
_MAX_GROUPS: int = 4

# Reverse lookup: internal type → display name
_REVERSE_TYPE_MAP: Dict[str, str] = {
    "mean": "Mean Calculator",
    "normalize": "Normalize",
    "sort": "Sort",
    "conditionSelector": "Filter",
}


def _init_dispatch() -> None:
    """Lazily initialize the dispatch dict to avoid circular imports."""
    global _DISPATCH_INITIALIZED  # noqa: PLW0603
    if _DISPATCH_INITIALIZED:
        return

    from src.web.pages.ui.components.shapers.mean_config import MeanConfig
    from src.web.pages.ui.components.shapers.normalize_config import (
        NormalizeConfig,
    )
    from src.web.pages.ui.components.shapers.selector_transformer_configs import (
        ConditionSelectorConfig,
    )
    from src.web.pages.ui.components.shapers.sort_config import SortConfig

    _SUB_SHAPER_DISPATCH.update(
        {
            "Mean Calculator": ("mean", MeanConfig.render),
            "Normalize": ("normalize", NormalizeConfig.render),
            "Sort": ("sort", SortConfig.render),
            "Filter": ("conditionSelector", ConditionSelectorConfig.render),
        }
    )
    _DISPATCH_INITIALIZED = True


class SplitApplyConfig:
    """UI component for configuring the SplitApply shaper."""

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
        _init_dispatch()

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

        # ── Number of groups ──────────────────────────────────────
        existing_groups: List[Dict[str, Any]] = existing_config.get("groups", [])
        default_num_groups: int = max(
            _MIN_GROUPS, min(len(existing_groups) or _MIN_GROUPS, _MAX_GROUPS)
        )
        num_groups: int = st.slider(
            "Number of groups",
            min_value=_MIN_GROUPS,
            max_value=_MAX_GROUPS,
            value=default_num_groups,
            key=f"{key_prefix}sa_ngroups_{shaper_id}",
            help="How many independent column groups to create (2–4).",
        )

        # Pad existing groups if needed
        while len(existing_groups) < num_groups:
            existing_groups.append({})

        # ── Render each group in an expander ──────────────────────
        groups: List[Dict[str, Any]] = []
        for g_idx in range(num_groups):
            label: str = _GROUP_LABELS[g_idx]
            with st.expander(f"**{label}**", expanded=True):
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

        Delegates to the exact same UI component used by the main
        shaper pipeline (MeanConfig, NormalizeConfig, SortConfig,
        ConditionSelectorConfig) so the user gets an identical
        interface.

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
        st.markdown(f"**Step {step_index + 1}**")

        # ── Shaper type selector ──────────────────────────────────
        display_names: List[str] = list(_SUB_SHAPER_DISPATCH.keys())
        existing_type: str = existing_step.get("type", "")
        default_display: str = _REVERSE_TYPE_MAP.get(existing_type, display_names[0])
        default_idx: int = (
            display_names.index(default_display) if default_display in display_names else 0
        )

        selected_display: str = st.selectbox(
            "Transformation",
            options=display_names,
            index=default_idx,
            key=f"{key_base}_type",
        )
        shaper_type, render_fn = _SUB_SHAPER_DISPATCH[selected_display]

        # ── Delegate to the real config component ─────────────────
        sub_key_prefix: str = f"{key_base}_"
        sub_shaper_id: str = f"sub{step_index}"

        cfg: Dict[str, Any] = render_fn(
            data,
            existing_step,
            sub_key_prefix,
            sub_shaper_id,
        )

        cfg["type"] = shaper_type
        return cfg
