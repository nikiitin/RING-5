"""
Bar Style UI - Bar Chart Styling Configuration.

Implements style UI configuration specific to bar charts, including
bar-specific visual options and parameters.
"""

from typing import Any, Dict

import streamlit as st

from .base_ui import BaseStyleUI


class BarStyleUI(BaseStyleUI):
    def _render_specific_series_visuals(
        self, current_style: Dict[str, Any], key_suffix: str, key_prefix: str = ""
    ) -> None:
        patterns = ["", "/", "\\", "x", "-", "|", "+", "."]
        cur_pat = current_style.get("pattern", "")
        if isinstance(cur_pat, dict):
            cur_pat = cur_pat.get("shape", "")

        new_pattern = st.selectbox(
            "Pattern",
            options=patterns,
            index=patterns.index(cur_pat) if cur_pat in patterns else 0,
            key=f"{key_prefix}pat_{self.plot_id}_{key_suffix}",
            format_func=lambda x: "Solid" if x == "" else x,
        )
        current_style["pattern"] = new_pattern
