"""Derive Column Config — UI for the DeriveColumn shaper.

Renders op-dependent widgets for creating one column from existing columns:
sum / ratio / scalar / concat / map (value recode).
"""

import json
from typing import Any, cast

import pandas as pd
import streamlit as st

from src.core.models.shaper_models import ShaperStepConfig, ShaperValue
from src.core.common.security_limits import MAX_PIPELINE_CONFIG_BYTES
from src.web.components.common.scalar_values import scalar_token

_OPS = ["sum", "ratio", "scalar", "concat", "map"]
_SCALAR_OPS = ["+", "-", "*", "/"]
_OP_HELP = (
    "sum/concat: combine N columns · ratio: a / b · "
    "scalar: column ∘ literal · map: recode a column's values"
)


def _index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


class DeriveColumnConfig:
    """Render controls for deriving a column from existing data."""

    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
        """Render derive-column controls.

        Args:
            data: Data available to the shaper.
            existing_config: Values from a previously configured step.
            key_prefix: Stable prefix for Streamlit widget keys.
            shaper_id: Identifier of the pipeline step.

        Returns:
            Updated derive-column configuration.
        """
        cols = data.columns.tolist()
        st.markdown("Create a new column from existing ones.")

        op = st.selectbox(
            "Operation",
            options=_OPS,
            index=_index(_OPS, cast(str, existing_config.get("op", "sum"))),
            help=_OP_HELP,
            key=f"{key_prefix}dc_op_{shaper_id}",
        )
        dest = st.text_input(
            "New column name",
            value=cast(str, existing_config.get("dest", "")),
            key=f"{key_prefix}dc_dest_{shaper_id}",
        )
        cfg: dict[str, Any] = {"op": op, "dest": dest}
        prev_sources = [
            c for c in cast("list[str]", existing_config.get("sources", [])) if c in cols
        ]

        if op in ("sum", "concat"):
            cfg["sources"] = st.multiselect(
                "Source columns",
                options=cols,
                default=prev_sources or cols[:1],
                key=f"{key_prefix}dc_src_{shaper_id}",
            )
            if op == "concat":
                cfg["separator"] = st.text_input(
                    "Separator",
                    value=cast(str, existing_config.get("separator", "_")),
                    key=f"{key_prefix}dc_sep_{shaper_id}",
                )
        elif op == "ratio":
            c1, c2 = st.columns(2)
            num = c1.selectbox(
                "Numerator",
                options=cols,
                index=_index(cols, prev_sources[0] if prev_sources else ""),
                key=f"{key_prefix}dc_num_{shaper_id}",
            )
            den = c2.selectbox(
                "Denominator",
                options=cols,
                index=_index(cols, prev_sources[1] if len(prev_sources) > 1 else ""),
                key=f"{key_prefix}dc_den_{shaper_id}",
            )
            cfg["sources"] = [num, den]
            zero_opts = ["nan", "propagate"]
            cfg["zero_denominator"] = st.selectbox(
                "When denominator is 0",
                options=zero_opts,
                index=_index(zero_opts, cast(str, existing_config.get("zero_denominator", "nan"))),
                help="'nan' → result is NaN (like Division); 'propagate' → raw division (inf).",
                key=f"{key_prefix}dc_zero_{shaper_id}",
            )
        elif op == "scalar":
            src = st.selectbox(
                "Source column",
                options=cols,
                index=_index(cols, prev_sources[0] if prev_sources else ""),
                key=f"{key_prefix}dc_scol_{shaper_id}",
            )
            c1, c2 = st.columns(2)
            scalar_op = c1.selectbox(
                "Operator",
                options=_SCALAR_OPS,
                index=_index(_SCALAR_OPS, cast(str, existing_config.get("scalar_op", "/"))),
                key=f"{key_prefix}dc_sop_{shaper_id}",
            )
            value = c2.number_input(
                "Value",
                value=float(cast(float, existing_config.get("scalar", 1.0))),
                key=f"{key_prefix}dc_sval_{shaper_id}",
            )
            cfg.update({"sources": [src], "scalar_op": scalar_op, "scalar": float(value)})
        else:  # map
            src = st.selectbox(
                "Source column",
                options=cols,
                index=_index(cols, prev_sources[0] if prev_sources else ""),
                key=f"{key_prefix}dc_mcol_{shaper_id}",
            )
            cfg["sources"] = [src]
            prev_map = cast(dict[str, ShaperValue | None], existing_config.get("mapping", {}))
            for mapping_value in prev_map.values():
                scalar_token(mapping_value)
            if not prev_map and src in data.columns:
                prev_map = {
                    value: value for value in data[src].dropna().unique() if type(value) is str
                }
            raw = st.text_area(
                "Value mapping (JSON object; unmapped values become missing)",
                value=json.dumps(prev_map, indent=2, ensure_ascii=False, allow_nan=False),
                max_chars=MAX_PIPELINE_CONFIG_BYTES,
                help="Quote text values. Numbers, booleans and null keep their types.",
                key=f"{key_prefix}dc_map_{shaper_id}",
            )
            try:
                mapping = json.loads(raw)
                if not isinstance(mapping, dict):
                    raise ValueError("A value mapping must be a JSON object.")
                for mapping_value in mapping.values():
                    scalar_token(mapping_value)
            except (ValueError, RecursionError) as exc:
                st.error(f"Cannot apply this mapping: {exc} The saved mapping is unchanged.")
                mapping = dict(prev_map)
            cfg["mapping"] = mapping

        return cast(ShaperStepConfig, cfg)
