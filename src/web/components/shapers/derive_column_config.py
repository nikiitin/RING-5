"""Derive Column Config — UI for the DeriveColumn shaper.

Renders op-dependent widgets for creating one column from existing columns:
sum / ratio / scalar / concat / map (value recode).
"""

from typing import Any, cast

import pandas as pd
import streamlit as st

from src.core.models.shaper_models import ShaperStepConfig

_OPS = ["sum", "ratio", "scalar", "concat", "map"]
_SCALAR_OPS = ["+", "-", "*", "/"]
_OP_HELP = (
    "sum/concat: combine N columns · ratio: a / b · "
    "scalar: column ∘ literal · map: recode a column's values"
)


def _index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


class DeriveColumnConfig:
    @staticmethod
    def render(
        data: pd.DataFrame, existing_config: ShaperStepConfig, key_prefix: str, shaper_id: int
    ) -> ShaperStepConfig:
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
            prev_map = cast("dict[str, str]", existing_config.get("mapping", {}) or {})
            uniques = [str(v) for v in data[src].unique()] if src in data.columns else []
            default_text = "\n".join(f"{k}={v}" for k, v in prev_map.items()) or "\n".join(
                f"{u}={u}" for u in uniques
            )
            raw = st.text_area(
                "Value mapping (one `old=new` per line; unmapped → NaN)",
                value=default_text,
                key=f"{key_prefix}dc_map_{shaper_id}",
            )
            mapping: dict[str, str] = {}
            for line in raw.splitlines():
                if "=" in line:
                    old, new = line.split("=", 1)
                    mapping[old.strip()] = new.strip()
            cfg["mapping"] = mapping

        return cast(ShaperStepConfig, cfg)
