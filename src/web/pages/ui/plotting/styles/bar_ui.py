"""Bar-series styling controls."""

from typing import Any

import streamlit as st

from src.core.common.plot_payload import BAR_HATCH_PATTERNS
from .base_ui import BaseStyleUI


class BarStyleUI(BaseStyleUI):
    """Render bar-specific series controls."""

    def _render_specific_series_visuals(
        self, current_style: dict[str, Any], key_suffix: str, key_prefix: str = ""
    ) -> None:
        # [impl->req~ring5.figure.series-styling~1]
        cur_pat = current_style.get("pattern")
        if "pattern" in current_style and (
            type(cur_pat) is not str or cur_pat not in BAR_HATCH_PATTERNS
        ):
            raise ValueError("A saved series pattern must be an exact supported string.")
        options = (None, *BAR_HATCH_PATTERNS)

        new_pattern = st.selectbox(
            "Pattern",
            options=options,
            index=options.index(cur_pat),
            key=f"{key_prefix}pat_{key_suffix}",
            format_func=lambda x: (
                "Default (trace/theme)" if x is None else ("Solid" if x == "" else x)
            ),
        )
        if new_pattern is None:
            current_style.pop("pattern", None)
        else:
            current_style["pattern"] = new_pattern
