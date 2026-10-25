"""Streamlit controls for SplitApply column groups and sub-pipelines."""

from collections.abc import Callable, Mapping, Sequence
from typing import cast

import pandas as pd
import streamlit as st

from src.core.models.shaper_models import ShaperStepConfig, SplitApplyGroupConfig

# Initialized lazily to avoid circular config-component imports.
_SUB_SHAPER_DISPATCH: dict[str, Callable[..., ShaperStepConfig]] = {}
_STATE: dict[str, bool] = {"initialized": False}

_GROUP_LABELS: list[str] = [
    "Group A",
    "Group B",
    "Group C",
    "Group D",
]

_MIN_GROUPS: int = 2
_MAX_GROUPS: int = 4


def _init_dispatch() -> None:
    """Lazily initialize the dispatch dict to avoid circular imports."""
    if _STATE["initialized"]:
        return

    from src.web.components.shapers.mean_config import MeanConfig
    from src.web.components.shapers.normalize_config import NormalizeConfig
    from src.web.components.shapers.selector_transformer_configs import (
        ConditionSelectorConfig,
    )
    from src.web.components.shapers.sort_config import SortConfig

    _SUB_SHAPER_DISPATCH.update(
        {
            "mean": MeanConfig.render,
            "normalize": NormalizeConfig.render,
            "sort": SortConfig.render,
            "conditionSelector": ConditionSelectorConfig.render,
        }
    )
    _STATE["initialized"] = True


class SplitApplyConfig:
    """UI component for configuring the SplitApply shaper."""

    @staticmethod
    def render(
        data: pd.DataFrame,
        existing_config: ShaperStepConfig,
        key_prefix: str,
        shaper_id: int,
        *,
        display_names: dict[str, str],
    ) -> ShaperStepConfig:
        """Render the SplitApply configuration UI.

        Args:
            data: Current DataFrame for column introspection.
            existing_config: Previously saved configuration.
            key_prefix: Unique prefix for Streamlit widget keys.
            shaper_id: Unique shaper instance ID.
            display_names: Current facade-provided editor labels and identifiers.

        Returns:
            Configuration dictionary consumable by ``SplitApply``.
        """
        _init_dispatch()

        numeric_cols: list[str] = data.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols: list[str] = data.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()

        st.markdown(
            "Split the data into independent column groups, apply "
            "separate transformations to each, then merge the results. "
            "Ideal for dual-axis plots where each axis needs its own "
            "Mean / Normalize step."
        )

        # Join Columns
        join_default: list[str] = [
            c
            for c in cast(list[str], existing_config.get("joinColumns", categorical_cols))
            if c in categorical_cols
        ]
        join_columns: list[str] = st.multiselect(
            "Join columns (shared categorical columns)",
            options=categorical_cols,
            default=join_default or categorical_cols,
            key=f"{key_prefix}sa_join_{shaper_id}",
            help=(
                "Categorical columns used to merge the groups back "
                "together. Typically all categorical columns."
            ),
        )

        # Number of groups
        # Copy: this list is the live persisted pipeline config (passed uncopied through
        # the controller); padding it below must not mutate stored state.
        existing_groups: list[SplitApplyGroupConfig] = list(
            cast("list[SplitApplyGroupConfig]", existing_config.get("groups", []))
        )
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
            existing_groups.append({"columns": []})

        # Render each group in an expander
        groups: list[SplitApplyGroupConfig] = []
        for g_idx in range(num_groups):
            label: str = _GROUP_LABELS[g_idx]
            with st.expander(f"**{label}**", expanded=True):
                grp = SplitApplyConfig._render_group(
                    data=data,
                    display_names=display_names,
                    numeric_cols=numeric_cols,
                    categorical_cols=categorical_cols,
                    join_columns=join_columns,
                    existing_group=existing_groups[g_idx],
                    key_prefix=key_prefix,
                    shaper_id=shaper_id,
                    group_index=g_idx,
                )
                groups.append(grp)

        return cast(
            ShaperStepConfig,
            {
                "joinColumns": join_columns,
                "groups": groups,
            },
        )

    # Private helpers
    @staticmethod
    def _render_group(
        data: pd.DataFrame,
        numeric_cols: list[str],
        categorical_cols: list[str],
        join_columns: list[str],
        existing_group: SplitApplyGroupConfig,
        key_prefix: str,
        shaper_id: int,
        group_index: int,
        display_names: dict[str, str],
    ) -> SplitApplyGroupConfig:
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

        # Column selection
        col_default: list[str] = [c for c in existing_group.get("columns", []) if c in numeric_cols]
        columns: list[str] = st.multiselect(
            "Numeric columns",
            options=numeric_cols,
            default=col_default,
            key=f"{gk}_cols",
            help="Numeric columns processed by this group's pipeline.",
        )

        # Sub-pipeline
        existing_pipeline: Sequence[Mapping[str, object]] = existing_group.get("pipeline", [])
        pipeline: list[Mapping[str, object]] = SplitApplyConfig._render_sub_pipeline(
            data=data,
            columns=columns,
            join_columns=join_columns,
            categorical_cols=categorical_cols,
            existing_pipeline=existing_pipeline,
            key_base=gk,
            display_names=display_names,
        )

        return {"columns": columns, "pipeline": pipeline}

    @staticmethod
    def _render_sub_pipeline(
        data: pd.DataFrame,
        columns: list[str],
        join_columns: list[str],
        categorical_cols: list[str],
        existing_pipeline: Sequence[Mapping[str, object]],
        key_base: str,
        display_names: dict[str, str],
    ) -> list[Mapping[str, object]]:
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
        pipeline: list[Mapping[str, object]] = []

        # How many steps does this group have?
        existing_count: int = len(existing_pipeline)
        step_count_key: str = f"{key_base}_step_count"

        # Use session_state to track add/remove
        if step_count_key not in st.session_state:
            st.session_state[step_count_key] = max(existing_count, 0)

        num_steps: int = st.session_state[step_count_key]

        for s_idx in range(num_steps):
            existing_step: Mapping[str, object] = (
                existing_pipeline[s_idx] if s_idx < existing_count else cast(ShaperStepConfig, {})
            )
            step_cfg: Mapping[str, object] | None = SplitApplyConfig._render_sub_step(
                data=data,
                display_names=display_names,
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
            st.button(
                "+ Add step",
                key=f"{key_base}_add",
                on_click=lambda: st.session_state.__setitem__(step_count_key, num_steps + 1),
            )
        with bc2:
            if num_steps > 0:
                st.button(
                    "− Remove last",
                    key=f"{key_base}_rem",
                    on_click=lambda: st.session_state.__setitem__(step_count_key, num_steps - 1),
                )

        return pipeline

    @staticmethod
    def _render_sub_step(
        data: pd.DataFrame,
        columns: list[str],
        join_columns: list[str],
        categorical_cols: list[str],
        existing_step: Mapping[str, object],
        key_base: str,
        step_index: int,
        display_names: dict[str, str],
    ) -> Mapping[str, object] | None:
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

        # Shaper type selector
        labels = {kind: label for label, kind in display_names.items()}
        options = [labels[kind] for kind in _SUB_SHAPER_DISPATCH]
        existing_type = existing_step.get("type", "")
        if not isinstance(existing_type, str) or (
            existing_type and existing_type not in _SUB_SHAPER_DISPATCH
        ):
            st.info(
                "This transformation has no editor in this group. Its configuration is preserved."
            )
            return existing_step
        default_display: str = labels.get(existing_type, options[0])
        default_idx: int = options.index(default_display) if default_display in options else 0

        selected_display: str = st.selectbox(
            "Transformation",
            options=options,
            index=default_idx,
            key=f"{key_base}_type",
        )
        shaper_type = display_names[selected_display]
        render_fn = _SUB_SHAPER_DISPATCH[shaper_type]

        # Delegate to the real config component
        sub_key_prefix: str = f"{key_base}_"
        sub_shaper_id: str = f"sub{step_index}"

        cfg: ShaperStepConfig = render_fn(
            data,
            cast(ShaperStepConfig, existing_step),
            sub_key_prefix,
            sub_shaper_id,
        )

        return cast(ShaperStepConfig, {**cfg, "type": shaper_type})
