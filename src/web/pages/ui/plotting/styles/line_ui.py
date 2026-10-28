"""Line- and scatter-series styling controls."""

from typing import Any

import streamlit as st

from .base_ui import BaseStyleUI


class LineStyleUI(BaseStyleUI):
    """Render marker and line controls."""

    def _render_specific_series_visuals(
        self, current_style: dict[str, Any], key_suffix: str, key_prefix: str = ""
    ) -> None:
        # [impl->req~ring5.figure.series-styling~2]
        with st.expander("Marker & Line", expanded=False):
            symbols = ["circle", "square", "diamond", "cross", "x", "triangle-up", "triangle-down"]
            saved_symbol = current_style.get("symbol", "circle")
            if isinstance(saved_symbol, str) and saved_symbol and saved_symbol not in symbols:
                symbols = [saved_symbol, *symbols]
            new_symbol = st.selectbox(
                "Marker Symbol",
                options=symbols,
                index=(
                    symbols.index(current_style.get("symbol", "circle"))
                    if current_style.get("symbol") in symbols
                    else 0
                ),
                key=f"{key_prefix}sym_{key_suffix}",
            )
            current_style["symbol"] = new_symbol

            marker_size = st.number_input(
                "Marker Size",
                min_value=0,
                value=int(current_style.get("marker_size", 8)),
                key=f"{key_prefix}msize_{key_suffix}",
            )
            current_style["marker_size"] = marker_size

            line_width = st.number_input(
                "Line Width",
                min_value=0.0,
                value=float(current_style.get("line_width", 2.0)),
                step=0.5,
                key=f"{key_prefix}lwidth_{key_suffix}",
            )
            current_style["line_width"] = line_width


class ScatterStyleUI(LineStyleUI):
    """Use line-style controls for scatter traces."""

    pass
